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
import os
import sys
from pathlib import Path

# Modify sys.path to include the current directory so schema_utils can be found.
sys.path.append(str(Path(__file__).resolve().parent))

import schema_utils  # noqa: E402


def define_env(env):
  """Injects custom macros into the MkDocs environment.

  This function is called by MkDocs and receives the `env` object,
  allowing it to register custom macros like `schema_fields` and
  `method_fields` for use in Markdown pages.

  Args:
  ----
    env: The MkDocs environment object.

  """
  # --- CONFIGURATION ---
  openapi_dir = "spec/services/shopping/"
  schemas_dirs = [
    "spec/handlers/google_pay/",
    "spec/schemas/",
    "spec/schemas/shopping/",
    "spec/schemas/shopping/types/",
  ]

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
    """Load the specific schema variant (create/update/resp) if available.

    Args:
    ----
      entity_name: The base name (e.g., 'checkout').
      context: Dict containing 'io_type' (request/response) and 'operation_id'.

    Returns:
    -------
      The loaded schema data as a dictionary, or None if not found.

    """
    if not context:
      return _load_json_file(entity_name)

    io_type = context.get("io_type")
    op_id = context.get("operation_id", "").lower()

    variant_name = None

    # 1. Determine the target filename based on IO type and Operation ID
    if io_type == "response":
      # e.g., checkout -> checkout_resp
      variant_name = f"{entity_name}_resp"

    elif io_type == "request":
      # Heuristic: Determine if this is a create or update operation
      if "create" in op_id:
        variant_name = f"{entity_name}.create_req"
      elif "update" in op_id or "patch" in op_id:
        variant_name = f"{entity_name}.update_req"

    # 2. Try to load the variant
    if variant_name:
      data = _load_json_file(variant_name)
      if data:
        return data

    return _load_json_file(entity_name)

  def create_link(ref_string, spec_file_name):
    """Transform schema paths into Markdown links.

    Transforms paths like "types/line_item.create_req.json" into Markdown links.
    This function is used to generate links to specific schema entities within
    the same specification file.

    Args:
    ----
      ref_string: e.g., "types/line_item.create_req.json"
      spec_file_name: e.g., "checkout"

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
      return ""

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
      return _read_schema_from_defs(
        "capability.json" + properties_list[0].get("$ref", ""),
        spec_file_name,
        False,
        properties_list[1].get("required", []),
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
          links.append(create_link(item["$ref"], spec_file_name))
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
            with Path("spec/schemas/ucp.json").open(encoding="utf-8") as f:
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
              f_type += create_link(one_of_type["$ref"], spec_file_name)
              if idx < len(details.get("oneOf", [])) - 1:
                f_type += ", "
          f_type += "]"
        elif ref:
          if version_data:
            f_type = version_data.get("type", "any")
          else:
            # Direct Reference
            f_type = create_link(ref, spec_file_name)
        elif f_type == "array" and items_ref:
          # Array of References
          link = create_link(items_ref, spec_file_name)
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

        desc += details.get("description", "")
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

  def _resolve_ref(ref, root_data):
    """Resolve a local reference (e.g., '#/components/parameters/id')."""
    return schema_utils.resolve_internal_ref(ref, root_data)

  def _create_file_loader(schema_path):
    """Create a file loader closure for a given base path."""

    def _loader(filename):
      dir_path = Path(schema_path).parent
      return schema_utils.load_json(dir_path / filename)

    return _loader

  def _read_schema_from_defs(
    entity_name, spec_file_name, need_header=True, parent_required_list=None
  ):
    """Parse a standalone JSON Schema file with ref definitions.

    Render a table.
    """
    if ".json#/" not in entity_name:
      return f"**Error:** Invalid entity name format for def: {entity_name}"

    try:
      core_entity_name, def_path = entity_name.split(".json#", 1)
      core_entity_name += ".json"
      def_path = "#" + def_path
    except ValueError:
      return f"**Error:** Malformed entity name: {entity_name}"

    for schemas_dir in schemas_dirs:
      full_path = Path(schemas_dir) / core_entity_name
      data = schema_utils.load_json(full_path)
      if data:
        file_loader = _create_file_loader(full_path)
        embedded_schema_data = schema_utils.resolve_internal_ref(def_path, data)
        if embedded_schema_data is not None:
          # Resolve allOf/refs before rendering to flatten composed schemas
          resolved_schema = schema_utils.resolve_schema(
            embedded_schema_data, data, file_loader
          )
          return _render_table_from_schema(
            resolved_schema,
            spec_file_name,
            need_header,
            parent_required_list,
          )
        else:
          return (
            f"**Error:** Definition '{def_path}' not found in '{full_path}'"
          )
      # Try next directory if load_json returned None

    return (
      f"**Error:** Schema file '{core_entity_name}' not found in any schema"
      " directory."
    )

  # --- MACRO 1: For Standalone JSON Schemas ---
  @env.macro
  def schema_fields(entity_name, spec_file_name):
    """Parse a standalone JSON Schema file and render a table.

    Usage: {{ schema_fields('buyer') }}  (assumes .json extension)

    Args:
    ----
      entity_name: The name of the schema entity (e.g., 'buyer').
      spec_file_name: The name of the spec file indicating where the dictionary
        should be rendered (e.g., "checkout", "fulfillment").

    """
    data = None
    loaded_path = None
    for schemas_dir in schemas_dirs:
      full_path = Path(schemas_dir) / (entity_name + ".json")
      try:
        with full_path.open() as f:
          data = json.load(f)
          loaded_path = full_path
          break
      except FileNotFoundError:
        continue
      except json.JSONDecodeError as e:
        return f"**Error parsing schema '{full_path}':** {e}"

    if data and loaded_path:
      file_loader = _create_file_loader(loaded_path)
      resolved_schema = schema_utils.resolve_schema(data, data, file_loader)
      return _render_table_from_schema(resolved_schema, spec_file_name)
    return (
      f"**Error:** Schema '{entity_name}' not found in any schema directory."
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

    Scan a subdirectory within spec/schemas/shopping/ for .json files
    and generate documentation for each schema found.

    Args:
    ----
      sub_dir: The subdirectory to scan, relative to spec/schemas/shopping/.
      spec_file_name: The name of the spec file for link generation.
      include_extensions: If true, includes schemas with 'Extension' in title.
      include_capability: If true, includes schemas without 'Extension' in
        title.

    """
    schema_base_path = Path("spec/schemas/shopping")
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
        entity_name = sub_dir.replace(os.sep, "/") + "/" + entity_name_base

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
    full_path = Path("spec/schemas/shopping") / (entity_name + ".json")
    try:
      with full_path.open(encoding="utf-8") as f:
        data = json.load(f)

      # Extension schemas have their composed type in $defs.checkout
      # or $defs.order_line_item.
      defs = data.get("$defs", {})
      # Find the composed type (checkout or order_line_item)
      composed_type = defs.get("checkout") or defs.get("order_line_item")
      if composed_type and "allOf" in composed_type:
        # Get the extension-specific properties (second element of allOf)
        for item in composed_type["allOf"]:
          if "properties" in item:
            return _render_table_from_schema(item, spec_file_name)

      return (
        f"**Error:** Could not find extension properties in '{entity_name}'"
      )
    except (FileNotFoundError, json.JSONDecodeError) as e:
      return f"**Error loading extension '{entity_name}':** {e}"

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
    full_path = Path(openapi_dir) / file_name

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
        return f"**Error:** Operation ID `{operation_id}` not found."

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
          resolved = _resolve_ref(schema["$ref"], root)
          if resolved:
            schema = resolved

        # 2. Resolve Composition Refs (e.g. "complete_checkout" response)
        if "allOf" in schema:
          new_all_of = []
          for item in schema["allOf"]:
            if "$ref" in item and item["$ref"].startswith("#/"):
              resolved = _resolve_ref(item["$ref"], root)
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
            resolved = _resolve_ref(param["$ref"], data)
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
      return f"**Error processing OpenAPI:** {e}"

  # --- MACRO 4: For HTTP Headers ---
  @env.macro
  def header_fields(operation_id, file_name):
    """Extract HTTP headers for a specific OpenAPI operationId.

    Args:
    ----
      operation_id: The `operationId` of the OpenAPI operation.
      file_name: The name of the OpenAPI file to read.

    """
    full_path = Path(openapi_dir) / file_name

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
        return f"**Error:** Operation ID `{operation_id}` not found."

      # 2. Extract Request Parameters (Path + Operation)
      op_parameters = operation.get("parameters", [])
      all_parameters = path_parameters + op_parameters

      req_headers = []
      for param in all_parameters:
        # Resolve reference if needed
        if "$ref" in param:
          resolved = _resolve_ref(param["$ref"], data)
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
          resolved = _resolve_ref(header["$ref"], data)
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
      return f"**Error processing OpenAPI:** {e}"
