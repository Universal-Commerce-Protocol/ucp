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

# Tip Extension

## Overview

Gratuity for couriers and counter staff is part of the checkout itself,
not an afterthought. The Food Tip Extension (`dev.ucp.food.tip`) adds a `tip`
field to food checkout sessions for courier and counter-staff gratuity,
separating what the Business suggests from what the buyer chooses.

**Key features:**

- Business-suggested tip presets (`options[]`) in either `percentage` or
  `absolute` units
- Buyer choice expressed via a preset selection (`selected_option_id`) or a
  custom amount (`custom_amount`) in minor currency units
- Mutual exclusion (`oneOf`) between preset selection, custom amount, and an
  unset state
- Authoritative resolution of the selected tip into checkout `totals[]` as a
  `type: "tip"` entry

`tip` contains:

- `options[]` — Business-authored tip suggestions, each with an `id`, `unit`
  (`percentage` or `absolute`), and `amount`
- `selected_option_id` — Platform-authored `id` of a selected preset option from
  `options[]` (available on Update Checkout)
- `custom_amount` — Platform-authored custom tip amount in ISO 4217 minor units
  (available on Create and Update Checkout; `0` = no tip)

**Mental model:**

- `options[]` 💡 Business suggestions
    - `options[0]` 🔘 `15%` (`unit: "percentage"`, `amount: 15`)
    - `options[1]` 🔘✅ `18%` (`unit: "percentage"`, `amount: 18`)
    - `options[2]` 🔘 `20%` (`unit: "percentage"`, `amount: 20`)
    - `options[3]` 🔘 `$5.00` (`unit: "absolute"`, `amount: 500`)
- `selected_option_id` = `options[1].id` *(or `custom_amount` for custom input)*
- `totals[]` 🧾 `{ "type": "tip", "display_text": "Courier Tip (18%)", "amount": 900 }`

## Discovery

Businesses advertise food tip support in their profile:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.food.tip": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.food.checkout",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/food/extensions/tip",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/food/tip.json"
        }
      ]
    }
  }
}
```

## Tip Selection & Resolution

Across a checkout session, gratuity flows through three stages: the Business
advertises preset [Tip Options](#tip-option) in `tip.options[]`, the Platform
submits the buyer's choice on [Tip](#tip) via `selected_option_id` or
`custom_amount`, and the Business resolves the monetary amount into `totals[]`.

### Suggestions (`tip.options[]`)

**Business-authored.** Each [Tip Option](#tip-option) has an `id`, a `unit`
(`percentage` or `absolute`), and an `amount`. With `unit: "percentage"`,
`amount` is the percent (e.g., `18`); with `unit: "absolute"`, it is in
ISO 4217 minor units (e.g., `500` for $5.00). Tip options carry no label: the
Platform renders one from `unit` and `amount` (e.g., "18%", "$5").

A Platform renders the suggestions as quick-select chips:

```text
Add a tip for your courier
 [ 15% ]  [ ✅ 18% ]  [ 20% ]  [ Custom ]                  Tip: $9.00
```

### Choice (`tip.selected_option_id` or `tip.custom_amount`)

**Platform-authored.** `selected_option_id` is omitted on Create Checkout
(`create: omit`) and available on Update Checkout (`update: optional`) once the
Business has returned `tip.options[]`; `custom_amount` **MAY** be sent on
either create or update. The schema's `oneOf` admits exactly three states:

| State | `selected_option_id` | `custom_amount` | Meaning |
| :--- | :--- | :--- | :--- |
| Preset | ✅ | — | Buyer picked a suggested option (on update). |
| Custom | — | ✅ | Buyer entered an amount in minor units (`0` = no tip). |
| Unset | — | — | No choice yet; adds nothing to `totals[]` until the Platform submits an explicit selection via `selected_option_id` or `custom_amount`. |
| ❌ Invalid | ✅ | ✅ | Rejected by schema validation. |

### Resolution (`totals[]`)

**Business-authored.** The Business resolves the choice into money — percentage
`tip.options[]` are computed against the pre-discount `subtotal` entry in
`totals[]` — and **MUST** report any non-zero selected tip as a `type: "tip"`
entry in `totals[]`. Because `tip` is a food-defined total type and not in the
common well-known set, Businesses **MUST** include `display_text` on it. `tip`
holds the choice; `totals[]` holds the amount.

### Fulfillment Changes & Checkout Handoff

- **Fulfillment switch**: When a fulfillment switch (e.g., `delivery` → `pickup`)
  replaces `tip.options[]` and invalidates a prior `selected_option_id`, the
  Business **MUST** clear `selected_option_id` (returning `tip` to `Unset`
  state) and **SHOULD** surface a `notice` warning.
- **Checkout handoff (`continue_url`)**: When a Platform hands off a checkout
  session to the Business UI via
  [`continue_url`](../checkout/index.md#continue-url) before a tip has been
  selected, it **SHOULD** label the displayed total as pre-tip so the buyer
  expects gratuity selection on the Business UI.

## Guidelines

### Platform

- **MUST NOT** send both `tip.selected_option_id` and `tip.custom_amount`, and
  **MUST** render the tip from the `type: "tip"` entry in `totals[]`.
- Because the tip can change up to the moment of completion, **MUST** present
  the final `totals[]` — including `type: "tip"` — for buyer confirmation
  before submitting payment.
- When handing off via `continue_url` before a tip has been selected,
  **SHOULD** label the displayed total as pre-tip so the buyer expects gratuity
  selection on the Business UI.

### Business

- **MUST** include `display_text` on `type: "tip"` totals and report any
  non-zero tip in `totals[]`.
- **MUST** compute percentage `tip.options[]` against the pre-discount
  `subtotal` entry in `totals[]` and recompute percentage tips when the basket
  or fulfillment changes.
- When a fulfillment switch replaces `tip.options[]` and invalidates a prior
  `selected_option_id`, **MUST** clear `selected_option_id` (returning `tip` to
  `Unset` state) and **SHOULD** surface a `notice` warning.
- **MAY** require an explicit choice before completion; where it does, a `custom_amount`
  of `0` **MUST** satisfy that requirement.

## Schema

### Entities

#### Tip

{{ schema_fields('food/types/tip_resp', 'food/extensions/tip') }}

#### Tip Option

{{ schema_fields('food/types/tip_option_resp', 'food/extensions/tip') }}

## Example

=== "Business Suggests Options"

    <!-- ucp:example schema=food/types/tip op=read -->
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

    <!-- ucp:example schema=food/tip def=dev.ucp.food.checkout op=update direction=request -->
    ```json
    {
      "food_establishment": { "id": "est_luigis_01" },
      "line_items": [
        {
          "id": "li_1",
          "quantity": 2,
          "dish": { "id": "dish_margherita_12" }
        }
      ],
      "tip": {
        "selected_option_id": "tip_18"
      }
    }
    ```

=== "Platform Sends a Custom Amount"

    <!-- ucp:example schema=food/tip def=dev.ucp.food.checkout op=update direction=request -->
    ```json
    {
      "food_establishment": { "id": "est_luigis_01" },
      "line_items": [
        {
          "id": "li_1",
          "quantity": 2,
          "dish": { "id": "dish_margherita_12" }
        }
      ],
      "tip": {
        "custom_amount": 700
      }
    }
    ```
