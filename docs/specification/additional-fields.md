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

# Additional Fields Extension

## Overview

Additional Fields extension allows businesses to indicate that they need extra
checkout data collection fields, and specifies how field definitions and
submitted values are shared between the platform and the business.

The base extension defines the additional field envelope and `text` input
semantics, including the `multiline` hint for multi-line text. Additional input
types and validation hints are defined by the
[Advanced Additional Fields Extension](additional-fields-advanced.md).

**Key features:**

- Receive business-defined required and optional text fields, including
    multi-line text fields
- Submit additional field values as `key` plus `value` entries
- Preserve extensibility through an open `input.type` vocabulary
- Invalid values communicated via `messages[]` with detailed error codes

**Dependencies:**

- Checkout Capability

## Discovery

Businesses advertise additional field support in their profile. For checkout
data collection, the capability extends checkout:

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
      ]
    }
  }
}
```

Platforms SHOULD check that checkout is extended before submitting additional
field values. The order read projection for captured values is documented in
[Order Additional Fields](order-additional-fields.md).

## Schema

When this capability is active for checkout, checkout is extended with an
`additional_fields` array containing field definitions and current values.

### Checkout Extension

{{ extension_fields('additional_fields', 'additional-fields') }}

### Additional Field

{{ extension_schema_fields('additional_fields.json#/$defs/additional_field', 'additional-fields') }}

## Input Type Details

Each field definition includes an `input` object with a required `type` string.
Platforms SHOULD respect the declared type. Platforms that do not recognize a
type SHOULD NOT render it as a different supported type, coerce it to text, or
collect a value unless a negotiated extension defines that type.

All non-null values are submitted as strings regardless of input type.

### Additional Field Input

{{ extension_schema_fields('additional_fields.json#/$defs/additional_field_input', 'additional-fields') }}

### Text Input

{{ extension_schema_fields('additional_fields.json#/$defs/text_input', 'additional-fields') }}

## Extensibility

The additional field envelope is independent from the input type vocabulary:

- `additional_fields[].input.type` is an open string, not a closed enum.
- The base extension defines only `text` semantics.
- Future UCP or vendor extensions can extend
    `dev.ucp.shopping.additional_fields` and introduce new type identifiers and
    hints without changing the field envelope.

For vendor-defined types, use the vendor namespace in the type identifier, for
example `com.example.file_upload`.

## Operations

Additional field values are submitted via standard checkout create and update
operations.

**Request behavior:**

- **Replacement semantics**: Submitting `additional_fields` replaces any
    previously submitted additional field values
- **Retain values**: Platforms must include each field value they want to keep
    in the replacement set
- **Clear values**: Omit a configured field from the replacement set, or send
    `"value": null` for that field key
- **Request format**: Platforms submit only `key` and `value` for each entry.
    Definition properties are ignored if present
- **Unknown values**: Entries whose `key` does not match a configured field are
    ignored by the business

**Response behavior:**

- `additional_fields` contains all configured fields with current values merged
    into each entry
- `value` is `null` for fields that have not been submitted or have been
    cleared by replacement
- Invalid values communicated via `messages[]` (see below)

## Invalid Values

When a submitted additional field value cannot be accepted, businesses
communicate this via the `messages[]` array:

```json
{
  "status": "incomplete",
  "messages": [
    {
      "type": "error",
      "severity": "recoverable",
      "code": "additional_field_invalid_value",
      "path": "$.additional_fields[?@.key=='po_number']",
      "content": "Purchase Order Number is required"
    }
  ]
}
```

> **Implementation guidance:** Required or invalid additional field values
> prevent checkout completion but can be corrected by the platform. Businesses
> SHOULD use `type: "error"` and `severity: "recoverable"` for these cases.

| Severity      | Scenario                                                      | Platform Action                           |
| :------------ | :------------------------------------------------------------ | :---------------------------------------- |
| `recoverable` | Value is missing, empty, or otherwise invalid                 | Resubmit with a corrected value via Update Checkout |

**Error codes for additional field validation:**

| Code                             | Description                                                 |
| :------------------------------- | :---------------------------------------------------------- |
| `additional_field_invalid_value` | Field value is missing, empty, or fails business validation |

## Examples

### Checkout with additional field definitions

When a checkout is created or updated, the business response includes the
additional fields it needs. Values are `null` until submitted or when cleared by
replacement.

=== "Response"

    ```json
    {
      "additional_fields": [
        {
          "key": "po_number",
          "label": "Purchase Order Number",
          "input": { "type": "text" },
          "required": true,
          "description": "Required for B2B orders.",
          "value": null
        },
        {
          "key": "engraving",
          "label": "Engraving Text",
          "input": { "type": "text" },
          "required": false,
          "description": "Custom engraving text.",
          "value": null
        },
        {
          "key": "special_instructions",
          "label": "Special Instructions",
          "input": { "type": "text", "multiline": true },
          "required": false,
          "description": "Any special delivery or handling instructions.",
          "value": null
        }
      ]
    }
    ```

### Submitting additional field values

The platform submits the full replacement set of additional field values it
wants to retain. Configured fields omitted from the request have no submitted
value after the update.

=== "Request"

    ```json
    {
      "additional_fields": [
        { "key": "po_number", "value": "PO-2026-001234" },
        { "key": "engraving", "value": "Happy Birthday Sarah" },
        {
          "key": "special_instructions",
          "value": "Please leave at reception.\nRing buzzer #4."
        }
      ]
    }
    ```

=== "Response"

    ```json
    {
      "additional_fields": [
        {
          "key": "po_number",
          "label": "Purchase Order Number",
          "input": { "type": "text" },
          "required": true,
          "description": "Required for B2B orders.",
          "value": "PO-2026-001234"
        },
        {
          "key": "engraving",
          "label": "Engraving Text",
          "input": { "type": "text" },
          "required": false,
          "description": "Custom engraving text.",
          "value": "Happy Birthday Sarah"
        },
        {
          "key": "special_instructions",
          "label": "Special Instructions",
          "input": { "type": "text", "multiline": true },
          "required": false,
          "description": "Any special delivery or handling instructions.",
          "value": "Please leave at reception.\nRing buzzer #4."
        }
      ]
    }
    ```

### Clearing a value

Because `additional_fields` uses replacement semantics, the platform includes
the values it wants to retain. It can clear a field by sending `null` for that
key, or by omitting the configured field from the replacement set.

=== "Request"

    ```json
    {
      "additional_fields": [
        { "key": "po_number", "value": "PO-2026-001234" },
        { "key": "engraving", "value": null }
      ]
    }
    ```

=== "Response"

    ```json
    {
      "additional_fields": [
        {
          "key": "po_number",
          "label": "Purchase Order Number",
          "input": { "type": "text" },
          "required": true,
          "description": "Required for B2B orders.",
          "value": "PO-2026-001234"
        },
        {
          "key": "engraving",
          "label": "Engraving Text",
          "input": { "type": "text" },
          "required": false,
          "description": "Custom engraving text.",
          "value": null
        },
        {
          "key": "special_instructions",
          "label": "Special Instructions",
          "input": { "type": "text", "multiline": true },
          "required": false,
          "description": "Any special delivery or handling instructions.",
          "value": null
        }
      ]
    }
    ```
