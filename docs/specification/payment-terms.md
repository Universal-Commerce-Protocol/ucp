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

The Payment Terms extension lets a business describe when payment is due for a
checkout. A buyer-facing **payment term** is composed of one or more **payment
schedules**. Each schedule can be due immediately, due at a future date, or due
on a recurring cadence.

This is intended for payment timing, not for changing what is being purchased.
For example, a lodging checkout can offer one term where the first night is paid
at booking time and the remaining stay is paid at check-in.

This extension adds to `checkout.payment`:

* `available_terms[]` — payment terms the buyer can choose from.
* `terms[]` — the buyer's selected term for specific line items.
* `instruments[].term_refs[]` — optional assignment of instruments to terms or
  schedules.

Payment handlers can also use `available_instruments[].constraints.term_refs[]`
to describe which terms or schedules an instrument supports.

## Schema

### Payment

When this capability is active, `checkout.payment` is extended with available
and selected payment terms.

{{ extension_schema_fields('payment_terms.json#/$defs/payment', 'payment_terms') }}

### Entities

#### Available Payment Term

{{ schema_fields('types/available_payment_term', 'payment_terms') }}

#### Payment Term

{{ schema_fields('types/payment_term', 'payment_terms') }}

#### Payment Schedule

{{ schema_fields('types/payment_schedule', 'payment_terms') }}

#### Schedule

{{ schema_fields('types/schedule', 'payment_terms') }}

#### Schedule Type

{{ schema_fields('types/schedule_type', 'payment_terms') }}

#### Entity Reference

{{ schema_fields('types/entity_ref', 'payment_terms') }}

#### Available Payment Instrument (Payment Terms)

{{ extension_schema_fields('payment_terms.json#/$defs/available_payment_instrument', 'payment_terms') }}

#### Payment Instrument (Payment Terms)

{{ extension_schema_fields('payment_terms.json#/$defs/payment_instrument', 'payment_terms') }}

## Payment schedules

Payment schedules use `type` as an open string vocabulary. Well-known values are:

| Type | Meaning |
| :--- | :------ |
| `immediate` | Payment is due when checkout is completed. |
| `deferred` | Payment is due after checkout completion, according to `due_at`. |

Businesses MAY use additional values. Platforms MUST tolerate unknown schedule
types and either apply business-specific support or surface clear validation
messages when a selected payment instrument cannot satisfy them.

The `due_at` field uses the shared Schedule type:

* `anchor_date` — RFC 3339 reference point. If omitted, order time is the
  default anchor.
* `offset` — ISO 8601 duration from `anchor_date` to the first occurrence.
* `interval` — ISO 8601 duration between recurring occurrences.
* `occurrences` — number of occurrences. Omit for an indefinite recurring
  schedule.

Each payment schedule can specify either:

* `percentage` — percentage of the selected term's line-item total due for each
  occurrence.
* `amount` — fixed amount in the checkout currency's minor unit due for each
  occurrence.

If neither `percentage` nor `amount` is present, the schedule covers the
remaining balance for the selected term. For recurring schedules,
`percentage` and `amount` apply to each occurrence.

## Instrument constraints

Payment handlers declare term and schedule support with
`available_instruments[].constraints.term_refs`. Each `term_refs[]` entry is an
Entity Reference interpreted in the payment terms context.

References can target:

* **Payment term ID** — `{ "id": "pt_deposit_balance" }` applies to all
  schedules in that term.
* **Payment schedule ID** — `{ "schedule_id": "balance_at_check_in" }` applies
  to matching schedules.
* **Schedule type** — `{ "schedule_type": "immediate" }` applies to all
  schedules with that timing class.
* **Compound refs** — `{ "id": "pt_deposit_balance", "schedule_type":
  "immediate" }` applies only to schedules that match both selectors.

Businesses SHOULD make payment schedule IDs unique across
`payment.available_terms[]` when platforms are expected to reference schedules
by `schedule_id` alone. If the same schedule ID appears in more than one term,
a `schedule_id`-only reference matches every schedule with that ID; include `id`
to scope the match to a specific payment term.

<!-- ucp:example schema=shopping/payment_terms def=available_payment_instrument -->
```json
{
  "type": "gift_card",
  "constraints": {
    "term_refs": [
      { "schedule_type": "immediate" }
    ]
  }
}
```

When the [Split Payments](split-payments.md) extension is also active,
instruments may include an `amount` field to specify a fixed contribution when
multiple instruments share a schedule.

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
          "extends": "dev.ucp.shopping.checkout",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/payment-terms",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/payment_terms.json"
        }
      ]
    }
  }
}
```

## Operations

### Selecting payment terms

The buyer selects payment terms by providing `payment.terms[]`. Each selected
term specifies:

* `id` — the selected `available_terms[].id`.
* `line_item_ids` — line items to apply the selected term to.

Invariants:

* Every line item that requires payment term selection is covered by exactly one
  selected term.
* Selected `line_item_ids` are a subset of the corresponding
  `available_terms[].line_item_ids`.
* Selected term IDs reference valid `available_terms[].id` values.
* The expanded schedule amounts for a selected term cover that selected term's
  payable total exactly once.

### Assigning instruments to schedules

Payment instruments can include `term_refs` to declare which terms or schedules
they pay for. These references use the same payment terms context and AND
matching semantics as handler constraints. If omitted, the business applies the
instrument according to the selected terms and the payment handler's
constraints.

When multiple instruments are assigned to the same schedule, the
[Split Payments](split-payments.md) extension defines how fixed contributions
are expressed.

## Examples

### Lodging deposit and balance at check-in

> Pay the first night at booking time and the rest of the stay at check-in.

**Checkout response fragment:**

<!-- ucp:example schema=shopping/payment_terms def=payment op=read direction=response -->
```json
{
  "available_terms": [
    {
      "id": "pt_first_night_balance",
      "name": "First night now, balance at check-in",
      "description": "Pay $300 now and $900 when you check in.",
      "line_item_ids": ["li_stay"],
      "schedules": [
        {
          "id": "sched_first_night",
          "type": "immediate",
          "amount": 30000
        },
        {
          "id": "sched_check_in_balance",
          "type": "deferred",
          "due_at": {
            "anchor_date": "2026-09-01T15:00:00-07:00"
          },
          "amount": 90000
        }
      ]
    }
  ]
}
```

**Complete request payment fragment:**

<!-- ucp:example schema=shopping/payment_terms def=payment op=complete direction=request -->
```json
{
  "terms": [
    {
      "id": "pt_first_night_balance",
      "line_item_ids": ["li_stay"]
    }
  ],
  "instruments": [
    {
      "id": "pi_card_1",
      "handler_id": "handler_1",
      "type": "card",
      "credential": {
        "type": "token",
        "token": "tok_visa_xxxx"
      },
      "term_refs": [
        { "id": "pt_first_night_balance" }
      ]
    }
  ]
}
```

The card is used for both the immediate first-night payment and the deferred
check-in balance.

### Different instruments for immediate and deferred schedules

> Use a gift card for the deposit, and a card for the check-in balance.

**Complete request payment fragment:**

<!-- ucp:example schema=shopping/payment_terms def=payment op=complete direction=request -->
```json
{
  "terms": [
    {
      "id": "pt_first_night_balance",
      "line_item_ids": ["li_stay"]
    }
  ],
  "instruments": [
    {
      "id": "pi_gift_card_1",
      "handler_id": "handler_1",
      "type": "gift_card",
      "credential": {
        "type": "token",
        "token": "gc_abc123"
      },
      "term_refs": [
        { "schedule_id": "sched_first_night" }
      ]
    },
    {
      "id": "pi_card_1",
      "handler_id": "handler_1",
      "type": "card",
      "credential": {
        "type": "token",
        "token": "tok_visa_xxxx"
      },
      "term_refs": [
        { "schedule_id": "sched_check_in_balance" }
      ]
    }
  ]
}
```

If both instruments contribute to the same schedule, use the
[Split Payments](split-payments.md) extension to specify fixed contribution
amounts.

### Installments

> Pay 25% today, then 25% every two weeks for three more payments.

<!-- ucp:example schema=shopping/payment_terms def=available_payment_term -->
```json
{
  "id": "pt_pay_in_4",
  "name": "Pay in 4",
  "line_item_ids": ["li_order"],
  "schedules": [
    {
      "id": "sched_installment_1",
      "type": "immediate",
      "percentage": 25
    },
    {
      "id": "sched_installments_2_to_4",
      "type": "deferred",
      "due_at": {
        "offset": "P2W",
        "interval": "P2W",
        "occurrences": 3
      },
      "percentage": 25
    }
  ]
}
```

The deferred schedule has three occurrences. Because `percentage` applies to
each occurrence, the selected term expands to four payments of 25% each.

## Platform responsibilities

Platforms SHOULD:

* Present available payment terms in a clear, buyer-understandable format.
* Show amounts and due dates for each schedule, including future payments.
* Validate selected terms and instrument constraints before submitting payment.
* Tolerate unknown schedule types and surface clear recovery guidance when a
  selected instrument cannot satisfy them.

## Business responsibilities

Businesses MUST:

* Provide at least one payment term that covers all payable line items when the
  extension is active.
* Ensure selected schedule amounts cover each selected term's payable total
  exactly once.
* Honor payment instrument constraints declared by payment handlers.

Businesses SHOULD:

* Include clear names and descriptions for buyer-facing terms.
* Include at least one immediate pay-now term for simple checkouts when
  supported.
* Use stable schedule IDs so platforms can assign instruments precisely.
