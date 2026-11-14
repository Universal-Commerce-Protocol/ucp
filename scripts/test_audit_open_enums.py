#!/usr/bin/env python3
#   Copyright 2026 UCP Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Contract conformance tests for audit_open_enums.py.

Run: python3 scripts/test_audit_open_enums.py
Exit: 0 on all pass, 1 on any failure.

No external dependencies beyond the Python standard library.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_open_enums as a  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------
# Test harness (minimal, no deps; dual standalone / pytest)
# -----------------------------------------------------------

_RESULTS: list[tuple[str, bool, str]] = []


def _check(name: str, condition: bool, detail: str = "") -> None:
  """Record a test result and fail immediately under pytest."""
  _RESULTS.append((name, condition, detail))
  if "pytest" in sys.modules and not condition:
    raise AssertionError(f"{name}: {detail}" if detail else name)


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


# -----------------------------------------------------------
# Unit tests (positive & negative cases)
# -----------------------------------------------------------


def test_extract_prose_values_positive_and_negative() -> None:
  """Prose extraction handles colons, parens, and excludes sibling fields."""
  v1 = a.extract_prose_values("Type. Well-known values: `delivery`, `pickup`.")
  _check(
    "prose_extract[well_known_backticks]",
    v1 == ["delivery", "pickup"],
    f"got {v1!r}",
  )

  v2 = a.extract_prose_values(
    "Common values include: processing (preparing to ship), "
    "shipped (handed to carrier)."
  )
  _check(
    "prose_extract[common_values_parens]",
    v2 == ["processing", "shipped"],
    f"got {v2!r}",
  )

  v3 = a.extract_prose_values(
    "Typically money-related like: refund, return, credit."
  )
  _check(
    "prose_extract[like_clause]",
    v3 == ["refund", "return", "credit"],
    f"got {v3!r}",
  )

  v4 = a.extract_prose_values(
    "Timing class, drawn from an open vocabulary. `immediate` is defined "
    "and `description` states terms.",
    sibling_props={"id", "type", "description", "amount"},
  )
  _check(
    "prose_extract[excludes_sibling_props]",
    v4 == ["immediate"],
    f"got {v4!r}",
  )


def test_audit_schema_open_enums_positive_and_negative() -> None:
  """Open-string schemas are partitioned into declared vs missing examples."""
  with tempfile.TemporaryDirectory() as tmp:
    schemas_dir = Path(tmp) / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "sample.json").write_text(
      json.dumps(
        {
          "type": "object",
          "properties": {
            "declared": {
              "type": "string",
              "description": "Open enum with examples.",
              "examples": ["a", "b"],
            },
            "missing": {
              "type": "string",
              "description": "Status. Well-known values: `foo`, `bar`.",
            },
            "closed_enum": {
              "type": "string",
              "enum": ["x", "y"],
            },
            "formatted": {
              "type": "string",
              "format": "uri",
              "description": "Well-known values: `https`.",
            },
          },
        }
      ),
      encoding="utf-8",
    )

    declared, missing = a.audit_schema_open_enums(schemas_dir)
    _check(
      "schema_audit[declared_count]",
      len(declared) == 1 and declared[0]["examples"] == ["a", "b"],
      f"got {declared!r}",
    )
    _check(
      "schema_audit[missing_count_and_suggestions]",
      len(missing) == 1 and missing[0]["suggested_examples"] == ["foo", "bar"],
      f"got {missing!r}",
    )


def _write_synthetic_fixture(root: Path) -> tuple[Path, Path]:
  """Build minimal synthetic schemas + docs fixture for payload tests."""
  schemas_dir = root / "schemas"
  (schemas_dir / "common" / "types").mkdir(parents=True)
  (schemas_dir / "shopping").mkdir(parents=True)

  (schemas_dir / "common" / "types" / "total.json").write_text(
    json.dumps(
      {
        "type": "object",
        "properties": {
          "type": {
            "type": "string",
            "description": (
              "Cost category. Well-known values: subtotal, tax, total."
            ),
          },
          "amount": {"type": "integer"},
        },
      }
    ),
    encoding="utf-8",
  )
  (schemas_dir / "common" / "types" / "link.json").write_text(
    json.dumps(
      {
        "type": "object",
        "properties": {
          "type": {
            "type": "string",
            "description": (
              "Link type. Well-known values: `privacy_policy`, `refund_policy`."
            ),
          },
        },
      }
    ),
    encoding="utf-8",
  )
  (schemas_dir / "common" / "types" / "error_code.json").write_text(
    json.dumps(
      {
        "type": "string",
        "examples": ["out_of_stock", "payment_failed"],
      }
    ),
    encoding="utf-8",
  )
  (schemas_dir / "common" / "types" / "message_error.json").write_text(
    json.dumps(
      {
        "type": "object",
        "properties": {
          "type": {"type": "string", "const": "error"},
          "code": {"$ref": "error_code.json"},
        },
      }
    ),
    encoding="utf-8",
  )
  (schemas_dir / "shopping" / "checkout.json").write_text(
    json.dumps(
      {
        "type": "object",
        "properties": {
          "totals": {
            "type": "array",
            "items": {"$ref": "../common/types/total.json"},
          },
          "links": {
            "type": "array",
            "items": {"$ref": "../common/types/link.json"},
          },
          "messages": {
            "type": "array",
            "items": {"$ref": "../common/types/message_error.json"},
          },
        },
      }
    ),
    encoding="utf-8",
  )

  docs_dir = root / "docs" / "specification" / "shopping"
  docs_dir.mkdir(parents=True)
  return schemas_dir, root / "docs"


def test_audit_docs_open_enum_values_positive_and_negative() -> None:
  """Doc value audit warns only on uncataloged non-reverse-domain values."""
  with tempfile.TemporaryDirectory() as tmp:
    schemas_dir, docs_dir = _write_synthetic_fixture(Path(tmp))
    md_file = docs_dir / "specification" / "shopping" / "checkout.md"
    md_file.write_text(
      "\n".join(
        [
          "# Checkout",
          "",
          "<!-- ucp:example schema=shopping/checkout op=read -->",
          "```json",
          "{",
          '  "totals": [{"type": "subtotal", "amount": 1000}],',
          '  "links": [{"type": "privacy_policy"}],',
          '  "messages": [',
          '    {"type": "error", "code": "out_of_stock"},',
          '    {"type": "error", "code": "com.example.custom_error"}',
          "  ]",
          "}",
          "```",
          "",
          '<!-- ucp:example skip reason="illustrative custom total" -->',
          "```json",
          '{"totals": [{"type": "skipped_custom", "amount": 10}]}',
          "```",
          "",
          "<!-- ucp:example schema=shopping/checkout op=read -->",
          "```json",
          "{",
          '  "totals": [{"type": "tip", "amount": 200}],',
          '  "links": [{"type": "cancellation_policy"}]',
          "}",
          "```",
          "",
        ]
      ),
      encoding="utf-8",
    )

    warnings = a.audit_docs_open_enum_values(docs_dir, schemas_dir)
    _check(
      "doc_audit[two_expected_warnings]",
      len(warnings) == 2,
      f"expected 2 warnings, got {warnings!r}",
    )

    values_found = {w["value"] for w in warnings}
    _check(
      "doc_audit[flagged_values]",
      values_found == {"tip", "cancellation_policy"},
      f"got {values_found!r}",
    )

    paths_found = {w["path"] for w in warnings}
    _check(
      "doc_audit[json_paths_accurate]",
      paths_found == {"$.totals[0].type", "$.links[0].type"},
      f"got {paths_found!r}",
    )

    tip_warn = next((w for w in warnings if w["value"] == "tip"), None)
    link_warn = next(
      (w for w in warnings if w["value"] == "cancellation_policy"), None
    )
    _check(
      "doc_audit[warning_metadata_and_line]",
      tip_warn is not None
      and tip_warn["line"] == 23
      and tip_warn["file"] == "specification/shopping/checkout.md"
      and "subtotal" in tip_warn["known_values"]
      and link_warn is not None
      and link_warn["line"] == 24,
      f"got tip={tip_warn!r}, link={link_warn!r}",
    )


def test_corpus_integration() -> None:
  """Running against the real UCP repository succeeds and surfaces findings."""
  schemas_dir = REPO_ROOT / "source" / "schemas"
  docs_dir = REPO_ROOT / "docs"
  if not schemas_dir.is_dir() or not docs_dir.is_dir():
    return

  declared, missing = a.audit_schema_open_enums(schemas_dir)
  warnings = a.audit_docs_open_enum_values(docs_dir, schemas_dir)

  _check(
    "corpus[declared_open_enums_gte_10]",
    len(declared) >= 10,
    f"got {len(declared)}",
  )
  _check(
    "corpus[missing_open_enum_examples_gte_20]",
    len(missing) >= 20,
    f"got {len(missing)}",
  )
  _check(
    "corpus[doc_warnings_present]",
    len(warnings) > 0,
    f"got {len(warnings)}",
  )


# -----------------------------------------------------------
# Main
# -----------------------------------------------------------


def main() -> int:
  """Run all open-enumeration contract tests and report."""
  print("Running audit_open_enums contract tests...\n")
  test_extract_prose_values_positive_and_negative()
  test_audit_schema_open_enums_positive_and_negative()
  test_audit_docs_open_enum_values_positive_and_negative()
  test_corpus_integration()
  return _report()


if __name__ == "__main__":
  sys.exit(main())
