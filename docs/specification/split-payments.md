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

> **Note on examples:** Instrument `type` strings used in this spec
> (`card`, `gift_card`, `store_credit`, `loyalty`) are illustrative.
> Only `card` has a normative instrument schema in the base spec
> (`card_payment_instrument.json`); the others are handler-defined.
> Credential shapes shown in examples are similarly illustrative —
> real handlers MUST publish their credential schemas. Each usage
> example below assumes a business `allowed_combinations` config that
> admits the instrument set shown; the "Example Configuration" block
> later in this doc is one such config, not the only one.

## Overview

The Split Payments extension lets buyers pay with more than one payment
instrument in a single checkout. Businesses declare the instrument
combinations they support in `allowed_combinations`.

Each instrument is submitted in one of two modes:

* **Specified-amount** (`amount` present): the platform requests a
  specific contribution.
* **Open-amount** (`amount` omitted): the business determines the
  instrument's contribution at processing time (e.g., by querying a
  gift card's available balance).

On the response, the business reports the actual amount authorized or
charged for each successfully-processed instrument in the same `amount`
field. Response `amount` is informational only; see "Response: Actual
Charges" below.

All `amount` values are expressed in `checkout.currency` minor units
(ISO 4217). Handlers using foreign-currency-denominated instruments
(e.g., a CAD gift card in a USD checkout) or non-currency instruments
like loyalty points MUST convert each instrument's contribution to the
checkout currency.

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

{{ schema_fields('types/instrument_group', 'split_payments') }}

**Matching algorithm:** a submission matches a combination if there exists
an assignment of each submitted instrument to exactly one group such that

* the instrument's `type` is in the assigned group's `types`, and
* every group's instrument count falls within its `min` and `max`
  (inclusive).

The business MAY use any algorithm to find such an assignment;
if any valid assignment exists, the combination matches.

#### Example Configuration

A business that supports (a) a card with up to 2 redeemables, (b) up to 5
gift cards alone, and (c) two credit cards:

<!-- ucp:example skip reason="illustrative business profile fragment showing allowed_combinations shape" -->
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

A split payment either completes fully or has no financial effect. If
the business cannot process an instrument with a specified amount, or
cannot achieve the final total, the business MUST return
`payment_failed` in `messages[]` and MUST void or reverse any
authorizations it made. Reversal MAY retry transiently (e.g., to work
around acquirer rate limits or a failing void call), but the buyer
MUST NOT remain charged for an incomplete split.

At the protocol layer, each request is processed independently —
split-payments state does not persist between requests. The business
MUST process each request as a fresh, full submission, without
reference to prior requests or responses.

> [!NOTE]
> **Idempotency & Correlation during Recovery Retries:**
> When retrying a partially authorized split payment with a modified set of payment instruments (e.g., replacing a declined card), the request payload changes and therefore **MUST** use a new idempotency key. Downstream systems cannot rely on the idempotency key to correlate the retry with previous partial authorizations; they must use the stable Checkout Session `id` to correlate and reconcile these distinct attempts.

**Per-instrument reporting:** when a split is incomplete or has failed,
the business MUST emit a `payment_failed` error for each failed
instrument, with `path` pointing at the instrument. Businesses MAY also
emit `info` messages for succeeded instruments to convey positive
context (e.g., "Gift card authorized for $10.00") that the platform can
surface to the buyer:

<!-- ucp:example schema=shopping/checkout extract=$.messages target=$.messages -->
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

Severity is `recoverable` because the platform's API supports collecting
a replacement instrument and re-submitting. This contrasts with
`requires_buyer_input`, which is reserved for cases where the API cannot
programmatically collect what the merchant needs.

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
instrument that was authorized or charged, reflecting the actual
contribution. For open-amount instruments (submitted without `amount`),
the business MUST derive and report the actual contribution. The
business MUST omit `amount` on all other instruments (e.g., a
provisional authorization that was voided when a later instrument
failed, or an instrument the business never attempted).

Response `amount` is informational. It conveys what the business
processed for buyer-facing UX and audit (e.g., "$10.00 charged to your
gift card"). The platform MUST NOT treat prior response `amount` values
as preserved state on subsequent requests, and the business MUST NOT
rely on the platform echoing them. Each request is fresh intent — the
platform sets `amount` to specify a contribution or omits it for
open-amount, independent of any prior response.

## Examples

### Gift Card + Credit Card

> "Pay with my gift card first, credit card for the rest."

**Inbound (buyer's selection):**

<!-- ucp:example schema=shopping/checkout op=complete direction=request extract=$.payment target=$.payment -->
```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_gc_1",
        "handler_id": "example_handler_1",
        "type": "gift_card",
        "credential": { "type": "gift_card", "token": "gc_abc123" }
      },
      {
        "id": "pi_card_1",
        "handler_id": "example_handler_1",
        "type": "card",
        "credential": { "type": "card", "token": "tok_visa_xxxx" }
      }
    ]
  }
}
```

Neither instrument includes `amount` — the business determines both.

**Outbound (completed checkout, $50 order):**

<!-- ucp:example schema=shopping/checkout extract=$.payment target=$.payment -->
```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_gc_1",
        "handler_id": "example_handler_1",
        "type": "gift_card",
        "credential": { "type": "gift_card", "token": "gc_abc123" },
        "amount": 1000
      },
      {
        "id": "pi_card_1",
        "handler_id": "example_handler_1",
        "type": "card",
        "credential": { "type": "card", "token": "tok_visa_xxxx" },
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

<!-- ucp:example schema=shopping/checkout op=complete direction=request extract=$.payment target=$.payment -->
```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_lp_1",
        "handler_id": "example_handler_1",
        "type": "loyalty",
        "credential": { "type": "loyalty", "token": "lp_abc123" },
        "amount": 500
      },
      {
        "id": "pi_card_1",
        "handler_id": "example_handler_1",
        "type": "card",
        "credential": { "type": "card", "token": "tok_visa_xxxx" }
      }
    ]
  }
}
```

The platform specifies `amount: 500` on the loyalty instrument (the
customer chose to redeem exactly 500 points). The credit card covers
the rest.

**Outbound (completed checkout, $50 order):**

<!-- ucp:example schema=shopping/checkout extract=$.payment target=$.payment -->
```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_lp_1",
        "handler_id": "example_handler_1",
        "type": "loyalty",
        "credential": { "type": "loyalty", "token": "lp_abc123" },
        "amount": 500
      },
      {
        "id": "pi_card_1",
        "handler_id": "example_handler_1",
        "type": "card",
        "credential": { "type": "card", "token": "tok_visa_xxxx" },
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

<!-- ucp:example schema=shopping/checkout op=complete direction=request extract=$.payment target=$.payment -->
```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_gc_1",
        "handler_id": "handler_gc",
        "type": "gift_card",
        "credential": { "type": "gift_card", "token": "gc_abc123" }
      },
      {
        "id": "pi_gc_2",
        "handler_id": "handler_gc",
        "type": "gift_card",
        "credential": { "type": "gift_card", "token": "gc_def456" }
      },
      {
        "id": "pi_card_1",
        "handler_id": "handler_card",
        "type": "card",
        "credential": { "type": "card", "token": "tok_visa_xxxx" }
      }
    ]
  }
}
```

**Outbound (completed checkout, $100 order):**

<!-- ucp:example schema=shopping/checkout extract=$.payment target=$.payment -->
```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_gc_1",
        "handler_id": "handler_gc",
        "type": "gift_card",
        "credential": { "type": "gift_card", "token": "gc_abc123" },
        "amount": 2500
      },
      {
        "id": "pi_gc_2",
        "handler_id": "handler_gc",
        "type": "gift_card",
        "credential": { "type": "gift_card", "token": "gc_def456" },
        "amount": 0
      },
      {
        "id": "pi_card_1",
        "handler_id": "handler_card",
        "type": "card",
        "credential": { "type": "card", "token": "tok_visa_xxxx" },
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
> credit card declines. The business voids the gift card authorization
> and signals the platform that the checkout can be retried with a
> replacement card.

**Outbound (incomplete checkout, $50 order — gift card auth was voided
per the atomic invariant):**

<!-- ucp:example skip reason="illustrative full response combining status, payment, and messages; per-subtree validation shown elsewhere" -->
```json
{
  "status": "incomplete",
  "payment": {
    "instruments": [
      {
        "id": "pi_gc_1",
        "handler_id": "example_handler_1",
        "type": "gift_card",
        "credential": { "type": "gift_card", "token": "gc_abc123" }
      },
      {
        "id": "pi_card_1",
        "handler_id": "example_handler_1",
        "type": "card",
        "credential": { "type": "card", "token": "tok_visa_xxxx" }
      }
    ]
  },
  "messages": [
    {
      "type": "info",
      "path": "$.payment.instruments[0]",
      "content": "Gift card has $10.00 available balance."
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

Both instruments omit `amount` because neither contributed funds —
the gift card was provisionally authorized and then voided when the
card declined, and the card declined outright. The `info` message
conveys the discovered gift card balance so the platform can render
accurate buyer UX; the `payment_failed` error identifies the failing
instrument with `severity: recoverable`.

**Inbound (platform re-submits with a replacement card, $50 order):**

<!-- ucp:example schema=shopping/checkout op=complete direction=request extract=$.payment target=$.payment -->
```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_gc_1",
        "handler_id": "example_handler_1",
        "type": "gift_card",
        "credential": { "type": "gift_card", "token": "gc_abc123" }
      },
      {
        "id": "pi_card_2",
        "handler_id": "example_handler_1",
        "type": "card",
        "credential": { "type": "card", "token": "tok_visa_yyyy" }
      }
    ]
  }
}
```

The platform submits a new request — the gift card is re-submitted
as open-amount and the failing card is replaced. The business processes
this as new intent.
