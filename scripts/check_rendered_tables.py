#!/usr/bin/env python3
"""Check the built site for schema tables that rendered wrong.

The field tables on the spec pages are generated from the JSON schemas and
OpenAPI documents by the macros in main.py. When a macro cannot name a
type, the build still succeeds: the Type cell just reads "any", "OneOf[]",
"Array[any]", or is empty. Each of those has reached the published site
before and was found by someone reading the page.

This runs after the MkDocs build and fails on the rendered output, so a
regression is caught in the PR that introduces it:

- Every schema field table (Name / Type / Requirement / Description) has a
  non-empty Name and a Type that names something: no placeholder, no empty
  composite such as "OneOf[]", no "any" at any nesting level.
- Every REST binding page renders its HTTP Headers table.
- Every `response_*_schema` definition in ucp.json has a rendered section
  with the `ucp-response-<name>-schema` anchor somewhere on the site.

Usage: python3 scripts/check_rendered_tables.py [SITE_DIR] [--schema-base DIR]
SITE_DIR defaults to local_preview; --schema-base to source/schemas.
Exit: 0 when clean, 1 when anything is reported.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys

SCHEMA_TABLE_HEADER = ("Name", "Type", "Requirement", "Description")
HEADER_TABLE_HEADER = ("Header", "Required", "Description")

# A Type cell that reads like one of these did not resolve.
_BAD_TYPE_PATTERNS = (
  re.compile(r"^any$"),
  re.compile(r"\[any\]"),
  re.compile(r"\[\]"),
  re.compile(r"[{}]"),
)


class _TableParser(HTMLParser):
  """Collect every table on a page as a list of rows of cell text."""

  def __init__(self) -> None:
    super().__init__()
    self.title = ""
    self.ids: set[str] = set()
    self.tables: list[list[list[str]]] = []
    self._table: list[list[str]] | None = None
    self._row: list[str] | None = None
    self._cell: list[str] | None = None
    self._in_title = False

  def handle_starttag(self, tag, attrs):
    attrs_dict = dict(attrs)
    if "id" in attrs_dict:
      self.ids.add(attrs_dict["id"])
    if tag == "title":
      self._in_title = True
    elif tag == "table":
      self._table = []
    elif tag == "tr" and self._table is not None:
      self._row = []
    elif tag in ("td", "th") and self._row is not None:
      self._cell = []

  def handle_endtag(self, tag):
    if tag == "title":
      self._in_title = False
    elif tag in ("td", "th") and self._cell is not None:
      self._row.append(" ".join("".join(self._cell).split()))
      self._cell = None
    elif tag == "tr" and self._row is not None:
      self._table.append(self._row)
      self._row = None
    elif tag == "table" and self._table is not None:
      self.tables.append(self._table)
      self._table = None

  def handle_data(self, data):
    if self._in_title:
      self.title += data
    if self._cell is not None:
      self._cell.append(data)


def _parse(path: Path) -> _TableParser:
  parser = _TableParser()
  parser.feed(path.read_text(encoding="utf-8"))
  return parser


def _is_redirect_stub(page: _TableParser) -> bool:
  return page.title.strip() == "Redirecting..."


def _bad_type(cell: str) -> bool:
  return not cell or any(p.search(cell) for p in _BAD_TYPE_PATTERNS)


def check_schema_tables(path: Path, page: _TableParser) -> list[str]:
  """Report rows whose Name or Type cell did not render."""
  problems = []
  for table in page.tables:
    if not table or tuple(table[0]) != SCHEMA_TABLE_HEADER:
      continue
    for row in table[1:]:
      name = row[0] if row else ""
      type_cell = row[1] if len(row) > 1 else ""
      if not name:
        problems.append(
          f"{path}: schema table row has no Name (type {type_cell!r})"
        )
      elif _bad_type(type_cell):
        shown = name if len(name) <= 60 else name[:57] + "..."
        problems.append(
          f"{path}: field {shown!r} rendered with type {type_cell!r}"
        )
  return problems


def check_rest_headers(path: Path, page: _TableParser) -> list[str]:
  """Report a REST binding page that renders no HTTP Headers table."""
  if not any(
    table and tuple(table[0]) == HEADER_TABLE_HEADER for table in page.tables
  ):
    return [f"{path}: REST binding page has no HTTP Headers table"]
  return []


def response_metadata_anchors(schema_base: Path) -> dict[str, str]:
  """Map each ucp.json `response_*_schema` def to its reference anchor."""
  ucp = json.loads((schema_base / "ucp.json").read_text(encoding="utf-8"))
  anchors = {}
  for name in ucp.get("$defs", {}):
    match = re.fullmatch(r"response_(\w+)_schema", name)
    if match:
      anchors[name] = f"ucp-response-{match.group(1)}-schema"
  return anchors


def _is_rest_binding(path: Path, site_dir: Path) -> bool:
  parts = path.relative_to(site_dir).parts
  return "specification" in parts and parts[-2:] == ("rest", "index.html")


def check_site(site_dir: Path, schema_base: Path) -> list[str]:
  """Run every check over the built site and return the problems found."""
  problems: list[str] = []
  seen_ids: set[str] = set()
  pages = 0

  for path in sorted(site_dir.rglob("*.html")):
    page = _parse(path)
    if _is_redirect_stub(page):
      continue
    pages += 1
    seen_ids |= page.ids
    problems += check_schema_tables(path, page)
    if _is_rest_binding(path, site_dir):
      problems += check_rest_headers(path, page)

  if pages == 0:
    return [f"{site_dir}: no HTML pages found; was the site built?"]

  for def_name, anchor in sorted(
    response_metadata_anchors(schema_base).items()
  ):
    if anchor not in seen_ids:
      problems.append(
        f"ucp.json $defs/{def_name} has no rendered section (#{anchor})"
      )

  return problems


def main(argv: list[str] | None = None) -> int:
  """Parse arguments, run the checks and return the exit code."""
  parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  parser.add_argument(
    "site_dir",
    nargs="?",
    default="local_preview",
    help="built site directory (default: local_preview)",
  )
  parser.add_argument(
    "--schema-base",
    default="source/schemas",
    help="schema directory holding ucp.json (default: source/schemas)",
  )
  args = parser.parse_args(argv)

  site_dir = Path(args.site_dir)
  if not site_dir.is_dir():
    print(f"Error: {site_dir} is not a directory", file=sys.stderr)
    return 1

  problems = check_site(site_dir, Path(args.schema_base))
  for problem in problems:
    print(problem)
  if problems:
    print(f"\n{len(problems)} rendering problem(s) found")
    return 1
  print("Rendered tables OK")
  return 0


if __name__ == "__main__":
  sys.exit(main())
