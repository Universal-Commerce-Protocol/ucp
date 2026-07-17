# Catalog Capability

## Overview

The Catalog capability allows platforms to search and browse business product catalogs. This enables product discovery before checkout, supporting use cases like:

- Free-text product search
- Category and filter-based browsing
- Batch product/variant retrieval by identifier
- Price comparison across variants

## Capabilities

| Capability                                                                                      | Description                                       |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| [`dev.ucp.shopping.catalog.search`](http://ucp.dev/draft/specification/catalog/search/index.md) | Search for products using query text and filters. |
| [`dev.ucp.shopping.catalog.lookup`](http://ucp.dev/draft/specification/catalog/lookup/index.md) | Retrieve products or variants by identifier.      |

## Key Concepts

- **Product**: A catalog item with title, description, media, and one or more variants.
- **Variant**: A purchasable item with specific option selections (e.g., "Blue / Large"), price, and availability.
- **Price**: Price values include both amount (in minor currency units) and currency code, enabling multi-currency catalogs.

### Relationship to Checkout

Catalog operations return product and variant IDs that can be used directly in checkout `line_items[].item.id`. The variant ID from catalog retrieval should match the item ID expected by checkout.

Catalog responses (pricing, availability, etc.) reflect the Business's current terms for the given request but are not transactional commitments — checkout is authoritative. Responses can be session-specific and **SHOULD NOT** be reused across sessions without re-validation.

## Shared Entities

### Context

Location and market context for catalog operations. All fields are optional hints for relevance and localization. Platforms MAY geo-detect context from request headers.

Context signals are provisional—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data.

Businesses determine market assignment—including currency—based on context signals. Price filter values are denominated in `context.currency`; when the presentment currency differs, businesses SHOULD convert before applying (see [Price Filter](http://ucp.dev/draft/specification/catalog/search/#price-filter)). Response prices include explicit currency codes confirming the resolution.

When `context.eligibility` claims are present, Businesses that accept them **MAY** adjust `price` / `list_price` directly for strikethrough display and **MAY** use `messages` with `code: "eligibility_benefit"` to attribute the adjustment to a specific claim.

| Name            | Type                                                                                | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --------------- | ----------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| address_country | string                                                                              | Optional    | The country, as a 2-letter ISO 3166-1 alpha-2 code (e.g. "US"). A 3-letter alpha-3 code or full country name MAY also be used.                                                                                                                                                                                                                                                                                                                                     |
| address_region  | string                                                                              | Optional    | The first-level administrative region within the country (e.g. a state or province such as California).                                                                                                                                                                                                                                                                                                                                                            |
| postal_code     | string                                                                              | Optional    | The postal code (e.g. "94043").                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| intent          | string                                                                              | Optional    | Background context describing buyer's intent (e.g., 'looking for a gift under $50', 'need something durable for outdoor use'). Informs relevance, recommendations, and personalization.                                                                                                                                                                                                                                                                            |
| language        | string                                                                              | Optional    | Preferred language for content. Use IETF BCP 47 language tags (e.g., 'en', 'fr-CA', 'zh-Hans'). For REST, equivalent to Accept-Language header—platforms SHOULD fall back to Accept-Language when this field is absent; when provided, overrides Accept-Language. Businesses MAY return content in a different language if unavailable.                                                                                                                            |
| currency        | string                                                                              | Optional    | Preferred currency (ISO 4217, e.g., 'EUR', 'USD'). Businesses determine presentment currency from context and authoritative signals; this hint MAY inform selection in multi-currency markets. Also serves as the denomination for price filter values — platforms SHOULD include this field when sending price filters. Response prices include explicit currency confirming the resolution.                                                                      |
| eligibility     | Array\[[Reverse Domain Name](/draft/specification/reference/#reverse-domain-name)\] | Optional    | Buyer claims about eligible benefits such as loyalty membership, payment instrument perks, and similar. Recognized claims MAY inform the Business response (e.g., member-only product availability, adjusted pricing in catalog, provisional discounts at cart or checkout). Businesses MUST ignore unrecognized values without error. Values MUST use reverse-domain naming (e.g., 'com.example.loyalty_gold', 'org.school.student') and MUST be non-identifying. |

### Signals

Environment data provided by the platform to support authorization and abuse prevention. Signal values MUST NOT be buyer-asserted claims. See [Signals](http://ucp.dev/draft/specification/overview/#signals) for details and privacy requirements.

| Name               | Type   | Requirement | Description                                    |
| ------------------ | ------ | ----------- | ---------------------------------------------- |
| dev.ucp.buyer_ip   | string | Optional    | Client's IP address (IPv4 or IPv6).            |
| dev.ucp.user_agent | string | Optional    | Client's HTTP User-Agent header or equivalent. |

### Attribution

Platform-provided referral and conversion-event context — campaign IDs, click identifiers, and source/medium markers communicated by the platform. See [Attribution](http://ucp.dev/draft/specification/overview/#attribution) for details and consent requirements.

Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.

### Product

A catalog item representing a sellable item with one or more purchasable variants.

`media` and `variants` are ordered arrays. Businesses SHOULD return the most relevant variant and image first—default for lookups, best match based on query and context for search. Platforms SHOULD treat the first element as featured.

| Name             | Type                                                                      | Requirement  | Description                                                                                      |
| ---------------- | ------------------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------ |
| id               | string                                                                    | **Required** | Global ID (GID) uniquely identifying this product.                                               |
| handle           | string                                                                    | Optional     | URL-safe slug for SEO-friendly URLs (e.g., 'blue-runner-pro'). Use id for stable API references. |
| title            | string                                                                    | **Required** | Product title.                                                                                   |
| description      | [Description](/draft/specification/reference/#description)                | **Required** | Product description in one or more formats.                                                      |
| url              | string                                                                    | Optional     | Canonical product page URL.                                                                      |
| categories       | Array\[[Category](/draft/specification/reference/#category)\]             | Optional     | Product categories with optional taxonomy identifiers.                                           |
| price_range      | [Price Range](/draft/specification/reference/#price-range)                | **Required** | Price range across all variants.                                                                 |
| list_price_range | [Price Range](/draft/specification/reference/#price-range)                | Optional     | List price range before discounts (for strikethrough display).                                   |
| media            | Array\[[Media](/draft/specification/reference/#media)\]                   | Optional     | Product media (images, videos, 3D models). First item is the featured media for listings.        |
| options          | Array\[[Product Option](/draft/specification/reference/#product-option)\] | Optional     | Product options (Size, Color, etc.).                                                             |
| variants         | Array\[[Variant](/draft/specification/reference/#variant)\]               | **Required** | Purchasable variants of this product. First item is the featured variant for listings.           |
| rating           | [Rating](/draft/specification/reference/#rating)                          | Optional     | Aggregate product rating.                                                                        |
| tags             | Array[string]                                                             | Optional     | Product tags for categorization and search.                                                      |
| metadata         | object                                                                    | Optional     | Business-defined custom data extending the standard product model.                               |

### Variant

A purchasable item with specific option selections, price, and availability.

In lookup responses, each variant carries an `inputs` array for correlation: which request identifiers resolved to this variant, and whether the match was `exact` or `featured` (server-selected). See [Client Correlation](http://ucp.dev/draft/specification/catalog/lookup/#client-correlation) for details.

`media` is an ordered array. Businesses SHOULD return the featured variant image as the first element. Platforms SHOULD treat the first element as featured.

| Name         | Type                                                                        | Requirement  | Description                                                                               |
| ------------ | --------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------- |
| id           | string                                                                      | **Required** | Global ID (GID) uniquely identifying this variant. Used as item.id in checkout.           |
| sku          | string                                                                      | Optional     | Business-assigned identifier for inventory and fulfillment.                               |
| barcodes     | Array[object]                                                               | Optional     | Industry-standard product identifiers for cross-reference and correlation.                |
| handle       | string                                                                      | Optional     | URL-safe variant handle/slug.                                                             |
| title        | string                                                                      | **Required** | Variant display title (e.g., 'Blue / Large').                                             |
| description  | [Description](/draft/specification/reference/#description)                  | **Required** | Variant description in one or more formats.                                               |
| url          | string                                                                      | Optional     | Canonical variant page URL.                                                               |
| categories   | Array\[[Category](/draft/specification/reference/#category)\]               | Optional     | Variant categories with optional taxonomy identifiers.                                    |
| price        | [Price](/draft/specification/reference/#price)                              | **Required** | Current selling price.                                                                    |
| list_price   | [Price](/draft/specification/reference/#price)                              | Optional     | List price before discounts (for strikethrough display).                                  |
| unit_price   | object                                                                      | Optional     | Price per standard unit of measurement. MAY be omitted when unit pricing does not apply.  |
| availability | [Availability](/draft/specification/reference/#availability)                | Optional     | Variant availability for purchase.                                                        |
| options      | Array\[[Selected Option](/draft/specification/reference/#selected-option)\] | Optional     | Option values that define this variant (e.g., Color: Blue, Size: Large).                  |
| media        | Array\[[Media](/draft/specification/reference/#media)\]                     | Optional     | Variant media (images, videos, 3D models). First item is the featured media for listings. |
| rating       | [Rating](/draft/specification/reference/#rating)                            | Optional     | Variant rating.                                                                           |
| tags         | Array[string]                                                               | Optional     | Variant tags for categorization and search.                                               |
| metadata     | object                                                                      | Optional     | Business-defined custom data extending the standard variant model.                        |
| seller       | object                                                                      | Optional     | Optional seller context for this variant.                                                 |

### Price

See [Price](/draft/specification/reference/#price) in the [Schema Reference](/draft/specification/reference/) for the canonical field definition.

### Price Range

| Name | Type                                           | Requirement  | Description                 |
| ---- | ---------------------------------------------- | ------------ | --------------------------- |
| min  | [Price](/draft/specification/reference/#price) | **Required** | Minimum price in the range. |
| max  | [Price](/draft/specification/reference/#price) | **Required** | Maximum price in the range. |

### Media

See [Media](/draft/specification/reference/#media) in the [Schema Reference](/draft/specification/reference/) for the canonical field definition.

### Product Option

| Name   | Type                                                                  | Requirement  | Description                          |
| ------ | --------------------------------------------------------------------- | ------------ | ------------------------------------ |
| name   | string                                                                | **Required** | Option name (e.g., 'Size', 'Color'). |
| values | Array\[[Option Value](/draft/specification/reference/#option-value)\] | **Required** | Available values for this option.    |

### Option Value

| Name  | Type   | Requirement  | Description                                                                                                                                           |
| ----- | ------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| id    | string | Optional     | Optional server-assigned identifier for this option value. When present in a selected_option, the server SHOULD use it for matching instead of label. |
| label | string | **Required** | Display text for this option value (e.g., 'Small', 'Blue').                                                                                           |

### Selected Option

| Name  | Type   | Requirement  | Description                                                                                                                                             |
| ----- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| name  | string | **Required** | Option name (e.g., 'Size').                                                                                                                             |
| id    | string | Optional     | Optional option value identifier from option_value.id. When present, the server SHOULD use it for matching; name and label remain required for display. |
| label | string | **Required** | Selected option label (e.g., 'Large').                                                                                                                  |

### Rating

| Name      | Type    | Requirement  | Description                                                |
| --------- | ------- | ------------ | ---------------------------------------------------------- |
| value     | number  | **Required** | Average rating value.                                      |
| scale_min | number  | Optional     | Minimum value on the rating scale (e.g., 1 for 1-5 stars). |
| scale_max | number  | **Required** | Maximum value on the rating scale (e.g., 5 for 5-star).    |
| count     | integer | Optional     | Number of reviews contributing to the rating.              |

## Messages and Error Handling

All catalog responses include an optional `messages` array that allows businesses to provide context about errors, warnings, or informational notices.

### Message Types

Messages communicate business outcomes and provide context:

| Type      | When to Use                             | Example Codes                                    |
| --------- | --------------------------------------- | ------------------------------------------------ |
| `error`   | Business-level errors                   | `NOT_FOUND`, `OUT_OF_STOCK`, `REGION_RESTRICTED` |
| `warning` | Important conditions affecting purchase | `DELAYED_FULFILLMENT`, `FINAL_SALE`              |
| `info`    | Additional context without issues       | `PROMOTIONAL_PRICING`, `LIMITED_AVAILABILITY`    |

Warnings with `presentation: "disclosure"` carry notices (e.g., allergen declarations, safety warnings) that platforms must not hide or dismiss. See [Warning Presentation](http://ucp.dev/draft/specification/checkout/#warning-presentation) for the full rendering contract.

**Note**: Most catalog errors use `severity: "recoverable"` - agents handle them programmatically (retry, inform user, show alternatives). `get_product` returns `severity: "unrecoverable"` when an identifier doesn't resolve; agents MUST NOT retry the same `id` (see the [REST](http://ucp.dev/draft/specification/catalog/rest/#product-not-found) and [MCP](http://ucp.dev/draft/specification/catalog/mcp/#product-not-found) examples).

#### Message (Error)

See [Message Error](/draft/specification/reference/#message-error) in the [Schema Reference](/draft/specification/reference/) for the canonical field definition.

#### Message (Warning)

See [Message Warning](/draft/specification/reference/#message-warning) in the [Schema Reference](/draft/specification/reference/) for the canonical field definition.

#### Message (Info)

See [Message Info](/draft/specification/reference/#message-info) in the [Schema Reference](/draft/specification/reference/) for the canonical field definition.

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

When a product is available but has delayed fulfillment, return the product with a warning message. Use the `path` field to target specific variants.

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

Agents can present the option and inform the user about the delay. The `path` field uses RFC 9535 JSONPath to target specific components.

#### Identifiers Not Found

When requested identifiers don't exist, return success with the found products (if any). The response MAY include informational messages indicating which identifiers were not found.

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

Agents correlate results using the `inputs` array on each variant. See [Client Correlation](http://ucp.dev/draft/specification/catalog/lookup/#client-correlation).

#### Product Disclosure

When a product requires a disclosure (e.g., allergen notice, safety warning), return it as a warning with `presentation: "disclosure"`. The `path` field targets the relevant component in the response — when it targets a product, the disclosure applies to all of its variants.

```json
{
  "ucp": {...},
  "products": [
    {
      "id": "prod_nut_butter",
      "title": "Artisan Nut Butter Collection",
      "description": { "plain": "Assorted artisan nut butters." },
      "price_range": {
        "min": { "amount": 1299, "currency": "USD" },
        "max": { "amount": 1499, "currency": "USD" }
      },
      "variants": [
        {
          "id": "var_almond",
          "title": "Almond Butter",
          "description": { "plain": "Smooth almond butter." },
          "price": { "amount": 1299, "currency": "USD" },
          "availability": { "available": true }
        },
        {
          "id": "var_cashew",
          "title": "Cashew Butter",
          "description": { "plain": "Creamy cashew butter." },
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

See [Warning Presentation](http://ucp.dev/draft/specification/checkout/#warning-presentation) for the full rendering contract.

## Scopes

The Catalog Search and Catalog Lookup capabilities define the following well-known scopes for user-authenticated access:

| Scope                                  | Description                                                                                              |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `dev.ucp.shopping.catalog.search:read` | Search on behalf of the authenticated user — personalized results, member pricing, gated inventory.      |
| `dev.ucp.shopping.catalog.lookup:read` | Lookup on behalf of the authenticated user — personalized pricing or availability for specific products. |

Scope declaration, derivation, and rules for extending this set with custom scopes are defined in [Identity Linking — Scopes](http://ucp.dev/draft/specification/identity-linking/#scopes).

## Transport Bindings

The capabilities above are bound to specific transport protocols:

- [REST Binding](http://ucp.dev/draft/specification/catalog/rest/index.md): RESTful API mapping.
- [MCP Binding](http://ucp.dev/draft/specification/catalog/mcp/index.md): Model Context Protocol mapping via JSON-RPC.
