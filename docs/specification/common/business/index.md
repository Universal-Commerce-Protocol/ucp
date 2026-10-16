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

# Business Capability

* **Capability Name:** `dev.ucp.common.business`
* **Schema:** `https://ucp.dev/{{ ucp_version }}/schemas/common/business.json`

## Overview

The Business capability lets a Business publish **location-independent**
identity metadata about the business or brand as a whole (`name`, `media`,
`links`, `address`, `contacts`, and `categories`) in its discovery profile
(`/.well-known/ucp`).

It is a declarative, profile-resident Common capability: it defines no runtime
RPC operations of its own, and serves as the base capability that vertical
specifications and third-party ecosystems extend via `extends` to attach
vertical-specific business identity attributes. Its shared summary type
(`common/types/business_summary.json`) also provides the common identity shape
reusable across other UCP surfaces, such as seller records in multi-seller
catalogs.

### Separation from Location

`dev.ucp.common.business` and [Location](../location/index.md)
(`dev.ucp.common.location.*`) address distinct concerns and are independently
adoptable:

* **Business (`dev.ucp.common.business`) — who the business is (location-independent):**
  Describes the business or brand entity as a whole, independent of physical
  retail branches: its display `name`, brand `media` (`logo`, `cover`),
  canonical `website` and business-wide policy `links`, corporate or legal
  `address`, business-wide `contacts`, and business `categories` (`mcc`,
  `naics`, `isic`, `merchant`). It is declared statically in `ucp.capabilities`
  on `/.well-known/ucp`.
* **Location (`dev.ucp.common.location.*`) — where physical branches operate:**
  Describes individual physical places (`Location` resources with `id`, branch
  `name`, branch `address`, `geo` coordinates, `hours`, `exception_hours`,
  `timezone`, and physical `amenities`), queried dynamically at runtime via
  [Location Search](../location/search.md) and
  [Location Lookup](../location/lookup.md).

An online-only merchant or digital brand advertises `dev.ucp.common.business`
(including its corporate `address` and customer-support `contacts`) without
`dev.ucp.common.location.*`. A brick-and-mortar or omnichannel business
advertises `dev.ucp.common.business` for its brand-level and corporate identity
alongside `dev.ucp.common.location.*` for its physical retail branches.

## Discovery

Businesses advertise `dev.ucp.common.business` in `ucp.capabilities` with a
`config` object carrying their location-independent identity metadata:

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {},
    "capabilities": {
      "dev.ucp.common.business": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/business/",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/business.json",
          "config": {
            "name": "Joe's Pizza",
            "media": [
              {
                "type": "image",
                "role": "logo",
                "url": "https://cdn.joespizza.example/logo.png",
                "alt_text": "Joe's Pizza logo"
              },
              {
                "type": "image",
                "role": "cover",
                "url": "https://cdn.joespizza.example/cover.jpg"
              }
            ],
            "links": [
              {
                "type": "website",
                "url": "https://joespizza.example"
              }
            ],
            "address": {
              "street_address": "123 Carmine St",
              "address_locality": "New York",
              "address_region": "NY",
              "postal_code": "10014",
              "address_country": "US"
            },
            "contacts": [
              {
                "type": "general",
                "phone_number": "+12125550100",
                "email": "info@joespizza.example"
              },
              {
                "type": "customer_support",
                "email": "support@joespizza.example"
              }
            ],
            "categories": [
              {
                "taxonomy": "mcc",
                "value": "5812"
              },
              {
                "taxonomy": "merchant",
                "value": "Pizza restaurant"
              }
            ]
          }
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

Because each version-specific profile referenced via `supported_versions` is a
self-contained document, leaf profiles **SHOULD** include
`dev.ucp.common.business` when present.

### Storefront and Policy Links

`config.links` carries the business's customer-facing `website` URL and
business-wide legal or policy disclosures (`privacy_policy`,
`terms_of_service`, `refund_policy`, `shipping_policy`, `faq`), not a sitemap of
site navigation pages.

### Corporate Address and Contacts

`config.address` carries the business entity's corporate, headquarters, or
registered legal address (distinct from physical retail branches in
`dev.ucp.common.location.*`). `config.contacts` carries business-wide contact
channels (`general`, `customer_support`, `admin`, `legal`). Because
`/.well-known/ucp` is a public, unauthenticated document, Businesses **SHOULD**
publish public or business-routed contact channels (such as a main business
phone number or a domain email like `info@joespizza.example`) rather than an
individual's personal email address or personal phone number.

## Schema

### Configuration

{{ extension_schema_fields('business.json#/$defs/config', 'common/business') }}

<!-- ucp:example schema=common/business def=config -->
```json
{
  "name": "Joe's Pizza",
  "media": [
    {
      "type": "image",
      "role": "logo",
      "url": "https://cdn.joespizza.example/logo.png",
      "alt_text": "Joe's Pizza logo"
    },
    {
      "type": "image",
      "role": "cover",
      "url": "https://cdn.joespizza.example/cover.jpg"
    }
  ],
  "links": [
    {
      "type": "website",
      "url": "https://joespizza.example"
    }
  ],
  "address": {
    "street_address": "123 Carmine St",
    "address_locality": "New York",
    "address_region": "NY",
    "postal_code": "10014",
    "address_country": "US"
  },
  "contacts": [
    {
      "type": "general",
      "phone_number": "+12125550100",
      "email": "info@joespizza.example"
    },
    {
      "type": "customer_support",
      "email": "support@joespizza.example"
    }
  ],
  "categories": [
    {
      "taxonomy": "mcc",
      "value": "5812"
    },
    {
      "taxonomy": "merchant",
      "value": "Pizza restaurant"
    }
  ]
}
```

### Business Summary {: #business-summary }

{{ schema_fields('types/business_summary', 'common/business') }}

### Contact {: #contact }

{{ schema_fields('types/contact', 'common/business') }}

### Business Category {: #business-category }

{{ extension_schema_fields('business.json#/$defs/category', 'common/business') }}

## Extensibility

`dev.ucp.common.business` defines the horizontal, vertical-agnostic base
identity of a business. Vertical specifications (such as Dining, Services,
Retail, or Lodging) and third-party ecosystems **MAY** define extension
capabilities that declare `"extends": "dev.ucp.common.business"` in
`ucp.capabilities`, carrying their own `version`, `schema` URL (governed by
[Authority Binding](../../overview/index.md#authority-binding)), and
vertical-specific `config` fields:

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {},
    "capabilities": {
      "dev.ucp.common.business": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/business/",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/business.json",
          "config": {
            "name": "Joe's Pizza",
            "links": [
              {
                "type": "website",
                "url": "https://joespizza.example"
              }
            ],
            "categories": [
              {
                "taxonomy": "mcc",
                "value": "5812"
              }
            ]
          }
        }
      ],
      "com.example.dining": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.common.business",
          "spec": "https://example.com/specs/dining",
          "schema": "https://example.com/schemas/dining.json",
          "config": {
            "cuisines": ["pizza", "italian"],
            "dietary_options": ["vegetarian", "gluten_free"]
          }
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

Per UCP's capability negotiation and pruning rules, a Platform that does not
recognize an extension capability ignores it while still consuming the base
`dev.ucp.common.business` metadata.
