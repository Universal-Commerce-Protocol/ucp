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

# Subscription Capability - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the
[Subscription Capability](index.md).

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
      "dev.ucp.shopping.subscription": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/subscription",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/subscription.json"
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

### Request Metadata

MCP clients **MUST** include a `meta` object in every request containing
protocol metadata:

<!-- ucp:example schema=transports/mcp_tool_call def=request direction=request -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
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

The `meta["ucp-agent"]` field is **required** on all requests to enable
[capability negotiation](../../overview/index.md#negotiation-protocol). Platforms **MAY**
include additional metadata fields.

## Tools

UCP Capabilities map 1:1 to MCP Tools.

| Tool | Operation | Description |
| :---- | :---- | :---- |
| `get_subscription` | [Get Subscription](index.md#get-subscription) | Get the current state of a subscription. |
| `list_subscriptions` | [List Subscriptions](index.md#list-subscriptions) | List the subscriptions the caller may access. |

### `get_subscription`

Maps to the [Get Subscription](index.md#get-subscription) operation. Returns
the current-state snapshot of a subscription.

#### Input Schema

* `meta` (Object, required): Request metadata with `ucp-agent.profile`.
* `id` (String, required): The ID of the subscription.

#### Output Schema

{{ extension_schema_fields('subscription.json#/$defs/get_subscription_response', 'shopping/subscription') }}

#### Example

=== "Request"

    <!-- ucp:example schema=transports/mcp_tool_call def=request direction=request -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
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

    <!-- ucp:example schema=shopping/subscription op=get_subscription direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
          "ucp": {
            "version": "{{ ucp_version }}",
            "capabilities": {
              "dev.ucp.shopping.subscription": [{"version": "{{ ucp_version }}"}]
            }
          },
          "subscription": {
            "id": "sub_8f2k1",
            "label": "House Blend, every month",
            "status": "active",
            "permalink_url": "https://business.example.com/account/subscriptions/sub_8f2k1",
            "currency": "USD",
            "origin": { "order_id": "ord_8f3e2a", "line_item_ids": ["li_1"] },
            "line_items": [ ... ],
            "orders": [
              { "id": "ord_9c41d7", "permalink_url": "https://business.example.com/orders/9c41d7" },
              { "id": "ord_8f3e2a", "permalink_url": "https://business.example.com/orders/8f3e2a" }
            ],
            "upcoming_orders": [
              { "expected_at": "2026-12-02T00:00:00Z" }
            ]
          },
          "policies": [ ... ]
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

=== "Not Found"

    <!-- ucp:example schema=common/types/error_response op=read direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
          "ucp": {
            "version": "{{ ucp_version }}",
            "status": "error",
            "capabilities": {
              "dev.ucp.shopping.subscription": [{"version": "{{ ucp_version }}"}]
            }
          },
          "messages": [
            {
              "type": "error",
              "code": "not_found",
              "severity": "unrecoverable",
              "content": "Subscription not found."
            }
          ]
        },
        "content": [
          {
            "type": "text",
            "text": "Subscription not found."
          }
        ]
      }
    }
    ```

### `list_subscriptions`

Maps to the [List Subscriptions](index.md#list-subscriptions) operation.
Returns the subscriptions the caller may access.

#### Input Schema {: #list-subscriptions-input-schema }

* `meta` (Object, required): Request metadata with `ucp-agent.profile`.
* `subscription` (Object, required): The list request, with optional `filters`
  and `pagination`.

{{ extension_schema_fields('subscription.json#/$defs/list_subscriptions_request', 'shopping/subscription') }}

#### Output Schema {: #list-subscriptions-output-schema }

{{ extension_schema_fields('subscription.json#/$defs/list_subscriptions_response', 'shopping/subscription') }}

#### Example {: #list-subscriptions-example }

=== "Request"

    <!-- ucp:example schema=shopping/subscription op=list_subscriptions direction=request extract=$.params.arguments.subscription -->
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
          "subscription": {
            "filters": { "order_id": "ord_8f3e2a" },
            "pagination": { "limit": 10 }
          }
        }
      }
    }
    ```

=== "Response"

    <!-- ucp:example schema=shopping/subscription op=list_subscriptions direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
          "ucp": {
            "version": "{{ ucp_version }}",
            "capabilities": {
              "dev.ucp.shopping.subscription": [{"version": "{{ ucp_version }}"}]
            }
          },
          "subscriptions": [
            {
              "id": "sub_8f2k1",
              "label": "House Blend, every month",
              "status": "active",
              "permalink_url": "https://business.example.com/account/subscriptions/sub_8f2k1",
              "currency": "USD",
              "origin": { "order_id": "ord_8f3e2a", "line_item_ids": ["li_1"] },
              "line_items": [ ... ],
              "orders": [ ... ],
              "upcoming_orders": [ ... ]
            }
          ],
          "pagination": { "has_next_page": false },
          "policies": [ ... ]
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

## Error Handling

When the Business cannot return a subscription, the response includes a
`messages` array describing the outcome. Platforms **MUST** check `messages`
before accessing subscription fields.

## Conformance

Platforms implementing the MCP binding:

* **MUST** include `meta.ucp-agent.profile` on all requests
* **MUST** check the `messages` array in responses before accessing
  subscription data
* **SHOULD** delegate to the Business via `permalink_url` for everything this
  capability does not expose - the Business site is where the buyer manages
  the subscription

Businesses implementing the MCP binding:

* **MUST** implement the `get_subscription` and `list_subscriptions` tools per
  the [OpenRPC schema](site:services/shopping/mcp.openrpc.json)

See [Subscription Capability - Guidelines](index.md#operations-guidelines) for
capability-level requirements that apply across all transports.
