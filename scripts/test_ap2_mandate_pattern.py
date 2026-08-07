#!/usr/bin/env python3
"""Unit tests for checkout_mandate pattern in ap2_mandate.json.

The pattern must accept RFC 9901 compact SD-JWT serializations, including
trailing tildes and empty disclosure segments, and delegate chains joined
with ``~~`` as emitted by the AP2 reference implementation.

Run: python3 scripts/test_ap2_mandate_pattern.py
Exit: 0 on all pass, 1 on any failure.
"""

import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SCHEMA_PATH = _REPO_ROOT / "source" / "schemas" / "shopping" / "ap2_mandate.json"

_RESULTS: list[tuple[str, bool, str]] = []


def _check(name: str, condition: bool, detail: str = "") -> None:
  _RESULTS.append((name, condition, detail))


def _report() -> int:
  passed = sum(1 for _, ok, _ in _RESULTS if ok)
  failed = [(n, d) for n, ok, d in _RESULTS if not ok]
  for name, ok, detail in _RESULTS:
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail and not ok else ""
    print(f"  {status}  {name}{suffix}")
  print(f"\n{passed} passed, {len(failed)} failed")
  return 0 if not failed else 1


def _load_checkout_mandate_pattern() -> re.Pattern[str]:
  schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
  raw = schema["$defs"]["checkout_mandate"]["pattern"]
  return re.compile(raw)


def test_checkout_mandate_pattern() -> None:
  """Pattern accepts expected SD-JWT wire forms and rejects invalid strings."""
  pattern = _load_checkout_mandate_pattern()
  matches = pattern.fullmatch

  valid = [
    ("compact_jwt_only", "eyJhbGciOiJFUzI1NiJ9.eyJpc3MiOiJ1c3AifQ.signature"),
    ("trailing_tilde_no_kb", "eyJhbGciOiJFUzI1NiJ9.payload.sig~"),
    (
      "disclosures_and_trailing_tilde",
      "eyJhbGciOiJFUzI1NiJ9.payload.sig~disclosure1~disclosure2~",
    ),
    (
      "delegate_chain_reference_shape",
      "eyJhbGciOiJFUzI1NiJ9.payload.sig~~disclosure1~disclosure2~",
    ),
    ("empty_disclosure_segment", "eyJhbGciOiJFUzI1NiJ9.payload.sig~~"),
  ]

  for name, value in valid:
    _check(
      f"valid[{name}]",
      matches(value) is not None,
      f"expected match for {value!r}",
    )

  invalid = [
    ("missing_signature", "eyJhbGciOiJFUzI1NiJ9.payload"),
    ("space_in_disclosure", "eyJhbGciOiJFUzI1NiJ9.payload.sig~bad segment~"),
    ("dot_in_disclosure_segment", "eyJhbGciOiJFUzI1NiJ9.payload.sig~a.b~"),
  ]

  for name, value in invalid:
    _check(
      f"invalid[{name}]",
      matches(value) is None,
      f"expected no match for {value!r}",
    )


def main() -> int:
  print("Running ap2_mandate checkout_mandate pattern tests...\n")
  test_checkout_mandate_pattern()
  return _report()


if __name__ == "__main__":
  sys.exit(main())
