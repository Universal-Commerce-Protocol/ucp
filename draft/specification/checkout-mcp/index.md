# Checkout Capability - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the [Checkout Capability](https://ucp.dev/draft/specification/checkout/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "2026-01-11",
    "services": {
      "dev.ucp.shopping": {
        "version": "2026-01-11",
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
        "name": "dev.ucp.shopping.fulfillment",
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specification/fulfillment",
        "schema": "https://ucp.dev/schemas/shopping/fulfillment.json",
        "extends": "dev.ucp.shopping.checkout"
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
  "method": "create_checkout",
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

- **Requests:** For operations on existing checkouts (`get`, `update`, `complete`, `cancel`), a top-level `id` parameter identifies the target resource. The `checkout` object in the request payload **MUST NOT** contain an `id` field.
- **Responses:** All responses include `checkout.id` as part of the full resource state.
- **Create:** The `create_checkout` operation does not require an `id` in the request, and the response includes the newly assigned `checkout.id`.

| Tool                | Operation                                                                            | Description                |
| ------------------- | ------------------------------------------------------------------------------------ | -------------------------- |
| `create_checkout`   | [Create Checkout](https://ucp.dev/draft/specification/checkout/#create-checkout)     | Create a checkout session. |
| `get_checkout`      | [Get Checkout](https://ucp.dev/draft/specification/checkout/#get-checkout)           | Get a checkout session.    |
| `update_checkout`   | [Update Checkout](https://ucp.dev/draft/specification/checkout/#update-checkout)     | Update a checkout session. |
| `complete_checkout` | [Complete Checkout](https://ucp.dev/draft/specification/checkout/#complete-checkout) | Place the order.           |
| `cancel_checkout`   | [Cancel Checkout](https://ucp.dev/draft/specification/checkout/#cancel-checkout)     | Cancel a checkout session. |

### `create_checkout`

Maps to the [Create Checkout](https://ucp.dev/draft/specification/checkout/#create-checkout) operation.

#### Input Schema

- [Checkout](https://ucp.dev/draft/specification/checkout/#create-checkout) object.
  - Extensions (Optional):
    - `dev.ucp.shopping.buyer_consent`: [Buyer Consent](https://ucp.dev/draft/specification/buyer-consent/index.md)
    - `dev.ucp.shopping.fulfillment`: [Fulfillment](https://ucp.dev/draft/specification/fulfillment/index.md)
    - `dev.ucp.shopping.discount`: [Discount](https://ucp.dev/draft/specification/discount/index.md)
    - `dev.ucp.shopping.ap2_mandate`: [AP2 Mandates](https://ucp.dev/draft/specification/ap2-mandates/index.md)

#### Output Schema

- [Checkout](https://ucp.dev/draft/specification/checkout/#create-checkout) object.

#### Example

```json
{
  "jsonrpc": "2.0",
  "method": "create_checkout",
  "params": {
    "_meta": {
      "ucp": {
        "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
      }
    },
    "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
    "buyer": {
      "email": "jane.doe@example.com",
      "first_name": "Jane",
      "last_name": "Doe"
    },
    "line_items": [
      {
        "item": {
          "id": "item_123"
        },
        "quantity": 1
      }
    ],
    "currency": "USD",
    "fulfillment": {
      "methods": [
        {
          "type": "shipping",
          "destinations": [
            {
              "street_address": "123 Main St",
              "address_locality": "Springfield",
              "address_region": "IL",
              "postal_code": "62701",
              "address_country": "US"
            }
          ]
        }
      ]
    },
    "payment": {}
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
      "version": "2026-01-11",
      "capabilities": [
        {
          "name": "dev.ucp.shopping.checkout",
          "version": "2026-01-11"
        },
        {
          "name": "dev.ucp.shopping.fulfillment",
          "version": "2026-01-11"
        }
      ]
    },
    "id": "checkout_abc123",
    "status": "incomplete",
    "buyer": {
      "email": "jane.doe@example.com",
      "first_name": "Jane",
      "last_name": "Doe"
    },
    "line_items": [
      {
        "id": "item_123",
        "item": {
          "id": "item_123",
          "title": "Blue Jeans",
          "price": 5000
        },
        "quantity": 1,
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
        "type": "fulfillment",
        "display_text": "Shipping",
        "amount": 500
      },
      {
        "type": "total",
        "amount": 5500
      }
    ],
    "fulfillment": {
      "methods": [
        {
          "id": "shipping_1",
          "type": "shipping",
          "line_item_ids": ["item_123"],
          "selected_destination_id": "dest_home",
          "destinations": [
            {
              "id": "dest_home",
              "street_address": "123 Main St",
              "address_locality": "Springfield",
              "address_region": "IL",
              "postal_code": "62701",
              "address_country": "US"
            }
          ],
          "groups": [
            {
              "id": "package_1",
              "line_item_ids": ["item_123"],
              "selected_option_id": "standard",
              "options": [
                {
                  "id": "standard",
                  "title": "Standard Shipping",
                  "description": "Arrives in 5-7 business days",
                  "totals": [
                    {
                      "type": "total",
                      "amount": 500
                    }
                  ]
                },
                {
                  "id": "express",
                  "title": "Express Shipping",
                  "description": "Arrives in 2-3 business days",
                  "totals": [
                    {
                      "type": "total",
                      "amount": 1000
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    },
    "payment": {
      "handlers": [
        {
          "id": "handler_1",
          "name": "com.example.vendor.delegate_payment",
          "version": "2026-01-11",
          "spec": "https://example.vendor.com/specs/delegate-payment",
          "config_schema": "https://example.vendor.com/schemas/delegate-payment-config.json",
          "instrument_schemas": [
            "https://example.vendor.com/schemas/delegate-payment-instrument.json"
          ],
          "config": {}
        }
      ]
    },
    "links": [
      {
        "type": "privacy_policy",
        "url": "https://business.example.com/privacy"
      },
      {
        "type": "terms_of_service",
        "url": "https://business.example.com/terms"
      }
    ],
    "continue_url": "https://business.example.com/checkout-sessions/checkout_abc123",
    "expires_at": "2026-01-11T18:30:00Z"
  }
}
```

### `get_checkout`

Maps to the [Get Checkout](https://ucp.dev/draft/specification/checkout/#get-checkout) operation.

#### Input Schema

- `id` (String): The ID of the checkout session.

#### Output Schema

- [Checkout](https://ucp.dev/draft/specification/checkout/#get-checkout) object.

### `update_checkout`

Maps to the [Update Checkout](https://ucp.dev/draft/specification/checkout/#update-checkout) operation.

#### Input Schema

- `id` (String): The ID of the checkout session to update.
- [Checkout](https://ucp.dev/draft/specification/checkout/#update-checkout) object.
  - Extensions (Optional):
    - `dev.ucp.shopping.buyer_consent`: [Buyer Consent](https://ucp.dev/draft/specification/buyer-consent/index.md)
    - `dev.ucp.shopping.fulfillment`: [Fulfillment](https://ucp.dev/draft/specification/fulfillment/index.md)
    - `dev.ucp.shopping.discount`: [Discount](https://ucp.dev/draft/specification/discount/index.md)
    - `dev.ucp.shopping.ap2_mandate`: [AP2 Mandates](https://ucp.dev/draft/specification/ap2-mandates/index.md)

#### Output Schema

- [Checkout](https://ucp.dev/draft/specification/checkout/#update-checkout) object.

#### Example

```json
{
  "jsonrpc": "2.0",
  "method": "update_checkout",
  "params": {
    "_meta": {
      "ucp": {
        "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
      }
    },
    "id": "checkout_abc123",
    "buyer": {
      "email": "jane.doe@example.com",
      "first_name": "Jane",
      "last_name": "Doe"
    },
    "line_items": [
      {
        "item": {
          "id": "item_123"
        },
        "quantity": 1
      }
    ],
    "currency": "USD",
    "fulfillment": {
      "methods": [
        {
          "id": "shipping_1",
          "line_item_ids": ["item_123"],
          "groups": [
            {
              "id": "package_1",
              "selected_option_id": "express"
            }
          ]
        }
      ]
    },
    "payment": {}
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
      "version": "2026-01-11",
      "capabilities": [
        {
          "name": "dev.ucp.shopping.checkout",
          "version": "2026-01-11"
        },
        {
          "name": "dev.ucp.shopping.fulfillment",
          "version": "2026-01-11"
        }
      ]
    },
    "id": "checkout_abc123",
    "status": "incomplete",
    "buyer": {
      "email": "jane.doe@example.com",
      "first_name": "Jane",
      "last_name": "Doe"
    },
    "line_items": [
      {
        "id": "item_123",
        "item": {
          "id": "item_123",
          "title": "Blue Jeans",
          "price": 5000
        },
        "quantity": 1,
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
        "type": "fulfillment",
        "display_text": "Shipping",
        "amount": 1000
      },
      {
        "type": "total",
        "amount": 6000
      }
    ],
    "fulfillment": {
      "methods": [
        {
          "id": "shipping_1",
          "type": "shipping",
          "line_item_ids": ["item_123"],
          "selected_destination_id": "dest_home",
          "destinations": [
            {
              "id": "dest_home",
              "street_address": "123 Main St",
              "address_locality": "Springfield",
              "address_region": "IL",
              "postal_code": "62701",
              "address_country": "US"
            }
          ],
          "groups": [
            {
              "id": "package_1",
              "line_item_ids": ["item_123"],
              "selected_option_id": "express",
              "options": [
                {
                  "id": "standard",
                  "title": "Standard Shipping",
                  "description": "Arrives in 5-7 business days",
                  "totals": [
                    {
                      "type": "total",
                      "amount": 500
                    }
                  ]
                },
                {
                  "id": "express",
                  "title": "Express Shipping",
                  "description": "Arrives in 2-3 business days",
                  "totals": [
                    {
                      "type": "total",
                      "amount": 1000
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    },
    "payment": {
      "handlers": [
        {
          "id": "handler_1",
          "name": "com.example.vendor.delegate_payment",
          "version": "2026-01-11",
          "spec": "https://example.vendor.com/specs/delegate-payment",
          "config_schema": "https://example.vendor.com/schemas/delegate-payment-config.json",
          "instrument_schemas": [
            "https://example.vendor.com/schemas/delegate-payment-instrument.json"
          ],
          "config": {}
        }
      ]
    },
    "links": [
      {
        "type": "privacy_policy",
        "url": "https://business.example.com/privacy"
      },
      {
        "type": "terms_of_service",
        "url": "https://business.example.com/terms"
      }
    ],
    "continue_url": "https://business.example.com/checkout-sessions/checkout_abc123",
    "expires_at": "2026-01-11T18:30:00Z"
  }
}
```

### `complete_checkout`

Maps to the [Complete Checkout](https://ucp.dev/draft/specification/checkout/#complete-checkout) operation.

#### Input Schema

- `id` (String): The ID of the checkout session.
- `payment` ([Payment](https://ucp.dev/draft/specification/checkout/#payment), Optional): Payment instrument instance submitted by the buyer.
- `idempotency_key` (String, UUID): **Required**. Unique key for retry safety.

#### Output Schema

- [Checkout](https://ucp.dev/draft/specification/checkout/#complete-checkout) object, containing a partial `order` that holds only `id` and `permalink_url`.

### `cancel_checkout`

Maps to the [Cancel Checkout](https://ucp.dev/draft/specification/checkout/#cancel-checkout) operation.

#### Input Schema

- `id` (String): The ID of the checkout session.
- `idempotency_key` (String, UUID): **Required**. Unique key for retry safety.

#### Output Schema

- [Checkout](https://ucp.dev/draft/specification/checkout/#cancel-checkout) object with `status: canceled`.

## Error Handling

Error responses follow JSON-RPC 2.0 format while using the UCP error structure defined in the [Core Specification](https://ucp.dev/draft/specification/overview/index.md). The UCP error object is embedded in the JSON-RPC error's `data` field:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "status": "error",
      "errors": [
        {
          "code": "MERCHANDISE_NOT_AVAILABLE",
          "message": "One or more cart items are not available",
          "severity": "requires_buyer_input",
          "details": {
            "invalid_items": ["sku_999"]
          }
        }
      ]
    }
  }
}
```

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0 protocol correctly.
1. Provide all core checkout tools defined in this specification.
1. Handle errors with UCP-specific error codes embedded in the JSON-RPC error object.
1. Validate tool inputs against UCP schemas.
1. Support HTTP transport with streaming.
