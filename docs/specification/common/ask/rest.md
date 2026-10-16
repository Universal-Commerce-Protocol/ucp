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

# Ask - REST Binding

This document specifies the HTTP/REST binding for the
[Ask Capability](index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability for the Common service and
the Ask capability through their UCP profile at `/.well-known/ucp`.

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.common": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/common/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.common.ask": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/ask",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/ask.json"
      }]
    },
    "payment_handlers": {}
  }
}
```

## Endpoints

| Endpoint | Method | Capability | Description |
| :--- | :--- | :--- | :--- |
| `/ask` | POST | [Ask](index.md) | Ask the Business about its resources, policies, and services, including questions other capabilities cannot answer. |

### `POST /ask`

Maps to the [Ask](index.md) capability.

{{ method_fields('ask_business', 'common/rest.openapi.json', 'common/ask/rest') }}

#### Example

The Buyer asks a policy question about a specific product, identified here by
its page URL. `ids` grounds the question in any Business resource, by a
Business-issued Global ID (GID) or by a secondary identifier the Business
recognizes — a SKU, handle, or URL — so the Platform can pass whichever it
already has (see [Scoping a Question](index.md#scoping-a-question)).

=== "Request"

    <!-- ucp:example schema=common/ask def=ask_request op=create direction=request -->
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

=== "Response"

    <!-- ucp:example schema=common/ask def=ask_response op=read -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.common.ask": [
            {"version": "{{ ucp_version }}"}
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

A Business that supports multi-turn conversations returns a `conversation`
whose opaque `id` the Platform replays on the next turn. Turn 1 omits
`conversation` (a new conversation); turn 2 replays the identifier to build
on it.

Turn 1, request — a new conversation (no `conversation`):

<!-- ucp:example schema=common/ask def=ask_request op=create direction=request -->
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

<!-- ucp:example schema=common/ask def=ask_response op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.ask": [
        {"version": "{{ ucp_version }}"}
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

<!-- ucp:example schema=common/ask def=ask_request op=create direction=request -->
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

<!-- ucp:example schema=common/ask def=ask_response op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.ask": [
        {"version": "{{ ucp_version }}"}
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

When the Business cannot address the question, the response is still HTTP 200
with a populated `answer` stating the limitation.

<!-- ucp:example schema=common/ask def=ask_response op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.ask": [
        {"version": "{{ ucp_version }}"}
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

{{ header_fields('ask_business', 'common/rest.openapi.json') }}

### Specific Header Requirements

{{ header_requirements('ucp_agent') }}

* **Idempotency-Key**: The Common service declares `Idempotency-Key` as an
    optional request header. A Platform **SHOULD** include it on any request
    that carries a `conversation`, and **MAY** include it on any other (see
    [Conversation](index.md#conversation)). When present, the Business
    **MUST**:
    1. Store the key with the result for at least 24 hours.
    2. Return the cached result for a duplicate key whose operation, target
       resource, and payload all match the stored record, without appending a
       second turn.
    3. Return `409 Conflict` if the key is reused with a different operation, a
       different target resource, or a different payload.
    See [Message Signatures — Replay Protection](../../signatures.md#replay-protection)
    for the full payload-matching contract.

## Error Handling

UCP uses a two-layer error model separating transport errors from business outcomes.

### Transport Errors

Use HTTP status codes for protocol-level issues that prevent request processing:

| Status | Meaning |
| :--- | :--- |
| 400 | Bad Request - Malformed JSON or missing required parameters |
| 401 | Unauthorized - Missing or invalid authentication |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |

### Business Outcomes

All application-level outcomes return HTTP 200 with the UCP envelope and a
populated `answer`. Per-answer warnings or info notes ride in the optional
`messages` array. See
[Ask Overview](index.md#messages-and-error-handling) for message semantics.

#### Example: Answer with a Disclosure Warning

When an answer touches on a regulated disclosure (allergens, safety, legal),
the binding disclosure is referenced as a warning with
`presentation: "disclosure"`. The answer itself states the limitation and
defers to the binding source.

<!-- ucp:example schema=common/ask def=ask_response op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.ask": [
        {"version": "{{ ucp_version }}"}
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

### UCP Response Ask {: #ucp-response-ask-schema }

{{ extension_schema_fields('ucp.json#/$defs/response_ask_schema', 'common/ask/rest') }}

### Conversation {: #conversation }

{{ extension_schema_fields('ask.json#/$defs/conversation', 'common/ask/rest') }}

### Error Response {: #error-response }

{{ schema_fields('types/error_response', 'common/ask/rest') }}

## Conformance

A conforming REST transport implementation **MUST**:

1. When `dev.ucp.common.ask` is advertised in the Business's UCP profile, expose
   `POST /ask` under the `dev.ucp.common` service's REST `endpoint`.
2. Validate request bodies against the [Ask schema](index.md).
3. Return HTTP 200 for every well-formed, authorized, in-limits request; convey
   business outcomes through the `answer` and `messages` array, and use HTTP
   error status codes only for transport-level issues (authentication, rate
   limiting, unavailability, malformed input).
4. Return a populated `answer` on every successful response. A "can't answer"
   outcome is a populated `answer` that states the limitation plainly, **not**
   an omitted field, error code, or non-2xx status.
