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

"""Check complete extension-authoring examples, without fetching vendor URLs.

By default, published UCP URLs are mapped to this checkout's source schemas.
Pass --published to smoke-test the loyalty response against published UCP
schemas instead. Feed examples are tested only when their section is present.
"""

import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
GUIDE = ROOT / "docs/documentation/extension-authoring.md"
TEXT = GUIDE.read_text(encoding="utf-8")
PUBLISHED = "--published" in sys.argv
if PUBLISHED:
  sys.argv.remove("--published")


def _blocks():
  pattern = (
    r"<!-- extension-authoring-example: ([a-z0-9-]+) -->\s*"
    r"(?:<!--.*?-->\s*)*```(json|text)\n(.*?)\n```"
  )
  return {
    match.group(1): (match.group(2), match.group(3))
    for match in re.finditer(pattern, TEXT, re.DOTALL)
  }


BLOCKS = _blocks()


def _example(name, version="2026-09-25"):
  raw = BLOCKS[name][1].replace("{{ ucp_version }}", version)
  return json.loads(raw)


def _property_defined(value, name):
  if isinstance(value, dict):
    if name in value.get("properties", {}):
      return True
    return any(
      _property_defined(child, name)
      for key, child in value.items()
      if key not in ("$defs", "definitions", "examples", "default", "const")
    )
  if isinstance(value, list):
    return any(_property_defined(child, name) for child in value)
  return False


class _Examples(unittest.TestCase):
  """Run isolated CLI checks on temporary copies of the displayed examples."""

  def setUp(self):
    """Create a private fixture directory for each test."""
    directory = tempfile.TemporaryDirectory(prefix="extension-authoring-")
    self.addCleanup(directory.cleanup)
    self.directory = Path(directory.name)

  def _write(self, name, data):
    path = self.directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path

  def _reference(self, path):
    if PUBLISHED:
      return str(path)
    # With a local base, non-URL references are resolved against that base.
    return os.path.relpath(path, SOURCE)

  def _cli(self, arguments, version, expected=0):
    mapping = []
    if not PUBLISHED:
      mapping = [
        "--schema-remote-base",
        "https://ucp.dev/" + version,
        "--schema-local-base",
        str(SOURCE),
      ]
    result = subprocess.run(
      ["ucp-schema", *map(str, arguments), *mapping],
      cwd=self.directory,
      capture_output=True,
      text=True,
      check=False,
      timeout=90,
    )
    self.assertEqual(
      result.returncode,
      expected,
      msg=f"Command: {arguments}\n{result.stdout}\n{result.stderr}",
    )
    return result

  def _authority(self, schema):
    host = urlsplit(schema["$id"]).hostname
    self.assertIsNotNone(host)
    authority = ".".join(reversed(host.split(".")))
    self.assertTrue(
      schema["name"] == authority or schema["name"].startswith(authority + ".")
    )


class LoyaltyExamples(_Examples):
  """Keep the copyable loyalty walkthrough internally consistent."""

  def setUp(self):
    """Extract the complete schema, response and profile from the guide."""
    super().setUp()
    self.schema = _example("loyalty-schema")
    self.response = _example("loyalty-response")
    self.profile = _example("loyalty-profile")
    self.version = self.response["ucp"]["version"]
    schema_path = self._write("schemas/loyalty.json", self.schema)
    extension = self.response["ucp"]["capabilities"][self.schema["name"]][0]
    extension["schema"] = self._reference(schema_path)

  def _validate(self, response, expected=0):
    return self._cli(
      [
        "validate",
        self._write("response.json", response),
        "--op",
        "read",
        "--response",
        "--json",
      ],
      self.version,
      expected,
    )

  def test_complete_response(self):
    """The complete response passes the displayed extension constraints."""
    result = self._validate(self.response)
    self.assertTrue(json.loads(result.stdout)["valid"])

  def test_negative_points(self):
    """Negative points fail, proving that the extension's rules are applied."""
    response = copy.deepcopy(self.response)
    response["loyalty"]["points_earned"] = -1
    self.assertFalse(json.loads(self._validate(response, 1).stdout)["valid"])

  def test_wrong_points_type(self):
    """Points are integers, not strings."""
    response = copy.deepcopy(self.response)
    response["loyalty"]["points_earned"] = "120"
    self._validate(response, 1)

  def test_points_required_when_loyalty_present(self):
    """A loyalty object must include its computed points."""
    response = copy.deepcopy(self.response)
    response["loyalty"] = {"member_id": "example-member"}
    self._validate(response, 1)

  def test_request_and_response_views(self):
    """Computed points belong in the response view, not the request view."""
    path = self._write("response.json", self.response)
    request = self._cli(
      ["resolve", path, "--op", "create", "--request"],
      self.version,
    )
    self.assertFalse(_property_defined(json.loads(request.stdout), "loyalty"))
    response = self._cli(
      ["resolve", path, "--op", "read", "--response"],
      self.version,
    )
    self.assertTrue(_property_defined(json.loads(response.stdout), "loyalty"))

  def test_both_profile_roles(self):
    """The example declarations work as both minimal profile variants."""
    for definition in ("business_schema", "platform_schema"):
      with self.subTest(definition=definition):
        self._cli(
          [
            "validate",
            self._write("profile.json", self.profile),
            "--schema",
            SOURCE / "schemas/profile.json",
            "--def",
            definition,
            "--op",
            "read",
            "--response",
            "--json",
          ],
          self.version,
        )

  def test_names_and_versions_match(self):
    """The profile, response and schema use the same names and UCP release."""
    self._authority(self.schema)
    parent = self.response["ucp"]["capabilities"]["dev.ucp.shopping.checkout"][
      0
    ]
    base_ref = self.schema["$defs"]["dev.ucp.shopping.checkout"]["allOf"][0][
      "$ref"
    ]
    self.assertEqual(parent["schema"], base_ref)
    self.assertEqual(parent["version"], self.version)
    extension = self.profile["ucp"]["capabilities"][self.schema["name"]][0]
    self.assertEqual(extension["schema"], self.schema["$id"])
    self.assertEqual(extension["version"], self.schema["version"])
    self.assertEqual(extension["extends"], "dev.ucp.shopping.checkout")


class FeedExamples(_Examples):
  """Check the feeds supplement when this checkout includes that section."""

  def setUp(self):
    """Extract feed examples and add metadata only to validation fixtures."""
    super().setUp()
    self.version = "2026-09-25"
    self.schema = _example("feed-extension", self.version)
    self.profile = _example("feed-profile", self.version)
    self.manifest = _example("feed-manifest", self.version)
    self.record = _example("feed-record", self.version)
    schema_path = self._write("schemas/ads.json", self.schema)
    self.metadata = copy.deepcopy(self.manifest["ucp"])
    # Records do not need a per-record envelope. This adapter only supplies
    # the CLI with the manifest's declarations so it can compose the schema.
    for name, entries in self.metadata["capabilities"].items():
      if name == self.schema["name"]:
        entries[0]["schema"] = self._reference(schema_path)
      else:
        entries[0]["schema"] = self.profile["ucp"]["capabilities"][name][0][
          "schema"
        ]

  def _validate(self, record, expected=0):
    data = copy.deepcopy(record)
    data["ucp"] = self.metadata
    return self._cli(
      [
        "validate",
        self._write("record.json", data),
        "--def",
        "record",
        "--op",
        "list",
        "--response",
        "--json",
      ],
      self.version,
      expected,
    )

  def test_record_and_optional_flag(self):
    """Products accept a boolean flag or its absence, but not a string."""
    self._validate(self.record)
    false_record = copy.deepcopy(self.record)
    false_record["ads_eligible"] = False
    self._validate(false_record)
    absent = copy.deepcopy(self.record)
    del absent["ads_eligible"]
    self._validate(absent)
    wrong = copy.deepcopy(self.record)
    wrong["ads_eligible"] = "true"
    self._validate(wrong, 1)

  def test_base_fields_are_preserved(self):
    """The extension does not relax the Product's required fields."""
    record = copy.deepcopy(self.record)
    del record["variants"]
    self._validate(record, 1)

  def test_readable_record_matches_jsonl(self):
    """The expanded view and actual one-line record describe identical data."""
    kind, raw = BLOCKS["feed-record-jsonl"]
    self.assertEqual(kind, "text")
    self.assertEqual(len(raw.splitlines()), 1)
    self.assertEqual(json.loads(raw), self.record)

  def test_profile_and_manifest(self):
    """The authored profiles and manifests follow their source schemas."""
    self._cli(
      [
        "validate",
        self._write("profile.json", self.profile),
        "--schema",
        SOURCE / "schemas/profile.json",
        "--def",
        "business_schema",
        "--op",
        "read",
        "--response",
        "--json",
      ],
      self.version,
    )
    self._cli(
      [
        "validate",
        self._write("manifest.json", self.manifest),
        "--schema",
        SOURCE / "schemas/shopping/catalog_feed.json",
        "--def",
        "manifest",
        "--op",
        "list",
        "--response",
        "--json",
      ],
      self.version,
    )

  def test_authority_and_aliases(self):
    """Both complete extension examples have matching names and hosts."""
    self._authority(self.schema)
    self._authority(_example("feed-custom-extension", self.version))
    root = self.schema["$defs"]["dev.ucp.common.feed"]
    parent = self.schema["$defs"]["dev.ucp.shopping.catalog.feed"]
    self.assertEqual(root, parent)
    self.assertEqual(self.schema["name"], "com.example.ads.eligibility")


def load_tests(loader, standard_tests, pattern):
  """Select only examples present in this branch; missing markers still fail."""
  del standard_tests, pattern
  suite = loader.loadTestsFromTestCase(LoyaltyExamples)
  if not PUBLISHED and "## Extend a Feed" in TEXT:
    suite.addTests(loader.loadTestsFromTestCase(FeedExamples))
  return suite


if __name__ == "__main__":
  unittest.main()
