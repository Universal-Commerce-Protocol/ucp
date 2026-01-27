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

# Cart Capability - REST Binding

This document specifies the REST binding for the [Cart Capability](cart.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at
`/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "2026-01-15",
    "services": {
      "dev.ucp.shopping": {
        "version": "2026-01-15",
        "spec": "https://ucp.dev/specification/overview",
        "rest": {
          "schema": "https://ucp.dev/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp/v1"
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

### Base URL

All UCP REST endpoints are relative to the business's base URL, which is
discovered through the UCP profile at `/.well-known/ucp`. The endpoint for the
cart capability is defined in the `rest.endpoint` field of the business profile.

### Content Types

* **Request**: `application/json`
* **Response**: `application/json`

All request and response bodies **MUST** be valid JSON as specified in
[RFC 8259](https://tools.ietf.org/html/rfc8259){ target="_blank" }.

### Transport Security

All REST endpoints **MUST** be served over HTTPS with minimum TLS version 1.3.

## Operations

| Operation | Method | Endpoint | Description |
| :---- | :---- | :---- | :---- |
| [Create Cart](#create-cart) | `POST` | `/carts` | Create a cart session. |
| [Get Cart](#get-cart) | `GET` | `/carts/{id}` | Get a cart session. |
| [Update Cart](#update-cart) | `PUT` | `/carts/{id}` | Update a cart session. |
| [Cancel Cart](#cancel-cart) | `POST` | `/carts/{id}/cancel` | Cancel a cart session. |

### Create Cart

#### Input Schema

{{ schema_fields('cart.create_req', 'cart') }}

#### Output Schema

{{ schema_fields('cart_resp', 'cart') }}

#### Example

=== "Request"

    ```json
    POST /carts HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json

    {
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
    ```

=== "Response"

    ```json
    HTTP/1.1 201 Created
    Content-Type: application/json

    {
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
          "amount": 5000,
          "display_text": "Estimated total (taxes calculated at checkout)"
        }
      ],
      "continue_url": "https://business.example.com/checkout?cart=cart_abc123",
      "expires_at": "2026-01-16T12:00:00Z"
    }
    ```

### Get Cart

#### Input Schema

* `id` (String, required): The cart session ID (path parameter).

#### Output Schema

{{ schema_fields('cart_resp', 'cart') }}

#### Example

=== "Request"

    ```json
    GET /carts/{id} HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
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
    ```

=== "Not Found"

    ```
    HTTP/1.1 404 Not Found
    ```

### Update Cart

#### Input Schema

* `id` (String, required): The cart session ID (path parameter).

{{ schema_fields('cart.update_req', 'cart') }}

#### Output Schema

{{ schema_fields('cart_resp', 'cart') }}

#### Example

=== "Request"

    ```json
    PUT /carts/{id} HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json

    {
      "id": "cart_abc123",
      "line_items": [
        {
          "item": {
            "id": "item_123"
          },
          "id": "li_1",
          "quantity": 3
        },
        {
          "item": {
            "id": "item_456"
          },
          "id": "li_2",
          "quantity": 1
        }
      ],
      "context": {
        "address_country": "US",
        "address_region": "CA",
        "postal_code": "94105"
      }
    }
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
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
    ```

### Cancel Cart

#### Input Schema

* `id` (String, required): The cart session ID (path parameter).

#### Output Schema

{{ schema_fields('cart_resp', 'cart') }}

#### Example

=== "Request"

    ```json
    POST /carts/{id}/cancel HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json

    {}
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
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
    ```

## HTTP Headers

The following headers are defined for the HTTP binding and apply to all
operations unless otherwise noted.

{{ header_fields('create_cart', 'rest.openapi.json') }}

### Specific Header Requirements

* **UCP-Agent**: All requests **MUST** include the `UCP-Agent` header
    containing the platform profile URI using Dictionary Structured Field syntax
    ([RFC 8941](https://datatracker.ietf.org/doc/html/rfc8941){target="_blank"}).
    Format: `profile="https://platform.example/profile"`.
* **Idempotency-Key**: Operations that modify state **SHOULD** support
    idempotency. When provided, the server **MUST**:
    1. Store the key with the operation result for at least 24 hours.
    2. Return the cached result for duplicate keys.
    3. Return `409 Conflict` if the key is reused with different parameters.

## Protocol Mechanics

### Status Codes

| Status Code | Description |
| :--- | :--- |
| `200 OK` | The request was successful. |
| `201 Created` | The cart was successfully created. |
| `400 Bad Request` | The request was invalid or cannot be served. |
| `401 Unauthorized` | Authentication is required and has failed or has not been provided. |
| `403 Forbidden` | The request is authenticated but the user does not have the necessary permissions. |
| `404 Not Found` | The cart does not exist, has expired, or was canceled. |
| `409 Conflict` | The request could not be completed due to a conflict (e.g., idempotent key reuse). |
| `429 Too Many Requests` | Rate limit exceeded. |
| `500 Internal Server Error` | An unexpected condition was encountered on the server. |
| `503 Service Unavailable` | Temporary unavailability. |

### Error Responses

Transport errors (404, 500, etc.) are signaled via HTTP status code. The response
body is optional.

Validation errors return HTTP 200 with the cart containing a `messages` array:

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ucp": { ... },
  "id": "cart_abc123",
  "line_items": [ ... ],
  "currency": "USD",
  "totals": [ ... ],
  "messages": [
    {
      "type": "error",
      "code": "invalid_quantity",
      "path": "$.line_items[0].quantity",
      "content": "Quantity must be at least 1"
    }
  ],
  "continue_url": "https://business.example.com/checkout?cart=cart_abc123"
}
```

## Security Considerations

### Authentication

Authentication is optional and depends on business requirements. When
authentication is required, the REST transport **MAY** use:

1. **Open API**: No authentication required for public operations.
2. **API Keys**: Via `X-API-Key` header.
3. **OAuth 2.0**: Via `Authorization: Bearer {token}` header, following
    [RFC 6749](https://tools.ietf.org/html/rfc6749){ target="_blank" }.
4. **Mutual TLS**: For high-security environments.

Businesses **MAY** require authentication for some operations while leaving
others open (e.g., public cart without authentication).
