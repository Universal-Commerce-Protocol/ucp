#!/usr/bin/env python3
"""Contract conformance tests for validate_totals.py.

Each test asserts one claim about the two arithmetic invariants
documented in validate_totals.py's module docstring, which in turn
quote docs/specification/shopping/checkout/index.md ("Total", anchor
#totals). Tests
are deliberately one-claim-each so a failure points at exactly which
rule broke.

The doc corpus is the integration test — every `totals` array across
the spec docs is checked on each CI run, which proves conformant
examples pass. This file is the unit layer: it proves the invariants
are *enforced*, that the applicability filters skip what they must,
and that a skip is never mistaken for a pass.

Run: python3 scripts/test_validate_totals.py
Exit: 0 on all pass, 1 on any failure.

No external dependencies. Nothing here needs the `ucp-schema` binary:
validate_totals.py performs no schema resolution.
"""

import json
import sys
import tempfile
from pathlib import Path

# Import the validator module under test
sys.path.insert(0, str(Path(__file__).parent))
import validate_totals as t  # noqa: E402

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
    suffix = f" \u2014 {detail}" if detail and not ok else ""
    print(f"  {status}  {name}{suffix}")
  print(f"\n{passed} passed, {len(failed)} failed")
  return 0 if not failed else 1


# -----------------------------------------------------------
# Fixtures
# -----------------------------------------------------------


def _run(totals_json: str) -> t.Report:
  """Check one displayed `totals` array through the full pipeline.

  Wraps the array in a checkout body so the run exercises block
  extraction, Layer 1\u21922 reduction and the nested-array walk \u2014 not just
  the invariant functions in isolation.
  """
  md = (
    "<!-- ucp:example schema=shopping/checkout op=read -->\n"
    "```json\n"
    "{\n"
    '  "id": "chk_1",\n'
    f'  "totals": {totals_json}\n'
    "}\n"
    "```\n"
  )
  with tempfile.NamedTemporaryFile(
    mode="w",
    suffix=".md",
    delete=False,
    encoding="utf-8",
  ) as f:
    f.write(md)
    path = Path(f.name)
  report = t.Report()
  t.check_file(path, report)
  return report


def _entries(*pairs) -> str:
  """Render (type, amount) pairs as a displayed totals array."""
  return json.dumps(
    [{"type": ty, "display_text": ty.title(), "amount": n} for ty, n in pairs]
  )


# -----------------------------------------------------------
# Invariant (A): breakdown sum
# -----------------------------------------------------------


def test_breakdown_sum_passes() -> None:
  """A correct breakdown is checked and passes."""
  report = _run(
    _entries(
      ("subtotal", 5750),
      ("fulfillment", 899),
      ("tax", 797),
      ("total", 7446),
    )
  )
  _check(
    "breakdown_correct_passes",
    report.checked["A"] == 1 and not report.failures,
    f"checked={report.checked} failures={report.failures}",
  )


def test_breakdown_sum_fails() -> None:
  """A breakdown whose entries do not sum to `total` fails."""
  report = _run(
    _entries(
      ("subtotal", 5750),
      ("fulfillment", 899),
      ("tax", 797),
      ("total", 7000),
    )
  )
  _check(
    "breakdown_mismatch_fails",
    report.checked["A"] == 1 and len(report.failures) == 1,
    f"checked={report.checked} failures={report.failures}",
  )
  message = report.failures[0] if report.failures else ""
  _check(
    "breakdown_failure_reports_arithmetic",
    "7446" in message and "7000" in message and "+446" in message,
    f"got {message!r}",
  )
  _check(
    "breakdown_failure_reports_entries",
    "fulfillment" in message and "Subtotal" in message,
    f"got {message!r}",
  )


def test_repeated_types_summed() -> None:
  """Repeating types (e.g. two `tax` lines) are each summed.

  The spec permits every type except `subtotal` and `total` to repeat,
  so a correct implementation must add both, not overwrite one with the
  other.
  """
  report = _run(
    _entries(
      ("subtotal", 4999),
      ("tax", 300),
      ("tax", 144),
      ("total", 5443),
    )
  )
  _check(
    "repeated_types_summed",
    report.checked["A"] == 1 and not report.failures,
    f"failures={report.failures}",
  )

  # And the second occurrence is not silently dropped: omitting it from
  # the declared total must fail.
  report = _run(
    _entries(
      ("subtotal", 4999),
      ("tax", 300),
      ("tax", 144),
      ("total", 5299),
    )
  )
  _check(
    "repeated_types_not_deduplicated",
    len(report.failures) == 1,
    f"failures={report.failures}",
  )


def test_negative_entries_summed() -> None:
  """Negative (subtractive) entries reduce the sum by their amount."""
  report = _run(
    _entries(
      ("subtotal", 10000),
      ("discount", -1500),
      ("tax", 680),
      ("account_credit", -2500),
      ("total", 6680),
    )
  )
  _check(
    "negative_entries_summed",
    report.checked["A"] == 1 and not report.failures,
    f"failures={report.failures}",
  )

  # Treating a negative entry as additive would total 11180 \u2014 assert the
  # sign is honoured by failing that reading.
  report = _run(
    _entries(
      ("subtotal", 10000),
      ("discount", -1500),
      ("tax", 680),
      ("account_credit", -2500),
      ("total", 11180),
    )
  )
  _check(
    "negative_entries_not_added_as_positive",
    len(report.failures) == 1,
    f"failures={report.failures}",
  )


def test_offset_not_netted_breakdown() -> None:
  """A charge plus its offsetting discount sums to the declared total.

  This is the shape the spec prescribes for a free-shipping discount:
  the full `fulfillment` charge and a separate negative `discount`. It
  must pass \u2014 the guard locks in the arithmetic, and MUST NOT treat a
  discount alongside a shipping charge as suspicious on its own.
  """
  report = _run(
    _entries(
      ("subtotal", 4000),
      ("items_discount", -800),
      ("fulfillment", 599),
      ("discount", -599),
      ("total", 3200),
    )
  )
  _check(
    "offset_charge_and_discount_passes",
    report.checked["A"] == 1 and not report.failures,
    f"failures={report.failures}",
  )

  # Legitimately-free shipping \u2014 `fulfillment` at 0 and no offsetting
  # entry \u2014 must also pass. Flagging it would be a false positive.
  report = _run(
    _entries(
      ("subtotal", 4000),
      ("fulfillment", 0),
      ("total", 4000),
    )
  )
  _check(
    "free_fulfillment_without_discount_passes",
    report.checked["A"] == 1 and not report.failures,
    f"failures={report.failures}",
  )


def test_signed_amount_convention_asserted() -> None:
  """A positive subtractive entry fails rather than being summed.

  Summing amounts as written only yields the intended total under the
  signed-amount convention. An earlier snapshot of the spec defined
  `total` as `subtotal - discount + ...`, where discounts are positive
  and subtracted — under that reading a breakdown can sum as written
  and still be wrong. Honouring both conventions would pass broken
  arithmetic in either, so the convention is asserted, not inferred.
  """
  # 4000 + 599 == 4599, so a convention-blind check would pass this.
  report = _run(
    _entries(
      ("subtotal", 4000),
      ("discount", 599),
      ("total", 4599),
    )
  )
  _check(
    "positive_discount_fails",
    report.checked["A"] == 1 and len(report.failures) == 1,
    f"checked={report.checked} failures={report.failures}",
  )
  message = report.failures[0] if report.failures else ""
  _check(
    "positive_discount_names_the_convention",
    "not signed" in message,
    f"got {message!r}",
  )

  # items_discount too.
  report = _run(
    _entries(
      ("subtotal", 4000),
      ("items_discount", 800),
      ("total", 4800),
    )
  )
  _check(
    "positive_items_discount_fails",
    len(report.failures) == 1,
    f"failures={report.failures}",
  )

  # A zero discount is not positive and carries no convention signal.
  report = _run(
    _entries(
      ("subtotal", 4000),
      ("discount", 0),
      ("total", 4000),
    )
  )
  _check(
    "zero_discount_still_checked",
    report.checked["A"] == 1 and not report.failures,
    f"checked={report.checked} failures={report.failures}",
  )


# -----------------------------------------------------------
# Invariant (A): applicability filters
# -----------------------------------------------------------


def test_lone_total_skipped() -> None:
  """A lone `total` with no `subtotal` is skipped, not checked.

  Fulfillment options and order adjustments are typed
  `array<total.json>`, which carries no subtotal/total pairing rule.
  Their single-entry `totals` is legitimate and summing it against
  itself would be meaningless.
  """
  report = _run('[{"type": "total", "amount": 500}]')
  _check(
    "lone_total_skipped",
    report.checked["A"] == 0
    and report.skips["A"].get(t.SKIP_SHAPE) == 1
    and not report.failures,
    f"checked={report.checked} skips={report.skips}",
  )

  # Two `total` entries is also not the totals.json shape.
  report = _run(
    '[{"type": "total", "amount": 500}, {"type": "total", "amount": 600}]'
  )
  _check(
    "duplicate_total_skipped",
    report.checked["A"] == 0 and report.skips["A"].get(t.SKIP_SHAPE) == 1,
    f"checked={report.checked} skips={report.skips}",
  )

  # A subtotal with no total is likewise unpaired.
  report = _run('[{"type": "subtotal", "amount": 500}]')
  _check(
    "subtotal_without_total_skipped",
    report.checked["A"] == 0 and report.skips["A"].get(t.SKIP_SHAPE) == 1,
    f"checked={report.checked} skips={report.skips}",
  )


def test_elided_array_skipped() -> None:
  """An array carrying elision markers is skipped, not checked."""
  report = _run("[ ... ]")
  _check(
    "bare_ellipsis_array_skipped",
    report.checked["A"] == 0
    and report.skips["A"].get(t.SKIP_ELIDED) == 1
    and not report.failures,
    f"checked={report.checked} skips={report.skips}",
  )

  # Partial elision is the dangerous case: stripping the sentinel would
  # leave a subtotal/total pair whose sum is wrong by the elided entries.
  report = _run(
    '[{"type": "subtotal", "amount": 5000}, "...",'
    ' {"type": "total", "amount": 5900}]'
  )
  _check(
    "partially_elided_array_skipped",
    report.checked["A"] == 0
    and report.skips["A"].get(t.SKIP_ELIDED) == 1
    and not report.failures,
    f"checked={report.checked} skips={report.skips} {report.failures}",
  )

  # An elided value nested inside an entry counts too.
  report = _run(
    '[{"type": "subtotal", "amount": 5000, "lines": [ ... ]},'
    ' {"type": "total", "amount": 5000}]'
  )
  _check(
    "entry_with_elided_member_skipped",
    report.checked["A"] == 0 and report.skips["A"].get(t.SKIP_ELIDED) == 1,
    f"checked={report.checked} skips={report.skips}",
  )


def test_non_integer_amount_skipped() -> None:
  """Entries without a string type and integer amount are skipped."""
  report = _run(
    '[{"type": "subtotal", "amount": "5000"},'
    ' {"type": "total", "amount": 5000}]'
  )
  _check(
    "string_amount_skipped",
    report.checked["A"] == 0 and report.skips["A"].get(t.SKIP_MALFORMED) == 1,
    f"checked={report.checked} skips={report.skips}",
  )

  report = _run(
    '[{"type": "subtotal", "amount": 50.5}, {"type": "total", "amount": 50.5}]'
  )
  _check(
    "float_amount_skipped",
    report.checked["A"] == 0 and report.skips["A"].get(t.SKIP_MALFORMED) == 1,
    f"checked={report.checked} skips={report.skips}",
  )

  report = _run('[{"amount": 5000}, {"type": "total", "amount": 5000}]')
  _check(
    "entry_without_type_skipped",
    report.checked["A"] == 0 and report.skips["A"].get(t.SKIP_MALFORMED) == 1,
    f"checked={report.checked} skips={report.skips}",
  )


# -----------------------------------------------------------
# Invariant (B): sub-line sum
# -----------------------------------------------------------


def test_sub_lines_pass() -> None:
  """A correct `lines` breakdown is checked and passes."""
  report = _run(
    json.dumps(
      [
        {"type": "subtotal", "amount": 4999},
        {
          "type": "fee",
          "display_text": "Fees",
          "amount": 549,
          "lines": [
            {"display_text": "Service Fee", "amount": 399},
            {"display_text": "Recycling Fee", "amount": 150},
          ],
        },
        {"type": "total", "amount": 5548},
      ]
    )
  )
  _check(
    "sub_lines_correct_passes",
    report.checked["A"] == 1
    and report.checked["B"] == 1
    and not report.failures,
    f"checked={report.checked} failures={report.failures}",
  )


def test_sub_lines_fail() -> None:
  """Sub-lines that do not sum to their parent's amount fail (B)."""
  report = _run(
    json.dumps(
      [
        {"type": "subtotal", "amount": 4999},
        {
          "type": "fee",
          "display_text": "Fees",
          "amount": 549,
          "lines": [
            {"display_text": "Service Fee", "amount": 399},
            {"display_text": "Recycling Fee", "amount": 100},
          ],
        },
        {"type": "total", "amount": 5548},
      ]
    )
  )
  _check(
    "sub_lines_mismatch_fails",
    report.checked["B"] == 1 and len(report.failures) == 1,
    f"checked={report.checked} failures={report.failures}",
  )
  message = report.failures[0] if report.failures else ""
  _check(
    "sub_line_failure_reports_arithmetic",
    "invariant (B)" in message
    and "499" in message
    and "549" in message
    and "-50" in message,
    f"got {message!r}",
  )
  _check(
    "sub_line_failure_locates_entry",
    "$.totals[1].lines" in message,
    f"got {message!r}",
  )


def test_sub_lines_checked_independently_of_shape() -> None:
  """(B) applies per entry, so it runs where (A) does not.

  A lone-`total` array is skipped by (A)'s applicability filter, but an
  entry in it that carries `lines` still has to add up.
  """
  report = _run(
    json.dumps(
      [
        {
          "type": "total",
          "display_text": "Total",
          "amount": 500,
          "lines": [{"display_text": "Base", "amount": 400}],
        }
      ]
    )
  )
  _check(
    "sub_lines_checked_when_A_skipped",
    report.checked["A"] == 0
    and report.checked["B"] == 1
    and len(report.failures) == 1,
    f"checked={report.checked} failures={report.failures}",
  )


# -----------------------------------------------------------
# Discovery: nesting depth, bare arrays, unparsable blocks
# -----------------------------------------------------------


def _write_md(content: str) -> Path:
  """Write a temporary markdown file."""
  with tempfile.NamedTemporaryFile(
    mode="w",
    suffix=".md",
    delete=False,
    encoding="utf-8",
  ) as f:
    f.write(content)
    return Path(f.name)


def test_nested_arrays_found() -> None:
  """Every `totals` array is found at any nesting depth."""
  tree = {
    "result": {
      "structuredContent": {
        "totals": [],
        "line_items": [{"totals": []}, {"totals": []}],
      }
    }
  }
  found = dict(t.find_totals_arrays(tree))
  _check(
    "nested_totals_all_found",
    set(found)
    == {
      "$.result.structuredContent.totals",
      "$.result.structuredContent.line_items[0].totals",
      "$.result.structuredContent.line_items[1].totals",
    },
    f"got {sorted(found)}",
  )


def test_bare_array_block_found() -> None:
  """A bare array bound with `target=$.totals` is checked.

  The canonical Total-section examples display the array itself rather
  than a checkout body, so the annotation is what identifies them.
  """
  md = (
    "<!-- ucp:example schema=shopping/checkout target=$.totals op=read -->\n"
    "```json\n"
    '[{"type": "subtotal", "amount": 100},'
    ' {"type": "total", "amount": 150}]\n'
    "```\n"
  )
  report = t.Report()
  t.check_file(_write_md(md), report)
  _check(
    "bare_array_with_target_checked",
    report.checked["A"] == 1 and len(report.failures) == 1,
    f"checked={report.checked} failures={report.failures}",
  )

  # A bare array bound elsewhere is not a totals breakdown.
  md = (
    "<!-- ucp:example schema=shopping/checkout target=$.messages op=read -->\n"
    "```json\n"
    '[{"type": "subtotal", "amount": 100},'
    ' {"type": "total", "amount": 150}]\n'
    "```\n"
  )
  report = t.Report()
  t.check_file(_write_md(md), report)
  _check(
    "bare_array_other_target_ignored",
    report.checked["A"] == 0 and not report.failures,
    f"checked={report.checked} failures={report.failures}",
  )


def test_authoring_conveniences_reduced() -> None:
  """Comments, templates and HTTP envelopes reduce before the check.

  The reduction is validate_examples.py's contract; this asserts it is
  reused rather than re-implemented, so an example is not skipped for
  using a convenience the docs permit.
  """
  md = (
    "<!-- ucp:example schema=shopping/checkout op=read -->\n"
    "```json\n"
    "HTTP/1.1 200 OK\n"
    "Content-Type: application/json\n"
    "\n"
    "{\n"
    '  "ucp": { "version": "{{ ucp_version }}" },\n'
    '  "totals": [\n'
    '    { "type": "subtotal", "amount": 100 }, // the goods\n'
    '    { "type": "total", "amount": 150 }\n'
    "  ]\n"
    "}\n"
    "```\n"
  )
  report = t.Report()
  t.check_file(_write_md(md), report)
  _check(
    "authoring_conveniences_reduced",
    report.checked["A"] == 1 and len(report.failures) == 1,
    f"checked={report.checked} failures={report.failures}",
  )


def test_unparsable_block_skipped_silently() -> None:
  """A block that will not parse is counted, never failed.

  validate_examples.py already fails those blocks. Reporting them here
  too would make one defect look like two.
  """
  md = "<!-- ucp:example schema=x -->\n```json\n{ not json\n```\n"
  report = t.Report()
  t.check_file(_write_md(md), report)
  _check(
    "unparsable_block_skipped_silently",
    report.unparsed == 1 and not report.failures,
    f"unparsed={report.unparsed} failures={report.failures}",
  )


def test_exit_code_and_summary() -> None:
  """The summary carries the counts and a failure sets exit status 1."""
  report = _run(
    _entries(("subtotal", 100), ("total", 150)),
  )
  summary = report.summary()
  _check(
    "summary_reports_counts",
    "1 checked, 1 failed" in summary and "(A) breakdown sum: 1" in summary,
    f"got {summary!r}",
  )

  report = t.Report()
  report.skip("A", t.SKIP_SHAPE)
  _check(
    "summary_reports_skip_reasons",
    "0 checked, 0 failed, 1 skipped" in report.summary()
    and t.SKIP_SHAPE in report.summary(),
    f"got {report.summary()!r}",
  )


# -----------------------------------------------------------
# Main
# -----------------------------------------------------------


def main() -> int:
  """Run all contract tests and report. Exit 0 on pass, 1 on failure."""
  print("Running validate_totals contract tests...\n")
  test_breakdown_sum_passes()
  test_breakdown_sum_fails()
  test_repeated_types_summed()
  test_negative_entries_summed()
  test_offset_not_netted_breakdown()
  test_signed_amount_convention_asserted()
  test_lone_total_skipped()
  test_elided_array_skipped()
  test_non_integer_amount_skipped()
  test_sub_lines_pass()
  test_sub_lines_fail()
  test_sub_lines_checked_independently_of_shape()
  test_nested_arrays_found()
  test_bare_array_block_found()
  test_authoring_conveniences_reduced()
  test_unparsable_block_skipped_silently()
  test_exit_code_and_summary()
  return _report()


if __name__ == "__main__":
  sys.exit(main())
