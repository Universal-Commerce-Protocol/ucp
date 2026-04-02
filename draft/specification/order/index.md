# Order Capability

- **Capability Name:** `dev.ucp.shopping.order`

## Overview

Orders represent confirmed transactions resulting from a successful checkout submission. It provides a complete record of what was purchased, how it will be delivered, and what has happened since order placement.

### Key Concepts

Orders have three main components:

**Line Items** — what was purchased at checkout:

- Includes current quantity counts (total, fulfilled)
- Can change post-order (e.g. order edits, exchanges); **MUST** include all line items that ever existed on the order regardless of edits or alterations

**Fulfillment** — how items get delivered:

- **Expectations** — buyer-facing *promises* about when/how items will arrive
- **Events** (append-only log) — what actually happened (e.g. 👕 was shipped)

**Adjustments** — post-order events independent of fulfillment:

- Typically money movements (refunds, returns, credits, disputes, cancellations)
- Can be any post-order change
- Can happen before, during, or after fulfillment
- Businesses SHOULD append new entries rather than mutating existing ones; append-only ledger is preferred. Businesses that do not maintain adjustment history MAY perform in-place updates of existing entries (e.g. a single `return` adjustment can transition from `pending` to `completed`)

## Data Model

### Line Items

Line items reflect what was purchased at checkout and their current state:

- Item details (product, price, quantity ordered)
- Quantity counts and fulfillment status

### Fulfillment

Fulfillment tracks how items are delivered to the buyer.

#### Expectations

**Expectations** are buyer-facing groupings of items (e.g., "package 📦"). They represent:

- What items are grouped together
- Where they're going (`destination`)
- How they're being delivered (`method_type`)
- When they'll arrive (`description`, `fulfillable_on`)

Expectations can be split, merged, or adjusted post-order. For example:

- Group everything by delivery date: "what is coming when"
- Use a single expectation with a wide date range for flexibility
- The goal is **setting buyer expectations** - for the best buyer experience

#### Fulfillment Events

**Fulfillment Events** are an append-only log tracking physical shipments:

- Reference line items by ID and quantity
- Include tracking information
- Type is an open string field - businesses can use any values that make sense (common examples: `processing`, `shipped`, `in_transit`, `delivered`, `failed_attempt`, `canceled`, `undeliverable`, `returned_to_sender`)

### Adjustments

**Adjustments** are post-order events that exist independently of fulfillment:

- Type is an open string field - businesses can use any values that make sense (typically money movements like `refund`, `return`, `credit`, `price_adjustment`, `dispute`, `cancellation`)
- Can be any post-order change
- Optionally link to line items (or order-level for things like shipping refunds)
- Quantities and amounts are signed—negative for reductions (returns, refunds), positive for additions (exchanges)
- Include totals breakdown when relevant
- Can happen at any time regardless of fulfillment status

## Schema

### Order

| Name          | Type                                                                               | Required | Description                                                                                                             |
| ------------- | ---------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------- |
| ucp           | [Ucp Response Order Schema](/draft/specification/order/#ucp-response-order-schema) | **Yes**  | Protocol metadata for discovery profiles and responses. Uses slim schema pattern with context-specific required fields. |
| id            | string                                                                             | **Yes**  | Unique order identifier.                                                                                                |
| checkout_id   | string                                                                             | **Yes**  | Associated checkout ID for reconciliation.                                                                              |
| permalink_url | string                                                                             | **Yes**  | Permalink to access the order on merchant site.                                                                         |
| line_items    | Array\[[Order Line Item](/draft/specification/reference/#order-line-item)\]        | **Yes**  | Line items representing what was purchased — can change post-order via edits or exchanges.                              |
| fulfillment   | object                                                                             | **Yes**  | Fulfillment data: buyer expectations and what actually happened.                                                        |
| adjustments   | Array\[[Adjustment](/draft/specification/reference/#adjustment)\]                  | No       | Post-order events (refunds, returns, credits, disputes, cancellations, etc.) that exist independently of fulfillment.   |
| currency      | string                                                                             | No       | ISO 4217 currency code. MUST match the currency from the originating checkout session.                                  |
| totals        | [Totals](/draft/specification/reference/#totals)                                   | **Yes**  | Different totals for the order.                                                                                         |

### Order Line Item

Line items reflect what was purchased at checkout and their current state.

| Name      | Type                                                    | Required | Description                                                                                                                                                                                                                                                         |
| --------- | ------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id        | string                                                  | **Yes**  | Line item identifier.                                                                                                                                                                                                                                               |
| item      | [Item](/draft/specification/reference/#item)            | **Yes**  | Product data (id, title, price, image_url).                                                                                                                                                                                                                         |
| quantity  | object                                                  | **Yes**  | Quantity tracking for the line item.                                                                                                                                                                                                                                |
| totals    | Array\[[Total](/draft/specification/reference/#total)\] | **Yes**  | Line item totals breakdown.                                                                                                                                                                                                                                         |
| status    | string                                                  | **Yes**  | Derived status: removed if quantity.total == 0, fulfilled if quantity.total > 0 and quantity.fulfilled == quantity.total, partial if quantity.total > 0 and quantity.fulfilled > 0, otherwise processing. **Enum:** `processing`, `partial`, `fulfilled`, `removed` |
| parent_id | string                                                  | No       | Parent line item identifier for any nested structures.                                                                                                                                                                                                              |

**Quantity Structure:**

```json
{
  "original": 3,   // Quantity from the original checkout
  "total": 3,      // Current total (may differ after edits/exchanges)
  "fulfilled": 2   // What has been fulfilled
}
```

**Status Derivation:**

```text
if (total == 0) → "removed"
else if (fulfilled == total) → "fulfilled"
else if (fulfilled > 0) → "partial"
else → "processing"
```

### Expectation

Expectations are buyer-facing groupings representing when/how items will be delivered. They represent the current promise to the buyer and can be split, merged, or adjusted post-order.

| Name           | Type                                                             | Required | Description                                                                                                 |
| -------------- | ---------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------- |
| id             | string                                                           | **Yes**  | Expectation identifier.                                                                                     |
| line_items     | Array[object]                                                    | **Yes**  | Which line items and quantities are in this expectation.                                                    |
| method_type    | string                                                           | **Yes**  | Delivery method type (shipping, pickup, digital). **Enum:** `shipping`, `pickup`, `digital`                 |
| destination    | [Postal Address](/draft/specification/reference/#postal-address) | **Yes**  | Delivery destination address.                                                                               |
| description    | string                                                           | No       | Human-readable delivery description (e.g., 'Arrives in 5-8 business days').                                 |
| fulfillable_on | string                                                           | No       | When this expectation can be fulfilled: 'now' or ISO 8601 timestamp for future date (backorder, pre-order). |

### Fulfillment Event

Events are append-only records tracking actual shipments. The `type` field is an open string - businesses can use any values that make sense for their fulfillment process.

| Name            | Type          | Required | Description                                                                                                                                                                                                                                                                                                                             |
| --------------- | ------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id              | string        | **Yes**  | Fulfillment event identifier.                                                                                                                                                                                                                                                                                                           |
| occurred_at     | string        | **Yes**  | RFC 3339 timestamp when this fulfillment event occurred.                                                                                                                                                                                                                                                                                |
| type            | string        | **Yes**  | Fulfillment event type. Common values include: processing (preparing to ship), shipped (handed to carrier), in_transit (in delivery network), delivered (received by buyer), failed_attempt (delivery attempt failed), canceled (fulfillment canceled), undeliverable (cannot be delivered), returned_to_sender (returned to merchant). |
| line_items      | Array[object] | **Yes**  | Which line items and quantities are fulfilled in this event.                                                                                                                                                                                                                                                                            |
| tracking_number | string        | No       | Carrier tracking number (required if type != processing).                                                                                                                                                                                                                                                                               |
| tracking_url    | string        | No       | URL to track this shipment (required if type != processing).                                                                                                                                                                                                                                                                            |
| carrier         | string        | No       | Carrier name (e.g., 'FedEx', 'USPS').                                                                                                                                                                                                                                                                                                   |
| description     | string        | No       | Human-readable description of the shipment status or delivery information (e.g., 'Delivered to front door', 'Out for delivery').                                                                                                                                                                                                        |

Examples: `processing`, `shipped`, `in_transit`, `delivered`, `failed_attempt`, `canceled`, `undeliverable`, `returned_to_sender`, etc.

### Adjustment

Adjustments are polymorphic events that exist independently of fulfillment. The `type` field is an open string - businesses can use any values that make sense to them.

| Name        | Type                                                    | Required | Description                                                                                                                                                                                     |
| ----------- | ------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string                                                  | **Yes**  | Adjustment event identifier.                                                                                                                                                                    |
| type        | string                                                  | **Yes**  | Type of adjustment (open string). Typically money-related like: refund, return, credit, price_adjustment, dispute, cancellation. Can be any value that makes sense for the merchant's business. |
| occurred_at | string                                                  | **Yes**  | RFC 3339 timestamp when this adjustment occurred.                                                                                                                                               |
| status      | string                                                  | **Yes**  | Adjustment status. **Enum:** `pending`, `completed`, `failed`                                                                                                                                   |
| line_items  | Array[object]                                           | No       | Which line items and quantities are affected (optional).                                                                                                                                        |
| totals      | Array\[[Total](/draft/specification/reference/#total)\] | No       | Adjustment totals breakdown. Signed values - negative for money returned to buyer (refunds, credits), positive for additional charges (exchanges).                                              |
| description | string                                                  | No       | Human-readable reason or description (e.g., 'Defective item', 'Customer requested').                                                                                                            |

Examples: `refund`, `return`, `credit`, `price_adjustment`, `dispute`, `cancellation`, etc.

## Example

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.shopping.order": [{"version": "draft"}]
    }
  },
  "id": "order_abc123",
  "checkout_id": "checkout_xyz789",
  "permalink_url": "https://business.com/orders/abc123",
  "line_items": [
    {
      "id": "li_shoes",
      "item": { "id": "prod_shoes", "title": "Running Shoes", "price": 3000 },
      "quantity": { "original": 3, "total": 3, "fulfilled": 3 },
      "totals": [
        {"type": "subtotal", "amount": 9000},
        {"type": "total", "amount": 9000}
      ],
      "status": "fulfilled"
    },
    {
      "id": "li_shirts",
      "item": { "id": "prod_shirts", "title": "Cotton T-Shirt", "price": 2000 },
      "quantity": { "original": 2, "total": 2, "fulfilled": 0 },
      "totals": [
        {"type": "subtotal", "amount": 4000},
        {"type": "total", "amount": 4000}
      ],
      "status": "processing"
    }
  ],
  "fulfillment": {
    "expectations": [
      {
        "id": "exp_1",
        "line_items": [{ "id": "li_shoes", "quantity": 3 }],
        "method_type": "shipping",
        "destination": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "description": "Arrives in 2-3 business days",
        "fulfillable_on": "now"
      },
      {
        "id": "exp_2",
        "line_items": [{ "id": "li_shirts", "quantity": 2 }],
        "method_type": "shipping",
        "destination": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "description": "Backordered - ships Jan 15, arrives in 7-10 days",
        "fulfillable_on": "2025-01-15T00:00:00Z"
      }
    ],
    "events": [
      {
        "id": "evt_1",
        "occurred_at": "2025-01-08T10:30:00Z",
        "type": "delivered",
        "line_items": [{ "id": "li_shoes", "quantity": 3 }],
        "tracking_number": "123456789",
        "tracking_url": "https://fedex.com/track/123456789",
        "description": "Delivered to front door"
      }
    ]
  },
  "adjustments": [
    {
      "id": "adj_1",
      "type": "refund",
      "occurred_at": "2025-01-10T14:30:00Z",
      "status": "completed",
      "line_items": [{ "id": "li_shoes", "quantity": -1 }],
      "totals": [
        { "type": "total", "amount": -3000 }
      ],
      "description": "Defective item"
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 13000 },
    { "type": "fulfillment", "amount": 1200 },
    { "type": "tax", "amount": 1142 },
    { "type": "total", "amount": 15342 }
  ]
}
```

## Events

Businesses send order status changes as events after order placement.

| Event Mechanism                             | Method | Endpoint              | Description                                            |
| ------------------------------------------- | ------ | --------------------- | ------------------------------------------------------ |
| [Order Event Webhook](#order-event-webhook) | `POST` | Platform-provided URL | Business sends order lifecycle events to the platform. |

### Order Event Webhook

Businesses POST order events to a webhook URL provided by the platform during partner onboarding. The URL format is platform-specific.

**Inputs**

| Name          | Type                                                                               | Required | Description                                                                                                             |
| ------------- | ---------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------- |
| ucp           | [Ucp Response Order Schema](/draft/specification/order/#ucp-response-order-schema) | **Yes**  | Protocol metadata for discovery profiles and responses. Uses slim schema pattern with context-specific required fields. |
| id            | string                                                                             | **Yes**  | Unique order identifier.                                                                                                |
| checkout_id   | string                                                                             | **Yes**  | Associated checkout ID for reconciliation.                                                                              |
| permalink_url | string                                                                             | **Yes**  | Permalink to access the order on merchant site.                                                                         |
| line_items    | Array\[[Order Line Item](/draft/specification/reference/#order-line-item)\]        | **Yes**  | Line items representing what was purchased — can change post-order via edits or exchanges.                              |
| fulfillment   | object                                                                             | **Yes**  | Fulfillment data: buyer expectations and what actually happened.                                                        |
| adjustments   | Array\[[Adjustment](/draft/specification/reference/#adjustment)\]                  | No       | Post-order events (refunds, returns, credits, disputes, cancellations, etc.) that exist independently of fulfillment.   |
| totals        | [Totals](/draft/specification/reference/#totals)                                   | **Yes**  | Different totals for the order.                                                                                         |
| event_id      | string                                                                             | **Yes**  | Unique event identifier.                                                                                                |
| created_time  | string                                                                             | **Yes**  | Event creation timestamp in RFC 3339 format.                                                                            |

**Output**

| Name | Type                                   | Required | Description |
| ---- | -------------------------------------- | -------- | ----------- |
| ucp  | [Ucp](/draft/specification/order/#ucp) | **Yes**  |             |

### Webhook URL Configuration

The platform provides its webhook URL in the order capability's `config` field during capability negotiation. The business discovers this URL from the platform's profile and uses it to send order lifecycle events.

| Name        | Type   | Required | Description                                                 |
| ----------- | ------ | -------- | ----------------------------------------------------------- |
| webhook_url | string | **Yes**  | URL where merchant sends order lifecycle events (webhooks). |

**Example:**

```json
{
  "dev.ucp.shopping.order": [
    {
      "version": "draft",
      "config": {
        "webhook_url": "https://platform.example.com/webhooks/ucp/orders"
      }
    }
  ]
}
```

### Webhook Signature Verification

Webhook payloads **MUST** be signed by the business and verified by the platform to ensure authenticity and integrity. Signatures follow the [Message Signatures](http://ucp.dev/draft/specification/signatures/index.md) specification using the REST binding (RFC 9421).

**Required Headers:**

| Header            | Description                                |
| ----------------- | ------------------------------------------ |
| `UCP-Agent`       | Business profile URL (RFC 8941 Dictionary) |
| `Signature-Input` | Describes signed components                |
| `Signature`       | Contains the signature value               |
| `Content-Digest`  | Body digest (RFC 9530)                     |

**Example Webhook Request:**

```http
POST /webhooks/ucp/orders HTTP/1.1
Host: platform.example.com
Content-Type: application/json
UCP-Agent: profile="https://merchant.example/.well-known/ucp"
Content-Digest: sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:
Signature-Input: sig1=("@method" "@authority" "@path" "content-digest" "content-type");keyid="merchant-2026"
Signature: sig1=:MEUCIQDTxNq8h7LGHpvVZQp1iHkFp9+3N8Mxk2zH1wK4YuVN8w...:

{"id":"order_abc123","event_id":"evt_123","created_time":"2026-01-15T12:00:00Z",...}
```

#### Signing (Business)

1. Compute SHA-256 digest of the raw request body and set `Content-Digest` header
1. Build signature base per [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421)
1. Sign using a key from `signing_keys` in the business's UCP profile
1. Set `Signature-Input` and `Signature` headers

See [Message Signatures - REST Request Signing](http://ucp.dev/draft/specification/signatures/#rest-request-signing) for complete algorithm.

#### Verification (Platform)

**Authentication** (signature verification):

1. Parse `Signature-Input` to extract `keyid` and signed components
1. Fetch business's UCP profile from `/.well-known/ucp` (cache as appropriate)
1. Locate key in `signing_keys` with matching `kid`
1. Verify `Content-Digest` matches SHA-256 of raw body
1. Reconstruct signature base and verify signature

See [Message Signatures - REST Request Verification](http://ucp.dev/draft/specification/signatures/#rest-request-verification) for complete algorithm.

**Authorization** (order ownership):

After verifying the signature, the platform **MUST** confirm the signer is authorized to send events for the referenced order:

1. Extract the order ID from the webhook payload
1. Verify the order was created with this business (profile URL matches)
1. Reject webhooks where the signer's profile doesn't match the order's business

This prevents a malicious business from sending fake events for another business's orders, even with a valid signature.

#### Key Rotation

See [Message Signatures - Key Rotation](http://ucp.dev/draft/specification/signatures/#key-rotation) for zero-downtime key rotation procedures.

## Guidelines

**Platform:**

- **MUST** respond quickly with a 2xx HTTP status code to acknowledge receipt
- Process events asynchronously after responding

**Business:**

- **MUST** include `UCP-Agent` header with profile URL for signer identification
- **MUST** sign all webhook payloads per the [Message Signatures](http://ucp.dev/draft/specification/signatures/index.md) specification using RFC 9421 headers (`Signature`, `Signature-Input`, `Content-Digest`).
- **MUST** send "Order created" event with fully populated order entity
- **MUST** send full order entity on updates (not incremental deltas)
- **MUST** retry failed webhook deliveries

## Entities

### Item

| Name      | Type                                             | Required | Description                                                                                                                                                                 |
| --------- | ------------------------------------------------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id        | string                                           | **Yes**  | The product identifier, often the SKU, required to resolve the product details associated with this line item. Should be recognized by both the Platform, and the Business. |
| title     | string                                           | **Yes**  | Product title.                                                                                                                                                              |
| price     | [Amount](/draft/specification/reference/#amount) | **Yes**  | Unit price in ISO 4217 minor units.                                                                                                                                         |
| image_url | string                                           | No       | Product image URI.                                                                                                                                                          |

### Postal Address

| Name             | Type   | Required | Description                                                                                                                                                                                                                               |
| ---------------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| extended_address | string | No       | An address extension such as an apartment number, C/O or alternative name.                                                                                                                                                                |
| street_address   | string | No       | The street address.                                                                                                                                                                                                                       |
| address_locality | string | No       | The locality in which the street address is, and which is in the region. For example, Mountain View.                                                                                                                                      |
| address_region   | string | No       | The region in which the locality is, and which is in the country. Required for applicable countries (i.e. state in US, province in CA). For example, California or another appropriate first-level Administrative division.               |
| address_country  | string | No       | The country. Recommended to be in 2-letter ISO 3166-1 alpha-2 format, for example "US". For backward compatibility, a 3-letter ISO 3166-1 alpha-3 country code such as "SGP" or a full country name such as "Singapore" can also be used. |
| postal_code      | string | No       | The postal code. For example, 94043.                                                                                                                                                                                                      |
| first_name       | string | No       | Optional. First name of the contact associated with the address.                                                                                                                                                                          |
| last_name        | string | No       | Optional. Last name of the contact associated with the address.                                                                                                                                                                           |
| phone_number     | string | No       | Optional. Phone number of the contact associated with the address.                                                                                                                                                                        |

### Response

| Name    | Type    | Required | Description                                                                                                                     |
| ------- | ------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| version | string  | **Yes**  | Entity version in YYYY-MM-DD format.                                                                                            |
| spec    | string  | No       | URL to human-readable specification document.                                                                                   |
| schema  | string  | No       | URL to JSON Schema defining this entity's structure and payloads.                                                               |
| id      | string  | No       | Unique identifier for this entity instance. Used to disambiguate when multiple instances exist.                                 |
| config  | object  | No       | Entity-specific configuration. Structure defined by each entity's schema.                                                       |
| extends | OneOf[] | No       | Parent capability(s) this extends. Present for extensions, absent for root capabilities. Use array for multi-parent extensions. |

### Total

| Name                     | Type | Required | Description |
| ------------------------ | ---- | -------- | ----------- |
| *No properties defined.* |      |          |             |
| *No properties defined.* |      |          |             |

### UCP Response Order Schema

| Name             | Type   | Required | Description                                                                 |
| ---------------- | ------ | -------- | --------------------------------------------------------------------------- |
| version          | string | **Yes**  | UCP version in YYYY-MM-DD format.                                           |
| status           | string | No       | Application-level status of the UCP operation. **Enum:** `success`, `error` |
| services         | object | No       | Service registry keyed by reverse-domain name.                              |
| capabilities     | object | No       | Capability registry keyed by reverse-domain name.                           |
| payment_handlers | object | No       | Payment handler registry keyed by reverse-domain name.                      |
| capabilities     | any    | No       |                                                                             |
