#!/usr/bin/env python3
# cspell:ignore shema directon
"""Contract conformance tests for validate_examples.py.

Each test asserts one claim from the contract documented in
validate_examples.py's module docstring (and mirrored in the author
guide at docs/documentation/schema-authoring.md). Tests are
deliberately one-claim-each so a failure points at exactly which rule
broke.

Two layers of testing exist for the validator:

  - **The doc corpus is the integration test.** All 268 ```json blocks
    across 39 spec docs are validated on every CI run. This proves
    real-world examples conform to the contract.

  - **This file is the unit test layer.** It proves the contract is
    *enforced* (negative tests + edge cases). Without it, the corpus
    only proves "conformant examples pass" \u2014 not "non-conformant
    examples are rejected."

Run: python3 scripts/test_validate_examples.py
Exit: 0 on all pass, 1 on any failure.

No external dependencies. Tests that require the `ucp-schema` binary
are gated and skipped if the binary is missing.
"""

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

# Import the validator module under test
sys.path.insert(0, str(Path(__file__).parent))
import validate_examples as v  # noqa: E402

# -----------------------------------------------------------
# Test harness (minimal, no deps)
# -----------------------------------------------------------

_RESULTS: list[tuple[str, bool, str]] = []


def _check(name: str, condition: bool, detail: str = "") -> None:
  """Record a test result."""
  _RESULTS.append((name, condition, detail))


def _report() -> int:
  """Print results and return exit code."""
  passed = sum(1 for _, ok, _ in _RESULTS if ok)
  failed = [(n, d) for n, ok, d in _RESULTS if not ok]
  for name, ok, detail in _RESULTS:
    status = "PASS" if ok else "FAIL"
    suffix = f" \u2014 {detail}" if detail and not ok else ""
    print(f"  {status}  {name}{suffix}")
  print(f"\n{passed} passed, {len(failed)} failed")
  return 0 if not failed else 1


def _has_ucp_schema() -> bool:
  return shutil.which("ucp-schema") is not None


# -----------------------------------------------------------
# Layer 1\u21922: text reduction stages
# -----------------------------------------------------------


def test_layer1_to_layer2() -> None:
  """Text reduction: 4 stages applied in order, output is canonical JSON."""
  # HTTP envelope unwrap \u2014 each recognized method
  for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
    raw = f'{method} /foo HTTP/1.1\nHost: x\n\n{{"a": 1}}'
    out = v.unwrap_http_envelope(raw)
    _check(
      f"http_unwrap[{method}]",
      out == '{"a": 1}',
      f"got {out!r}",
    )

  # HTTP/ response line also unwraps
  raw = 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{"x": 2}'
  _check(
    "http_unwrap[response]",
    v.unwrap_http_envelope(raw) == '{"x": 2}',
  )

  # Unsupported HTTP methods are NOT unwrapped (parsed as JSON, will fail)
  for method in ("OPTIONS", "HEAD", "CONNECT", "TRACE"):
    raw = f'{method} /foo HTTP/1.1\n\n{{"a": 1}}'
    out = v.unwrap_http_envelope(raw)
    _check(
      f"http_unwrap_rejects[{method}]",
      out == raw,  # unchanged
      f"unexpectedly unwrapped: {out!r}",
    )

  # Template substitution \u2014 strict allowlist
  out = v.expand_templates('{"version": "{{ ucp_version }}"}')
  _check(
    "template_substituted[ucp_version]",
    "{{" not in out and "}}" not in out,
    f"got {out!r}",
  )

  # Other template vars are NOT substituted (will fail JSON parse)
  out = v.expand_templates('{"x": "{{ other_var }}"}')
  _check(
    "template_unknown_not_substituted",
    out == '{"x": "{{ other_var }}"}',
  )

  # Line comments stripped
  out = v.strip_line_comments('{"a": 1, // note\n"b": 2}')
  _check(
    "line_comment_stripped",
    "//" not in out and '"a"' in out and '"b"' in out,
    f"got {out!r}",
  )

  # Comments inside string literals are NOT stripped
  out = v.strip_line_comments('{"url": "http://example.com"}')
  _check(
    "line_comment_in_string_preserved",
    "http://example.com" in out,
    f"got {out!r}",
  )

  # Block comments are NOT stripped (will cause JSON parse failure \u2014
  # documented as unsupported)
  out = v.strip_line_comments('{"a": 1 /* block */}')
  _check(
    "block_comment_not_stripped",
    "/* block */" in out,
    f"got {out!r}",
  )

  # Bare ellipsis lowered to string-sentinel form
  out = v.lower_ellipsis_to_sentinels('{"x": [ ... ], "y": { ... }}')
  parsed = json.loads(out)
  _check(
    "bare_ellipsis_array_lowered",
    parsed["x"] == ["..."],
    f"got {parsed['x']!r}",
  )
  _check(
    "bare_ellipsis_object_lowered",
    parsed["y"] == {"...": "..."},
    f"got {parsed['y']!r}",
  )

  # End-to-end reduction: all 4 stages compose
  raw = 'POST /x HTTP/1.1\n\n{"v": "{{ ucp_version }}", "ids": [ ... ]} // c'
  out = v.reduce_to_canonical_json(raw)
  parsed = json.loads(out)
  _check(
    "reduce_to_canonical_json[end_to_end]",
    parsed["ids"] == ["..."] and "{{" not in out,
    f"got {out!r}",
  )


# -----------------------------------------------------------
# Layer 2\u21923: parse_example, ellipsis semantics
# -----------------------------------------------------------


def test_parse_example_keeps_sentinels() -> None:
  """parse_example returns the parsed tree with sentinels intact.

  Layer 3 walkers (check_coverage, strip_ellipsis) interpret them in
  semantic order \u2014 stripping happens AFTER coverage checks.
  """
  tree = v.parse_example('{"id": "...", "items": [ ... ]}')
  _check(
    "parse_example_keeps_sentinels",
    tree == {"id": "...", "items": ["..."]},
    f"got {tree!r}",
  )


def test_strip_ellipsis_records_paths() -> None:
  """strip_ellipsis returns (cleaned_tree, paths) with elided keys removed."""
  tree = {"id": "...", "items": ["..."], "real": 42}
  cleaned, paths = v.strip_ellipsis(tree)
  _check(
    "strip_ellipsis_removes_elided_keys",
    "id" not in cleaned and cleaned["real"] == 42,
    f"got {cleaned!r}",
  )
  _check(
    "strip_ellipsis_records_paths",
    "/id" in paths and "/items" in paths,
    f"got {paths!r}",
  )


def test_string_ellipsis_in_array() -> None:
  """`[1, "...", 3]` \u2014 middle item elided, others kept."""
  tree = [1, "...", 3]
  cleaned, paths = v.strip_ellipsis(tree)
  _check(
    "string_ellipsis_in_array_item",
    cleaned == [1, 3],
    f"got {cleaned!r}",
  )


# -----------------------------------------------------------
# AP2 checkout_mandate pattern
# -----------------------------------------------------------


def test_ap2_checkout_mandate_pattern() -> None:
  """checkout_mandate accepts an SD-JWT+kb and stays a superset of the old.

  An SD-JWT+kb is <issuer-JWT>~<disclosure>...~<KB-JWT>; the trailing
  KB-JWT is itself a JWT, so it contains dots. The pattern must accept that,
  keep accepting what the old pattern accepted, and not go wide open. Reads
  the pattern from the schema so a revert fails here.
  """
  schema_path = (
    Path(__file__).parent.parent / "source/schemas/shopping/ap2_mandate.json"
  )
  pattern = json.loads(schema_path.read_text())["$defs"]["checkout_mandate"][
    "pattern"
  ]

  def matches(value: str) -> bool:
    # fullmatch, not search: the pattern is anchored ^...$ and a JSON Schema
    # validator treats $ as end-of-string (no trailing-newline match).
    return re.fullmatch(pattern, value) is not None

  j = "eyJh.eyJz.SIG"  # a JWT: three base64url parts with dots
  d = "WyJzYWx0Il0"  # a disclosure: one base64url segment, no dots

  for value, why in [
    (f"{j}~{j}", "key binding, zero disclosures"),
    (f"{j}~{d}~{j}", "key binding, one disclosure"),
    (f"{j}~{d}~{d}~{j}", "key binding, many disclosures"),
    (j, "old form: bare issuer JWT"),
    (f"{j}~{d}", "old form: issuer JWT + disclosure"),
  ]:
    _check(
      f"checkout_mandate_accepts[{why}]",
      matches(value),
      f"{value!r} should match {pattern!r}",
    )

  for value, why in [
    ("not a credential", "free text"),
    (f"{j}~{j}~{j}", "two KB-JWTs"),
    (f"{j}~d.e", "malformed two-segment KB-JWT"),
  ]:
    _check(
      f"checkout_mandate_rejects[{why}]",
      not matches(value),
      f"{value!r} should not match {pattern!r}",
    )

  # The fix must be a strict superset: the key-bound form was rejected by
  # the old pattern and is accepted by the new one.
  old = r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+(~[A-Za-z0-9_-]+)*$"
  kb = f"{j}~{d}~{j}"
  _check(
    "checkout_mandate_expands_to_key_binding",
    re.fullmatch(old, kb) is None and matches(kb),
    "old pattern should reject the key-bound form, new should accept it",
  )


# -----------------------------------------------------------
# Annotation parsing
# -----------------------------------------------------------


def test_annotation_parsing() -> None:
  """parse_annotation: defaults, recognized keys, unknown key rejection."""
  ann = v.parse_annotation("schema=shopping/checkout")
  _check(
    "annotation_defaults_applied",
    ann.get("op") == "read" and ann.get("direction") == "response",
    f"got {ann!r}",
  )

  ann = v.parse_annotation('skip reason="because"')
  _check(
    "annotation_skip_with_reason",
    ann.get("skip") is True and ann.get("reason") == "because",
    f"got {ann!r}",
  )

  ann = v.parse_annotation("schema=x op=create direction=request")
  _check(
    "annotation_explicit_op_direction",
    ann.get("op") == "create" and ann.get("direction") == "request",
    f"got {ann!r}",
  )

  # Unknown attribute key rejected via reserved _error
  ann = v.parse_annotation("shema=foo")  # typo
  _check(
    "annotation_unknown_key_rejected",
    "_error" in ann and "shema" in ann["_error"],
    f"got {ann!r}",
  )

  # Extract, target, and def attributes recognized
  ann = v.parse_annotation(
    "schema=x extract=$.result.payload target=$.totals def=request_schema"
  )
  _check(
    "annotation_extract_target_and_def_recognized",
    "_error" not in ann
    and ann.get("extract") == "$.result.payload"
    and ann.get("target") == "$.totals"
    and ann.get("def") == "request_schema",
    f"got {ann!r}",
  )

  # Legacy path= is intentionally not recognized in the final contract.
  ann = v.parse_annotation("schema=x path=$.totals")
  _check(
    "annotation_legacy_path_rejected",
    "_error" in ann and "path" in ann["_error"],
    f"got {ann!r}",
  )


# -----------------------------------------------------------
# extract_blocks: fence tracking, stacked-annotation detection
# -----------------------------------------------------------


def _write_md(content: str) -> Path:
  """Write a temporary markdown file."""
  with tempfile.NamedTemporaryFile(
    mode="w",
    suffix=".md",
    delete=False,
    encoding="utf-8",
  ) as f:
    f.write(content)
    return Path(f.name)


def test_extract_blocks() -> None:
  """extract_blocks: pending annotation, fence state, stacked detection."""
  # Annotation immediately before fence
  md = "# h\n\n<!-- ucp:example schema=foo op=read -->\n```json\n{}\n```\n"
  blocks = v.extract_blocks(_write_md(md))
  _check(
    "extract_basic_annotation",
    len(blocks) == 1 and blocks[0]["annotation"]["schema"] == "foo",
    f"got {blocks!r}",
  )

  # Annotation with blank lines between is still valid
  md = "<!-- ucp:example schema=foo -->\n\n\n```json\n{}\n```\n"
  blocks = v.extract_blocks(_write_md(md))
  _check(
    "extract_blank_lines_between_ok",
    len(blocks) == 1 and blocks[0]["annotation"] is not None,
    f"got {blocks!r}",
  )

  # Intervening prose clears the pending annotation
  md = "<!-- ucp:example schema=foo -->\nSome prose here.\n```json\n{}\n```\n"
  blocks = v.extract_blocks(_write_md(md))
  _check(
    "extract_prose_clears_pending",
    len(blocks) == 1 and blocks[0]["annotation"] is None,
    f"got {blocks!r}",
  )

  # Stacked annotations \u2014 second one emits an error
  md = (
    "<!-- ucp:example schema=a -->\n"
    "<!-- ucp:example schema=b -->\n"
    "```json\n{}\n```\n"
  )
  blocks = v.extract_blocks(_write_md(md))
  errors = [b for b in blocks if b.get("error")]
  _check(
    "extract_stacked_annotations_rejected",
    len(errors) == 1 and "stacked" in errors[0]["error"],
    f"got {blocks!r}",
  )

  # Annotation inside a non-json fence is ignored (it's documentation)
  md = (
    "```\n"
    "<!-- ucp:example schema=ignored -->\n"
    "```\n"
    "\n"
    '<!-- ucp:example skip reason="x" -->\n'
    "```json\n{}\n```\n"
  )
  blocks = v.extract_blocks(_write_md(md))
  real = [b for b in blocks if not b.get("error")]
  _check(
    "extract_annotation_inside_other_fence_ignored",
    len(real) == 1 and real[0]["annotation"].get("skip") is True,
    f"got {real!r}",
  )

  # Nothing yielded for unannotated json blocks (handled at process_block)
  md = "```json\n{}\n```\n"
  blocks = v.extract_blocks(_write_md(md))
  _check(
    "extract_unannotated_block_yielded_with_no_annotation",
    len(blocks) == 1 and blocks[0]["annotation"] is None,
    f"got {blocks!r}",
  )


# -----------------------------------------------------------
# process_block: integration tests requiring ucp-schema
# -----------------------------------------------------------


_REPO_ROOT = Path(__file__).parent.parent
_SCHEMA_BASE = _REPO_ROOT / "source" / "schemas"
_SCAFFOLDS_DIR = _REPO_ROOT / "scripts" / "scaffolds"


def _process(md: str) -> v.Result:
  """Extract one block from `md` and run process_block on it."""
  path = _write_md(md)
  blocks = v.extract_blocks(path)
  assert len(blocks) == 1, f"expected 1 block, got {len(blocks)}"
  return v.process_block(blocks[0], _SCHEMA_BASE, _SCAFFOLDS_DIR)


def test_process_block_integration() -> None:
  """End-to-end through process_block. Requires ucp-schema on PATH."""
  if not _has_ucp_schema():
    _check(
      "process_block_integration",
      False,
      "SKIPPED: ucp-schema binary not on PATH",
    )
    return

  # Trailing comma is now rejected (was tolerated before). Assert on the
  # validator's "invalid JSON:" prefix; Python's JSONDecodeError text isn't
  # stable across versions.
  md = (
    "<!-- ucp:example schema=shopping/checkout op=read -->\n"
    '```json\n{ "a": 1, }\n```\n'
  )
  result = _process(md)
  _check(
    "process_trailing_comma_rejected",
    result.status == "fail" and result.message.startswith("invalid JSON:"),
    f"got {result.status}: {result.message}",
  )

  # Block comment leaves invalid JSON \u2014 fails parse
  md = (
    "<!-- ucp:example schema=shopping/checkout op=read -->\n"
    '```json\n{ "a": 1 /* block */ }\n```\n'
  )
  result = _process(md)
  _check(
    "process_block_comment_rejected",
    result.status == "fail" and "invalid JSON" in result.message,
    f"got {result.status}: {result.message}",
  )

  # NOTE: "unknown template variable not substituted" is covered by the
  # unit test template_unknown_not_substituted above. The integration
  # version is omitted because {{ unknown }} inside a string literal IS
  # valid JSON; failure occurs downstream at schema validation, not parse.

  # Unknown annotation attribute \u2192 ERR
  md = (
    "<!-- ucp:example schema=shopping/checkout shema=typo op=read -->\n"
    "```json\n{}\n```\n"
  )
  result = _process(md)
  _check(
    "process_unknown_annotation_attribute",
    result.status == "error" and "shema" in result.message,
    f"got {result.status}: {result.message}",
  )

  # def= selects a schema variant; target= selects a sub-schema within it.
  md = (
    "<!-- ucp:example schema=profile def=business_schema target=$.ucp.capabilities -->\n"  # noqa: E501
    '```json\n{ "dev.ucp.shopping.checkout": [{ "version": "{{ ucp_version }}", "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json" }] }\n```\n'  # noqa: E501
  )
  result = _process(md)
  _check(
    "process_def_and_target_compose",
    result.status == "ok",
    f"got {result.status}: {result.message}",
  )

  # Complete examples validate without a scaffold. Scaffolds are only required
  # when target= needs a parent object to insert the displayed fragment into.
  md = (
    "<!-- ucp:example schema=common/identity_linking def=scope_policy -->\n"
    '```json\n{ "description": { "plain": "Manage orders" } }\n```\n'
  )
  path = _write_md(md)
  blocks = v.extract_blocks(path)
  with tempfile.TemporaryDirectory() as empty_scaffolds:
    result = v.process_block(blocks[0], _SCHEMA_BASE, Path(empty_scaffolds))
  _check(
    "process_full_example_no_scaffold_ok",
    result.status == "ok",
    f"got {result.status}: {result.message}",
  )

  # extract= reads a payload subtree from the displayed JSON block before
  # normal target/scaffold validation.
  md = (
    "<!-- ucp:example schema=profile def=business_schema extract=$.ucp.payment_handlers target=$.ucp.payment_handlers -->\n"  # noqa: E501
    '```json\n{ "ucp": { "payment_handlers": { "com.example.handler": [{ "id": "h1", "version": "{{ ucp_version }}" }] } } }\n```\n'  # noqa: E501
  )
  result = _process(md)
  _check(
    "process_extract_then_target_ok",
    result.status == "ok",
    f"got {result.status}: {result.message}",
  )

  # Missing extract= path is a hard annotation/runtime error, not skip/fail.
  md = (
    "<!-- ucp:example schema=profile def=business_schema extract=$.missing target=$.ucp.payment_handlers -->\n"  # noqa: E501
    "```json\n{}\n```\n"
  )
  result = _process(md)
  _check(
    "process_extract_missing_path_errors",
    result.status == "error" and "extract path not found" in result.message,
    f"got {result.status}: {result.message}",
  )

  # Ellipsis paths inside a target= fragment are reported by validators at
  # their merged payload path, so suppression must include the target prefix.
  md = (
    "<!-- ucp:example schema=profile def=business_schema target=$.ucp.payment_handlers -->\n"  # noqa: E501
    '```json\n{ "com.example.handler": [{ "id": "h1", "version": "{{ ucp_version }}", "available_instruments": [ ... ] }] }\n```\n'  # noqa: E501
  )
  result = _process(md)
  _check(
    "process_target_ellipsis_paths_prefixed",
    result.status == "ok",
    f"got {result.status}: {result.message}",
  )

  # Empty body trivially valid
  md = (
    "<!-- ucp:example schema=shopping/checkout op=cancel direction=request -->\n"  # noqa: E501
    "```json\n{}\n```\n"
  )
  result = _process(md)
  _check(
    "process_empty_body_ok",
    result.status == "ok",
    f"got {result.status}: {result.message}",
  )


# -----------------------------------------------------------
# Main
# -----------------------------------------------------------


def main() -> int:
  """Run all contract tests and report. Exit 0 on pass, 1 on failure."""
  print("Running validate_examples contract tests...\n")
  test_layer1_to_layer2()
  test_parse_example_keeps_sentinels()
  test_strip_ellipsis_records_paths()
  test_string_ellipsis_in_array()
  test_ap2_checkout_mandate_pattern()
  test_annotation_parsing()
  test_extract_blocks()
  test_process_block_integration()
  return _report()


if __name__ == "__main__":
  sys.exit(main())
