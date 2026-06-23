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

# Ask - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the
[Ask Capability](index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability through their UCP profile at
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
          "transport": "mcp",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
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

### Request Metadata

MCP clients **MUST** include a `meta` object in every request containing
protocol metadata:

<!-- ucp:example schema=shopping/ask def=ask_request op=create direction=request extract=$.params.arguments.ask -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "ask_business",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
        }
      },
      "ask": {
        "query": "What is your return policy for sale items?"
      }
    }
  }
}
```

Requests **MUST** include `meta["ucp-agent"]` for version compatibility and
capability negotiation.

## Tools

| Tool | Capability | Description |
| :--- | :--- | :--- |
| `ask_business` | [Ask](index.md) | Ask the business about products, policies, services, and questions other capabilities can't answer. |

### `ask_business`

Maps to the [Ask](index.md) capability.

#### Ask Request

{{ extension_schema_fields(
  'ask.json#/$defs/ask_request', 'ask/mcp'
) }}

#### Ask Response

{{ extension_schema_fields(
  'ask.json#/$defs/ask_response', 'ask/mcp'
) }}

#### Ask Example

The buyer asks a policy question about a specific product. `ids` grounds the
question against specific items and accepts product IDs, variant IDs, and
secondary identifiers such as SKU, handle, or URL — so the platform can pass
whichever it already has, here the product page URL.

=== "Request"

    <!-- ucp:example schema=shopping/ask def=ask_request op=create direction=request extract=$.params.arguments.ask -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "ask_business",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
            }
          },
          "ask": {
            "query": "What is your return policy for these on sale?",
            "ids": ["https://business.example.com/products/winter-jacket"],
            "context": {
              "address_country": "US",
              "language": "en",
              "intent": "buying a discounted winter jacket as a gift"
            }
          }
        }
      }
    }
    ```

=== "Response"

    <!-- ucp:example schema=shopping/ask def=ask_response op=read direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
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
      }
    }
    ```

#### Multi-turn Example

A business that supports multi-turn conversations returns a `conversation` GID
the platform replays on the next turn. Turn 1 omits `conversation` (new
conversation); turn 2 replays the GID to build on it.

Turn 1, request — a new conversation (no GID):

<!-- ucp:example schema=shopping/ask def=ask_request op=create direction=request extract=$.params.arguments.ask -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "ask_business",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
        }
      },
      "ask": {
        "query": "Is this jacket warm enough for winter?",
        "ids": ["https://business.example.com/products/winter-jacket"]
      }
    }
  }
}
```

Turn 1, response — the business issues a `conversation` GID:

<!-- ucp:example schema=shopping/ask def=ask_response op=read direction=response extract=$.result.structuredContent -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
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
      "conversation": { "id": "conv_9a3f2e7b", "expires_at": "2026-06-22T18:30:00Z" }
    }
  }
}
```

Turn 2, request — replay the GID to continue:

<!-- ucp:example schema=shopping/ask def=ask_request op=create direction=request extract=$.params.arguments.ask -->
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "ask_business",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
        }
      },
      "ask": {
        "query": "And is it waterproof?",
        "conversation": { "id": "conv_9a3f2e7b" }
      }
    }
  }
}
```

Turn 2, response:

<!-- ucp:example schema=shopping/ask def=ask_response op=read direction=response extract=$.result.structuredContent -->
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "structuredContent": {
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
      "conversation": { "id": "conv_9a3f2e7b", "expires_at": "2026-06-22T18:30:00Z" }
    }
  }
}
```

#### "Can't Answer" Example

When the business cannot address the question, the response is still a
successful result with a populated `answer` stating the limitation.

<!-- ucp:example schema=shopping/ask def=ask_response op=read direction=response extract=$.result.structuredContent -->
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "structuredContent": {
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
  }
}
```

## Error Handling

UCP uses a two-layer error model separating transport errors from business outcomes.

### Transport Errors

Transport-level failures (authentication, rate limiting, unavailability) that
prevent request processing are returned as JSON-RPC `error`. See the
[Core Specification](../overview.md#error-codes) for the complete error code
registry and JSON-RPC error code mappings.

### Business Outcomes

All application-level outcomes return a successful JSON-RPC result with the UCP
envelope and a populated `answer`. Per-answer warnings or info notes ride in
the optional `messages` array. See
[Ask Overview](index.md#messages-and-error-handling) for message semantics.

#### Example: Answer with a Disclosure Warning

When an answer touches on a regulated disclosure (allergens, safety, legal),
the binding disclosure is referenced as a warning with
`presentation: "disclosure"`. The answer itself states the limitation and
defers to the binding source.

<!-- ucp:example schema=shopping/ask def=ask_response op=read direction=response extract=$.result.structuredContent -->
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "structuredContent": {
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
  }
}
```

## Entities

### UCP Response Ask {: #ucp-response-ask-schema }

{{ extension_schema_fields('ucp.json#/$defs/response_ask_schema', 'ask/mcp') }}

### Error Response {: #error-response }

{{ schema_fields('types/error_response', 'ask/mcp') }}

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0.
2. When `dev.ucp.shopping.ask` is advertised in the business's UCP profile, expose the `ask_business` tool.
3. Validate tool inputs against the [Ask schema](index.md).
4. Return a successful JSON-RPC result for every well-formed, authorized,
   in-limits request; convey business outcomes through the `answer` and
   `messages` array, and use JSON-RPC errors only for transport-level issues
   (authentication, rate limiting, unavailability, malformed input).
5. Return a populated `answer` on every successful response. A "can't answer"
   outcome is a populated `answer` that states the limitation plainly, **not**
   an omitted field, error code, or JSON-RPC error.
