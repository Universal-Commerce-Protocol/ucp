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
"""Validate synthetic cancellation lab inputs and held-out expected answers.

Run: python3 scripts/test_cancellation_lab.py (requires ucp-schema on PATH).
This checks fixture consistency, not agent performance or legal prose. Known
semantic conflicts remain exploratory probes, not automatic detection claims.
Money checks use only Business-resolved fees or an explicitly full refund.
"""

import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

from test_cancellation_schedule import (
  FIXTURES as SOURCE_FIXTURES,
  ROOT,
  SCHEMA,
  check_local_policy_examples,
  evaluate,
  instant,
  schema_valid,
)

FIXTURES = ROOT / "scripts/fixtures/lodging_cancellation_lab.json"
HANDLING = {
  "valid": "terms",
  "invalid_schedule": "prose_fallback",
  "description_conflict": "conflict_probe",
}


def require(condition: bool, message: str) -> None:
  """Reject a fixture invariant without relying on removable assertions."""
  if not condition:
    raise ValueError(message)


@cache
def valid_json(serialized: str, definition: str) -> bool:
  """Validate a policy or schedule, caching repeated mutation-test inputs."""
  if definition == "cancellation_schedule":
    return schema_valid(json.loads(serialized))
  with tempfile.TemporaryDirectory(prefix="ucp-cancellation-lab-") as temp:
    payload = Path(temp) / "policy.json"
    payload.write_text(serialized, encoding="utf-8")
    result = subprocess.run(
      [
        "ucp-schema",
        "validate",
        str(payload),
        "--schema",
        str(SCHEMA),
        "--def",
        definition,
        "--op",
        "read",
        "--response",
        "--json",
      ],
      capture_output=True,
      text=True,
      check=False,
    )
  if result.returncode not in {0, 1} or not result.stdout.strip():
    raise RuntimeError(result.stderr.strip() or "ucp-schema did not respond")
  output = json.loads(result.stdout)
  if type(output.get("valid")) is not bool:
    raise RuntimeError(f"Unexpected schema result: {output}")
  return output["valid"]


def valid(value: dict, definition: str = "cancellation_schedule") -> bool:
  """Validate a JSON value using the repository's source schema."""
  return valid_json(json.dumps(value, sort_keys=True), definition)


def selected(schedule: dict, result: dict) -> dict | None:
  """Resolve the oracle's test-only JSON Pointer, or return no outcome."""
  if result["status"] != "selected":
    return None
  value = {"schedule": schedule}
  for part in result["pointer"].split("/")[1:]:
    value = value[int(part)] if isinstance(value, list) else value[part]
  return value


def check_penalty(penalty: dict, outcome: dict, currency: str) -> None:
  """Forbid cash expectations without a resolved, unambiguous amount."""
  amount = None
  if outcome["kind"] == "fixed_fee":
    amount = outcome["penalty"]["amount"]
  elif outcome == {"kind": "percentage", "buyer_bps": 10000}:
    amount = 0
  if amount is not None:
    require(
      type(penalty.get("amount")) is int, "penalty amount must be integer"
    )
    require(
      penalty == {"status": "resolved", "amount": amount, "currency": currency},
      "resolved penalty differs from intended outcome or currency",
    )
  else:
    require(set(penalty) == {"status", "reason"}, "unresolved penalty has cash")
    require(penalty["status"] == "not_resolved", "symbolic terms need no cash")
    require(
      isinstance(penalty["reason"], str) and penalty["reason"].strip(),
      "unresolved penalty needs a reason",
    )


def check_fixture(fixture: dict, source: dict) -> None:
  """Check one envelope, its wire values, and every held-out expected result."""
  category = fixture["category"]
  require(category in HANDLING, "unknown category")
  require(type(fixture["schema_valid"]) is bool, "schema_valid must be boolean")
  policy, context = fixture["policy"], fixture["context"]
  require(
    set(policy) == {"type", "description", "refundability", "url", "schedule"},
    "policy must contain only the supplied protocol fields",
  )
  require(set(policy["description"]) == {"plain"}, "description must be plain")
  require(
    isinstance(policy["description"]["plain"], str)
    and policy["description"]["plain"].strip(),
    "empty policy prose",
  )
  require(
    isinstance(policy["url"], str)
    and re.fullmatch(
      r"https://example\.com/cancellation-terms#p[0-9]{2}", policy["url"]
    ),
    "policy URL must be opaque and reveal no fixture category or answer",
  )
  require(context["currency"] == "USD", "this fixture set uses USD only")
  require(
    type(context["stay_nights"]) is int and context["stay_nights"] > 0,
    "stay_nights must be a positive integer",
  )
  ZoneInfo(context["property_timezone"])
  schedule = policy["schedule"]
  prose_only = {
    key: value for key, value in policy.items() if key != "schedule"
  }
  require(
    valid(prose_only, "cancellation_item"), "prose-only policy fails schema"
  )
  wire_valid = valid(schedule)
  require(
    wire_valid == fixture["schema_valid"], "wire schema expectation mismatch"
  )
  require(
    valid(policy, "cancellation_item") == wire_valid,
    "policy and schedule schema results differ",
  )
  require(
    ("reference_schedule" in fixture) == (category != "valid"),
    "reference schedule belongs only to invalid/conflict fixtures",
  )
  reference = fixture.get("reference_schedule", schedule)
  require(valid(reference), "reference schedule fails schema")
  generated = instant(context["response_generated_at"])
  anchor = instant(reference["anchor"])
  require(
    instant(context["check_in"]) == anchor, "check-in differs from anchor"
  )
  require(generated < anchor, "response must precede check-in")
  snapshot = selected(
    reference, evaluate(reference, context["response_generated_at"], True)
  )
  classification = {
    10000: "refundable",
    0: "non_refundable",
  }.get(snapshot.get("buyer_bps") if snapshot else None)
  require(
    classification is not None and policy["refundability"] == classification,
    "snapshot classification mismatch or unsupported fixture snapshot",
  )
  if "local_policy_example" in fixture:
    example = next(
      (
        item
        for item in source["local_policy_examples"]
        if item["id"] == fixture["local_policy_example"]
      ),
      None,
    )
    require(example is not None, "unknown local-policy example")
    require(
      reference == source["schedules"][example["schedule"]]["value"],
      "reference differs from published local-policy example",
    )
    require(
      context["property_timezone"] == example["timezone"],
      "property timezone differs from local-policy example",
    )
  evaluations = fixture["evaluations"]
  require(
    isinstance(evaluations, list) and len(evaluations) >= 2,
    "each fixture needs multiple evaluation instants",
  )
  ids = set()
  divergent = False
  for case in evaluations:
    require(
      isinstance(case["id"], str) and case["id"] and case["id"] not in ids,
      "missing or duplicate evaluation id",
    )
    ids.add(case["id"])
    require(
      generated <= instant(case["at"]) < anchor, "evaluation outside scope"
    )
    expected = case["expected"]
    require(
      set(expected)
      == {
        "schedule_result",
        "selected_outcome",
        "intended_outcome",
        "penalty",
        "handling",
      },
      "expected fields mismatch",
    )
    result = evaluate(schedule, case["at"], wire_valid)
    require(
      result == expected["schedule_result"],
      f"{case['id']}: wire result mismatch",
    )
    require(
      selected(schedule, result) == expected["selected_outcome"],
      f"{case['id']}: selected outcome mismatch",
    )
    intended = selected(reference, evaluate(reference, case["at"], True))
    divergent |= intended != selected(schedule, result)
    require(
      intended is not None and intended == expected["intended_outcome"],
      f"{case['id']}: intended outcome mismatch",
    )
    require(
      expected["handling"] == HANDLING[category], "handling category mismatch"
    )
    require(
      (result["status"] == "unavailable") == (category == "invalid_schedule"),
      "invalid schedule must fall back; valid/conflict schedules must select",
    )
    check_penalty(expected["penalty"], intended, context["currency"])
  if category == "description_conflict":
    require(divergent, "conflict probe never differs from intended terms")


def validate(bundle: dict, source: dict) -> list[str]:
  """Return actionable failures; never modify the supplied fixture bundle."""
  if not isinstance(bundle, dict):
    return ["fixture bundle must be an object"]
  failures = []
  if (
    type(bundle.get("format_version")) is not int
    or bundle["format_version"] != 1
  ):
    failures.append("format_version must be 1")
  fixtures = bundle.get("fixtures", [])
  if not isinstance(fixtures, list) or len(fixtures) != 10:
    return failures + ["expected exactly ten fixtures"]
  ids = set()
  for number, fixture in enumerate(fixtures):
    try:
      name = fixture["id"]
      require(
        isinstance(name, str) and name and name not in ids,
        "missing or duplicate fixture id",
      )
      ids.add(name)
      check_fixture(fixture, source)
    except (
      KeyError,
      IndexError,
      TypeError,
      ValueError,
      AttributeError,
    ) as error:
      failures.append(f"fixture[{number}]: {error}")
  return failures


def mutation_checks(bundle: dict, source: dict) -> tuple[list[str], int]:
  """Ensure key expected-answer and context corruptions are rejected."""
  mutations = [
    (["fixtures", 1, "id"], bundle["fixtures"][0]["id"]),
    (["fixtures", 0, "context", "currency"], "EUR"),
    (["fixtures", 0, "context", "response_generated_at"], "not-a-time"),
    (["fixtures", 0, "policy", "refundability"], "unknown"),
    (["fixtures", 0, "policy", "url"], "https://example.com/invalid-schedule"),
    (["fixtures", 0, "evaluations", 0, "expected", "selected_outcome"], None),
    (
      ["fixtures", 0, "evaluations", 0, "expected", "penalty"],
      {"status": "resolved", "amount": 999, "currency": "USD"},
    ),
  ]
  cases = [
    (["fixtures", fi, "evaluations", ci, "expected"], fixture, case["expected"])
    for fi, fixture in enumerate(bundle["fixtures"])
    for ci, case in enumerate(fixture["evaluations"])
  ]
  path, _, _ = next(
    item
    for item in cases
    if item[2]["intended_outcome"]["kind"] == "unit_deduction"
  )
  mutations.append(
    (
      path + ["penalty"],
      {"status": "resolved", "amount": 15000, "currency": "USD"},
    )
  )
  path, _, expected = next(
    item
    for item in cases
    if item[1]["category"] == "description_conflict"
    and item[2]["selected_outcome"] != item[2]["intended_outcome"]
  )
  mutations.append((path + ["intended_outcome"], expected["selected_outcome"]))
  path, _, _ = next(
    item for item in cases if item[1]["category"] == "invalid_schedule"
  )
  mutations.append(
    (
      path + ["schedule_result"],
      {"status": "selected", "pointer": "/schedule/tiers/0/outcome"},
    )
  )
  failures = []
  for path, replacement in mutations:
    mutant = copy.deepcopy(bundle)
    target = mutant
    for part in path[:-1]:
      target = target[part]
    target[path[-1]] = replacement
    if not validate(mutant, source):
      failures.append(f"mutation was not rejected: {path}")
  return failures, len(mutations)


def main() -> int:
  """Run fixture validation and negative checks with a concise summary."""
  if shutil.which("ucp-schema") is None:
    print("ERROR: ucp-schema is required; no checks were run.")
    return 1
  try:
    bundle = json.loads(FIXTURES.read_text(encoding="utf-8"))
    source = json.loads(SOURCE_FIXTURES.read_text(encoding="utf-8"))
    failures = check_local_policy_examples(source) + validate(bundle, source)
    if failures:
      for failure in failures:
        print(f"FAIL: {failure}")
      print("Mutation checks not run because fixture validation failed.")
      return 1
    failures, mutation_count = mutation_checks(bundle, source)
  except (OSError, ValueError, RuntimeError) as error:
    print(f"ERROR: {error}")
    return 1
  for failure in failures:
    print(f"FAIL: {failure}")
  count = sum(len(item["evaluations"]) for item in bundle["fixtures"])
  print(
    f"{len(bundle['fixtures'])} lab fixtures, {count} evaluation cases, "
    f"{mutation_count} mutation checks, {len(failures)} failures"
  )
  return int(bool(failures))


if __name__ == "__main__":
  sys.exit(main())
