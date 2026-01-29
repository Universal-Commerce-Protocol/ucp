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

The additional fields extension enables businesses to request checkout inputs
that are not covered by the core schema, and to bind those inputs to cart,
buyer, or fulfillment data via JSONPath.

**Key features**

- Declare required and optional additional fields with typed UI controls
- Map each field to cart, buyer, or fulfillment data using JSONPath
- Receive input in a consistent structure keyed by field `key`
- Surface validation via `messages[]` with JSONPath to the field value

**Dependencies**

- Checkout capability

## Discovery

Businesses advertise additional fields support in their profile:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": {
      "dev.ucp.shopping.additional_fields": [
        {
          "version": "2026-01-11",
          "extends": "dev.ucp.shopping.checkout",
          "spec": "https://ucp.dev/specification/additional-fields",
          "schema": "https://ucp.dev/schemas/shopping/additional_fields.json"
        }
      ]
    }
  }
}
```

## Schema

When this extension is active, checkout gains an `additional_fields` object with
field definitions and buyer-provided values.

### Additional Fields

{{ extension_schema_fields('additional_fields.json#/$defs/additional_fields', 'additional-fields') }}

### Field Definition

{{ extension_schema_fields('additional_fields.json#/$defs/additional_field', 'additional-fields') }}

### Validation Hints

{{ extension_schema_fields('additional_fields.json#/$defs/validation_hints', 'additional-fields') }}

## Input types and values

- `single_line_text` and `multi_line_text`: string values. Platforms **SHOULD**
  honor `min_length`, `max_length`, and `pattern` hints when rendering input.
- `checkbox`: boolean values.
- `date`: RFC 3339 full-date string (e.g., `2026-02-14`).
- `date_time`: RFC 3339 date-time string with offset (e.g.,
  `2026-02-14T15:04:05Z`).
- `default_value` must match the field's input type.

## Validation

- Businesses validate submitted values and return issues in `messages[]` using
  `type: "error"` with `severity: "recoverable"` and `path` set to the field
  value (e.g., `$.additional_fields.values.delivery_date`).
- No new message type is introduced; `type: "error"` + `severity` communicates
  that the issue is blocking until resolved.
- Suggested error codes: `additional_field_required`, `additional_field_invalid`
  (type or format mismatch), `additional_field_not_supported` (key unknown).
- The `validation_hints` object is a **hint** for platforms to improve UX;
  businesses remain the source of truth and enforce rules via `messages[]`.

## Operations

- **Create/Update Checkout:** Platforms send buyer input in
  `additional_fields.values`. Submitting the object replaces previously sent
  values. Send an empty object to clear all additional fields.
- **Responses:** Businesses return `additional_fields.fields` to describe what
  is supported, and may echo `additional_fields.values` received from the
  platform.
- **Mapping:** `path` is a JSONPath from the checkout root to the data the field
  influences (e.g., buyer attributes, line items, fulfillment options). It
  allows platforms to render the field near its context while keeping the core
  schema unchanged.

## Example

```json
{
  "additional_fields": {
    "fields": [
      {
        "key": "po_number",
        "label": "PO number",
        "description": "Optional purchase order for your records",
        "type": "single_line_text",
        "path": "$.buyer",
        "validation_hints": {
          "max_length": 24
        }
      },
      {
        "key": "gift_wrap",
        "label": "Gift wrap",
        "type": "checkbox",
        "default_value": false,
        "path": "$.line_items[?(@.id=='shirt')]"
      },
      {
        "key": "delivery_date",
        "label": "Delivery date",
        "type": "date",
        "required": true,
        "path": "$.fulfillment.methods[0].groups[0]",
        "validation_hints": {
          "min_date": "2026-02-01"
        }
      },
      {
        "key": "gift_message",
        "label": "Gift message",
        "type": "multi_line_text",
        "path": "$.line_items[?(@.id=='gift_box')]"
      },
      {
        "key": "agree_to_terms",
        "label": "Agree to terms",
        "type": "checkbox",
        "required": true,
        "path": "$"
      }
    ],
    "values": {
      "po_number": "PO-45822",
      "gift_wrap": true,
      "delivery_date": "2026-02-05",
      "gift_message": "Happy birthday, Alex!",
      "agree_to_terms": true
    }
  },
  "messages": [
    {
      "type": "error",
      "code": "additional_field_required",
      "severity": "recoverable",
      "path": "$.additional_fields.values.delivery_date",
      "content": "Select an eligible delivery date."
    }
  ]
}
```

Use cases include buyer birthdays, order notes, line-item personalization
(e.g., monogramming), delivery dates, gift wrap and gift messages, PO numbers,
tax IDs, and terms acceptance.
