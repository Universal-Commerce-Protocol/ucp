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

# Choice Additional Fields Extension

## Overview

Choice Additional Fields extends
[`dev.ucp.shopping.additional_fields`](additional-fields.md) with `choice`
input semantics and selectable `options[]` for checkout additional fields.

**Key features:**

- Add fields whose submitted value must be selected from `options[]`
- Let businesses provide labels for each submitted option value
- Keep choice support independently negotiable from other additional field
    types

**Dependencies:**

- Additional Fields Extension

## Discovery

Businesses advertise choice additional field support by extending the base
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
      "dev.ucp.shopping.additional_fields_choice": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.additional_fields",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/additional-fields-choice",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/additional_fields_choice.json"
        }
      ]
    }
  }
}
```

Platforms SHOULD check that both the base and choice capabilities are active
before submitting choice additional field values. The order read projection is
documented in
[Order Choice Additional Fields](order-additional-fields-choice.md).

## Schema

### Choice Input

{{ extension_schema_fields('additional_fields_choice.json#/$defs/choice_input', 'additional-fields-choice') }}

### Choice Option

{{ extension_schema_fields('additional_fields_choice.json#/$defs/choice_option', 'additional-fields-choice') }}

## Operations

This extension does not change checkout operations. Choice additional field
values use the create and update behavior defined by the base
[Additional Fields Extension](additional-fields.md).

## Examples

### Checkout with a choice additional field

=== "Response"

    ```json
    {
      "additional_fields": [
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
        }
      ]
    }
    ```

### Submitting a choice additional field value

=== "Request"

    ```json
    {
      "additional_fields": [
        { "key": "gift_wrap_type", "value": "birthday" }
      ]
    }
    ```
