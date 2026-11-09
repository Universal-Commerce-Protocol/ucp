#!/usr/bin/env python3
"""Tests for the schema and header table macros in main.py.

The spec's field tables are rendered by MkDocs macros (`schema_fields`,
`extension_schema_fields`, `method_fields`). When a field's type could not
be named, the Type column fell back to "any": every `ucp` metadata field
and every composed (`allOf`) field rendered that way. The type-column tests
call the macros the same way the docs build does and assert on the Type
cell.

`header_fields` renders each REST binding's HTTP Headers table. Headers that
OpenAPI declares outside the parameter list (authentication through
`security`, media types through content maps) must still appear in it,
exactly once.

Some tables resolve schemas through the ucp-schema CLI, so it must be on
PATH (install with `cargo install ucp-schema`).

Run: python3 scripts/test_schema_tables.py
Exit: 0 on all pass, 1 on any failure.
"""

import ast
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parent.parent

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
    suffix = f" — {detail}" if detail and not ok else ""
    print(f"  {status}  {name}{suffix}")
  print(f"\n{passed} passed, {len(failed)} failed")
  return 0 if not failed else 1


class _Env:
  """Stand-in for the mkdocs-macros env: collects registered macros."""

  def __init__(self) -> None:
    self.macros = {}

  def macro(self, fn):
    self.macros[fn.__name__] = fn
    return fn


def _load_macros() -> dict:
  # main.py resolves schema paths relative to the repository root.
  os.chdir(REPO_ROOT)
  sys.path.insert(0, str(REPO_ROOT))
  import main

  env = _Env()
  main.define_env(env)
  return env.macros


def _type_cell(table: str, field: str) -> str | None:
  """Return the Type cell of `field`'s row in a rendered Markdown table."""
  match = re.search(
    rf"^\| {re.escape(field)} \| (.*?) \|", table, flags=re.MULTILINE
  )
  return match.group(1) if match else None


# -----------------------------------------------------------
# Tests
# -----------------------------------------------------------


def test_ucp_ref_links_reference_section(macros: dict) -> None:
  """A `ucp` field $ref'ing a ucp.json $def links its reference anchor."""
  cell = _type_cell(
    macros["schema_fields"]("cart_resp", "shopping/cart"), "ucp"
  )
  _check(
    "ucp_ref_links_reference_section",
    cell is not None
    and "site:specification/reference/#ucp-response-cart-schema" in cell,
    f"got {cell!r}",
  )


def test_bundled_ucp_def_links_reference_section(macros: dict) -> None:
  """A ucp.json $def inlined by bundling is still identified and linked."""
  cell = _type_cell(
    macros["extension_schema_fields"](
      "catalog_search.json#/$defs/search_response", "shopping/catalog"
    ),
    "ucp",
  )
  _check(
    "bundled_ucp_def_links_reference_section",
    cell is not None
    and "site:specification/reference/#ucp-response-catalog-schema" in cell,
    f"got {cell!r}",
  )


def test_ucp_def_without_anchor_is_named(macros: dict) -> None:
  """A ucp.json $def with no reference anchor is named, not linked."""
  cell = _type_cell(
    macros["schema_fields"]("types/error_response", "shopping/checkout"),
    "ucp",
  )
  _check(
    "ucp_def_without_anchor_is_named",
    cell == "UCP Error",
    f"got {cell!r}",
  )


def test_composed_field_links_referenced_type(macros: dict) -> None:
  """An allOf of a $ref plus constraints shows the referenced type."""
  cell = _type_cell(
    macros["schema_fields"]("types/location_serves", "common/location"),
    "address",
  )
  _check(
    "composed_field_links_referenced_type",
    cell is not None and "[Locality]" in cell,
    f"got {cell!r}",
  )


def test_bundled_composed_field_uses_shared_type(macros: dict) -> None:
  """An allOf whose inlined branches agree on a type shows that type."""
  cell = _type_cell(
    macros["extension_schema_fields"](
      "payment_ap2_mandate.json#/$defs/dev.ucp.shopping.checkout",
      "payment/extensions/ap2-mandates",
    ),
    "ap2",
  )
  _check(
    "bundled_composed_field_uses_shared_type",
    cell == "object",
    f"got {cell!r}",
  )


def test_bundled_whole_file_and_inherited_refs_link_reference_section(
  macros: dict,
) -> None:
  """Bundled $defs preserve links for whole-file, inherited, and alias refs."""
  lookup_req = macros["extension_schema_fields"](
    "location_lookup.json#/$defs/lookup_request", "common/location"
  )
  lookup_resp = macros["extension_schema_fields"](
    "location_lookup.json#/$defs/lookup_response", "common/location"
  )
  lookup_loc = macros["extension_schema_fields"](
    "location_lookup.json#/$defs/lookup_location", "common/location"
  )
  fulfillment_search = macros["extension_schema_fields"](
    "fulfillment.json#/$defs/fulfillment_search_request",
    "shopping/extensions/fulfillment",
  )
  payment_with_terms = macros["extension_schema_fields"](
    "payment_terms.json#/$defs/payment", "payment/extensions/terms"
  )
  cases = [
    (
      "lookup_request.distance",
      _type_cell(lookup_req, "distance"),
      "site:specification/reference/#location-distance",
    ),
    (
      "lookup_response.locations",
      _type_cell(lookup_resp, "locations"),
      "site:specification/reference/#location",
    ),
    (
      "lookup_response.messages",
      _type_cell(lookup_resp, "messages"),
      "site:specification/reference/#message",
    ),
    (
      "lookup_location.address",
      _type_cell(lookup_loc, "address"),
      "site:specification/reference/#postal-address",
    ),
    (
      "lookup_location.hours",
      _type_cell(lookup_loc, "hours"),
      "site:specification/reference/#daily-hour",
    ),
    (
      "fulfillment_search_request.pagination",
      _type_cell(fulfillment_search, "pagination"),
      "site:specification/reference/#pagination-request",
    ),
    (
      "payment_terms.terms",
      _type_cell(payment_with_terms, "terms"),
      "site:specification/reference/#payment-term",
    ),
  ]
  missing = [
    f"{name}={got!r}" for name, got, want in cases if not got or want not in got
  ]
  _check(
    "bundled_whole_file_and_inherited_refs_link_reference_section",
    not missing,
    f"missing links: {missing}",
  )


def test_restore_fragment_refs_without_nested_ids() -> None:
  """_restore_fragment_refs recovers refs when ucp-schema 2.0.0 strips $id."""
  main = sys.modules["main"]
  schema_path = REPO_ROOT / "source/schemas/common/location_lookup.json"
  raw_root = main._resolve_schema(schema_path)
  raw_def = main._resolve_json_pointer("#/$defs/lookup_location", raw_root)
  bundled = {
    "description": "Location with required correlation metadata.",
    "allOf": [
      {
        "title": "Location",
        "allOf": [
          {
            "title": "Location Summary",
            "type": "object",
            "properties": {
              "id": {"type": "string"},
              "address": {"title": "Postal Address", "type": "object"},
            },
          },
          {
            "type": "object",
            "properties": {
              "geo": {"title": "Geo", "type": "object"},
              "hours": {
                "type": "array",
                "items": {"title": "Daily Hour", "type": "object"},
              },
            },
          },
        ],
      },
      {
        "type": "object",
        "properties": {
          "inputs": {"type": "array", "items": {"type": "object"}}
        },
      },
    ],
  }
  restored = main._restore_fragment_refs(
    bundled, raw_def, schema_path, raw_root
  )
  summary_props = restored["allOf"][0]["allOf"][0]["properties"]
  loc_props = restored["allOf"][0]["allOf"][1]["properties"]

  # Verify items -> #/$defs/... -> allOf restoration (lookup_response.locations)
  raw_resp = main._resolve_json_pointer("#/$defs/lookup_response", raw_root)
  bundled_resp = {
    "type": "object",
    "properties": {
      "locations": {
        "type": "array",
        "items": {
          "allOf": [
            {"title": "Location", "type": "object"},
            {"type": "object", "properties": {"inputs": {"type": "array"}}},
          ]
        },
      }
    },
  }
  restored_resp = main._restore_fragment_refs(
    bundled_resp, raw_resp, schema_path, raw_root
  )
  locations_branch = restored_resp["properties"]["locations"]["items"]["allOf"][
    0
  ]

  # Verify same-file #/$defs/... alias to cross-file $ref (payment_terms.terms)
  terms_path = REPO_ROOT / "source/schemas/common/payment_terms.json"
  terms_root = main._resolve_schema(terms_path)
  raw_payment = main._resolve_json_pointer("#/$defs/payment", terms_root)
  bundled_payment = {
    "type": "object",
    "properties": {
      "terms": {
        "type": "array",
        "items": {"title": "Payment Term", "type": "object"},
      }
    },
  }
  restored_payment = main._restore_fragment_refs(
    bundled_payment, raw_payment, terms_path, terms_root
  )
  terms_items = restored_payment["properties"]["terms"]["items"]

  # Verify property-level allOf branch restoration (serves.address)
  serves_path = REPO_ROOT / "source/schemas/common/types/location_serves.json"
  raw_serves = main._resolve_schema(serves_path)
  bundled_serves = {
    "type": "object",
    "properties": {
      "address": {
        "allOf": [
          {"title": "Locality", "type": "object"},
          {"required": ["postal_code"]},
        ]
      }
    },
  }
  restored_serves = main._restore_fragment_refs(
    bundled_serves, raw_serves, serves_path, raw_serves
  )
  address_branch = restored_serves["properties"]["address"]["allOf"][0]

  _check(
    "restore_fragment_refs_without_nested_ids",
    summary_props["address"].get("$ref") == "postal_address.json"
    and loc_props["geo"].get("$ref") == "geo.json"
    and loc_props["hours"]["items"].get("$ref") == "daily_hour.json"
    and locations_branch.get("$ref") == "types/location.json"
    and terms_items.get("$ref") == "types/payment_term.json"
    and address_branch.get("$ref") == "locality.json",
    f"got summary={summary_props!r} loc={loc_props!r} "
    f"locations={locations_branch!r} terms={terms_items!r} "
    f"address={address_branch!r}",
  )


def test_method_tables_name_ucp_field(macros: dict) -> None:
  """Operation tables built from OpenAPI name the `ucp` field too."""
  table = macros["method_fields"](
    "search_catalog", "shopping/rest.openapi.json", "shopping/catalog/rest"
  )
  cell = _type_cell(table, "ucp")
  _check(
    "method_tables_name_ucp_field",
    cell is not None and cell != "any",
    f"got {cell!r}",
  )


def _strip_non_root_ids(node: object, *, is_root: bool = True) -> object:
  """Simulate ucp-schema 2.0.0 --bundle stripping non-root `$id`s."""
  if isinstance(node, dict):
    return {
      k: _strip_non_root_ids(v, is_root=False)
      for k, v in node.items()
      if is_root or k != "$id"
    }
  if isinstance(node, list):
    return [_strip_non_root_ids(item, is_root=False) for item in node]
  return node


def _render_synthetic_schema(
  macros: dict, schema: dict, spec_file: str = "reference"
) -> str:
  """Render an arbitrary JSON Schema dict via `method_fields`."""
  main = sys.modules["main"]
  spec = {
    "openapi": "3.1.0",
    "info": {"title": "synthetic", "version": "1"},
    "paths": {
      "/x": {
        "post": {
          "operationId": "op",
          "requestBody": {"content": {"application/json": {"schema": schema}}},
          "responses": {"200": {"description": "ok"}},
        }
      }
    },
  }
  original = main.OPENAPI_DIR
  with tempfile.TemporaryDirectory() as tmp:
    Path(tmp, "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    main.OPENAPI_DIR = Path(tmp)
    try:
      return macros["method_fields"]("op", "spec.json", spec_file, "request")
    finally:
      main.OPENAPI_DIR = original


def test_loyalty_catalog_lookup_one_of_all_of_renders_prose(
  macros: dict,
) -> None:
  """Top-level oneOf without branch `type` renders prose, not an empty table."""
  loyalty = macros["extension_schema_fields"](
    "loyalty.json#/$defs/dev.ucp.shopping.catalog.lookup", "reference"
  )
  union_prose = _render_synthetic_schema(
    macros,
    {
      "oneOf": [
        {"$ref": "types/message.json"},
        {"title": "JSON-RPC Message", "oneOf": [{"type": "object"}]},
      ]
    },
  )
  _check(
    "loyalty_catalog_lookup_one_of_all_of_renders_prose",
    (
      "This object MUST be one of the following types: "
      "Lookup Response, Get Product Response."
    )
    in loyalty
    and "| Name | Type |" not in loyalty
    and (
      "This object MUST be one of the following types: "
      "[Message](site:specification/reference/#message), JSON-RPC Message."
    )
    in union_prose,
    f"loyalty={loyalty!r} union={union_prose!r}",
  )


def test_recursive_schema_and_all_of_constraint_branch(macros: dict) -> None:
  """Recursive `#` refs and constraint-only allOf branches preserve types."""
  main = sys.modules["main"]
  direct = macros["schema_fields"]("types/constraint_expression", "reference")

  ce_path = REPO_ROOT / "source/schemas/common/types/constraint_expression.json"
  raw_ce = main._resolve_schema(ce_path)
  bundled_ce = _strip_non_root_ids(main._resolve_schema_bundled(ce_path))
  restored_ce = main._restore_fragment_refs(bundled_ce, raw_ce, ce_path, raw_ce)
  rendered_bundled_ce = _render_synthetic_schema(macros, restored_ce)

  composed_table = _render_synthetic_schema(
    macros,
    {
      "$id": "https://ucp.dev/schemas/common/types/constraint_expression.json",
      "type": "object",
      "properties": {
        "by_id": {
          "allOf": [
            {
              "$id": "https://ucp.dev/schemas/common/types/locality.json",
              "type": "object",
            },
            {"required": ["postal_code"]},
          ]
        },
        "self_composed": {
          "allOf": [
            {"$ref": "#"},
            {"required": ["id"]},
          ]
        },
        "untitled_constrained": {
          "allOf": [
            {"type": "object", "properties": {"x": {"type": "string"}}},
            {"required": ["x"]},
          ]
        },
      },
    },
  )

  want_props = (
    "Map[string, OneOf["
    "[Constraint Expression]"
    "(site:specification/reference/#constraint-expression), `object`]]"
  )
  want_array = (
    "Array[[Constraint Expression]"
    "(site:specification/reference/#constraint-expression)]"
  )
  _check(
    "recursive_schema_and_all_of_constraint_branch",
    _type_cell(direct, "properties") == want_props
    and _type_cell(direct, "anyOf") == want_array
    and _type_cell(rendered_bundled_ce, "properties") == want_props
    and _type_cell(rendered_bundled_ce, "anyOf") == want_array
    and _type_cell(composed_table, "by_id")
    == "[Locality](site:specification/reference/#locality)"
    and _type_cell(composed_table, "self_composed")
    == (
      "[Constraint Expression]"
      "(site:specification/reference/#constraint-expression)"
    )
    and _type_cell(composed_table, "untitled_constrained") == "object",
    f"direct_props={_type_cell(direct, 'properties')!r} "
    f"bundled_props={_type_cell(rendered_bundled_ce, 'properties')!r} "
    f"composed={composed_table!r}",
  )


def test_fragment_ref_real_anchor_vs_title_fallback(macros: dict) -> None:
  """Fragment refs link real anchors and fall back to title/type otherwise."""
  main = sys.modules["main"]
  lookup_loc = macros["extension_schema_fields"](
    "location_lookup.json#/$defs/lookup_location", "common/location"
  )
  loc_rest = macros["schema_fields"]("types/location", "common/location/rest")
  get_prod = macros["extension_schema_fields"](
    "catalog_lookup.json#/$defs/get_product_response", "shopping/catalog"
  )

  # Cross-file fragment inside allOf: pagination.json#/$defs/request has a real
  # anchor on reference.md (#pagination-request), whereas capability.json's
  # platform_schema has no anchor on shopping/checkout and falls back to title.
  fulfillment_path = REPO_ROOT / "source/schemas/shopping/fulfillment.json"
  raw_synthetic = {
    "type": "object",
    "properties": {
      "anchored_frag": {
        "allOf": [
          {"$ref": "../common/types/pagination.json#/$defs/request"},
          {"required": ["limit"]},
        ]
      },
      "unanchored_frag": {"$ref": "../capability.json#/$defs/platform_schema"},
    },
  }
  bundled_synthetic = {
    "type": "object",
    "properties": {
      "anchored_frag": {
        "allOf": [
          {"type": "object", "properties": {"limit": {"type": "integer"}}},
          {"required": ["limit"]},
        ]
      },
      "unanchored_frag": {"type": "object", "properties": {}},
    },
  }
  restored = main._restore_fragment_refs(
    bundled_synthetic,
    raw_synthetic,
    fulfillment_path,
    raw_synthetic,
    anchor_checker=lambda ref: "pagination.json#/$defs/request" in ref,
  )
  rendered_synthetic = _render_synthetic_schema(
    macros, restored, "shopping/checkout"
  )

  _check(
    "fragment_ref_real_anchor_vs_title_fallback",
    _type_cell(lookup_loc, "amenities") == "Map[string, Amenity]"
    and _type_cell(loc_rest, "amenities")
    == (
      "Map[string, [Amenity](site:specification/common/location/rest/#amenity)]"
    )
    and _type_cell(get_prod, "product")
    == "[Product](site:specification/shopping/catalog/#product)"
    and restored["properties"]["anchored_frag"]["allOf"][0].get("$ref")
    == "../common/types/pagination.json#/$defs/request"
    and "$ref" not in restored["properties"]["unanchored_frag"]
    and _type_cell(rendered_synthetic, "anchored_frag")
    == "[Pagination Request](site:specification/reference/#pagination-request)"
    and _type_cell(rendered_synthetic, "unanchored_frag")
    == "Capability (Platform Schema)",
    f"amenities_loc={_type_cell(lookup_loc, 'amenities')!r} "
    f"amenities_rest={_type_cell(loc_rest, 'amenities')!r} "
    f"product={_type_cell(get_prod, 'product')!r} "
    f"synthetic={rendered_synthetic!r}",
  )


def test_union_any_of_and_map_restoration_and_rendering(macros: dict) -> None:
  """oneOf, anyOf, and Map[string, ...] restore stripped refs and render."""
  main = sys.modules["main"]
  cap_resp = macros["extension_schema_fields"](
    "capability.json#/$defs/response_schema", "reference"
  )
  ucp_plat = macros["extension_schema_fields"](
    "ucp.json#/$defs/platform_schema", "reference"
  )

  types_path = REPO_ROOT / "source/schemas/common/types/location.json"
  raw_schema = {
    "type": "object",
    "properties": {
      "union_obj": {
        "oneOf": [
          {"$ref": "postal_address.json"},
          {"$ref": "locality.json"},
        ]
      },
      "union_items": {
        "type": "array",
        "items": {
          "oneOf": [
            {"$ref": "postal_address.json"},
            {"$ref": "locality.json"},
          ]
        },
      },
      "union_no_top_type": {
        "oneOf": [
          {"$ref": "message.json"},
          {"$ref": "postal_address.json"},
        ]
      },
      "any_of_union": {
        "anyOf": [
          {"$ref": "postal_address.json"},
          {"type": "string"},
        ]
      },
      "constraint_any_of": {
        "type": "object",
        "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
        "anyOf": [{"required": ["a"]}, {"required": ["b"]}],
      },
      "typed_map": {
        "type": "object",
        "additionalProperties": {"$ref": "daily_hour.json"},
      },
      "titled_union": {
        "title": "Destination",
        "oneOf": [
          {"$ref": "postal_address.json"},
          {"$ref": "locality.json"},
        ],
      },
      "titled_map": {
        "title": "Daily Schedule",
        "type": "object",
        "additionalProperties": {"$ref": "daily_hour.json"},
      },
    },
  }
  bundled_schema = {
    "type": "object",
    "properties": {
      "union_obj": {
        "oneOf": [
          {"title": "Postal Address", "type": "object"},
          {"title": "Locality", "type": "object"},
        ]
      },
      "union_items": {
        "type": "array",
        "items": {
          "oneOf": [
            {"title": "Postal Address", "type": "object"},
            {"title": "Locality", "type": "object"},
          ]
        },
      },
      "union_no_top_type": {
        "oneOf": [
          {"title": "Message", "oneOf": [{"type": "object"}]},
          {"title": "Postal Address", "type": "object"},
        ]
      },
      "any_of_union": {
        "anyOf": [
          {"title": "Postal Address", "type": "object"},
          {"type": "string"},
        ]
      },
      "constraint_any_of": {
        "type": "object",
        "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
        "anyOf": [{"required": ["a"]}, {"required": ["b"]}],
      },
      "typed_map": {
        "type": "object",
        "additionalProperties": {"title": "Daily Hour", "type": "object"},
      },
      "titled_union": {
        "title": "Destination",
        "oneOf": [
          {"title": "Postal Address", "type": "object"},
          {"title": "Locality", "type": "object"},
        ],
      },
      "titled_map": {
        "title": "Daily Schedule",
        "type": "object",
        "additionalProperties": {"title": "Daily Hour", "type": "object"},
      },
    },
  }
  restored = main._restore_fragment_refs(
    bundled_schema, raw_schema, types_path, raw_schema
  )
  rendered = _render_synthetic_schema(macros, restored)

  addr_link = "[Postal Address](site:specification/reference/#postal-address)"
  loc_link = "[Locality](site:specification/reference/#locality)"
  msg_link = "[Message](site:specification/reference/#message)"
  hour_link = "[Daily Hour](site:specification/reference/#daily-hour)"
  rdn_link = (
    "[Reverse Domain Name](site:specification/reference/#reverse-domain-name)"
  )
  _check(
    "union_any_of_and_map_restoration_and_rendering",
    _type_cell(cap_resp, "extends") == f"OneOf[{rdn_link}, Array[{rdn_link}]]"
    and _type_cell(ucp_plat, "map_order") == "Map[string, Array[string]]"
    and _type_cell(ucp_plat, "services")
    == "Map[string, Array[Service (Platform Schema)]]"
    and _type_cell(rendered, "union_obj") == f"OneOf[{addr_link}, {loc_link}]"
    and _type_cell(rendered, "union_items")
    == f"Array[OneOf[{addr_link}, {loc_link}]]"
    and _type_cell(rendered, "union_no_top_type")
    == f"OneOf[{msg_link}, {addr_link}]"
    and _type_cell(rendered, "any_of_union") == f"AnyOf[{addr_link}, `string`]"
    and _type_cell(rendered, "constraint_any_of") == "object"
    and _type_cell(rendered, "typed_map") == f"Map[string, {hour_link}]"
    and _type_cell(rendered, "titled_union")
    == f"OneOf[{addr_link}, {loc_link}]"
    and _type_cell(rendered, "titled_map") == f"Map[string, {hour_link}]",
    f"cap_extends={_type_cell(cap_resp, 'extends')!r} "
    f"ucp_plat={ucp_plat!r} rendered={rendered!r}",
  )


def _find_schema_file(entity_name: str) -> Path | None:
  main = sys.modules["main"]
  for d in main.SCHEMAS_DIRS:
    candidate = Path(d) / f"{entity_name}.json"
    if candidate.exists():
      return candidate.resolve()
  return None


def _collect_node_cross_refs(
  node: object,
  cur_path: Path,
  cur_root: dict,
  orig_root_path: Path,
  seen: set | None = None,
) -> list[str]:
  """Collect cross-file `$ref` targets backing a property schema node."""
  main = sys.modules["main"]
  if seen is None:
    seen = set()
  if not isinstance(node, dict):
    return []
  refs: list[str] = []
  raw_ref = node.get("$ref")
  if isinstance(raw_ref, str) and raw_ref:
    ref = raw_ref
    seen_local: set[str] = set()
    while ref.startswith("#/") and ref not in seen_local:
      seen_local.add(ref)
      target = main._resolve_json_pointer(ref, cur_root)
      if isinstance(target, dict) and isinstance(target.get("$ref"), str):
        ref = target["$ref"]
      else:
        break
    if cur_path.resolve() != orig_root_path.resolve():
      rel = Path(
        os.path.relpath(cur_path.resolve(), orig_root_path.resolve().parent)
      ).as_posix()
      if ref == "#":
        ref = rel
      elif ref.startswith("#/"):
        ref = f"{rel}{ref}"
    if not ref.startswith("#"):
      refs.append(ref)
    elif ref.startswith("#/") and (cur_path, ref) not in seen:
      seen.add((cur_path, ref))
      target = main._resolve_json_pointer(ref, cur_root)
      if isinstance(target, dict):
        refs.extend(
          _collect_node_cross_refs(
            target, cur_path, cur_root, orig_root_path, seen
          )
        )

  for sub_key in ("items", "additionalProperties"):
    sub = node.get(sub_key)
    if isinstance(sub, dict):
      refs.extend(
        _collect_node_cross_refs(sub, cur_path, cur_root, orig_root_path, seen)
      )
  for comp_key in ("allOf", "oneOf", "anyOf"):
    comp = node.get(comp_key)
    if isinstance(comp, list):
      for branch in comp:
        refs.extend(
          _collect_node_cross_refs(
            branch, cur_path, cur_root, orig_root_path, seen
          )
        )
  return refs


def _collect_table_cross_refs(
  schema_node: object,
  cur_path: Path,
  cur_root: dict,
  orig_root_path: Path,
  seen: set | None = None,
) -> dict[str, list[str]]:
  """Collect `{field_name: [cross_file_refs]}` across table properties/allOf."""
  main = sys.modules["main"]
  if seen is None:
    seen = set()
  if not isinstance(schema_node, dict):
    return {}
  out: dict[str, list[str]] = {}

  if isinstance(schema_node.get("$ref"), str):
    ref_str = schema_node["$ref"]
    key = (cur_path, ref_str)
    if key not in seen:
      seen.add(key)
      target, next_path, next_root = main._resolve_raw_ref(
        ref_str, cur_path, cur_root
      )
      if isinstance(target, dict) and next_path and isinstance(next_root, dict):
        for fname, field_refs in _collect_table_cross_refs(
          target, next_path, next_root, orig_root_path, seen
        ).items():
          out.setdefault(fname, []).extend(field_refs)

  if isinstance(schema_node.get("allOf"), list):
    for branch in schema_node["allOf"]:
      for fname, field_refs in _collect_table_cross_refs(
        branch, cur_path, cur_root, orig_root_path, seen
      ).items():
        out.setdefault(fname, []).extend(field_refs)

  props = schema_node.get("properties")
  if isinstance(props, dict):
    if isinstance(props.get("allOf"), list):
      for branch in props["allOf"]:
        for fname, field_refs in _collect_table_cross_refs(
          branch, cur_path, cur_root, orig_root_path, seen
        ).items():
          out.setdefault(fname, []).extend(field_refs)
    else:
      for fname, details in props.items():
        if fname == "$ref" and isinstance(details, str):
          target, next_path, next_root = main._resolve_raw_ref(
            details, cur_path, cur_root
          )
          if (
            isinstance(target, dict)
            and next_path
            and isinstance(next_root, dict)
          ):
            for sub_f, sub_refs in _collect_table_cross_refs(
              target, next_path, next_root, orig_root_path, seen
            ).items():
              out.setdefault(sub_f, []).extend(sub_refs)
          continue
        field_refs = _collect_node_cross_refs(
          details, cur_path, cur_root, orig_root_path
        )
        if field_refs:
          out.setdefault(fname, []).extend(field_refs)
  return out


def _is_degraded_type_cell(cell: str) -> bool:
  """Return True when a cross-file `$ref` cell degraded to a generic type."""
  if cell in (
    "any",
    "object",
    "Array[object]",
    "Array[any]",
    "Map[string, object]",
    "Map[string, Array[object]]",
  ):
    return True
  return any(
    prefix in cell and "](" not in cell for prefix in ("OneOf[", "AnyOf[")
  )


def _parse_table_type_cells(md_text: str) -> dict[str, str]:
  """Map `field_name -> Type cell` across Markdown table rows."""
  rows: dict[str, str] = {}
  for line in md_text.splitlines():
    stripped = line.strip()
    if (
      stripped.startswith("|")
      and stripped.endswith("|")
      and not stripped.endswith(r"\|")
    ):
      parts = [p.strip() for p in re.split(r"(?<!\\)\|", stripped)]
      if len(parts) >= 5 and parts[1] not in ("Name", ":---"):
        rows[parts[1]] = parts[2]
  return rows


def test_corpus_cross_file_refs_are_linked_or_named(macros: dict) -> None:
  """Every cross-file `$ref` field rendered in `docs/` is linked or named."""
  main = sys.modules["main"]
  # Untitled, unanchored base `$defs` in service.json and payment_handler.json
  # intentionally carry no standalone anchor or title in the specification.
  allowlisted_refs = {
    "service.json#/$defs/base",
    "payment_handler.json#/$defs/base",
  }
  macro_re = re.compile(
    r"\{\{\s*(schema_fields|extension_schema_fields|extension_fields|"
    r"method_fields|auto_generate_schema_reference)\(([^)]*)\)\s*\}\}"
  )
  checked_fields = 0
  unexpected: list[str] = []

  def split_union_items(items_str: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in items_str:
      if ch in "[(":
        depth += 1
      elif ch in "])":
        depth = max(0, depth - 1)
      if ch == "," and depth == 0:
        parts.append("".join(current).strip())
        current = []
      else:
        current.append(ch)
    if current:
      parts.append("".join(current).strip())
    return parts

  def check_union_prose(
    label: str,
    schema_node: object,
    cur_path: Path,
    cur_root: dict,
    rendered_text: str,
  ) -> None:
    nonlocal checked_fields
    if (
      not isinstance(schema_node, dict)
      or not isinstance(schema_node.get("oneOf"), list)
      or schema_node.get("properties")
      or schema_node.get("allOf")
      or schema_node.get("$ref")
    ):
      return
    branch_refs = [
      _collect_node_cross_refs(branch, cur_path, cur_root, cur_path)
      for branch in schema_node["oneOf"]
    ]
    if not any(branch_refs):
      return
    prose_match = re.search(
      r"This object MUST be one of the following types: (.+)\.", rendered_text
    )
    if not prose_match:
      checked_fields += 1
      unexpected.append(f"{label}[oneOf]=missing_prose")
      return
    items = split_union_items(prose_match.group(1))
    for idx, field_refs in enumerate(branch_refs):
      if not field_refs:
        continue
      checked_fields += 1
      item = items[idx] if idx < len(items) else "<missing>"
      if item in ("`object`", "object", "any", "<missing>") and not (
        set(field_refs) <= allowlisted_refs
      ):
        unexpected.append(f"{label}.oneOf[{idx}]={item!r} (refs={field_refs})")

  def check_table(
    label: str, field_map: dict[str, list[str]], rendered_text: str
  ) -> None:
    nonlocal checked_fields
    trows = _parse_table_type_cells(rendered_text)
    for fname, field_refs in field_map.items():
      if fname not in trows:
        continue
      checked_fields += 1
      cell = trows[fname]
      if (
        _is_degraded_type_cell(cell) and not set(field_refs) <= allowlisted_refs
      ):
        unexpected.append(f"{label}.{fname}={cell!r} (refs={field_refs})")

  for md_path in sorted((REPO_ROOT / "docs").rglob("*.md")):
    rel_md = md_path.relative_to(REPO_ROOT).as_posix()
    for match in macro_re.finditer(md_path.read_text(encoding="utf-8")):
      name, arg_str = match.group(1), match.group(2)
      call = ast.parse(f"f({arg_str})", mode="eval").body
      pos = [ast.literal_eval(a) for a in call.args]
      kw = {k.arg: ast.literal_eval(k.value) for k in call.keywords if k.arg}
      rendered = macros[name](*pos, **kw)

      if name == "schema_fields":
        entity_name = pos[0]
        render_inline = kw.get(
          "render_inline", pos[2] if len(pos) > 2 else True
        )
        if not render_inline and "See [" in rendered:
          continue
        base_name, direction, op = entity_name, "response", "read"
        if entity_name.endswith("_resp"):
          base_name = entity_name[:-5]
        elif entity_name.endswith("_req"):
          parts = entity_name[:-4].rsplit("_", 1)
          if len(parts) == 2 and parts[1] in (
            "create",
            "update",
            "complete",
            "read",
          ):
            base_name, op = parts
          else:
            base_name = entity_name[:-4]
          direction = "request"
        schema_path = _find_schema_file(base_name)
        if not schema_path:
          continue
        raw = main._resolve_schema(schema_path, direction, op, bundle=False)
        label = f"{rel_md}:{name}({arg_str})"
        check_table(
          label,
          _collect_table_cross_refs(raw, schema_path, raw, schema_path),
          rendered,
        )
        check_union_prose(label, raw, schema_path, raw, rendered)

      elif name == "extension_schema_fields":
        entity_name = pos[0]
        render_inline = kw.get(
          "render_inline", pos[2] if len(pos) > 2 else True
        )
        if not render_inline and "|" not in rendered:
          continue
        core_entity, def_part = entity_name.split(".json#", 1)
        schema_path = _find_schema_file(core_entity)
        if not schema_path:
          continue
        raw_root = main._resolve_schema(schema_path)
        raw_def = main._resolve_json_pointer("#" + def_part, raw_root)
        label = f"{rel_md}:{name}({arg_str})"
        check_table(
          label,
          _collect_table_cross_refs(
            raw_def, schema_path, raw_root, schema_path
          ),
          rendered,
        )
        check_union_prose(label, raw_def, schema_path, raw_root, rendered)

      elif name == "extension_fields":
        entity_name = pos[0]
        target_name = kw.get("target", pos[2] if len(pos) > 2 else "checkout")
        schema_path = (
          main.SHOPPING_SCHEMAS_DIR / f"{entity_name}.json"
        ).resolve()
        raw_root = json.loads(schema_path.read_text(encoding="utf-8"))
        target_def = next(
          (
            schema_def
            for k, schema_def in raw_root.get("$defs", {}).items()
            if (k == target_name or k.endswith("." + target_name))
            and isinstance(schema_def, dict)
            and "allOf" in schema_def
          ),
          None,
        )
        if target_def:
          item = next((i for i in target_def["allOf"] if "properties" in i), {})
          check_table(
            f"{rel_md}:{name}({arg_str})",
            _collect_table_cross_refs(item, schema_path, raw_root, schema_path),
            rendered,
          )

      elif name == "auto_generate_schema_reference":
        sub_dir = pos[0] if len(pos) > 0 else kw.get("sub_dir", ".")
        spec_file = (
          pos[1] if len(pos) > 1 else kw.get("spec_file_name", "reference")
        )
        inc_ext = pos[2] if len(pos) > 2 else kw.get("include_extensions", True)
        inc_cap = pos[3] if len(pos) > 3 else kw.get("include_capability", True)
        base_dir = pos[4] if len(pos) > 4 else kw.get("base_dir")
        base_p = Path(base_dir) if base_dir else main.SHOPPING_SCHEMAS_DIR
        scan_p = base_p / sub_dir if sub_dir != "." else base_p
        for schema_file in sorted(
          f for f in scan_p.iterdir() if f.suffix == ".json"
        ):
          sdata = json.loads(schema_file.read_text(encoding="utf-8"))
          is_ext = "Extension" in sdata.get("title", "")
          if (is_ext and not inc_ext) or (not is_ext and not inc_cap):
            continue
          # Qualify by path under source/schemas/ (e.g. `food/cart`): bare
          # stems are ambiguous once verticals share filenames.
          ent = (
            schema_file.resolve()
            .relative_to(main.SCHEMAS_DIR.resolve())
            .with_suffix("")
            .as_posix()
          )
          resolved_file = schema_file.resolve()
          raw_root = main._resolve_schema(resolved_file)
          if is_ext and sdata.get("$defs"):
            for def_name in sdata["$defs"]:
              sub_render = macros["extension_schema_fields"](
                f"{ent}.json#/$defs/{def_name}", spec_file
              )
              raw_def = main._resolve_json_pointer(
                f"#/$defs/{def_name}", raw_root
              )
              label = f"{rel_md}:{ent}.json#/$defs/{def_name}"
              check_table(
                label,
                _collect_table_cross_refs(
                  raw_def, resolved_file, raw_root, resolved_file
                ),
                sub_render,
              )
              check_union_prose(
                label, raw_def, resolved_file, raw_root, sub_render
              )
          else:
            sub_render = macros["schema_fields"](ent, spec_file)
            label = f"{rel_md}:{ent}.json"
            check_table(
              label,
              _collect_table_cross_refs(
                raw_root, resolved_file, raw_root, resolved_file
              ),
              sub_render,
            )
            check_union_prose(
              label, raw_root, resolved_file, raw_root, sub_render
            )

      elif name == "method_fields":
        op_id, file_name = pos[0], pos[1]
        io_type = pos[3] if len(pos) > 3 else kw.get("io_type")
        oa_path = (main.OPENAPI_DIR / file_name).resolve()
        oa_data = json.loads(oa_path.read_text(encoding="utf-8"))
        op_obj = next(
          (
            v
            for path_item in (
              *oa_data.get("paths", {}).values(),
              *oa_data.get("webhooks", {}).values(),
            )
            for v in path_item.values()
            if isinstance(v, dict) and v.get("operationId") == op_id
          ),
          None,
        )
        if not op_obj:
          continue
        if io_type in (None, "request"):
          req_s = (
            op_obj.get("requestBody", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
          )
          req_txt = (
            rendered.split("**Output**")[0]
            if "**Output**" in rendered
            else rendered
          )
          if req_s:
            check_table(
              f"{rel_md}:{name}({op_id},request)",
              _collect_table_cross_refs(req_s, oa_path, oa_data, oa_path),
              req_txt,
            )
        if io_type in (None, "response"):
          res_s = next(
            (
              op_obj["responses"][code]
              .get("content", {})
              .get("application/json", {})
              .get("schema", {})
              for code in ("200", "201")
              if code in op_obj.get("responses", {})
            ),
            {},
          )
          res_txt = (
            rendered.split("**Output**")[1]
            if "**Output**" in rendered
            else rendered
          )
          if res_s:
            check_table(
              f"{rel_md}:{name}({op_id},response)",
              _collect_table_cross_refs(res_s, oa_path, oa_data, oa_path),
              res_txt,
            )

  _check(
    "corpus_cross_file_refs_are_linked_or_named",
    checked_fields >= 1000 and not unexpected,
    f"checked={checked_fields} unexpected={unexpected}",
  )


# -----------------------------------------------------------
# Header tables
# -----------------------------------------------------------


def _header_rows(table: str) -> list[str]:
  """Header names listed in the Request Headers part of a header table."""
  request = table.split("**Response Headers**")[0]
  return re.findall(r"^\| `([^`]+)` \|", request, re.M)


def test_header_tables_list_each_header_once(macros: dict) -> None:
  """No published header table names the same header twice."""
  docs = (REPO_ROOT / "docs").rglob("*.md")
  calls = set(
    re.findall(
      r"header_fields\('([^']+)', '([^']+)'\)",
      "".join(p.read_text(encoding="utf-8") for p in docs),
    )
  )
  duplicated = []
  for operation_id, file_name in sorted(calls):
    table = macros["header_fields"](operation_id, file_name)
    rows = [r.lower() for r in _header_rows(table)]
    if len(rows) != len(set(rows)):
      duplicated.append(operation_id)
  _check(
    "header_tables_list_each_header_once",
    bool(calls) and not duplicated,
    f"duplicates in {duplicated}" if calls else "no header_fields calls",
  )


def test_security_header_rows_follow_requirements() -> None:
  """Auth rows mirror security; required only if every alternative needs it."""
  main = sys.modules["main"]
  schemes = {
    "bearer": {"type": "http", "scheme": "bearer"},
    "basic": {"type": "http", "scheme": "basic"},
    "token": {"type": "oauth2", "flows": {}},
    "key": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
    "query_key": {"type": "apiKey", "in": "query", "name": "key"},
    "mtls": {"type": "mutualTLS"},
  }

  def required(document_security: list, operation: dict | None = None):
    data = {
      "security": document_security,
      "components": {"securitySchemes": schemes},
    }
    rows = main._security_header_rows(data, operation or {})
    return {r["name"]: r["required"] for r in rows}

  cases = [
    (
      "optional_alternatives",
      required([{}, {"bearer": []}, {"key": []}]),
      {"Authorization": False, "X-API-Key": False},
    ),
    ("single", required([{"bearer": []}]), {"Authorization": True}),
    (
      "conjunction",
      required([{"bearer": [], "key": []}]),
      {"Authorization": True, "X-API-Key": True},
    ),
    ("operation_opts_out", required([{"bearer": []}], {"security": []}), {}),
    (
      "operation_overrides",
      required([{"bearer": []}], {"security": [{"key": []}]}),
      {"X-API-Key": True},
    ),
    ("oauth2", required([{"token": []}]), {"Authorization": True}),
    ("no_header", required([{"query_key": []}, {"mtls": []}]), {}),
    (
      "shared_header",
      required([{"bearer": []}, {"basic": []}]),
      {"Authorization": True},
    ),
  ]
  wrong = [name for name, got, want in cases if got != want]
  _check(
    "security_header_rows_follow_requirements",
    not wrong,
    f"wrong: {wrong}",
  )


def test_content_header_rows_follow_media_types() -> None:
  """Content-Type needs a request body; Accept comes from a 2xx response."""
  main = sys.modules["main"]
  data = {
    "components": {
      "requestBodies": {"Body": {"content": {"application/json": {}}}}
    }
  }
  post = {
    "requestBody": {"$ref": "#/components/requestBodies/Body"},
    "responses": {
      "201": {"content": {"application/json": {}}},
      "default": {"content": {"text/plain": {}}},
    },
  }
  get = {"responses": {"200": {"content": {"application/json": {}}}}}
  errors_only = {
    "responses": {
      "4XX": {"content": {"application/json": {}}},
      "default": {"content": {"text/plain": {}}},
    }
  }
  post_rows = [r["name"] for r in main._content_header_rows(data, post)]
  get_rows = [r["name"] for r in main._content_header_rows(data, get)]
  error_rows = main._content_header_rows(data, errors_only)
  _check(
    "content_header_rows_follow_media_types",
    post_rows == ["Content-Type", "Accept"]
    and get_rows == ["Accept"]
    and not error_rows,
    f"post={post_rows} get={get_rows} errors={error_rows}",
  )


def test_declared_header_parameter_keeps_single_row(macros: dict) -> None:
  """A header still declared as a parameter is not synthesized again."""
  main = sys.modules["main"]
  spec = {
    "openapi": "3.1.0",
    "info": {"title": "headers", "version": "1"},
    "security": [{"bearer": []}],
    "paths": {
      "/x": {
        "post": {
          "operationId": "op",
          "parameters": [
            {"name": "Authorization", "in": "header"},
            {"name": "content-type", "in": "header"},
          ],
          "requestBody": {"content": {"application/json": {}}},
          "responses": {"200": {"content": {"application/json": {}}}},
        }
      }
    },
    "components": {
      "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}
    },
  }
  original = main.OPENAPI_DIR
  with tempfile.TemporaryDirectory() as tmp:
    Path(tmp, "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    main.OPENAPI_DIR = Path(tmp)
    try:
      rows = _header_rows(macros["header_fields"]("op", "spec.json"))
    finally:
      main.OPENAPI_DIR = original
  _check(
    "declared_header_parameter_keeps_single_row",
    sorted(r.lower() for r in rows)
    == ["accept", "authorization", "content-type"],
    f"got {rows}",
  )


# -----------------------------------------------------------
# Main
# -----------------------------------------------------------


def main() -> int:
  """Run all tests and report. Exit 0 on pass, 1 on failure."""
  print("Running schema and header table tests...\n")
  if not shutil.which("ucp-schema"):
    _check(
      "ucp_schema_available",
      False,
      "ucp-schema binary not on PATH (cargo install ucp-schema)",
    )
    return _report()
  macros = _load_macros()
  test_ucp_ref_links_reference_section(macros)
  test_bundled_ucp_def_links_reference_section(macros)
  test_ucp_def_without_anchor_is_named(macros)
  test_composed_field_links_referenced_type(macros)
  test_bundled_composed_field_uses_shared_type(macros)
  test_bundled_whole_file_and_inherited_refs_link_reference_section(macros)
  test_restore_fragment_refs_without_nested_ids()
  test_method_tables_name_ucp_field(macros)
  test_loyalty_catalog_lookup_one_of_all_of_renders_prose(macros)
  test_recursive_schema_and_all_of_constraint_branch(macros)
  test_fragment_ref_real_anchor_vs_title_fallback(macros)
  test_union_any_of_and_map_restoration_and_rendering(macros)
  test_corpus_cross_file_refs_are_linked_or_named(macros)
  test_header_tables_list_each_header_once(macros)
  test_security_header_rows_follow_requirements()
  test_content_header_rows_follow_media_types()
  test_declared_header_parameter_keeps_single_row(macros)
  return _report()


if __name__ == "__main__":
  sys.exit(main())
