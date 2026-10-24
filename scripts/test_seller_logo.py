#!/usr/bin/env python3
"""Check seller logo declarations and catalog response validation.

Run: python scripts/test_seller_logo.py
Requires ucp-schema on PATH, as does documentation example validation.
"""

import copy
import json
from pathlib import Path

from validate_examples import validate_payload

SCHEMA_BASE = Path(__file__).resolve().parent.parent / "source" / "schemas"
_RESULTS: list[tuple[str, bool, str]] = []


def _check(name: str, condition: bool, detail: str = "") -> None:
  """Record a test result."""
  _RESULTS.append((name, condition, detail))


def main() -> int:
  """Validate the shared declaration and all three catalog response shapes."""
  schema = json.loads(
    (SCHEMA_BASE / "shopping/types/variant.json").read_text(encoding="utf-8")
  )
  seller = schema["properties"]["seller"]
  logo_schema = seller["properties"].get("logo", {})
  _check("seller declares logo", "logo" in seller["properties"])
  _check(
    "logo references shared Media",
    logo_schema.get("$ref") == "../../common/types/media.json",
  )
  _check("seller is optional", "seller" not in schema["required"])
  _check("logo is optional", "logo" not in seller.get("required", []))

  logo = {
    "type": "image",
    "url": "https://cdn.example.com/store-logo.png",
    "alt_text": "Example Store logo",
    "width": 128,
    "height": 128,
  }
  cases = [
    ("seller absent", None, True),
    ("name only", {"name": "Example Store"}, True),
    ("valid logo", {"name": "Example Store", "logo": logo}, True),
    ("empty logo", {"name": "Example Store", "logo": {}}, False),
    ("null logo", {"name": "Example Store", "logo": None}, False),
    ("string logo", {"name": "Example Store", "logo": logo["url"]}, False),
  ]
  for field in ("type", "url"):
    incomplete = {key: value for key, value in logo.items() if key != field}
    cases.append(
      (f"missing {field}", {"name": "Example Store", "logo": incomplete}, False)
    )
  for field, value in (("url", 42), ("width", 0), ("height", 0)):
    invalid = {**logo, field: value}
    cases.append(
      (f"invalid {field}", {"name": "Example Store", "logo": invalid}, False)
    )
  # Media's type is an open vocabulary, not an image-only enum.
  cases.append(
    (
      "unknown media type",
      {"name": "Example Store", "logo": {**logo, "type": "future_media"}},
      True,
    )
  )

  for schema_path, op in (
    ("shopping/catalog_search", "search"),
    ("shopping/catalog_lookup", "lookup"),
    ("shopping/catalog_lookup", "get_product"),
  ):
    for name, seller_value, expected in cases:
      variant = {
        "id": "variant_1",
        "title": "Example item",
        "description": {"plain": "An example item."},
        "price": {"amount": 1000, "currency": "USD"},
      }
      if seller_value is not None:
        variant["seller"] = copy.deepcopy(seller_value)
      if op == "lookup":
        variant["inputs"] = [{"id": "variant_1", "match": "exact"}]
      product = {
        "id": "product_1",
        "title": "Example product",
        "description": {"plain": "An example product."},
        "price_range": {
          "min": {"amount": 1000, "currency": "USD"},
          "max": {"amount": 1000, "currency": "USD"},
        },
        "variants": [variant],
      }
      payload = {"ucp": {"version": "2026-08-25"}}
      if op == "get_product":
        payload["product"] = product
      else:
        payload["products"] = [product]
      valid, errors = validate_payload(
        payload, schema_path, "response", op, SCHEMA_BASE
      )
      _check(f"{op}: {name}", valid == expected, str(errors))
      if not expected:
        _check(
          f"{op}: {name} fails at seller.logo",
          any("/seller/logo" in error.get("path", "") for error in errors),
          str(errors),
        )

  for name, ok, detail in _RESULTS:
    suffix = f" — {detail}" if not ok and detail else ""
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{suffix}")
  passed = sum(ok for _, ok, _ in _RESULTS)
  failed = len(_RESULTS) - passed
  print(f"\n{passed} passed, {failed} failed")
  return 1 if failed else 0


if __name__ == "__main__":
  raise SystemExit(main())
