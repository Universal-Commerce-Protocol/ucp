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
"""Check two stay-targeted schedules inside a complete Booking response.

Run: python3 scripts/test_cancellation_booking.py (ucp-schema on PATH).
The synthetic wire response is adapted from lodging_booking_response.json;
only its `booking` member is protocol data. Expectations are test metadata.

This integration check resolves only a single explicit $.stays[N] target per
policy. It is not a JSONPath engine or a policy-precedence implementation.
Expected stay IDs, dates, anchors, and outcomes are independently supplied;
date-only stay_dates never generate an anchor. The existing schedule oracle
selects outcomes. No amounts, refundability classifications, or aggregate
penalties are calculated, and hypothetical evaluations do not refresh the
response's Business-supplied refundability snapshot or its expired quote.
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

from test_cancellation_schedule import ROOT, SCHEMA, elapsed, evaluate, instant

FIXTURES = ROOT / "scripts/fixtures/lodging_cancellation_booking.json"
TARGET = re.compile(r"\$\.stays\[(0|[1-9][0-9]*)\]")


def require(condition: bool, message: str) -> None:
  """Reject an invariant without relying on removable assertions."""
  if not condition:
    raise ValueError(message)


@cache
def booking_schema_valid(serialized: str) -> bool:
  """Validate the entire Booking through the cancellation extension."""
  with tempfile.TemporaryDirectory(prefix="ucp-cancellation-booking-") as temp:
    payload = Path(temp) / "booking.json"
    payload.write_text(serialized, encoding="utf-8")
    result = subprocess.run(
      [
        "ucp-schema",
        "validate",
        str(payload),
        "--schema",
        str(SCHEMA),
        "--def",
        "dev.ucp.lodging.booking",
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


def target_stay(booking: dict, policy: dict) -> dict:
  """Resolve the fixture's explicit index against the actual Booking node."""
  targets = policy["applies_to"]
  require(len(targets) == 1, "fixture requires one explicit stay target")
  match = TARGET.fullmatch(targets[0])
  require(match is not None, "unsupported fixture target")
  index = int(match.group(1))
  require(index < len(booking["stays"]), "stay target is out of range")
  return booking["stays"][index]


def check_evaluation(schedule: dict, at: str, expected: dict) -> None:
  """Compare the existing oracle's selection and exact declared outcome."""
  # The enclosing Booking has already passed the extension's full schema.
  result = evaluate(schedule, at, True)
  require(result == expected["result"], "schedule selection mismatch")
  require(result["status"] == "selected", "fixture requires selected outcome")
  selected = {"schedule": schedule}
  for part in result["pointer"].split("/")[1:]:
    selected = (
      selected[int(part)] if isinstance(selected, list) else selected[part]
    )
  require(selected == expected["outcome"], "declared outcome mismatch")


def check_fixture(bundle: dict) -> None:
  """Verify Booking shape, actual targeting, and independent boundaries."""
  require(
    type(bundle["format_version"]) is int and bundle["format_version"] == 1,
    "unsupported fixture format",
  )
  booking = bundle["booking"]
  require(
    booking_schema_valid(json.dumps(booking, sort_keys=True)),
    "full Booking fails cancellation-extension schema",
  )
  stays, policies = booking["stays"], booking["policies"]
  require(
    len(stays) == len(policies) == 2, "fixture requires two stays/policies"
  )
  require("stay_dates" not in booking, "fixture has no global stay dates")
  require(booking["currency"] == "USD", "fixture amounts are supplied in USD")
  require(
    len({stay["id"] for stay in stays}) == 2,
    "fixture requires distinct stay IDs",
  )
  require(
    len({stay["stay_dates"]["start_date"] for stay in stays}) == 2,
    "fixture requires different arrival dates",
  )
  generated = instant(bundle["response_generated_at"])
  require(generated < instant(booking["expires_at"]), "quote already expired")
  expectations = bundle["expectations"]
  require(
    [item["policy_index"] for item in expectations] == [0, 1],
    "expected coverage must include both policies exactly once",
  )
  for expected in expectations:
    policy = policies[expected["policy_index"]]
    require(
      policy["type"] == "dev.ucp.lodging.policy.cancellation",
      "fixture requires cancellation policies",
    )
    stay = target_stay(booking, policy)
    require(
      stay["id"] == expected["stay_id"], "target resolves to wrong stay ID"
    )
    require(stay["stay_dates"] == expected["stay_dates"], "stay dates mismatch")
    schedule = policy["schedule"]
    require(
      schedule["anchor"] == expected["anchor"], "explicit anchor mismatch"
    )
    require(len(schedule["tiers"]) == 1, "fixture requires one cutoff per stay")
    cutoff = instant(schedule["anchor"]) - elapsed(
      schedule["tiers"][0]["until"]
    )
    require(cutoff == instant(expected["cutoff"]), "cutoff mismatch")
    require(generated < cutoff, "fixture snapshot must precede both cutoffs")
    # Preserve the supplied snapshot; never derive a classification from terms.
    require(
      policy["refundability"] == expected["refundability_snapshot"],
      "Business-supplied snapshot changed",
    )
    cases = expected["evaluations"]
    require(len(cases) == 2, "fixture requires before/equal boundary cases")
    require(
      instant(cases[0]["at"]) == cutoff - 1,
      "before case not one second before",
    )
    require(instant(cases[1]["at"]) == cutoff, "equal case not at exact cutoff")
    for case in cases:
      check_evaluation(schedule, case["at"], case)
  require(
    len({policy["schedule"]["anchor"] for policy in policies}) == 2,
    "fixture requires independent anchors",
  )
  mixed = bundle["mixed_evaluation"]
  require(
    [item["policy_index"] for item in mixed["expected"]] == [0, 1],
    "mixed evaluation must cover both policies",
  )
  require(
    instant(expectations[0]["cutoff"])
    <= instant(mixed["at"])
    < instant(expectations[1]["cutoff"]),
    "mixed instant must lie between the independent cutoffs",
  )
  for expected in mixed["expected"]:
    policy = policies[expected["policy_index"]]
    stay = target_stay(booking, policy)
    require(stay["id"] == expected["stay_id"], "mixed target ID mismatch")
    check_evaluation(policy["schedule"], mixed["at"], expected)
  require(
    mixed["expected"][0]["outcome"]["kind"] == "fixed_fee"
    and mixed["expected"][1]["outcome"]
    == {"kind": "percentage", "buyer_bps": 10000},
    "mixed evaluation must retain separate penalty and free terms",
  )


def validate(bundle: dict) -> list[str]:
  """Return fixture failures without changing the input."""
  try:
    check_fixture(bundle)
  except (KeyError, IndexError, TypeError, ValueError, AttributeError) as error:
    return [str(error)]
  return []


def mutation_checks(bundle: dict) -> tuple[list[str], int]:
  """Reject dangling paths, wrong nodes/anchors, and incomplete wire shapes."""
  booking = bundle["booking"]
  mutations = []
  for index in range(2):
    for name, target in (
      ("old_room_rates_path", f"$.room_rates[{index}]"),
      ("out_of_range", "$.stays[2]"),
      ("swapped_target", f"$.stays[{1 - index}]"),
      ("leading_zero_index", f"$.stays[0{index}]"),
    ):
      mutant = copy.deepcopy(bundle)
      mutant["booking"]["policies"][index]["applies_to"] = [target]
      mutations.append((f"{name}[{index}]", mutant, False))
    mutant = copy.deepcopy(bundle)
    del mutant["booking"]["stays"][index]["stay_dates"]
    mutations.append((f"missing_stay_dates[{index}]", mutant, True))
    mutant = copy.deepcopy(bundle)
    mutant["booking"]["policies"][index]["schedule"]["anchor"] = booking[
      "policies"
    ][1 - index]["schedule"]["anchor"]
    mutations.append((f"shared_anchor[{index}]", mutant, False))
  for field in ("applies_to", "schedule"):
    mutant = copy.deepcopy(bundle)
    for index in range(2):
      mutant["booking"]["policies"][index][field] = copy.deepcopy(
        booking["policies"][1 - index][field]
      )
    mutations.append((f"swapped_{field}", mutant, False))
  mutant = copy.deepcopy(bundle)
  for index in range(2):
    mutant["booking"]["policies"][index]["schedule"]["anchor"] = booking[
      "policies"
    ][1 - index]["schedule"]["anchor"]
  mutations.append(("swapped_anchors", mutant, False))
  mutant = copy.deepcopy(bundle)
  mutant["booking"]["stays"].reverse()
  mutations.append(("reordered_stays_with_stale_targets", mutant, False))
  mutant = copy.deepcopy(bundle)
  del mutant["booking"]["policies"][0]["schedule"]["anchor"]
  mutations.append(("missing_explicit_anchor", mutant, True))
  mutant = copy.deepcopy(bundle)
  mutant["booking"]["policies"][0]["schedule"]["tiers"][0]["outcome"][
    "buyer_bps"
  ] = 10001
  mutations.append(("invalid_nested_cancellation_outcome", mutant, True))
  failures = []
  for name, mutant, schema_rejects in mutations:
    valid = booking_schema_valid(json.dumps(mutant["booking"], sort_keys=True))
    if valid != (not schema_rejects):
      failures.append(f"{name}: unexpected full Booking schema result {valid}")
    if not validate(mutant):
      failures.append(f"mutation was not rejected: {name}")
  return failures, len(mutations)


def main() -> int:
  """Run the complete response, selection checks, and regression mutations."""
  if shutil.which("ucp-schema") is None:
    print("ERROR: ucp-schema is required; no checks were run.")
    return 1
  try:
    bundle = json.loads(FIXTURES.read_text(encoding="utf-8"))
    failures = validate(bundle)
    if failures:
      for failure in failures:
        print(f"FAIL: {failure}")
      print("Mutation checks not run because fixture validation failed.")
      return 1
    failures, mutation_count = mutation_checks(bundle)
  except (OSError, ValueError, RuntimeError) as error:
    print(f"ERROR: {error}")
    return 1
  for failure in failures:
    print(f"FAIL: {failure}")
  print(
    "1 full Booking, 2 targeted stays, 4 boundary selections, "
    f"2 simultaneous selections, {mutation_count} mutation checks, "
    f"{len(failures)} failures"
  )
  return int(bool(failures))


if __name__ == "__main__":
  sys.exit(main())
