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

# Catalog Recommendations Extension

* **Capability Name:** `dev.ucp.shopping.catalog.recommendations`
* **Extends:** `dev.ucp.shopping.catalog.search`

## Overview

The Catalog Recommendations extension lets a Platform ask a Business for
items related to catalog items the Platform already knows: items that resemble
a product the Buyer is viewing, items that go with a product or a cart, and a
replacement for an item that is unavailable. The Business owns the judgment of
what is related; this extension defines how a Platform asks for it and what
the answer guarantees.

This extension adds two fields to the Catalog Search request:

* `purpose`: the relation the results bear to the references (`similar`,
    `complementary`, or `substitute`; `search` is the default).
* `references`: the anchors for the request. Each reference names a product
    or variant by `id`; other extensions can define additional kinds of
    anchor.

Responses are ordinary Catalog Search responses. Every returned item is a
`products[]` entry, so other extensions that enrich Catalog Search results
(for example, [Fulfillment](fulfillment.md)) apply to recommended items
without further composition.

**Dependencies:**

* Catalog Search (`dev.ucp.shopping.catalog.search`).

## Discovery

Support for each relation varies by Business: recommendations often run on a
separate merchandising service, and substitution is common in grocery,
pharmacy, and B2B catalogs. A Business declares the extension and lists the
relations it supports in `config.relations`:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.catalog.recommendations": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.catalog.search",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/recommendations",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/catalog_recommendations.json",
          "config": {
            "relations": {
              "complementary": { "max_references": 20 },
              "substitute": {}
            }
          }
        }
      ]
    }
  }
}
```

A Platform that supports the extension declares it in its own profile without
`config`. The extension is active only when both parties declare it and Catalog
Search is in the negotiated intersection (see
[Intersection Algorithm](../../overview/index.md#intersection-algorithm)).
A Platform reads `config.relations` from the profile it already fetches, so it
knows before calling which relations it can offer.

### Configuration

{{ extension_schema_fields('catalog_recommendations.json#/$defs/business_config', 'shopping/extensions/recommendations') }}

Each entry in `config.relations` is a relation policy. An empty object means the
relation is supported with no advertised limits.

{{ extension_schema_fields('catalog_recommendations.json#/$defs/relation_policy', 'shopping/extensions/recommendations') }}

## Schema

{{ extension_schema_fields('catalog_recommendations.json#/$defs/recommendations_search_request', 'shopping/extensions/recommendations') }}

### Reference

{{ extension_schema_fields('catalog_recommendations.json#/$defs/reference', 'shopping/extensions/recommendations') }}

## Relations

| `purpose` | Returns | `references` |
| :-- | :-- | :-- |
| `search` (default) | Text or filter results, as in [Catalog Search](../catalog/search.md) | Ignored |
| `similar` | Alternatives that resemble the anchors ("more like this") | One or more; one joint anchor set |
| `complementary` | Items that go with the anchors (cross-sell, basket completion) | One or more; one joint anchor set |
| `substitute` | A replacement for one specific item, for the same need | Exactly one |

A request names the relation it wants in `purpose`; a Business advertises the
relations it answers in `config.relations`.

The vocabulary is open. A Business **MAY** support additional values, and
lists every value it supports in `config.relations`.

## Rules

1. **Negotiation**: A Platform **MUST NOT** send a `purpose` other than
    `search` unless this extension is active and the value is a key of
    `config.relations`.
2. **Pairing**: When `purpose` is `similar` or `complementary`, `references`
    **MUST** contain at least one reference; multiple references jointly
    describe one anchor set, results relate to that set as a whole, and the
    response does not correlate results to individual anchors. When `purpose`
    is `substitute`, `references` **MUST** contain exactly one reference, and
    it **MUST** carry an `id`; a Platform that needs substitutes for several
    items sends one request per item. When `purpose` is `search` (or omitted),
    the Business **MUST** ignore `references`, and the request follows the
    [Search Inputs](../catalog/search.md#search-inputs) requirements. A
    Business **MUST** reject a request that violates these rules using the
    binding's invalid-request mechanism, never with an empty or general result.
3. **Anchor Kinds**: Each reference carries exactly one anchor kind. This
    extension defines `id`, which names a product or variant in the Business's
    catalog. Other extensions **MAY** define additional anchor kinds as
    additional reference properties, together with their own discovery and
    rules. A Business that does not recognize a reference's anchor kind drops
    that reference and **SHOULD** include an informational
    `unsupported_reference` message whose `path` points at it.
4. **Resolution**: A Business **MUST** resolve an `id` by product ID and
    variant ID, and **MAY** additionally resolve the secondary identifiers
    permitted by [Catalog Lookup](../catalog/lookup.md#supported-identifiers).
    An `id` that does not resolve is dropped, and the Business **SHOULD**
    include an informational `not_found` message naming it. When no reference
    remains after dropping unresolved and unrecognized references, the
    Business **MUST** return an empty `products` array, regardless of `query`
    or `filters`; it **MUST NOT** fall back to a general search or browse.
5. **Substitute Target**: For `substitute`, a reference whose `id` resolves
    to more than one product or variant has no single item to replace (a
    product ID is one anchor even when the product has several variants). The
    Business **MUST NOT** choose one. It drops the reference as it would an
    unresolved one and **SHOULD** include an informational
    `ambiguous_reference` message whose `path` points at the reference and
    whose `content` names the matching identifiers, so the Platform can resend
    with one of them; as [Catalog Lookup](../catalog/lookup.md) already treats
    an identifier matching several products as a successful outcome, so does
    this extension. When no reference remains, the empty result of the
    Resolution rule applies. A Platform replacing a cart line **SHOULD** use
    that line's product or variant ID.
6. **Exclusion**: Catalog anchors are never returned, on any page of the
    result set. A product anchor excludes the whole product. A variant anchor
    excludes that variant; other variants of its product **MAY** be returned,
    except for `complementary`, where the Business **MUST** also exclude the
    product of every catalog anchor. An excluded variant **MUST NOT** appear
    in `variants[]`, and a product left with no returnable variants is
    omitted.
7. **Anchor Limit**: A Business **MAY** limit the number of references it
    processes and **SHOULD** advertise the limit as `max_references`. When a
    request exceeds its limit, the Business processes the first distinct
    references in request order up to the limit and includes an informational
    `batch_limit_applied` message stating the limit and how many references
    were not processed. References that were not processed **MUST NOT** be
    reported as `not_found`.
8. **Query and Filters**: A request **MAY** combine `references` with
    `query`, which guides ranking (for example, a substitute that is also
    waterproof), and with `filters`. Supplied `filters` narrow the returned
    candidates with the `AND` semantics of
    [Search Filters](../catalog/search.md#search-filters); they do not
    constrain resolution of `references`, so an unavailable item still
    anchors a request whose filters it fails. For `substitute`, the anchor's
    attributes guide relevance but are not matching constraints: a Platform
    **MUST NOT** assume a result preserves pack size, `quantity_unit`, or
    compatibility solely because the request used `substitute`. Hard
    constraints come only from supported `filters` and negotiated extensions.
    Checkout remains authoritative (see
    [Relationship to Checkout](../catalog/index.md#relationship-to-checkout)).
9. **Unsupported Purpose**: A Business **MUST NOT** ignore `purpose`. A
    Business that receives a value it has not advertised (for example, from a
    Platform acting on a stale profile) **MUST** return `ucp.status: "error"`
    with an `error` message whose `code` is `unsupported_purpose`, whose
    `severity` is `recoverable`, and whose `content` names the relations it
    supports, together with an empty `products` array; it **MUST NOT** answer
    with a general search.
10. **Buyer Identity**: Results reflect the Business's judgment about the
    anchors and are valid without buyer identity. A Business **MAY**
    personalize results for a buyer-authenticated request.

## Composition

This extension composes onto the Catalog Search request only. Results are
`search_response.products[]` entries, so every extension that enriches Catalog
Search results applies to them. With the [Fulfillment](fulfillment.md)
extension active, `filters.fulfills_to` and `filters.methods` narrow the
candidates, and each returned variant carries its `fulfillment` methods.

## Examples

### Substitute for Store Pickup

A cart line is out of stock at the Buyer's store. The Platform asks for a
replacement that can be picked up there, within budget. The unavailable item
still anchors the request even though it fails the pickup filter; the filters
apply to the candidates:

<!-- ucp:example schema=shopping/catalog_recommendations def=recommendations_search_request op=search direction=request -->
```json
{
  "purpose": "substitute",
  "references": [{ "id": "prod_abc123_size10" }],
  "context": { "currency": "USD" },
  "filters": {
    "fulfills_to": { "location": "loc_downtown" },
    "methods": ["pickup"],
    "price": { "max": 15000 }
  },
  "pagination": { "limit": 5 }
}
```

The anchor variant is excluded. Because the anchor was a variant, another
variant of the same product (Size 10 Wide) can be returned. With Fulfillment
active, each result carries its pickup availability:

<!-- ucp:example schema=shopping/fulfillment def=fulfillment_search_response op=search -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.catalog.recommendations": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.fulfillment": [{ "version": "{{ ucp_version }}" }]
    }
  },
  "products": [
    {
      "id": "prod_abc123",
      "title": "Blue Runner Pro",
      "description": { "plain": "Lightweight running shoes." },
      "price_range": {
        "min": { "amount": 12000, "currency": "USD" },
        "max": { "amount": 12000, "currency": "USD" }
      },
      "variants": [
        {
          "id": "prod_abc123_size10w",
          "title": "Size 10 Wide",
          "description": { "plain": "Size 10 Wide" },
          "price": { "amount": 12000, "currency": "USD" },
          "availability": { "available": true },
          "options": [{ "name": "Size", "label": "10 Wide" }],
          "fulfillment": {
            "methods": [
              {
                "type": "pickup",
                "location": "loc_downtown",
                "availability": { "available": true }
              }
            ]
          }
        }
      ]
    },
    {
      "id": "prod_def456",
      "title": "Trail Blazer X",
      "description": { "plain": "Waterproof trail shoes." },
      "price_range": {
        "min": { "amount": 14500, "currency": "USD" },
        "max": { "amount": 14500, "currency": "USD" }
      },
      "variants": [
        {
          "id": "prod_def456_size10",
          "title": "Size 10",
          "description": { "plain": "Size 10" },
          "price": { "amount": 14500, "currency": "USD" },
          "availability": { "available": true },
          "options": [{ "name": "Size", "label": "10" }],
          "fulfillment": {
            "methods": [
              {
                "type": "pickup",
                "location": "loc_downtown",
                "availability": { "available": true }
              }
            ]
          }
        }
      ]
    }
  ],
  "pagination": { "has_next_page": false }
}
```

### Guided Substitute

`query` steers the replacement toward the Buyer's stated preference:

<!-- ucp:example schema=shopping/catalog_recommendations def=recommendations_search_request op=search direction=request -->
```json
{
  "purpose": "substitute",
  "references": [{ "id": "prod_abc123_size10" }],
  "query": "waterproof",
  "context": { "currency": "USD" }
}
```

### Ambiguous Substitute Reference

A substitute request names a shared SKU (`TEE-BLK`) that matches two variants.
Rather than guess, the Business drops the reference and names the matches; the
Platform resends with the variant ID from the cart line:

<!-- ucp:example schema=shopping/catalog_search op=search -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.catalog.recommendations": [{ "version": "{{ ucp_version }}" }]
    }
  },
  "products": [],
  "pagination": { "has_next_page": false },
  "messages": [
    {
      "type": "info",
      "code": "ambiguous_reference",
      "path": "$.references[0].id",
      "content": "TEE-BLK matches prod_tee_black_m and prod_tee_black_l; resend with one of these IDs."
    }
  ]
}
```

The Platform resends with the variant ID from the cart line:

<!-- ucp:example schema=shopping/catalog_recommendations def=recommendations_search_request op=search direction=request -->
```json
{
  "purpose": "substitute",
  "references": [{ "id": "prod_tee_black_m" }]
}
```

### Goes Well With

Complementary items for a product the Buyer is viewing. The tent itself is
never returned:

<!-- ucp:example schema=shopping/catalog_recommendations def=recommendations_search_request op=search direction=request -->
```json
{
  "purpose": "complementary",
  "references": [{ "id": "prod_tent_4p" }],
  "context": { "address_country": "US", "currency": "USD" },
  "pagination": { "limit": 4 }
}
```

### Basket Completion

Complementary items for a whole cart, narrowed to two categories. The anchors
form one joint set, and every anchor's product is excluded on every page:

<!-- ucp:example schema=shopping/catalog_recommendations def=recommendations_search_request op=search direction=request -->
```json
{
  "purpose": "complementary",
  "references": [{ "id": "prod_tent_4p" }, { "id": "prod_stove_2b" }],
  "filters": { "categories": ["Sleeping Bags", "Camp Lighting"] },
  "context": { "address_country": "US", "currency": "USD" },
  "pagination": { "limit": 10 }
}
```

### Similar but Cheaper

Alternatives that resemble a product, within a lower price range:

<!-- ucp:example schema=shopping/catalog_recommendations def=recommendations_search_request op=search direction=request -->
```json
{
  "purpose": "similar",
  "references": [{ "id": "prod_abc123" }],
  "filters": { "price": { "max": 10000 } },
  "context": { "currency": "USD" },
  "pagination": { "limit": 10 }
}
```

### Anchor Limit and Unresolved Anchors

A Business advertising `max_references: 20` receives 24 references, one
of which is unknown. It processes the first 20 and reports both outcomes:

<!-- ucp:example schema=shopping/catalog_search op=search -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.catalog.recommendations": [{ "version": "{{ ucp_version }}" }]
    }
  },
  "products": [
    {
      "id": "prod_lantern_led",
      "title": "LED Camp Lantern",
      "description": { "plain": "Rechargeable 400-lumen lantern." },
      "price_range": {
        "min": { "amount": 2900, "currency": "USD" },
        "max": { "amount": 2900, "currency": "USD" }
      },
      "variants": [
        {
          "id": "prod_lantern_led_std",
          "title": "Standard",
          "description": { "plain": "Standard" },
          "price": { "amount": 2900, "currency": "USD" },
          "availability": { "available": true }
        }
      ]
    }
  ],
  "pagination": { "has_next_page": false },
  "messages": [
    {
      "type": "info",
      "code": "batch_limit_applied",
      "path": "$.references",
      "content": "Processed the first 20 of 24 references."
    },
    {
      "type": "info",
      "code": "not_found",
      "content": "prod_retired_001"
    }
  ]
}
```

### MCP Tool Call

<!-- ucp:example schema=shopping/catalog_recommendations def=recommendations_search_request op=search direction=request extract=$.params.arguments.catalog -->
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "search_catalog",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://agent.example/profiles/shopping-agent.json"
        }
      },
      "catalog": {
        "purpose": "complementary",
        "references": [{ "id": "prod_tent_4p" }],
        "pagination": { "limit": 4 }
      }
    }
  }
}
```

## Out of Scope

This extension does not define:

* Recommendations without anchors (for example, recommendations derived from
    `context` alone). A Business can offer them under an additional `purpose`
    value it lists in `config.relations`.
* Related items returned inline with Catalog Lookup or Get Product results.
* Anchor kinds other than `id`, such as inline images or items outside the
    Business's catalog. Other extensions can define them as additional
    reference properties (see the Anchor Kinds rule).
* Substitution preferences that a Buyer sets on a cart, checkout, or order
    line.
