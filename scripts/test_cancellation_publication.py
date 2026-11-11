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
"""Check synthetic producer-publication examples, not legal prose parsing.

Run: python3 scripts/test_cancellation_publication.py (ucp-schema on PATH).
All source_terms, publication decisions, expected values and policy facts in
the bundle are TEST METADATA. They are not proposed wire fields. Test authors
explicitly supply the meaning and completeness of each synthetic source; this
runner neither discovers missing clauses nor certifies a real policy's fidelity.

The small publication adapter handles only these fully described examples. It
checks actual wire schema validity and calls the unchanged schedule oracle.
Source-side grace eligibility, local calendar cutoffs, and component-specific
percentages are calculated separately. A schema-valid candidate can still be
unsafe to publish. Omitted schedules must produce schedule_absent fallback,
not a machine-derived answer; prose may itself require Business clarification.
No cancellation execution, cash calculation or general rules engine is added.
"""

import copy
import json
import shutil
import sys
from datetime import timedelta
from zoneinfo import ZoneInfo

from test_cancellation_lab import require, selected, valid
from test_cancellation_schedule import (
  ROOT,
  elapsed,
  evaluate,
  instant,
  local_example_instant,
)

FIXTURES = ROOT / "scripts/fixtures/lodging_cancellation_publication.json"


def source_cutoffs(terms: dict) -> list:
  """Resolve only explicitly supplied elapsed or local-calendar test terms."""
  anchor = instant(terms["anchor"])
  if terms["timing"] == "elapsed":
    return [anchor - seconds for seconds in terms["before_seconds"]]
  if terms["timing"] == "calendar":
    zone = ZoneInfo(terms["timezone"])
    arrival = local_example_instant(terms["check_in_local"], zone)
    require(instant(arrival.isoformat()) == anchor, "local anchor differs")
    cutoffs = []
    for days in terms["before_calendar_days"]:
      day = arrival.date() - timedelta(days=days)
      local = f"{day.isoformat()}T{terms['cutoff_local_time']}"
      cutoffs.append(instant(local_example_instant(local, zone).isoformat()))
    return cutoffs
  raise ValueError("source cutoff is not authoritatively resolved")


def grace_eligible(terms: dict) -> bool | None:
  """Apply test-author choices: lead time >= threshold, elapsed seconds."""
  if "grace" not in terms:
    return False
  booking = terms["grace"]["booking_completed_at"]
  if booking is None:
    return None
  lead = instant(terms["anchor"]) - instant(booking)
  return lead >= terms["grace"]["minimum_lead_seconds"]


def authoritative_terms(terms: dict, at: str) -> dict:
  """Calculate the explicit synthetic contract, separately from wire tiers."""
  if terms["timing"] == "unconfirmed_date_only":
    return {"status": "unresolved", "reason": "cutoff_not_confirmed"}
  when = instant(at)
  eligible = grace_eligible(terms)
  if eligible is None:
    return {"status": "unresolved", "reason": "booking_instant_unknown"}
  if "grace" in terms:
    booking = instant(terms["grace"]["booking_completed_at"])
    require(when >= booking, "query precedes booking completion")
    # Strict upper boundary is chosen for these synthetic tests, not inferred
    # from the external policy whose public URL has not yet been supplied.
    if eligible and when < booking + terms["grace"]["within_seconds"]:
      return {"kind": "percentage", "buyer_bps": 10000}
  bps = terms["refund_bps"][-1]
  for cutoff, refund in zip(
    source_cutoffs(terms), terms["refund_bps"][:-1], strict=True
  ):
    if when < cutoff:
      bps = refund
      break
  if terms["percentage_scope"] == "room_only_with_refundable_fees":
    return {
      "kind": "component_percentages",
      "room_bps": bps,
      "cleaning_bps": 10000,
      "tax_bps": 10000,
    }
  require(terms["percentage_scope"] == "single_scope", "unknown scope")
  return {"kind": "percentage", "buyer_bps": bps}


def publication_reason(terms: dict, candidate: dict) -> str:
  """Decide only the fixture's explicitly described, whole-timeline scope."""
  if terms["timing"] == "unconfirmed_date_only":
    return "cutoff_not_confirmed"
  eligible = grace_eligible(terms)
  if eligible is None:
    return "booking_instant_unknown"
  if eligible:
    # These candidates have no booking-relative grace interval, even when the
    # particular query is after that interval. Do not silently narrow scope.
    return "applicable_grace_not_represented"
  if terms["percentage_scope"] != "single_scope":
    return "component_refunds_not_represented"
  cutoffs = [
    instant(candidate["anchor"]) - elapsed(tier["until"])
    for tier in candidate["tiers"]
  ]
  if cutoffs != source_cutoffs(terms):
    return "cutoffs_disagree"
  outcomes = [tier["outcome"] for tier in candidate["tiers"]]
  outcomes.append(candidate["after_last_tier"])
  expected = [
    {"kind": "percentage", "buyer_bps": value} for value in terms["refund_bps"]
  ]
  if outcomes != expected:
    return "outcomes_disagree"
  return "represented"


def emitted_policy(fixture: dict, candidate: dict) -> dict:
  """Construct the test adapter's actual wire cancellation policy item."""
  policy = copy.deepcopy(fixture["policy_without_schedule"])
  if publication_reason(fixture["source_terms"], candidate) == "represented":
    policy["schedule"] = copy.deepcopy(candidate)
  return policy


def check_emission(fixture: dict, candidate: dict, policy: dict) -> None:
  """Require faithful emission or real omission, and test consumer fallback."""
  require(valid(policy, "cancellation_item"), "emitted policy fails schema")
  expected_present = fixture["expected_publication"] == "represented"
  require(
    ("schedule" in policy) == expected_present,
    "unsafe schedule emitted or safe schedule omitted",
  )
  without = {key: value for key, value in policy.items() if key != "schedule"}
  require(without == fixture["policy_without_schedule"], "prose changed")
  if expected_present:
    require(policy["schedule"] == candidate, "candidate changed in emission")
  for case in fixture["evaluations"]:
    schedule = policy.get("schedule")
    result = evaluate(schedule, case["at"], True)
    if expected_present:
      require(
        selected(schedule, result) == case["authoritative"],
        "published schedule disagrees with authoritative example",
      )
    else:
      require(
        result == {"status": "unavailable", "reason": "schedule_absent"},
        "omission must cause schedule_absent fallback, not a numeric answer",
      )


def check_fixture(fixture: dict, schedules: dict) -> None:
  """Verify candidate validity, independent evidence, and emitted output."""
  require(bool(fixture["evaluations"]), "fixture has no evaluation evidence")
  candidate = schedules[fixture["candidate"]]
  require(valid(candidate), "candidate unexpectedly fails schema")
  policy = fixture["policy_without_schedule"]
  require("schedule" not in policy, "base policy unexpectedly has schedule")
  require(valid(policy, "cancellation_item"), "prose-only policy invalid")
  require(
    valid({**policy, "schedule": candidate}, "cancellation_item"),
    "candidate policy unexpectedly fails schema",
  )
  terms = fixture["source_terms"]
  require(candidate["anchor"] == terms["anchor"], "anchor differs")
  snapshot = authoritative_terms(terms, fixture["response_generated_at"])
  if snapshot.get("kind") == "percentage":
    classification = {10000: "refundable", 0: "non_refundable"}.get(
      snapshot["buyer_bps"], "partially_refundable"
    )
    require(policy["refundability"] == classification, "snapshot differs")
  elif snapshot.get("status") == "unresolved":
    require(policy["refundability"] == "unknown", "unknown snapshot guessed")
  else:
    # The component case supplies its classification explicitly; no aggregate
    # refund percentage is inferred from unpriced fee components.
    require(
      policy["refundability"] == fixture["expected_refundability"],
      "Business-authored component snapshot differs",
    )
  require(
    publication_reason(terms, candidate) == fixture["expected_publication"],
    "publication expectation mismatch",
  )
  if "expected_cutoff_seconds" in fixture:
    actual = [
      instant(terms["anchor"]) - value for value in source_cutoffs(terms)
    ]
    require(actual == fixture["expected_cutoff_seconds"], "DST offset wrong")
  for case in fixture["evaluations"]:
    result = evaluate(candidate, case["at"], True)
    require(
      selected(candidate, result) == case["candidate_outcome"],
      "mechanical candidate outcome differs",
    )
    source = authoritative_terms(terms, case["at"])
    require(source == case["authoritative"], "source-side expectation differs")
    require(
      case["money"] == {"status": "not_resolved"},
      "these examples supply no resolved cash or unambiguous money basis",
    )
  check_emission(fixture, candidate, emitted_policy(fixture, candidate))


def validate(bundle: dict) -> list[str]:
  """Return failures while keeping source-fidelity out of the wire oracle."""
  if bundle.get("format_version") != 1:
    return ["unsupported fixture format"]
  if not isinstance(bundle.get("fixtures"), list) or not bundle["fixtures"]:
    return ["no publication fixtures"]
  failures = []
  ids = set()
  for fixture in bundle["fixtures"]:
    try:
      name = fixture["id"]
      require(name not in ids, "duplicate fixture id")
      ids.add(name)
      check_fixture(fixture, bundle["schedules"])
    except (ValueError, KeyError, TypeError, IndexError) as error:
      failures.append(f"{fixture.get('id', 'unnamed')}: {error}")
  return failures


def mutation_checks(bundle: dict) -> tuple[list[str], int]:
  """Catch unsafe emission plus ignored grace, calendar and basis evidence."""
  failures = []
  count = 0
  for fixture in bundle["fixtures"]:
    if fixture["expected_publication"] == "represented":
      continue
    candidate = bundle["schedules"][fixture["candidate"]]
    bad_policy = {**fixture["policy_without_schedule"], "schedule": candidate}
    count += 1
    try:
      check_emission(fixture, candidate, bad_policy)
    except ValueError:
      continue
    failures.append(f"unsafe emission not rejected: {fixture['id']}")
  ignored_grace = copy.deepcopy(bundle["fixtures"][0]["source_terms"])
  del ignored_grace["grace"]
  guessed_cutoff = copy.deepcopy(ignored_grace)
  mutations = [
    ("grace_ten_days", ["source_terms"], ignored_grace),
    ("grace_ten_days", ["source_terms", "grace", "within_seconds"], 86401),
    (
      "grace_exact_seven_days",
      ["source_terms", "grace", "minimum_lead_seconds"],
      604801,
    ),
    (
      "grace_below_seven_days",
      ["source_terms", "grace", "minimum_lead_seconds"],
      604799,
    ),
    (
      "unknown_booking",
      ["source_terms", "grace", "booking_completed_at"],
      "2026-11-02T16:00:00-05:00",
    ),
    ("date_only_unconfirmed", ["source_terms"], guessed_cutoff),
    ("calendar_resolved", ["candidate"], "elapsed_twenty_seven"),
    ("mixed_components", ["source_terms", "percentage_scope"], "single_scope"),
    (
      "mixed_components",
      ["policy_without_schedule", "refundability"],
      "non_refundable",
    ),
    (
      "simple_elapsed",
      ["evaluations", 0, "money"],
      {"status": "resolved", "amount": 5000},
    ),
  ]
  for name, path, value in mutations:
    mutant = copy.deepcopy(bundle)
    target = next(item for item in mutant["fixtures"] if item["id"] == name)
    for part in path[:-1]:
      target = target[part]
    target[path[-1]] = value
    count += 1
    if not validate(mutant):
      failures.append(f"mutation not rejected: {name}/{path}")
  return failures, count


def compatibility_checks(bundle: dict) -> tuple[list[str], int]:
  """Prove unknown partial/grace markers do not protect existing readers."""
  fixture = next(
    item for item in bundle["fixtures"] if item["id"] == "grace_ten_days"
  )
  grace_marker = {
    "booking_grace": {
      "within": "PT24H",
      "min_lead_time": "P7D",
      "outcome": {"kind": "percentage", "buyer_bps": 10000},
    }
  }
  markers = [
    {"partial": True},
    grace_marker,
    {"partial": True, **grace_marker},
  ]
  failures = []
  for marker in markers:
    candidate = {**bundle["schedules"][fixture["candidate"]], **marker}
    try:
      require(valid(candidate), "unknown-marker candidate fails wire schema")
      case = fixture["evaluations"][0]
      result = evaluate(candidate, case["at"], True)
      require(
        selected(candidate, result) == case["candidate_outcome"],
        "unknown marker unexpectedly altered the existing reader",
      )
      require(
        case["candidate_outcome"] != case["authoritative"],
        "compatibility example must retain the incorrect structured answer",
      )
      policy = {**fixture["policy_without_schedule"], "schedule": candidate}
      require(valid(policy, "cancellation_item"), "marked policy invalid")
    except ValueError as error:
      failures.append(f"marker[{list(marker)}]: {error}")
      continue
    try:
      check_emission(fixture, candidate, policy)
    except ValueError:
      continue
    failures.append(f"unsafe marked emission accepted: {list(marker)}")
  return failures, len(markers)


def main() -> int:
  """Run schema, publication, source-evidence and mutation regressions."""
  if shutil.which("ucp-schema") is None:
    print("ERROR: ucp-schema is required; no checks were run.")
    return 1
  try:
    bundle = json.loads(FIXTURES.read_text(encoding="utf-8"))
    failures = validate(bundle)
    mutation_count = 0
    compatibility_count = 0
    if not failures:
      failures, mutation_count = mutation_checks(bundle)
      compatibility_failures, compatibility_count = compatibility_checks(bundle)
      failures.extend(compatibility_failures)
  except (OSError, ValueError, RuntimeError) as error:
    print(f"ERROR: {error}")
    return 1
  for failure in failures:
    print(f"FAIL: {failure}")
  cases = sum(len(item["evaluations"]) for item in bundle["fixtures"])
  print(
    f"{len(bundle['fixtures'])} publication fixtures, {cases} source/candidate "
    f"comparisons, {mutation_count} mutation checks, "
    f"{compatibility_count} compatibility checks, {len(failures)} failures"
  )
  return int(bool(failures))


if __name__ == "__main__":
  sys.exit(main())
