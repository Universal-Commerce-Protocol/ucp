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

# Catalog Similarity Extension

* **Capability Name:** `dev.ucp.shopping.catalog.similarity`
* **Extends:** `dev.ucp.shopping.catalog.search`,
    `dev.ucp.shopping.catalog.lookup`

## Overview

The Catalog Similarity extension lets a Platform discover items by their
relationship to an item it already knows: products that resemble one the
Buyer is viewing, substitutes for one that is unavailable, and the items a
Business recommends alongside one.

This extension adds one field to each parent capability:

* **Catalog Search** (`dev.ucp.shopping.catalog.search`) — `like`, a list of
    similarity anchors the results should resemble. See
    [Similarity Anchors](#similarity-anchors).
* **Catalog Lookup** (`dev.ucp.shopping.catalog.lookup`) — `include`, a list
    naming additional data to return with each product, on both
    `lookup_catalog` and `get_product`: `substitutes` and `recommendations`.
    See [Includes](#includes).

Declaring the extension is an explicit opt-in: a Platform sends `like` or
`include` only to a Business that declares it. `like` is configurable:
`config` lets the Business advertise what it supports, such as how many
anchors it processes per request and whether it accepts inline images for
search by image similarity (see [Configuration](#configuration)).

## Configuration

A Business declares the extension in its profile, listing the parent
capabilities it applies to in `extends` and its limits in `config`:

{{ schema_fields('types/business_similarity_config', 'shopping/extensions/similarity') }}

`config.like` carries:

* `max_items` — the maximum number of anchors the Business processes per
    request (default 1).
* `images` — inline image anchor support. `images.max_items` defaults to 0:
    the Business accepts no image anchors until it advertises 1 or more,
    together with the accepted `types` and `max_bytes`, the maximum length
    of an image's base64 `data`. An absent `images` block is equivalent to
    `max_items: 0`. Image anchors count toward `like.max_items`.

<!-- ucp:example schema=profile def=business_schema target=$.ucp.capabilities -->
```json
{
  "dev.ucp.shopping.catalog.similarity": [
    {
      "version": "{{ ucp_version }}",
      "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/similarity",
      "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/catalog_similarity.json",
      "extends": [
        "dev.ucp.shopping.catalog.search",
        "dev.ucp.shopping.catalog.lookup"
      ],
      "config": {
        "like": {
          "max_items": 2,
          "images": {
            "max_items": 1,
            "types": ["image/jpeg", "image/webp"],
            "max_bytes": 5242880
          }
        }
      }
    }
  ]
}
```

This example says: up to two anchors per request, at most one of them an
inline JPEG or WebP image whose base64 `data` is at most 5 MiB. Image bytes
travel inside the JSON payload, so the limit applies to the encoded string.

### Anchor Count

`like.max_items` (default 1) is the Business's limit, not a request-validity
rule. A Platform **SHOULD** send no more anchors than it; a request that
carries more is still processed — the Business keeps the first `max_items`
anchors in request order and reports the truncation (see
[Anchor Limit](#anchor-limit)).

### Image Anchors

A Platform **MUST NOT** send an image anchor unless `images.max_items`
is 1 or more, and **MUST** stay within the advertised `images` constraints:
no more than `images.max_items` image anchors per request, each with a
`content_type` listed in `types` and `data` no longer than `max_bytes`.

An image anchor the Business cannot accept is not a request error. The
Business drops the anchor, processes the request on its remaining inputs,
and **SHOULD** include an informational message naming the reason:
`image_type_unsupported` when `content_type` is not in `types`,
`image_too_large` when `data` is longer than `max_bytes`, or `image_invalid`
when it cannot decode `data`. Omitting the message is conformant but leaves
the Platform unable to tell a dropped anchor from a weak match. Image anchors
beyond `images.max_items` are handled as in [Anchor Limit](#anchor-limit).
If no anchor remains, [Unresolved Anchors](#unresolved-anchors) applies.

## Similarity Anchors

`like` lists similarity anchors: products or variants the results should
resemble — "more like this" from an item the Buyer is viewing. Combined
with `query`, an anchor and the text rank together — for example, items
resembling a given shoe that also match "waterproof". Functional
replacements for an unavailable item are `substitutes` in
[Includes](#includes), not an anchored search. `like` is an extension-defined
input under [Search Inputs](../catalog/search.md#search-inputs): a request
carrying a recognized anchor is valid without `query` or `filters`, and is
not a browse — anchors rank. Each anchor carries one key naming its kind:
`id`, or `image` when the Business advertises `config.like.images`. Other
extensions add anchor kinds by adding keys and **SHOULD** name them with
reverse-domain keys (for example `com.example.color`) so independently
authored kinds cannot collide.

{{ extension_schema_fields('catalog_similarity.json#/$defs/like_item', 'shopping/extensions/similarity') }}

An `image` anchor carries `content_type`, the MIME type of the encoded image,
and `data`, the base64-encoded image bytes; both are required. The limits a
Platform observes when sending one are in
[Configuration](#image-anchors).

### Resolution

The Business resolves `id` as in Catalog Lookup's
[Supported Identifiers](../catalog/lookup.md#supported-identifiers): it
**MUST** support product ID and variant ID anchors and **MAY** support
secondary identifiers such as SKU or handle. An identifier that resolves to
several items (for example a SKU shared across variants) makes each of them
an anchor.

### Ranking

Results are ranked by resemblance to the request's inputs, as the Business
determines it. `query` and `like` both rank; `filters` narrow and never
rank. How `query` and multiple anchors combine, and whether weakly
resembling items are omitted or merely ranked low, is Business-determined —
as it is for text relevance. This specification does not define the
resemblance function, and the response does not indicate which anchor a
result resembles. A Platform **MUST NOT** infer that an item is dissimilar
from its absence.

### Exclusion

An anchor is never returned as a result. A product anchor excludes the
whole product. A variant anchor excludes that variant only; its product
**MAY** appear with its other variants. The Platform chooses accordingly:
anchor on the product ID to exclude the model, on the variant ID to allow
other colors and sizes of it. The Business **MUST** treat anchors that
resolve to the same product or variant as one anchor (so a SKU and the
variant ID it resolves to are one); a product anchor subsumes anchors on
its variants. The Business **MUST NOT** return an anchored product or
variant on any page of the result set.

### Unresolved Anchors

The Business drops an anchor that does not resolve and **SHOULD** add an
informational `not_found` message naming it, as Catalog Lookup does for an
unresolved identifier. Omitting the message is conformant but leaves the
Platform unable to tell a dropped anchor from a weak match. When no anchor
resolves, the Business **MUST** return an empty result regardless of
`query` or `filters` — the request's subject is gone, and the Business
**MUST NOT** substitute a text search or filter browse for it. An image
anchor the Business accepts (see [Image Anchors](#image-anchors)) is always
resolved; it is never dropped or reported as `not_found`.

### Unrecognized Anchor Kinds

The Business **MUST** ignore an item whose anchor key it does not recognize,
such as an extension-defined kind it does not implement. If no recognized
input remains, the [Search Inputs](../catalog/search.md#search-inputs) rule
applies.

### Anchor Limit

The Business's maximum anchor count is `config.like.max_items`.
When a request exceeds it, the Business **MUST** process the first maximum
number of distinct anchors in request order and include an informational
`batch_limit_applied` message stating the maximum and how many anchors were
not processed, as [Location Lookup](../../common/location/lookup.md#batch-size)
does for identifiers. The Business **MUST NOT** report the omitted anchors as
unresolved.

## Includes

Both `lookup_catalog` and `get_product` accept an optional `include` list
naming additional data to return with the products and variants the request
resolves. Two values are well-known; the vocabulary is open, and a Business
**MAY** support others.

| Value | Contents |
| :--- | :--- |
| `substitutes` | functionally similar items purchasable in place of the requested variant |
| `recommendations` | related items the Business selects for the product, typically complementary |

### Presence

The Business returns included data only when `include` names it. The Business
**MUST** omit a value it does not recognize or support, handling the
request otherwise as if the value were absent, and **MUST** return an empty
array for a supported value with no qualifying entries — presence means the
Business understood the request. A Platform **MUST NOT** read absence as
"none exist"; absence means the Business does not offer it. An empty
`include` is equivalent to omitting it.

### Scope

Included data is relative to the requested or featured variant
(`variants[0]`) in `get_product`, and to the variants the request
identifiers resolved to in `lookup_catalog`.

### Substitutes

A substitute is a functionally similar variant a Buyer could purchase in
place of the requested variant.

* The Business **MUST NOT** include the requested variant itself in
    `substitutes`. Another variant of the same product **MAY** appear.
* Qualifying variants of the same product share one entry, with
    `variants[]` narrowed to them. Entries, and the variants within an entry,
    are ordered most suitable first.

### Recommendations

`recommendations` are related items the Business selects for the product,
most relevant first — typically complementary ("pairs well with"). The
Business **MUST NOT** include the product itself. What counts as related is
the Business's merchandising decision; this specification does not define
it.

### Filters and Includes

`filters` narrow included entries exactly as they narrow the primary
product's variants, with the same AND semantics (see
[Filters](../catalog/lookup.md#filters)): a price filter removes variants
outside the range from each entry's `variants[]`, and the Business omits an
entry left with no variants. Filters apply to the primary product under each
operation's existing rules, which this section does not change. When a
filter excludes the requested product or variant, its included data is
excluded with it. A Platform that wants substitutes for an item that would
itself fail its filters omits those filters and narrows the returned entries
itself.

### Count and Order

Included lists are not paginated. The Business decides how many entries to
return; a Platform **MUST NOT** assume a list is complete.

## Examples

### Products Like a Variant

Products resembling a variant, within a budget. The anchored variant is
excluded; other variants of its product can appear:

<!-- ucp:example schema=shopping/catalog_similarity def=similarity_search_request op=search direction=request -->
```json
{
  "like": [
    { "id": "prod_abc123_size10" }
  ],
  "context": { "currency": "USD" },
  "filters": {
    "price": { "max": 15000 }
  },
  "pagination": { "limit": 10 }
}
```

### Query Refined by an Anchor

A text query refined by an anchor. Results are ranked by resemblance to
both the query and the product; the anchored product is excluded:

<!-- ucp:example schema=shopping/catalog_similarity def=similarity_search_request op=search direction=request -->
```json
{
  "query": "waterproof trail shoes",
  "like": [
    { "id": "prod_abc123" }
  ],
  "context": { "currency": "USD" },
  "filters": {
    "categories": ["Footwear"],
    "price": { "max": 15000 }
  }
}
```

### Image Anchor

A photo the Buyer took, refined by a text query and a budget. The Business
advertises `config.like.images` with `image/jpeg` among its `types`; results
are ranked by resemblance to both the image and the query:

<!-- ucp:example schema=shopping/catalog_similarity def=similarity_search_request op=search direction=request -->
```json
{
  "query": "waterproof trail shoes",
  "like": [
    {
      "image": {
        "content_type": "image/jpeg",
        "data": "/9j/4AAQSkZJRg..."
      }
    }
  ],
  "context": { "currency": "USD" },
  "filters": {
    "price": { "max": 15000 }
  }
}
```

### Substitutes for an Unavailable Variant

A Buyer wants a shoe in Size 10 that is out of stock. The Platform asks for
substitutes within budget:

<!-- ucp:example schema=shopping/catalog_similarity def=similarity_get_product_request op=get_product direction=request -->
```json
{
  "id": "prod_abc123_size10",
  "include": ["substitutes"],
  "filters": {
    "price": { "max": 15000 }
  },
  "context": { "currency": "USD" }
}
```

The requested variant is returned first: out of stock, and at 12000 within
the price filter. `substitutes` holds one entry per product, most
suitable first: the same shoe in Size 10 Wide, then a different shoe in
Size 10. Each entry's `variants[]` is narrowed to the qualifying variant:

<!-- ucp:example schema=shopping/catalog_similarity def=similarity_get_product_response op=get_product -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.catalog.lookup": [
        {"version": "{{ ucp_version }}"}
      ],
      "dev.ucp.shopping.catalog.similarity": [
        {
          "version": "{{ ucp_version }}",
          "extends": ["dev.ucp.shopping.catalog.lookup"]
        }
      ]
    }
  },
  "product": {
    "id": "prod_abc123",
    "title": "Blue Runner Pro",
    "description": {
      "plain": "Lightweight running shoes with responsive cushioning."
    },
    "price_range": {
      "min": { "amount": 12000, "currency": "USD" },
      "max": { "amount": 12000, "currency": "USD" }
    },
    "options": [
      {
        "name": "Size",
        "values": [
          {"label": "9", "available": true, "exists": true},
          {"label": "10", "available": false, "exists": true},
          {"label": "10 Wide", "available": true, "exists": true},
          {"label": "11", "available": true, "exists": true}
        ]
      }
    ],
    "selected": [
      { "name": "Size", "label": "10" }
    ],
    "variants": [
      {
        "id": "prod_abc123_size10",
        "title": "Size 10",
        "description": { "plain": "Size 10 variant" },
        "price": { "amount": 12000, "currency": "USD" },
        "availability": { "available": false, "status": "out_of_stock" },
        "options": [
          { "name": "Size", "label": "10" }
        ]
      }
    ],
    "substitutes": [
      {
        "id": "prod_abc123",
        "title": "Blue Runner Pro",
        "description": {
          "plain": "Lightweight running shoes with responsive cushioning."
        },
        "price_range": {
          "min": { "amount": 12000, "currency": "USD" },
          "max": { "amount": 12000, "currency": "USD" }
        },
        "variants": [
          {
            "id": "prod_abc123_size10w",
            "title": "Size 10 Wide",
            "description": { "plain": "Size 10 Wide variant" },
            "price": { "amount": 12000, "currency": "USD" },
            "availability": { "available": true },
            "options": [
              { "name": "Size", "label": "10 Wide" }
            ]
          }
        ]
      },
      {
        "id": "prod_def456",
        "title": "Trail Blazer X",
        "description": {
          "plain": "Trail shoes with superior traction."
        },
        "price_range": {
          "min": { "amount": 14500, "currency": "USD" },
          "max": { "amount": 14500, "currency": "USD" }
        },
        "variants": [
          {
            "id": "prod_def456_size10",
            "title": "Size 10",
            "description": { "plain": "Size 10 variant" },
            "price": { "amount": 14500, "currency": "USD" },
            "availability": { "available": true },
            "options": [
              { "name": "Size", "label": "10" }
            ]
          }
        ]
      }
    ]
  }
}
```

A Trail Blazer X variant priced above 15000 would be left out of its entry;
had none remained, the entry would be omitted. A Business that does not
support `substitutes` returns the same product with no `substitutes` key.
