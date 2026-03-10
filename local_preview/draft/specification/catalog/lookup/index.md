# Catalog Lookup Capability

- **Capability Name:** `dev.ucp.shopping.catalog.lookup`

Retrieves products or variants by identifier. Use this when you already have identifiers (e.g., from a saved list, deep links, or cart validation).

## Operation

| Operation          | Description                                  |
| ------------------ | -------------------------------------------- |
| **Lookup Catalog** | Retrieve products or variants by identifier. |

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

### Request

| Name    | Type          | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------- | ------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ids     | Array[string] | **Yes**  | Identifiers to lookup. Implementations MUST support product ID and variant ID; MAY support secondary identifiers (SKU, handle, etc.).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| context | object        | No       | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |

### Response

| Name     | Type          | Required | Description                                                                                                                                         |
| -------- | ------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp      | any           | **Yes**  | UCP metadata for catalog responses.                                                                                                                 |
| products | Array[any]    | **Yes**  | Products matching the requested identifiers. May contain fewer items if some identifiers not found, or more if identifiers match multiple products. |
| messages | Array[object] | No       | Errors, warnings, or informational messages about the requested items.                                                                              |

## Transport Bindings

- [REST Binding](https://ucp.dev/draft/specification/catalog/rest/#post-cataloglookup): `POST /catalog/lookup`
- [MCP Binding](https://ucp.dev/draft/specification/catalog/mcp/#lookup_catalog): `lookup_catalog` tool
