# Processor Tokenizer Payment Handler

- **Handler Name:** `com.example.processor_tokenizer`
- **Type:** Payment Handler Example

## Introduction

This handler implements a **"Tokenize to Process"** flow where the entity that generates the token (the Tokenizer) is the same entity that processes the final payment (the Processor).

**Note:** While this example uses card credentials, the pattern applies to **any credential type**. Compliance requirements vary by credential type (e.g., PCI DSS for cards).

This specification unifies two common implementation scenarios:

1. **Business-Hosted:** An enterprise Business hosts their own secure vault. The Business tokenizes and processes.
1. **PSP-Hosted:** The Business uses a third-party PSP. The PSP tokenizes and processes.

In both cases, **no API detokenization step is required**. The token resolution happens internally within the Processor's secure environment.

### Comparison of Scenarios

| Feature              | Scenario A: PSP-Hosted                       | Scenario B: Business-Hosted          |
| -------------------- | -------------------------------------------- | ------------------------------------ |
| **Tokenizer Host**   | Third-Party PSP                              | The Business                         |
| **Compliance Scope** | **Low** (Business never sees PAN)            | **High** (Business stores PAN)       |
| **Identity Binding** | **Required** (PSP needs Merchant Identifier) | **Implicit** (Business knows itself) |

______________________________________________________________________

## Participants

| Participant               | Role                                                                                 | Prerequisites                                             |
| ------------------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------- |
| **Tokenizer / Processor** | Host `/tokenize` endpoint, store tokens, process payments. (Can be Business or PSP). | Compliance per credential type (e.g., PCI DSS for cards). |
| **Platform**              | Collect credentials via secure credential provider, call Tokenizer, submit checkout. | Secure credential provider.                               |
| **Business**              | Configures the handler for the checkout.                                             | None (if PSP-hosted).                                     |

### Pattern Flow

```text
+------------+                         +-----------------------------------+
|  Platform  |                         |       Tokenizer / Processor       |
| (Collector)|                         |      (Business or PSP)            |
+-----+------+                         +-----------------+-----------------+
      |                                                  |
      |  1. GET ucp.payment_handlers                     |
      |------------------------------------------------->|
      |                                                  |
      |  2. Handler Config (URL + Identity)              |
      |<-------------------------------------------------|
      |                                                  |
      |  3. POST /tokenize (Credential + Identity)       |
      |------------------------------------------------->|
      |                                                  |
      |  4. Token                                        |
      |<-------------------------------------------------|
      |                                                  |
      |  5. POST checkout with TokenCredential           |
      |------------------------------------------------->|
      |                                                  |
      |        (Internal Resolution: Token -> Info)      |
      |                                                  |
      |  6. Payment Result                               |
      |<-------------------------------------------------|
```

______________________________________________________________________

## Configuration

The Business advertises this handler in their UCP profile's `payment_handlers` registry. The configuration determines whether the Platform acts in "PSP Mode" (sending identity) or "Direct Mode" (implicit identity).

### Business Config (Discovery)

The business advertises their tokenization endpoint and identity during discovery. The handler's specification (referenced via the `spec` field) documents the `/tokenize` endpoint URL.

| Field         | Type   | Required | Description                                 |
| ------------- | ------ | -------- | ------------------------------------------- |
| `environment` | string | Yes      | API environment (`sandbox` or `production`) |
| `business_id` | string | Yes      | Business identifier with the processor      |

#### Example Business Handler Declaration

```json
{
  "ucp": {
    "version": "2026-01-11",
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {
          "id": "processor_tokenizer",
          "version": "2026-01-11",
          "spec": "https://example.com/ucp/processor-tokenizer.json",
          "schema": "https://example.com/ucp/processor-tokenizer/schema.json",
          "config": {
            "environment": "production",
            "business_id": "merchant_xyz789"
          }
        }
      ]
    }
  }
}
```

### Response Config (Checkout)

The response config includes runtime information about what's available for this checkout.

| Field                | Type   | Required | Description                                  |
| -------------------- | ------ | -------- | -------------------------------------------- |
| `environment`        | string | Yes      | API environment used for this checkout       |
| `business_id`        | string | Yes      | Business identifier                          |
| `supported_networks` | array  | No       | Card networks supported for this transaction |

#### Example Response Config

```json
{
  "config": {
    "environment": "production",
    "business_id": "merchant_xyz789",
    "supported_networks": ["visa", "mastercard", "amex"]
  }
}
```

## Platform Integration

### Prerequisites

Before using this handler, platforms must:

1. Have access to a **compliant secure payment credential providers** that collects sensitive payment data from users. This service must meet the compliance requirements of the instruments being handled (e.g., PCI DSS).
1. Obtain authentication credentials (e.g., API Key) authorized to call the specific `endpoint` defined in the handler configuration.

**Prerequisites Output:**

| Field                        | Description                                                                   |
| ---------------------------- | ----------------------------------------------------------------------------- |
| payment credential providers | **Compliant** secure service for collecting sensitive payment data from users |
| Authentication credentials   | API key or OAuth token for authenticating `/tokenize` calls                   |

### Payment Protocol

#### Step 1: Discover Handler

Platform identifies the processor tokenizer handler and retrieves the business's configuration.

```json
{
  "ucp": {
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {
          "id": "processor_tokenizer",
          "version": "2026-01-11",
          "config": {
            "environment": "production",
            "business_id": "merchant_xyz789"
          }
        }
      ]
    }
  }
}
```

#### Step 2: Collect Sensitive Data

Platform's **compliant secure payment credential providers** collects the sensitive payment data from the user (e.g., via a compliant payment form that ensures the sensitive instrument details never touch the platform).

#### Step 3: Tokenize Data

Platform's payment credential provider calls the configured `endpoint`.

**Note:** If the handler configuration includes an `identity` object, the credential provider **MUST** inject it into the `binding` object.

Response:

```json
{
  "token": "tok_a1b2c3d4e5f6"
}
```

### Step 4: Complete Checkout

The Platform submits the token.

```json
POST /checkout-sessions/{checkout_id}/complete
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json

{
  "payment": {
    "instruments": [
      {
        "id": "instr_1",
        "handler_id": "processor_tokenizer",
        "type": "card",
        "selected": true,
        "display": {
          "brand": "visa",
          "last_digits": "1111",
          "expiry_month": 12,
          "expiry_year": 2026
        },
        "credential": {
          "type": "token",
          "token": "tok_a1b2c3d4e5f6"
        }
      }
    ]
  },
  "risk_signal": {
    // ... the key value pair for potential risk signal data
  }
}
```

______________________________________________________________________

## Implementation Guide

### Scenario A: Enterprise Implementation (Self-Hosted)

- **Role:** The Business implements this specification.
- **Requirements:**
  1. Deploy the `endpoint` on their own infrastructure.
  1. Internally map tokens to PANs in their own database.
- **Security:** **CRITICAL.** For card credentials, the Business **MUST** be PCI DSS compliant as they are receiving raw PANs at their endpoint. Other credential types have their own compliance requirements.

### Scenario B: PSP Implementation (Third-Party)

- **Role:** The PSP implements this specification.
- **Requirements:**
  1. Provide the `endpoint` URL to merchants.
  1. Issue `identity.access_token` (Merchant Secure Identifier) to merchants.
  1. Validate that the `binding.identity` matches the merchant requesting the final payment charge.
- **Security:** PSP bears the compliance burden for credential storage (e.g., PCI DSS for cards).

______________________________________________________________________

## Security Considerations

| Requirement            | Description                                                                                                                                                    |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **TLS/HTTPS**          | All traffic to `config.endpoint` **MUST** be encrypted.                                                                                                        |
| **Compliance**         | The entity hosting `config.endpoint` **MUST** be compliant with relevant data standards for the credential type (e.g., PCI DSS for cards, GDPR for PII, etc.). |
| **Scope Isolation**    | The Platform's main application **MUST NOT** see the raw credential; only the Platform's Secure credential provider and the Tokenizer Host may see it.         |
| **Binding Validation** | The Tokenizer/Processor **MUST** verify that the `checkout_id` submitted during final payment matches the `checkout_id` provided during tokenization.          |
