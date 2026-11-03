#!/usr/bin/env python3
"""Validate the experimental schema against fixtures and seeded probes.

This is JSON Schema validation, not generated-SDK or UCP conformance testing.
All references resolve from the two local pinned schema trees.
"""

import argparse
import json
import random
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

HERE = Path(__file__).resolve().parent
VARIANT_URL = "https://ucp.dev/schemas/shopping/types/variant.json"
PRODUCT_URL = "https://ucp.dev/schemas/shopping/types/product.json"


def load_store(root):
  """Load and meta-validate all local schemas without network retrieval."""
  store = {}
  for path in (Path(root) / "source/schemas").rglob("*.json"):
    schema = json.loads(path.read_text())
    Draft202012Validator.check_schema(schema)
    if "$id" in schema:
      store[schema["$id"]] = schema
  if VARIANT_URL not in store or PRODUCT_URL not in store:
    raise ValueError("Expected a UCP schema root")
  return store


def make_validator(url, store):
  """Build a validator with an offline registry and correct nested scope."""
  registry = Registry().with_resources(
    (uri, Resource.from_contents(schema)) for uri, schema in store.items()
  )
  return Draft202012Validator({"$ref": url}, registry=registry)


def random_variant(rng):
  """Generate a priced variant in the baseline-compatible subset."""
  return {
    "id": str(rng.randrange(1_000_000)),
    "title": "Generated",
    "description": {"plain": "Generated fixture"},
    "price": {
      "amount": rng.choice([0, 1, 99, 10000, 1000000000]),
      "currency": "USD",
    },
  }


def product(variants):
  """Build a product with a numeric range for schema-shape probes."""
  amounts = [v["price"]["amount"] for v in variants if "price" in v]
  value = {
    "id": "p",
    "title": "Product",
    "description": {"plain": "Fixture"},
    "variants": variants,
  }
  if amounts:
    value["price_range"] = {
      "min": {"amount": min(amounts), "currency": "USD"},
      "max": {"amount": max(amounts), "currency": "USD"},
    }
  return value


def expected_mode_valid(mode, priced):
  """Express the proposed mode table independently of JSON Schema syntax."""
  if mode is None or mode == "public":
    return priced
  if mode in {"quote_required", "contract_only", "undisclosed"}:
    return not priced
  return True


def verify(baseline, proposed, count):
  """Run fixture expectations, compatibility probes and mode-table probes."""
  stores = [load_store(baseline), load_store(proposed)]
  validators = [
    {
      "variant": make_validator(VARIANT_URL, store),
      "product": make_validator(PRODUCT_URL, store),
    }
    for store in stores
  ]
  vectors = json.loads((HERE / "vectors.json").read_text())["vectors"]
  failures = []
  for vector in vectors:
    instance = json.loads((HERE / "fixtures" / vector["file"]).read_text())
    for side, label in enumerate(("baseline", "proposed")):
      got = validators[side][vector["kind"]].is_valid(instance)
      want = vector[label] == "valid"
      if got != want:
        failures.append(f"{vector['file']}: {label}={got}, expected {want}")
  print(f"Fixture vectors: {len(vectors)}; failures: {len(failures)}")
  rng = random.Random(20261016)
  before = len(failures)
  for index in range(count):
    variants = [random_variant(rng) for _ in range(rng.randint(1, 4))]
    for kind, instance in (
      ("variant", variants[0]),
      ("product", product(variants)),
    ):
      if not all(v[kind].is_valid(instance) for v in validators):
        failures.append(f"priced compatibility {kind} {index}")
  print(f"Priced probes: {count}+{count}; failures: {len(failures) - before}")
  before = len(failures)
  for index in range(count):
    variants = []
    expected = []
    for _ in range(rng.randint(1, 4)):
      value = random_variant(rng)
      mode = rng.choice(
        [
          None,
          "public",
          "buyer_specific",
          "quote_required",
          "contract_only",
          "undisclosed",
          "future",
          "com.example.new",
        ]
      )
      priced = rng.choice([False, True])
      if mode is not None:
        value["pricing"] = {"mode": mode}
      if not priced:
        del value["price"]
      variants.append(value)
      expected.append(expected_mode_valid(mode, priced))
    for kind, instance, want in (
      ("variant", variants[0], expected[0]),
      ("product", product(variants), all(expected)),
    ):
      if validators[1][kind].is_valid(instance) != want:
        failures.append(f"mode-table {kind} {index}, expected {want}")
  print(f"Mode probes: {count}+{count}; failures: {len(failures) - before}")
  for failure in failures:
    print(f"FAIL: {failure}")
  return not failures


def main():
  """Run the reproducible schema-only comparison."""
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--baseline", required=True)
  parser.add_argument("--proposed", default=str(HERE.parents[2]))
  parser.add_argument("--fuzz", type=int, default=300)
  args = parser.parse_args()
  if args.fuzz < 1:
    parser.error("--fuzz must be positive")
  return 0 if verify(args.baseline, args.proposed, args.fuzz) else 1


if __name__ == "__main__":
  raise SystemExit(main())
