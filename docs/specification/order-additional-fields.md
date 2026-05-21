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

# Order Additional Fields Extension

## Overview

Order Additional Fields is the order read projection of the
[Additional Fields Extension](additional-fields.md). Checkout uses additional
fields to collect values; order uses compact read-only summaries of the values
captured during checkout.

**Key features:**

- Receive captured additional field values on order read responses
- Preserve field context with `key`, `label`, `label_content_type`,
    `description`, and `input.type`
- Exclude checkout-only collection details such as `required` and validation
    hints

**Dependencies:**

- Order Capability

## Discovery

Businesses advertise additional field support in their profile. For order read
responses, the capability extends order:

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.additional_fields": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.order",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/order-additional-fields",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/additional_fields.json"
        }
      ]
    }
  }
}
```

Businesses MAY advertise additional field support for checkout only, order only,
or both. Platforms SHOULD check which resources are extended before expecting
additional fields on order read responses.

## Schema

When this capability is active for order, order is extended with an
`additional_fields` array containing compact read-only field summaries.

### Order Additional Field

{{ extension_schema_fields('additional_fields.json#/$defs/order_additional_field', 'order-additional-fields') }}

### Order Additional Field Input

{{ extension_schema_fields('additional_fields.json#/$defs/order_additional_field_input', 'order-additional-fields') }}

### Order Choice Input

{{ extension_schema_fields('additional_fields.json#/$defs/order_choice_input', 'order-additional-fields') }}

## Operations

Order additional fields are returned through order read responses and order
event payloads. They are read-only:

- Businesses MAY return `additional_fields` with values captured during checkout
- Platforms do not update order additional fields through order operations
- Each entry contains only `key`, `label`, `label_content_type`, `description`,
    `input`, and `value`
- Checkout collection details such as `required` and validation hints are not
    included
- Choice fields include `input.value_label` for the captured value label

## Examples

### Order with additional field values

```json
{
  "additional_fields": [
    {
      "key": "po_number",
      "label": "Purchase Order Number",
      "description": "Required for B2B orders. Must match format PO-<digits>.",
      "input": { "type": "text" },
      "value": "PO-2026-001234"
    },
    {
      "key": "gift_wrap",
      "label": "Gift Wrap",
      "description": "Add gift wrapping for $5",
      "input": { "type": "boolean" },
      "value": "true"
    },
    {
      "key": "gift_wrap_type",
      "label": "Gift Wrap Type",
      "description": "Gift wrap style selected for the order.",
      "input": {
        "type": "choice",
        "value_label": "Birthday"
      },
      "value": "birthday"
    },
    {
      "key": "delivery_date",
      "label": "Preferred Delivery Date",
      "description": "Preferred delivery date.",
      "input": { "type": "date" },
      "value": "2026-04-01"
    },
    {
      "key": "special_instructions",
      "label": "Special Instructions",
      "description": "Any special delivery or handling instructions",
      "input": { "type": "text" },
      "value": null
    }
  ]
}
```
