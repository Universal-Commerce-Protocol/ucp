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

# Split Payments Extension

* **Capability Name:** `dev.ucp.shopping.split_payments`

## Overview

The Split Payments extension lets buyers pay with more than one payment
instrument in a single checkout. Businesses declare the instrument
combinations they support in `allowed_combinations`.

Each instrument is submitted in one of two modes:

* **Specified-amount** (`amount` present): the platform requests a
  specific contribution, in ISO 4217 minor units.
* **Open-amount** (`amount` omitted): the business determines the
  instrument's contribution at processing time (e.g., by querying a
  gift card's available balance).

Instruments are submitted in **allocation priority order** — the first
instrument gets first claim on the checkout total, the second gets next
claim, and so on. The business MAY process payment authorizations in
any order for operational reasons (e.g., gift cards before open-loop
cards to minimize reversal costs); array order governs amount
allocation, not processing sequence.

## Schema

### Payment Instrument (Split Payments)

When this capability is active, each payment instrument in
`checkout.payment.instruments` gains an optional `amount` field.

{{ extension_schema_fields('split_payments.json#/$defs/payment_instrument', 'split_payments') }}

## Configuration

Businesses declare split payments configuration in their profile.

### Business Profile

{{ schema_fields('types/business_split_payments_config', 'split_payments') }}

#### `allowed_combinations`

An array of valid instrument combinations. Each combination is an array of
**instrument groups** -- constraints that together define one valid way to
split a payment.

A set of instruments is valid if it matches **any** combination in the array.

#### Instrument Group

Each group within a combination defines a "slot" that accepts certain
instrument types:

| Field | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `types` | string[] | *(required)* | Instrument types accepted by this group (OR logic). Any listed type qualifies. |
| `min` | integer | `0` | Minimum number of instruments required from this group. |
| `max` | integer | `1` | Maximum number of instruments allowed from this group. |

**Matching algorithm:** for a given combination, each submitted instrument must
be assignable to exactly one group whose `types` list includes that
instrument's type. After assignment, every group must have between `min` and
`max` instruments (inclusive). If all constraints are satisfied, the
combination matches.

#### Example Configuration

A business that supports (a) a card with up to 2 redeemables, (b) up to 5
gift cards alone, and (c) two credit cards:

```json
{
  "capabilities": [{
    "dev.ucp.shopping.split_payments": [
      {
        "version": "2026-01-23",
        "config": {
          "allowed_combinations": [
            [
              { "types": ["card"], "min": 1, "max": 1 },
              { "types": ["gift_card", "store_credit"], "max": 2 }
            ],
            [
              { "types": ["gift_card"], "min": 1, "max": 5 }
            ],
            [
              { "types": ["card"], "min": 2, "max": 2 }
            ]
          ]
        }
      }
    ]
  }]
}
```

Reading each combination:

1. **Card + redeemables**: Exactly 1 card (required), plus up to 2 instruments
   that are either gift cards or store credit (optional). Valid payments: card
   alone, card + gift card, card + store credit, card + 2 gift cards, etc.
2. **Gift cards only**: 1 to 5 gift cards with no other instrument types.
3. **Two cards**: Exactly 2 credit/debit cards.

## Using Split Payments

### Instrument Processing Model

1. The platform submits instruments in the `payment.instruments` array
   in allocation priority order.
2. The business MUST derive a contribution for each instrument, in
   array order:
   * **Specified-amount**: the business MUST authorize for the stated
     `amount`.
   * **Open-amount**: the business determines the
     contribution — typically the instrument's full available balance,
     up to the remaining checkout total after all prior contributions.
     A zero available balance is a valid $0 contribution, not a failure.

### Error Handling

A split payment either completes fully or has no financial effect. If the business cannot process an instrument with a specified
amount, or cannot achieve the final total, the business MUST return
`payment_failed` in `messages[]` and MUST ensure all previously
successful authorizations are voided or reversed. This is an
eventual-consistency requirement: the reversal MAY happen asynchronously
(e.g., to retry a failing void or work around acquirer rate limits, or
to wait and see if the buyer re-submits partially captured instruments),
but the buyer MUST NOT remain charged for an incomplete split after
checkout.

**Per-instrument reporting:** when a split is incomplete or has failed,
the business MUST emit a `payment_failed` error for each failed
instrument, with `path` pointing at the instrument. Businesses MAY also
emit `info` messages for succeeded instruments to convey positive
context (e.g., "Gift card authorized for $10.00") that the platform can
surface to the buyer:

```json
{
  "messages": [
    {
      "type": "info",
      "path": "$.payment.instruments[0]",
      "content": "Gift card authorized for $10.00."
    },
    {
      "type": "error",
      "code": "payment_failed",
      "path": "$.payment.instruments[1]",
      "severity": "recoverable",
      "content": "Card declined — insufficient funds."
    }
  ]
}
```

Error conditions:

* If any instrument cannot be processed (invalid credentials, fraud flag,
  hard decline, expired, insufficient funds), the business MUST return an error. For
  open-amount instruments, a zero available balance is not a failure.
* If the checkout total cannot be reached after applying all submitted
  instruments, the business MUST return an error.
* If the sum of all specified `amount` values exceeds the
  checkout total, the business MUST return an error.
* If the submitted instruments did not match any valid `allowed_combinations`, the business MUST return an error.

### Response: Actual Charges

On the checkout response, the business MUST set `amount` on every
instrument to reflect the actual amount that will be charged. This includes
instruments submitted without `amount`: the business MUST derive their
actual contribution and return it.

## Examples

### Gift Card + Credit Card

> "Pay with my gift card first, credit card for the rest."

**Inbound (buyer's selection):**

```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_gc_1",
        "handler_id": "example_handler_1",
        "type": "gift_card",
        "credential": { "token": "gc_abc123" }
      },
      {
        "id": "pi_card_1",
        "handler_id": "example_handler_1",
        "type": "card",
        "credential": { "token": "tok_visa_xxxx" }
      }
    ]
  }
}
```

Neither instrument includes `amount` — the business determines both.

**Outbound (completed checkout, $50 order):**

```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_gc_1",
        "handler_id": "example_handler_1",
        "type": "gift_card",
        "credential": { "token": "gc_abc123" },
        "amount": 1000
      },
      {
        "id": "pi_card_1",
        "handler_id": "example_handler_1",
        "type": "card",
        "credential": { "token": "tok_visa_xxxx" },
        "amount": 4000
      }
    ]
  }
}
```

The business queried the gift card's balance ($10), charged it in full,
and charged the credit card for the remaining $40.

### Loyalty Points + Credit Card

> "Use 500 of my 2000 loyalty points ($5 equivalent), credit card for the rest."

**Inbound (buyer's selection):**

```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_lp_1",
        "handler_id": "example_handler_1",
        "type": "loyalty",
        "credential": { "token": "lp_abc123" },
        "amount": 500
      },
      {
        "id": "pi_card_1",
        "handler_id": "example_handler_1",
        "type": "card",
        "credential": { "token": "tok_visa_xxxx" }
      }
    ]
  }
}
```

The platform specifies `amount: 500` on the loyalty instrument (the
customer chose to redeem exactly 500 points). The credit card covers the rest.

**Outbound (completed checkout, $50 order):**

```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_lp_1",
        "handler_id": "example_handler_1",
        "type": "loyalty",
        "credential": { "token": "lp_abc123" },
        "amount": 500
      },
      {
        "id": "pi_card_1",
        "handler_id": "example_handler_1",
        "type": "card",
        "credential": { "token": "tok_visa_xxxx" },
        "amount": 4500
      }
    ]
  }
}
```

The business charged the loyalty points for $5 as requested, and the
credit card covers the remaining $45.

### Gift Card + Gift Card + Credit Card (mixed amounts)

> "Use both gift cards, credit card for the rest."

**Inbound:**

```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_gc_1",
        "handler_id": "handler_gc",
        "type": "gift_card",
        "credential": { "token": "gc_abc123" }
      },
      {
        "id": "pi_gc_2",
        "handler_id": "handler_gc",
        "type": "gift_card",
        "credential": { "token": "gc_def456" }
      },
      {
        "id": "pi_card_1",
        "handler_id": "handler_card",
        "type": "card",
        "credential": { "token": "tok_visa_xxxx" }
      }
    ]
  }
}
```

**Outbound (completed checkout, $100 order):**

```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_gc_1",
        "handler_id": "handler_gc",
        "type": "gift_card",
        "credential": { "token": "gc_abc123" },
        "amount": 2500
      },
      {
        "id": "pi_gc_2",
        "handler_id": "handler_gc",
        "type": "gift_card",
        "credential": { "token": "gc_def456" },
        "amount": 0
      },
      {
        "id": "pi_card_1",
        "handler_id": "handler_card",
        "type": "card",
        "credential": { "token": "tok_visa_xxxx" },
        "amount": 7500
      }
    ]
  }
}
```

The first gift card had a $25 balance (charged in full). The second gift
card had a $0 balance — this is not an error, it simply contributes
nothing. The credit card covers the remaining $75.

### Partial Failure with Recovery

> "Pay with my gift card first, credit card for the rest." — but the
> credit card declines. The business holds the gift card authorization
> and signals the platform to resubmit with a replacement card.

**Outbound (incomplete checkout, $50 order):**

```json
{
  "status": "incomplete",
  "payment": {
    "instruments": [
      {
        "id": "pi_gc_1",
        "handler_id": "example_handler_1",
        "type": "gift_card",
        "credential": { "token": "gc_abc123" },
        "amount": 1000
      },
      {
        "id": "pi_card_1",
        "handler_id": "example_handler_1",
        "type": "card",
        "credential": { "token": "tok_visa_xxxx" },
        "amount": 0
      }
    ]
  },
  "messages": [
    {
      "type": "info",
      "path": "$.payment.instruments[0]",
      "content": "Gift card authorized for $10.00."
    },
    {
      "type": "error",
      "code": "payment_failed",
      "path": "$.payment.instruments[1]",
      "severity": "recoverable",
      "content": "Card declined — insufficient funds."
    }
  ]
}
```

The business charged the gift card for $10 (held) and the card declined.
`severity: recoverable` tells the platform it can resubmit with a
replacement card; the gift card auth remains held until the platform
either completes the split or abandons the checkout (at which point the
gift card is reversed per the eventual-consistency rule).
Outstanding amount: $50 − $10 = $40.
