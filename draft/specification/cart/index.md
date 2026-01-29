# Cart Capability

- **Capability Name:** `dev.ucp.shopping.cart`
- **Version:** `DRAFT`

## Overview

The Cart capability enables basket building without the complexity of checkout. While [Checkout](https://ucp.dev/draft/specification/checkout/index.md) manages payment handlers, status lifecycle, and order finalization, cart provides a lightweight CRUD interface for item collection before purchase intent is established.

**When to use Cart vs Checkout:**

- **Cart**: User is exploring, comparing, saving items for later. No payment configuration needed. Platform/agent can freely add, remove, update items.
- **Checkout**: User has expressed purchase intent. Payment handlers are configured, status lifecycle begins, session moves toward completion.

The typical flow: `cart session` → `checkout session` → `order`

Carts support:

- **Incremental building**: Add/remove items across sessions
- **Localized estimates**: Context-aware pricing without full checkout overhead
- **Sharing**: `continue_url` enables cart sharing and recovery

## Cart vs Checkout

| Aspect                 | Cart                       | Checkout                               |
| ---------------------- | -------------------------- | -------------------------------------- |
| **Purpose**            | Pre-purchase exploration   | Purchase finalization                  |
| **Payment**            | None                       | Required (handlers, instruments)       |
| **Status**             | Binary (exists/not found)  | Lifecycle (`incomplete` → `completed`) |
| **Complete Operation** | No                         | Yes                                    |
| **Totals**             | Estimates (may be partial) | Final pricing                          |

## Cart-to-Checkout Conversion

When the cart capability is negotiated, platforms can convert a cart to checkout by providing `cart_id` in the Create Checkout request. The cart contents (`line_items`, `context`, `buyer`) initialize the checkout session.

```json
{
  "cart_id": "cart_abc123",
  "line_items": []
}
```

Business MUST use cart contents and MUST ignore overlapping fields in checkout payload. The `cart_id` parameter is only available when the cart capability is advertised in the business profile.

**Idempotent conversion:**

If an incomplete checkout already exists for the given `cart_id`, the business MUST return the existing checkout session rather than creating a new one. This ensures a single active checkout per cart and prevents conflicting sessions.

**Cart lifecycle after conversion:**

When checkout is initialized via `cart_id`, the cart and checkout sessions SHOULD be linked for the duration of the checkout.

- **During active checkout** — Business SHOULD maintain the cart and reflect relevant checkout modifications (quantity changes, item removals) back to the cart. This supports back-to-storefront flows when buyers transition between checkout and storefront.
- **After checkout completion** — Business MAY clear the cart based on TTL, completion of the checkout, or other business logic. Subsequent operations on a cleared cart ID return `NOT_FOUND`; the platform can start a new session with `create_cart`.

## Guidelines

### Platform

- **MAY** use carts for pre-purchase exploration and session persistence.
- **SHOULD** convert cart to checkout when user expresses purchase intent.
- **MAY** display `continue_url` for handoff to business UI.
- **SHOULD** handle `NOT_FOUND` gracefully when cart expires or is canceled.

### Business

- **SHOULD** provide `continue_url` for cart handoff and session recovery.
- TODO: discuss `continue_url` destination - cart vs checkout.
- **SHOULD** provide estimated totals when calculable.
- **MAY** omit fulfillment totals until checkout when address is unknown.
- **SHOULD** return informational messages for validation warnings.
- **MAY** set cart expiry via `expires_at`.
- **SHOULD** follow [cart lifecycle requirements](#cart-to-checkout-conversion) when checkout is initialized via `cart_id`.

## Cart Schema Definition

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

## Operations

The Cart capability defines the following logical operations.

| Operation       | Description                                    |
| --------------- | ---------------------------------------------- |
| **Create Cart** | Creates a new cart session.                    |
| **Get Cart**    | Retrieves the current state of a cart session. |
| **Update Cart** | Updates a cart session.                        |
| **Cancel Cart** | Cancels a cart session.                        |

### Create Cart

Creates a new cart session with line items and optional buyer/context information for localized pricing estimates.

- [REST Binding](https://ucp.dev/draft/specification/cart-rest/#create-cart)
- [MCP Binding](https://ucp.dev/draft/specification/cart-mcp/#create_cart)

### Get Cart

Retrieves the latest state of a cart session. Returns `NOT_FOUND` if the cart does not exist, has expired, or was canceled.

- [REST Binding](https://ucp.dev/draft/specification/cart-rest/#get-cart)
- [MCP Binding](https://ucp.dev/draft/specification/cart-mcp/#get_cart)

### Update Cart

Performs a full replacement of the cart session. The platform **MUST** send the entire cart resource. The provided resource replaces the existing cart state on the business side.

- [REST Binding](https://ucp.dev/draft/specification/cart-rest/#update-cart)
- [MCP Binding](https://ucp.dev/draft/specification/cart-mcp/#update_cart)

### Cancel Cart

Cancels a cart session. Business MUST return the cart state before deletion. Subsequent operations for this cart ID SHOULD return `NOT_FOUND`.

- [REST Binding](https://ucp.dev/draft/specification/cart-rest/#cancel-cart)
- [MCP Binding](https://ucp.dev/draft/specification/cart-mcp/#cancel_cart)

## Entities

Cart reuses the same entity schemas as [Checkout](https://ucp.dev/draft/specification/checkout/index.md). This ensures consistent data structures when converting a cart to a checkout session.

### Line Item

#### Line Item Create Request

**Error:** Schema 'types/line_item.create' not found in any schema directory.

#### Line Item Update Request

**Error:** Schema 'types/line_item.update' not found in any schema directory.

#### Line Item Response

| Name      | Type                                                   | Required | Description                                            |
| --------- | ------------------------------------------------------ | -------- | ------------------------------------------------------ |
| id        | string                                                 | **Yes**  |                                                        |
| item      | [Item](/draft/specification/checkout/#item)            | **Yes**  |                                                        |
| quantity  | integer                                                | **Yes**  | Quantity of the item being purchased.                  |
| totals    | Array\[[Total](/draft/specification/checkout/#total)\] | **Yes**  | Line item totals breakdown.                            |
| parent_id | string                                                 | No       | Parent line item identifier for any nested structures. |

### Buyer

| Name         | Type   | Required | Description              |
| ------------ | ------ | -------- | ------------------------ |
| first_name   | string | No       | First name of the buyer. |
| last_name    | string | No       | Last name of the buyer.  |
| email        | string | No       | Email of the buyer.      |
| phone_number | string | No       | E.164 standard.          |

### Context

| Name            | Type   | Required | Description                                                                                                                                                                                                                                                                                                                                                                         |
| --------------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| address_country | string | No       | The country. Recommended to be in 2-letter ISO 3166-1 alpha-2 format, for example "US". For backward compatibility, a 3-letter ISO 3166-1 alpha-3 country code such as "SGP" or a full country name such as "Singapore" can also be used. Optional hint for market context (currency, availability, pricing)—higher-resolution data (e.g., shipping address) supersedes this value. |
| address_region  | string | No       | The region in which the locality is, and which is in the country. For example, California or another appropriate first-level Administrative division. Optional hint for progressive localization—higher-resolution data (e.g., shipping address) supersedes this value.                                                                                                             |
| postal_code     | string | No       | The postal code. For example, 94043. Optional hint for regional refinement—higher-resolution data (e.g., shipping address) supersedes this value.                                                                                                                                                                                                                                   |
| intent          | string | No       | Background context describing buyer's intent (e.g., 'looking for a gift under $50', 'need something durable for outdoor use'). Informs relevance, recommendations, and personalization.                                                                                                                                                                                             |

### Total

| Name         | Type    | Required | Description                                                                                                                   |
| ------------ | ------- | -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| type         | string  | **Yes**  | Type of total categorization. **Enum:** `items_discount`, `subtotal`, `discount`, `fulfillment`, `tax`, `fee`, `total`        |
| display_text | string  | No       | Text to display against the amount. Should reflect appropriate method (e.g., 'Shipping', 'Delivery').                         |
| amount       | integer | **Yes**  | If type == total, sums subtotal - discount + fulfillment + tax + fee. Should be >= 0. Amount in minor (cents) currency units. |

Taxes MAY be included where calculable. Platforms SHOULD assume cart totals are estimates; accurate taxes are computed at checkout.

### Message

This object MUST be one of the following types: [Message Error](/draft/specification/checkout/#message-error), [Message Warning](/draft/specification/checkout/#message-warning), [Message Info](/draft/specification/checkout/#message-info).

#### Message Error

| Name         | Type   | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------ | ------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = error**. Message type discriminator.                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| code         | string | **Yes**  | Error code. Possible values include: missing, invalid, out_of_stock, payment_declined, requires_sign_in, requires_3ds, requires_identity_linking. Freeform codes also allowed.                                                                                                                                                                                                                                                                                                                                 |
| path         | string | No       | RFC 9535 JSONPath to the component the message refers to (e.g., $.items[1]).                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| content      | string | **Yes**  | Human-readable message.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| severity     | string | **Yes**  | Declares who resolves this error. 'recoverable': agent can fix via API. 'requires_buyer_input': merchant requires information their API doesn't support collecting programmatically (checkout incomplete). 'requires_buyer_review': buyer must authorize before order placement due to policy, regulatory, or entitlement rules (checkout complete). Errors with 'requires\_*' severity contribute to 'status: requires_escalation'.* *Enum:*\* `recoverable`, `requires_buyer_input`, `requires_buyer_review` |

#### Message Info

| Name         | Type   | Required | Description                                                    |
| ------------ | ------ | -------- | -------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = info**. Message type discriminator.               |
| path         | string | No       | RFC 9535 JSONPath to the component the message refers to.      |
| code         | string | No       | Info code for programmatic handling.                           |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown` |
| content      | string | **Yes**  | Human-readable message.                                        |

#### Message Warning

| Name         | Type   | Required | Description                                                                                                                           |
| ------------ | ------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = warning**. Message type discriminator.                                                                                   |
| path         | string | No       | JSONPath (RFC 9535) to related field (e.g., $.line_items[0]).                                                                         |
| code         | string | **Yes**  | Warning code. Machine-readable identifier for the warning type (e.g., final_sale, prop65, fulfillment_changed, age_restricted, etc.). |
| content      | string | **Yes**  | Human-readable warning message that MUST be displayed.                                                                                |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                        |

### Link

| Name  | Type   | Required | Description                                                                                                                                                                                                                          |
| ----- | ------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| type  | string | **Yes**  | Type of link. Well-known values: `privacy_policy`, `terms_of_service`, `refund_policy`, `shipping_policy`, `faq`. Consumers SHOULD handle unknown values gracefully by displaying them using the `title` field or omitting the link. |
| url   | string | **Yes**  | The actual URL pointing to the content to be displayed.                                                                                                                                                                              |
| title | string | No       | Optional display text for the link. When provided, use this instead of generating from type.                                                                                                                                         |
