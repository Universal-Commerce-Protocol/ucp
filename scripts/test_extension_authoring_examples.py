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

When contributing to the guide, run:
    uv run python scripts/test_extension_authoring_examples.py

These tests check the complete examples and response-only annotation against
local UCP schemas, including values that must fail. By default, published UCP
URLs are mapped to this checkout's source schemas. Pass --published to check
the walkthrough and container pattern against published UCP schemas instead.
Fictional vendor URLs are not fetched.
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
GUIDE = ROOT / "docs/specification/extension-authoring.md"
TEXT = GUIDE.read_text(encoding="utf-8")
PUBLISHED = False


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


class CarbonExamples(_Examples):
  """Keep the copyable carbon-estimate walkthrough internally consistent."""

  def setUp(self):
    """Extract the complete schema, response and profile from the guide."""
    super().setUp()
    self.schema = _example("carbon-schema")
    self.response = _example("carbon-response")
    self.profile = _example("carbon-profile")
    self.version = self.response["ucp"]["version"]
    schema_path = self._write("schemas/carbon.json", self.schema)
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

  def test_negative_estimate(self):
    """A negative estimate proves that the extension's rules are applied."""
    response = copy.deepcopy(self.response)
    response["acme_carbon_estimate"]["grams_co2e"] = -1
    self.assertFalse(json.loads(self._validate(response, 1).stdout)["valid"])

  def test_wrong_estimate_type(self):
    """The estimate uses integer grams, not strings."""
    response = copy.deepcopy(self.response)
    response["acme_carbon_estimate"]["grams_co2e"] = "120"
    self._validate(response, 1)

  def test_estimate_required_when_object_present(self):
    """An estimate object must include its computed grams of CO2 equivalent."""
    response = copy.deepcopy(self.response)
    response["acme_carbon_estimate"] = {"methodology": "example-method"}
    self._validate(response, 1)

  def test_request_and_response_views(self):
    """Computed estimates belong in the response view, not the request view."""
    path = self._write("response.json", self.response)
    request = self._cli(
      ["resolve", path, "--op", "create", "--request"],
      self.version,
    )
    self.assertFalse(
      _property_defined(json.loads(request.stdout), "acme_carbon_estimate")
    )
    response = self._cli(
      ["resolve", path, "--op", "read", "--response"],
      self.version,
    )
    self.assertTrue(
      _property_defined(json.loads(response.stdout), "acme_carbon_estimate")
    )

  def test_both_profile_roles(self):
    """Run the walkthrough's commands for both saved profile variants."""
    for role in ("business", "platform"):
      with self.subTest(role=role):
        self._cli(
          [
            "validate",
            self._write(f"{role}-profile.json", self.profile),
            "--schema",
            f"https://ucp.dev/{self.version}/schemas/profile.json",
            "--def",
            f"{role}_schema",
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
    declared = self.response["ucp"]["capabilities"][self.schema["name"]][0]
    self.assertEqual(declared["version"], extension["version"])
    self.assertEqual(declared["extends"], extension["extends"])

  def test_coexists_with_ucp_loyalty(self):
    """UCP loyalty and the Acme estimate can compose on the same checkout."""
    response = copy.deepcopy(self.response)
    response["ucp"]["capabilities"]["dev.ucp.common.loyalty"] = [
      {
        "version": self.version,
        "schema": f"https://ucp.dev/{self.version}/schemas/common/loyalty.json",
        "extends": "dev.ucp.shopping.checkout",
      }
    ]
    response["loyalty"] = {
      "com.acme.rewards": {
        "id": "member_123",
        "name": "Acme Rewards",
        "provisional": False,
      }
    }
    self._validate(response)
    bad_loyalty = copy.deepcopy(response)
    del bad_loyalty["loyalty"]["com.acme.rewards"]["id"]
    result = self._validate(bad_loyalty, 1)
    self.assertIn("/loyalty/com.acme.rewards", result.stdout)
    self.assertIn("required property", result.stdout)
    response["acme_carbon_estimate"]["grams_co2e"] = -1
    self._validate(response, 1)

  def test_absent_estimate_is_valid(self):
    """Supporting the extension does not require an estimate on every reply."""
    response = copy.deepcopy(self.response)
    del response["acme_carbon_estimate"]
    self._validate(response)


class OperationVisibilityExamples(_Examples):
  """Check the displayed completion-only alternative."""

  def setUp(self):
    """Apply the displayed property map to a temporary checkout extension."""
    super().setUp()
    self.field = "acme_carbon_estimate"
    self.schema = _example("carbon-schema")
    self.schema["$defs"]["dev.ucp.shopping.checkout"]["allOf"][1][
      "properties"
    ] = _example("completion-visibility")
    self.response = _example("carbon-response")
    self.version = self.response["ucp"]["version"]
    self.response["status"] = "completed"
    self.response["order"] = {
      "id": "order_123",
      "permalink_url": "https://acme.com/orders/order_123",
    }
    path = self._write("schemas/completion-carbon.json", self.schema)
    self.response["ucp"]["capabilities"][self.schema["name"]][0]["schema"] = (
      self._reference(path)
    )

  def _validate(self, data, op="complete", expected=0):
    result = self._cli(
      [
        "validate",
        self._write("response.json", data),
        "--op",
        op,
        "--response",
        "--json",
      ],
      self.version,
      expected,
    )
    self.assertEqual(json.loads(result.stdout)["valid"], expected == 0)
    return result

  def test_all_checkout_views(self):
    """Only the completion response includes the field in its schema."""
    path = self._write("response.json", self.response)
    for op in ("create", "read", "update", "complete", "cancel"):
      for direction in ("request", "response"):
        with self.subTest(op=op, direction=direction):
          result = self._cli(
            ["resolve", path, "--op", op, "--" + direction], self.version
          )
          self.assertEqual(
            _property_defined(json.loads(result.stdout), self.field),
            op == "complete" and direction == "response",
          )

  def test_completion_optional_and_constrained(self):
    """Completion accepts absence but applies the constraint when present."""
    self._validate(self.response)
    absent = copy.deepcopy(self.response)
    del absent[self.field]
    self._validate(absent)
    bad = copy.deepcopy(self.response)
    bad[self.field]["grams_co2e"] = -1
    result = self._validate(bad, expected=1)
    self.assertIn("/acme_carbon_estimate/grams_co2e", result.stdout)

  def test_omission_does_not_reject_unknown_response_fields(self):
    """Read/cancel views omit the field without closing the base object."""
    for op in ("read", "cancel"):
      with self.subTest(op=op):
        data = copy.deepcopy(self.response)
        if op == "cancel":
          data["status"] = "canceled"
          del data["order"]
        data[self.field]["grams_co2e"] = -1
        self._validate(data, op=op)


class ContainerExamples(_Examples):
  """Exercise the displayed nested container pattern with failing payloads."""

  def setUp(self):
    """Complete the pattern fragment with reusable types and a Product."""
    super().setUp()
    self.version = "2026-08-25"
    self.parent = "dev.ucp.shopping.catalog.search"
    self.schema = _example("container-pattern", self.version)
    self.schema.update(
      {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://acme.com/ucp/schemas/catalog-carbon.json",
        "name": "com.acme.shopping.carbon",
        "version": "2026-09-01",
      }
    )
    self.schema["$defs"]["acme_carbon_estimate"] = _example("carbon-schema")[
      "$defs"
    ]["acme_carbon_estimate"]
    self.schema["$defs"]["product_with_carbon"] = {
      "allOf": [
        {
          "$ref": f"https://ucp.dev/{self.version}/schemas/shopping/types/product.json"
        },
        {
          "type": "object",
          "properties": {
            "acme_carbon_estimate": {
              "$ref": "#/$defs/acme_carbon_estimate",
              "ucp_request": "omit",
            }
          },
        },
      ]
    }
    path = self._write("schemas/catalog-carbon.json", self.schema)
    self.response = {
      "ucp": {
        "version": self.version,
        "capabilities": {
          self.parent: [
            {
              "version": self.version,
              "schema": f"https://ucp.dev/{self.version}/schemas/shopping/catalog_search.json",
            }
          ],
          self.schema["name"]: [
            {
              "version": self.schema["version"],
              "schema": self._reference(path),
              "extends": self.parent,
            }
          ],
        },
      },
      "products": [
        {
          "id": "P100",
          "title": "Oxford Shirt",
          "description": {"plain": "Cotton oxford shirt."},
          "price_range": {
            "min": {"amount": 4500, "currency": "USD"},
            "max": {"amount": 4500, "currency": "USD"},
          },
          "variants": [
            {
              "id": "V100",
              "title": "Medium",
              "description": {"plain": "Medium"},
              "price": {"amount": 4500, "currency": "USD"},
            }
          ],
          "acme_carbon_estimate": {"grams_co2e": 120},
        }
      ],
    }

  def _validate(self, expected=0):
    return self._cli(
      [
        "validate",
        self._write("search-response.json", self.response),
        "--op",
        "search",
        "--response",
        "--json",
      ],
      self.version,
      expected,
    )

  def test_nested_constraints_are_applied(self):
    """The pattern accepts a valid Product and rejects a negative estimate."""
    self._validate()
    self.response["products"][0]["acme_carbon_estimate"]["grams_co2e"] = -1
    result = self._validate(1)
    self.assertFalse(json.loads(result.stdout)["valid"])
    self.assertIn("grams_co2e", result.stdout)

  def test_product_constraints_are_preserved(self):
    """Adding an estimate does not relax the base Product's required fields."""
    del self.response["products"][0]["variants"]
    self._validate(1)

  def test_www_host_is_rejected(self):
    """A www URL does not bind to the apex-domain extension name."""
    self.response["ucp"]["capabilities"][self.schema["name"]][0]["schema"] = (
      "https://www.acme.com/ucp/schemas/catalog-carbon.json"
    )
    result = self._validate(2)
    self.assertIn("com.acme.www", result.stdout + result.stderr)


if __name__ == "__main__":
  if "--published" in sys.argv:
    PUBLISHED = True
    sys.argv.remove("--published")
  unittest.main()
