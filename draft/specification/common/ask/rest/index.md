# Ask - REST Binding

This document specifies the HTTP/REST binding for the [Ask Capability](http://ucp.dev/draft/specification/common/ask/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability for the Common service and the Ask capability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "draft",
    "services": {
      "dev.ucp.common": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/draft/services/common/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.common.ask": [{
        "version": "draft",
        "spec": "https://ucp.dev/draft/specification/common/ask",
        "schema": "https://ucp.dev/draft/schemas/common/ask.json"
      }]
    },
    "payment_handlers": {}
  }
}
```

## Endpoints

| Endpoint | Method | Capability                                                    | Description                                                                                                         |
| -------- | ------ | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `/ask`   | POST   | [Ask](http://ucp.dev/draft/specification/common/ask/index.md) | Ask the Business about its resources, policies, and services, including questions other capabilities cannot answer. |

### `POST /ask`

Maps to the [Ask](http://ucp.dev/draft/specification/common/ask/index.md) capability.

**Inputs**

| Name         | Type                                                               | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ------------------------------------------------------------------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| query        | string                                                             | **Required** | Natural-language question.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| conversation | [Conversation](/draft/specification/common/ask/rest/#conversation) | Optional     | Provide a conversation to continue it on a follow-up; omit to start a new one.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ids          | Array[string]                                                      | Optional     | Optional identifiers that ground the question in any Business resource. A Business SHOULD accept its own Global IDs (GIDs) and MAY accept recognized secondary identifiers such as SKU, handle, or URL. GIDs self-describe to the Business; a Platform may send them as opaque grounding references. Examples include a product, location, cart, order, or booking.                                                                                                                                                                                                                                                                                                     |
| context      | [Context](/draft/specification/reference/#context)                 | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals      | [Signals](/draft/specification/reference/#signals)                 | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |

**Output**

| Name         | Type                                                               | Requirement  | Description                                                                                                                                                                                                                                                                         |
| ------------ | ------------------------------------------------------------------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | UCP Ask Response Schema                                            | **Required** | UCP metadata for ask responses.                                                                                                                                                                                                                                                     |
| answer       | [Description](/draft/specification/reference/#description)         | **Required** | Answer provided by the Business. Plain text is required; Markdown and HTML are optional alternative encodings.                                                                                                                                                                      |
| conversation | [Conversation](/draft/specification/common/ask/rest/#conversation) | Optional     | Business-issued conversation for multi-turn continuation. When returned, the business SHOULD retain its history until `expires_at` (or per its own policy) so a follow-up with the same `id` builds on it. An unresolved `id` starts a new conversation and is noted in `messages`. |
| links        | Array\[[Link](/draft/specification/reference/#link)\]              | Optional     | Optional links and references related to the answer. When a link refers to an addressable UCP resource, the Business SHOULD include its GID in the link's `id`.                                                                                                                     |
| messages     | Array\[[Message](/draft/specification/reference/#message)\]        | Optional     | Errors, warnings, or informational messages about the answer or its grounding.                                                                                                                                                                                                      |

#### Example

The Buyer asks a policy question about a specific product, identified here by its page URL. `ids` grounds the question in any Business resource, by a Business-issued Global ID (GID) or by a secondary identifier the Business recognizes — a SKU, handle, or URL — so the Platform can pass whichever it already has (see [Scoping a Question](http://ucp.dev/draft/specification/common/ask/#scoping-a-question)).

```json
POST /ask HTTP/1.1
Host: business.example.com
Content-Type: application/json

{
  "query": "What is your return policy for these on sale?",
  "ids": ["https://business.example.com/products/winter-jacket"],
  "context": {
    "address_country": "US",
    "language": "en",
    "intent": "buying a discounted winter jacket as a gift"
  }
}
```

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.common.ask": [
        {"version": "draft"}
      ]
    }
  },
  "answer": {
    "plain": "Sale items can be returned within 14 days of delivery for store credit. Items returned to a different region may be subject to local return rules — see the refund policy for details.",
    "markdown": "Sale items can be returned within **14 days** of delivery for store credit. Items returned to a different region may be subject to local return rules — see the refund policy for details."
  },
  "links": [
    {
      "type": "refund_policy",
      "url": "https://business.example.com/policies/refunds",
      "title": "Refund Policy"
    }
  ]
}
```

#### Multi-turn Example

A Business that supports multi-turn conversations returns a `conversation` whose opaque `id` the Platform replays on the next turn. Turn 1 omits `conversation` (a new conversation); turn 2 replays the identifier to build on it.

Turn 1, request — a new conversation (no `conversation`):

```json
POST /ask HTTP/1.1
Host: business.example.com
Content-Type: application/json

{
  "query": "Is this jacket warm enough for winter?",
  "ids": ["https://business.example.com/products/winter-jacket"]
}
```

Turn 1, response — the Business issues a conversation identifier:

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.common.ask": [
        {"version": "draft"}
      ]
    }
  },
  "answer": {
    "plain": "Yes — it's insulated for sub-zero conditions and rated for harsh winter use."
  },
  "conversation": { "id": "conv_9a3f2e7b", "expires_at": "2026-06-22T18:30:00Z" }
}
```

Turn 2, request — replay the identifier to continue:

```json
POST /ask HTTP/1.1
Host: business.example.com
Content-Type: application/json
Idempotency-Key: 7c9e6679-7425-40de-944b-e07fc1f90ae7

{
  "query": "And is it waterproof?",
  "conversation": { "id": "conv_9a3f2e7b" }
}
```

Turn 2, response:

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.common.ask": [
        {"version": "draft"}
      ]
    }
  },
  "answer": {
    "plain": "It's water-resistant with a durable water-repellent finish — good for snow and light rain, though not fully waterproof."
  },
  "conversation": { "id": "conv_9a3f2e7b", "expires_at": "2026-06-22T18:30:00Z" }
}
```

#### "Can't Answer" Example

When the Business cannot address the question, the response is still HTTP 200 with a populated `answer` stating the limitation.

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.common.ask": [
        {"version": "draft"}
      ]
    }
  },
  "answer": {
    "plain": "I don't have information about competitor pricing. For questions about this store's products, I can help with policies, materials, fit, and availability."
  }
}
```

## HTTP Headers

The following headers are defined for the HTTP binding.

**Request Headers**

| Header            | Required | Description                                                                                                                           |
| ----------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `Authorization`   | No       | Contains an OAuth token representing Platform or Buyer credentials.                                                                   |
| `X-API-Key`       | No       | Reusable API key allocated to the Platform by the Business.                                                                           |
| `Signature`       | No       | RFC 9421 HTTP Message Signature. Format: `sig1=:<base64-signature>:`.                                                                 |
| `Signature-Input` | No       | RFC 9421 Signature-Input header. Format: `sig1=("@method" "@path" ...);created=<timestamp>;keyid="<key-id>"`.                         |
| `Content-Digest`  | No       | Body digest per RFC 9530. Format: `sha-256=:<base64-digest>:`.                                                                        |
| `Idempotency-Key` | No       | Ensures duplicate operations don't happen during retries.                                                                             |
| `Request-Id`      | **Yes**  | Unique UUID for tracing requests across components.                                                                                   |
| `User-Agent`      | No       | Identifies the user agent string making the call.                                                                                     |
| `UCP-Agent`       | **Yes**  | Identifies the UCP agent making the call, containing the signer's profile URI. Format: profile="https://example.com/.well-known/ucp". |
| `Content-Type`    | No       | Representation Metadata describing the body content.                                                                                  |
| `Accept`          | No       | Content Negotiation, indicating accepted formats.                                                                                     |
| `Accept-Language` | No       | Preferred natural languages for localization.                                                                                         |
| `Accept-Encoding` | No       | Supported content-codings (compression).                                                                                              |

**Response Headers**

| Header            | Required | Description                                   |
| ----------------- | -------- | --------------------------------------------- |
| `Signature`       | No       | RFC 9421 HTTP Message Signature for response. |
| `Signature-Input` | No       | RFC 9421 Signature-Input header for response. |
| `Content-Digest`  | No       | Body digest per RFC 9530 for response.        |

### Specific Header Requirements

- **UCP-Agent**: All requests **MUST** include the `UCP-Agent` header containing the platform profile URI using Dictionary Structured Field syntax ([RFC 8941](https://datatracker.ietf.org/doc/html/rfc8941)). Format: `profile="https://platform.example/profile"`.

- **Idempotency-Key**: The Common service declares `Idempotency-Key` as an optional request header. A Platform **SHOULD** include it on any request that carries a `conversation`, and **MAY** include it on any other (see [Conversation](http://ucp.dev/draft/specification/common/ask/#conversation)). When present, the Business **MUST**:

  1. Store the key with the result for at least 24 hours.
  1. Return the cached result for a duplicate key whose request body matches the original, without appending a second turn.
  1. Return `409 Conflict` if the key is reused with a mismatched body. See [Message Signatures — Replay Protection](http://ucp.dev/draft/specification/signatures/#replay-protection) for the full payload-matching contract.

## Error Handling

UCP uses a two-layer error model separating transport errors from business outcomes.

### Transport Errors

Use HTTP status codes for protocol-level issues that prevent request processing:

| Status | Meaning                                                     |
| ------ | ----------------------------------------------------------- |
| 400    | Bad Request - Malformed JSON or missing required parameters |
| 401    | Unauthorized - Missing or invalid authentication            |
| 429    | Too Many Requests - Rate limited                            |
| 500    | Internal Server Error                                       |

### Business Outcomes

All application-level outcomes return HTTP 200 with the UCP envelope and a populated `answer`. Per-answer warnings or info notes ride in the optional `messages` array. See [Ask Overview](http://ucp.dev/draft/specification/common/ask/#messages-and-error-handling) for message semantics.

#### Example: Answer with a Disclosure Warning

When an answer touches on a regulated disclosure (allergens, safety, legal), the binding disclosure is referenced as a warning with `presentation: "disclosure"`. The answer itself states the limitation and defers to the binding source.

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.common.ask": [
        {"version": "draft"}
      ]
    }
  },
  "answer": {
    "plain": "This nut butter is made with almonds. For complete allergen information, please consult the on-product allergen disclosure, which is the authoritative source.",
    "markdown": "This nut butter is made with almonds. For complete allergen information, please consult the on-product allergen disclosure, which is the authoritative source."
  },
  "links": [
    {
      "type": "faq",
      "url": "https://business.example.com/faq/allergens",
      "title": "Allergen FAQ"
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "allergens",
      "content": "**Contains: tree nuts.** Produced in a facility that also processes peanuts, milk, and soy.",
      "content_type": "markdown",
      "presentation": "disclosure"
    }
  ]
}
```

## Entities

### UCP Response Ask

UCP metadata for ask responses.

| Name             | Type   | Requirement  | Description                                                                                                                                    |
| ---------------- | ------ | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| version          | string | **Required** | Version identifier in YYYY-MM-DD format.                                                                                                       |
| map_order        | object | Optional     | Preferred key-traversal order for sibling registry fields inside the root `ucp` envelope (`services`, `capabilities`, and `payment_handlers`). |
| status           | string | Optional     | Application-level status of the UCP operation. **Enum:** `success`, `error`                                                                    |
| services         | object | Optional     | Service registry keyed by reverse-domain name.                                                                                                 |
| capabilities     | object | Optional     | Capability registry keyed by reverse-domain name.                                                                                              |
| payment_handlers | object | Optional     | Payment handler registry keyed by reverse-domain name.                                                                                         |

### Conversation

| Name       | Type   | Requirement  | Description                                                                         |
| ---------- | ------ | ------------ | ----------------------------------------------------------------------------------- |
| id         | string | **Required** | Opaque, business-issued conversation identifier.                                    |
| expires_at | string | Optional     | RFC 3339 timestamp after which the conversation context may be discarded. Optional. |

### Error Response

| Name         | Type                                                        | Requirement  | Description                                                       |
| ------------ | ----------------------------------------------------------- | ------------ | ----------------------------------------------------------------- |
| ucp          | UCP Error                                                   | **Required** | UCP protocol metadata. Status MUST be 'error' for error response. |
| messages     | Array\[[Message](/draft/specification/reference/#message)\] | **Required** | Array of messages describing why the operation failed.            |
| continue_url | string                                                      | Optional     | URL for buyer handoff or session recovery.                        |

## Conformance

A conforming REST transport implementation **MUST**:

1. When `dev.ucp.common.ask` is advertised in the Business's UCP profile, expose `POST /ask` under the `dev.ucp.common` service's REST `endpoint`.
1. Validate request bodies against the [Ask schema](http://ucp.dev/draft/specification/common/ask/index.md).
1. Return HTTP 200 for every well-formed, authorized, in-limits request; convey business outcomes through the `answer` and `messages` array, and use HTTP error status codes only for transport-level issues (authentication, rate limiting, unavailability, malformed input).
1. Return a populated `answer` on every successful response. A "can't answer" outcome is a populated `answer` that states the limitation plainly, **not** an omitted field, error code, or non-2xx status.
