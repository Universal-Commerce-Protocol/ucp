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

This guide documents conventions for authoring UCP JSON schemas: metadata fields,
the registry pattern, schema variants, and versioning.

## Schema Metadata Fields

UCP schemas use standard JSON Schema fields plus UCP-specific metadata:

| Field | Standard | Purpose | Required For |
| ----- | -------- | ------- | ------------ |
| `$schema` | JSON Schema | Declares JSON Schema draft version (**SHOULD** use `draft/2020-12`) | All schemas |
| `$id` | JSON Schema | Schema's canonical URI for `$ref` resolution | All schemas |
| `title` | JSON Schema | Human-readable display name | All schemas |
| `description` | JSON Schema | Schema purpose and usage | All schemas |
| `name` | UCP | Reverse-domain identifier; doubles as registry key | Capabilities, extensions, payment handlers |
| `version` | UCP | Entity version (`YYYY-MM-DD` format) | Capabilities, extensions, payment handlers |
| `id` | UCP | Instance identifier for multiple configurations | Payment handlers only |

This table lists top-level metadata embedded in published schema documents;
profile registry declarations are covered in the sections below.

### Why Self-Describing?

Capability and payment-handler schemas **must be self-describing**: when a
Platform fetches a schema, it should determine exactly what entity and version
it represents without cross-referencing other documents. This matters because:

1. **Explicit version identity**: Capabilities, extensions, and payment handlers
   declare their version explicitly; it cannot be inferred from the URL.
   UCP-authored `dev.ucp.*` capabilities and extensions declare version `D` in
   each UCP release `D`. Payment handlers publish on their authors' own schedules.

2. **Validation**: Validators can cross-check that a capability declaration's
   `schema` URL points to a schema whose embedded `name`/`version` match the
   declaration. Mismatches are authoring errors caught at build time.

3. **Developer experience**: When reading a schema file, integrators immediately
   see what entity it defines without reverse-engineering the `$id` URL.

4. **Compact namespace**: The `name` field provides a standardized reverse-domain
   identifier (e.g., `dev.ucp.shopping.checkout`) that's more compact and semantic
   than the full `$id` URL. Service registry keys provide the same stable
   identity.

### Why Both `$id` and `name`?

| Field  | Role                                                    | Format                 |
| ------ | ------------------------------------------------------- | ---------------------- |
| `$id`  | JSON Schema primitive for `$ref` resolution and tooling | URI (required by spec) |
| `name` | Registry key and stable identifier                      | Reverse-domain         |

`$id` must be a valid URI per JSON Schema spec. `name` is the **key used in
registries** (`capabilities`, `services`, `payment_handlers`) and the wire protocol
identifier used in capability negotiation—decoupled from schema hosting so that
`schema` URLs can change as infrastructure evolves.

The reverse-domain format provides **namespace governance**: domain owners control
their namespace (`dev.ucp.*`, `com.shopify.*`), avoiding collisions between UCP
and vendor entities. This stable identity layer allows trust and resolution
mechanisms to evolve independently—future versions could adopt verifiable
credentials, content-addressed schemas, or other verification methods without
breaking capability negotiation.

### Why `version` Uses Dates?

The `version` field uses date-based versioning (`YYYY-MM-DD`) to enable:

- **Capability negotiation**: Platforms request specific versions they support
- **Certified release identity**: Each date identifies the entity's complete,
  published schema closure
- **Independent author lifecycles**: Third-party extensions and payment handlers
  can release on their authors' own schedules

## Schema Categories

UCP schemas fall into six categories based on their role in the protocol.

### Capability Schemas

Define negotiated capabilities that appear in `ucp.capabilities{}` registries.

- **Top-level fields**: `$schema`, `$id`, `title`, `description`, `name`, `version`
- **Variants**: `platform_schema`, `business_schema`, `response_schema`

Examples: `checkout.json`, `fulfillment.json`, `discount.json`, `order.json`

### Service Schemas

Define transport bindings that appear in `ucp.services{}` registries. Each transport
(REST, MCP, A2A, Embedded) is a separate entry.

- **Registry identity**: Reverse-domain service name used as the registry key
- **Entry fields**: `version`, `spec`, `schema`, `config`, and transport-specific fields
- **Versioning**: Every service entry declares an explicit `version`; in release
  `D` it is `D`. Because each entry pairs the service with one transport binding,
  that service `version` repeats on each entry, and transport bindings have no
  separate version. The referenced OpenAPI/OpenRPC artifact carries its own
  `info.version` as artifact metadata, not a negotiated version. See
  [Component Versioning and Release Snapshots](../specification/overview/index.md#component-versioning-and-release-snapshots)
- **Variants**: `platform_schema`, `business_schema`
- **Transport requirements** (additional beyond the common base):
    - Platform profile (`platform_schema`): REST/MCP/Embedded require `schema` (OpenAPI/OpenRPC URL). A2A has no additional requirements.
    - Business profile (`business_schema`): REST/MCP/A2A require `endpoint` (Agent Card URL for A2A). Embedded has no additional requirements.

### Payment Handler Schemas

Define payment handler configurations in `ucp.payment_handlers{}` registries.

- **Top-level fields**: `$schema`, `$id`, `title`, `description`, `name`, `version`, `available_instruments`
- **Variants**: `platform_schema`, `business_schema`, `response_schema`
- **Instance `id`**: Required to distinguish multiple configurations of the same handler
- **`available_instruments`**: Optional. Array of supported instrument types with type-specific constraints (e.g., brands for credit cards). When absent, the handler places no restrictions — it supports the full set of instrument types defined by its handler schema.

Examples: `com.google.pay`, `dev.shopify.shop_pay`, `dev.ucp.processor_tokenizer`

**→ See [Payment Handler Guide](../specification/payment/guide.md)** for detailed
guidance on handler structure, config/instrument/credential schemas, and the full
specification template.

### Component Schemas

Data structures embedded within capabilities but not independently negotiated.
Do **not** appear in registries.

- **Top-level fields**: `$schema`, `$id`, `title`, `description`
- **Omit**: `name`, `version` (not independently versioned)

Examples:

- `schemas/shopping/payment.json` — Payment configuration (part of checkout)

### Type Schemas

Reusable definitions referenced by other schemas. Do **not** appear in registries.

- **Top-level fields**: `$schema`, `$id`, `title`, `description`
- **Omit**: `name`, `version`
- **Expression grammars**: A type schema that defines expression syntax rather
  than independently placeable UCP fields is direction-agnostic. Its grammar
  properties carry no `ucp_request` annotation; each UCP property that exposes
  the grammar declares its own applicability. Example:
  `common/types/constraint_expression.json`.

Examples: `types/buyer.json`, `types/line_item.json`, `types/postal_address.json`

### Meta Schemas

Define protocol structure rather than entity payloads.

- **Top-level fields**: `$schema`, `$id`, `title`, `description`
- **Omit**: `name`, `version`

Examples: `ucp.json` (entity base), `capability.json`, `service.json`, `payment_handler.json`

## The Registry Pattern

UCP organizes capabilities, services, and handlers in **registries**—objects keyed
by `name` rather than arrays of objects with `name` fields.

<!-- ucp:example skip reason="schema authoring example" -->
```json
{
  "capabilities": {
    "dev.ucp.shopping.checkout": [{"version": "{{ ucp_version }}"}],
    "dev.ucp.shopping.fulfillment": [{"version": "{{ ucp_version }}"}]
  },
  "services": {
    "dev.ucp.shopping": [
      {"version": "{{ ucp_version }}", "transport": "rest"},
      {"version": "{{ ucp_version }}", "transport": "mcp"}
    ]
  },
  "payment_handlers": {
    "com.google.pay": [{"id": "gpay_1234", "version": "{{ ucp_version }}", "available_instruments": [{"type": "google_pay_card"}]}]
  }
}
```

### Registry Contexts

The same registry structure appears in three contexts with different field requirements:

| Registry | Platform Profile | Business Profile | API Responses |
| -------- | ---------------- | ---------------- | ------------- |
| Services | `version`, `transport`, `spec`; `schema` for REST, MCP, and Embedded | `version`, `transport`; `endpoint` for REST, MCP, and A2A | `version`, `transport`; transport-specific `config` where applicable |
| Capabilities/extensions | `version`, `spec`, `schema` | `version`, `schema`; may add `config` | `version` |
| Payment handlers | `id`, `version`, `spec`, `schema` | `id`, `version`; may add `config` | `id`, `version` |

## The Reserved `ucp` Member

The member name `ucp` is reserved at every structured UCP object scope — an
object whose members are schema-defined fields — for the protocol namespace.
The top-level envelope is its root manifestation. Dictionary containers are
excluded because their keys are data rather than fields. See
[The `ucp` Protocol Namespace](../specification/overview/index.md#the-ucp-protocol-namespace)
for the normative rules. For schema authors this means:

- **Never mint a structured domain field named `ucp`.** Schema authors
  **MUST NOT** declare a domain field named `ucp` in a structured object; the
  name denotes the protocol namespace there.
- **Do not declare ambient `ucp` in open nested objects.** The root `ucp`
  envelope is not ambient placement; UCP root schemas already declare its
  required protocol metadata. Below the root, the member is UCP document grammar
  defined centrally, so schema authors **MUST NOT** declare it in an open nested
  object. A Business or Platform **MAY** include it in an eligible open
  structured scope without the domain schema saying so. Ordinary instance
  validation against an open UCP source domain schema treats it as an ignored
  unknown object; validating its contents is a conformance-tooling concern.
- **Dictionary keys remain data.** A dictionary container cannot host the
  protocol namespace. Schema authors **MUST NOT** model a dictionary key named
  `ucp` as that namespace; the key is governed by the dictionary's key and
  value schemas and is ordinary data. A structured object used as a
  dictionary value remains an eligible scope and follows these rules. For
  example, `attribution` is a dictionary of string values, so its key `ucp` is
  ordinary attribution data.
- **The vocabulary grows only in UCP core.** New protocol members are added
  in `ucp.json#/$defs/members`, never in domain or extension schemas, and a
  member is admitted only if it is safe to ignore — a Business or Platform
  that does not process it loses only that member's benefit, never
  correctness. The container is open for forward compatibility with future
  UCP versions, not as an extension point.
- **Registry maps can never host `ucp`.** Registry maps are dictionaries, so
  they cannot host the protocol namespace. Their reverse-domain
  `propertyNames` constraints additionally reject the literal `ucp` key.
  This is why structural metadata about a registry map — such as `map_order`
  — sits in the parent structured scope's protocol namespace rather than
  inside the map itself.
- **Closed nested structured objects must declare optional `ucp`
  explicitly.** Closing a nested structured object does not exempt it from the
  protocol grammar. A schema author defining one with
  `additionalProperties: false` **MUST** declare an optional `ucp` property
  referencing `ucp.json#/$defs/members`. This exception applies only to nested
  structured objects; closing a dictionary does not create an ambient namespace
  there.
- **Declare member applicability.** Schema authors **MUST** annotate every
  property registered in `ucp.json#/$defs/members` with `ucp_request` (`omit`,
  `optional`, or `required`, as appropriate). They **MUST** repeat the
  annotation wherever the same member is exposed elsewhere in `ucp.json`. An
  explicit ambient `ucp` property follows the applicability of its containing
  schema and is not automatically omitted from requests.

## The Entity Pattern

All capabilities, services, and handlers extend a common `entity` base schema:

| Field | Type | Description |
| ----- | ---- | ----------- |
| `version` | string | Entity version (`YYYY-MM-DD`) — always required |
| `spec` | URI | Human-readable specification |
| `schema` | URI | JSON Schema URL |
| `id` | string | Instance identifier (handlers only) |
| `config` | object | Entity-specific configuration |

### Schema Variants

Each entity type defines **three variants** for different contexts:

**`platform_schema`** — Full declarations for discovery

<!-- ucp:example skip reason="schema authoring example" -->
```json
{
  "dev.ucp.shopping.fulfillment": [{
    "version": "{{ ucp_version }}",
    "spec": "https://ucp.dev/{{ ucp_version }}/specification/fulfillment",
    "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/fulfillment.json",
    "config": {
      "supports_multi_group": true
    }
  }]
}
```

**`business_schema`** — Business-specific overrides

<!-- ucp:example skip reason="schema authoring example" -->
```json
{
  "dev.ucp.shopping.fulfillment": [{
    "version": "{{ ucp_version }}",
    "config": {
      "multi_destination": [{"method": "shipping"}]
    }
  }]
}
```

**`response_schema`** — Minimal references in API responses

<!-- ucp:example skip reason="schema authoring example" -->
```json
{
  "ucp": {
    "capabilities": {
      "dev.ucp.shopping.fulfillment": [{"version": "{{ ucp_version }}"}]
    }
  }
}
```

Define all three in your schema's `$defs`:

<!-- ucp:example skip reason="schema authoring example" -->
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

## String Vocabularies vs Enums

Prefer **open string vocabularies** with documented well-known values over closed
`enum` arrays. Enums are a one-way door: adding a new value is a breaking change
for strict validators, and removing one breaks existing producers.

<!-- ucp:example skip reason="schema authoring example" -->
```json
// PREFER: open vocabulary — extensible without schema changes
"type": {
  "type": "string",
  "description": "Media type. Well-known values: `image`, `video`, `model_3d`."
}

// AVOID: closed enum — adding `audio` requires a schema version bump
"type": {
  "type": "string",
  "enum": ["image", "video", "model_3d"]
}
```

**Use `enum` only for provably closed sets** where new values would represent a
fundamental protocol change (e.g., `checkout.status: open | completed | expired`).
If the set might grow as new use cases emerge, use an open string with well-known
values documented in the `description`.

## Versioning Strategy

### UCP Services (`dev.ucp.*`)

In each UCP release `D`, every UCP-defined service entry declares version `D`.
See [Service Schemas](#service-schemas) for how the flattened registry represents
service versions and transport bindings.

### UCP Capabilities (`dev.ucp.*`)

In each UCP release `D`, every UCP-defined capability and extension declares
version `D`, even when its schema did not change directly. Declaring version `D`
does not replace negotiation: capabilities and extensions are still selected by
exact-version intersection.

Profile selection, including profiles for older supported releases, is defined
in [Protocol Version](../specification/overview/index.md#protocol-version).

### Third-Party Extensions and Payment Handlers

Third-party extensions and payment handlers publish versions on their authors'
own schedules. Their versions remain independent of the selected `ucp.version`
and are not constrained to `D`. UCP's `payment_handler.json` defines the shared
declaration shape, not a payment-handler implementation or its release cadence.

Third-party extensions version independently:

<!-- ucp:example skip reason="schema authoring example" -->
```json
{
  "name": "com.shopify.loyalty",
  "version": "2025-09-01",
  "spec": "https://shopify.dev/ucp/loyalty",
  "schema": "https://shopify.dev/ucp/schemas/loyalty.json"
}
```

Extension version requirements belong in the extension schema document:
`requires.protocol` constrains the selected `ucp.version`, and
`requires.capabilities` constrains selected parent versions.

## Extensibility and Forward Compatibility

When designing schemas, you must account for how older clients will validate newer payloads. In serialization formats
like Protobuf, adding a new field or enum value is generally a safe, forward-compatible change.

Because modern code generators (e.g. [Quicktype](https://quicktype.io/)) translate JSON Schemas into strictly typed
classes (e.g., Go structs or Java Enums), certain schema constraints will cause deserialization errors on older clients
as the protocol evolves.  Avoiding such changes helps minimize the need to up-version the protocol.

A second failure mode comes from composition itself: extensions extend a base with `allOf`, which can only *add*
constraints. An `allOf` of two enums (or two `oneOf`s) *intersects* their members — it never unions in a new value or
branch — so a closed `enum`, `oneOf`, or `additionalProperties: false` is a one-way door an extension cannot widen.

### Open Enumerations

If a field's list of values might expand in the future (e.g., adding a `"refunded"` status or a new payment method),
**do not use `enum`**.

Instead, define a standard `string`, document the requirement to ignore unknown values in the `description`, and use
`examples` to convey current expected values to code generators. Avoid complex "Open Set" validation patterns
(e.g., combining `anyOf` with `const`), as they frequently confuse client-side code generators and make schemas
difficult to read.

<!-- ucp:example skip reason="schema authoring example" -->
```json
"cancellation_reason": {
  "type": "string",
  "description": "Reason for order cancellation. Clients MUST tolerate and ignore unknown values.",
  "examples": ["customer_requested", "inventory_shortage", "fraud_suspected"]
}
```

### Closed Enumerations

Use strict `enum` or `const` only for permanently fixed domains or when unknown values are inherently unsupported.
Reserve  them for cases where adding a new value inherently requires integrators to update their code (e.g., protocol
versions, strict type discriminators, or days of the week).

<!-- ucp:example skip reason="schema authoring example" -->
```json
"status": {
  "type": "string",
  "enum": ["open", "completed", "expired"],
  "description": "Lifecycle state. This domain is strictly bounded; unknown states represent a breakdown in the state machine and MUST be rejected."
}
```

### Variants (`oneOf`)

`oneOf` models a sum type — a field that is *one of several shapes* — but it is **closed**, with the same one-way-door
problem as `enum`: an extension cannot add a branch (an `allOf` of two `oneOf`s intersects their branches, it does not
union them), and under open objects (`additionalProperties: true`) a payload matching two branches fails `oneOf`
validation.

For a variant set that may grow, model it as open in one of two ways:

- an **open discriminator** — an open `type`/`kind` string that names the active form, with tolerant readers, exactly
  like an open enumeration; or
- a single **open object with documented precedence** — when the active form is implied by which field is present
  rather than a tag, a stated rule decides which one wins if more than one appears.

Reserve `oneOf` for permanently fixed variant sets — the same bar as a closed `enum`.

<!-- ucp:example skip reason="schema authoring example" -->
```json
// PREFER: an open `kind` discriminator — a new variant is a new value; readers tolerate unknowns
"target": {
  "type": "object",
  "required": ["kind"],
  "properties": {
    "kind": {
      "type": "string",
      "description": "Delivery target. Well-known: `email`, `sms`. Unknown values MUST be tolerated.",
      "examples": ["email", "sms"]
    }
  }
}

// AVOID: oneOf — adding a `push` variant means adding a branch, which an extension cannot do
"target": {
  "oneOf": [
    { "required": ["email_address"], "properties": { "email_address": { "type": "string" } } },
    { "required": ["phone_number"],  "properties": { "phone_number":  { "type": "string" } } }
  ]
}
```

### Open Objects (`additionalProperties`)

Marking an object as closed preemptively prevents any future non-breaking additions to the schema. In a distributed
protocol, what would otherwise be a backward-compatible field addition (e.g., adding a "gift_message" field to an order)
becomes a breaking change for any client validating against a closed schema.

By default, JSON Schema is open and ignores unknown properties. Authors should leave this keyword omitted except in rare circumstances: polymorphic discriminators (where strictness prevents oneOf validation ambiguity) or security-critical payloads (where unknown fields may indicate tampering). The `ucp` protocol namespace itself is deliberately open (tolerant readers ignore unrecognized members); typo discipline there is an authoring-time concern, not a wire-validation one.

**Anti-Pattern (Prevents adding new fields without a reversion):**

<!-- ucp:example skip reason="schema authoring example" -->
```json
"totals": {
  "type": "object",
  "properties": {
    "subtotal": {"type": "integer"}
  },
  "additionalProperties": false
}
```

### Property-Count Constraints (`minProperties` / `maxProperties`)

By default, UCP schemas do not set `minProperties` or `maxProperties` on
object fields:

- **`maxProperties`** — Limits are deferred to implementers. The protocol
  does not define caps because any specific limit requires judgment calls
  that inevitably run into exceptions. Implementers are encouraged to
  impose their own constraints and surface clear error feedback to support
  debugging and good behavior.
- **`minProperties`** — Empty objects (`{}`) are well-formed and harmless.
  Implementers should accept and process them as a no-op.

## The `request_constraints` Protocol Member

Normative processing, scope, lifecycle, and invalid-member behavior are defined
in [Request Constraints](../specification/overview/index.md#request-constraints).
This section covers only the schema-authoring boundary.

### Local structure

`request_constraints` is centrally registered in `ucp.json#/$defs/members` as a
response-only protocol member with `ucp_request: "omit"`. Capability, extension,
handler, and shared type schemas do not redeclare it. A conforming UCP-aware
resolver materializes the registered member into eligible response scopes so
ordinary resolved-schema validation applies the shared schema.

`schemas/common/types/constraint_expression.json` defines the closed Constraint
Expression grammar. `schemas/common/types/request_constraints.json` binds that
grammar to data in the next UCP request and is the schema referenced by the
registered member.

| Position | Admitted members | Shape |
| :-- | :-- | :-- |
| Object Constraint | `required`, `properties` | `required` contains unique field names; `properties` maps field names to Object or Value Constraints; an empty object is a no-op. |
| Value Constraint | `enum`, `const` | `enum` is non-empty and unique; at least one member is present; both apply when present together. |

The listed members define the grammar. A `request_constraints` value may
additionally contain `path` at the top level.

Grammar changes belong in `constraint_expression.json`, and changes to the root
Object Constraint must also be reflected in `request_constraints.json`.

### Annotations and applicability

`constraint_expression.json` carries no `ucp_request` annotations. Its
properties are Constraint Expression syntax, not independently placeable UCP
fields, so the grammar has no direction of its own.

Applicability belongs to the containing UCP property. Each UCP property that
exposes a Constraint Expression owns whichever direction-specific applicability
annotations that property requires, and those annotations alone determine when
the grammar is reachable. For `request_constraints`, the containing property is
the member registered in `ucp.json#/$defs/members`; it remains
`ucp_request: "omit"` and is the only place that member's response-only
visibility is declared. Because the grammar is direction-agnostic, the same
file can be referenced from a request-applicable property and from a
response-only one without change.

### Constraint Expression grammar

Except for the outer `path` member, an emitted value and its nested constraint
objects are JSON Schema Draft 2020-12 Constraint Expression syntax, not
structured UCP domain objects. Do not add or materialize ambient `ucp` inside
them. The keys in a `properties` map name fields on a selected request object
and are data, not ambient members.

The containing `ucp` object still follows
[The Reserved `ucp` Member](#the-reserved-ucp-member). A closed structured object
admits that container through its optional reference to
`ucp.json#/$defs/members`, not by declaring `request_constraints` itself.

## Extension-Declared Action Types

Every Action type is declared by an extension and becomes available only when
that extension is negotiated, as defined in
[Actions](../specification/overview/index.md#actions). Before advertising support,
both the Business and the Platform should assess the extension's complete
Action contract. Negotiation is pre-runtime agreement on that contract's
semantics and support; it does not pre-approve every future `config` value or
delegate. Each concrete instance still needs to conform to the composed
schema, the Action-type contract's runtime rules, and Platform policy.

When they apply to the Action type, extension authors should define:

- its Action type key or keys, parent capability, and emission conditions;
- the exact effect that the Action type gates;
- its concrete `config` schema and how the Platform processes it, explicitly
  identifying any field that is executable or causes content to be loaded;
- relevant schemes, origins, delegates, and trust anchors;
- presentation, isolation, and permission controls;
- how the Business observes Action completion and reflects it in a later parent
  response;
- if the parent response can be delayed, any timeout and bounded-backoff rules,
  and whether the Platform can safely process the same Action again; if so,
  every safe-retry condition;
- the fallback when processing fails, is declined, or is abandoned, when the
  Action is unsupported or expires, or when the Business does not update the
  parent response;
- the Action-specific conditions under which work is resolved, superseded, or
  replaced, plus within-type or cross-type ordering semantics when needed.

Extension authors should define only controls relevant to the concrete
processing model. For example, an Action with no loadable URL needs no URL
scheme or origin rules. Extension authors should keep Action-specific data
under `config` and use the existing `allOf` extension composition to contribute
each Action key and `config` shape to the parent capability schema. They should
not introduce a standalone Actions capability or registry. Nor should they
expand the common Actions contract with generic machinery—whether an executor,
callback/result model, state machine, fallback enum, retry field, or polling
protocol. A concrete extension may define its own callback, result, state,
fallback, retry, timeout, or backoff semantics when genuinely required by its
Action type.

## Complete Example: Capability Schema

A capability schema defines both payload structure and declaration variants:

<!-- ucp:example skip reason="schema authoring example" -->
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json",
  "name": "dev.ucp.shopping.checkout",
  "version": "{{ ucp_version }}",
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

## Documenting JSON Examples

UCP's specification documents are validated mechanically. Every ` ```json `
block is either checked against the schemas the spec defines or explicitly
marked as out-of-scope. Schema drift breaks CI instead of silently misleading
readers.

To make this work, UCP examples use a **bespoke JSON capability set**: strict
JSON plus a small, fixed set of authoring conveniences. The validator reduces
these conveniences to canonical JSON before validating against schema. Authors
write enriched JSON; the wire format remains strict JSON.

### The annotation contract

Every ` ```json ` block in the spec **MUST** be preceded by an annotation
comment. Unannotated blocks fail CI.

<!-- ucp:example skip reason="example validation guide" -->
```json
<!-- ucp:example schema=shopping/checkout op=read -->
{ ... }
```

#### Annotation grammar

```text
<!-- ucp:example schema=PATH [op=OP] [direction=DIR] [extract=JSONPATH] [target=JSONPATH] [def=NAME] -->
<!-- ucp:example skip reason="..." -->
```

| Attribute     | Required          | Default    | Purpose                                                                    |
| ------------- | ----------------- | ---------- | -------------------------------------------------------------------------- |
| `schema`      | yes (unless skip) | —          | Schema to validate against, e.g. `shopping/checkout`                       |
| `op`          | no                | `read`     | Operation: `create`, `read`, `update`, `complete`, `cancel`, etc.          |
| `direction`   | no                | `response` | `request` or `response`                                                    |
| `extract`     | no                | `$`        | JSONPath inside the displayed block; selected subtree becomes the example  |
| `target`      | no                | `$`        | JSONPath into the schema/scaffold; example replaces a sub-tree             |
| `def`         | no                | —          | Pull `$defs/<name>` out of the schema and validate against that            |
| `skip reason` | yes (with skip)   | —          | Free-form prose explaining why this block can't be validated               |

#### Placement rules

- The annotation **MUST** appear on its own line preceding the ` ```json `
  fence. Blank lines between are allowed.
- One annotation per block. **Multiple stacked annotations are rejected.**
<!-- cspell:ignore shema -->
- **Unknown attribute names are rejected.** A typo like `shema=` fails CI
  rather than silently dropping the attribute.

### Authoring conveniences

The validator accepts these features beyond strict JSON. Use them where they
aid clarity; default to strict JSON otherwise.

#### Line comments

`//` to end-of-line. Stripped before validation.

<!-- ucp:example skip reason="example validation guide" -->
```json
{
  "currency": "USD",       // ISO 4217
  "amount": 5000           // minor units (cents)
}
```

Block comments (`/* */`) are **not** supported. Use multiple `//` lines if you
need a multi-line note.

**Limitation:** the `//` stripper tracks string boundaries per-line and is
approximate. An example containing a string literal with an escaped backslash
followed by `//` will be misparsed. No corpus example currently triggers this;
if you hit it, restructure the example.

#### Template variable

Exactly one variable is substituted: `{{ ucp_version }}` becomes a valid date
stamp. No other template variables are recognized — any other `{{ name }}`
will survive into JSON parse and fail.

#### HTTP envelope

If the first non-blank line matches an HTTP request line
(`GET|POST|PUT|PATCH|DELETE`) or status line (`HTTP/`), the validator extracts
the JSON body after the first blank line. Headers between are ignored.

<!-- ucp:example skip reason="example validation guide" -->
```json
POST /checkout-sessions HTTP/1.1
Host: api.example.com
Content-Type: application/json

{ "line_items": [ ... ] }
```

Other HTTP methods (`OPTIONS`, `HEAD`, `CONNECT`, `TRACE`) are not recognized
as envelopes — they would be parsed as JSON and fail.

#### Extracting from envelopes

Use `extract=` when the displayed JSON block is a transport or wrapper object
but the UCP payload to validate is nested inside it. `extract=` reads from the
displayed example; `target=` writes the extracted value into the validation
scaffold.

```text
<!-- ucp:example schema=shopping/checkout op=create direction=request extract=$.params.arguments.checkout -->
```

```text
<!-- ucp:example schema=shopping/checkout extract=$.result.structuredContent.totals target=$.totals -->
```

The first example validates the nested checkout request. The second extracts a
`totals` fragment from a displayed envelope, inserts it into `$.totals` of the
checkout scaffold, and validates the merged checkout.

#### Elision markers

The validator understands shapes that mean **"this required field is present;
its value is not asserted."** Coverage check still verifies the field is
acknowledged. Schema validation errors at the elided sub-tree are suppressed.

| Shape                | Meaning                                                |
| -------------------- | ------------------------------------------------------ |
| `"..."`              | A field's value is elided                              |
| `[ ... ]`            | A non-empty array; contents elided                     |
| `{ ... }`            | A non-empty object; contents elided                    |
| `[ "..." ]`          | Equivalent to `[ ... ]`                                |
| `{ "...": "..." }`   | Equivalent to `{ ... }`                                |

<!-- ucp:example skip reason="example validation guide" -->
```json
{
  "ucp": { ... },
  "id": "chk_abc",
  "currency": "USD",
  "line_items": [ ... ],
  "totals": [ ... ]
}
```

The bare-form `[ ... ]` and `{ ... }` are the canonical way to elide
container contents. They communicate the right semantics: *a non-empty
container whose members exist but are not shown.* The string-sentinel forms
(`["..."]`, `{"...": "..."}`) are accepted for parser convenience but say
something subtly wrong literally — they describe *an array containing one
string* or *an object with one key.* Prefer the bare form in new examples.

**Limitations:**

- Bare `...` is recognized only as the **sole content** of an array or object.
  Interior bare-dot forms like `[a, ..., b]` are not supported.
- For partial elision (some items shown, some elided), use the string form
  `"..."` at the position to elide: `[1, "...", 3]`.
- The literal three-character string `"..."` cannot appear in an example as
  actual data — it is reserved as the elision sentinel. Use a Unicode escape
  (`"\u002e\u002e\u002e"`) if you genuinely need it.

### What is not supported

- **Trailing commas** before `}` or `]`. Strict JSON only; the wire format is
  strict, the spec stays honest.
- **Block comments** `/* */`.
- **JSON5 features**: single-quoted strings, unquoted keys, hex literals,
  `NaN` / `Infinity`, multi-line strings.
- **Multiple template variables** beyond `{{ ucp_version }}`.
- **Interior bare ellipsis** `[a, ..., b]`.

### Skip reasons

When a block can't be validated, use `skip` with a precise reason. Skip
reasons are CI-grepable; they track what's not yet covered.

Established categories — extend as needed, but be specific:

- `"JSON-RPC transport binding"` — wrapped in JSON-RPC envelope
- `"embedded protocol binding"` — Embedded Protocol transport wrapper
- `"A2A transport binding"` — A2A transport wrapper
- `"profile document, no wrapper schema"` — top-level `ucp` block, no
  enclosing entity
- `"schema authoring example"` — JSON Schema fragments, not UCP payloads
- `"handler config example"` / `"handler schema definition"` — payment
  handler internals
- `"capability declaration fragment"` — capability registry snippet
- `"OAuth metadata, not UCP payload"` — third-party protocol payloads
- `"cryptographic material, not UCP payload"` — keys, signatures
- `"<feature> fragment"` — incomplete object showing one nested field

Avoid vague reasons like `"conceptual example"`. The taxonomy is how we
prioritize what to validate next.

### Common patterns

**Full request or response.** The default case. The example is a complete
payload for the named operation.

```text
<!-- ucp:example schema=shopping/cart op=create direction=request -->
```

**Sub-tree with surrounding context.** Use `target=` when the example focuses
on one field. The example is spliced into a known-valid scaffold at that
target path; the rest uses the scaffold's defaults.

```text
<!-- ucp:example schema=shopping/checkout target=$.totals -->
```

**Displayed envelope with nested payload.** Use `extract=` when the code block
shows an envelope but only a subtree is the UCP payload under validation.

```text
<!-- ucp:example schema=shopping/checkout op=create direction=request extract=$.params.arguments.checkout -->
```

**Schema with `$defs`.** Some schemas hold several message shapes under
`$defs`. When a capability's request and response are different objects (e.g.
catalog: a search request is a query, a search response is a list of products),
just name the operation and direction — the validator selects
`$defs/{op}_{direction}` automatically:

```text
<!-- ucp:example schema=shopping/catalog_search op=search direction=response extract=$.result.structuredContent -->
```

For a shape that isn't an operation+direction — a transport's `error_response`,
a profile's `business_schema`, or a named sub-type — select it explicitly with
`def=`:

```text
<!-- ucp:example schema=transports/jsonrpc def=error_response op=read -->
```

**Empty body.** A `{}` payload (e.g. cancel, GET) validates trivially against
the matching op + direction. No special syntax needed.

### Keep validator wiring invisible

The validation contract is repo infrastructure: annotations, scaffolds, and
schema file paths. Readers of the rendered specification see only protocol
prose and JSON examples — never the wiring.

This works because:

- Annotations live in HTML comments (`<!-- ucp:example ... -->`) that don't
  render.
- Scaffolds live under `scripts/scaffolds/`.
- Validator schemas live under `source/schemas/` (and
  `source/schemas/transports/` for envelope schemas).

When you add a JSON example, pointing the validator at the right schema is
**annotation work, not prose work.** The annotation already names the schema
and the validator already enforces its scope. Sentences like *"this binding
is schema-defined by `transports/X.json`, which validates A but not B"*
duplicate what the annotation says and leak validator internals into
reader-facing pages.

If a binding has genuine scope confusion worth preempting — e.g. *"UCP's
A2A binding does not redefine the A2A protocol"* — say it in **protocol
terms**, not as a schema-coverage note. The protocol concern is real; the
file path isn't part of it.

### What authors don't do

- **Don't invent skip reasons that hide bugs.** If validation fails because
  the example is wrong, fix the example.
- **Don't put validation directives in comments.** Comments are documentation
  for human readers; they are not interpreted by the validator.
- **Don't use unsupported syntax.** The "what is not supported" list above is
  exhaustive — additions require updating the contract and the validator
  together, not stretching the parser.
- **Don't nest ` ```json ` blocks** or place annotations in indented contexts
  where the markdown parser might miss them.

### Running the validator locally

The validator is pure stdlib Python and shells out to the
[`ucp-schema`](https://github.com/universal-commerce-protocol/ucp-schema)
binary for schema resolution and payload validation. First-time setup:

```bash
uv sync                                   # Python deps
cargo install ucp-schema                  # validator backend
uv tool install pre-commit                # if not already installed
pre-commit install --hook-type pre-commit --hook-type pre-push
```

The `--hook-type pre-push` flag is important: pre-commit only installs the
`pre-commit` stage hook by default, but this repo also uses `pre-push`
hooks as a safety net. Pass both to opt into the full enforcement story.

Manual invocation:

```bash
python3 scripts/validate_examples.py --schema-base source/schemas/
python3 scripts/validate_examples.py --schema-base source/schemas/ --file docs/specification/shopping/checkout/rest.md docs/specification/shopping/cart/index.md
python3 scripts/validate_examples.py --schema-base source/schemas/ --audit
```

The `--audit` mode lists blocks without validating them — useful for counting
skips and identifying unannotated blocks. `--file` accepts one or more paths
for incremental validation.

#### What runs automatically

The "schema drift breaks CI" claim above is enforced by three surfaces:

| Surface | Scope | When |
| --- | --- | --- |
| `pre-commit` stage hook | Changed `docs/*.md` files only | Every `git commit` (if installed) |
| `pre-commit` stage hook | Full corpus | Every `git commit` that touches `source/schemas/` or the validator itself |
| `pre-push` stage hook | Same as pre-commit | Every `git push` — catches `--no-verify` bypasses |
| CI (`.github/workflows/docs.yml`) | Full corpus | Every PR — the mandatory backstop |

The pre-commit hooks are opt-in (require the install commands above);
CI is unconditional. Skipping local hooks doesn't break anything — PRs
with unannotated blocks or broken validation will fail CI — but local
hooks give earlier feedback than waiting for the GitHub Actions run.

#### When the full-corpus check fires (and why)

The pre-commit/pre-push split between "changed files only" and "full
corpus" is intentional:

- **Doc edits** (`docs/*.md`) validate only the changed files. Catches
  direct errors — unannotated blocks, wrong schema name, broken example
  payload — in the file you're editing, fast.
- **Schema or validator-code edits** trigger a full-corpus check. A
  single change to `source/schemas/shopping/cart.json` (or to
  `validate_examples.py` itself) can invalidate examples across many
  unrelated docs. The full check is the only way to catch that
  cross-file regression locally before it hits CI.
