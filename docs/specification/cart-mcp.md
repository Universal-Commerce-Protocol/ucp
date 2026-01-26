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

# Cart Capability - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the
[Cart Capability](cart.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability through their UCP profile at
`/.well-known/ucp`.

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

MCP clients **MUST** include the UCP platform profile URI with every request.
The platform profile is included in the `_meta.ucp` structure within the request
parameters:

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

The `_meta.ucp.profile` field **MUST** be present in every MCP tool invocation
to enable version compatibility checking and capability negotiation.

## Tools

UCP Capabilities map 1:1 to MCP Tools.

### Identifier Pattern

MCP tools separate resource identification from payload data:

* **Requests:** For operations on existing carts (`get`, `update`, `cancel`),
    a top-level `id` parameter identifies the target resource. The `cart`
    object in the request payload **MUST NOT** contain an `id` field.
* **Responses:** All responses include `cart.id` as part of the full resource state.
* **Create:** The `create_cart` operation does not require an `id` in the
    request, and the response includes the newly assigned `cart.id`.

| Tool | Operation | Description |
| :---- | :---- | :---- |
| `create_cart` | [Create Cart](cart.md#create-cart) | Create a cart session. |
| `get_cart` | [Get Cart](cart.md#get-cart) | Get a cart session. |
| `update_cart` | [Update Cart](cart.md#update-cart) | Update a cart session. |
| `cancel_cart` | [Cancel Cart](cart.md#cancel-cart) | Cancel a cart session. |

### `create_cart`

Maps to the [Create Cart](cart.md#create-cart) operation.

#### Input Schema

{{ schema_fields('cart.create_req', 'cart') }}

#### Output Schema

{{ schema_fields('cart_resp', 'cart') }}

#### Example

=== "Request"

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

=== "Response"

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

Maps to the [Get Cart](cart.md#get-cart) operation.

#### Input Schema

* `id` (String, required): The ID of the cart session.

#### Output Schema

{{ schema_fields('cart_resp', 'cart') }}

#### Example

=== "Request"

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

=== "Response"

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

=== "Not Found"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "error": {
        "code": -32602,
        "message": "Invalid params: cart not found"
      }
    }
    ```

### `update_cart`

Maps to the [Update Cart](cart.md#update-cart) operation.

#### Input Schema

* `id` (String, required): The ID of the cart session to update.

{{ schema_fields('cart.update_req', 'cart') }}

#### Output Schema

{{ schema_fields('cart_resp', 'cart') }}

#### Example

=== "Request"

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

=== "Response"

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

Maps to the [Cancel Cart](cart.md#cancel-cart) operation.

#### Input Schema

* `id` (String, required): The ID of the cart session.
* `idempotency_key` (String, UUID, required): Unique key for retry safety.

#### Output Schema

{{ schema_fields('cart_resp', 'cart') }}

#### Example

=== "Request"

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

=== "Response"

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

Error responses follow JSON-RPC 2.0 format.

### Not Found (-32602)

Returned when cart does not exist, has expired, or was canceled:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params: cart not found"
  }
}
```

### Validation Errors

Validation errors are returned in the cart's `messages` array. The operation
succeeds and returns the cart state with messages indicating issues:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "ucp": { ... },
    "id": "cart_abc123",
    "line_items": [ ... ],
    "messages": [
      {
        "type": "error",
        "code": "invalid_quantity",
        "path": "$.line_items[0].quantity",
        "content": "Quantity must be at least 1"
      }
    ],
    ...
  }
}
```

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0 protocol correctly.
2. Provide all core cart tools defined in this specification.
3. Handle errors with appropriate JSON-RPC error codes.
4. Validate tool inputs against UCP schemas.
5. Support HTTP transport with streaming.
