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

# Boolean Additional Fields Extension

## Overview

Boolean Additional Fields extends
[`dev.ucp.shopping.additional_fields`](additional-fields.md) with `boolean`
input semantics for checkout additional fields.

**Key features:**

- Add boolean fields represented as `"true"` or `"false"`
- Keep boolean support independently negotiable from other additional field
    types

**Dependencies:**

- Additional Fields Extension

## Discovery

Businesses advertise boolean additional field support by extending the base
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
      "dev.ucp.shopping.additional_fields_boolean": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.additional_fields",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/additional-fields-boolean",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/additional_fields_boolean.json"
        }
      ]
    }
  }
}
```

Platforms SHOULD check that both the base and boolean capabilities are active
before submitting boolean additional field values. The order read projection is
documented in
[Order Boolean Additional Fields](order-additional-fields-boolean.md).

## Schema

### Boolean Input

{{ extension_schema_fields('additional_fields_boolean.json#/$defs/boolean_input', 'additional-fields-boolean') }}

## Operations

This extension does not change checkout operations. Boolean additional field
values use the create and update behavior defined by the base
[Additional Fields Extension](additional-fields.md).

## Examples

### Checkout with a boolean additional field

=== "Response"

    ```json
    {
      "additional_fields": [
        {
          "key": "gift_wrap",
          "label": "Gift Wrap",
          "input": { "type": "boolean" },
          "required": false,
          "description": "Add gift wrapping for $5",
          "value": null
        }
      ]
    }
    ```

### Submitting a boolean additional field value

=== "Request"

    ```json
    {
      "additional_fields": [
        { "key": "gift_wrap", "value": "true" }
      ]
    }
    ```
