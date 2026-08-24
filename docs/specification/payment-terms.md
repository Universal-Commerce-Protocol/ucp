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
* `selected_term_id` — the selected term. Present in a response whenever `terms`
  is; a Platform writes it to change the selection.

A Buyer picks one of the options in `terms[]`, the same way they pick
one [fulfillment option](fulfillment.md#platform-responsibilities).

## When a Checkout carries terms

Payment terms are optional. A Business offers them when a Checkout has something
to say about payment timing — a choice between terms, or a single term whose
schedules must be disclosed. Where payment is due in full at completion, a
Business may omit `terms` and `selected_term_id` entirely, and the Checkout
`total` is the amount due, as core Checkout already states.

Where `terms` is present it **MUST** contain at least one term, and
`selected_term_id` **MUST** name one of them. The Checkout `total` is the
selected term's total, so a list of terms without a selection would show an
amount matching no stated term.

## Presenting payment terms

Presentation is **term-agnostic**: a Platform does not need to model deposits,
installments, or trade credit to present a term meaningfully.

Given the Checkout's `currency`, a Platform that recognizes no `type` value and
reads no payment-term field other than `title`, `description`,
`schedules[].description`, and `schedules[].amount` **MUST** be able to present
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

A Business offering exactly one term is disclosing rather than asking. A
Platform **SHOULD** present that term without implying a choice.

## Payment schedules

A schedule is **one payment**. A term that charges four times has four
schedules.

A Business **MUST** make each schedule's `description` a complete buyer-facing
statement of when and how that payment is due, so that a Platform can render it
verbatim. A Platform **MAY** use `type` and `due_at` for a richer presentation
— a calendar view, a countdown, a reminder — but **MUST NOT** present derived
timing that contradicts the `description`.

### Timing class

`type` is an open string vocabulary with exactly one well-known value:

| Type | Meaning |
| :--- | :------ |
| `immediate` | The payment is due when the checkout is completed. |

Any other value means the payment is **not** due at completion; the
`description` states when it is due. A Platform **MUST** treat an unrecognized
`type` as not due at completion. Businesses **MAY** use additional values
such as `deferred` or `on_shipment`, but those values carry no protocol meaning
beyond "not `immediate`".

### Due dates

`due_at` is an absolute RFC 3339 date-time. A Business **SHOULD** provide it
when it can determine the due date at checkout, and **MUST** omit it when the
date depends on a future event — "due on delivery" has no date yet. `due_at`
never replaces `description`; it restates in machine-readable form what the
description already says.

### Amounts

Each schedule states a single `amount`: the amount charged when that payment is
taken, inclusive of tax and every other charge, in the Checkout `currency`.

A term's schedule amounts sum to the amount payable under that term. For the
**selected** term, the Business **MUST** ensure that sum equals the checkout
`total`.

Unselected terms are **indicative**. A term that discounts the purchase for
paying today has a different payable amount than one that defers part of it, so
only the selected term must match the checkout total at any moment.

Where the selected term changes what the purchase costs — a discount for paying
today, a finance charge for paying over time — that difference **MUST** appear
as its own entry in `checkout.totals`, a negative `discount` or a positive
`fee`. A Business **SHOULD** set `display_text` on that entry so the Buyer can
understand what choosing the term contributed.

## Selecting a payment term

Selecting a payment term is a **Checkout update**. A Platform sets
`selected_term_id`; the Business returns a recomputed Checkout. That response is
**authoritative for all derived state** — including `totals`, line item prices,
discount eligibility, `policies[]`, `messages[]`, and the payment handlers
offered.

A Platform **MUST NOT** assume that the amounts shown in `terms[]`
survive selection unchanged, and **MUST** re-render from the response.

A Business **MUST** make `terms[].id` unique within a Checkout, so
that a selection resolves to exactly one term.

In every response that carries `terms`, one of them is selected. Where the Buyer
has made no choice, the Business selects a default.

A Platform changes the selection through Update Checkout, setting
`selected_term_id` to an `id` from the latest `terms[]`. A Platform **MUST**
omit it on create, because term IDs are scoped to a Checkout and no options
exist yet — the create response establishes the options, if any, and the default
among them. A Platform **MUST** omit it on complete, because the term is already
agreed before a Checkout can reach `ready_for_complete`, and the amount due at
completion follows from it. A Business receiving a selection that no
longer resolves — because the options changed — **MUST NOT** silently substitute
a term, and **MUST** report the change as a `payment_term_changed` warning in
`messages[]`.

Selecting a term can invalidate a selection previously accepted elsewhere in the
Checkout — a deferred term may not be available with a same-day fulfillment
option. The Business resolves the conflict, returns the authoritative state, and
**MUST** report the change as a `payment_term_changed` warning in `messages[]`.
A Business **MUST** also report that warning when changing the selected term
in place, by altering its schedules, due dates, or amounts, without naming a
different term.
A Platform can therefore detect a changed selection from the code alone, rather
than by comparing responses.

## Payment instruments and eligibility

This extension does not change how instruments are supplied. The Buyer's
instruments fund the checkout under the selected term.

Checkout-specific handler and instrument eligibility is a **runtime result**.
Profiles advertise broad support; the Business resolves that support against the
Checkout context and any instruments already supplied, then returns the
authoritative `ucp.payment_handlers` in the response. This covers cases a
discovery-time predicate cannot express — a gift card whose balance is below the
deposit, an issuer that will not support a delayed capture for this Business, a
credential that expires before the balance comes due.

A Platform therefore cannot pre-compute the effect of a choice, and **MUST**
treat the set in each response as authoritative for that response alone. A
handler that must be initialized with the amount and timing it will charge
cannot be prepared before the term is agreed, and **MAY** cease to be offered
once it is.

The instrument funding a term is charged once for each of that term's
schedules, and **MUST** be capable of every one of them. A Business **MUST NOT**
advertise an instrument that cannot fund every schedule of the selected term,
and **MUST** reject one that is submitted. An instrument that can only be
charged immediately therefore cannot be offered on a term that defers any part
of the payment.

A term with more than one schedule **MUST** be funded by a single instrument.
[Split Payments](payment/split-payments.md) composes with a term that has exactly one
schedule, and not otherwise.

## Disclosures

Some terms carry display obligations. An installment plan with a finance charge
and a deposit that is forfeited on cancellation are both subject to
consumer-protection rules about what must be shown, and when.

This extension does not define a private disclosure channel. It uses the two
that already exist:

1. A [policy](overview/index.md#policies) carries the durable terms text, targeted
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
Presentation](shopping/checkout/index.md#warning-presentation) a Platform **MUST** display
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

**Multiple currencies within one term.** Every schedule amount is denominated in
the Checkout `currency`, so a term cannot express an obligation payable partly
in another currency.

**Recurring commerce.** Schedules settle the current checkout. They do not
create future purchases, renewals, or fulfillment obligations.

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

{{ extension_schema_fields('payment_terms.json#/$defs/payment', 'payment-terms') }}

### Order Payment

On the Order, `payment` carries the accepted term. The terms offered at checkout
are not projected.

The accepted term is the agreement, not a running balance. When the Order is
created, a Business **MUST** ensure its schedule amounts sum to the Order
`total`. A Business **MUST NOT** modify the accepted term after the Order
is created; post-purchase changes are recorded in `adjustments[]`. The schedules
can therefore sum to more than the Order currently owes after a refund, or less
after an exchange: the term states what was agreed, and the adjustments state
what happened after.

{{ extension_schema_fields('payment_terms.json#/$defs/order_payment', 'payment-terms') }}

### Entities

#### Payment Term

{{ schema_fields('types/payment_term', 'payment-terms') }}

#### Payment Schedule

{{ schema_fields('types/payment_schedule', 'payment-terms') }}

## Examples

### Lodging: pay now, or deposit and balance at check-in

> A $1,200 stay. Pay in full today for $1,150, or pay the first night now and
> the balance at check-in.

The two terms have **different payable amounts**. Each term's schedules sum to
what that term is payable at, and only the selected one is bound to the checkout
total.

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
          "amount": 115000
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
          "amount": 30000
        },
        {
          "id": "sched_balance",
          "type": "deferred",
          "description": {
            "plain": "Due at check-in on September 1, 2026 at 3:00 PM PDT."
          },
          "due_at": "2026-09-01T15:00:00-07:00",
          "amount": 90000
        }
      ]
    }
  ]
}
```

The $50 the pay-now term saves is stated where the purchase is priced, as its
own entry in `checkout.totals`:

<!-- ucp:example schema=shopping/checkout target=$.totals -->
```json
[
  { "type": "subtotal", "amount": 120000 },
  { "type": "discount", "amount": -5000, "display_text": "Pay-now saving" },
  { "type": "total", "amount": 115000 }
]
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
            "amount": 115000
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
            "amount": 30000
          },
          {
            "id": "sched_balance",
            "type": "deferred",
            "description": {
              "plain": "Due at check-in on September 1, 2026 at 3:00 PM PDT."
            },
            "due_at": "2026-09-01T15:00:00-07:00",
            "amount": 90000
          }
        ]
      }
    ]
  }
}
```

Because the pay-now discount no longer applies, `checkout.totals` reports
$1,200 — the sum of the selected term's two schedules — and the `discount` entry
that carried the $50 saving is gone. Had the Buyer selected `pt_pay_now`, the
checkout total would be $1,150, composed with that entry. The terms are
unchanged; only the selected term is bound to the checkout total.
`ucp.payment_handlers` in this response is the set resolved for the selected
term.

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
          "amount": 30000
        },
        {
          "id": "sched_balance",
          "type": "deferred",
          "description": {
            "plain": "Due at check-in on September 1, 2026 at 3:00 PM PDT."
          },
          "due_at": "2026-09-01T15:00:00-07:00",
          "amount": 90000
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

Four payments and four schedules: one due at completion, and three with
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
      "amount": 2500
    },
    {
      "id": "sched_2",
      "type": "deferred",
      "description": { "plain": "Due September 15, 2026." },
      "due_at": "2026-09-15T00:00:00Z",
      "amount": 2500
    },
    {
      "id": "sched_3",
      "type": "deferred",
      "description": { "plain": "Due September 29, 2026." },
      "due_at": "2026-09-29T00:00:00Z",
      "amount": 2500
    },
    {
      "id": "sched_4",
      "type": "deferred",
      "description": { "plain": "Due October 13, 2026." },
      "due_at": "2026-10-13T00:00:00Z",
      "amount": 2500
    }
  ]
}
```

## Platform responsibilities

Platforms **MUST**:

* Present each term's `title`, and each schedule's `description` and `amount`,
  formatted in the Checkout `currency`.
* Re-render from the Business response after selecting a term, rather than
  reusing amounts read from `terms[]`.
* Treat an unrecognized schedule `type` as not due at completion, and present
  the term regardless.
* Process disclosures attached to terms per
  [Warning Presentation](shopping/checkout/index.md#warning-presentation), escalating through
  `continue_url` when the rendering contract cannot be honored.

Platforms **MAY** use `type` and `due_at` for enhanced presentation — calendar
views, countdowns, reminders. This is optional; recognizing a `type` never
changes what a Platform is required to render.

Platforms **SHOULD**:

* Present terms so the Buyer can compare them before selecting, unless only one
  term is available or the Checkout is being handed off.

## Business responsibilities

Businesses **MUST**:

* Offer terms where a Checkout has a choice to present or schedules to disclose.
* Name one of the offered terms in `selected_term_id` on every response that
  carries `terms`.
* Ensure every term's schedules state, in `description` alone, when each payment
  is due.
* Ensure the selected term's schedule amounts sum to the checkout total exactly
  once.
* State any difference the selected term makes to what the purchase costs as its
  own entry in `checkout.totals`.
* Return the recomputed Checkout after a selection, including any change to
  totals, policies, messages, or eligible payment handlers.
* Report a `payment_term_changed` warning whenever a response changes the term
  in effect, whether by naming a different term or by rewriting the selected one
  in place.
* Place any content that must reach the Buyer in the disclosure `content`, not
  only in the paired policy `description`.
* Carry the accepted term onto the Order as `payment.accepted_term`, along with
  any disclosure that governed it.

Businesses **SHOULD**:

* Provide `due_at` whenever the due date is determinable at checkout.
* Keep schedule IDs stable across Checkout responses unless the schedule itself
  changes.
