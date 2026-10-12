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

# Catalog Capability

## Overview

The Catalog capability allows platforms to search and browse business product catalogs.
This enables product discovery before checkout, supporting use cases like:

* Free-text product search
* Category and filter-based browsing
* Batch product/variant retrieval by identifier
* Price comparison across variants

## Capabilities

| Capability | Description |
| :--- | :--- |
| [`dev.ucp.shopping.catalog.search`](search.md) | Search for products using query text and filters. |
| [`dev.ucp.shopping.catalog.lookup`](lookup.md) | Retrieve products or variants by identifier. |

## Key Concepts

* **Product**: A catalog item with title, description, media, and one or more
  variants.
* **Variant**: A purchasable item with specific option selections (e.g., "Blue /
  Large"), price, and availability.
* **Price**: Price values include both amount (in minor currency units) and
  currency code, enabling multi-currency catalogs.

### Relationship to Checkout

Catalog operations return product and variant IDs that can be used directly in
checkout `line_items[].item.id`. The variant ID from catalog retrieval should match
the item ID expected by checkout.

Catalog responses (pricing, availability, etc.) reflect the Business's current
terms for the given request but are not transactional commitments — checkout
is authoritative. Responses can be session-specific and **SHOULD NOT** be
reused across sessions without re-validation.

## Shared Entities

### Context

Location and market context for catalog operations. All fields are optional
hints for relevance and localization. Platforms MAY geo-detect context from
request headers.

Context signals are provisional—not authoritative data. Businesses SHOULD use
these values when verified inputs (e.g., shipping address) are absent, and MAY
ignore or down-rank them if inconsistent with higher-confidence signals
(authenticated account, risk detection) or regulatory constraints (export
controls). Eligibility and policy enforcement MUST occur at checkout time using
binding transaction data.

Businesses determine market assignment—including currency—based on context
signals. Price filter values are denominated in `context.currency`; when
the presentment currency differs, businesses SHOULD convert before applying
(see [Price Filter](search.md#price-filter)). Response prices include
explicit currency codes confirming the resolution.

When `context.eligibility` claims are present, Businesses that accept them
**MAY** adjust `price` / `list_price` directly for strikethrough display and
**MAY** use `messages` with `code: "eligibility_benefit"` to attribute the
adjustment to a specific claim.

{{ schema_fields('types/context', 'catalog') }}

### Signals

Environment data provided by the platform to support authorization
and abuse prevention. Signal values MUST NOT be buyer-asserted claims. See
[Signals](../overview.md#signals) for details and privacy requirements.

{{ schema_fields('types/signals', 'catalog') }}

### Attribution

Platform-provided referral and conversion-event context — campaign IDs,
click identifiers, and source/medium markers communicated by the platform.
See [Attribution](../overview.md#attribution) for details and consent
requirements.

{{ schema_fields('types/attribution', 'catalog') }}

### Product

A catalog item representing a sellable item with one or more purchasable variants.

`media` and `variants` are ordered arrays. Businesses **SHOULD** return the
most relevant variant and media item first — default for lookups, best match
based on query and context for search. Platforms **SHOULD** treat the first
media item they present as featured.

{{ schema_fields('types/product', 'catalog') }}

### Variant

A purchasable item with specific option selections, price, and availability.

In lookup responses, each variant carries an `inputs` array for correlation:
which request identifiers resolved to this variant, and whether the match
was `exact` or `featured` (server-selected). See
[Client Correlation](lookup.md#client-correlation) for details.

`media` is an ordered array. Businesses **SHOULD** return the featured variant
media item as the first element. Platforms **SHOULD** treat the first media
item they present as featured.

{{ schema_fields('types/variant', 'catalog') }}

### Price

{{ schema_fields('types/price', 'catalog') }}

### Price Range

{{ schema_fields('types/price_range', 'catalog') }}

### Media

One logical media item on a Product or Variant — such as an image, a video, or
a 3D model. A media item is a resource the Platform renders: `url` identifies
it, `sources` lists alternate renditions of it, `preview` is a still the
Platform can show before or instead of it, and `width` and `height` are its
intrinsic pixel dimensions. The `width` and `height` on `preview` and on each
`sources` entry are the pixel dimensions of that still or rendition.

`type` is an open string with four well-known values: `image`, `video`,
`external_video`, and `model_3d`. A Platform **MUST NOT** reject a product or
response because it does not recognize a media item's `type`. It **MAY**
present such an item from `preview` and `name`, or omit it. Recognizing a
`type` only enables type-specific presentation.

A Platform **MAY** refuse to load or embed a media URL that does not use the
`https` scheme.

A Platform selects a rendition from `sources` by `mime_type` and dimensions. A
Business that provides `sources` **SHOULD** include the rendition at `url`.

{{ schema_fields('types/media', 'catalog') }}

#### Image

`url` is a directly displayable image. `sources`, when present, lists alternate
encodings and sizes of it — for example `image/avif`, `image/webp`, and
`image/jpeg`, or width variants for responsive layout. The Business **SHOULD**
make `url` the most broadly decodable rendition, because a Platform that does
not select from `sources` loads `url` directly.

{{ schema_fields('types/media_image', 'catalog') }}

#### Video

`url` is a playable rendition of the video: a progressive file or an
adaptive-streaming manifest. `sources`, when present, lists alternate
renditions and manifests.

{{ schema_fields('types/media_video', 'catalog') }}

#### External Video

A video presented through a third-party player. `url` is the player, which the
Platform embeds; a video the Business serves as files from any origin,
including a CDN, is `video`. A Platform that does not embed third-party players
presents `preview` or omits the item.

A Platform that embeds the player **MUST** isolate it from the Platform's
authority: no Platform credentials, no access to Platform APIs or agent tools,
no protocol messaging privileges, and no navigation of the host application.
Before embedding, it **MUST** decline the item unless `url` is an absolute
`https` URL without userinfo that is not same-site with the Platform. On the
web, the player is one iframe whose `src` is `url`, sandboxed and
credentialless, granting only the capabilities the player needs:

```html
<iframe sandbox="allow-scripts allow-same-origin" allow="fullscreen" credentialless src="https://videos.example.com/embed/123"></iframe>
```

See
[Iframe Sandbox Attributes](../embedded-protocol.md#iframe-sandbox-attributes)
and [Credentialless Iframes](../embedded-protocol.md#credentialless-iframes).

{{ schema_fields('types/media_external_video', 'catalog') }}

#### 3D Model

`url` is the primary model file, such as GLB. `sources`, when present, lists
alternate formats such as glTF and USDZ.

{{ schema_fields('types/media_model_3d', 'catalog') }}

### Product Option

{{ schema_fields('types/product_option', 'catalog') }}

### Option Value

{{ schema_fields('types/option_value', 'catalog') }}

### Selected Option

{{ schema_fields('types/selected_option', 'catalog') }}

### Rating

{{ schema_fields('types/rating', 'catalog') }}

## Messages and Error Handling

All catalog responses include an optional `messages` array that allows businesses
to provide context about errors, warnings, or informational notices.

### Message Types

Messages communicate business outcomes and provide context:

| Type | When to Use | Example Codes |
| :--- | :--- | :--- |
| `error` | Business-level errors | `NOT_FOUND`, `OUT_OF_STOCK`, `REGION_RESTRICTED` |
| `warning` | Important conditions affecting purchase | `DELAYED_FULFILLMENT`, `FINAL_SALE` |
| `info` | Additional context without issues | `PROMOTIONAL_PRICING`, `LIMITED_AVAILABILITY` |

Warnings with `presentation: "disclosure"` carry notices (e.g., allergen
declarations, safety warnings) that platforms must not hide or dismiss. See
[Warning Presentation](../checkout.md#warning-presentation) for the full
rendering contract.

**Note**: All catalog errors use `severity: "recoverable"` - agents handle them programmatically (retry, inform user, show alternatives).

#### Message (Error)

{{ schema_fields('types/message_error', 'catalog') }}

#### Message (Warning)

{{ schema_fields('types/message_warning', 'catalog') }}

#### Message (Info)

{{ schema_fields('types/message_info', 'catalog') }}

### Common Scenarios

#### Empty Search

When search finds no matches, return an empty array without messages.

```json
{
  "ucp": {...},
  "products": []
}
```

This is not an error - the query was valid but returned no results.

#### Backorder Warning

When a product is available but has delayed fulfillment, return the product with
a warning message. Use the `path` field to target specific variants.

```json
{
  "ucp": {...},
  "products": [
    {
      "id": "prod_xyz789",
      "title": "Professional Chef Knife Set",
      "description": { "plain": "Complete professional knife collection." },
      "price_range": {
        "min": { "amount": 29900, "currency": "USD" },
        "max": { "amount": 29900, "currency": "USD" }
      },
      "variants": [
        {
          "id": "var_abc",
          "title": "12-piece Set",
          "description": { "plain": "Complete professional knife collection." },
          "price": { "amount": 29900, "currency": "USD" },
          "availability": { "available": true }
        }
      ]
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "delayed_fulfillment",
      "path": "$.products[0].variants[0]",
      "content": "12-piece set on backorder, ships in 2-3 weeks"
    }
  ]
}
```

Agents can present the option and inform the user about the delay. The `path`
field uses RFC 9535 JSONPath to target specific components.

#### Identifiers Not Found

When requested identifiers don't exist, return success with the found products
(if any). The response MAY include informational messages indicating which
identifiers were not found.

```json
{
  "ucp": {...},
  "products": [],
  "messages": [
    {
      "type": "info",
      "code": "not_found",
      "content": "prod_invalid"
    }
  ]
}
```

Agents correlate results using the `inputs` array on each variant. See
[Client Correlation](lookup.md#client-correlation).

#### Product Disclosure

When a product requires a disclosure (e.g., allergen notice, safety warning),
return it as a warning with `presentation: "disclosure"`. The `path` field targets the
relevant component in the response — when it targets a product, the
disclosure applies to all of its variants.

```json
{
  "ucp": {...},
  "products": [
    {
      "id": "prod_nut_butter",
      "title": "Artisan Nut Butter Collection",
      "variants": [
        {
          "id": "var_almond",
          "title": "Almond Butter",
          "price": { "amount": 1299, "currency": "USD" },
          "availability": { "available": true }
        },
        {
          "id": "var_cashew",
          "title": "Cashew Butter",
          "price": { "amount": 1499, "currency": "USD" },
          "availability": { "available": true }
        }
      ]
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "allergens",
      "path": "$.products[0]",
      "content": "**Contains: tree nuts.** Produced in a facility that also processes peanuts, milk, and soy.",
      "content_type": "markdown",
      "presentation": "disclosure",
      "image_url": "https://merchant.com/allergen-tree-nuts.svg",
      "url": "https://merchant.com/allergen-info"
    }
  ]
}
```

See [Warning Presentation](../checkout.md#warning-presentation) for the
full rendering contract.

## Scopes

The Catalog Search and Catalog Lookup capabilities define the following
well-known scopes for user-authenticated access:

| Scope | Description |
| :--- | :--- |
| `dev.ucp.shopping.catalog.search:read` | Search on behalf of the authenticated user — personalized results, member pricing, gated inventory. |
| `dev.ucp.shopping.catalog.lookup:read` | Lookup on behalf of the authenticated user — personalized pricing or availability for specific products. |

Scope declaration, derivation, and rules for extending this set with
custom scopes are defined in [Identity Linking — Scopes](../identity-linking.md#scopes).

## Transport Bindings

The capabilities above are bound to specific transport protocols:

* [REST Binding](rest.md): RESTful API mapping.
* [MCP Binding](mcp.md): Model Context Protocol mapping via JSON-RPC.
