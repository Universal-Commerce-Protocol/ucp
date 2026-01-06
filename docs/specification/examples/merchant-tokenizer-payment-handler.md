<!--
   Copyright 2025 Google LLC

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

# Merchant Tokenizer Payment Handler (Example)

* **Handler Name:** `com.example.merchant_tokenizer`
* **Version:** `2026-01-11`
* **Type:** Concrete Handler (Example)

## 1. Introduction

This example demonstrates a tokenization payment handler where the
**merchant acts as the tokenizer**. The merchant hosts their own tokenization
service. The agent's **PCI DSS compliant vaulting service** collects raw
credentials from users and calls the merchant's `/tokenize` endpoint to obtain
tokens. Since the merchant is both tokenizer and processor, there is no
`/detokenize` step—the merchant already has the mapping from token to credential.

### 1.1 Key Benefits

- **No third-party tokenizer:** Merchant controls the entire tokenization flow
- **Simplified architecture:** Token storage and payment processing are co-located
- **No detokenization latency:** Merchant resolves tokens internally during processing

### 1.2 Quick Start

| If you are a... | Start here |
|:----------------|:-----------|
| **Merchant** implementing this handler | [3. Merchant Integration](#3-merchant-integration) |
| **Agent** using this handler | [4. Agent Integration](#4-agent-integration) |

---

## 2. Participants

| Participant | Role | Prerequisites |
|:------------|:-----|:--------------|
| **Merchant** | Hosts `/tokenize` endpoint, stores tokens, processes payments | Yes — implements tokenization service |
| **Agent** | Discovers handler, collects credentials via PCI-compliant vaulting service, tokenizes via merchant, submits checkout | Yes — registers with merchant |

### Pattern Flow

```
┌─────────┐                              ┌────────────────────────┐
│  Agent  │                              │  Merchant (Tokenizer)  │
└────┬────┘                              └───────────┬────────────┘
     │                                               │
     │  1. Register with merchant (out-of-band)      │
     │──────────────────────────────────────────────>│
     │                                               │
     │  2. API credentials                           │
     │<──────────────────────────────────────────────│
     │                                               │
     │  3. GET payment.handlers                      │
     │──────────────────────────────────────────────>│
     │                                               │
     │  4. Handler with spec URL                     │
     │<──────────────────────────────────────────────│
     │                                               │
     │  5. POST /tokenize (with agent identity)      │
     │──────────────────────────────────────────────>│
     │                                               │
     │  6. Token                                     │
     │<──────────────────────────────────────────────│
     │                                               │
     │  7. POST checkout with TokenCredential        │
     │──────────────────────────────────────────────>│
     │                                               │
     │       (Merchant resolves token internally)    │
     │                                               │
     │  8. Checkout complete                         │
     │<──────────────────────────────────────────────│
```

---

## 3. Merchant Integration

### 3.1 Prerequisites

This handler is only relevant for integration with a single merchant who owns
the tokenizer, so there are no normative prerequisites.

**CRITICAL: PCI DSS Compliance Required**

As the party receiving raw `CardCredential` payloads via the `/tokenize`
endpoint, the merchant MUST be **PCI DSS compliant**. This includes:

- Secure transmission of `CardCredential` (HTTPS/TLS with strong cipher suites)
- Secure storage of raw credentials if persisted
- Proper key management and access controls
- Compliance with all PCI DSS requirements for handling Primary Account Numbers (PANs)

To highlight their role as the tokenizer, the merchant will:
1. Deploy a `/tokenize` endpoint conforming to the [Tokenization Payment Handler API](https://ucp.dev/handlers/tokenization/openapi.json)
2. Implement **PCI DSS compliant** secure token storage mapping tokens to
   credentials
3. Integrate token resolution into their payment processing flow

### 3.2 Handler Configuration

Merchants advertise their tokenization handler in the checkout's
`payment.handlers` array.

The handler accepts [CardCredential](https://ucp.dev/schemas/shopping/types/card_credential.json)
for tokenization and produces [TokenCredential](https://ucp.dev/schemas/shopping/types/token_credential.json)
for checkout. The resulting payment instruments use
[CardPaymentInstrument](https://ucp.dev/schemas/shopping/types/card_payment_instrument.json)
schema.

**Note:** `CardCredential` contains raw PANs. Both the sender (agent's vaulting
service) and receiver (merchant's `/tokenize` endpoint) MUST be PCI DSS
compliant. The connection between them MUST use secure TLS.

#### Example Handler Declaration

```json
{
  "payment": {
    "handlers": [
      {
        "id": "merchant_tokenizer",
        "name": "com.example.merchant_tokenizer",
        "version": "2026-01-11",
        "spec": "https://example.com/ucp/merchant-tokenizer.json",
        "config_schema": "https://example.com/ucp/merchant-tokenizer/config.json",
        "instrument_schemas": [
          "https://ucp.dev/schemas/shopping/types/card_payment_instrument.json"
        ],
        "config": {}
      }
    ]
  }
}
```

### 3.3 Processing Payments

Upon receiving a checkout with a token credential:

1. **Validate Handler:** Confirm `instrument.handler_id` matches the expected handler ID
2. **Resolve Token:** Look up the token in internal storage to retrieve the original credential
3. **Verify Binding:** Confirm the token's `checkout_id` matches the current checkout
4. **Process Payment:** Charge the credential through the merchant's payment processor
5. **Invalidate Token:** Mark the token as used (single-use recommended)
6. **Return Response:** Respond with the finalized checkout state

---

## 4. Agent Integration

### 4.1 Prerequisites

Before using this handler, agents must:

1. Have access to a **PCI DSS compliant** card vaulting service (either
   self-hosted or 3rd party) that collects raw payment credentials from users
2. Register with the merchant to obtain an identity (`access_token`) and authentication credentials

**Prerequisites Output:**

| Field | Description |
|:------|:------------|
| Vaulting service | **PCI DSS compliant** secure service for collecting raw credentials from users |
| Authentication credentials | API key or OAuth token for authenticating `/tokenize` calls |

### 4.2 Payment Protocol

#### Step 1: Discover Handler

Agent identifies the merchant tokenizer handler.

```json
{
  "id": "merchant_tokenizer",
  "name": "com.example.merchant_tokenizer",
  "spec": "https://example.com/ucp/merchant-tokenizer.json"
}
```

#### Step 2: Collect Credential

Agent's **PCI DSS compliant** vaulting service collects the raw payment
credential from the user (e.g., via a PCI-compliant payment form that ensures
the raw PAN never touches the agent application).

#### Step 3: Tokenize Credential

Agent's vaulting service calls the merchant's `/tokenize` endpoint. Both the
agent's vaulting service (sender) and merchant's endpoint (receiver) are
**PCI DSS compliant** and the connection uses secure HTTPS/TLS:

```json
POST https://pay.example.com/ucp/tokenize
Content-Type: application/json
Authorization: Bearer {agent_api_key}

{
  "credential": {
    "type": "card",
    "card_number_type": "fpan",
    "number": "4111111111111111",
    "expiry_month": 12,
    "expiry_year": 2026,
    "cvc": "123",
    "name": "Jane Doe"
  },
  "binding": {
    "checkout_id": "gid://example.com/Checkout/order_12345"
  }
}
```

Note: No `binding.identity` is needed since the merchant is the tokenizer—the binding is implicit.

Response:

```json
{
  "token": "mtok_a1b2c3d4e5f6"
}
```

#### Step 4: Complete Checkout

Agent submits the checkout:

```json
POST /checkout-sessions/{checkout_id}/complete
Content-Type: application/json

{
  "payment_data": {
    "id": "instr_1",
    "handler_id": "merchant_tokenizer",
    "type": "card",
    "brand": "visa",
    "last_digits": "1111",
    "expiry_month": 12,
    "expiry_year": 2026,
    "credential": {
      "type": "token",
      "token": "mtok_a1b2c3d4e5f6"
    }
  },
  "risk_signal": {
    // ... the key value pair for potential risk signal data
  }
}
```

---

## 5. Security Considerations

| Requirement | Description |
|:------------|:------------|
| **PCI DSS compliance (Agent)** | Agent vaulting services MUST be PCI DSS compliant when handling and sending raw PANs (Primary Account Numbers) |
| **PCI DSS compliance (Merchant)** | Merchant `/tokenize` endpoints MUST be PCI DSS compliant when receiving and storing raw PANs |
| **Secure transmission** | `CardCredential` transmission MUST use HTTPS/TLS with strong cipher suites between PCI-compliant endpoints |
| **No agent app credential access** | Agent applications MUST NOT handle raw credentials—only the PCI-compliant vaulting service does |
| **Agent authentication** | Merchant MUST authenticate agent vaulting services before accepting `/tokenize` calls |
| **Checkout-bound** | Tokens MUST be bound to the specific `checkout_id` |
| **Single-use** | Tokens SHOULD be invalidated after processing |
| **Short TTL** | Tokens SHOULD expire within 15 minutes |
| **HTTPS required** | All `/tokenize` calls must use TLS |

---

## 6. References

- **Pattern:** [Tokenization Payment Handler](/third_party/ucp/docs/specification/tokenization-guide.md)
- **API Pattern:** `https://ucp.dev/handlers/tokenization/openapi.json`
- **Identity Schema:** `https://ucp.dev/schemas/shopping/types/payment_identity.json`
