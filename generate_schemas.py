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

"""Generates spec/ from annotated source/ schemas and ECP definitions.

Pass 1-2: Processes UCP annotations (ucp_request, ucp_response) and produces
per-operation JSON Schema output. Files with annotations generate:
  - type.create_req.json, type.update_req.json, type_resp.json
Files without annotations are copied as-is. $refs to annotated schemas are
rewritten to point to the appropriate per-operation variant.

Pass 3: Generates Embedded Protocol OpenRPC spec by aggregating methods
from source/services/shopping/embedded.json and extension schemas.

Usage: uv run generate_schemas.py
"""

import copy
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import schema_utils

SOURCE_DIR = "source"
SPEC_DIR = "spec"
REQUEST_OPERATIONS = ["create", "update", "complete"]
UCP_ANNOTATIONS = {"ucp_request", "ucp_response", "ucp_shared_request"}

# Valid annotation values
VALID_REQUEST_VALUES = {"omit", "optional", "required"}
VALID_RESPONSE_VALUES = {"omit"}

# ECP constants
ECP_SOURCE_FILE = "source/services/shopping/embedded.json"
ECP_SCHEMAS_DIR = "source/schemas/shopping"
ECP_VERSION = "2026-01-11"


def get_visibility(prop: Any, operation: str | None) -> tuple[str, bool]:
  """Return (visibility, has_explicit_annotation) for a field."""
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
  """Check if schema contains any ucp_* annotations."""
  if isinstance(data, dict):
    if any(k in UCP_ANNOTATIONS for k in data):
      return True
    return any(has_ucp_annotations(v) for v in data.values())
  if isinstance(data, list):
    return any(has_ucp_annotations(item) for item in data)
  return False


def validate_ucp_annotations(data: Any, path: str = "") -> list[str]:
  """Validate ucp_* annotations in source schema. Return list of errors."""
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
  """Walk source dir and return dict of absolute paths -> is_shared_request."""
  annotated = {}
  for root, _, files in os.walk(source_dir):
    for filename in files:
      if not filename.endswith(".json"):
        continue
      filepath = Path(root) / filename
      data = schema_utils.load_json(filepath)
      if data and has_ucp_annotations(data):
        is_shared = (
          data.get("ucp_shared_request", False)
          if isinstance(data, dict)
          else False
        )
        annotated[str(filepath.resolve())] = is_shared
  return annotated


# --- Pass 2: Transform with ref rewriting ---


def rewrite_ref(
  ref: str,
  current_file: str,
  annotated_schemas: dict[str, bool],
  operation: str | None,
) -> str:
  """Rewrite $ref if target is an annotated schema.

  For annotated targets:
    - operation="create"|"update" -> type.{op}_req.json (or type.req.json if
    shared)
    - operation=None (response) -> type_resp.json

  Args:
  ----
    ref: The $ref value.
    current_file: Absolute path of file containing the ref.
    annotated_schemas: Dict of paths to annotated schemas -> is_shared_request.
    operation: Request operation ('create' or 'update') or None for response.

  Returns:
  -------
    The rewritten $ref, or original if no rewrite is needed.

  """
  target_path = schema_utils.resolve_ref_path(ref, current_file)
  if target_path is None or str(target_path) not in annotated_schemas:
    return ref  # Internal ref, external URL, or non-annotated file

  is_shared = annotated_schemas[str(target_path)]

  # Split ref into file and anchor parts
  parts = ref.split("#")
  file_part = parts[0]
  anchor_part = f"#{parts[1]}" if len(parts) > 1 else ""

  # Transform filename: types/line_item.json -> types/line_item.create_req.json
  file_path = Path(file_part)
  if operation:
    if is_shared:
      new_file = file_path.parent / f"{file_path.stem}_req{file_path.suffix}"
    else:
      new_file = (
        file_path.parent / f"{file_path.stem}.{operation}_req{file_path.suffix}"
      )
  else:
    new_file = file_path.parent / f"{file_path.stem}_resp{file_path.suffix}"

  return new_file.as_posix() + anchor_part


def transform_schema(
  data: Any,
  operation: str | None,
  current_file: str,
  annotated_schemas: dict[str, bool],
  title_suffix: str = "",
) -> Any:
  """Transform schema for a specific operation (or response if None).

  - Filters fields based on visibility annotations - Adjusts required array
  (base required preserved, annotations override) - Rewrites $refs to annotated
  schemas - Strips ucp_* annotations from output - Preserves source key ordering
  - Appends title_suffix to "title" fields in definitions to avoid name
  collisions.

  Args:
  ----
    data: Schema data to transform.
    operation: Request operation ('create' or 'update') or None for response.
    current_file: Absolute path of file containing the schema data.
    annotated_schemas: Set of paths to annotated schemas for ref rewriting.
    title_suffix: Suffix to append to titles (e.g., " Create Request").

  Returns:
  -------
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


def write_json(data: dict[str, Any], path: str | Path) -> None:
  """Write JSON data to path, creating directories if needed."""
  Path(path).parent.mkdir(parents=True, exist_ok=True)
  with Path(path).open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")


def process_openapi_schema_schema(
  source_path: str,
  dest_dir: str,
  rel_path: str,
  annotated_schemas: dict[str, bool],
) -> tuple[list[str], list[str]]:
  """Process schema file. Return (generated_paths, validation_errors)."""
  data = schema_utils.load_json(source_path)
  if data is None:
    return [], [f"Error reading {source_path}"]

  validation_errors = validate_ucp_annotations(data)
  if validation_errors:
    return [], [f"{rel_path}: {err}" for err in validation_errors]

  dir_path = Path(rel_path).parent
  stem = Path(rel_path).stem
  generated = []
  source_path_norm = str(Path(source_path).resolve())

  if source_path_norm in annotated_schemas:
    is_shared = annotated_schemas[source_path_norm]

    # Generate request schemas
    if is_shared:
      # Generate single shared request schema
      out_name = f"{stem}_req.json"
      out_path = Path(dest_dir) / dir_path / out_name
      # Use 'create' as representative operation for shared request
      suffix = " Request"
      transformed = transform_schema(
        copy.deepcopy(data), "create", source_path, annotated_schemas, suffix
      )
      if "$id" in transformed:
        transformed["$id"] = transformed["$id"].replace(".json", "_req.json")
      write_json(transformed, out_path)
      generated.append(str(dir_path / out_name))
    else:
      # Generate per-operation request schemas
      for op in REQUEST_OPERATIONS:
        out_name = f"{stem}.{op}_req.json"
        out_path = Path(dest_dir) / dir_path / out_name
        suffix = f" {op.capitalize()} Request"
        transformed = transform_schema(
          copy.deepcopy(data), op, source_path, annotated_schemas, suffix
        )
        if "$id" in transformed:
          transformed["$id"] = transformed["$id"].replace(
            ".json", f".{op}_req.json"
          )
        write_json(transformed, out_path)
        generated.append(str(dir_path / out_name))

    # Generate response schema
    out_name = f"{stem}_resp.json"
    out_path = Path(dest_dir) / dir_path / out_name
    suffix = " Response"
    transformed = transform_schema(
      data, None, source_path, annotated_schemas, suffix
    )
    write_json(transformed, out_path)
    generated.append(str(dir_path / out_name))
  else:
    # Non-annotated: copy with refs potentially rewritten
    out_path = Path(dest_dir) / rel_path
    transformed = transform_schema(
      data, None, source_path, annotated_schemas, ""
    )
    write_json(transformed, out_path)
    generated.append(rel_path)

  return generated, []


# =============================================================================
# OpenAPI Schema Generation
# =============================================================================


def process_openapi_schema(
  source_path: str, dest_path: str, annotated_schemas: dict[str, bool]
) -> None:
  """Split components and convert refs. Preserve absolute URLs if present."""
  spec = schema_utils.load_json(source_path)
  if not spec or "components" not in spec:
    return

  ref_map = {}
  schemas = spec["components"].get("schemas", {})
  source_dir_abs = Path(source_path).resolve().parent

  for name, schema in list(schemas.items()):
    ref = schema.get("$ref", "")

    # 1. Find the local file that matches this Ref
    found_path = None
    if not (ref.startswith("http:") or ref.startswith("#")):
      # Resolve the ref path relative to the openapi.json file's location
      # and check if its absolute path is in the annotated list.
      resolved_ref_path = (source_dir_abs / ref).resolve()
      if str(resolved_ref_path) in annotated_schemas:
        found_path = str(resolved_ref_path)

    if found_path:
      is_shared = annotated_schemas[found_path]

      # 2. Calculate the base for the new $ref
      # If the original ref was a URL, keep it a URL.
      # If it was a local file path, keep it relative.
      if ref.startswith("http:") or ref.startswith("https:"):
        # Remove extension from URL while preserving path
        base_ref = ref.rsplit(".", 1)[0] if "." in ref.split("/")[-1] else ref
      else:
        # The ref from the source openapi.json already has the correct
        # relative path. We just need to strip the extension.
        base_ref = ref.rsplit(".json", 1)[0]

      # 3. Create Split Components
      # Response (always exists)
      resp_comp = f"{name}_response"
      schemas[resp_comp] = {"$ref": f"{base_ref}_resp.json"}

      req_refs = {}
      if is_shared:
        req_comp = f"{name}_request"
        schemas[req_comp] = {"$ref": f"{base_ref}_req.json"}
        req_refs["create"] = req_refs["update"] = req_refs["complete"] = (
          f"#/components/schemas/{req_comp}"
        )
      else:
        create_comp = f"{name}_create_request"
        schemas[create_comp] = {"$ref": f"{base_ref}.create_req.json"}

        update_comp = f"{name}_update_request"
        schemas[update_comp] = {"$ref": f"{base_ref}.update_req.json"}

        complete_comp = f"{name}_complete_request"
        schemas[complete_comp] = {"$ref": f"{base_ref}.complete_req.json"}

        req_refs["create"] = f"#/components/schemas/{create_comp}"
        req_refs["update"] = f"#/components/schemas/{update_comp}"
        req_refs["complete"] = f"#/components/schemas/{complete_comp}"

      # 4. Map Old -> New and Delete
      ref_map[f"#/components/schemas/{name}"] = {
        "response": f"#/components/schemas/{resp_comp}",
        **req_refs,
      }
      del schemas[name]

  # --- Update Paths ---
  def update_node(node: Any, ctx: str):
    if isinstance(node, dict):
      if (
        "$ref" in node
        and node["$ref"] in ref_map
        and ctx in ref_map[node["$ref"]]
      ):
        node["$ref"] = ref_map[node["$ref"]][ctx]
      for v in node.values():
        update_node(v, ctx)
    elif isinstance(node, list):
      for v in node:
        update_node(v, ctx)

  for root in [spec.get("paths", {}), spec.get("webhooks", {})]:
    for path, path_item in root.items():
      for method, op in path_item.items():
        if method in ["parameters", "summary", "description", "$ref"]:
          continue

        # Determine request context based on method and path
        if method == "post":
          # Check if this is a complete operation
          if path.endswith("/complete") or op.get("operationId", "").startswith(
            "complete_"
          ):
            req_ctx = "complete"
          else:
            req_ctx = "create"
        elif method in ["put", "patch"]:
          req_ctx = "update"
        else:
          req_ctx = "read"

        if "requestBody" in op:
          update_node(op["requestBody"], req_ctx)
        if "responses" in op:
          update_node(op["responses"], "response")

  write_json(spec, dest_path)


# =============================================================================
# OpenRPC Schema Generation
# =============================================================================


def process_openrpc_schema(
  source_path: str, dest_path: str, annotated_schemas: dict[str, bool]
) -> None:
  """Rewrites refs in OpenRPC methods to use operation-specific schemas."""
  spec = schema_utils.load_json(source_path)
  if not spec or "methods" not in spec:
    return

  def rewrite_schema_ref(schema: Any, operation: str) -> Any:
    """Recursively rewrite $refs in schema based on operation type."""
    if isinstance(schema, dict):
      if "$ref" in schema:
        ref = schema["$ref"]
        # Find if this ref points to an annotated schema
        found_path = None
        for path in annotated_schemas:
          path_suffix = os.path.relpath(path, SOURCE_DIR).replace(os.sep, "/")
          if ref.endswith(path_suffix) or path_suffix in ref:
            found_path = path
            break

        if found_path:
          is_shared = annotated_schemas[found_path]
          # Rewrite the ref to point to the operation-specific schema
          if ref.startswith("http:") or ref.startswith("https:"):
            base_ref, ext = ref.rsplit(".", 1) if "." in ref else (ref, "json")
          else:
            p_ref = Path(ref)
            base_ref, ext = str(p_ref.with_suffix("")), p_ref.suffix
            ext = ext[1:] if ext.startswith(".") else ext

          if operation in ["create", "update", "complete"]:
            if is_shared:
              new_ref = f"{base_ref}_req.{ext}"
            else:
              new_ref = f"{base_ref}.{operation}_req.{ext}"
          else:
            new_ref = f"{base_ref}_resp.{ext}"

          return {**schema, "$ref": new_ref}

      # Recursively process nested schemas
      return {k: rewrite_schema_ref(v, operation) for k, v in schema.items()}
    elif isinstance(schema, list):
      return [rewrite_schema_ref(item, operation) for item in schema]
    return schema

  # Process each method
  for method in spec.get("methods", []):
    method_name = method.get("name", "")

    # Determine operation type from method name
    if "complete" in method_name or method_name.endswith(".complete"):
      operation = "complete"
    elif "create" in method_name:
      operation = "create"
    elif "update" in method_name:
      operation = "update"
    else:
      operation = "read"

    # Rewrite refs in params
    if "params" in method:
      for param in method["params"]:
        if "schema" in param:
          param["schema"] = rewrite_schema_ref(param["schema"], operation)

    # Rewrite refs in result (always response)
    if "result" in method and "schema" in method["result"]:
      method["result"]["schema"] = rewrite_schema_ref(
        method["result"]["schema"], "response"
      )

  write_json(spec, dest_path)


# =============================================================================
# EP (Embedded Protocol) Generation
# =============================================================================


def rewrite_refs_for_ecp(data: Any, annotated_schemas: set[str]) -> Any:
  """Rewrite $refs in ECP methods to point to spec/ schema paths.

  Source embedded.json uses refs like ../../schemas/shopping/checkout.json
  which need _resp suffix for annotated schemas.

  Args:
  ----
    data: Schema data to rewrite refs for.
    annotated_schemas: Set of annotated schema paths.

  Returns:
  -------
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
  ----
    annotated_schemas: Set of annotated schema paths.

  Returns:
  -------
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
  if Path(ECP_SOURCE_FILE).exists():
    with Path(ECP_SOURCE_FILE).open(encoding="utf-8") as f:
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
  if Path(ECP_SCHEMAS_DIR).exists():
    for filepath in Path(ECP_SCHEMAS_DIR).iterdir():
      if filepath.suffix != ".json":
        continue
      if filepath.name in ["checkout.json", "payment.json", "order.json"]:
        continue
      with filepath.open(encoding="utf-8") as f:
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

  out_path = Path(SPEC_DIR) / "services/shopping/embedded.openrpc.json"
  write_json(spec, out_path)
  print(
    f"{schema_utils.Colors.GREEN}✓{schema_utils.Colors.RESET}"
    " services/shopping/embedded.openrpc.json"
  )

  return 1


def main() -> None:
  """Run the schema generation process."""
  if not Path(SOURCE_DIR).exists():
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

  if Path(SPEC_DIR).exists():
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

      source_path = Path(root) / filename
      rel_path = source_path.relative_to(SOURCE_DIR)

      # 1. Special Handling: OpenAPI Spec (The Linker)
      if filename == "openapi.json" and str(rel_path).startswith("services/"):
        dest_rel = rel_path.parent / "rest.openapi.json"
        process_openapi_schema(
          str(source_path), str(Path(SPEC_DIR) / dest_rel), annotated_schemas
        )
        print(
          f"{schema_utils.Colors.GREEN}✓{schema_utils.Colors.RESET} {dest_rel}"
        )
        generated_count += 1

      # 2. Special Handling: Embedded Protocol (Skip, done in Pass 3)
      elif filename == "embedded.json":
        pass

      # 3. Special Handling: OpenRPC (The Linker for MCP)
      elif filename == "openrpc.json" and str(rel_path).startswith("services/"):
        dest_rel = rel_path.parent / "mcp.openrpc.json"
        process_openrpc_schema(
          str(source_path), str(Path(SPEC_DIR) / dest_rel), annotated_schemas
        )
        print(
          f"{schema_utils.Colors.GREEN}✓{schema_utils.Colors.RESET} {dest_rel}"
        )
        generated_count += 1

      # 4. Standard Handling: JSON Schemas (The Generator)
      elif filename.endswith(".json"):
        generated, errors = process_openapi_schema_schema(
          str(source_path), SPEC_DIR, str(rel_path), annotated_schemas
        )
        for g in generated:
          print(f"{schema_utils.Colors.GREEN}✓{schema_utils.Colors.RESET} {g}")
        generated_count += len(generated)
        all_errors.extend(errors)

      # 5. Fallback: Copy other files
      else:
        dest_name = (
          "mcp.openrpc.json" if filename == "openrpc.json" else filename
        )
        dest_rel_path = rel_path.parent / dest_name
        dest_path = Path(SPEC_DIR) / dest_rel_path
        try:
          dest_path.parent.mkdir(parents=True, exist_ok=True)
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
  schemas_base = (Path(SOURCE_DIR) / "schemas/shopping").resolve()
  ecp_annotated = set()
  for abs_path in annotated_schemas:
    if Path(abs_path).is_relative_to(schemas_base):
      rel_path = Path(abs_path).relative_to(schemas_base).as_posix()
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
