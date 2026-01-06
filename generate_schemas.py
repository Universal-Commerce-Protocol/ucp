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

"""Generates spec/ from annotated source/ schemas and ECP definitions.

Pass 1-2: Processes UCP annotations (ucp_request, ucp_response) and produces
per-operation JSON Schema output. Files with annotations generate:
  - type.create_req.json, type.update_req.json, type_resp.json
Files without annotations are copied as-is. $refs to annotated schemas are
rewritten to point to the appropriate per-operation variant.

Pass 3: Generates Embedded Protocol OpenRPC spec by aggregating methods
from source/services/shopping/embedded.json and extension schemas.

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

# ECP constants
ECP_SOURCE_FILE = "source/services/shopping/embedded.json"
ECP_SCHEMAS_DIR = "source/schemas/shopping"
ECP_VERSION = "2026-01-11"


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


# =============================================================================
# EP (Embedded Protocol) Generation
# =============================================================================


def rewrite_refs_for_ecp(data: Any, annotated_schemas: set[str]) -> Any:
  """Rewrite $refs in ECP methods to point to spec/ schema paths.

  Source embedded.json uses refs like ../../schemas/shopping/checkout.json
  which need _resp suffix for annotated schemas.

  Args:
    data: Schema data to rewrite refs for.
    annotated_schemas: Set of annotated schema paths.

  Returns:
    Schema data with rewritten refs.
  """
  if isinstance(data, dict):
    result = {}
    for k, v in data.items():
      if k == "$ref" and isinstance(v, str) and not v.startswith("#"):
        if "schemas/shopping/" in v:
          parts = v.split("schemas/shopping/")
          if len(parts) == 2:
            schema_path = parts[1]
            anchor_part = ""
            if "#" in schema_path:
              schema_path, anchor_part = schema_path.split("#", 1)
              anchor_part = "#" + anchor_part
            # Add _resp suffix if schema has ucp annotations
            if schema_path in annotated_schemas and schema_path.endswith(
                ".json"
            ):
              schema_path = schema_path[:-5] + "_resp.json"
            result[k] = f"../../schemas/shopping/{schema_path}{anchor_part}"
          else:
            result[k] = v
        else:
          result[k] = v
      else:
        result[k] = rewrite_refs_for_ecp(v, annotated_schemas)
    return result
  elif isinstance(data, list):
    return [rewrite_refs_for_ecp(item, annotated_schemas) for item in data]
  return data


def transform_ecp_method(
    method: dict[str, Any], annotated_schemas: set[str]
) -> dict[str, Any]:
  """Transform an ECP method definition to OpenRPC format."""
  openrpc_method = {
      "name": method["name"],
      "summary": method.get("summary", ""),
  }
  if method.get("description"):
    openrpc_method["description"] = method["description"]

  if "params" in method:
    openrpc_method["params"] = []
    for param in method["params"]:
      openrpc_param = {
          "name": param["name"],
          "required": param.get("required", False),
          "schema": rewrite_refs_for_ecp(param["schema"], annotated_schemas),
      }
      if "description" in param.get("schema", {}):
        openrpc_param["description"] = param["schema"]["description"]
      openrpc_method["params"].append(openrpc_param)

  if "result" in method:
    result = method["result"]
    openrpc_method["result"] = {
        "name": result.get("name", "result"),
        "schema": rewrite_refs_for_ecp(result["schema"], annotated_schemas),
    }

  if "errors" in method:
    openrpc_method["errors"] = method["errors"]

  return openrpc_method


def generate_ecp_spec(annotated_schemas: set[str]) -> int:
  """Generate Embedded Protocol OpenRPC spec.

  Args:
    annotated_schemas: Set of annotated schema paths.

  Returns:
    number of files generated.
  """
  print(
      f"\n{schema_utils.Colors.CYAN}Pass 3: Generating ECP OpenRPC"
      f" spec...{schema_utils.Colors.RESET}\n"
  )

  methods = []
  delegations = []
  ep_title = "Embedded Protocol"
  ep_description = "Embedded Protocol methods for UCP capabilities."

  # Collect core methods from embedded.json
  if os.path.exists(ECP_SOURCE_FILE):
    with open(ECP_SOURCE_FILE, "r") as f:
      data = json.load(f)
    ep_title = data.get("title", ep_title)
    ep_description = data.get("description", ep_description)
    if "methods" in data:
      for method in data["methods"]:
        methods.append(transform_ecp_method(method, annotated_schemas))
    if "delegations" in data:
      delegations.extend(data["delegations"])
    print(f"  From embedded.json: {len(methods)} methods")

  # Collect extension methods from schema files with "embedded" blocks
  ext_count = 0
  if os.path.exists(ECP_SCHEMAS_DIR):
    for filename in os.listdir(ECP_SCHEMAS_DIR):
      if not filename.endswith(".json"):
        continue
      if filename in ["checkout.json", "payment.json", "order.json"]:
        continue
      filepath = os.path.join(ECP_SCHEMAS_DIR, filename)
      with open(filepath, "r") as f:
        data = json.load(f)
      if "embedded" not in data:
        continue
      embedded_block = data["embedded"]
      if "methods" in embedded_block:
        for method in embedded_block["methods"]:
          methods.append(transform_ecp_method(method, annotated_schemas))
          ext_count += 1
      if "delegations" in embedded_block:
        delegations.extend(embedded_block["delegations"])

  if ext_count:
    print(f"  From extensions: {ext_count} methods")

  print(f"\n  Total: {len(methods)} methods")
  print(f"  Delegations: {list(set(delegations))}\n")

  # Generate OpenRPC spec
  spec = {
      "openrpc": "1.3.2",
      "info": {
          "title": ep_title,
          "description": ep_description,
          "version": ECP_VERSION,
      },
      "x-delegations": sorted(set(delegations)),
      "methods": methods,
  }

  out_path = os.path.join(SPEC_DIR, "services/shopping/embedded.openrpc.json")
  os.makedirs(os.path.dirname(out_path), exist_ok=True)
  write_json(spec, out_path)
  print(
      f"{schema_utils.Colors.GREEN}✓{schema_utils.Colors.RESET}"
      " services/shopping/embedded.openrpc.json"
  )

  return 1


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

      # Skip embedded.json - we generate embedded.openrpc.json in Pass 3
      if filename == "embedded.json":
        continue

      # Rename transport specs in services/ to use
      # {transport}.{format}.json naming
      transport_renames = {}
      if rel_path.startswith("services/"):
        transport_renames = {
            "openapi.json": "rest.openapi.json",
            "openrpc.json": "mcp.openrpc.json",
        }

      # Process JSON schemas, copy other files as-is
      if filename.endswith(".json") and filename not in transport_renames:
        generated, errors = process_schema(
            source_path, SPEC_DIR, rel_path, annotated_schemas
        )
        for g in generated:
          print(f"{schema_utils.Colors.GREEN}✓{schema_utils.Colors.RESET} {g}")
        generated_count += len(generated)
        all_errors.extend(errors)
      else:
        # Apply rename if this is a services/ transport spec
        dest_filename = transport_renames.get(filename, filename)
        dest_rel_path = os.path.join(os.path.dirname(rel_path), dest_filename)
        dest_path = os.path.join(SPEC_DIR, dest_rel_path)
        try:
          os.makedirs(os.path.dirname(dest_path), exist_ok=True)
          shutil.copy2(source_path, dest_path)
          print(
              f"{schema_utils.Colors.GREEN}✓{schema_utils.Colors.RESET}"
              f" {dest_rel_path}"
          )
          generated_count += 1
        except OSError as e:
          all_errors.append(f"Error copying {source_path}: {e}")

  # Pass 3: Generate ECP OpenRPC spec
  # Convert annotated_schemas to relative paths for ECP ref rewriting
  schemas_base = os.path.normpath(os.path.join(SOURCE_DIR, "schemas/shopping"))
  ecp_annotated = set()
  for abs_path in annotated_schemas:
    if schemas_base in abs_path:
      rel_path = os.path.relpath(abs_path, schemas_base)
      ecp_annotated.add(rel_path)
  ecp_count = generate_ecp_spec(ecp_annotated)
  generated_count += ecp_count

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
