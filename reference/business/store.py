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

"""A small digital-goods store, held in memory.

Everything the Business knows lives here: a catalog, one discount code, and
the carts and checkouts created during a run. The goods are downloads, so
an order needs an email address and no shipping address.

Ids and the clock are deterministic, so a run always produces the same
wire traffic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from reference.generated.full import models

CURRENCY = "USD"
CHECKOUT_EXPIRES_AT = "2026-01-01T06:00:00Z"  # six hours after "now"

# code -> (title shown to the Buyer, percent off each line)
DISCOUNT_CODES = {"WELCOME10": ("Welcome offer: 10% off", 10)}


def _price(amount: int) -> dict:
  """Return a price in minor units."""
  return {"amount": amount, "currency": CURRENCY}


def _product(key: str, title: str, blurb: str, variants: dict) -> dict:
  """Build a catalog product; `variants` maps a variant title to a price."""
  prices = sorted(variants.values())
  return {
    "id": f"prod_{key}",
    "title": title,
    "description": {"plain": blurb},
    "price_range": {"min": _price(prices[0]), "max": _price(prices[-1])},
    "variants": [
      {
        "id": f"var_{key}_{name.split()[0].lower()}",
        "title": name,
        "description": {"plain": f"{title}, {name.lower()}."},
        "price": _price(amount),
        "availability": {"available": True},
      }
      for name, amount in variants.items()
    ],
  }


PRODUCTS = [
  _product(
    "field_guide",
    "Field Guide to Commerce Protocols",
    "An illustrated e-book on how agents and businesses trade.",
    {"Standard edition": 1800, "Annotated edition": 2400},
  ),
  _product(
    "poster_pack",
    "Checkout Patterns Poster Pack",
    "Six printable posters of common checkout flows.",
    {"Digital download": 900},
  ),
  _product(
    "workshop",
    "Agent Builder Workshop Recording",
    "Three hours of recorded workshop sessions.",
    {"Lifetime access": 4900},
  ),
]


@dataclass(frozen=True)
class Item:
  """One thing the store sells: a variant of a product, as a line item."""

  id: str
  title: str
  price: int  # in minor units


@dataclass
class StoredCart:
  """A cart as the Business keeps it: what the Platform set on it."""

  line_items: list[models.LineItemCreateRequest]
  codes: list[str]  # discount codes, as submitted
  buyer: models.Buyer | None = None
  context: models.Context | None = None


@dataclass
class StoredCheckout(StoredCart):
  """A checkout as the Business keeps it: a cart's fields, and its progress."""

  status: str = "open"  # open, completed or canceled
  cart_id: str | None = None  # the cart it was created from
  order: models.OrderConfirmation | None = None  # set on completion


class Store:
  """All mutable state of the Business."""

  def __init__(self):
    """Start with no carts, checkouts or remembered replies."""
    self.carts: dict[str, StoredCart] = {}
    self.checkouts: dict[str, StoredCheckout] = {}
    self.replies: dict[tuple, tuple] = {}  # see Business.call: idempotency
    self._counters: dict[str, int] = {}

  def new_id(self, prefix: str) -> str:
    """Return the next id for a kind of resource: `cart_1`, `cart_2`, ..."""
    self._counters[prefix] = self._counters.get(prefix, 0) + 1
    return f"{prefix}_{self._counters[prefix]}"

  def item(self, item_id: str) -> Item | None:
    """Find what a line item refers to: a variant of one of the products."""
    for product in PRODUCTS:
      for variant in product["variants"]:
        if variant["id"] == item_id:
          title = f"{product['title']} ({variant['title']})"
          return Item(item_id, title, variant["price"]["amount"])
    return None

  def search(self, query: str) -> list[dict]:
    """Return products whose title or description contains every term."""
    terms = query.lower().split()
    return [
      product
      for product in PRODUCTS
      if all(
        term in f"{product['title']} {product['description']['plain']}".lower()
        for term in terms
      )
    ]
