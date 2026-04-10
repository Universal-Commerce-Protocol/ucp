# Order Capability - REST Binding

This document specifies the REST binding for the [Order Capability](http://ucp.dev/draft/specification/order/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "draft",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/draft/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp/v1"
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

### Base URL

All UCP REST endpoints are relative to the business's base URL, which is discovered through the UCP profile at `/.well-known/ucp`. The endpoint for the order capability is defined in the `rest.endpoint` field of the business profile.

### Content Types

- **Response**: `application/json`

All response bodies **MUST** be valid JSON as specified in [RFC 8259](https://tools.ietf.org/html/rfc8259).

### Transport Security

All REST endpoints **MUST** be served over HTTPS with minimum TLS version 1.3.

## Operations

| Operation               | Method | Endpoint       | Description                        |
| ----------------------- | ------ | -------------- | ---------------------------------- |
| [Get Order](#get-order) | `GET`  | `/orders/{id}` | Get the current state of an order. |

For the Order Event Webhook (business -> platform push), see the [Order Capability overview](http://ucp.dev/draft/specification/order/#order-event-webhook).

### Get Order

Returns the current-state snapshot of an order.

#### Input Schema

- `id` (String, required): The order ID (path parameter).

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

#### Example

```json
GET /orders/order_abc123 HTTP/1.1
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Accept: application/json
Signature-Input: sig1=("@method" "@authority" "@path" "ucp-agent");created=1706800000;keyid="platform-2026"
Signature: sig1=:MEUCIQDTxNq8h7LGHpvVZQp1iHkFp9+3N8Mxk2zH1wK4YuVN8w...:
```

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
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
}
```

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
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
}
```

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
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
}
```

## HTTP Headers

**Request Headers**

| Header            | Required | Description                                                                                                                                                                                                                                                   |
| ----------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Authorization`   | No       | Should contain oauth token representing the following 2 schemes: 1. Platform self authenticating (client_credentials). 2. Platform authenticating on behalf of end user (authorization_code).                                                                 |
| `X-API-Key`       | No       | Authenticates the platform with a reusable api key allocated to the platform by the business.                                                                                                                                                                 |
| `Signature`       | No       | RFC 9421 HTTP Message Signature. Required when using HTTP Message Signatures for authentication. Format: `sig1=:<base64-signature>:`.                                                                                                                         |
| `Signature-Input` | No       | RFC 9421 Signature-Input header. Required when using HTTP Message Signatures for authentication. Format: `sig1=("@method" "@path" ...);created=<timestamp>;keyid="<key-id>"`.                                                                                 |
| `Request-Id`      | **Yes**  | For tracing the requests across network layers and components.                                                                                                                                                                                                |
| `User-Agent`      | No       | Identifies the user agent string making the call.                                                                                                                                                                                                             |
| `UCP-Agent`       | **Yes**  | Identifies the UCP agent making the call. All requests MUST include the UCP-Agent header containing the signer's profile URI using RFC 8941 Dictionary syntax. The URL MUST point to /.well-known/ucp. Format: profile="https://example.com/.well-known/ucp". |
| `Content-Type`    | No       | Representation Metadata. Tells the receiver what the data in the message body actually is.                                                                                                                                                                    |
| `Accept`          | No       | Content Negotiation. The client tells the server what data formats it is capable of understanding.                                                                                                                                                            |
| `Accept-Language` | No       | Localization. Tells the receiver the user's preferred natural languages, often with "weights" or priorities.                                                                                                                                                  |
| `Accept-Encoding` | No       | Compression. The client tells the server which content-codings it supports, usually for compression.                                                                                                                                                          |

### Specific Header Requirements

**UCP-Agent** (required on all requests):

Platform identification using [RFC 8941 Dictionary](https://www.rfc-editor.org/rfc/rfc8941#name-dictionaries) syntax:

```http
UCP-Agent: profile="https://platform.example/.well-known/ucp"
```

## Message Signing

Request and response signatures follow the [Message Signatures](http://ucp.dev/draft/specification/signatures/index.md) specification using RFC 9421 HTTP Message Signatures. See [REST Request Signing](http://ucp.dev/draft/specification/signatures/#rest-request-signing) and [REST Request Verification](http://ucp.dev/draft/specification/signatures/#rest-request-verification) for the complete algorithm.

## Conformance

Platforms implementing the REST binding:

- **MUST** include `UCP-Agent` header with profile URL on all requests
- **MUST** check the `messages` array in responses before accessing order data
- **SHOULD** delegate to the business via `permalink_url` for the authoritative order experience - the business site is the source of truth for order details and post-purchase operations

Businesses implementing the REST binding:

- **MUST** serve all endpoints over HTTPS with TLS 1.3+
- **SHOULD** sign responses per the [Message Signatures](http://ucp.dev/draft/specification/signatures/index.md) specification

See [Order Capability - Guidelines](http://ucp.dev/draft/specification/order/#operations-guidelines) for capability-level requirements that apply across all transports.
