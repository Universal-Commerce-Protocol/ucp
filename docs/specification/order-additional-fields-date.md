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

# Order Date Additional Fields Extension

## Overview

Order Date Additional Fields is the order read projection of the
[Date Additional Fields Extension](additional-fields-date.md). It lets order
additional fields use the `date` input type identifier while keeping the order
shape compact.

Date order additional fields do not include checkout range hints such as `min`
or `max`.

**Key features:**

- Surface date input type identifiers on order additional fields
- Exclude checkout validation hints from order read responses

**Dependencies:**

- Order Additional Fields Extension

## Discovery

For order read responses, the base additional fields capability extends order
and the date capability extends the base additional fields capability:

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
      ],
      "dev.ucp.shopping.additional_fields_date": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.additional_fields",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/order-additional-fields-date",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/additional_fields_date.json"
        }
      ]
    }
  }
}
```

Platforms SHOULD check that both the base and date capabilities are active
before interpreting date order additional field input type identifiers.

## Operations

This extension does not change order read behavior. It only broadens the
additional field `input.type` identifiers defined by
[Order Additional Fields](order-additional-fields.md).

## Examples

### Order with a date additional field value

```json
{
  "additional_fields": [
    {
      "key": "delivery_date",
      "label": "Preferred Delivery Date",
      "description": "Preferred delivery date.",
      "input": { "type": "date" },
      "value": "2026-04-01"
    }
  ]
}
```
