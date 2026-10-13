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
`links`, and `categories`) in its discovery profile (`/.well-known/ucp`).

It is a declarative, profile-resident Common capability: it defines no runtime
RPC operations of its own, and serves as the base capability that vertical
specifications and third-party ecosystems extend via `extends` to attach
vertical-specific business identity attributes.

### Separation from Location

`dev.ucp.common.business` and [Location](../location/index.md)
(`dev.ucp.common.location.*`) address distinct concerns and are independently
adoptable:

* **Business (`dev.ucp.common.business`) — who the business is (location-independent):**
  Describes the business or brand entity as a whole, independent of physical
  geography or brick-and-mortar footprint: its display `name`, brand `media`
  (`logo`, `cover`), canonical `website` and business-wide policy `links`, and
  business `categories` (`mcc`, `naics`, `isic`, `merchant`). It is declared
  statically in `ucp.capabilities` on `/.well-known/ucp`.
* **Location (`dev.ucp.common.location.*`) — where physical branches operate:**
  Describes individual physical places (`Location` resources with `id`, branch
  `name`, `address`, `geo` coordinates, `phone`, `hours`, `exception_hours`,
  `timezone`, and physical `amenities`), queried dynamically at runtime via
  [Location Search](../location/search.md) and
  [Location Lookup](../location/lookup.md).

An online-only merchant or digital brand advertises `dev.ucp.common.business`
without `dev.ucp.common.location.*`. A brick-and-mortar or omnichannel business
advertises `dev.ucp.common.business` for its brand-level identity alongside
`dev.ucp.common.location.*` for its physical branches.

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
                "url": "https://cdn.pos-host.example/joes/logo.png",
                "alt_text": "Joe's Pizza logo"
              },
              {
                "type": "image",
                "role": "cover",
                "url": "https://cdn.pos-host.example/joes/cover.jpg"
              }
            ],
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

### Storefront Binding (`website` Link)

When a business profile origin (`/.well-known/ucp`) differs from the business's
buyer-facing storefront URL, the business **SHOULD** include a `website` entry
in `config.links` pointing to its canonical customer-facing storefront:

* **Platform-hosted SMB:** A profile hosted at
  `https://joes-pizza.pos-host.example/.well-known/ucp` declares
  `{"type": "website", "url": "https://joespizza.example"}` (or
  `https://pos-host.example/joes-pizza`).
* **Multi-region enterprise with path-based country storefronts:** An
  enterprise serving regional storefronts at `https://global-apparel.example/us`
  and `https://global-apparel.example/ca` publishes separate UCP profiles at
  `https://us.ucp.global-apparel.example/.well-known/ucp` and
  `https://ca.ucp.global-apparel.example/.well-known/ucp`, each setting
  `config.name` (e.g., `"Global Apparel US"`) and `config.links`
  (`{"type": "website", "url": "https://global-apparel.example/us"}`).
* **Multi-brand enterprise:** Each brand origin declares that brand's own
  `config.name`, `media`, `links`, and `categories`.

`config.links` is for canonical storefront binding (`website`) and
business-wide legal or policy disclosures (`privacy_policy`,
`terms_of_service`, `refund_policy`, `shipping_policy`, `faq`)—not a sitemap of
site navigation pages.

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
      "url": "https://cdn.pos-host.example/joes/logo.png",
      "alt_text": "Joe's Pizza logo"
    },
    {
      "type": "image",
      "role": "cover",
      "url": "https://cdn.pos-host.example/joes/cover.jpg"
    }
  ],
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
    },
    {
      "taxonomy": "merchant",
      "value": "Pizza restaurant"
    }
  ]
}
```

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
