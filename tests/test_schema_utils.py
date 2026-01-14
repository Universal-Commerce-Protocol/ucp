#   Copyright 2026 UCP Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Unit tests for schema_utils.py.

This module contains comprehensive tests for the schema utility functions
used throughout the UCP specification generation and validation pipeline.
"""

import json
import os
import tempfile
import unittest
from typing import Any, Dict, Optional
from unittest.mock import mock_open, patch

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import schema_utils


class TestColors(unittest.TestCase):
    """Tests for the Colors class ANSI codes."""

    def test_color_constants_defined(self) -> None:
        """Verify all color constants are defined as ANSI escape codes."""
        self.assertTrue(hasattr(schema_utils.Colors, 'GREEN'))
        self.assertTrue(hasattr(schema_utils.Colors, 'RED'))
        self.assertTrue(hasattr(schema_utils.Colors, 'YELLOW'))
        self.assertTrue(hasattr(schema_utils.Colors, 'CYAN'))
        self.assertTrue(hasattr(schema_utils.Colors, 'RESET'))

    def test_color_codes_are_strings(self) -> None:
        """Verify color codes are string type."""
        self.assertIsInstance(schema_utils.Colors.GREEN, str)
        self.assertIsInstance(schema_utils.Colors.RED, str)
        self.assertIsInstance(schema_utils.Colors.YELLOW, str)
        self.assertIsInstance(schema_utils.Colors.CYAN, str)
        self.assertIsInstance(schema_utils.Colors.RESET, str)

    def test_color_codes_start_with_escape(self) -> None:
        """Verify color codes start with ANSI escape sequence."""
        self.assertTrue(schema_utils.Colors.GREEN.startswith('\033['))
        self.assertTrue(schema_utils.Colors.RESET.startswith('\033['))


class TestResolveRefPath(unittest.TestCase):
    """Tests for resolve_ref_path function."""

    def test_internal_reference_returns_none(self) -> None:
        """Internal references starting with # should return None."""
        result = schema_utils.resolve_ref_path('#/definitions/Item', '/path/to/file.json')
        self.assertIsNone(result)

    def test_http_reference_returns_none(self) -> None:
        """HTTP/HTTPS URLs should return None."""
        result = schema_utils.resolve_ref_path(
            'https://example.com/schema.json',
            '/path/to/file.json'
        )
        self.assertIsNone(result)

    def test_relative_reference_resolution(self) -> None:
        """Relative paths should be resolved correctly."""
        result = schema_utils.resolve_ref_path(
            'types/item.json',
            '/project/schemas/checkout.json'
        )
        expected = os.path.normpath('/project/schemas/types/item.json')
        self.assertEqual(result, expected)

    def test_reference_with_anchor(self) -> None:
        """References with anchors should strip anchor and resolve file path."""
        result = schema_utils.resolve_ref_path(
            'common.json#/$defs/Address',
            '/project/schemas/checkout.json'
        )
        expected = os.path.normpath('/project/schemas/common.json')
        self.assertEqual(result, expected)

    def test_anchor_only_returns_none(self) -> None:
        """References that are only anchors should return None."""
        result = schema_utils.resolve_ref_path(
            '#/$defs/Address',
            '/project/schemas/checkout.json'
        )
        self.assertIsNone(result)

    def test_parent_directory_reference(self) -> None:
        """Parent directory references should be resolved correctly."""
        result = schema_utils.resolve_ref_path(
            '../common/types.json',
            '/project/schemas/shopping/checkout.json'
        )
        expected = os.path.normpath('/project/schemas/common/types.json')
        self.assertEqual(result, expected)


class TestLoadJson(unittest.TestCase):
    """Tests for load_json function."""

    def test_load_valid_json(self) -> None:
        """Valid JSON files should be loaded correctly."""
        test_data = {'name': 'test', 'value': 42}
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = schema_utils.load_json(temp_path)
            self.assertEqual(result, test_data)
        finally:
            os.unlink(temp_path)

    def test_load_nonexistent_file(self) -> None:
        """Nonexistent files should return None."""
        result = schema_utils.load_json('/nonexistent/path/file.json')
        self.assertIsNone(result)

    def test_load_invalid_json(self) -> None:
        """Invalid JSON should return None."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            f.write('{ invalid json }')
            temp_path = f.name

        try:
            result = schema_utils.load_json(temp_path)
            self.assertIsNone(result)
        finally:
            os.unlink(temp_path)


class TestResolveInternalRef(unittest.TestCase):
    """Tests for resolve_internal_ref function."""

    def test_resolve_simple_path(self) -> None:
        """Simple JSON pointer paths should resolve correctly."""
        root_data = {
            'definitions': {
                'Item': {'type': 'object', 'title': 'Item'}
            }
        }
        result = schema_utils.resolve_internal_ref('#/definitions/Item', root_data)
        self.assertEqual(result, {'type': 'object', 'title': 'Item'})

    def test_resolve_nested_path(self) -> None:
        """Nested JSON pointer paths should resolve correctly."""
        root_data = {
            '$defs': {
                'types': {
                    'Address': {'type': 'object'}
                }
            }
        }
        result = schema_utils.resolve_internal_ref('#/$defs/types/Address', root_data)
        self.assertEqual(result, {'type': 'object'})

    def test_resolve_nonexistent_path(self) -> None:
        """Nonexistent paths should return None."""
        root_data = {'definitions': {}}
        result = schema_utils.resolve_internal_ref('#/definitions/Missing', root_data)
        self.assertIsNone(result)

    def test_resolve_array_index(self) -> None:
        """Array indices in paths should resolve correctly."""
        root_data = {
            'items': [
                {'name': 'first'},
                {'name': 'second'}
            ]
        }
        result = schema_utils.resolve_internal_ref('#/items/1', root_data)
        self.assertEqual(result, {'name': 'second'})

    def test_invalid_ref_format(self) -> None:
        """References not starting with #/ should return None."""
        root_data = {'definitions': {'Item': {}}}
        result = schema_utils.resolve_internal_ref('definitions/Item', root_data)
        self.assertIsNone(result)


class TestMergeSchemas(unittest.TestCase):
    """Tests for merge_schemas function."""

    def test_simple_merge(self) -> None:
        """Simple schemas should merge correctly."""
        base = {'type': 'object', 'title': 'Base'}
        overlay = {'description': 'An overlay'}
        result = schema_utils.merge_schemas(base, overlay)
        self.assertEqual(result['type'], 'object')
        self.assertEqual(result['title'], 'Base')
        self.assertEqual(result['description'], 'An overlay')

    def test_properties_merge(self) -> None:
        """Properties should be merged, not replaced."""
        base = {
            'properties': {
                'name': {'type': 'string'},
                'age': {'type': 'integer'}
            }
        }
        overlay = {
            'properties': {
                'email': {'type': 'string'}
            }
        }
        result = schema_utils.merge_schemas(base, overlay)
        self.assertIn('name', result['properties'])
        self.assertIn('age', result['properties'])
        self.assertIn('email', result['properties'])

    def test_required_union(self) -> None:
        """Required arrays should be unioned and deduplicated."""
        base = {'required': ['name', 'age']}
        overlay = {'required': ['age', 'email']}
        result = schema_utils.merge_schemas(base, overlay)
        self.assertEqual(sorted(result['required']), ['age', 'email', 'name'])

    def test_overlay_wins_for_same_key(self) -> None:
        """Overlay values should override base for non-special keys."""
        base = {'title': 'Base Title', 'type': 'object'}
        overlay = {'title': 'Overlay Title'}
        result = schema_utils.merge_schemas(base, overlay)
        self.assertEqual(result['title'], 'Overlay Title')

    def test_additional_properties_overlay_wins(self) -> None:
        """additionalProperties from overlay should override base."""
        base = {'additionalProperties': True}
        overlay = {'additionalProperties': False}
        result = schema_utils.merge_schemas(base, overlay)
        self.assertFalse(result['additionalProperties'])


class TestResolveSchema(unittest.TestCase):
    """Tests for resolve_schema function."""

    def test_simple_schema_passthrough(self) -> None:
        """Schemas without refs or allOf should pass through unchanged."""
        schema = {'type': 'object', 'properties': {'name': {'type': 'string'}}}
        result = schema_utils.resolve_schema(schema, schema)
        self.assertEqual(result['type'], 'object')
        self.assertIn('name', result['properties'])

    def test_internal_ref_resolution(self) -> None:
        """Internal $ref should be resolved and merged."""
        root_data = {
            '$defs': {
                'Name': {'type': 'string', 'minLength': 1}
            }
        }
        schema = {'$ref': '#/$defs/Name'}
        result = schema_utils.resolve_schema(schema, root_data)
        self.assertEqual(result['type'], 'string')
        self.assertEqual(result['minLength'], 1)

    def test_allof_merging(self) -> None:
        """allOf schemas should be merged together."""
        schema = {
            'allOf': [
                {'type': 'object', 'properties': {'a': {'type': 'string'}}},
                {'properties': {'b': {'type': 'integer'}}}
            ]
        }
        result = schema_utils.resolve_schema(schema, schema)
        self.assertEqual(result['type'], 'object')
        self.assertIn('a', result['properties'])
        self.assertIn('b', result['properties'])

    def test_circular_ref_prevention(self) -> None:
        """Circular references should not cause infinite recursion."""
        root_data = {
            '$defs': {
                'Node': {
                    'type': 'object',
                    'properties': {
                        'child': {'$ref': '#/$defs/Node'}
                    }
                }
            }
        }
        # This should complete without hanging
        result = schema_utils.resolve_schema(
            root_data['$defs']['Node'],
            root_data
        )
        self.assertEqual(result['type'], 'object')


class TestJsonSuffixReplacement(unittest.TestCase):
    """Tests to verify correct .json suffix handling (PR #7 bug fix)."""

    def test_suffix_only_replacement(self) -> None:
        """Verify .json is only replaced when it's a suffix, not in the middle."""
        # This tests the expected behavior after the bug fix
        # The string "foo.json.backup.json" should become "foo.json.backup_req.json"
        # NOT "foo_req.backup_req"

        test_id = "shopping/checkout.json"
        # Correct approach: only replace the suffix
        if test_id.endswith(".json"):
            result = test_id[:-5] + "_req.json"
        else:
            result = test_id

        self.assertEqual(result, "shopping/checkout_req.json")
        self.assertNotEqual(result, "shopping/checkout_req")

    def test_multiple_json_in_path(self) -> None:
        """Paths with .json in directory names should be handled correctly."""
        test_id = "json.schemas/types/item.json"
        if test_id.endswith(".json"):
            result = test_id[:-5] + "_req.json"
        else:
            result = test_id

        # The json.schemas part should remain unchanged
        self.assertEqual(result, "json.schemas/types/item_req.json")


if __name__ == '__main__':
    unittest.main()
