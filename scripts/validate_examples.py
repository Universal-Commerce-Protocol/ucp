#!/usr/bin/env python3
# cspell:ignore shema directon
"""Validate JSON examples in UCP specification documentation.

UCP doc examples use a bespoke JSON capability set: strict JSON plus
authoring conveniences that are reduced to canonical JSON before
validation. This module owns that reduction and the validation that
follows.

The author-facing contract lives in docs/documentation/schema-authoring.md
under "Documenting JSON Examples". This docstring is the implementation
contract: a precise, normative description of what the code enforces.
The two MUST stay in sync.

================================================================
THE ANNOTATION CONTRACT
================================================================

Every ```json fenced block in the spec docs MUST be preceded by an
annotation comment:

    <!-- ucp:example schema=PATH [op=OP] [direction=DIR]
                     [extract=JSONPATH] [target=JSONPATH]
                     [def=NAME] -->
    <!-- ucp:example skip reason="..." -->

Defaults: op=read, direction=response.

Recognized attribute keys: schema, op, direction, extract, target,
def, skip, reason. Unknown keys are rejected (typo guard).

At most one annotation per block; multiple stacked annotations
before a fence are rejected. The annotation MUST appear on its own
line preceding the ```json fence; blank lines between are allowed,
any other intervening line clears the pending annotation.

Annotation comments inside any ``` ... ``` fenced block are ignored
(they are documentation of the contract, not real annotations).

Unannotated ```json blocks are hard failures.

================================================================
THE THREE LAYERS
================================================================

Layer 1 — Surface syntax. What authors write. Strict JSON plus:

  (a) Line comments        // to end of line
  (b) Template variable    {{ ucp_version }} (exactly this name)
  (c) HTTP envelope        request/status line + headers + blank
                           line + body — body is extracted
  (d) Elision markers      bare `...` inside [] or {}
                           string "..." as a value
                           list ["..."]
                           object {"...": "..."}

Not supported: trailing commas, block comments /* */, JSON5
features (single quotes, unquoted keys, NaN, hex), interior list
ellipsis [a, ..., b], template variables other than
{{ ucp_version }}, HTTP methods other than GET/POST/PUT/PATCH/DELETE.

Layer 2 — Canonical form. RFC 8259 JSON, produced by reducing
Layer 1 via these stages, in order:

  1. unwrap_http_envelope        (c) → body only
  2. expand_templates            (b) → date substitution
  3. strip_line_comments         (a) → stripped
  4. lower_ellipsis_to_sentinels (d) → bare `...` becomes string
                                 "..." inside containers

The output is parseable by json.loads. Sentinels survive into
Layer 3.

Layer 3 — Semantic interpretation. Operates on the parsed tree:

  - If extract= is present, the indicated subtree is selected from
    the parsed displayed example before semantic validation.
  - Ellipsis sentinels are recorded as elided JSON Pointer paths,
    then removed from the tree.
  - The example is deep-merged into a scaffold (a known-valid
    fixture per schema/op/direction). Example fields win; scaffold
    fills required gaps.
  - Coverage walk: for each object in the example, verify every
    schema-required field is either present or elision-acknowledged.
  - The merged payload is validated by `ucp-schema validate`.
  - Validation errors whose path is an elided path (or descendant)
    are suppressed.

================================================================
KNOWN LIMITATIONS
================================================================

  - Line-comment stripper tracks string boundaries per-line and is
    approximate. An example with a string literal containing an
    escaped backslash followed by `//` will be misparsed. No corpus
    example currently triggers this.
  - The literal three-character string "..." cannot appear in an
    example as actual data — it is reserved as the elision sentinel.

================================================================
CLI
================================================================

  validate_examples.py --schema-base source/schemas/
  validate_examples.py --schema-base source/schemas/ --file FILE
  validate_examples.py --schema-base source/schemas/ --audit

Exit codes: 0 if all pass or skip; 1 if any block fails or errors.
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
# Any fenced code block (json or otherwise). Annotations inside such
# blocks are documentation of the contract, not real annotations.
FENCE_ANY_OPEN_RE = re.compile(r"^(\s*)```(\S*)\s*$")

# Recognized annotation attribute keys. Unknown keys are rejected at
# parse time to catch typos like `shema=` or `directon=`.
_KNOWN_ATTRS = frozenset(
  {"schema", "op", "direction", "extract", "target", "def"}
)

# -----------------------------------------------------------
# Annotation parsing
# -----------------------------------------------------------


def parse_annotation(text: str) -> dict:
  """Parse annotation attributes from the comment body.

  Returns a dict of attribute key/values. Defaults op=read,
  direction=response are applied. Unknown attribute keys are
  reported via a reserved "_error" key (consumed by process_block).
  """
  text = text.strip()
  if text.startswith("skip"):
    reason_match = re.search(r'reason="([^"]*)"', text)
    return {
      "skip": True,
      "reason": (reason_match.group(1) if reason_match else ""),
    }
  attrs: dict = {}
  unknown: list[str] = []
  for m in re.finditer(r'(\w+)=(?:"([^"]+)"|(\S+))', text):
    key = m.group(1)
    value = m.group(2) if m.group(2) is not None else m.group(3)
    if key in _KNOWN_ATTRS:
      attrs[key] = value
    else:
      unknown.append(key)
  if unknown:
    attrs["_error"] = (
      f"unknown annotation attribute(s): {', '.join(sorted(set(unknown)))}"
      f" — recognized keys: {', '.join(sorted(_KNOWN_ATTRS))}"
    )
  attrs.setdefault("op", "read")
  attrs.setdefault("direction", "response")
  return attrs


# -----------------------------------------------------------
# Markdown extraction
# -----------------------------------------------------------


def extract_blocks(filepath: Path) -> list[dict]:
  """Extract ```json blocks with their annotations.

  Tracks non-json fence state so annotation comments inside other
  fenced blocks (e.g. the contract documentation in schema-authoring.md)
  are not parsed as real annotations.

  Detects stacked annotations — two ucp:example comments before a
  fence with no intervening fence — and emits an error block for the
  second one. Per contract, at most one annotation per block.
  """
  lines = filepath.read_text().splitlines()
  blocks: list[dict] = []
  i = 0
  pending_annotation = None
  pending_annotation_line = 0

  while i < len(lines):
    line = lines[i]

    # JSON fence opening — collect content until matching close
    json_match = FENCE_OPEN_RE.match(line)
    if json_match:
      fence_indent = json_match.group(1)
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

      blocks.append(
        {
          "file": str(filepath),
          "line": start_line,
          "content": "\n".join(content_lines),
          "annotation": pending_annotation,
        }
      )
      pending_annotation = None
      pending_annotation_line = 0
      i += 1
      continue

    # Non-JSON fence — skip its contents entirely. Annotations inside
    # are documentation, not directives. Any pending annotation is
    # cleared because a fence isn't a valid carrier for it.
    any_fence_match = FENCE_ANY_OPEN_RE.match(line)
    if any_fence_match:
      fence_indent = any_fence_match.group(1)
      pending_annotation = None
      pending_annotation_line = 0
      i += 1
      while i < len(lines):
        close_match = FENCE_CLOSE_RE.match(lines[i])
        if close_match and len(close_match.group(1)) <= len(fence_indent):
          i += 1  # consume the close
          break
        i += 1
      continue

    # Annotation comment (only outside fences — fence cases handled above)
    ann_match = ANNOTATION_RE.match(line)
    if ann_match:
      if pending_annotation is not None:
        # Stacked annotation: emit an error block for the second one.
        blocks.append(
          {
            "file": str(filepath),
            "line": i + 1,
            "content": "",
            "annotation": None,
            "error": (
              f"multiple stacked annotations before fence "
              f"(previous at line {pending_annotation_line})"
            ),
          }
        )
      pending_annotation = parse_annotation(ann_match.group(2))
      pending_annotation_line = i + 1
      i += 1
      continue

    # Non-blank, non-annotation, non-fence line clears pending
    if pending_annotation and line.strip():
      pending_annotation = None
      pending_annotation_line = 0

    i += 1

  return blocks


# -----------------------------------------------------------
# Layer 1 → Layer 2: text reduction stages
# -----------------------------------------------------------

# Recognized HTTP methods for envelope detection. Other methods
# (OPTIONS, HEAD, CONNECT, TRACE) are not recognized — a block
# starting with one would parse as JSON and fail.
HTTP_METHOD_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE)\s|^HTTP/")


def unwrap_http_envelope(content: str) -> str:
  """Stage 1. Extract JSON body after blank line in HTTP blocks."""
  first_line = content.lstrip().split("\n")[0]
  if HTTP_METHOD_RE.match(first_line):
    parts = content.split("\n\n", 1)
    if len(parts) == 2:
      return parts[1].strip()
  return content


def expand_templates(content: str) -> str:
  """Stage 2. Substitute {{ ucp_version }} with a valid date.

  Strict allowlist of one variable. Other {{ name }} survive into
  json.loads and produce a parse error — intentional.
  """
  return content.replace("{{ ucp_version }}", UCP_VERSION_PLACEHOLDER)


def strip_line_comments(content: str) -> str:
  """Stage 3. Strip // line comments outside string literals.

  Per-line string-boundary tracking. Approximate — see module
  docstring for the documented edge case.
  """
  lines = content.split("\n")
  cleaned = []
  for line in lines:
    result = []
    in_string = False
    i = 0
    while i < len(line):
      ch = line[i]
      if ch == '"' and (i == 0 or line[i - 1] != "\\"):
        in_string = not in_string
        result.append(ch)
      elif (
        ch == "/" and not in_string and i + 1 < len(line) and line[i + 1] == "/"
      ):
        break  # rest of line is comment
      else:
        result.append(ch)
      i += 1
    cleaned.append("".join(result).rstrip())
  return "\n".join(cleaned)


# Bare ... inside an otherwise-empty [] or {} container. Authors
# write `[ ... ]` and `{ ... }` to mean "non-empty container,
# contents elided." These are converted to string-sentinel form
# (`["..."]`, `{"...": "..."}`) so json.loads accepts them; the
# Layer 3 walker recognizes the sentinels as elision markers.
#
# The string-sentinel form is also accepted directly. Interior bare
# dots (e.g. `[1, ..., 3]`) are not supported — only whole-container
# bare-dot ellipsis. For partial elision use the string form
# (`[1, "...", 3]`).
_BARE_ELLIPSIS_ARRAY = re.compile(r"(\[\s*)\.\.\.(\s*\])")
_BARE_ELLIPSIS_OBJECT = re.compile(r"(\{\s*)\.\.\.(\s*\})")


def lower_ellipsis_to_sentinels(content: str) -> str:
  """Stage 4. Lower bare `...` to string-sentinel form."""
  content = _BARE_ELLIPSIS_ARRAY.sub(r'\1"..."\2', content)
  content = _BARE_ELLIPSIS_OBJECT.sub(r'\1"...": "..."\2', content)
  return content


def reduce_to_canonical_json(raw: str) -> str:
  """Layer 1 → Layer 2. Pure text transformation, no JSON parse.

  Applies the four authoring conveniences in order. Output is
  parseable by json.loads. String-sentinel "..." survives into
  Layer 3 and is interpreted there as an elision marker.
  """
  raw = unwrap_http_envelope(raw)
  raw = expand_templates(raw)
  raw = strip_line_comments(raw)
  raw = lower_ellipsis_to_sentinels(raw)
  return raw


def _is_ellipsis(value) -> bool:
  """Check if a value is a recognized ellipsis marker."""
  return (
    value == "..."
    or (isinstance(value, list) and len(value) == 1 and value[0] == "...")
    or (isinstance(value, dict) and value == {"...": "..."})
  )


def strip_ellipsis(obj, _path="", _paths=None):
  """Replace ellipsis markers with empty defaults.

  Returns (cleaned_obj, ellipsis_paths) where ellipsis_paths
  is a set of JSON Pointer paths that were ellipsis-marked.
  Validation errors at these paths are suppressed.
  """
  if _paths is None:
    _paths = set()

  if isinstance(obj, dict):
    result = {}
    for k, v in obj.items():
      child_path = f"{_path}/{k}"
      if v == "...":
        _paths.add(child_path)
        continue
      elif isinstance(v, list) and v == ["..."]:
        _paths.add(child_path)
        result[k] = []
      elif isinstance(v, dict) and v == {"...": "..."}:
        _paths.add(child_path)
        result[k] = {}
      else:
        result[k] = strip_ellipsis(v, child_path, _paths)
    return result if _path else (result, _paths)
  elif isinstance(obj, list):
    items = []
    for i, item in enumerate(obj):
      if item == "...":
        continue
      items.append(strip_ellipsis(item, f"{_path}/{i}", _paths))
    return items if _path else (items, _paths)
  return obj if _path else (obj, _paths)


# -----------------------------------------------------------
# JSONPath navigation (minimal subset)
# -----------------------------------------------------------

_SEGMENT_RE = re.compile(r"^(\w+)(?:\[(\d+)\])?$")


def jsonpath_to_pointer(path: str) -> str:
  """Convert the supported JSONPath subset to a JSON Pointer prefix."""
  if path == "$":
    return ""
  pointer_parts: list[str] = []
  for seg in path.lstrip("$").lstrip(".").split("."):
    m = _SEGMENT_RE.match(seg)
    if not m:
      return ""
    name, idx = m.group(1), m.group(2)
    pointer_parts.append(name)
    if idx is not None:
      pointer_parts.append(idx)
  return "".join(f"/{part}" for part in pointer_parts)


def jsonpath_get(obj, path: str):
  """Get a value from an object using the supported JSONPath subset."""
  if path == "$":
    return obj
  current = obj
  for seg in path.lstrip("$").lstrip(".").split("."):
    m = _SEGMENT_RE.match(seg)
    if not m:
      raise KeyError(seg)
    name, idx = m.group(1), m.group(2)
    current = current[name]
    if idx is not None:
      current = current[int(idx)]
  return current


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


def validate_payload_with_schema(
  payload: dict,
  schema_dict: dict,
  direction: str,
  op: str,
  schema_base: Path,
) -> tuple[bool, list[dict]]:
  """Validate against an extracted schema dict."""
  tmp_schema = None
  tmp_payload = None
  try:
    with tempfile.NamedTemporaryFile(
      mode="w", suffix=".json", delete=False
    ) as f:
      json.dump(schema_dict, f)
      tmp_schema = f.name
    with tempfile.NamedTemporaryFile(
      mode="w", suffix=".json", delete=False
    ) as f:
      json.dump(payload, f)
      tmp_payload = f.name
    result = subprocess.run(
      [
        "ucp-schema",
        "validate",
        tmp_payload,
        "--schema",
        tmp_schema,
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
    if result.returncode != 0:
      return False, [{"path": "", "message": result.stderr.strip()}]
    return True, []
  finally:
    if tmp_schema:
      Path(tmp_schema).unlink()
    if tmp_payload:
      Path(tmp_payload).unlink()


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
      if self.annotation.get("extract"):
        parts.append(f"extract={self.annotation['extract']}")
      if self.annotation.get("target"):
        parts.append(f"target={self.annotation['target']}")
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


def parse_example(raw: str):
  """Layer 2 boundary. Reduce text to JSON, parse to a tree.

  The returned tree still contains string-sentinel "..." markers
  where the source had ellipsis. Layer 3 walkers (check_coverage,
  strip_ellipsis) interpret the sentinels in semantic order:
  coverage first (sentinels signal acknowledged-but-elided fields),
  then strip (sentinels are removed for scaffold merge + validate).

  May raise json.JSONDecodeError if the reduced text isn't valid JSON.
  """
  canonical = reduce_to_canonical_json(raw)
  return json.loads(canonical)


def process_block(
  block: dict,
  schema_base: Path,
  scaffolds_dir: Path,
) -> Result:
  """Run the validation pipeline on one block.

  Three layers, in order:
    Layer 1→2: reduce_to_canonical_json (text → strict JSON)
    Layer 2→3: parse_example (JSON → tree + elided paths)
    Layer 3:    coverage + scaffold merge + schema validate
  """
  file, line = block["file"], block["line"]
  annotation = block["annotation"]

  # Structural errors from extract_blocks (stacked annotations etc.)
  if block.get("error"):
    return Result(file, line, "error", block["error"])

  # Unannotated block
  if annotation is None:
    return Result(file, line, "error", "unannotated JSON block")

  # Annotation parse error (unknown attribute, etc.)
  if annotation.get("_error"):
    return Result(file, line, "error", annotation["_error"], annotation)

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
  extract_path = annotation.get("extract", "$")
  target_path = annotation.get("target")
  schema_def = annotation.get("def")

  # Layers 1→2: reduce text to JSON, parse to tree (with sentinels),
  # then select the authored payload if the displayed block is an envelope.
  try:
    parsed_example = parse_example(block["content"])
  except json.JSONDecodeError as e:
    return Result(file, line, "fail", f"invalid JSON: {e}", annotation)

  try:
    example = jsonpath_get(parsed_example, extract_path)
  except (
    KeyError,
    IndexError,
    TypeError,
  ) as e:
    return Result(
      file,
      line,
      "error",
      f"extract path not found: {extract_path}: {e}",
      annotation,
    )

  # Empty body — trivially valid (e.g. GET, cancel)
  if example == {}:
    return Result(file, line, "ok", annotation=annotation)

  # Layer 3: resolve schema
  try:
    resolved = resolve_schema(schema_path, direction, op, schema_base)
  except RuntimeError as e:
    return Result(file, line, "error", str(e), annotation)

  # 6. Coverage check — def= selects the base validation schema;
  # target= optionally selects a sub-schema within that base for
  # partial examples. Final validation still runs against the full
  # selected base schema after scaffold merge.
  if schema_def:
    defs = resolved.get("$defs", {})
    if schema_def not in defs:
      return Result(
        file,
        line,
        "error",
        f"$defs/{schema_def} not found in schema",
        annotation,
      )
    validation_schema = defs[schema_def]
  else:
    validation_schema = resolved

  if target_path:
    coverage_schema = jsonpath_get_schema(validation_schema, target_path)
  else:
    coverage_schema = validation_schema

  coverage_errors = check_coverage(example, coverage_schema)

  # 7. Strip ellipsis (track paths for error suppression). When the example
  # is inserted at target=, validation errors are reported against the merged
  # payload, so relative elision paths need the same target prefix.
  stripped, ellipsis_paths = strip_ellipsis(example)
  if target_path and ellipsis_paths:
    target_pointer = jsonpath_to_pointer(target_path)
    ellipsis_paths = {f"{target_pointer}{path}" for path in ellipsis_paths}

  # 8. Load scaffold and merge
  scaffold = load_scaffold(schema_path, direction, op, scaffolds_dir)
  if scaffold is None:
    if target_path:
      return Result(
        file,
        line,
        "error",
        f"no scaffold for {schema_path} ({direction}/{op})",
        annotation,
      )
    # Full examples do not need a seed object: coverage already checks the
    # displayed payload against required fields before validation. Scaffolds are
    # only mandatory when target= needs a concrete parent object to insert into.
    scaffold = {}

  if target_path:
    # deep copy
    merged = json.loads(json.dumps(scaffold))
    try:
      jsonpath_set(merged, target_path, stripped)
    except (
      KeyError,
      IndexError,
      TypeError,
    ) as e:
      return Result(
        file,
        line,
        "error",
        f"scaffold navigation failed at {target_path}: {e}",
        annotation,
      )
  else:
    merged = deep_merge(scaffold, stripped)

  # 9. Validate — use extracted $def schema if specified
  if schema_def:
    valid, val_errors = validate_payload_with_schema(
      merged, validation_schema, direction, op, schema_base
    )
  else:
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
    # Suppress errors at ellipsis-acknowledged paths
    err_path = ve.get("path", "")
    if any(
      err_path == ep or err_path.startswith(ep + "/") for ep in ellipsis_paths
    ):
      continue
    messages.append(f"validation: {err_path} \u2014 {ve.get('message', '')}")

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
    nargs="+",
    default=None,
    help="Validate one or more files instead of the full corpus.",
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
  md_files = args.file if args.file else sorted(docs_dir.rglob("*.md"))

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
