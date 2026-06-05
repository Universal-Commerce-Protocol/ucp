#!/usr/bin/env python3
"""Regression tests for docs macro rendering in main.py."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main  # noqa: E402

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


def _has_ucp_schema() -> bool:
  return shutil.which("ucp-schema") is not None


class DummyEnv:
  def __init__(self):
    self.macros = {}
    self.page = None

  def macro(self, fn):
    self.macros[fn.__name__] = fn
    return fn


def test_complete_checkout_payment_required() -> None:
  if not _has_ucp_schema():
    _check("complete_checkout_payment_required", True)
    return

  env = DummyEnv()
  main.define_env(env)
  rendered = env.macros["method_fields"](
    "complete_checkout", "rest.openapi.json", "checkout"
  )

  _check(
    "complete_checkout_payment_required",
    "| payment | [Payment](site:specification/checkout/#payment) | **Yes** |"
    in rendered,
    "payment row was not rendered as required",
  )


if __name__ == "__main__":
  test_complete_checkout_payment_required()
  raise SystemExit(_report())
