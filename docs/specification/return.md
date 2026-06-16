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

By exposing the return policy natively in the UCP schema, platforms can
intelligently answer user queries like _"Can I return this
in-store?"_ or _"How many days do I have to return this?"_ without forcing the
user to leave the platform to hunt for a policy on the merchant's website.

This extension adds a `return_policies` registry to Checkout and a reference on line items:

- `line_items[].return_policy_id` — reference to the policy that applies to this item.
- `return_policies` — map of policy definitions keyed by ID, containing:
    - `return_period_in_days` — the number of days allowed for the return.
    - `supported_resolutions[]` — allowed outcomes (refund, exchange, etc.).
    - `methods[]` — permitted physical methods (in-store, by-mail, etc.)
        - `fee` — the cost structure for that specific method.
    - `reason` — human-readable explanation of why this policy applies.
    - `policy_url` — URL to the merchant's full return policy document.

### Relationship to Other Extensions

The Return Extension is independent of the Fulfillment Extension. Businesses MAY use information from `fulfillment` to compute return options (e.g., in-store return locations may correlate with fulfillment retail locations), but this extension does NOT model that relationship. Platforms MUST NOT assume any structural correlation between return methods and fulfillment methods.

### Scope and Future Directions

- **Pre-Purchase Disclosure Only**: This extension addresses pre-purchase disclosure of return policy only. Post-purchase return initiation, label generation, refund processing, and exchange execution are out of scope. A future `dev.ucp.shopping.return_action` extension may address these workflows; implementers MUST NOT extend this schema for those purposes.
- **Product-Level Returns**: A return policy is fundamentally a property of a product (or its category), not a property of a checkout. A separate Product or Catalog capability could expose return policies at the catalog level in the future. For v1, checkout-time exposure is used for simplicity.

**Mental model:**

- **Line Items:**
    - 👕 (Shirt) -> `return_policy_id` = `"rp_standard"`
    - 👖 (Pants) -> `return_policy_id` = `"rp_standard"`
    - ⌚ (Watch) -> `return_policy_id` = `"rp_final_sale"`
- **Return Policies Registry:**
    - `"rp_standard"`:
        - `return_period_in_days` = 30 Days 🗓️
        - `supported_resolutions` = `["original_payment_method", "exchange"]`
        - `methods`: In-Store (free) 🏬, By Mail ($5.00) 📦
    - `"rp_final_sale"`:
        - `supported_resolutions` = `[]` (Final Sale)
        - `reason` = "Clearance items are non-returnable." 🚫

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

| Location            | Field                   | Required | Purpose                                            |
| ------------------- | ----------------------- | -------- | -------------------------------------------------- |
| `return_policy`     | `return_period_in_days` | No       | Quantitative window for the return.                |
| `return_policy`     | `reason`                | No       | Human-readable explanation of policy application.  |
| `return_policy`     | `policy_url`            | No       | URL to the merchant's full return policy document. |
| `return_policy`     | `supported_resolutions` | No       | Allowed outcomes (refund, exchange, etc.).         |
| `return_method.fee` | `display_text`          | No       | Context for the fee (e.g., "Restocking Fee").      |
| `return_method.fee` | `amount`                | No       | Price in minor units for fixed fees.               |

### Business Responsibilities

**For Policy References:**

- **MUST** ensure every `return_policy_id` on a line item resolves to a key present in the top-level `return_policies` registry.

**For Policy Locking:**

- **MUST** honor the return policy that was in effect at the time of order placement; that policy MUST be sourced from the Order resource (when available) rather than recomputed from current merchant rules. The return policy returned at checkout response time is the policy in effect for the buyer at that moment.

**For `return_period_in_days`:**

- **MUST** accurately reflect the merchant's legal and commercial return window
  duration.

**For `supported_resolutions`:**

- **MUST** list all resolutions supported by the merchant (e.g. if exchange is
  supported it must be explicitly listed).

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
- Use `return_period_in_days` to calculate and display the specific return
  deadline based on the delivery date.

**For Partial Quantity Returns:**

- **SHOULD** assume return policies apply to individual units within a line item. Unless specified otherwise (e.g., for bundled items), any subset of quantities is subject to the same return policy.

**For Absent Policy Data:**

- **MUST NOT** infer items are non-returnable if the Return capability is advertised in discovery but `return_policies` is absent or empty in a checkout response. Platforms SHOULD fall back to general merchant return info (e.g., via the merchant's profile URL).
- **MUST** treat unresolved policy references (`return_policy_id` without a matching key in `return_policies`) as having no stated return policy (per the Absent Policy Data rule) and **MUST NOT** infer the item is non-returnable.

**Interpretation of Policy States:**

Platforms MUST interpret combinations of `methods` and `return_period_in_days` as follows:

- `methods` absent or empty (`[]`): Treat as "no return methods supported" (i.e., non-returnable/final sale).
- `return_period_in_days` is `0`: Treat as "non-returnable" (final sale).
- `return_period_in_days` absent, but `methods` present: Treat as "no time limit on returns".
- `return_period_in_days` present, but `methods` absent/empty: Ambiguous. Interpret as returnable, but client/buyer must arrange their own return shipment, or consult the full policy link if provided.

## Examples

### Mixed Cart

In this example, apparel items reference a standard policy, while a custom item references a final sale policy with a reason.

```json
{
  "line_items": [
    {
      "id": "shirt",
      "return_policy_id": "rp_standard"
    },
    {
      "id": "pants",
      "return_policy_id": "rp_standard"
    },
    {
      "id": "custom_engraved_watch",
      "return_policy_id": "rp_final_sale"
    }
  ],
  "return_policies": {
    "rp_standard": {
      "return_period_in_days": 30,
      "policy_url": "https://example.com/returns",
      "supported_resolutions": ["original_payment_method", "exchange"],
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
    "rp_final_sale": {
      "supported_resolutions": [],
      "reason": "Custom engraved items are final sale."
    }
  }
}
```
