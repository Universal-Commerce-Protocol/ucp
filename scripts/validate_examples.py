#!/usr/bin/env python3
"""Validate JSON examples in UCP spec documentation.

Every ```json code block in the spec docs must be annotated
with:

    <!-- ucp:example schema=shopping/checkout
         [path=$.totals] [op=read]
         [direction=response] -->
    ```json
    { ... }
    ```

Or explicitly skipped:

    <!-- ucp:example skip [reason="..."] -->

Unannotated blocks are hard failures.
See artifacts/ucp-testing-proposal.md.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# -----------------------------------------------------------
# Constants
# -----------------------------------------------------------

# any valid YYYY-MM-DD satisfies the pattern
UCP_VERSION_PLACEHOLDER = "2026-04-08"

ANNOTATION_RE = re.compile(r"^(\s*)<!--\s*ucp:example\s+(.*?)\s*-->")
FENCE_OPEN_RE = re.compile(r"^(\s*)```json\s*$")
FENCE_CLOSE_RE = re.compile(r"^(\s*)```\s*$")

# -----------------------------------------------------------
# Annotation parsing
# -----------------------------------------------------------


def parse_annotation(text: str) -> dict:
  """Parse annotation attributes from the comment body."""
  text = text.strip()
  if text.startswith("skip"):
    reason_match = re.search(r'reason="([^"]*)"', text)
    return {
      "skip": True,
      "reason": (reason_match.group(1) if reason_match else ""),
    }
  attrs = {}
  for m in re.finditer(r'(\w+)=(?:"([^"]+)"|(\S+))', text):
    attrs[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
  # Defaults
  attrs.setdefault("op", "read")
  attrs.setdefault("direction", "response")
  return attrs


# -----------------------------------------------------------
# Markdown extraction
# -----------------------------------------------------------


def extract_blocks(filepath: Path) -> list[dict]:
  """Extract ```json blocks with their annotations."""
  lines = filepath.read_text().splitlines()
  blocks: list[dict] = []
  i = 0
  pending_annotation = None

  while i < len(lines):
    line = lines[i]

    # Check for annotation comment
    ann_match = ANNOTATION_RE.match(line)
    if ann_match:
      pending_annotation = parse_annotation(ann_match.group(2))
      i += 1
      continue

    # Check for code fence opening
    fence_match = FENCE_OPEN_RE.match(line)
    if fence_match:
      fence_indent = fence_match.group(1)
      # Collect content until closing fence
      content_lines: list[str] = []
      start_line = i + 1
      i += 1
      while i < len(lines):
        close_match = FENCE_CLOSE_RE.match(lines[i])
        if close_match and len(close_match.group(1)) <= len(fence_indent):
          break
        # Strip indent prefix from content
        content_line = lines[i]
        if fence_indent and content_line.startswith(fence_indent):
          content_line = content_line[len(fence_indent) :]
        content_lines.append(content_line)
        i += 1

      block = {
        "file": str(filepath),
        "line": start_line,
        "content": "\n".join(content_lines),
        "annotation": pending_annotation,
      }
      blocks.append(block)
      pending_annotation = None
      i += 1
      continue

    # Non-blank, non-annotation line clears pending
    if pending_annotation and line.strip():
      pending_annotation = None

    i += 1

  return blocks


# -----------------------------------------------------------
# HTTP unwrap
# -----------------------------------------------------------

HTTP_METHOD_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE)\s|^HTTP/")


def unwrap_http(content: str) -> str:
  """Extract JSON body after blank line in HTTP blocks."""
  first_line = content.lstrip().split("\n")[0]
  if HTTP_METHOD_RE.match(first_line):
    parts = content.split("\n\n", 1)
    if len(parts) == 2:
      return parts[1].strip()
  return content


# -----------------------------------------------------------
# Template expansion
# -----------------------------------------------------------


def expand_templates(content: str) -> str:
  """Replace {{ ucp_version }} with a valid date."""
  return content.replace("{{ ucp_version }}", UCP_VERSION_PLACEHOLDER)


# -----------------------------------------------------------
# Ellipsis handling
# -----------------------------------------------------------

# Bare ... inside [] or {} — convert to valid JSON before
# json.loads.  Authors write [ ... ] for arrays, { ... } for
# objects.  Preprocessing converts these to ["..."] and
# {"...":"..."} respectively.
_BARE_ELLIPSIS_ARRAY = re.compile(r"(\[\s*)\.\.\.(\s*\])")
_BARE_ELLIPSIS_OBJECT = re.compile(r"(\{\s*)\.\.\.(\s*\})")


def preprocess_ellipsis(content: str) -> str:
  """Convert bare ... to valid JSON placeholders."""
  content = _BARE_ELLIPSIS_ARRAY.sub(r'\1"..."\2', content)
  content = _BARE_ELLIPSIS_OBJECT.sub(r'\1"...": "..."\2', content)
  return content


def _is_ellipsis(value) -> bool:
  """Check if a value is a recognized ellipsis marker."""
  return (
    value == "..."
    or (isinstance(value, list) and len(value) == 1 and value[0] == "...")
    or (isinstance(value, dict) and value == {"...": "..."})
  )


def strip_ellipsis(obj):
  """Remove ellipsis markers, returning cleaned object."""
  if isinstance(obj, dict):
    return {k: strip_ellipsis(v) for k, v in obj.items() if not _is_ellipsis(v)}
  elif isinstance(obj, list):
    return [strip_ellipsis(item) for item in obj if item != "..."]
  return obj


# -----------------------------------------------------------
# JSONPath navigation (minimal subset)
# -----------------------------------------------------------

_SEGMENT_RE = re.compile(r"^(\w+)(?:\[(\d+)\])?$")


def jsonpath_set(obj: dict, path: str, value):
  """Set a value at a JSONPath. Mutates obj."""
  segments = path.lstrip("$").lstrip(".").split(".")
  current = obj
  for seg in segments[:-1]:
    m = _SEGMENT_RE.match(seg)
    name, idx = m.group(1), m.group(2)
    current = current[name]
    if idx is not None:
      current = current[int(idx)]
  last = _SEGMENT_RE.match(segments[-1])
  name, idx = last.group(1), last.group(2)
  if idx is not None:
    current[name][int(idx)] = value
  else:
    current[name] = value


def jsonpath_get_schema(schema: dict, path: str) -> dict:
  """Navigate a JSON Schema to the sub-schema at path."""
  segments = path.lstrip("$").lstrip(".").split(".")
  current = schema
  for seg in segments:
    m = _SEGMENT_RE.match(seg)
    name, idx = m.group(1), m.group(2)
    # Resolve through allOf to find properties
    current = _get_property_schema(current, name)
    if current is None:
      return {}
    if idx is not None:
      current = current.get("items", {})
  return current


# -----------------------------------------------------------
# Deep merge
# -----------------------------------------------------------


def deep_merge(scaffold: dict, example: dict) -> dict:
  """Merge example into scaffold.

  Example fields win. Objects recurse, arrays replace.
  """
  if isinstance(scaffold, dict) and isinstance(example, dict):
    result = dict(scaffold)
    for key, value in example.items():
      if (
        key in result
        and isinstance(result[key], dict)
        and isinstance(value, dict)
      ):
        result[key] = deep_merge(result[key], value)
      else:
        result[key] = value
    return result
  return example


# -----------------------------------------------------------
# Coverage walker
# -----------------------------------------------------------


def _collect_required(schema: dict) -> set[str]:
  """Collect required fields, merging allOf branches."""
  required = set(schema.get("required", []))
  for branch in schema.get("allOf", []):
    required |= set(branch.get("required", []))
  return required


def _collect_properties(schema: dict) -> dict:
  """Collect properties, merging allOf branches."""
  props = dict(schema.get("properties", {}))
  for branch in schema.get("allOf", []):
    props.update(branch.get("properties", {}))
  return props


def _get_property_schema(schema: dict, key: str) -> dict | None:
  """Get schema for a property, resolving allOf."""
  props = _collect_properties(schema)
  return props.get(key)


def _resolve_discriminator(schema: dict, value) -> dict:
  """Select matching oneOf branch via discriminator."""
  if not isinstance(value, dict):
    return schema
  disc = schema.get("discriminator", {})
  disc_key = disc.get("propertyName")
  if not disc_key or disc_key not in value:
    return schema
  disc_val = value[disc_key]
  for branch in schema.get("oneOf", []):
    branch_props = _collect_properties(branch)
    const = branch_props.get(disc_key, {}).get("const")
    if const == disc_val:
      return branch
  return schema


def check_coverage(example, schema: dict, path: str = "$") -> list[str]:
  """Verify required fields are present or elided."""
  errors: list[str] = []

  # Guard: skip self-references
  if "$ref" in schema and schema["$ref"] == "#":
    return errors

  # Object coverage
  if isinstance(example, dict):
    obj_type = schema.get("type")
    # Schemas without explicit "type" but with
    # "properties" or "allOf" are still objects.
    has_object_shape = (
      obj_type == "object"
      or "properties" in schema
      or any("properties" in b for b in schema.get("allOf", []))
    )
    if has_object_shape:
      required = _collect_required(schema)
      present = set(example.keys())
      missing = required - present
      for field in sorted(missing):
        errors.append(f'{path}: missing required field "{field}"')

      # Recurse into non-ellipsis fields
      for key, value in example.items():
        if _is_ellipsis(value):
          continue
        prop_schema = _get_property_schema(schema, key)
        if prop_schema is None:
          continue
        # Handle oneOf with discriminator
        if "oneOf" in prop_schema:
          prop_schema = _resolve_discriminator(prop_schema, value)
        errors += check_coverage(
          value,
          prop_schema,
          f"{path}.{key}",
        )

  # Array coverage: check each real element
  elif isinstance(example, list):
    items_schema = schema.get("items", {})
    # Also check allOf for items
    for branch in schema.get("allOf", []):
      if "items" in branch:
        items_schema = branch["items"]
        break
    for i, item in enumerate(example):
      if _is_ellipsis(item):
        continue
      item_schema = items_schema
      # Handle oneOf discriminator on items
      if "oneOf" in item_schema:
        item_schema = _resolve_discriminator(item_schema, item)
      errors += check_coverage(
        item,
        item_schema,
        f"{path}[{i}]",
      )

  return errors


# -----------------------------------------------------------
# Schema resolution (cached)
# -----------------------------------------------------------

_schema_cache: dict[tuple, dict] = {}


def resolve_schema(
  schema_path: str,
  direction: str,
  op: str,
  schema_base: Path,
) -> dict:
  """Resolve a schema via ucp-schema, with caching."""
  key = (schema_path, direction, op)
  if key in _schema_cache:
    return _schema_cache[key]

  full_path = schema_base / f"{schema_path}.json"
  result = subprocess.run(
    [
      "ucp-schema",
      "resolve",
      str(full_path),
      f"--{direction}",
      "--op",
      op,
      "--bundle",
      "--pretty",
    ],
    capture_output=True,
    text=True,
    cwd=str(schema_base.parent),
  )
  if result.returncode != 0:
    raise RuntimeError(
      f"ucp-schema resolve failed for"
      f" {schema_path} ({direction}/{op}):"
      f" {result.stderr.strip()}"
    )
  schema = json.loads(result.stdout)
  _schema_cache[key] = schema
  return schema


# -----------------------------------------------------------
# Payload validation via ucp-schema
# -----------------------------------------------------------


def validate_payload(
  payload: dict,
  schema_path: str,
  direction: str,
  op: str,
  schema_base: Path,
) -> tuple[bool, list[dict]]:
  """Validate a payload via ucp-schema validate."""
  full_schema = schema_base / f"{schema_path}.json"
  with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    json.dump(payload, f)
    tmp_path = f.name

  try:
    result = subprocess.run(
      [
        "ucp-schema",
        "validate",
        tmp_path,
        "--schema",
        str(full_schema),
        f"--{direction}",
        "--op",
        op,
        "--json",
      ],
      capture_output=True,
      text=True,
      cwd=str(schema_base.parent),
    )
    if result.stdout.strip():
      output = json.loads(result.stdout)
      return (
        output.get("valid", False),
        output.get("errors", []),
      )
    # No JSON output — non-zero exit is an error
    if result.returncode != 0:
      return False, [
        {
          "path": "",
          "message": result.stderr.strip(),
        }
      ]
    return True, []
  finally:
    Path(tmp_path).unlink()


# -----------------------------------------------------------
# Scaffold loading
# -----------------------------------------------------------


def load_scaffold(
  schema_path: str,
  direction: str,
  op: str,
  scaffolds_dir: Path,
) -> dict | None:
  """Load scaffold fixture for a schema+direction+op."""
  # Try specific: checkout_request_create.json
  name = schema_path.replace("/", "_")
  specific = scaffolds_dir / f"{name}_{direction}_{op}.json"
  if specific.exists():
    return json.loads(specific.read_text())

  # Try direction-only: checkout_response.json
  dir_only = scaffolds_dir / f"{name}_{direction}.json"
  if dir_only.exists():
    return json.loads(dir_only.read_text())

  # Try generic: checkout.json
  generic = scaffolds_dir / f"{name}.json"
  if generic.exists():
    return json.loads(generic.read_text())

  return None


# -----------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------


class Result:
  """Outcome of validating a single JSON block."""

  def __init__(
    self,
    file: str,
    line: int,
    status: str,
    message: str = "",
    annotation: dict | None = None,
  ) -> None:
    """Initialize a validation result."""
    self.file = file
    self.line = line
    self.status = status
    self.message = message
    self.annotation = annotation or {}

  def __str__(self) -> str:
    """Format result as a human-readable line."""
    rel = self.file
    schema_info = ""
    if self.annotation:
      parts: list[str] = []
      if "schema" in self.annotation:
        parts.append(f"schema={self.annotation['schema']}")
      if self.annotation.get("path"):
        parts.append(f"path={self.annotation['path']}")
      parts.append(f"op={self.annotation.get('op', 'read')}")
      schema_info = f"  [{' '.join(parts)}]"

    prefix = {
      "ok": "OK   ",
      "fail": "FAIL ",
      "skip": "SKIP ",
      "error": "ERR  ",
    }[self.status]

    line = f"{prefix} {rel}:{self.line}{schema_info}"
    if self.message:
      line += f"\n       {self.message}"
    return line


def process_block(
  block: dict,
  schema_base: Path,
  scaffolds_dir: Path,
) -> Result:
  """Run the validation pipeline on one block."""
  file, line = block["file"], block["line"]
  annotation = block["annotation"]

  # Unannotated block
  if annotation is None:
    return Result(file, line, "error", "unannotated JSON block")

  # Skip
  if annotation.get("skip"):
    reason = annotation.get("reason", "")
    return Result(file, line, "skip", reason, annotation)

  # Must have schema
  schema_path = annotation.get("schema")
  if not schema_path:
    return Result(
      file,
      line,
      "error",
      'annotation missing "schema" attribute',
      annotation,
    )

  op = annotation["op"]
  direction = annotation["direction"]
  subtree_path = annotation.get("path")

  # 1. Unwrap HTTP
  content = unwrap_http(block["content"])

  # 2. Expand templates
  content = expand_templates(content)

  # 3. Preprocess bare ... into valid JSON
  content = preprocess_ellipsis(content)

  # 4. Parse JSON
  try:
    example = json.loads(content)
  except json.JSONDecodeError as e:
    return Result(
      file,
      line,
      "fail",
      f"invalid JSON: {e}",
      annotation,
    )

  # 5. Resolve schema
  try:
    resolved = resolve_schema(schema_path, direction, op, schema_base)
  except RuntimeError as e:
    return Result(file, line, "error", str(e), annotation)

  # 6. Coverage check
  if subtree_path:
    coverage_schema = jsonpath_get_schema(resolved, subtree_path)
  else:
    coverage_schema = resolved

  coverage_errors = check_coverage(example, coverage_schema)

  # 7. Strip ellipsis
  stripped = strip_ellipsis(example)

  # 8. Load scaffold and merge
  scaffold = load_scaffold(schema_path, direction, op, scaffolds_dir)
  if scaffold is None:
    return Result(
      file,
      line,
      "error",
      f"no scaffold for {schema_path} ({direction}/{op})",
      annotation,
    )

  if subtree_path:
    # deep copy
    merged = json.loads(json.dumps(scaffold))
    try:
      jsonpath_set(merged, subtree_path, stripped)
    except (
      KeyError,
      IndexError,
      TypeError,
    ) as e:
      return Result(
        file,
        line,
        "error",
        f"scaffold navigation failed at {subtree_path}: {e}",
        annotation,
      )
  else:
    merged = deep_merge(scaffold, stripped)

  # 9. Validate
  valid, val_errors = validate_payload(
    merged,
    schema_path,
    direction,
    op,
    schema_base,
  )

  # Collect all failures
  messages: list[str] = []
  for ce in coverage_errors:
    messages.append(f"coverage: {ce}")
  for ve in val_errors:
    messages.append(
      f"validation: {ve.get('path', '')} \u2014 {ve.get('message', '')}"
    )

  if messages:
    return Result(
      file,
      line,
      "fail",
      "\n       ".join(messages),
      annotation,
    )

  return Result(file, line, "ok", annotation=annotation)


# -----------------------------------------------------------
# CLI
# -----------------------------------------------------------


def main() -> int:
  """Run example validation across spec docs."""
  parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=(argparse.RawDescriptionHelpFormatter),
  )
  parser.add_argument(
    "--schema-base",
    type=Path,
    required=True,
    help="Path to source/schemas/ directory",
  )
  parser.add_argument(
    "--scaffolds",
    type=Path,
    default=None,
    help=("Path to scaffolds directory (default: scripts/scaffolds/)"),
  )
  parser.add_argument(
    "--docs",
    type=Path,
    default=None,
    help=("Path to docs/ directory (default: docs/)"),
  )
  parser.add_argument(
    "--file",
    type=Path,
    default=None,
    help="Validate a single file instead of all",
  )
  parser.add_argument(
    "--audit",
    action="store_true",
    help="Just list blocks without validating",
  )
  args = parser.parse_args()

  # Resolve paths relative to script location
  script_dir = Path(__file__).parent
  repo_root = script_dir.parent

  schema_base = args.schema_base
  if not schema_base.is_absolute():
    schema_base = repo_root / schema_base

  scaffolds_dir = args.scaffolds or script_dir / "scaffolds"
  docs_dir = args.docs or repo_root / "docs"

  # Collect markdown files
  md_files = [args.file] if args.file else sorted(docs_dir.rglob("*.md"))

  # Extract all blocks
  all_blocks: list[dict] = []
  for md_file in md_files:
    blocks = extract_blocks(md_file)
    all_blocks.extend(blocks)

  if args.audit:
    # Audit mode: just report what we found
    annotated = sum(1 for b in all_blocks if b["annotation"] is not None)
    skipped = sum(
      1 for b in all_blocks if b["annotation"] and b["annotation"].get("skip")
    )
    unannotated = sum(1 for b in all_blocks if b["annotation"] is None)
    print(f"Found {len(all_blocks)} JSON blocks across {len(md_files)} files")
    print(f"  annotated: {annotated} ({skipped} skip)")
    print(f"  unannotated: {unannotated}")
    if unannotated:
      print("\nUnannotated blocks:")
      for b in all_blocks:
        if b["annotation"] is None:
          print(f"  {b['file']}:{b['line']}")
    return 1 if unannotated else 0

  # Validate
  results: list[Result] = []
  for block in all_blocks:
    result = process_block(block, schema_base, scaffolds_dir)
    results.append(result)

  # Report
  passed = sum(1 for r in results if r.status == "ok")
  failed = sum(1 for r in results if r.status == "fail")
  errors = sum(1 for r in results if r.status == "error")
  skipped = sum(1 for r in results if r.status == "skip")

  # Print failures and errors first
  for r in results:
    if r.status in ("fail", "error"):
      print(r)
  for r in results:
    if r.status == "skip":
      print(r)

  print(
    f"\n{passed} passed, {failed} failed, {errors} errors, {skipped} skipped"
  )

  return 0 if (failed == 0 and errors == 0) else 1


if __name__ == "__main__":
  sys.exit(main())
