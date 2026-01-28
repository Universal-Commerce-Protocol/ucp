# Order Capability

- **Capability Name:** `dev.ucp.shopping.order`

## Overview

Orders represent confirmed transactions resulting from a successful checkout submission. It provides a complete record of what was purchased, how it will be delivered, and what has happened since order placement.

### Key Concepts

Orders have three main components:

**Line Items** — what was purchased at checkout:

- Includes current quantity counts (total, fulfilled)

**Fulfillment** — how items get delivered:

- **Expectations** — buyer-facing *promises* about when/how items will arrive
- **Events** (append-only log) — what actually happened (e.g. 👕 was shipped)

**Adjustments** (append-only log) — post-order events independent of fulfillment:

- Typically money movements (refunds, returns, credits, disputes, cancellations)
- Can be any post-order change
- Can happen before, during, or after fulfillment

## Data Model

### Line Items

Line items reflect what was purchased at checkout and their current state:

- Item details (product, price, quantity ordered)
- Quantity counts and status are derived

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

**Adjustments** are an append-only log of events that exist independently of fulfillment:

- Type is an open string field - businesses can use any values that make sense (typically money movements like `refund`, `return`, `credit`, `price_adjustment`, `dispute`, `cancellation`)
- Can be any post-order change
- Optionally link to line items (or order-level for things like shipping refunds)
- Include amount when relevant
- Can happen at any time regardless of fulfillment status

## Schema

### Order

| Name          | Type                                                                               | Required | Description                                                                                                                                  |
| ------------- | ---------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp           | [UCP Response Order Schema](/draft/specification/order/#ucp-response-order-schema) | **Yes**  | Protocol metadata for discovery profiles and responses. Uses slim schema pattern with context-specific required fields.                      |
| id            | string                                                                             | **Yes**  | Unique order identifier.                                                                                                                     |
| checkout_id   | string                                                                             | **Yes**  | Associated checkout ID for reconciliation.                                                                                                   |
| permalink_url | string                                                                             | **Yes**  | Permalink to access the order on merchant site.                                                                                              |
| line_items    | Array\[[Order Line Item](/draft/specification/order/#order-line-item)\]            | **Yes**  | Immutable line items — source of truth for what was ordered.                                                                                 |
| fulfillment   | object                                                                             | **Yes**  | Fulfillment data: buyer expectations and what actually happened.                                                                             |
| adjustments   | Array\[[Adjustment](/draft/specification/order/#adjustment)\]                      | No       | Append-only event log of money movements (refunds, returns, credits, disputes, cancellations, etc.) that exist independently of fulfillment. |
| totals        | Array\[[Total Response](/draft/specification/order/#total-response)\]              | **Yes**  | Different totals for the order.                                                                                                              |

### Order Line Item

Line items reflect what was purchased at checkout and their current state. Status and quantity counts should reflect the event logs.

| Name      | Type                                                | Required | Description                                                                                                                                                                |
| --------- | --------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id        | string                                              | **Yes**  | Line item identifier.                                                                                                                                                      |
| item      | [Item](/draft/specification/order/#item)            | **Yes**  | Product data (id, title, price, image_url).                                                                                                                                |
| quantity  | object                                              | **Yes**  | Quantity tracking. Both total and fulfilled are derived from events.                                                                                                       |
| totals    | Array\[[Total](/draft/specification/order/#total)\] | **Yes**  | Line item totals breakdown.                                                                                                                                                |
| status    | string                                              | **Yes**  | Derived status: fulfilled if quantity.fulfilled == quantity.total, partial if quantity.fulfilled > 0, otherwise processing. **Enum:** `processing`, `partial`, `fulfilled` |
| parent_id | string                                              | No       | Parent line item identifier for any nested structures.                                                                                                                     |

**Quantity Structure:**

```json
{
  "total": 3,      // Current total quantity
  "fulfilled": 2   // What has been fulfilled
}
```

**Status Derivation:**

```text
if (fulfilled == total) → "fulfilled"
else if (fulfilled > 0) → "partial"
else → "processing"
```

### Expectation

Expectations are buyer-facing groupings representing when/how items will be delivered. They represent the current promise to the buyer and can be split, merged, or adjusted post-order.

| Name           | Type                                                         | Required | Description                                                                                                 |
| -------------- | ------------------------------------------------------------ | -------- | ----------------------------------------------------------------------------------------------------------- |
| id             | string                                                       | **Yes**  | Expectation identifier.                                                                                     |
| line_items     | Array[object]                                                | **Yes**  | Which line items and quantities are in this expectation.                                                    |
| method_type    | string                                                       | **Yes**  | Delivery method type (shipping, pickup, digital). **Enum:** `shipping`, `pickup`, `digital`                 |
| destination    | [Postal Address](/draft/specification/order/#postal-address) | **Yes**  | Delivery destination address.                                                                               |
| description    | string                                                       | No       | Human-readable delivery description (e.g., 'Arrives in 5-8 business days').                                 |
| fulfillable_on | string                                                       | No       | When this expectation can be fulfilled: 'now' or ISO 8601 timestamp for future date (backorder, pre-order). |

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

| Name        | Type          | Required | Description                                                                                                                                                                                     |
| ----------- | ------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string        | **Yes**  | Adjustment event identifier.                                                                                                                                                                    |
| type        | string        | **Yes**  | Type of adjustment (open string). Typically money-related like: refund, return, credit, price_adjustment, dispute, cancellation. Can be any value that makes sense for the merchant's business. |
| occurred_at | string        | **Yes**  | RFC 3339 timestamp when this adjustment occurred.                                                                                                                                               |
| status      | string        | **Yes**  | Adjustment status. **Enum:** `pending`, `completed`, `failed`                                                                                                                                   |
| line_items  | Array[object] | No       | Which line items and quantities are affected (optional).                                                                                                                                        |
| amount      | integer       | No       | Amount in minor units (cents) for refunds, credits, price adjustments (optional).                                                                                                               |
| description | string        | No       | Human-readable reason or description (e.g., 'Defective item', 'Customer requested').                                                                                                            |

Examples: `refund`, `return`, `credit`, `price_adjustment`, `dispute`, `cancellation`, etc.

## Example

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": {
      "dev.ucp.shopping.order": [{"version": "2026-01-11"}]
    }
  },
  "id": "order_abc123",
  "checkout_id": "checkout_xyz789",
  "permalink_url": "https://business.com/orders/abc123",
  "line_items": [
    {
      "id": "li_shoes",
      "item": { "id": "prod_shoes", "title": "Running Shoes", "price": 3000 },
      "quantity": { "total": 3, "fulfilled": 3 },
      "totals": [
        {"type": "subtotal", "amount": 9000},
        {"type": "total", "amount": 9000}
      ],
      "status": "fulfilled"
    },
    {
      "id": "li_shirts",
      "item": { "id": "prod_shirts", "title": "Cotton T-Shirt", "price": 2000 },
      "quantity": { "total": 2, "fulfilled": 0 },
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
      "line_items": [{ "id": "li_shoes", "quantity": 1 }],
      "amount": 3000,
      "description": "Defective item"
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 13000 },
    { "type": "shipping", "amount": 1200 },
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

**Error processing OpenAPI:** [Errno 2] No such file or directory: 'source/services/shopping/rest.openapi.json'

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
      "version": "2026-01-11",
      "config": {
        "webhook_url": "https://platform.example.com/webhooks/ucp/orders"
      }
    }
  ]
}
```

### Webhook Signature Verification

Webhook payloads **MUST** be signed by the business and verified by the platform to ensure authenticity and integrity.

#### Signing (Business)

1. Select a key from the `signing_keys` array in UCP profile.
1. Create a detached JWT (RFC 7797) over the request body using the selected key.
1. Include the JWT in the `Request-Signature` header.
1. Include the key ID in the JWT header's `kid` claim to allow the receiver to identify which key to use for verification.

#### Verification (Platform)

1. Extract the `Request-Signature` header from the incoming webhook request.
1. Parse the JWT header to retrieve the `kid` (key ID).
1. Fetch the business's UCP profile from `/.well-known/ucp` (cache as appropriate).
1. Locate the key in `signing_keys` with the matching `kid`.
1. Verify the JWT signature against the request body using the public key.
1. If verification fails, reject the webhook with an appropriate error response.

#### Key Rotation

The `signing_keys` array supports multiple keys to enable zero-downtime rotation:

- **Adding a new key:** Add the new key to `signing_keys`, then start signing with it. Verifiers will find it by `kid`.
- **Removing an old key:** After sufficient time for all in-flight webhooks to be delivered, remove the old key from `signing_keys`.

## Guidelines

**Platform:**

- **MUST** respond quickly with a 2xx HTTP status code to acknowledge receipt
- Process events asynchronously after responding

**Business:**

- **MUST** sign all webhook payloads using a key from their `signing_keys` array (published in `/.well-known/ucp`). The signature **MUST** be included in the `Request-Signature` header as a detached JWT (RFC 7797).
- **MUST** send "Order created" event with fully populated order entity
- **MUST** send full order entity on updates (not incremental deltas)
- **MUST** retry failed webhook deliveries
- **MUST** include business identifier in webhook path or headers

## Entities

### Item Response

| Name      | Type    | Required | Description                                                                                                                                                                 |
| --------- | ------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id        | string  | **Yes**  | The product identifier, often the SKU, required to resolve the product details associated with this line item. Should be recognized by both the Platform, and the Business. |
| title     | string  | **Yes**  | Product title.                                                                                                                                                              |
| price     | integer | **Yes**  | Unit price in minor (cents) currency units.                                                                                                                                 |
| image_url | string  | No       | Product image URI.                                                                                                                                                          |

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

| Name                                                                                        | Type | Required | Description |
| ------------------------------------------------------------------------------------------- | ---- | -------- | ----------- |
| **Error:** Failed to resolve ''. Ensure ucp-schema is installed: `cargo install ucp-schema` |      |          |             |

### Total Response

| Name         | Type    | Required | Description                                                                                                                   |
| ------------ | ------- | -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| type         | string  | **Yes**  | Type of total categorization. **Enum:** `items_discount`, `subtotal`, `discount`, `fulfillment`, `tax`, `fee`, `total`        |
| display_text | string  | No       | Text to display against the amount. Should reflect appropriate method (e.g., 'Shipping', 'Delivery').                         |
| amount       | integer | **Yes**  | If type == total, sums subtotal - discount + fulfillment + tax + fee. Should be >= 0. Amount in minor (cents) currency units. |

### UCP Response Order

| Name                                                                                        | Type | Required | Description |
| ------------------------------------------------------------------------------------------- | ---- | -------- | ----------- |
| **Error:** Failed to resolve ''. Ensure ucp-schema is installed: `cargo install ucp-schema` |      |          |             |
| capabilities                                                                                | any  | No       |             |
