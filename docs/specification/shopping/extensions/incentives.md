<!--
   Copyright 2026 UCP Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
-->

# Incentives Extension

## Overview

The Incentives Extension lets a business list the offers it is running on
what it just returned: a free-shipping threshold, a quantity deal, a member
price. It composes onto Catalog Search, Catalog Lookup, Cart, and Checkout.

It is response-only. Nothing here applies an offer; application stays with
Cart and Checkout, where the [Discount](discount.md) extension reports what
took effect in `discounts.applied`.

A plain sale price goes on the variant as `price` with `list_price`, as today.
How a member price is computed and reported stays with
[Loyalty](../../common/extensions/loyalty.md). Incentives carry the offers a
business cannot express as a price on a variant.

**Key features:**

- Offers on catalog responses, before the buyer has a cart (`available`)
- Offers a cart or checkout is close to qualifying for, with the remaining
  gap (`approaching`)
- A typed benefit: amount off, percent off, a fixed price, free shipping
- Conditions the business evaluates: order minimum, quantity, an eligibility
  claim
- Offers that can be shown to a buyer who does not yet qualify, without
  changing any price on a variant

**Dependencies:**

- One or more of Catalog Search, Catalog Lookup, Cart, or Checkout
- Discount, when a disclosed code is to be submitted

## Discovery

Businesses advertise incentive support in their profile. The extension can
extend any subset of the four capabilities:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.incentives": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup",
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/incentives",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/incentives.json"
        }
      ]
    }
  }
}
```

A platform that has not negotiated the extension receives the same response
it receives today. A platform that has negotiated it **MAY** present the
incentives alongside the entities they target.

## Schema

Catalog Search and Catalog Lookup responses, including `get_product`, gain an
`incentives` member carrying `available`. Cart and Checkout responses gain an
`incentives` member carrying `available` and `approaching`.

### Incentives

{{ extension_schema_fields('incentives.json#/$defs/incentives', 'shopping/extensions/incentives') }}

### Incentive

{{ extension_schema_fields('incentives.json#/$defs/incentive', 'shopping/extensions/incentives') }}

### Incentive Period

{{ extension_schema_fields('incentives.json#/$defs/period', 'shopping/extensions/incentives') }}

### Incentive Benefit

{{ extension_schema_fields('incentives.json#/$defs/benefit', 'shopping/extensions/incentives') }}

| `type` | Carries | Meaning |
| :-- | :-- | :-- |
| `amount_off` | `amount` | Taken off each targeted item; off the order subtotal when the incentive has no `targets` on a cart or checkout. |
| `percent_off` | `basis_points`, optionally `maximum_amount` | Percentage taken off, in basis points (`1250` = 12.5%), capped at `maximum_amount` when stated. |
| `fixed_price` | `price` | What each targeted variant costs while the incentive applies. **MUST** be below the variant's `price`. |
| `free_shipping` | `fulfillment_option_ids` (optional) | The named fulfillment options cost nothing; any option when omitted. |

The vocabulary is open. A business **MAY** use a reverse-domain name for a
custom benefit kind. A platform **MUST** ignore an incentive whose benefit
type it does not recognize.

### Incentive Conditions

{{ extension_schema_fields('incentives.json#/$defs/conditions', 'shopping/extensions/incentives') }}

`minimum_order_amount` is measured against the session's `subtotal` total:
line item totals after item-level discounts, before fulfillment, tax, and
fees. `minimum_quantity` is summed across every line item the incentive
targets, so two units of one variant and one of another meet a minimum of
three. The set of conditions is closed in this version; a condition a
platform cannot read is one it cannot evaluate.

### Incentive Targets

{{ extension_schema_fields('incentives.json#/$defs/targets', 'shopping/extensions/incentives') }}

Incentives target by id rather than by path because catalog responses are
keyed by product and variant id. Exclusions are taken out of whatever the
other fields select, so "20% off everything except gift cards" is an
incentive with no inclusion list and `excluded_product_ids`.

### Approaching Incentive

{{ extension_schema_fields('incentives.json#/$defs/approaching', 'shopping/extensions/incentives') }}

## Targeting and precedence

An incentive with `targets` applies to those entities only; one without
applies to every product, variant, or line item in the response. Every id in
`targets` names an entity present in the same response. A business **MUST
NOT** use `targets` to advertise what it did not return. This is not
schema-validated.

Several incentives may target the same entity. The business decides which
apply together when it applies them. `combinable: false` tells the platform
not to present the incentive as cumulative with any other. Tiered thresholds
are several incentives, and `approaching` **MAY** list more than one.

An incentive outside its `active_period` is not offered. A platform **MUST**
drop it regardless of cache. A business **SHOULD** set `end_time` on anything
time-limited.

`conditions` are evaluated by the business at application. A platform **MAY**
evaluate the ones it can, such as an order minimum against a cart it holds,
to decide what to present, never what applies. It **MUST NOT** present an
incentive it cannot evaluate as applying.

Incentives are scoped to the response's `context`, like every other value in
it. A business **MUST NOT** list an incentive that does not apply in that
market.

## Gated incentives

A business **MAY** list an incentive whose `conditions.eligibility` names a
claim the buyer has not asserted, so the platform can offer to link the
buyer's account or supply the claim. Listing the incentive states that the
offer exists and what it gives; it does not change `price` on any variant,
and the business resolves the price only for a session that holds the claim,
following the scope rules in [Catalog](../catalog/index.md#scopes) and the
member pricing rules in [Loyalty](../../common/extensions/loyalty.md).

## Codes

Disclosing a code is the business's choice. A disclosed `code` is submitted
through `discounts.codes` exactly as any other code, and the Discount
extension's [rejection codes](discount.md#rejected-codes) apply unchanged. An
incentive with `application: code` and no `code` tells the platform that a
code exists and the buyer must already hold it. `code` is only valid with
`application: code`; the schema rejects it otherwise.

## Responsibilities

A business **MUST** list only incentives it will honor at application under
the stated conditions, and **MUST NOT** target entities it did not return. It
**MUST NOT** change `price` on a variant for a caller that lacks a claim the
incentive is gated on. It **MAY** omit any incentive, and **MAY** list
different incentives to different platforms.

A platform **MUST NOT** present an incentive as applied; `discounts.applied`
is the record of what took effect. It **MUST NOT** present a total derived
from incentives as final. It **MAY** show a figure the business supplied, such
as a `fixed_price`, or one it computed itself, labelled as its own estimate
and as conditional on the named incentive. It **MUST** submit a disclosed code
through `discounts.codes`, and **MUST** ignore an incentive whose benefit type
it does not recognize.

## Relationship to policies

The [`policies[]`](../../overview/index.md#policies) primitive carries terms:
a type, a description, a URL, and what they apply to. An incentive carries a
typed benefit and conditions. A business **MAY** point an incentive's `url` at
a policy page, and **MAY** publish a policy that describes a promotion in
prose; a platform reads the benefit and conditions from the incentive.

## Examples

### Catalog search with a threshold and a member offer

<!-- ucp:example schema=shopping/incentives def=search_response op=search -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.incentives": [
        {
          "version": "{{ ucp_version }}",
          "extends": ["dev.ucp.shopping.catalog.search"]
        }
      ]
    }
  },
  "products": [
    {
      "id": "prod_trail",
      "title": "Trail Runner",
      "description": { "plain": "Lightweight trail running shoe." },
      "price_range": {
        "min": { "amount": 12000, "currency": "USD" },
        "max": { "amount": 12000, "currency": "USD" }
      },
      "variants": [
        {
          "id": "var_trail_9",
          "title": "Trail Runner, size 9",
          "description": { "plain": "Size 9." },
          "price": { "amount": 12000, "currency": "USD" }
        }
      ]
    }
  ],
  "incentives": {
    "available": [
      {
        "id": "inc_fs50",
        "title": "Free standard shipping over $50",
        "application": "automatic",
        "benefit": { "type": "free_shipping" },
        "conditions": {
          "minimum_order_amount": { "amount": 5000, "currency": "USD" }
        }
      },
      {
        "id": "inc_gold_15",
        "title": "Gold members save 15%",
        "application": "automatic",
        "benefit": { "type": "percent_off", "basis_points": 1500 },
        "conditions": { "eligibility": "com.example.loyalty.gold" },
        "targets": { "product_ids": ["prod_trail"] },
        "active_period": { "end_time": "2026-12-31T23:59:59Z" }
      }
    ]
  }
}
```

The platform can tell the buyer that the shoe is $120, that gold members save
15% on it, and that an order this size ships free. It applies nothing, and
`price` on the variant is unchanged for a buyer who has not asserted the
claim.

### Product detail with a quantity deal and a disclosed code

<!-- ucp:example schema=shopping/incentives def=get_product_response op=get_product target=$.incentives -->
```json
{
  "available": [
    {
      "id": "inc_two_pack",
      "title": "Buy 2, save 15%",
      "application": "automatic",
      "benefit": { "type": "percent_off", "basis_points": 1500 },
      "conditions": { "minimum_quantity": 2 },
      "targets": { "product_ids": ["prod_scaffold"] }
    },
    {
      "id": "inc_welcome",
      "title": "$10 off with code WELCOME10",
      "application": "code",
      "code": "WELCOME10",
      "benefit": {
        "type": "amount_off",
        "amount": { "amount": 1000, "currency": "USD" }
      },
      "combinable": false,
      "url": "https://example.com/offers/welcome"
    }
  ]
}
```

### Cart approaching a threshold

<!-- ucp:example schema=shopping/incentives def=dev.ucp.shopping.cart op=update target=$.incentives -->
```json
{
  "available": [
    {
      "id": "inc_fs50",
      "title": "Free standard shipping over $50",
      "application": "automatic",
      "benefit": { "type": "free_shipping" },
      "conditions": {
        "minimum_order_amount": { "amount": 5000, "currency": "USD" }
      }
    }
  ],
  "approaching": [
    {
      "incentive_id": "inc_fs50",
      "remaining_amount": { "amount": 4000, "currency": "USD" }
    }
  ]
}
```

The cart subtotal is $10. The platform can tell the buyer that $40 more
qualifies the order for free shipping. When the subtotal crosses the
threshold, the business applies the incentive and it appears in
`discounts.applied` with `automatic: true`; `approaching` no longer lists it.

### Checkout with a capped site-wide promotion

<!-- ucp:example schema=shopping/incentives def=dev.ucp.shopping.checkout target=$.incentives -->
```json
{
  "available": [
    {
      "id": "inc_holiday",
      "title": "Holiday sale, 20% off everything except gift cards, up to $100",
      "application": "automatic",
      "benefit": {
        "type": "percent_off",
        "basis_points": 2000,
        "maximum_amount": { "amount": 10000, "currency": "USD" }
      },
      "targets": { "excluded_product_ids": ["prod_gift_card"] },
      "active_period": {
        "start_time": "2026-11-20T00:00:00Z",
        "end_time": "2026-12-01T23:59:59Z"
      }
    }
  ]
}
```

Inside the period the business applies the incentive and reports it in
`discounts.applied`. Outside the period it is not offered: the business does
not list it, and a platform holding a cached response drops it.
