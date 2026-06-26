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

For order read responses, the capability extends order:

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

Platforms SHOULD check that order is extended before expecting additional fields
on order read responses.

## Schema

When this capability is active for order, order is extended with an
`additional_fields` array containing compact read-only field summaries.

### Order Additional Field

{{ extension_schema_fields('additional_fields.json#/$defs/order_additional_field', 'order-additional-fields') }}

### Order Additional Field Input

{{ extension_schema_fields('additional_fields.json#/$defs/order_additional_field_input', 'order-additional-fields') }}

## Operations

Order additional fields are returned through order read responses and order
event payloads. They are read-only:

- Businesses MAY return `additional_fields` with values captured during checkout
- Platforms do not update order additional fields through order operations
- Each entry contains only `key`, `label`, `label_content_type`, `description`,
    `input`, and `value`
- Checkout collection details such as `required` and validation hints are not
    included

## Examples

### Order with additional field values

```json
{
  "additional_fields": [
    {
      "key": "po_number",
      "label": "Purchase Order Number",
      "description": "Required for B2B orders.",
      "input": { "type": "text" },
      "value": "PO-2026-001234"
    },
    {
      "key": "engraving",
      "label": "Engraving Instructions",
      "description": "Custom engraving text.",
      "input": { "type": "text" },
      "value": null
    }
  ]
}
```
