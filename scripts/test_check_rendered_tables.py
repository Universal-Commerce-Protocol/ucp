#!/usr/bin/env python3
"""Tests for scripts/check_rendered_tables.py.

Each test writes a small built site into a temp directory and runs the
checks over it, so the script is exercised on the same HTML shapes
mkdocs-material emits, without a full docs build.

Run: python3 scripts/test_check_rendered_tables.py
Exit: 0 on all pass, 1 on any failure.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_rendered_tables as crt  # noqa: E402

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


# -----------------------------------------------------------
# Fixtures
# -----------------------------------------------------------


def _table(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
  def tr(cells, tag):
    inner = "".join(
      f'<{tag} style="text-align: left;">{c}</{tag}>' for c in cells
    )
    return f"<tr>{inner}</tr>"

  body = "".join(tr(r, "td") for r in rows)
  return (
    f"<table><thead>{tr(header, 'th')}</thead><tbody>{body}</tbody></table>"
  )


def _page(title: str, body: str) -> str:
  return (
    '<!doctype html><html><head><meta charset="utf-8">'
    f"<title>{title}</title></head><body>{body}</body></html>"
  )


SCHEMA = crt.SCHEMA_TABLE_HEADER
HEADERS = crt.HEADER_TABLE_HEADER

GOOD_SCHEMA_TABLE = _table(
  SCHEMA,
  [
    ("id", "string", "Required", "Identifier."),
    ("totals", "Array[Total]", "Optional", "Totals."),
    ("ucp", '<a href="#x">UCP Checkout Response Schema</a>', "Required", ""),
    ("extends", "OneOf[string, array]", "Optional", "Extends."),
  ],
)
GOOD_HEADER_TABLE = _table(
  HEADERS, [("<code>UCP-Agent</code>", "<strong>Yes</strong>", "Agent.")]
)
METADATA_SECTION = '<h3 id="ucp-response-checkout-schema">Checkout</h3>'


class _Site:
  """A temp site dir plus a schema dir with one ucp.json."""

  def __init__(self, defs: list[str] = ("response_checkout_schema",)):
    self._tmp = tempfile.TemporaryDirectory()
    root = Path(self._tmp.name)
    self.site = root / "site"
    self.schemas = root / "schemas"
    self.schemas.mkdir()
    (self.schemas / "ucp.json").write_text(
      json.dumps({"$defs": {name: {} for name in defs}}), encoding="utf-8"
    )

  def write(self, rel: str, html: str) -> None:
    path = self.site / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")

  def problems(self) -> list[str]:
    return crt.check_site(self.site, self.schemas)

  def close(self) -> None:
    self._tmp.cleanup()


def _clean_site() -> _Site:
  site = _Site()
  site.write(
    "specification/reference/index.html",
    _page("Reference", METADATA_SECTION + GOOD_SCHEMA_TABLE),
  )
  site.write(
    "specification/shopping/checkout/rest/index.html",
    _page("Checkout REST", GOOD_HEADER_TABLE + GOOD_SCHEMA_TABLE),
  )
  return site


# -----------------------------------------------------------
# Tests
# -----------------------------------------------------------


def test_clean_site_passes() -> None:
  """A site with good tables and a metadata section reports nothing."""
  site = _clean_site()
  problems = site.problems()
  site.close()
  _check("clean_site_passes", problems == [], f"got {problems!r}")


def test_bad_type_cells_are_reported() -> None:
  """Each placeholder or empty Type cell is reported once, naming the page."""
  cases = {
    "any": "any",
    "array_any": "Array[any]",
    "empty_one_of": "OneOf[]",
    "empty_all_of": "AllOf[]",
    "placeholder": "{type}",
    "empty": "",
  }
  for label, cell in cases.items():
    site = _clean_site()
    site.write(
      "specification/shopping/cart/index.html",
      _page("Cart", _table(SCHEMA, [("field", cell, "Optional", "d")])),
    )
    problems = site.problems()
    site.close()
    _check(
      f"bad_type_cell_reported_{label}",
      len(problems) == 1
      and "cart/index.html" in problems[0]
      and repr(cell) in problems[0],
      f"got {problems!r}",
    )


def test_good_type_cells_pass() -> None:
  """Named, nested and union types are never flagged; only placeholders."""
  cells = [
    "string",
    "Array[string]",
    "Map[string, Array[object]]",
    "OneOf[string, null]",
    "AllOf[Ap2 With Merchant Authorization, Ap2 With Checkout Mandate]",
    '<a href="../reference/#geo">Geo</a>',
    "Map[string, OneOf[Constraint Expression, object]]",
  ]
  site = _clean_site()
  site.write(
    "specification/shopping/cart/index.html",
    _page(
      "Cart",
      _table(
        SCHEMA, [(f"f{i}", c, "Optional", "d") for i, c in enumerate(cells)]
      ),
    ),
  )
  problems = site.problems()
  site.close()
  _check("good_type_cells_pass", problems == [], f"got {problems!r}")


def test_scalar_prose_under_header_is_reported() -> None:
  """The amenity_type shape: description as a one-cell row, Type empty."""
  site = _clean_site()
  site.write(
    "specification/common/location/index.html",
    _page(
      "Location",
      _table(SCHEMA, [("Reverse-domain identifier used for ...", "", "", "")]),
    ),
  )
  problems = site.problems()
  site.close()
  _check(
    "scalar_prose_under_header_is_reported",
    len(problems) == 1 and "rendered with type ''" in problems[0],
    f"got {problems!r}",
  )


def test_hand_written_tables_are_ignored() -> None:
  """Only macro-shaped tables are checked; other Type columns are prose."""
  site = _clean_site()
  site.write(
    "specification/payment/template/index.html",
    _page(
      "Template",
      _table(
        ("Field", "Type", "Required", "Description"),
        [("{field}", "{type}", "{Yes/No}", "{description}")],
      )
      + _table(("Type", "Description"), [("info", "Informational.")]),
    ),
  )
  problems = site.problems()
  site.close()
  _check("hand_written_tables_are_ignored", problems == [], f"got {problems!r}")


def test_rest_page_without_headers_table_is_reported() -> None:
  """A REST binding page missing its HTTP Headers table is reported."""
  site = _clean_site()
  site.write(
    "specification/common/location/rest/index.html",
    _page("Location REST", GOOD_SCHEMA_TABLE),
  )
  problems = site.problems()
  site.close()
  _check(
    "rest_page_without_headers_table_is_reported",
    len(problems) == 1
    and "location/rest/index.html" in problems[0]
    and "HTTP Headers" in problems[0],
    f"got {problems!r}",
  )


def test_redirect_stubs_are_skipped() -> None:
  """Redirect stubs mike writes at old paths are not REST bindings."""
  site = _clean_site()
  site.write(
    "specification/catalog/rest/index.html",
    _page("Redirecting...", "You're being redirected"),
  )
  problems = site.problems()
  site.close()
  _check("redirect_stubs_are_skipped", problems == [], f"got {problems!r}")


def test_missing_response_metadata_section_is_reported() -> None:
  """A ucp.json response metadata def with no rendered anchor is reported."""
  site = _Site(defs=["response_checkout_schema", "response_ask_schema"])
  site.write(
    "specification/reference/index.html",
    _page("Reference", METADATA_SECTION + GOOD_SCHEMA_TABLE),
  )
  problems = site.problems()
  site.close()
  _check(
    "missing_response_metadata_section_is_reported",
    len(problems) == 1
    and "response_ask_schema" in problems[0]
    and "ucp-response-ask-schema" in problems[0],
    f"got {problems!r}",
  )


def test_metadata_anchor_anywhere_on_site_counts() -> None:
  """The section may live on a binding page rather than reference.md."""
  site = _Site(defs=["response_ask_schema"])
  site.write(
    "specification/common/ask/rest/index.html",
    _page(
      "Ask REST",
      '<h3 id="ucp-response-ask-schema">Ask</h3>' + GOOD_HEADER_TABLE,
    ),
  )
  problems = site.problems()
  site.close()
  _check(
    "metadata_anchor_anywhere_on_site_counts",
    problems == [],
    f"got {problems!r}",
  )


def test_empty_site_is_an_error() -> None:
  """A directory with no HTML is reported rather than passing vacuously."""
  site = _Site()
  site.site.mkdir()
  problems = site.problems()
  site.close()
  _check(
    "empty_site_is_an_error",
    len(problems) == 1 and "no HTML pages" in problems[0],
    f"got {problems!r}",
  )


def test_cli_exit_codes() -> None:
  """The CLI exits 0 on a clean site and 1 when anything is reported."""
  site = _clean_site()
  ok = crt.main([str(site.site), "--schema-base", str(site.schemas)])
  site.write(
    "specification/shopping/cart/index.html",
    _page("Cart", _table(SCHEMA, [("f", "any", "Optional", "d")])),
  )
  bad = crt.main([str(site.site), "--schema-base", str(site.schemas)])
  site.close()
  _check("cli_exit_codes", (ok, bad) == (0, 1), f"got {(ok, bad)!r}")


def main() -> int:
  """Run every test and report."""
  test_clean_site_passes()
  test_bad_type_cells_are_reported()
  test_good_type_cells_pass()
  test_scalar_prose_under_header_is_reported()
  test_hand_written_tables_are_ignored()
  test_rest_page_without_headers_table_is_reported()
  test_redirect_stubs_are_skipped()
  test_missing_response_metadata_section_is_reported()
  test_metadata_anchor_anywhere_on_site_counts()
  test_empty_site_is_an_error()
  test_cli_exit_codes()
  return _report()


if __name__ == "__main__":
  sys.exit(main())
