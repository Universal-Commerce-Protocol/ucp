# Catalog Lookup Capability

- **Capability Name:** `dev.ucp.shopping.catalog.lookup`

Retrieves products or variants by identifier. Use this when you already have identifiers (e.g., from a saved list, deep links, cart validation, or a selected product for detail rendering).

## Operations

| Operation        | Tool / Endpoint                           | Description                                |
| ---------------- | ----------------------------------------- | ------------------------------------------ |
| **Batch Lookup** | `lookup_catalog` / `POST /catalog/lookup` | Retrieve multiple products by identifier.  |
| **Get Product**  | `get_product` / `POST /catalog/product`   | Retrieve full detail for a single product. |

`lookup_catalog` resolves identifiers to products; `get_product` fetches full detail for a known product or variant ID:

| Concern      | `lookup_catalog`                                                 | `get_product`                                                                |
| ------------ | ---------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Input**    | `ids[]` — product/variant ID; MAY support SKU, handle, URL, etc. | `id` — product or variant ID                                                 |
| **Purpose**  | Resolve identifiers to products                                  | Full product detail for purchase decisions with interactive option selection |
| **Variants** | One featured variant per product                                 | Featured variant and relevant subset, filtered by option selections          |

Use `lookup_catalog` when you have identifiers to resolve or display in a list. Use `get_product` when a product has been identified and the agent needs full detail, including interactive variant selection, for a purchase decision.

______________________________________________________________________

## Batch Lookup (`lookup_catalog`)

### Supported Identifiers

The `ids` parameter accepts an array of identifiers. Implementations MUST support lookup by product ID and variant ID. Implementations MAY additionally support secondary identifiers such as SKU or handle, provided these are also fields on the returned product object.

Duplicate identifiers in the request MUST be deduplicated. When an identifier matches multiple products (e.g., a SKU shared across variants), implementations return matching products and MAY limit the result set. When multiple identifiers resolve to the same product, it MUST be returned once.

### Client Correlation

The response does not guarantee order. Each variant carries an `inputs` array identifying which request identifiers resolved to it, and how.

| Name  | Type   | Required | Description                                                                                                                                                                                                                                                                                                                   |
| ----- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id    | string | **Yes**  | The identifier from the lookup request that resolved to this variant.                                                                                                                                                                                                                                                         |
| match | string | No       | How the request identifier resolved to this variant. Well-known values: `exact` (input directly identifies this variant, e.g., variant ID, SKU), `featured` (server selected this variant as representative, e.g., product ID resolved to best match). Businesses MAY implement and provide additional resolution strategies. |

Multiple request identifiers may resolve to the same variant (e.g., a product ID and one of its variant IDs). When this occurs, the variant's `inputs` array contains one entry per resolved identifier, each with its own match type. Variants without an `inputs` entry MUST NOT appear in lookup responses.

### Batch Size

Implementations SHOULD accept at least 10 identifiers per request. Implementations MAY enforce a maximum batch size and MUST reject requests exceeding their limit with an appropriate error (HTTP 400 `request_too_large` for REST, JSON-RPC `-32602` for MCP).

### Resolution Behavior

`match` reflects the resolution level of the identifier, not its type:

- **`exact`**: Identifier resolved directly to this variant (e.g., variant ID, SKU, barcode).
- **`featured`**: Identifier resolved to the parent product; server selected this variant as representative (e.g., product ID, handle).

### Filters

Both `lookup_catalog` and `get_product` accept optional `filters` to narrow the returned products and variants. Filters use the same schema and AND semantics as [Search Filters](http://ucp.dev/draft/specification/catalog/search/#search-filters) — for example, a price filter excludes variants outside the specified range.

Filters apply *after* identifier resolution (lookup) or option selection (get_product). An identifier that resolves to a product whose variants all fall outside the price filter results in that product being excluded from the response.

### Request

Request body for catalog lookup.

| Name        | Type          | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------- | ------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ids         | Array[string] | **Yes**  | Identifiers to lookup. Implementations MUST support product ID and variant ID; MAY support secondary identifiers (SKU, handle, etc.).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| filters     | object        | No       | Filter criteria to narrow returned products and variants. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context     | object        | No       | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals     | object        | No       | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution | object        | No       | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

### Response

| Name     | Type          | Required | Description                                                                                                                                         |
| -------- | ------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp      | any           | **Yes**  | UCP metadata for catalog responses.                                                                                                                 |
| products | Array[any]    | **Yes**  | Products matching the requested identifiers. May contain fewer items if some identifiers not found, or more if identifiers match multiple products. |
| messages | Array[object] | No       | Errors, warnings, or informational messages about the requested items.                                                                              |

______________________________________________________________________

## Get Product (`get_product`)

Retrieves current product state for a single identifier, with support for interactive variant selection and real-time availability signals. This is the authoritative source for purchase decisions.

### Supported Identifiers

The `id` parameter accepts a single product ID or variant ID.

### Resolution Behavior

The response returns the product with complete context (title, description, media, options) and a **subset of variants matching [`product.selected`](#option-selection)**:

- **Product ID**: `variants` SHOULD contain the featured variant and other variants matching `product.selected`. When the request includes `selected` options, this narrows the subset to variants matching the client's choices.
- **Variant ID**: The requested variant MUST be the first element (featured). `product.selected` reflects that variant's options. Remaining variants match the same effective selections. When the request includes `selected` options that conflict with the variant's own options, the variant's options take precedence — the variant ID fully determines the selection state and `selected` is ignored.

### Response Shape

The response contains a singular `product` object (not an array). This reflects the single-resource semantics of the operation. When the identifier is not found, the server returns `ucp.status: "error"` with a `messages` array containing the error detail. This is an application outcome — the handler ran and reports its result via the UCP envelope, not a transport error.

### Option Selection

The `selected` and `preferences` parameters enable interactive variant narrowing: the core product detail page interaction where a user progressively selects options (Color, Size, etc.) and the UI updates availability in real time.

#### Input

- **`selected`**: Array of option selections (e.g., `[{"name": "Color", "label": "Red"}]`). Partial selections are valid; the client sends whatever the user has chosen so far. Each option name MUST appear at most once.
- **`preferences`**: Option names in relaxation priority order (e.g., `["Color", "Size"]`). When no variant matches all selections, the server drops options from the **end** of this list first, keeping higher-priority selections intact. Optional; if omitted, the server uses its own relaxation heuristic.

#### Output: Effective Selections

The response MUST include `product.selected` when the product has configurable options — reflecting the effective selections after any relaxation when the request includes `selected`, or the featured variant's default selections otherwise. When the product has no configurable options, `selected` MAY be empty or omitted.

Clients that send `selected` detect relaxation by diffing their request against `product.selected`:

- **No relaxation**: Response `selected` matches the request — all selections resolved to at least one variant.
- **Relaxation occurred**: Response `selected` is a subset of the request — the server dropped unresolvable options per `preferences` priority.

#### Output: Availability Signals

Option values in the response SHOULD include availability signals relative to `product.selected`:

| `available` | `exists` | Meaning                                       | UI Treatment                |
| ----------- | -------- | --------------------------------------------- | --------------------------- |
| `true`      | `true`   | In stock — purchasable                        | Selectable                  |
| `false`     | `true`   | Out of stock — variant exists but unavailable | Disabled / strikethrough    |
| `false`     | `false`  | No variant for this combination               | Hidden or visually distinct |

These fields appear on each option value in `product.options[].values[]`. They reflect availability **relative to the effective selections**. Changing a selection changes the availability map.

### Request

Request body for single-product retrieval. Supports interactive variant narrowing via selected and preferences.

| Name        | Type          | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------- | ------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string        | **Yes**  | Product or variant identifier. Implementations MUST support product ID and variant ID.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| selected    | Array[object] | No       | Partial or full option selections for interactive variant narrowing. When provided, response option values include availability signals (available, exists) relative to these selections.                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| preferences | Array[string] | No       | Option names in relaxation priority order. When no exact variant matches all selections, the server drops options from the end of this list first. E.g., ['Color', 'Size'] keeps Color and relaxes Size.                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| filters     | object        | No       | Filter criteria to narrow returned variants. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| context     | object        | No       | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals     | object        | No       | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution | object        | No       | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

### Response

| Name     | Type          | Required | Description                                                                                                |
| -------- | ------------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| ucp      | any           | **Yes**  | UCP metadata for catalog responses.                                                                        |
| product  | object        | **Yes**  | The requested product with full detail. Singular — this is a single-resource operation.                    |
| messages | Array[object] | No       | Warnings or informational messages about the product (e.g., price recently changed, limited availability). |

______________________________________________________________________

## Transport Bindings

- [REST Binding](http://ucp.dev/draft/specification/catalog/rest/#post-cataloglookup): `POST /catalog/lookup` (batch)
- [REST Binding](http://ucp.dev/draft/specification/catalog/rest/#post-catalogproduct): `POST /catalog/product` (single)
- [MCP Binding](http://ucp.dev/draft/specification/catalog/mcp/#lookup_catalog): `lookup_catalog` tool (batch)
- [MCP Binding](http://ucp.dev/draft/specification/catalog/mcp/#get_product): `get_product` tool (single)
