#!/usr/bin/env python3
# cspell:ignore ucp unprocessable linearizable unbilled Dalet Dagesh skey
# cspell:ignore canonicalizer interleavings unneg lref
"""Conformance vectors for the order_consultation extension (EP #944 draft).

WHAT THIS IS. A protocol conformance harness: an in-memory *reference model*
of the rules the specification states (admission, idempotent replay, lost
response recovery, application), driven by named test vectors. Every wire
payload the model emits is validated against the schemas in
source/schemas/shopping/order_consultation.json using `ucp-schema`.

WHAT THIS IS NOT. It is not a deployed merchant service and it does not
prove that any production Business enforces linearizable admission. The
concurrency vectors replay the *authoritative admission orders* a conforming
Business must be equivalent to; they are protocol vectors, not load tests.
An implementer proves their own server by running the same vectors against
it through its API.

Vector IDs (CV-xx) are referenced from
docs/specification/shopping/extensions/order-consultation.md.

Run: python3 scripts/test_order_consultation.py
Exit: 0 on all pass, 1 on any failure.

Tests that need the `ucp-schema` binary are skipped, and reported as
skipped, when it is missing.
"""

import base64
import contextlib
import copy
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parent.parent
SCHEMA = REPO / "source/schemas/shopping/order_consultation.json"
SPEC = REPO / "docs/specification/shopping/extensions/order-consultation.md"

V = "2026-04-08"
CAP = "dev.ucp.shopping.order_consultation"
SCOPE_READ = f"{CAP}:read"
SCOPE_DECIDE = f"{CAP}:decide"
DIGEST_CONTEXT = "dev.ucp.shopping.order_consultation.proposal.v1"
DIGEST_MEMBERS = (
  "consultation_id",
  "order_id",
  "revision",
  "change_type",
  "scope",
  "proposed_terms",
  "baseline_reference",
  "decision_deadline",
  "effective_from",
  "effective_time_rule",
  "application_deadline",
)

# -----------------------------------------------------------
# Harness
# -----------------------------------------------------------

_RESULTS: list[tuple[str, bool, str]] = []
_SKIPPED: list[str] = []
_PAYLOADS: list[tuple[str, str, dict]] = []  # (vector, def, payload)
_RECORD = [True]  # exhaustive runs switch payload capture off


def _emit(vector, def_name, payload):
  """Capture an emitted payload for schema validation."""
  if _RECORD[0]:
    _PAYLOADS.append((vector, def_name, payload))


def _check(name: str, condition: bool, detail: str = "") -> None:
  """Record one assertion."""
  _RESULTS.append((name, bool(condition), detail))


def _t(text: str) -> datetime:
  """Parse an RFC 3339 `Z` timestamp."""
  return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _z(moment: datetime) -> str:
  """Format a datetime as an RFC 3339 `Z` timestamp."""
  return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jcs(value) -> str:
  """RFC 8785 JSON Canonicalization for the value types used here.

  Objects sort by UTF-16 code units, strings use the shortest JSON escapes,
  and only integers within the I-JSON safe range are accepted (floats are
  rejected rather than risk a serialization difference).
  """
  if isinstance(value, bool):
    return "true" if value else "false"
  if value is None:
    return "null"
  if isinstance(value, int):
    if abs(value) > 2**53 - 1:
      raise ValueError("integer outside the I-JSON safe range")
    return str(value)
  if isinstance(value, float):
    raise ValueError("floats are not permitted in digest input")
  if isinstance(value, str):
    return json.dumps(value, ensure_ascii=False)
  if isinstance(value, list):
    return "[" + ",".join(jcs(v) for v in value) + "]"
  if isinstance(value, dict):
    keys = sorted(value, key=lambda k: k.encode("utf-16-be"))
    return (
      "{"
      + ",".join(
        json.dumps(k, ensure_ascii=False) + ":" + jcs(value[k]) for k in keys
      )
      + "}"
    )
  raise TypeError(type(value))


def digest_input(proposal: dict) -> dict:
  """Return the exact object whose JCS form is hashed for the digest."""
  terms = {k: proposal[k] for k in DIGEST_MEMBERS if k in proposal}
  terms["digest_context"] = DIGEST_CONTEXT
  return terms


def proposal_digest(proposal: dict) -> str:
  """Canonical proposal digest (not an HTTP Content-Digest)."""
  canon = jcs(digest_input(proposal))
  return "sha-256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


# -----------------------------------------------------------
# Reference model
# -----------------------------------------------------------


class Actor:
  """An authenticated caller: a Platform acting for a buyer."""

  def __init__(
    self,
    platform,
    buyer,
    scopes,
    max_delta=None,
    negotiated=True,
    token="buyer",
    token_exp=None,
    allowed_consultations=None,
  ):
    """Create an actor.

    `max_delta` and `allowed_consultations` model delegation/mandate limits;
    `negotiated` says whether the extension is in the negotiated capability
    intersection. `token` is the credential presented: "buyer" is a
    buyer-authenticated identity token for `buyer` (expiring at `token_exp`
    when set), "platform" is Platform credentials only, "none" is nothing.
    """
    self.platform = platform
    self.buyer = buyer
    self.scopes = set(scopes)
    self.max_delta = max_delta
    self.negotiated = negotiated
    self.token = token
    self.token_exp = token_exp
    self.allowed_consultations = allowed_consultations


def _ucp_ok() -> dict:
  return {
    "version": V,
    "capabilities": {CAP: [{"version": V}]},
  }


def _err(status, code, severity, content, data=None):
  message = {
    "type": "error",
    "code": code,
    "severity": severity,
    "content": content,
  }
  if data:
    message["data"] = data
  body = {
    "ucp": {
      "version": V,
      "status": "error",
      "capabilities": {CAP: [{"version": V}]},
    },
    "messages": [message],
  }
  _emit("error", "consultation_error_response", body)
  return status, body


def _not_negotiated():
  """Core `capabilities_incompatible` business outcome (HTTP 200)."""
  body = {
    "ucp": {"version": V, "status": "error"},
    "messages": [
      {
        "type": "error",
        "code": "capabilities_incompatible",
        "severity": "unrecoverable",
        "content": "order_consultation was not negotiated.",
      }
    ],
  }
  return 200, body


def _identity_required(invalid):
  """Core Identity Linking `identity_required` (HTTP 401)."""
  return _err(
    401,
    "identity_required",
    "requires_buyer_review",
    "A valid buyer identity token is required."
    if not invalid
    else "The buyer identity token is invalid or expired.",
  )


class ReferenceBusiness:
  """Single-writer reference model of a conforming Business.

  Every state-changing call is one atomic step on a single timeline, which
  is exactly the linearizable admission the specification requires.
  """

  def __init__(self, now="2026-10-20T12:00:00Z"):
    """Create an empty Business at `now`."""
    self.now = _t(now)
    self.orders: dict[str, dict] = {}
    self.cons: dict[tuple, dict] = {}
    self.decisions: dict[str, dict] = {}
    self.idem: dict[tuple, dict] = {}
    self.inflight: dict[tuple, bytes] = {}
    self.replay_store_up = True
    self.log: list[dict] = []
    self.unsafe_arrival_clock = False  # models a NON-conforming Business
    self.charges: list[dict] = []  # payment side effects (must stay empty)
    self.rentals: dict[str, dict] = {}
    self._seq = 0

  # -- fixtures ------------------------------------------------

  def add_order(self, order_id, buyer, version="v12", line_items=None):
    """Register an accepted Order owned by `buyer`."""
    self.orders[order_id] = {
      "buyer": buyer,
      "version": version,
      "line_items": line_items or [],
      "applications": [],
    }

  def add_rental(self, rental_id, order_id, start, rate, unit="hour"):
    """Register a metered rental with its original accepted tariff."""
    self.rentals[rental_id] = {
      "order_id": order_id,
      "usage": [],
      "schedule": [
        {"valid_from": start, "rate_amount": rate, "billing_unit": unit}
      ],
    }

  def advance(self, to):
    """Move the authoritative clock forward."""
    moment = _t(to)
    assert moment >= self.now, "clock must not move backwards"
    self.now = moment

  def _log(self, kind, **info):
    """Append one entry to the authoritative serialization log."""
    if self.log:
      assert self.now >= self.log[-1]["ts"], "clock moved backwards"
    entry = {"seq": len(self.log) + 1, "ts": self.now, "kind": kind}
    entry.update(info)
    self.log.append(entry)
    return entry

  # -- Business-side proposal lifecycle (not Platform operations) --

  def _next(self, prefix):
    self._seq += 1
    return f"{prefix}_{self._seq}"

  def issue(self, order_id, cid, **fields):
    """Issue revision 1 of a new consultation."""
    assert (order_id, cid) not in self.cons
    self.cons[(order_id, cid)] = {"revs": [], "decision": None}
    return self._add_revision(order_id, cid, fields, supersedes=None)

  def revise(self, order_id, cid, **fields):
    """Supersede the undecided current revision with a new revision."""
    cons = self.cons[(order_id, cid)]
    if cons["decision"] is not None:
      self._log(
        "supersede",
        cid=cid,
        revision=cons["revs"][-1]["revision"],
        committed=False,
      )
      raise ValueError("decided: issue a new consultation instead")
    current = cons["revs"][-1]
    status = self._rev_status(cons, current)
    if status != "open":
      self._log(
        "supersede", cid=cid, revision=current["revision"], committed=False
      )
      raise ValueError(f"cannot revise a {status} revision")
    self._log(
      "supersede", cid=cid, revision=current["revision"], committed=True
    )
    current["_status"] = "superseded"
    new = self._add_revision(
      order_id, cid, fields, supersedes=current["revision"]
    )
    current["superseded_by_revision"] = new["revision"]
    return new

  def withdraw(self, order_id, cid):
    """Withdraw an undecided proposal; never erases a recorded decision."""
    cons = self.cons[(order_id, cid)]
    if cons["decision"] is not None:
      self._log(
        "withdraw",
        cid=cid,
        revision=cons["revs"][-1]["revision"],
        committed=False,
      )
      raise ValueError("a recorded decision cannot be withdrawn")
    current = cons["revs"][-1]
    opened = self._rev_status(cons, current) == "open"
    self._log(
      "withdraw", cid=cid, revision=current["revision"], committed=opened
    )
    if opened:
      current["_status"] = "withdrawn"

  def _add_revision(self, order_id, cid, fields, supersedes):
    cons = self.cons[(order_id, cid)]
    rev = {
      "consultation_id": cid,
      "order_id": order_id,
      "revision": len(cons["revs"]) + 1,
      "_status": "open",
      "baseline_reference": {"order_version": self.orders[order_id]["version"]},
    }
    rev.update(fields)
    if supersedes:
      rev["supersedes_revision"] = supersedes
    rev["proposal_digest"] = proposal_digest(rev)
    cons["revs"].append(rev)
    return rev

  def _rev_status(self, cons, rev):
    stored = rev["_status"]
    if stored != "open":
      return stored
    if cons["decision"] is not None and rev is cons["revs"][-1]:
      return cons["decision"]["_outcome"]
    if self.now > _t(rev["decision_deadline"]):
      return "expired"
    return "open"

  def _public(self, cons, rev):
    out = {k: v for k, v in rev.items() if not k.startswith("_")}
    out["status"] = self._rev_status(cons, rev)
    return out

  # -- authorization ------------------------------------------

  def _authn(self, actor):
    """Buyer-authenticated token present and unexpired, else 401."""
    if actor.token != "buyer":
      return _identity_required(invalid=False)
    if actor.token_exp and self.now >= _t(actor.token_exp):
      return _identity_required(invalid=True)
    return None

  def _authorize(self, actor, order_id, cid, scope):
    if not actor.negotiated:
      return _not_negotiated()
    unauthenticated = self._authn(actor)
    if unauthenticated:
      return unauthenticated
    order = self.orders.get(order_id)
    cons = self.cons.get((order_id, cid))
    if order is None or cons is None or order["buyer"] != actor.buyer:
      return _err(404, "not_found", "unrecoverable", "Not found.")
    if scope not in actor.scopes:
      return _err(
        403, "insufficient_scope", "unrecoverable", f"Requires {scope}."
      )
    return None

  # -- reads ---------------------------------------------------

  def get_consultation(self, actor, order_id, cid):
    """Consultation read."""
    denied = self._authorize(actor, order_id, cid, SCOPE_READ)
    if denied:
      return denied
    cons = self.cons[(order_id, cid)]
    cur = cons["revs"][-1]
    status = self._rev_status(cons, cur)
    body = {
      "ucp": _ucp_ok(),
      "consultation_id": cid,
      "order_id": order_id,
      "status": status,
      "current_revision": cur["revision"],
      "proposal": self._public(cons, cur),
      "revisions": [
        {
          "revision": r["revision"],
          "status": self._rev_status(cons, r),
          "proposal_digest": r["proposal_digest"],
        }
        for r in cons["revs"]
      ],
    }
    if cons["decision"] is not None:
      body["decision"] = self._receipt_public(cons["decision"])
    _emit("get_consultation", "consultation", body)
    return 200, body

  def get_revision(self, actor, order_id, cid, revision):
    """Revision-specific read: exact historical terms."""
    denied = self._authorize(actor, order_id, cid, SCOPE_READ)
    if denied:
      return denied
    cons = self.cons[(order_id, cid)]
    if not 1 <= revision <= len(cons["revs"]):
      return _err(404, "not_found", "unrecoverable", "Not found.")
    body = {"ucp": _ucp_ok()}
    body.update(self._public(cons, cons["revs"][revision - 1]))
    _emit("get_revision", "consultation_revision", body)
    return 200, body

  def list_consultations(self, actor, order_id, statuses=("open",)):
    """Order-scoped list: the mandatory discovery path."""
    if not actor.negotiated:
      return _not_negotiated()
    unauthenticated = self._authn(actor)
    if unauthenticated:
      return unauthenticated
    order = self.orders.get(order_id)
    if order is None or order["buyer"] != actor.buyer:
      return _err(404, "not_found", "unrecoverable", "Not found.")
    if SCOPE_READ not in actor.scopes:
      return _err(403, "insufficient_scope", "unrecoverable", "Scope.")
    rows = []
    for (oid, cid), cons in self.cons.items():
      if oid != order_id:
        continue
      cur = cons["revs"][-1]
      status = self._rev_status(cons, cur)
      if status not in statuses:
        continue
      row = {
        "consultation_id": cid,
        "order_id": order_id,
        "status": status,
        "current_revision": cur["revision"],
        "change_type": cur["change_type"],
        "decision_deadline": cur["decision_deadline"],
        "proposal_digest": cur["proposal_digest"],
      }
      if cons["decision"] is not None:
        row["decision_id"] = cons["decision"]["decision_id"]
      rows.append(row)
    body = {
      "ucp": _ucp_ok(),
      "order_id": order_id,
      "consultations": rows,
      "pagination": {"has_next_page": False},
    }
    _emit("list", "consultation_list", body)
    return 200, body

  def _receipt_public(self, receipt):
    return {k: v for k, v in receipt.items() if not k.startswith("_")}

  def get_decision(self, actor, order_id, cid, decision_id):
    """Decision read by `decision_id`."""
    denied = self._authorize(actor, order_id, cid, SCOPE_READ)
    if denied:
      return denied
    receipt = self.decisions.get(decision_id)
    if receipt is None or receipt["consultation_id"] != cid:
      return _err(404, "not_found", "unrecoverable", "Not found.")
    body = {"ucp": _ucp_ok()}
    body.update(self._receipt_public(receipt))
    _emit("get_decision", "decision_receipt", body)
    return 200, body

  def lookup_by_key(self, actor, order_id, cid, key):
    """Decision lookup by the original scoped idempotency key."""
    denied = self._authorize(actor, order_id, cid, SCOPE_READ)
    if denied:
      return denied
    scope_key = (actor.platform, order_id, cid, "decide", key)
    body = {"ucp": _ucp_ok(), "checked_at": _z(self.now)}
    record = self.idem.get(scope_key)
    if record is not None and record["decision_id"]:
      body["outcome"] = "recorded"
      body["decision"] = self._receipt_public(
        self.decisions[record["decision_id"]]
      )
    elif scope_key in self.inflight:
      body["outcome"] = "in_flight"
    else:
      cons = self.cons[(order_id, cid)]
      body["outcome"] = "not_recorded"
      closed = self._rev_status(cons, cons["revs"][-1]) != "open"
      body["final"] = closed
      if closed:
        body["final_reason"] = "consultation_closed"
    self._log(
      "lookup",
      key=key,
      platform=actor.platform,
      cid=cid,
      outcome=body["outcome"],
      final=body.get("final", False),
    )
    _emit("lookup", "decision_lookup", body)
    return 200, body

  # -- decision admission -------------------------------------

  def begin_decide(self, actor, order_id, cid, key, raw):
    """Register an in-flight admission (request sent, outcome unknown)."""
    self.inflight[(actor.platform, order_id, cid, "decide", key)] = (
      raw,
      self.now,
    )

  def decide(self, actor, order_id, cid, key, raw):
    """Admit a decision. `raw` are the exact request body bytes."""
    scope_key = (actor.platform, order_id, cid, "decide", key)
    before = len(self.decisions)
    try:
      result = self._decide(actor, order_id, cid, key, raw, scope_key)
    finally:
      arrived = self.inflight.pop(scope_key, None)
    self._log(
      "decide",
      key=key,
      platform=actor.platform,
      cid=cid,
      status=result[0],
      committed=len(self.decisions) > before,
      received_at=arrived[1] if arrived else self.now,
    )
    return result

  def _decide(self, actor, order_id, cid, key, raw, scope_key):
    denied = self._authorize(actor, order_id, cid, SCOPE_DECIDE)
    if denied:
      return denied
    if not self.replay_store_up:
      return _err(
        503,
        "replay_store_unavailable",
        "recoverable",
        "Replay store unavailable; nothing was recorded. Retry the same "
        "key and body.",
      )
    body_hash = hashlib.sha256(raw).hexdigest()
    prior = self.idem.get(scope_key)
    if prior is not None:
      if prior["body_hash"] != body_hash:
        return _err(
          409,
          "idempotency_key_conflict",
          "unrecoverable",
          "Idempotency-Key reused with a different request body.",
        )
      return prior["response"]  # replay: no second side effect
    request = json.loads(raw)
    if any(
      k in request for k in ("scope", "proposed_terms", "authorized_scope")
    ):
      return _err(
        422,
        "decision_scope_not_accepted",
        "unrecoverable",
        "Scope and terms come from the immutable revision.",
      )
    cons = self.cons[(order_id, cid)]
    cur = cons["revs"][-1]
    wanted = request["proposal_revision"]
    status = self._rev_status(cons, cur)
    arrived = self.inflight.get(scope_key)
    if (
      self.unsafe_arrival_clock
      and status == "expired"
      and arrived
      and arrived[1] <= _t(cur["decision_deadline"])
    ):
      status = "open"  # NON-conforming: admits on request arrival time
    if cons["decision"] is not None:
      return _err(
        409,
        "decision_conflict",
        "unrecoverable",
        "A terminal decision is already recorded.",
        {"decision_id": cons["decision"]["decision_id"]},
      )
    if wanted < cur["revision"]:
      return _err(
        409,
        "proposal_superseded",
        "requires_buyer_review",
        "Revision superseded; review the current revision.",
        {"current_revision": cur["revision"]},
      )
    if wanted > cur["revision"]:
      return _err(404, "not_found", "unrecoverable", "Not found.")
    if status == "withdrawn":
      return _err(
        409, "proposal_withdrawn", "unrecoverable", "Proposal withdrawn."
      )
    if status == "expired":
      return _err(409, "proposal_expired", "unrecoverable", "Past deadline.")
    digest = request.get("proposal_digest")
    if digest is not None and digest != cur["proposal_digest"]:
      return _err(
        422, "proposal_digest_mismatch", "unrecoverable", "Digest mismatch."
      )
    if (
      cur["baseline_reference"]["order_version"]
      != (self.orders[order_id]["version"])
    ):
      return _err(
        409,
        "proposal_stale",
        "requires_buyer_review",
        "Order changed since the proposal was issued.",
        {"current_revision": cur["revision"]},
      )
    delta = cur["proposed_terms"].get("price_delta_amount", 0)
    if (
      actor.allowed_consultations is not None
      and cid not in actor.allowed_consultations
    ):
      return _err(
        403,
        "decision_not_authorized",
        "requires_buyer_review",
        "Delegation does not cover this consultation.",
      )
    if actor.max_delta is not None and delta > actor.max_delta:
      return _err(
        403,
        "decision_not_authorized",
        "requires_buyer_review",
        "Delegation constraints do not cover this proposal.",
      )
    return self._commit(actor, cons, cur, request, scope_key, body_hash)

  def _commit(self, actor, cons, cur, request, scope_key, body_hash):
    approve = request["decision"] == "approve"
    receipt = {
      "decision_id": self._next("dec"),
      "consultation_id": cur["consultation_id"],
      "order_id": cur["order_id"],
      "proposal_revision": cur["revision"],
      "proposal_digest": cur["proposal_digest"],
      "decision": request["decision"],
      "status": "recorded",
      "recorded_at": _z(self.now),
      "decided_by": {"type": "buyer", "id": actor.buyer},
      "application_status": "pending" if approve else "not_applicable",
      "_outcome": "approved" if approve else "declined",
    }
    if approve:
      receipt["authorized_scope"] = copy.deepcopy(cur["scope"])
    cons["decision"] = receipt
    self.decisions[receipt["decision_id"]] = receipt
    body = {"ucp": _ucp_ok()}
    body.update(self._receipt_public(receipt))
    _emit("decide", "decision_receipt", copy.deepcopy(body))
    response = (201, body)
    self.idem[scope_key] = {
      "body_hash": body_hash,
      "response": response,
      "decision_id": receipt["decision_id"],
    }
    return response

  # -- application (Business-internal, observed by reads) ------

  def apply(self, decision_id, payment_authorized=False):
    """Apply an approved decision to the Order, re-checking applicability."""
    receipt = self.decisions[decision_id]
    if receipt["decision"] != "approve":
      raise ValueError("only approvals enter the application lifecycle")
    cons = self.cons[(receipt["order_id"], receipt["consultation_id"])]
    rev = cons["revs"][receipt["proposal_revision"] - 1]
    order = self.orders[receipt["order_id"]]

    def fail(code, content):
      receipt["application_status"] = "failed"
      receipt["application"] = {"failure": {"code": code, "content": content}}
      return receipt

    if rev["baseline_reference"]["order_version"] != order["version"]:
      return fail("order_changed", "Order changed after approval.")
    app_deadline = rev.get("application_deadline")
    if app_deadline and self.now > _t(app_deadline):
      return fail("application_deadline_passed", "Past application deadline.")
    effective = rev.get("effective_from")
    exact = rev.get("effective_time_rule") == "exact"
    if exact and self.now > _t(effective):
      return fail(
        "effective_time_unsatisfiable", "Exact effective instant has passed."
      )
    delta = rev["proposed_terms"].get("price_delta_amount", 0)
    if delta > 0 and not payment_authorized:
      return fail(
        "payment_authority_missing",
        "Approval does not authorize a new charge.",
      )
    boundary = max(_t(effective), self.now) if effective else None
    new_version = f"v{int(order['version'][1:]) + 1}"
    application = {
      "applied_at": _z(self.now),
      "resulting_order_version": new_version,
    }
    record = {
      "consultation_id": rev["consultation_id"],
      "decision_id": decision_id,
      "proposal_revision": rev["revision"],
      "proposal_digest": rev["proposal_digest"],
      "change_type": rev["change_type"],
      "baseline_reference": copy.deepcopy(rev["baseline_reference"]),
      "applied_at": application["applied_at"],
      "resulting_order_version": new_version,
    }
    if boundary:
      application["actual_effective_from"] = _z(boundary)
      record["actual_effective_from"] = _z(boundary)
    if rev["change_type"] == "usage_tariff_change":
      rental = self.rentals[rev["scope"]["rental_id"]]
      terms = rev["proposed_terms"]
      rental["schedule"][-1]["valid_until"] = _z(boundary)
      rental["schedule"].append(
        {
          "valid_from": _z(boundary),
          "rate_amount": terms["proposed_rate_amount"],
          "billing_unit": terms["billing_unit"],
          "decision_id": decision_id,
        }
      )
      record["applied_terms"] = {
        "rental_id": rev["scope"]["rental_id"],
        "rate_schedule": copy.deepcopy(rental["schedule"]),
      }
      application["applied_terms"] = copy.deepcopy(record["applied_terms"])
    order["version"] = new_version
    order["applications"].append(record)
    receipt["application_status"] = "applied"
    receipt["application"] = application
    return receipt

  def accrue(self, rental_id, at, units):
    """Record metered usage at an instant (accrued, not necessarily billed)."""
    self.rentals[rental_id]["usage"].append((at, units))

  def price_usage(self, rental_id):
    """Price every accrued usage record on the authoritative schedule."""
    out = []
    for at, units in self.rentals[rental_id]["usage"]:
      rate = None
      for entry in self.rentals[rental_id]["schedule"]:
        until = entry.get("valid_until")
        if _t(entry["valid_from"]) <= _t(at) and (
          until is None or _t(at) < _t(until)
        ):
          rate = entry["rate_amount"]
      out.append((at, units, rate))
    return out

  def get_order(self, actor, order_id):
    """Order read with the negotiated `consultation_applications`."""
    order = self.orders.get(order_id)
    if order is None or order["buyer"] != actor.buyer:
      return _err(404, "not_found", "unrecoverable", "Not found.")
    body = json.loads(
      (REPO / "scripts/scaffolds/shopping_order_response.json").read_text()
    )
    body["ucp"] = {
      "version": V,
      "capabilities": {
        "dev.ucp.shopping.order": [{"version": V}],
        CAP: [{"version": V}],
      },
    }
    body["id"] = order_id
    if not actor.negotiated:
      body["ucp"]["capabilities"].pop(CAP)
      return 200, body
    body["consultation_applications"] = copy.deepcopy(order["applications"])
    _emit("get_order", "dev.ucp.shopping.order", body)
    return 200, body


# -----------------------------------------------------------
# Scenario helpers
# -----------------------------------------------------------

BUYER = "buyer_1"
KEY_A = "b3b8f086-8f4e-41ab-bdc5-3f9156f05f79"
KEY_B = "0b6c1f0e-5c29-4e2a-9a6e-77e0a1d3c8e4"
KEY_C = "e7d2a1c4-93f0-4b68-8a35-2d1f6b9e0c57"
APPROVE_3 = b'{"proposal_revision":3,"decision":"approve"}'
DECLINE_3 = b'{"proposal_revision":3,"decision":"decline"}'


def _platform(name="platform_a", scopes=(SCOPE_READ, SCOPE_DECIDE), **kw):
  return Actor(name, BUYER, scopes, **kw)


def _tariff(**over):
  fields = {
    "change_type": "usage_tariff_change",
    "scope": {
      "rental_id": "equipment_1",
      "usage_from": "2026-10-21T00:00:00Z",
    },
    "proposed_terms": {
      "current_rate_amount": 1000,
      "proposed_rate_amount": 1400,
      "billing_unit": "hour",
    },
    "decision_deadline": "2026-10-20T18:00:00Z",
    "effective_from": "2026-10-21T00:00:00Z",
    "reason": "Updated rental tariff for future usage.",
  }
  fields.update(over)
  return fields


def _substitute(**over):
  fields = {
    "change_type": "item_substitution",
    "scope": {"line_item_id": "li_1", "quantity": 1},
    "proposed_terms": {
      "replacement_item": {"id": "sku_9", "title": "Alt Item", "price": 1250},
      "price_delta_amount": 250,
    },
    "decision_deadline": "2026-10-20T18:00:00Z",
  }
  fields.update(over)
  return fields


def _rental_world(revisions=3):
  """Order + rental with `revisions` undecided tariff revisions issued."""
  biz = ReferenceBusiness()
  biz.add_order("ord_rental_1", BUYER)
  biz.add_rental("equipment_1", "ord_rental_1", "2026-10-01T00:00:00Z", 1000)
  biz.issue("ord_rental_1", "consult_17", **_tariff())
  for _ in range(revisions - 1):
    biz.revise("ord_rental_1", "consult_17", **_tariff())
  return biz


def _decide(biz, actor, key, raw, cid="consult_17", order="ord_rental_1"):
  return biz.decide(actor, order, cid, key, raw)


# -----------------------------------------------------------
# Vectors
# -----------------------------------------------------------


def cv01_digest_and_immutable_revisions():
  """CV-01 Revisions are immutable and addressable; digest binds terms."""
  biz = _rental_world(3)
  actor = _platform()
  _, rev2 = biz.get_revision(actor, "ord_rental_1", "consult_17", 2)
  _, rev3 = biz.get_revision(actor, "ord_rental_1", "consult_17", 3)
  _check("CV-01 rev2 superseded", rev2["status"] == "superseded")
  _check("CV-01 rev3 open", rev3["status"] == "open")
  _check(
    "CV-01 digest recomputes from terms",
    proposal_digest(rev3) == rev3["proposal_digest"],
  )
  changed = dict(rev3, proposed_terms=dict(rev3["proposed_terms"]))
  changed["proposed_terms"]["proposed_rate_amount"] = 1500
  _check(
    "CV-01 changed terms change digest",
    proposal_digest(changed) != rev3["proposal_digest"],
  )
  before = rev2["proposal_digest"]
  biz.advance("2026-10-20T17:00:00Z")
  _, again = biz.get_revision(actor, "ord_rental_1", "consult_17", 2)
  _check("CV-01 historical terms stable", again["proposal_digest"] == before)
  _, cons = biz.get_consultation(actor, "ord_rental_1", "consult_17")
  _check(
    "CV-01 index lists every revision",
    [r["revision"] for r in cons["revisions"]] == [1, 2, 3],
  )


def cv02_discovery_without_webhook():
  """CV-02 List finds open consultations with no notification delivered."""
  biz = _rental_world(3)
  actor = _platform()
  _, listing = biz.list_consultations(actor, "ord_rental_1")
  _check(
    "CV-02 open consultation discoverable by list alone",
    [c["consultation_id"] for c in listing["consultations"]] == ["consult_17"],
  )
  other = _platform("platform_b", scopes=())
  status, _ = biz.list_consultations(other, "ord_rental_1")
  _check("CV-02 list requires read scope", status == 403)
  stranger = Actor("platform_a", "buyer_2", (SCOPE_READ,))
  status, _ = biz.list_consultations(stranger, "ord_rental_1")
  _check("CV-02 cross-buyer list is not_found", status == 404)
  biz.advance("2026-10-20T18:00:01Z")
  _, listing = biz.list_consultations(actor, "ord_rental_1")
  _check("CV-02 expired is not listed as open", listing["consultations"] == [])
  _, listing = biz.list_consultations(
    actor, "ord_rental_1", statuses=("open", "expired")
  )
  _check(
    "CV-02 status filter selects expired", len(listing["consultations"]) == 1
  )


def cv03_authorized_approve_and_decline_receipts():
  """CV-03 Approve carries scope+pending; decline carries neither."""
  biz = _rental_world(3)
  actor = _platform()
  status, receipt = _decide(biz, actor, KEY_A, APPROVE_3)
  _check("CV-03 approve is 201 recorded", status == 201)
  _check("CV-03 approve pending", receipt["application_status"] == "pending")
  _check(
    "CV-03 approve scope copied from revision",
    receipt["authorized_scope"]
    == biz.cons[("ord_rental_1", "consult_17")]["revs"][2]["scope"],
  )
  biz2 = _rental_world(3)
  status, receipt = _decide(biz2, _platform(), KEY_A, DECLINE_3)
  _check("CV-03 decline recorded", status == 201)
  _check(
    "CV-03 decline has no authorized_scope", "authorized_scope" not in receipt
  )
  _check(
    "CV-03 decline is not_applicable",
    receipt["application_status"] == "not_applicable",
  )
  try:
    biz2.apply(receipt["decision_id"])
    entered = True
  except ValueError:
    entered = False
  _check("CV-03 decline cannot enter application lifecycle", not entered)


def cv04_authority_boundaries():
  """CV-04 Read access, wrong scope, cross-buyer and cross-Order refused."""
  biz = _rental_world(3)
  reader = _platform(scopes=(SCOPE_READ,))
  status, body = _decide(biz, reader, KEY_A, APPROVE_3)
  _check("CV-04 read scope cannot decide", status == 403)
  _check(
    "CV-04 insufficient_scope code",
    body["messages"][0]["code"] == "insufficient_scope",
  )
  manager = _platform(scopes=("dev.ucp.shopping.order:manage",))
  status, _ = _decide(biz, manager, KEY_A, APPROVE_3)
  _check("CV-04 order:manage never suffices", status in (403, 404))
  stranger = Actor("platform_a", "buyer_2", (SCOPE_READ, SCOPE_DECIDE))
  status, _ = _decide(biz, stranger, KEY_A, APPROVE_3)
  _check("CV-04 cross-buyer decision is not_found", status == 404)
  biz.add_order("ord_other", BUYER)
  status, _ = biz.decide(
    _platform(), "ord_other", "consult_17", KEY_A, APPROVE_3
  )
  _check("CV-04 cross-Order decision is not_found", status == 404)
  capped = _platform(max_delta=0)
  biz3 = ReferenceBusiness()
  biz3.add_order("ord_s", BUYER)
  biz3.issue("ord_s", "consult_s", **_substitute())
  status, body = biz3.decide(
    capped, "ord_s", "consult_s", KEY_A, APPROVE_3.replace(b"3", b"1")
  )
  _check("CV-04 delegation cap enforced", status == 403)
  _check(
    "CV-04 decision_not_authorized code",
    body["messages"][0]["code"] == "decision_not_authorized",
  )
  _check(
    "CV-04 nothing recorded on refusal",
    biz3.cons[("ord_s", "consult_s")]["decision"] is None,
  )
  _check(
    "CV-04 silence never approves",
    biz.get_consultation(_platform(), "ord_rental_1", "consult_17")[1]["status"]
    == "open",
  )


def cv05_revision_binding():
  """CV-05 Approval of revision 3 never authorizes revision 4."""
  biz = _rental_world(3)
  biz.revise(
    "ord_rental_1",
    "consult_17",
    **_tariff(
      proposed_terms={
        "current_rate_amount": 1000,
        "proposed_rate_amount": 1600,
        "billing_unit": "hour",
      }
    ),
  )
  status, body = _decide(biz, _platform(), KEY_A, APPROVE_3)
  _check("CV-05 stale revision refused", status == 409)
  _check(
    "CV-05 proposal_superseded with current_revision",
    body["messages"][0]["code"] == "proposal_superseded"
    and body["messages"][0]["data"]["current_revision"] == 4,
  )
  _check(
    "CV-05 nothing recorded",
    biz.cons[("ord_rental_1", "consult_17")]["decision"] is None,
  )
  digest3 = biz.cons[("ord_rental_1", "consult_17")]["revs"][2][
    "proposal_digest"
  ]
  raw = json.dumps(
    {"proposal_revision": 4, "decision": "approve", "proposal_digest": digest3}
  ).encode()
  status, body = _decide(biz, _platform(), KEY_B, raw)
  _check("CV-05 digest of another revision rejected", status == 422)
  _check(
    "CV-05 proposal_digest_mismatch",
    body["messages"][0]["code"] == "proposal_digest_mismatch",
  )
  raw = (
    b'{"proposal_revision":4,"decision":"approve","scope":{"rental_id":"x"}}'
  )
  status, body = _decide(biz, _platform(), KEY_C, raw)
  _check("CV-05 request scope rejected", status == 422)
  _check(
    "CV-05 decision_scope_not_accepted",
    body["messages"][0]["code"] == "decision_scope_not_accepted",
  )
  biz2 = _rental_world(3)
  _decide(biz2, _platform(), KEY_A, APPROVE_3)
  try:
    biz2.revise("ord_rental_1", "consult_17", **_tariff())
    superseded_decided = True
  except ValueError:
    superseded_decided = False
  _check("CV-05 decided revision cannot be superseded", not superseded_decided)


def cv06_expiry_withdrawal_supersession_races():
  """CV-06 Admission order decides every race; recorded approvals stand."""
  biz = _rental_world(3)
  biz.advance("2026-10-20T18:00:00Z")  # exactly at the deadline: inclusive
  status, _ = _decide(biz, _platform(), KEY_A, APPROVE_3)
  _check("CV-06 admitted at deadline instant", status == 201)

  biz = _rental_world(3)
  biz.advance("2026-10-20T18:00:01Z")
  status, body = _decide(biz, _platform(), KEY_A, APPROVE_3)
  _check("CV-06 late request refused as expired", status == 409)
  _check(
    "CV-06 proposal_expired",
    body["messages"][0]["code"] == "proposal_expired",
  )

  # Withdrawal commits first: approval refused.
  biz = _rental_world(3)
  biz.withdraw("ord_rental_1", "consult_17")
  status, body = _decide(biz, _platform(), KEY_A, APPROVE_3)
  _check(
    "CV-06 withdrawal-first blocks approval",
    status == 409 and body["messages"][0]["code"] == "proposal_withdrawn",
  )

  # Approval commits first: later withdrawal cannot erase it.
  biz = _rental_world(3)
  _decide(biz, _platform(), KEY_A, APPROVE_3)
  try:
    biz.withdraw("ord_rental_1", "consult_17")
    erased = True
  except ValueError:
    erased = False
  _check("CV-06 approval-first survives withdrawal", not erased)
  _, cons = biz.get_consultation(_platform(), "ord_rental_1", "consult_17")
  _check("CV-06 status stays approved", cons["status"] == "approved")

  # Supersession commits first.
  biz = _rental_world(3)
  biz.revise("ord_rental_1", "consult_17", **_tariff())
  status, body = _decide(biz, _platform(), KEY_A, APPROVE_3)
  _check(
    "CV-06 supersession-first blocks stale approval",
    status == 409 and body["messages"][0]["code"] == "proposal_superseded",
  )

  # Expiry is evaluated at admission, not when the packet was generated.
  biz = _rental_world(3)
  generated_at = biz.now
  biz.advance("2026-10-20T18:00:05Z")
  _check(
    "CV-06 packet generated before deadline",
    generated_at < _t("2026-10-20T18:00:00Z"),
  )
  status, _ = _decide(biz, _platform(), KEY_A, APPROVE_3)
  _check("CV-06 delayed packet still expired", status == 409)


def cv07_approve_decline_race():
  """CV-07 Exactly one terminal decision, in either admission order."""
  for order in (("approve", "decline"), ("decline", "approve")):
    biz = _rental_world(3)
    web = _platform("platform_web")
    app = _platform("platform_app")
    raws = {"approve": APPROVE_3, "decline": DECLINE_3}
    first_actor, second_actor = web, app
    s1, b1 = _decide(biz, first_actor, KEY_A, raws[order[0]])
    s2, b2 = _decide(biz, second_actor, KEY_B, raws[order[1]])
    _check(f"CV-07 {order[0]}-first wins", s1 == 201)
    _check(f"CV-07 {order[0]}-first loser conflict", s2 == 409)
    msg = b2["messages"][0]
    _check(
      f"CV-07 {order[0]}-first loser points to receipt",
      msg["code"] == "decision_conflict"
      and msg["data"]["decision_id"] == b1["decision_id"],
    )
    status, receipt = biz.get_decision(
      second_actor, "ord_rental_1", "consult_17", msg["data"]["decision_id"]
    )
    _check(
      f"CV-07 {order[0]}-first loser can read authoritative receipt",
      status == 200 and receipt["decision"] == order[0],
    )
    _check(
      f"CV-07 {order[0]}-first one terminal decision",
      len(biz.decisions) == 1,
    )
  biz = _rental_world(3)
  _decide(biz, _platform("platform_web"), KEY_A, APPROVE_3)
  status, body = _decide(biz, _platform("platform_app"), KEY_B, APPROVE_3)
  _check(
    "CV-07 simultaneous approvals produce one decision",
    status == 409 and len(biz.decisions) == 1,
  )


def cv08_idempotent_replay():
  """CV-08 Same key+bytes replays; changed bytes conflict; fail closed."""
  biz = _rental_world(3)
  actor = _platform()
  first = _decide(biz, actor, KEY_A, APPROVE_3)
  again = _decide(biz, actor, KEY_A, APPROVE_3)
  _check("CV-08 replay returns the original response", first == again)
  _check("CV-08 replay adds no second decision", len(biz.decisions) == 1)
  reformatted = b'{ "proposal_revision": 3, "decision": "approve" }'
  status, body = _decide(biz, actor, KEY_A, reformatted)
  _check(
    "CV-08 same JSON, different raw bytes conflicts (raw-body SHA-256)",
    status == 409 and body["messages"][0]["code"] == "idempotency_key_conflict",
  )
  status, body = _decide(biz, actor, KEY_A, DECLINE_3)
  _check(
    "CV-08 changed decision under reused key conflicts",
    status == 409 and body["messages"][0]["code"] == "idempotency_key_conflict",
  )
  _check(
    "CV-08 original decision unchanged",
    next(iter(biz.decisions.values()))["decision"] == "approve",
  )
  # Keys are scoped to platform identity.
  other = _platform("platform_b")
  status, body = _decide(biz, other, KEY_A, APPROVE_3)
  _check(
    "CV-08 same key under another platform is a distinct scope",
    status == 409 and body["messages"][0]["code"] == "decision_conflict",
  )
  # Replay store failure fails closed.
  biz = _rental_world(3)
  biz.replay_store_up = False
  status, body = _decide(biz, _platform(), KEY_A, APPROVE_3)
  _check(
    "CV-08 replay-store failure fails closed with 503",
    status == 503 and body["messages"][0]["code"] == "replay_store_unavailable",
  )
  _check("CV-08 nothing recorded when failing closed", not biz.decisions)
  biz.replay_store_up = True
  status, _ = _decide(biz, _platform(), KEY_A, APPROVE_3)
  _check("CV-08 same-key retry succeeds after recovery", status == 201)


def cv09_lost_response_recovery():
  """CV-09 Lookup distinguishes recorded / in-flight / provisional / final."""
  biz = _rental_world(3)
  actor = _platform()
  status, original = _decide(biz, actor, KEY_A, APPROVE_3)  # response "lost"
  _, lookup = biz.lookup_by_key(actor, "ord_rental_1", "consult_17", KEY_A)
  _check(
    "CV-09 lookup by original key finds the committed decision",
    lookup["outcome"] == "recorded"
    and lookup["decision"]["decision_id"] == original["decision_id"],
  )

  biz = _rental_world(3)
  actor = _platform()
  biz.begin_decide(actor, "ord_rental_1", "consult_17", KEY_A, APPROVE_3)
  _, lookup = biz.lookup_by_key(actor, "ord_rental_1", "consult_17", KEY_A)
  _check("CV-09 in-flight is not a failure", lookup["outcome"] == "in_flight")
  _check("CV-09 in-flight never final", lookup.get("final") is not True)

  biz = _rental_world(3)
  actor = _platform()
  _, lookup = biz.lookup_by_key(actor, "ord_rental_1", "consult_17", KEY_B)
  _check(
    "CV-09 absent while open is provisional, not no-commit",
    lookup["outcome"] == "not_recorded" and lookup["final"] is False,
  )
  # Safe same-key retry resolves it deterministically.
  status, _ = _decide(biz, actor, KEY_B, APPROVE_3)
  _check("CV-09 same-key retry is safe and commits once", status == 201)
  status2, _ = _decide(biz, actor, KEY_B, APPROVE_3)
  _check(
    "CV-09 second retry replays", status2 == 201 and len(biz.decisions) == 1
  )

  biz = _rental_world(3)
  actor = _platform()
  biz.advance("2026-10-20T18:00:01Z")
  _, lookup = biz.lookup_by_key(actor, "ord_rental_1", "consult_17", KEY_B)
  _check(
    "CV-09 final no-commit only once the consultation is closed",
    lookup["final"] is True and lookup["final_reason"] == "consultation_closed",
  )
  status, _ = _decide(biz, actor, KEY_B, APPROVE_3)
  _check("CV-09 late retry cannot commit after final", status == 409)

  # Another platform's key reveals nothing; another buyer is not_found.
  biz = _rental_world(3)
  _decide(biz, _platform("platform_a"), KEY_A, APPROVE_3)
  _, lookup = biz.lookup_by_key(
    _platform("platform_b"), "ord_rental_1", "consult_17", KEY_A
  )
  _check(
    "CV-09 key lookup is scoped to the authenticated Platform",
    "decision" not in lookup,
  )
  stranger = Actor("platform_a", "buyer_2", (SCOPE_READ,))
  status, _ = biz.lookup_by_key(stranger, "ord_rental_1", "consult_17", KEY_A)
  _check("CV-09 cross-buyer key lookup is not_found", status == 404)
  # Never swap approve for decline after an empty lookup.
  status, body = _decide(biz, _platform("platform_a"), KEY_C, DECLINE_3)
  _check(
    "CV-09 blind new-key decline loses to the recorded decision",
    status == 409 and body["messages"][0]["code"] == "decision_conflict",
  )


def cv10_application_lifecycle():
  """CV-10 Recorded approval is not application; failures stay failures."""
  biz = _rental_world(3)
  actor = _platform()
  _, receipt = _decide(biz, actor, KEY_A, APPROVE_3)
  _, order = biz.get_order(actor, "ord_rental_1")
  _check(
    "CV-10 approval alone leaves Order unchanged",
    order["consultation_applications"] == []
    and receipt["application_status"] == "pending",
  )
  _check("CV-10 approval created no charge", biz.charges == [])
  # Order changes between approval and application.
  biz.orders["ord_rental_1"]["version"] = "v13"
  result = biz.apply(receipt["decision_id"])
  _check(
    "CV-10 changed Order fails application",
    result["application_status"] == "failed"
    and result["application"]["failure"]["code"] == "order_changed",
  )
  _check(
    "CV-10 failed application did not substitute other terms",
    biz.get_order(actor, "ord_rental_1")[1]["consultation_applications"] == [],
  )
  _, read = biz.get_decision(
    actor, "ord_rental_1", "consult_17", receipt["decision_id"]
  )
  _check(
    "CV-10 decision read shows failed", read["application_status"] == "failed"
  )
  # Happy path.
  biz = _rental_world(3)
  _, receipt = _decide(biz, actor, KEY_A, APPROVE_3)
  biz.advance("2026-10-20T17:40:00Z")
  done = biz.apply(receipt["decision_id"])
  _check("CV-10 applied", done["application_status"] == "applied")
  _, order = biz.get_order(actor, "ord_rental_1")
  _check(
    "CV-10 Order shows baseline, digest and decision linkage",
    order["consultation_applications"][0]["decision_id"]
    == receipt["decision_id"]
    and order["consultation_applications"][0]["baseline_reference"]
    == {"order_version": "v12"},
  )
  _, read = biz.get_decision(
    actor, "ord_rental_1", "consult_17", receipt["decision_id"]
  )
  _check(
    "CV-10 receipt reflects applied", read["application_status"] == "applied"
  )


def cv11_late_application_prospective_boundary():
  """CV-11 Approval before deadline, application after effective_from."""
  biz = _rental_world(3)
  actor = _platform()
  biz.advance("2026-10-20T17:30:00Z")
  _, receipt = _decide(biz, actor, KEY_A, APPROVE_3)
  biz.advance(
    "2026-10-21T02:00:00Z"
  )  # application commits after effective_from
  biz.accrue("equipment_1", "2026-10-21T01:00:00Z", 1)  # before application
  done = biz.apply(receipt["decision_id"])
  _check(
    "CV-11 actual boundary is the later of effective_from and commit",
    done["application"]["actual_effective_from"] == "2026-10-21T02:00:00Z",
  )
  biz.accrue("equipment_1", "2026-10-21T03:00:00Z", 1)  # after application
  priced = biz.price_usage("equipment_1")
  _check(
    "CV-11 prior (unbilled) usage preserved at the old tariff",
    priced[0][2] == 1000,
  )
  _check("CV-11 later usage at the applied tariff", priced[1][2] == 1400)
  _, order = biz.get_order(actor, "ord_rental_1")
  schedule = order["consultation_applications"][0]["applied_terms"][
    "rate_schedule"
  ]
  _check(
    "CV-11 schedule closes old tariff exactly at the boundary",
    schedule[0]["valid_until"] == schedule[1]["valid_from"]
    and "decision_id" not in schedule[0]
    and schedule[1]["decision_id"] == receipt["decision_id"],
  )
  # Early application never moves the boundary earlier than effective_from.
  biz = _rental_world(3)
  _, receipt = _decide(biz, actor, KEY_A, APPROVE_3)
  done = biz.apply(receipt["decision_id"])
  _check(
    "CV-11 early application keeps effective_from",
    done["application"]["actual_effective_from"] == "2026-10-21T00:00:00Z",
  )


def cv12_exact_time_and_deadlines():
  """CV-12 Unsatisfiable exact time or application deadline: fail closed."""
  biz2 = ReferenceBusiness()
  biz2.add_order("ord_rental_1", BUYER)
  biz2.add_rental("equipment_1", "ord_rental_1", "2026-10-01T00:00:00Z", 1000)
  biz2.issue(
    "ord_rental_1",
    "consult_17",
    **_tariff(effective_time_rule="exact"),
  )
  _, receipt = biz2.decide(
    _platform(),
    "ord_rental_1",
    "consult_17",
    KEY_A,
    b'{"proposal_revision":1,"decision":"approve"}',
  )
  biz2.advance("2026-10-21T00:00:01Z")
  result = biz2.apply(receipt["decision_id"])
  _check(
    "CV-12 exact instant unsatisfiable fails application",
    result["application_status"] == "failed"
    and result["application"]["failure"]["code"]
    == "effective_time_unsatisfiable",
  )
  biz2.accrue("equipment_1", "2026-10-21T00:30:00Z", 1)
  _check(
    "CV-12 no retroactive repricing after failure",
    biz2.price_usage("equipment_1")[0][2] == 1000
    and len(biz2.rentals["equipment_1"]["schedule"]) == 1,
  )
  biz3 = ReferenceBusiness()
  biz3.add_order("ord_rental_1", BUYER)
  biz3.add_rental("equipment_1", "ord_rental_1", "2026-10-01T00:00:00Z", 1000)
  biz3.issue(
    "ord_rental_1",
    "consult_17",
    **_tariff(application_deadline="2026-10-21T00:30:00Z"),
  )
  _, receipt = biz3.decide(
    _platform(),
    "ord_rental_1",
    "consult_17",
    KEY_A,
    b'{"proposal_revision":1,"decision":"approve"}',
  )
  biz3.advance("2026-10-20T19:00:00Z")  # past decision_deadline
  _check(
    "CV-12 approval recorded before deadline stays authorized afterward",
    biz3.decisions[receipt["decision_id"]]["decision"] == "approve",
  )
  biz3.advance("2026-10-21T01:00:00Z")
  result = biz3.apply(receipt["decision_id"])
  _check(
    "CV-12 late application still honors application_deadline",
    result["application"]["failure"]["code"] == "application_deadline_passed",
  )


def cv13_payment_authority_is_separate():
  """CV-13 Commercial approval never implies a charge."""
  biz = ReferenceBusiness()
  biz.add_order("ord_s", BUYER)
  biz.issue("ord_s", "consult_s", **_substitute())
  _, receipt = biz.decide(
    _platform(),
    "ord_s",
    "consult_s",
    KEY_A,
    b'{"proposal_revision":1,"decision":"approve"}',
  )
  result = biz.apply(receipt["decision_id"], payment_authorized=False)
  _check(
    "CV-13 additional obligation without payment authority fails",
    result["application"]["failure"]["code"] == "payment_authority_missing",
  )
  _check("CV-13 no charge executed", biz.charges == [])
  biz = ReferenceBusiness()
  biz.add_order("ord_s", BUYER)
  biz.issue("ord_s", "consult_s", **_substitute())
  _, receipt = biz.decide(
    _platform(),
    "ord_s",
    "consult_s",
    KEY_A,
    b'{"proposal_revision":1,"decision":"approve"}',
  )
  result = biz.apply(receipt["decision_id"], payment_authorized=True)
  _check(
    "CV-13 applies when payment authority exists separately",
    result["application_status"] == "applied",
  )
  _check(
    "CV-13 receipt carries no adjustment inferred from approval",
    "adjustment_ids" not in result["application"],
  )


def cv14_coexistence():
  """CV-14 Base Order untouched; no dependency on EP #943."""
  base = json.loads(
    (REPO / "scripts/scaffolds/shopping_order_response.json").read_text()
  )
  _check(
    "CV-14 base Order has no consultation members",
    "consultation_applications" not in base,
  )
  text = SCHEMA.read_text()
  _check(
    "CV-14 schema does not reference EP #943 artifacts",
    "order_modification" not in text and "cancellation" not in text,
  )
  base_order = json.loads(
    (REPO / "source/schemas/shopping/order.json").read_text()
  )
  _check(
    "CV-14 order.json unchanged by this extension",
    "consultation" not in json.dumps(base_order),
  )


def cv15_unknown_values_fail_closed():
  """CV-15 Unknown lifecycle values grant no authority."""

  def actionable(status):
    return status == "open"

  _check(
    "CV-15 unknown revision status not actionable", not actionable("on_hold")
  )

  def authority(decision):
    return decision == "approve"

  _check("CV-15 unknown decision grants no authority", not authority("maybe"))

  def application(status):
    known = {"pending", "applied", "failed", "indeterminate", "not_applicable"}
    return status if status in known else "indeterminate"

  _check(
    "CV-15 unknown application_status read as indeterminate",
    application("deferred") == "indeterminate",
  )


def cv16_negotiation_and_scope():
  """CV-16 Absent capability changes nothing; scope is Business-initiated."""
  biz = _rental_world(3)
  platform = _platform(negotiated=False)
  for name, call in (
    ("list", lambda: biz.list_consultations(platform, "ord_rental_1")),
    (
      "read",
      lambda: biz.get_consultation(platform, "ord_rental_1", "consult_17"),
    ),
    ("decide", lambda: _decide(biz, platform, KEY_A, APPROVE_3)),
  ):
    status, body = call()
    _check(
      f"CV-16 {name} without negotiation is capabilities_incompatible",
      status == 200
      and body["messages"][0]["code"] == "capabilities_incompatible",
    )
  _check("CV-16 nothing recorded without negotiation", not biz.decisions)
  _, order = biz.get_order(platform, "ord_rental_1")
  _check(
    "CV-16 un-negotiated Order read is the base Order",
    "consultation_applications" not in order
    and CAP not in order["ucp"]["capabilities"],
  )
  _check(
    "CV-16 model offers no Platform-side create operation",
    not any(
      hasattr(biz, n) for n in ("create_consultation", "create", "propose")
    ),
  )


def _base_rev3():
  """Return the documented revision 3 proposal (for digest vectors)."""
  return {
    "consultation_id": "consult_17",
    "order_id": "ord_rental_1",
    "revision": 3,
    "change_type": "usage_tariff_change",
    "scope": {
      "rental_id": "equipment_1",
      "usage_from": "2026-10-21T00:00:00Z",
    },
    "proposed_terms": {
      "current_rate_amount": 1000,
      "proposed_rate_amount": 1400,
      "billing_unit": "hour",
    },
    "baseline_reference": {"order_version": "v12"},
    "decision_deadline": "2026-10-20T18:00:00Z",
    "effective_from": "2026-10-21T00:00:00Z",
  }


def digest_cases():
  """(label, mutated proposal) pairs whose digest MUST differ from base."""
  cases = []

  def mut(label, fn):
    proposal = copy.deepcopy(_base_rev3())
    fn(proposal)
    cases.append((label, proposal))

  mut(
    "`proposed_rate_amount` 1400 to 1500",
    lambda p: p["proposed_terms"].__setitem__("proposed_rate_amount", 1500),
  )
  mut(
    "`scope.usage_from` earlier (broader scope)",
    lambda p: p["scope"].__setitem__("usage_from", "2026-10-20T00:00:00Z"),
  )
  mut(
    "`scope.rental_id` equipment_2",
    lambda p: p["scope"].__setitem__("rental_id", "equipment_2"),
  )
  mut(
    "`effective_time_rule` set to `exact`",
    lambda p: p.__setitem__("effective_time_rule", "exact"),
  )
  mut(
    "`effective_from` one hour later",
    lambda p: p.__setitem__("effective_from", "2026-10-21T01:00:00Z"),
  )
  mut(
    "`baseline_reference.order_version` v13",
    lambda p: p["baseline_reference"].__setitem__("order_version", "v13"),
  )
  mut(
    "`decision_deadline` one hour later",
    lambda p: p.__setitem__("decision_deadline", "2026-10-20T19:00:00Z"),
  )
  mut(
    "`application_deadline` added",
    lambda p: p.__setitem__("application_deadline", "2026-10-22T00:00:00Z"),
  )
  mut("`revision` 4", lambda p: p.__setitem__("revision", 4))
  mut(
    "`order_id` ord_rental_2",
    lambda p: p.__setitem__("order_id", "ord_rental_2"),
  )
  mut(
    "`consultation_id` consult_18",
    lambda p: p.__setitem__("consultation_id", "consult_18"),
  )
  return cases


def _raises(fn):
  try:
    fn()
  except (ValueError, TypeError):
    return True
  return False


def cv20_digest_interoperability():
  """CV-20 Canonical digest binds every approval-relevant member."""
  # RFC 8785 section 3.2.3 property-sorting sample.
  sample = {
    "€": "Euro Sign",
    "\r": "Carriage Return",
    "דּ": "Hebrew Letter Dalet With Dagesh",
    "1": "One",
    "\U0001f600": "Emoji: Grinning Face",
    "\u0080": "Control",
    "ö": "Latin Small Letter O With Diaeresis",
  }
  order = ["\r", "1", "\u0080", "ö", "€", "\U0001f600", "דּ"]
  canon = jcs(sample)
  positions = [canon.index(json.dumps(k, ensure_ascii=False)) for k in order]
  _check(
    "CV-20 canonicalizer sorts keys by UTF-16 code unit (RFC 8785 sample)",
    positions == sorted(positions),
  )
  _check("CV-20 canonicalizer rejects floats", _raises(lambda: jcs({"x": 1.5})))
  base = _base_rev3()
  base_digest = proposal_digest(base)
  _check(
    "CV-20 digest has the documented shape",
    re.fullmatch(r"sha-256:[0-9a-f]{64}", base_digest) is not None,
  )
  for label, proposal in digest_cases():
    _check(
      f"CV-20 changing {label} invalidates the digest",
      proposal_digest(proposal) != base_digest,
    )
  all_digests = {proposal_digest(p) for _, p in digest_cases()}
  _check(
    "CV-20 every single-member change yields a distinct digest",
    len(all_digests) == len(digest_cases()),
  )
  for label, extra in (
    ("`reason`", {"reason": "anything"}),
    ("`status`", {"status": "superseded"}),
    ("`supersedes_revision`", {"supersedes_revision": 2}),
    ("`proposal_digest` itself", {"proposal_digest": "sha-256:" + "0" * 64}),
  ):
    _check(
      f"CV-20 {label} is excluded from the digest",
      proposal_digest({**base, **extra}) == base_digest,
    )
  raw = json.dumps(base, separators=(",", ":")).encode()
  content_digest = (
    "sha-256=:" + base64.b64encode(hashlib.sha256(raw).digest()).decode() + ":"
  )
  _check(
    "CV-20 canonical digest is not a raw-body Content-Digest",
    base_digest.split(":")[1] not in content_digest
    and not base_digest.startswith("sha-256=:"),
  )
  # Historical reads reproduce the same digest at every point in time.
  biz = _rental_world(3)
  actor = _platform()
  issued = {
    r["revision"]: r["proposal_digest"]
    for r in biz.cons[("ord_rental_1", "consult_17")]["revs"]
  }
  for when in ("2026-10-20T12:00:00Z", "2026-10-20T17:00:00Z"):
    biz.advance(when)
    for rev in (1, 2, 3):
      _, body = biz.get_revision(actor, "ord_rental_1", "consult_17", rev)
      _check(
        f"CV-20 revision {rev} read at {when} reproduces its digest",
        body["proposal_digest"] == issued[rev]
        and proposal_digest(body) == issued[rev],
      )
  _, receipt = _decide(biz, actor, KEY_A, APPROVE_3)
  biz.advance("2026-10-21T03:00:00Z")
  for rev in (1, 2, 3):
    _, body = biz.get_revision(actor, "ord_rental_1", "consult_17", rev)
    _check(
      f"CV-20 revision {rev} still reproduces its digest after the decision",
      proposal_digest(body) == issued[rev],
    )
  _check(
    "CV-20 receipt digest equals the revision digest it was admitted against",
    receipt["proposal_digest"] == issued[3],
  )
  if shutil.which("node"):
    script = (
      "const c=require('crypto');"
      "function j(v){if(v===null||typeof v!=='object')return JSON.stringify(v);"
      "if(Array.isArray(v))return '['+v.map(j).join(',')+']';"
      "return '{'+Object.keys(v).sort().map("
      "k=>JSON.stringify(k)+':'+j(v[k])).join(',')+'}'}"
      "const o=JSON.parse(process.argv[1]);"
      "console.log('sha-256:'+c.createHash('sha256')"
      ".update(j(o),'utf8').digest('hex'))"
    )
    out = subprocess.run(
      ["node", "-e", script, json.dumps(digest_input(base))],
      capture_output=True,
      text=True,
      check=False,
    ).stdout.strip()
    _check("CV-20 independent Node JCS digest agrees", out == base_digest, out)
  else:
    _SKIPPED.append("CV-20 Node cross-check (node not found)")
  if SPEC.exists():
    text = SPEC.read_text()
    _check(
      "CV-20 spec digest-vector table matches the algorithm",
      base_digest.split(":")[1] in text
      and all(
        proposal_digest(p).split(":")[1] in text for _, p in digest_cases()
      ),
    )


def cv19_buyer_authorization():
  """CV-19 Decision needs a buyer-authenticated token; fail closed."""

  def world():
    biz = _rental_world(3)
    biz.advance("2026-10-20T17:00:00Z")
    return biz

  def attempt(label, actor, expect_status, code):
    biz = world()
    status, body = _decide(biz, actor, KEY_A, APPROVE_3)
    got = body["messages"][0]["code"] if status != 201 else ""
    _check(
      f"CV-19 {label}: {expect_status} {code or 'recorded'}",
      status == expect_status and (code is None or got == code),
      f"{status} {got}",
    )
    if status != 201:
      _check(
        f"CV-19 {label}: nothing recorded and no replay record",
        not biz.decisions and not biz.idem,
      )

  attempt("valid buyer token", _platform(), 201, None)
  attempt("no credential", _platform(token="none"), 401, "identity_required")
  attempt(
    "Platform credentials only (no buyer token)",
    _platform(token="platform"),
    401,
    "identity_required",
  )
  attempt(
    "expired buyer token",
    _platform(token_exp="2026-10-20T16:59:59Z"),
    401,
    "identity_required",
  )
  attempt(
    "read-only buyer scope",
    _platform(scopes=(SCOPE_READ,)),
    403,
    "insufficient_scope",
  )
  attempt(
    "order:manage alone",
    _platform(scopes=("dev.ucp.shopping.order:manage",)),
    403,
    "insufficient_scope",
  )
  attempt(
    "order:manage plus read, still no decide",
    _platform(scopes=("dev.ucp.shopping.order:manage", SCOPE_READ)),
    403,
    "insufficient_scope",
  )
  attempt(
    "token for a different buyer (Order not visible)",
    Actor("platform_a", "buyer_2", (SCOPE_READ, SCOPE_DECIDE)),
    404,
    "not_found",
  )
  attempt(
    "delegation excludes this consultation",
    _platform(allowed_consultations={"consult_other"}),
    403,
    "decision_not_authorized",
  )
  attempt(
    "capability not negotiated",
    _platform(negotiated=False),
    200,
    "capabilities_incompatible",
  )
  biz = world()
  status, _ = biz.decide(
    _platform(allowed_consultations={"consult_17"}),
    "ord_rental_1",
    "consult_17",
    KEY_A,
    APPROVE_3,
  )
  _check("CV-19 delegation naming this consultation is accepted", status == 201)
  # Authentication precedes replay: a lapsed token cannot collect a cached
  # receipt, nor use lookup.
  biz = world()
  actor = _platform(token_exp="2026-10-20T17:30:00Z")
  s1, _ = _decide(biz, actor, KEY_A, APPROVE_3)
  biz.advance("2026-10-20T17:31:00Z")
  s2, _ = _decide(biz, actor, KEY_A, APPROVE_3)
  _check(
    "CV-19 expired token gets 401, not a replay of the cached receipt",
    s1 == 201 and s2 == 401,
  )
  status, _ = biz.lookup_by_key(actor, "ord_rental_1", "consult_17", KEY_A)
  _check("CV-19 expired token cannot use lookup either", status == 401)
  _check("CV-19 only the first decision exists", len(biz.decisions) == 1)
  status, _ = biz.list_consultations(_platform(token="none"), "ord_rental_1")
  _check("CV-19 unauthenticated list is 401", status == 401)


def check_invariants(biz):
  """Check serialization invariants over the log; return the problems."""
  problems = []
  last = None
  for entry in biz.log:
    if last is not None and entry["ts"] < last:
      problems.append("clock moved backwards")
    last = entry["ts"]
  by_cid = {cid: cons for (_, cid), cons in biz.cons.items()}
  for cid in by_cid:
    decided = [d for d in biz.decisions.values() if d["consultation_id"] == cid]
    if len(decided) > 1:
      problems.append(f"{cid}: more than one terminal decision")
  for entry in biz.log:
    if entry["kind"] != "decide" or not entry["committed"]:
      continue
    cons = by_cid[entry["cid"]]
    receipt = next(
      d for d in biz.decisions.values() if d["consultation_id"] == entry["cid"]
    )
    rev = cons["revs"][receipt["proposal_revision"] - 1]
    if entry["ts"] > _t(rev["decision_deadline"]):
      problems.append("decision committed after its deadline")
    for other in biz.log:
      if (
        other["kind"] in ("withdraw", "supersede")
        and other.get("committed")
        and other["seq"] < entry["seq"]
        and other["cid"] == entry["cid"]
        and other["revision"] == receipt["proposal_revision"]
      ):
        problems.append("decision committed after withdrawal/supersession")
  for entry in biz.log:
    if entry["kind"] != "lookup":
      continue
    if entry["final"]:
      for later in biz.log:
        if (
          later["seq"] > entry["seq"]
          and later["kind"] == "decide"
          and later["committed"]
        ):
          problems.append("commit after an authoritative non-commit result")
      if any(
        d["kind"] == "decide" and d["committed"] and d["key"] == entry["key"]
        for d in biz.log
      ):
        problems.append("final no-commit for a key that committed")
    if entry["outcome"] == "recorded" and not any(
      d["kind"] == "decide"
      and d["committed"]
      and d["key"] == entry["key"]
      and d["seq"] < entry["seq"]
      for d in biz.log
    ):
      problems.append("lookup reported a decision that never committed")
  return problems


def cv17_closure_and_serialization():
  """CV-17 Expiry/withdrawal/supersession overlap with a lost approval."""
  actor = _platform()
  skey = (actor.platform, "ord_rental_1", "consult_17", "decide", KEY_A)

  # (a) Approval sent before the deadline, response lost, processing overlaps
  # expiry. Admission is evaluated at the serialization point.
  biz = _rental_world(3)
  biz.advance("2026-10-20T17:59:59Z")
  biz.begin_decide(actor, "ord_rental_1", "consult_17", KEY_A, APPROVE_3)
  biz.advance("2026-10-20T18:00:01Z")
  _, mid = biz.lookup_by_key(actor, "ord_rental_1", "consult_17", KEY_A)
  _check(
    "CV-17a overlap lookup is unresolved (in_flight), never a final negative",
    mid["outcome"] == "in_flight" and mid.get("final") is not True,
  )
  status, body = _decide(biz, actor, KEY_A, APPROVE_3)
  _check(
    "CV-17a the delayed attempt serializes after expiry and is refused",
    status == 409 and body["messages"][0]["code"] == "proposal_expired",
  )
  _, after = biz.lookup_by_key(actor, "ord_rental_1", "consult_17", KEY_A)
  _check(
    "CV-17a only now is non-commitment final",
    after["outcome"] == "not_recorded" and after["final"] is True,
  )
  status, _ = _decide(biz, actor, KEY_A, APPROVE_3)
  _check(
    "CV-17a the same attempt cannot commit after the final result",
    status == 409 and not biz.decisions,
  )
  problems = check_invariants(biz)
  _check("CV-17a log invariants hold", not problems, str(problems))

  # (a') The same overlap on a NON-conforming Business that admits on request
  # arrival time: it reports a final non-commit to a reader, then commits the
  # earlier arrival. The checker must catch it, so the invariant is not
  # vacuous.
  bad = _rental_world(3)
  bad.unsafe_arrival_clock = True
  bad.advance("2026-10-20T17:59:59Z")
  bad.begin_decide(actor, "ord_rental_1", "consult_17", KEY_A, APPROVE_3)
  held = bad.inflight.pop(skey)
  bad.advance("2026-10-20T18:00:01Z")
  _, falsely_final = bad.lookup_by_key(
    actor, "ord_rental_1", "consult_17", KEY_A
  )
  bad.inflight[skey] = held
  _decide(bad, actor, KEY_A, APPROVE_3)
  _check(
    "CV-17a' unsafe arrival-time admission yields a detectable violation",
    falsely_final.get("final") is True and bool(check_invariants(bad)),
  )

  # (b) Withdrawal overlap.
  biz = _rental_world(3)
  biz.begin_decide(actor, "ord_rental_1", "consult_17", KEY_A, APPROVE_3)
  biz.withdraw("ord_rental_1", "consult_17")
  status, body = _decide(biz, actor, KEY_A, APPROVE_3)
  _check(
    "CV-17b withdrawal serialized first refuses the in-flight approval",
    status == 409 and body["messages"][0]["code"] == "proposal_withdrawn",
  )
  _, lookup = biz.lookup_by_key(actor, "ord_rental_1", "consult_17", KEY_A)
  _check("CV-17b non-commit is then final", lookup["final"] is True)
  _check("CV-17b invariants", not check_invariants(biz))
  biz = _rental_world(3)
  biz.begin_decide(actor, "ord_rental_1", "consult_17", KEY_A, APPROVE_3)
  _decide(biz, actor, KEY_A, APPROVE_3)
  with contextlib.suppress(ValueError):
    biz.withdraw("ord_rental_1", "consult_17")
  _, lookup = biz.lookup_by_key(actor, "ord_rental_1", "consult_17", KEY_A)
  _check(
    "CV-17b approval serialized first stays recorded; no false negative",
    lookup["outcome"] == "recorded" and not check_invariants(biz),
  )

  # (c) Supersession overlap.
  biz = _rental_world(3)
  biz.begin_decide(actor, "ord_rental_1", "consult_17", KEY_A, APPROVE_3)
  biz.revise("ord_rental_1", "consult_17", **_tariff())
  status, body = _decide(biz, actor, KEY_A, APPROVE_3)
  _check(
    "CV-17c supersession serialized first refuses the stale approval",
    status == 409 and body["messages"][0]["code"] == "proposal_superseded",
  )
  _, lookup = biz.lookup_by_key(actor, "ord_rental_1", "consult_17", KEY_A)
  _check(
    "CV-17c revision 4 is still open, so absence is NOT final",
    lookup["outcome"] == "not_recorded" and lookup["final"] is False,
  )
  _check("CV-17c invariants", not check_invariants(biz))

  # (d) A genuine negative stays negative for every later attempt.
  biz = _rental_world(3)
  biz.advance("2026-10-20T18:00:01Z")
  _, lookup = biz.lookup_by_key(actor, "ord_rental_1", "consult_17", KEY_A)
  _check("CV-17d closed consultation reports final", lookup["final"] is True)
  for key in (KEY_A, KEY_B):
    status, _ = _decide(biz, actor, key, APPROVE_3)
    _check(f"CV-17d later attempt under {key[:4]} cannot commit", status == 409)
  _check("CV-17d no decision exists", not biz.decisions)


def cv18_exhaustive_interleavings():
  """CV-18 Every ordering of racing events satisfies the invariants."""
  _RECORD[0] = False
  events = ["A", "B", "W", "S", "T", "L", "R"]
  plat_a = _platform("platform_a")
  plat_b = _platform("platform_b")
  total = 0
  bad = []
  outcomes = set()
  try:
    for order in itertools.permutations(events):
      biz = _rental_world(3)
      biz.advance("2026-10-20T17:00:00Z")
      first = None
      for ev in order:
        if ev == "A":
          first = _decide(biz, plat_a, KEY_A, APPROVE_3)
        elif ev == "R":
          again = _decide(biz, plat_a, KEY_A, APPROVE_3)
          if first and first[0] == 201 and again != first:
            bad.append((order, "retry did not replay the original"))
        elif ev == "B":
          _decide(biz, plat_b, KEY_B, DECLINE_3)
        elif ev == "W":
          with contextlib.suppress(ValueError):
            biz.withdraw("ord_rental_1", "consult_17")
        elif ev == "S":
          with contextlib.suppress(ValueError):
            biz.revise("ord_rental_1", "consult_17", **_tariff())
        elif ev == "T":
          biz.advance("2026-10-20T18:00:01Z")
        elif ev == "L":
          biz.lookup_by_key(plat_a, "ord_rental_1", "consult_17", KEY_A)
      total += 1
      problems = check_invariants(biz)
      if problems:
        bad.append((order, problems))
      outcomes.add(len(biz.decisions))
  finally:
    _RECORD[0] = True
  _check(f"CV-18 enumerated {total} orderings", total == 5040)
  _check(
    "CV-18 no ordering violates a serialization invariant",
    not bad,
    str(bad[:2]),
  )
  _check(
    "CV-18 both outcomes are reachable (decision / no decision)",
    outcomes == {0, 1},
    str(outcomes),
  )


def authority_ok(name, url):
  """Apply the Authority Binding derivation (overview)."""
  try:
    parts = urlsplit(url)
    host = parts.hostname
  except ValueError:
    return False
  if parts.scheme != "https" or parts.username or parts.password or not host:
    return False
  labels = host.lower().rstrip(".").split(".")
  if len(labels) < 2 or all(label.isdigit() for label in labels):
    return False
  prefix = ".".join(reversed(labels))
  return name == prefix or name.startswith(prefix + ".")


def negotiate(business, platform):
  """UCP capability intersection with version selection and pruning."""
  result = {}
  for name, b_entries in business.get("capabilities", {}).items():
    p_entries = platform.get("capabilities", {}).get(name)
    if not p_entries:
      continue
    common = {e["version"] for e in b_entries} & {
      e["version"] for e in p_entries
    }
    if not common:
      continue
    chosen = max(common)
    result[name] = next(e for e in b_entries if e["version"] == chosen)
  changed = True
  while changed:
    changed = False
    for name, entry in list(result.items()):
      parents = entry.get("extends")
      if parents is None:
        continue
      parents = [parents] if isinstance(parents, str) else parents
      if not any(p in result for p in parents):
        del result[name]
        changed = True
  return result


def _load_service_descriptor(schema_url):
  """Map a published service schema URL to the repository file."""
  match = re.match(r"https://ucp\.dev/[^/]+/services/(.+)$", schema_url)
  assert match, schema_url
  return json.loads((REPO / "source/services" / match.group(1)).read_text())


def _service_operations(doc, transport):
  """{operation name: description} for a REST or MCP service descriptor."""
  if transport == "rest":
    return {
      op["operationId"]: op.get("description", "")
      for item in doc["paths"].values()
      for op in item.values()
      if isinstance(op, dict) and "operationId" in op
    }
  return {m["name"]: m.get("description", "") for m in doc["methods"]}


def _available_ops(ops, negotiated):
  """Operations a session may call: gated ones need their capability."""
  available = set()
  for name, description in ops.items():
    gate = re.match(r"\[Requires the `([^`]+)` extension", description)
    if gate is None or gate.group(1) in negotiated:
      available.add(name)
  return available


def _doc_examples():
  """Return the parsed JSON examples of the specification page."""
  sys.path.insert(0, str(Path(__file__).parent))
  import validate_examples as ve  # noqa: PLC0415

  out = []
  for block in ve.extract_blocks(SPEC):
    if block.get("skip"):
      continue
    try:
      out.append(ve.parse_example(block["content"]))
    except (ValueError, KeyError, json.JSONDecodeError):
      continue
  return out


def _doc_profiles():
  """Return (business, platform) profile examples from the spec page."""
  if not SPEC.exists():
    return None, None
  business = platform = None
  for example in _doc_examples():
    if not isinstance(example, dict) or "ucp" not in example:
      continue
    ucp = example["ucp"]
    if CAP not in ucp.get("capabilities", {}) or "services" not in ucp:
      continue
    first = next(iter(ucp["services"].values()))[0]
    if "spec" in first:
      platform = example
    else:
      business = example
  return business, platform


def cv21_profile_negotiation_and_transport():
  """CV-21 Discovery, negotiation and operation resolution from a profile."""
  business, platform = _doc_profiles()
  if business is None or platform is None:
    _check("CV-21 spec page carries both example profiles", False)
    return
  b_ucp, p_ucp = business["ucp"], platform["ucp"]
  for label, ucp in (("business", b_ucp), ("platform", p_ucp)):
    for reg in ("capabilities", "services"):
      for name, entries in ucp.get(reg, {}).items():
        for entry in entries:
          if "schema" in entry:
            _check(
              f"CV-21 {label} {name} passes Authority Binding",
              authority_ok(name, entry["schema"]),
              entry["schema"],
            )
  _check(
    "CV-21 schema $id passes Authority Binding for the capability name",
    authority_ok(CAP, json.loads(SCHEMA.read_text())["$id"]),
  )
  ns = "dev.ucp.shopping.order_consultation"
  for name, url, expected in (
    (
      "com.example.shopping.order_consultation",
      "https://ucp.dev/s.json",
      False,
    ),
    (ns, "https://evil.example/s.json", False),
    ("com.examplecorp.pay", "https://example.com/s.json", False),
    (ns, "https://ucp.dev@evil.example/s.json", False),
    (ns, "https://203.0.113.10/s.json", False),
    (ns, "http://ucp.dev/s.json", False),
    (ns, "https://ucp.dev/s.json", True),
    ("com.example.pay", "https://pay.example.com/s.json", True),
  ):
    _check(
      f"CV-21 authority binding {name} <- {url} is {expected}",
      authority_ok(name, url) is expected,
    )

  negotiated = negotiate(b_ucp, p_ucp)
  _check(
    "CV-21 extension and its parent are negotiated",
    CAP in negotiated and "dev.ucp.shopping.order" in negotiated,
  )
  _check(
    "CV-21 negotiated extension names its parent",
    negotiated[CAP]["extends"] == "dev.ucp.shopping.order",
  )
  p_plain = copy.deepcopy(p_ucp)
  del p_plain["capabilities"][CAP]
  _check(
    "CV-21 platform not declaring it does not negotiate it",
    CAP not in negotiate(b_ucp, p_plain),
  )
  b_plain = copy.deepcopy(b_ucp)
  del b_plain["capabilities"][CAP]
  _check(
    "CV-21 business not declaring it does not negotiate it",
    CAP not in negotiate(b_plain, p_ucp),
  )
  p_orphan = copy.deepcopy(p_ucp)
  del p_orphan["capabilities"]["dev.ucp.shopping.order"]
  _check(
    "CV-21 extension without its negotiated parent is pruned",
    CAP not in negotiate(b_ucp, p_orphan),
  )
  p_old = copy.deepcopy(p_ucp)
  p_old["capabilities"][CAP][0]["version"] = "2020-01-01"
  _check(
    "CV-21 no mutual version excludes the extension",
    CAP not in negotiate(b_ucp, p_old),
  )

  want = {
    "list_order_consultations",
    "get_order_consultation",
    "get_order_consultation_revision",
    "decide_order_consultation",
    "lookup_order_consultation_decision",
    "get_order_consultation_decision",
  }
  plain = negotiate(b_ucp, p_plain)
  for transport in ("rest", "mcp"):
    entry = next(
      e
      for e in b_ucp["services"]["dev.ucp.shopping"]
      if e["transport"] == transport
    )
    ops = _service_operations(
      _load_service_descriptor(entry["schema"]), transport
    )
    gated = {n for n, d in ops.items() if f"`{CAP}`" in d}
    _check(
      f"CV-21 {transport}: all six operations resolve via dev.ucp.shopping",
      want <= set(ops),
    )
    _check(
      f"CV-21 {transport}: exactly the six operations are capability-gated",
      gated == want,
      str(gated ^ want),
    )
    _check(
      f"CV-21 {transport}: a negotiated session exposes them",
      want <= _available_ops(ops, negotiated),
    )
    available = _available_ops(ops, plain)
    _check(
      f"CV-21 {transport}: an un-negotiated session exposes none",
      not (want & available),
    )
    _check(
      f"CV-21 {transport}: base operations stay available un-negotiated",
      "get_order" in available,
    )
    if transport == "rest":
      doc = _load_service_descriptor(entry["schema"])
      path = next(
        pth
        for pth, item in doc["paths"].items()
        for op in item.values()
        if isinstance(op, dict)
        and op.get("operationId") == "list_order_consultations"
      )
      _check(
        "CV-21 rest: the path appends to the profile endpoint",
        path.replace("{id}", "ord_1") == "/orders/ord_1/consultations",
      )

  biz = _rental_world(3)
  unneg = _platform(negotiated=CAP in plain)
  for name, call in (
    ("list", lambda: biz.list_consultations(unneg, "ord_rental_1")),
    ("read", lambda: biz.get_consultation(unneg, "ord_rental_1", "consult_17")),
    (
      "revision",
      lambda: biz.get_revision(unneg, "ord_rental_1", "consult_17", 3),
    ),
    ("decide", lambda: _decide(biz, unneg, KEY_A, APPROVE_3)),
    (
      "lookup",
      lambda: biz.lookup_by_key(unneg, "ord_rental_1", "consult_17", KEY_A),
    ),
  ):
    _, body = call()
    _check(
      f"CV-21 un-negotiated {name} is rejected as capabilities_incompatible",
      body["messages"][0]["code"] == "capabilities_incompatible",
    )
  _check("CV-21 un-negotiated attempts recorded nothing", not biz.decisions)
  yes = _platform(negotiated=CAP in negotiated)
  _check(
    "CV-21 the negotiated session succeeds",
    _decide(biz, yes, KEY_A, APPROVE_3)[0] == 201,
  )

  il = b_ucp["capabilities"]["dev.ucp.common.identity_linking"][0]["config"]
  scopes = il["scopes"]
  _check(
    "CV-21 profile declares the dedicated decide and read scopes",
    SCOPE_DECIDE in scopes and SCOPE_READ in scopes,
  )
  token = re.compile(
    r"^[a-z](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9_-]*[a-z0-9_])?)+"
    r":[a-z][a-z0-9_]*$"
  )
  _check(
    "CV-21 scope strings match the Identity Linking scope_token pattern",
    all(token.match(sc) for sc in (SCOPE_READ, SCOPE_DECIDE)),
  )
  _check(
    "CV-21 the scope's capability prefix is negotiated (scope derivation)",
    SCOPE_DECIDE.rsplit(":", 1)[0] in negotiated,
  )
  _check(
    "CV-21 order:manage is not the decide scope",
    SCOPE_DECIDE != "dev.ucp.shopping.order:manage",
  )


def cv22_schema_composition():
  """CV-22 Negotiated composition enforces the extension; absent does not."""
  if shutil.which("ucp-schema") is None:
    _SKIPPED.append("CV-22 composition (ucp-schema binary not found)")
    return
  scaffold = json.loads(
    (REPO / "scripts/scaffolds/shopping_order_response.json").read_text()
  )
  good = {
    "consultation_id": "consult_17",
    "decision_id": "dec_52",
    "proposal_revision": 3,
    "proposal_digest": "sha-256:" + "0" * 64,
    "change_type": "item_substitution",
    "baseline_reference": {"order_version": "v1"},
    "applied_at": "2026-10-21T02:00:00Z",
    "resulting_order_version": "v2",
  }
  bad = {"consultation_id": "consult_17"}

  def payload(negotiated, applications):
    caps = {
      "dev.ucp.shopping.order": [
        {"version": V, "schema": "https://ucp.dev/schemas/shopping/order.json"}
      ]
    }
    if negotiated:
      caps[CAP] = [
        {
          "version": V,
          "schema": "https://ucp.dev/schemas/shopping/order_consultation.json",
          "extends": "dev.ucp.shopping.order",
        }
      ]
    body = copy.deepcopy(scaffold)
    body["ucp"] = {"version": V, "capabilities": caps}
    body["consultation_applications"] = applications
    return body

  def validate(body):
    with tempfile.NamedTemporaryFile(
      mode="w", suffix=".json", delete=False
    ) as handle:
      json.dump(body, handle)
      path = handle.name
    try:
      out = subprocess.run(
        [
          "ucp-schema",
          "validate",
          path,
          "--schema-local-base",
          str(REPO / "source/schemas"),
          "--schema-remote-base",
          "https://ucp.dev/schemas",
          "--response",
          "--op",
          "read",
          "--json",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
      ).stdout
    finally:
      Path(path).unlink()
    result = json.loads(out)
    errors = [
      e
      for e in result.get("errors", [])
      if "consultation_applications" in e["path"]
    ]
    return result.get("valid", False), errors

  ok, errs = validate(payload(True, [good]))
  _check(
    "CV-22 negotiated, valid application composes and validates", ok, str(errs)
  )
  ok, errs = validate(payload(True, [bad]))
  _check("CV-22 negotiated, malformed application is rejected", bool(errs))
  ok, errs = validate(payload(False, [bad]))
  _check(
    "CV-22 not negotiated: extension rules are not applied (base Order)",
    not errs,
    str(errs),
  )
  ok, _ = validate(payload(True, []))
  _check("CV-22 negotiated with no applications validates", ok)


def cv23_application_timing_and_scope():
  """CV-23 Late application never reprices accrued usage or changes scope."""
  biz = _rental_world(3)
  actor = _platform()
  biz.advance("2026-10-20T17:30:00Z")
  _, receipt = _decide(biz, actor, KEY_A, APPROVE_3)
  biz.add_rental("equipment_2", "ord_rental_1", "2026-10-01T00:00:00Z", 1000)
  biz.accrue("equipment_1", "2026-10-20T23:00:00Z", 2)  # before usage_from
  biz.accrue("equipment_1", "2026-10-21T00:30:00Z", 1)  # billed already
  biz.accrue("equipment_1", "2026-10-21T01:45:00Z", 3)  # unbilled
  biz.accrue("equipment_2", "2026-10-21T04:00:00Z", 1)  # outside scope
  biz.advance("2026-10-21T02:00:00Z")
  done = biz.apply(receipt["decision_id"])
  biz.accrue("equipment_1", "2026-10-21T02:00:00Z", 1)  # at the boundary
  biz.accrue("equipment_1", "2026-10-21T05:00:00Z", 4)
  priced = {at: rate for at, _, rate in biz.price_usage("equipment_1")}
  _check(
    "CV-23 usage before usage_from stays at the original rate",
    priced["2026-10-20T23:00:00Z"] == 1000,
  )
  _check(
    "CV-23 billed usage after effective_from stays at the original rate",
    priced["2026-10-21T00:30:00Z"] == 1000,
  )
  _check(
    "CV-23 unbilled usage before the commit stays at the original rate",
    priced["2026-10-21T01:45:00Z"] == 1000,
  )
  _check(
    "CV-23 usage at the actual boundary is at the new rate",
    priced["2026-10-21T02:00:00Z"] == 1400,
  )
  _check(
    "CV-23 later usage is at the new rate",
    priced["2026-10-21T05:00:00Z"] == 1400,
  )
  _check(
    "CV-23 another rental is outside the approved scope and unchanged",
    biz.price_usage("equipment_2")[0][2] == 1000,
  )
  _, order = biz.get_order(actor, "ord_rental_1")
  record = order["consultation_applications"][0]
  schedule = record["applied_terms"]["rate_schedule"]
  _check(
    "CV-23 the Order exposes the actual effective schedule",
    [e["rate_amount"] for e in schedule] == [1000, 1400]
    and schedule[0]["valid_until"] == "2026-10-21T02:00:00Z"
    and schedule[1]["valid_from"]
    == done["application"]["actual_effective_from"],
  )
  authorized = biz.decisions[receipt["decision_id"]]["authorized_scope"]
  rev = biz.cons[("ord_rental_1", "consult_17")]["revs"][2]
  _check(
    "CV-23 applied scope equals the authorized scope (not broadened)",
    record["applied_terms"]["rental_id"] == authorized["rental_id"],
  )
  _check(
    "CV-23 applied rate equals the approved proposed rate",
    schedule[1]["rate_amount"] == rev["proposed_terms"]["proposed_rate_amount"],
  )
  names = ReferenceBusiness.apply.__code__.co_varnames[
    : ReferenceBusiness.apply.__code__.co_argcount
  ]
  _check(
    "CV-23 apply() accepts no terms or scope, so it cannot change them",
    set(names) == {"self", "decision_id", "payment_authorized"},
    str(names),
  )
  # Materially changed terms need a new proposal; the old approval cannot
  # authorize them and the failed application does not reprice.
  biz = _rental_world(3)
  biz.advance("2026-10-20T17:30:00Z")
  _, receipt = _decide(biz, actor, KEY_A, APPROVE_3)
  old_digest = biz.cons[("ord_rental_1", "consult_17")]["revs"][2][
    "proposal_digest"
  ]
  biz.orders["ord_rental_1"]["version"] = "v13"
  failed = biz.apply(receipt["decision_id"])
  _check(
    "CV-23 a changed Order fails application and reprices nothing",
    failed["application_status"] == "failed"
    and len(biz.rentals["equipment_1"]["schedule"]) == 1,
  )
  fresh = biz.issue(
    "ord_rental_1",
    "consult_19",
    **_tariff(
      proposed_terms={
        "current_rate_amount": 1000,
        "proposed_rate_amount": 1500,
        "billing_unit": "hour",
      }
    ),
  )
  _check(
    "CV-23 new terms arrive as a new consultation with its own digest",
    fresh["proposal_digest"] != old_digest,
  )
  raw = json.dumps(
    {
      "proposal_revision": 1,
      "decision": "approve",
      "proposal_digest": old_digest,
    }
  ).encode()
  status, _ = biz.decide(actor, "ord_rental_1", "consult_19", KEY_B, raw)
  _check(
    "CV-23 the old approval's digest cannot authorize the new terms",
    status == 422,
  )
  biz = _rental_world(3)
  _, receipt = _decide(biz, actor, KEY_A, DECLINE_3)
  _check(
    "CV-23 decline carries no scope and no pending application",
    "authorized_scope" not in receipt
    and receipt["application_status"] == "not_applicable",
  )


def binding_vectors():
  """BV Shared REST/MCP service descriptors carry the operations."""
  rest = json.loads(
    (REPO / "source/services/shopping/rest.openapi.json").read_text()
  )
  rpc = json.loads(
    (REPO / "source/services/shopping/mcp.openrpc.json").read_text()
  )
  schema = json.loads(SCHEMA.read_text())
  ops = {}
  for path, item in rest["paths"].items():
    for method, op in item.items():
      if method in ("get", "post") and "consultation" in op["operationId"]:
        ops[op["operationId"]] = (method, path)
  base = "/orders/{id}/consultations"
  cid = base + "/{consultation_id}"
  expected = {
    "list_order_consultations": ("get", base),
    "get_order_consultation": ("get", cid),
    "get_order_consultation_revision": ("get", cid + "/revisions/{revision}"),
    "decide_order_consultation": ("post", cid + "/decisions"),
    "lookup_order_consultation_decision": ("get", cid + "/decisions"),
    "get_order_consultation_decision": (
      "get",
      cid + "/decisions/{decision_id}",
    ),
  }
  _check("BV REST exposes exactly the specified operations", ops == expected)
  _check(
    "BV REST only the decision POST is state-changing",
    [o for o, (m, _) in ops.items() if m == "post"]
    == ["decide_order_consultation"],
  )
  decide = rest["paths"][expected["decide_order_consultation"][1]]["post"]
  refs = [p["$ref"] for p in decide["parameters"]]
  _check(
    "BV decide requires Idempotency-Key and Content-Digest",
    "#/components/parameters/idempotency_key" in refs
    and "#/components/parameters/content_digest" in refs
    and rest["components"]["parameters"]["idempotency_key"]["required"],
  )
  lookup = rest["paths"][expected["lookup_order_consultation_decision"][1]][
    "get"
  ]
  lref = [p["$ref"] for p in lookup["parameters"]]
  header = rest["components"]["parameters"][
    "consultation_original_idempotency_key"
  ]
  _check(
    "BV lookup carries the original key in a header, never the URL",
    "#/components/parameters/consultation_original_idempotency_key" in lref
    and header["in"] == "header"
    and header["name"] == "Original-Idempotency-Key",
  )
  _check(
    "BV list defaults to open",
    rest["components"]["parameters"]["consultation_status_query"]["schema"][
      "default"
    ]
    == ["open"],
  )
  for code in ("401", "403", "404", "409", "422", "503"):
    _check(f"BV decide documents HTTP {code}", code in decide["responses"])
  gate = f"[Requires the `{CAP}` extension"
  for name, (method, path) in ops.items():
    desc = rest["paths"][path][method]["description"]
    _check(
      f"BV REST {name} states the negotiation requirement",
      desc.startswith(gate),
    )
  methods = {
    m["name"]: m for m in rpc["methods"] if "consultation" in m["name"]
  }
  _check(
    "BV MCP tools mirror REST operations 1:1", set(methods) == set(expected)
  )
  for name, method in methods.items():
    _check(
      f"BV MCP {name} states the negotiation requirement",
      method["description"].startswith(gate),
    )
  _check(
    "BV MCP decide requires idempotency-key in meta",
    "idempotency-key"
    in json.dumps(methods["decide_order_consultation"]["params"][0]),
  )
  defs = schema["$defs"]

  def refs_of(node):
    if isinstance(node, dict):
      for k, v in node.items():
        if k == "$ref" and isinstance(v, str):
          yield v
        else:
          yield from refs_of(v)
    elif isinstance(node, list):
      for item in node:
        yield from refs_of(item)

  unresolved = []
  for doc in (rest, rpc):
    for ref in set(refs_of(doc)):
      if "order_consultation.json#/$defs/" in ref:
        if ref.split("#/$defs/")[1] not in defs:
          unresolved.append(ref)
      elif ref.startswith("#/components/"):
        node = doc
        for part in ref[2:].split("/"):
          node = node.get(part) if isinstance(node, dict) else None
        if node is None:
          unresolved.append(ref)
  for ref in set(refs_of(schema)):
    if ref.startswith("#/$defs/") and ref.split("/")[-1] not in defs:
      unresolved.append(ref)
  _check("BV every $ref resolves", not unresolved, str(unresolved))
  _check(
    "BV no standalone extension descriptors remain",
    not list((REPO / "source/services/shopping").glob("order_consultation*")),
  )
  if SPEC.exists():
    spec = SPEC.read_text()
    _check(
      "BV spec names every operation and tool",
      all(f"`{t}`" in spec for t in methods),
    )
    _check(
      "BV spec documents the mandatory list path",
      "GET /orders/{id}/consultations`" in spec,
    )


# -----------------------------------------------------------
# Schema validation of every emitted payload
# -----------------------------------------------------------


def _ucp_schema(payload, def_name, expect_valid=True):
  with tempfile.NamedTemporaryFile(
    mode="w", suffix=".json", delete=False
  ) as handle:
    json.dump(payload, handle)
    path = handle.name
  try:
    result = subprocess.run(
      [
        "ucp-schema",
        "validate",
        path,
        "--schema",
        str(SCHEMA),
        "--def",
        def_name,
        "--response",
        "--op",
        "read",
        "--json",
      ],
      capture_output=True,
      text=True,
      cwd=str(REPO),
      check=False,
    )
  finally:
    Path(path).unlink()
  out = json.loads(result.stdout) if result.stdout.strip() else {}
  return out.get("valid", False), out.get("errors", [])


def schema_vectors():
  """SV-xx Emitted payloads validate; invalid shapes are rejected."""
  if shutil.which("ucp-schema") is None:
    _SKIPPED.append("schema validation (ucp-schema binary not found)")
    return
  seen = set()
  for vector, def_name, payload in _PAYLOADS:
    sig = (def_name, json.dumps(payload, sort_keys=True))
    if sig in seen:
      continue
    seen.add(sig)
    ok, errors = _ucp_schema(payload, def_name)
    _check(f"SV payload from {vector} conforms to {def_name}", ok, str(errors))

  digest = "sha-256:" + "0" * 64
  base = {
    "ucp": {"version": V},
    "decision_id": "d1",
    "consultation_id": "c1",
    "order_id": "o1",
    "proposal_revision": 1,
    "proposal_digest": digest,
    "status": "recorded",
    "recorded_at": "2026-10-20T17:35:00Z",
  }

  def case(name, extra, valid):
    ok, _ = _ucp_schema({**base, **extra}, "decision_receipt")
    _check(f"SV receipt: {name}", ok == valid)

  decline = {"decision": "decline"}
  approve = {
    "decision": "approve",
    "authorized_scope": {"rental_id": "r"},
  }
  case("decline omitting application_status is valid", decline, True)
  case(
    "decline with not_applicable is valid",
    {**decline, "application_status": "not_applicable"},
    True,
  )
  for bad in ("pending", "applied", "indeterminate", "failed"):
    case(
      f"decline with {bad} is invalid",
      {**decline, "application_status": bad},
      False,
    )
  case(
    "decline with authorized_scope is invalid",
    {**decline, "authorized_scope": {"rental_id": "r"}},
    False,
  )
  case(
    "decline with application block is invalid",
    {**decline, "application_status": "not_applicable", "application": {}},
    False,
  )
  case(
    "approve without scope is invalid",
    {"decision": "approve", "application_status": "pending"},
    False,
  )
  case("approve without application_status is invalid", approve, False)
  case(
    "approve with not_applicable is invalid",
    {**approve, "application_status": "not_applicable"},
    False,
  )
  case(
    "approve pending is valid",
    {**approve, "application_status": "pending"},
    True,
  )
  case(
    "applied without application is invalid",
    {**approve, "application_status": "applied"},
    False,
  )
  case(
    "pending with applied_at is invalid",
    {
      **approve,
      "application_status": "pending",
      "application": {"applied_at": "2026-10-21T00:00:00Z"},
    },
    False,
  )
  case(
    "failed without failure is invalid",
    {**approve, "application_status": "failed", "application": {}},
    False,
  )
  case(
    "unknown decision value validates (tolerant reader)",
    {"decision": "defer"},
    True,
  )
  # Request shape.
  ok, _ = _ucp_schema(
    {"proposal_revision": 3, "decision": "approve", "scope": {}},
    "decision_request",
  )
  _check("SV request: scope in decision request rejected", not ok)
  ok, _ = _ucp_schema(
    {"proposal_revision": 3, "decision": "maybe"}, "decision_request"
  )
  _check("SV request: unknown decision value rejected", not ok)
  # Lookup shape: a final negative must say why; in_flight is never final.
  ok, _ = _ucp_schema(
    {
      "ucp": {"version": V},
      "outcome": "not_recorded",
      "final": True,
      "checked_at": "2026-10-20T17:35:00Z",
    },
    "decision_lookup",
  )
  _check("SV lookup: final without final_reason rejected", not ok)
  ok, _ = _ucp_schema(
    {
      "ucp": {"version": V},
      "outcome": "in_flight",
      "final": True,
      "final_reason": "consultation_closed",
      "checked_at": "2026-10-20T17:35:00Z",
    },
    "decision_lookup",
  )
  _check("SV lookup: in_flight can never be final", not ok)
  ok, _ = _ucp_schema(
    {
      "ucp": {"version": V},
      "outcome": "recorded",
      "checked_at": "2026-10-20T17:35:00Z",
    },
    "decision_lookup",
  )
  _check("SV lookup: recorded requires the receipt", not ok)


# -----------------------------------------------------------
# Documentation digests
# -----------------------------------------------------------


def doc_digest_check():
  """DOC Every digest-bearing example in the spec recomputes correctly."""
  if not SPEC.exists():
    _SKIPPED.append("doc digests (specification page not present)")
    return
  sys.path.insert(0, str(Path(__file__).parent))
  import validate_examples as ve  # noqa: PLC0415

  checked = 0
  for block in ve.extract_blocks(SPEC):
    if block.get("skip"):
      continue
    try:
      example = ve.parse_example(block["content"])
    except (ValueError, KeyError, json.JSONDecodeError):
      continue
    stack = [example]
    while stack:
      node = stack.pop()
      if isinstance(node, list):
        stack.extend(node)
      elif isinstance(node, dict):
        stack.extend(node.values())
        if {"scope", "proposed_terms", "proposal_digest"} <= node.keys():
          checked += 1
          _check(
            f"DOC digest at line {block['line']} recomputes",
            proposal_digest(node) == node["proposal_digest"],
            proposal_digest(node),
          )
  _check("DOC found digest-bearing examples", checked > 0)


def main() -> int:
  """Run every vector and report."""
  vectors = [
    cv01_digest_and_immutable_revisions,
    cv02_discovery_without_webhook,
    cv03_authorized_approve_and_decline_receipts,
    cv04_authority_boundaries,
    cv05_revision_binding,
    cv06_expiry_withdrawal_supersession_races,
    cv07_approve_decline_race,
    cv08_idempotent_replay,
    cv09_lost_response_recovery,
    cv10_application_lifecycle,
    cv11_late_application_prospective_boundary,
    cv12_exact_time_and_deadlines,
    cv13_payment_authority_is_separate,
    cv14_coexistence,
    cv15_unknown_values_fail_closed,
    cv16_negotiation_and_scope,
    cv17_closure_and_serialization,
    cv18_exhaustive_interleavings,
    cv19_buyer_authorization,
    cv20_digest_interoperability,
    cv21_profile_negotiation_and_transport,
    cv22_schema_composition,
    cv23_application_timing_and_scope,
    binding_vectors,
  ]
  for vector in vectors:
    try:
      vector()
    except Exception as exc:  # noqa: BLE001 - report as a failed vector
      _check(f"{vector.__name__} raised", False, repr(exc))
  schema_vectors()
  doc_digest_check()

  failed = [(n, d) for n, ok, d in _RESULTS if not ok]
  for name, ok, detail in _RESULTS:
    suffix = f" - {detail}" if detail and not ok else ""
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{suffix}")
  for skipped in _SKIPPED:
    print(f"  SKIP  {skipped}")
  print(f"\n{len(_RESULTS) - len(failed)} passed, {len(failed)} failed")
  if _SKIPPED:
    print(f"{len(_SKIPPED)} skipped (see above); skipped is not passed")
  return 1 if failed else 0


if __name__ == "__main__":
  sys.exit(main())
