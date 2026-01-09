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

# PSP Payment Handler (Example)

* **Handler Name:** `com.example.psp_payments`
* **Version:** `2026-01-11`
* **Type:** Concrete Handler (Example)

## 1. Introduction

This example demonstrates a tokenization payment handler where the **PSP acts as both tokenizer and processor**. The merchant never handles credentials or calls `/detokenize`—they simply receive tokens and forward them to their PSP, who resolves and processes them in a single step.

The agent uses its secure card vaulting service (or a 3rd party vaulting
service) to collect raw credentials from the user, then tokenizes them via the
PSP's `/tokenize` endpoint.

This pattern provides **maximum PCI scope reduction** for merchants while
giving PSPs full control over the payment flow.

### 1.1 Key Benefits

- **Zero merchant PCI scope:** Merchants never see or handle payment credentials
- **Secure credential handling:** Raw credentials are handled only by the agent's PCI DSS compliant vaulting service and the PSP
- **Single integration point:** Merchants only integrate with their PSP
- **PSP-controlled tokenization:** PSP defines token policies, credential acceptance, and processing rules
- **Simplified merchant flow:** No detokenization step—merchant just forwards tokens to PSP

### 1.2 Quick Start

| If you are a... | Start here |
|:----------------|:-----------|
| **Merchant** using this handler | [3. Merchant Integration](#3-merchant-integration) |
| **Agent** using this handler | [4. Agent Integration](#4-agent-integration) |
| **PSP** implementing this handler | [5. PSP Integration](#5-psp-integration) |

---

## 2. Participants

| Participant | Role | Prerequisites |
|:------------|:-----|:--------------|
| **Merchant** | Advertises handler, receives tokens, forwards to PSP | Yes — onboards with PSP |
| **Agent** | Discovers handler, collects credentials via secure vaulting service, tokenizes via PSP, submits checkout | Yes — registers with PSP |
| **PSP** | Hosts `/tokenize`, stores tokens, processes payments | Yes — implements full handler |

### Pattern Flow

```
┌─────────┐     ┌───────────────────┐     ┌────────────┐
│  Agent  │     │  PSP (Tokenizer   │     │  Merchant  │
│         │     │   + Processor)    │     │            │
└────┬────┘     └─────────┬─────────┘     └──────┬─────┘
     │                    │                      │
     │  1. Agent + Merchant register with PSP (out-of-band)
     │───────────────────>│                      │
     │                    │<─────────────────────│
     │                    │                      │
     │  2. API credentials│                      │
     │<───────────────────│                      │
     │                    │─────────────────────>│
     │                    │                      │
     │  3. GET payment.handlers                  │
     │──────────────────────────────────────────>│
     │                    │                      │
     │  4. Handler with merchant identity        │
     │<──────────────────────────────────────────│
     │                    │                      │
     │  5. Agent's vaulting service: POST /tokenize
     │───────────────────>│                      │
     │                    │                      │
     │  6. Token          │                      │
     │<───────────────────│                      │
     │                    │                      │
     │  7. POST checkout with TokenCredential    │
     │──────────────────────────────────────────>│
     │                    │                      │
     │                    │  8. Process Payments │
     │                    │        (token)       │
     │                    │<─────────────────────│
     │                    │                      │
     │                    │  9. Payment result   │
     │                    │─────────────────────>│
     │                    │                      │
     │  10. Checkout complete                    │
     │<──────────────────────────────────────────│
```

Note: The merchant calls the PSP to process (not `/detokenize`). The PSP
resolves the token and processes payment atomically.

---

## 3. Merchant Integration

### 3.1 Prerequisites

Before using this handler, merchants must register with the PSP to obtain an
identity (`access_token`) and authentication credentials for processing
payments. Since the PSP handles raw credentials on behalf of merchants, the
PSP typically requires merchants to complete security acknowledgements during
onboarding.

**Prerequisites Output:**

| Field | Description |
|:------|:------------|
| `identity.access_token` | Merchant identifier assigned by PSP during onboarding |
| Authentication credentials | API key or OAuth token for authenticating payment processing |

### 3.2 Handler Configuration

Merchants advertise the PSP's handler in their checkout. The handler accepts [CardCredential](https://ucp.dev/schemas/shopping/types/card_credential.json) for tokenization and produces [TokenCredential](https://ucp.dev/schemas/shopping/types/token_credential.json) for checkout. The resulting payment instruments use [CardPaymentInstrument](https://ucp.dev/schemas/shopping/types/card_payment_instrument.json) schema.

**Note:** `CardCredential` contains raw PANs. Both the sender (agent's vaulting
service) and receiver (PSP's `/tokenize` endpoint) MUST be PCI DSS compliant.
The connection between them MUST use secure TLS.

#### Example Handler Declaration

```json
{
  "payment": {
    "handlers": [
      {
        "id": "psp_payments",
        "name": "com.example.psp_payments",
        "version": "2026-01-11",
        "spec": "https://psp.example.com/ucp/handler.json",
        "config_schema": "https://psp.example.com/ucp/handler/config.json",
        "instrument_schemas": [
          "https://ucp.dev/schemas/shopping/types/card_payment_instrument.json"
        ],
        "config": {
          "merchant_id": "merchant_xyz789",
          "environment": "production"
        }
      }
    ]
  }
}
```

### 3.3 Processing Payments

Upon receiving a checkout with a token credential, the merchant:

1. **Validate Handler:** Confirm `instrument.handler_id` matches the expected handler ID
2. **Forward to PSP:** Call the PSP's to process payments with the token and payment details
3. **Handle Response:** The PSP returns the payment result directly
4. **Return Response:** Respond with the finalized checkout state

---

## 4. Agent Integration

### 4.1 Prerequisites

Before using this handler, agents must:

1. Have access to a **PCI DSS compliant** card vaulting service (either
   self-hosted or 3rd party) that collects raw payment credentials from users
2. Register with the PSP to obtain authentication credentials for calling `/tokenize`

**Prerequisites Output:**

| Field | Description |
|:------|:------------|
| Vaulting service | **PCI DSS compliant** secure service for collecting raw credentials from users (agent's own infrastructure or 3rd party provider) |
| Authentication credentials | API key or publishable key for authenticating `/tokenize` calls to PSP |

### 4.2 Payment Protocol

#### Step 1: Discover Handler

Agent identifies the PSP payment handler. The merchant's configuration includes
their merchant ID:

```json
{
  "id": "psp_payments",
  "name": "com.example.psp_payments",
  "spec": "https://psp.example.com/ucp/handler.json",
  "config": {
    "merchant_id": "merchant_xyz789",
    "environment": "production"
  }
}
```

#### Step 2: Collect Credential

Agent's **PCI DSS compliant** vaulting service collects the raw payment
credential from the user (e.g., via a PCI-compliant payment form that ensures
the raw PAN never touches the agent application).

#### Step 3: Tokenize Credential

Agent's vaulting service calls the PSP's `/tokenize` endpoint (URL from handler
spec). Both the agent's vaulting service (sender) and PSP's endpoint (receiver)
are **PCI DSS compliant** and the connection uses secure HTTPS/TLS. The vaulting
service binds the token to the merchant's identity from the handler:

```json
POST https://api.psp.example.com/v1/tokenize
Content-Type: application/json
Authorization: Bearer {agent_api_key}

{
  "credential": {
    "type": "card",
    "card_number_type": "fpan",
    "number": "4242424242424242",
    "expiry_month": 12,
    "expiry_year": 2028,
    "cvc": "314",
    "name": "John Smith"
  },
  "binding": {
    "checkout_id": "checkout_456",
    "identity": {
      "access_token": "merchant_xyz789"
    }
  }
}
```

Response:

```json
{
  "token": "psp_tok_a1b2c3d4e5f6"
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
    "handler_id": "psp_payments",
    "type": "card",
    "brand": "visa",
    "last_digits": "4242",
    "expiry_month": 12,
    "expiry_year": 2028,
    "credential": {
      "type": "token",
      "token": "psp_tok_a1b2c3d4e5f6"
    }
  },
  "risk_signal": {
    // ... the key value pair for potential risk signal data
  }
}
```

---

## 5. PSP Integration

### 5.1 Prerequisites

**CRITICAL: PCI DSS Compliance Required**

This handler is implemented by PSPs that act as both tokenizer and payment
processor. As the party receiving raw `CardCredential` payloads via the
`/tokenize` endpoint, PSPs MUST be **PCI DSS compliant**. This includes:

- Secure transmission of `CardCredential` (HTTPS/TLS with strong cipher suites)
- Secure storage of raw credentials if persisted
- Proper key management and access controls
- Compliance with all PCI DSS requirements for handling Primary Account Numbers (PANs)

To implement, PSPs must:

1. Deploy a `/tokenize` endpoint for agents
2. Support payment processing for merchants (instead of `/detokenize`)
3. Onboard merchants and agents who will use these endpoints

**Implementation Requirements:**

| Requirement | Description |
|:------------|:------------|
| `/tokenize` endpoint | Accept credentials from agent vaulting services, return tokens |
| Payment Processing | Accept tokens + payment details from merchants, return payment result |
| Token storage | Map tokens to credentials with binding metadata |
| Participant allowlist | Only onboarded agent vaulting services and merchants can call endpoints |
| Binding verification | Verify `checkout_id` and merchant identity on processing |

### 5.2 Endpoint Specifications

#### POST /tokenize

Same as the base [Tokenization Payment Handler API](https://ucp.dev/handlers/tokenization/openapi.json).

#### Payment Processing

The PSP:
1. Identifies the merchant from their authentication credentials
2. Resolves the token to the original credential
3. Verifies binding matches (`checkout_id`, merchant identity)
4. Processes the payment
5. Invalidates the token
6. Returns the payment result

---

## 6. Security Considerations

| Requirement | Description |
|:------------|:------------|
| **Participant authentication** | PSP MUST authenticate agent vaulting services and merchants before accepting calls |
| **PCI DSS compliance (Agent)** | Agent vaulting services MUST be PCI DSS compliant when handling and sending raw PANs (Primary Account Numbers) |
| **PCI DSS compliance (PSP)** | PSP `/tokenize` endpoints MUST be PCI DSS compliant when receiving and storing raw PANs |
| **Secure transmission** | `CardCredential` transmission MUST use HTTPS/TLS with strong cipher suites between PCI-compliant endpoints |
| **Identity binding** | Tokens MUST be bound to the merchant's `identity` from the handler declaration |
| **Checkout-bound** | Tokens MUST be bound to the specific `checkout_id` |
| **Caller verification** | PSP MUST verify authenticated merchant matches the token's bound identity |
| **No merchant credential access** | Merchants MUST NOT call `/detokenize`—only `/process` |
| **No agent app credential access** | Agent applications MUST NOT handle raw credentials—only the PCI-compliant vaulting service does |
| **Single-use** | Tokens SHOULD be invalidated after processing |
| **Short TTL** | Tokens SHOULD expire within 15 minutes |
| **HTTPS required** | All `/tokenize` and `/process` calls must use TLS |

---

## 7. References

- **Pattern:** [Tokenization Payment Handler](../tokenization-guide.md)
- **API Pattern:** `https://ucp.dev/handlers/tokenization/openapi.json`
- **Identity Schema:** `https://ucp.dev/schemas/shopping/types/payment_identity.json`
