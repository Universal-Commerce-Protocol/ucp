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

# Tokenization Guide

**OpenAPI:** [Tokenization API](site:handlers/tokenization/openapi.json)

## Overview

This guide is for **implementers building tokenization payment handlers**. It
defines the shared API, security requirements, and conformance criteria that all
tokenization handlers follow.

**Note:** While the examples in this guide use card credentials, tokenization
patterns apply to **any sensitive credential type**—bank accounts, digital
wallets, loyalty accounts, etc. Compliance requirements (e.g., PCI DSS for
cards) vary by credential type.

We offer a range of examples to utilize forms of tokenization in UCP:

| Example | Use Case |
| :------ | :------- |
| [Processor Tokenizer](examples/processor-tokenizer-payment-handler.md) | Business or PSP runs tokenization and processing |
| [Platform Tokenizer](examples/platform-tokenizer-payment-handler.md) | Platform tokenizes credentials for businesses/PSPs |
| [Encrypted Credential Handler](examples/encrypted-credential-payment-handler.md) | Platform encrypts credentials instead of tokenizing |

---

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
|   | * pan           |                      | What comes OUT          |  |
|   | * network_token |                ----->| * token                 |  |
|   |                 |                      |                         |  |
|   +-----------------+                      +-------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

Tokenization handlers accept source credentials (e.g., a PAN credential) and
produce checkout credentials (e.g., tokens).

A network token does not always need this round-trip. A handler **MAY** accept
`network_token_credential.json` as a source credential for tokenization, or
**MAY** accept it directly as a checkout credential, since the token is
unusable without a matching cryptogram. The handler's specification **MUST**
state which of the two it accepts.

### Token Lifecycle

Tokens move through distinct phases. Your handler specification must document
which lifecycle policy you use:

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
| :----------------- | :------------------------------------------ | :---------------------------------------------- |
| **Single-use**     | Invalidated after first detokenization      | Most secure; recommended default                |
| **TTL-based**      | Expires after fixed duration (e.g., 15 min) | Allows retries on transient failures            |
| **Session-scoped** | Valid for checkout session duration         | Complex flows with multiple processing attempts |

### Binding

All tokenization requests require a `binding` object that ties the token to a
specific capability resource:

| Field  | Required | Description                                                                                                 |
| :----- | :------- | :---------------------------------------------------------------------------------------------------------- |
| `type` | Yes      | The capability that owns the bound resource, for example `dev.ucp.shopping.checkout`                        |
| `id`   | Yes      | Opaque identifier of the bound resource within that capability. The caller **MUST** send a non-empty string |

See [Binding Schema](site:schemas/common/types/binding.json).

Resource scope and participant scope are separate. Requests carry `identity`
alongside `binding` rather than inside it: `binding` says which resource the
token is for, `identity` says which participant it is for. `identity` is
required when the caller acts on behalf of another participant, and omitted
when the authenticated caller is that participant. See
[Payment Identity Schema](site:schemas/common/types/payment_identity.json).

Binding is a replay guard, not a resource reference. The following rules apply
to every tokenizer:

1. A Tokenizer **MUST** verify a binding by exact equality over `type` and
   `id`. A Tokenizer **MUST NOT** accept a partial match, and **MUST NOT**
   reject a request because `binding` carries members it does not recognize. A
   Tokenizer **MUST** ignore unrecognized members when comparing. An extension
   that defines additional `binding` members **MUST** specify whether those
   members participate in the comparison; a Tokenizer implementing that
   extension **MUST** follow the extension's definition.
2. A Tokenizer **MUST** treat `binding.id` as opaque: it **MUST NOT** require
   the value to be resolvable, and **MUST NOT** reject a request because it
   cannot confirm that the identified resource exists.
3. A Tokenizer **MUST NOT** reject a request solely because it does not
   recognize `binding.type`. A tokenizer serving one capability today therefore
   remains usable by capabilities defined later without changing its
   implementation.
4. Every token is issued to exactly one participant. A Tokenizer **MUST**
   record that participant at `/tokenize` — from `identity` when present,
   otherwise the authenticated caller. On `/detokenize` a Tokenizer **MUST**
   resolve the requesting participant the same way, **MUST** verify it matches
   the participant recorded at issuance, and **MUST** verify that the
   authenticated caller is that participant or is authorized to act for it. A
   Tokenizer **MUST NOT** return the credential when either check fails.
   `identity` is a participant identifier, not a credential, and a Tokenizer
   **MUST NOT** accept it as authentication. The mechanism by which one
   participant is authorized to act for another is handler-defined and outside
   the scope of this specification.

---

## OpenAPI

Tokenization handlers implement two endpoints. Your handler **MAY** implement
one or both depending on your architecture. Or none, like our encrypted
payload example, which defines its own mechanism to encrypt.

### POST /tokenize

Converts a raw credential into a token bound to a capability resource and issued
to a participant.

**When to implement:** Always, unless you are an agent generating tokens
internally.

<!-- ucp:example skip reason="tokenization API, not UCP payload" -->
```json
POST /tokenize
Content-Type: application/json

{
  "credential": {
    "type": "pan",
    "number": "4111111111111111",
    "expiry_month": 12,
    "expiry_year": 2026,
    "cvc": "123"
  },
  "binding": {
    "type": "dev.ucp.shopping.checkout",
    "id": "abc123"
  },
  "identity": {
    "access_token": "merchant_001"
  }
}
```

**Response:**

<!-- ucp:example skip reason="tokenization API, not UCP payload" -->
```json
{
  "token": "tok_abc123xyz789"
}
```

### POST /detokenize

Returns the original credential for a valid token. Binding must match.

**When to implement:** Always, unless you combine detokenization with
processing (see PSP example).

<!-- ucp:example skip reason="tokenization API, not UCP payload" -->
```json
POST /detokenize
Content-Type: application/json
Authorization: Bearer {caller_access_token}

{
  "token": "tok_abc123xyz789",
  "binding": {
    "type": "dev.ucp.shopping.checkout",
    "id": "abc123"
  }
}
```

**Response:**

<!-- ucp:example skip reason="tokenization API, not UCP payload" -->
```json
{
  "type": "pan",
  "number": "4111111111111111",
  "expiry_month": 12,
  "expiry_year": 2026,
  "cvc": "123"
}
```

**Note:** `identity` is omitted when the authenticated caller is the participant
the token was issued to. Include it when acting on behalf of another participant
(e.g., PSP detokenizing for business).

See the full [OpenAPI specification](site:handlers/tokenization/openapi.json) for complete request/response schemas.

---

## Security Requirements

| Requirement                  | Description                                                                                                                    |
| :--------------------------- | :----------------------------------------------------------------------------------------------------------------------------- |
| **Binding required**         | Credentials **MUST** be bound to a `binding` resource (`type` and `id`) and issued to exactly one participant to prevent reuse |
| **Binding verified**         | Tokenizer **MUST** verify binding matches before returning credentials                                                         |
| **Cryptographically random** | Use secure random generators; tokens must be unguessable                                                                       |
| **Sufficient length**        | Minimum 128 bits of entropy                                                                                                    |
| **Non-reversible**           | Cannot derive the credential from the token                                                                                    |
| **Scoped**                   | Token should only work with your tokenizer                                                                                     |
| **Time-limited**             | Enforce TTL appropriate to use case (typically 5-30 minutes)                                                                   |
| **Single-use preferred**     | Invalidate after first detokenization when possible                                                                            |

---

## Handler Specification Requirements

When publishing your handler, your specification document **MUST** include:

| Requirement                     | Example                                                           |
| :------------------------------ | :---------------------------------------------------------------- |
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
**OpenAPI:** [Tokenization API](site:handlers/tokenization/openapi.json)

| Environment | Base URL                           |
| :---------- | :--------------------------------- |
| Production  | `https://api.acme.com/ucp`         |
| Sandbox     | `https://sandbox.api.acme.com/ucp` |

**Supported Instruments:**

| Instrument | Source Credentials           | Checkout Credentials |
| :--------- | :--------------------------- | :------------------- |
| `card`     | `pan`, `network_token`       | `token`              |

**Token Lifecycle:** Single-use (invalidated after detokenization)

**Authentication:** OAuth 2.0 client credentials

**Onboarding:** Register at portal.acme.com. Businesses receive `access_token` for handler identity.
```

---

## Conformance Checklist

A tokenizer handler conforms to this pattern if it:

- [ ] Publishes a handler specification at a stable URL with a unique, reverse-DNS `handler_name`
- [ ] Implements `/tokenize` and/or `/detokenize` per the OpenAPI
- [ ] Defines authentication and onboarding requirements
- [ ] Documents credential transformation between source and checkout forms
- [ ] Produces tokens compatible with the `TokenCredential` schema
- [ ] Specifies token lifecycle policy (TTL, single-use, etc.)
- [ ] Requires `binding` with `type` and `id` on tokenization requests
- [ ] Uses `PaymentIdentity` for participant identification
- [ ] Verifies `binding` matches by exact equality on detokenization requests
- [ ] Records the participant each token is issued to, and on detokenization verifies both that participant and the caller's authority to act for it
- [ ] Accepts binding types it does not recognize
- [ ] Requires security acknowledgements from participants receiving raw credentials

---

## References

| Resource                | URL                                                                                                             |
| :---------------------- | :-------------------------------------------------------------------------------------------------------------- |
| Tokenization OpenAPI    | [handlers/tokenization/openapi.json](site:handlers/tokenization/openapi.json)                                   |
| Identity Schema         | [schemas/common/types/payment_identity.json](site:schemas/common/types/payment_identity.json)                   |
| Binding Schema          | [schemas/common/types/binding.json](site:schemas/common/types/binding.json)                                     |
| Token Credential Schema | [schemas/common/types/token_credential.json](site:schemas/common/types/token_credential.json)                   |
| Card Instrument Schema  | [schemas/common/types/card_payment_instrument.json](site:schemas/common/types/card_payment_instrument.json)     |

---

## See Also

- **[Encrypted Credential Handler](examples/encrypted-credential-payment-handler.md)** — Alternative pattern using encryption instead of tokenize/detokenize round-trips
- **[AP2 Mandates Extension](extensions/ap2-mandates.md)** — Add cryptographic proof of checkout agreement for PSP verification
