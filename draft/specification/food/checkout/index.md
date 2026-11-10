# Checkout Capability

Draft - Work in Progress

This capability is in **draft status**. Implementers are cautioned that data models, protocol bindings, and operational flows are under active iteration and may undergo breaking changes as the specification evolves.

- **Capability Name:** `dev.ucp.food.checkout`

## Overview

The Checkout capability allows Platforms to facilitate checkout sessions for prepared food and beverage orders — from restaurants, cafes, bakeries, food trucks, etc.

The Business remains the Merchant of Record (MoR) and the system of record for the menu, the kitchen, and the order. It does not need to become PCI DSS compliant to accept card payments through this capability. Unless the AP2 Mandates extension is supported, the checkout must be finalized manually by the buyer through a trusted UI.

### Flow Overview

Checkout follows a progressive session lifecycle:

1. **Session Initiation**: The Platform creates a checkout session for one `food_establishment` with the dishes and modifications the buyer picked from the menu (or converts an existing cart via `cart_id`).
1. **Progressive Enrichment**: The Platform updates the session with the fulfillment choice (delivery or pickup, ASAP or scheduled), buyer contact details, and a tip. The Business re-prices on every update.
1. **Session Completion**: The Platform submits payment. The Business injects the order into the kitchen and returns an order confirmation with an optional display label and a live tracking link.

```text
        +------------+                         +---------------------+
        | incomplete |<----------------------->| requires_escalation |
        +-----+------+                         |   (buyer handoff    |
              |                                |  via continue_url)  |
              | all info collected             +----------+----------+
              v                                           |
     +------------------+                                 |
     |ready_for_complete|                                 |
     |                  |                                 |
     | (platform can    |                                 | continue_url
     |  call Complete   |                                 |
     |    Checkout)     |                                 |
     +--------+---------+                                 |
              |                                           |
              | Complete Checkout                         |
              v                                           |
    +--------------------+                                |
    |complete_in_progress|  (payment capture /            |
    +---------+----------+   kitchen POS injection)       |
              |                                           |
              +-----------------------+-------------------+
                                      v
                                +-------------+
                                |  completed  |  order.id, order.label,
                                +-------------+  order.tracking_url

                                +-------------+
                                |  canceled   |
                                +-------------+
           (session invalid/expired - can occur from any state)
```

### Anatomy of a Food Order

**Mental model:**

- `food_establishment` 🏪 Luigi's Artisan Pizzeria — every dish below comes from this one kitchen
- `line_items[0]` 🍕 × 2
  - `dish` Margherita Pizza (12") — $16.00
  - `modifications[]` 🧀 Extra Mozzarella +$2.00 · 🌿 Fresh Basil +$1.50
  - `note` 📝 "Well done crust, please"
- `line_items[1]` 🥗 × 1
  - `dish` Caesar Salad — $11.00
  - `note` 📝 "Dressing on the side"
- `fulfillment.methods[0]` 🛵 delivery → 450 Serra Mall, Apt 3B *(via the [Fulfillment Extension](http://ucp.dev/draft/specification/food/extensions/fulfillment/index.md))*
  - `selected_option_id` 🔘✅ Standard Delivery, 6:35–6:50 PM, $2.99
- `tip` 💵 `selected_option_id` 🔘✅ 18% *(via the [Tip Extension](http://ucp.dev/draft/specification/food/extensions/tip/index.md))*
- `totals[]` 🧾 subtotal · delivery · fees · tax · tip · **total**
- `order` 🎫 `#42` → `tracking_url` *(after completion)*

## Key Concepts

- **Single-Establishment Order Scope (`food_establishment`)**: Prepared food is cooked to order and must leave the kitchen within a tight freshness window, so a checkout session is bound to exactly one preparation location. Every `line_items[].dish` **MUST** come from that establishment's active menu.
- **Shared Menu Identifiers (`dish.id`, `modification.id`)**: Dish and modification identifiers come from upper-funnel menu discovery and **MUST** be recognized by both the Platform and the Business. On requests the Platform sends only these opaque identifiers (plus `quantity` and `note`); all other attributes (e.g., `title`, `description`, `price`, etc.) are Business-authored and omitted from requests.
- **Provisional Menu vs. Authoritative Checkout**:
  - *Menu Browsing (Provisional)*: Menus, prices, and estimated prep times shown during discovery are provisional. Kitchens can sell out of dishes mid-service, pause intake when ticket queues back up, and switch between lunch and dinner menus.
  - *Checkout Session (Authoritative)*: Each create or update re-validates the session against live kitchen state — operating hours, item and modifier availability, delivery coverage, and order minimums — and returns authoritative `line_items[].totals` and `totals[]`.

### Dish Customization

Food ordering relies on rich item-level customization — choosing a protein, picking a spice level, upgrading a side, or adding toppings — alongside free-form kitchen requests. The [Line Item](#line-item) entity separates the menu [Dish](#dish) from buyer-selected customization:

| Mechanism                    | Field                                                          | Priced?          | Contract                                                                                                                                                                                                                                  |
| ---------------------------- | -------------------------------------------------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Structured modifications** | `line_items[].modifications[]` ([Modification](#modification)) | Yes ($0 or more) | Platform sends menu-backed modification `id`s. Business validates modifier-group rules (required choices, min/max selections, mutually exclusive options), echoes `title` and `price`, and includes the charges in `line_items[].totals`. |
| **Special instructions**     | `line_items[].note`                                            | No               | Free-form buyer text for the kitchen (e.g., "sauce on the side", "cut in half", "well done crust"). **MUST NOT** alter price or structured modifications.                                                                                 |

- **Modification quantity applies per unit of the dish.** `modification.quantity` specifies how many units of that modification apply to **each** unit of the dish (defaults to 1 when omitted). `line_items[].quantity` multiplies the whole configured dish (base price plus all modifications scaled by their quantity).
- **Platforms MUST NOT convey quantity by repetition.** Repeated units of the same modification **MUST** be expressed as a single entry with `quantity` greater than 1.
- **A configured dish is a line item.** Two units of the same dish with different modifications or different notes are separate `line_items[]` entries; Platforms **MUST NOT** merge them.
- **Line item arithmetic.** A `line_item`'s `subtotal` is `(dish.price + sum(modifications[].price × modifications[].quantity)) × line_items[].quantity` (where omitted `modifications[].quantity` defaults to 1).
- **Free-form kitchen `note` rules:**
  1. `line_items[].note` is passed to the kitchen verbatim and **MUST NOT** alter price or structured `modifications[]`.
  1. A Business **SHOULD** return `note_contains_modification` warning when a note asks for a menu-modeled modifier at any price (including `$0` removal or substitution modifiers such as "no onions"), and **MAY** return `note_not_supported` error when a request cannot be honored by the kitchen (e.g., "pepperoni on half").
  1. A Platform **MUST NOT** present a free-form `note` to the buyer as an applied or verified modification.

The Platform sends identifiers and buyer inputs only:

```json
[
  {
    "quantity": 2,
    "dish": {
      "id": "dish_margherita_12"
    },
    "modifications": [
      { "id": "mod_extra_mozzarella" },
      { "id": "mod_fresh_basil" }
    ],
    "note": "Well done crust, please"
  },
  {
    "quantity": 1,
    "dish": {
      "id": "dish_caesar"
    },
    "note": "Dressing on the side"
  }
]
```

The Business echoes authoritative menu data and prices each configured dish:

```json
[
  {
    "id": "li_1",
    "quantity": 2,
    "dish": {
      "id": "dish_margherita_12",
      "title": "Margherita Pizza (12\")",
      "price": 1600,
      "media": [
        { "type": "image", "url": "https://food.example.com/img/margherita.jpg" }
      ]
    },
    "modifications": [
      { "id": "mod_extra_mozzarella", "title": "Extra Mozzarella", "price": 200 },
      { "id": "mod_fresh_basil", "title": "Fresh Basil", "price": 150 }
    ],
    "note": "Well done crust, please",
    "totals": [
      { "type": "subtotal", "amount": 3900 },
      { "type": "total", "amount": 3900 }
    ]
  },
  {
    "id": "li_2",
    "quantity": 1,
    "dish": {
      "id": "dish_caesar",
      "title": "Caesar Salad",
      "price": 1100
    },
    "note": "Dressing on the side",
    "totals": [
      { "type": "subtotal", "amount": 1100 },
      { "type": "total", "amount": 1100 }
    ]
  }
]
```

When a `line_items[].note` asks for something the menu models as a modification, the Business **SHOULD** return a warning pointing back to the note:

```json
[
  {
    "type": "warning",
    "code": "note_contains_modification",
    "path": "$.line_items[0].note",
    "content": "\"Add avocado\" is a paid add-on (+$2.50). Select the Avocado modification to add it; notes are passed to the kitchen as-is and cannot add charges."
  }
]
```

### Pricing Scope

Checkout uses the shared [Total](#total) structure and follows the rendering contract, verification rule, repeating types, and `lines[]` sub-line invariant defined in [Checkout — Total](http://ucp.dev/draft/specification/shopping/checkout/#totals). Amounts are signed: discounts are negative, charges are non-negative, and all non-total entries sum to the single `total` entry.

- **Line items (`subtotal`, `items_discount`)**: `subtotal` is the sum of `line_items[].totals[type=subtotal]` (dish plus modification prices). Dish-level promotions (e.g., "Free garlic knots with any large pizza") roll up as `items_discount`.
- **Delivery (`fulfillment`)**: The price of the selected [fulfillment option](http://ucp.dev/draft/specification/food/extensions/fulfillment/#fulfillment-option). Pickup options are typically `0`.
- **Fees (`fee`)**: Some common examples include: marketplace service fees, small-order fees (basket below a threshold), bag or packaging fees, and municipal surcharges (e.g., courier minimum-pay regulatory fees). Use repeating `fee` entries or one `fee` entry with itemized `lines[]`.
- **Tax (`tax`)**: Sales tax and prepared-food or beverage taxes, which may differ from grocery rates and may apply to fees and delivery in some jurisdictions.
- **Gratuity (`tip`)**: A **food-defined total type** populated when the [Tip Extension](http://ucp.dev/draft/specification/food/extensions/tip/index.md) is active. Because `tip` is not in the common well-known set, Businesses **MUST** include `display_text` on it.

The following snippets illustrate canonical food pricing patterns:

A $50.00 delivery basket with a $2.99 delivery fee, service and regulatory fees itemized under one `fee` entry, 8.75% tax, and an 18% tip:

```json
[
  { "type": "subtotal", "display_text": "Subtotal", "amount": 5000 },
  { "type": "fulfillment", "display_text": "Standard Delivery", "amount": 299 },
  {
    "type": "fee",
    "display_text": "Service & Regulatory Fees",
    "amount": 550,
    "lines": [
      { "display_text": "Service Fee", "amount": 350 },
      { "display_text": "City Courier Regulatory Fee", "amount": 200 }
    ]
  },
  { "type": "tax", "display_text": "Tax (8.75%)", "amount": 438 },
  { "type": "tip", "display_text": "Courier Tip (18%)", "amount": 900 },
  { "type": "total", "display_text": "Total", "amount": 7187 }
]
```

The same basket picked up at the counter: no delivery fee, no courier fees, and a smaller staff tip:

```json
[
  { "type": "subtotal", "display_text": "Subtotal", "amount": 5000 },
  { "type": "fulfillment", "display_text": "Pickup", "amount": 0 },
  { "type": "tax", "display_text": "Tax (8.75%)", "amount": 438 },
  { "type": "tip", "display_text": "Staff Tip (10%)", "amount": 500 },
  { "type": "total", "display_text": "Total", "amount": 5938 }
]
```

A dish-level promotion (`items_discount`), an order-level promo code (`discount`), and free delivery:

```json
[
  { "type": "subtotal", "display_text": "Subtotal", "amount": 5000 },
  { "type": "items_discount", "display_text": "Free Garlic Knots", "amount": -600 },
  { "type": "discount", "display_text": "Promo WELCOME10", "amount": -440 },
  { "type": "fulfillment", "display_text": "Free Delivery", "amount": 0 },
  { "type": "fee", "display_text": "Service Fee", "amount": 350 },
  { "type": "tax", "display_text": "Tax (8.75%)", "amount": 346 },
  { "type": "tip", "display_text": "Courier Tip (18%)", "amount": 900 },
  { "type": "total", "display_text": "Total", "amount": 5556 }
]
```

Rendered in order, Pattern 1 looks like this:

```text
Subtotal                                                      $50.00
Standard Delivery                                              $2.99
Service & Regulatory Fees                                      $5.50
    Service Fee                                     $3.50
    City Courier Regulatory Fee                     $2.00
Tax (8.75%)                                                    $4.38
Courier Tip (18%)                                              $9.00
────────────────────────────────────────────────────────────────────
Total                                                         $71.87
```

### Payments

Payment handlers are discovered from the Business's UCP profile at `/.well-known/ucp` and `checkout.ucp.payment_handlers`, following the same model as [Checkout — Payments](http://ucp.dev/draft/specification/shopping/checkout/#payments). `payment` is optional on create & update and **REQUIRED** on Complete Checkout.

Because dynamic charges such as delivery fees and tips can change up to the moment of completion, Platforms **MUST** present the final `totals[]` for buyer confirmation before submitting payment.

### Cart-to-Checkout Conversion

The Platform can create a checkout when the Platform and Business share an out-of-band communicated cart identifier that both parties acknowledge (for example, a pre-built basket built on the food establishment's web/app surface).

Conversion follows [Cart — Cart-to-Checkout Conversion](http://ucp.dev/draft/specification/shopping/cart/#cart-to-checkout-conversion): the Business initializes the session from the cart's `food_establishment`, `line_items[]` (dishes, modifications, and notes), `buyer`, and `context`, and **MUST** ignore overlapping fields in the request. The Platform **MAY** omit `food_establishment` and `line_items` (or send `"line_items": []`) when providing `cart_id`. Checkout-only and extension fields — such as `fulfillment`, `tip`, and `payment` — **MAY** be sent alongside `cart_id`. The Business **MUST** reject requests containing `cart_id` if an out-of-band cart source is not recognized, and **MUST NOT** silently fall back to inline `line_items`. `cart_id` is an initialization input only and is omitted from checkout responses.

```json
{
  "cart_id": "cart_food_8912"
}
```

### Checkout Status Lifecycle

The `status` field indicates the current phase of the session. Statuses follow [Checkout — Status Values](http://ucp.dev/draft/specification/shopping/checkout/#status-values); in food ordering they typically mean:

| Status                 | Typical food ordering situation                                                                                                                                                                   | Recommended Platform action                                     |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `incomplete`           | No fulfillment method yet, a dish was 86'd, or the basket is under the delivery minimum.                                                                                                          | Resolve `messages[]` via Update Checkout.                       |
| `requires_escalation`  | Alcohol in the basket requires ID verification, or a catering order needs business review.                                                                                                        | Hand off via `continue_url`.                                    |
| `ready_for_complete`   | Dishes, buyer contact, and any active extension's inputs (e.g., fulfillment, tip) are valid, and no gating Action remains outstanding.                                                            | Show the final summary and disclosures; call Complete Checkout. |
| `complete_in_progress` | Payment capture or kitchen POS injection is still running. See [Accepted Completion](http://ucp.dev/draft/specification/shopping/checkout/#accepted-completion). `order` **MUST NOT** be present. | Process any outstanding Action, then poll Get Checkout.         |
| `completed`            | The kitchen has the ticket. `order` is present.                                                                                                                                                   | Show confirmation screen.                                       |
| `canceled`             | Canceled by the Platform or expired (default TTL: 6 hours).                                                                                                                                       | Start a new session if needed.                                  |

#### Actions

When an active extension has outstanding step-up work for the checkout (such as 3D Secure device data collection or a buyer authentication challenge), the Business surfaces instances in the response-only `actions` map. Food Checkout adopts the [Overview — Actions](http://ucp.dev/draft/specification/overview/#actions) model and follows the lifecycle, message-targeting, and [Accepted Completion](http://ucp.dev/draft/specification/shopping/checkout/#accepted-completion) contracts defined in [Shopping Checkout — Actions](http://ucp.dev/draft/specification/shopping/checkout/#actions).

### Error Handling

Checkout uses the shared `messages[]` model, severities, and [`path`](http://ucp.dev/draft/specification/shopping/checkout/#the-path-field) targeting defined in [Checkout — Error Handling](http://ucp.dev/draft/specification/shopping/checkout/#error-handling), including [eligibility verification at completion](http://ucp.dev/draft/specification/shopping/checkout/#eligibility-verification-at-completion).

Kitchen state changes by the minute, so food checkouts surface recoverable errors far more often than retail. In addition to the shared [standard errors](http://ucp.dev/draft/specification/shopping/checkout/#standard-errors), food Businesses **SHOULD** use these codes so Platforms can offer targeted recovery:

| Code                           | Typical `path`                                               | Food ordering meaning                                                         | Suggested recovery                                     |
| ------------------------------ | ------------------------------------------------------------ | ----------------------------------------------------------------------------- | ------------------------------------------------------ |
| `out_of_stock`                 | `$.line_items[1].dish` or `$.line_items[1].modifications[0]` | Dish or ingredient 86'd for this service.                                     | Offer a substitute or remove.                          |
| `item_unavailable`             | `$.line_items[1].dish`                                       | Dish not on the current menu (e.g., breakfast-only).                          | Remove or schedule for a later time.                   |
| `modification_required`        | `$.line_items[0]`                                            | Required modifier group (e.g., protein or size) is missing a selection.       | Prompt the buyer to choose a required modification.    |
| `modification_invalid`         | `$.line_items[0].modifications[1]`                           | Modification is not valid for the dish or violates group min/max rules.       | Adjust or remove the invalid modification.             |
| `note_not_supported`           | `$.line_items[0].note`                                       | Kitchen request in `note` cannot be honored (e.g., half-topping not offered). | Edit or remove the note, or offer an alternative.      |
| `location_closed`              | `$.food_establishment`                                       | Establishment closed or paused for intake.                                    | Offer scheduled ordering or another location.          |
| `fulfillment_time_unavailable` | `$.fulfillment.methods[0].requested_fulfillment_time`        | Requested scheduled time is outside operating hours or slot capacity.         | Propose one of the alternative windows in `options[]`. |
| `address_undeliverable`        | `$.fulfillment.methods[0].destination`                       | Address outside the delivery zone.                                            | Offer pickup or a different address.                   |
| `minimum_order_unmet`          | `$.totals`                                                   | Basket below the delivery minimum.                                            | Prompt to add items.                                   |
| `payment_failed`               | `$.payment`                                                  | Authorization or capture failed.                                              | Prompt for another payment method.                     |
| `eligibility_invalid`          | `$.context.eligibility`                                      | Delivery pass or membership could not be verified.                            | Show recomputed totals for review.                     |

Sample definitions based on the error examples above:

```json
[
  {
    "type": "error",
    "code": "out_of_stock",
    "path": "$.line_items[1].dish",
    "content": "Truffle Arancini is sold out for tonight's dinner service.",
    "severity": "recoverable"
  },
  {
    "type": "error",
    "code": "minimum_order_unmet",
    "path": "$.totals",
    "content": "Delivery orders require a $15.00 minimum. Add $3.00 more to continue.",
    "severity": "recoverable"
  }
]
```

```json
[
  {
    "type": "error",
    "code": "location_closed",
    "path": "$.food_establishment",
    "content": "Luigi's is not accepting ASAP orders right now due to high volume. Scheduled orders from 7:30 PM are available.",
    "severity": "recoverable"
  }
]
```

```json
[
  {
    "type": "error",
    "code": "age_verification_required",
    "path": "$.line_items[2]",
    "content": "Orders containing alcohol require ID verification before checkout.",
    "severity": "requires_buyer_input"
  }
]
```

Platforms turn these messages into recovery prompts, for example:

> 🤖 Truffle Arancini just sold out for tonight. Want something else, or should I remove it? Either way you're $3.00 short of the $15 delivery minimum.

### Warning Presentation

Checkout follows the `notice` vs. `disclosure` presentation contract in [Checkout — Warning Presentation](http://ucp.dev/draft/specification/shopping/checkout/#warning-presentation). In food ordering, `disclosure` is the right tier for **statutory food-safety and labeling notices**, which Platforms **MUST** show prominently near the referenced item and **MUST NOT** auto-dismiss:

- **Consumer advisory** (`consumer_advisory`): Raw or undercooked animal products, as required by food codes such as the U.S. FDA.
- **Allergens** (`allergens`): Major allergens or shared-equipment cross-contact.
- **Nutrition** (`nutritional_info`): Calorie or sodium statements required by menu-labeling laws.
- **Price changes** (`totals_changed`): A menu or fee change re-priced the order after the buyer reviewed it. The Business **MUST** return the recomputed `totals[]` along with a `totals_changed` disclosure warning at `$.totals`, and **MUST NOT** complete a checkout at a modified price without first returning the updated totals for buyer review.

Use `notice` for operational context (e.g., "High demand — delivery times are longer than usual").

```json
[
  {
    "type": "warning",
    "code": "consumer_advisory",
    "path": "$.line_items[0]",
    "presentation": "disclosure",
    "content": "**Consumer Advisory**: Consuming raw or undercooked meats, poultry, seafood, shellfish, or eggs may increase your risk of foodborne illness.",
    "content_type": "markdown"
  },
  {
    "type": "warning",
    "code": "allergens",
    "path": "$.line_items[1]",
    "presentation": "disclosure",
    "content": "Prepared in a kitchen that handles peanuts, tree nuts, sesame, and wheat.",
    "url": "https://food.example.com/allergens"
  },
  {
    "type": "warning",
    "code": "high_demand",
    "presentation": "notice",
    "content": "High demand — delivery times are about 15 minutes longer than usual."
  }
]
```

```text
1 × Steak Tartare                                           $18.00
┌────────────────────────────────────────────────────────────────┐
│ ⚠ Consumer Advisory: Consuming raw or undercooked meats,       │
│   poultry, seafood, shellfish, or eggs may increase your risk  │
│   of foodborne illness.                                        │
└────────────────────────────────────────────────────────────────┘
1 × Pad Thai                                                $15.00
┌────────────────────────────────────────────────────────────────┐
│ ⚠ Prepared in a kitchen that handles peanuts, tree nuts,       │
│   sesame, and wheat.                          Allergen info ›  │
└────────────────────────────────────────────────────────────────┘
ℹ High demand — delivery times are about 15 minutes longer than usual.
```

### Order Confirmation & Tracking

On `completed`, the Business returns an [Order Confirmation](#order-confirmation) in `order`. Its design reflects how food orders are handed off:

- **`order.id`** (required): The Business's canonical order identifier.
- **`order.label`** (optional, Business-only): A short, human-readable callout that buyers and couriers use at the counter, shelf, or locker (e.g., `#42`, `B12`). It exists because order IDs may be too long to shout across a kitchen.
- **`order.tracking_url`** (required): A live page showing preparation status, ready or arrival time, and courier location. Unlike retail, where a receipt link suffices, food orders are tracked minute by minute until handoff.
- **`order.earliest_fulfillment_time` / `order.latest_fulfillment_time`** (optional, Business-only): The committed post-placement ready or arrival window (RFC 3339), allowing the Platform to render an immediate ETA on the confirmation screen without scraping `tracking_url`.

```json
{
  "id": "ord_food_9876543210",
  "label": "#42",
  "tracking_url": "https://food.example.com/orders/ord_food_9876543210",
  "earliest_fulfillment_time": "2026-04-10T18:35:00-07:00",
  "latest_fulfillment_time": "2026-04-10T18:50:00-07:00"
}
```

## Scopes

The Checkout capability defines the following well-known scopes for user-authenticated access:

| Scope                          | Description                                                                                                  |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `dev.ucp.food.checkout:manage` | All checkout operations on behalf of the authenticated user — create, update, complete, and cancel checkout. |

Scope declaration, derivation, and rules for extending this set with custom scopes are defined in [Identity Linking — Scopes](http://ucp.dev/draft/specification/common/identity-linking/#scopes).

## Continue URL

The `continue_url` field enables checkout handoff from the Platform to the Business UI — for example, for ID verification or catering approval. URL construction (server-side state vs. permalink) and security/recovery considerations follow [Checkout — Continue URL](http://ucp.dev/draft/specification/shopping/checkout/#continue-url).

### Availability

Businesses **MUST** provide `continue_url` when returning `status` = `requires_escalation`. For all other non-terminal statuses (`incomplete`, `ready_for_complete`, `complete_in_progress`), Businesses **SHOULD** provide `continue_url`. For terminal states (`completed`, `canceled`), `continue_url` **SHOULD** be omitted.

## Guidelines

### Platform

- **MUST** supply a valid `food_establishment.id` and `line_items[].dish.id` (and `modifications[].id` where customized) sourced from menu discovery, unless converting a cart via `cart_id`.
- **MUST** present each `line_items[]` entry as a unit — `dish.title`, every modification `title`, `quantity` (when greater than 1), and `price`, `line_items[].note`, and the line's `totals` — and **MUST NOT** merge entries that differ in modifications or notes.
- **MUST** keep kitchen instructions in `line_items[].note` and courier instructions in `fulfillment.methods[].notes`.
- **SHOULD** collect `buyer.phone_number` (E.164) for delivery orders so the courier or kitchen can reach the buyer.
- **MUST** render `presentation: "disclosure"` warnings (consumer advisories, allergens, `totals_changed`) prominently and **MUST NOT** auto-dismiss them.
- **MUST** surface `order.tracking_url`, and `order.label` when present, after completion.
- **MUST** use `continue_url` when status is `requires_escalation`, and **MAY** use it to hand off in other situations.

### Business

- **MUST** validate `food_establishment.id`, dish IDs, and modification IDs against live operating hours, item and ingredient availability, and modifier-group rules on every create and update operation.
- **MUST** echo authoritative `title` and `price` for every dish and modification, and compute `line_items[].totals` and `totals[]` deterministically.
- **MUST NOT** infer a quantity from a repeated modification `id` within a single line item, and **SHOULD** reject duplicate modification IDs as invalid.
- **MUST NOT** add charges based on `line_items[].note`; **SHOULD** return a warning message when a note requests a menu-modeled modification.
- **SHOULD** use the food error codes in [Error Handling](#error-handling) with a precise `path`.
- **MUST** return `order.id` and `order.tracking_url` on `completed`, and **SHOULD** return `order.label` whenever buyers or couriers collect at a counter, shelf, or locker.
- **MUST** send an order confirmation when a valid `buyer.email` is available.
- **MUST** provide `continue_url` and at least one message with `severity` of `requires_buyer_input` or `requires_buyer_review` when returning `requires_escalation`.
- After a checkout session reaches `completed`, it is considered immutable.

## Capability Schema Definition

| Name               | Type                                                                                         | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------------ | -------------------------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp                | [UCP Checkout Response Schema](/draft/specification/reference/#ucp-response-checkout-schema) | **Required** | UCP metadata for checkout responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| id                 | string                                                                                       | **Required** | Unique identifier of the checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| food_establishment | [Location Summary Response](/draft/specification/reference/#location-summary)                | **Required** | Food establishment location the checkout is associated with. In create requests, required when initializing with inline `line_items` and optional when initializing via `cart_id`. Required in update requests and checkout responses.                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| line_items         | Array\[[Line Item Response](/draft/specification/food/checkout/#line-item)\]                 | **Required** | List of dishes being checked out. In create requests, the Platform MUST include `line_items` (with `food_establishment`) or `cart_id`, and MAY include both. The Platform MUST include `line_items` in update requests and omits it from complete requests. The Business MUST include `line_items` in checkout responses.                                                                                                                                                                                                                                                                                                                                               |
| buyer              | [Buyer](/draft/specification/food/checkout/#buyer)                                           | Optional     | Representation of the buyer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| context            | [Context](/draft/specification/reference/#context)                                           | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals            | [Signals](/draft/specification/reference/#signals)                                           | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| status             | string                                                                                       | **Required** | Checkout state indicating the current phase and required action. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                         |
| currency           | string                                                                                       | **Required** | ISO 4217 currency code reflecting the business's market determination. Derived from address, context, and geo IP—buyers provide signals, business determines currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| totals             | [Totals](/draft/specification/reference/#totals)                                             | **Required** | Different checkout totals.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| actions            | [Actions](/draft/specification/reference/#actions)                                           | Optional     | Outstanding extension-defined Actions for this checkout.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| messages           | Array\[[Message](/draft/specification/reference/#message)\]                                  | Optional     | List of messages with error and info about the checkout session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| links              | Array\[[Link](/draft/specification/reference/#link)\]                                        | **Required** | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies           | Array\[[Policy](/draft/specification/reference/#policy)\]                                    | Optional     | Policies (e.g., cancellation/refund terms) that apply to the items in this checkout. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| expires_at         | string                                                                                       | Optional     | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| continue_url       | string                                                                                       | Optional     | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| payment            | [Payment](/draft/specification/reference/#payment)                                           | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| order              | [Order Confirmation](/draft/specification/food/checkout/#order-confirmation)                 | Optional     | Details about an order created for this checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

## Operations

The Checkout capability defines the following logical operations:

| Operation             | Description                                                                                   |
| --------------------- | --------------------------------------------------------------------------------------------- |
| **Create Checkout**   | Initiates a new food checkout session. Called as soon as the buyer expresses intent to order. |
| **Get Checkout**      | Retrieves the current state of a checkout session.                                            |
| **Update Checkout**   | Updates a checkout session via full resource replacement.                                     |
| **Complete Checkout** | Submits payment and places the order with the kitchen.                                        |
| **Cancel Checkout**   | Cancels a checkout session.                                                                   |

### Create Checkout

Invoked when the buyer expresses intent to order from a food establishment.

The create request initializes the checkout from one of two sources: `food_establishment` and `line_items` provided inline, or the contents of a cart identified by `cart_id` — e.g., an out-of-band communicated cart that both the Platform and Business acknowledge (see [Cart-to-Checkout Conversion](#cart-to-checkout-conversion) and [Shopping Checkout — Create Checkout](http://ucp.dev/draft/specification/shopping/checkout/#create-checkout)). The Business **MUST** reject a create request that provides `cart_id` when out-of-band cart resolution is not supported (or when `cart_id` cannot be resolved), and **MUST NOT** ignore `cart_id` and initialize the checkout from inline `line_items` instead. The Business **MUST** also reject a create request that provides neither inline items nor `cart_id`.

**Inputs**

| Name               | Type                                                                 | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------------ | -------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| food_establishment | [Location Summary](/draft/specification/reference/#location-summary) | Optional    | Food establishment location the checkout is associated with. In create requests, required when initializing with inline `line_items` and optional when initializing via `cart_id`. Required in update requests and checkout responses.                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| line_items         | Array\[[Line Item](/draft/specification/food/checkout/#line-item)\]  | Optional    | List of dishes being checked out. In create requests, the Platform MUST include `line_items` (with `food_establishment`) or `cart_id`, and MAY include both. The Platform MUST include `line_items` in update requests and omits it from complete requests. The Business MUST include `line_items` in checkout responses.                                                                                                                                                                                                                                                                                                                                               |
| cart_id            | string                                                               | Optional    | Cart ID for checkout initialization, referencing an out-of-band cart mutually recognized by the Platform and Business. The Business MUST reject requests with an unsupported or unrecognized `cart_id`. Cart contents (`food_establishment`, `line_items`, `context`, `buyer`) take precedence over overlapping checkout fields; `food_establishment` and `line_items` may be omitted or empty.                                                                                                                                                                                                                                                                         |
| buyer              | [Buyer](/draft/specification/food/checkout/#buyer)                   | Optional    | Representation of the buyer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| context            | [Context](/draft/specification/reference/#context)                   | Optional    | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals            | [Signals](/draft/specification/reference/#signals)                   | Optional    | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| payment            | [Payment](/draft/specification/reference/#payment)                   | Optional    | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

**Output**

This object MUST be one of the following types: [Checkout](/draft/specification/food/checkout/#checkout), [Error Response](/draft/specification/reference/#error-response).

### Get Checkout

Retrieves the latest state of the checkout session.

**Inputs**

| Name | Type   | Requirement  | Description                                                    |
| ---- | ------ | ------------ | -------------------------------------------------------------- |
| id   | string | **Required** | The unique identifier of the checkout session.Defined in path. |

**Output**

This object MUST be one of the following types: [Checkout](/draft/specification/food/checkout/#checkout), [Error Response](/draft/specification/reference/#error-response).

### Update Checkout

Performs a full replacement of the checkout session. The Platform is **REQUIRED** to send the complete writable state, including `food_establishment` and `line_items`, along with any changes (e.g., fulfillment, buyer, tip). To preserve existing line item handles across updates, the Platform **SHOULD** include each item's `line_items[].id` from the prior response; omitting `id` indicates a newly added line item.

**Inputs**

| Name               | Type                                                                 | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------------ | -------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id                 | string                                                               | **Required** | The unique identifier of the checkout session.Defined in path.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| food_establishment | [Location Summary](/draft/specification/reference/#location-summary) | **Required** | Food establishment location the checkout is associated with. In create requests, required when initializing with inline `line_items` and optional when initializing via `cart_id`. Required in update requests and checkout responses.                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| line_items         | Array\[[Line Item](/draft/specification/food/checkout/#line-item)\]  | **Required** | List of dishes being checked out. In create requests, the Platform MUST include `line_items` (with `food_establishment`) or `cart_id`, and MAY include both. The Platform MUST include `line_items` in update requests and omits it from complete requests. The Business MUST include `line_items` in checkout responses.                                                                                                                                                                                                                                                                                                                                               |
| buyer              | [Buyer](/draft/specification/food/checkout/#buyer)                   | Optional     | Representation of the buyer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| context            | [Context](/draft/specification/reference/#context)                   | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals            | [Signals](/draft/specification/reference/#signals)                   | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| payment            | [Payment](/draft/specification/reference/#payment)                   | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

**Output**

This object MUST be one of the following types: [Checkout](/draft/specification/food/checkout/#checkout), [Error Response](/draft/specification/reference/#error-response).

### Complete Checkout

Final order placement call. Invoked when payment has been collected and the buyer commits to the order.

**Inputs**

| Name    | Type                                               | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                             |
| ------- | -------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id      | string                                             | **Required** | The unique identifier of the checkout session.Defined in path.                                                                                                                                                                                                                                                                                                                                          |
| signals | [Signals](/draft/specification/reference/#signals) | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace. |
| payment | [Payment](/draft/specification/reference/#payment) | **Required** | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                              |

**Output**

This object MUST be one of the following types: [Checkout](/draft/specification/food/checkout/#checkout), [Error Response](/draft/specification/reference/#error-response).

### Cancel Checkout

Cancels an active checkout session prior to completion.

**Inputs**

| Name | Type   | Requirement  | Description                                                    |
| ---- | ------ | ------------ | -------------------------------------------------------------- |
| id   | string | **Required** | The unique identifier of the checkout session.Defined in path. |

**Output**

This object MUST be one of the following types: [Checkout](/draft/specification/food/checkout/#checkout), [Error Response](/draft/specification/reference/#error-response).

## Transport Bindings

The abstract operations above are bound to specific transport protocols:

- [REST Binding](http://ucp.dev/draft/specification/food/checkout/rest/index.md): RESTful API mapping using standard HTTP verbs and JSON payloads.
- [MCP Binding](http://ucp.dev/draft/specification/food/checkout/mcp/index.md): Model Context Protocol mapping for agentic interaction.

## Entities

### Actions

Outstanding extension-defined Action instances, keyed by reverse-domain Action type, not extension name.

### Buyer

The person placing the order. `phone_number` uses E.164 format and lets the courier or kitchen reach the buyer about delivery or substitutions.

| Name         | Type   | Requirement | Description              |
| ------------ | ------ | ----------- | ------------------------ |
| first_name   | string | Optional    | First name of the buyer. |
| last_name    | string | Optional    | Last name of the buyer.  |
| email        | string | Optional    | Email of the buyer.      |
| phone_number | string | Optional    | E.164 standard.          |

### Context

Buyer location, localization, and eligibility claims (e.g., delivery-pass membership) used before completion.

| Name            | Type                                                                                | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --------------- | ----------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| address_country | string                                                                              | Optional    | The country, as a 2-letter ISO 3166-1 alpha-2 code (e.g. "US"). A 3-letter alpha-3 code or full country name MAY also be used.                                                                                                                                                                                                                                                                                                                                     |
| address_region  | string                                                                              | Optional    | The first-level administrative region within the country (e.g. a state or province such as California).                                                                                                                                                                                                                                                                                                                                                            |
| postal_code     | string                                                                              | Optional    | The postal code (e.g. "94043").                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| location        | string                                                                              | Optional    | Stable, opaque identifier for a Location in the Business's namespace. This provisional, non-binding hint is distinct from the Buyer's locality. The operation specification or an active capability/extension defines its effects. A common example in retail shopping is the default home store ID selected and saved by the user when purchasing groceries.                                                                                                      |
| intent          | string                                                                              | Optional    | Background context describing buyer's intent (e.g., 'looking for a gift under $50', 'need something durable for outdoor use'). Informs relevance, recommendations, and personalization.                                                                                                                                                                                                                                                                            |
| language        | string                                                                              | Optional    | Preferred language for content. Use IETF BCP 47 language tags (e.g., 'en', 'fr-CA', 'zh-Hans'). For REST, equivalent to Accept-Language header—platforms SHOULD fall back to Accept-Language when this field is absent; when provided, overrides Accept-Language. Businesses MAY return content in a different language if unavailable.                                                                                                                            |
| currency        | string                                                                              | Optional    | Preferred currency (ISO 4217, e.g., 'EUR', 'USD'). Businesses determine presentment currency from context and authoritative signals; this hint MAY inform selection in multi-currency markets. Also serves as the denomination for price filter values — platforms SHOULD include this field when sending price filters. Response prices include explicit currency confirming the resolution.                                                                      |
| eligibility     | Array\[[Reverse Domain Name](/draft/specification/reference/#reverse-domain-name)\] | Optional    | Buyer claims about eligible benefits such as loyalty membership, payment instrument perks, and similar. Recognized claims MAY inform the Business response (e.g., member-only product availability, adjusted pricing in catalog, provisional discounts at cart or checkout). Businesses MUST ignore unrecognized values without error. Values MUST use reverse-domain naming (e.g., 'com.example.loyalty_gold', 'org.school.student') and MUST be non-identifying. |
| payment         | Array\[[Context Payment](#context-payment)\]                                        | Optional    | Buyer-preferred payment handlers in priority order (most preferred first). Each entry names a handler advertised in the Business profile's `ucp.payment_handlers`, optionally narrowed to preferred instrument types. The Business SHOULD use it to preselect or prioritize the handler (and type, when given) and MAY ignore unavailable or ineligible entries; unrecognized values MUST be ignored without error.                                                |

#### Context Payment

| Name    | Type                                                                       | Requirement  | Description                                                                                                                                                                                                          |
| ------- | -------------------------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| handler | [Reverse Domain Name](/draft/specification/reference/#reverse-domain-name) | **Required** | Handler registry key advertised in the Business profile's `ucp.payment_handlers`.                                                                                                                                    |
| types   | Array[string]                                                              | Optional     | Optional preferred instrument types for this handler, in priority order, aligned with the handler's advertised `payment_instrument.type` values (for example `card` or `bank`). Unrecognized values MUST be ignored. |

### Dish

A menu item being ordered, with its base `price` and descriptive metadata.

| Name        | Type                                                    | Requirement  | Description                                                                                                                             |
| ----------- | ------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string                                                  | **Required** | The dish identifier, required to resolve the associated dish details. SHOULD be recognized by both the Platform and the Business.       |
| title       | string                                                  | **Required** | Dish title.                                                                                                                             |
| description | string                                                  | Optional     | Dish description.                                                                                                                       |
| price       | [Amount](/draft/specification/reference/#amount)        | **Required** | Unit price in ISO 4217 minor units.                                                                                                     |
| media       | Array\[[Media](/draft/specification/reference/#media)\] | Optional     | Dish media assets (e.g., dish images, preparation videos). First item is the featured media for presentation in food ordering surfaces. |

### Line Item

A configured dish and its `quantity`, structured `modifications[]`, free-form kitchen `note`, and Business-computed `totals`.

| Name          | Type                                                                      | Requirement  | Description                                                                                                                                                                                                                |
| ------------- | ------------------------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id            | string                                                                    | **Required** | Session-scoped line item identifier. Under full replacement on update, an echoed id is preserved on the resulting line, an omitted id is minted as a new line, and an unknown or duplicate id returns a recoverable error. |
| dish          | [Dish](/draft/specification/food/checkout/#dish)                          | **Required** | Dish object. Expected to use the currency of the parent object.                                                                                                                                                            |
| modifications | Array\[[Modification](/draft/specification/food/checkout/#modification)\] | Optional     | List of modifications selected for the dish on this line item.                                                                                                                                                             |
| note          | string                                                                    | Optional     | Buyer-specified freeform note for the kitchen on this line item. Passed verbatim; MUST NOT alter price or structured modifications.                                                                                        |
| quantity      | integer                                                                   | **Required** | Quantity of the dish being purchased.                                                                                                                                                                                      |
| totals        | Array\[[Total Response](/draft/specification/reference/#total)\]          | **Required** | Line item totals breakdown.                                                                                                                                                                                                |

### Link

Legal and policy links (e.g., Privacy Policy, Terms of Service, allergen information).

| Name  | Type   | Requirement  | Description                                                                                                                                                                                                                                                  |
| ----- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| type  | string | **Required** | Type of link. Well-known values: `privacy_policy`, `terms_of_service`, `refund_policy`, `shipping_policy`, `faq`. Consumers SHOULD handle unknown values gracefully by displaying them using the `title` field or omitting the link.                         |
| url   | string | **Required** | The actual URL pointing to the content to be displayed.                                                                                                                                                                                                      |
| title | string | Optional     | Optional display text for the link. When provided, use this instead of generating from type.                                                                                                                                                                 |
| id    | string | Optional     | Optional identifier for the linked resource when it is an addressable UCP resource (for example, a product or variant), so a platform can act on it through the capability that owns it. Omit for resources without a UCP identifier, such as a policy page. |

### Location Summary

The food establishment (restaurant, cafe, or kitchen) that prepares the order, referenced by `food_establishment`.

| Name    | Type                                                             | Requirement  | Description                                                                                                   |
| ------- | ---------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------- |
| id      | string                                                           | **Required** | Stable, opaque, Business-scoped Location identifier.                                                          |
| name    | string                                                           | **Required** | Buyer-facing, Business-owned display name.                                                                    |
| address | [Postal Address](/draft/specification/reference/#postal-address) | Optional     | Physical address of the location.                                                                             |
| media   | Array\[[Media](/draft/specification/reference/#media)\]          | Optional     | Location media assets (e.g., images, logos, hero banners). First item is the featured media for presentation. |

### Message Error

| Name         | Type                                                     | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------ | -------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                   | **Required** | **Constant = error**. Message type discriminator.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| code         | [Error Code](/draft/specification/reference/#error-code) | **Required** | Error code identifying the type of error. Standard errors are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| path         | string                                                   | Optional     | RFC 9535 JSONPath to the component the message refers to (e.g., $.line_items[0]).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| content_type | string                                                   | Optional     | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| content      | string                                                   | **Required** | Human-readable message.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| severity     | string                                                   | **Required** | Reflects the resource state and recommended action. 'recoverable': platform can resolve the condition in band, for example by modifying inputs or processing a related Action, and submit a new operation when needed. 'requires_buyer_input': merchant requires information their API doesn't support collecting programmatically (checkout incomplete). 'requires_buyer_review': buyer must authorize before order placement due to policy, regulatory, or entitlement rules. 'unrecoverable': no valid resource exists to act on, retry with new resource or inputs. Errors with 'requires\_*' severity contribute to 'status: requires_escalation'.* *Enum:*\* `recoverable`, `requires_buyer_input`, `requires_buyer_review`, `unrecoverable` |

### Message Info

| Name         | Type                                                   | Requirement  | Description                                                                                                                                                                                    |
| ------------ | ------------------------------------------------------ | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                 | **Required** | **Constant = info**. Message type discriminator.                                                                                                                                               |
| path         | string                                                 | Optional     | RFC 9535 JSONPath to the component the message refers to (e.g., $.line_items[0]).                                                                                                              |
| code         | [Info Code](/draft/specification/reference/#info-code) | Optional     | Info code identifying the type of informational message. Standard codes are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted. |
| content_type | string                                                 | Optional     | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                 |
| content      | string                                                 | **Required** | Human-readable message.                                                                                                                                                                        |

### Message Warning

| Name         | Type                                                         | Requirement  | Description                                                                                                                                                                                                                                         |
| ------------ | ------------------------------------------------------------ | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                       | **Required** | **Constant = warning**. Message type discriminator.                                                                                                                                                                                                 |
| path         | string                                                       | Optional     | RFC 9535 JSONPath to the component the message refers to (e.g., $.line_items[0]).                                                                                                                                                                   |
| code         | [Warning Code](/draft/specification/reference/#warning-code) | **Required** | Warning code identifying the type of warning. Standard codes are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.                                                                 |
| content      | string                                                       | **Required** | Human-readable warning message that MUST be displayed.                                                                                                                                                                                              |
| content_type | string                                                       | Optional     | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                      |
| presentation | string                                                       | Optional     | Rendering contract for this warning. 'notice' (default): platform MUST display, MAY dismiss. 'disclosure': platform MUST display in proximity to the path-referenced component, MUST NOT hide or auto-dismiss. See specification for full contract. |
| image_url    | string                                                       | Optional     | URL to a required visual element (e.g., warning symbol, energy class label).                                                                                                                                                                        |
| url          | string                                                       | Optional     | Reference URL for more information (e.g., regulatory site, registry entry, policy page).                                                                                                                                                            |

### Modification

A menu-defined customization (priced or `$0`, such as "Extra Mozzarella", "Gluten-Free Crust", or "No Onions") applied to a [Line Item](#line-item).

A modification with `quantity` omitted **MUST** be treated as `quantity: 1`. `price` remains the price of a single unit regardless of `quantity`, and businesses **MUST** reflect `quantity` in the line item `totals` breakdown.

Platforms **MUST** express repeated units of the same modification as a single entry whose `quantity` is greater than 1, and **MUST NOT** repeat an entry to convey quantity. Businesses **MUST NOT** infer a quantity from a repeated modification `id` within a single line item, and **SHOULD** reject such a request as invalid.

| Name        | Type                                                    | Requirement  | Description                                                                                                                         |
| ----------- | ------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| id          | string                                                  | **Required** | The modification identifier. SHOULD be recognized by both the Platform and the Business.                                            |
| title       | string                                                  | **Required** | Modification title.                                                                                                                 |
| description | string                                                  | Optional     | Modification description.                                                                                                           |
| price       | [Amount](/draft/specification/reference/#amount)        | **Required** | Unit price in ISO 4217 minor units.                                                                                                 |
| quantity    | integer                                                 | Optional     | Quantity of the modification. Defaults to 1 when omitted.                                                                           |
| media       | Array\[[Media](/draft/specification/reference/#media)\] | Optional     | Modification media assets (e.g., modification photos). First item is the featured media for presentation in food ordering surfaces. |

### Order Confirmation

Order details returned on `completed`: the order `id`, an optional human-readable `label`, a live `tracking_url`, and an optional committed fulfillment window (`earliest_fulfillment_time` / `latest_fulfillment_time`).

| Name                      | Type   | Requirement  | Description                                                                            |
| ------------------------- | ------ | ------------ | -------------------------------------------------------------------------------------- |
| id                        | string | **Required** | Unique order identifier.                                                               |
| label                     | string | Optional     | Human-readable label for identifying the order. MUST only be provided by the business. |
| tracking_url              | string | **Required** | A URL to access or track the order on the business site.                               |
| earliest_fulfillment_time | string | Optional     | Earliest committed fulfillment time (RFC 3339) after kitchen acceptance.               |
| latest_fulfillment_time   | string | Optional     | Latest committed fulfillment time (RFC 3339) after kitchen acceptance.                 |

### Payment

Payment details and collected payment instruments.

| Name        | Type                                                                                                                                      | Requirement | Description                                                                                                                                                                                                                |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| instruments | Array\[[Payment Instrument Selected Payment Instrument](/draft/specification/reference/#payment-instrument-selected-payment-instrument)\] | Optional    | The payment instruments available for this payment. Each instrument is associated with a specific handler via the handler_id field. Handlers can extend the base payment_instrument schema to add handler-specific fields. |

### Policy

Business-specific policies applicable to the checkout session.

| Name        | Type                                                                       | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ----------- | -------------------------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type        | [Reverse Domain Name](/draft/specification/reference/#reverse-domain-name) | **Required** | Policy type discriminator. Open reverse-DNS vocabulary. See specification documentation for the registry of well-known policy types. Businesses MAY define custom types in their own domain (e.g., `com.example.policy.price_match`). Platforms MUST tolerate unknown values.                                                                                                                                                                                                                                                                                                                                                                                                      |
| description | [Description](/draft/specification/reference/#description)                 | **Required** | Human-readable policy summary in one or more formats (plain, markdown, html). Required on every policy so a platform can present it without understanding any type-specific fields. This is not the buyer-facing disclosure — display is compelled by a `messages[]` warning (see the Policies section).                                                                                                                                                                                                                                                                                                                                                                           |
| applies_to  | Array[string]                                                              | Optional     | RFC 9535 JSONPath expressions identifying the nodes this policy applies to, relative to the embedding response root (e.g., `$.line_items[0]` in cart/checkout, `$.products[2]` in catalog). Each target covers the node it names and everything nested under it, so a target on a product also covers its variants. A singular query (RFC 9535 Section 2.3.5.1; name and index selectors only) names a single node; filters, wildcards, and slices match a set. When omitted, the policy applies to the entire response. When policies of the same `type` contest a node, the narrowest target wins and overrides the rest. See the Policies section for how specificity resolves. |
| url         | string                                                                     | Optional     | Optional link to the full policy document.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

### Signals

Platform-supplied fraud and security context.

| Name               | Type   | Requirement | Description                                    |
| ------------------ | ------ | ----------- | ---------------------------------------------- |
| dev.ucp.buyer_ip   | string | Optional    | Client's IP address (IPv4 or IPv6).            |
| dev.ucp.user_agent | string | Optional    | Client's HTTP User-Agent header or equivalent. |

### Total

Authoritative itemized price components and the aggregate order total. See [Checkout — Total](http://ucp.dev/draft/specification/shopping/checkout/#totals) for the rendering and verification contract.

| Name         | Type                                                           | Requirement  | Description                                                                                                                                                                                                                                                                                 |
| ------------ | -------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                         | **Required** | Cost category. Well-known values: subtotal, items_discount, discount, fulfillment, tax, fee, total. Businesses MAY use additional values.                                                                                                                                                   |
| display_text | string                                                         | Optional     | Text to display against the amount. Should reflect appropriate method (e.g., 'Shipping', 'Delivery').                                                                                                                                                                                       |
| amount       | [Signed Amount](/draft/specification/reference/#signed-amount) | **Required** | Monetary amount in the currency's minor unit as defined by ISO 4217. Refer to the currency's exponent to determine minor-to-major ratio (e.g., 2 for USD, 0 for JPY, 3 for KWD). May be negative — the sign is intrinsic to the value (e.g., discounts are negative, charges are positive). |
