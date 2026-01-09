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

# Agent Tokenizer Payment Handler (Example)

* **Handler Name:** `com.example.agent_tokenizer`
* **Version:** `2026-01-11`
* **Type:** Concrete Handler (Example)

## 1. Introduction

This example demonstrates a tokenization payment handler where the **agent acts
as the tokenizer**. The agent's **PCI DSS compliant card vaulting service**
securely stores payment credentials (e.g., stored cards from user wallets) and
generates tokens internally without calling an external `/tokenize` endpoint.
The vaulting service exposes a `/detokenize` endpoint for merchants or PSPs to
call back to retrieve credentials.

This pattern is ideal for agents that operate as wallet providers with
PCI-compliant credential vaults.

### 1.1 Key Benefits

- **No early credential transmission:** Agents never expose raw credentials
  until a payment request is being finalized, after checkout submission.
- **Agent-controlled security:** Agent defines token lifecycle and binding policies
- **PSP flexibility:** Merchants can delegate detokenization to their PSP, keeping credentials out of merchant systems entirely

### 1.2 Quick Start

| If you are a... | Start here |
|:----------------|:-----------|
| **Merchant** accepting this handler | [3. Merchant Integration](#3-merchant-integration) |
| **Agent** implementing this handler | [4. Agent Integration](#4-agent-integration) |
| **PSP** processing for merchants | [5. PSP Integration](#5-psp-integration) |

---

## 2. Participants

| Participant | Role | Prerequisites |
|:------------|:-----|:--------------|
| **Merchant** | Advertises handler, receives tokens, optionally delegates to PSP | Yes — onboards with agent |
| **Agent** | Operates PCI-compliant card vaulting service that generates tokens and exposes `/detokenize` endpoint | Yes — implements tokenization service |
| **PSP** | Optionally detokenizes on merchant's behalf, processes payments | Yes — onboards with agent |

### Pattern Flow: Merchant Detokenizes

```
┌─────────────────┐                              ┌────────────┐
│  Agent          │                              │  Merchant  │
│  (Tokenizer)    │                              │            │
└────────┬────────┘                              └──────┬─────┘
         │                                              │
         │  1. Merchant registers with agent (out-of-band)
         │<─────────────────────────────────────────────│
         │                                              │
         │  2. API credentials                          │
         │─────────────────────────────────────────────>│
         │                                              │
         │  3. GET payment.handlers                     │
         │─────────────────────────────────────────────>│
         │                                              │
         │  4. Handler with merchant identity            │
         │<─────────────────────────────────────────────│
         │                                              │
         │  5. Agent's vaulting service generates token │
         │                                              │
         │  6. POST checkout with TokenCredential       │
         │─────────────────────────────────────────────>│
         │                                              │
         │  7. POST /detokenize (to vaulting service)   │
         │<─────────────────────────────────────────────│
         │                                              │
         │  8. Credential                               │
         │─────────────────────────────────────────────>│
         │                                              │
         │  9. Checkout complete                        │
         │<─────────────────────────────────────────────│
```

### Pattern Flow: PSP Detokenizes

```
┌─────────────────┐     ┌────────────┐      ┌─────────┐
│  Agent          │     │  Merchant  │      │   PSP   │
│  (Tokenizer)    │     │            │      │         │
└────────┬────────┘     └──────┬─────┘      └────┬────┘
         │                     │                 │
         │  1. Merchant + PSP register with agent (out-of-band)
         │<────────────────────│                 │
         │<──────────────────────────────────────│
         │                     │                 │
         │  2. API credentials │                 │
         │────────────────────>│                 │
         │──────────────────────────────────────>│
         │                     │                 │
         │  3. Agent's vaulting service          │
         │     generates token                   │
         │                     │                 │
         │  4. POST checkout with TokenCredential│
         │────────────────────>│                 │
         │                     │                 │
         │                     │  5. Forward     │
         │                     │  token to PSP   │
         │                     │────────────────>│
         │                     │                 │
         │  6. POST /detokenize (to vaulting service, with merchant identity)
         │<──────────────────────────────────────│
         │                     │                 │
         │  7. Credential      │                 │
         │──────────────────────────────────────>│
         │                     │                 │
         │                     │  8. Payment     │
         │                     │  result         │
         │                     │<────────────────│
         │                     │                 │
         │  9. Checkout complete                 │
         │<────────────────────│                 │
```

---

## 3. Merchant Integration

### 3.1 Prerequisites

**CRITICAL: PCI DSS Compliance Required**

Before accepting this handler, merchants must register with the agent to obtain
authentication credentials for calling `/detokenize`.

As the party receiving raw `CardCredential` payloads via the `/detokenize`
endpoint, merchants MUST be **PCI DSS compliant**. This includes:

- Secure transmission of `CardCredential` (HTTPS/TLS with strong cipher suites)
- Secure handling of raw credentials during payment processing
- Compliance with all PCI DSS requirements for handling Primary Account Numbers (PANs)

Optionally, merchants may configure their PSP to detokenize on their behalf
(PSP must also be PCI DSS compliant).

**Prerequisites Output:**

| Field | Description |
|:------|:------------|
| `identity.access_token` | Merchant identifier assigned by agent during onboarding |
| Authentication credentials | API key or OAuth token for authenticating `/detokenize` calls |

### 3.2 Handler Configuration

Merchants advertise the agent's tokenization handler. The `config` contains the
 merchant's identity with the agent for token binding. The agent's handler
 specification (referenced via `spec`) documents the `/detokenize` endpoint
 URL exposed by the agent's PCI-compliant card vaulting service.

The handler accepts [CardCredential](https://ucp.dev/schemas/shopping/types/card_credential.json) for tokenization and produces [TokenCredential](https://ucp.dev/schemas/shopping/types/token_credential.json) for checkout. The resulting payment instruments use [CardPaymentInstrument](https://ucp.dev/schemas/shopping/types/card_payment_instrument.json) schema.

**Note:** `CardCredential` contains raw PANs. The agent's **PCI DSS compliant**
credential vault handles and stores these credentials internally. When merchants
or PSPs call `/detokenize`, they receive raw `CardCredential` payloads and MUST
also be PCI DSS compliant.

#### Example Handler Declaration

```json
{
  "payment": {
    "handlers": [
      {
        "id": "agent_wallet",
        "name": "com.example.agent_tokenizer",
        "version": "2026-01-11",
        "spec": "https://agent.example.com/ucp/handler.json",
        "config_schema": "https://agent.example.com/ucp/handler/config.json",
        "instrument_schemas": [
          "https://ucp.dev/schemas/shopping/types/card_payment_instrument.json"
        ],
        "config": {
          "merchant_id": "merchant_abc123",
          "environment": "production"
        }
      }
    ]
  }
}
```

### 3.3 Processing Payments

Upon receiving a checkout with a token credential:

1. **Validate Handler:** Confirm `instrument.handler_id` matches the expected handler ID
2. **Detokenize or Delegate:**
   - **Option A:** Call the agent's card vaulting service `/detokenize` endpoint directly, then process payments
   - **Option B:** Forward the token to your PSP for detokenization and payment processing.
3. **Return Response:** Respond with the finalized checkout state

For option B, see section [5. PSP Integration](#5-psp-integration)

#### Detokenize Request Example (Merchant)

```json
POST https://vault.agent.example.com/ucp/detokenize
Content-Type: application/json
Authorization: Bearer {merchant_api_key}

{
  "token": "atok_x9y8z7w6v5u4",
  "binding": {
    "checkout_id": "checkout_789"
  }
}
```

Note: No `binding.identity` is needed since the merchant authenticates directly—the agent knows who they are.

---

## 4. Agent Integration

### 4.1 Prerequisites

This handler is implemented by agents that operate **PCI DSS compliant** card
vaulting services or wallet services. The vaulting service (not the agent
application) handles raw credentials and exposes the `/detokenize` endpoint. To
implement, agents must:

1. Deploy a **PCI DSS compliant** card vaulting service that maintains
   compliance for credential storage and handling
2. The vaulting service exposes a `/detokenize` endpoint conforming to the API pattern
3. Onboard merchants and PSPs who will call the vaulting service's `/detokenize` endpoint

**Implementation Requirements:**

| Requirement | Description |
|:------------|:------------|
| `/detokenize` endpoint | Exposed by the PCI-compliant vaulting service (not the agent application) |
| Token storage | Map tokens to credentials with binding metadata in the vaulting service |
| Participant allowlist | Only onboarded merchants/PSPs can call the vaulting service's `/detokenize` |
| Binding verification | Vaulting service verifies `checkout_id` and caller identity on detokenization |

### 4.2 Token Generation

The agent application orchestrates the payment flow but **never has access to
raw credentials**. Instead:

1. The agent's **PCI-compliant card vaulting service** securely stores payment credentials
2. When a payment is needed, the agent application requests a token from the vaulting service
3. The vaulting service generates a token bound to both the `checkout_id` and
   the merchant's `identity` (from the handler declaration)
4. The vaulting service returns the token to the agent application
5. The agent application includes this token in the checkout submission

This separation ensures the agent application itself never handles or has
access to raw PANs.

### 4.3 Submitting Checkout

Agent application submits the checkout with the token (received from its
vaulting service):

```json
POST /checkout-sessions/{checkout_id}/complete
Content-Type: application/json

{
  "payment_data": {
    "id": "instr_1",
    "handler_id": "agent_wallet",
    "type": "card",
    "brand": "visa",
    "last_digits": "4242",
    "expiry_month": 3,
    "expiry_year": 2027,
    "credential": {
      "type": "token",
      "token": "atok_x9y8z7w6v5u4"
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

Before detokenizing on behalf of merchants, PSPs must register with the agent,
providing the list of merchants they process for.

As the party receiving raw `CardCredential` payloads via the `/detokenize`
endpoint, PSPs MUST be **PCI DSS compliant**. This includes:

- Secure transmission of `CardCredential` (HTTPS/TLS with strong cipher suites)
- Secure handling of raw credentials during payment processing
- Compliance with all PCI DSS requirements for handling Primary Account Numbers (PANs)

**Prerequisites Output:**

| Field | Description |
|:------|:------------|
| Authentication credentials | API key or OAuth token for authenticating `/detokenize` calls |
| Merchant associations | List of merchant identities this PSP can detokenize for |

### 5.2 Detokenization Flow

When the merchant forwards a token to the PSP:

1. Extract the token from the payment instrument
2. Call the agent's card vaulting service `/detokenize` endpoint with the merchant's identity in binding
3. Process the payment with the returned credential

#### Detokenize Request Example (PSP)

```json
POST https://vault.agent.example.com/ucp/detokenize
Content-Type: application/json
Authorization: Bearer {psp_api_key}

{
  "token": "atok_x9y8z7w6v5u4",
  "binding": {
    "checkout_id": "checkout_789",
    "identity": {
      "access_token": "merchant_abc123"
    }
  }
}
```

Note: `binding.identity` IS required here—the PSP is calling on behalf of a merchant, so they must specify which merchant's token they're retrieving.

The agent's vaulting service verifies that:

- The PSP is authorized to detokenize for this merchant
- The `checkout_id` matches the original tokenization
- The token has not expired or been used

---

## 6. Security Considerations

| Requirement | Description |
|:------------|:------------|
| **PCI DSS compliance (Vaulting Service)** | Agent's card vaulting service MUST be PCI DSS compliant when handling and storing raw PANs (Primary Account Numbers) |
| **PCI DSS compliance (Receivers)** | Merchants/PSPs calling `/detokenize` MUST be PCI DSS compliant when receiving raw `CardCredential` payloads |
| **Secure transmission** | `CardCredential` transmission via `/detokenize` MUST use HTTPS/TLS with strong cipher suites |
| **No agent app credential access** | Agent applications MUST NOT handle raw credentials—only the PCI-compliant vaulting service does |
| **Endpoint isolation** | `/detokenize` endpoint MUST be exposed by the vaulting service, not the agent application |
| **Participant authentication** | Vaulting service MUST authenticate merchants/PSPs before accepting `/detokenize` calls |
| **Identity binding** | Tokens MUST be bound to the merchant's `identity` from the handler declaration |
| **Checkout-bound** | Tokens MUST be bound to the specific `checkout_id` |
| **Caller verification** | Agent MUST verify authenticated caller matches the token's bound identity (or is an authorized PSP) |
| **Single-use** | Tokens SHOULD be invalidated after detokenization |
| **Short TTL** | Tokens SHOULD expire within 15 minutes |
| **HTTPS required** | All `/detokenize` calls must use TLS |

---

## 7. References

- **Pattern:** [Tokenization Payment Handler](../tokenization-guide.md)
- **API Pattern:** `https://ucp.dev/handlers/tokenization/openapi.json`
- **Identity Schema:** `https://ucp.dev/schemas/shopping/types/payment_identity.json`
