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

# Schema Authoring Guide

This guide documents the conventions for authoring UCP JSON schemas, including
required metadata fields and versioning strategy.

## Schema Metadata Fields

UCP schemas use a combination of standard JSON Schema fields and
UCP-specific metadata:

| Field | Standard | Purpose | Required For |
|-------|----------|---------|--------------|
| `$schema` | JSON Schema | Declares JSON Schema draft version (**SHOULD** use `draft/2020-12`) | All schemas |
| `$id` | JSON Schema | Schema's canonical URI for `$ref` resolution | All schemas |
| `title` | JSON Schema | Human-readable display name | All schemas |
| `description` | JSON Schema | Schema purpose and usage | All schemas |
| `name` | UCP | Reverse-domain capability identifier | Capability schemas only |
| `version` | UCP | Capability version (YYYY-MM-DD format) | Capability schemas only |

## Self-Describing Schemas

**Capability schemas MUST be self-describing.** When a platform fetches a
schema, it should be able to determine exactly what capability and version it
represents without cross-referencing other documents.

### Why self-describing?

1. **Independent versioning**: Capabilities **MAY** version independently. The
   schema must declare its version explicitly.

2. **Validation**: Validators can cross-check that a capability declaration's
   `schema` URL points to a schema whose embedded `name`/`version` match the
   declaration. Mismatches are authoring errors caught at build time.

3. **Developer experience**: When reading a schema file, integrators immediately
   see what capability it defines without reverse-engineering the `$id` URL.

4. **Compact namespace**: The `name` field provides a standardized
   reverse-domain identifier (e.g., `dev.ucp.shopping.checkout`) that's more
   compact and semantic than the full `$id` URL.

### Why both `$id` and `name`?

| Field | Role | Format |
|-------|------|--------|
| `$id` | JSON Schema primitive for `$ref` resolution and tooling | URI (required by spec) |
| `name` | Stable capability identity, independent of hosting | Reverse-domain |

`$id` must be a valid URI per JSON Schema spec. `name` is the wire protocol
identifier used in capability declarations and negotiation, decoupled from
schema hosting—`schema` URLs can change as infrastructure evolves.

UCP uses reverse-domain notation for `name` (e.g.,
`dev.ucp.shopping.checkout`) with DNS-based namespace governance. The stable
identity layer allows trust and resolution mechanisms to evolve
independently—future versions could adopt verifiable credentials,
content-addressed schemas, or other verification methods without breaking
capability negotiation.

```json
{
  "capabilities": [
    {"name": "dev.ucp.shopping.checkout", "version": "2026-01-11"},
    {
      "name": "dev.ucp.shopping.fulfillment",
      "version": "2026-01-11",
      "extends": "dev.ucp.shopping.checkout"
    }
  ]
}
```

### The `name` field

The `name` field uses reverse-domain notation for capability identification:

```
dev.ucp.shopping.checkout        # UCP checkout capability
dev.ucp.shopping.fulfillment     # UCP fulfillment extension
com.shopify.loyalty              # Vendor capability
```

This provides:

- **Namespace governance**: Domain owners control their namespace
- **Collision avoidance**: No conflicts between UCP and vendor capabilities
- **Wire protocol identity**: The exact string used in capability negotiation

### The `version` field

The `version` field uses date-based versioning (`YYYY-MM-DD`):

```json
"version": "2026-01-11"
```

This indicates which specification version the schema implements, enabling:

- **Capability negotiation**: Platforms request specific versions they support
- **Breaking change management**: New versions get new dates
- **Independent lifecycles**: Extensions can release on their own schedule

## Schema Categories

### Capability Schemas

Schemas that define negotiated capabilities. These appear in
`ucp.capabilities[]` arrays in discovery profiles and responses.

**MUST include**: `$schema`, `$id`, `title`, `description`, `name`, `version`

Examples:

- `schemas/shopping/checkout.json` → `dev.ucp.shopping.checkout`
- `schemas/shopping/order.json` → `dev.ucp.shopping.order`
- `schemas/shopping/fulfillment.json` → `dev.ucp.shopping.fulfillment`
- `schemas/shopping/discount.json` → `dev.ucp.shopping.discount`
- `schemas/shopping/buyer_consent.json` → `dev.ucp.shopping.buyer_consent`
- `schemas/shopping/ap2_mandate.json` → `dev.ucp.shopping.ap2_mandate`

### Component Schemas

Schemas that define data structures embedded within capabilities but are not
independently negotiated.

**MUST include**: `$schema`, `$id`, `title`, `description`
**MUST NOT include**: `name`, `version`

Examples:

- `schemas/shopping/payment.json` — Payment configuration (part of checkout)

### Type Schemas

Reusable type definitions referenced by capability and component schemas.

**MUST include**: `$schema`, `$id`, `title`, `description`
**MUST NOT include**: `name`, `version`

Examples:

- `schemas/shopping/types/buyer.json`
- `schemas/shopping/types/line_item.json`
- `schemas/shopping/types/postal_address.json`

### Meta Schemas

Schemas that define protocol structure rather than capability payloads.

**MUST include**: `$schema`, `$id`, `title`, `description`
**MUST NOT include**: `name`, `version`

Examples:

- `schemas/ucp.json` — Protocol metadata definitions
- `schemas/capability.json` — Capability declaration structure

## Versioning Strategy

### UCP Capabilities (`dev.ucp.*`)

UCP-authored capabilities version with protocol releases by default. Individual
capabilities **MAY** version independently when needed.

### Vendor Capabilities (`com.{vendor}.*`)

Capabilities outside the `dev.ucp.*` namespace version fully independently:

```json
{
  "name": "com.shopify.loyalty",
  "version": "2025-09-01",
  "spec": "https://shopify.dev/ucp/loyalty",
  "schema": "https://shopify.dev/ucp/schemas/loyalty.json"
}
```

Vendor schemas follow the same self-describing requirements.

## Example: Capability Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ucp.dev/schemas/shopping/checkout.json",
  "name": "dev.ucp.shopping.checkout",
  "version": "2026-01-11",
  "title": "Checkout",
  "description": "Base checkout schema. Extensions compose via allOf.",
  "type": "object",
  "required": [
    "ucp",
    "id",
    "line_items",
    "status",
    "currency",
    "totals",
    "links",
    "payment"
  ],
  "properties": {
    ...
  }
}
```

## Example: Type Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ucp.dev/schemas/shopping/types/buyer.json",
  "title": "Buyer",
  "description": "Representation of the buyer in a checkout.",
  "type": "object",
  "properties": {
    ...
  }
}
```
