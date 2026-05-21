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

# Order Advanced Additional Fields Extension

## Overview

Order Advanced Additional Fields is the order read projection of the
[Advanced Additional Fields Extension](additional-fields-advanced.md). It lets
order additional fields use the advanced input type identifiers negotiated for
checkout while keeping the order shape compact.

Advanced order additional fields do not include checkout validation hints such
as `pattern`, `min`, or `max`. Choice fields include `input.value_label` for
the captured value label.

**Key features:**

- Surface advanced input type identifiers on order additional fields
- Include captured choice value labels
- Exclude checkout validation hints from order read responses

**Dependencies:**

- Order Additional Fields Extension

## Discovery

For order read responses, the base additional fields capability extends order
and the advanced capability extends the base additional fields capability:

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
      "dev.ucp.shopping.additional_fields_advanced": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.additional_fields",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/order-additional-fields-advanced",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/additional_fields_advanced.json"
        }
      ]
    }
  }
}
```

Platforms SHOULD check that both the base and advanced capabilities are active
before interpreting advanced order additional field input type identifiers.

## Operations

This extension does not change order read behavior. It only broadens the
additional field `input.type` identifiers defined by
[Order Additional Fields](order-additional-fields.md).

## Examples

### Order with advanced additional field values

```json
{
  "additional_fields": [
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
    }
  ]
}
```
