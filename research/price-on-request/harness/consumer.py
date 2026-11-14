"""Experimental consumer behavior for schema-validated catalog responses.

The caller must authenticate and derive the opaque authorization context.
This module does not authenticate buyers or implement an HTTP cache.
"""

from copy import deepcopy


def usable_price(
  variant, *, buyer_authorized=False, pricing_profile_supported=False
):
  """Fail closed on restricted prices without BOTH authorization and support.

  The booleans must be derived by the integrating Platform from authenticated
  buyer entitlement and explicit pricing-profile negotiation. This module
  neither authenticates callers nor negotiates UCP capabilities.
  """
  mode = variant.get("pricing", {}).get("mode", "public")
  if mode not in {"public", "buyer_specific"}:
    return None
  if mode == "buyer_specific" and not (
    buyer_authorized and pricing_profile_supported
  ):
    return None
  return deepcopy(variant.get("price"))


def price_matches(
  variant,
  currency,
  minimum=None,
  maximum=None,
  *,
  buyer_authorized=False,
  pricing_profile_supported=False,
):
  """Exclude missing or unauthorized prices from numeric filters."""
  price = usable_price(
    variant,
    buyer_authorized=buyer_authorized,
    pricing_profile_supported=pricing_profile_supported,
  )
  if price is None or price["currency"] != currency:
    return False
  amount = price["amount"]
  return (minimum is None or amount >= minimum) and (
    maximum is None or amount <= maximum
  )


def selling_range(
  product, *, buyer_authorized=False, pricing_profile_supported=False
):
  """Recompute from eligible variants instead of trusting a supplied range.

  Currency conversion and cross-unit comparison are intentionally unsupported.
  The result may cover only the priced subset and is not the product's full
  commercial range. The containing response retains the pricing markers.
  """
  priced = [
    (
      variant,
      usable_price(
        variant,
        buyer_authorized=buyer_authorized,
        pricing_profile_supported=pricing_profile_supported,
      ),
    )
    for variant in product["variants"]
  ]
  priced = [(variant, price) for variant, price in priced if price is not None]
  if not priced:
    return None
  currencies = {price["currency"] for _, price in priced}
  units = {
    (
      variant.get("quantity_unit", {}).get("unit", "C62"),
      variant.get("quantity_unit", {}).get("scale", 0),
    )
    for variant, _ in priced
  }
  if len(currencies) != 1 or len(units) != 1:
    return None
  prices = [price for _, price in priced]
  return {
    "min": deepcopy(min(prices, key=lambda price: price["amount"])),
    "max": deepcopy(max(prices, key=lambda price: price["amount"])),
  }


class ContextCatalogCache:
  """Reference isolation map; authorization and freshness remain external.

  Context must distinguish buyer, entitlement revision, negotiated capability
  set, and any other price-relevant context. Mode is never an isolation key.
  Production implementations also need expiry and authorization revalidation.
  """

  def __init__(self):
    """Create an empty, private in-memory map."""
    self._responses = {}

  @staticmethod
  def _key(business, context, request):
    if not all(
      isinstance(value, str) and value for value in (business, context, request)
    ):
      raise ValueError(
        "Business, authorization context and request are required"
      )
    return business, context, request

  def put(self, business, context, request, response):
    """Store the full response, including caller-specific derived fields."""
    self._responses[self._key(business, context, request)] = deepcopy(response)

  def get(self, business, context, request):
    """Return a copy without allowing a consumer to mutate shared state."""
    return deepcopy(self._responses.get(self._key(business, context, request)))
