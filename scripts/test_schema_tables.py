#!/usr/bin/env python3
"""Type-column tests for the schema table macros in main.py.

The spec's field tables are rendered by MkDocs macros (`schema_fields`,
`extension_schema_fields`, `method_fields`). When a field's type could not
be named, the Type column fell back to "any": every `ucp` metadata field
and every composed (`allOf`) field rendered that way. These tests call the
macros the same way the docs build does and assert on the Type cell.

Some tables resolve schemas through the ucp-schema CLI, so it must be on
PATH (install with `cargo install ucp-schema`).

Run: python3 scripts/test_schema_tables.py
Exit: 0 on all pass, 1 on any failure.
"""

import os
from pathlib import Path
import re
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------
# Test harness (minimal, no deps)
# -----------------------------------------------------------

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


class _Env:
  """Stand-in for the mkdocs-macros env: collects registered macros."""

  def __init__(self) -> None:
    self.macros = {}

  def macro(self, fn):
    self.macros[fn.__name__] = fn
    return fn


def _load_macros() -> dict:
  # main.py resolves schema paths relative to the repository root.
  os.chdir(REPO_ROOT)
  sys.path.insert(0, str(REPO_ROOT))
  import main

  env = _Env()
  main.define_env(env)
  return env.macros


def _type_cell(table: str, field: str) -> str | None:
  """Return the Type cell of `field`'s row in a rendered Markdown table."""
  match = re.search(
    rf"^\| {re.escape(field)} \| (.*?) \|", table, flags=re.MULTILINE
  )
  return match.group(1) if match else None


# -----------------------------------------------------------
# Tests
# -----------------------------------------------------------


def test_ucp_ref_links_reference_section(macros: dict) -> None:
  """A `ucp` field $ref'ing a ucp.json $def links its reference anchor."""
  cell = _type_cell(
    macros["schema_fields"]("cart_resp", "shopping/cart"), "ucp"
  )
  _check(
    "ucp_ref_links_reference_section",
    cell is not None
    and "site:specification/reference/#ucp-response-cart-schema" in cell,
    f"got {cell!r}",
  )


def test_bundled_ucp_def_links_reference_section(macros: dict) -> None:
  """A ucp.json $def inlined by bundling is still identified and linked."""
  cell = _type_cell(
    macros["extension_schema_fields"](
      "catalog_search.json#/$defs/search_response", "shopping/catalog"
    ),
    "ucp",
  )
  _check(
    "bundled_ucp_def_links_reference_section",
    cell is not None
    and "site:specification/reference/#ucp-response-catalog-schema" in cell,
    f"got {cell!r}",
  )


def test_ucp_def_without_anchor_is_named(macros: dict) -> None:
  """A ucp.json $def with no reference anchor is named, not linked."""
  cell = _type_cell(
    macros["schema_fields"]("types/error_response", "shopping/checkout"),
    "ucp",
  )
  _check(
    "ucp_def_without_anchor_is_named",
    cell == "UCP Error",
    f"got {cell!r}",
  )


def test_composed_field_links_referenced_type(macros: dict) -> None:
  """An allOf of a $ref plus constraints shows the referenced type."""
  cell = _type_cell(
    macros["schema_fields"]("types/location_serves", "common/location"),
    "address",
  )
  _check(
    "composed_field_links_referenced_type",
    cell is not None and "[Locality]" in cell,
    f"got {cell!r}",
  )


def test_bundled_composed_field_uses_shared_type(macros: dict) -> None:
  """An allOf whose inlined branches agree on a type shows that type."""
  cell = _type_cell(
    macros["extension_schema_fields"](
      "payment_ap2_mandate.json#/$defs/dev.ucp.shopping.checkout",
      "payment/extensions/ap2-mandates",
    ),
    "ap2",
  )
  _check(
    "bundled_composed_field_uses_shared_type",
    cell == "object",
    f"got {cell!r}",
  )


def test_method_tables_name_ucp_field(macros: dict) -> None:
  """Operation tables built from OpenAPI name the `ucp` field too."""
  table = macros["method_fields"](
    "search_catalog", "shopping/rest.openapi.json", "shopping/catalog/rest"
  )
  cell = _type_cell(table, "ucp")
  _check(
    "method_tables_name_ucp_field",
    cell is not None and cell != "any",
    f"got {cell!r}",
  )


# -----------------------------------------------------------
# Main
# -----------------------------------------------------------


def main() -> int:
  """Run all tests and report. Exit 0 on pass, 1 on failure."""
  print("Running schema table type-column tests...\n")
  if not shutil.which("ucp-schema"):
    _check(
      "ucp_schema_available",
      False,
      "ucp-schema binary not on PATH (cargo install ucp-schema)",
    )
    return _report()
  macros = _load_macros()
  test_ucp_ref_links_reference_section(macros)
  test_bundled_ucp_def_links_reference_section(macros)
  test_ucp_def_without_anchor_is_named(macros)
  test_composed_field_links_referenced_type(macros)
  test_bundled_composed_field_uses_shared_type(macros)
  test_method_tables_name_ucp_field(macros)
  return _report()


if __name__ == "__main__":
  sys.exit(main())
