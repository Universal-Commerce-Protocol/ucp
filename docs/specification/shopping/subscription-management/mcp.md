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

# Subscription Management Capability - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the
[Subscription Management Capability](index.md).

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
      "dev.ucp.shopping.subscription_management": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/subscription-management",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/subscription_management.json"
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

### Request Metadata

MCP clients **MUST** include a `meta` object in every request, with
`ucp-agent.profile`. Every tool that changes a subscription also requires
`meta["idempotency-key"]`.

## Tools

UCP Capabilities map 1:1 to MCP Tools. Each tool name is also the key of its
entry in a subscription's [`operations`](index.md#operations-on-a-subscription).

| Tool | Operation | Description |
| :-- | :-- | :-- |
| `list_subscriptions` | [List Subscriptions](index.md#list-subscriptions) | List the buyer's subscriptions. |
| `get_subscription` | [Get Subscription](index.md#get-subscription) | Get the current state of a subscription. |
| `pause_subscription` | [Pause Subscription](index.md#pause-subscription) | Stop placing recurring orders until resumed. |
| `resume_subscription` | [Resume Subscription](index.md#resume-subscription) | Start placing recurring orders again. |
| `skip_subscription_order` | [Skip Subscription Order](index.md#skip-subscription-order) | Do not place one upcoming order. |
| `unskip_subscription_order` | [Unskip Subscription Order](index.md#unskip-subscription-order) | Reverse a skip. |
| `cancel_subscription` | [Cancel Subscription](index.md#cancel-subscription) | End the subscription. |

### `list_subscriptions`

#### Input Schema

* `meta` (Object, required): Request metadata with `ucp-agent.profile`.
* `filters` (Object, optional): `status` (array of strings) and `order_id`
  (string), combined with AND.
* `pagination` (Object, optional): `cursor` and `limit`.

#### Output Schema

{{ extension_schema_fields('subscription_management.json#/$defs/list_response', 'shopping/subscription-management') }}

#### Example

<!-- ucp:example schema=transports/mcp_tool_call def=request direction=request -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "list_subscriptions",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/.well-known/ucp"
        }
      },
      "filters": { "status": ["active", "paused"] },
      "pagination": { "limit": 10 }
    }
  }
}
```

### `get_subscription`

#### Input Schema

* `meta` (Object, required): Request metadata with `ucp-agent.profile`.
* `id` (String, required): The ID of the subscription.

#### Output Schema

{{ extension_schema_fields('subscription_management.json#/$defs/subscription_response', 'shopping/subscription-management') }}

#### Example

=== "Request"

    <!-- ucp:example schema=transports/mcp_tool_call def=request direction=request -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 2,
      "method": "tools/call",
      "params": {
        "name": "get_subscription",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/.well-known/ucp"
            }
          },
          "id": "sub_8f2k1"
        }
      }
    }
    ```

=== "Response"

    <!-- ucp:example schema=shopping/subscription_management op=get direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 2,
      "result": {
        "structuredContent": {
          "ucp": {
            "version": "{{ ucp_version }}",
            "capabilities": {
              "dev.ucp.shopping.subscription_management": [{"version": "{{ ucp_version }}"}]
            }
          },
          "subscription": {
            "id": "sub_8f2k1",
            "status": "active",
            "revision": "r_41",
            "permalink_url": "https://business.example.com/account/subscriptions/sub_8f2k1",
            "currency": "USD",
            "line_items": [...],
            "upcoming_orders": [
              {
                "id": "uo_2026_12",
                "status": "scheduled",
                "expected_at": "2026-12-02T00:00:00Z",
                "operations": {
                  "skip_subscription_order": { "available": true }
                }
              }
            ],
            "operations": {
              "pause_subscription": { "available": true },
              "cancel_subscription": { "available": true },
              "update_payment": {
                "available": false,
                "continue_url": "https://business.example.com/account/subscriptions/sub_8f2k1/payment"
              }
            }
          },
          "policies": [...]
        },
        "content": [
          {
            "type": "text",
            "text": "{\"ucp\":{…},…}"
          }
        ]
      }
    }
    ```

### `pause_subscription`, `resume_subscription`, `cancel_subscription`

#### Input Schema

* `meta` (Object, required): Request metadata with `ucp-agent.profile` and
  `idempotency-key`.
* `id` (String, required): The ID of the subscription.
* `revision` (String, required): The subscription's `revision` as the buyer
  last saw it.
* `reason` (String, optional, `cancel_subscription` only): The buyer's reason
  for cancelling. Never required.

#### Output Schema

The [Subscription Response](index.md#subscription-response).

#### Example

<!-- ucp:example schema=transports/mcp_tool_call def=request direction=request -->
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "cancel_subscription",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/.well-known/ucp"
        },
        "idempotency-key": "3c2b1a0f-9e8d-4c7b-a6f5-e4d3c2b1a0f9"
      },
      "id": "sub_8f2k1",
      "revision": "r_41",
      "reason": "Too much coffee"
    }
  }
}
```

### `skip_subscription_order`, `unskip_subscription_order`

#### Input Schema

* `meta` (Object, required): Request metadata with `ucp-agent.profile` and
  `idempotency-key`.
* `id` (String, required): The ID of the subscription.
* `revision` (String, required): The subscription's `revision` as the buyer
  last saw it.
* `upcoming_order_id` (String, required): The `id` of the upcoming order.

#### Output Schema

The [Subscription Response](index.md#subscription-response).

#### Example

<!-- ucp:example schema=transports/mcp_tool_call def=request direction=request -->
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "skip_subscription_order",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/.well-known/ucp"
        },
        "idempotency-key": "6f1d2e3c-4b5a-4c6d-9e7f-8a9b0c1d2e3f"
      },
      "id": "sub_8f2k1",
      "revision": "r_41",
      "upcoming_order_id": "uo_2026_12"
    }
  }
}
```

## Events

[Subscription events](index.md#events) are not MCP messages. The Business
delivers them by HTTP `POST` to the `webhook.url` in the Platform's profile,
also for Platforms that call the tools above over MCP. See the
[REST binding](rest.md#events) for the request.

## Error Handling

When the business cannot return a subscription or refuses an operation, the
response is an error response with a `messages` array. Platforms **MUST** check
`messages` before accessing subscription fields. See
[Errors](index.md#errors) for the codes this capability defines.

## Conformance

Platforms implementing the MCP binding:

* **MUST** include `meta.ucp-agent.profile` on all requests
* **MUST** include `meta.idempotency-key` on every tool that changes a
  subscription
* **MUST** check the `messages` array in responses before accessing
  subscription data

Businesses implementing the MCP binding:

* **MUST** implement every tool above per the
  [OpenRPC schema](site:services/shopping/mcp.openrpc.json)

See [Subscription Management Capability - Responsibilities](index.md#responsibilities) for
capability-level requirements that apply across all transports.
