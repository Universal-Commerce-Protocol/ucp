"""Tests for the MCP tool annotations in the OpenRPC documents.

Every method in source/services/*/mcp.openrpc.json must carry an
`x-ucp-mcp-annotations` member (MCP ToolAnnotations hints). The values must
follow the rule set below, and the table in docs/specification/overview/
index.md must equal them, so the spec text and the machine-readable source
cannot drift.

Run: python3 scripts/test_openrpc_annotations.py
Exit: 0 on all pass, 1 on any failure.
"""

import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
KEY = "x-ucp-mcp-annotations"
HINTS = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")
DOC = REPO_ROOT / "docs" / "specification" / "overview" / "index.md"

_RESULTS: list[tuple[str, bool, str]] = []


def _check(name: str, condition: bool, detail: str = "") -> None:
  """Record a test result."""
  _RESULTS.append((name, condition, detail))


def _report() -> int:
  """Print results and return exit code."""
  failed = [(n, d) for n, ok, d in _RESULTS if not ok]
  for name, ok, detail in _RESULTS:
    suffix = f" - {detail}" if detail and not ok else ""
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{suffix}")
  print(f"\n{len(_RESULTS) - len(failed)} passed, {len(failed)} failed")
  return 0 if not failed else 1


def _methods() -> list[tuple[str, dict]]:
  """Return (service/name, method) for every MCP OpenRPC method."""
  out = []
  for path in sorted(
    (REPO_ROOT / "source" / "services").glob("*/mcp.openrpc.json")
  ):
    doc = json.loads(path.read_text(encoding="utf-8"))
    for method in doc["methods"]:
      out.append((f"{path.parent.name}/{method['name']}", method))
  return out


def _expected(name: str) -> dict:
  """Rule set: derive the hints from the tool-name family."""
  family = name.split("_", 1)[0]
  if family in ("search", "lookup") or name in ("get_product", "ask_business"):
    return {"readOnlyHint": True, "openWorldHint": True}
  if family == "get":
    return {"readOnlyHint": True, "openWorldHint": False}
  base = {"readOnlyHint": False}
  if family == "create":
    return {
      **base,
      "destructiveHint": False,
      "idempotentHint": False,
      "openWorldHint": False,
    }
  if family == "update":
    return {
      **base,
      "destructiveHint": False,
      "idempotentHint": True,
      "openWorldHint": False,
    }
  if family == "cancel":
    return {
      **base,
      "destructiveHint": True,
      "idempotentHint": True,
      "openWorldHint": False,
    }
  if family == "complete":
    return {
      **base,
      "destructiveHint": True,
      "idempotentHint": False,
      "openWorldHint": True,
    }
  raise KeyError(f"no classification rule for tool family {family!r} ({name})")


def test_every_method_has_annotations(methods) -> None:
  """Every method carries a complete annotations object."""
  for label, method in methods:
    ann = method.get(KEY)
    ok = (
      isinstance(ann, dict) and "readOnlyHint" in ann and "openWorldHint" in ann
    )
    if ok and ann["readOnlyHint"] is False:
      ok = "destructiveHint" in ann and "idempotentHint" in ann
    _check(f"annotations present: {label}", ok)


def test_annotations_follow_rule_set(methods) -> None:
  """Values equal those the name-family rule set derives."""
  for label, method in methods:
    try:
      want = _expected(method["name"])
    except KeyError as exc:
      _check(f"rule set covers: {label}", False, str(exc))
      continue
    _check(
      f"annotations follow rule set: {label}",
      method.get(KEY) == want,
      f"got {method.get(KEY)!r}, want {want!r}",
    )


def test_hints_are_booleans_and_known(methods) -> None:
  """Only the four MCP hints, all booleans."""
  for label, method in methods:
    ann = method.get(KEY) or {}
    ok = set(ann) <= set(HINTS) and all(
      isinstance(v, bool) for v in ann.values()
    )
    _check(f"only known boolean hints: {label}", ok)


def test_same_tool_name_same_annotations_across_services(methods) -> None:
  """Shopping and food share tool names; values must agree."""
  seen: dict[str, dict] = {}
  for label, method in methods:
    name = method["name"]
    ann = method.get(KEY)
    if name in seen:
      _check(f"consistent across services: {label}", seen[name] == ann)
    seen.setdefault(name, ann)


def _doc_table() -> dict[str, dict]:
  """Parse the annotation table from the overview page."""
  text = DOC.read_text(encoding="utf-8")
  rows = {}
  for m in re.finditer(
    r"^\| `(\w+)` \| (\w+) \| (\w+) \| (\w+) \| (\w+) \|", text, re.M
  ):
    name, *cells = m.groups()
    rows[name] = {
      hint: {"true": True, "false": False}[c]
      for hint, c in zip(HINTS, cells, strict=True)
      if c in ("true", "false")
    }
  return rows


def test_docs_table_equals_openrpc(methods) -> None:
  """The docs table is the same data as the OpenRPC members."""
  table = _doc_table()
  _check("docs table exists", bool(table))
  names = {m["name"] for _, m in methods}
  _check(
    "docs table lists exactly the OpenRPC tool names",
    set(table) == names,
    f"diff: {sorted(set(table) ^ names)}",
  )
  for label, method in methods:
    _check(
      f"docs table row equals OpenRPC: {label}",
      table.get(method["name"]) == method.get(KEY),
      f"docs {table.get(method['name'])!r} vs openrpc {method.get(KEY)!r}",
    )


def test_no_state_changing_tool_is_read_only(methods) -> None:
  """create/update/cancel/complete are never read-only."""
  for label, method in methods:
    if method["name"].startswith(
      ("create_", "update_", "cancel_", "complete_")
    ):
      _check(
        f"state-changing tool is not read-only: {label}",
        (method.get(KEY) or {}).get("readOnlyHint") is False,
      )


def main() -> int:
  """Run all checks."""
  methods = _methods()
  _check("found OpenRPC methods", len(methods) > 0)
  test_every_method_has_annotations(methods)
  test_annotations_follow_rule_set(methods)
  test_hints_are_booleans_and_known(methods)
  test_same_tool_name_same_annotations_across_services(methods)
  test_docs_table_equals_openrpc(methods)
  test_no_state_changing_tool_is_read_only(methods)
  return _report()


if __name__ == "__main__":
  sys.exit(main())
