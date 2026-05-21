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

# Advanced Additional Fields Extension

## Overview

Advanced Additional Fields extension allows businesses to use additional input
types and validation hints for checkout additional fields.

This extension extends
[`dev.ucp.shopping.additional_fields`](additional-fields.md). The base
extension defines the field envelope, the `text` type, and the `multiline`
hint for text. This extension adds validation hints for `text` and defines
`boolean`, `date`, and `choice`.

**Key features:**

- Add text validation hints: `min_length`, `max_length`, and `pattern`
- Add boolean fields represented as `"true"` or `"false"`
- Add date fields with optional `min` and `max` bounds
- Add choice fields with selectable `options[]`

**Dependencies:**

- Additional Fields Extension

## Discovery

Businesses advertise advanced additional field support in their profile. The
advanced capability extends the base additional fields capability:

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.additional_fields": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.checkout",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/additional-fields",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/additional_fields.json"
        }
      ],
      "dev.ucp.shopping.additional_fields_advanced": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.additional_fields",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/additional-fields-advanced",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/additional_fields_advanced.json"
        }
      ]
    }
  }
}
```

Platforms SHOULD check that both the base and advanced capabilities are active
before submitting advanced additional field values. If the advanced capability
is not negotiated, businesses SHOULD only send `text` fields defined by the base
extension. The order read projection for advanced type identifiers is documented
in [Order Advanced Additional Fields](order-additional-fields-advanced.md).

## Type Additions

The base Additional Fields extension defines the shared `input` envelope and
value submission rules. This extension adds the following type-specific
semantics:

| Type      | What it adds                              | Example Value  |
| :-------- | :---------------------------------------- | :------------- |
| `text`    | Text validation hints                     | `"PO-12345"`   |
| `boolean` | Boolean semantics represented as strings | `"true"`       |
| `date`    | Calendar date semantics and date bounds  | `"2026-03-15"` |
| `choice`  | Select-from-list semantics and `options[]` | `"birthday"` |

### Text Input

{{ extension_schema_fields('additional_fields_advanced.json#/$defs/text_input', 'additional-fields-advanced') }}

### Boolean Input

{{ extension_schema_fields('additional_fields_advanced.json#/$defs/boolean_input', 'additional-fields-advanced') }}

### Date Input

{{ extension_schema_fields('additional_fields_advanced.json#/$defs/date_input', 'additional-fields-advanced') }}

### Choice Input

{{ extension_schema_fields('additional_fields_advanced.json#/$defs/choice_input', 'additional-fields-advanced') }}

### Choice Option

{{ extension_schema_fields('additional_fields_advanced.json#/$defs/choice_option', 'additional-fields-advanced') }}

## Operations

This extension does not change checkout operations. Advanced additional field
values use the create and update behavior defined by the base
[Additional Fields Extension](additional-fields.md).

## Examples

### Checkout with advanced additional field definitions

=== "Response"

    ```json
    {
      "additional_fields": [
        {
          "key": "po_number",
          "label": "Purchase Order Number",
          "input": { "type": "text", "pattern": "^PO-\\d+$" },
          "required": true,
          "description": "Required for B2B orders. Must match format PO-<digits>.",
          "value": null
        },
        {
          "key": "gift_wrap",
          "label": "Gift Wrap",
          "input": { "type": "boolean" },
          "required": false,
          "description": "Add gift wrapping for $5",
          "value": null
        },
        {
          "key": "gift_wrap_type",
          "label": "Gift Wrap Type",
          "input": {
            "type": "choice",
            "options": [
              { "value": "classic", "label": "Classic" },
              { "value": "birthday", "label": "Birthday" },
              { "value": "holiday", "label": "Holiday" }
            ]
          },
          "required": false,
          "description": "Select the gift wrap style",
          "value": null
        },
        {
          "key": "delivery_date",
          "label": "Preferred Delivery Date",
          "input": { "type": "date", "min": "2026-03-15", "max": "2026-12-31" },
          "required": false,
          "description": "Select a delivery date within the next 9 months",
          "value": null
        }
      ]
    }
    ```

### Submitting advanced additional field values

=== "Request"

    ```json
    {
      "additional_fields": [
        { "key": "po_number", "value": "PO-2026-001234" },
        { "key": "gift_wrap", "value": "true" },
        { "key": "gift_wrap_type", "value": "birthday" },
        { "key": "delivery_date", "value": "2026-04-01" }
      ]
    }
    ```
