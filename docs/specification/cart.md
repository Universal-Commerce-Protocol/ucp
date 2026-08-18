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
* **Outcome observability**: `status` lets a platform learn how a cart ended,
  including after a one-way handoff it does not otherwise participate in

## Cart vs Checkout

| Aspect | Cart | Checkout |
| ------ | ---- | -------- |
| **Purpose** | Pre-purchase exploration | Purchase finalization |
| **Payment** | None | Required (handlers, instruments) |
| **Status** | Terminal disposition only (`active` → `ordered`) | Full lifecycle (`incomplete` → `completed`) |
| **Complete Operation** | No | Yes |
| **Totals** | Estimates (may be partial) | Final pricing |

Cart defines no intermediate states. Every state between purchase intent and
order placement belongs to Checkout. Cart carries only a terminal disposition,
so that how a cart ended is reported rather than inferred.

## Cart Status

The cart `status` field indicates the cart's disposition. The business sets the
status. `active` is the only non-terminal value; the remaining values are
terminal and **MUST NOT** change once reached.

* **`active`**: Cart accepts reads and updates. This is the state a cart is
    created in.

* **`ordered`**: Cart contents were purchased. Terminal. Independent of the flow
    that placed the order — a UCP checkout session, the business's own web
    checkout following a `continue_url` handoff, or any other flow the business
    supports. The business sets it from its own record of the purchase; no UCP
    checkout session need exist.

* **`canceled`**: Cart was canceled via [Cancel Cart](#cancel-cart) or by the
    business. Terminal.

* **`expired`**: Cart passed `expires_at` without being ordered. Terminal.

```text
                                            +-----------+
                    +---------------------->|  ordered  |
                    | contents purchased    +-----------+
                    |
                    |                       +-----------+
   +----------+     |                       | canceled  |
   |  active  |-----+---------------------->|           |
   +----------+     |   Cancel Cart         +-----------+
                    |
                    |                       +-----------+
                    +---------------------->|  expired  |
                        past expires_at     +-----------+

                    (terminal states are immutable)
```

Operations that would mutate a cart in a terminal state **MUST** fail. The
platform can start a fresh session with Create Cart. Cancel Cart on a cart that
is already `canceled` **SHOULD** succeed and return the canceled cart, so that
cancellation remains idempotent.

| Code | Meaning |
| :--- | :--- |
| `cart_not_active` | A mutating operation was called on a cart whose `status` is terminal. |

### Expiry and Retention

Expiry and retention are separate concerns. Cart defines the first only.

* **Expiry** — `expires_at` is the RFC 3339 deadline after which the cart is no
    longer usable. Passing it transitions `status` to `expired`. Businesses
    **MAY** set `expires_at`; cart defines no default TTL.

* **Retention** — how long the business keeps the record after the cart reaches
    a terminal state, and therefore how long that `status` stays observable.
    Cart defines no field and no default for retention. Once the record is
    discarded, Get Cart returns `not_found`.

A terminal `status` is therefore readable for a bounded, business-specific
window. Platforms **MUST NOT** assume a terminal `status` remains retrievable
indefinitely.

### Relationship to `not_found`

A terminal `status` and `not_found` are different answers. `not_found` reports
that no record exists; it does not report how a cart ended. It covers ordered,
canceled, expired, and never-existed alike, so a platform cannot use it to tell
a purchase from an abandonment.

Businesses **SHOULD** report the terminal `status` in preference to `not_found`
for carts they still hold. `not_found` remains correct for cart IDs that never
existed and for records already discarded.

## Detecting Outcome After Handoff

Cart handoff via `continue_url` is one-way. The buyer completes the purchase in
the business UI, and the platform does not participate in that flow — it may
hold no checkout session and issue no further calls. The platform is still
surfacing the cart, so it needs to know whether to continue doing so.

Platforms **SHOULD** poll [Get Cart](#get-cart) after a handoff and act on
`status`:

| `status` | Meaning | Platform Action |
| :--- | :--- | :--- |
| `active` | Buyer has not finished | Continue surfacing the cart, subject to `expires_at` |
| `ordered` | Cart contents were purchased | Stop surfacing the cart as pending; stop prompting the buyer to complete it |
| `canceled` | Cart was canceled | Release the cart; **MAY** offer to rebuild |
| `expired` | Cart passed `expires_at` without a purchase | Release the cart; **MAY** offer to rebuild |
| `not_found` | No record retained | Outcome unknown; **MUST NOT** be read as purchased or as abandoned |

`ordered` and `canceled`/`expired` prescribe opposite handling, which is why
`not_found` is not a substitute for `status`. Because terminal values are
immutable, a platform that observes one **MAY** stop polling; no later reversal
occurs at this layer.

### Scope of `ordered`

`ordered` reports that cart contents were purchased. It does not identify the
resulting order and carries no fulfillment information.

Platforms requiring the order itself — for reconciliation, attribution, or
post-purchase support — **MUST** obtain it from the [Checkout](checkout.md)
capability, whose `order_confirmation` carries the order `id` and
`permalink_url`, and track delivery through the [Order](order.md) capability.
Cart `status` is a cart lifecycle signal, not an order handle.

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

* **During active checkout** — Cart `status` remains `active`. Business SHOULD
    maintain the cart and reflect relevant checkout modifications (quantity
    changes, item removals) back to the cart. This supports back-to-storefront
    flows when buyers transition between checkout and storefront.

* **After checkout completion** — Business **MUST** set cart `status` to
    `ordered`. Business **MAY** subsequently discard the cart based on TTL or
    other business logic, after which operations on that cart ID return
    `not_found`; the platform can start a new session with `create_cart`.

Conversion is one path to `ordered`, not the only one. A business whose buyers
finish on its own web checkout after a `continue_url` handoff sets `ordered`
from that flow. See [Cart Status](#cart-status).

> **Note:** Cart defines no retention window — see
> [Expiry and Retention](#expiry-and-retention). A cart discarded before the
> platform polls is indistinguishable from one that was never ordered, so
> businesses supporting handoff **SHOULD** retain terminal carts long enough for
> the outcome to be read.

## Quantity and sale basis

Cart line items apply the shared
[quantities and units](overview.md#quantities-and-units) contract. Each
`line_items[].quantity` is an integer step count in the item's authoritative
sale basis. On a Business response, an absent
`line_items[].item.quantity_unit` encodes the default `each` basis, so
`quantity` counts whole items.

On a Platform request, omission of `line_items[].item.quantity_unit` makes no
assertion. The Business interprets `quantity` using the item's authoritative
sale basis, so a request for a measure-denominated item can omit the descriptor
without asserting `each`. The Platform **MAY** include `item.quantity_unit` to
assert the sale-basis identity.

Cart follows [Checkout — Quantity and sale basis](checkout.md#quantity-and-sale-basis)
for sale-basis discovery, assertion matching, mismatch conversion or
rejection, response echo, ordering-increment handling, and line pricing.
Cart totals remain estimates (see [Total](#total)). A measure-denominated line
counts as one line item in cart summaries; its `quantity` is an amount, not an
item count.

## Actions

The cart surfaces outstanding Action instances in its response-only `actions`
map, defined in [Overview — Actions](overview.md#actions).

The cart has no intermediate status lifecycle to advance; `status` records only a
terminal disposition (see [Cart Status](#cart-status)). Actions **MUST NOT**
change `status`, and an outstanding Action does not prevent a cart from remaining
`active`. Each Action gates only the cart effect specified for its Action type.
The Business **MUST NOT** treat an outstanding Action as a reason to reject an
unrelated cart operation. The Platform **MAY** continue to add, remove, and
update items while an Action is outstanding.

After processing an Action, the Platform **SHOULD** use [Get Cart](#get-cart)
or a subsequent update response to obtain the latest Cart.

## Scopes

The Cart capability defines the following well-known scopes for
user-authenticated access:

| Scope | Description |
| :--- | :--- |
| `dev.ucp.shopping.cart:manage` | All cart operations on behalf of the authenticated user — create, read, update, persist. |

Scope declaration, derivation, and rules for extending this set with
custom scopes are defined in [Identity Linking — Scopes](identity-linking.md#scopes).

## Guidelines

### Platform

* **MAY** use carts for pre-purchase exploration and session persistence.
* **SHOULD** convert cart to checkout when user expresses purchase intent.
* **MAY** display `continue_url` for handoff to business UI.
* **SHOULD** poll Get Cart after a `continue_url` handoff to observe `status`
    rather than inferring the outcome from `not_found`.
* **MUST NOT** treat `not_found` as evidence that an order was or was not
    placed.
* **SHOULD** stop surfacing a cart as pending once `status` is terminal.
* **MUST NOT** assume a terminal `status` remains retrievable indefinitely.
* **MUST NOT** rely on cart `status` to identify or track the resulting order;
    use the [Checkout](checkout.md) and [Order](order.md) capabilities instead.
* **SHOULD** handle `not_found` gracefully when the business retains no record.

### Business

* **SHOULD** provide `continue_url` for cart handoff and session recovery.
* TODO: discuss `continue_url` destination - cart vs checkout.
* **MUST** set `status` = `ordered` once cart contents have been purchased,
    regardless of which flow placed the order.
* **MUST NOT** change `status` once it holds a terminal value.
* **SHOULD** return the terminal `status` in preference to `not_found` for carts
    they still hold.
* **SHOULD** retain terminal carts long enough for a handed-off platform to read
    the outcome.
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

* [REST Binding](cart-rest.md#create-cart)
* [MCP Binding](cart-mcp.md#create_cart)

### Get Cart

Retrieves the latest state of a cart session, including its `status`. This is the
operation a platform polls to
[detect the outcome of a handoff](#detecting-outcome-after-handoff).

Carts that have reached a terminal state are still returned, carrying the
terminal `status`. Returns `not_found` only when the business holds no record
for the cart ID.

* [REST Binding](cart-rest.md#get-cart)
* [MCP Binding](cart-mcp.md#get_cart)

### Update Cart

Performs a full replacement of the cart session. The platform **MUST** send
the entire cart resource. The provided resource replaces the existing cart
state on the business side.

Only carts with `status` = `active` are updatable. Updating a cart in a
terminal state **MUST** fail with `cart_not_active`.

* [REST Binding](cart-rest.md#update-cart)
* [MCP Binding](cart-mcp.md#update_cart)

### Cancel Cart

Cancels a cart session. Business **MUST** return the cart with `status` set to
`canceled`, and **SHOULD** return the same for a cart that is already
`canceled`, keeping the operation idempotent.

Cancel Cart on a cart that is `ordered` **MUST** fail with `cart_not_active` —
the order has been placed, and cancellation at that point is an
[Order](order.md) concern, not a cart one.

* [REST Binding](cart-rest.md#cancel-cart)
* [MCP Binding](cart-mcp.md#cancel_cart)

## Entities

Cart reuses the same entity schemas as [Checkout](checkout.md). This ensures
consistent data structures when converting a cart to a checkout session.

### UCP Response Cart {: #ucp-response-cart-schema }

{{ extension_schema_fields('ucp.json#/$defs/response_cart_schema', 'cart') }}

### Line Item

#### Line Item Create Request

{{ schema_fields('types/line_item_create_req', 'checkout') }}

#### Line Item Update Request

{{ schema_fields('types/line_item_update_req', 'checkout') }}

#### Line Item

{{ schema_fields('types/line_item_resp', 'cart') }}

#### Item

{{ schema_fields('types/item_resp', 'cart') }}

### Buyer

{{ schema_fields('buyer', 'checkout') }}

### Context

{{ schema_fields('context', 'checkout') }}

### Signals

Environment data provided by the platform to support authorization
and abuse prevention. Signal values MUST NOT be buyer-asserted claims. See
[Signals](overview.md#signals) for details and privacy
requirements.

{{ schema_fields('types/signals', 'checkout') }}

### Attribution

Platform-provided referral and conversion-event context — campaign IDs,
click identifiers, and source/medium markers communicated by the platform.
See [Attribution](overview.md#attribution) for details and consent
requirements.

{{ schema_fields('types/attribution', 'checkout') }}

### Total

The same totals contract applies to cart and checkout. See
[Checkout Totals](checkout.md#totals) for the rendering contract, accounting
identity, well-known types, repeating types, and sub-line semantics.

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

### Policy

Policies (return/refund terms, warranty, and the like) that apply to the items
in this cart. JSONPath targets in `applies_to` are relative to
this response root (e.g., `$.line_items[0]`). See
[Policies](overview.md#policies) for the full model.

{{ schema_fields('types/policy', 'cart') }}
