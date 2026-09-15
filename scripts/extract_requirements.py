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

"""Extract a machine-readable requirements catalog from the specification.

Reads the normative prose of the checkout capability and writes two files:

  generated/requirements/requirements.json       the requirements
  generated/requirements/extraction_report.json  what was excluded, and why

The report is not a debug log. Every clause citing an RFC 2119 keyword
either becomes a requirement or appears in the report with a reason, so the
two documents reconcile against the spec exactly. Reading the report is how
an author finds obligations the extractor could not attribute, and prose
that reads as normative but is not marked up as such.

Usage:

  # Write both documents.
  .venv/bin/python scripts/extract_requirements.py

  # Verify the committed documents match the specification. Exits non-zero
  # if regenerating would change anything, which is the form to run in CI.
  .venv/bin/python scripts/extract_requirements.py --check

  # Print a summary without touching the filesystem.
  .venv/bin/python scripts/extract_requirements.py --dry-run --summary
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.requirements_extractor import catalog, config  # noqa: E402


def _print_summary(summary: dict) -> None:
  """Print the run summary in a form that is readable in CI logs."""
  print(f"requirements: {summary['requirements']}")

  print("\n  by level:")
  for level, count in summary["by_level"].items():
    print(f"    {level:<12} {count}")

  print("\n  by actor:")
  for actor, count in summary["by_actor"].items():
    print(f"    {actor:<20} {count}")

  print("\n  by file:")
  for name, count in summary["by_file"].items():
    print(f"    {Path(name).name:<16} {count}")

  print(
    f"\n  with a condition: {summary['with_condition']}"
    f"   with referenced fields: {summary['with_referenced_fields']}"
    f"   from a compound split: {summary['from_compound_split']}"
  )

  print("\n  diagnostics:")
  for name, count in summary["diagnostics"].items():
    marker = " " if count == 0 else "*"
    print(f"   {marker}{name:<30} {count}")


def _check(paths_and_documents: list[tuple[Path, dict]]) -> int:
  """Compare regenerated documents against what is on disk.

  Args:
    paths_and_documents: Destination paths paired with fresh documents.

  Returns:
    A process exit status: 0 when every file is already current.

  """
  stale = []
  for path, document in paths_and_documents:
    expected = catalog.serialize(document)
    if not path.exists():
      stale.append((path, "missing"))
    elif path.read_text(encoding="utf-8") != expected:
      stale.append((path, "out of date"))

  if not stale:
    print("Requirements catalog is up to date.")
    return 0

  for path, reason in stale:
    print(f"{path.relative_to(REPO_ROOT)}: {reason}", file=sys.stderr)
  print(
    "\nRegenerate with: python scripts/extract_requirements.py",
    file=sys.stderr,
  )
  return 1


def main() -> int:
  """Entry point.

  Returns:
    A process exit status.

  """
  argument_parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
  )
  argument_parser.add_argument(
    "--catalog",
    type=Path,
    default=config.DEFAULT_CATALOG_PATH,
    help="Where to write the requirements (default: %(default)s).",
  )
  argument_parser.add_argument(
    "--report",
    type=Path,
    default=config.DEFAULT_REPORT_PATH,
    help="Where to write the diagnostics (default: %(default)s).",
  )
  argument_parser.add_argument(
    "--check",
    action="store_true",
    help=(
      "Do not write. Exit non-zero if regenerating would change either "
      "file, so CI can prove the committed catalog matches the spec."
    ),
  )
  argument_parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Run the pipeline but write nothing.",
  )
  argument_parser.add_argument(
    "--summary",
    action="store_true",
    help="Print counts for the run.",
  )
  argument_parser.add_argument(
    "--fail-on-unresolved",
    action="store_true",
    help=(
      "Exit non-zero if any document's capability could not be resolved. "
      "Useful once scope widens past a single capability directory."
    ),
  )
  args = argument_parser.parse_args()

  requirements, report = catalog.build()
  catalog_doc = catalog.catalog_document(requirements, report)
  report_doc = catalog.report_document(requirements, report)

  if args.summary:
    _print_summary(catalog_doc["summary"])

  unresolved = catalog.unresolved_capabilities(requirements)
  if unresolved:
    print(
      f"\nwarning: {len(unresolved)} document(s) with no capability:",
      file=sys.stderr,
    )
    for name in unresolved:
      print(f"  {name}", file=sys.stderr)
    if args.fail_on_unresolved:
      return 1

  if args.check:
    return _check([(args.catalog, catalog_doc), (args.report, report_doc)])

  if args.dry_run:
    print("\nDry run: nothing written.")
    return 0

  catalog.write(args.catalog, catalog_doc)
  catalog.write(args.report, report_doc)
  print(f"\nWrote {len(requirements)} requirements")
  print(f"  {args.catalog.relative_to(REPO_ROOT)}")
  print(f"  {args.report.relative_to(REPO_ROOT)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
