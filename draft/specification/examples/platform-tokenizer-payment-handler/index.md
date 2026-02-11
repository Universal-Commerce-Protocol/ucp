# Platform Tokenizer Payment Handler

- **Handler Name:** `com.example.platform_tokenizer`
- **Type:** Payment Handler Example

## Introduction

This example demonstrates a tokenization payment handler where the **platform acts as the tokenizer**. The platform's **payment credential provider** securely stores sensitive payment data (e.g., stored cards from user wallets) and generates tokens internally without calling an external `/tokenize` endpoint.

The platform's credential provider exposes a `/detokenize` endpoint for businesses to call back and retrieve the sensitive instrument details for processing.

This pattern is ideal for platforms that operate as wallet providers with compliant credential storage.

**Note:** While this example uses card credentials, the pattern applies to **any credential type**. Compliance requirements vary by credential type (e.g., PCI DSS for cards).

### Key Benefits

- **Zero early transmission:** Platforms never expose sensitive data until a payment request is being finalized.
- **Platform-controlled security:** Platform defines token lifecycle and binding policies.
- **PSP flexibility:** Businesses can delegate detokenization to their PSP, keeping sensitive data out of business systems entirely.

### QuickStart

| If you are a...                        | Start here                                    |
| -------------------------------------- | --------------------------------------------- |
| **Business** accepting this handler    | [Business Integration](#business-integration) |
| **Platform** implementing this handler | [Platform Integration](#platform-integration) |
| **PSP** processing for businesses      | [PSP Integration](#psp-integration)           |

______________________________________________________________________

## Participants

| Participant  | Role                                                                                            | Prerequisites                         |
| ------------ | ----------------------------------------------------------------------------------------------- | ------------------------------------- |
| **Business** | Advertises handler, receives tokens, optionally delegates to PSP                                | Yes — onboards with platform          |
| **Platform** | Operates a payment credential provider that generates tokens and exposes `/detokenize` endpoint | Yes — implements tokenization service |
| **PSP**      | Optionally detokenizes on business's behalf, processes payments                                 | Yes — onboards with platform          |

### Pattern Flow: Business Detokenizes

```text
+-----------------+                              +------------+
|    Platform     |                              |  Business  |
|  (Tokenizer)    |                              |            |
+--------+--------+                              +------+-----+
         |                                              |
         |  1. Business registers with Platform (out-of-band)
         |<---------------------------------------------|
         |                                              |
         |  2. API credentials                          |
         |--------------------------------------------->|
         |                                              |
         |  3. GET ucp.payment_handlers                 |
         |--------------------------------------------->|
         |                                              |
         |  4. Handler with business identity           |
         |<---------------------------------------------|
         |                                              |
         |5. Platforms's Credential Provider generates token
         |                                              |
         |  6. POST checkout with TokenCredential       |
         |--------------------------------------------->|
         |                                              |
         |  7. POST /detokenize (to Credential Provider)|
         |<---------------------------------------------|
         |                                              |
         |  8. Sensitive Data                           |
         |--------------------------------------------->|
         |                                              |
         |  9. Checkout complete                        |
         |<---------------------------------------------|
```

### Pattern Flow: PSP Detokenizes

```text
+-----------------+     +------------+      +---------+
|    Platform     |     |  Business  |      |   PSP   |
|  (Tokenizer)    |     |            |      |         |
+--------+--------+     +------+-----+      +----+----+
         |                     |                 |
         |  1. Business + PSP register with Platform (out-of-band)
         |<--------------------|                 |
         |<--------------------------------------|
         |                     |                 |
         |  2. API credentials |                 |
         |-------------------->|                 |
         |-------------------------------------->|
         |                     |                 |
         |  3. Payment Credential Provider       |
         |     generates token                   |
         |                     |                 |
         |  4. POST checkout with TokenCredential|
         |-------------------->|                 |
         |                     |                 |
         |                     |  5. Forward     |
         |                     |  token to PSP   |
         |                     |---------------->|
         |                     |                 |
         |  6. POST /detokenize (to Credential Provider, with business identity)
         |<--------------------------------------|
         |                     |                 |
         |  7. Sensitive Data  |                 |
         |-------------------------------------->|
         |                     |                 |
         |                     |  8. Payment     |
         |                     |  result         |
         |                     |                  |
         |                     |<----------------|
         |                     |                 |
         |  9. Checkout complete                 |
         |<--------------------|                 |
```

______________________________________________________________________

## Business Integration

### Prerequisites

#### CRITICAL: Security & Compliance Required

Before accepting this handler, businesses must register with the platform to obtain authentication credentials for calling `/detokenize`.

As the party receiving sensitive instrument details via the `/detokenize` endpoint, businesses **MUST** be compliant with relevant data security standards for the credential type being handled (e.g., PCI DSS for cards). This includes:

- Secure transmission (HTTPS/TLS with strong cipher suites)
- Secure handling of sensitive data during payment processing
- Compliance with all regulations regarding the storage and processing of financial instruments

Optionally, businesses may configure their PSP to detokenize on their behalf (PSP must also be compliant).

**Prerequisites Output:**

| Field                      | Description                                                   |
| -------------------------- | ------------------------------------------------------------- |
| `identity.access_token`    | Business identifier assigned by platform during onboarding    |
| Authentication credentials | API key or OAuth token for authenticating `/detokenize` calls |

### Handler Configuration

Businesses advertise the platform's tokenization handler. The `config` contains the business's identity with the platform for token binding. The platform's handler specification (referenced via `spec`) documents the `/detokenize` endpoint URL exposed by the platform's **payment credential provider**.

The handler accepts [CardCredential](https://ucp.dev/schemas/shopping/types/card_credential.json) for tokenization and produces [TokenCredential](https://ucp.dev/schemas/shopping/types/token_credential.json) for checkout.

**Note:** The result of `/detokenize` contains **sensitive payment data**. Both the sender (platform's credential provider) and receiver (business or PSP) **MUST** be compliant with relevant standards for the credential type (e.g., PCI DSS for cards).

#### Business Config (Discovery)

| Field         | Type   | Required | Description                                 |
| ------------- | ------ | -------- | ------------------------------------------- |
| `environment` | string | Yes      | API environment (`sandbox` or `production`) |
| `business_id` | string | Yes      | Business identifier assigned by platform    |

#### Example Business Handler Declaration

```json
{
  "ucp": {
    "version": "2026-01-11",
    "payment_handlers": {
      "com.example.platform_tokenizer": [
        {
          "id": "platform_wallet",
          "version": "2026-01-11",
          "spec": "https://platform.example.com/ucp/handler.json",
          "schema": "https://platform.example.com/ucp/handler/schema.json",
          "config": {
            "environment": "production",
            "business_id": "business_abc123"
          }
        }
      ]
    }
  }
}
```

#### Response Config (Checkout)

The response config includes runtime token lifecycle information.

| Field               | Type    | Required | Description                   |
| ------------------- | ------- | -------- | ----------------------------- |
| `environment`       | string  | Yes      | API environment               |
| `business_id`       | string  | Yes      | Business identifier           |
| `token_ttl_seconds` | integer | No       | Token time-to-live in seconds |

#### Example Response Config

```json
{
  "config": {
    "environment": "production",
    "business_id": "business_abc123",
    "token_ttl_seconds": 900,
  }
}
```

### Processing Payments

Upon receiving a checkout with a token credential:

1. **Validate Handler:** Confirm `instrument.handler_id` matches the expected handler ID.
1. **Detokenize or Delegate:**
1. **Option A (Direct):** Call the platform's **credential provider** `/detokenize` endpoint directly, then process payments.
1. **Option B (Delegated):** Forward the token to a PSP for detokenization and payment processing.
1. **Return Response:** Respond with the finalized checkout state.

For option B, see section [PSP Integration](#psp-integration).

#### Detokenize Request Example (Business)

```json
POST https://provider.platform.example.com/ucp/detokenize
Content-Type: application/json
Authorization: Bearer {business_api_key}

{
  "token": "ptok_x9y8z7w6v5u4",
  "binding": {
    "checkout_id": "checkout_789"
  }
}
```

Note: No `binding.identity` is needed if the business authenticates directly—the platform knows who they are based on the API key.

______________________________________________________________________

## Platform Integration

### Prerequisites

This handler is implemented by platforms that operate **compliant payment credential providers** or wallet services. The payment credential provider (not the main platform application) handles sensitive data and exposes the `/detokenize` endpoint. To implement, platforms must:

1. Deploy a **compliant payment credential provider** that maintains compliance for credential storage and handling.
1. Expose a `/detokenize` endpoint conforming to the API pattern from the credential provider.
1. Onboard businesses and PSPs who will call the credential provider's `/detokenize` endpoint.

**Implementation Requirements:**

| Requirement            | Description                                                                              |
| ---------------------- | ---------------------------------------------------------------------------------------- |
| `/detokenize` endpoint | Exposed by the compliant payment credential provider (not the platform application)      |
| Token storage          | Map tokens to credentials with binding metadata in the credential provider               |
| Participant allowlist  | Only onboarded businesses/PSPs can call the credential provider's `/detokenize`          |
| Binding verification   | payment credential provider verifies `checkout_id` and caller identity on detokenization |

### Handler Configuration (Platform)

Platforms advertise this handler in their UCP profile's `payment_handlers` registry using `platform_config`.

#### Platform Config (Discovery)

| Field                       | Type    | Required | Description                                 |
| --------------------------- | ------- | -------- | ------------------------------------------- |
| `environment`               | string  | Yes      | API environment (`sandbox` or `production`) |
| `platform_id`               | string  | Yes      | Platform identifier                         |
| `default_token_ttl_seconds` | integer | No       | Default token TTL offered to businesses     |

#### Example Platform Handler Declaration

```json
{
  "ucp": {
    "version": "2026-01-11",
    "payment_handlers": {
      "com.example.platform_tokenizer": [
        {
          "id": "platform_wallet",
          "version": "2026-01-11",
          "spec": "https://platform.example.com/ucp/handler.json",
          "schema": "https://platform.example.com/ucp/handler/schema.json",
          "config": {
            "environment": "production",
            "platform_id": "platform_abc123",
            "default_token_ttl_seconds": 900
          }
        }
      ]
    }
  }
}
```

### Token Generation

The platform application orchestrates the payment flow but **never has access to sensitive payment data**. Instead:

1. The platform's **payment credential provider** securely stores payment credentials.
1. When a payment is needed, the platform application requests a token from the credential provider.
1. The credential provider generates a token bound to both the `checkout_id` and the business's `identity` (from the handler declaration).
1. The credential provider returns the token to the platform application.
1. The platform application includes this token in the checkout submission.

This separation ensures the platform application itself never handles or has access to sensitive instrument details.

### Submitting Checkout

The platform application submits the checkout with the token (received from its payment credential provider):

```json
POST /checkout-sessions/{checkout_id}/complete
Content-Type: application/json

{
  "payment": {
    "instruments": [
      {
        "id": "instr_1",
        "handler_id": "platform_wallet",
        "type": "card",
        "selected": true,
        "display": {
          "brand": "visa",
          "last_digits": "4242"
        },
        "credential": {
          "type": "token",
          "token": "ptok_x9y8z7w6v5u4"
        }
      }
    ]
  },
  "risk_signals": {
    // ... the key value pair for potential risk signal data
  }
}
```

______________________________________________________________________

## PSP Integration

### Prerequisites

#### CRITICAL: Security & Compliance Required

Before detokenizing on behalf of businesses, PSPs must register with the platform, providing the list of businesses they process for.

As the party receiving sensitive instrument details via the `/detokenize` endpoint, PSPs **MUST** be **compliant** with relevant security standards for the credential type being handled (e.g., PCI DSS for cards). This includes:

- Secure transmission (HTTPS/TLS with strong cipher suites)
- Secure handling of sensitive data during payment processing
- Compliance with all regulations regarding the storage and processing of financial instruments

**Prerequisites Output:**

| Field                      | Description                                                   |
| -------------------------- | ------------------------------------------------------------- |
| Authentication credentials | API key or OAuth token for authenticating `/detokenize` calls |
| Business associations      | List of business identities this PSP can detokenize for       |

### Detokenization Flow

When the business forwards a token to the PSP:

1. Extract the token from the payment instrument.
1. Call the platform's **payment credential provider** `/detokenize` endpoint with the business's identity in binding.
1. Process the payment with the returned credential.

#### Detokenize Request Example (PSP)

```json
POST https://provider.platform.example.com/ucp/detokenize
Content-Type: application/json
Authorization: Bearer {psp_api_key}

{
  "token": "ptok_x9y8z7w6v5u4",
  "binding": {
    "checkout_id": "checkout_789",
    "identity": {
      "access_token": "business_abc123"
    }
  }
}
```

Note: `binding.identity` IS required here—the PSP is calling on behalf of a business, so they must specify which businesses' token they are retrieving.

The platform's payment credential provider verifies that:

- The PSP is authorized to detokenize for this business.
- The `checkout_id` matches the original tokenization.
- The token has not expired or been used.

______________________________________________________________________

## Security Considerations

| Requirement                          | Description                                                                                                                                                                            |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Compliance (credential provider)** | Platform's credential provider **MUST** be compliant with relevant standards for the credential type (e.g., PCI DSS for cards) when handling and storing sensitive instrument details. |
| **Compliance (Receivers)**           | Businesses/PSPs calling `/detokenize` **MUST** be compliant with relevant standards for the credential type when receiving sensitive data payloads.                                    |
| **Secure transmission**              | Data transmission via `/detokenize` **MUST** use HTTPS/TLS with strong cipher suites.                                                                                                  |
| **No Platform App access**           | Platform applications **MUST NOT** handle sensitive data—only the compliant payment credential provider does.                                                                          |
| **Endpoint isolation**               | `/detokenize` endpoint **MUST** be exposed by the payment credential provider, not the platform application.                                                                           |
| **Participant authentication**       | Platform's credential provider **MUST** authenticate businesses/PSPs before accepting `/detokenize` calls.                                                                             |
| **Identity binding**                 | Tokens **MUST** be bound to the business's `identity` from the handler declaration.                                                                                                    |
| **Checkout-bound**                   | Tokens **MUST** be bound to the specific `checkout_id`.                                                                                                                                |
| **Caller verification**              | Platform **MUST** verify authenticated caller matches the token's bound identity (or is an authorized PSP).                                                                            |
| **Single-use**                       | Tokens **SHOULD** be invalidated after detokenization.                                                                                                                                 |
| **Short TTL**                        | Tokens **SHOULD** expire shortly.                                                                                                                                                      |
| **HTTPS required**                   | All `/detokenize` calls must use TLS.                                                                                                                                                  |

______________________________________________________________________

## References

- **Pattern:** [Tokenization Payment Handler](https://ucp.dev/specification/payment-handler-guide)
- **API Pattern:** `https://ucp.dev/handlers/tokenization/openapi.json`
- **Identity Schema:** `https://ucp.dev/schemas/shopping/types/payment_identity.json`
