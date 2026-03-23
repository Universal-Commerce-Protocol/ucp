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

# Card Network Token Credential

## Overview

The card network token credential type enables platforms to present card
network tokens (Visa VTS, Mastercard MDES, Amex Token Service) directly as
payment credentials in checkout sessions. Network tokens are opaque
credentials issued by card networks that replace the primary account number
(PAN) with a domain-restricted, cryptogram-protected token.

**Key features:**

- Present pre-provisioned network tokens directly at checkout
- Eliminate CVV collection (cryptogram structurally replaces CVC)
- Reduce PCI DSS compliance scope compared to handling raw card data
- Support all major card networks (Visa, Mastercard, Amex, Discover, JCB)

**Dependencies:**

- Checkout Capability
- Payment Handler Guide

## Credential Schema

### `card_network_token_credential.json`

The credential extends `payment_credential.json` via `allOf`:

| Field                | Type    | Required | Description                                                      |
|----------------------|---------|----------|------------------------------------------------------------------|
| `type`               | const   | Yes      | `"card_network_token"`                                           |
| `token`              | string  | Yes      | Card network token value (DPAN). Omitted from responses.         |
| `token_expiry_month` | integer | Yes      | Month of the token's expiration date (1-12)                      |
| `token_expiry_year`  | integer | Yes      | Year of the token's expiration date                              |
| `cryptogram`         | string  | No       | One-time-use cryptogram (TAVV/CAVV). Omitted from responses.     |
| `eci_value`          | string  | No       | Electronic Commerce Indicator / Security Level Indicator         |
| `name`               | string  | No       | Cardholder name. Required by some PSPs (e.g., Adyen).            |
| `token_requestor_id` | string  | No       | Token Requestor ID (TRID) from the card network                  |

**Required vs optional fields reflect PSP reality:**

- `token` and `token_expiry_*` are universally required by all PSPs
- `cryptogram` and `eci_value` are conditional: required for customer-initiated
  transactions (CIT) but may be omitted for merchant-initiated transactions
  (MIT/recurring)
- `name` is optional because only some PSPs (e.g., Adyen) require it
- `token_requestor_id` is optional; relevant when the token presenter differs
  from the provisioner

**Response omission:** `token` and `cryptogram` use `ucp_response: "omit"` to
prevent sensitive data leakage in API responses, following the pattern from
`token_credential.json`.

## Instrument Schema

### `card_network_token_instrument.json`

Network tokens are cards — they share display properties (brand, last digits,
expiry, card art) with card instruments. The instrument extends
`card_payment_instrument.json`:

```json
{
  "allOf": [
    { "$ref": "card_payment_instrument.json" },
    {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": { "const": "card_network_token" },
        "credential": {
          "$ref": "card_network_token_credential.json"
        }
      }
    }
  ]
}
```

The instrument inherits the card display properties (`brand`, `last_digits`,
`expiry_month`, `expiry_year`, `card_art`) from the card instrument schema.

### Available Instrument Variant

The schema defines `available_card_network_token_instrument` in `$defs`,
extending `available_card_payment_instrument` to inherit `constraints.brands`:

```json
{
  "$defs": {
    "available_card_network_token_instrument": {
      "allOf": [
        { "$ref": "card_payment_instrument.json#/$defs/available_card_payment_instrument" },
        {
          "type": "object",
          "properties": {
            "type": { "const": "card_network_token" }
          }
        }
      ]
    }
  }
}
```

## How Network Tokens Fit the Handler Model

Network tokens are **pre-provisioned credentials** that bypass the
tokenize/detokenize flow:

1. **Negotiation** — The business's handler declares `available_instruments`
   including `card_network_token`. The platform sees that the handler accepts
   network token instruments.
2. **Acquisition** — No tokenizer round-trip is needed. The platform constructs
   the instrument from a pre-provisioned network token, including a fresh
   cryptogram from the card network.
3. **Completion** — The platform submits the `card_network_token` instrument.
   The business's PSP processes the network token directly.

This is analogous to how wallet handlers (e.g., Google Pay, Shop Pay) work:
the platform holds a pre-provisioned opaque credential and presents it
directly.

## Usage Example

A platform presenting a pre-provisioned Visa network token at checkout:

```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_ntoken_001",
        "handler_id": "handler_merchant_psp",
        "type": "card_network_token",
        "credential": {
          "type": "card_network_token",
          "token": "4895370012003478",
          "token_expiry_month": 12,
          "token_expiry_year": 2028,
          "name": "Jane Doe",
          "cryptogram": "AJkBBkhAAAAA0YFAAAAAAAAAAA==",
          "eci_value": "05",
          "token_requestor_id": "40012345678"
        },
        "display": {
          "brand": "visa",
          "last_digits": "3478",
          "expiry_month": 12,
          "expiry_year": 2028
        },
        "selected": true
      }
    ]
  }
}
```
