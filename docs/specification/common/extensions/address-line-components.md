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

# Address Line Components Extension

## Overview

A postal address carries its street information in two flat lines,
`street_address` and `extended_address`. Many countries write those lines from
named parts — Brazil separates the street name, the building number and the
*bairro*; Indonesia a *kecamatan* and a *kelurahan*; Saudi Arabia adds a
delivery-point code that belongs to neither line — and carriers, customs and
tax systems there consume the parts, which a composed line cannot reliably be
split back into.

This extension adds a structured view of the two street lines,
`address_line_components`, and an independent `address_code`, to the postal
addresses of the Checkout and Order capabilities. It is additive:
`street_address` and `extended_address` keep their meaning and remain the
representation every reader can print as a label.

## Key Concepts

**Each component belongs to one flat line.** `street_name` and `street_number`
are the components of `street_address`; `additional_information`, `district`
and `subdistrict` are the components of `extended_address`. The components of
one flat line form its *component group*.

**The country owns the composition.** How components are ordered and punctuated
into a flat line — `Avenida Paulista, 1578` in Brazil, `15 Rue de Rivoli` in
France — is a convention of the destination country. The business composes;
the platform never does.

**Which components a country uses is a country fact.** The schema accepts every
component everywhere; a sender includes the components the destination country
writes and omits the rest. Per-country applicability is published separately.

**`address_code` is not a line component.** It identifies the delivery point on
its own and is never composed into a flat line.

<!-- ucp:example schema=common/address_line_components def=postal_address op=read -->
```json
{
  "first_name": "Ana",
  "last_name": "Souza",
  "street_address": "Avenida Paulista, 1578",
  "extended_address": "Conjunto 42, Bela Vista",
  "address_locality": "São Paulo",
  "address_region": "SP",
  "postal_code": "01310-200",
  "address_country": "BR",
  "address_line_components": {
    "street_name": "Avenida Paulista",
    "street_number": "1578",
    "additional_information": "Conjunto 42",
    "district": "Bela Vista"
  }
}
```

## Discovery

Businesses advertise the extension in their profile with the standard
mechanism. It decorates the Checkout and Order capabilities; businesses MAY
advertise either or both, and platforms SHOULD check which are extended.

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/checkout",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.shopping.order": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/order",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/order.json"
        }
      ],
      "dev.shopify.common.address_line_components": [
        {
          "version": "{{ ucp_version }}",
          "extends": ["dev.ucp.shopping.checkout", "dev.ucp.shopping.order"],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/extensions/address-line-components",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/address_line_components.json"
        }
      ]
    }
  }
}
```

**Dependencies:**

* Checkout Capability
* Order Capability
* Fulfillment Extension, for shipping destinations on Checkout. Billing
  addresses do not depend on it.

| Capability | Location | Direction |
| ---------- | -------- | --------- |
| Checkout | `fulfillment.methods[].destinations[]` with `type: shipping_address` | Request and response |
| Checkout | `payment.instruments[].billing_address` | Request and response |
| Order | `fulfillment.expectations[].destination` | Response |

A `business_location` destination never carries the properties. Cart has no
address-bearing member at this revision and is not extended.

## Schema

### Entities

#### Address Line Components

{{ extension_schema_fields('address_line_components.json#/$defs/address_line_components', 'common/extensions/address-line-components') }}

#### Postal Address with Address Line Components

{{ extension_schema_fields('address_line_components.json#/$defs/postal_address', 'common/extensions/address-line-components') }}

#### Shipping Destination with Address Line Components

{{ extension_schema_fields('address_line_components.json#/$defs/shipping_destination', 'common/extensions/address-line-components') }}

## Address line components behavior

### Writing an address

An address in a request is a complete statement of the address. This follows
from the capability it rides on: [Update Checkout](../../shopping/checkout/index.md#update-checkout)
replaces the whole resource rather than patching it, so there is no persisted
address for an omitted field to fall back to. APIs with patch semantics
typically preserve an omitted field and clear it with an explicit `null`; a
platform bridging from such an API must send the full intended address here.

The business applies these rules to each component group independently;
`address_code` is handled like any other top-level address field.

1. **Components win.** When a request carries a flat line together with any
   component of its group, the business composes the flat line from the
   components in the destination country's convention and discards the flat
   value it received. No message is raised.
2. **A flat line without components carries no components.** A platform that
   knows only the flat shape keeps writing it exactly as before, and the
   resulting address has no components for that group.
3. **Clearing is by omission.** A field is cleared by leaving it out of the
   request. `null` is not a valid value: every `PostalAddress` field is a
   non-nullable string, and an extension can only add constraints, never relax
   them.
4. **The business never infers components.** A response contains only the
   components a request supplied; the business does not split a flat line.

The business MUST reject a component the destination country does not use, an
empty required component or a value beyond the country's limits with a
recoverable `message` of `type: "error"` whose `path` names the field.

### Reading an address

A response carries the composed flat lines alongside the components the
business holds, and `address_code` when one is held. A reader that does not
implement this extension reads the flat lines and ignores the rest; one that
does SHOULD prefer the components when present.

### Absence

When the extension is not negotiated, a business MUST ignore
`address_line_components` and `address_code` in requests and MUST NOT return
them. The flat address behaves exactly as it does without the extension.

## Use Cases and Examples

### Shipping to a structured address

A platform collects a Brazilian delivery address as components and sends them
on a checkout update together with the flat lines it would have sent anyway.

=== "Request"

    <!-- ucp:example schema=common/address_line_components def=dev.ucp.shopping.checkout op=update direction=request -->
    ```json
    {
      "line_items": [
        {
          "id": "li_1",
          "item": { "id": "prod_1" },
          "quantity": 1
        }
      ],
      "fulfillment": {
        "methods": [
          {
            "type": "shipping",
            "line_item_ids": ["li_1"],
            "destinations": [
              {
                "type": "shipping_address",
                "first_name": "Ana",
                "last_name": "Souza",
                "street_address": "Avenida Paulista, 1578",
                "extended_address": "Conjunto 42, Bela Vista",
                "address_locality": "São Paulo",
                "address_region": "SP",
                "postal_code": "01310-200",
                "address_country": "BR",
                "address_line_components": {
                  "street_name": "Avenida Paulista",
                  "street_number": "1578",
                  "additional_information": "Conjunto 42",
                  "district": "Bela Vista"
                }
              }
            ]
          }
        ]
      }
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/address_line_components def=shipping_destination op=read direction=response -->
    ```json
    {
      "type": "shipping_address",
      "id": "dest_1",
      "first_name": "Ana",
      "last_name": "Souza",
      "street_address": "Avenida Paulista, 1578",
      "extended_address": "Conjunto 42, Bela Vista",
      "address_locality": "São Paulo",
      "address_region": "SP",
      "postal_code": "01310-200",
      "address_country": "BR",
      "address_line_components": {
        "street_name": "Avenida Paulista",
        "street_number": "1578",
        "additional_information": "Conjunto 42",
        "district": "Bela Vista"
      }
    }
    ```

### Flat address from a platform that does not send components

The resulting address has no components, and the response omits
`address_line_components`.

=== "Request"

    <!-- ucp:example schema=common/address_line_components def=shipping_destination op=update direction=request -->
    ```json
    {
      "street_address": "Rua Augusta, 1200",
      "extended_address": "Apto 31",
      "address_locality": "São Paulo",
      "address_region": "SP",
      "postal_code": "01304-001",
      "address_country": "BR"
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/address_line_components def=shipping_destination op=read direction=response -->
    ```json
    {
      "type": "shipping_address",
      "id": "dest_1",
      "street_address": "Rua Augusta, 1200",
      "extended_address": "Apto 31",
      "address_locality": "São Paulo",
      "address_region": "SP",
      "postal_code": "01304-001",
      "address_country": "BR"
    }
    ```

### Components take precedence over a flat line

The request's `street_address` disagrees with its `street_name` and
`street_number`; `extended_address` comes with no components. The business
recomposes `street_address` and keeps `extended_address` as a flat line.

=== "Request"

    <!-- ucp:example schema=common/address_line_components def=shipping_destination op=update direction=request -->
    ```json
    {
      "street_address": "1578 Avenida Paulista",
      "extended_address": "Conjunto 42",
      "address_locality": "São Paulo",
      "address_region": "SP",
      "postal_code": "01310-200",
      "address_country": "BR",
      "address_line_components": {
        "street_name": "Avenida Paulista",
        "street_number": "1578"
      }
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/address_line_components def=shipping_destination op=read direction=response -->
    ```json
    {
      "type": "shipping_address",
      "id": "dest_1",
      "street_address": "Avenida Paulista, 1578",
      "extended_address": "Conjunto 42",
      "address_locality": "São Paulo",
      "address_region": "SP",
      "postal_code": "01310-200",
      "address_country": "BR",
      "address_line_components": {
        "street_name": "Avenida Paulista",
        "street_number": "1578"
      }
    }
    ```

### Billing address with an address code

A Saudi billing address on a payment instrument. The code is returned as sent
and is never part of a flat line.

<!-- ucp:example schema=common/address_line_components def=postal_address op=read direction=response -->
```json
{
  "first_name": "Noura",
  "last_name": "Al-Qahtani",
  "street_address": "Olaya Street 7248",
  "extended_address": "Apt 501",
  "address_locality": "Riyadh",
  "postal_code": "12271",
  "address_country": "SA",
  "address_code": "2929",
  "address_line_components": {
    "street_name": "Olaya Street",
    "street_number": "7248",
    "additional_information": "Apt 501"
  }
}
```

## Mapping from other address models

The components carry the same names as the structured address fields of
Shopify's GraphQL APIs, in UCP's snake_case convention; only the spelling
differs.

| GraphQL field | UCP property |
| ------------- | ------------ |
| `addressLineComponents.streetName` | `address_line_components.street_name` |
| `addressLineComponents.streetNumber` | `address_line_components.street_number` |
| `addressLineComponents.additionalInformation` | `address_line_components.additional_information` |
| `addressLineComponents.district` | `address_line_components.district` |
| `addressLineComponents.subdistrict` | `address_line_components.subdistrict` |
| `addressCode` | `address_code` |
| `address1` | `street_address` |
| `address2` | `extended_address` |

## Implementation guidelines

* Businesses MUST NOT put invisible or non-printing separators in a composed
  flat line.
* Platforms that render an editable address form SHOULD edit the components
  when the response carries them, and SHOULD NOT pre-fill components from a
  flat line without the buyer's confirmation.
