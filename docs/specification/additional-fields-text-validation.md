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

# Text Validation Additional Fields Extension

## Overview

Text Validation Additional Fields extends
[`dev.ucp.shopping.additional_fields`](additional-fields.md) with validation
hints for `text` checkout additional fields.

The base Additional Fields extension defines the `text` type and the
`multiline` hint. This extension adds validation hints for that existing text
type; it does not introduce a new input type identifier.

**Key features:**

- Add text validation hints: `min_length`, `max_length`, and `pattern`
- Keep text validation independently negotiable from other additional field
    types

**Dependencies:**

- Additional Fields Extension

## Discovery

Businesses advertise text validation support by extending the base additional
fields capability:

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
      "dev.ucp.shopping.additional_fields_text_validation": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.additional_fields",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/additional-fields-text-validation",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/additional_fields_text_validation.json"
        }
      ]
    }
  }
}
```

Platforms SHOULD check that both the base and text validation capabilities are
active before interpreting or applying text validation hints.

## Schema

### Text Validation Input

{{ extension_schema_fields('additional_fields_text_validation.json#/$defs/text_validation_input', 'additional-fields-text-validation') }}

## Operations

This extension does not change checkout operations. Text validation additional
field values use the create and update behavior defined by the base
[Additional Fields Extension](additional-fields.md).

## Examples

### Checkout with a validated text additional field

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
          "key": "engraving",
          "label": "Engraving Text",
          "input": { "type": "text", "max_length": 20 },
          "required": false,
          "description": "Custom engraving text.",
          "value": null
        }
      ]
    }
    ```

### Submitting a validated text additional field value

=== "Request"

    ```json
    {
      "additional_fields": [
        { "key": "po_number", "value": "PO-2026-001234" },
        { "key": "engraving", "value": "Happy Birthday Sarah" }
      ]
    }
    ```
