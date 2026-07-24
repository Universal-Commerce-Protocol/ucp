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

* `available_terms[]` — checkout-wide payment terms the buyer can choose from.
* `instruments[].term_refs[]` — selection of one term and optional assignment
  of instruments to schedules within that term.

It also adds `order.payment.terms[]`, containing exactly one complete snapshot
of the accepted `available_terms[]` entry. Payment handlers can use
`available_instruments[].constraints.term_refs[]` to describe which terms or
schedules an instrument supports.

## Schema

### Payment

When this capability is active, `checkout.payment` is extended with available
terms and term-aware payment instruments.

{{ extension_schema_fields('payment_terms.json#/$defs/payment', 'payment_terms') }}

### Entities

#### Available Payment Term

{{ schema_fields('types/available_payment_term', 'payment_terms') }}

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

An `immediate` schedule **MUST** omit `due_at`; a `deferred` schedule **MUST**
include a non-empty `due_at`. The shared Schedule fields are:

* `anchor_date` — RFC 3339 reference point. If omitted, the anchor is the
  instant successful checkout completion creates the order.
* `offset` — ISO 8601 duration from the anchor to the first occurrence.
* `interval` — ISO 8601 duration between recurring occurrences.
* `occurrences` — finite number of occurrences; **MUST** be present when
  `interval` is present.

Each payment schedule has `totals[]`. For a recurring schedule, those totals
apply to each occurrence. Expanding every occurrence, the sum of schedule
`total` entries **MUST** equal the checkout `total` exactly once.

Schedules settle only the current checkout; they do not create future purchases,
orders, renewals, or fulfillment obligations. They disclose payment timing but
do not themselves define credential storage, future-charge authorization,
processor capture behavior, or mandate requirements.

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

For instrument assignment, every reference **MUST** include `id`, and all
assignment references in one checkout **MUST** identify the same available
term. `schedule_id` and `schedule_type` only narrow that selected term. Handler
constraints may omit `id` to express support across terms. Empty references are
invalid in both contexts.

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
multiple instruments share a schedule. A fixed contribution **MUST** resolve to
exactly one schedule. Contributions to each schedule **MUST** equal that
schedule's expanded total, and every schedule **MUST** be covered by at least
one eligible instrument.

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

## Operations

### Selecting and assigning payment terms

The buyer selects one checkout-wide term through
`payment.instruments[].term_refs[]`. Every referenced `id` **MUST** match one
`payment.available_terms[].id`; referenced schedules **MUST** belong to that
term, and every schedule **MUST** be completely funded by eligible instruments.

Before authorization, the business **MUST** return a Checkout response containing
the accepted instruments and their `term_refs`. A change to the selected term or
schedule assignment requires a new Checkout response and renewed authorization.
When AP2 is active, these accepted assignments are part of the Checkout state
bound by the mandate.

### Persisting terms on orders

When this extension is active, a completed Order **MUST** include exactly one
`payment.terms[]` entry. That entry **MUST** equal the selected
`available_terms[]` object, including its schedules and totals.

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
      "schedules": [
        {
          "id": "sched_first_night",
          "type": "immediate",
          "totals": [
            { "type": "subtotal", "amount": 30000 },
            { "type": "total", "amount": 30000 }
          ]
        },
        {
          "id": "sched_check_in_balance",
          "type": "deferred",
          "due_at": {
            "anchor_date": "2026-09-01T15:00:00-07:00"
          },
          "totals": [
            { "type": "subtotal", "amount": 90000 },
            { "type": "total", "amount": 90000 }
          ]
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
        {
          "id": "pt_first_night_balance",
          "schedule_id": "sched_first_night"
        }
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
        {
          "id": "pt_first_night_balance",
          "schedule_id": "sched_check_in_balance"
        }
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
  "schedules": [
    {
      "id": "sched_installment_1",
      "type": "immediate",
      "totals": [
        { "type": "subtotal", "amount": 2500 },
        { "type": "total", "amount": 2500 }
      ]
    },
    {
      "id": "sched_installments_2_to_4",
      "type": "deferred",
      "due_at": {
        "offset": "P2W",
        "interval": "P2W",
        "occurrences": 3
      },
      "totals": [
        { "type": "subtotal", "amount": 2500 },
        { "type": "total", "amount": 2500 }
      ]
    }
  ]
}
```

The deferred schedule has three occurrences. Its totals apply to each
occurrence, so the term expands to four payments of $25 each.

### Order with accepted payment terms

The Order carries the complete accepted term from the originating Checkout.

<!-- ucp:example schema=shopping/payment_terms def=dev.ucp.shopping.order op=read direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order": [
        { "version": "{{ ucp_version }}" }
      ],
      "dev.ucp.shopping.payment_terms": [
        { "version": "{{ ucp_version }}" }
      ]
    }
  },
  "id": "order_123",
  "checkout_id": "checkout_123",
  "permalink_url": "https://business.example.com/orders/123",
  "line_items": [],
  "fulfillment": {},
  "currency": "USD",
  "totals": [
    { "type": "subtotal", "amount": 10000 },
    { "type": "total", "amount": 10000 }
  ],
  "payment": {
    "instruments": [
      {
        "id": "pi_gift_card",
        "type": "gift_card",
        "amount": 2500,
        "display": {
          "description": "Gift card",
          "last_digits": "9821"
        },
        "term_refs": [
          {
            "id": "pt_pay_in_4",
            "schedule_id": "sched_installment_1"
          }
        ]
      },
      {
        "id": "pi_installment_card",
        "type": "card",
        "billing_address": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "display": {
          "brand": "visa",
          "last_digits": "4242",
          "description": "Visa ending in 4242"
        },
        "term_refs": [
          {
            "id": "pt_pay_in_4",
            "schedule_id": "sched_installments_2_to_4"
          }
        ]
      }
    ],
    "terms": [
      {
        "id": "pt_pay_in_4",
        "name": "Pay in 4",
        "schedules": [
          {
            "id": "sched_installment_1",
            "type": "immediate",
            "totals": [
              { "type": "subtotal", "amount": 2500 },
              { "type": "total", "amount": 2500 }
            ]
          },
          {
            "id": "sched_installments_2_to_4",
            "type": "deferred",
            "due_at": {
              "offset": "P2W",
              "interval": "P2W",
              "occurrences": 3
            },
            "totals": [
              { "type": "subtotal", "amount": 2500 },
              { "type": "total", "amount": 2500 }
            ]
          }
        ]
      }
    ]
  }
}
```

## Platform responsibilities

Platforms SHOULD:

* Present available payment terms in a clear, buyer-understandable format.
* Show amounts and due dates for each schedule, including future payments.
* Validate term and schedule references plus instrument constraints before submitting payment.
* Tolerate unknown schedule types and surface clear recovery guidance when a
  selected instrument cannot satisfy them.

## Business responsibilities

Businesses MUST:

* Provide at least one checkout-wide payment term when the extension is active.
* Ensure expanded schedule totals cover the checkout total exactly once.
* Validate that all instrument assignments select the same term and completely
  fund its schedules.
* Include that complete accepted term on the resulting Order.
* Honor payment instrument constraints declared by payment handlers.

Businesses SHOULD:

* Include clear names and descriptions for buyer-facing terms.
* Include at least one immediate pay-now term for simple checkouts when
  supported.
* Use stable schedule IDs so platforms can assign instruments precisely.
