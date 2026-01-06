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

# Agent Encrypted Credential Handler (Example)

* **Handler Name:** `com.example.agent_encrypted`
* **Version:** `2026-01-11`
* **Type:** Concrete Handler (Example)

## 1. Introduction

This example demonstrates a payment handler where the **agent encrypts
credentials directly for the merchant**. Unlike tokenization patterns, there is
no `/tokenize` or `/detokenize`
endpoint—the agent's **PCI DSS compliant credential vault** encrypts credentials
using the merchant's public key, and the merchant decrypts them locally.

This pattern is ideal when merchants want to avoid round-trip latency to a
tokenizer at payment time.

### 1.1 Key Benefits

- **No runtime round-trips:** Merchant decrypts locally, no `/detokenize` call needed
- **Simpler architecture:** No token storage or token-to-credential mapping
- **Merchant-controlled keys:** Merchant manages their own decryption keys

### 1.2 Quick Start

| If you are a... | Start here |
|:----------------|:-----------|
| **Merchant** accepting this handler | [3. Merchant Integration](#3-merchant-integration) |
| **Agent** implementing this handler | [4. Agent Integration](#4-agent-integration) |

---

## 2. Participants

| Participant | Role | Prerequisites |
|:------------|:-----|:--------------|
| **Merchant** | Registers public key, receives encrypted credentials, decrypts locally | Yes — registers with agent |
| **Agent** | Operates PCI-compliant credential vault, encrypts for merchant using their public key | Yes — implements encryption |

### Pattern Flow

```
┌─────────────────┐                              ┌────────────┐
│  Agent          │                              │  Merchant  │
│                 │                              │            │
└────────┬────────┘                              └──────┬─────┘
         │                                              │
         │  1. Merchant registers public key (out-of-band)
         │<─────────────────────────────────────────────│
         │                                              │
         │  2. Confirmation                             │
         │─────────────────────────────────────────────>│
         │                                              │
         │  3. GET payment.handlers                     │
         │─────────────────────────────────────────────>│
         │                                              │
         │  4. Handler with merchant identity           │
         │<─────────────────────────────────────────────│
         │                                              │
         │  5. Agent's vaulting service encrypts        │
         │     credential with merchant's key           │
         │                                              │
         │  6. POST checkout with EncryptedCredential   │
         │─────────────────────────────────────────────>│
         │                                              │
         │       (Merchant decrypts locally)            │
         │                                              │
         │  7. Checkout complete                        │
         │<─────────────────────────────────────────────│
```

---

## 3. Merchant Integration

### 3.1 Prerequisites

**CRITICAL: PCI DSS Compliance Required**

Before accepting this handler, merchants must register their public encryption
key with the agent.

While merchants receive only encrypted `EncryptedCredential` payloads during
checkout, they MUST be **PCI DSS compliant** because they decrypt these payloads
locally to obtain raw `CardCredential` for payment processing. This includes:

- Secure key management for decryption keys
- Secure handling of raw credentials after decryption
- Compliance with all PCI DSS requirements for handling Primary Account Numbers (PANs)

**Prerequisites Output:**

| Field | Description |
|:------|:------------|
| `identity.access_token` | Merchant identifier assigned by agent during onboarding |
| Public key registered | Agent stores merchant's public key for encryption |

### 3.2 Handler Configuration

Merchants advertise the agent's handler. The `identity` field contains the
**merchant's identity**, which the agent uses to look up the correct public key
for encryption.

The only supported identity schema is [PaymentIdentity](https://ucp.dev/schemas/shopping/types/payment_identity.json).

The only supported instrument schema is [CardPaymentInstrument](https://ucp.dev/schemas/shopping/types/card_payment_instrument.json), the only supported checkout credential schema is `EncryptedCredential`, and the only supported source credential schema is [CardCredential](https://ucp.dev/schemas/shopping/types/card_credential.json).

**Note:** `CardCredential` contains raw PANs. The agent's **PCI DSS compliant**
vaulting service handles these credentials and encrypts them before
transmission. Merchants receive only encrypted payloads but MUST be PCI DSS
compliant once they decrypt the credentials locally.

#### Example Handler Declaration

```json
{
  "payment": {
    "handlers": [
      {
        "id": "agent_encrypted",
        "name": "com.example.agent_encrypted",
        "version": "2026-01-11",
        "spec": "https://agent.example.com/ucp/encrypted-handler.json",
        "config_schema": "https://agent.example.com/ucp/encrypted-handler/config.json",
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

Upon receiving a checkout with an encrypted credential:

1. **Validate Handler:** Confirm `instrument.handler_name` matches `com.example.agent_encrypted`
2. **Decrypt Credential:** Use merchant's private key to decrypt the credential
3. **Verify Binding:** Confirm the decrypted `checkout_id` matches the current checkout
4. **Process Payment:** Use the decrypted credential to complete payment
5. **Return Response:** Respond with the finalized checkout state

---

## 4. Agent Integration

### 4.1 Prerequisites

This handler is implemented by agents that operate **PCI DSS compliant**
credential vaults and can encrypt credentials for merchants. To implement,
agents must:

1. Maintain PCI DSS compliance for credential storage and handling
2. Store merchant public keys during onboarding
3. Encrypt credentials using the correct merchant's key based on handler identity

**Implementation Requirements:**

| Requirement | Description |
|:------------|:------------|
| Key storage | Map merchant identities to their public keys |
| Encryption | Encrypt credentials + binding context with merchant's public key |

### 4.2 Credential Encryption

The agent application orchestrates the payment flow but
**never has access to raw credentials**. Instead:

1. The agent's **PCI-compliant card vaulting service** receives the raw
   credential from the user
2. The vaulting service encrypts the credential along with binding context using
   the merchant's public key
3. The vaulting service returns the encrypted payload to the agent application
4. The agent application includes this encrypted payload in the checkout submission

This separation ensures the agent application itself never handles or has access
to raw PANs.

### 4.3 Submitting Checkout

Agent application submits the checkout with the encrypted credential (received
from its vaulting service):

```json
POST /checkout-sessions/{checkout_id}/complete
Content-Type: application/json

{
  "payment_data": {
    "id": "instr_1",
    "handler_name": "com.example.agent_encrypted",
    "type": "card",
    "brand": "visa",
    "last_digits": "1111",
    "expiry_month": 12,
    "expiry_year": 2026,
    "credential": {
      "type": "encrypted",
      "encrypted_data": "base64-encoded-encrypted-payload..."
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
| **PCI DSS compliance (Agent)** | Agent vaulting services MUST be PCI DSS compliant when handling and encrypting raw PANs (Primary Account Numbers) |
| **PCI DSS compliance (Merchant)** | Merchants MUST be PCI DSS compliant for decryption and handling of raw credentials locally |
| **No agent app credential access** | Agent applications MUST NOT handle raw credentials—only the PCI-compliant vaulting service does |
| **Asymmetric encryption** | Agent's credential vault encrypts with merchant's public key; only merchant can decrypt |
| **Binding embedded** | `checkout_id` MUST be included in encrypted payload to prevent replay |
| **Key rotation** | Merchants SHOULD rotate keys periodically; agent must support key updates |
| **No credential storage** | Agent does not store encrypted credentials; encryption is one-way |
| **HTTPS required** | All checkout submissions must use TLS |

---

## 6. References

- **Identity Schema:** `https://ucp.dev/schemas/shopping/types/payment_identity.json`
- **Instrument Schema:** `https://ucp.dev/schemas/shopping/types/card_payment_instrument.json`
