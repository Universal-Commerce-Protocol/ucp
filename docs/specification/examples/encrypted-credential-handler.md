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

# Encrypted Credential Handler

* **Handler Name:** `com.example.encrypted_credential`
* **Version:** `2026-01-11`
* **Type:** Payment Handler Example

## Introduction

This example demonstrates a payment handler where the **platform encrypts
credentials directly for the business**. Unlike tokenization patterns, there is
no `/tokenize` or `/detokenize`
endpoint—the platform's **PCI DSS compliant credential vault** encrypts credentials
using the business's public key, and the business decrypts them locally.

This pattern is ideal when businesses want to avoid round-trip latency to a
tokenizer at payment time.

### Key Benefits

- **No runtime round-trips:** Business decrypts locally, no `/detokenize` call needed
- **Simpler architecture:** No token storage or token-to-credential mapping
- **Business-controlled keys:** Business manages their own decryption keys

### Quick Start

| If you are a... | Start here |
|:----------------|:-----------|
| **Business** accepting this handler | [Business Integration](#business-integration) |
| **Platform** implementing this handler | [Platform Integration](#platform-integration) |

---

## Participants

| Participant | Role | Prerequisites |
|:------------|:-----|:--------------|
| **Business** | Registers public key, receives encrypted credentials, decrypts locally | Yes — registers with platform |
| **Platform** | Operates PCI-compliant credential vault, encrypts for business using their public key | Yes — implements encryption |

### Pattern Flow

```
┌─────────────────┐                              ┌────────────┐
│  Platform       │                              │  Business  │
│                 │                              │            │
└────────┬────────┘                              └──────┬─────┘
         │                                              │
         │  1. Business registers public key (out-of-band)
         │<─────────────────────────────────────────────│
         │                                              │
         │  2. Confirmation                             │
         │─────────────────────────────────────────────>│
         │                                              │
         │  3. GET payment.handlers                     │
         │─────────────────────────────────────────────>│
         │                                              │
         │  4. Handler with business identity           │
         │<─────────────────────────────────────────────│
         │                                              │
         │  5. Platform's vaulting service encrypts     │
         │     credential with business's key           │
         │                                              │
         │  6. POST checkout with EncryptedCredential   │
         │─────────────────────────────────────────────>│
         │                                              │
         │       (Business decrypts locally)            │
         │                                              │
         │  7. Checkout complete                        │
         │<─────────────────────────────────────────────│
```

---

## Business Integration

### Prerequisites

**CRITICAL: PCI DSS Compliance Required**

Before accepting this handler, businesses must register their public encryption
key with the platform.

While businesses receive only encrypted `EncryptedCredential` payloads during
checkout, they MUST be **PCI DSS compliant** because they decrypt these payloads
locally to obtain raw `CardCredential` for payment processing. This includes:

- Secure key management for decryption keys
- Secure handling of raw credentials after decryption
- Compliance with all PCI DSS requirements for handling Primary Account Numbers (PANs)

**Prerequisites Output:**

| Field | Description |
|:------|:------------|
| `identity.access_token` | Business identifier assigned by platform during onboarding |
| Public key registered | Platform stores business's public key for encryption |

### Handler Configuration

Businesses advertise the platform's handler. The `identity` field contains the
**business's identity**, which the platform uses to look up the correct public
key for encryption.

The only supported identity schema is [PaymentIdentity](https://ucp.dev/schemas/shopping/types/payment_identity.json).

The only supported instrument schema is [CardPaymentInstrument](https://ucp.dev/schemas/shopping/types/card_payment_instrument.json), the only supported checkout credential schema is `EncryptedCredential`, and the only supported source credential schema is [CardCredential](https://ucp.dev/schemas/shopping/types/card_credential.json).

**Note:** `CardCredential` contains raw PANs. The platform's
**PCI DSS compliant** vaulting service handles these credentials and encrypts
them before transmission. Businesses receive only encrypted payloads but
MUST be PCI DSS compliant once they decrypt the credentials locally.

#### Example Handler Declaration

```json
{
  "payment": {
    "handlers": [
      {
        "id": "platform_encrypted",
        "name": "com.example.platform_encrypted",
        "version": "2026-01-11",
        "spec": "https://platform.example.com/ucp/encrypted-handler.json",
        "config_schema": "https://platform.example.com/ucp/encrypted-handler/config.json",
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

### Processing Payments

Upon receiving a checkout with an encrypted credential:

1. **Validate Handler:** Confirm `instrument.handler_id` matches the expected handler ID
2. **Decrypt Credential:** Use business's private key to decrypt the credential
3. **Verify Binding:** Confirm the decrypted `checkout_id` matches the current checkout
4. **Process Payment:** Use the decrypted credential to complete payment
5. **Return Response:** Respond with the finalized checkout state

---

## Platform Integration

### Prerequisites

This handler is implemented by platforms that operate **PCI DSS compliant**
credential vaults and can encrypt credentials for businesses. To implement,
platforms must:

1. Maintain PCI DSS compliance for credential storage and handling
2. Store business public keys during onboarding
3. Encrypt credentials using the correct business's key based on handler identity

**Implementation Requirements:**

| Requirement | Description |
|:------------|:------------|
| Key storage | Map business identities to their public keys |
| Encryption | Encrypt credentials + binding context with business's public key |

### Credential Encryption

The platform application orchestrates the payment flow but
**never has access to raw credentials**. Instead:

1. The platform's **PCI-compliant card vaulting service** receives the raw
   credential from the user
2. The vaulting service encrypts the credential along with binding context using
   the business's public key
3. The vaulting service returns the encrypted payload to the platform application
4. The platform application includes this encrypted payload in the checkout submission

This separation ensures the platform application itself never handles or has
access to raw PANs.

### Submitting Checkout

Platform application submits the checkout with the encrypted credential
(received from its vaulting service):

```json
POST /checkout-sessions/{checkout_id}/complete
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json

{
  "payment": {
    "instruments": [
      {
        "id": "instr_1",
        "handler_id": "platform_encrypted",
        "type": "card",
        "brand": "visa",
        "last_digits": "1111",
        "expiry_month": 12,
        "expiry_year": 2026,
        "credential": {
          "type": "encrypted",
          "encrypted_data": "base64-encoded-encrypted-payload..."
        }
      }
    ]
  },
  "risk_signals": {
    // ... the key value pair for potential risk signal data
  }
}
```

---

## Security Considerations

| Requirement | Description |
|:------------|:------------|
| **PCI DSS compliance (Platform)** | Platform vaulting services MUST be PCI DSS compliant when handling and encrypting raw PANs (Primary Account Numbers) |
| **PCI DSS compliance (Business)** | Businesses MUST be PCI DSS compliant for decryption and handling of raw credentials locally |
| **No platform app credential access** | Platform applications MUST NOT handle raw credentials—only the PCI-compliant vaulting service does |
| **Asymmetric encryption** | Platform's credential vault encrypts with business's public key; only business can decrypt |
| **Binding embedded** | `checkout_id` MUST be included in encrypted payload to prevent replay |
| **Key rotation** | Businesses SHOULD rotate keys periodically; platform must support key updates |
| **No credential storage** | Platform does not store encrypted credentials; encryption is one-way |
| **HTTPS required** | All checkout submissions must use TLS |

---

## References

- **Identity Schema:** `https://ucp.dev/schemas/shopping/types/payment_identity.json`
- **Instrument Schema:** `https://ucp.dev/schemas/shopping/types/card_payment_instrument.json`
