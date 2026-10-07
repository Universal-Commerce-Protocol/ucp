# Ask - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the [Ask Capability](http://ucp.dev/draft/specification/common/ask/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability for the Common service and the Ask capability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "draft",
    "services": {
      "dev.ucp.common": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/overview",
          "transport": "mcp",
          "schema": "https://ucp.dev/draft/services/common/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
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

### Request Metadata

A Platform using MCP **MUST** include a `meta` object with `meta["ucp-agent"].profile` in every request. The field identifies the Platform's UCP profile for version compatibility checks and capability negotiation. Protocol metadata stays in `meta`, separate from the domain request in `ask`:

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
          "profile": "https://platform.example/profiles/v2026-01/agent.json"
        }
      },
      "ask": {
        "query": "What is your return policy for sale items?"
      }
    }
  }
}
```

The Common service's `meta` also defines an optional `idempotency-key`, the MCP counterpart of the HTTP `Idempotency-Key` header. A Platform **SHOULD** include `meta["idempotency-key"]` on any request that carries a `conversation`, and **MAY** include it on any other; see [Conversation](http://ucp.dev/draft/specification/common/ask/#conversation) for the retry contract.

## Tools

| Tool           | Capability                                                    | Description                                                                                                         |
| -------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `ask_business` | [Ask](http://ucp.dev/draft/specification/common/ask/index.md) | Ask the Business about its resources, policies, and services, including questions other capabilities cannot answer. |

### `ask_business`

Maps to the [Ask](http://ucp.dev/draft/specification/common/ask/index.md) capability.

#### Ask Request

| Name         | Type                                               | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | -------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| query        | string                                             | **Required** | Natural-language question.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| conversation | object                                             | Optional     | Provide a conversation to continue it on a follow-up; omit to start a new one.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ids          | Array[string]                                      | Optional     | Optional identifiers that ground the question in any Business resource. A Business SHOULD accept its own Global IDs (GIDs) and MAY accept recognized secondary identifiers such as SKU, handle, or URL. GIDs self-describe to the Business; a Platform may send them as opaque grounding references. Examples include a product, location, cart, order, or booking.                                                                                                                                                                                                                                                                                                     |
| context      | [Context](/draft/specification/reference/#context) | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals      | [Signals](/draft/specification/reference/#signals) | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |

#### Ask Response

| Name         | Type                                                        | Requirement  | Description                                                                                                                                                                                                                                                                         |
| ------------ | ----------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | any                                                         | **Required** | UCP metadata for ask responses.                                                                                                                                                                                                                                                     |
| answer       | [Description](/draft/specification/reference/#description)  | **Required** | Answer provided by the Business. Plain text is required; Markdown and HTML are optional alternative encodings.                                                                                                                                                                      |
| conversation | object                                                      | Optional     | Business-issued conversation for multi-turn continuation. When returned, the business SHOULD retain its history until `expires_at` (or per its own policy) so a follow-up with the same `id` builds on it. An unresolved `id` starts a new conversation and is noted in `messages`. |
| links        | Array\[[Link](/draft/specification/reference/#link)\]       | Optional     | Optional links and references related to the answer. When a link refers to an addressable UCP resource, the Business SHOULD include its GID in the link's `id`.                                                                                                                     |
| messages     | Array\[[Message](/draft/specification/reference/#message)\] | Optional     | Errors, warnings, or informational messages about the answer or its grounding.                                                                                                                                                                                                      |

#### Ask Example

The Buyer asks a policy question about a specific product, identified here by its page URL. `ids` grounds the question in any Business resource, by a Business-issued Global ID (GID) or by a secondary identifier the Business recognizes — a SKU, handle, or URL — so the Platform can pass whichever it already has (see [Scoping a Question](http://ucp.dev/draft/specification/common/ask/#scoping-a-question)).

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
          "profile": "https://platform.example/profiles/v2026-01/agent.json"
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

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
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
  }
}
```

#### Multi-turn Example

A Business that supports multi-turn conversations returns a `conversation` whose opaque `id` the Platform replays on the next turn. Turn 1 omits `conversation` (a new conversation); turn 2 replays the identifier to build on it.

Turn 1, request — a new conversation (no `conversation`):

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
          "profile": "https://platform.example/profiles/v2026-01/agent.json"
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

Turn 1, response — the Business issues a conversation identifier:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
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
  }
}
```

Turn 2, request — replay the identifier to continue:

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
          "profile": "https://platform.example/profiles/v2026-01/agent.json"
        },
        "idempotency-key": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
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

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "structuredContent": {
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
  }
}
```

#### "Can't Answer" Example

When the Business cannot address the question, the response is still a successful result with a populated `answer` stating the limitation.

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "structuredContent": {
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
  }
}
```

## Error Handling

UCP uses a two-layer error model separating transport errors from business outcomes.

### Transport Errors

Transport-level failures (authentication, rate limiting, unavailability) that prevent request processing are returned as JSON-RPC `error`. See the [Core Specification](http://ucp.dev/draft/specification/overview/#error-codes) for the complete error code registry and JSON-RPC error code mappings.

### Business Outcomes

All application-level outcomes return a successful JSON-RPC result with the UCP envelope and a populated `answer`. Per-answer warnings or info notes ride in the optional `messages` array. See [Ask Overview](http://ucp.dev/draft/specification/common/ask/#messages-and-error-handling) for message semantics.

#### Example: Answer with a Disclosure Warning

When an answer touches on a regulated disclosure (allergens, safety, legal), the binding disclosure is referenced as a warning with `presentation: "disclosure"`. The answer itself states the limitation and defers to the binding source.

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "structuredContent": {
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
  }
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

### Error Response

| Name         | Type                                                        | Requirement  | Description                                                       |
| ------------ | ----------------------------------------------------------- | ------------ | ----------------------------------------------------------------- |
| ucp          | UCP Error                                                   | **Required** | UCP protocol metadata. Status MUST be 'error' for error response. |
| messages     | Array\[[Message](/draft/specification/reference/#message)\] | **Required** | Array of messages describing why the operation failed.            |
| continue_url | string                                                      | Optional     | URL for buyer handoff or session recovery.                        |

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0.
1. When `dev.ucp.common.ask` is advertised in the Business's UCP profile, expose the `ask_business` tool at the `dev.ucp.common` service's MCP `endpoint`.
1. Validate tool inputs against the [Ask schema](http://ucp.dev/draft/specification/common/ask/index.md).
1. Return a successful JSON-RPC result for every well-formed, authorized, in-limits request; convey business outcomes through the `answer` and `messages` array, and use JSON-RPC errors only for transport-level issues (authentication, rate limiting, unavailability, malformed input).
1. Return a populated `answer` on every successful response. A "can't answer" outcome is a populated `answer` that states the limitation plainly, **not** an omitted field, error code, or JSON-RPC error.
