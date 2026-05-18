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

The Return Extension allows businesses to communicate the conditions, methods,
timelines, and costs associated with returning physical items directly to the
platform and the buyer, mirroring real-world commerce requirements.

By exposing the return policy natively in the UCP schema, AI agents and
platforms can intelligently answer user queries like _"Can I return this
in-store?"_ or _"How many days do I have to return this?"_ without forcing the
user to leave the platform to hunt for a policy on the merchant's website.

This extension adds a `return_policies` field to Checkout containing:

- `return_policies[]` — conditions governed by the merchant for specific items.
    - `return_days` — the number of days allowed for the return.
    - `methods[]` — permitted physical methods (in-store, by-mail, etc.)
        - `fee` — the cost structure for that specific method.

**Mental model:**

- `return_policies[0]` Standard Apparel
    - `line_item_ids` 👕👖
    - `return_days` = 30 Days 🗓️
    - `methods[0]` In-Store 🏬
        - `fee` = `free` ✅
    - `methods[1]` By Mail 📦
        - `fee` = `fixed_fee` $5.00 💸
- `return_policies[1]` Non-Returnable / Final Sale
    - `line_item_ids` ⌚
    - `exchanges_allowed` = `false`

## Discovery

Businesses advertise return policy support in their profile by registering the
extension under `capabilities`:

```json
{
    "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
            "dev.ucp.shopping.return": [
                {
                    "version": "{{ ucp_version }}",
                    "extends": ["dev.ucp.shopping.checkout"],
                    "spec": "https://ucp.dev/{{ ucp_version }}/specification/return",
                    "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/return.json"
                }
            ]
        }
    }
}
```

Platforms SHOULD check for this capability before attempting to render
`return_policies` from a checkout response.

## Schema

Return policies apply to physical items in a checkout session. Items not
governed by a specific policy (e.g., digital services) may be omitted or covered
by a default policy.

### Properties

{{ extension_fields('return', 'return') }}

### Entities

#### Return Policy

{{ extension_schema_fields('return.json#/$defs/return_policy', 'return') }}

#### Return Method

{{ extension_schema_fields('return.json#/$defs/return_method', 'return') }}

#### Return Fee

{{ extension_schema_fields('return.json#/$defs/return_fee', 'return') }}

## Rendering

Return policies are designed for proactive disclosures by the merchant.
Platforms use these fields to provide transparency about the logistical
requirements of a purchase before completion.

### Human-Readable Fields

| Location            | Field          | Required | Purpose                                       |
| ------------------- | -------------- | -------- | --------------------------------------------- |
| `return_policy`     | `return_days`  | No       | Quantitative window for the return.           |
| `return_method.fee` | `display_text` | No       | Context for the fee (e.g., "Restocking Fee"). |
| `return_method.fee` | `amount`       | No       | Price in minor units for fixed fees.          |

### Business Responsibilities

**For `return_days`:**

- **MUST** accurately reflect the merchant's legal and commercial return window
  duration.

**For `return_method.fee`:**

- **SHOULD** use `display_text` to explain the nature of the fee (e.g., "Prepaid
  Label", "Restocking Fee").
- **MUST** provide `amount` if the type is `fixed_fee`.

### Platform Responsibilities

Platforms **SHOULD** use return policies to answer buyer questions and provide
assurance:

- Surface "Final Sale" warnings early in the checkout flow.
- Answer specific questions like "Is return shipping free?" by inspecting the
  `by_mail` method fee.
- Use `return_days` to calculate and display the specific return deadline based
  on the delivery date.

## Examples

### Mixed Cart

In this example, apparel items have a standard window, while a custom item is
final sale.

```json
{
    "return_policies": [
        {
            "line_item_ids": ["shirt", "pants"],
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
            "line_item_ids": ["custom_engraved_watch"],
            "exchanges_allowed": false
        }
    ]
}
```
