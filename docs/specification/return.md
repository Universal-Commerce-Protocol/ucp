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
type on the core [`policies[]`](overview.md#policies) primitive. It adds
pre-purchase, machine-readable return terms to policies that carry this type, so
platforms and agents can answer questions like "How long do I have to return
this?", "Do I get my money back or store credit?", "Where and at what cost do I
send it back?", and "Can I return this at all?" without leaving to read a policy
page.

**Key features:**

- A return window as a policy statement (`window`), with an explicit anchor
- What the buyer receives on an accepted return (`supported_resolutions`)
- Permitted return channels and their logistics cost (`methods`)
- A restocking fee that deducts from the refund independent of channel
  (`restocking_fee`)
- A hard `final_sale` flag for non-returnable items

**Dependencies:**

- The core `policies[]` primitive (see [Policies](overview.md#policies)).
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
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/return",
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

{{ extension_schema_fields('policy_return.json#/$defs/return_body', 'return') }}

### Return Method

{{ extension_schema_fields('policy_return.json#/$defs/return_method', 'return') }}

## Return terms

### Window and anchor

`window.days` is the length of the return window as a **policy statement**, not a
live countdown. A platform computes a concrete deadline by adding `days` to the
event named by `window.anchor`.

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
`final_sale` to `true` and SHOULD omit the other return-body fields, since return
terms do not apply. A business MUST NOT use an empty `supported_resolutions` array
to signal non-returnability; `final_sale` is the single, unambiguous signal a
platform acts on.

When a business requires the buyer to be shown that an item is final sale, it
emits a `messages[]` warning with `presentation: "disclosure"` and `code` equal
to `dev.ucp.shopping.policy.return`, targeting the item. The disclosure pairs
with the governing return policy at that node, as defined in
[Presenting policies](overview.md#presenting-policies).

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
precomputed amount uses `restocking_fee.amount`.

When a return method's `fee.type` is `fixed_fee`, `amount` MUST be present, so the
charge is never left uninterpretable.

## Targeting and precedence

Targeting and precedence are provided by the `policies[]` primitive and are not
redefined here. In short: a policy with no `applies_to` is the response-wide
default; a policy that targets specific items overrides it where they overlap,
with the narrowest same-type target winning. See
[Targeting](overview.md#targeting) and [Precedence](overview.md#precedence).

For return policies this means a business states a single default return policy
once, then adds targeted overrides only for the exceptions (a final-sale item, a
category with a different window), rather than repeating a policy on every line.

## Responsibilities

Return policies are business-stated facts. They are response-only data
(`ucp_request: omit` on cart, checkout, and order) that a platform never submits;
there is no buyer selection and no request-side machinery. They carry no
buyer-asserted claims and no PII, so they cross no new trust boundary beyond the
base response.

A business SHOULD populate the structured fields it can author accurately and MAY
state anything it cannot yet structure (condition requirements, category
nuances) in the policy `description` or link to it through `url`. A platform
SHOULD surface `url` alongside the structured terms so the buyer can review the
full policy.

A policy's `description` and its structured fields are two representations of the
same policy. The `description` MAY add terms not modeled here, but a business MUST
NOT let it contradict a structured field. A platform that models this type MUST
treat the structured fields as authoritative (for computing the return deadline,
net refund, and returnability); the `description` is the human-readable summary it
renders, and the fallback for a platform that does not model the type.

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
policy marks one engraved line as final sale; because it targets that line
directly, it governs it under same-type precedence, while every other line keeps
the default. A paired disclosure compels the final-sale notice to be shown.

<!-- ucp:example schema=shopping/checkout target=$.policies -->
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
    "applies_to": ["$.line_items[?@.id=='engraved_watch']"],
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
    "path": "$.line_items[?@.id=='engraved_watch']",
    "presentation": "disclosure",
    "content": "This engraved item is final sale and cannot be returned."
  }
]
```

### Catalog with a store-credit-only return policy

On a catalog surface, a return policy targets one product and signals that
returns are store credit only, a material purchase-decision factor:

<!-- ucp:example schema=shopping/catalog_search op=search direction=response target=$.policies -->
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
