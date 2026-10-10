#!/usr/bin/env python3
"""Tests for the schema and header table macros in main.py.

The spec's field tables are rendered by MkDocs macros (`schema_fields`,
`extension_schema_fields`, `method_fields`). When a field's type could not
be named, the Type column fell back to "any": every `ucp` metadata field
and every composed (`allOf`) field rendered that way. The type-column tests
call the macros the same way the docs build does and assert on the Type
cell.

`header_fields` renders each REST binding's HTTP Headers table. Headers that
OpenAPI declares outside the parameter list (authentication through
`security`, media types through content maps) must still appear in it,
exactly once.

Some tables resolve schemas through the ucp-schema CLI, so it must be on
PATH (install with `cargo install ucp-schema`).

Run: python3 scripts/test_schema_tables.py
Exit: 0 on all pass, 1 on any failure.
"""

import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

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
# Header tables
# -----------------------------------------------------------


def _header_rows(table: str) -> list[str]:
  """Header names listed in the Request Headers part of a header table."""
  request = table.split("**Response Headers**")[0]
  return re.findall(r"^\| `([^`]+)` \|", request, re.M)


def test_header_tables_list_each_header_once(macros: dict) -> None:
  """No published header table names the same header twice."""
  docs = (REPO_ROOT / "docs").rglob("*.md")
  calls = set(
    re.findall(
      r"header_fields\('([^']+)', '([^']+)'\)",
      "".join(p.read_text(encoding="utf-8") for p in docs),
    )
  )
  duplicated = []
  for operation_id, file_name in sorted(calls):
    table = macros["header_fields"](operation_id, file_name)
    rows = [r.lower() for r in _header_rows(table)]
    if len(rows) != len(set(rows)):
      duplicated.append(operation_id)
  _check(
    "header_tables_list_each_header_once",
    bool(calls) and not duplicated,
    f"duplicates in {duplicated}" if calls else "no header_fields calls",
  )


def test_security_header_rows_follow_requirements() -> None:
  """Auth rows mirror security; required only if every alternative needs it."""
  main = sys.modules["main"]
  schemes = {
    "bearer": {"type": "http", "scheme": "bearer"},
    "basic": {"type": "http", "scheme": "basic"},
    "token": {"type": "oauth2", "flows": {}},
    "key": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
    "query_key": {"type": "apiKey", "in": "query", "name": "key"},
    "mtls": {"type": "mutualTLS"},
  }

  def required(document_security: list, operation: dict | None = None):
    data = {
      "security": document_security,
      "components": {"securitySchemes": schemes},
    }
    rows = main._security_header_rows(data, operation or {})
    return {r["name"]: r["required"] for r in rows}

  cases = [
    (
      "optional_alternatives",
      required([{}, {"bearer": []}, {"key": []}]),
      {"Authorization": False, "X-API-Key": False},
    ),
    ("single", required([{"bearer": []}]), {"Authorization": True}),
    (
      "conjunction",
      required([{"bearer": [], "key": []}]),
      {"Authorization": True, "X-API-Key": True},
    ),
    ("operation_opts_out", required([{"bearer": []}], {"security": []}), {}),
    (
      "operation_overrides",
      required([{"bearer": []}], {"security": [{"key": []}]}),
      {"X-API-Key": True},
    ),
    ("oauth2", required([{"token": []}]), {"Authorization": True}),
    ("no_header", required([{"query_key": []}, {"mtls": []}]), {}),
    (
      "shared_header",
      required([{"bearer": []}, {"basic": []}]),
      {"Authorization": True},
    ),
  ]
  wrong = [name for name, got, want in cases if got != want]
  _check(
    "security_header_rows_follow_requirements",
    not wrong,
    f"wrong: {wrong}",
  )


def test_content_header_rows_follow_media_types() -> None:
  """Content-Type needs a request body; Accept comes from a 2xx response."""
  main = sys.modules["main"]
  data = {
    "components": {
      "requestBodies": {"Body": {"content": {"application/json": {}}}}
    }
  }
  post = {
    "requestBody": {"$ref": "#/components/requestBodies/Body"},
    "responses": {
      "201": {"content": {"application/json": {}}},
      "default": {"content": {"text/plain": {}}},
    },
  }
  get = {"responses": {"200": {"content": {"application/json": {}}}}}
  errors_only = {
    "responses": {
      "4XX": {"content": {"application/json": {}}},
      "default": {"content": {"text/plain": {}}},
    }
  }
  post_rows = [r["name"] for r in main._content_header_rows(data, post)]
  get_rows = [r["name"] for r in main._content_header_rows(data, get)]
  error_rows = main._content_header_rows(data, errors_only)
  _check(
    "content_header_rows_follow_media_types",
    post_rows == ["Content-Type", "Accept"]
    and get_rows == ["Accept"]
    and not error_rows,
    f"post={post_rows} get={get_rows} errors={error_rows}",
  )


def test_declared_header_parameter_keeps_single_row(macros: dict) -> None:
  """A header still declared as a parameter is not synthesized again."""
  main = sys.modules["main"]
  spec = {
    "openapi": "3.1.0",
    "info": {"title": "headers", "version": "1"},
    "security": [{"bearer": []}],
    "paths": {
      "/x": {
        "post": {
          "operationId": "op",
          "parameters": [
            {"name": "Authorization", "in": "header"},
            {"name": "content-type", "in": "header"},
          ],
          "requestBody": {"content": {"application/json": {}}},
          "responses": {"200": {"content": {"application/json": {}}}},
        }
      }
    },
    "components": {
      "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}
    },
  }
  original = main.OPENAPI_DIR
  with tempfile.TemporaryDirectory() as tmp:
    Path(tmp, "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    main.OPENAPI_DIR = Path(tmp)
    try:
      rows = _header_rows(macros["header_fields"]("op", "spec.json"))
    finally:
      main.OPENAPI_DIR = original
  _check(
    "declared_header_parameter_keeps_single_row",
    sorted(r.lower() for r in rows)
    == ["accept", "authorization", "content-type"],
    f"got {rows}",
  )


# -----------------------------------------------------------
# Main
# -----------------------------------------------------------


def main() -> int:
  """Run all tests and report. Exit 0 on pass, 1 on failure."""
  print("Running schema and header table tests...\n")
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
  test_header_tables_list_each_header_once(macros)
  test_security_header_rows_follow_requirements()
  test_content_header_rows_follow_media_types()
  test_declared_header_parameter_keeps_single_row(macros)
  return _report()


if __name__ == "__main__":
  sys.exit(main())
