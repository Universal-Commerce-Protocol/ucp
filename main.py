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

"""MkDocs plugin to generate API documentation from OpenAPI and JSON Schemas.

This module defines custom macros for MkDocs (`schema_fields` and
`method_fields`) that parse OpenAPI specifications and JSON schema files
to automatically generate Markdown tables for API request and response
bodies.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

# --- CONFIGURATION ---
# Base directories for schema resolution
OPENAPI_DIR = Path("source/services/shopping")
SHOPPING_SCHEMAS_DIR = Path("source/schemas/shopping")
UCP_SCHEMA_PATH = Path("source/schemas/ucp.json")
SCHEMAS_DIRS = [
  Path("source/handlers/google_pay"),
  Path("source/schemas"),
  SHOPPING_SCHEMAS_DIR,
  SHOPPING_SCHEMAS_DIR / "types",
]

# Cache for resolved schemas to avoid repeated subprocess calls
_resolved_schema_cache: dict[str, dict] = {}


# --- HELPER FUNCTIONS ---
# These are thin wrappers; actual schema resolution is done by ucp-schema CLI.


def _load_json(path: str | Path) -> dict[str, Any] | None:
  """Load JSON file, returns None on error."""
  try:
    with Path(path).open(encoding="utf-8") as f:
      return json.load(f)
  except (json.JSONDecodeError, OSError):
    return None


def _resolve_json_pointer(pointer: str, data: Any) -> Any | None:
  """Navigate to a JSON pointer path (e.g., '#/$defs/foo' or '#/components/x').

  Args:
    pointer: JSON pointer starting with '#' (e.g., '#/$defs/allocation').
    data: The JSON data to navigate.

  Returns:
    The value at the pointer path, or None if not found.

  """
  if pointer == "#":
    return data
  if not pointer.startswith("#/"):
    return None

  path_parts = pointer[2:].split("/")  # Remove '#/' prefix and split
  current = data
  for part in path_parts:
    if isinstance(current, dict) and part in current:
      current = current[part]
    elif isinstance(current, list):
      try:
        current = current[int(part)]
      except (ValueError, IndexError):
        return None
    else:
      return None
  return current


def _resolve_schema(
  schema_path: str | Path,
  direction: str = "response",
  operation: str = "read",
  bundle: bool = False,
) -> dict[str, Any] | None:
  """Resolve a schema using ucp-schema CLI.

  Args:
    schema_path: Path to the schema file.
    direction: 'request' or 'response'.
    operation: 'create', 'update', 'complete', or 'read'.
    bundle: If True, inline all $ref pointers. If False, preserve $refs for
      hyperlink generation in documentation.

  Returns:
    Resolved schema as dict, or raises RuntimeError if ucp-schema fails.

  """
  bundle_suffix = ":bundled" if bundle else ""
  cache_key = f"{schema_path}:{direction}:{operation}{bundle_suffix}"
  if cache_key in _resolved_schema_cache:
    return _resolved_schema_cache[cache_key]

  dir_flag = "--request" if direction == "request" else "--response"
  cmd = [
    "ucp-schema",
    "resolve",
    str(schema_path),
    dir_flag,
    "--op",
    operation,
  ]
  if bundle:
    cmd.append("--bundle")

  result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    check=False,
  )
  if result.returncode == 0:
    data = json.loads(result.stdout)
    _resolved_schema_cache[cache_key] = data
    return data
  else:
    raise RuntimeError(f"ucp-schema execution error: result = {result}")


# Backward compatibility alias
def _resolve_schema_bundled(
  schema_path: str | Path,
  direction: str = "response",
  operation: str = "read",
) -> dict[str, Any] | None:
  """Resolve a schema with bundling (backward compat)."""
  return _resolve_schema(schema_path, direction, operation, bundle=True)


def define_env(env):
  """Injects custom macros into the MkDocs environment.

  This function is called by MkDocs and receives the `env` object,
  allowing it to register custom macros like `schema_fields` and
  `method_fields` for use in Markdown pages.

  Args:
  ----
    env: The MkDocs environment object.

  """
  # Use module-level constants for paths
  schemas_dirs = SCHEMAS_DIRS

  def get_error_context():
    try:
      return f" (in file: {env.page.file.src_path})"
    except AttributeError:
      return ""

  def _resolve_with_ucp_schema(schema_path, direction, operation):
    """Resolve a schema using ucp-schema CLI (delegates to module-level fn)."""
    return _resolve_schema(schema_path, direction, operation, bundle=False)

  def _load_json_file(entity_name):
    """Try loading a JSON file from the configured directories."""
    for schemas_dir in schemas_dirs:
      full_path = Path(schemas_dir) / (entity_name + ".json")
      try:
        with full_path.open(encoding="utf-8") as f:
          return json.load(f)
      except FileNotFoundError:
        continue
    return None

  def _load_schema_variant(entity_name, context):
    """Load and resolve a schema for a specific operation.

    Uses ucp-schema to resolve annotations at runtime based on context.

    Args:
    ----
      entity_name: The base name (e.g., 'checkout').
      context: Dict containing 'io_type' (request/response) and 'operation_id'.

    Returns:
    -------
      The resolved schema data as a dictionary, or None if not found.

    """
    if not context:
      return _load_json_file(entity_name)

    io_type = context.get("io_type")
    op_id = context.get("operation_id", "").lower()

    # Find the schema file
    schema_path = None
    for schemas_dir in schemas_dirs:
      full_path = Path(schemas_dir) / (entity_name + ".json")
      if full_path.exists():
        schema_path = str(full_path)
        break

    if not schema_path:
      return _load_json_file(entity_name)

    # Determine direction and operation for ucp-schema
    direction = io_type  # "request" or "response"
    operation = "read"  # default for responses

    if io_type == "request":
      if "create" in op_id:
        operation = "create"
      elif "update" in op_id or "patch" in op_id:
        operation = "update"
      elif "complete" in op_id:
        operation = "complete"
    elif io_type == "response":
      operation = "read"

    # Resolve using ucp-schema (no fallback - fail loudly if unavailable)
    resolved = _resolve_with_ucp_schema(schema_path, direction, operation)
    if resolved:
      return resolved

    # ucp-schema failed - don't silently fall back to raw JSON with annotations
    return None

  # Cache for polymorphic type detection
  _polymorphic_cache: dict[str, bool] = {}

  def _is_polymorphic_type(ref_string: str) -> bool:
    """Check if a schema file is polymorphic (has ucp_request annotations).

    Polymorphic types have different request/response variants and require
    the -response suffix in anchors to match markdown headings.
    """
    if ref_string in _polymorphic_cache:
      return _polymorphic_cache[ref_string]

    # Only check types/ refs
    if "types/" not in ref_string:
      _polymorphic_cache[ref_string] = False
      return False

    # Find and load the schema file
    # ref_string is like "types/line_item.json", extract just the filename
    filename = Path(ref_string).name.replace(".json", "")
    # _load_json_file searches in SCHEMAS_DIRS which already includes the
    # types directory, so we just pass the filename
    schema_data = _load_json_file(filename)
    if not schema_data:
      _polymorphic_cache[ref_string] = False
      return False

    # Check if any property has ucp_request annotation
    properties = schema_data.get("properties", {})
    for prop_details in properties.values():
      if isinstance(prop_details, dict) and "ucp_request" in prop_details:
        _polymorphic_cache[ref_string] = True
        return True

    _polymorphic_cache[ref_string] = False
    return False

  def create_link(ref_string, spec_file_name, context=None):
    """Transform schema paths into Markdown links.

    Transforms paths like "types/line_item.create_req.json" into Markdown links.
    This function is used to generate links to specific schema entities within
    the same specification file.

    Args:
    ----
      ref_string: e.g., "types/line_item.create_req.json"
      spec_file_name: e.g., "checkout"
      context: Optional dict with 'io_type' (request/response) for polymorphic
        type handling.

    Returns:
    -------
      Markdown link: [Line Item.Create_Req](#line-item-create_request)

    """
    # Refer to checkout.json for ap2-mandates.json entities that are not
    # explicitly defined in ap2-mandates.json.
    if (
      spec_file_name == "ap2-mandates"
      and "ap2_mandate" not in ref_string
      and not ref_string.startswith("#")
    ):
      spec_file_name = "checkout"

    filename = Path(ref_string).name

    # Check if this reference comes from the core UCP schema
    is_ucp = "ucp.json" in ref_string

    # 1. Clean extension and paths
    raw_name = filename.replace(".json", "")
    if filename.endswith("#/schema"):
      raw_name = raw_name.replace("#/schema", "")

    # 2. Generate Link Text (Visual)
    # e.g. "checkout_response" -> "Checkout Response"
    link_text = (
      raw_name.replace("_", " ").replace(".", " ").replace("-", " ").title()
    )
    if link_text.endswith("Resp"):
      link_text = link_text.replace("Resp", "Response")
    elif link_text.endswith("Req"):
      link_text = link_text.replace("Req", "Request")

    # FIX: Explicitly add UCP prefix for core UCP definitions if missing
    if is_ucp and "Ucp" not in link_text and "UCP" not in link_text:
      link_text = f"UCP {link_text}"

    # 3. Generate Anchor (Target)
    # We want "types/line_item.create_req.json" -> "#line-item-create_request"
    # This matches the pattern: "Line Item" H3 -> "Create Request" H4

    # 3. Generate Anchor (Target)
    parts = raw_name.split(".")
    base_entity = parts[0]

    anchor_name = base_entity.replace("_", "-")

    if len(parts) > 1:
      variant = parts[1]
      variant_expanded = (
        variant.replace("create_req", "create-request")
        .replace("update_req", "update-request")
        .replace("resp", "response")
        .replace("-", " ")
      )
      anchor_name = f"{anchor_name}-{variant_expanded}".replace(" ", "-")
    elif raw_name.endswith("_resp"):
      anchor_name = raw_name.replace("_", "-").replace("-resp", "-response")
    elif raw_name.endswith("_req"):
      anchor_name = raw_name.replace("_", "-").replace("-req", "-request")
    elif context and context.get("io_type") == "response":
      # For polymorphic types in response mode, append -response to match
      # markdown headings like "Line Item Response" (h4 under "Line Item" h3)
      if _is_polymorphic_type(ref_string):
        anchor_name = f"{anchor_name}-response"
        if not link_text.endswith("Response"):
          link_text = f"{link_text} Response"

    # FIX: Ensure anchor starts with ucp- for UCP definitions
    if is_ucp and not anchor_name.startswith("ucp-"):
      anchor_name = f"ucp-{anchor_name}"

    base = f"site:specification/{spec_file_name}/#"
    return f"[{link_text}]({base}{anchor_name.lower()})"

  def _render_table_from_ref(
    properties_ref, required_list, spec_file_name, context=None
  ):
    """Inline fields from a given list of properties.

    Args:
    ----
      properties_ref: The reference JSON file.
      required_list: The list of required properties from the parent schema.
      spec_file_name: The name of the spec file indicating where the dictionary
        should be rendered.
      context: Optional. A dictionary providing context for loading schema
        variants (e.g., {'io_type': 'request', 'operation_id':
        'createCheckout'}).

    Returns:
    -------
      A string containing a Markdown table representing the schema properties,
      or a message indicating why a table could not be rendered.

    """
    # Clean up ref to get entity name
    ref_clean = properties_ref.split("#")[0]
    if ref_clean.endswith("/schema"):
      ref_clean = ref_clean.replace("/schema", "")

    ref_entity_name = Path(ref_clean).stem

    # LOAD DATA WITH CONTEXT
    ref_schema_data = _load_schema_variant(ref_entity_name, context)

    if ref_schema_data:
      # Handle embedded anchors (e.g. file.json#/$defs/Something)
      if "#" in properties_ref and "$defs" in properties_ref:
        def_name = properties_ref.split("/")[-1]
        ref_schema_data = ref_schema_data.get("$defs", {}).get(def_name)

      if ref_schema_data and not any(
        key in ref_schema_data for key in ("properties", "allOf", "$ref")
      ):
        ref_schema_data = ref_schema_data.get("schema", ref_schema_data)

      return _render_table_from_schema(
        ref_schema_data, spec_file_name, False, required_list, context
      )
    else:
      # If purely external and not found locally
      if properties_ref.startswith("http"):
        return f"_See [{properties_ref}]({properties_ref})_"
      # ucp-schema failed or schema not found - fail loudly
      raise RuntimeError(
        f"Failed to resolve '{ref_entity_name}'{get_error_context()}. "
        f"Ensure ucp-schema is installed: `cargo install ucp-schema`"
      )

  def _render_embedded_table(
    properties_list, required_list, spec_file_name, context=None
  ):
    """Inline fields from a given list of properties.

    Args:
    ----
      properties_list: A list containing properties JSON.
      required_list: The list of required properties from the parent schema.
      spec_file_name: The name of the spec file indicating where the dictionary
        should be rendered.
      context: Optional. A dictionary providing context for loading schema
        variants (e.g., {'io_type': 'request', 'operation_id':
        'createCheckout'}).

    Returns:
    -------
      A string containing a Markdown table representing the schema properties,
      or a message indicating why a table could not be rendered.

    """
    if not properties_list:
      return "_No content fields defined._"

    # Special handling for capability.
    if (
      len(properties_list) == 2
      and len(properties_list[1].keys()) == 1
      and "required" in properties_list[1]
    ):
      ref = properties_list[0].get("$ref")
      if ref:
        return _read_schema_from_defs(
          "capability.json" + ref,
          spec_file_name,
          False,
          properties_list[1].get("required", []),
        )
      else:
        # If the ref was already resolved, render the schema directly.
        return _render_table_from_schema(
          properties_list[0],
          spec_file_name,
          False,
          properties_list[1].get("required", []),
          context,
        )

    md = []
    for properties in properties_list:
      if len(properties) == 1 and "$ref" in properties:
        embedded_data = _render_table_from_ref(
          properties["$ref"], required_list, spec_file_name, context
        )
        md.append(embedded_data)
        continue
      md.append(
        _render_table_from_schema(
          properties, spec_file_name, False, required_list, context
        )
      )

    return "\n".join(md)

  def _render_table_from_schema(
    schema_data,
    spec_file_name,
    need_header=True,
    parent_required_list=None,
    context=None,
  ):
    """Render a Markdown table from a schema dictionary.

    Schema dictionary must contain 'properties'. 'required' list is optional.

    Args:
    ----
      schema_data: A dictionary representing the JSON schema.
      spec_file_name: The name of the spec file indicating where the dictionary
        should be rendered.
      need_header: Optional. Whether to render the header row.
      parent_required_list: Optional. The list of required properties from the
        parent schema.
      context: Optional. A dictionary providing context for loading schema
        variants (e.g., {'io_type': 'request', 'operation_id':
        'createCheckout'}).

    Returns:
    -------
      A string containing a Markdown table representing the schema properties,
      or a message indicating why a table could not be rendered.

    """
    if not schema_data:
      return "_No content fields defined._"

    # If schema is ONLY a oneOf, render as prose instead of table
    if (
      "oneOf" in schema_data
      and not schema_data.get("properties")
      and not schema_data.get("allOf")
      and not schema_data.get("$ref")
    ):
      links = []
      for item in schema_data["oneOf"]:
        if "$ref" in item:
          links.append(create_link(item["$ref"], spec_file_name, context))
        elif item.get("type"):
          links.append(f"`{item.get('type')}`")
      if links:
        return (
          "\nThis object MUST be one of the following types: "
          + ", ".join(links)
          + ".\n"
        )

    properties = schema_data.get("properties", {})
    required_list = schema_data.get("required", [])

    if parent_required_list:
      # Used for embedded schemas, we will only enforce the uppermost level
      # required list.
      required_list = parent_required_list

    if (
      not properties
      and "allOf" not in schema_data
      and "oneOf" not in schema_data
      and "$ref" not in schema_data
    ):
      # Fallback for scalar schemas (Enums, Strings with patterns, etc.)
      s_type = schema_data.get("type")
      enum_val = schema_data.get("enum")
      pattern_val = schema_data.get("pattern")

      if s_type or enum_val:
        desc = schema_data.get("description", "")
        if pattern_val:
          desc += f"\n\n**Pattern:** `{pattern_val}`"
        if enum_val:
          formatted = ", ".join([f"`{v}`" for v in enum_val])
          desc += f"\n\n**Enum:** {formatted}"
        return desc

      return "_No properties defined._"

    md = []
    if need_header:
      md = ["| Name | Type | Required | Description |"]
      md.append("| :--- | :--- | :--- | :--- |")

    if "allOf" in properties:
      md.append(
        _render_embedded_table(
          properties.get("allOf", []),
          required_list,
          spec_file_name,
          context,
        )
      )
    elif "allOf" in schema_data:
      md.append(
        _render_embedded_table(
          schema_data.get("allOf", []),
          required_list,
          spec_file_name,
          context,
        )
      )
    elif "$ref" in schema_data:
      md.append(
        _render_table_from_ref(
          schema_data.get("$ref"), required_list, spec_file_name, context
        )
      )
    else:
      for field_name, details in properties.items():
        if field_name == "$ref":
          md.append(
            _render_table_from_ref(
              details, required_list, spec_file_name, context
            )
          )
          continue

        f_type = details.get("type", "any")
        ref = details.get("$ref")

        # Check for Array specific logic
        items = details.get("items", {})
        items_ref = items.get("$ref")

        # Special handling for UCP version
        version_data = None
        if ref and ref.endswith("#/$defs/version"):
          try:
            with UCP_SCHEMA_PATH.open(encoding="utf-8") as f:
              data = json.load(f)
              version_data = data.get("$defs", {}).get("version", {})
          except json.JSONDecodeError as e:
            print(f"**Error loading schema {'ucp.json' + ref}':** {e}")

        # --- Logic to determine Display Type ---
        if "oneOf" in details:
          # List of values embedded within an oneOf
          f_type = "OneOf["
          for idx, one_of_type in enumerate(details.get("oneOf", [])):
            if "$ref" in one_of_type:
              f_type += create_link(
                one_of_type["$ref"], spec_file_name, context
              )
              if idx < len(details.get("oneOf", [])) - 1:
                f_type += ", "
          f_type += "]"
        elif ref:
          if version_data:
            f_type = version_data.get("type", "any")
          else:
            # Direct Reference
            f_type = create_link(ref, spec_file_name, context)
        elif f_type == "array" and items_ref:
          # Array of References
          link = create_link(items_ref, spec_file_name, context)
          f_type = f"Array[{link}]"
        elif f_type == "array":
          # Array of Primitives
          inner_type = items.get("type", "any")
          f_type = f"Array[{inner_type}]"

        # --- Handle Description ---
        desc = ""
        # Handle additional description text for constant
        if "const" in details:
          desc += f"**Constant = {details.get('const')}**. "
        # Special handling for UCP version
        elif version_data and ref == "#/$defs/version":
          desc += version_data.get("description", "")

        # Get embedder's description, or inherit from ref'd type if omitted
        embedder_desc = details.get("description")
        if embedder_desc is not None:
          desc += embedder_desc
        elif ref and not ref.startswith("#"):
          # No embedder description - inherit from ref'd type
          ref_clean = ref.split("#")[0]
          ref_entity = ref_clean.replace(".json", "")
          ref_schema = _load_json_file(ref_entity)
          if ref_schema:
            desc += ref_schema.get("description", "")

        enum_values = details.get("enum")

        # --- Handle Enum ---
        if enum_values and isinstance(enum_values, list):
          # Format values like: `val1`, `val2`
          formatted_enums = ", ".join([f"`{str(v)}`" for v in enum_values])
          # Add a line break if description exists, then append Enum list
          if desc:
            desc += "<br>"
          desc += f"**Enum:** {formatted_enums}"

        # --- Handle Required ---
        req_display = "**Yes**" if field_name in required_list else "No"

        md.append(f"| {field_name} | {f_type} | {req_display} | {desc} |")

    return "\n".join(md)

  def _read_schema_from_defs(
    entity_name, spec_file_name, need_header=True, parent_required_list=None
  ):
    """Parse a standalone JSON Schema file with ref definitions.

    Render a table.
    """
    if ".json#/" not in entity_name:
      raise ValueError(
        f"Invalid entity name format for def: {entity_name}"
        f"{get_error_context()}"
      )

    try:
      core_entity_name, def_path = entity_name.split(".json#", 1)
      core_entity_name += ".json"
      def_path = "#" + def_path
    except ValueError:
      raise ValueError(
        f"Malformed entity name: {entity_name}{get_error_context()}"
      ) from None

    for schemas_dir in schemas_dirs:
      full_path = Path(schemas_dir) / core_entity_name
      if not full_path.exists():
        continue
      # Use ucp-schema to resolve the full file with bundling
      bundled = _resolve_schema_bundled(full_path)
      if bundled:
        # Extract the $def from the bundled result
        embedded_schema_data = _resolve_json_pointer(def_path, bundled)
        if embedded_schema_data is not None:
          # Resolve internal refs (like #/$defs/base) against the bundled root
          if "allOf" in embedded_schema_data:
            new_all_of = []
            for item in embedded_schema_data["allOf"]:
              if "$ref" in item and item["$ref"].startswith("#/"):
                resolved = _resolve_json_pointer(item["$ref"], bundled)
                new_all_of.append(resolved if resolved else item)
              else:
                new_all_of.append(item)
            embedded_schema_data = embedded_schema_data.copy()
            embedded_schema_data["allOf"] = new_all_of

          return _render_table_from_schema(
            embedded_schema_data,
            spec_file_name,
            need_header,
            parent_required_list,
          )
        else:
          raise RuntimeError(
            f"Definition '{def_path}' not found in '{full_path}'"
            f"{get_error_context()}"
          )
      # Try next directory if resolution failed

    raise FileNotFoundError(
      f"Schema file '{core_entity_name}' not found in any schema"
      f" directory{get_error_context()}."
    )

  # --- MACRO 1: For Standalone JSON Schemas ---
  @env.macro
  def schema_fields(entity_name, spec_file_name):
    """Parse a standalone JSON Schema file and render a table.

    Usage: {{ schema_fields('buyer', 'checkout') }}

    Suffixes control schema resolution direction:
    - 'cart_resp' -> resolves cart.json as response schema
    - 'cart_create_req' -> resolves cart.json as request schema (op=create)
    - 'buyer' -> resolves buyer.json as response schema (default)

    Args:
    ----
      entity_name: Schema name with optional suffix (e.g., 'cart_resp').
      spec_file_name: Spec file for link generation (e.g., 'checkout').

    """
    # Parse suffix to determine resolution direction/operation
    direction = "response"
    operation = "read"
    base_name = entity_name

    if entity_name.endswith("_resp"):
      base_name = entity_name[:-5]  # Strip _resp
      direction = "response"
    elif entity_name.endswith("_req"):
      # Pattern: entity_op_req (e.g., cart_create_req)
      parts = entity_name[:-4].rsplit("_", 1)  # Strip _req, split on last _
      if len(parts) == 2 and parts[1] in (
        "create",
        "update",
        "complete",
        "read",
      ):
        base_name, operation = parts
        direction = "request"
      else:
        base_name = entity_name[:-4]
        direction = "request"

    # Build context for downstream link generation
    context = {"io_type": direction, "operation_id": operation}

    for schemas_dir in schemas_dirs:
      full_path = Path(schemas_dir) / (base_name + ".json")
      if not full_path.exists():
        continue
      # Resolve WITHOUT bundling to preserve $refs for hyperlinks
      resolved_schema = _resolve_schema(
        full_path, direction, operation, bundle=False
      )
      if resolved_schema:
        return _render_table_from_schema(
          resolved_schema, spec_file_name, context=context
        )
      # ucp-schema failed - fail loudly, don't silently use raw JSON
      raise RuntimeError(
        f"Failed to resolve schema '{full_path}' with ucp-schema"
        f"{get_error_context()}. "
        f"Ensure ucp-schema is installed: `cargo install ucp-schema`"
      )

    raise FileNotFoundError(
      f"Schema '{base_name}' not found in any schema directory"
      f"{get_error_context()}."
    )

  @env.macro
  def extension_schema_fields(entity_name, spec_file_name):
    """Parse a standalone JSON Schema file and render a table.

    Usage: {{ extension_schema_fields('fulfillment_option') }}

    Args:
    ----
      entity_name: The name of the schema entity embedded in the extension
        (e.g., 'fulfillment.json#/$defs/fulfillment_option').
      spec_file_name: The name of the spec file indicating where the dictionary
        should be rendered (e.g., "checkout", "fulfillment").

    """
    return _read_schema_from_defs(entity_name, spec_file_name)

  @env.macro
  def auto_generate_schema_reference(
    sub_dir=".",
    spec_file_name="reference",
    include_extensions=True,
    include_capability=True,
  ):
    """Scan a dir for JSON schemas and generate documentation.

    Scan a subdirectory within source/schemas/shopping/ for .json files
    and generate documentation for each schema found.

    Args:
    ----
      sub_dir: The subdirectory to scan, relative to source/schemas/shopping/.
      spec_file_name: The name of the spec file for link generation.
      include_extensions: If true, includes schemas with 'Extension' in title.
      include_capability: If true, includes schemas without 'Extension' in
        title.

    """
    schema_base_path = SHOPPING_SCHEMAS_DIR
    scan_path = (
      schema_base_path / sub_dir if sub_dir != "." else schema_base_path
    )

    if not scan_path.is_dir():
      return f"<p><em>Schema directory not found: {scan_path}</em></p>"

    output = []
    try:
      schema_files = sorted(
        [f for f in scan_path.iterdir() if f.suffix == ".json"]
      )
    except FileNotFoundError:
      return f"<p><em>Schema directory not found: {scan_path}</em></p>"

    if not schema_files:
      return f"<p><em>No schema files found in {scan_path}</em></p>"

    for schema_file in schema_files:
      entity_name_base = schema_file.stem
      if sub_dir == ".":
        entity_name = entity_name_base
      else:
        entity_name = str(Path(sub_dir).as_posix()) + "/" + entity_name_base

      schema_data = _load_json_file(entity_name)
      if schema_data:
        is_extension = "Extension" in schema_data.get("title", "")
        if is_extension and not include_extensions:
          continue
        if not is_extension and not include_capability:
          continue

        # If a schema has no structural elements worth documenting here,
        # skip it.
        if (
          not schema_data.get("properties")
          and not schema_data.get("allOf")
          and not schema_data.get("oneOf")
          and not schema_data.get("$ref")
          and not schema_data.get("$defs")
        ):
          continue
        schema_title = schema_data.get(
          "title", entity_name_base.replace("_", " ").title()
        )
        if is_extension:
          output.append(f"### {schema_title}\n")
          defs = schema_data.get("$defs", {})
          def_count = 0
          for def_name, def_schema in defs.items():
            def_count += 1
            def_title = def_schema.get(
              "title", def_name.replace("_", " ").title()
            )
            output.append(f"#### {def_title}\n")
            rendered_table = _read_schema_from_defs(
              f"{entity_name}.json#/$defs/{def_name}", spec_file_name
            )
            output.append(rendered_table)
            output.append("\n")

          if def_count > 0:
            output.append("\n---\n")
          elif (
            schema_data.get("properties")
            or schema_data.get("allOf")
            or schema_data.get("oneOf")
            or schema_data.get("$ref")
          ):
            rendered_table = _render_table_from_schema(
              schema_data, spec_file_name
            )
            if rendered_table == "_No properties defined._":
              output.pop()  # remove title
              continue
            output.append(rendered_table)
            output.append("\n---\n")
          else:
            output.pop()  # remove title
            continue
        else:
          rendered_table = _render_table_from_schema(
            schema_data, spec_file_name
          )
          if rendered_table == "_No properties defined._":
            continue
          output.append(f"### {schema_title}\n")
          output.append(rendered_table)
          output.append("\n---\n")
      else:
        output.append(f"### {entity_name_base}\n")
        output.append(
          f"<p><em>Could not load schema for entity: {entity_name}</em></p>"
        )
        output.append("\n---\n")

    return "\n".join(output)

  # --- MACRO 2: For Standalone JSON Extensions ---
  @env.macro
  def extension_fields(entity_name, spec_file_name):
    """Parse an extension schema file and render a table from its $defs.

    Usage: {{ extension_fields('discount', 'checkout') }}

    Args:
    ----
      entity_name: The name of the extension schema (e.g., 'discount').
      spec_file_name: The name of the spec file indicating where the dictionary
        should be rendered (e.g., "checkout", "fulfillment").

    """
    # Construct full path based on new structure
    full_path = SHOPPING_SCHEMAS_DIR / (entity_name + ".json")
    try:
      with full_path.open(encoding="utf-8") as f:
        data = json.load(f)

      # Extension schemas have their composed type in $defs.checkout
      # or $defs.order_line_item.
      defs = data.get("$defs", {})

      # Dynamically find the composed type by looking for an entry with 'allOf'
      # where one of the items defines 'properties'.
      for schema_def in defs.values():
        if isinstance(schema_def, dict) and "allOf" in schema_def:
          for item in schema_def["allOf"]:
            if "properties" in item:
              return _render_table_from_schema(item, spec_file_name)

      raise RuntimeError(
        f"Could not find extension properties in '{entity_name}'"
        f"{get_error_context()}"
      )
    except (FileNotFoundError, json.JSONDecodeError) as e:
      raise RuntimeError(
        f"Error loading extension '{entity_name}': {e}{get_error_context()}"
      ) from e

  # --- MACRO 3: For Transport Operations ---
  @env.macro
  def method_fields(operation_id, file_name, spec_file_name, io_type=None):
    """Extract Request/Response schemas for a specific OpenAPI operationId.

    Args:
    ----
      operation_id: The `operationId` of the OpenAPI operation to document.
      file_name: The name of the OpenAPI file to read.
      spec_file_name: The name of the spec file indicating where the dictionary
        should be rendered (e.g., "checkout", "fulfillment").
      io_type: Optional. Specifies whether to render 'request', 'response', or
        both (if None).

    """
    full_path = OPENAPI_DIR / file_name

    try:
      with full_path.open(encoding="utf-8") as f:
        data = json.load(f)

      # 1. Find the Operation Object by ID (search paths first, then webhooks)
      operation = None
      path_parameters = []

      # Search in paths
      paths = data.get("paths", {})
      for _, path_item in paths.items():
        for _, op_data in path_item.items():
          if not isinstance(op_data, dict):
            continue
          if op_data.get("operationId") == operation_id:
            operation = op_data
            path_parameters = path_item.get("parameters", [])
            break
        if operation:
          break

      # If not found in paths, search in webhooks (OpenAPI 3.1+)
      if not operation:
        webhooks = data.get("webhooks", {})
        for _, webhook_item in webhooks.items():
          for _, op_data in webhook_item.items():
            if not isinstance(op_data, dict):
              continue
            if op_data.get("operationId") == operation_id:
              operation = op_data
              break
          if operation:
            break

      if not operation:
        raise ValueError(
          f"Operation ID `{operation_id}` not found{get_error_context()}."
        )

      # 2. Extract Request Schema
      req_content = operation.get("requestBody", {}).get("content", {})
      req_schema = req_content.get("application/json", {}).get("schema", {})

      # 3. Extract Parameters (Path + Operation)
      op_parameters = operation.get("parameters", [])
      all_parameters = path_parameters + op_parameters

      # 4. Extract Response Schema
      success_response_codes = ["200", "201"]
      res_schema = {}
      res = operation.get("responses", {})
      for code in success_response_codes:
        if code in res:
          res_content = res.get(code, {}).get("content", {})
          res_schema = res_content.get("application/json", {}).get("schema", {})
          break

      # --- FIX: Targeted Reference Resolution ---
      # We only resolve the top-level ref and 'allOf' children.
      # This fixes the "Complete Checkout" table without expanding every
      # property.

      def resolve_structure(schema, root):
        if not schema:
          return schema
        # 1. Resolve Top-Level Ref (e.g. "create_checkout")
        if "$ref" in schema and schema["$ref"].startswith("#/"):
          resolved = _resolve_json_pointer(schema["$ref"], root)
          if resolved:
            schema = resolved

        # 2. Resolve Composition Refs (e.g. "complete_checkout" response)
        if "allOf" in schema:
          new_all_of = []
          for item in schema["allOf"]:
            if "$ref" in item and item["$ref"].startswith("#/"):
              resolved = _resolve_json_pointer(item["$ref"], root)
              new_all_of.append(resolved if resolved else item)
            else:
              new_all_of.append(item)
          schema["allOf"] = new_all_of
        return schema

      req_schema = resolve_structure(req_schema, data)
      res_schema = resolve_structure(res_schema, data)
      # ------------------------------------------

      output = ""

      # -- Render Request --
      if io_type is None or io_type == "request":
        req_context = {"io_type": "request", "operation_id": operation_id}

        param_props = {}
        param_required_fields = []
        for param in all_parameters:
          # Resolve param refs explicitly if needed (rare for params but good
          # safety)
          if "$ref" in param and param["$ref"].startswith("#/"):
            resolved = _resolve_json_pointer(param["$ref"], data)
            if resolved:
              param = resolved

          # Filter out headers (transport-specific)
          if param.get("in") == "header":
            continue
          name = param.get("name", "")
          if not name:
            continue

          # Convert to schema property format
          prop_schema = param.get("schema", {}).copy()
          if "description" in param:
            prop_schema["description"] = param["description"]

          # Add additional annotation for path parameters
          if param.get("in", "") == "path":
            prop_schema["description"] = (
              prop_schema.get("description", "") + "Defined in path."
            )
          param_props[name] = prop_schema
          if param.get("required"):
            param_required_fields.append(name)

        param_schema = None
        if param_props:
          param_schema = {
            "properties": param_props,
            "required": param_required_fields,
          }

        # 5. Combine Parameters and Request Body into a single "Inputs" schema
        combined_schema = None
        if param_schema and req_schema:
          combined_schema = {
            "properties": {"allOf": [param_schema, req_schema]}
          }
        elif param_schema:
          combined_schema = param_schema
        elif req_schema:
          combined_schema = req_schema

        if combined_schema:
          output += "**Inputs**\n\n"
          output += (
            _render_table_from_schema(
              combined_schema, spec_file_name, context=req_context
            )
            + "\n\n"
          )
        elif io_type is None or io_type == "request":
          output += "_No inputs defined._\n\n"

      # -- Render Output --
      if io_type is None or io_type == "response":
        if io_type is None and res_schema:
          output += "**Output**\n\n"

        if res_schema:
          res_context = {"io_type": "response", "operation_id": operation_id}
          output += (
            _render_table_from_schema(
              res_schema, spec_file_name, context=res_context
            )
            + "\n\n"
          )
        elif io_type is None or io_type == "response":
          output += "_No output defined._\n\n"

      return output

    except (FileNotFoundError, json.JSONDecodeError) as e:
      raise RuntimeError(
        f"Error processing OpenAPI: {e}{get_error_context()}"
      ) from e

  # --- MACRO 4: For HTTP Headers ---
  @env.macro
  def header_fields(operation_id, file_name):
    """Extract HTTP headers for a specific OpenAPI operationId.

    Args:
    ----
      operation_id: The `operationId` of the OpenAPI operation.
      file_name: The name of the OpenAPI file to read.

    """
    full_path = OPENAPI_DIR / file_name

    try:
      with full_path.open(encoding="utf-8") as f:
        data = json.load(f)

      # 1. Find the Operation Object by ID
      operation = None
      path_parameters = []
      paths = data.get("paths", {})
      for _, path_item in paths.items():
        for _, op_data in path_item.items():
          if not isinstance(op_data, dict):
            continue

          if op_data.get("operationId") == operation_id:
            operation = op_data
            # Extract parameters defined at the path level
            path_parameters = path_item.get("parameters", [])
            break
        if operation:
          break

      if not operation:
        raise ValueError(
          f"Operation ID `{operation_id}` not found{get_error_context()}."
        )

      # 2. Extract Request Parameters (Path + Operation)
      op_parameters = operation.get("parameters", [])
      all_parameters = path_parameters + op_parameters

      req_headers = []
      for param in all_parameters:
        # Resolve reference if needed
        if "$ref" in param:
          resolved = _resolve_json_pointer(param["$ref"], data)
          if resolved:
            param = resolved
          else:
            continue

        if param.get("in") == "header":
          req_headers.append(param)

      # 3. Extract Response Headers (Assumes 200 OK)
      res_headers_defs = (
        operation.get("responses", {}).get("200", {}).get("headers", {})
      )
      res_headers = []
      for name, header in res_headers_defs.items():
        if "$ref" in header:
          resolved = _resolve_json_pointer(header["$ref"], data)
          if resolved:
            h = resolved.copy()
            h["name"] = name
            res_headers.append(h)
          else:
            # If ref not resolved, just use name
            h = {"name": name, "description": "Ref not resolved"}
            res_headers.append(h)
        else:
          h = header.copy()
          h["name"] = name
          res_headers.append(h)

      if not req_headers and not res_headers:
        return "_No headers defined._"

      def render_headers_table(headers_list):
        """Render a list of headers into a Markdown table."""
        md_table = ["| Header | Required | Description |"]
        md_table.append("| :--- | :--- | :--- |")
        for h in headers_list:
          name = f"`{h.get('name')}`"
          required = "**Yes**" if h.get("required") else "No"
          desc = h.get("description", "")
          # Handle line breaks in description
          desc = desc.replace("\n", "<br>")
          md_table.append(f"| {name} | {required} | {desc} |")
        return "\n".join(md_table)

      output_parts = []
      if req_headers:
        output_parts.append(
          "**Request Headers**\n\n" + render_headers_table(req_headers)
        )
      if res_headers:
        output_parts.append(
          "**Response Headers**\n\n" + render_headers_table(res_headers)
        )

      return "\n\n".join(output_parts)

    except (FileNotFoundError, json.JSONDecodeError) as e:
      raise RuntimeError(
        f"Error processing OpenAPI: {e}{get_error_context()}"
      ) from e
