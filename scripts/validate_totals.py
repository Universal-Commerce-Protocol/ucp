#!/usr/bin/env python3
# cspell:ignore JSONPath
"""Enforce totals arithmetic in UCP specification documentation examples.

`validate_examples.py` proves every ```json block in the docs conforms
to its declared schema. Schema conformance is structural: JSON Schema
cannot express a relationship between the values of sibling array
entries. The `totals[]` arithmetic the specification states normatively
therefore has no enforcement, and an example can drift silently while
staying schema-valid. This script closes that gap, and only that gap.

================================================================
THE TWO INVARIANTS
================================================================

Both are quoted from docs/specification/shopping/checkout/index.md, "Total"
(anchor #totals). Nothing else is inferred, and no heuristic is
applied: an arithmetic identity is either stated there or is not
checked here.

(A) Breakdown sum — from "Verification":

      assert sum(e.amount for e in totals if e.type != "total")
        == total_entry.amount

(B) Sub-line sum — from "Sub-Lines (`lines`)":

      sum(lines[].amount) MUST equal the parent entry's amount

================================================================
WHEN (A) APPLIES
================================================================

(A) presupposes the `totals.json` shape, which the specification
defines by its subtotal/total pairing: "Exactly one `type: "subtotal"`
MUST be present. Exactly one `type: "total"` MUST be present." An array
is treated as that shape when it carries at least one `subtotal` entry
and exactly one `total` entry.

Several fields are typed `array<total.json>` rather than `totals.json`
and carry no such pairing rule — a fulfillment option
(`fulfillment.methods[].groups[].options[].totals`) and an order
adjustment (`adjustments[].totals`) legitimately hold a single
`{"type": "total"}` entry. A lone `total` with no `subtotal` is
therefore skipped, not failed.

Arrays are also skipped when they carry elision markers, or an entry
without a string `type` and integer `amount`: the displayed numbers are
then an incomplete record of the breakdown and no sum over them is
meaningful.

(B) is applied per entry, so an entry with a complete `lines` breakdown
is still checked when an unrelated sibling entry is elided.

================================================================
SIGNED AMOUNTS ARE A PRECONDITION
================================================================

(A) sums amounts as written, which is only meaningful under the
convention the specification defines: "Amounts are signed integers —
negative values are subtractive (e.g., discounts), positive values are
additive. The sign IS the direction."

A `discount` or `items_discount` entry with a positive amount means the
document is instead using a subtract-the-discount convention, under
which summing as written can balance while the intended total differs.
That is a failure, not an accepted second reading: a check that honours
both conventions would pass broken arithmetic under either one.

================================================================
THE CORPUS
================================================================

Across docs/ the walk finds 138 `totals` arrays:

   88  a subtotal and exactly one total     → checked under (A)
       (47 at order level, 41 at line_items[].totals)
   30  a lone `total`, no subtotal          → skipped
       (26 fulfillment options, 4 order adjustments)
   20  elision markers                      → skipped
    1  an entry carrying `lines`            → checked under (B)

Line-item `totals` is typed `array<total.json>`, like a fulfillment
option, so nothing obliges it to carry the pair. Where a doc example
does carry it, `subtotal ± adjustments == total` is a true statement
about those numbers, and admitting them keeps the filter structural
rather than encoding per-path schema shape.

================================================================
WHAT THIS DELIBERATELY DOES NOT DO
================================================================

No schema resolution and no `ucp-schema` subprocess: schema binding is
`validate_examples.py`'s job. Staying pure-stdlib keeps this check fast
and independent of the toolchain version installed locally.

The bespoke JSON superset the docs are authored in — line comments,
`{{ ucp_version }}`, bare `...` elision, HTTP envelopes — is not
re-implemented either. `validate_examples.py` owns that reduction and
documents it in its module docstring; this script imports it. Blocks
that still fail to parse afterwards are skipped silently: an
unparsable block is already a hard failure in that validator, and
reporting it twice would make one defect look like two.

================================================================
CLI
================================================================

  validate_totals.py
  validate_totals.py --file FILE [FILE ...]

Exit codes: 0 if every checked array satisfies both invariants; 1 if
any array violates one.
"""

import argparse
import json
import sys
from pathlib import Path

import validate_examples as examples

# -----------------------------------------------------------
# Skip reasons
# -----------------------------------------------------------

SKIP_ELIDED = "contains elision markers"
SKIP_EMPTY = "empty array"
SKIP_MALFORMED = "entry without a string type and integer amount"
SKIP_SHAPE = "no subtotal/total pairing (array<total.json>)"

# Types the specification defines as subtractive, whose amounts are
# therefore negative under the signed-amount convention.
SUBTRACTIVE_TYPES = frozenset({"discount", "items_discount"})

# -----------------------------------------------------------
# Candidate discovery
# -----------------------------------------------------------


def find_totals_arrays(node, path: str = "$"):
  """Yield (location, array) for every `totals` array at any depth."""
  if isinstance(node, dict):
    for key, value in node.items():
      child = f"{path}.{key}"
      if key == "totals" and isinstance(value, list):
        yield child, value
      yield from find_totals_arrays(value, child)
  elif isinstance(node, list):
    for index, item in enumerate(node):
      yield from find_totals_arrays(item, f"{path}[{index}]")


def block_totals_arrays(block: dict, tree) -> list[tuple[str, list]]:
  """Collect the totals arrays one example block contributes.

  Most blocks nest the breakdown under a `totals` key. The canonical
  examples in the Total section display the bare array instead and bind
  it with `target=$.totals`, so the annotation is what identifies them.
  An `extract=` block displays an envelope around the bound payload,
  where the key search already finds the array.
  """
  found = list(find_totals_arrays(tree))
  annotation = block.get("annotation") or {}
  target = annotation.get("target") or ""
  if (
    isinstance(tree, list)
    and not annotation.get("extract")
    and target.split(".")[-1] == "totals"
  ):
    found.append(("$", tree))
  return found


# -----------------------------------------------------------
# Entry predicates
# -----------------------------------------------------------


def contains_elision(node) -> bool:
  """Report whether any elision marker appears anywhere under `node`.

  Defers to validate_examples for what counts as a marker: the
  sentinel forms are part of that module's authoring contract.
  """
  if examples._is_ellipsis(node):
    return True
  if isinstance(node, dict):
    return any(
      key == "..." or contains_elision(value) for key, value in node.items()
    )
  if isinstance(node, list):
    return any(contains_elision(item) for item in node)
  return False


def is_amount(value) -> bool:
  """Report whether a value is a usable signed integer amount."""
  return isinstance(value, int) and not isinstance(value, bool)


def is_entry(value) -> bool:
  """Report whether a value is a complete `total.json`-shaped entry."""
  return (
    isinstance(value, dict)
    and isinstance(value.get("type"), str)
    and is_amount(value.get("amount"))
  )


# -----------------------------------------------------------
# Reporting
# -----------------------------------------------------------


class Report:
  """Outcomes accumulated across every array a run inspected."""

  def __init__(self) -> None:
    """Start an empty report."""
    self.checked: dict[str, int] = {"A": 0, "B": 0}
    self.skips: dict[str, dict[str, int]] = {"A": {}, "B": {}}
    self.failures: list[str] = []
    self.unparsed = 0

  def skip(self, invariant: str, reason: str) -> None:
    """Record one skipped candidate against an invariant."""
    reasons = self.skips[invariant]
    reasons[reason] = reasons.get(reason, 0) + 1

  def skipped(self, invariant: str) -> int:
    """Count candidates skipped for one invariant."""
    return sum(self.skips[invariant].values())

  def fail(
    self,
    file: str,
    line: int,
    location: str,
    headline: str,
    rows: list[str],
    arithmetic: tuple[tuple[str, int], tuple[str, int]] | None = None,
  ) -> None:
    """Record one violated invariant, with its sums where it has them."""
    body = [f"FAIL {file}:{line}  {location}", f"       {headline}"]
    body += [f"         {row}" for row in rows]
    if arithmetic:
      (computed_label, computed), (declared_label, declared) = arithmetic
      width = max(len(computed_label), len(declared_label), len("delta"))
      body += [
        f"       {computed_label:<{width}} : {computed}",
        f"       {declared_label:<{width}} : {declared}",
        f"       {'delta':<{width}} : {computed - declared:+d}",
      ]
    self.failures.append("\n".join(body))

  def summary(self) -> str:
    """Render the counts a run ends with."""
    checked = self.checked["A"] + self.checked["B"]
    skipped = self.skipped("A") + self.skipped("B")
    lines = [
      f"{checked} checked, {len(self.failures)} failed, {skipped} skipped",
      f"  (A) breakdown sum: {self.checked['A']} arrays checked,"
      f" {self.skipped('A')} skipped",
      f"  (B) sub-line sum:  {self.checked['B']} entries checked,"
      f" {self.skipped('B')} skipped",
    ]
    for invariant in ("A", "B"):
      for reason, count in sorted(self.skips[invariant].items()):
        lines.append(f"      {invariant}: {count} {reason}")
    if self.unparsed:
      lines.append(
        f"  {self.unparsed} JSON blocks not parsable after reduction"
        f" (reported by validate_examples.py)"
      )
    return "\n".join(lines)


def entry_rows(entries: list[dict]) -> list[str]:
  """Render entries as aligned type / amount / display_text rows."""
  types = [str(entry.get("type", "?")) for entry in entries]
  width = max((len(name) for name in types), default=0)
  rows = []
  for name, entry in zip(types, entries, strict=True):
    text = entry.get("display_text")
    label = f'"{text}"' if isinstance(text, str) else "(no display_text)"
    rows.append(f"{name:<{width}}  {entry.get('amount'):>12}  {label}")
  return rows


def line_rows(lines: list[dict]) -> list[str]:
  """Render sub-lines as aligned amount / display_text rows."""
  rows = []
  for sub in lines:
    text = sub.get("display_text")
    label = f'"{text}"' if isinstance(text, str) else "(no display_text)"
    rows.append(f"{sub.get('amount'):>12}  {label}")
  return rows


# -----------------------------------------------------------
# The invariants
# -----------------------------------------------------------


def check_breakdown_sum(
  file: str,
  line: int,
  location: str,
  array: list,
  report: Report,
) -> None:
  """Invariant (A). Non-total entries MUST sum to the total entry."""
  if contains_elision(array):
    report.skip("A", SKIP_ELIDED)
    return
  if not array:
    report.skip("A", SKIP_EMPTY)
    return
  if not all(is_entry(entry) for entry in array):
    report.skip("A", SKIP_MALFORMED)
    return

  totals = [entry for entry in array if entry["type"] == "total"]
  subtotals = [entry for entry in array if entry["type"] == "subtotal"]
  if len(totals) != 1 or not subtotals:
    report.skip("A", SKIP_SHAPE)
    return

  report.checked["A"] += 1

  # Summing as written presupposes the signed-amount convention. A
  # positive subtractive entry means the document subtracts discounts
  # instead, where a balanced sum does not imply the intended total.
  if any(
    entry["type"] in SUBTRACTIVE_TYPES and entry["amount"] > 0
    for entry in array
  ):
    report.fail(
      file,
      line,
      location,
      "invariant (A): subtractive entry is positive, so the amounts are"
      " not signed",
      entry_rows(array),
    )
    return

  declared = totals[0]["amount"]
  computed = sum(entry["amount"] for entry in array if entry["type"] != "total")
  if computed == declared:
    return

  report.fail(
    file,
    line,
    location,
    'invariant (A): entries do not sum to the "total" entry',
    entry_rows(array),
    (('sum of type != "total"', computed), ('declared "total"', declared)),
  )


def check_sub_line_sums(
  file: str,
  line: int,
  location: str,
  array: list,
  report: Report,
) -> None:
  """Invariant (B). Each entry's `lines` MUST sum to its amount."""
  for index, entry in enumerate(array):
    if not isinstance(entry, dict):
      continue
    lines = entry.get("lines")
    if not isinstance(lines, list):
      continue
    if contains_elision(entry):
      report.skip("B", SKIP_ELIDED)
      continue
    if not is_amount(entry.get("amount")) or not all(
      isinstance(sub, dict) and is_amount(sub.get("amount")) for sub in lines
    ):
      report.skip("B", SKIP_MALFORMED)
      continue
    if not lines:
      report.skip("B", SKIP_EMPTY)
      continue

    report.checked["B"] += 1
    declared = entry["amount"]
    computed = sum(sub["amount"] for sub in lines)
    if computed == declared:
      continue

    report.fail(
      file,
      line,
      f"{location}[{index}].lines",
      "invariant (B): sub-lines do not sum to the parent entry",
      line_rows(lines),
      (
        ("sum of lines[].amount", computed),
        (f'parent "{entry.get("type", "?")}" amount', declared),
      ),
    )


# -----------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------


def check_file(path: Path, report: Report) -> None:
  """Check every totals array in every example block of one doc."""
  for block in examples.extract_blocks(path):
    if not block["content"].strip():
      continue
    try:
      tree = examples.parse_example(block["content"])
    except json.JSONDecodeError:
      report.unparsed += 1
      continue
    for location, array in block_totals_arrays(block, tree):
      check_breakdown_sum(block["file"], block["line"], location, array, report)
      check_sub_line_sums(block["file"], block["line"], location, array, report)


def main() -> int:
  """Check totals arithmetic across the spec docs."""
  parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=(argparse.RawDescriptionHelpFormatter),
  )
  parser.add_argument(
    "--docs",
    type=Path,
    default=None,
    help="Path to docs/ directory (default: docs/)",
  )
  parser.add_argument(
    "--file",
    type=Path,
    nargs="+",
    default=None,
    help="Check one or more files instead of the full corpus.",
  )
  args = parser.parse_args()

  repo_root = Path(__file__).parent.parent
  docs_dir = args.docs or repo_root / "docs"
  md_files = args.file if args.file else sorted(docs_dir.rglob("*.md"))

  report = Report()
  for md_file in md_files:
    check_file(md_file, report)

  for failure in report.failures:
    print(failure)
  if report.failures:
    print()
  print(report.summary())

  return 1 if report.failures else 0


if __name__ == "__main__":
  sys.exit(main())
