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

## Overview

The Cart capability enables basket building without the complexity of checkout.
While [Checkout](../checkout/index.md) manages payment handlers, status lifecycle, and
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

<!-- ucp:example schema=shopping/cart def=checkout op=create direction=request -->
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

## Quantity and sale basis

Cart line items apply the shared
[quantities and units](../../overview/index.md#quantities-and-units) contract. Each
`line_items[].quantity` is an integer step count in the item's authoritative
sale basis. On a Business response, an absent
`line_items[].item.quantity_unit` encodes the default `each` basis, so
`quantity` counts whole items.

On a Platform request, omission of `line_items[].item.quantity_unit` makes no
assertion. The Business interprets `quantity` using the item's authoritative
sale basis, so a request for a measure-denominated item can omit the descriptor
without asserting `each`. The Platform **MAY** include `item.quantity_unit` to
assert the sale-basis identity.

Cart follows [Checkout — Quantity and sale basis](../checkout/index.md#quantity-and-sale-basis)
for sale-basis discovery, assertion matching, mismatch conversion or
rejection, response echo, ordering-increment handling, and line pricing.
Cart totals remain estimates (see [Total](#total)). A measure-denominated line
counts as one line item in cart summaries; its `quantity` is an amount, not an
item count.

## Actions

The cart surfaces outstanding Action instances in its response-only `actions`
map, defined in [Overview — Actions](../../overview/index.md#actions).

The cart has no status lifecycle. Each Action gates only the cart effect
specified for its Action type. The Business **MUST NOT** treat an outstanding
Action as a reason to reject an unrelated cart operation. The Platform **MAY**
continue to add, remove, and update items while an Action is outstanding.

After processing an Action, the Platform **SHOULD** use [Get Cart](#get-cart)
or a subsequent update response to obtain the latest Cart.

## Scopes

The Cart capability defines the following well-known scopes for
user-authenticated access:

| Scope | Description |
| :--- | :--- |
| `dev.ucp.shopping.cart:manage` | All cart operations on behalf of the authenticated user — create, read, update, persist. |

Scope declaration, derivation, and rules for extending this set with
custom scopes are defined in [Identity Linking — Scopes](../../common/identity-linking/index.md#scopes).

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

{{ schema_fields('cart_resp', 'shopping/cart') }}

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

When **all** requested items are unavailable, the business MAY return an
error response instead of creating a cart resource. `ucp.status` is the
primary discriminator; the absence of `id` is a consistent secondary
indicator:

<!-- ucp:example schema=common/types/error_response op=read -->
```json
{
  "ucp": { "version": "{{ ucp_version }}", "status": "error" },
  "messages": [
    {
      "type": "error",
      "code": "out_of_stock",
      "content": "All requested items are currently out of stock",
      "severity": "unrecoverable"
    }
  ],
  "continue_url": "https://merchant.com/"
}
```

* [REST Binding](rest.md#create-cart)
* [MCP Binding](mcp.md#create_cart)

### Get Cart

Retrieves the latest state of a cart session. Returns `not_found` if the cart
does not exist, has expired, or was canceled.

* [REST Binding](rest.md#get-cart)
* [MCP Binding](mcp.md#get_cart)

### Update Cart

Performs a full replacement of the cart session. The platform **MUST** send
the entire cart resource. The provided resource replaces the existing cart
state on the business side.

* [REST Binding](rest.md#update-cart)
* [MCP Binding](mcp.md#update_cart)

### Cancel Cart

Cancels a cart session. Business MUST return the cart state before deletion.
Subsequent operations for this cart ID SHOULD return `not_found`.

* [REST Binding](rest.md#cancel-cart)
* [MCP Binding](mcp.md#cancel_cart)

## Entities

Cart reuses the same entity schemas as [Checkout](../checkout/index.md). This ensures
consistent data structures when converting a cart to a checkout session.

### UCP Response Cart {: #ucp-response-cart-schema }

{{ extension_schema_fields('ucp.json#/$defs/response_cart_schema', 'shopping/cart') }}

### Line Item

#### Line Item Create Request

{{ schema_fields('types/line_item_create_req', 'shopping/checkout') }}

#### Line Item Update Request

{{ schema_fields('types/line_item_update_req', 'shopping/checkout') }}

#### Line Item

{{ schema_fields('types/line_item_resp', 'shopping/cart') }}

#### Item

{{ schema_fields('types/item_resp', 'shopping/cart') }}

### Buyer

{{ schema_fields('buyer', 'shopping/checkout') }}

### Context

{{ schema_fields('context', 'shopping/checkout') }}

### Signals

Environment data provided by the platform to support authorization
and abuse prevention. Signal values MUST NOT be buyer-asserted claims. See
[Signals](../../overview/index.md#signals) for details and privacy
requirements.

{{ schema_fields('types/signals', 'shopping/checkout') }}

### Attribution

Platform-provided referral and conversion-event context — campaign IDs,
click identifiers, and source/medium markers communicated by the platform.
See [Attribution](../../overview/index.md#attribution) for details and consent
requirements.

{{ schema_fields('types/attribution', 'shopping/checkout') }}

### Total

The same totals contract applies to cart and checkout. See
[Checkout Totals](../checkout/index.md#totals) for the rendering contract, accounting
identity, well-known types, repeating types, and sub-line semantics.

{{ schema_fields('types/total_resp', 'shopping/checkout') }}

Taxes MAY be included where calculable. Platforms SHOULD assume cart totals
are estimates; accurate taxes are computed at checkout.

### Message

{{ schema_fields('message', 'shopping/checkout') }}

#### Message Error

{{ schema_fields('types/message_error', 'shopping/checkout') }}

#### Message Info

{{ schema_fields('types/message_info', 'shopping/checkout') }}

#### Message Warning

{{ schema_fields('types/message_warning', 'shopping/checkout') }}

### Link

{{ schema_fields('types/link', 'shopping/checkout') }}

### Policy

Policies (return/refund terms, warranty, and the like) that apply to the items
in this cart. JSONPath targets in `applies_to` are relative to
this response root (e.g., `$.line_items[0]`). See
[Policies](../../overview/index.md#policies) for the full model.

{{ schema_fields('types/policy', 'shopping/cart') }}
