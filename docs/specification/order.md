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

# Order Capability

* **Capability Name:** `dev.ucp.shopping.order`

## Overview

Orders represent confirmed transactions resulting from a successful checkout
submission. They provide a complete record of what was purchased, how
it will be delivered, and what has happened since order placement.

### Key Concepts

Orders have three main components:

**Line Items** — what was purchased at checkout:

* Includes current quantity counts (total, fulfilled)
* Can change post-order (e.g. order edits, exchanges); **MUST** include all
  line items that ever existed on the order regardless of edits or alterations

**Fulfillment** — how items get delivered:

* **Expectations** — buyer-facing *promises* about when/how items will arrive
* **Events** (append-only log) — what actually happened (e.g. 👕 was shipped)

**Adjustments** — post-order events independent of fulfillment:

* Typically money movements (refunds, returns, credits, disputes, cancellations)
* Can be any post-order change
* Can happen before, during, or after fulfillment
* Businesses **SHOULD** append new entries rather than mutating existing ones;
  append-only ledger is preferred. Businesses that do not maintain adjustment
  history **MAY** perform in-place updates of existing entries
  (e.g. a single `return` adjustment can transition from `pending` to `completed`)

## Data Model

### Line Items

Line items reflect what was purchased at checkout and their current state:

* Item details (product, price, quantity ordered)
* Quantity counts and fulfillment status

### Fulfillment

Fulfillment tracks how items are delivered to the buyer.

#### Expectations

**Expectations** are buyer-facing groupings of items (e.g., "package 📦"). They represent:

* What items are grouped together
* Where they're going (`destination`)
* How they're being delivered (`method_type`)
* When they'll arrive (`description`, `fulfillable_on`)

Expectations can be split, merged, or adjusted post-order. For example:

* Group everything by delivery date: "what is coming when"
* Use a single expectation with a wide date range for flexibility
* The goal is **setting buyer expectations** - for the best buyer experience

#### Fulfillment Events

**Fulfillment Events** are an append-only log tracking physical shipments:

* Reference line items by ID and quantity
* Include tracking information
* Type is an open string field - businesses can use any values that make sense
  (common examples: `processing`, `shipped`, `in_transit`, `delivered`,
  `failed_attempt`, `canceled`, `undeliverable`, `returned_to_sender`)

### Adjustments

**Adjustments** are post-order events that exist independently of
fulfillment:

* Type is an open string field - businesses can use any values that make sense
  (typically money movements like `refund`, `return`, `credit`,
  `price_adjustment`, `dispute`, `cancellation`)
* Can be any post-order change
* Optionally link to line items (or order-level for things like shipping refunds)
* Quantities and amounts are signed—negative for reductions (returns, refunds),
  positive for additions (exchanges)
* Include totals breakdown when relevant
* Can happen at any time regardless of fulfillment status

## Schema

### Order

{{ schema_fields('order', 'order') }}

### Order Line Item

Line items reflect what was purchased at checkout and their current state.

{{ schema_fields('order_line_item', 'order') }}

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

Expectations are buyer-facing groupings representing when/how items will be
delivered. They represent the current promise to the buyer and can be
split, merged, or adjusted post-order.

{{ schema_fields('expectation', 'order') }}

### Fulfillment Event

Events are append-only records tracking actual shipments. The `type` field is
an open string - businesses can use any values that make sense for their
fulfillment process.

{{ schema_fields('fulfillment_event', 'order') }}

Examples: `processing`, `shipped`, `in_transit`, `delivered`, `failed_attempt`,
`canceled`, `undeliverable`, `returned_to_sender`, etc.

### Adjustment

Adjustments are polymorphic events that exist independently of fulfillment.
The `type` field is an open string - businesses can use any values that make
sense to them.

{{ schema_fields('adjustment', 'order') }}

Examples: `refund`, `return`, `credit`, `price_adjustment`, `dispute`,
`cancellation`, etc.

## Example

```json
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

## Operations

The order entity is a **current-state snapshot**: the authoritative latest
state of the order at the time of retrieval or delivery. Businesses **MUST**
return the full order entity on every response. The same schema is used
for both synchronous retrieval (this section) and asynchronous event
delivery (see [Events](#events)).

The `permalink_url` is the authoritative reference for the full order
experience - timeline, post-purchase operations, returns. The API provides
programmatic access to current state for conversational and operational use
cases.

| Operation                               | Method | Endpoint       | Description                             |
| :-------------------------------------- | :----- | :------------- | :-------------------------------------- |
| [Get Order](#get-order)                 | `GET`  | `/orders/{id}` | Platform retrieves current order state. |

For transport-specific details, see [REST Binding](order-rest.md), and
[MCP Binding](order-mcp.md)

### Get Order

Returns the current-state snapshot of an order.

#### Authorization

The business **MUST** authenticate requests to order data before returning a
response, using any supported UCP mechanism - API keys, OAuth 2.0, mutual
TLS, or HTTP Message Signatures (see
[Identity and Authentication](checkout-rest.md#authentication)). The
authentication method determines the scope of accessible orders:

| Authentication | Recommended Access Scope |
| :------------- | :----------------------- |
| Platform credentials | Orders originated by the platform |
| Buyer authorization | Orders originated by the buyer, subject to granted scope |

**Platform credentials** (API key, signatures, OAuth client credentials) -
businesses **MAY** allow access for orders the platform originated. The
platform provided buyer and payment information during the checkout flow,
observed the order confirmation, and is retrieving the latest state of an
order it already has context for.

**Buyer authorization** - the platform obtains buyer authorization via
[Identity Linking](identity-linking.md) with the necessary scopes, or a
similar mechanism. This grants access to the buyer's orders regardless of
which platform originated them.

Businesses **MAY** define additional access policies (e.g., trusted partner
agreements), enforce data availability constraints (e.g., retention
windows, regulatory erasure), and omit or redact optional fields from the response
based on context, business policy, or other requirements - independently
of authorization.

#### Error Responses

When the business cannot return an order, the response returns an error
that includes a `messages` array describing the outcome:

**Order not found:**

```json
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

**Not authorized:**

```json
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

### Guidelines {: #operations-guidelines }

**Platform:**

* **MUST** include `UCP-Agent` header with profile URL on all requests
* **SHOULD** rely on webhooks (see [Events](#events)) as the primary order update channel
  and use Get Order for reconciliation or on-demand retrieval
* **SHOULD** treat order data as ephemeral and discard it when no longer needed
  for active commerce flows

**Business:**

* **MUST** authenticate requests to order data before returning a response
  (see [Authorization](#authorization))

## Events

Businesses push order lifecycle updates to the platform via webhooks. The
payload is the same **current-state snapshot** described in
[Operations](#operations) — the full order entity.

| Event                                       | Method | Endpoint              | Description                                            |
| :------------------------------------------ | :----- | :-------------------- | :----------------------------------------------------- |
| [Order Event Webhook](#order-event-webhook) | `POST` | Platform-provided URL | Business sends order lifecycle events to the platform. |

### Order Event Webhook

Businesses POST order events to a webhook URL provided by the platform
during partner onboarding. The URL format is platform-specific.

{{ method_fields('order_event_webhook', 'rest.openapi.json', 'order') }}

### Webhook URL Configuration

The platform provides its webhook URL in the order capability's `config` field
during capability negotiation. The business discovers this URL from the
platform's profile and uses it to send order lifecycle events.

{{ extension_schema_fields('order.json#/$defs/platform_schema', 'order') }}

**Example:**

```json
{
  "dev.ucp.shopping.order": [
    {
      "version": "{{ ucp_version }}",
      "config": {
        "webhook_url": "https://platform.example.com/webhooks/ucp/orders"
      }
    }
  ]
}
```

### Webhook Signature Verification

Webhook payloads **MUST** be signed by the business and verified by the platform
to ensure authenticity and integrity. Signatures follow the
[Message Signatures](signatures.md) specification using the REST binding
(RFC 9421).

**Required Headers:**

| Header           | Description                                |
| :--------------- | :----------------------------------------- |
| `UCP-Agent`      | Business profile URL (RFC 8941 Dictionary) |
| `Signature-Input`| Describes signed components                |
| `Signature`      | Contains the signature value               |
| `Content-Digest` | Body digest (RFC 9530)                     |

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
2. Build signature base per [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421)
3. Sign using a key from `signing_keys` in the business's UCP profile
4. Set `Signature-Input` and `Signature` headers

See [Message Signatures - REST Request Signing](signatures.md#rest-request-signing)
for complete algorithm.

#### Verification (Platform)

**Authentication** (signature verification):

1. Parse `Signature-Input` to extract `keyid` and signed components
2. Fetch business's UCP profile from `/.well-known/ucp` (cache as appropriate)
3. Locate key in `signing_keys` with matching `kid`
4. Verify `Content-Digest` matches SHA-256 of raw body
5. Reconstruct signature base and verify signature

See [Message Signatures - REST Request Verification](signatures.md#rest-request-verification)
for complete algorithm.

**Authorization** (order ownership):

After verifying the signature, the platform **MUST** confirm the signer is
authorized to send events for the referenced order:

1. Extract the order ID from the webhook payload
2. Verify the order was created with this business (profile URL matches)
3. Reject webhooks where the signer's profile doesn't match the order's business

This prevents a malicious business from sending fake events for another
business's orders, even with a valid signature.

#### Key Rotation

See [Message Signatures - Key Rotation](signatures.md#key-rotation) for
zero-downtime key rotation procedures.

### Guidelines {: #events-guidelines }

**Platform:**

* **MUST** respond quickly with a 2xx HTTP status code to acknowledge webhook
  receipt; process events asynchronously after responding

**Business:**

* **MUST** include `UCP-Agent` header with profile URL for signer identification
* **MUST** sign all webhook payloads per the
  [Message Signatures](signatures.md) specification using RFC 9421 headers
  (`Signature`, `Signature-Input`, `Content-Digest`)
* **MUST** send "Order created" event with fully populated order entity
* **MUST** send full order entity on updates (not incremental deltas)
* **MUST** retry failed webhook deliveries

## Entities

### Item

{{ schema_fields('types/item_resp', 'order') }}

### Postal Address

{{ schema_fields('postal_address', 'order') }}

### Response

{{ extension_schema_fields('capability.json#/$defs/response_schema', 'order') }}

### Total

{{ schema_fields('types/total_resp', 'order') }}

### UCP Response Order Schema <span id="ucp"></span> {: #ucp-response-order-schema }

{{ extension_schema_fields('ucp.json#/$defs/response_order_schema', 'order') }}
