#!/usr/bin/env python3
"""Contract test: embedded auth `type` param must be required in OpenRPC.

The Embedded Protocol prose defines the `ec.auth`/`ep.cart.auth` authorization
request `type` as REQUIRED. Under OpenRPC an omitted `required` defaults to
false, so the schema silently drifted from the prose (issue: embedded auth
`type` params missing `"required": true`) and downstream generators produced
an optional field. This keeps the two back in sync.

Run: python3 scripts/test_embedded_auth_required.py
Exit: 0 on all pass, 1 on any failure.
"""

import json
import sys
from pathlib import Path

_RESULTS: list[tuple[str, bool, str]] = []


def _check(name: str, condition: bool, detail: str = "") -> None:
  """Record a test result."""
  _RESULTS.append((name, condition, detail))


def _report() -> int:
  """Print results and return exit code."""
  passed = sum(1 for _, ok, _ in _RESULTS if ok)
  failed = [(n, d) for n, ok, d in _RESULTS if not ok]
  for name, ok, detail in _RESULTS:
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail and not ok else ""
    print(f"  {status}  {name}{suffix}")
  print(f"\n{passed} passed, {len(failed)} failed")
  return 0 if not failed else 1


REPO_ROOT = Path(__file__).parent.parent
OPENRPC_PATH = REPO_ROOT / "source" / "services" / "shopping" / "embedded.openrpc.json"
AUTH_METHODS = ("ec.auth", "ep.cart.auth")


def _find_method(doc: dict, name: str) -> dict:
  for method in doc.get("methods", []):
    if method.get("name") == name:
      return method
  raise AssertionError(f"method {name!r} not found in {OPENRPC_PATH}")


def _find_param(method: dict, name: str) -> dict:
  for param in method.get("params", []):
    if param.get("name") == name:
      return param
  raise AssertionError(f"param {name!r} not found on method {method.get('name')!r}")


def test_auth_type_param_is_required() -> None:
  doc = json.loads(OPENRPC_PATH.read_text())
  for method_name in AUTH_METHODS:
    method = _find_method(doc, method_name)
    param = _find_param(method, "type")
    _check(
      f"{method_name}.type.required",
      param.get("required") is True,
      f"got required={param.get('required')!r}",
    )


def main() -> int:
  print("Running embedded-auth-required contract tests...\n")
  test_auth_type_param_is_required()
  return _report()


if __name__ == "__main__":
  sys.exit(main())
