# Cart Capability - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the [Cart Capability](https://ucp.dev/draft/specification/cart/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "2026-01-15",
    "services": {
      "dev.ucp.shopping": {
        "version": "2026-01-15",
        "spec": "https://ucp.dev/specification/overview",
        "mcp": {
          "schema": "https://ucp.dev/services/shopping/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
        }
      }
    },
    "capabilities": [
      {
        "name": "dev.ucp.shopping.checkout",
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specification/checkout",
        "schema": "https://ucp.dev/schemas/shopping/checkout.json"
      },
      {
        "name": "dev.ucp.shopping.cart",
        "version": "2026-01-15",
        "spec": "https://ucp.dev/specification/cart",
        "schema": "https://ucp.dev/schemas/shopping/cart.json"
      }
    ]
  }
}
```

### Platform Profile Advertisement

MCP clients **MUST** include the UCP platform profile URI with every request. The platform profile is included in the `_meta.ucp` structure within the request parameters:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "create_cart",
  "params": {
    "_meta": {
      "ucp": {
        "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
      }
    },
    "idempotency_key": "..."
  }
}
```

The `_meta.ucp.profile` field **MUST** be present in every MCP tool invocation to enable version compatibility checking and capability negotiation.

## Tools

UCP Capabilities map 1:1 to MCP Tools.

### Identifier Pattern

MCP tools separate resource identification from payload data:

- **Requests:** For operations on existing carts (`get`, `update`, `cancel`), a top-level `id` parameter identifies the target resource. The `cart` object in the request payload **MUST NOT** contain an `id` field.
- **Responses:** All responses include `cart.id` as part of the full resource state.
- **Create:** The `create_cart` operation does not require an `id` in the request, and the response includes the newly assigned `cart.id`.

| Tool          | Operation                                                            | Description            |
| ------------- | -------------------------------------------------------------------- | ---------------------- |
| `create_cart` | [Create Cart](https://ucp.dev/draft/specification/cart/#create-cart) | Create a cart session. |
| `get_cart`    | [Get Cart](https://ucp.dev/draft/specification/cart/#get-cart)       | Get a cart session.    |
| `update_cart` | [Update Cart](https://ucp.dev/draft/specification/cart/#update-cart) | Update a cart session. |
| `cancel_cart` | [Cancel Cart](https://ucp.dev/draft/specification/cart/#cancel-cart) | Cancel a cart session. |

### `create_cart`

Maps to the [Create Cart](https://ucp.dev/draft/specification/cart/#create-cart) operation.

#### Input Schema

**Error:** Schema 'cart.create' not found in any schema directory.

#### Output Schema

| Name         | Type                                                                            | Required | Description                                                                                                                                        |
| ------------ | ------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | [UCP Response Cart Schema](/draft/specification/cart/#ucp-response-cart-schema) | **Yes**  | Protocol metadata for discovery profiles and responses. Uses slim schema pattern with context-specific required fields.                            |
| id           | string                                                                          | **Yes**  | Unique cart identifier.                                                                                                                            |
| line_items   | Array\[[Line Item Response](/draft/specification/cart/#line-item-response)\]    | **Yes**  | Cart line items. Same structure as checkout. Full replacement on update.                                                                           |
| context      | [Context](/draft/specification/cart/#context)                                   | No       | Buyer signals for localization (country, region, postal_code). Merchant uses for pricing, availability, currency. Falls back to geo-IP if omitted. |
| buyer        | [Buyer](/draft/specification/cart/#buyer)                                       | No       | Optional buyer information for personalized estimates.                                                                                             |
| currency     | string                                                                          | **Yes**  | ISO 4217 currency code. Determined by merchant based on context or geo-IP.                                                                         |
| totals       | Array\[[Total Response](/draft/specification/cart/#total-response)\]            | **Yes**  | Estimated cost breakdown. May be partial if shipping/tax not yet calculable.                                                                       |
| messages     | Array\[[Message](/draft/specification/cart/#message)\]                          | No       | Validation messages, warnings, or informational notices.                                                                                           |
| links        | Array\[[Link](/draft/specification/cart/#link)\]                                | No       | Optional merchant links (policies, FAQs).                                                                                                          |
| continue_url | string                                                                          | No       | URL for cart handoff and session recovery. Enables sharing and human-in-the-loop flows.                                                            |
| expires_at   | string                                                                          | No       | Cart expiry timestamp (RFC 3339). Optional.                                                                                                        |

#### Example

```json
{
  "jsonrpc": "2.0",
  "method": "create_cart",
  "params": {
    "_meta": {
      "ucp": {
        "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
      }
    },
    "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
    "cart": {
      "line_items": [
        {
          "item": {
            "id": "item_123"
          },
          "quantity": 2
        }
      ],
      "context": {
        "address_country": "US",
        "address_region": "CA",
        "postal_code": "94105"
      }
    }
  },
  "id": 1
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "ucp": {
      "version": "2026-01-15",
      "capabilities": [
        {
          "name": "dev.ucp.shopping.checkout",
          "version": "2026-01-11"
        },
        {
          "name": "dev.ucp.shopping.cart",
          "version": "2026-01-15"
        }
      ]
    },
    "id": "cart_abc123",
    "line_items": [
      {
        "id": "li_1",
        "item": {
          "id": "item_123",
          "title": "Red T-Shirt",
          "price": 2500
        },
        "quantity": 2,
        "totals": [
          {"type": "subtotal", "amount": 5000},
          {"type": "total", "amount": 5000}
        ]
      }
    ],
    "currency": "USD",
    "totals": [
      {
        "type": "subtotal",
        "amount": 5000
      },
      {
        "type": "total",
        "amount": 5000
      }
    ],
    "continue_url": "https://business.example.com/checkout?cart=cart_abc123",
    "expires_at": "2026-01-16T12:00:00Z"
  }
}
```

### `get_cart`

Maps to the [Get Cart](https://ucp.dev/draft/specification/cart/#get-cart) operation.

#### Input Schema

- `id` (String, required): The ID of the cart session.

#### Output Schema

| Name         | Type                                                                            | Required | Description                                                                                                                                        |
| ------------ | ------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | [UCP Response Cart Schema](/draft/specification/cart/#ucp-response-cart-schema) | **Yes**  | Protocol metadata for discovery profiles and responses. Uses slim schema pattern with context-specific required fields.                            |
| id           | string                                                                          | **Yes**  | Unique cart identifier.                                                                                                                            |
| line_items   | Array\[[Line Item Response](/draft/specification/cart/#line-item-response)\]    | **Yes**  | Cart line items. Same structure as checkout. Full replacement on update.                                                                           |
| context      | [Context](/draft/specification/cart/#context)                                   | No       | Buyer signals for localization (country, region, postal_code). Merchant uses for pricing, availability, currency. Falls back to geo-IP if omitted. |
| buyer        | [Buyer](/draft/specification/cart/#buyer)                                       | No       | Optional buyer information for personalized estimates.                                                                                             |
| currency     | string                                                                          | **Yes**  | ISO 4217 currency code. Determined by merchant based on context or geo-IP.                                                                         |
| totals       | Array\[[Total Response](/draft/specification/cart/#total-response)\]            | **Yes**  | Estimated cost breakdown. May be partial if shipping/tax not yet calculable.                                                                       |
| messages     | Array\[[Message](/draft/specification/cart/#message)\]                          | No       | Validation messages, warnings, or informational notices.                                                                                           |
| links        | Array\[[Link](/draft/specification/cart/#link)\]                                | No       | Optional merchant links (policies, FAQs).                                                                                                          |
| continue_url | string                                                                          | No       | URL for cart handoff and session recovery. Enables sharing and human-in-the-loop flows.                                                            |
| expires_at   | string                                                                          | No       | Cart expiry timestamp (RFC 3339). Optional.                                                                                                        |

#### Example

```json
{
  "jsonrpc": "2.0",
  "method": "get_cart",
  "params": {
    "_meta": {
      "ucp": {
        "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
      }
    },
    "id": "cart_abc123"
  },
  "id": 1
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "ucp": {
      "version": "2026-01-15",
      "capabilities": [
        {
          "name": "dev.ucp.shopping.checkout",
          "version": "2026-01-11"
        },
        {
          "name": "dev.ucp.shopping.cart",
          "version": "2026-01-15"
        }
      ]
    },
    "id": "cart_abc123",
    "line_items": [
      {
        "id": "li_1",
        "item": {
          "id": "item_123",
          "title": "Red T-Shirt",
          "price": 2500
        },
        "quantity": 2,
        "totals": [
          {"type": "subtotal", "amount": 5000},
          {"type": "total", "amount": 5000}
        ]
      }
    ],
    "currency": "USD",
    "totals": [
      {
        "type": "subtotal",
        "amount": 5000
      },
      {
        "type": "total",
        "amount": 5000
      }
    ],
    "continue_url": "https://business.example.com/checkout?cart=cart_abc123",
    "expires_at": "2026-01-16T12:00:00Z"
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "ucp": {
      "version": "2026-01-15",
      "capabilities": [
        {
          "name": "dev.ucp.shopping.cart",
          "version": "2026-01-15"
        }
      ]
    },
    "messages": [
      {
        "type": "error",
        "code": "NOT_FOUND",
        "content": "Cart not found or has expired"
      }
    ],
    "continue_url": "https://merchant.com/"
  }
}
```

### `update_cart`

Maps to the [Update Cart](https://ucp.dev/draft/specification/cart/#update-cart) operation.

#### Input Schema

- `id` (String, required): The ID of the cart session to update.

**Error:** Schema 'cart.update' not found in any schema directory.

#### Output Schema

| Name         | Type                                                                            | Required | Description                                                                                                                                        |
| ------------ | ------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | [UCP Response Cart Schema](/draft/specification/cart/#ucp-response-cart-schema) | **Yes**  | Protocol metadata for discovery profiles and responses. Uses slim schema pattern with context-specific required fields.                            |
| id           | string                                                                          | **Yes**  | Unique cart identifier.                                                                                                                            |
| line_items   | Array\[[Line Item Response](/draft/specification/cart/#line-item-response)\]    | **Yes**  | Cart line items. Same structure as checkout. Full replacement on update.                                                                           |
| context      | [Context](/draft/specification/cart/#context)                                   | No       | Buyer signals for localization (country, region, postal_code). Merchant uses for pricing, availability, currency. Falls back to geo-IP if omitted. |
| buyer        | [Buyer](/draft/specification/cart/#buyer)                                       | No       | Optional buyer information for personalized estimates.                                                                                             |
| currency     | string                                                                          | **Yes**  | ISO 4217 currency code. Determined by merchant based on context or geo-IP.                                                                         |
| totals       | Array\[[Total Response](/draft/specification/cart/#total-response)\]            | **Yes**  | Estimated cost breakdown. May be partial if shipping/tax not yet calculable.                                                                       |
| messages     | Array\[[Message](/draft/specification/cart/#message)\]                          | No       | Validation messages, warnings, or informational notices.                                                                                           |
| links        | Array\[[Link](/draft/specification/cart/#link)\]                                | No       | Optional merchant links (policies, FAQs).                                                                                                          |
| continue_url | string                                                                          | No       | URL for cart handoff and session recovery. Enables sharing and human-in-the-loop flows.                                                            |
| expires_at   | string                                                                          | No       | Cart expiry timestamp (RFC 3339). Optional.                                                                                                        |

#### Example

```json
{
  "jsonrpc": "2.0",
  "method": "update_cart",
  "params": {
    "_meta": {
      "ucp": {
        "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
      }
    },
    "id": "cart_abc123",
    "cart": {
      "line_items": [
        {
          "item": {
            "id": "item_123"
          },
          "quantity": 3
        },
        {
          "item": {
            "id": "item_456"
          },
          "quantity": 1
        }
      ],
      "context": {
        "address_country": "US",
        "address_region": "CA",
        "postal_code": "94105"
      }
    }
  },
  "id": 2
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "ucp": {
      "version": "2026-01-15",
      "capabilities": [
        {
          "name": "dev.ucp.shopping.checkout",
          "version": "2026-01-11"
        },
        {
          "name": "dev.ucp.shopping.cart",
          "version": "2026-01-15"
        }
      ]
    },
    "id": "cart_abc123",
    "line_items": [
      {
        "id": "li_1",
        "item": {
          "id": "item_123",
          "title": "Red T-Shirt",
          "price": 2500
        },
        "quantity": 3,
        "totals": [
          {"type": "subtotal", "amount": 7500},
          {"type": "total", "amount": 7500}
        ]
      },
      {
        "id": "li_2",
        "item": {
          "id": "item_456",
          "title": "Blue Jeans",
          "price": 7500
        },
        "quantity": 1,
        "totals": [
          {"type": "subtotal", "amount": 7500},
          {"type": "total", "amount": 7500}
        ]
      }
    ],
    "currency": "USD",
    "totals": [
      {
        "type": "subtotal",
        "amount": 15000
      },
      {
        "type": "total",
        "amount": 15000
      }
    ],
    "continue_url": "https://business.example.com/checkout?cart=cart_abc123",
    "expires_at": "2026-01-16T12:00:00Z"
  }
}
```

### `cancel_cart`

Maps to the [Cancel Cart](https://ucp.dev/draft/specification/cart/#cancel-cart) operation.

#### Input Schema

- `id` (String, required): The ID of the cart session.
- `idempotency_key` (String, UUID, required): Unique key for retry safety.

#### Output Schema

| Name         | Type                                                                            | Required | Description                                                                                                                                        |
| ------------ | ------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | [UCP Response Cart Schema](/draft/specification/cart/#ucp-response-cart-schema) | **Yes**  | Protocol metadata for discovery profiles and responses. Uses slim schema pattern with context-specific required fields.                            |
| id           | string                                                                          | **Yes**  | Unique cart identifier.                                                                                                                            |
| line_items   | Array\[[Line Item Response](/draft/specification/cart/#line-item-response)\]    | **Yes**  | Cart line items. Same structure as checkout. Full replacement on update.                                                                           |
| context      | [Context](/draft/specification/cart/#context)                                   | No       | Buyer signals for localization (country, region, postal_code). Merchant uses for pricing, availability, currency. Falls back to geo-IP if omitted. |
| buyer        | [Buyer](/draft/specification/cart/#buyer)                                       | No       | Optional buyer information for personalized estimates.                                                                                             |
| currency     | string                                                                          | **Yes**  | ISO 4217 currency code. Determined by merchant based on context or geo-IP.                                                                         |
| totals       | Array\[[Total Response](/draft/specification/cart/#total-response)\]            | **Yes**  | Estimated cost breakdown. May be partial if shipping/tax not yet calculable.                                                                       |
| messages     | Array\[[Message](/draft/specification/cart/#message)\]                          | No       | Validation messages, warnings, or informational notices.                                                                                           |
| links        | Array\[[Link](/draft/specification/cart/#link)\]                                | No       | Optional merchant links (policies, FAQs).                                                                                                          |
| continue_url | string                                                                          | No       | URL for cart handoff and session recovery. Enables sharing and human-in-the-loop flows.                                                            |
| expires_at   | string                                                                          | No       | Cart expiry timestamp (RFC 3339). Optional.                                                                                                        |

#### Example

```json
{
  "jsonrpc": "2.0",
  "method": "cancel_cart",
  "params": {
    "_meta": {
      "ucp": {
        "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
      }
    },
    "id": "cart_abc123",
    "idempotency_key": "660e8400-e29b-41d4-a716-446655440001"
  },
  "id": 1
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "ucp": {
      "version": "2026-01-15",
      "capabilities": [
        {
          "name": "dev.ucp.shopping.checkout",
          "version": "2026-01-11"
        },
        {
          "name": "dev.ucp.shopping.cart",
          "version": "2026-01-15"
        }
      ]
    },
    "id": "cart_abc123",
    "line_items": [
      {
        "id": "li_1",
        "item": {
          "id": "item_123",
          "title": "Red T-Shirt",
          "price": 2500
        },
        "quantity": 2,
        "totals": [
          {"type": "subtotal", "amount": 5000},
          {"type": "total", "amount": 5000}
        ]
      }
    ],
    "currency": "USD",
    "totals": [
      {
        "type": "subtotal",
        "amount": 5000
      },
      {
        "type": "total",
        "amount": 5000
      }
    ],
    "continue_url": "https://business.example.com/checkout?cart=cart_abc123"
  }
}
```

## Error Handling

See the [Core Specification](https://ucp.dev/draft/specification/overview/#error-handling) for negotiation error handling (discovery failures, negotiation failures).

### Business Outcomes

Business outcomes (including not found and validation errors) are returned as JSON-RPC `result` with the UCP envelope and `messages`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "ucp": {
      "version": "2026-01-11",
      "capabilities": {
        "dev.ucp.shopping.cart": [{"version": "2026-01-11"}]
      }
    },
    "messages": [
      {
        "type": "error",
        "code": "NOT_FOUND",
        "content": "Cart not found or has expired"
      }
    ],
    "continue_url": "https://merchant.com/"
  }
}
```

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0 protocol correctly.
1. Provide all core cart tools defined in this specification.
1. Return negotiation failures per the [Core Specification](https://ucp.dev/draft/specification/overview/#error-handling).
1. Return business outcomes as JSON-RPC `result` with UCP envelope and `messages` array.
1. Validate tool inputs against UCP schemas.
1. Support HTTP transport with streaming.
