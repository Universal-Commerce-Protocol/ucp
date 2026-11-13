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

# Offsite Payment Handler

* **Handler Name:** `dev.ucp.common.payment.handlers.offsite`
* **Type:** Payment Handler

## Introduction

The Offsite Payment Handler covers payments that are settled **out of band**:
cash on delivery, bank transfer, pay by invoice, pay at pickup, or any other
method where money moves outside the UCP exchange.

It is a single, generic handler. Each **way to pay** is a distinct
[Offsite Payment Instrument](#offsite-payment-instrument) that the business
enumerates in `payment.instruments` of its checkout responses and describes
through the instrument's `display`. The platform presents those instruments,
submits the buyer's choice with `selected` set to `true`, and relays the
business's payment instructions. That is the full extent of its role:

* The platform collects **no credential** and never attaches one.
* The platform takes **no part** in processing or settling the payment.
* A checkout **MAY** complete before the payment is received. Whether and when
  it arrives is tracked by the business outside of UCP; this handler does not
  report settlement.

### Key Benefits

* **Zero integration surface for platforms:** no tokenizer, wallet, SDK, or
  compliance scope—platforms only render what the business returns.
* **Supports all out of band payment methods:** businesses only needs to provide
  instructions to be displayed via text, link, or image/QR Code.

### Integration Guide

| If you are a...                        | Start here                                    |
| :------------------------------------- | :-------------------------------------------- |
| **Business** accepting this handler    | [Business Integration](#business-integration) |
| **Platform** implementing this handler | [Platform Integration](#platform-integration) |

---

## Participants

| Participant  | Role                                                                                                        | Prerequisites |
| :----------- | :---------------------------------------------------------------------------------------------------------- | :------------ |
| **Business** | Declares the handler, enumerates offsite instruments, provides payment instructions, collects payment out of band | No            |
| **Platform** | Presents offsite instruments, submits the buyer's selection, displays the business's payment instructions         | No            |

No third party participates. Settlement happens between buyer and business outside UCP.

### Pattern Flow

```text
+-----------------+                                    +------------+
|  Platform       |                                    |  Business  |
+--------+--------+                                    +------+-----+
         |                                                    |
         |  1. GET /.well-known/ucp                            |
         |--------------------------------------------------->|
         |  2. Profile advertising the offsite handler         |
         |<---------------------------------------------------|
         |                                                    |
         |  3. POST /checkout-sessions                         |
         |--------------------------------------------------->|
         |  4. Checkout with offsite instruments in            |
         |     payment.instruments (one per way to pay)        |
         |<---------------------------------------------------|
         |                                                    |
         |  (buyer picks a way to pay)                         |
         |                                                    |
         |  5. POST .../complete with the chosen instrument    |
         |     selected: true, no credential                   |
         |--------------------------------------------------->|
         |  6. Completed checkout; selected instrument         |
         |     carries display.instructions                    |
         |<---------------------------------------------------|
         |                                                    |
         |  (platform shows instructions; buyer pays           |
         |   out of band; business confirms receipt)           |
```

---

## Business Integration

### Prerequisites

None beyond the ability to accept the out-of-band method and to record when
payment is received.

### Handler Configuration

Businesses advertise support for this handler in their UCP profile's
`payment_handlers` registry.

#### Handler Schema

**Schema URL:** [`schemas/payment/payment-handlers/offsite.json`](site:schemas/payment/payment-handlers/offsite.json)

A business declares exactly one instance of this handler regardless of how many
ways to pay it offers.

| Variant           | Context            | Config                       |
| :---------------- | :----------------- | :--------------------------- |
| `business_schema` | Business discovery | None                         |
| `platform_schema` | Platform discovery | None                         |
| `response_schema` | Checkout responses | None                         |

#### Example Handler Declaration

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.payment_handlers target=$.ucp.payment_handlers -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "payment_handlers": {
      "dev.ucp.common.payment.handlers.offsite": [
        {
          "id": "offsite_1",
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/payment/handlers/offsite/",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/payment/payment-handlers/offsite.json",
          "available_instruments": [
            { "type": "offsite" }
          ]
        }
      ]
    }
  }
}
```

### Offsite Payment Instrument

Businesses return one offsite instrument per way to pay in `payment.instruments`
of checkout responses, beginning with the create response. Offsite instruments describe
the business's payment methods, not a buyer's saved state, so they **MAY** be returned
on unauthenticated requests.

Each instrument carries:

| Field                            | Set by   | Purpose                                                                                                     |
| :------------------------------- | :------- | :---------------------------------------------------------------------------------------------------------- |
| `id`                             | Business | Opaque, business-scoped identifier for this way to pay. The platform echoes it to select the instrument.   |
| `handler_id`                     | Business | The `id` of the business's offsite handler declaration.                                                     |
| `type`                           | Business | Always `offsite`.                                                                                           |
| `display.description`            | Business | Buyer-facing name of the method (e.g., `Cash on Delivery`, `Bank Transfer`).                                |
| `display.instructions`           | Business | How to complete the payment. **SHOULD** be present once the instrument is selected.                         |
| `display.instructions_image_url` | Business | Optional image conveying the instructions or a QR code.                                                |
| `display.link`                   | Business | Optional link to complete the payment or view further instructions.                                         |
| `selected`                       | Platform | `true` on the instrument the buyer chose.                                                                   |

`display` is response-only. The handler schema forbids a `credential` on
offsite instruments in both directions.

{{ schema_fields('types/offsite_payment_instrument', 'payment/handlers/offsite') }}

#### Example Checkout Response

A business offering two ways to pay returns two instruments on the same
handler. Instructions **MAY** be withheld until an instrument is selected, as
with cash on delivery below, or provided up front, as with bank transfer.

<!-- ucp:example schema=shopping/checkout extract=$.payment target=$.payment -->
```json
{
  "payment": {
    "instruments": [
      {
        "id": "offsite_cod",
        "handler_id": "offsite_1",
        "type": "offsite",
        "selected": false,
        "display": {
          "description": "Cash on Delivery"
        }
      },
      {
        "id": "offsite_bank_transfer",
        "handler_id": "offsite_1",
        "type": "offsite",
        "selected": false,
        "display": {
          "description": "Bank Transfer",
          "instructions": "Transfer the order total to account DE89 3704 0044 0532 0130 00 within 3 business days. Use your order number as the payment reference."
        }
      }
    ]
  }
}
```

### Processing Payments

Upon receiving a checkout update or completion that selects an offsite
instrument, businesses **MUST**:

1. **Validate Instrument:** Confirm `instrument.handler_id` matches the
   advertised handler and `instrument.id` names an offsite instrument the
   business offered for this checkout. Reject unknown ids and any instrument
   carrying a `credential`.
2. **Ensure Idempotency:** If the request is a retry, return the previous result
   without creating a second order or payment record.
3. **Record the Obligation:** On completion, create the order with payment
   outstanding. Do not wait for funds to arrive before completing the checkout.
4. **Return Instructions:** Respond with the selected instrument carrying
   `display.instructions` (and `instructions_image_url` or `link` where useful).
5. **Collect Out of Band:** Reconcile the payment when it arrives using the
   business's own systems. This handler does not carry settlement state.

---

## Platform Integration

### Prerequisites

None. Platforms need no credentials, SDKs, or third-party registrations.

### Handler Configuration

Platforms advertise support for this handler in their UCP profile's
`payment_handlers` registry. There is no platform config.

#### Example Platform Handler Declaration

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.payment_handlers target=$.ucp.payment_handlers -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "payment_handlers": {
      "dev.ucp.common.payment.handlers.offsite": [
        {
          "id": "offsite_platform_1",
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/payment/handlers/offsite/",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/payment/payment-handlers/offsite.json",
          "available_instruments": [
            { "type": "offsite" }
          ]
        }
      ]
    }
  }
}
```

### Payment Protocol

#### Step 1: Discover Handler

The platform identifies `dev.ucp.common.payment.handlers.offsite` in the
business's UCP profile `payment_handlers` registry (from `/.well-known/ucp`)
and confirms its own profile advertises the handler.

#### Step 2: Present Offsite Instruments

The platform reads `payment.instruments` from the checkout response and
presents each `offsite` instrument to the buyer using `display.description`
(and `display.instructions`, if already present) alongside instruments from any
other handlers.

#### Step 3: Select the Instrument

The platform submits the buyer's choice by echoing the instrument's `id`,
`handler_id`, and `type` with `selected: true`. No `credential` or `display` is
sent.

<!-- ucp:example schema=payment/payment-handlers/offsite def=payment_instrument op=update direction=request -->
```json
{
  "id": "offsite_bank_transfer",
  "handler_id": "offsite_1",
  "type": "offsite",
  "selected": true
}
```

#### Step 4: Complete Checkout

<!-- ucp:example schema=shopping/checkout op=complete direction=request -->
```json
POST /checkout-sessions/{checkout_id}/complete
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json

{
  "payment": {
    "instruments": [
      {
        "id": "offsite_bank_transfer",
        "handler_id": "offsite_1",
        "type": "offsite",
        "selected": true
      }
    ]
  },
  "signals": {
    "dev.ucp.buyer_ip": "203.0.113.42",
    "dev.ucp.user_agent": "Mozilla/5.0 ..."
  }
}
```

#### Step 5: Display Instructions

The completed checkout returns the selected instrument with the business's
payment instructions. The platform **MUST** surface `display.instructions`
(and render `instructions_image_url` or offer `link` where present) and
**SHOULD** make clear that the order is placed but payment is still to be made.

<!-- ucp:example schema=payment/payment-handlers/offsite def=payment_instrument -->
```json
{
  "id": "offsite_bank_transfer",
  "handler_id": "offsite_1",
  "type": "offsite",
  "selected": true,
  "display": {
    "description": "Bank Transfer",
    "instructions": "Transfer $42.00 to account DE89 3704 0044 0532 0130 00 within 3 business days. Use ORD-1001 as the payment reference.",
    "instructions_image_url": "https://business.example/pay/ORD-1001/qr.png",
    "link": {
      "type": "payment_instructions",
      "url": "https://business.example/pay/ORD-1001",
      "title": "View payment instructions"
    }
  }
}
```

The platform does nothing further to progress the payment. Completion of the
checkout is not evidence that payment has been made; the buyer settles directly
with the business, which reconciles receipt through its own systems.

---

## Security Considerations

| Requirement                      | Description                                                                                                                                                                        |
| :------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Completion is not payment**    | Platforms **MUST NOT** treat checkout completion as evidence of payment and **MUST NOT** represent the order as paid; settlement happens outside UCP.                              |
| **Untrusted display content**    | `display.instructions`, `instructions_image_url`, and `link` are business-supplied. Platforms **MUST** sanitize text before rendering and **SHOULD** show link destinations.       |

---

## References

* **Handler Schema:** [schemas/payment/payment-handlers/offsite.json](site:schemas/payment/payment-handlers/offsite.json)
* **Instrument Schema:** [schemas/common/types/offsite_payment_instrument.json](site:schemas/common/types/offsite_payment_instrument.json)
* **Payment Handler Guide:** [guide.md](../guide.md)
* **Checkout Capability:** [Payments](../../shopping/checkout/index.md#payments)
