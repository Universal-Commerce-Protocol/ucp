#!/usr/bin/env python3
"""Fixture tests for the draft Order Modification extension (EP #943).

This file separates two kinds of checks:

  1. Schema-validator tests (executed here). Every fixture listed in
     fixtures/order_modification/manifest.json is validated against the
     extension schema, or the base Order/error schemas, and the result
     must match the manifest's `expect`. Negative fixtures prove that
     the schema rejects the violation named in `note`.

  2. Reference checks (executed here, illustrative). Small pure functions
     that encode rules JSON Schema cannot express across documents:
     request-vs-declaration validation order, Order history retention
     across a committed cancellation, byte-exact payload matching, and
     fail-safe handling of unknown outcomes. They operate on fixtures
     only. They are NOT a merchant server and prove nothing about any
     runtime.

Runtime Business behavior (replay caches, fencing, review queues,
concurrency) is described by the conformance vectors under
fixtures/order_modification/vectors/. This file checks only that each
vector is well formed and that every payload it embeds validates. The
vectors are inputs for a future runtime conformance suite; none has been
executed against an implementation.

Run: uv run python scripts/test_order_modification.py
Exit: 0 on all pass, 1 on any failure. Requires `ucp-schema` on PATH.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).parent))

import validate_examples as ve  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_BASE = ROOT / "source" / "schemas"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "order_modification"
SERVICES = ROOT / "source" / "services" / "shopping"

KNOWN_OUTCOMES = {
  "awaiting_business_decision",
  "committed",
  "refused",
  "failed",
  "indeterminate",
  "not_attempted",
}

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
  """Record one assertion and print a one-line result."""
  global passed, failed
  if condition:
    passed += 1
    print(f"  ok    {name}")
  else:
    failed += 1
    print(f"  FAIL  {name}" + (f"\n        {detail}" if detail else ""))


def load(rel: str) -> dict:
  """Load a fixture relative to the fixture directory."""
  return json.loads((FIXTURES / rel).read_text())


# -----------------------------------------------------------
# Layer 1: schema-validator tests
# -----------------------------------------------------------


def run_schema_check(payload: dict, spec: dict) -> tuple[bool, str]:
  """Validate payload per one manifest check; return (valid, errors)."""
  schema, op, direction = spec["schema"], spec["op"], spec["direction"]
  if "def" in spec:
    resolved = ve.resolve_schema(schema, direction, op, SCHEMA_BASE)
    sub = resolved["$defs"][spec["def"]]
    ok, errs = ve.validate_payload_with_schema(
      payload, sub, direction, op, SCHEMA_BASE
    )
  else:
    ok, errs = ve.validate_payload(payload, schema, direction, op, SCHEMA_BASE)
  text = " | ".join(f"{e.get('path', '')} {e.get('message', '')}" for e in errs)
  return ok, text


def test_manifest() -> None:
  """Every manifest fixture validates (or fails) as declared."""
  print("schema fixtures")
  manifest = json.loads((FIXTURES / "manifest.json").read_text())
  for entry in manifest["fixtures"]:
    payload = load(entry["file"])
    for spec in entry["checks"]:
      ok, text = run_schema_check(payload, spec)
      want = spec["expect"] == "valid"
      label = f"{entry['file']} [{spec.get('def') or spec['schema']}]"
      detail = text if ok != want else ""
      check(f"{label} -> {spec['expect']}", ok == want, detail)
      needle = spec.get("error_contains")
      if needle and not want:
        check(f"{label} reports '{needle}'", needle in text, f"errors: {text}")


def test_auto_composition() -> None:
  """A payload advertising the extension composes via ucp-schema."""
  print("auto-composition from the payload's capability declaration")
  payload = load("orders/order_by_unit_merchant_review.json")
  caps = payload["ucp"]["capabilities"]
  version = ve.UCP_VERSION_PLACEHOLDER
  caps["dev.ucp.shopping.order"] = [
    {
      "version": version,
      "schema": "https://ucp.dev/schemas/shopping/order.json",
    }
  ]
  caps["dev.ucp.shopping.order_modification"] = [
    {
      "version": version,
      "extends": ["dev.ucp.shopping.order"],
      "schema": "https://ucp.dev/schemas/shopping/order_modification.json",
    }
  ]
  ok, text = _compose_validate(payload, SCHEMA_BASE)
  check("composed Order validates (authority binding passes)", ok, text)
  broken = json.loads(json.dumps(payload))
  del broken["modification"]
  ok, text = _compose_validate(broken, SCHEMA_BASE)
  check("composed Order without declaration is rejected", not ok)
  absent = load("orders/order_extension_absent.json")
  absent["ucp"]["capabilities"]["dev.ucp.shopping.order"] = [
    {
      "version": version,
      "schema": "https://ucp.dev/schemas/shopping/order.json",
    }
  ]
  ok, text = _compose_validate(absent, SCHEMA_BASE)
  check("Order without the extension still validates as base Order", ok, text)


def _compose_validate(payload: dict, base: Path) -> tuple[bool, str]:
  import subprocess
  import tempfile

  with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
    json.dump(payload, f)
    path = f.name
  try:
    proc = subprocess.run(
      [
        "ucp-schema",
        "validate",
        path,
        "--op",
        "read",
        "--response",
        "--schema-local-base",
        str(base),
        "--schema-remote-base",
        "https://ucp.dev/schemas",
        "--json",
      ],
      capture_output=True,
      text=True,
      encoding="utf-8",
      check=False,
    )
  finally:
    Path(path).unlink()
  out = json.loads(proc.stdout) if proc.stdout.strip() else {}
  return bool(out.get("valid")), proc.stdout.strip() or proc.stderr.strip()


# -----------------------------------------------------------
# Layer 2: reference checks (illustrative, fixture-only)
# -----------------------------------------------------------


def check_request_against_declaration(order: dict, request: dict) -> str:
  """Return the error code a new request would get, or `admit`.

  Order of evaluation is normative: version precondition first, then
  structure, then unit addressing, then per-unit operation support.
  """
  decl = order.get("modification")
  if decl is None:
    return "modification_not_supported"
  if request["base_order_version"] != order["order_version"]:
    return "stale_order_state"
  targets = [
    json.dumps(o["target"], sort_keys=True) for o in request["operations"]
  ]
  kinds = {o["target"]["type"] for o in request["operations"]}
  if len(set(targets)) != len(targets) or {"order", "unit"} <= kinds:
    return "invalid_modification_request"
  units = {u["id"]: u for u in decl.get("units", [])}
  for op in request["operations"]:
    target = op["target"]
    if target["type"] == "order":
      if op["op"] not in decl["operations"]:
        return "operation_not_supported_for_unit"
    elif target["type"] == "unit":
      if target["id"] not in units:
        return "unknown_modification_unit"
      if op["op"] not in units[target["id"]]["operations"]:
        return "operation_not_supported_for_unit"
    else:
      return "invalid_modification_request"
  return "admit"


def check_order_history(before: dict, after: dict) -> list[str]:
  """Return violations of Order history rules across a commit."""
  problems = []
  after_lines = {li["id"]: li for li in after["line_items"]}
  for li in before["line_items"]:
    if li["id"] not in after_lines:
      problems.append(f"line {li['id']} deleted instead of retained")
  for li in after["line_items"]:
    total = li["quantity"]["total"]
    fulfilled = li["quantity"]["fulfilled"]
    if total == 0:
      derived = "removed"
    elif fulfilled == total:
      derived = "fulfilled"
    elif fulfilled > 0:
      derived = "partial"
    else:
      derived = "processing"
    if li["status"] != derived:
      problems.append(f"line {li['id']} status {li['status']} != {derived}")
  changed = {
    li["id"]
    for li in before["line_items"]
    if li["id"] in after_lines
    and li["quantity"]["total"] != after_lines[li["id"]]["quantity"]["total"]
  }
  b_events = before["fulfillment"].get("events", [])
  a_events = after["fulfillment"].get("events", [])
  if b_events != a_events:
    problems.append("fulfillment events changed")
  b_exp = {e["id"]: e for e in before["fulfillment"].get("expectations", [])}
  for exp in after["fulfillment"].get("expectations", []):
    touched = {i["id"] for i in exp["line_items"]} & changed
    if not touched and exp["id"] in b_exp and b_exp[exp["id"]] != exp:
      problems.append(f"retained expectation {exp['id']} altered")
  if after["order_version"] == before["order_version"]:
    problems.append("order_version did not change on commit")
  return problems


def is_success(outcome: str) -> bool:
  """Only `committed` is success; unknown values are never success."""
  return outcome == "committed"


def is_unresolved(outcome: str) -> bool:
  """Pending, indeterminate, and unrecognized outcomes stay unresolved."""
  return outcome not in KNOWN_OUTCOMES or outcome in {
    "awaiting_business_decision",
    "indeterminate",
  }


def body_digest(raw: bytes) -> str:
  """SHA-256 over raw body bytes, as RFC 9530 Content-Digest."""
  return "sha-256=" + hashlib.sha256(raw).hexdigest()


def test_reference_checks() -> None:
  """Exercise the illustrative reference checks on fixtures."""
  print("reference checks (illustrative, fixture-only)")
  decl_order = load("orders/order_by_unit_merchant_review.json")
  shipped = load("orders/order_by_unit_whole_order_unavailable.json")
  cases = [
    ("requests/cancel_unit.json", decl_order, "admit"),
    ("requests/cancel_order.json", decl_order, "admit"),
    ("requests/cancel_two_units.json", decl_order, "admit"),
    ("requests/cancel_unit.json", shipped, "admit"),
    ("requests/cancel_order.json", shipped, "operation_not_supported_for_unit"),
    (
      "requests/cancel_two_units.json",
      shipped,
      "operation_not_supported_for_unit",
    ),
  ]
  for rel, order, want in cases:
    got = check_request_against_declaration(order, load(rel))
    check(f"{rel} vs {order['id']}: {want}", got == want, f"got {got}")

  stale = load("requests/cancel_unit.json")
  stale["base_order_version"] = "v13"
  check(
    "stale version beats unit validation",
    check_request_against_declaration(decl_order, stale) == "stale_order_state",
  )
  unknown = load("requests/cancel_unit.json")
  unknown["operations"][0]["target"]["id"] = "unit_goods_9"
  check(
    "unknown unit rejected",
    check_request_against_declaration(decl_order, unknown)
    == "unknown_modification_unit",
  )
  stale_unknown = json.loads(json.dumps(unknown))
  stale_unknown["base_order_version"] = "v13"
  check(
    "version is checked before unit ids",
    check_request_against_declaration(decl_order, stale_unknown)
    == "stale_order_state",
  )
  mixed = load("requests/cancel_unit.json")
  mixed["operations"].append({"op": "cancel", "target": {"type": "order"}})
  check(
    "order target mixed with unit target rejected",
    check_request_against_declaration(decl_order, mixed)
    == "invalid_modification_request",
  )
  dup = load("requests/cancel_unit.json")
  dup["operations"].append(dup["operations"][0])
  check(
    "duplicate targets rejected",
    check_request_against_declaration(decl_order, dup)
    == "invalid_modification_request",
  )
  absent = load("orders/order_extension_absent.json")
  absent_req = load("requests/cancel_unit.json")
  absent["order_version"] = "v14"
  check(
    "extension absent: no programmatic cancellation inferred",
    check_request_against_declaration(absent, absent_req)
    == "modification_not_supported",
  )

  before = load("orders/history_before_cancel.json")
  after = load("orders/history_after_cancel_refund_pending.json")
  refunded = load("orders/history_after_refund_completed.json")
  check(
    "commit retains lines, derives removed, keeps shipment",
    check_order_history(before, after) == [],
    str(check_order_history(before, after)),
  )
  check(
    "refund completion changes only adjustments",
    check_order_history(after, refunded) == [],
    str(check_order_history(after, refunded)),
  )
  removed = next(li for li in after["line_items"] if li["id"] == "li_2")
  check(
    "removed line keeps quantity.original",
    removed["quantity"]["original"] == 1
    and removed["quantity"]["total"] == 0
    and removed["status"] == "removed",
  )
  refund_pending = next(
    a for a in after["adjustments"] if a["type"] == "refund"
  )
  refund_done = next(
    a for a in refunded["adjustments"] if a["type"] == "refund"
  )
  cancel_adj = next(
    a for a in after["adjustments"] if a["type"] == "cancellation"
  )
  check(
    "cancellation committed while refund pending",
    cancel_adj["status"] == "completed"
    and refund_pending["status"] == "pending",
  )
  est = before["modification"]["units"][1]["estimated_refund_amount"]
  check(
    "final refund differs from estimate",
    refund_done["status"] == "completed"
    and abs(refund_done["totals"][0]["amount"]) != est,
  )
  bad = load("orders/semantic_zero_quantity_not_removed.json")
  check(
    "zero quantity without removed status is caught",
    any("status" in p for p in check_order_history(before, bad)),
  )
  deleted = json.loads(json.dumps(after))
  deleted["line_items"] = deleted["line_items"][:1]
  check(
    "deleted line is caught",
    any("deleted" in p for p in check_order_history(before, deleted)),
  )

  check(
    "unknown outcome is not success",
    not is_success("queued_for_fraud_check"),
  )
  check(
    "unknown outcome stays unresolved",
    is_unresolved("queued_for_fraud_check"),
  )
  check(
    "pending is unresolved and not success",
    is_unresolved("awaiting_business_decision")
    and not is_success("awaiting_business_decision"),
  )
  check("committed is success", is_success("committed"))

  body = json.dumps(load("requests/cancel_unit.json")).encode()
  reordered_doc = load("requests/cancel_unit.json")
  reordered = json.dumps(
    {k: reordered_doc[k] for k in reversed(list(reordered_doc))}
  ).encode()
  check(
    "same JSON, different bytes => different digest",
    json.loads(body) == json.loads(reordered)
    and body_digest(body) != body_digest(reordered),
  )
  check(
    "identical bytes => identical digest",
    body_digest(body) == body_digest(body),
  )


def check_cancel_commit(
  before: dict, after: dict, cancelled_units: list[str]
) -> list[str]:
  """Check quantities and fulfillment across a committed cancellation."""
  problems = []
  units = {u["id"]: u for u in before["modification"].get("units", [])}
  cut: dict[str, int] = {}
  if cancelled_units == ["*"]:
    for li in before["line_items"]:
      cut[li["id"]] = li["quantity"]["total"]
  else:
    for uid in cancelled_units:
      for tgt in units[uid]["targets"]:
        cut[tgt["id"]] = cut.get(tgt["id"], 0) + tgt["quantity"]
  after_lines = {li["id"]: li for li in after["line_items"]}
  for li in before["line_items"]:
    now = after_lines[li["id"]]["quantity"]
    was = li["quantity"]
    want = was["total"] - cut.get(li["id"], 0)
    if now["total"] != want:
      problems.append(f"{li['id']} total {now['total']} != {want}")
    if now["fulfilled"] != was["fulfilled"]:
      problems.append(f"{li['id']} fulfilled changed")
    if now.get("original") != was.get("original"):
      problems.append(f"{li['id']} original changed")
  return problems


def plan_targets(decl: dict) -> dict:
  """Fail-safe Platform planning from a declaration (unknown vocab)."""
  plan = {"units": [], "order": False, "max_operations": 1}
  cancel = decl.get("order_cancellation", {})
  plan["order"] = bool(cancel.get("available"))
  if decl.get("granularity") == "by_unit":
    plan["units"] = [
      u["id"] for u in decl.get("units", []) if "cancel" in u["operations"]
    ]
  if decl.get("atomicity") in {"atomic", "per_unit"}:
    plan["max_operations"] = 1_000_000
  return plan


def test_order_invariants() -> None:
  """Order history, quantities, metadata, atomic review, refund split."""
  print("order invariants")
  before = load("orders/history_before_cancel.json")
  after = load("orders/history_after_cancel_refund_pending.json")
  check(
    "unit commit: totals drop by declared quantity, fulfilled untouched",
    check_cancel_commit(before, after, ["unit_goods_2"]) == [],
    str(check_cancel_commit(before, after, ["unit_goods_2"])),
  )
  wrong = check_cancel_commit(before, after, ["unit_goods_1"])
  check("mismatched cancelled unit is caught", len(wrong) >= 1)
  w_before = load("orders/whole_order_before_cancel.json")
  w_after = load("orders/whole_order_after_cancel.json")
  check(
    "whole-order commit retains every line",
    check_order_history(w_before, w_after) == [],
    str(check_order_history(w_before, w_after)),
  )
  check(
    "whole-order commit zeroes every unfulfilled line",
    check_cancel_commit(w_before, w_after, ["*"]) == [],
    str(check_cancel_commit(w_before, w_after, ["*"])),
  )
  check(
    "whole-order commit derives removed on every line",
    all(li["status"] == "removed" for li in w_after["line_items"]),
  )
  oc = w_before["modification"]["order_cancellation"]
  check(
    "whole-order metadata declared with by_unit granularity",
    w_before["modification"]["granularity"] == "by_unit"
    and oc["available"]
    and oc["processing_mode"] in {"immediate", "merchant_review"},
  )
  moved = json.loads(json.dumps(after))
  moved["line_items"][0]["quantity"]["fulfilled"] = 0
  check(
    "commit that alters fulfilled quantity is caught",
    any(
      "fulfilled" in p
      for p in check_cancel_commit(before, moved, ["unit_goods_2"])
    ),
  )
  pending = load("responses/atomic_pending_nothing_committed.json")
  check(
    "atomic pending: no unit committed, status open",
    pending["status"] == "open"
    and all(r["outcome"] != "committed" for r in pending["results"]),
  )
  by_type = {a["type"]: a for a in after["adjustments"]}
  check(
    "committed cancellation is distinct from refund completion",
    by_type["cancellation"]["status"] == "completed"
    and by_type["refund"]["status"] == "pending",
  )
  gran = load("orders/unknown_granularity_value.json")["modification"]
  plan = plan_targets(gran)
  check(
    "unknown granularity/atomicity: no unit addressing, one operation",
    plan["units"] == [] and plan["max_operations"] == 1 and plan["order"],
    str(plan),
  )
  known = plan_targets(
    load("orders/order_by_unit_merchant_review.json")["modification"]
  )
  check(
    "known vocabulary: units addressable, multi-operation allowed",
    known["units"] == ["unit_goods_1", "unit_goods_2"]
    and known["max_operations"] > 1,
  )


# -----------------------------------------------------------
# Executable specification model (NOT a merchant implementation)
# -----------------------------------------------------------

REPLAY_RETENTION = timedelta(hours=24)
TERMINAL = {"committed", "refused", "failed", "not_attempted"}


class UnavailableError(Exception):
  """Raised when the replay store is down; the Business fails closed."""


class SpecModel:
  """Tiny model of scoped claim, replay, fence, and lookup rules.

  It encodes only the normative reconciliation rules so they can be
  tested negatively. It executes no cancellation and says nothing about
  any real Business. `fence_ttl=None` is the conforming permanent
  tombstone; a timedelta models the NON-conforming temporary fence that
  the contract forbids. `lookup` is a pure read; only `fence` writes.
  """

  def __init__(
    self,
    retained: timedelta,
    fence_ttl: timedelta | None = None,
    supports_fence: bool = True,
  ):
    """Create a model with the chosen record and fence lifetimes."""
    self.retained = retained
    self.fence_ttl = fence_ttl
    self.supports_fence = supports_fence
    self.records: dict[tuple, dict] = {}
    self.claims: set[tuple] = set()  # permanent claim markers
    self.fences: dict[tuple, datetime | None] = {}
    self.committed_units: set[str] = set()
    self.store_up = True
    self.seq = 0

  def snapshot(self):
    """Return admission state: records, claims, and fences."""
    return (
      sorted(self.records),
      sorted(self.claims),
      sorted(self.fences.items(), key=lambda kv: kv[0]),
    )

  def _fenced(self, scope, now) -> bool:
    if scope not in self.fences:
      return False
    until = self.fences[scope]
    return until is None or now < until

  def claim(self, scope, body, now):
    """Atomically claim the scoped key; returns (kind, record)."""
    if not self.store_up:
      raise UnavailableError
    if self._fenced(scope, now):
      return "rejected_fenced", None
    rec = self.records.get(scope)
    if rec is not None:
      same = hashlib.sha256(body).digest() == rec["digest"]
      return ("replay" if same else "conflict"), rec
    self.seq += 1
    rec = {
      "modification_id": f"mod_{self.seq}",
      "digest": hashlib.sha256(body).digest(),
      "results": [{"outcome": "awaiting_business_decision"}],
      "created_at": now,
      "retained_until": now + self.retained,
    }
    self.records[scope] = rec
    self.claims.add(scope)
    return "admitted", rec

  def lookup(self, scope, now):
    """Strictly read-only scoped lookup: found or unresolved only."""
    rec = self.records.get(scope)
    if rec is not None and now <= rec["retained_until"]:
      return {"status": "found", "record": rec}
    if scope in self.claims:
      return {"status": "unresolved", "reason_code": "record_expired"}
    return {"status": "unresolved", "reason_code": "admission_in_flight"}

  def fence(self, scope, now):
    """Explicit atomic compare-and-set; the only operation that fences."""
    if not self.store_up:
      raise UnavailableError
    if not self.supports_fence:
      return {"error": "fence_not_supported"}
    if scope in self.claims:
      rec = self.records.get(scope)
      if rec is not None and now <= rec["retained_until"]:
        return {"status": "found", "record": rec}
      return {"status": "unresolved", "reason_code": "record_expired"}
    if scope not in self.fences:
      self.fences[scope] = (
        None if self.fence_ttl is None else now + self.fence_ttl
      )
    return {"status": "fenced", "key_fenced": True}

  def approve(self, scope, unit):
    """Commit an admitted attempt unless the unit is already cancelled."""
    res = self.records[scope]["results"][0]
    if res["outcome"] in TERMINAL:
      raise ValueError("terminal result is immutable")
    if unit in self.committed_units:
      res["outcome"] = "refused"
    else:
      self.committed_units.add(unit)
      res["outcome"] = "committed"
    return res["outcome"]

  def resolve(self, scope, outcome):
    """Move an in-progress result; terminal results are immutable."""
    res = self.records[scope]["results"][0]
    if res["outcome"] in TERMINAL:
      raise ValueError("terminal result is immutable")
    res["outcome"] = outcome


def test_get_safety() -> None:
  """GET lookup is read-only: it never fences or changes admission."""
  print("GET safety (RFC 9110 section 9.2.1)")
  t0 = datetime(2026, 10, 13, 9, 0, tzinfo=timezone.utc)
  scope = ("platform-a", "ord_9f2", "cancel", "key-1")
  body = b'{"base_order_version":"v14"}'
  m = SpecModel(retained=timedelta(days=30))
  before = m.snapshot()
  results = [m.lookup(scope, t0 + timedelta(seconds=i)) for i in range(25)]
  check(
    "25 repeated or prefetched lookups leave admission state unchanged",
    m.snapshot() == before,
  )
  check(
    "lookup of an unclaimed key is unresolved, never a non-commit",
    all(r["status"] == "unresolved" for r in results)
    and all("key_fenced" not in r for r in results),
  )
  kind, _ = m.claim(scope, body, t0 + timedelta(seconds=30))
  check(
    "the original is still admitted after any number of lookups",
    kind == "admitted",
  )
  check(
    "lookup then finds the claim",
    m.lookup(scope, t0 + timedelta(seconds=31))["status"] == "found",
  )
  after_claim = m.snapshot()
  for _ in range(5):
    m.lookup(scope, t0 + timedelta(minutes=1))
  check("lookups after admission change nothing", m.snapshot() == after_claim)
  expired = m.lookup(scope, t0 + timedelta(days=31))
  check(
    "expired record: unresolved/record_expired, no state change",
    expired["reason_code"] == "record_expired" and m.snapshot() == after_claim,
  )
  schema = json.loads(
    (SCHEMA_BASE / "shopping" / "order_modification.json").read_text()
  )
  props = schema["$defs"]["lookup_response"]["properties"]
  check(
    "lookup_response defines no fence or tombstone field",
    "key_fenced" not in props and "fenced_until" not in props,
  )
  check(
    "lookup_response status examples exclude not_found",
    "not_found" not in props["status"]["examples"],
  )
  legacy = load("lookups/unknown_not_found_status.json")
  check(
    "a lookup that says not_found is treated as unresolved",
    is_unresolved_lookup(legacy["status"]),
  )
  check(
    "only found is a definite lookup result",
    not is_unresolved_lookup("found") and is_unresolved_lookup("unresolved"),
  )
  for rel in sorted(p.name for p in (FIXTURES / "lookups").glob("*.json")):
    doc = load(f"lookups/{rel}")
    if "key_fenced" in doc:
      check(f"lookup fixture {rel} carries no key_fenced", False)
  check("no lookup fixture carries key_fenced", True)


def is_unresolved_lookup(status: str) -> bool:
  """Platform rule: anything but found is unresolved."""
  return status != "found"


def test_reconciliation_model() -> None:
  """Negative and positive tests of the reconciliation rules."""
  print("reconciliation rules (executable specification model)")
  t0 = datetime(2026, 10, 13, 9, 0, tzinfo=timezone.utc)
  scope = ("platform-a", "ord_9f2", "cancel", "key-1")
  body = b'{"base_order_version":"v14"}'
  late = t0 + timedelta(days=400)
  replacement = ("platform-a", "ord_9f2", "cancel", "key-replacement")

  m = SpecModel(retained=timedelta(days=30))
  res = m.lookup(scope, t0)
  check(
    "no record: lookup is unresolved, not a non-commit",
    res["status"] == "unresolved",
  )
  kind, _ = m.claim(scope, body, t0 + timedelta(seconds=2))
  check(
    "the late original can still be admitted (so a lookup negative is unsafe)",
    kind == "admitted",
  )

  m = SpecModel(retained=timedelta(days=30))
  res = m.fence(scope, t0)
  check(
    "fence on an unclaimed key installs the tombstone and returns fenced",
    res == {"status": "fenced", "key_fenced": True},
  )
  kind, rec = m.claim(scope, body, t0 + timedelta(seconds=2))
  check(
    "after fenced the in-flight original cannot commit",
    kind == "rejected_fenced" and rec is None and not m.records,
  )
  again = m.fence(scope, t0 + timedelta(hours=1))
  check(
    "fence is idempotent: a repeat returns fenced again",
    again == res and len(m.fences) == 1,
  )
  other = ("platform-a", "ord_9f2", "cancel", "key-2")
  check(
    "fence is scoped: another key is unaffected",
    m.claim(other, body, t0)[0] == "admitted",
  )
  foreign = ("platform-b",) + scope[1:]
  check(
    "another Platform's key is unaffected by the fence",
    m.claim(foreign, body, t0)[0] == "admitted",
  )

  m = SpecModel(retained=timedelta(days=30))
  m.claim(scope, body, t0)
  res = m.fence(scope, t0 + timedelta(seconds=1))
  check(
    "fence on a claimed key returns found and installs nothing",
    res["status"] == "found" and not m.fences,
  )

  m = SpecModel(retained=timedelta(days=2))
  m.claim(scope, body, t0)
  res = m.fence(scope, t0 + timedelta(days=3))
  check(
    "fence on a claimed key whose record expired is unresolved, not fenced",
    res["status"] == "unresolved" and not m.fences,
  )
  check(
    "the claim marker outlives the record, so the key can never be fenced",
    scope in m.claims
    and m.claim(scope, body, t0 + timedelta(days=4))[0] == "replay",
  )

  # Delayed original after the replacement and after ALL retention windows.
  m = SpecModel(retained=timedelta(days=30))
  m.fence(scope, t0)
  kind, _ = m.claim(replacement, body, t0 + timedelta(seconds=5))
  check("replacement under a new key is admitted", kind == "admitted")
  kind, rec = m.claim(scope, body, late)
  check(
    "delayed original after retained_until and replay window is rejected",
    kind == "rejected_fenced" and rec is None and len(m.records) == 1,
  )
  check(
    "only the replacement can commit the unit",
    m.approve(replacement, "unit_goods_2") == "committed"
    and m.committed_units == {"unit_goods_2"},
  )
  m = SpecModel(retained=timedelta(days=30))
  m.fence(scope, t0)
  m.claim(replacement, body, t0 + timedelta(seconds=5))
  kind, _ = m.claim(scope, body, late)
  check(
    "late original cannot be admitted while the replacement is pending",
    kind == "rejected_fenced",
  )

  # NON-conforming variant: a temporary fence lets the original through.
  m = SpecModel(retained=timedelta(days=30), fence_ttl=REPLAY_RETENTION)
  m.fence(scope, t0)
  m.claim(replacement, body, t0 + timedelta(seconds=5))
  kind, rec = m.claim(scope, body, t0 + timedelta(hours=25))
  check(
    "a temporary fence is unsafe: the late original is admitted "
    "(why the contract requires a permanent tombstone)",
    kind == "admitted" and rec is not None,
  )
  check(
    "...and it could commit before the replacement (non-conforming)",
    m.approve(scope, "unit_goods_2") == "committed"
    and m.approve(replacement, "unit_goods_2") == "refused",
  )

  m = SpecModel(retained=timedelta(days=30), supports_fence=False)
  res = m.fence(scope, t0)
  check(
    "a Business that cannot fence permanently rejects with fence_not_supported",
    res == {"error": "fence_not_supported"}
    and not m.fences
    and m.claim(scope, body, t0)[0] == "admitted",
  )

  m = SpecModel(retained=timedelta(days=30))
  k1, r1 = m.claim(scope, body, t0)
  k2, r2 = m.claim(scope, body, t0 + timedelta(seconds=30))
  check(
    "same key + identical bytes: replay, one record, no second attempt",
    k1 == "admitted" and k2 == "replay" and r1 is r2 and len(m.records) == 1,
  )
  k3, _ = m.claim(scope, body + b" ", t0 + timedelta(seconds=40))
  check(
    "same key + different bytes: conflict, no second attempt",
    k3 == "conflict" and len(m.records) == 1,
  )
  check(
    "another Platform's lookup does not see the record",
    m.lookup(("platform-b",) + scope[1:], t0)["status"] != "found",
  )

  m = SpecModel(retained=timedelta(days=2))
  m.claim(scope, body, t0)
  check(
    "within retained_until lookup is found",
    m.lookup(scope, t0 + timedelta(days=1, hours=23))["status"] == "found",
  )
  res = m.lookup(scope, t0 + timedelta(days=2, minutes=1))
  check(
    "after retained_until lookup is unresolved/record_expired",
    res["status"] == "unresolved" and res["reason_code"] == "record_expired",
  )

  m = SpecModel(retained=timedelta(days=30))
  m.claim(scope, body, t0)
  m.resolve(scope, "committed")
  try:
    m.resolve(scope, "refused")
    immutable = False
  except ValueError:
    immutable = True
  check("terminal result cannot change afterwards", immutable)

  m = SpecModel(retained=timedelta(days=30))
  m.store_up = False
  failures = 0
  for call in (
    lambda: m.claim(scope, body, t0),
    lambda: m.fence(scope, t0),
  ):
    try:
      call()
    except UnavailableError:
      failures += 1
  check(
    "storage outage fails closed for claim and fence, no state written",
    failures == 2 and not m.records and not m.fences,
  )

  retained_ok = True
  detail = ""
  for rel in sorted(p.name for p in (FIXTURES / "responses").glob("*.json")):
    doc = load(f"responses/{rel}")
    if "created_at" not in doc or rel.startswith("invalid_"):
      continue
    created = datetime.fromisoformat(doc["created_at"].replace("Z", "+00:00"))
    until = datetime.fromisoformat(doc["retained_until"].replace("Z", "+00:00"))
    if until - created < REPLAY_RETENTION:
      retained_ok = False
      detail += f" {rel}"
  check("every fixture retained_until >= created_at + 24h", retained_ok, detail)
  fenced = load("fences/fenced.json")
  check(
    "fixture fenced response carries key_fenced and no expiring field",
    fenced["key_fenced"] is True and "fenced_until" not in fenced,
  )


# -----------------------------------------------------------
# Conformance vectors (structure only; NOT executed against a runtime)
# -----------------------------------------------------------


def test_vectors() -> None:
  """Each vector is well formed and every embedded payload validates."""
  print("conformance vectors (structural; not run against a runtime)")
  manifest = json.loads((FIXTURES / "manifest.json").read_text())
  valid = {
    e["file"]
    for e in manifest["fixtures"]
    if all(c["expect"] == "valid" for c in e["checks"])
  }
  vectors = sorted((FIXTURES / "vectors").glob("*.json"))
  check("vectors present", len(vectors) >= 15, f"found {len(vectors)}")
  seen = set()
  for path in vectors:
    vec = json.loads(path.read_text())
    vid = vec.get("id", "")
    check(
      f"{path.name}: id unique and matches file",
      vid and vid not in seen and path.name.startswith(vid),
    )
    seen.add(vid)
    check(
      f"{vid}: declared runtime-only",
      vec.get("kind") == "runtime_conformance_vector"
      and vec.get("executed_against_runtime") is False,
    )
    check(
      f"{vid}: has title, refs, steps, assertions",
      all(vec.get(k) for k in ("title", "spec_refs", "steps", "assertions")),
    )
    refs_ok = True
    detail = ""
    for step in vec.get("steps", []):
      for side in ("request", "response"):
        ref = (step.get(side) or {}).get("body_ref")
        if ref and ref not in valid:
          refs_ok = False
          detail += f" {side} body_ref {ref} is not a valid fixture;"
      method = (step.get("request") or {}).get("method")
      path_ = (step.get("request") or {}).get("path", "")
      if method == "POST" and "/modifications" in path_:
        header_names = {k.lower() for k in step["request"].get("headers", {})}
        if "idempotency-key" not in header_names:
          refs_ok = False
          detail += " state-changing POST lacks Idempotency-Key;"
      if method == "GET" and "idempotency-key" in {
        k.lower() for k in (step.get("request") or {}).get("headers", {})
      }:
        refs_ok = False
        detail += " GET carries Idempotency-Key;"
    check(f"{vid}: payload refs valid, key rules", refs_ok, detail)


# -----------------------------------------------------------
# Discovery and bindings
# -----------------------------------------------------------

EXT = "dev.ucp.shopping.order_modification"
OPS_REST = {
  "create_modification",
  "get_modification",
  "lookup_modification",
  "fence_modification",
}


def service_key(capability: str) -> str:
  """Service that serves a capability: its {authority}.{service} prefix."""
  return ".".join(capability.split(".")[:3])


def local_schema(url: str) -> Path:
  """Map a ucp.dev service URL to its source file."""
  tail = url.split("/services/", 1)[1]
  return ROOT / "source" / "services" / tail


def discover(profile: dict, capability: str, transport: str) -> set:
  """Discover operation names for a negotiated capability.

  A client follows existing registry semantics only: the capability's
  namespace names the service, the profile's services[service][] entry
  for the transport names the descriptor, and the descriptor lists the
  operations. Returns an empty set when the capability is not advertised.
  """
  ucp = profile["ucp"]
  if capability not in ucp["capabilities"]:
    return set()
  entries = ucp["services"].get(service_key(capability), [])
  found = set()
  for entry in entries:
    if entry["transport"] != transport:
      continue
    doc = json.loads(local_schema(entry["schema"]).read_text())
    if transport == "rest":
      for item in doc["paths"].values():
        for method in ("get", "post"):
          if method in item:
            found.add(item[method]["operationId"])
    else:
      found |= {m["name"] for m in doc["methods"]}
  return found


def test_discovery() -> None:
  """A client can discover the operations from the Business profile."""
  print("transport discovery through the profile")
  profile = load("profiles/business_profile.json")
  caps = profile["ucp"]["capabilities"]
  ext = caps[EXT][0]
  check(
    "extension extends the advertised Order capability",
    "dev.ucp.shopping.order" in ext["extends"]
    and "dev.ucp.shopping.order" in caps,
  )
  check(
    "no separate service key is needed or used",
    service_key(EXT) == "dev.ucp.shopping"
    and set(profile["ucp"]["services"]) == {"dev.ucp.shopping"},
  )
  for transport in ("rest", "mcp"):
    ops = discover(profile, EXT, transport)
    check(
      f"{transport}: modification operations discovered from the profile",
      ops >= OPS_REST,
      str(sorted(ops)),
    )
    check(
      f"{transport}: base operations still discovered",
      "get_order" in ops,
    )
  bare = json.loads(json.dumps(profile))
  del bare["ucp"]["capabilities"][EXT]
  check(
    "profile without the extension yields no callable modification ops",
    discover(bare, EXT, "rest") == set()
    and discover(bare, EXT, "mcp") == set(),
  )
  rest = json.loads((SERVICES / "rest.openapi.json").read_text())
  mcp = json.loads((SERVICES / "mcp.openrpc.json").read_text())
  refs = []
  for text in (json.dumps(rest), json.dumps(mcp)):
    refs += re.findall(
      r'"\.\./\.\./schemas/shopping/order_modification\.json#/\$defs/([\w.]+)"',
      text,
    )
  schema = json.loads(
    (SCHEMA_BASE / "shopping" / "order_modification.json").read_text()
  )
  check(
    "descriptor $refs resolve to extension $defs",
    bool(refs) and all(r in schema["$defs"] for r in refs),
    str(sorted(set(refs) - set(schema["$defs"]))),
  )


def negotiate(platform: dict, business: dict) -> set:
  """Capabilities negotiated: common name and version, parents included."""
  p_caps = platform["ucp"]["capabilities"]
  b_caps = business["ucp"]["capabilities"]
  agreed = {
    name
    for name, entries in b_caps.items()
    if name in p_caps
    and {e["version"] for e in entries} & {e["version"] for e in p_caps[name]}
  }
  changed = True
  while changed:
    changed = False
    for name in sorted(agreed):
      parents = b_caps[name][0].get("extends", [])
      parents = [parents] if isinstance(parents, str) else parents
      if parents and not all(par in agreed for par in parents):
        agreed.discard(name)
        changed = True
  return agreed


def client_operations(descriptor_ops: set, negotiated: set) -> set:
  """Operations a client exposes: gated operations need negotiation."""
  gated = descriptor_ops & OPS_REST
  return descriptor_ops if EXT in negotiated else descriptor_ops - gated


def business_handle(
  operation: str, negotiated: bool
) -> tuple[dict | None, bool]:
  """Gate a Business call; return (error or None, state_changed)."""
  if operation in OPS_REST and not negotiated:
    return load("errors/modification_not_supported.json"), False
  return None, True


def test_gating() -> None:
  """Operations are exposed and accepted only when negotiated."""
  print("capability gating")
  business = load("profiles/business_profile.json")
  both = json.loads(json.dumps(business))
  both["ucp"]["capabilities"].setdefault("dev.ucp.shopping.checkout", [])
  platform = json.loads(json.dumps(business))
  without = json.loads(json.dumps(business))
  del without["ucp"]["capabilities"][EXT]
  other_version = json.loads(json.dumps(business))
  other_version["ucp"]["capabilities"][EXT][0]["version"] = "2099-01-01"
  no_parent = json.loads(json.dumps(business))
  del no_parent["ucp"]["capabilities"]["dev.ucp.shopping.order"]
  rest_ops = discover(business, EXT, "rest")
  mcp_ops = discover(business, EXT, "mcp")
  cases = [
    ("both advertise the same version", platform, business, True),
    ("Platform does not advertise the extension", without, business, False),
    ("Business does not advertise the extension", platform, without, False),
    ("versions do not intersect", other_version, business, False),
    ("parent Order capability not negotiated", no_parent, business, False),
  ]
  for label, plat, biz, want in cases:
    agreed = negotiate(plat, biz)
    got = EXT in agreed
    check(f"negotiation: {label} -> {want}", got == want, str(sorted(agreed)))
    for ops in (rest_ops, mcp_ops):
      exposed = client_operations(ops, agreed) & OPS_REST
      check(
        f"client exposes modification ops iff negotiated ({label})",
        (exposed == OPS_REST) == want and (want or not exposed),
      )
    err, changed = business_handle("create_modification", got)
    if want:
      check(f"Business accepts when negotiated ({label})", err is None)
    else:
      code = err["messages"][0]["code"] if err else None
      check(
        f"Business rejects with modification_not_supported ({label})",
        code == "modification_not_supported" and not changed,
      )
  agreed = negotiate(without, business)
  check(
    "base operations stay exposed without the extension",
    "get_order" in client_operations(rest_ops, agreed),
  )
  for op in sorted(OPS_REST):
    err, changed = business_handle(op, False)
    check(
      f"Business rejects {op} without negotiation, no state change",
      err is not None and not changed,
    )


def test_bindings() -> None:
  """Binding operations declared in the core service descriptors."""
  print("binding descriptors")
  rest = json.loads((SERVICES / "rest.openapi.json").read_text())
  mcp = json.loads((SERVICES / "mcp.openrpc.json").read_text())
  paths = rest["paths"]
  create = paths["/orders/{id}/modifications"]["post"]
  names = {p["$ref"].rsplit("/", 1)[-1] for p in create["parameters"]}
  check("REST create requires Idempotency-Key", "idempotency_key" in names)
  check("REST create requires Content-Digest", "content_digest" in names)
  fence = paths["/orders/{id}/modifications/fence"]
  check("fence is a POST, not a GET", "post" in fence and "get" not in fence)
  fence_names = {
    p["$ref"].rsplit("/", 1)[-1] for p in fence["post"]["parameters"]
  }
  check(
    "REST fence requires its own Idempotency-Key and Content-Digest",
    {"idempotency_key", "content_digest"} <= fence_names,
  )
  check(
    "REST lookup is GET-only (safe method)",
    set(paths["/orders/{id}/modifications/lookup"]) - {"parameters"} == {"get"},
  )
  for route, method, codes in (
    ("/orders/{id}/modifications", "post", ["200", "201"]),
    ("/orders/{id}/modifications/{modification_id}", "get", ["200"]),
    ("/orders/{id}/modifications/lookup", "get", ["200"]),
    ("/orders/{id}/modifications/fence", "post", ["200"]),
  ):
    for code in codes:
      hdr = paths[route][method]["responses"][code]["headers"]
      check(
        f"{method.upper()} {route} {code} declares Cache-Control: no-store",
        hdr.get("Cache-Control", {}).get("schema", {}).get("const")
        == "no-store",
      )
  for route in (
    "/orders/{id}/modifications/{modification_id}",
    "/orders/{id}/modifications/lookup",
  ):
    get = paths[route]["get"]
    get_names = {p["$ref"].rsplit("/", 1)[-1] for p in get["parameters"]}
    check(
      f"REST GET {route} has no Idempotency-Key",
      "idempotency_key" not in get_names,
    )
  lookup = paths["/orders/{id}/modifications/lookup"]["get"]
  lookup_names = {p["$ref"].rsplit("/", 1)[-1] for p in lookup["parameters"]}
  check(
    "REST lookup carries the original key in a distinct header",
    "original_idempotency_key" in lookup_names,
  )
  methods = {m["name"]: m for m in mcp["methods"]}

  def meta_required(method: dict) -> set:
    meta = next(p for p in method["params"] if p["name"] == "meta")
    return set(meta["schema"].get("allOf", [{}, {}])[-1].get("required", []))

  check(
    "MCP create requires meta.idempotency-key",
    "idempotency-key" in meta_required(methods["create_modification"]),
  )
  for name in ("get_modification", "lookup_modification"):
    check(
      f"MCP {name} does not require meta.idempotency-key",
      "idempotency-key" not in meta_required(methods[name]),
    )
  check(
    "MCP fence requires meta.idempotency-key",
    "idempotency-key" in meta_required(methods["fence_modification"]),
  )
  lookup_args = {p["name"] for p in methods["lookup_modification"]["params"]}
  fence_args = {p["name"] for p in methods["fence_modification"]["params"]}
  check(
    "MCP original key is a lookup argument, REST header equivalent",
    "original_idempotency_key" in lookup_args,
  )
  check(
    "MCP fence carries the original key inside the fence_request body",
    "fence" in fence_args and "original_idempotency_key" not in fence_args,
  )
  base_paths = {"/checkout-sessions", "/carts", "/orders/{id}"}
  check("pre-existing core paths remain", base_paths <= set(paths))


def main() -> int:
  """Run all test groups."""
  if ve.shutil.which("ucp-schema") is None:
    print(ve.UCP_SCHEMA_MISSING)
    return 1
  test_manifest()
  test_auto_composition()
  test_reference_checks()
  test_order_invariants()
  test_get_safety()
  test_reconciliation_model()
  test_vectors()
  test_discovery()
  test_gating()
  test_bindings()
  print(f"\n{passed} passed, {failed} failed")
  return 1 if failed else 0


if __name__ == "__main__":
  sys.exit(main())
