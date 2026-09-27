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

# Return Policy Extension

## Overview

The Return Policy Extension defines the `dev.ucp.shopping.policy.return` policy
type on the core [`policies[]`](../../overview/index.md#policies) primitive.
It adds machine-readable return terms to policies that carry this type, from
catalog through cart, checkout, and order, so platforms and agents can answer
questions like "How long do I have to return this?", "Do I get my money back or
store credit?", "Where and at what cost do I send it back?", and "Can I return
this at all?" without leaving to read a policy page.

Policy pages often lack product-level granularity: one page covers the standard
terms, final-sale items, category exceptions, and marketplace sellers in prose,
leaving buyers and agents unable to tell which terms govern a given item.
Because each return policy targets items through `applies_to`, the terms a
platform reads for an item are the ones that apply to it.

**Key features:**

- A return window as a policy statement (`window`), with an explicit anchor
- What the buyer receives on an accepted return (`supported_resolutions`)
- Permitted return channels and their logistics cost (`methods`)
- A restocking fee that deducts from the refund independent of channel
  (`restocking_fee`)
- A hard `final_sale` flag for non-returnable items

**Dependencies:**

- The core `policies[]` primitive (see
  [Policies](../../overview/index.md#policies)).
- One or more of the parent capabilities this type extends: Catalog Search,
  Catalog Lookup, Cart, Checkout, or Order.

This extension only structures the type-specific body. The `policies[]`
container, `applies_to` targeting, same-type precedence, and buyer-facing
disclosure through `messages[]` are defined once by the primitive and are
**unchanged** here.

## Discovery

Businesses advertise return policy support in their profile. The type extends any
surface that carries `policies[]`:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.policy.return": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup",
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/return-policy",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/policy_return.json"
        }
      ]
    }
  }
}
```

A business MAY advertise support on a subset of these surfaces. A platform that
has negotiated this type validates the return body and MAY reason over it (for
example, computing a return deadline). A platform that has not negotiated it
still renders the policy from the base `type` and `description`, because the
return body is purely additive.

## Schema

When this type is active, a `policies[]` entry whose `type` is
`dev.ucp.shopping.policy.return` MAY carry the following fields in addition to the
base `type`, `description`, `applies_to`, and `url`. All fields are optional; a
return policy with no structured fields is still presentable from its
`description`.

### Return Policy

{{ extension_schema_fields('policy_return.json#/$defs/return_body', 'shopping/extensions/return-policy') }}

### Return Method

{{ extension_schema_fields('policy_return.json#/$defs/return_method', 'shopping/extensions/return-policy') }}

### Return Method Fee

{{ extension_schema_fields('policy_return.json#/$defs/fee', 'shopping/extensions/return-policy') }}

### Fixed Fee

{{ extension_schema_fields('policy_return.json#/$defs/fixed_fee', 'shopping/extensions/return-policy') }}

## Return terms

### Window and anchor

`window.days` is the length of the return window as a **policy statement**, not a
live countdown. It is a guaranteed minimum: a return started within the window
is accepted with any listed resolution through any listed method. A platform
computes that guaranteed deadline by adding `days` to the event named by
`window.anchor`.

When the window varies with something known only at return time, such as the
item's condition or the resolution the buyer picks, `window` states the period
that holds in every case, and `description` states the longer ones. A policy
with 30 days for a refund and 60 days for store credit sets `days` to `30`,
lists both resolutions, and describes the store-credit extension (see
[Different windows per resolution](#different-windows-per-resolution)).

Businesses differ on whether the clock starts at delivery, purchase, shipment, or
fulfillment, so when `window` is present a business MUST provide both `days` and
`anchor`. There is no default anchor, and a platform MUST NOT assume one. Omit
`window` entirely for an unlimited window, or when the window is not stated
structurally, and convey it in `description`.

The resolved, absolute cutoff is an Order-time fact: once the anchor event has
occurred, a business republishes the policy on the Order as the source of truth
(see [Order-time resolution](#order-time-resolution)). Pre-purchase, the window
stays a duration plus an anchor.

### Non-returnable items

To signal that the covered items cannot be returned, a business MUST set
`final_sale` to `true`. Because return terms do not apply, a final-sale policy
MUST NOT carry `window`, `supported_resolutions`, `methods`, or
`restocking_fee`; the schema rejects the combination, so no precedence between
fields of one policy is ever needed. A business MUST NOT use an empty
`supported_resolutions` or `methods` array to signal non-returnability, and the
schema requires at least one entry in each; omit a field that is not stated
structurally. `final_sale` is the single, unambiguous signal a platform acts on.

When a business requires the buyer to be shown that an item is final sale, it
emits a `messages[]` warning with `presentation: "disclosure"` and `code` equal
to `dev.ucp.shopping.policy.return`, targeting the item. The disclosure pairs
with the governing return policy at that node, as defined in
[Presenting policies](../../overview/index.md#presenting-policies).

### Two kinds of cost

Returns carry two independent costs, modeled separately:

- **Logistics cost** is the price of using a channel (return shipping or
  handling). It lives on each `methods[].fee` because it varies by channel: an
  in-store drop-off may be `free` while a mailed return is a `fixed_fee`.
- **Restocking fee** is a deduction from the refund charged regardless of how the
  item comes back. It lives once at the policy level as `restocking_fee`.

Keeping them separate lets a business express, for example, "free returns by mail
with a 15% restocking fee" - which a single per-method fee cannot represent. A
percentage restocking fee uses `restocking_fee.percentage_bps`; a flat or
precomputed amount uses `restocking_fee.amount`. A `restocking_fee` MUST carry
at least one of them. When both are present, each is a cap and the deduction
never exceeds either: `percentage_bps` of `1500` with an `amount` of `5000`
means 15% of the item price, up to $50.00 in a USD checkout.

Both costs are maximums: `restocking_fee` and each method's `fee` state the most
the buyer is charged. A fee that applies only in some cases, such as a
restocking fee on opened items, states its full value, and its `display_text`
names the condition. An omitted `restocking_fee` means no restocking fee is
charged, so a business that may charge one MUST provide it.

A method's logistics cost, by contrast, is stated only by its `fee`. A method
with no `fee`, or with a `fee.type` the platform does not recognize, states no
cost, and `customer_responsibility` means the buyer arranges and pays for the
return shipping, with no maximum stated. A platform MUST NOT present any of
these as free.

When a return method's `fee.type` is `fixed_fee`, `amount` MUST be present, so the
charge is never left uninterpretable.

Amounts (`methods[].fee.amount` and `restocking_fee.amount`) carry no currency
of their own. They are in the `currency` of the enclosing cart, checkout, or
order, or, on catalog surfaces, in the currency of the covered product's price.

## Targeting and precedence

Targeting and precedence are provided by the `policies[]` primitive and are not
redefined here. In short: a policy with no `applies_to` is the response-wide
default; a policy that targets specific items overrides it where they overlap,
with the narrowest same-type target winning. See
[Targeting](../../overview/index.md#targeting) and
[Precedence](../../overview/index.md#precedence).

For return policies this means a business states a single default return policy
once, then adds targeted overrides only for the exceptions (a final-sale item, a
category with a different window), rather than repeating a policy on every line.
An override replaces the default for the items it governs and inherits none of
its terms, so a business MUST restate in the override every term that still
applies. This includes `restocking_fee`: an override that omits it states that
no restocking fee is charged.

## Responsibilities

Return policies are business-stated facts. They are response-only data
(`ucp_request: omit` on cart, checkout, and order) that a platform never submits;
there is no buyer selection and no request-side machinery. They carry no
buyer-asserted claims and no PII, so they cross no new trust boundary beyond the
base response.

The return-term fields (`window`, `supported_resolutions`, `methods`, and
`restocking_fee`) are guarantees that hold for every eligible return in the
policy's scope, not an exhaustive statement of its terms. Within `window`, any
listed resolution is available through any listed method (see
[Window and anchor](#window-and-anchor)), and each fee is a maximum (see
[Two kinds of cost](#two-kinds-of-cost)). Eligibility requirements, such as tags
attached or original packaging, are stated in `description`. A condition under
which an item stays returnable on different terms, such as opened or unopened,
is not an eligibility requirement, so the fields state the terms that hold in
every case.

A business SHOULD populate the fields it can state as guarantees and MUST NOT
populate a field with a value that does not hold for every eligible return. It
omits `window`, `supported_resolutions`, or `methods` when it cannot state them
as guarantees, and conveys the term in `description` or links to it through
`url`; an omitted `restocking_fee`, by contrast, means none is charged. Where a
term depends on something known when the response is built, such as the seller,
the purchase date, an authenticated buyer's membership, or a selected payment
instrument, a business SHOULD resolve it, scoping policies with `applies_to`
where it differs per item.

A policy's `description` and its structured fields are two representations of
the same policy. The `description` MAY state better terms than a field (a longer
window for one resolution) or the conditions under which a fee applies, but a
business MUST NOT let it state terms worse for the buyer than a field. It is the
human-readable summary a platform renders, and the fallback for a platform that
does not model the type. A platform SHOULD surface `url` alongside the
structured terms so the buyer can review the full policy.

A platform that models this type MAY compute a guaranteed return deadline and a
worst-case net refund from these fields, where every cost involved is stated
(see [Two kinds of cost](#two-kinds-of-cost)). It MUST NOT treat an elapsed
`window` as making an item non-returnable, since the `description` may allow
later returns; only `final_sale` signals that.

## Order-time resolution

Pre-purchase, the return window is a duration plus an anchor. The concrete
deadline a buyer actually has can only be computed once the anchor event (for
example, delivery) has occurred. That resolution is an Order-time concern: on the
Order, a business republishes the same return policy carrying the resolved cutoff,
so the platform reads it rather than tracking fulfillment events and recomputing.
Modeling the resolved deadline field is deferred to that Order-side work.

## Examples

### Checkout with a default policy and a final-sale override

A response-wide return policy states the standard terms once. An item-scoped
policy marks the engraved line (line 2) as final sale; because it names that
line with a singular query (`$.line_items[2]`), it governs it under same-type
precedence, outranking any Set match at the same depth, while every other line
keeps the default. A paired disclosure compels the final-sale notice to be
shown. The default policy's 15% restocking fee is a maximum; its `display_text`
names the condition (opened items) under which it applies.

<!-- ucp:example schema=shopping/policy_return def=dev.ucp.shopping.checkout target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.return",
    "description": {
      "plain": "30-day returns from delivery. Refund to original payment or exchange. Free in-store; $5 return shipping by mail. 15% restocking fee on opened items."
    },
    "window": { "days": 30, "anchor": "delivered" },
    "supported_resolutions": ["original_payment_method", "exchange"],
    "methods": [
      { "type": "in_store", "fee": { "type": "free", "display_text": "Free in-store return" } },
      { "type": "by_mail", "fee": { "type": "fixed_fee", "amount": 500, "display_text": "Return shipping" } }
    ],
    "restocking_fee": { "percentage_bps": 1500, "display_text": "15% restocking fee on opened items" },
    "url": "https://example.com/returns"
  },
  {
    "type": "dev.ucp.shopping.policy.return",
    "description": { "plain": "This engraved item is final sale and cannot be returned." },
    "applies_to": ["$.line_items[2]"],
    "final_sale": true,
    "url": "https://example.com/returns#final-sale"
  }
]
```

The paired disclosure that compels display of the final-sale term:

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "dev.ucp.shopping.policy.return",
    "path": "$.line_items[2]",
    "presentation": "disclosure",
    "content": "This engraved item is final sale and cannot be returned."
  }
]
```

### Catalog with a store-credit-only return policy

On a catalog surface, a return policy targets one product whose returns are
store credit only, a material purchase-decision factor. Store credit is the only
resolution the policy guarantees, and its `description` rules out any other:

<!-- ucp:example schema=shopping/policy_return def=search_response op=search target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.return",
    "description": { "plain": "Returns accepted within 30 days for store credit only." },
    "applies_to": ["$.products[0]"],
    "window": { "days": 30, "anchor": "purchased" },
    "supported_resolutions": ["store_credit"]
  }
]
```

### Different windows per resolution

A business offers refunds for 30 days after delivery and store credit for 60.
Precedence lets only one return policy govern an item, so a single policy
carries both: `window` states the 30 days in which either resolution is
guaranteed, and the `description` states the longer store-credit window:

<!-- ucp:example schema=shopping/policy_return def=dev.ucp.shopping.checkout target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.return",
    "description": {
      "plain": "Return within 30 days of delivery for a refund to your original payment method, or within 60 days for store credit."
    },
    "window": { "days": 30, "anchor": "delivered" },
    "supported_resolutions": ["original_payment_method", "store_credit"],
    "url": "https://example.com/returns"
  }
]
```

A platform can tell the buyer that either resolution is guaranteed until 30
days after delivery. After that, it relies on the `description`, which offers
store credit until day 60, rather than reporting the item as non-returnable.
