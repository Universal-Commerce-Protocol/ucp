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

# Checkout Capability

!!! note "Draft - Work in Progress"
    This capability is in **draft status**. Implementers are cautioned that data
    models, protocol bindings, and operational flows are under active iteration
    and may undergo breaking changes as the specification evolves.

* **Capability Name:** `dev.ucp.food.checkout`

## Overview

The Checkout capability allows Platforms to facilitate checkout sessions
for prepared food and beverage orders — from restaurants, cafes, bakeries, food
trucks, etc.

The Business remains the Merchant of Record (MoR) and the system of record for
the menu, the kitchen, and the order. It does not need to become PCI DSS
compliant to accept card payments through this capability. Unless the AP2
Mandates extension is supported, the checkout must be finalized manually by the
buyer through a trusted UI.

### Flow Overview

Checkout follows a progressive session lifecycle:

1. **Session Initiation**: The Platform creates a checkout session for one
   `food_establishment` with the dishes and modifications the buyer picked from
   the menu (or converts an existing cart via `cart_id`).
2. **Progressive Enrichment**: The Platform updates the session with the
   fulfillment choice (delivery or pickup, ASAP or scheduled), buyer contact
   details, and a tip. The Business re-prices on every update.
3. **Session Completion**: The Platform submits payment. The Business injects
   the order into the kitchen and returns an order confirmation with an optional
   display label and a live tracking link.

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

* `food_establishment` 🏪 Luigi's Artisan Pizzeria — every dish below comes from this one kitchen
* `line_items[0]` 🍕 × 2
    * `dish` Margherita Pizza (12") — $16.00
    * `dish.modifications[]` 🧀 Extra Mozzarella +$2.00 · 🌿 Fresh Basil +$1.50
    * `dish.note` 📝 "Well done crust, please"
* `line_items[1]` 🥗 × 1
    * `dish` Caesar Salad — $11.00
    * `dish.note` 📝 "Dressing on the side"
* `fulfillment.methods[0]` 🛵 delivery → 450 Serra Mall, Apt 3B *(via the [Fulfillment Extension](../extensions/fulfillment.md))*
    * `selected_option_id` 🔘✅ Standard Delivery, 6:35–6:50 PM, $2.99
* `tip` 💵 `selected_option_id` 🔘✅ 18%
* `totals[]` 🧾 subtotal · delivery · fees · tax · tip · **total**
* `order` 🎫 `#42` → `tracking_url` *(after completion)*

## Key Concepts

* **Single-Establishment Order Scope (`food_establishment`)**: Prepared food is
  cooked to order and must leave the kitchen within a tight freshness window, so
  a checkout session is bound to exactly one preparation location. Every
  `line_items[].dish` **MUST** come from that establishment's active menu.
* **Shared Menu Identifiers (`dish.id`, `modification.id`)**: Dish and
  modification identifiers come from upper-funnel menu discovery and **MUST**
  be recognized by both the Platform and the Business. On requests the Platform
  sends only these opaque identifiers (plus `quantity` and `note`); all other attributes
  (e.g., `title`, `description`, `price`, etc.) are Business-authored and omitted from requests.
* **Provisional Menu vs. Authoritative Checkout**:
    * *Menu Browsing (Provisional)*: Menus, prices, and estimated prep times
      shown during discovery are provisional. Kitchens can sell out of dishes
      mid-service, pause intake when ticket queues back up, and switch between
      lunch and dinner menus.
    * *Checkout Session (Authoritative)*: Each create or update re-validates the
      session against live kitchen state — operating hours, item and modifier
      availability, delivery coverage, and order minimums — and returns
      authoritative `line_items[].totals` and `totals[]`.

### Dish Customization

Food ordering relies on rich item-level customization — choosing a protein,
picking a spice level, upgrading a side, or adding toppings — alongside
free-form kitchen requests. The [Dish](#dish) entity separates the two:

| Mechanism | Field | Priced? | Contract |
| :--- | :--- | :--- | :--- |
| **Structured modifications** | `dish.modifications[]` ([Modification](#modification)) | Yes | Platform sends menu-backed modification `id`s. Business validates modifier-group rules (required choices, min/max selections, mutually exclusive options), echoes `title` and `price`, and includes the charges in `line_items[].totals`. |
| **Special instructions** | `dish.note` | No | Free-form buyer text for the kitchen (e.g., "sauce on the side", "cut in half", "no onions"). **MUST NOT** trigger paid add-ons. |

* **Modification quantity applies per unit of the dish.** `modification.quantity`
  specifies how many units of that modification apply to **each** unit of the dish
  (defaults to 1 when omitted). `line_items[].quantity` multiplies the whole
  configured dish (base price plus all modifications scaled by their quantity).
* **Platforms MUST NOT convey quantity by repetition.** Repeated units of the
  same modification **MUST** be expressed as a single entry with `quantity`
  greater than 1.
* **A configured dish is a line item.** Two units of the same dish with
  different modifications or different notes are separate `line_items[]`
  entries; Platforms **MUST NOT** merge them.
* **Line item arithmetic.** A line's `subtotal` is
  `(dish.price + sum(modifications[].price × modifications[].quantity)) × line_items[].quantity`
  (where omitted `modifications[].quantity` defaults to 1).

=== "Request"

    The Platform sends identifiers and buyer input only:

    <!-- ucp:example schema=food/checkout op=create direction=request -->
    ```json
    {
      "food_establishment": { "id": "est_luigis_01" },
      "line_items": [
        {
          "quantity": 2,
          "dish": {
            "id": "dish_margherita_12",
            "modifications": [
              { "id": "mod_extra_mozzarella" },
              { "id": "mod_fresh_basil" }
            ],
            "note": "Well done crust, please"
          }
        },
        {
          "quantity": 1,
          "dish": {
            "id": "dish_caesar",
            "note": "Dressing on the side"
          }
        }
      ]
    }
    ```

=== "Response"

    The Business echoes authoritative menu data and prices each configured dish:

    <!-- ucp:example schema=food/checkout target=$.line_items op=read -->
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
          ],
          "modifications": [
            { "id": "mod_extra_mozzarella", "title": "Extra Mozzarella", "price": 200 },
            { "id": "mod_fresh_basil", "title": "Fresh Basil", "price": 150 }
          ],
          "note": "Well done crust, please"
        },
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
          "price": 1100,
          "note": "Dressing on the side"
        },
        "totals": [
          { "type": "subtotal", "amount": 1100 },
          { "type": "total", "amount": 1100 }
        ]
      }
    ]
    ```

=== "Error Response: Note Carries Add-Ons"

    When a `dish.note` asks for something the menu sells as a modification, the
    Business **SHOULD** return a warning pointing back to the note:

    <!-- ucp:example schema=food/checkout target=$.messages op=read -->
    ```json
    [
      {
        "type": "warning",
        "code": "note_contains_modification",
        "path": "$.line_items[0].dish.note",
        "content": "\"Add avocado\" is a paid add-on (+$2.50). Select the Avocado modification to add it; notes are passed to the kitchen as-is and cannot add charges."
      }
    ]
    ```

### Pricing Scope

Checkout uses the shared [Total](#total) structure and follows the
rendering contract, verification rule, repeating types, and `lines[]` sub-line
invariant defined in [Checkout — Total](../../shopping/checkout/index.md#totals).
Amounts are signed: discounts are negative, charges are non-negative, and all
non-total entries sum to the single `total` entry.

* **Line items (`subtotal`, `items_discount`)**: `subtotal` is the sum of
  `line_items[].totals[type=subtotal]` (dish plus modification prices). Dish-level
  promotions (e.g., "Free garlic knots with any large pizza") roll up as `items_discount`.
* **Delivery (`fulfillment`)**: The price of the selected
  [fulfillment option](../extensions/fulfillment.md#fulfillment-option). Pickup
  options are typically `0`.
* **Fees (`fee`)**: Some common examples include - marketplace service fees,
  small-order fees (basket below a threshold), bag or packaging fees, and municipal
  surcharges (e.g., courier minimum-pay regulatory fees). Use repeating `fee` entries
  or one `fee` entry with itemized `lines[]`.
* **Tax (`tax`)**: Sales tax and prepared-food or beverage taxes, which may
  differ from grocery rates and may apply to fees and delivery in some
  jurisdictions.
* **Gratuity (`tip`)**: A **food-defined total type**. Because `tip` is not in
  the common well-known set, Businesses **MUST** include `display_text` on it.
  See [Tips & Gratuity](#tips-and-gratuity).

The following snippets illustrate canonical food pricing patterns:

=== "Pattern 1: Delivery with Fees & Tip"

    A $50.00 delivery basket with a $2.99 delivery fee, service and regulatory
    fees itemized under one `fee` entry, 8.75% tax, and an 18% tip:

    <!-- ucp:example schema=food/checkout target=$.totals op=read -->
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

=== "Pattern 2: Pickup"

    The same basket picked up at the counter: no delivery fee, no courier fees,
    and a smaller staff tip:

    <!-- ucp:example schema=food/checkout target=$.totals op=read -->
    ```json
    [
      { "type": "subtotal", "display_text": "Subtotal", "amount": 5000 },
      { "type": "fulfillment", "display_text": "Pickup", "amount": 0 },
      { "type": "tax", "display_text": "Tax (8.75%)", "amount": 438 },
      { "type": "tip", "display_text": "Staff Tip (10%)", "amount": 500 },
      { "type": "total", "display_text": "Total", "amount": 5938 }
    ]
    ```

=== "Pattern 3: Promotions & Delivery Pass"

    A dish-level promotion (`items_discount`), an order-level promo code
    (`discount`), and a delivery-pass membership that waives the delivery fee:

    <!-- ucp:example schema=food/checkout target=$.totals op=read -->
    ```json
    [
      { "type": "subtotal", "display_text": "Subtotal", "amount": 5000 },
      { "type": "items_discount", "display_text": "Free Garlic Knots", "amount": -600 },
      { "type": "discount", "display_text": "Promo WELCOME10", "amount": -440 },
      { "type": "fulfillment", "display_text": "Delivery (Free with Pass)", "amount": 0 },
      { "type": "fee", "display_text": "Service Fee", "amount": 350 },
      { "type": "tax", "display_text": "Tax (8.75%)", "amount": 346 },
      { "type": "tip", "display_text": "Courier Tip (18%)", "amount": 450 },
      { "type": "total", "display_text": "Total", "amount": 5106 }
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

### Tips and Gratuity

Gratuity for couriers and counter staff is part of the checkout itself,
not an afterthought. The top-level [Tip](#tip) object separates what the
Business suggests from what the buyer chooses:

* **Suggestions (`tip.options[]`, Business-authored)**: Each
  [Tip Option](#tip-option) has an `id`, a `unit` (`percentage` or `absolute`),
  and an `amount`. With `unit: "percentage"`, `amount` is the percent (e.g.,
  `18`); with `unit: "absolute"`, it is in ISO 4217 minor units (e.g., `500` for
  $5.00). Tip options carry no label: the Platform renders one from `unit` and
  `amount` (e.g., "18%", "$5").
* **Choice (`tip.selected_option_id` or `tip.custom_amount`, Platform-authored)**:
  The schema's `oneOf` admits exactly three states:

| State | `selected_option_id` | `custom_amount` | Meaning |
| :--- | :--- | :--- | :--- |
| Preset | ✅ | — | Buyer picked a suggested option. |
| Custom | — | ✅ | Buyer entered an amount in minor units (`0` = no tip). |
| Unset | — | — | No choice yet; the Business **MAY** apply a default. |
| ❌ Invalid | ✅ | ✅ | Rejected by schema validation. |

* **Resolution (`totals[]`, Business-authored)**: The Business resolves the
  choice into money — computing percentages against its stated basis
  (typically the pre-tax `subtotal`) — and **MUST** report any non-zero tip as a
  `type: "tip"` entry in `totals[]`. `tip` holds the choice; `totals[]` holds the
  amount.

A Platform renders the suggestions as quick-select chips:

```text
Add a tip for your courier
 [ 15% ]  [ ✅ 18% ]  [ 20% ]  [ Custom ]                  Tip: $9.00
```

=== "Business Suggests Options"

    <!-- ucp:example schema=food/checkout target=$.tip op=read -->
    ```json
    {
      "options": [
        { "id": "tip_15", "unit": "percentage", "amount": 15 },
        { "id": "tip_18", "unit": "percentage", "amount": 18 },
        { "id": "tip_20", "unit": "percentage", "amount": 20 },
        { "id": "tip_5usd", "unit": "absolute", "amount": 500 }
      ]
    }
    ```

=== "Platform Selects a Preset"

    <!-- ucp:example schema=food/types/tip op=update direction=request -->
    ```json
    {
      "selected_option_id": "tip_18"
    }
    ```

=== "Platform Sends a Custom Amount"

    <!-- ucp:example schema=food/types/tip op=update direction=request -->
    ```json
    {
      "custom_amount": 700
    }
    ```

### Payments

Payment handlers are discovered from the Business's UCP profile at
`/.well-known/ucp` and `checkout.ucp.payment_handlers`, following the same model
as [Checkout — Payments](../../shopping/checkout/index.md#payments). `payment`
is optional on create & update and **REQUIRED** on Complete Checkout.

Because the tip and the delivery fee can change up to the moment of completion,
Platforms **MUST** present the final `totals[]` — including `type: "tip"` — for
buyer confirmation before submitting payment.

### Cart-to-Checkout Conversion

A Platform can create a checkout by passing `cart_id`. Conversion follows
[Cart — Cart-to-Checkout Conversion](../../shopping/cart/index.md#cart-to-checkout-conversion):
the Business populates the session from the cart's `food_establishment`,
`line_items[]` (dishes, modifications, and notes), `buyer`, and `context`, and
ignores overlapping fields in the request. Checkout-only fields — `tip`,
`fulfillment`, `payment` — **MAY** be sent alongside `cart_id`.

<!-- ucp:example schema=food/cart def=checkout op=create direction=request -->
```json
{
  "cart_id": "cart_food_8912",
  "line_items": [],
  "tip": { "selected_option_id": "tip_18" }
}
```

### Checkout Status Lifecycle

The `status` field indicates the current phase of the session. Statuses follow
[Checkout — Status Values](../../shopping/checkout/index.md#status-values); in
food ordering they typically mean:

| Status | Typical food ordering situation | Platform action |
| :--- | :--- | :--- |
| `incomplete` | No fulfillment method yet, a dish was 86'd, or the basket is under the delivery minimum. | Resolve `messages[]` via Update Checkout. |
| `requires_escalation` | Alcohol in the basket requires ID verification, or a catering order needs business review. | Hand off via `continue_url`. |
| `ready_for_complete` | Dishes, fulfillment, buyer contact, and tip are valid. | Show the final summary and disclosures; call Complete Checkout. |
| `complete_in_progress` | Payment capture or kitchen POS injection is still running. See [Accepted Completion](../../shopping/checkout/index.md#accepted-completion). `order` **MUST NOT** be present. | Poll Get Checkout. |
| `completed` | The kitchen has the ticket. `order` is present. | Show confirmation screen. |
| `canceled` | Canceled by the Platform or expired (default TTL: 6 hours). | Start a new session if needed. |

### Error Handling

Checkout uses the shared `messages[]` model, severities, and
[`path`](../../shopping/checkout/index.md#the-path-field) targeting defined in
[Checkout — Error Handling](../../shopping/checkout/index.md#error-handling),
including [eligibility verification at completion](../../shopping/checkout/index.md#eligibility-verification-at-completion).

Kitchen state changes by the minute, so food checkouts surface recoverable
errors far more often than retail. In addition to the shared
[standard errors](../../shopping/checkout/index.md#standard-errors), food
Businesses **SHOULD** use these codes so Platforms can offer targeted recovery:

| Code | Typical `path` | Food ordering meaning | Suggested recovery |
| :--- | :--- | :--- | :--- |
| `out_of_stock` | `$.line_items[1].dish` or `...modifications[0]` | Dish or ingredient 86'd for this service. | Offer a substitute or remove. |
| `item_unavailable` | `$.line_items[1].dish` | Dish not on the current menu (e.g., breakfast-only). | Remove or schedule for a later time. |
| `location_closed` | `$.food_establishment` | Establishment closed or paused for intake. | Offer scheduled ordering or another location. |
| `address_undeliverable` | `$.fulfillment.methods[0].destination` | Address outside the delivery zone. | Offer pickup or a different address. |
| `minimum_order_unmet` | `$.totals` | Basket below the delivery minimum. | Prompt to add items. |
| `payment_failed` | `$.payment` | Authorization or capture failed. | Prompt for another payment method. |
| `eligibility_invalid` | `$.context.eligibility` | Delivery pass or membership could not be verified. | Show recomputed totals for review. |

`location_closed` and `minimum_order_unmet` are food-specific; the remaining
codes are the shared standard errors.

=== "Sold-Out Dish & Delivery Minimum"

    <!-- ucp:example schema=food/checkout target=$.messages op=read -->
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

=== "Kitchen Paused"

    <!-- ucp:example schema=food/checkout target=$.messages op=read -->
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

=== "Alcohol Requires ID Check"

    <!-- ucp:example schema=food/checkout target=$.messages op=read -->
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

> 🤖 Truffle Arancini just sold out for tonight. Want something else,
> or should I remove it? Either way you're $3.00 short of the $15
> delivery minimum.

### Warning Presentation

Checkout follows the `notice` vs. `disclosure` presentation contract and
the `totals_changed` rule in
[Checkout — Warning Presentation](../../shopping/checkout/index.md#warning-presentation).
In food ordering, `disclosure` is the right tier for **statutory food-safety
and labeling notices**, which Platforms **MUST** show prominently near the
referenced item and **MUST NOT** auto-dismiss:

* **Consumer advisory** (`consumer_advisory`): Raw or undercooked animal
  products, as required by food codes such as the U.S. FDA.
* **Allergens** (`allergens`): Major allergens or shared-equipment
  cross-contact.
* **Nutrition** (`nutritional_info`): Calorie or sodium statements required by
  menu-labeling laws.
* **Price changes** (`totals_changed`): A menu or fee change re-priced the
  order after the buyer reviewed it.

Use `notice` for operational context (e.g., "High demand — delivery times are
longer than usual").

=== "Food-Safety Disclosures"

    <!-- ucp:example schema=food/checkout target=$.messages op=read -->
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

=== "How It May Be Rendered by a Platform"

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

On `completed`, the Business returns an [Order Confirmation](#order-confirmation)
in `order`. Its design reflects how food orders are handed off:

* **`order.id`** (required): The Business's canonical order identifier.
* **`order.label`** (optional, Business-only): A short, human-readable callout
  that buyers and couriers use at the counter, shelf, or locker (e.g., `#42`,
  `B12`). It exists because order IDs may be too long to shout across a kitchen.
* **`order.tracking_url`** (required): A live page showing preparation status,
  ready or arrival time, and courier location. Unlike retail, where a receipt
  link suffices, food orders are tracked minute by minute until handoff.

<!-- ucp:example schema=food/checkout target=$.order op=read -->
```json
{
  "id": "ord_food_9876543210",
  "label": "#42",
  "tracking_url": "https://food.example.com/orders/ord_food_9876543210"
}
```

## Scopes

The Checkout capability defines the following well-known scopes for
user-authenticated access:

| Scope | Description |
| :--- | :--- |
| `dev.ucp.food.checkout:manage` | All checkout operations on behalf of the authenticated user — create, update, complete, and cancel checkout. |

Scope declaration, derivation, and rules for extending this set with
custom scopes are defined in [Identity Linking — Scopes](../../common/identity-linking/index.md#scopes).

## Continue URL

The `continue_url` field enables checkout handoff from the Platform to the
Business UI — for example, for ID verification or catering approval. URL
construction (server-side state vs. permalink) follows
[Checkout — Continue URL](../../shopping/checkout/index.md#continue-url).

### Availability

Businesses **MUST** provide `continue_url` when returning `status` =
`requires_escalation`. For all other non-terminal statuses (`incomplete`,
`ready_for_complete`, `complete_in_progress`), Businesses **SHOULD** provide
`continue_url`. For terminal states (`completed`, `canceled`), `continue_url`
**SHOULD** be omitted.

## Guidelines

### Platform

* **MUST** supply a valid `food_establishment.id` and `line_items[].dish.id`
  (and `modifications[].id` where customized) sourced from menu discovery, unless
  converting a cart via `cart_id`.
* **MUST** present each `line_items[]` entry as a unit — `dish.title`, every
  modification `title`, `quantity` (when greater than 1), and `price`,
  `dish.note`, and the line's `totals` — and **MUST NOT** merge entries that
  differ in modifications or notes.
* **MUST** keep kitchen instructions in `dish.note` and courier instructions in
  `fulfillment.methods[].notes`.
* **MUST NOT** send both `tip.selected_option_id` and `tip.custom_amount`, and
  **MUST** render the tip from the `type: "tip"` entry in `totals[]`.
* **SHOULD** collect `buyer.phone_number` (E.164) for delivery orders so the
  courier or kitchen can reach the buyer.
* **MUST** render `presentation: "disclosure"` warnings (consumer advisories,
  allergens, `totals_changed`) prominently and **MUST NOT** auto-dismiss them.
* **MUST** surface `order.tracking_url`, and `order.label` when present, after
  completion.
* **MUST** use `continue_url` when status is `requires_escalation`, and **MAY**
  use it to hand off in other situations.

### Business

* **MUST** validate `food_establishment.id`, dish IDs, and modification IDs
  against live operating hours, item and ingredient availability, and
  modifier-group rules on every create and update operation.
* **MUST** echo authoritative `title` and `price` for every dish and modification,
  and compute `line_items[].totals` and `totals[]` deterministically.
* **MUST NOT** infer a quantity from a repeated modification `id` within a
  single dish, and **SHOULD** reject duplicate modification IDs as invalid.
* **MUST NOT** add charges based on `dish.note`; **SHOULD** return a warning message
  when a note requests for a paid add-on.
* **MUST** include `display_text` on `type: "tip"` totals and report any non-zero
  tip in `totals[]`.
* **SHOULD** use the food error codes in [Error Handling](#error-handling) with a
  precise `path`.
* **MUST** return `order.id` and `order.tracking_url` on `completed`, and
  **SHOULD** return `order.label` whenever buyers or couriers collect at a
  counter, shelf, or locker.
* **MUST** send an order confirmation when a valid `buyer.email` is available.
* **MUST** provide `continue_url` and at least one message with `severity` of
  `requires_buyer_input` or `requires_buyer_review` when returning
  `requires_escalation`.
* After a checkout session reaches `completed`, it is considered immutable.

## Capability Schema Definition <span id="checkout"></span>

{{ schema_fields('food/checkout_resp', 'food/checkout') }}

## Operations

The Checkout capability defines the following logical operations:

| Operation | Description |
| :--- | :--- |
| **Create Checkout** | Initiates a new food checkout session. Called as soon as the buyer expresses intent to order. |
| **Get Checkout** | Retrieves the current state of a checkout session. |
| **Update Checkout** | Updates a checkout session via full resource replacement. |
| **Complete Checkout** | Submits payment and places the order with the kitchen. |
| **Cancel Checkout** | Cancels a checkout session. |

### Create Checkout

Invoked when the buyer expresses intent to order from a food establishment.

{{ method_fields('create_checkout', 'food/rest.openapi.json', 'food/checkout') }}

### Get Checkout

Retrieves the latest state of the checkout session.

{{ method_fields('get_checkout', 'food/rest.openapi.json', 'food/checkout') }}

### Update Checkout

Performs a full replacement of the checkout session. The Platform is
**REQUIRED** to send the complete writable state, including `line_items`, along
with any changes (e.g., fulfillment, buyer, tip).

{{ method_fields('update_checkout', 'food/rest.openapi.json', 'food/checkout') }}

### Complete Checkout

Final order placement call. Invoked when payment has been collected and the
buyer commits to the order.

{{ method_fields('complete_checkout', 'food/rest.openapi.json', 'food/checkout') }}

### Cancel Checkout

Cancels an active checkout session prior to completion.

{{ method_fields('cancel_checkout', 'food/rest.openapi.json', 'food/checkout') }}

## Transport Bindings

The abstract operations above are bound to specific transport protocols:

* [REST Binding](rest.md): RESTful API mapping using standard HTTP verbs and JSON payloads.
* [MCP Binding](mcp.md): Model Context Protocol mapping for agentic interaction.

## Entities

### Buyer

The person placing the order. `phone_number` uses E.164 format and lets the
courier or kitchen reach the buyer about delivery or substitutions.

{{ schema_fields('food/types/buyer', 'food/checkout') }}

### Context

Buyer location, localization, and eligibility claims (e.g., delivery-pass
membership) used before completion.

{{ schema_fields('types/context', 'food/checkout') }}

### Dish

A menu item being ordered, with its base `price`, structured `modifications[]`,
and free-form kitchen `note`.

{{ schema_fields('food/types/dish', 'food/checkout') }}

### Food Establishment

The restaurant, cafe, or kitchen that prepares the order.

{{ schema_fields('food/types/food_establishment', 'food/checkout') }}

### Line Item

A configured dish and its `quantity`, with Business-computed `totals`.

{{ schema_fields('food/types/line_item', 'food/checkout') }}

### Link

Legal and policy links (e.g., Privacy Policy, Terms of Service, allergen
information).

{{ schema_fields('types/link', 'food/checkout') }}

### Message Error

{{ schema_fields('types/message_error', 'food/checkout') }}

### Message Info

{{ schema_fields('types/message_info', 'food/checkout') }}

### Message Warning

{{ schema_fields('types/message_warning', 'food/checkout') }}

### Modification

A priced customization applied to a [Dish](#dish) (e.g., "Extra Mozzarella",
"Gluten-Free Crust").

A modification with `quantity` omitted **MUST** be treated as `quantity: 1`.
`price` remains the price of a single unit regardless of `quantity`, and
businesses **MUST** reflect `quantity` in the line item `totals` breakdown.

Platforms **MUST** express repeated units of the same modification as a single
entry whose `quantity` is greater than 1, and **MUST NOT** repeat an entry to
convey quantity. Businesses **MUST NOT** infer a quantity from a repeated
modification `id` within a single dish, and **SHOULD** reject such a request as
invalid.

{{ schema_fields('food/types/modification', 'food/checkout') }}

### Order Confirmation

Order details returned on `completed`: the order `id`, an optional
human-readable `label`, and a live `tracking_url`.

{{ schema_fields('food/types/order_confirmation', 'food/checkout') }}

### Payment

Payment details and collected payment instruments.

{{ schema_fields('payment', 'food/checkout') }}

### Signals

Platform-supplied fraud and security context.

{{ schema_fields('types/signals', 'food/checkout') }}

### Tip

The buyer's gratuity choice and the Business's suggested options.

{{ schema_fields('food/types/tip', 'food/checkout') }}

### Tip Option

A suggested gratuity, expressed as a percentage or an absolute amount.

{{ schema_fields('food/types/tip_option', 'food/checkout') }}

### Total

Authoritative itemized price components and the aggregate order total. See
[Checkout — Total](../../shopping/checkout/index.md#totals) for the rendering
and verification contract.

{{ schema_fields('types/total_resp', 'food/checkout') }}
