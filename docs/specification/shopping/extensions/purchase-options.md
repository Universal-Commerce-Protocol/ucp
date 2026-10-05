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

# Purchase Options Extension

## Overview

A product can be sold in several ways: once, as a subscription, on pre-order. The Purchase Options extension lets a Business advertise
those ways on a variant, lets a Platform select one by opaque identifier, and
preserves the selected option's identity on the resulting Order.

Today a variant has one price and one way to buy it. A Business that also
sells the same coffee on a monthly plan has no way to say so in its catalog, a
Platform has no way to choose, and a checkout has no way to know which was
chosen. The result is a late failure — an item that cannot be added without a
selection the Platform never learned about — and an incomplete comparison, where
the Business's best offer is invisible while the buyer is deciding.

A **purchase option** is an addressable, renderable choice: an `id`, a `title`,
a `price` for the current purchase and, where that price is a saving, the
`list_price` it saves against. The Business enumerates the options it sells;
the Platform selects one. This is `options[]` plus a selected id, the same shape as
a [fulfillment option](fulfillment.md) and a
[payment term](../../payment/extensions/terms.md), applied on the axis where the
choice to subscribe actually lives: the item.

This extension adds:

- `purchase_options[]` on a catalog variant and on a cart or checkout line —
    the ways the variant can be bought. Response-only.
- `selected_purchase_option_id` on a cart or checkout line — the selected
    option. Present in a response whenever `purchase_options` is; a Platform
    writes it to change the selection.
- `purchase_option` on an Order line — the frozen identity of the option the
    line was bought through.

**Dependencies:**

- One or more of the parent capabilities this extension extends: Catalog
  Search, Catalog Lookup, Cart, Checkout, or Order.
- The [Subscription Policy](subscription-policy.md) type, for any option that
  recurs. Purchase Options carries the choice; the subscription policy states
  what recurs, by targeting the option before it is chosen and the line after.

An option modifies how the line it is selected on is bought — its price now.
It never adds, removes, or changes other lines, and it carries no terms of its
own: what recurs, when payment is due, and how the item is fulfilled are stated
by the capabilities that own those concerns.

## Discovery

Businesses advertise purchase options in their profile:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.purchase_options": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup",
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/purchase-options",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/purchase_options.json"
        }
      ]
    }
  }
}
```

Advertising this extension means the Business returns `purchase_options` for
variants that offer them, accepts and echoes `selected_purchase_option_id` on
cart and checkout lines, and preserves the selected option on the resulting
Order line.

## Schema

### Purchase Option

{{ schema_fields('types/purchase_option', 'shopping/extensions/purchase-options') }}

### Variant Purchase Options

{{ extension_schema_fields('purchase_options.json#/$defs/variant_purchase_options', 'shopping/extensions/purchase-options') }}

### Line Item with Purchase Options

{{ extension_schema_fields('purchase_options.json#/$defs/line_item', 'shopping/extensions/purchase-options') }}

### Order Purchase Option

{{ extension_schema_fields('purchase_options.json#/$defs/order_purchase_option', 'shopping/extensions/purchase-options') }}

## Offering options

### Presence and the default

Purchase options are optional. A Business offers them when a variant can be
bought in more than one way, or in exactly one way that is not an ordinary
one-time purchase. Where a variant is bought the ordinary way at its `price`,
`purchase_options` is omitted entirely, and nothing about the variant changes.

Where `purchase_options` is present it **MUST** contain at least one option,
and exactly one of them is in effect. On a cart or checkout line,
`selected_purchase_option_id` **MUST** name it. In a catalog, the first entry is
the **default**: the option the Business selects when a Platform adds the
variant without choosing one, and the option whose `price` the variant's own
`price` states. A Business orders `purchase_options` by its preference, default
first.

A one-time purchase is an option like any other. A variant that can be bought
once or on a plan lists both; a variant whose list contains no one-time option
is sold only through the options listed. There is no implicit one-time purchase
alongside a list of options, and no separate signal is needed to say so — a
Platform reads presence exactly as it reads `payment.terms`.

A Business offering exactly one option is disclosing rather than asking, and a
Platform **SHOULD** present it without implying a choice.

### Price

`purchase_options[].price` answers one question: what does one unit cost in
this purchase under this option? It reflects any discount or fixed pricing the
option defines and is stated before quantity, taxes, discounts, fees, and
fulfillment. Every option's `price` is directly comparable with every other's,
and with the variant's `price`, because all of them answer the same question.

The same rule holds across arrangements:

- A $10 item whose payment is collected in 14 days has a `price` of $10. When
  the $10 is collected is a [payment term](../../payment/extensions/terms.md).
- A subscription whose first order costs $8.50 has a `price` of $8.50. The
  recurring orders are stated by a subscription policy targeting the option.
- A free trial has the first order's full `price`. Selecting it is what makes
  the Business defer that order's payment to the end of the trial under a
  payment term, and state the recurring orders in a subscription policy.
- `0` means the current purchase is genuinely free. It never means a non-zero
  amount is merely collected later.

On a cart or checkout line, the selected option's price is the line's
`item.price`, and the line's `totals` and the checkout `totals` follow from it.
Unselected options are indicative, priced by the Business for this cart or
checkout as best it can; only the selected option is reflected in the totals.
The option is the pricing mechanism: a "subscribe & save" option's saving is
its lower `price`. Where that price is a saving against a reference, the
option carries `list_price` — for a subscribe-and-save option, the one-time
price — mirroring `variant.list_price` for strikethrough display and a
derivable saving. The
catalog states a price and a reference price, never a breakdown; breakdowns
begin at the line. Whether a Business then itemizes the saving as a discount
entry in a line's `totals` is its choice, applied consistently to today's
order and to the recurring orders a policy states.

### Recurring orders

An option carries no recurrence fields. What choosing it would entail is stated
by a [subscription policy](subscription-policy.md) that **targets the option**
— `$.product.variants[0].purchase_options[1]` in a catalog,
`$.line_items[0].purchase_options[1]` for an unselected option on a line. Such
a policy is prospective, as that extension defines: it governs the option node
only, pairs with no disclosure, and is not carried onto the Order. An agent
reading the option list resolves the policy for each option the same way it
resolves a return policy for each product, and can tell "$8.50 every month"
from "$102 for the year" without parsing a title.

When a selected option recurs, the Business **MUST** emit a
`dev.ucp.shopping.policy.subscription` policy targeting the line, with its
paired disclosure. Because a target covers everything nested under it, that
policy also governs the selected option's node, so the chosen terms appear
once; policies remain on the unselected options as previews. A Platform reads
`policies[]` for what the buyer is agreeing to.

A policy's schedule `totals` follow the basis of the node it targets: on a
catalog option, one unit; on a line, or on an option under a line, the line's
quantity. The option's own `price` is always per unit.

An option on a line composed from components may itself entail nothing
recurring while the components do; their recurrence is stated by policies
targeting the component lines (see [Nested line items](#nested-line-items)).

## Selecting an option

A Platform selects an option on a line by sending its identifier:

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.checkout op=create direction=request -->
```json
{
  "line_items": [
    {
      "item": { "id": "gid://example/Variant/coffee-340g" },
      "quantity": 2,
      "selected_purchase_option_id": "po_monthly"
    }
  ]
}
```

Selecting an option is a cart or checkout mutation, and the Business response
is **authoritative for all derived state**: `purchase_options` as priced for
this cart or checkout, the line's `item.price` and `totals`, the checkout
`totals`, `policies[]`, `messages[]`, the payment terms offered — a selection
can introduce a term, as a trial introduces a deferred one, or withdraw one —
and the payment handlers and instruments offered. A Platform **MUST NOT** assume the prices it
read in the catalog survive selection, and **MUST** re-render from the
response.

`selected_purchase_option_id` **MUST** match a `purchase_options[].id` from the
catalog or from the latest cart or checkout response for that line. A Platform
**SHOULD** always send an explicit selection. Where it sends none, the Business
selects the default and echoes it; a Platform that negotiated this extension is
expected to read the echoed selection and the policies and disclosures that
come with it. A Platform **MUST** omit the field on complete, because the
option is already agreed before a checkout can reach `ready_for_complete`.

The Business **MUST** make `purchase_options[].id` unique within a line, so
that a selection resolves to exactly one option.

### Selections that no longer resolve

An option can be withdrawn, repriced, or made ineligible between responses. A
Business receiving a selection that does not resolve against the options it
currently offers for that line **MUST NOT** silently substitute another. It
selects the default, returns the authoritative state, and **MUST** report the
change as a `purchase_option_changed` warning in `messages[]` with `path`
naming the line. A Business **MUST** report the same warning when it changes
the selected option in place — its price, or the terms a policy states for
it — without
naming a different one. A Platform can therefore detect a changed selection
from the code alone, rather than by comparing responses.

Changing the selected option can invalidate a selection accepted elsewhere in
the checkout: a deposit term a Business offers on one-time purchases but not
on subscriptions. The Business resolves the conflict and reports it through
that extension's own warning, `payment_term_changed`.

## Composition

### Payment terms

Payment terms answer when the current purchase is paid; a purchase option
answers what the current purchase is. They do not overlap. A try-before-you-buy
option is a one-time purchase at full `price` whose payment is deferred, so it
is expressed as an option plus a deferred payment term. A subscription's first
order is simply in the checkout `totals`, paid at completion like anything
else; the recurring orders are not owed yet and are not payment schedules. A
free trial composes the two: the option is the first order at full `price`,
its selection makes the Business return a deferred payment term for that order
and a subscription policy for the recurring orders, and nothing is paid at
completion. In a catalog, when an option's purchase is paid is stated in its
`description`; a structured preview of payment timing there would be an
additive composition of payment terms onto catalog, title and description like
fulfillment's previews, not a field on the option.

### Subscription policy

The option carries the choice; the policy carries the obligation. A Business
that sells a variant only as a subscription, with no alternative, needs no
purchase option at all — the subscription policy on the line is sufficient.
This extension is for the case where there is something to choose.

### Nested line items

A purchase option is selected on the line it belongs to. Where a Business
composes a line from components — nested lines that reference it through
`parent_id` — the option is selected on the **parent**, and a selection sent
on a component line is not honored. The components' prices are a breakdown of
the parent's as that composition defines; the components' recurrence, where
it differs from the parent's, is stated by subscription policies targeting the
component lines. Purchase Options does not define composition and does not
infer it: an option never causes lines to be added or removed.

### Platforms that have not negotiated this extension

A Platform that has not negotiated this extension must not receive a variant
that looks ordinary but cannot be bought as one. For such a Platform a
Business:

- returns a variant that has a one-time option with that option's price as the
  variant's `price` and no extension fields, so it can be bought once as it
  always could;
- omits from search a variant that has no one-time option, and omits a product
  none of whose variants can be bought without this extension;
- returns an actionable `item_unavailable` message for such a variant on exact
  lookup, rather than an unusable result; and
- rejects an attempt to add such a variant to a cart or checkout with an
  `item_unavailable` error, never selling it the ordinary way.

## Order

When a checkout line carried `purchase_options`, the Business **MUST** include
`purchase_option` on the corresponding Order line, with the `id` and `title`
of the option that was selected — including an explicitly listed one-time
option. It is absent when the line's variant carried no options.

The value is a historical snapshot. A Business **MUST NOT** change it when the
catalog option is later renamed, changed, or withdrawn, and a Platform **MUST
NOT** assume `purchase_option.id` still resolves through the catalog. The
snapshot records which offer produced the line; the Order line's `item.price`
and `totals` record what the current purchase cost; and the recurring orders
the option entailed are recorded by the Order's subscription policy. Available
options are checkout state and are not projected.

## Out of scope

- **What recurs, and its disclosure.** Stated by the subscription policy,
  which targets an option to preview and the line to bind. Nothing recurring
  is stated on the option.
- **When the current purchase is paid.** Payment terms.
- **Composition.** Which lines make up a bundle, how their totals relate, and
  how they are updated are defined by the capability that defines nested
  lines. An option is selected on one line and changes only that line.
- **Future deliveries.** A recurring option's delivery schedule is
  described in `description` until a capability for scheduled fulfillment
  exists. Billing cadence does not imply delivery cadence.
- **Platform-assembled options.** A Platform selects one id. It never composes
  a cadence, price, and commitment into an option the Business did not
  advertise.

## Responsibilities

Businesses **MUST**:

- List every way a variant can be bought, including a one-time purchase where
  one is offered, default first, with the variant's `price` stating the
  default option's price.
- Name one offered option in `selected_purchase_option_id` on every cart or
  checkout line that carries `purchase_options`, selecting the default where
  the Platform made no choice.
- Return the recomputed cart or checkout after a selection, including every
  change to prices, totals, policies, messages, payment terms, and payment
  handlers.
- Emit a governing subscription policy and its disclosure on every line whose
  selected option recurs.
- Report a `purchase_option_changed` warning whenever a response changes the
  option in effect, by naming a different option or by rewriting the selected
  one in place.
- Honor a selection only on the line it is sent for; never add, remove, or
  change other lines as a consequence of a selection.
- Shape responses to Platforms that have not negotiated this extension so that
  no variant appears ordinarily purchasable when it is not.
- Carry the selected option onto the Order line as `purchase_option`.

Platforms **MUST**:

- Treat `purchase_options[].id` as opaque.
- Present `title`, `price`, and `description` for each option so the buyer can
  compare them before selecting, unless only one option is offered.
- Re-render from the Business response after a selection.
- Read `policies[]`, not the option, for the terms the buyer is agreeing to.
- Omit `selected_purchase_option_id` on complete.

Platforms **SHOULD**:

- Send an explicit `selected_purchase_option_id` rather than relying on the
  default.

## Examples

### Catalog: one-time or subscribe

A coffee that can be bought once for $10 or on a monthly plan for $8.50. The
one-time purchase is the default and first; the variant's `price` states it.
The monthly option's `list_price` is the one-time price it saves against.

<!-- ucp:example schema=shopping/purchase_options def=get_product_response op=get_product target=$.product.variants[0] -->
```json
{
  "id": "gid://example/Variant/coffee-340g",
  "title": "340g",
  "description": { "plain": "Medium roast, whole bean." },
  "price": { "amount": 1000, "currency": "USD" },
  "purchase_options": [
    {
      "id": "po_once",
      "title": "One-time",
      "price": { "amount": 1000, "currency": "USD" }
    },
    {
      "id": "po_monthly",
      "title": "Subscribe & save 15%",
      "description": { "plain": "Cancel anytime." },
      "price": { "amount": 850, "currency": "USD" },
      "list_price": { "amount": 1000, "currency": "USD" }
    }
  ]
}
```

What the monthly option entails is a subscription policy on the same response,
targeting the option. It is prospective: nothing recurs until the option is
chosen.

<!-- ucp:example schema=shopping/policy_subscription def=get_product_response op=get_product target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.subscription",
    "description": { "plain": "Monthly coffee subscription. Cancel anytime." },
    "applies_to": ["$.product.variants[0].purchase_options[1]"],
    "schedules": [
      {
        "description": { "plain": "$8.50 plus applicable tax and shipping every month until you cancel." },
        "totals": [
          { "type": "subtotal", "amount": 850 },
          { "type": "total", "amount": 850 }
        ]
      }
    ]
  }
]
```

A variant sold only on a plan lists no one-time option. Its `price` is the
default plan's price, and a Platform that adds it without choosing gets that
plan. Each option has its own policy.

<!-- ucp:example schema=shopping/purchase_options def=get_product_response op=get_product target=$.product.variants[0] -->
```json
{
  "id": "gid://example/Variant/coffee-club",
  "title": "Coffee Club",
  "description": { "plain": "A rotating single-origin selection." },
  "price": { "amount": 1800, "currency": "USD" },
  "purchase_options": [
    {
      "id": "po_club_monthly",
      "title": "Monthly",
      "description": { "plain": "One bag a month. Cancel anytime." },
      "price": { "amount": 1800, "currency": "USD" }
    },
    {
      "id": "po_club_quarterly",
      "title": "Quarterly",
      "description": { "plain": "Three bags every three months. Cancel anytime." },
      "price": { "amount": 5100, "currency": "USD" },
      "list_price": { "amount": 5400, "currency": "USD" }
    }
  ]
}
```

<!-- ucp:example schema=shopping/policy_subscription def=get_product_response op=get_product target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.subscription",
    "description": { "plain": "Coffee Club, monthly. Cancel anytime." },
    "applies_to": ["$.product.variants[0].purchase_options[0]"],
    "schedules": [
      {
        "description": { "plain": "$18.00 plus applicable tax and shipping every month until you cancel." },
        "totals": [
          { "type": "subtotal", "amount": 1800 },
          { "type": "total", "amount": 1800 }
        ]
      }
    ]
  },
  {
    "type": "dev.ucp.shopping.policy.subscription",
    "description": { "plain": "Coffee Club, quarterly. Cancel anytime." },
    "applies_to": ["$.product.variants[0].purchase_options[1]"],
    "schedules": [
      {
        "description": { "plain": "$51.00 plus applicable tax and shipping every three months until you cancel." },
        "totals": [
          { "type": "subtotal", "amount": 5400 },
          { "type": "discount", "amount": -300, "display_text": "Quarterly saving" },
          { "type": "total", "amount": 5100 }
        ]
      }
    ]
  }
]
```

### Checkout: the subscription selected

The Platform selected `po_monthly` for two bags. The line is priced under the
selected option, today's `totals` settle those two bags, the options are
echoed as priced for this checkout, and the subscription policy now targets
the line — binding, with a start date and a disclosure. It covers the selected
option's node by nesting, so the terms appear once; the one-time option
entails nothing and has no policy.

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_abc123",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/coffee-340g", "title": "House Blend 340g", "price": 850 },
      "quantity": 2,
      "totals": [
        { "type": "subtotal", "amount": 1700 },
        { "type": "total", "amount": 1700 }
      ],
      "selected_purchase_option_id": "po_monthly",
      "purchase_options": [
        {
          "id": "po_once",
          "title": "One-time",
          "price": { "amount": 1000, "currency": "USD" }
        },
        {
          "id": "po_monthly",
          "title": "Subscribe & save 15%",
          "description": { "plain": "Cancel anytime." },
          "price": { "amount": 850, "currency": "USD" },
          "list_price": { "amount": 1000, "currency": "USD" }
        }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 1700 },
    { "type": "tax", "amount": 136 },
    { "type": "total", "amount": 1836 }
  ],
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": { "plain": "Monthly coffee subscription. Manage or cancel anytime at example.com/account." },
      "applies_to": ["$.line_items[0]"],
      "url": "https://example.com/subscription-terms",
      "schedules": [
        {
          "description": { "plain": "$17.00 plus applicable tax and shipping every month from November 2, 2026, until you cancel." },
          "totals": [
            { "type": "subtotal", "amount": 1700 },
            { "type": "total", "amount": 1700 }
          ],
          "starts_at": "2026-11-02T00:00:00Z"
        }
      ]
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "dev.ucp.shopping.policy.subscription",
      "path": "$.line_items[0]",
      "presentation": "disclosure",
      "content": "$18.36 today. Then $17.00 plus tax and shipping every month from November 2, 2026, until you cancel."
    }
  ],
  "links": [ ... ]
}
```

### Checkout: a free trial selected

A trial option is the first order at its full price. Selecting it makes the
Business return a deferred payment term for that order — due at the end of the
trial unless the buyer cancels first — and a subscription policy for the
recurring orders that follow. Nothing is paid at completion. The unselected
"Start today" option keeps a prospective policy of its own, so the buyer can
still compare; it pairs with no disclosure and would not reach the Order.

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_trial",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/pro-plan", "title": "Pro plan", "price": 1200 },
      "quantity": 1,
      "totals": [
        { "type": "subtotal", "amount": 1200 },
        { "type": "total", "amount": 1200 }
      ],
      "selected_purchase_option_id": "po_trial",
      "purchase_options": [
        {
          "id": "po_trial",
          "title": "Start with a 14-day free trial",
          "description": { "plain": "Cancel before October 16, 2026 and you owe nothing." },
          "price": { "amount": 1200, "currency": "USD" }
        },
        {
          "id": "po_monthly",
          "title": "Start today",
          "price": { "amount": 1200, "currency": "USD" }
        }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 1200 },
    { "type": "total", "amount": 1200 }
  ],
  "payment": {
    "terms": [
      {
        "id": "pt_trial",
        "title": "Free for 14 days",
        "description": { "plain": "Nothing today. Cancel before October 16, 2026 and you owe nothing." },
        "schedules": [
          {
            "id": "sched_after_trial",
            "type": "deferred",
            "description": { "plain": "$12.00 due October 16, 2026, unless you cancel before then." },
            "due_at": "2026-10-16T00:00:00Z",
            "amount": 1200
          }
        ]
      }
    ],
    "selected_term_id": "pt_trial"
  },
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": { "plain": "Pro plan, monthly. Cancel anytime." },
      "applies_to": ["$.line_items[0]"],
      "schedules": [
        {
          "description": { "plain": "$12.00 every month from November 16, 2026, until you cancel." },
          "totals": [
            { "type": "subtotal", "amount": 1200 },
            { "type": "total", "amount": 1200 }
          ],
          "starts_at": "2026-11-16T00:00:00Z"
        }
      ]
    },
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": { "plain": "Pro plan, monthly, starting today. Cancel anytime." },
      "applies_to": ["$.line_items[0].purchase_options[1]"],
      "schedules": [
        {
          "description": { "plain": "$12.00 every month from November 2, 2026, until you cancel." },
          "totals": [
            { "type": "subtotal", "amount": 1200 },
            { "type": "total", "amount": 1200 }
          ],
          "starts_at": "2026-11-02T00:00:00Z"
        }
      ]
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "dev.ucp.shopping.policy.subscription",
      "path": "$.line_items[0]",
      "presentation": "disclosure",
      "content": "Free for 14 days. $12.00 on October 16, 2026 unless you cancel before then, and $12.00 every month after."
    }
  ],
  "links": [ ... ]
}
```

### Switching back to one-time

The Platform changes the selection with an update. The Business reprices the
line at $10, the binding subscription policy and its disclosure disappear, and
any payment handlers it had withheld for the subscription return.

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.checkout op=update direction=request -->
```json
{
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/coffee-340g" },
      "quantity": 2,
      "selected_purchase_option_id": "po_once"
    }
  ]
}
```

### A selection that no longer resolves

The monthly plan was withdrawn between responses. The Business selects the
default, reprices, and says so:

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "purchase_option_changed",
    "path": "$.line_items[0]",
    "content": "The monthly plan is no longer available for this item. It has been added as a one-time purchase at $10.00."
  }
]
```

### Order

The Order line records the option it was bought through. The recurring orders
are recorded by the Order's subscription policy, as that extension shows;
policies that targeted unselected options do not reach the Order.

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.order op=read -->
```json
{
  "ucp": { ... },
  "id": "ord_8f3e2a",
  "checkout_id": "chk_abc123",
  "permalink_url": "https://example.com/orders/8f3e2a",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/coffee-340g", "title": "House Blend 340g", "price": 850 },
      "quantity": { "original": 2, "total": 2, "fulfilled": 0 },
      "totals": [ ... ],
      "status": "processing",
      "purchase_option": { "id": "po_monthly", "title": "Subscribe & save 15%" }
    }
  ],
  "totals": [ ... ],
  "fulfillment": { ... },
  "policies": [ ... ]
}
```
