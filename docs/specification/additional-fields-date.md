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

# Date Additional Fields Extension

## Overview

Date Additional Fields extends
[`dev.ucp.shopping.additional_fields`](additional-fields.md) with `date` input
semantics and optional date range hints for checkout additional fields.

**Key features:**

- Add calendar date fields represented as `YYYY-MM-DD` strings
- Add optional `min` and `max` date bounds
- Keep date support independently negotiable from other additional field types

**Dependencies:**

- Additional Fields Extension

## Discovery

Businesses advertise date additional field support by extending the base
additional fields capability:

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
      "dev.ucp.shopping.additional_fields_date": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.additional_fields",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/additional-fields-date",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/additional_fields_date.json"
        }
      ]
    }
  }
}
```

Platforms SHOULD check that both the base and date capabilities are active
before submitting date additional field values. The order read projection is
documented in [Order Date Additional Fields](order-additional-fields-date.md).

## Schema

### Date Input

{{ extension_schema_fields('additional_fields_date.json#/$defs/date_input', 'additional-fields-date') }}

## Operations

This extension does not change checkout operations. Date additional field
values use the create and update behavior defined by the base
[Additional Fields Extension](additional-fields.md).

## Examples

### Checkout with a date additional field

=== "Response"

    ```json
    {
      "additional_fields": [
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

### Submitting a date additional field value

=== "Request"

    ```json
    {
      "additional_fields": [
        { "key": "delivery_date", "value": "2026-04-01" }
      ]
    }
    ```
