"""Regression cases for catalog privacy, filtering and unknown-mode handling."""

import unittest

from consumer import (
  ContextCatalogCache,
  price_matches,
  selling_range,
  usable_price,
)


def variant(mode=None, amount=None, currency="USD"):
  """Build a minimal consumer input after schema validation."""
  result = {"id": "v"}
  if mode is not None:
    result["pricing"] = {"mode": mode}
  if amount is not None:
    result["price"] = {"amount": amount, "currency": currency}
  return result


class ConsumerTests(unittest.TestCase):
  """Exercise the motivating failures with independent expected outcomes."""

  def test_missing_price_is_not_free(self):
    """A genuinely free item matches zero; an unresolved item does not."""
    self.assertTrue(price_matches(variant(amount=0), "USD", maximum=0))
    self.assertFalse(price_matches(variant("quote_required"), "USD", maximum=0))

  def test_unknown_numeric_price_is_not_authoritative(self):
    """An unknown mode cannot become priced solely because amount exists."""
    value = variant("com.example.future", 1)
    self.assertIsNone(usable_price(value))
    self.assertFalse(price_matches(value, "USD", maximum=100))

  def test_reference_price_is_not_selling_price(self):
    """A list price must not turn a quote-only variant into a priced one."""
    value = variant("quote_required")
    value["list_price"] = {"amount": 100, "currency": "USD"}
    self.assertIsNone(usable_price(value))

  def test_quote_hint_does_not_remove_usable_price(self):
    """Quote availability is orthogonal to price availability."""
    for mode in ("public", "buyer_specific"):
      value = variant(mode, 49900)
      value["pricing"]["next_step"] = "request_quote"
      self.assertEqual(
        usable_price(
          value,
          buyer_authorized=True,
          pricing_profile_supported=True,
        )["amount"],
        49900,
      )

  def test_range_excludes_unresolved_and_unknown(self):
    """Do not zero-fill a missing price or trust a supplied aggregate."""
    product = {
      "variants": [
        variant(amount=100),
        variant("buyer_specific", 150),
        variant("quote_required"),
        variant("future", 1),
      ],
      "price_range": {"min": {"amount": 1, "currency": "USD"}},
    }
    self.assertEqual(
      selling_range(
        product, buyer_authorized=True, pricing_profile_supported=True
      ),
      {
        "min": {"amount": 100, "currency": "USD"},
        "max": {"amount": 150, "currency": "USD"},
      },
    )

  def test_no_eligible_prices_means_no_range(self):
    """Unknown numeric prices do not produce a usable aggregate."""
    self.assertIsNone(selling_range({"variants": [variant("future", 99)]}))

  def test_incompatible_currencies_or_units_are_not_compared(self):
    """A consumer cannot invent a currency conversion or unit conversion."""
    self.assertFalse(price_matches(variant(amount=10, currency="EUR"), "USD"))
    self.assertIsNone(
      selling_range(
        {"variants": [variant(amount=10), variant(amount=10, currency="EUR")]}
      )
    )
    weight = variant(amount=10)
    weight["quantity_unit"] = {"unit": "KGM", "scale": 0}
    self.assertIsNone(selling_range({"variants": [variant(amount=10), weight]}))

  def test_same_mode_different_buyers_and_ranges_are_isolated(self):
    """Same SKU and mode must not share buyer-specific values or aggregates."""
    cache = ContextCatalogCache()
    for buyer, amount in (
      ("buyer-a:v1:caps-a", 875),
      ("buyer-b:v1:caps-a", 740),
    ):
      response = {"variants": [variant("buyer_specific", amount)]}
      response["price_range"] = selling_range(
        response, buyer_authorized=True, pricing_profile_supported=True
      )
      cache.put("merchant", buyer, "sku", response)
    a = cache.get("merchant", "buyer-a:v1:caps-a", "sku")
    b = cache.get("merchant", "buyer-b:v1:caps-a", "sku")
    self.assertEqual(a["price_range"]["min"]["amount"], 875)
    self.assertEqual(b["price_range"]["min"]["amount"], 740)
    for context in ("anonymous", "buyer-a:v2:caps-a", "buyer-a:v1:caps-b"):
      self.assertIsNone(cache.get("merchant", context, "sku"))
    self.assertIsNone(cache.get("other-merchant", "buyer-a:v1:caps-a", "sku"))

  def test_cached_state_is_not_mutated_by_consumer(self):
    """Returned objects and their source are isolated from stored state."""
    cache = ContextCatalogCache()
    source = {"variants": [variant("buyer_specific", 875)]}
    cache.put("merchant", "buyer-a", "sku", source)
    source["variants"][0]["price"]["amount"] = 0
    first = cache.get("merchant", "buyer-a", "sku")
    first["variants"][0]["price"]["amount"] = 1
    self.assertEqual(
      cache.get("merchant", "buyer-a", "sku")["variants"][0]["price"]["amount"],
      875,
    )

  def test_cache_requires_explicit_context(self):
    """Missing authorization context must not collapse to a shared key."""
    with self.assertRaises(ValueError):
      ContextCatalogCache().get("merchant", "", "sku")

  def test_restricted_prices_require_both_guards(self):
    """Neither auth alone nor profile support alone permits disclosure."""
    restricted = variant("buyer_specific", 100000)
    for auth, profile in ((False, False), (True, False), (False, True)):
      self.assertIsNone(
        usable_price(
          restricted,
          buyer_authorized=auth,
          pricing_profile_supported=profile,
        )
      )
      self.assertFalse(
        price_matches(
          restricted,
          "USD",
          minimum=0,
          buyer_authorized=auth,
          pricing_profile_supported=profile,
        )
      )
    self.assertEqual(
      usable_price(
        restricted, buyer_authorized=True, pricing_profile_supported=True
      )["amount"],
      100000,
    )

  def test_disclosure_neutral_caller_sees_no_price_or_price_list_signal(self):
    """Same public representation can cover list-member and quote-only cases."""
    on_private_list = variant("undisclosed")
    quote_only = variant("undisclosed")
    self.assertEqual(on_private_list, quote_only)
    for item in (on_private_list, quote_only):
      self.assertIsNone(
        usable_price(
          item, buyer_authorized=True, pricing_profile_supported=True
        )
      )
      self.assertFalse(
        price_matches(
          item,
          "USD",
          minimum=0,
          buyer_authorized=True,
          pricing_profile_supported=True,
        )
      )
    self.assertIsNone(
      selling_range({"variants": [on_private_list, quote_only]})
    )

  def test_private_aggregate_requires_entitlement_and_profile(self):
    """Reject a supplied private aggregate unless both guards pass."""
    private = variant("buyer_specific", 100000)
    product = {
      "variants": [private],
      "price_range": {
        "min": {"amount": 100000, "currency": "USD"},
        "max": {"amount": 100000, "currency": "USD"},
      },
    }
    self.assertIsNone(selling_range(product))
    self.assertIsNone(selling_range(product, buyer_authorized=True))
    self.assertEqual(
      selling_range(
        product, buyer_authorized=True, pricing_profile_supported=True
      )["min"]["amount"],
      100000,
    )

  def test_mixed_variant_recomputes_only_authorized_subset(self):
    """Never trust a precomputed aggregate containing restricted prices."""
    response = {
      "variants": [variant(amount=300), variant("buyer_specific", 100)],
      "price_range": {
        "min": {"amount": 100, "currency": "USD"},
        "max": {"amount": 300, "currency": "USD"},
      },
    }
    self.assertEqual(selling_range(response)["min"]["amount"], 300)
    self.assertEqual(selling_range(response)["max"]["amount"], 300)
    self.assertEqual(
      selling_range(
        response, buyer_authorized=True, pricing_profile_supported=True
      )["min"]["amount"],
      100,
    )

  def test_expired_entitlement_is_not_a_cache_key_or_authorization(self):
    """Entitlement loss requires fresh independent authorization decisions."""
    price = variant("buyer_specific", 4800)
    self.assertIsNotNone(
      usable_price(price, buyer_authorized=True, pricing_profile_supported=True)
    )
    self.assertIsNone(
      usable_price(
        price, buyer_authorized=False, pricing_profile_supported=True
      )
    )
    cache = ContextCatalogCache()
    cache.put("merchant", "buyer:entitlement-v1", "product", price)
    self.assertIsNone(
      cache.get("merchant", "buyer:entitlement-v2-revoked", "product")
    )


if __name__ == "__main__":
  unittest.main()
