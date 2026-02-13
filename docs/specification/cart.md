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

# Cart Capability

* **Capability Name:** `dev.ucp.shopping.cart`
* **Version:** `DRAFT`

## Overview

The Cart capability enables basket building without the complexity of checkout.
While [Checkout](checkout.md) manages payment handlers, status lifecycle, and
order finalization, cart provides a lightweight CRUD interface for item
collection before purchase intent is established.

**When to use Cart vs Checkout:**

* **Cart**: User is exploring, comparing, saving items for later. No payment
  configuration needed. Platform/agent can freely add, remove, update items.
* **Checkout**: User has expressed purchase intent. Payment handlers are
  configured, status lifecycle begins, session moves toward completion.

The typical flow: `cart session` &#8594; `checkout session` &#8594; `order`

Carts support:

* **Incremental building**: Add/remove items across sessions
* **Localized estimates**: Context-aware pricing without full checkout overhead
* **Sharing**: `continue_url` enables cart sharing and recovery

## Cart vs Checkout

| Aspect | Cart | Checkout |
| ------ | ---- | -------- |
| **Purpose** | Pre-purchase exploration | Purchase finalization |
| **Payment** | None | Required (handlers, instruments) |
| **Status** | Binary (exists/not found) | Lifecycle (`incomplete` → `completed`) |
| **Complete Operation** | No | Yes |
| **Totals** | Estimates (may be partial) | Final pricing |

## Cart-to-Checkout Conversion

When the cart capability is negotiated, platforms can convert a cart to checkout
by providing `cart_id` in the Create Checkout request. The cart contents
(`line_items`, `context`, `buyer`) initialize the checkout session.

```json
{
  "cart_id": "cart_abc123",
  "line_items": []
}
```

Business MUST use cart contents and MUST ignore overlapping fields in checkout payload.
The `cart_id` parameter is only available when the cart capability is advertised
in the business profile.

**Idempotent conversion:**

If an incomplete checkout already exists for the given `cart_id`, the business
MUST return the existing checkout session rather than creating a new one. This
ensures a single active checkout per cart and prevents conflicting sessions.

**Cart lifecycle after conversion:**

When checkout is initialized via `cart_id`, the cart and checkout sessions
SHOULD be linked for the duration of the checkout.

* **During active checkout** — Business SHOULD maintain the cart and reflect
    relevant checkout modifications (quantity changes, item removals) back to
    the cart. This supports back-to-storefront flows when buyers transition
    between checkout and storefront.

* **After checkout completion** — Business MAY clear the cart based on TTL,
    completion of the checkout, or other business logic. Subsequent operations
    on a cleared cart ID return `not_found`; the platform can start a new
    session with `create_cart`.

## Guidelines

### Platform

* **MAY** use carts for pre-purchase exploration and session persistence.
* **SHOULD** convert cart to checkout when user expresses purchase intent.
* **MAY** display `continue_url` for handoff to business UI.
* **SHOULD** handle `not_found` gracefully when cart expires or is canceled.

### Business

* **SHOULD** provide `continue_url` for cart handoff and session recovery.
* TODO: discuss `continue_url` destination - cart vs checkout.
* **SHOULD** provide estimated totals when calculable.
* **MAY** omit fulfillment totals until checkout when address is unknown.
* **SHOULD** return informational messages for validation warnings.
* **MAY** set cart expiry via `expires_at`.
* **SHOULD** follow [cart lifecycle requirements](#cart-to-checkout-conversion)
    when checkout is initialized via `cart_id`.

## Cart Schema Definition

{{ schema_fields('cart_resp', 'cart') }}

## Operations

The Cart capability defines the following logical operations.

| Operation | Description |
| :--- | :--- |
| **Create Cart** | Creates a new cart session. |
| **Get Cart** | Retrieves the current state of a cart session. |
| **Update Cart** | Updates a cart session. |
| **Cancel Cart** | Cancels a cart session. |

### Create Cart

Creates a new cart session with line items and optional buyer/context
information for localized pricing estimates.

* [REST Binding](cart-rest.md#create-cart)
* [MCP Binding](cart-mcp.md#create_cart)

### Get Cart

Retrieves the latest state of a cart session. Returns `not_found` if the cart
does not exist, has expired, or was canceled.

* [REST Binding](cart-rest.md#get-cart)
* [MCP Binding](cart-mcp.md#get_cart)

### Update Cart

Performs a full replacement of the cart session. The platform **MUST** send
the entire cart resource. The provided resource replaces the existing cart
state on the business side.

* [REST Binding](cart-rest.md#update-cart)
* [MCP Binding](cart-mcp.md#update_cart)

### Cancel Cart

Cancels a cart session. Business MUST return the cart state before deletion.
Subsequent operations for this cart ID SHOULD return `not_found`.

* [REST Binding](cart-rest.md#cancel-cart)
* [MCP Binding](cart-mcp.md#cancel_cart)

## Entities

Cart reuses the same entity schemas as [Checkout](checkout.md). This ensures
consistent data structures when converting a cart to a checkout session.

### Line Item

#### Line Item Create Request

{{ schema_fields('types/line_item_create_req', 'checkout') }}

#### Line Item Update Request

{{ schema_fields('types/line_item_update_req', 'checkout') }}

#### Line Item Response

{{ schema_fields('types/line_item_resp', 'checkout') }}

### Buyer

{{ schema_fields('buyer', 'checkout') }}

### Context

{{ schema_fields('context', 'checkout') }}

### Total

{{ schema_fields('types/total_resp', 'checkout') }}

Taxes MAY be included where calculable. Platforms SHOULD assume cart totals
are estimates; accurate taxes are computed at checkout.

### Message

{{ schema_fields('message', 'checkout') }}

#### Message Error

{{ schema_fields('types/message_error', 'checkout') }}

#### Message Info

{{ schema_fields('types/message_info', 'checkout') }}

#### Message Warning

{{ schema_fields('types/message_warning', 'checkout') }}

### Link

{{ schema_fields('types/link', 'checkout') }}
