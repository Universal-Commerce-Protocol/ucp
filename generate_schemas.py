#   Copyright 2025 Google LLC
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

"""Generates spec/ schemas from annotated source/ schemas.

Processes UCP annotations (ucp_request, ucp_response) and produces per-operation
JSON Schema output. Files with annotations generate:

  - type.create_req.json, type.update_req.json, type_resp.json
Files without annotations are copied as-is. $refs to annotated schemas are
rewritten to point to the appropriate per-operation variant.
Usage: python generate_schemas.py
"""

import copy
import json
import os
import shutil
import sys
from typing import Any, Optional

import schema_utils

SOURCE_DIR = "source"
SPEC_DIR = "spec"
REQUEST_OPERATIONS = ["create", "update"]
UCP_ANNOTATIONS = {"ucp_request", "ucp_response", "ucp_shared_request"}

# Valid annotation values
VALID_REQUEST_VALUES = {"omit", "optional", "required"}
VALID_RESPONSE_VALUES = {"omit"}


def get_visibility(prop: Any, operation: Optional[str]) -> tuple[str, bool]:
  """Returns (visibility, has_explicit_annotation) for a field."""
  if not isinstance(prop, dict):
    return "include", False

  if operation:  # Request
    ann = prop.get("ucp_request")
    if ann is None:
      return "include", False
    if isinstance(ann, str):
      return ann, True
    return ann.get(operation, "include"), True
  else:  # Response
    return ("omit" if prop.get("ucp_response") == "omit" else "include"), False


def has_ucp_annotations(data: Any) -> bool:
  """Checks if schema contains any ucp_* annotations."""
  if isinstance(data, dict):
    if any(k in UCP_ANNOTATIONS for k in data):
      return True
    return any(has_ucp_annotations(v) for v in data.values())
  if isinstance(data, list):
    return any(has_ucp_annotations(item) for item in data)
  return False


def validate_ucp_annotations(data: Any, path: str = "") -> list[str]:
  """Validates ucp_* annotations in source schema. Returns list of errors."""
  errors = []

  if isinstance(data, dict):
    for key, value in data.items():
      current_path = f"{path}.{key}" if path else key

      if key.startswith("ucp_") and key not in UCP_ANNOTATIONS:
        errors.append(f"{current_path}: unknown annotation '{key}'")
        continue

      if key == "ucp_request":
        if isinstance(value, str):
          if value not in VALID_REQUEST_VALUES:
            errors.append(f"{current_path}: invalid value '{value}'")
        elif isinstance(value, dict):
          for op, op_value in value.items():
            if op not in REQUEST_OPERATIONS:
              errors.append(f"{current_path}.{op}: unknown operation '{op}'")
            elif op_value not in VALID_REQUEST_VALUES:
              errors.append(f"{current_path}.{op}: invalid value '{op_value}'")
        else:
          errors.append(f"{current_path}: must be string or object")

      elif key == "ucp_response":
        if not isinstance(value, str) or value not in VALID_RESPONSE_VALUES:
          errors.append(f"{current_path}: invalid value '{value}'")

      else:
        errors.extend(validate_ucp_annotations(value, current_path))

  elif isinstance(data, list):
    for i, item in enumerate(data):
      errors.extend(validate_ucp_annotations(item, f"{path}[{i}]"))

  return errors


# --- Pass 1: Collect annotated schemas ---


def collect_annotated_schemas(source_dir: str) -> dict[str, bool]:
  """Walks source dir and returns dict of absolute paths -> is_shared_request."""
  annotated = {}
  for root, _, files in os.walk(source_dir):
    for filename in files:
      if not filename.endswith(".json"):
        continue
      filepath = os.path.join(root, filename)
      data = schema_utils.load_json(filepath)
      if data and has_ucp_annotations(data):
        is_shared = (
            data.get("ucp_shared_request", False)
            if isinstance(data, dict)
            else False
        )
        annotated[os.path.normpath(filepath)] = is_shared
  return annotated


# --- Pass 2: Transform with ref rewriting ---


def rewrite_ref(
    ref: str,
    current_file: str,
    annotated_schemas: dict[str, bool],
    operation: Optional[str],
) -> str:
  """Rewrites $ref if target is an annotated schema.

  For annotated targets:
    - operation="create"|"update" -> type.{op}_req.json (or type.req.json if
    shared)
    - operation=None (response) -> type_resp.json

  Args:
    ref: The $ref value.
    current_file: Absolute path of file containing the ref.
    annotated_schemas: Dict of paths to annotated schemas -> is_shared_request.
    operation: Request operation ('create' or 'update') or None for response.

  Returns:
    The rewritten $ref, or original if no rewrite is needed.
  """
  target_path = schema_utils.resolve_ref_path(ref, current_file)
  if target_path is None or target_path not in annotated_schemas:
    return ref  # Internal ref, external URL, or non-annotated file

  is_shared = annotated_schemas[target_path]

  # Split ref into file and anchor parts
  parts = ref.split("#")
  file_part = parts[0]
  anchor_part = f"#{parts[1]}" if len(parts) > 1 else ""

  # Transform filename: types/line_item.json -> types/line_item.create_req.json
  base, ext = os.path.splitext(file_part)
  if operation:
    if is_shared:
      new_file = f"{base}_req{ext}"
    else:
      new_file = f"{base}.{operation}_req{ext}"
  else:
    new_file = f"{base}_resp{ext}"

  return new_file + anchor_part


def transform_schema(
    data: Any,
    operation: Optional[str],
    current_file: str,
    annotated_schemas: dict[str, bool],
    title_suffix: str = "",
) -> Any:
  """Transforms schema for a specific operation (or response if None).

  - Filters fields based on visibility annotations - Adjusts required array
  (base required preserved, annotations override) - Rewrites $refs to annotated
  schemas - Strips ucp_* annotations from output - Preserves source key ordering
  - Appends title_suffix to "title" fields in definitions to avoid name
  collisions.

  Args:
    data: Schema data to transform.
    operation: Request operation ('create' or 'update') or None for response.
    current_file: Absolute path of file containing the schema data.
    annotated_schemas: Set of paths to annotated schemas for ref rewriting.
    title_suffix: Suffix to append to titles (e.g., " Create Request").

  Returns:
    Transformed schema data.
  """
  if isinstance(data, dict):
    # Handle $ref rewriting
    if "$ref" in data:
      new_ref = rewrite_ref(
          data["$ref"], current_file, annotated_schemas, operation
      )
      result = {}
      for k, v in data.items():
        if k == "$ref":
          result[k] = new_ref
        elif k not in UCP_ANNOTATIONS:
          result[k] = transform_schema(
              v, operation, current_file, annotated_schemas, title_suffix
          )
      return result

    if "properties" not in data:
      result = {
          k: transform_schema(
              v, operation, current_file, annotated_schemas, title_suffix
          )
          for k, v in data.items()
          if k not in UCP_ANNOTATIONS
      }
      # Update title if we are in a definition context (heuristic: has title and
      # type/properties or is inside $defs) Actually, we just update any title
      # we see, assuming it's a type definition.
      if "title" in result and title_suffix:
        result["title"] += title_suffix
      return result

    props = data["properties"]
    base_required = set(data.get("required", []))
    new_props = {}
    new_required = []

    for name, field in props.items():
      visibility, has_annotation = get_visibility(field, operation)

      if visibility == "omit":
        continue

      new_props[name] = transform_schema(
          field, operation, current_file, annotated_schemas, title_suffix
      )

      if visibility == "required":
        new_required.append(name)
      elif visibility == "optional" and has_annotation:
        pass
      elif name in base_required:
        new_required.append(name)

    result = {}
    for k, v in data.items():
      if k in UCP_ANNOTATIONS:
        continue
      elif k == "properties":
        result["properties"] = new_props
      elif k == "required":
        if new_required:
          result["required"] = new_required
      else:
        result[k] = transform_schema(
            v, operation, current_file, annotated_schemas, title_suffix
        )

    if "title" in result and title_suffix:
      result["title"] += title_suffix

    return result

  if isinstance(data, list):
    return [
        transform_schema(
            item, operation, current_file, annotated_schemas, title_suffix
        )
        for item in data
    ]

  return data


def write_json(data: dict[str, Any], path: str) -> None:
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")


def process_schema(
    source_path: str,
    dest_dir: str,
    rel_path: str,
    annotated_schemas: dict[str, bool],
) -> tuple[list[str], list[str]]:
  """Processes schema file. Returns (generated_paths, validation_errors)."""
  data = schema_utils.load_json(source_path)
  if data is None:
    return [], [f"Error reading {source_path}"]

  validation_errors = validate_ucp_annotations(data)
  if validation_errors:
    return [], [f"{rel_path}: {err}" for err in validation_errors]

  dir_path = os.path.dirname(rel_path)
  stem = os.path.splitext(os.path.basename(rel_path))[0]
  generated = []
  source_path_norm = os.path.normpath(source_path)

  if source_path_norm in annotated_schemas:
    is_shared = annotated_schemas[source_path_norm]

    # Generate request schemas
    if is_shared:
      # Generate single shared request schema
      out_name = f"{stem}_req.json"
      out_path = os.path.join(dest_dir, dir_path, out_name)
      # Use 'create' as representative operation for shared request
      suffix = " Request"
      transformed = transform_schema(
          copy.deepcopy(data), "create", source_path, annotated_schemas, suffix
      )
      if "$id" in transformed:
        transformed["$id"] = transformed["$id"].replace(".json", "_req.json")
      write_json(transformed, out_path)
      generated.append(os.path.join(dir_path, out_name))
    else:
      # Generate per-operation request schemas
      for op in REQUEST_OPERATIONS:
        out_name = f"{stem}.{op}_req.json"
        out_path = os.path.join(dest_dir, dir_path, out_name)
        suffix = f" {op.capitalize()} Request"
        transformed = transform_schema(
            copy.deepcopy(data), op, source_path, annotated_schemas, suffix
        )
        if "$id" in transformed:
          transformed["$id"] = transformed["$id"].replace(
              ".json", f".{op}_req.json"
          )
        write_json(transformed, out_path)
        generated.append(os.path.join(dir_path, out_name))

    # Generate response schema
    out_name = f"{stem}_resp.json"
    out_path = os.path.join(dest_dir, dir_path, out_name)
    suffix = " Response"
    transformed = transform_schema(
        data, None, source_path, annotated_schemas, suffix
    )
    if "$id" in transformed:
      transformed["$id"] = transformed["$id"].replace(".json", "_resp.json")
    write_json(transformed, out_path)
    generated.append(os.path.join(dir_path, out_name))
  else:
    # Non-annotated: copy with refs potentially rewritten
    out_path = os.path.join(dest_dir, rel_path)
    transformed = transform_schema(
        data, None, source_path, annotated_schemas, ""
    )
    write_json(transformed, out_path)
    generated.append(rel_path)

  return generated, []


def main() -> None:
  if not os.path.exists(SOURCE_DIR):
    print(
        f"{schema_utils.Colors.RED}Error: '{SOURCE_DIR}' not"
        f" found.{schema_utils.Colors.RESET}"
    )
    sys.exit(1)

  # Pass 1: Collect annotated schemas
  print(
      f"{schema_utils.Colors.CYAN}Pass 1: Scanning for annotated"
      f" schemas...{schema_utils.Colors.RESET}"
  )
  annotated_schemas = collect_annotated_schemas(SOURCE_DIR)
  print(f"  Found {len(annotated_schemas)} annotated schema(s)\n")

  if os.path.exists(SPEC_DIR):
    print(
        f"{schema_utils.Colors.YELLOW}Removing existing {SPEC_DIR}/"
        f" ...{schema_utils.Colors.RESET}"
    )
    shutil.rmtree(SPEC_DIR)

  # Pass 2: Transform and generate
  print(
      f"{schema_utils.Colors.CYAN}Pass 2: Generating {SOURCE_DIR}/ ->"
      f" {SPEC_DIR}/{schema_utils.Colors.RESET}\n"
  )

  generated_count = 0
  all_errors = []

  for root, _, files in os.walk(SOURCE_DIR):
    for filename in files:
      if filename.startswith("."):
        continue

      source_path = os.path.join(root, filename)
      rel_path = os.path.relpath(source_path, SOURCE_DIR)

      if filename.endswith(".json") and filename not in [
          "openapi.json",
          "openrpc.json",
      ]:
        generated, errors = process_schema(
            source_path, SPEC_DIR, rel_path, annotated_schemas
        )
        for g in generated:
          print(f"{schema_utils.Colors.GREEN}✓{schema_utils.Colors.RESET} {g}")
        generated_count += len(generated)
        all_errors.extend(errors)
      else:
        dest_path = os.path.join(SPEC_DIR, rel_path)
        try:
          os.makedirs(os.path.dirname(dest_path), exist_ok=True)
          shutil.copy2(source_path, dest_path)
          print(
              f"{schema_utils.Colors.GREEN}✓{schema_utils.Colors.RESET} {rel_path}"
          )
          generated_count += 1
        except OSError as e:
          all_errors.append(f"Error copying {source_path}: {e}")

  print()
  if all_errors:
    print(f"{schema_utils.Colors.RED}Errors:{schema_utils.Colors.RESET}")
    for err in all_errors:
      print(f"  {schema_utils.Colors.RED}✗{schema_utils.Colors.RESET} {err}")
    print(
        f"\n{schema_utils.Colors.RED}🚨 Failed with"
        f" {len(all_errors)} errors.{schema_utils.Colors.RESET}"
    )
    sys.exit(1)
  else:
    print(
        f"{schema_utils.Colors.GREEN}✅ Generated"
        f" {generated_count} files.{schema_utils.Colors.RESET}"
    )
    sys.exit(0)


if __name__ == "__main__":
  main()
