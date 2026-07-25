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

# Shared Payment Token Payment Handler

* **Handler Name:** `dev.ucp.payment.shared_payment_token`
* **Type:** Payment Handler Specification Proposal
* **Status:** Working Draft proposal

## Introduction

This specification proposes a **Shared Payment Token (SPT)** payment handler for
UCP. A platform
discovers that a business accepts scoped SPT checkout credentials, obtains buyer
consent or applies a delegated allowance, requests a token from an SPT-capable
issuer, and submits that token at checkout.

The token is a provider-neutral checkout instrument. It is scoped,
short-lived, single-use, and processor-redeemable. The handler keeps UCP-native
field names while preserving the same SPT contract around amount, currency,
business identity, checkout binding, processor route, idempotency, consent or
delegated allowance, and replay protection.

The token is not a raw PAN, CVC, network-token cryptogram, wallet secret, bank
credential, or PSP secret. It is an opaque, time-limited checkout instrument
bound to a business, checkout, amount, currency, processor route, and
idempotency key.

This example is adjacent to tokenization handlers, but the platform does not
submit raw card credentials for tokenization. The SPT issuer already holds or
can access the buyer's funding source under an approved relationship. The
platform requests a checkout token for a specific UCP transaction.

This proposal defines a UCP-governed handler name and interoperable handler
contract. It does **not** change UCP core schemas, transports, or checkout state
machines. Implementations continue to use the existing `payment_handlers`
registry and `PaymentHandler` schema.

### Key Benefits

* **Portable checkout instrument:** The platform can submit one credential shape
  while the business keeps its configured processor route.
* **Reduced credential exposure:** The platform and agent never receive raw
  funding credentials.
* **Bounded agentic checkout:** Each token is scoped to one checkout context,
  amount, currency, business identity, and expiration window.

---

## Participants

| Participant | Role | Prerequisites |
| :---------- | :--- | :------------ |
| **Business** | Advertises the handler and processes the returned token directly or through a PSP. | Business identity and configured processor binding. |
| **Platform** | Discovers the handler, obtains consent or delegated allowance, requests the token, and submits it at checkout. | Platform identity and access to an SPT issuer. |
| **SPT Issuer** | Stores or resolves funding sources, evaluates consent and binding, issues scoped tokens, and verifies redemption. | Credential service, policy engine, and processor adapters. |
| **PSP / Processor** | Authorizes or captures the final payment using the business's configured route. | Existing business processing relationship. |

### Pattern Flow

```text
+----------+        +------------+        +----------------+        +----------+
| Platform |        | SPT Issuer |        |    Business    |        |   PSP    |
+----+-----+        +-----+------+        +-------+--------+        +----+-----+
     |                    |                       |                      |
     | 1. Discover handler|                       |                      |
     |<-------------------------------------------|                      |
     |                    |                       |                      |
     | 2. Request scoped token                    |                      |
     |------------------->|                       |                      |
     |                    | 3. Opaque token       |                      |
     |<-------------------|                       |                      |
     |                    |                       |                      |
     | 4. Submit checkout with token              |                      |
     |------------------------------------------->|                      |
     |                    |                       | 5. Verify/process    |
     |                    |<--------------------->|--------------------->|
     |                    |                       |                      |
     | 6. Checkout result |                       |                      |
     |<-------------------------------------------|                      |
```

---

## Configuration

The business advertises this handler in its UCP profile's `payment_handlers`
registry. The checkout response remains authoritative for the final amount,
currency, processor route, and accepted token constraints.

### Business Config

| Field | Type | Required | Description |
| :---- | :--- | :------- | :---------- |
| `environment` | string | Yes | API environment, such as `sandbox` or `production`. |
| `business_id` | string | Yes | Business identifier. |
| `credential_provider` | string | Yes | Base URL for token issuance and verification. |
| `processing.mode` | string | Yes | Processing mode, such as `issuer_adapter` or `processor_forwarded`. |
| `processing.supported_processors` | array | Yes | Processor routes the business can use for this handler. |
| `binding.checkout_id_required` | boolean | Yes | Whether tokens must be bound to a checkout identifier. |
| `binding.amount_required` | boolean | Yes | Whether tokens must be bound to final amount and currency. |

#### Example Business Handler Declaration

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.payment_handlers target=$.ucp.payment_handlers -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "payment_handlers": {
      "dev.ucp.payment.shared_payment_token": [
        {
          "id": "spt_primary",
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shared-payment-token-payment-handler",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/payment_handler.json",
          "available_instruments": [
            {
              "type": "dev.ucp.payment.shared_payment_token",
              "constraints": {
                "funding_source_classes": ["card", "network_token", "wallet"],
                "currencies": ["USD"],
                "single_use": true,
                "max_ttl_seconds": 900
              }
            }
          ],
          "config": {
            "environment": "production",
            "business_id": "business_123",
            "credential_provider": "https://processor.example",
            "processing": {
              "mode": "issuer_adapter",
              "supported_processors": ["examplepay"],
              "processor_binding_required": true
            },
            "binding": {
              "checkout_id_required": true,
              "amount_required": true,
              "currency_required": true,
              "idempotency_key_required": true
            }
          }
        }
      ]
    }
  }
}
```

### Response Config

The business checkout response narrows the discovered handler configuration for
the current checkout.

| Field | Type | Required | Description |
| :---- | :--- | :------- | :---------- |
| `business_id` | string | Yes | Business identifier for this checkout. |
| `processor_binding` | object | Conditional | Required when the token must be redeemable only through one processor account. |
| `credential_acquisition.url` | string | Yes | Endpoint used by the platform to request a token. |
| `binding.checkout_id` | string | Yes | Checkout identifier to bind into the issued token. |
| `binding.amount` | object | Yes | Final amount and currency to bind. |

#### Example Response Config

<!-- ucp:example schema=payment_handler def=response_schema -->
```json
{
  "id": "spt_primary",
  "version": "{{ ucp_version }}",
  "available_instruments": [
    {
      "type": "dev.ucp.payment.shared_payment_token",
      "constraints": {
        "funding_source_classes": ["card", "network_token"],
        "currencies": ["USD"],
        "single_use": true,
        "max_ttl_seconds": 300
      }
    }
  ],
  "config": {
    "environment": "production",
    "business_id": "business_123",
    "processor_binding": {
      "processor": "examplepay",
      "merchant_account_id": "acct_merchant_123"
    },
    "credential_acquisition": {
      "url": "https://processor.example/ucp/shared-payment-tokens"
    },
    "binding": {
      "checkout_id": "checkout_abc123",
      "amount": {
        "value": "12.00",
        "currency": "USD"
      },
      "idempotency_key_required": true
    }
  }
}
```

---

## Platform Integration

### Prerequisites

Before using this handler, platforms must:

1. Register with an SPT issuer or wallet to obtain a platform identity.
2. Support a buyer consent or delegated allowance flow.
3. Present checkout details to the buyer or agent policy before token issuance.
4. Store and submit only the opaque checkout token returned by the issuer.
5. Handle token expiration and refresh by repeating the acquisition flow.

### Credential Acquisition

The platform requests a token for a specific checkout. The exact API is defined
by the handler provider, but requests should include the authoritative checkout
binding from the business response.

<!-- ucp:example skip reason="handler provider API, not UCP payload" -->
```json
POST /ucp/shared-payment-tokens
Content-Type: application/json

{
  "handler_id": "spt_primary",
  "instrument_type": "dev.ucp.payment.shared_payment_token",
  "business_id": "business_123",
  "platform_id": "platform_456",
  "funding_source_id": "funding_source_789",
  "consent": {
    "type": "delegated_allowance",
    "allowance_id": "allow_abc123"
  },
  "binding": {
    "checkout_id": "checkout_abc123",
    "amount": {
      "value": "12.00",
      "currency": "USD"
    },
    "processor": "examplepay",
    "merchant_account_id": "acct_merchant_123",
    "idempotency_key": "idem_01J4ZTKC49R2AK7Y4M6GPJCMJ2"
  }
}
```

**Response:**

<!-- ucp:example skip reason="handler provider API, not UCP payload" -->
```json
{
  "instrument": {
    "type": "dev.ucp.payment.shared_payment_token",
    "handler_id": "spt_primary",
    "credential_id": "spt_01J4ZTM7JVAF5J29VE1S58F7RC",
    "token": "spt_live_opaque_value",
    "display": {
      "funding_source_type": "card",
      "brand": "visa",
      "last4": "4242"
    },
    "binding_proof": "sptproof_opaque_value",
    "expires_at": "2026-07-24T18:05:00Z",
    "single_use": true
  }
}
```

### Checkout Submission

The platform submits the returned instrument to the business checkout endpoint.
The business treats the token as a payment credential for the advertised handler
and verifies the same binding used during acquisition.

<!-- ucp:example schema=checkout def=complete_request -->
```json
{
  "checkout_id": "checkout_abc123",
  "payment": {
    "handler": "dev.ucp.payment.shared_payment_token",
    "instrument": {
      "type": "dev.ucp.payment.shared_payment_token",
      "handler_id": "spt_primary",
      "credential_id": "spt_01J4ZTM7JVAF5J29VE1S58F7RC",
      "token": "spt_live_opaque_value",
      "binding_proof": "sptproof_opaque_value"
    }
  }
}
```

---

## Business Processing

Upon receiving this handler's instrument, businesses **MUST**:

1. Confirm the handler id matches a configured handler.
2. Validate that the checkout id, amount, currency, business id, and processor
   binding match the response configuration used for token acquisition.
3. Ensure the idempotency key has not already been used with a different
   checkout fingerprint.
4. Submit the token to the SPT issuer for verification and processing, or
   forward it to an approved PSP integration that can redeem the token.
5. Return the finalized checkout result.

### Verification Request

<!-- ucp:example skip reason="handler provider API, not UCP payload" -->
```json
POST /ucp/shared-payment-tokens/verify
Content-Type: application/json

{
  "credential_id": "spt_01J4ZTM7JVAF5J29VE1S58F7RC",
  "token": "spt_live_opaque_value",
  "binding_proof": "sptproof_opaque_value",
  "binding": {
    "checkout_id": "checkout_abc123",
    "amount": {
      "value": "12.00",
      "currency": "USD"
    },
    "business_id": "business_123",
    "processor": "examplepay",
    "merchant_account_id": "acct_merchant_123",
    "idempotency_key": "idem_01J4ZTKC49R2AK7Y4M6GPJCMJ2"
  }
}
```

**Response:**

<!-- ucp:example skip reason="handler provider API, not UCP payload" -->
```json
{
  "success": true,
  "payment": {
    "status": "authorized",
    "processor": "examplepay",
    "processor_payment_id": "pi_123",
    "amount": {
      "value": "12.00",
      "currency": "USD"
    }
  },
  "receipt": {
    "credential_id": "spt_01J4ZTM7JVAF5J29VE1S58F7RC",
    "checkout_id": "checkout_abc123",
    "processed_at": "2026-07-24T18:04:22Z"
  }
}
```

---

## Security Requirements

| Requirement | Description |
| :---------- | :---------- |
| **Opaque token** | Platforms and agents receive only an opaque token and display-safe metadata. |
| **Checkout binding** | Tokens **MUST** be bound to checkout id, amount, currency, business id, and expiration. |
| **Processor binding** | If the business config requires a processor route, redemption **MUST** reject other routes. |
| **Single-use default** | Tokens **SHOULD** be single-use and short-lived. |
| **Replay protection** | Verification **MUST** bind idempotency keys to a normalized checkout fingerprint. |
| **No raw credential fallback** | Implementations **MUST NOT** expose PAN, CVC, network-token cryptograms, wallet secrets, bank credentials, or PSP secrets to platforms or agents as a fallback path. |
| **Consent traceability** | Issuance **MUST** record human consent or delegated allowance proof. |

## Error Handling

| Error | Meaning |
| :---- | :------ |
| `invalid_binding` | Checkout, amount, currency, business, or processor binding does not match. |
| `credential_expired` | Token expired before redemption. |
| `credential_revoked` | Token was revoked or invalidated. |
| `credential_replayed` | Token or idempotency key was reused with a different checkout fingerprint. |
| `unsupported_processor_route` | Business route cannot redeem this token. |
| `payment_declined` | Processor declined the payment. |
| `retryable_processing_error` | Temporary processor or network failure. |

## Related Specifications

* [Payment Handler Guide](../payment-handler-guide.md)
* [Tokenization Guide](../tokenization-guide.md)
* [Processor Tokenizer Payment Handler](processor-tokenizer-payment-handler.md)
* [Platform Tokenizer Payment Handler](platform-tokenizer-payment-handler.md)
