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

Businesses advertise REST transport availability through their UCP profile at
`/.well-known/ucp`.

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.ask": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/ask",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/ask.json"
      }]
    },
    "payment_handlers": {}
  }
}
```

## Endpoints

| Endpoint | Method | Capability | Description |
| :--- | :--- | :--- | :--- |
| `/ask` | POST | [Ask](index.md) | Ask the business about products, policies, services, and questions other capabilities can't answer. |

### `POST /ask`

Maps to the [Ask](index.md) capability.

{{ method_fields('ask_business', 'rest.openapi.json', 'ask/rest') }}

#### Example

The buyer asks a policy question about a specific product, identified by its
page URL. `ids` accepts product IDs, variant IDs, and secondary identifiers
such as SKU, handle, or URL, so the platform can pass whichever it already has.

=== "Request"

    <!-- ucp:example schema=shopping/ask def=ask_request op=create direction=request -->
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

    <!-- ucp:example schema=shopping/ask def=ask_response op=read -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.shopping.ask": [
            {"version": "{{ ucp_version }}"}
          ]
        }
      },
      "answer": {
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

A business that supports multi-turn conversations returns a `conversation` GID
the platform replays on the next turn. Turn 1 omits `conversation` (new
conversation); turn 2 replays the GID to build on it.

Turn 1, request — a new conversation (no GID):

<!-- ucp:example schema=shopping/ask def=ask_request op=create direction=request -->
```json
POST /ask HTTP/1.1
Host: business.example.com
Content-Type: application/json

{
  "query": "Is this jacket warm enough for winter?",
  "ids": ["https://business.example.com/products/winter-jacket"]
}
```

Turn 1, response — the business issues a `conversation` GID:

<!-- ucp:example schema=shopping/ask def=ask_response op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.ask": [
        {"version": "{{ ucp_version }}"}
      ]
    }
  },
  "answer": {
    "plain": "Yes — it's insulated for sub-zero conditions and rated for harsh winter use."
  },
  "conversation": "conv_9a3f2e7b"
}
```

Turn 2, request — replay the GID to continue:

<!-- ucp:example schema=shopping/ask def=ask_request op=create direction=request -->
```json
POST /ask HTTP/1.1
Host: business.example.com
Content-Type: application/json

{
  "query": "And is it waterproof?",
  "conversation": "conv_9a3f2e7b"
}
```

Turn 2, response:

<!-- ucp:example schema=shopping/ask def=ask_response op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.ask": [
        {"version": "{{ ucp_version }}"}
      ]
    }
  },
  "answer": {
    "plain": "It's water-resistant with a durable water-repellent finish — good for snow and light rain, though not fully waterproof."
  },
  "conversation": "conv_9a3f2e7b"
}
```

#### "Can't Answer" Example

When the business cannot address the question, the response is still HTTP 200
with a populated `answer` stating the limitation.

<!-- ucp:example schema=shopping/ask def=ask_response op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.ask": [
        {"version": "{{ ucp_version }}"}
      ]
    }
  },
  "answer": {
    "plain": "I don't have information about competitor pricing. For questions about this store's products, I can help with policies, materials, fit, and availability."
  }
}
```

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

<!-- ucp:example schema=shopping/ask def=ask_response op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.ask": [
        {"version": "{{ ucp_version }}"}
      ]
    }
  },
  "answer": {
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

{{ extension_schema_fields('ucp.json#/$defs/response_ask_schema', 'ask/rest') }}

### Error Response {: #error-response }

{{ schema_fields('types/error_response', 'ask/rest') }}

## Conformance

A conforming REST transport implementation **MUST**:

1. When `dev.ucp.shopping.ask` is advertised in the business's UCP profile, expose `POST /ask`.
2. Validate request bodies against the [Ask schema](index.md).
3. Return HTTP 200 for every well-formed, authorized, in-limits request; convey
   business outcomes through the `answer` and `messages` array, and use HTTP
   error status codes only for transport-level issues (authentication, rate
   limiting, unavailability, malformed input).
4. Return a populated `answer` on every successful response. A "can't answer"
   outcome is a populated `answer` that states the limitation plainly, **not**
   an omitted field, error code, or non-2xx status.
