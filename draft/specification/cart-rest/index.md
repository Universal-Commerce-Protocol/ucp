# Cart Capability - REST Binding

This document specifies the REST binding for the [Cart Capability](https://ucp.dev/draft/specification/cart/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at `/.well-known/ucp`.

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

All UCP REST endpoints are relative to the business's base URL, which is discovered through the UCP profile at `/.well-known/ucp`. The endpoint for the cart capability is defined in the `rest.endpoint` field of the business profile.

### Content Types

- **Request**: `application/json`
- **Response**: `application/json`

All request and response bodies **MUST** be valid JSON as specified in [RFC 8259](https://tools.ietf.org/html/rfc8259).

### Transport Security

All REST endpoints **MUST** be served over HTTPS with minimum TLS version 1.3.

## Operations

| Operation                   | Method | Endpoint             | Description            |
| --------------------------- | ------ | -------------------- | ---------------------- |
| [Create Cart](#create-cart) | `POST` | `/carts`             | Create a cart session. |
| [Get Cart](#get-cart)       | `GET`  | `/carts/{id}`        | Get a cart session.    |
| [Update Cart](#update-cart) | `PUT`  | `/carts/{id}`        | Update a cart session. |
| [Cancel Cart](#cancel-cart) | `POST` | `/carts/{id}/cancel` | Cancel a cart session. |

### Create Cart

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

- `id` (String, required): The cart session ID (path parameter).

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
GET /carts/{id} HTTP/1.1
UCP-Agent: profile="https://platform.example/profile"
```

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

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
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
```

### Update Cart

#### Input Schema

- `id` (String, required): The cart session ID (path parameter).

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

- `id` (String, required): The cart session ID (path parameter).

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
POST /carts/{id}/cancel HTTP/1.1
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json

{}
```

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

The following headers are defined for the HTTP binding and apply to all operations unless otherwise noted.

**Error processing OpenAPI:** [Errno 2] No such file or directory: 'source/services/shopping/rest.openapi.json'

### Specific Header Requirements

- **UCP-Agent**: All requests **MUST** include the `UCP-Agent` header containing the platform profile URI using Dictionary Structured Field syntax ([RFC 8941](https://datatracker.ietf.org/doc/html/rfc8941)). Format: `profile="https://platform.example/profile"`.
- **Idempotency-Key**: Operations that modify state **SHOULD** support idempotency. When provided, the server **MUST**:
  1. Store the key with the operation result for at least 24 hours.
  1. Return the cached result for duplicate keys.
  1. Return `409 Conflict` if the key is reused with different parameters.

## Protocol Mechanics

### Status Codes

| Status Code                 | Description                                                                        |
| --------------------------- | ---------------------------------------------------------------------------------- |
| `200 OK`                    | The request was successful.                                                        |
| `201 Created`               | The cart was successfully created.                                                 |
| `400 Bad Request`           | The request was invalid or cannot be served.                                       |
| `401 Unauthorized`          | Authentication is required and has failed or has not been provided.                |
| `403 Forbidden`             | The request is authenticated but the user does not have the necessary permissions. |
| `409 Conflict`              | The request could not be completed due to a conflict (e.g., idempotent key reuse). |
| `422 Unprocessable Entity`  | The profile content is malformed (discovery failure).                              |
| `424 Failed Dependency`     | The profile URL is valid but fetch failed (discovery failure).                     |
| `429 Too Many Requests`     | Rate limit exceeded.                                                               |
| `500 Internal Server Error` | An unexpected condition was encountered on the server.                             |
| `503 Service Unavailable`   | Temporary unavailability.                                                          |

### Error Responses

See the [Core Specification](https://ucp.dev/draft/specification/overview/#error-handling) for negotiation error handling (discovery failures, negotiation failures).

#### Business Outcomes

Business outcomes (including not found and validation errors) are returned with HTTP 200 and the UCP envelope containing `messages`:

```json
{
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
```

## Security Considerations

### Authentication

Authentication is optional and depends on business requirements. When authentication is required, the REST transport **MAY** use:

1. **Open API**: No authentication required for public operations.
1. **API Keys**: Via `X-API-Key` header.
1. **OAuth 2.0**: Via `Authorization: Bearer {token}` header, following [RFC 6749](https://tools.ietf.org/html/rfc6749).
1. **Mutual TLS**: For high-security environments.

Businesses **MAY** require authentication for some operations while leaving others open (e.g., public cart without authentication).
