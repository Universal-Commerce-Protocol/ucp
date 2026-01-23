# Schema Authoring Guide

This guide documents conventions for authoring UCP JSON schemas: metadata fields, the registry pattern, schema variants, and versioning.

## Schema Metadata Fields

UCP schemas use standard JSON Schema fields plus UCP-specific metadata:

| Field         | Standard    | Purpose                                                             | Required For                             |
| ------------- | ----------- | ------------------------------------------------------------------- | ---------------------------------------- |
| `$schema`     | JSON Schema | Declares JSON Schema draft version (**SHOULD** use `draft/2020-12`) | All schemas                              |
| `$id`         | JSON Schema | Schema's canonical URI for `$ref` resolution                        | All schemas                              |
| `title`       | JSON Schema | Human-readable display name                                         | All schemas                              |
| `description` | JSON Schema | Schema purpose and usage                                            | All schemas                              |
| `name`        | UCP         | Reverse-domain identifier; doubles as registry key                  | Capabilities, services, handlers         |
| `version`     | UCP         | Entity version (`YYYY-MM-DD` format)                                | Capabilities, services, payment handlers |
| `id`          | UCP         | Instance identifier for multiple configurations                     | Payment handlers only                    |

### Why Self-Describing?

Capability schemas **must be self-describing**: when a platform fetches a schema, it should determine exactly what capability and version it represents without cross-referencing other documents. This matters because:

1. **Independent versioning**: Capabilities may version independently. The schema must declare its version explicitly—you can't infer it from the URL.
1. **Validation**: Validators can cross-check that a capability declaration's `schema` URL points to a schema whose embedded `name`/`version` match the declaration. Mismatches are authoring errors caught at build time.
1. **Developer experience**: When reading a schema file, integrators immediately see what capability it defines without reverse-engineering the `$id` URL.
1. **Compact namespace**: The `name` field provides a standardized reverse-domain identifier (e.g., `dev.ucp.shopping.checkout`) that's more compact and semantic than the full `$id` URL.

### Why Both `$id` and `name`?

| Field  | Role                                                    | Format                 |
| ------ | ------------------------------------------------------- | ---------------------- |
| `$id`  | JSON Schema primitive for `$ref` resolution and tooling | URI (required by spec) |
| `name` | Registry key and stable identifier                      | Reverse-domain         |

`$id` must be a valid URI per JSON Schema spec. `name` is the **key used in registries** (`capabilities`, `services`, `payment_handlers`) and the wire protocol identifier used in capability negotiation—decoupled from schema hosting so that `schema` URLs can change as infrastructure evolves.

The reverse-domain format provides **namespace governance**: domain owners control their namespace (`dev.ucp.*`, `com.shopify.*`), avoiding collisions between UCP and vendor entities. This stable identity layer allows trust and resolution mechanisms to evolve independently—future versions could adopt verifiable credentials, content-addressed schemas, or other verification methods without breaking capability negotiation.

### Why `version` Uses Dates?

The `version` field uses date-based versioning (`YYYY-MM-DD`) to enable:

- **Capability negotiation**: Platforms request specific versions they support
- **Breaking change management**: New versions get new dates; old versions remain valid and resolvable
- **Independent lifecycles**: Extensions can release on their own schedule

## Schema Categories

UCP schemas fall into six categories based on their role in the protocol.

### Capability Schemas

Define negotiated capabilities that appear in `ucp.capabilities{}` registries.

- **Top-level fields**: `$schema`, `$id`, `title`, `description`, `name`, `version`
- **Variants**: `platform_schema`, `business_schema`, `response_schema`

Examples: `checkout.json`, `fulfillment.json`, `discount.json`, `order.json`

### Service Schemas

Define transport bindings that appear in `ucp.services{}` registries. Each transport (REST, MCP, A2A, Embedded) is a separate entry.

- **Top-level fields**: `$schema`, `$id`, `title`, `description`, `name`, `version`
- **Variants**: `platform_schema`, `business_schema`
- **Transport requirements**:
  - REST/MCP: `endpoint`, `schema` (OpenAPI/OpenRPC URL)
  - A2A: `endpoint` (Agent Card URL)
  - Embedded: `schema` (OpenRPC URL)

### Payment Handler Schemas

Define payment handler configurations in `ucp.payment_handlers{}` registries.

- **Top-level fields**: `$schema`, `$id`, `title`, `description`, `name`, `version`
- **Variants**: `platform_schema`, `business_schema`, `response_schema`
- **Instance `id`**: Required to distinguish multiple configurations of the same handler

Examples: `com.google.pay`, `dev.shopify.shop_pay`, `dev.ucp.processor_tokenizer`

**→ See [Payment Handler Guide](https://ucp.dev/draft/specification/payment-handler-guide/index.md)** for detailed guidance on handler structure, config/instrument/credential schemas, and the full specification template.

### Component Schemas

Data structures embedded within capabilities but not independently negotiated. Do **not** appear in registries.

- **Top-level fields**: `$schema`, `$id`, `title`, `description`
- **Omit**: `name`, `version` (not independently versioned)

Examples:

- `schemas/shopping/payment.json` — Payment configuration (part of checkout)

### Type Schemas

Reusable definitions referenced by other schemas. Do **not** appear in registries.

- **Top-level fields**: `$schema`, `$id`, `title`, `description`
- **Omit**: `name`, `version`

Examples: `types/buyer.json`, `types/line_item.json`, `types/postal_address.json`

### Meta Schemas

Define protocol structure rather than entity payloads.

- **Top-level fields**: `$schema`, `$id`, `title`, `description`
- **Omit**: `name`, `version`

Examples: `ucp.json` (entity base), `capability.json`, `service.json`, `payment_handler.json`

## The Registry Pattern

UCP organizes capabilities, services, and handlers in **registries**—objects keyed by `name` rather than arrays of objects with `name` fields.

```json
{
  "capabilities": {
    "dev.ucp.shopping.checkout": [{"version": "2026-01-11"}],
    "dev.ucp.shopping.fulfillment": [{"version": "2026-01-11"}]
  },
  "services": {
    "dev.ucp.shopping": [
      {"version": "2026-01-11", "transport": "rest"},
      {"version": "2026-01-11", "transport": "mcp"}
    ]
  },
  "payment_handlers": {
    "com.google.pay": [{"id": "gpay_1234", "version": "2026-01-11"}]
  }
}
```

### Registry Contexts

The same registry structure appears in three contexts with different field requirements:

| Context          | Location                | Required Fields                 |
| ---------------- | ----------------------- | ------------------------------- |
| Platform Profile | Advertised URI          | `version`, `spec`, `schema`     |
| Business Profile | `/.well-known/ucp`      | `version`; may add `config`     |
| API Responses    | Checkout/order payloads | `version` (+ `id` for handlers) |

## The Entity Pattern

All capabilities, services, and handlers extend a common `entity` base schema:

| Field     | Type   | Description                                     |
| --------- | ------ | ----------------------------------------------- |
| `version` | string | Entity version (`YYYY-MM-DD`) — always required |
| `spec`    | URI    | Human-readable specification                    |
| `schema`  | URI    | JSON Schema URL                                 |
| `id`      | string | Instance identifier (handlers only)             |
| `config`  | object | Entity-specific configuration                   |

### Schema Variants

Each entity type defines **three variants** for different contexts:

**`platform_schema`** — Full declarations for discovery

```json
{
  "dev.ucp.shopping.fulfillment": [{
    "version": "2026-01-11",
    "spec": "https://ucp.dev/specification/fulfillment",
    "schema": "https://ucp.dev/schemas/shopping/fulfillment.json",
    "config": {
      "supports_multi_group": true
    }
  }]
}
```

**`business_schema`** — Business-specific overrides

```json
{
  "dev.ucp.shopping.fulfillment": [{
    "version": "2026-01-11",
    "config": {
      "allows_multi_destination": {"shipping": true}
    }
  }]
}
```

**`response_schema`** — Minimal references in API responses

```json
{
  "ucp": {
    "capabilities": {
      "dev.ucp.shopping.fulfillment": [{"version": "2026-01-11"}]
    }
  }
}
```

Define all three in your schema's `$defs`:

```json
"$defs": {
  "platform_schema": {
    "allOf": [{"$ref": "../capability.json#/$defs/platform_schema"}]
  },
  "business_schema": {
    "allOf": [{"$ref": "../capability.json#/$defs/business_schema"}]
  },
  "response_schema": {
    "allOf": [{"$ref": "../capability.json#/$defs/response_schema"}]
  }
}
```

## Versioning Strategy

### UCP Capabilities (`dev.ucp.*`)

UCP-authored capabilities version with protocol releases by default. Individual capabilities **may** version independently when needed.

### Vendor Capabilities (`com.{vendor}.*`)

Capabilities outside `dev.ucp.*` version fully independently:

```json
{
  "name": "com.shopify.loyalty",
  "version": "2025-09-01",
  "spec": "https://shopify.dev/ucp/loyalty",
  "schema": "https://shopify.dev/ucp/schemas/loyalty.json"
}
```

Vendor schemas follow the same self-describing requirements.

## Complete Example: Capability Schema

A capability schema defines both payload structure and declaration variants:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ucp.dev/schemas/shopping/checkout.json",
  "name": "dev.ucp.shopping.checkout",
  "version": "2026-01-11",
  "title": "Checkout",
  "description": "Base checkout schema. Extensions compose via allOf.",

  "$defs": {
    "platform_schema": {
      "allOf": [{"$ref": "../capability.json#/$defs/platform_schema"}]
    },
    "business_schema": {
      "allOf": [{"$ref": "../capability.json#/$defs/business_schema"}]
    },
    "response_schema": {
      "allOf": [{"$ref": "../capability.json#/$defs/response_schema"}]
    }
  },

  "type": "object",
  "required": ["ucp", "id", "line_items", "status", "currency", "totals", "links"],
  "properties": {
    "ucp": {"$ref": "../ucp.json#/$defs/response_checkout_schema"},
    "id": {"type": "string", "description": "Checkout identifier"},
    "line_items": {"type": "array", "items": {"$ref": "types/line_item.json"}},
    "status": {"type": "string", "enum": ["open", "completed", "expired"]},
    "currency": {"type": "string", "pattern": "^[A-Z]{3}$"},
    "totals": {"$ref": "types/totals.json"},
    "links": {"$ref": "types/links.json"}
  }
}
```

Key points:

- **Top-level `name` and `version`** make the schema self-describing
- **`$defs` variants** enable validation in different contexts
- **Payload properties** define the actual checkout response structure
