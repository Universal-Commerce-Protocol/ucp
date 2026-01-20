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

"""Shared utilities for schema processing and validation."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


class Colors:
  """ANSI color codes for terminal output."""

  GREEN = "\033[92m"
  RED = "\033[91m"
  YELLOW = "\033[93m"
  CYAN = "\033[96m"
  RESET = "\033[0m"


def resolve_ref_path(ref: str, current_file: str | Path) -> Path | None:
  """Resolve a $ref to an absolute file path.

  Args:
  ----
      ref: The $ref value (e.g., "types/line_item.json" or
        "foo.json#/$defs/Bar")
      current_file: Absolute path of the file containing the $ref

  Returns:
  -------
      Absolute path to referenced file, or None if ref is internal (#) or
      external (http)

  """
  if ref.startswith("#"):
    return None  # Internal reference within same file
  if ref.startswith("http"):
    return None  # External URL

  # Split file path from internal anchor (e.g., "foo.json#/$defs/Bar")
  file_part = ref.split("#")[0]
  if not file_part:
    return None  # Just an anchor like "#/$defs/Bar"

  current_dir = Path(current_file).parent
  return (current_dir / file_part).resolve()


def load_json(path: str | Path) -> dict[str, Any] | None:
  """Load JSON file, returns None on error."""
  try:
    with Path(path).open(encoding="utf-8") as f:
      return json.load(f)
  except (json.JSONDecodeError, OSError):
    return None


def resolve_internal_ref(ref: str, root_data: Any) -> Any | None:
  """Resolve a local reference (e.g., '#/definitions/item') against root_data.

  Args:
  ----
    ref: The internal reference string (starting with '#').
    root_data: The full JSON/YAML object of the file.

  Returns:
  -------
    The data at the reference, or None if not found.

  """
  if ref == "#":
    return root_data

  if not ref.startswith("#/"):
    return None
  path = ref.lstrip("#/").split("/")
  current = root_data
  for key in path:
    if isinstance(current, dict) and key in current:
      current = current[key]
    else:
      # Check if the key is an integer for list indexing
      try:
        idx = int(key)
        if isinstance(current, list) and 0 <= idx < len(current):
          current = current[idx]
        else:
          return None
      except ValueError:
        return None
  return current


def merge_schemas(
  base: dict[str, Any], overlay: dict[str, Any]
) -> dict[str, Any]:
  """Merge two JSON schemas, with overlay taking precedence.

  Handles special JSON Schema keywords that require array union (required)
  vs object merge (properties) vs replacement (other fields).

  Args:
  ----
    base: The base schema to merge into.
    overlay: The schema to merge on top.

  Returns:
  -------
    A new merged schema dictionary.

  """
  result = base.copy()

  for key, value in overlay.items():
    if key == "properties" and "properties" in result:
      # Merge properties objects
      result["properties"] = {**result["properties"], **value}
    elif key == "required" and "required" in result:
      # Union of required arrays (deduplicated)
      result["required"] = list(set(result["required"]) | set(value))
    elif key == "additionalProperties" and key in result:
      # Overlay wins for additionalProperties
      result[key] = value
    else:
      # Default: overlay replaces base
      result[key] = value

  return result


def resolve_schema(
  schema: dict[str, Any],
  root_data: dict[str, Any],
  file_loader: Callable | None = None,
  visited: set[str] | None = None,
) -> dict[str, Any]:
  """Recursively resolve $ref and allOf in a JSON schema.

  This flattens composed schemas into a single schema with merged properties,
  which is useful for documentation rendering.

  Args:
  ----
    schema: The schema to resolve.
    root_data: The root document (for resolving internal #/ refs).
    file_loader: Optional callable(filename) -> dict for loading external files.
    visited: Set of visited refs to prevent infinite recursion.

  Returns:
  -------
    A flattened schema with refs resolved and allOf merged.

  """
  if not isinstance(schema, dict):
    return schema

  if visited is None:
    visited = set()

  result = {}

  # Handle $ref first - resolve and merge
  if "$ref" in schema:
    ref = schema["$ref"]
    ref_id = ref  # Use ref string as visited key

    if ref_id not in visited:
      visited.add(ref_id)
      resolved = None

      if ref.startswith("#/") or ref == "#":
        # Internal reference
        resolved = resolve_internal_ref(ref, root_data)
      elif file_loader and not ref.startswith("http"):
        # External file reference
        file_part = ref.split("#")[0]
        anchor_part = ref.split("#")[1] if "#" in ref else None

        ext_data = file_loader(file_part)
        if ext_data:
          if anchor_part:
            resolved = resolve_internal_ref("#" + anchor_part, ext_data)
          else:
            resolved = ext_data

      if resolved:
        # Recursively resolve the referenced schema
        resolved = resolve_schema(resolved, root_data, file_loader, visited)
        result = merge_schemas(result, resolved)

      visited.discard(ref_id)

  # Handle allOf - resolve each and merge
  if "allOf" in schema:
    for item in schema["allOf"]:
      resolved_item = resolve_schema(item, root_data, file_loader, visited)
      result = merge_schemas(result, resolved_item)

  # Copy over remaining fields (excluding $ref and allOf which we handled)
  for key, value in schema.items():
    if key in ("$ref", "allOf"):
      continue
    if key not in result:
      result[key] = value

  return result
