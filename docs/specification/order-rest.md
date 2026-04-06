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

# Order Capability - REST Binding

This document specifies the REST binding for the [Order Capability](order.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at
`/.well-known/ucp`.

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
          "endpoint": "https://business.example.com/ucp/v1"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.order": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/order",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/order.json"
        }
      ]
    }
  }
}
```

### Base URL

All UCP REST endpoints are relative to the business's base URL, which is
discovered through the UCP profile at `/.well-known/ucp`. The endpoint for the
order capability is defined in the `rest.endpoint` field of the business profile.

### Content Types

* **Response**: `application/json`

All response bodies **MUST** be valid JSON as specified in
[RFC 8259](https://tools.ietf.org/html/rfc8259){ target="_blank" }.

### Transport Security

All REST endpoints **MUST** be served over HTTPS with minimum TLS version 1.3.

## Operations

| Operation | Method | Endpoint | Description |
| :---- | :---- | :---- | :---- |
| [Get Order](#get-order) | `GET` | `/orders/{id}` | Get the current state of an order. |

For the Order Event Webhook (business -> platform push), see the
[Order Capability overview](order.md#order-event-webhook).

### Get Order

Returns the current-state snapshot of an order.

#### Input Schema

* `id` (String, required): The order ID (path parameter).

#### Output Schema

{{ schema_fields('order', 'order') }}

#### Example

=== "Request"

    ```json
    GET /orders/order_abc123 HTTP/1.1
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Accept: application/json
    Signature-Input: sig1=("@method" "@authority" "@path" "ucp-agent");created=1706800000;keyid="platform-2026"
    Signature: sig1=:MEUCIQDTxNq8h7LGHpvVZQp1iHkFp9+3N8Mxk2zH1wK4YuVN8w...:
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.shopping.order": [{"version": "{{ ucp_version }}"}]
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
    }
    ```

=== "Not Found"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.order": [{"version": "{{ ucp_version }}"}]
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
    }
    ```

=== "Not Authorized"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.order": [{"version": "{{ ucp_version }}"}]
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
    }
    ```

## HTTP Headers

{{ header_fields('get_order', 'rest.openapi.json') }}

### Specific Header Requirements

**UCP-Agent** (required on all requests):

Platform identification using
[RFC 8941 Dictionary](https://www.rfc-editor.org/rfc/rfc8941#name-dictionaries){ target="_blank" }
syntax:

```http
UCP-Agent: profile="https://platform.example/.well-known/ucp"
```

## Message Signing

Request and response signatures follow the
[Message Signatures](signatures.md) specification using RFC 9421 HTTP Message
Signatures. See
[REST Request Signing](signatures.md#rest-request-signing) and
[REST Request Verification](signatures.md#rest-request-verification) for
the complete algorithm.

## Conformance

Platforms implementing the REST binding:

* **MUST** include `UCP-Agent` header with profile URL on all requests
* **MUST** check the `messages` array in responses before accessing order data
* **SHOULD** delegate to the business via `permalink_url` for the authoritative
  order experience - the business site is the source of truth for order details
  and post-purchase operations

Businesses implementing the REST binding:

* **MUST** serve all endpoints over HTTPS with TLS 1.3+
* **SHOULD** sign responses per the
  [Message Signatures](signatures.md) specification

See [Order Capability - Guidelines](order.md#operations-guidelines) for
capability-level requirements that apply across all transports.
