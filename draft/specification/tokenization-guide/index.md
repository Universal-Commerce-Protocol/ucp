# Tokenization Guide

**OpenAPI:** [Tokenization API](https://ucp.dev/handlers/tokenization/openapi.json)

## Overview

This guide is for **implementers building tokenization payment handlers**. It defines the shared API, security requirements, and conformance criteria that all tokenization handlers follow.

**Note:** While the examples in this guide use card credentials, tokenization patterns apply to **any sensitive credential type**—bank accounts, digital wallets, loyalty accounts, etc. Compliance requirements (e.g., PCI DSS for cards) vary by credential type.

We offer a range of examples to utilize forms of tokenization in UCP:

| Example                                                                                                            | Use Case                                            |
| ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| [Processor Tokenizer](https://ucp.dev/draft/specification/examples/processor-tokenizer-payment-handler/index.md)   | Business or PSP runs tokenization and processing    |
| [Platform Tokenizer](https://ucp.dev/draft/specification/examples/platform-tokenizer-payment-handler/index.md)     | Platform tokenizes credentials for businesses/PSPs  |
| [Encrypted Credential Handler](https://ucp.dev/draft/specification/examples/encrypted-credential-handler/index.md) | Platform encrypts credentials instead of tokenizing |

______________________________________________________________________

## Core Concepts

### Credential Flow

Tokenization handlers transform credentials between source and checkout forms:

```text
+-------------------------------------------------------------------------+
|                     Tokenization Payment Flow                           |
+-------------------------------------------------------------------------+
|                                                                         |
|   Platform has:            Tokenizer            Business receives:      |
|   Source Credential    -->  /tokenize  -->         TokenCredential      |
|                                                                         |
|   +-----------------+                      +-------------------------+  |
|   | source_         |                      | checkout_               |  |
|   | credentials     |    What goes IN      | credentials             |  |
|   |                 |<---------------      |                         |  |
|   | * card/fpan     |                      | What comes OUT          |  |
|   | * card/dpan     |                ----->| * token                 |  |
|   |                 |                      |                         |  |
|   +-----------------+                      +-------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

Tokenization handlers accept source credentials (e.g., card with FPAN) and produce checkout credentials (e.g., tokens).

### Token Lifecycle

Tokens move through distinct phases. Your handler specification must document which lifecycle policy you use:

```text
+--------------+    +--------------+    +--------------+    +--------------+
|  Generation  |--->|   Storage    |--->| Detokenize   |--->| Invalidation |
|              |    |              |    |              |    |              |
|Platform calls|    | Tokenizer    |    | Business/PSP |    | Token expires|
| /tokenize    |    | holds token  |    | calls        |    | or is used   |
|              |    | -> credential|    | /detokenize  |    |              |
+--------------+    +--------------+    +--------------+    +--------------+
```

| Policy             | Description                                 | Use Case                                        |
| ------------------ | ------------------------------------------- | ----------------------------------------------- |
| **Single-use**     | Invalidated after first detokenization      | Most secure; recommended default                |
| **TTL-based**      | Expires after fixed duration (e.g., 15 min) | Allows retries on transient failures            |
| **Session-scoped** | Valid for checkout session duration         | Complex flows with multiple processing attempts |

### Binding

All tokenization requests require a `binding` object that ties the token to a specific context:

| Field         | Required    | Description                                                                                     |
| ------------- | ----------- | ----------------------------------------------------------------------------------------------- |
| `checkout_id` | Yes         | The checkout session this token is valid for                                                    |
| `identity`    | Conditional | The participant identity to bind to; required when caller acts on behalf of another participant |

The tokenizer **MUST** verify binding matches on `/detokenize`. See [Binding Schema](https://ucp.dev/schemas/shopping/types/binding.json).

______________________________________________________________________

## OpenAPI

Tokenization handlers implement two endpoints. Your handler **MAY** implement one or both depending on your architecture. Or none, like our encrypted payload example, which defines its own mechanism to encrypt.

### POST /tokenize

Converts a raw credential into a token bound to a checkout and identity.

**When to implement:** Always, unless you are an agent generating tokens internally.

```json
POST /tokenize
Content-Type: application/json

{
  "credential": {
    "type": "card",
    "card_number_type": "fpan",
    "number": "4111111111111111",
    "expiry_month": 12,
    "expiry_year": 2026,
    "cvc": "123"
  },
  "binding": {
    "checkout_id": "abc123",
    "identity": {
      "access_token": "merchant_001"
    }
  }
}
```

**Response:**

```json
{
  "token": "tok_abc123xyz789"
}
```

### POST /detokenize

Returns the original credential for a valid token. Binding must match.

**When to implement:** Always, unless you combine detokenization with processing (see PSP example).

```json
POST /detokenize
Content-Type: application/json
Authorization: Bearer {caller_access_token}

{
  "token": "tok_abc123xyz789",
  "binding": {
    "checkout_id": "abc123"
  }
}
```

**Response:**

```json
{
  "type": "card",
  "card_number_type": "fpan",
  "number": "4111111111111111",
  "expiry_month": 12,
  "expiry_year": 2026,
  "cvc": "123"
}
```

**Note:** `binding.identity` is omitted when the authenticated caller is the binding target. Include it when acting on behalf of another participant (e.g., PSP detokenizing for business).

See the full [OpenAPI specification](https://ucp.dev/handlers/tokenization/openapi.json) for complete request/response schemas.

______________________________________________________________________

## Security Requirements

| Requirement                  | Description                                                                                |
| ---------------------------- | ------------------------------------------------------------------------------------------ |
| **Binding required**         | Credentials **MUST** be bound to `checkout_id` and participant `identity` to prevent reuse |
| **Binding verified**         | Tokenizer **MUST** verify binding matches before returning credentials                     |
| **Cryptographically random** | Use secure random generators; tokens must be unguessable                                   |
| **Sufficient length**        | Minimum 128 bits of entropy                                                                |
| **Non-reversible**           | Cannot derive the credential from the token                                                |
| **Scoped**                   | Token should only work with your tokenizer                                                 |
| **Time-limited**             | Enforce TTL appropriate to use case (typically 5-30 minutes)                               |
| **Single-use preferred**     | Invalidate after first detokenization when possible                                        |

______________________________________________________________________

## Handler Specification Requirements

When publishing your handler, your specification document **MUST** include:

| Requirement                     | Example                                                           |
| ------------------------------- | ----------------------------------------------------------------- |
| **Unique handler name**         | `com.example.tokenization_payment` (reverse-DNS format)           |
| **Endpoint URLs**               | Production and sandbox base URLs                                  |
| **Authentication requirements** | OAuth 2.0, API keys, etc.                                         |
| **Onboarding process**          | How participants register and receive identities                  |
| **Accepted credentials**        | Which credential types are accepted for tokenization              |
| **Token lifecycle policy**      | Single-use, TTL, or session-scoped                                |
| **Security acknowledgements**   | Participants receiving raw credentials must accept responsibility |

### Example Specification Outline

```markdown
**Handler Name:** `com.acme.tokenization_payment`
**OpenAPI:** [Tokenization API](https://ucp.dev/handlers/tokenization/openapi.json)

| Environment | Base URL                           |
| :---------- | :--------------------------------- |
| Production  | `https://api.acme.com/ucp`         |
| Sandbox     | `https://sandbox.api.acme.com/ucp` |

**Supported Instruments:**

| Instrument | Source Credentials           | Checkout Credentials |
| :--------- | :--------------------------- | :------------------- |
| `card`     | `card` (fpan, network_token) | `token`              |

**Token Lifecycle:** Single-use (invalidated after detokenization)

**Authentication:** OAuth 2.0 client credentials

**Onboarding:** Register at portal.acme.com. Businesses receive `access_token` for handler identity.
```

______________________________________________________________________

## Conformance Checklist

A tokenizer handler conforms to this pattern if it:

- Publishes a handler specification at a stable URL with a unique, reverse-DNS `handler_name`
- Implements `/tokenize` and/or `/detokenize` per the OpenAPI
- Defines authentication and onboarding requirements
- Documents credential transformation between source and checkout forms
- Produces tokens compatible with the `TokenCredential` schema
- Specifies token lifecycle policy (TTL, single-use, etc.)
- Requires `binding` with `checkout_id` on tokenization requests
- Uses `PaymentIdentity` for participant identification
- Verifies `binding` matches on detokenization requests
- Requires security acknowledgements from participants receiving raw credentials

______________________________________________________________________

## References

| Resource                | URL                                                                   |
| ----------------------- | --------------------------------------------------------------------- |
| Tokenization OpenAPI    | `https://ucp.dev/handlers/tokenization/openapi.json`                  |
| Identity Schema         | `https://ucp.dev/schemas/shopping/types/payment_identity.json`        |
| Binding Schema          | `https://ucp.dev/schemas/shopping/types/binding.json`                 |
| Token Credential Schema | `https://ucp.dev/schemas/shopping/types/token_credential.json`        |
| Card Instrument Schema  | `https://ucp.dev/schemas/shopping/types/card_payment_instrument.json` |

______________________________________________________________________

## See Also

- **[Encrypted Credential Handler](https://ucp.dev/draft/specification/examples/encrypted-credential-handler/index.md)** — Alternative pattern using encryption instead of tokenize/detokenize round-trips
- **[AP2 Mandates Extension](https://ucp.dev/draft/specification/ap2-mandates/index.md)** — Add cryptographic proof of checkout agreement for PSP verification
