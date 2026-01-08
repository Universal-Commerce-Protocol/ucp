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

# Checkout Capability - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the
[Checkout Capability](checkout.md).

## Protocol Fundamentals

### Discovery
Merchants advertise MCP transport availability through their UCP profile at
`/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "2025-10-21"
  },
  "transports": {
    "mcp": {
      "endpoint": "https://example-merchant.com/ucp/mcp"
    }
  }
}
```

### Agent Profile Advertisement
MCP clients **MUST** include the UCP agent profile URI with every request. The
agent profile is included in the `_meta.ucp` structure within the request
parameters:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "create_checkout",
  "params": {
    "_meta": {
      "ucp": {
        "profile": "https://agent.example/profiles/v2025-11/shopping-agent.json"
      }
    },
    "idempotency_key": "..."
  }
}
```

The `_meta.ucp.profile` field **MUST** be present in every MCP tool invocation
to enable version compatibility checking and capability negotiation.

## Protocol Mapping & Data Visibility

To ensure strict security and correct Agentic reasoning, integrators must map
standard parameters into the MCP architecture using the following
categorization.

### Data Visibility Model

*   **Transport Scope**: Metadata required for network routing,
    security, and observability. These are handled by the Client Infrastructure
    and Server Gateway. They are **NOT** visible to the LLM/Agent.
*   **Logic Scope**: Data required for business logic, transaction
    identity, and decision making. These must be exposed as **Tool Arguments**
    so the Agent can utilize them.

### Header Mapping Reference

The following table dictates where standard headers must be implemented in an
MCP environment when transported over HTTP.

| Parameter Name | Protocol Location | Implementation Requirement |
| :--- | :--- | :--- |
| `Authorization` | Transport Config | **DO NOT expose to Agent**. Configure in the MCP Client. |
| `X-API-Key` | Transport Config | Authenticates the tenant/platform. Handled by Client/Gateway. |
| `Request-Signature` | Transport Config | Verified by Gateway. Reject before MCP processing if invalid. |
| `User-Agent` | Transport Config | Identifies the calling software. |
| `Request-Id` | Transport Config | Used for distributed tracing. |
| `Accept-Language` | Context Injection | Server extracts this to localize Tool responses. |
| `Idempotency-Key` | Tool Argument | Must be defined as a property in the Tool Input Schema. |

### Context Injection Strategy

The MCP Server Implementation must "bridge" specific Transport Headers into the
Tool Execution Context. The Agent does not need to manually request these
values.

*   **Localization**: If `Accept-Language` is `es-MX`, the Server should
    format monetary values and translate error messages automatically.

### Security Warning

**CRITICAL**: `Authorization` (OAuth) and `X-API-Key` headers must **never** be
defined as arguments in the Tool Schema. Passing credentials through the LLM
context window creates a severe security risk (Leakage/Prompt Injection). These
values must remain strictly in the Transport layer.

## Tools

UCP Capabilities map 1:1 to MCP Tools.

| Tool | Operation | Description |
| :---- | :---- | :---- |
| `create_checkout` | [Create Checkout](checkout.md#create-checkout) | Create a checkout session. |
| `get_checkout` | [Get Checkout](checkout.md#get-checkout) | Get a checkout session. |
| `update_checkout` | [Update Checkout](checkout.md#update-checkout) | Update a checkout session. |
| `complete_checkout` | [Complete Checkout](checkout.md#complete-checkout) | Place the order. |
| `cancel_checkout` | [Cancel Checkout](checkout.md#cancel-checkout) | Cancel a checkout session. |

### `create_checkout`

Maps to the [Create Checkout](checkout.md#create-checkout) operation.

#### Input Schema

*   [Checkout](checkout.md#checkout) object.
*   Extensions (Optional):
    *   `dev.ucp.shopping.buyer_consent`: [Buyer Consent](buyer-consent.md)
    *   `dev.ucp.shopping.fulfillment`: [Fulfillment](fulfillment.md)
    *   `dev.ucp.shopping.discount`: [Discount](discount.md)

**Output:**

*   [Checkout](checkout.md#checkout) object.

#### Example Request (JSON-RPC)

```json
{
  "jsonrpc": "2.0",
  "method": "create_checkout",
  "params": {
    "_meta": {
      "ucp": {
        "profile": "https://agent.example/profiles/v2025-11/shopping-agent.json"
      }
    },
    "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
    "line_items": [
      {
        "item": {
          "id": "item_123",
          "title": "Blue Jeans",
          "price": 5000
        },
        "id": "li_1",
        "quantity": 1,
      }
    ]
  },
  "id": 1
}
```

### `get_checkout`

Maps to the [Get Checkout](checkout.md#get-checkout) operation.

#### Input Schema

*   `checkout_id` (String): The ID of the checkout session.

**Output:**

*   [Checkout](checkout.md#checkout) object.

### `update_checkout`

Maps to the [Update Checkout](checkout.md#update-checkout) operation.

#### Input Schema

*   [Checkout](checkout.md#checkout) object.
*   Extensions (Optional):
    *   `dev.ucp.shopping.buyer_consent`: [Buyer Consent](buyer-consent.md)
    *   `dev.ucp.shopping.fulfillment`: [Fulfillment](fulfillment.md)
    *   `dev.ucp.shopping.discount`: [Discount](discount.md)

**Output:**

*   [Checkout](checkout.md#checkout) object.

### `complete_checkout`

Maps to the [Complete Checkout](checkout.md#complete-checkout) operation.

#### Input Schema

*   `checkout_id` (String): The ID of the checkout session.
*   `payment_data` ([Payment Data](checkout.md#payment_data)): Payment instrument instance submitted
    by the buyer.
*   `risk_signals` (Object, Optional): Associated risk signals.
*   `idempotency_key` (String, UUID): **Required**. Unique key for retry
    safety.

**Output:**

*   [Checkout](checkout.md#checkout) object, containing `order_id` and
    `order_permalink_url`.

### `cancel_checkout`

Maps to the [Cancel Checkout](checkout.md#cancel-checkout) operation.

#### Input Schema

*   `checkout_id` (String): The ID of the checkout session.
*   `idempotency_key` (String, UUID): **Required**. Unique key for retry safety.

**Output:**

*   [Checkout](checkout.md#checkout) object with `status: canceled`.

## Error Handling

Error responses follow JSON-RPC 2.0 format while using the UCP error structure
defined in the [Core Specification](overview.md). The UCP error object is
embedded in the JSON-RPC error's `data` field:

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

1.  Implement JSON-RPC 2.0 protocol correctly.
2.  Provide all core checkout tools defined in this specification.
3.  Handle errors with UCP-specific error codes embedded in the JSON-RPC error
    object.
4.  Validate tool inputs against UCP schemas.
5.  Support HTTP transport with streaming.
