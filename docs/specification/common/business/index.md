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

The Business capability lets a Business publish its **public, self-declared brand
and storefront card** (`name`, `legal_name`, `description`, `media`, `links`,
`address`, `contacts`, and `categories`) in its discovery profile
(`/.well-known/ucp`). Analogous to `schema.org/Organization`, it states who
operates the profile origin and is decoupled from transactional capabilities so
that any UCP profile (including online-only brands, regional storefronts, or
profiles advertising only non-transactional capabilities such as Location or
Ask) can publish location-independent identity metadata.

It is a declarative, profile-resident Common capability: it defines no runtime
RPC operations of its own, and serves as the base capability that vertical
specifications and third-party ecosystems extend via `extends` to attach
vertical-specific business identity attributes. Its shared summary type
(`common/types/business_summary.json`) also provides the common party identity
shape reused across multi-seller Catalog responses and transactional Cart,
Checkout, and Order sessions.

### Separation from Location

`dev.ucp.common.business` and [Location](../location/index.md)
(`dev.ucp.common.location.*`) address distinct concerns and are independently
adoptable:

* **Business (`dev.ucp.common.business`), who the business is (location-independent):**
  Describes the business or brand entity operating the profile as a whole,
  independent of physical retail branches: its display `name`, registered
  `legal_name`, `description`, brand `media` (`logo`, `icon`, `cover`),
  canonical `website` and business-wide policy `links`, publicly disclosable
  corporate `address`, public `contacts`, and business `categories` (`mcc`,
  `naics`, `isic`, `merchant`). It is declared statically in `ucp.capabilities`
  on `/.well-known/ucp`.
* **Location (`dev.ucp.common.location.*`), where physical branches operate:**
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

### Relationship to Marketplace Sellers and Regional Entities

`dev.ucp.common.business` on `/.well-known/ucp` describes only the party
operating that profile origin (the storefront or marketplace brand). Declaring
`dev.ucp.common.business` does not assert that the profile host is the sole
seller of record for every catalog offer or buyer region.

Multi-seller marketplaces (where third-party sellers often do not host their own
`/.well-known/ucp` profiles) and multi-entity global brands (where the
contracting legal entity varies by buyer region or shipping address, such as US
Inc. vs. Canada Ltd. vs. EU GmbH) reuse `common/types/business_summary.json` in
response-level `sellers` maps referenced by `seller_id` across Catalog, Cart,
Checkout, and Order responses. This allows platforms to render per-offer seller
identity and resolve the authoritative contracting entity at checkout without
requiring third-party sellers to operate UCP servers or adding extra lookup
round trips.

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
            "legal_name": "Joe's Pizza LLC",
            "description": {
              "markdown": "New York slice shop serving Greenwich Village since 1975."
            },
            "media": [
              {
                "type": "image",
                "role": "logo",
                "url": "https://cdn.joespizza.example/logo.png",
                "alt_text": "Joe's Pizza logo"
              },
              {
                "type": "image",
                "role": "icon",
                "url": "https://cdn.joespizza.example/icon.png",
                "alt_text": "Joe's Pizza icon"
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
site navigation pages. A Business **SHOULD** include at most one `website` link
in `config.links`, representing the canonical customer-facing storefront for
that profile origin.

### Corporate Address and Contacts

`config.address` carries the publicly disclosable corporate, headquarters, or
statutory establishment address of the business entity (distinct from physical
retail branches in `dev.ucp.common.location.*`). `config.contacts` carries
public contact channels (`general`, `customer_support`, `legal`, `press`).

Because `/.well-known/ucp` is a public, unauthenticated document cached across
platforms, Businesses **MUST NOT** place private tax or underwriting
identifiers, non-public personal or residential addresses (such as for sole
proprietors), or internal operational contacts in `config`. Businesses
**SHOULD** publish public or business-routed contact channels (such as a main
customer-support phone number or a domain email like `info@joespizza.example`)
rather than an individual's personal email address or personal phone number.
Context-dependent or statutory seller disclosures required before purchase bind
at checkout time.

## Security Considerations

### Self-Declared Claims ("Presented as Stated")

All fields in `dev.ucp.common.business` (`name`, `legal_name`, `description`,
`media`, `links`, `address`, `contacts`, and `categories`) are self-declared by
the business publishing the profile. A Platform **MUST** treat these fields as
stated by the business, **MUST NOT** display or badge them as third-party
verified based solely on their presence in the profile, **MUST NOT** infer
omitted fields, and **MUST NOT** treat self-declared `categories` (such as
`mcc`) as underwritten payment or compliance classifications without independent
verification.

### Rich Text Sanitization

When rendering `description.html` or `description.markdown`, a Platform **MUST**
sanitize untrusted HTML and Markdown and strip active content (including
`<script>`, `<iframe>`, `<object>`, `<embed>`, inline event handlers, and
`javascript:` or `data:` URLs) before rendering, in accordance with
`common/types/description.json`.

## Schema

### Configuration

{{ extension_schema_fields('business.json#/$defs/config', 'common/business') }}

<!-- ucp:example schema=common/business def=config -->
```json
{
  "name": "Joe's Pizza",
  "legal_name": "Joe's Pizza LLC",
  "description": {
    "markdown": "New York slice shop serving Greenwich Village since 1975."
  },
  "media": [
    {
      "type": "image",
      "role": "logo",
      "url": "https://cdn.joespizza.example/logo.png",
      "alt_text": "Joe's Pizza logo"
    },
    {
      "type": "image",
      "role": "icon",
      "url": "https://cdn.joespizza.example/icon.png",
      "alt_text": "Joe's Pizza icon"
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
