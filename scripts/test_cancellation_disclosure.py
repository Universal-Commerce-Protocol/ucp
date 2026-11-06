#!/usr/bin/env python3
# Copyright 2026 UCP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Guard exact-cutoff and conflict expectations in the frozen lab fixtures.

Run: python3 scripts/test_cancellation_disclosure.py (ucp-schema on PATH).
These deterministic regressions do not run language models, grade natural
language, or discover contradictions in prose. The conflict fixture supplies
its intended terms separately from the emitted schedule. Mechanical selection
of that schedule is not an authoritative disclosure of the intended terms.
No fixture, wire field, or production evaluation behavior is changed here.
"""

import copy
import json
import shutil
import sys
import unittest
from unittest.mock import patch

from test_cancellation_lab import (
  FIXTURES,
  SOURCE_FIXTURES,
  selected,
  valid,
  validate,
)
from test_cancellation_schedule import elapsed, evaluate, instant

FREE = {"kind": "percentage", "buyer_bps": 10000}
FEE = {"kind": "fixed_fee", "penalty": {"amount": 15000}}
AFTER_LAST = {
  "status": "selected",
  "pointer": "/schedule/after_last_tier",
}
FIRST_TIER = {
  "status": "selected",
  "pointer": "/schedule/tiers/0/outcome",
}
CONFLICT = "description_schedule_amount_conflict"


class DisclosureRegressionTests(unittest.TestCase):
  """Keep wire selection distinct from intended disclosure and its evidence."""

  @classmethod
  def setUpClass(cls) -> None:
    """Read the original lab package without editing its study inputs."""
    cls.bundle = json.loads(FIXTURES.read_text(encoding="utf-8"))
    cls.source = json.loads(SOURCE_FIXTURES.read_text(encoding="utf-8"))
    cls.fixtures = {item["id"]: item for item in cls.bundle["fixtures"]}

  def test_original_package_remains_valid(self) -> None:
    """Establish the baseline before testing deliberate corruptions."""
    self.assertEqual(validate(self.bundle, self.source), [])

  def check_boundary(self, name: str, cases: list[tuple[str, bool]]) -> None:
    """Check explicit instants without inferring boundaries from prose."""
    schedule = self.fixtures[name]["policy"]["schedule"]
    self.assertTrue(valid(schedule))
    for at, before in cases:
      with self.subTest(scenario=name, at=at):
        result = evaluate(schedule, at, True)
        self.assertEqual(result, FIRST_TIER if before else AFTER_LAST)
        self.assertEqual(selected(schedule, result), FREE if before else FEE)

  def test_phoenix_exclusive_boundary(self) -> None:
    """Equality and sub-second instants must not extend the free interval."""
    self.check_boundary(
      "phoenix_resolved_fee",
      [
        ("2026-10-15T00:59:59Z", True),
        ("2026-10-15T00:59:59.999999999Z", True),
        ("2026-10-15T01:00:00Z", False),
        ("2026-10-15T01:00:00.000000001Z", False),
        ("2026-10-15T01:00:01Z", False),
        ("2026-10-14T18:00:00-07:00", False),
      ],
    )

  def test_new_york_fall_exclusive_boundary(self) -> None:
    """Keep the resolved autumn cutoff, including its pre-transition offset."""
    self.check_boundary(
      "new_york_fall_resolved_fee",
      [
        ("2026-10-31T21:59:59Z", True),
        ("2026-10-31T21:59:59.999999999Z", True),
        ("2026-10-31T22:00:00Z", False),
        ("2026-10-31T22:00:00.000000001Z", False),
        ("2026-10-31T22:00:01Z", False),
        ("2026-10-31T18:00:00-04:00", False),
      ],
    )

  def test_conflict_selection_is_not_intended_amount(self) -> None:
    """Do not repair a conflicting schedule or conflate it with the key."""
    fixture = self.fixtures[CONFLICT]
    wire = fixture["policy"]["schedule"]
    reference = fixture["reference_schedule"]
    self.assertTrue(valid(wire))
    self.assertTrue(valid(reference))
    for case in fixture["evaluations"]:
      with self.subTest(at=case["at"]):
        actual = selected(wire, evaluate(wire, case["at"], True))
        intended = selected(reference, evaluate(reference, case["at"], True))
        expected = case["expected"]
        self.assertEqual(actual, expected["selected_outcome"])
        self.assertEqual(intended, expected["intended_outcome"])
        if case["id"] == "before_cutoff":
          # The schedules agree now, but diverge over the full timeline.
          self.assertEqual(actual, FREE)
          self.assertEqual(intended, FREE)
        else:
          self.assertEqual(
            actual, {"kind": "fixed_fee", "penalty": {"amount": 7500}}
          )
          self.assertEqual(intended, FEE)
          self.assertNotEqual(actual, intended)
          self.assertEqual(expected["penalty"]["amount"], 15000)
        self.assertEqual(expected["handling"], "conflict_probe")

  def test_inclusive_oracle_mutation_is_rejected(self) -> None:
    """The existing validator must catch an evaluator using <= at a cutoff."""

    def inclusive(schedule: dict | None, at: str, schema_valid: bool) -> dict:
      result = evaluate(schedule, at, schema_valid)
      if result["status"] == "selected" and schedule is not None:
        anchor = instant(schedule["anchor"])
        for index, tier in enumerate(schedule["tiers"]):
          if instant(at) == anchor - elapsed(tier["until"]):
            return {
              "status": "selected",
              "pointer": f"/schedule/tiers/{index}/outcome",
            }
      return result

    with patch("test_cancellation_lab.evaluate", side_effect=inclusive):
      failures = validate(self.bundle, self.source)
    for name in ("phoenix_resolved_fee", "new_york_fall_resolved_fee"):
      index = self.bundle["fixtures"].index(self.fixtures[name])
      with self.subTest(scenario=name):
        self.assertIn(
          f"fixture[{index}]: at_cutoff: wire result mismatch", failures
        )

  def test_free_at_cutoff_answer_mutation_is_rejected(self) -> None:
    """Changing every expected free-answer field cannot hide a boundary bug."""
    for name in ("phoenix_resolved_fee", "new_york_fall_resolved_fee"):
      mutant = copy.deepcopy(self.bundle)
      fixture = next(item for item in mutant["fixtures"] if item["id"] == name)
      case = next(
        item for item in fixture["evaluations"] if item["id"] == "at_cutoff"
      )
      case["expected"].update(
        {
          "schedule_result": FIRST_TIER,
          "selected_outcome": FREE,
          "intended_outcome": FREE,
          "penalty": {"status": "resolved", "amount": 0, "currency": "USD"},
        }
      )
      index = mutant["fixtures"].index(fixture)
      with self.subTest(scenario=name):
        self.assertIn(
          f"fixture[{index}]: at_cutoff: wire result mismatch",
          validate(mutant, self.source),
        )

  def test_wire_amount_as_intended_answer_mutation_is_rejected(self) -> None:
    """Selecting 7500 must not silently redefine the intended 15000 answer."""
    mutant = copy.deepcopy(self.bundle)
    fixture = next(
      item for item in mutant["fixtures"] if item["id"] == CONFLICT
    )
    case = next(
      item for item in fixture["evaluations"] if item["id"] == "at_cutoff"
    )
    expected = case["expected"]
    expected["intended_outcome"] = copy.deepcopy(expected["selected_outcome"])
    expected["penalty"]["amount"] = 7500
    index = mutant["fixtures"].index(fixture)
    self.assertIn(
      f"fixture[{index}]: at_cutoff: intended outcome mismatch",
      validate(mutant, self.source),
    )

  def test_conflict_as_unqualified_terms_mutation_is_rejected(self) -> None:
    """The fixture key must retain its conflict probe, not ordinary terms."""
    mutant = copy.deepcopy(self.bundle)
    fixture = next(
      item for item in mutant["fixtures"] if item["id"] == CONFLICT
    )
    case = next(
      item for item in fixture["evaluations"] if item["id"] == "at_cutoff"
    )
    case["expected"]["handling"] = "terms"
    index = mutant["fixtures"].index(fixture)
    self.assertIn(
      f"fixture[{index}]: handling category mismatch",
      validate(mutant, self.source),
    )


if __name__ == "__main__":
  if shutil.which("ucp-schema") is None:
    print("ERROR: ucp-schema is required; no checks were run.")
    sys.exit(1)
  unittest.main(verbosity=2)
