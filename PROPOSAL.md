# Catalog List Operation -- Paginated Catalog Enumeration for UCP

**Capability:** `dev.ucp.shopping.catalog.list`

## Motivation

Platforms building agentic shopping experiences need to index a business's entire catalog for offline ranking, embedding, and recommendation. Today the only catalog operation in UCP is **search**, which requires a query or filter, returns relevance-ranked results, and is designed for buyer-initiated discovery rather than platform-initiated indexing. There is no way to deterministically enumerate all products in a business's catalog.

A live list API fills this gap:

- **Full enumeration** -- no query required, returns all products (paginated)
- **Incremental sync** -- `modified_since` filter fetches only changes since last sync
- **Real-time** -- reflects current catalog state, not a periodic snapshot
- **Same schema** -- returns the same Product/Variant objects used by search and lookup

Note: [RFC #550](https://github.com/Universal-Commerce-Protocol/ucp/issues/550) proposes a complementary static-feed approach for bulk discovery. This proposal addresses the live API use case independently.

## How it fits

| Operation  | Input                | Use case                           |
| ---------- | -------------------- | ---------------------------------- |
| **Search** | Query text + filters | Buyer-initiated discovery          |
| **Lookup** | Known IDs            | Cart validation, deep links        |
| **List**   | None required        | Platform indexing, incremental sync |

## Design

A new operation within the existing `dev.ucp.shopping.catalog` capability.
No new capability namespace -- businesses that support catalog already have
the infrastructure.

### Request

```json
{
  "filters": {
    "modified_since": "2026-07-01T00:00:00Z"
  },
  "pagination": {
    "cursor": "eyJsYXN0X2lkIjoicHJvZF8xMjM0In0=",
    "limit": 100
  }
}
```

When no filters are provided, the operation returns all products in the catalog.

### Response

Same shape as `catalog.search` -- reuses existing pagination and product schemas:

```json
{
  "ucp": {},
  "products": [
    {
      "id": "prod_abc123",
      "title": "Classic Running Shoe",
      "description": { "plain": "Lightweight running shoe." },
      "price_range": {
        "min": { "amount": 8900, "currency": "USD" },
        "max": { "amount": 12900, "currency": "USD" }
      },
      "variants": [
        {
          "id": "var_001",
          "title": "Black / Size 10",
          "description": { "plain": "Black colorway, men's size 10." },
          "price": { "amount": 8900, "currency": "USD" },
          "availability": { "available": true, "status": "in_stock" }
        }
      ]
    }
  ],
  "pagination": {
    "cursor": "eyJsYXN0X2lkIjoicHJvZF9hYmMxMjMifQ==",
    "has_next_page": true,
    "total_count": 5420
  }
}
```

### Key semantics

- **Page size** -- implementations SHOULD accept at least 100 (higher than
  search's 10, since list targets bulk ingestion)
- **Ordering** -- stable and deterministic within a pagination sequence
  (implementation-defined, typically by internal ID)
- **`modified_since`** -- inclusive; covers any change to product or its
  variants. Businesses that do not track modification timestamps MAY ignore
  and return the full catalog, notifying via a message
- **Deleted products** -- MAY be indicated via `messages` with
  `code: "deleted"`, or omitted entirely

## Design principles

- **Purely additive.** New operation within an existing capability -- no
  breaking changes.
- **Shared product schema.** Same Product/Variant objects used by search and
  lookup. Platforms reuse existing parsers.
- **Existing pagination primitive.** Reuses `common/types/pagination.json`
  already defined for search.
- **Open vocabulary filters.** `list_filters.json` uses
  `additionalProperties: true` for extensibility, matching `search_filters.json`.

## Files in this PR

| File                                              | Purpose                             |
| ------------------------------------------------- | ----------------------------------- |
| `source/schemas/shopping/catalog_list.json`       | Operation schema (request/response) |
| `source/schemas/shopping/types/list_filters.json` | Filter type (`modified_since`)      |
| `source/services/shopping/rest.openapi.json`      | OpenAPI -- `/catalog/list` endpoint |
| `source/services/shopping/mcp.openrpc.json`       | OpenRPC -- `list_catalog` tool      |
| `docs/specification/catalog/list.md`              | Specification page                  |
| `docs/specification/catalog/index.md`             | Capabilities table                  |
| `docs/specification/catalog/rest.md`              | REST binding (endpoint + example)   |
| `docs/specification/catalog/mcp.md`               | MCP binding (tool entry)            |
| `mkdocs.yml`                                      | Navigation                          |

## Open questions for TC

- **Scope** -- is list appropriate within `catalog`, or should it live under a
  separate capability namespace?
- **`modified_since` support** -- MUST vs MAY for businesses?
- **Deleted product signaling** -- is `messages`-based sufficient, or should
  deleted products appear with a `status` field?
- **Rate limiting** -- should the spec include normative language about
  rate-limiting list differently from search?
