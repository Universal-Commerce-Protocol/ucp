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

| Name            | Type                                                                                | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --------------- | ----------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| address_country | string                                                                              | No       | The country. Recommended to be in 2-letter ISO 3166-1 alpha-2 format, for example "US". For backward compatibility, a 3-letter ISO 3166-1 alpha-3 country code such as "SGP" or a full country name such as "Singapore" can also be used. Optional hint for market context (currency, availability, pricing)—higher-resolution data (e.g., shipping address) supersedes this value.                                                                                |
| address_region  | string                                                                              | No       | The region in which the locality is, and which is in the country. For example, California or another appropriate first-level Administrative division. Optional hint for progressive localization—higher-resolution data (e.g., shipping address) supersedes this value.                                                                                                                                                                                            |
| postal_code     | string                                                                              | No       | The postal code. For example, 94043. Optional hint for regional refinement—higher-resolution data (e.g., shipping address) supersedes this value.                                                                                                                                                                                                                                                                                                                  |
| intent          | string                                                                              | No       | Background context describing buyer's intent (e.g., 'looking for a gift under $50', 'need something durable for outdoor use'). Informs relevance, recommendations, and personalization.                                                                                                                                                                                                                                                                            |
| language        | string                                                                              | No       | Preferred language for content. Use IETF BCP 47 language tags (e.g., 'en', 'fr-CA', 'zh-Hans'). For REST, equivalent to Accept-Language header—platforms SHOULD fall back to Accept-Language when this field is absent; when provided, overrides Accept-Language. Businesses MAY return content in a different language if unavailable.                                                                                                                            |
| currency        | string                                                                              | No       | Preferred currency (ISO 4217, e.g., 'EUR', 'USD'). Businesses determine presentment currency from context and authoritative signals; this hint MAY inform selection in multi-currency markets. Also serves as the denomination for price filter values — platforms SHOULD include this field when sending price filters. Response prices include explicit currency confirming the resolution.                                                                      |
| eligibility     | Array\[[Reverse Domain Name](/draft/specification/reference/#reverse-domain-name)\] | No       | Buyer claims about eligible benefits such as loyalty membership, payment instrument perks, and similar. Recognized claims MAY inform the Business response (e.g., member-only product availability, adjusted pricing in catalog, provisional discounts at cart or checkout). Businesses MUST ignore unrecognized values without error. Values MUST use reverse-domain naming (e.g., 'com.example.loyalty_gold', 'org.school.student') and MUST be non-identifying. |

### Signals

Environment data provided by the platform to support authorization and abuse prevention. Signal values MUST NOT be buyer-asserted claims. See [Signals](http://ucp.dev/draft/specification/overview/#signals) for details and privacy requirements.

| Name               | Type   | Required | Description                                    |
| ------------------ | ------ | -------- | ---------------------------------------------- |
| dev.ucp.buyer_ip   | string | No       | Client's IP address (IPv4 or IPv6).            |
| dev.ucp.user_agent | string | No       | Client's HTTP User-Agent header or equivalent. |

### Attribution

Platform-provided referral and conversion-event context — campaign IDs, click identifiers, and source/medium markers communicated by the platform. See [Attribution](http://ucp.dev/draft/specification/overview/#attribution) for details and consent requirements.

Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.

### Product

A catalog item representing a sellable item with one or more purchasable variants.

`media` and `variants` are ordered arrays. Businesses SHOULD return the most relevant variant and image first—default for lookups, best match based on query and context for search. Platforms SHOULD treat the first element as featured.

| Name             | Type                                                                      | Required | Description                                                                                      |
| ---------------- | ------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------ |
| id               | string                                                                    | **Yes**  | Global ID (GID) uniquely identifying this product.                                               |
| handle           | string                                                                    | No       | URL-safe slug for SEO-friendly URLs (e.g., 'blue-runner-pro'). Use id for stable API references. |
| title            | string                                                                    | **Yes**  | Product title.                                                                                   |
| description      | [Description](/draft/specification/reference/#description)                | **Yes**  | Product description in one or more formats.                                                      |
| url              | string                                                                    | No       | Canonical product page URL.                                                                      |
| categories       | Array\[[Category](/draft/specification/reference/#category)\]             | No       | Product categories with optional taxonomy identifiers.                                           |
| price_range      | [Price Range](/draft/specification/reference/#price-range)                | **Yes**  | Price range across all variants.                                                                 |
| list_price_range | [Price Range](/draft/specification/reference/#price-range)                | No       | List price range before discounts (for strikethrough display).                                   |
| media            | Array\[[Media](/draft/specification/reference/#media)\]                   | No       | Product media (images, videos, 3D models). First item is the featured media for listings.        |
| options          | Array\[[Product Option](/draft/specification/reference/#product-option)\] | No       | Product options (Size, Color, etc.).                                                             |
| variants         | Array\[[Variant](/draft/specification/reference/#variant)\]               | **Yes**  | Purchasable variants of this product. First item is the featured variant for listings.           |
| rating           | [Rating](/draft/specification/reference/#rating)                          | No       | Aggregate product rating.                                                                        |
| tags             | Array[string]                                                             | No       | Product tags for categorization and search.                                                      |
| metadata         | object                                                                    | No       | Business-defined custom data extending the standard product model.                               |

### Variant

A purchasable item with specific option selections, price, and availability.

In lookup responses, each variant carries an `inputs` array for correlation: which request identifiers resolved to this variant, and whether the match was `exact` or `featured` (server-selected). See [Client Correlation](http://ucp.dev/draft/specification/catalog/lookup/#client-correlation) for details.

`media` is an ordered array. Businesses SHOULD return the featured variant image as the first element. Platforms SHOULD treat the first element as featured.

| Name         | Type                                                                        | Required | Description                                                                               |
| ------------ | --------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------- |
| id           | string                                                                      | **Yes**  | Global ID (GID) uniquely identifying this variant. Used as item.id in checkout.           |
| sku          | string                                                                      | No       | Business-assigned identifier for inventory and fulfillment.                               |
| barcodes     | Array[object]                                                               | No       | Industry-standard product identifiers for cross-reference and correlation.                |
| handle       | string                                                                      | No       | URL-safe variant handle/slug.                                                             |
| title        | string                                                                      | **Yes**  | Variant display title (e.g., 'Blue / Large').                                             |
| description  | [Description](/draft/specification/reference/#description)                  | **Yes**  | Variant description in one or more formats.                                               |
| url          | string                                                                      | No       | Canonical variant page URL.                                                               |
| categories   | Array\[[Category](/draft/specification/reference/#category)\]               | No       | Variant categories with optional taxonomy identifiers.                                    |
| price        | [Price](/draft/specification/reference/#price)                              | **Yes**  | Current selling price.                                                                    |
| list_price   | [Price](/draft/specification/reference/#price)                              | No       | List price before discounts (for strikethrough display).                                  |
| unit_price   | object                                                                      | No       | Price per standard unit of measurement. MAY be omitted when unit pricing does not apply.  |
| availability | object                                                                      | No       | Variant availability for purchase.                                                        |
| options      | Array\[[Selected Option](/draft/specification/reference/#selected-option)\] | No       | Option values that define this variant (e.g., Color: Blue, Size: Large).                  |
| media        | Array\[[Media](/draft/specification/reference/#media)\]                     | No       | Variant media (images, videos, 3D models). First item is the featured media for listings. |
| rating       | [Rating](/draft/specification/reference/#rating)                            | No       | Variant rating.                                                                           |
| tags         | Array[string]                                                               | No       | Variant tags for categorization and search.                                               |
| metadata     | object                                                                      | No       | Business-defined custom data extending the standard variant model.                        |
| seller       | object                                                                      | No       | Optional seller context for this variant.                                                 |

### Price

| Name     | Type                                             | Required | Description                                           |
| -------- | ------------------------------------------------ | -------- | ----------------------------------------------------- |
| amount   | [Amount](/draft/specification/reference/#amount) | **Yes**  | Amount in ISO 4217 minor units. Use 0 for free items. |
| currency | string                                           | **Yes**  | ISO 4217 currency code (e.g., 'USD', 'EUR', 'GBP').   |

### Price Range

| Name | Type                                           | Required | Description                 |
| ---- | ---------------------------------------------- | -------- | --------------------------- |
| min  | [Price](/draft/specification/reference/#price) | **Yes**  | Minimum price in the range. |
| max  | [Price](/draft/specification/reference/#price) | **Yes**  | Maximum price in the range. |

### Media

| Name     | Type    | Required | Description                                                  |
| -------- | ------- | -------- | ------------------------------------------------------------ |
| type     | string  | **Yes**  | Media type. Well-known values: `image`, `video`, `model_3d`. |
| url      | string  | **Yes**  | URL to the media resource.                                   |
| alt_text | string  | No       | Accessibility text describing the media.                     |
| width    | integer | No       | Width in pixels (for images/video).                          |
| height   | integer | No       | Height in pixels (for images/video).                         |

### Product Option

| Name   | Type                                                                  | Required | Description                          |
| ------ | --------------------------------------------------------------------- | -------- | ------------------------------------ |
| name   | string                                                                | **Yes**  | Option name (e.g., 'Size', 'Color'). |
| values | Array\[[Option Value](/draft/specification/reference/#option-value)\] | **Yes**  | Available values for this option.    |

### Option Value

| Name  | Type   | Required | Description                                                                                                                                           |
| ----- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| id    | string | No       | Optional server-assigned identifier for this option value. When present in a selected_option, the server SHOULD use it for matching instead of label. |
| label | string | **Yes**  | Display text for this option value (e.g., 'Small', 'Blue').                                                                                           |

### Selected Option

| Name  | Type   | Required | Description                                                                                                                                             |
| ----- | ------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| name  | string | **Yes**  | Option name (e.g., 'Size').                                                                                                                             |
| id    | string | No       | Optional option value identifier from option_value.id. When present, the server SHOULD use it for matching; name and label remain required for display. |
| label | string | **Yes**  | Selected option label (e.g., 'Large').                                                                                                                  |

### Rating

| Name      | Type    | Required | Description                                                |
| --------- | ------- | -------- | ---------------------------------------------------------- |
| value     | number  | **Yes**  | Average rating value.                                      |
| scale_min | number  | No       | Minimum value on the rating scale (e.g., 1 for 1-5 stars). |
| scale_max | number  | **Yes**  | Maximum value on the rating scale (e.g., 5 for 5-star).    |
| count     | integer | No       | Number of reviews contributing to the rating.              |

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

**Note**: All catalog errors use `severity: "recoverable"` - agents handle them programmatically (retry, inform user, show alternatives).

#### Message (Error)

| Name         | Type                                                     | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------ | -------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                   | **Yes**  | **Constant = error**. Message type discriminator.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| code         | [Error Code](/draft/specification/reference/#error-code) | **Yes**  | Error code identifying the type of error. Standard errors are defined in specification (see examples), and have standardized semantics; freeform codes are permitted.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| path         | string                                                   | No       | RFC 9535 JSONPath to the component the message refers to (e.g., $.items[1]).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| content_type | string                                                   | No       | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| content      | string                                                   | **Yes**  | Human-readable message.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| severity     | string                                                   | **Yes**  | Reflects the resource state and recommended action. 'recoverable': platform can resolve by modifying inputs and retrying via API. 'requires_buyer_input': merchant requires information their API doesn't support collecting programmatically (checkout incomplete). 'requires_buyer_review': buyer must authorize before order placement due to policy, regulatory, or entitlement rules. 'unrecoverable': no valid resource exists to act on, retry with new resource or inputs. Errors with 'requires\_*' severity contribute to 'status: requires_escalation'.* *Enum:*\* `recoverable`, `requires_buyer_input`, `requires_buyer_review`, `unrecoverable` |

#### Message (Warning)

| Name         | Type   | Required | Description                                                                                                                                                                                                                                         |
| ------------ | ------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = warning**. Message type discriminator.                                                                                                                                                                                                 |
| path         | string | No       | JSONPath (RFC 9535) to related field (e.g., $.line_items[0]).                                                                                                                                                                                       |
| code         | string | **Yes**  | Warning code. Machine-readable identifier for the warning type (e.g., final_sale, prop65, fulfillment_changed, age_restricted, etc.).                                                                                                               |
| content      | string | **Yes**  | Human-readable warning message that MUST be displayed.                                                                                                                                                                                              |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                      |
| presentation | string | No       | Rendering contract for this warning. 'notice' (default): platform MUST display, MAY dismiss. 'disclosure': platform MUST display in proximity to the path-referenced component, MUST NOT hide or auto-dismiss. See specification for full contract. |
| image_url    | string | No       | URL to a required visual element (e.g., warning symbol, energy class label).                                                                                                                                                                        |
| url          | string | No       | Reference URL for more information (e.g., regulatory site, registry entry, policy page).                                                                                                                                                            |

#### Message (Info)

| Name         | Type   | Required | Description                                                    |
| ------------ | ------ | -------- | -------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = info**. Message type discriminator.               |
| path         | string | No       | RFC 9535 JSONPath to the component the message refers to.      |
| code         | string | No       | Info code for programmatic handling.                           |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown` |
| content      | string | **Yes**  | Human-readable message.                                        |

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

See [Warning Presentation](http://ucp.dev/draft/specification/checkout/#warning-presentation) for the full rendering contract.

## Transport Bindings

The capabilities above are bound to specific transport protocols:

- [REST Binding](http://ucp.dev/draft/specification/catalog/rest/index.md): RESTful API mapping.
- [MCP Binding](http://ucp.dev/draft/specification/catalog/mcp/index.md): Model Context Protocol mapping via JSON-RPC.
