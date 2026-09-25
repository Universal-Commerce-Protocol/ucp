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

# Catalog Feed

* **Capability Name:** `dev.ucp.shopping.catalog.feed`

A catalog feed is a materialized catalog: the same Product records a Platform
would receive from [Catalog Search](search.md), published in bulk as files so
the Platform can index, embed, and rank them offline, then call Catalog Search
and [Catalog Lookup](lookup.md) at serving time for the authoritative price and
availability. The feed and the live catalog are complementary: the feed is
point-in-time, the live operations are authoritative.

This capability extends the **[Feed capability](../../common/feed/index.md)**
(`dev.ucp.common.feed`) with a record type. Discovery, the feed list,
manifests, files, snapshot semantics, formats, and access are defined there and
not restated here. This document defines what a catalog feed's records are,
which resolutions a Platform obtains from the live catalog at serving time, and
the `filters` this capability adds to a catalog manifest.

**Dependencies:**

* Feed Capability (`dev.ucp.common.feed`)

## Discovery

A shopping Business that publishes catalog feeds declares two entries in its
profile, beside its Catalog Search and Catalog Lookup entries:
`dev.ucp.common.feed`, whose `config.endpoint` serves the feed list, and
`dev.ucp.shopping.catalog.feed`, which declares `extends:
"dev.ucp.common.feed"` and carries no `config`. A Platform activates
`dev.ucp.shopping.catalog.feed` only when `dev.ucp.common.feed` is in the
negotiated set; without its parent, the entry is pruned. The one feed endpoint
serves every feed the Business publishes, whatever its record type.

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.common.feed": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/feed",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/feed.json",
        "config": {
          "endpoint": "https://merchant.example.com/ucp/feeds"
        }
      }],
      "dev.ucp.shopping.catalog.feed": [{
        "version": "{{ ucp_version }}",
        "extends": "dev.ucp.common.feed",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/catalog/feed",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/catalog_feed.json"
      }]
    },
    "payment_handlers": {}
  }
}
```

## Records

In this capability a record is a catalog [Product](index.md#product) with its
nested `variants`, exactly as returned by Catalog Search, conforming to the
schemas of the capabilities declared in the manifest's `ucp.capabilities`.

* For `jsonl+gzip`, each line is one Product.
* For `parquet`, each row is one Product with `variants` as a nested column;
  a snapshot may span several files.

Records carry the Business's own identity. The Business **MUST** carry in each
record the same product and variant identifiers that its Catalog Lookup
resolves. A Business that publishes through a delegate remains responsible for
the feed; it **MAY** include additional identifiers assigned by the delegate
but **MUST NOT** replace its own. A Platform that resolves a feed
identifier through Catalog Lookup at serving time observes a violation as a
`not_found` outcome and handles it as it would for any unresolved identifier.

## Context

A catalog feed is resolved for one market. Its `context` **SHOULD** carry
`address_country`, `language`, and `currency`; `CA`/`en-CA`/`CAD` and
`CA`/`fr-CA`/`CAD` are two feeds. A Business that materializes sub-national
markets **MAY** scope a feed further with `address_region` or `postal_code`. A
catalog feed **SHOULD NOT** be scoped by members that describe a buyer rather
than a market (`location`, `eligibility`, `intent`, `payment`); a Platform
obtains those resolutions, and the authoritative price and availability, from
Catalog Search or Catalog Lookup at serving time.

## Filters

This capability adds `filters` to the manifest: row-inclusion predicates the
Business applied when generating the snapshot, using the same names and
semantics as [Search Filters](search.md#search-filters). Absent means no filter
was applied. A catalog snapshot is complete for its `context` and its
`filters`: absence of a record from the latest complete snapshot means the
record is not offered in this context or does not satisfy the feed's `filters`.
The manifest below materializes the Business's Canadian French catalog
restricted to footwear. It declares both `dev.ucp.common.feed` and
`dev.ucp.shopping.catalog.feed`, and the latter is what defines `filters`:

<!-- ucp:example schema=shopping/catalog_feed op=list def=dev.ucp.common.feed -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.feed": [
        {"version": "{{ ucp_version }}"}
      ],
      "dev.ucp.shopping.catalog.feed": [
        {"version": "{{ ucp_version }}", "extends": "dev.ucp.common.feed"}
      ]
    }
  },
  "id": "ca-fr-cad",
  "format": "jsonl+gzip",
  "context": {
    "address_country": "CA",
    "language": "fr-CA",
    "currency": "CAD"
  },
  "filters": {
    "categories": ["Footwear"]
  },
  "generated_at": "2026-09-22T06:10:00Z",
  "expires_at": "2026-09-29T06:10:00Z",
  "files": [
    {
      "url": "part-00000.jsonl.gz",
      "digest": "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"
    }
  ]
}
```

## Supplemental Feeds

In a [supplemental feed](../../common/feed/index.md#supplemental-feeds) over a
catalog feed, Product satisfies the record-type requirements for supplemental
feeds. A Product's `id` and each Variant's `id` are the identifiers [Catalog
Lookup](lookup.md) resolves, a Variant's `id` being the `item.id` checkout
accepts, and `variants` is the identified list (see [Records](#records)). A
supplemental record matches a Product by `id` and each of its variants by `id`.
Every other member is replaced whole: a supplement that carries a variant's
`price` carries `amount` and `currency`; one that carries `availability`
carries the whole object.

### Example: Per-Market Prices as a Supplemental Feed

A Business sells in the United States and Canada. Titles, descriptions, and
media are shared between the two markets; only prices differ, and they change
faster than the catalog does. Rather than materialize a second full feed for
Canada, the Business publishes `ca-en-cad` as a supplemental feed extending
`us-en-usd`. The base rolls daily as Parquet; the supplement, which carries
only prices, rolls every two hours as gzipped JSON Lines:

<!-- ucp:example schema=common/feed op=list def=feed_list -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.feed": [
        {"version": "{{ ucp_version }}"}
      ]
    }
  },
  "feeds": [
    {
      "id": "us-en-usd",
      "context": {
        "address_country": "US",
        "language": "en-US",
        "currency": "USD"
      },
      "format": "parquet",
      "interval": "P1D",
      "generated_at": "2026-09-22T06:00:00Z",
      "manifest": "https://merchant.example.com/feeds/us-en-usd/20260922T060000Z/manifest.json"
    },
    {
      "id": "ca-en-cad",
      "extends": "us-en-usd",
      "context": {
        "address_country": "CA",
        "language": "en-CA",
        "currency": "CAD"
      },
      "format": "jsonl+gzip",
      "interval": "PT2H",
      "generated_at": "2026-09-22T10:00:00Z",
      "manifest": "https://merchant.example.com/feeds/ca-en-cad/20260922T100000Z/manifest.json"
    }
  ]
}
```

The supplemental manifest repeats `extends`, `context`, and
`format`, and declares the record type of its base feed:

<!-- ucp:example schema=shopping/catalog_feed op=list def=dev.ucp.common.feed -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.feed": [
        {"version": "{{ ucp_version }}"}
      ],
      "dev.ucp.shopping.catalog.feed": [
        {"version": "{{ ucp_version }}", "extends": "dev.ucp.common.feed"}
      ]
    }
  },
  "id": "ca-en-cad",
  "extends": "us-en-usd",
  "format": "jsonl+gzip",
  "context": {
    "address_country": "CA",
    "language": "en-CA",
    "currency": "CAD"
  },
  "generated_at": "2026-09-22T10:00:00Z",
  "expires_at": "2026-09-23T10:00:00Z",
  "files": [
    {
      "url": "part-00000.jsonl.gz",
      "digest": "sha-256=:AvfSa2lpX4dC8ex6Favv/LqBMclrorhzofoWCswgQ/w=:"
    }
  ]
}
```

Records are partial Products: each carries its `id`, its `price_range`, and,
for each of its variants, the variant's `id` and `price`, every amount in CAD
minor units:

```text
{"id": "P100", "price_range": {"min": {"amount": 15900, "currency": "CAD"}, "max": {"amount": 16900, "currency": "CAD"}}, "variants": [{"id": "V200", "price": {"amount": 15900, "currency": "CAD"}}, {"id": "V201", "price": {"amount": 16900, "currency": "CAD"}}]}
{"id": "P101", "price_range": {"min": {"amount": 7900, "currency": "CAD"}, "max": {"amount": 7900, "currency": "CAD"}}, "variants": [{"id": "V210", "price": {"amount": 7900, "currency": "CAD"}}]}
```

A Platform building the Canadian feed takes `us-en-usd` and applies each
supplemental record to the Product with the same `id`, and each supplemental
variant to the Variant with the same `id`, so titles, descriptions, and
availability carry over unchanged. The Business restates `price_range`
because it depends on the variant prices the supplement changes; that is the
general obligation that a composed record be correct for its `context`. The
base stays one set of files for both markets.

### Example: Platform-Specific Fields as a Supplemental Feed

A Business publishes one base feed of catalog Products for every Platform. One
Platform, a marketplace, defines an extension
`com.example.marketplace.compliance` whose fields are the trade-compliance
facts it needs for United States listings and no other Platform asks for:
country of origin, Harmonized Tariff Schedule code, and whether a California
Proposition 65 warning applies. Rather than add those fields to the base feed,
the Business advertises the extension in its profile and publishes a
supplemental feed that carries only the identifier of each base Product and
the extension's fields. The base feed stays portable, the two refresh on their
own cadences, and who sees the supplement is the Business's choice: here it is
provisioned only to the marketplace's identity; a supplement whose extension
many Platforms consume could as well be listed publicly.

The Business's profile advertises the extension beside the two feed entries;
the extension extends `dev.ucp.shopping.catalog.feed`, and its schema, on the
marketplace's own domain, defines the fields the supplemental records carry:

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.common.feed": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/feed",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/feed.json",
        "config": {
          "endpoint": "https://merchant.example.com/ucp/feeds"
        }
      }],
      "dev.ucp.shopping.catalog.feed": [{
        "version": "{{ ucp_version }}",
        "extends": "dev.ucp.common.feed",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/catalog/feed",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/catalog_feed.json"
      }],
      "com.example.marketplace.compliance": [{
        "version": "2026-06-01",
        "extends": "dev.ucp.shopping.catalog.feed",
        "spec": "https://marketplace.example.com/ucp/compliance",
        "schema": "https://marketplace.example.com/ucp/compliance.json"
      }]
    },
    "payment_handlers": {}
  }
}
```

Feed list as provisioned to the marketplace in this example:

<!-- ucp:example schema=common/feed op=list def=feed_list -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.feed": [
        {"version": "{{ ucp_version }}"}
      ]
    }
  },
  "feeds": [
    {
      "id": "us-en-usd",
      "context": {
        "address_country": "US",
        "language": "en-US",
        "currency": "USD"
      },
      "format": "jsonl+gzip",
      "interval": "P1D",
      "generated_at": "2026-09-22T06:00:00Z",
      "manifest": "https://merchant.example.com/feeds/us-en-usd/20260922T060000Z/manifest.json"
    },
    {
      "id": "us-en-usd-compliance",
      "extends": "us-en-usd",
      "context": {
        "address_country": "US",
        "language": "en-US",
        "currency": "USD"
      },
      "format": "jsonl+gzip",
      "interval": "P7D",
      "generated_at": "2026-09-21T00:00:00Z",
      "manifest": "https://merchant.example.com/feeds/us-en-usd-compliance/3f9c2a7e-5b41-4d8e-9c0a-1e6f7b2d8a54/manifest.json"
    }
  ]
}
```

The supplemental manifest repeats `extends` and declares the
record type of its base feed and the extension whose schema its records
follow:

<!-- ucp:example schema=common/feed op=list def=manifest -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.feed": [
        {"version": "{{ ucp_version }}"}
      ],
      "dev.ucp.shopping.catalog.feed": [
        {"version": "{{ ucp_version }}", "extends": "dev.ucp.common.feed"}
      ],
      "com.example.marketplace.compliance": [
        {"version": "2026-06-01", "extends": "dev.ucp.shopping.catalog.feed"}
      ]
    }
  },
  "id": "us-en-usd-compliance",
  "extends": "us-en-usd",
  "format": "jsonl+gzip",
  "context": {
    "address_country": "US",
    "language": "en-US",
    "currency": "USD"
  },
  "generated_at": "2026-09-21T00:00:00Z",
  "expires_at": "2026-10-05T00:00:00Z",
  "files": [
    {
      "url": "part-00000.jsonl.gz",
      "digest": "sha-256=:kP3xg2v7R6Yq1uHt9cLm4nBw8sDf0aJe5oZi2yXr7Vc=:"
    }
  ]
}
```

Records are partial Products carrying the fields
`com.example.marketplace.compliance` defines; each is applied to the base
Product with the same `id`:

```text
{"id": "P100", "country_of_origin": "VN", "hts_code": "6404.11.90", "prop65_warning": false}
{"id": "P101", "country_of_origin": "PT", "hts_code": "6115.95.90", "prop65_warning": false}
```

The Platform applies each supplemental record to the base Product whose `id`
equals its own. A record that matches nothing in its copy of the base is
ignored; a base Product with no supplemental record carries no
`com.example.marketplace.compliance` fields. Had the Business preferred, it
could have declared the extension on the base manifest and carried the fields
inline; the supplemental form suits fields that are heavy, managed on a
different cadence, or provisioned to a subset of callers.
