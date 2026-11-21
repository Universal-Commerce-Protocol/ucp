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

"""Check the feed supplement's complete examples against local UCP schemas.

Run directly with:
    uv run python scripts/test_feed_authoring_examples.py

The guide, feed schemas, and all feed example markers are required. Missing
fixtures fail the suite rather than silently omitting it. The shared harness
maps UCP URLs to this checkout and never fetches fictional vendor URLs.
"""

import copy
import json
import unittest

from test_extension_authoring_examples import (
  BLOCKS,
  SOURCE,
  _Examples,
  _example,
)


class FeedExamples(_Examples):
  """Check the complete examples in the feeds supplement."""

  def setUp(self):
    """Extract feed examples and add metadata only to validation fixtures."""
    super().setUp()
    required = {
      "feed-extension",
      "feed-profile",
      "feed-manifest",
      "feed-record",
      "feed-record-jsonl",
      "feed-custom-extension",
    }
    self.assertFalse(required - BLOCKS.keys(), "Missing feed example markers")
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


if __name__ == "__main__":
  unittest.main()
