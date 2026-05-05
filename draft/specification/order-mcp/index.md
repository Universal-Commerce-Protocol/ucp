# Order Capability - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the [Order Capability](http://ucp.dev/draft/specification/order/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "draft",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/overview",
          "transport": "mcp",
          "schema": "https://ucp.dev/draft/services/shopping/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.order": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/order",
          "schema": "https://ucp.dev/draft/schemas/shopping/order.json"
        }
      ]
    }
  }
}
```

### Request Metadata

MCP clients **MUST** include a `meta` object in every request containing protocol metadata:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_order",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/.well-known/ucp"
        }
      },
      "id": "order_abc123"
    }
  }
}
```

The `meta["ucp-agent"]` field is **required** on all requests to enable [capability negotiation](http://ucp.dev/draft/specification/overview/#negotiation-protocol). Platforms **MAY** include additional metadata fields.

## Tools

UCP Capabilities map 1:1 to MCP Tools.

| Tool        | Operation                                                        | Description                        |
| ----------- | ---------------------------------------------------------------- | ---------------------------------- |
| `get_order` | [Get Order](http://ucp.dev/draft/specification/order/#get-order) | Get the current state of an order. |

### `get_order`

Maps to the [Get Order](http://ucp.dev/draft/specification/order/#get-order) operation. Returns the current-state snapshot of an order.

#### Input Schema

- `meta` (Object, required): Request metadata with `ucp-agent.profile`.
- `id` (String, required): The ID of the order.

#### Output Schema

| Name          | Type                                                                        | Required | Description                                                                                                                                   |
| ------------- | --------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp           | any                                                                         | **Yes**  | UCP metadata for order responses. No payment handlers needed post-purchase.                                                                   |
| id            | string                                                                      | **Yes**  | Unique order identifier.                                                                                                                      |
| label         | string                                                                      | No       | Human-readable label for identifying the order. MUST only be provided by the business.                                                        |
| checkout_id   | string                                                                      | **Yes**  | Associated checkout ID for reconciliation.                                                                                                    |
| permalink_url | string                                                                      | **Yes**  | Permalink to access the order on merchant site.                                                                                               |
| line_items    | Array\[[Order Line Item](/draft/specification/reference/#order-line-item)\] | **Yes**  | Line items representing what was purchased — can change post-order via edits or exchanges.                                                    |
| fulfillment   | object                                                                      | **Yes**  | Fulfillment data: buyer expectations and what actually happened.                                                                              |
| adjustments   | Array\[[Adjustment](/draft/specification/reference/#adjustment)\]           | No       | Post-order events (refunds, returns, credits, disputes, cancellations, etc.) that exist independently of fulfillment.                         |
| currency      | string                                                                      | **Yes**  | ISO 4217 currency code. MUST match the currency from the originating checkout session.                                                        |
| totals        | [Totals](/draft/specification/reference/#totals)                            | **Yes**  | Different totals for the order.                                                                                                               |
| messages      | Array\[[Message](/draft/specification/reference/#message)\]                 | No       | Business outcome messages (errors, warnings, informational). Present when the business needs to communicate status or issues to the platform. |
| attribution   | [Attribution](/draft/specification/reference/#attribution)                  | No       | Snapshot of the attribution associated with the originating checkout. Read-only on the order.                                                 |

#### Example

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_order",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/.well-known/ucp"
        }
      },
      "id": "order_abc123"
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
          "dev.ucp.shopping.order": [{"version": "draft"}]
        }
      },
      "id": "order_abc123",
      "checkout_id": "checkout_xyz789",
      "permalink_url": "https://business.example.com/orders/abc123",
      "currency": "USD",
      "line_items": [
        {
          "id": "li_shoes",
          "item": { "id": "prod_shoes", "title": "Running Shoes", "price": 3000 },
          "quantity": { "total": 1, "fulfilled": 1 },
          "totals": [
            {"type": "subtotal", "amount": 3000},
            {"type": "total", "amount": 3000}
          ],
          "status": "fulfilled"
        }
      ],
      "fulfillment": {
        "expectations": [
          {
            "id": "exp_1",
            "line_items": [{ "id": "li_shoes", "quantity": 1 }],
            "method_type": "shipping",
            "destination": {
              "street_address": "123 Main St",
              "address_locality": "Austin",
              "address_region": "TX",
              "address_country": "US",
              "postal_code": "78701"
            },
            "description": "Delivered"
          }
        ],
        "events": [
          {
            "id": "evt_1",
            "occurred_at": "2026-01-08T10:30:00Z",
            "type": "delivered",
            "line_items": [{ "id": "li_shoes", "quantity": 1 }],
            "tracking_number": "1Z999AA10123456784",
            "tracking_url": "https://ups.com/track/1Z999AA10123456784",
            "description": "Delivered to front door"
          }
        ]
      },
      "adjustments": [],
      "totals": [
        { "type": "subtotal", "amount": 3000 },
        { "type": "fulfillment", "amount": 800 },
        { "type": "tax", "amount": 304 },
        { "type": "total", "amount": 4104 }
      ]
    },
    "content": [
      {
        "type": "text",
        "text": "{\"ucp\":{...},\"id\":\"order_abc123\",...}"
      }
    ]
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
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.order": [{"version": "draft"}]
        }
      },
      "messages": [
        {
          "type": "error",
          "code": "not_found",
          "severity": "unrecoverable",
          "content": "Order not found."
        }
      ]
    },
    "content": [
      {
        "type": "text",
        "text": "Order not found."
      }
    ]
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
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.order": [{"version": "draft"}]
        }
      },
      "messages": [
        {
          "type": "error",
          "code": "unauthorized",
          "severity": "unrecoverable",
          "content": "Not authorized to access this order."
        }
      ]
    },
    "content": [
      {
        "type": "text",
        "text": "Not authorized to access this order."
      }
    ]
  }
}
```

## Error Handling

When the business cannot return an order, the response includes a `messages` array describing the outcome. Platforms **MUST** check `messages` before accessing order fields.

## Conformance

Platforms implementing the MCP binding:

- **MUST** include `meta.ucp-agent.profile` on all requests
- **MUST** check the `messages` array in responses before accessing order data
- **SHOULD** delegate to the business via `permalink_url` for the authoritative order experience - the business site is the source of truth for order details and post-purchase operations

Businesses implementing the MCP binding:

- **MUST** implement the `get_order` tool per the [OpenRPC schema](https://ucp.dev/services/shopping/mcp.openrpc.json)

See [Order Capability - Guidelines](http://ucp.dev/draft/specification/order/#operations-guidelines) for capability-level requirements that apply across all transports.
