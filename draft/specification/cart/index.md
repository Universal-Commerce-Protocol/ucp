# Cart Capability

- **Capability Name:** `dev.ucp.shopping.cart`

## Overview

The Cart capability enables basket building without the complexity of checkout. While [Checkout](http://ucp.dev/draft/specification/checkout/index.md) manages payment handlers, status lifecycle, and order finalization, cart provides a lightweight CRUD interface for item collection before purchase intent is established.

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
- **After checkout completion** — Business MAY clear the cart based on TTL, completion of the checkout, or other business logic. Subsequent operations on a cleared cart ID return `not_found`; the platform can start a new session with `create_cart`.

## Actions

The cart surfaces outstanding Action instances in its response-only `actions` map, defined in [Overview — Actions](http://ucp.dev/draft/specification/overview/#actions).

The cart has no status lifecycle. Each Action gates only the cart effect specified for its Action type. The Business **MUST NOT** treat an outstanding Action as a reason to reject an unrelated cart operation. The Platform **MAY** continue to add, remove, and update items while an Action is outstanding.

After processing an Action, the Platform **SHOULD** use [Get Cart](#get-cart) or a subsequent update response to obtain the latest Cart.

## Scopes

The Cart capability defines the following well-known scopes for user-authenticated access:

| Scope                          | Description                                                                              |
| ------------------------------ | ---------------------------------------------------------------------------------------- |
| `dev.ucp.shopping.cart:manage` | All cart operations on behalf of the authenticated user — create, read, update, persist. |

Scope declaration, derivation, and rules for extending this set with custom scopes are defined in [Identity Linking — Scopes](http://ucp.dev/draft/specification/identity-linking/#scopes).

## Guidelines

### Platform

- **MAY** use carts for pre-purchase exploration and session persistence.
- **SHOULD** convert cart to checkout when user expresses purchase intent.
- **MAY** display `continue_url` for handoff to business UI.
- **SHOULD** handle `not_found` gracefully when cart expires or is canceled.

### Business

- **SHOULD** provide `continue_url` for cart handoff and session recovery.
- TODO: discuss `continue_url` destination - cart vs checkout.
- **SHOULD** provide estimated totals when calculable.
- **MAY** omit fulfillment totals until checkout when address is unknown.
- **SHOULD** return informational messages for validation warnings.
- **MAY** set cart expiry via `expires_at`.
- **SHOULD** follow [cart lifecycle requirements](#cart-to-checkout-conversion) when checkout is initialized via `cart_id`.

## Cart Schema Definition

| Name         | Type                                                                     | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ------------------------------------------------------------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | any                                                                      | **Required** | UCP metadata for cart responses. No payment handlers needed pre-checkout.                                                                                                                                                                                                                                                                                                                               |
| id           | string                                                                   | **Required** | Unique cart identifier.                                                                                                                                                                                                                                                                                                                                                                                 |
| line_items   | Array\[[Line Item Response](/draft/specification/reference/#line-item)\] | **Required** | Cart line items. Same structure as checkout. Full replacement on update.                                                                                                                                                                                                                                                                                                                                |
| context      | [Context](/draft/specification/reference/#context)                       | Optional     | Buyer signals for localization (country, region, postal_code). Merchant uses for pricing, availability, currency. Falls back to geo-IP if omitted.                                                                                                                                                                                                                                                      |
| signals      | [Signals](/draft/specification/reference/#signals)                       | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace. |
| attribution  | [Attribution](/draft/specification/reference/#attribution)               | Optional     | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                        |
| buyer        | [Buyer](/draft/specification/reference/#buyer)                           | Optional     | Optional buyer information for personalized estimates.                                                                                                                                                                                                                                                                                                                                                  |
| currency     | string                                                                   | **Required** | ISO 4217 currency code. Determined by merchant based on context or geo-IP.                                                                                                                                                                                                                                                                                                                              |
| totals       | [Totals](/draft/specification/reference/#totals)                         | **Required** | Estimated cost breakdown. May be partial if shipping/tax not yet calculable.                                                                                                                                                                                                                                                                                                                            |
| actions      | [Actions](/draft/specification/reference/#actions)                       | Optional     | Outstanding extension-defined Actions for this cart.                                                                                                                                                                                                                                                                                                                                                    |
| messages     | Array\[[Message](/draft/specification/reference/#message)\]              | Optional     | Validation messages, warnings, or informational notices.                                                                                                                                                                                                                                                                                                                                                |
| links        | Array\[[Link](/draft/specification/reference/#link)\]                    | Optional     | Optional merchant links (policies, FAQs).                                                                                                                                                                                                                                                                                                                                                               |
| continue_url | string                                                                   | Optional     | URL for cart handoff and session recovery. Enables sharing and human-in-the-loop flows.                                                                                                                                                                                                                                                                                                                 |
| expires_at   | string                                                                   | Optional     | Cart expiry timestamp (RFC 3339). Optional.                                                                                                                                                                                                                                                                                                                                                             |

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

When **all** requested items are unavailable, the business MAY return an error response instead of creating a cart resource. `ucp.status` is the primary discriminator; the absence of `id` is a consistent secondary indicator:

```json
{
  "ucp": { "version": "draft", "status": "error" },
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

- [REST Binding](http://ucp.dev/draft/specification/cart-rest/#create-cart)
- [MCP Binding](http://ucp.dev/draft/specification/cart-mcp/#create_cart)

### Get Cart

Retrieves the latest state of a cart session. Returns `not_found` if the cart does not exist, has expired, or was canceled.

- [REST Binding](http://ucp.dev/draft/specification/cart-rest/#get-cart)
- [MCP Binding](http://ucp.dev/draft/specification/cart-mcp/#get_cart)

### Update Cart

Performs a full replacement of the cart session. The platform **MUST** send the entire cart resource. The provided resource replaces the existing cart state on the business side.

- [REST Binding](http://ucp.dev/draft/specification/cart-rest/#update-cart)
- [MCP Binding](http://ucp.dev/draft/specification/cart-mcp/#update_cart)

### Cancel Cart

Cancels a cart session. Business MUST return the cart state before deletion. Subsequent operations for this cart ID SHOULD return `not_found`.

- [REST Binding](http://ucp.dev/draft/specification/cart-rest/#cancel-cart)
- [MCP Binding](http://ucp.dev/draft/specification/cart-mcp/#cancel_cart)

## Entities

Cart reuses the same entity schemas as [Checkout](http://ucp.dev/draft/specification/checkout/index.md). This ensures consistent data structures when converting a cart to a checkout session.

### UCP Response Cart

UCP metadata for cart responses. No payment handlers needed pre-checkout.

| Name             | Type   | Requirement  | Description                                                                 |
| ---------------- | ------ | ------------ | --------------------------------------------------------------------------- |
| version          | string | **Required** | UCP version in YYYY-MM-DD format.                                           |
| status           | string | Optional     | Application-level status of the UCP operation. **Enum:** `success`, `error` |
| services         | object | Optional     | Service registry keyed by reverse-domain name.                              |
| capabilities     | object | Optional     | Capability registry keyed by reverse-domain name.                           |
| payment_handlers | object | Optional     | Payment handler registry keyed by reverse-domain name.                      |
| capabilities     | any    | Optional     |                                                                             |

### Line Item

#### Line Item Create Request

| Name     | Type                                         | Requirement  | Description                           |
| -------- | -------------------------------------------- | ------------ | ------------------------------------- |
| item     | [Item](/draft/specification/reference/#item) | **Required** |                                       |
| quantity | integer                                      | **Required** | Quantity of the item being purchased. |

#### Line Item Update Request

| Name      | Type                                         | Requirement  | Description                                            |
| --------- | -------------------------------------------- | ------------ | ------------------------------------------------------ |
| id        | string                                       | Optional     |                                                        |
| item      | [Item](/draft/specification/reference/#item) | **Required** |                                                        |
| quantity  | integer                                      | **Required** | Quantity of the item being purchased.                  |
| parent_id | string                                       | Optional     | Parent line item identifier for any nested structures. |

#### Line Item

| Name      | Type                                                    | Requirement  | Description                                            |
| --------- | ------------------------------------------------------- | ------------ | ------------------------------------------------------ |
| id        | string                                                  | **Required** |                                                        |
| item      | [Item](/draft/specification/reference/#item)            | **Required** |                                                        |
| quantity  | integer                                                 | **Required** | Quantity of the item being purchased.                  |
| totals    | Array\[[Total](/draft/specification/reference/#total)\] | **Required** | Line item totals breakdown.                            |
| parent_id | string                                                  | Optional     | Parent line item identifier for any nested structures. |

#### Item

| Name      | Type                                             | Requirement  | Description                                                                                                                                                                 |
| --------- | ------------------------------------------------ | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id        | string                                           | **Required** | The product identifier, often the SKU, required to resolve the product details associated with this line item. Should be recognized by both the Platform, and the Business. |
| title     | string                                           | **Required** | Product title.                                                                                                                                                              |
| price     | [Amount](/draft/specification/reference/#amount) | **Required** | Unit price in ISO 4217 minor units.                                                                                                                                         |
| image_url | string                                           | Optional     | Product image URI.                                                                                                                                                          |

### Buyer

| Name         | Type   | Requirement | Description              |
| ------------ | ------ | ----------- | ------------------------ |
| first_name   | string | Optional    | First name of the buyer. |
| last_name    | string | Optional    | Last name of the buyer.  |
| email        | string | Optional    | Email of the buyer.      |
| phone_number | string | Optional    | E.164 standard.          |

### Context

| Name            | Type                                                                                | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --------------- | ----------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| address_country | string                                                                              | Optional    | The country, as a 2-letter ISO 3166-1 alpha-2 code (e.g. "US"). A 3-letter alpha-3 code or full country name MAY also be used.                                                                                                                                                                                                                                                                                                                                     |
| address_region  | string                                                                              | Optional    | The first-level administrative region within the country (e.g. a state or province such as California).                                                                                                                                                                                                                                                                                                                                                            |
| postal_code     | string                                                                              | Optional    | The postal code (e.g. "94043").                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| intent          | string                                                                              | Optional    | Background context describing buyer's intent (e.g., 'looking for a gift under $50', 'need something durable for outdoor use'). Informs relevance, recommendations, and personalization.                                                                                                                                                                                                                                                                            |
| language        | string                                                                              | Optional    | Preferred language for content. Use IETF BCP 47 language tags (e.g., 'en', 'fr-CA', 'zh-Hans'). For REST, equivalent to Accept-Language header—platforms SHOULD fall back to Accept-Language when this field is absent; when provided, overrides Accept-Language. Businesses MAY return content in a different language if unavailable.                                                                                                                            |
| currency        | string                                                                              | Optional    | Preferred currency (ISO 4217, e.g., 'EUR', 'USD'). Businesses determine presentment currency from context and authoritative signals; this hint MAY inform selection in multi-currency markets. Also serves as the denomination for price filter values — platforms SHOULD include this field when sending price filters. Response prices include explicit currency confirming the resolution.                                                                      |
| eligibility     | Array\[[Reverse Domain Name](/draft/specification/reference/#reverse-domain-name)\] | Optional    | Buyer claims about eligible benefits such as loyalty membership, payment instrument perks, and similar. Recognized claims MAY inform the Business response (e.g., member-only product availability, adjusted pricing in catalog, provisional discounts at cart or checkout). Businesses MUST ignore unrecognized values without error. Values MUST use reverse-domain naming (e.g., 'com.example.loyalty_gold', 'org.school.student') and MUST be non-identifying. |
| payment         | Array[object]                                                                       | Optional    | Buyer-preferred payment handlers in priority order (most preferred first). Each entry names a handler advertised in the Business profile's `ucp.payment_handlers`, optionally narrowed to preferred instrument types. The Business SHOULD use it to preselect or prioritize the handler (and type, when given) and MAY ignore unavailable or ineligible entries; unrecognized values MUST be ignored without error.                                                |

### Signals

Environment data provided by the platform to support authorization and abuse prevention. Signal values MUST NOT be buyer-asserted claims. See [Signals](http://ucp.dev/draft/specification/overview/#signals) for details and privacy requirements.

| Name               | Type   | Requirement | Description                                    |
| ------------------ | ------ | ----------- | ---------------------------------------------- |
| dev.ucp.buyer_ip   | string | Optional    | Client's IP address (IPv4 or IPv6).            |
| dev.ucp.user_agent | string | Optional    | Client's HTTP User-Agent header or equivalent. |

### Attribution

Platform-provided referral and conversion-event context — campaign IDs, click identifiers, and source/medium markers communicated by the platform. See [Attribution](http://ucp.dev/draft/specification/overview/#attribution) for details and consent requirements.

Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.

### Total

The same totals contract applies to cart and checkout. See [Checkout Totals](http://ucp.dev/draft/specification/checkout/#totals) for the rendering contract, accounting identity, well-known types, repeating types, and sub-line semantics.

| Name         | Type                                                           | Requirement  | Description                                                                                                                                                                                                                                                                                 |
| ------------ | -------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                         | **Required** | Cost category. Well-known values: subtotal, items_discount, discount, fulfillment, tax, fee, total. Businesses MAY use additional values.                                                                                                                                                   |
| display_text | string                                                         | Optional     | Text to display against the amount. Should reflect appropriate method (e.g., 'Shipping', 'Delivery').                                                                                                                                                                                       |
| amount       | [Signed Amount](/draft/specification/reference/#signed-amount) | **Required** | Monetary amount in the currency's minor unit as defined by ISO 4217. Refer to the currency's exponent to determine minor-to-major ratio (e.g., 2 for USD, 0 for JPY, 3 for KWD). May be negative — the sign is intrinsic to the value (e.g., discounts are negative, charges are positive). |

Taxes MAY be included where calculable. Platforms SHOULD assume cart totals are estimates; accurate taxes are computed at checkout.

### Message

See [Message](/draft/specification/reference/#message) in the [Schema Reference](/draft/specification/reference/) for the canonical field definition.

#### Message Error

See [Message Error](/draft/specification/reference/#message-error) in the [Schema Reference](/draft/specification/reference/) for the canonical field definition.

#### Message Info

See [Message Info](/draft/specification/reference/#message-info) in the [Schema Reference](/draft/specification/reference/) for the canonical field definition.

#### Message Warning

See [Message Warning](/draft/specification/reference/#message-warning) in the [Schema Reference](/draft/specification/reference/) for the canonical field definition.

### Link

See [Link](/draft/specification/reference/#link) in the [Schema Reference](/draft/specification/reference/) for the canonical field definition.
