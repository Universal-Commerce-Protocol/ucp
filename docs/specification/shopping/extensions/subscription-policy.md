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

# Subscription Policy Extension

## Overview

The Subscription Policy Extension defines the
`dev.ucp.shopping.policy.subscription` policy type on the core
[`policies[]`](../../overview/index.md#policies) primitive. It adds
machine-readable terms for the recurring orders that follow a purchase — what
recurs, for how much, how often, and from when — to policies that carry this
type, from catalog through cart, checkout, and order. A platform can tell a
buyer "this is $15 a month starting November 2 until you cancel" on every
surface, and an agent can see that an item recurs, for how much, and from
when, before it builds a cart.

A checkout prices and settles the **current** purchase: its `totals` are the
amount due now, and that amount is paid at completion exactly as core Checkout
already states. A subscription is a series of **recurring orders** that follow
— orders the Business places on the buyer's behalf, on agreed terms, when the
buyer is not present. Those orders do not exist yet and nothing about them is
owed at checkout, so they are not payment schedules and do not appear in
`totals`. They are terms about the items, disclosed and agreed to at checkout
and recorded on the Order. That is what a policy is for.

**Key features:**

- The subscription's recurring orders as one or more consecutive `schedules`,
    each a complete buyer-facing `description` supplemented by the order's
    `totals` and an absolute `starts_at` — timed like a payment term's
    schedules, priced like a line item, one subscription per policy
- Disclosure through the existing `messages[]` channel, so the buyer sees the
    recurring terms before completion on every platform
- A frozen record of the agreed terms on the Order, which is where the buyer
    manages the subscription
- No new payment, authorization, or request-side machinery

**Dependencies:**

- The core `policies[]` primitive (see
  [Policies](../../overview/index.md#policies)).
- One or more of the parent capabilities this type extends: Catalog Search,
  Catalog Lookup, Cart, Checkout, or Order.

This extension only structures the type-specific body. The `policies[]`
container, `applies_to` targeting, same-type precedence, and buyer-facing
disclosure through `messages[]` are defined once by the primitive and are
**unchanged** here. Whether an item recurs is a property of the item the
Business sells, or of a purchase option the buyer selects; this extension
describes the recurrence and does not offer the choice.

## Discovery

Businesses advertise subscription policy support in their profile. The type
extends any surface that carries `policies[]`:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.policy.subscription": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup",
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/subscription-policy",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/policy_subscription.json"
        }
      ]
    }
  }
}
```

A Business **MAY** advertise support on a subset of these surfaces. A Platform
that has negotiated this type validates the subscription body and **MAY** reason
over it. A Platform that has not negotiated it still renders the policy from
the base `type` and `description`, and still receives the paired disclosure,
because the subscription body is purely additive.

## Schema

When this type is active, a `policies[]` entry whose `type` is
`dev.ucp.shopping.policy.subscription` **MAY** carry the following fields in
addition to the base `type`, `description`, `applies_to`, and `url`. Every
field is optional, and an omitted field means the term is not stated
structurally; a subscription policy with no structured fields is still
presentable from its `description`.

### Subscription Policy

{{ extension_schema_fields('policy_subscription.json#/$defs/subscription_policy', 'shopping/extensions/subscription-policy') }}

### Subscription Terms

The schedules are a shared type, so that a purchase option can preview the
same terms a policy later binds.

{{ schema_fields('types/subscription_terms', 'shopping/extensions/subscription-policy') }}

### Subscription Schedule

{{ schema_fields('types/subscription_schedule', 'shopping/extensions/subscription-policy') }}

## Subscription terms

A subscription policy carries the same two layers a payment term does. The
policy's `description` summarizes the subscription as a whole, and its
`schedules[]` state the recurring orders: each schedule is one **run** of
orders on one set of terms, with its own complete `description`, the order's
`totals`, and a `starts_at`. Most subscriptions have exactly one schedule. A
subscription whose terms change — an introductory price that steps up, a
weekly cadence that becomes monthly after a year — has one schedule per run,
in the order they take effect.

### Description is the statement

A Business **MUST** make each schedule's `description` a complete buyer-facing
statement of that run of recurring orders — the amount of each, how often one
is placed, from when, and until when — so that a Platform can render it
verbatim. A Platform that reads no other field **MUST** be able to present the
subscription correctly from the policy `description` and the schedule
descriptions alone, and a Business **MUST** author them so this holds.

There is no recurrence vocabulary on the wire — no interval, no cycle count,
no anchor — for the same reason a payment schedule states its timing in text:
the Business does the calendar arithmetic, and a Platform prints the result.
The structured fields are an absolute date, as a payment schedule carries, and
the order's `totals`, as a line item carries. A Platform **MAY** use them for
a richer presentation — a budget check, a calendar reminder — but **MUST NOT**
present derived terms that contradict a `description`, and **MUST NOT** derive
further order dates from them.

### One subscription per policy

A subscription policy describes **one** subscription: the series of recurring
orders for the items it governs. Under
[Precedence](../../overview/index.md#precedence) exactly one policy of a given
type governs a node, and two policies of one type
covering a node at the same depth and precision is an authoring error a
Business **MUST NOT** publish. A sequence of terms on one line is therefore
never two policies; it is one policy with consecutive `schedules`. Composition
is authored by the Business, not resolved by the Platform.

Items on different subscriptions — a monthly coffee and a biweekly filter pack
— are governed by separate policies, each targeting its own line. Where a
Business cannot target them separately, it states every subscription in one
policy's `description` and omits `schedules`.

One policy also corresponds to one subscription the Business creates: two lines
that recur together on one set of terms are one policy with two `applies_to`
targets.

### Consecutive schedules

Schedules are listed in the order they take effect. Each continues until the
next one's `starts_at`; the last continues until the subscription ends — until
cancelled, or until the end its `description` states. The Business computes
every boundary and states it as a date; a Platform reads dates and never
derives them.

### Totals

A recurring order is an order, and a schedule states what it costs the way a
line item does: `totals` is a breakdown of each recurring order placed under
that schedule, for the items the policy governs, at the quantities in the
response — a policy over a line with `quantity` 2 states the order for both.
On a catalog surface, where there is no quantity, it is the breakdown for one
unit of the targeted variant. Amounts are in the response currency's minor
units, or on a catalog surface in the currency of the targeted variant's
`price`.

A schedule's `totals` follow the [line-item contract](../checkout/index.md#totals):
entries carry a `type` and a signed `amount`, a Platform renders them in the
order provided and **MUST NOT** aggregate, filter, or reorder them, and a
`total` entry **MUST** be present when `totals` is. A `subtotal` states the
merchandise at its one-time price; a `discount` makes the saving for
subscribing visible, with its `display_text` naming it; `total` is what the
order comes to.

`total` is the amount of the order **before** the taxes, fulfillment, and fees
the Business computes when it places it, because the rates that apply on a
future date are not knowable at checkout, and the schedule `description`
**MUST** say so where they apply. A Business that *can* state one of those
costs — a flat renewal shipping rate, a tax-exempt item — includes its entry,
and `total` then includes it. An omitted entry is not stated, not zero. This
is the one place a subscription schedule differs from a payment schedule,
whose amount is inclusive of every cost because the payment is known.

A saving that expires is not a changing `discount`; it is a schedule that ends
and another that begins, so the step-up is visible in structure.

### Start dates and the current purchase

The current purchase is the first order. Everything the buyer owes today is in
the checkout `totals` and is paid at completion; the first schedule's
`starts_at` is when the first recurring order **after** it is placed, stated as
an absolute RFC 3339 date-time. An order is either this checkout or a recurring
order under a schedule, never both. A later schedule's `starts_at` is when the
first order on its terms is placed.

A free trial is a checkout whose `totals` are zero and whose first schedule
starts when the trial ends. No separate trial field is needed. A trial
followed by recurring orders is a subscription; a purchase whose payment is
merely collected later is a [payment term](../../payment/extensions/terms.md),
not a subscription, and carries no subscription policy.

`starts_at` is supplementary to `description`, never a replacement for it. It
**MAY** be omitted where the Business cannot yet determine it — on a catalog
surface, or on a cart that lacks the destination or fulfillment selection its
first order date depends on. It **SHOULD** be present once a checkout is
`ready_for_complete`, so that what the buyer agrees to is dated.

A subscription that ends on its own — twelve monthly orders, a filter pack
every two weeks for a year — states its end in its last schedule's
`description`. A prepaid purchase that does **not** renew is not a
subscription: it is one purchase with a delivery schedule, carries no
subscription policy, and its future deliveries are described in the item's own
terms until a capability for scheduled fulfillment exists.

## Disclosure and agreement

Recurring orders are a buyer-facing commitment that nearly every jurisdiction
requires be shown before it is agreed to. When a subscription policy governs a
line on a cart or checkout, the Business **MUST** emit a `messages[]` warning
with `presentation: "disclosure"`, `code` set to
`dev.ucp.shopping.policy.subscription`, and `path` naming the line, as
[Presenting policies](../../overview/index.md#presenting-policies) defines.
Under [Warning Presentation](../checkout/index.md#warning-presentation) the
Platform **MUST** display it, **MUST** keep it adjacent to the line, **MUST
NOT** dismiss it, and **MUST** escalate through `continue_url` if it cannot.
Content that must reach the buyer belongs in the warning `content`, not only in
the policy `description`, because presenting a policy is optional for a
Platform.

Completing a checkout that carries a disclosed subscription policy is the
buyer's agreement to its terms, on the same trust model as a one-time
purchase: the authenticated Platform is relied upon to have shown the
disclosure. Where a Business or a jurisdiction requires affirmative
acknowledgment beyond display, the Business uses the mechanisms Checkout
already provides — an error with `severity: "requires_buyer_review"` moves the
checkout to `requires_escalation` and the buyer acknowledges through
`continue_url`; a signed [AP2 mandate](../../payment/extensions/ap2-mandates.md)
binds the buyer to the checkout state, policies included, where
cryptographic proof is wanted. This extension adds no authorization field of
its own.

## Payment eligibility

Recurring orders are paid with an instrument the Business can charge when the
buyer is not present. Checkout already requires a Business to filter the
payment handlers and instruments it offers to the context of the cart, and
names subscriptions as the example. A Business **MUST** offer only instruments
able to pay for the recurring orders a governing subscription policy describes,
and **MUST** reject one that cannot. A Platform **MUST** treat the handlers in each
response as authoritative, and re-read them after any change that adds or
removes a subscription policy.

A checkout whose `totals` are zero still completes with a payment instrument:
`payment` remains required at completion so that the Business can retain an
instrument for the recurring orders. How a handler stores an instrument,
whether it is authorized or captured at completion, and how a payment for a
recurring order is executed or recovers from a decline are payment-handler and
order-lifecycle behavior, outside this extension.

## Targeting and precedence

Targeting and precedence are provided by the `policies[]` primitive and are not
redefined here. A subscription policy targets the items that recur: a variant
or product on a catalog surface, a line item on cart, checkout, and order. It
is rarely response-wide, because a response-wide subscription policy would
declare that everything in the response recurs. See
[Targeting](../../overview/index.md#targeting) and
[Precedence](../../overview/index.md#precedence).

Nested line items are siblings in `line_items[]`, not JSON descendants of
their parent, so a policy that targets a parent line does not cover its
components. A bundle whose components recur on different terms carries one
policy per recurring component, each targeting that component's line. Where a
Business cannot emit component lines to a Platform, it targets the parent with
a single policy whose `description` states every subscription and which omits
`schedules`.

## Order

An Order carries the subscription policies that governed its lines at checkout
as part of its `policies[]` snapshot, with `applies_to` re-targeted to the
Order's lines. A Business **MUST** carry forward every subscription policy the
buyer agreed to, along with the disclosure that paired with it, its `path`
naming the Order line. This snapshot is the authoritative record of the terms
that were disclosed and agreed; a dispute is resolved against it.

The Order is also where the buyer manages the subscription. Every Order carries
a `permalink_url` to the Business's order page, and a subscription entered into
through an agent is managed there like any other: the recurring orders
originate from this Order, so a buyer who can reach it can reach them. The
policy's `url` and `description` state how to cancel, as the disclosure does.
No further identifier or link is needed.

The snapshot states what was agreed, not what has happened since. Price changes
the Business notifies later, pauses, and cancellation are not reflected on the
Order's policies; they belong to the subscription, which a separate capability
may expose, keyed by the Order it originated from. Recurring orders are Orders
in their own right, not adjustments to this one.

## Out of scope

- **The choice to subscribe.** A policy describes; it never offers a choice.
  Where a variant can be bought once or as a subscription, the selection is a
  purchase option on the line, defined by a separate extension. A product that
  is only sold as a subscription needs no selection: the policy alone carries
  its terms.
- **A recurrence engine.** Cadence, cycle counts, anchors, alignment, and
  time zones are not on the wire. A schedule's `description` states how often
  and until when; the Business computes dates and states them absolutely.
- **Usage-based pricing and spend caps.** A schedule states a fixed amount.
  Where a recurring order's amount depends on usage, `description` carries the
  terms; structured fields for estimates and caps are additive follow-ups to
  the shared type.
- **Delivery cadence.** Order cadence and fulfillment cadence are independent;
  a prepaid order delivered monthly is one order with several fulfillments, and
  a monthly order does not imply a monthly delivery. Future deliveries are
  described in `description` until a capability for scheduled fulfillment
  exists.
- **Subscription identity and management.** Status, modification, pause, and
  cancellation operations, and the lifecycle of the recurring orders
  themselves, are a separate capability. It defines how a subscription is
  identified when it exists; until then the Order the subscription originated
  from is the handle, and `permalink_url` is the buyer's path to it.
- **Payment execution.** Credential storage, recurring authorization models,
  mandates, and off-session recovery are payment-handler behavior.

## Responsibilities

Businesses **MUST**:

- Emit a `dev.ucp.shopping.policy.subscription` policy targeting every line
  for which recurring orders will follow the current purchase, on every
  surface that carries `policies[]`.
- Describe one subscription per policy, as consecutive schedules where its
  terms change, and target items on different subscriptions with separate
  policies.
- Make each schedule's `description` a complete buyer-facing statement of that
  run of recurring orders — what each costs, how often, from when, until when
  — sufficient on its own, and keep `totals` and `starts_at` consistent with
  it.
- Pair every governing subscription policy on a cart or checkout with a
  `messages[]` disclosure whose `path` names the line.
- Offer only payment instruments that can pay for the recurring orders
  described.
- Carry agreed subscription policies and their disclosures onto the Order.

Businesses **SHOULD**:

- Provide `starts_at` once a checkout is `ready_for_complete`.
- Provide `totals` on every schedule whose order cost is fixed, with a
  `discount` entry wherever the subscription prices below the one-time price.

Platforms **MUST**:

- Present the paired disclosure under the `disclosure` rendering contract.
- Present the subscription from the policy and schedule descriptions, and
  derive no order dates beyond each schedule's `starts_at`.
- Re-read `ucp.payment_handlers` after a response adds or removes a
  subscription policy.

Platforms **MAY**:

- Compare, filter, or budget against a schedule's `total` and `starts_at`.
- Surface `url` alongside the terms, and on the Order, `permalink_url` as the
  buyer's path to manage the subscription.

## Examples

### Checkout with a monthly subscription

A buyer takes two bags of coffee on a "subscribe & save" plan. The checkout
`totals` settle today's two bags; the policy's one schedule states the
recurring orders, with the saving against the $10 one-time price visible as a
`discount`. The policy targets the line, and a paired disclosure compels the
buyer-facing notice.

<!-- ucp:example schema=shopping/policy_subscription def=dev.ucp.shopping.checkout target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.subscription",
    "description": { "plain": "Monthly coffee subscription. Manage or cancel anytime at example.com/account." },
    "applies_to": ["$.line_items[0]"],
    "url": "https://example.com/subscription-terms",
    "schedules": [
      {
        "description": { "plain": "$17.00 plus applicable tax and shipping every month from November 2, 2026, until you cancel." },
        "totals": [
          { "type": "subtotal", "amount": 2000 },
          { "type": "discount", "amount": -300, "display_text": "Subscribe & save 15%" },
          { "type": "total", "amount": 1700 }
        ],
        "starts_at": "2026-11-02T00:00:00Z"
      }
    ]
  }
]
```

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "dev.ucp.shopping.policy.subscription",
    "path": "$.line_items[0]",
    "presentation": "disclosure",
    "content": "You'll be charged $17.00 plus tax and shipping every month starting November 2, 2026, until you cancel.",
    "url": "https://example.com/subscription-terms"
  }
]
```

### Introductory price

Two schedules: an introductory rate for three months, then the standing rate
until cancelled. The first ends where the second begins; the Business computed
both dates, and the deeper introductory `discount` simply stops appearing.

<!-- ucp:example schema=shopping/policy_subscription def=dev.ucp.shopping.checkout target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.subscription",
    "description": { "plain": "Monthly coffee subscription with an introductory rate for your first three months. Cancel anytime." },
    "applies_to": ["$.line_items[0]"],
    "url": "https://example.com/subscription-terms",
    "schedules": [
      {
        "description": { "plain": "$10.00 plus applicable tax and shipping every month for three months, from November 2, 2026." },
        "totals": [
          { "type": "subtotal", "amount": 2000 },
          { "type": "discount", "amount": -1000, "display_text": "Introductory rate" },
          { "type": "total", "amount": 1000 }
        ],
        "starts_at": "2026-11-02T00:00:00Z"
      },
      {
        "description": { "plain": "Then $17.00 plus applicable tax and shipping every month from February 2, 2027, until you cancel." },
        "totals": [
          { "type": "subtotal", "amount": 2000 },
          { "type": "discount", "amount": -300, "display_text": "Subscribe & save 15%" },
          { "type": "total", "amount": 1700 }
        ],
        "starts_at": "2027-02-02T00:00:00Z"
      }
    ]
  }
]
```

### Free trial

The checkout `totals` are zero. The schedule starts when the trial ends and
the first recurring order is placed; `payment` is still submitted at
completion so the Business holds an instrument for it.

<!-- ucp:example schema=shopping/policy_subscription def=dev.ucp.shopping.checkout target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.subscription",
    "description": { "plain": "Pro plan with a 14-day free trial. Cancel anytime." },
    "applies_to": ["$.line_items[0]"],
    "schedules": [
      {
        "description": { "plain": "Free for 14 days, then $12.00 per month starting October 16, 2026, until you cancel." },
        "totals": [
          { "type": "subtotal", "amount": 1200 },
          { "type": "total", "amount": 1200 }
        ],
        "starts_at": "2026-10-16T00:00:00Z"
      }
    ]
  }
]
```

### Cadence that changes

Weekly for the first year, then monthly. The amount happens not to change;
the cadence does, so the two runs are two schedules.

<!-- ucp:example schema=shopping/policy_subscription def=dev.ucp.shopping.checkout target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.subscription",
    "description": { "plain": "Weekly for the first year, then monthly. Cancel anytime." },
    "applies_to": ["$.line_items[0]"],
    "schedules": [
      {
        "description": { "plain": "$15.00 plus applicable tax and shipping every week from October 9, 2026 through October 1, 2027." },
        "totals": [
          { "type": "subtotal", "amount": 1500 },
          { "type": "total", "amount": 1500 }
        ],
        "starts_at": "2026-10-09T00:00:00Z"
      },
      {
        "description": { "plain": "Then $15.00 plus applicable tax and shipping every month from October 8, 2027, until you cancel." },
        "totals": [
          { "type": "subtotal", "amount": 1500 },
          { "type": "total", "amount": 1500 }
        ],
        "starts_at": "2027-10-08T00:00:00Z"
      }
    ]
  }
]
```

### Finite subscription

A filter pack every two weeks for one year. One schedule whose `description`
states the end.

<!-- ucp:example schema=shopping/policy_subscription def=dev.ucp.shopping.checkout target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.subscription",
    "description": { "plain": "Filter replenishment for one year. Does not renew after that." },
    "applies_to": ["$.line_items[0]"],
    "schedules": [
      {
        "description": { "plain": "$6.00 plus applicable tax and shipping every 2 weeks from October 16, 2026 through October 1, 2027 (26 shipments), then stops." },
        "totals": [
          { "type": "subtotal", "amount": 600 },
          { "type": "total", "amount": 600 }
        ],
        "starts_at": "2026-10-16T00:00:00Z"
      }
    ]
  }
]
```

### Catalog

A product sold only as a subscription carries its terms on the catalog
surface, so an agent can compare it before building a cart. The totals are
for one unit; the start date is not yet known, so it is omitted.

<!-- ucp:example schema=shopping/policy_subscription def=get_product_response op=get_product target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.subscription",
    "description": { "plain": "Monthly subscription. Cancel anytime from your account." },
    "applies_to": ["$.product.variants[0]"],
    "url": "https://example.com/subscription-terms",
    "schedules": [
      {
        "description": { "plain": "$15.00 plus applicable tax and shipping every month until cancelled." },
        "totals": [
          { "type": "subtotal", "amount": 1500 },
          { "type": "total", "amount": 1500 }
        ]
      }
    ]
  }
]
```

### Order

The Order carries the agreed policy, re-targeted to its line. The disclosure
travels with it, and `permalink_url` is where the buyer manages the
subscription.

<!-- ucp:example schema=shopping/policy_subscription def=dev.ucp.shopping.order op=read -->
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
      "totals": [
        { "type": "subtotal", "amount": 1700 },
        { "type": "total", "amount": 1700 }
      ],
      "status": "processing"
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 1700 },
    { "type": "tax", "amount": 136 },
    { "type": "total", "amount": 1836 }
  ],
  "fulfillment": { ... },
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": { "plain": "Monthly coffee subscription." },
      "applies_to": ["$.line_items[0]"],
      "url": "https://example.com/subscription-terms",
      "schedules": [
        {
          "description": { "plain": "$17.00 plus applicable tax and shipping every month from November 2, 2026, until you cancel." },
          "totals": [
            { "type": "subtotal", "amount": 2000 },
            { "type": "discount", "amount": -300, "display_text": "Subscribe & save 15%" },
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
      "content": "You'll be charged $17.00 plus tax and shipping every month starting November 2, 2026, until you cancel."
    }
  ]
}
```
