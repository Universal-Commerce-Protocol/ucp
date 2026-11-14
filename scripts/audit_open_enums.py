#!/usr/bin/env python3
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

"""Audit open-enumeration schemas and non-standard values in UCP docs.

Implements two complementary hygiene checks for UCP open strings:

  1. Schema coverage (`audit_schema_open_enums`): Finds open-string fields in
     `source/schemas/` whose descriptions document well-known values in prose
     without declaring a JSON Schema `"examples": [...]` array (as specified in
     `docs/documentation/schema-authoring.md`).
  2. Spec example warnings (`audit_docs_open_enum_values`): Audits ```json
     examples in `docs/` (reusing `validate_examples.py` parsing & reduction)
     and emits non-blocking warnings when an open-enumeration field uses a
     value outside its documented well-known values or `"examples"` list.

Run: python3 scripts/audit_open_enums.py [--strict] [--json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_examples as ve  # noqa: E402

OPEN_DESC_RE = re.compile(
  r"(?:well-known(?:\s+values)?|common\s+values\s+include|"
  r"open\s+vocabulary|open\s+string|'oauth2'\s+for\s+oauth)",
  re.IGNORECASE,
)

_CLAUSE_RE = re.compile(
  r"(?:well-known(?:\s+values)?|common\s+values\s+include|like)\s*:\s*([^.]+)",
  re.IGNORECASE,
)

_REVERSE_DOMAIN_RE = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z0-9_-]+){2,}$")


def extract_prose_values(
  description: str,
  sibling_props: set[str] | None = None,
) -> list[str]:
  """Extract well-known open-string values from a schema description.

  Prefers explicit enumeration clauses (after ``Well-known values:``,
  ``Common values include:``, or ``like:``), stripping parenthetical
  annotations. Falls back to backticked or single-quoted identifiers while
  excluding sibling property names mentioned in cross-references.
  """
  if not description:
    return []
  excluded = sibling_props or set()
  match = _CLAUSE_RE.search(description)
  if match:
    clause = match.group(1)
    backticked = re.findall(r"`([a-zA-Z0-9_-]+)`", clause)
    if backticked:
      return list(dict.fromkeys(backticked))
    cleaned = re.sub(r"\([^)]*\)", "", clause)
    tokens = [
      tok.strip().strip("'\"")
      for tok in re.split(r"[,;]", cleaned)
      if re.match(r"^[a-zA-Z0-9_-]+$", tok.strip().strip("'\""))
    ]
    if tokens:
      return list(dict.fromkeys(tokens))

  raw_tokens = re.findall(
    r"`([a-zA-Z0-9_-]+)`|'([a-zA-Z0-9_-]+)'",
    description,
  )
  values = [
    (a or b) for a, b in raw_tokens if (a or b) and (a or b) not in excluded
  ]
  return list(dict.fromkeys(values))


def _is_open_string_candidate(node: dict) -> bool:
  """Return True when a schema node is an unconstrained string type."""
  return (
    node.get("type") == "string"
    and "enum" not in node
    and "const" not in node
    and "pattern" not in node
    and "format" not in node
  )


def _walk_schema_open_enums(
  node: object,
  rel_path: str,
  declared: list[dict],
  missing: list[dict],
  pointer: str = "",
  sibling_props: set[str] | None = None,
) -> None:
  """Recursively collect open-string nodes with and without `examples`."""
  if isinstance(node, dict):
    if _is_open_string_candidate(node):
      desc = node.get("description", "")
      examples = node.get("examples")
      if isinstance(examples, list):
        if len(examples) >= 2 or OPEN_DESC_RE.search(desc):
          declared.append(
            {
              "schema": rel_path,
              "pointer": pointer or "/",
              "examples": list(examples),
              "description": desc,
            }
          )
      elif OPEN_DESC_RE.search(desc):
        suggested = extract_prose_values(desc, sibling_props)
        if suggested:
          missing.append(
            {
              "schema": rel_path,
              "pointer": pointer or "/",
              "suggested_examples": suggested,
              "description": desc,
            }
          )

    props = node.get("properties")
    if isinstance(props, dict):
      sibs = set(props.keys())
      for prop_key, prop_val in props.items():
        _walk_schema_open_enums(
          prop_val,
          rel_path,
          declared,
          missing,
          f"{pointer}/properties/{prop_key}",
          sibs,
        )

    for key, val in node.items():
      if key in ("properties", "examples", "enum", "required", "if"):
        continue
      _walk_schema_open_enums(
        val,
        rel_path,
        declared,
        missing,
        f"{pointer}/{key}",
        sibling_props,
      )
  elif isinstance(node, list):
    for idx, item in enumerate(node):
      _walk_schema_open_enums(
        item,
        rel_path,
        declared,
        missing,
        f"{pointer}[{idx}]",
        sibling_props,
      )


def audit_schema_open_enums(
  schemas_dir: Path,
) -> tuple[list[dict], list[dict]]:
  """Scan JSON Schemas for open-string fields with and without `examples`.

  Returns:
    Tuple `(declared, missing)` where `declared` lists open-string fields
    carrying an `"examples"` array and `missing` lists open-string fields whose
    descriptions enumerate well-known values without `"examples"`.

  """
  declared: list[dict] = []
  missing: list[dict] = []

  for schema_path in sorted(schemas_dir.rglob("*.json")):
    rel_path = schema_path.relative_to(schemas_dir).as_posix()
    try:
      data = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
      continue
    _walk_schema_open_enums(data, rel_path, declared, missing)

  return declared, missing


def _find_direct_type_refs(node: object) -> list[str]:
  """Find `$ref`s on a property or its items/unions without nested props."""
  refs: list[str] = []
  if isinstance(node, dict):
    ref_val = node.get("$ref")
    if isinstance(ref_val, str):
      refs.append(ref_val)
    for key in ("items", "additionalProperties"):
      if key in node:
        refs.extend(_find_direct_type_refs(node[key]))
    for key in ("allOf", "oneOf", "anyOf"):
      branches = node.get(key)
      if isinstance(branches, list):
        for branch in branches:
          refs.extend(_find_direct_type_refs(branch))
  return refs


def _resolve_rel_ref(
  base_file: Path,
  schemas_root: Path,
  ref_str: str,
) -> tuple[str, str] | None:
  """Resolve a local JSON Schema `$ref` to `(relative_schema, def_name)`."""
  if not ref_str:
    return None
  file_part, _, frag = ref_str.partition("#")
  def_name = frag.split("/")[-1] if frag.startswith("/$defs/") else ""
  if not file_part:
    return base_file.relative_to(schemas_root).as_posix(), def_name
  if file_part.startswith(("http://", "https://")):
    return None
  target = (base_file.parent / file_part).resolve()
  if not target.exists():
    return None
  try:
    return target.relative_to(schemas_root).as_posix(), def_name
  except ValueError:
    return None


def _index_schema_open_nodes(
  node: object,
  rel: str,
  vertical: str,
  scalar_schemas: dict[str, tuple[list[str], str]],
  parent_bindings: dict[tuple[str, str, str], tuple[list[str], str]],
  node_open_props: dict[tuple[str, str], dict[str, tuple[list[str], str]]],
  pointer: str = "",
  container: str = "",
  prop_name: str = "",
  enclosing_prop: str = "",
  siblings: set[str] | None = None,
) -> None:
  """Collect open-enum definitions per schema/container or inline property."""
  if isinstance(node, dict):
    if _is_open_string_candidate(node):
      desc = node.get("description", "")
      vals: list[str] | None = None
      examples = node.get("examples")
      if isinstance(examples, list):
        if len(examples) >= 2 or OPEN_DESC_RE.search(desc):
          vals = list(examples)
      elif OPEN_DESC_RE.search(desc):
        extracted = extract_prose_values(desc, siblings)
        if extracted:
          vals = extracted
      if vals is not None:
        if not pointer:
          scalar_schemas[rel] = (vals, rel)
        elif pointer.endswith(f"/properties/{prop_name}") and prop_name:
          if enclosing_prop:
            parent_bindings[(vertical, enclosing_prop, prop_name)] = (
              vals,
              rel,
            )
          else:
            node_open_props.setdefault((rel, container), {})[prop_name] = (
              vals,
              rel,
            )

    props = node.get("properties")
    if isinstance(props, dict):
      sibs = set(props.keys())
      next_enclosing = prop_name or enclosing_prop
      for pk, pv in props.items():
        _index_schema_open_nodes(
          pv,
          rel,
          vertical,
          scalar_schemas,
          parent_bindings,
          node_open_props,
          f"{pointer}/properties/{pk}",
          container,
          pk,
          next_enclosing,
          sibs,
        )

    for key, val in node.items():
      if key == "$defs" and isinstance(val, dict):
        for dk, dv in val.items():
          _index_schema_open_nodes(
            dv,
            rel,
            vertical,
            scalar_schemas,
            parent_bindings,
            node_open_props,
            f"{pointer}/$defs/{dk}",
            dk,
            "",
            "",
            set(),
          )
      elif key not in ("properties", "examples", "enum", "required", "if"):
        _index_schema_open_nodes(
          val,
          rel,
          vertical,
          scalar_schemas,
          parent_bindings,
          node_open_props,
          f"{pointer}/{key}",
          container,
          prop_name,
          enclosing_prop,
          siblings,
        )
  elif isinstance(node, list):
    for idx, item in enumerate(node):
      _index_schema_open_nodes(
        item,
        rel,
        vertical,
        scalar_schemas,
        parent_bindings,
        node_open_props,
        f"{pointer}[{idx}]",
        container,
        prop_name,
        enclosing_prop,
        siblings,
      )


def _bind_schema_refs(
  node: object,
  schema_path: Path,
  schemas_root: Path,
  vertical: str,
  scalar_schemas: dict[str, tuple[list[str], str]],
  node_open_props: dict[tuple[str, str], dict[str, tuple[list[str], str]]],
  parent_bindings: dict[tuple[str, str, str], tuple[list[str], str]],
  disc_bindings: dict[tuple[str, str, str], tuple[list[str], str]],
) -> None:
  """Bind container properties and const-discriminated refs to value sets."""
  if isinstance(node, dict):
    props = node.get("properties")
    if isinstance(props, dict):
      type_prop = props.get("type")
      type_const = (
        type_prop.get("const") if isinstance(type_prop, dict) else None
      )
      for pk, pv in props.items():
        if not isinstance(pv, dict):
          continue
        for ref in _find_direct_type_refs(pv):
          resolved = _resolve_rel_ref(schema_path, schemas_root, ref)
          if not resolved:
            continue
          t_rel, t_def = resolved
          if type_const is not None and t_rel in scalar_schemas:
            disc_bindings[("type", str(type_const), pk)] = scalar_schemas[t_rel]
          if (t_rel, t_def) in node_open_props:
            for target_prop, val_info in node_open_props[
              (t_rel, t_def)
            ].items():
              parent_bindings[(vertical, pk, target_prop)] = val_info

    for key, val in node.items():
      if key not in ("examples", "enum", "required"):
        _bind_schema_refs(
          val,
          schema_path,
          schemas_root,
          vertical,
          scalar_schemas,
          node_open_props,
          parent_bindings,
          disc_bindings,
        )
  elif isinstance(node, list):
    for item in node:
      _bind_schema_refs(
        item,
        schema_path,
        schemas_root,
        vertical,
        scalar_schemas,
        node_open_props,
        parent_bindings,
        disc_bindings,
      )


def _build_schema_value_index(schemas_dir: Path) -> dict:
  """Build dynamic lookup tables from schema `$ref`s to well-known values."""
  schemas_root = schemas_dir.resolve()
  node_open_props: dict[tuple[str, str], dict[str, tuple[list[str], str]]] = {}
  scalar_schemas: dict[str, tuple[list[str], str]] = {}
  parent_bindings: dict[tuple[str, str, str], tuple[list[str], str]] = {}
  schema_cache: dict[Path, tuple[str, str, dict]] = {}

  for schema_path in sorted(schemas_root.rglob("*.json")):
    rel = schema_path.relative_to(schemas_root).as_posix()
    vertical = rel.split("/", 1)[0] if "/" in rel else ""
    try:
      data = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
      continue
    schema_cache[schema_path] = (rel, vertical, data)
    _index_schema_open_nodes(
      data,
      rel,
      vertical,
      scalar_schemas,
      parent_bindings,
      node_open_props,
    )

  direct_props: dict[tuple[str, str], tuple[list[str], str]] = {}
  for (rel, container), prop_map in node_open_props.items():
    if not container:
      schema_key = rel.removesuffix(".json")
      for prop_name, val_info in prop_map.items():
        direct_props[(schema_key, prop_name)] = val_info

  disc_bindings: dict[tuple[str, str, str], tuple[list[str], str]] = {}
  for schema_path, (_, vertical, data) in schema_cache.items():
    _bind_schema_refs(
      data,
      schema_path,
      schemas_root,
      vertical,
      scalar_schemas,
      node_open_props,
      parent_bindings,
      disc_bindings,
    )

  return {
    "parent_bindings": parent_bindings,
    "disc_bindings": disc_bindings,
    "direct_props": direct_props,
  }


def _lookup_binding(
  index: dict,
  doc_vertical: str,
  schema_attr: str,
  parent_key: str,
  prop_name: str,
  has_fragment_directive: bool,
) -> tuple[list[str], str] | None:
  """Resolve `(allowed_values, source_schema)` for a payload field."""
  parent_bindings = index["parent_bindings"]
  if parent_key:
    for vert in (doc_vertical, "common", ""):
      if vert and (vert, parent_key, prop_name) in parent_bindings:
        return parent_bindings[(vert, parent_key, prop_name)]
    if ("", parent_key, prop_name) in parent_bindings:
      return parent_bindings[("", parent_key, prop_name)]

    candidates = [
      info
      for (_, p_key, p_prop), info in parent_bindings.items()
      if p_key == parent_key and p_prop == prop_name
    ]
    if candidates and len({c[1] for c in candidates}) == 1:
      return candidates[0]
  elif schema_attr and not has_fragment_directive:
    direct = index["direct_props"].get((schema_attr, prop_name))
    if direct is not None:
      return direct

  return None


def _infer_doc_vertical(md_file: Path, docs_dir: Path, schema_attr: str) -> str:
  """Infer UCP vertical (e.g. 'food', 'shopping') for a doc block."""
  if "/" in schema_attr:
    return schema_attr.split("/", 1)[0]
  try:
    rel_parts = md_file.relative_to(docs_dir).parts
  except ValueError:
    return ""
  if len(rel_parts) >= 2 and rel_parts[0] == "specification":
    return rel_parts[1]
  return ""


def _resolve_value_line(
  block_line: int,
  block_content: str,
  key: str,
  val: str,
  seen_occurrences: dict[tuple[str, str], int],
) -> int:
  """Locate the 1-based Markdown line of a `"key": "val"` pair in a block."""
  pattern = re.compile(rf'"{re.escape(key)}"\s*:\s*"{re.escape(val)}"')
  matches = [
    block_line + idx
    for idx, line_text in enumerate(block_content.splitlines(), start=1)
    if not line_text.lstrip().startswith("//") and pattern.search(line_text)
  ]
  if not matches:
    return block_line
  occ_key = (key, val)
  occ_idx = seen_occurrences.get(occ_key, 0)
  seen_occurrences[occ_key] = occ_idx + 1
  return matches[occ_idx] if occ_idx < len(matches) else matches[-1]


def _walk_payload_open_values(
  node: object,
  rel_md: str,
  block_line: int,
  block_content: str,
  doc_vertical: str,
  schema_attr: str,
  has_fragment: bool,
  index: dict,
  warnings: list[dict],
  seen_occurrences: dict[tuple[str, str], int],
  parent_key: str = "",
  path: str = "$",
) -> None:
  """Recursively audit open-enum string values inside a JSON payload."""
  disc_bindings = index["disc_bindings"]
  if isinstance(node, dict):
    disc_val = node.get("type")
    for key, val in node.items():
      child_path = f"{path}.{key}"
      if (
        isinstance(val, str)
        and val != "..."
        and not _REVERSE_DOMAIN_RE.match(val)
      ):
        if (
          isinstance(disc_val, str) and ("type", disc_val, key) in disc_bindings
        ):
          allowed, src_schema = disc_bindings[("type", disc_val, key)]
          if val not in allowed:
            warnings.append(
              {
                "file": rel_md,
                "line": _resolve_value_line(
                  block_line, block_content, key, val, seen_occurrences
                ),
                "path": child_path,
                "field": f"{key} ({disc_val})",
                "value": val,
                "known_values": sorted(set(allowed)),
                "schema": src_schema,
              }
            )
        else:
          binding = _lookup_binding(
            index,
            doc_vertical,
            schema_attr,
            parent_key,
            key,
            has_fragment,
          )
          if binding is not None:
            allowed, src_schema = binding
            if val not in allowed:
              warnings.append(
                {
                  "file": rel_md,
                  "line": _resolve_value_line(
                    block_line, block_content, key, val, seen_occurrences
                  ),
                  "path": child_path,
                  "field": (f"{parent_key}.{key}" if parent_key else key),
                  "value": val,
                  "known_values": sorted(set(allowed)),
                  "schema": src_schema,
                }
              )
      _walk_payload_open_values(
        val,
        rel_md,
        block_line,
        block_content,
        doc_vertical,
        schema_attr,
        has_fragment,
        index,
        warnings,
        seen_occurrences,
        key,
        child_path,
      )
  elif isinstance(node, list):
    for idx, item in enumerate(node):
      _walk_payload_open_values(
        item,
        rel_md,
        block_line,
        block_content,
        doc_vertical,
        schema_attr,
        has_fragment,
        index,
        warnings,
        seen_occurrences,
        parent_key,
        f"{path}[{idx}]",
      )


def audit_docs_open_enum_values(
  docs_dir: Path,
  schemas_dir: Path,
) -> list[dict]:
  """Audit ```json examples in `docs_dir` for non-standard open-enum values.

  Uses `validate_examples.extract_blocks`, `reduce_to_canonical_json`, and
  `strip_ellipsis` to avoid diverging from the official example parser.

  Returns:
    List of non-blocking warning dictionaries with file, line, JSONPath, field,
    value, known values, and schema reference.

  """
  index = _build_schema_value_index(schemas_dir)
  warnings: list[dict] = []

  for md_file in sorted(docs_dir.rglob("*.md")):
    rel_md = md_file.relative_to(docs_dir).as_posix()
    for block in ve.extract_blocks(md_file):
      ann = block.get("annotation") or {}
      if ann.get("skip"):
        continue

      try:
        reduced = ve.reduce_to_canonical_json(block["content"])
        parsed = json.loads(reduced)
        cleaned, _ = ve.strip_ellipsis(parsed)
      except (json.JSONDecodeError, ValueError, TypeError):
        continue

      schema_attr = ann.get("schema", "")
      doc_vertical = _infer_doc_vertical(md_file, docs_dir, schema_attr)
      has_fragment = bool(
        ann.get("extract") or ann.get("target") or ann.get("def")
      )

      _walk_payload_open_values(
        cleaned,
        rel_md,
        block["line"],
        block["content"],
        doc_vertical,
        schema_attr,
        has_fragment,
        index,
        warnings,
        {},
      )

  return warnings


def main(argv: list[str] | None = None) -> int:
  """Run open-enumeration schema and documentation value audit."""
  parser = argparse.ArgumentParser(
    description=(
      "Audit UCP open-enumeration schemas missing `examples` and warn on "
      "non-standard values used in docs."
    )
  )
  parser.add_argument(
    "--schemas-dir",
    type=Path,
    default=Path("source/schemas"),
    help="Path to UCP source schemas directory (default: source/schemas).",
  )
  parser.add_argument(
    "--docs-dir",
    type=Path,
    default=Path("docs"),
    help="Path to UCP documentation directory (default: docs).",
  )
  parser.add_argument(
    "--json",
    action="store_true",
    dest="as_json",
    help="Emit machine-readable JSON output.",
  )
  parser.add_argument(
    "--strict",
    action="store_true",
    help="Return exit code 1 if any missing `examples` or warnings are found.",
  )
  args = parser.parse_args(argv)

  declared, missing = audit_schema_open_enums(args.schemas_dir)
  warnings = audit_docs_open_enum_values(args.docs_dir, args.schemas_dir)

  if args.as_json:
    print(
      json.dumps(
        {
          "declared_count": len(declared),
          "missing_examples_count": len(missing),
          "doc_warnings_count": len(warnings),
          "missing_examples": missing,
          "doc_warnings": warnings,
        },
        indent=2,
      )
    )
  else:
    print(
      f"Open Enumerations in schemas: {len(declared)} with `examples`, "
      f"{len(missing)} missing `examples`"
    )
    if missing:
      print("\n[WARN] Schema open-string fields without `examples`:")
      for item in missing:
        vals = ", ".join(item["suggested_examples"])
        print(
          f"  - {item['schema']}#{item['pointer']} "
          f"(suggested examples: [{vals}])"
        )

    print(
      f"\nDoc value warnings (non-standard open-string values): {len(warnings)}"
    )
    for warn in warnings:
      known = ", ".join(warn["known_values"])
      print(
        f"  - {warn['file']}:{warn['line']} {warn['path']} = "
        f"{warn['value']!r} (schema: {warn['schema']}; well-known: [{known}])"
      )

  if args.strict and (missing or warnings):
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main())
