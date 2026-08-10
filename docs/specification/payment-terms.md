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

# Payment Terms Extension

* **Capability Name:** `dev.ucp.shopping.payment_terms`

## Overview

The Payment Terms extension lets a Business offer the Buyer a choice of **when**
payment for a checkout is due. A lodging Business can offer one term that
charges the full stay at booking and another that charges the first night now
and the balance at check-in. A Business selling equipment can offer Net-30
alongside pay-now.

A **payment term** is an addressable, renderable choice composed of one or more
**payment schedules**. Each schedule is one payment: an amount, and a complete
buyer-facing statement of when it is due.

This extension adds two properties to `checkout.payment`:

* `terms[]` — the payment terms the Business offers for this checkout.
  Response-only.
* `selected_term_id` — the selected term. Always present in a response;
  a Platform writes it to change the selection.

A Buyer picks one of the options in `terms[]`, the same way they pick
one [fulfillment option](fulfillment.md#platform-responsibilities).

## Presenting payment terms

Presentation is **term-agnostic**: a Platform does not need to model deposits,
installments, or trade credit to present a term meaningfully.

Given the Checkout's `currency`, a Platform that recognizes no `type` value and
reads no payment-term field other than `title`, `description`,
`schedules[].description`, and `schedules[].totals` **MUST** be able to present
what is owed and when, for every term. A Business **MUST** author terms so this
holds.

That floor covers amounts and timing. It does not by itself discharge a
jurisdictional disclosure duty — a finance charge that must be given a
prescribed prominence, for instance. Those obligations travel through
[Disclosures](#disclosures), and a Platform that cannot honor them escalates
rather than renders.

Everything above that floor is supplementary. `type` and `due_at` let a Platform
that wants to do more — split the checkout into due-now and due-later, sort
schedules, drive a calendar reminder — without ever being required to.

## Payment schedules

A schedule is **one payment**, not a timetable. A term that charges four times
has four schedules.

A Business **MUST** make each schedule's `description` a complete buyer-facing
statement of when and how that payment is due, so that a Platform can render it
verbatim. A Platform **MAY** use `type` and `due_at` for a richer presentation
— a calendar view, a countdown, a reminder — but **MUST NOT** present derived
timing that contradicts the `description`. Recognizing a `type` only enables
optional enhancement; the baseline contract is that `description` and `total`
are sufficient.

### Timing class

`type` is an open string vocabulary with exactly one well-known value:

| Type | Meaning |
| :--- | :------ |
| `immediate` | The payment is captured when the checkout is completed. |

Any other value means the payment is **not** captured at completion; the
`description` states when it is due. A Platform **MUST** treat an unrecognized
`type` as not captured at completion. Businesses **MAY** use additional values
such as `deferred` or `on_shipment`, but those values carry no protocol meaning
beyond "not `immediate`".

### Due dates

`due_at` is an absolute RFC 3339 date-time. A Business **SHOULD** provide it
when it can determine the due date at checkout, and **MUST** omit it when the
date depends on a future event — "due on delivery" has no date yet. `due_at`
never replaces `description`; it restates in machine-readable form what the
description already says.

The protocol defines no calendar arithmetic. A Business that offers four
biweekly payments emits four schedules with four computed dates, rather than a
recurrence rule a Platform would have to expand. This keeps month-end, daylight
saving, and rounding-residual decisions with the party that already makes them.

### Amounts

Each schedule's `totals` states what this one payment costs. A Business **MUST**
include exactly one `type: total` entry with a non-negative amount: the final
amount charged when this payment is taken, inclusive of tax and every other
charge. Unlike checkout totals, no `subtotal` is required, because the purchase
is priced at the checkout rather than once per payment.

A term's schedule `total` entries define the amount payable under that term. For
the **selected** term, the Business **MUST** ensure that sum equals the checkout
`total`.

Unselected terms are **indicative**. A term that discounts the purchase for
paying today has a different payable amount than one that defers part of it, so
at most one term can match the checkout total at any moment. Only the selected
term is bound to it.

## Selecting a payment term

Selecting a payment term is a **Checkout mutation**. A Platform sets
`selected_term_id`; the Business returns a recomputed Checkout. That response is
**authoritative for all derived state** — including `totals`, line item prices,
discount eligibility, `policies[]`, `messages[]`, and the payment handlers
offered.

A Platform **MUST NOT** assume that the amounts shown in `terms[]`
survive selection unchanged, and **MUST** re-render from the response.

A Business **MUST** make `terms[].id` unique within a Checkout, so
that a selection resolves to exactly one term.

A term is always selected. The Checkout `total` is the selected term's total, so
a response without a selection would show an amount that matches no stated
terms. A Business **MUST** return `selected_term_id` in every response. Where
the Buyer has made no choice, the Business selects a default.

When changing the selection, a Platform **MUST** set `selected_term_id` to an
`id` from the latest `terms[]`. A Platform **MUST** omit it on create, because
term IDs are scoped to a Checkout and no options exist yet — the create response
establishes both the options and the default. A Business receiving a selection
that no longer resolves — because the options changed — **MUST NOT** silently
substitute a term, and **MUST** report the change as a `payment_term_changed`
warning in `messages[]`.

Selecting a term can invalidate a selection previously accepted elsewhere in the
Checkout — a deferred term may not be available with a same-day fulfillment
option. The Business resolves the conflict, returns the authoritative state, and
**MUST** report the change as a `payment_term_changed` warning in `messages[]`.
A Platform can therefore detect a changed selection from the code alone, rather
than by comparing responses.

## Payment instruments and eligibility

This extension does not change how instruments are supplied. The Buyer's
instruments fund the checkout under the selected term, and the Business
allocates them across that term's schedules.

Checkout-specific handler and instrument eligibility is a **runtime result**.
Profiles advertise broad support; the Business resolves that support against the
Checkout context and any instruments already supplied, then returns the
authoritative `ucp.payment_handlers` in the response. This covers cases a
discovery-time predicate cannot express — a gift card whose balance is below the
deposit, an issuer that will not support a delayed capture for this Business, a
credential that expires before the balance comes due.

A Business **MUST NOT** publish payment-term identifiers in a discovery-time
handler profile. Term IDs are scoped to one checkout; a cacheable,
Buyer-independent profile cannot reference them.

Per-schedule funding — directing one instrument at one schedule and a different
instrument at another — is not defined in this version. A Business that supports
it does so outside the protocol.

## Disclosures

Some terms carry display obligations. A subscription that renews, an
installment plan with a finance charge, and a deposit that is forfeited on
cancellation are all subject to consumer-protection rules about what must be
shown, and when.

This extension does not define a private disclosure channel. It uses the two
that already exist:

1. A [policy](overview.md#policies) carries the durable terms text, targeted
   with `applies_to` at the node the terms concern — the payment term when the
   terms are about payment timing, the line item when they are about the goods.
2. A `messages[]` warning with `presentation: "disclosure"` and `code` set to
   that policy's `type` compels display of the notice.

These mechanisms carry durable terms and compel their display. The Business
remains responsible for the required content, its applicability, its timing, and
any affirmative Buyer acknowledgment. In particular, presenting a policy is
optional for a Platform, so any content that **must** reach the Buyer belongs in
the warning `content`, not only in the policy `description`.

Disclosure display is unconditional. Under [Warning
Presentation](checkout.md#warning-presentation) a Platform **MUST** display
every returned disclosure, **MUST** keep it in proximity to the node named by
`path`, and **MUST NOT** hide, collapse, or auto-dismiss it. A Platform that
cannot honor that contract — for example one that collapses a list of terms and
so cannot preserve proximity for each — **MUST** escalate through `continue_url`
rather than silently dropping the notice.

An obligation disclosed at checkout does not end at checkout: it records money
still owed, not context. Where a disclosure governed the term the Buyer
accepted, the Business **MUST** return that disclosure on the Order with its
`path` set to `$.payment.accepted_term`, and **MUST** use the same target in
the `applies_to` of any policy paired with it. A Business **MUST NOT** return
disclosures attached to terms the Buyer did not accept.

`applies_to` and `path` resolve against the response they appear in, so a target
that named the right node on the Checkout does not necessarily name it on the
Order; an Order's line items, for instance, are current-state data whose
positions need not match. A Business **MUST** ensure that every target it emits
resolves to the intended node on the response that carries it.

## Out of scope

**Amounts that are not determinable at checkout.** A schedule states a known
amount due at a stated time. Hotel incidentals, usage overages, and
post-purchase true-ups are not payment schedules; they are authorizations and
order adjustments.

**Multiple currencies within one term.** Every schedule total is denominated in
the Checkout `currency`, so a term cannot express an obligation payable partly
in another currency.

**Recurring commerce.** Schedules settle the current checkout. They do not
create future purchases, renewals, or fulfillment obligations. A Business
enrolling a Buyer in a subscription charges the first cycle through a payment
term and discloses the ongoing arrangement through a policy and its paired
disclosure. See [Subscription enrollment](#subscription-enrollment).

**Payment execution.** This extension discloses when money is due. It does not
define credential storage, future-charge authorization, how a Business executes
capture, or mandate requirements, and a Platform **MUST NOT** infer that a
deferred payment can be inspected, modified, or cancelled through UCP.

## Discovery

Businesses advertise payment terms support in their profile:

<!-- ucp:example skip reason="capability declaration fragment" -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.payment_terms": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/payment-terms",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/payment_terms.json"
        }
      ]
    }
  }
}
```

## Schema

### Payment

When this capability is active, `checkout.payment` is extended with available
terms and the selected term.

{{ extension_schema_fields('payment_terms.json#/$defs/payment', 'payment_terms') }}

### Order Payment

On the Order, `payment` carries the accepted term. The terms offered at checkout
are not projected.

The accepted term is the agreement, not a running balance. When the Order is
created, a Business **MUST** ensure its schedule `total` entries sum to the
Order `total`. A Business **MUST NOT** modify the accepted term after the Order
is created; post-purchase changes are recorded in `adjustments[]`. The schedules
can therefore sum to more than the Order currently owes after a refund, or less
after an exchange: the term states what was agreed, and the adjustments state
what happened after.

{{ extension_schema_fields('payment_terms.json#/$defs/order_payment', 'payment_terms') }}

### Entities

#### Payment Term

{{ schema_fields('types/payment_term', 'payment_terms') }}

#### Payment Schedule

{{ schema_fields('types/payment_schedule', 'payment_terms') }}

## Examples

### Lodging: pay now, or deposit and balance at check-in

> A $1,200 stay. Pay in full today for $1,150, or pay the first night now and
> the balance at check-in.

The two terms have **different payable amounts**. Their schedules sum to their
own term's total, and only the selected one is bound to the checkout total.

**Checkout response fragment — the terms on offer.** The Buyer has not chosen
yet, so the Business defaults to paying now, and says so:

<!-- ucp:example schema=shopping/payment_terms def=payment op=read direction=response -->
```json
{
  "selected_term_id": "pt_pay_now",
  "terms": [
    {
      "id": "pt_pay_now",
      "title": "Pay now",
      "description": { "plain": "Save $50 by paying for your stay today." },
      "schedules": [
        {
          "id": "sched_full",
          "type": "immediate",
          "description": { "plain": "Due today when you book." },
          "totals": [{ "type": "total", "amount": 115000 }]
        }
      ]
    },
    {
      "id": "pt_deposit_balance",
      "title": "First night now, balance at check-in",
      "description": { "plain": "Hold your room with one night's rate." },
      "schedules": [
        {
          "id": "sched_first_night",
          "type": "immediate",
          "description": { "plain": "Due today when you book." },
          "totals": [{ "type": "total", "amount": 30000 }]
        },
        {
          "id": "sched_balance",
          "type": "deferred",
          "description": {
            "plain": "Due at check-in on September 1, 2026 at 3:00 PM PDT."
          },
          "due_at": "2026-09-01T15:00:00-07:00",
          "totals": [{ "type": "total", "amount": 90000 }]
        }
      ]
    }
  ]
}
```

**Update request — the Buyer selects the deposit term:**

<!-- ucp:example schema=shopping/payment_terms def=payment op=update direction=request -->
```json
{
  "selected_term_id": "pt_deposit_balance"
}
```

**Checkout response — recomputed and authoritative:**

<!-- ucp:example schema=shopping/payment_terms def=dev.ucp.shopping.checkout op=update direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.checkout": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.payment_terms": [{ "version": "{{ ucp_version }}" }]
    },
    "payment_handlers": {
      "com.example.card_handler": [
        {
          "id": "card_handler",
          "version": "{{ ucp_version }}",
          "available_instruments": [{ "type": "card" }]
        }
      ]
    }
  },
  "id": "checkout_123",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [],
  "links": [
    { "type": "terms_of_service", "url": "https://example.com/tos" }
  ],
  "totals": [
    { "type": "subtotal", "amount": 120000 },
    { "type": "total", "amount": 120000 }
  ],
  "payment": {
    "selected_term_id": "pt_deposit_balance",
    "terms": [
      {
        "id": "pt_pay_now",
        "title": "Pay now",
        "description": { "plain": "Save $50 by paying for your stay today." },
        "schedules": [
          {
            "id": "sched_full",
            "type": "immediate",
            "description": { "plain": "Due today when you book." },
            "totals": [{ "type": "total", "amount": 115000 }]
          }
        ]
      },
      {
        "id": "pt_deposit_balance",
        "title": "First night now, balance at check-in",
        "description": { "plain": "Hold your room with one night's rate." },
        "schedules": [
          {
            "id": "sched_first_night",
            "type": "immediate",
            "description": { "plain": "Due today when you book." },
            "totals": [{ "type": "total", "amount": 30000 }]
          },
          {
            "id": "sched_balance",
            "type": "deferred",
            "description": {
              "plain": "Due at check-in on September 1, 2026 at 3:00 PM PDT."
            },
            "due_at": "2026-09-01T15:00:00-07:00",
            "totals": [{ "type": "total", "amount": 90000 }]
          }
        ]
      }
    ]
  }
}
```

Because the pay-now discount no longer applies, `checkout.totals` reports
$1,200 — the sum of the selected term's two schedules. Had the Buyer selected
`pt_pay_now`, the checkout total would be $1,150. The terms are unchanged; only
the selected term is bound to the checkout total. `ucp.payment_handlers` in this
response is the set resolved for the selected term.

The deposit terms live in a policy that targets the term they apply to:

<!-- ucp:example schema=shopping/checkout target=$.policies -->
```json
[
  {
    "type": "com.example.policy.deposit_forfeiture",
    "applies_to": ["$.payment.terms[1]"],
    "description": {
      "plain": "The $300 deposit is non-refundable within 48 hours of arrival."
    }
  }
]
```

On completion, the accepted term travels to the Order, so the Buyer can still
see that $900 is due at check-in. The other terms do not travel, and the deposit
disclosure moves with the term it governs:

<!-- ucp:example schema=shopping/payment_terms def=dev.ucp.shopping.order op=read direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order": [{"version": "{{ ucp_version }}"}],
      "dev.ucp.shopping.payment_terms": [{"version": "{{ ucp_version }}"}]
    }
  },
  "id": "order_9f2",
  "checkout_id": "checkout_7c1",
  "permalink_url": "https://hotel.example.com/orders/9f2",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_room",
      "item": {
        "id": "room_deluxe",
        "title": "Deluxe King, 3 nights",
        "price": 120000
      },
      "quantity": { "original": 1, "total": 1, "fulfilled": 0 },
      "totals": [
        { "type": "subtotal", "amount": 120000 },
        { "type": "total", "amount": 120000 }
      ],
      "status": "processing"
    }
  ],
  "fulfillment": { "expectations": [] },
  "totals": [
    { "type": "subtotal", "amount": 120000 },
    { "type": "total", "amount": 120000 }
  ],
  "payment": {
    "accepted_term": {
      "id": "pt_deposit_balance",
      "title": "First night now, balance at check-in",
      "description": { "plain": "Hold your room with one night's rate." },
      "schedules": [
        {
          "id": "sched_first_night",
          "type": "immediate",
          "description": { "plain": "Due today when you book." },
          "totals": [{ "type": "total", "amount": 30000 }]
        },
        {
          "id": "sched_balance",
          "type": "deferred",
          "description": {
            "plain": "Due at check-in on September 1, 2026 at 3:00 PM PDT."
          },
          "due_at": "2026-09-01T15:00:00-07:00",
          "totals": [{ "type": "total", "amount": 90000 }]
        }
      ]
    }
  },
  "policies": [
    {
      "type": "com.example.policy.deposit_forfeiture",
      "applies_to": ["$.payment.accepted_term"],
      "description": {
        "plain": "The $300 deposit is non-refundable within 48 hours of arrival."
      }
    }
  ]
}
```

The schedules sum to the Order `total`, and the policy that named
`$.payment.terms[1]` on the Checkout names `$.payment.accepted_term`
here. No representation of `pt_pay_now` survives.

### Installments

> Pay 25% today, then 25% every two weeks.

Four payments and four schedules: one captured at completion, and three with
computed due dates. The Business does the calendar arithmetic; the Platform
reads dates.

<!-- ucp:example schema=shopping/payment_terms def=payment_term -->
```json
{
  "id": "pt_pay_in_4",
  "title": "Pay in 4",
  "description": { "plain": "Four interest-free payments of $25." },
  "schedules": [
    {
      "id": "sched_1",
      "type": "immediate",
      "description": { "plain": "Due today." },
      "totals": [{ "type": "total", "amount": 2500 }]
    },
    {
      "id": "sched_2",
      "type": "deferred",
      "description": { "plain": "Due September 15, 2026." },
      "due_at": "2026-09-15T00:00:00Z",
      "totals": [{ "type": "total", "amount": 2500 }]
    },
    {
      "id": "sched_3",
      "type": "deferred",
      "description": { "plain": "Due September 29, 2026." },
      "due_at": "2026-09-29T00:00:00Z",
      "totals": [{ "type": "total", "amount": 2500 }]
    },
    {
      "id": "sched_4",
      "type": "deferred",
      "description": { "plain": "Due October 13, 2026." },
      "due_at": "2026-10-13T00:00:00Z",
      "totals": [{ "type": "total", "amount": 2500 }]
    }
  ]
}
```

### Subscription enrollment

> $29.99 per month, cancel anytime.

The checkout charges the first cycle. The ongoing arrangement is **disclosed**,
not scheduled: a later cycle is a future purchase the Buyer can decline by
cancelling, so it is not an amount owed for this checkout.

**Payment term — one immediate schedule for cycle one:**

<!-- ucp:example schema=shopping/payment_terms def=payment_term -->
```json
{
  "id": "pt_monthly",
  "title": "Monthly",
  "description": { "plain": "$29.99 today, then monthly until you cancel." },
  "schedules": [
    {
      "id": "sched_cycle_1",
      "type": "immediate",
      "description": { "plain": "Due today. Covers your first month." },
      "totals": [{ "type": "total", "amount": 2999 }]
    }
  ]
}
```

**Policy — the durable terms.** The recurrence concerns the subscribed item
rather than the payment timing, so it targets the line item — a node the Order
also has, which is what makes the snapshot possible:

<!-- ucp:example schema=shopping/checkout target=$.policies -->
```json
[
  {
    "type": "com.example.policy.subscription",
    "description": {
      "markdown": "Renews at **$29.99/month** on the 14th until cancelled. Cancel anytime at example.com/account."
    },
    "applies_to": ["$.line_items[0]"],
    "url": "https://example.com/subscription-terms"
  }
]
```

**Disclosure — compelled display, paired to the policy by `code`:**

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "com.example.policy.subscription",
    "path": "$.line_items[0]",
    "presentation": "disclosure",
    "content": "This subscription renews at $29.99/month on the 14th until you cancel. Cancel at https://example.com/account."
  }
]
```

A free trial works the same way: the schedule's `total` is `0`, and the
disclosure carries the obligation. A checkout whose total is zero while an
ongoing commitment is being authorized is precisely the case where compelled
display matters most.

## Platform responsibilities

Platforms **MUST**:

* Present each term's `title`, and each schedule's `description` and `total`
  amount, formatted in the Checkout `currency`.
* Re-render from the Business response after selecting a term, rather than
  reusing amounts read from `terms[]`.
* Treat an unrecognized schedule `type` as not captured at completion, and
  present the term regardless.
* Process disclosures attached to terms per
  [Warning Presentation](checkout.md#warning-presentation), escalating through
  `continue_url` when the rendering contract cannot be honored.

Platforms **MAY** use `type` and `due_at` for enhanced presentation — calendar
views, countdowns, reminders. This is optional; recognizing a `type` never
changes what a Platform is required to render.

Platforms **SHOULD**:

* Present terms so the Buyer can compare them before selecting, unless only one
  term is available or the Checkout is being handed off.

## Business responsibilities

Businesses **MUST**:

* Offer at least one payment term when the extension is active, and report the
  selected term in `selected_term_id` on every response.
* Ensure every term's schedules state, in `description` alone, when each payment
  is due.
* Ensure the selected term's schedule totals sum to the checkout total exactly
  once.
* Return the recomputed Checkout after a selection, including any change to
  totals, policies, messages, or eligible payment handlers.
* Place any content that must reach the Buyer in the disclosure `content`, not
  only in the paired policy `description`.
* Carry the accepted term onto the Order as `payment.accepted_term`, along with
  any disclosure that governed it.

Businesses **SHOULD**:

* Provide `due_at` whenever the due date is determinable at checkout.
* Keep schedule IDs stable across Checkout responses unless the schedule itself
  changes.
