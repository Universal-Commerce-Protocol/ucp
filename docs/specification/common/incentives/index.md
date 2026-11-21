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

# Incentives

* **Extension Name:** `dev.ucp.common.incentives`
* **Capability Name:** `dev.ucp.common.incentives.list`

## Overview

Incentives let a Business tell a Platform which offers it is running before
any of them is applied: a free-shipping threshold, a quantity deal, a member
discount, a promo code it is happy to disclose.

There are two ways to read them:

* The **Incentives extension** (`dev.ucp.common.incentives`) adds an
  `incentives` member to Cart and Checkout responses. It lists the offers on
  the session that are not applied yet (`available`) and the ones the session
  is close to qualifying for, with the remaining gap (`approaching`).
* The **Incentives List capability** (`dev.ucp.common.incentives.list`) is a
  standalone operation on the Common service. A Platform can ask what a
  Business is offering right now without running a product search or opening
  a session.

Both are read-only and both use the same incentive model. Nothing here
applies an offer. Application stays with Cart and Checkout, where the
[Discount](../../shopping/extensions/discount.md) extension reports what took
effect in `discounts.applied`, and the Business is authoritative on every
amount.

A plain sale price still goes on the variant as `price` with `list_price`.
How a member price is computed and reported stays with
[Loyalty](../extensions/loyalty.md). Incentives carry the offers a Business
cannot express as a price on a variant.

Incentives are a Common extension because promotions and threshold nudges are
not specific to retail. This version composes onto Shopping Cart and Checkout;
other verticals can compose the same model onto their sessions without
forking it.

**Key features:**

* One shared, typed model for what a discount gives
  ([Discount Benefit](#discount-benefit)): amount off, percent off, a fixed
  price, free shipping, a free item
* Offers on a session that are not applied yet (`available`), targeted with
  the same `applies_to` JSONPath convention as
  [policies](../../overview/index.md#policies)
* Offers a session is close to qualifying for, with a gap the Business
  computed (`approaching`)
* Open conditions: an order minimum, a quantity, an eligibility claim, and
  whatever a Business or another extension adds
* A way to link an applied discount back to the offer it came from
  (`discounts.applied[].incentive_id`)
* A standalone list of what the Business is offering

**Dependencies:**

* Cart or Checkout, for the extension
* The Common service, for the List capability
* Discount, when a disclosed code is to be submitted or an applied discount is
  to be linked to its incentive

**Out of scope for this version:** incentives on Catalog search, lookup, and
product detail responses. Linking offers to products and variants in the
catalog is specified separately, on top of this model.

## Discovery

Businesses advertise the extension and the capability in their profile. They
are independent: a Business **MAY** support either one without the other.

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.incentives": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/incentives",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/incentives.json"
        }
      ],
      "dev.ucp.common.incentives.list": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/incentives",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/incentives_list.json"
        }
      ]
    }
  }
}
```

A Platform that has not negotiated the extension receives the same cart and
checkout responses it receives today.

## Incentive model

### Incentive

{{ extension_schema_fields('incentives.json#/$defs/incentive', 'common/incentives') }}

`title` is required and states the offer and its condition in words. It is
what a Platform quotes, and it is enough on its own: a Platform that cannot
read the benefit type or one of the conditions can still present `title`,
`description`, `url`, and a disclosed `code`.

### Discount Benefit

`benefit` is a
[Discount Benefit](site:schemas/common/types/discount_benefit.json), a shared
type in `common` for the structured shape of a discount. It is not
specific to incentives: the same type is meant to describe a discount wherever
one is described, whether it is an offer that has not been applied or the
attribution of one that has.

{{ schema_fields('types/discount_benefit', 'common/incentives') }}

| `type` | Carries | Meaning |
| :-- | :-- | :-- |
| `amount_off` | `amount` | An amount off what the incentive applies to. |
| `percent_off` | `basis_points`, optionally `max_amount` | A percentage off, in basis points (`1250` = 12.5%), capped at `max_amount` when stated. |
| `fixed_price` | `price` | What each unit the incentive applies to costs while it applies. |
| `free_shipping` | nothing | Fulfillment costs nothing. `applies_to` on the incentive **MAY** narrow it to particular fulfillment options. |
| `free_item` | `quantity`, `item` (both optional) | `quantity` units are free (one when omitted). With `item`, the free unit is that gift. Without it, the free units are among the items the incentive applies to, as in "buy two, get one free" with `conditions.minimum_quantity`. |

`amount`, `basis_points`, and `price` are mutually exclusive, `max_amount`
requires `basis_points`, and every monetary value is greater than zero. On a
cart or checkout, the `currency` of every `Price` in a benefit **MUST** be the
session currency.

The vocabulary is open. A Business **MAY** use a reverse-domain name for a
custom benefit kind. A Platform that does not recognize `benefit.type`
**MUST NOT** derive a price, a saving, or a total from the benefit. It
**MAY** still present the incentive from its `title`, `description`, and
`url`, and it still submits a disclosed `code` like any other. An unknown
type is a reason to skip the price math, not to drop the offer.

### Incentive Conditions

{{ extension_schema_fields('incentives.json#/$defs/conditions', 'common/incentives') }}

Every stated condition must hold, and the Business decides whether it does.

The set of conditions is open. Another extension, or a Business in its own
namespace, **MAY** add a key such as a pickup or payment-tender qualifier. A
Platform **MUST** treat any condition key it does not recognize, other than
the reserved `ucp` member, as making qualification non-evaluable on its side,
and **MUST NOT** present that incentive as met or as applying. It can still present the offer
and its terms.

`minimum_order_amount` is a display threshold. The session's `subtotal` total
is the pre-discount sum of line items, and Businesses differ on what counts
toward a minimum: some count the value after item-level discounts, some
exclude gift cards or sale items. A Platform **MUST NOT** compute
qualification, or the distance to it, from `minimum_order_amount` and the
totals it holds. It reads the gap from [`approaching`](#approaching-incentive)
and learns that an incentive applied from `discounts.applied`.

`minimum_quantity` is summed across the line items the incentive applies to,
so two units of one variant and one of another meet a minimum of three. A
line item nested under another through `parent_id`, such as a component of a
bundle, is not counted; its parent line is.

### Incentive Period

{{ extension_schema_fields('incentives.json#/$defs/period', 'common/incentives') }}

An incentive outside its `active_period` is not offered. A Platform **MUST**
drop it regardless of cache. A Business **SHOULD** set `end_time` on anything
time-limited.

## Cart and Checkout

Cart and Checkout responses gain an `incentives` member.

{{ extension_schema_fields('incentives.json#/$defs/incentives', 'common/incentives') }}

`available` lists what the Business is offering on this session and has not
applied. Once the Business applies an incentive, it reports it in
`discounts.applied` and **SHOULD** stop listing it in `available`.

### Targeting

`applies_to` holds RFC 9535 JSONPath expressions relative to the response
root, with the same meaning as `applies_to` on
[policies](../../overview/index.md#policies): each target covers the node it
names and everything under it, and an incentive without `applies_to` is not
narrowed to particular nodes.

Paths are used instead of product or variant id lists because line items on a
session only carry what the session holds, and a path can name things an id
list cannot: a fulfillment option, a fulfillment group, a purchase option. An
exclusion is a filter, so a Platform never has to subtract one list from
another:

| Offer | `applies_to` |
| :-- | :-- |
| One line | `$.line_items[0]` |
| Everything except gift cards | `$.line_items[?@.item.id != 'gift_card']` |
| Free standard shipping only | `$.fulfillment.methods[*].groups[*].options[?@.id == 'standard']` |

Every path **MUST** resolve within the response that carries it. Selecting by
product, variant, or category id across a whole assortment belongs to bulk
feeds and to the catalog linkage, not to a session.

### Approaching Incentive

{{ extension_schema_fields('incentives.json#/$defs/approaching', 'common/incentives') }}

Each entry points at an entry of `available` and **MUST** state at least one
gap. The Business computes the gap under its own threshold rules, so it
already accounts for what counts toward the minimum. `remaining_amount` is an
`Amount` in the session currency. Tiered thresholds are several incentives,
and `approaching` **MAY** list more than one.

### Applied incentives

The Discount extension's `applied_discount` carries an optional
`incentive_id`. When a discount results from an incentive the Business listed,
the Business **SHOULD** set `incentive_id` to that incentive's `id`. An
automatic discount has no `code`, so this is how a Platform learns that an
offer it showed a moment ago has now been applied, and stops presenting it as
still to be earned.

### Stacking

Several incentives may apply to the same node. The Business decides which
apply together when it applies them. `combinable: false` tells the Platform
not to present the incentive as cumulative with any other.

## Listing incentives

The List capability answers one question: what is this Business offering
right now? It does not need a product search or a session, so a Platform can
use it to answer "any deals at this store?" directly.

| Operation | Description |
| :--- | :--- |
| **List Incentives** | List the incentives the Business is offering in the request's context. |

Transport bindings: [REST](rest.md), [MCP](mcp.md).

### Request

{{ extension_schema_fields('incentives_list.json#/$defs/list_request', 'common/incentives') }}

`context` works as it does everywhere else: the Business resolves market,
currency, and any eligibility claims from it, and returns the incentives it
offers in that context.

### Response

{{ extension_schema_fields('incentives_list.json#/$defs/list_response', 'common/incentives') }}

The response has no line items or products to point at, so entries **MUST
NOT** carry `applies_to`. An incentive that only covers part of the
assortment says so in `title` and `description`. A Platform **MUST NOT**
assume that a listed incentive covers a particular product; whether it applies
to what the buyer puts in a cart is answered by the cart.

A Business **MAY** omit any incentive from the list, and **SHOULD** omit the
ones that only make sense with a session in hand.

## Gated incentives

A Business **MAY** list an incentive whose `conditions.eligibility` names a
claim the buyer has not asserted, so the Platform can offer to link the
buyer's account or supply the claim. Listing the incentive states that the
offer exists and what it gives. It does not change any price for a buyer who
does not hold the claim; member pricing follows
[Loyalty](../extensions/loyalty.md).

## Codes

Disclosing a code is the Business's choice. A disclosed `code` is submitted
through `discounts.codes` exactly as any other code, and the Discount
extension's
[rejection codes](../../shopping/extensions/discount.md#rejected-codes) apply
unchanged. An incentive with `application: code` and no `code` tells the
Platform that a code exists and the buyer must already hold it. `code` is only
valid with `application: code`; the schema rejects it otherwise.

## Responsibilities

A Business **MUST** list only incentives it will honor at application under
the stated conditions, in the market the response's `context` resolves to. It
**MUST** compute every `approaching` gap itself. It **MAY** omit any
incentive, and **MAY** list different incentives to different Platforms.

A Platform:

* **MUST NOT** present an incentive as applied; `discounts.applied` is the
  record of what took effect.
* **MUST NOT** present an incentive as met when it carries a condition key the
  Platform does not recognize.
* **MUST NOT** derive an amount from a benefit whose `type` it does not
  recognize, and **MUST NOT** present a total derived from incentives as
  final.
* **MAY** show a figure the Business supplied, such as a `fixed_price` or a
  `remaining_amount`, or one it computed itself from a benefit it recognizes,
  labelled as an estimate that depends on the named incentive.
* **MUST** submit a disclosed code through `discounts.codes`.

## Relationship to policies

The [`policies[]`](../../overview/index.md#policies) primitive carries terms:
a type, a description, a URL, and what they apply to. An incentive carries a
typed benefit and conditions. A Business **MAY** point an incentive's `url` at
a policy page, and **MAY** publish a policy that describes a promotion in
prose; a Platform reads the benefit and conditions from the incentive.

## Examples

### Cart approaching a threshold

<!-- ucp:example schema=common/incentives def=dev.ucp.shopping.cart op=update target=$.incentives -->
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
    { "incentive_id": "inc_fs50", "remaining_amount": 4000 }
  ]
}
```

The Platform can tell the buyer that $40 more qualifies the order for free
shipping. It takes the $40 from `remaining_amount`, not from its own
arithmetic on the threshold.

### Cart after the incentive applied

<!-- ucp:example schema=shopping/cart op=read -->
```json
{
  "ucp": { "...": "..." },
  "id": "cart_abc123",
  "currency": "USD",
  "line_items": ["..."],
  "discounts": {
    "applied": [
      {
        "title": "Free standard shipping over $50",
        "amount": 599,
        "automatic": true,
        "incentive_id": "inc_fs50"
      }
    ]
  },
  "incentives": {
    "available": []
  },
  "totals": ["..."]
}
```

The discount has no code. `incentive_id` is what tells the Platform that the
offer it was nudging toward is the one that applied.

### Quantity deals and a disclosed code

<!-- ucp:example schema=common/incentives def=dev.ucp.shopping.cart op=update target=$.incentives -->
```json
{
  "available": [
    {
      "id": "inc_b2g1",
      "title": "Buy 2 candles, get 1 free",
      "application": "automatic",
      "benefit": { "type": "free_item", "quantity": 1 },
      "conditions": { "minimum_quantity": 2 },
      "applies_to": ["$.line_items[0]"]
    },
    {
      "id": "inc_tote",
      "title": "Free tote bag with orders over $75",
      "application": "automatic",
      "benefit": {
        "type": "free_item",
        "item": {
          "id": "var_tote",
          "title": "Canvas tote bag",
          "value": { "amount": 1500, "currency": "USD" }
        }
      },
      "conditions": {
        "minimum_order_amount": { "amount": 7500, "currency": "USD" }
      }
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
  ],
  "approaching": [
    { "incentive_id": "inc_b2g1", "remaining_quantity": 1 },
    { "incentive_id": "inc_tote", "remaining_amount": 5100 }
  ]
}
```

### Checkout with a capped promotion and an exclusion

<!-- ucp:example schema=common/incentives def=dev.ucp.shopping.checkout target=$.incentives -->
```json
{
  "available": [
    {
      "id": "inc_holiday",
      "title": "Holiday sale, 20% off everything except gift cards, up to $100, with code HOLIDAY",
      "application": "code",
      "code": "HOLIDAY",
      "benefit": {
        "type": "percent_off",
        "basis_points": 2000,
        "max_amount": { "amount": 10000, "currency": "USD" }
      },
      "applies_to": ["$.line_items[?@.item.id != 'gift_card']"],
      "active_period": {
        "start_time": "2026-11-20T00:00:00Z",
        "end_time": "2026-12-01T23:59:59Z"
      }
    }
  ]
}
```

### A benefit or condition the Platform does not know

<!-- ucp:example schema=common/incentives def=dev.ucp.shopping.checkout target=$.incentives -->
```json
{
  "available": [
    {
      "id": "inc_wrap",
      "title": "Free gift wrapping when you pay with the Example Store Card",
      "application": "automatic",
      "benefit": { "type": "com.example.benefit.gift_wrap" },
      "conditions": { "com.example.payment_tender": "store_card" },
      "url": "https://example.com/offers/gift-wrap"
    }
  ]
}
```

A Platform that knows neither the benefit type nor the condition key can
still tell the buyer the offer exists, in the Business's own words, and link
to its terms. It does no price math and does not say the buyer qualifies.

### Listing a Business's incentives

See the [REST](rest.md#example) and [MCP](mcp.md#example) bindings.
