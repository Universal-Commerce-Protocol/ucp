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

# Return Extension

## Overview

The Return Extension allows businesses to communicate the conditions, methods, timelines, and costs associated with returning physical items directly to the platform and the buyer, mirroring real-world commerce requirements.

By exposing the return policy natively in the UCP schema, AI agents and platforms can intelligently answer user queries like *"Can I return this in-store?"* or *"How many days do I have to return this?"* without forcing the user to leave the platform to hunt for a policy on the merchant's website.

This extension adds a `return_policies` field to Checkout containing:

* `return_policies[]` — conditions governed by the merchant for specific items.
    * `window_type` — the category of return window (finite, lifetime, final sale, etc.)
    * `return_days` — the number of days in the window.
    * `methods[]` — permitted physical methods (in-store, by-mail, etc.)
        * `fee` — the cost structure for that specific method.

**Mental model:**

* `return_policies[0]` Standard Apparel
    * `line_item_ids` 👕👖
    * `window_type` = `finite_window` 🗓️ 30 Days
    * `methods[0]` In-Store 🏬
        * `fee` = `free` ✅
    * `methods[1]` By Mail 📦
        * `fee` = `fixed_fee` $5.00 💸
* `return_policies[1]` Final Sale
    * `line_item_ids` ⌚
    * `window_type` = `final_sale` 🚫
    * `exchanges_allowed` = `false`

## Schema

Return policies apply to physical items in a checkout session. Items not governed by a specific policy (e.g., digital services) may be omitted or covered by a default policy.

### Properties

{{ extension_fields('return', 'return_policies') }}

### Entities

#### Return Policy

{{ schema_fields('types/return_policy', 'return') }}

#### Return Method

{{ schema_fields('types/return_method', 'return') }}

#### Return Fee

{{ schema_fields('types/return_fee', 'return') }}

## Rendering

Return policies are designed for proactive disclosures by the merchant. Platforms use these fields to provide transparency about the logistical requirements of a purchase before completion.

### Human-Readable Fields

| Location               | Field          | Required | Purpose                                             |
| ---------------------- | -------------- | -------- | --------------------------------------------------- |
| `return_policy`        | `return_days`  | No       | Quantitative window for the return.                 |
| `return_method.fee`    | `display_text` | No       | Context for the fee (e.g., "Restocking Fee").       |
| `return_method.fee`    | `amount`       | No       | Price in minor units for fixed fees.                |

### Business Responsibilities

**For `window_type`:**

* **MUST** accurately reflect the merchant's legal and commercial policy.
* **MUST** provide `return_days` if the type is `finite_window`.

**For `return_method.fee`:**

* **SHOULD** use `display_text` to explain the nature of the fee (e.g., "Prepaid Label", "Restocking Fee").
* **MUST** provide `amount` if the type is `fixed_fee`.

### Platform Responsibilities

Platforms **SHOULD** use return policies to answer buyer questions and provide assurance:

* Surface "Final Sale" warnings early in the checkout flow.
* Answer specific questions like "Is return shipping free?" by inspecting the `by_mail` method fee.
* Use `return_days` to calculate and display the specific return deadline based on the delivery date.

## Examples

### Mixed Cart

In this example, apparel items have a standard window, while a custom item is final sale.

```json
{
  "return_policies": [
    {
      "id": "rp_apparel",
      "line_item_ids": ["shirt", "pants"],
      "window_type": "finite_window",
      "return_days": 30,
      "exchanges_allowed": true,
      "methods": [
        {
          "type": "in_store",
          "fee": {
            "type": "free",
            "display_text": "Free In-Store Return"
          }
        },
        {
          "type": "by_mail",
          "fee": {
            "type": "fixed_fee",
            "amount": 500,
            "display_text": "Return Shipping Fee"
          }
        }
      ]
    },
    {
      "id": "rp_final_sale",
      "line_item_ids": ["custom_engraved_watch"],
      "window_type": "final_sale",
      "exchanges_allowed": false
    }
  ]
}
```
