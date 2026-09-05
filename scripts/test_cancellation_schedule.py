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
"""Run portable cancellation schedule vectors against a test-only oracle.

Run: python3 scripts/test_cancellation_schedule.py
Requires ucp-schema on PATH; no Python packages are required.

These vectors check selection and fallback after a policy has been targeted.
The small oracle uses exact Fraction arithmetic and the specification's POSIX
time profile. It is not a production evaluator, does not resolve targeting or
interpret legal prose, and never calculates money or classifies refundability.
Its result envelope and JSON Pointers are test metadata, not protocol fields.

Schema checks use ucp-schema. Calendar validity, normalized ordering, exact
boundaries, and unsupported selected kinds are separate semantic checks.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "scripts/fixtures/lodging_cancellation_schedule.json"
SCHEMA = ROOT / "source/schemas/lodging/policy_cancellation.json"
TIMESTAMP = re.compile(
  r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]"
  r"([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]+))?"
  r"([Zz]|[+-][0-9]{2}:[0-9]{2})"
)
DURATION = re.compile(
  r"P(?:([0-9]+)D)?"
  r"(?:T(?:([0-9]+)H)?(?:([0-9]+)M)?(?:([0-9]+)S)?)?"
)
KNOWN_KINDS = {"percentage", "fixed_fee", "unit_deduction"}


def instant(value: str) -> Fraction:
  """Parse a fixture instant without rounding fractional seconds."""
  match = TIMESTAMP.fullmatch(value)
  if match is None:
    raise ValueError("Invalid timestamp syntax")
  year, month, day, hour, minute, second = map(int, match.groups()[:6])
  if hour > 23 or minute > 59 or second > 59:
    raise ValueError("Unsupported or invalid time")
  ordinal = date(year, month, day).toordinal()
  fraction, zone = match.groups()[6:]
  offset = 0
  if zone not in {"Z", "z"}:
    offset_hour, offset_minute = map(int, zone[1:].split(":"))
    if offset_hour > 23 or offset_minute > 59:
      raise ValueError("Invalid UTC offset")
    offset = (offset_hour * 60 + offset_minute) * 60
    if zone[0] == "-":
      offset = -offset
  whole = ordinal * 86400 + hour * 3600 + minute * 60 + second - offset
  part = Fraction(int(fraction), 10 ** len(fraction)) if fraction else 0
  return Fraction(whole) + part


def elapsed(value: str) -> int:
  """Normalize a supported duration to exact whole elapsed seconds."""
  match = DURATION.fullmatch(value)
  if match is None or not any(match.groups()):
    raise ValueError("Invalid duration")
  if "T" in value and not any(match.groups()[1:]):
    raise ValueError("Empty time component")
  return sum(
    int(component or 0) * unit
    for component, unit in zip(
      match.groups(), (86400, 3600, 60, 1), strict=True
    )
  )


def schema_valid(schedule: dict) -> bool:
  """Validate the whole wire schedule using the repository's schema tool."""
  with tempfile.TemporaryDirectory(prefix="ucp-cancellation-vector-") as temp:
    payload = Path(temp) / "schedule.json"
    payload.write_text(json.dumps(schedule), encoding="utf-8")
    result = subprocess.run(
      [
        "ucp-schema",
        "validate",
        str(payload),
        "--schema",
        str(SCHEMA),
        "--def",
        "cancellation_schedule",
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
  if "valid" not in output:
    raise RuntimeError(f"Unexpected schema result: {output}")
  return output["valid"]


def unavailable(reason: str, pointer: str | None = None) -> dict:
  """Build a test-only fallback result."""
  result = {"status": "unavailable", "reason": reason}
  if pointer is not None:
    result["pointer"] = pointer
  return result


def evaluate(schedule: dict | None, at: str, valid: bool) -> dict:
  """Select a wire outcome after validating the entire schedule."""
  if schedule is None:
    return unavailable("schedule_absent")
  if not valid:
    return unavailable("invalid_schedule")
  try:
    anchor = instant(schedule["anchor"])
    durations = [elapsed(tier["until"]) for tier in schedule["tiers"]]
    if any(
      left <= right
      for left, right in zip(durations, durations[1:], strict=False)
    ):
      return unavailable("invalid_schedule")
  except ValueError:
    return unavailable("invalid_schedule")
  try:
    when = instant(at)
  except ValueError:
    return unavailable("invalid_instant")
  pointer = "/schedule/after_last_tier"
  selected = schedule["after_last_tier"]
  for index, duration in enumerate(durations):
    if when < anchor - duration:
      pointer = f"/schedule/tiers/{index}/outcome"
      selected = schedule["tiers"][index]["outcome"]
      break
  if selected["kind"] not in KNOWN_KINDS:
    return unavailable("unsupported_kind", pointer)
  return {"status": "selected", "pointer": pointer}


def main() -> int:
  """Check every fixture and return a nonzero status on any failure."""
  if shutil.which("ucp-schema") is None:
    print("ERROR: ucp-schema is required; no checks were run.")
    return 1
  fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
  results = {}
  failures = []
  schema_checks = 0
  for name, entry in fixtures["schedules"].items():
    results[name] = schema_valid(entry["value"])
    if "schema_valid" in entry:
      schema_checks += 1
      if results[name] != entry["schema_valid"]:
        failures.append(f"schema[{name}]: got {results[name]}")
  names = set()
  for case in fixtures["cases"]:
    if case["id"] in names:
      failures.append(f"duplicate case id: {case['id']}")
    names.add(case["id"])
    name = case["schedule"]
    schedule = fixtures["schedules"][name]["value"] if name else None
    actual = evaluate(schedule, case["at"], results[name] if name else True)
    if actual != case["expected"]:
      failures.append(
        f"{case['id']}: expected {case['expected']}, got {actual}"
      )
  for failure in failures:
    print(f"FAIL: {failure}")
  print(
    f"{len(fixtures['cases'])} selection/fallback vectors, "
    f"{schema_checks} schema expectations, {len(failures)} failures"
  )
  return int(bool(failures))


if __name__ == "__main__":
  sys.exit(main())
