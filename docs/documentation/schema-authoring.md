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
| `name` | UCP | Reverse-domain identifier; doubles as registry key | Capabilities, services, handlers |
| `version` | UCP | Entity version (`YYYY-MM-DD` format) | Capabilities, services, payment handlers |
| `id` | UCP | Instance identifier for multiple configurations | Payment handlers only |

### Why Self-Describing?

Capability schemas **must be self-describing**: when a platform fetches a schema,
it should determine exactly what capability and version it represents without
cross-referencing other documents. This matters because:

1. **Independent versioning**: Capabilities may version independently. The schema
   must declare its version explicitly—you can't infer it from the URL.

2. **Validation**: Validators can cross-check that a capability declaration's
   `schema` URL points to a schema whose embedded `name`/`version` match the
   declaration. Mismatches are authoring errors caught at build time.

3. **Developer experience**: When reading a schema file, integrators immediately
   see what capability it defines without reverse-engineering the `$id` URL.

4. **Compact namespace**: The `name` field provides a standardized reverse-domain
   identifier (e.g., `dev.ucp.shopping.checkout`) that's more compact and semantic
   than the full `$id` URL.

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
- **Breaking change management**: New versions get new dates; old versions remain
  valid and resolvable
- **Independent lifecycles**: Extensions can release on their own schedule

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

- **Top-level fields**: `$schema`, `$id`, `title`, `description`, `name`, `version`
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

**→ See [Payment Handler Guide](../specification/payment-handler-guide.md)** for detailed
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

| Context | Location | Required Fields |
| ------- | -------- | --------------- |
| Platform Profile | Advertised URI | `version`, `spec`, `schema` |
| Business Profile | `/.well-known/ucp` | `version`; may add `config` |
| API Responses | Checkout/order payloads | `version` (+ `id` for handlers) |

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
      "multi_destination": {"shipping": {"allowed": true}}
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

### UCP Capabilities (`dev.ucp.*`)

UCP-authored capabilities version with protocol releases by default. Individual
capabilities **may** version independently when needed.

### Vendor Capabilities (`com.{vendor}.*`)

Capabilities outside `dev.ucp.*` version fully independently:

<!-- ucp:example skip reason="schema authoring example" -->
```json
{
  "name": "com.shopify.loyalty",
  "version": "2025-09-01",
  "spec": "https://shopify.dev/ucp/loyalty",
  "schema": "https://shopify.dev/ucp/schemas/loyalty.json"
}
```

Vendor schemas follow the same self-describing requirements.

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

By default, JSON Schema is open and ignores unknown properties. Authors should leave this keyword omitted except in rare
circumstances: polymorphic discriminators (where strictness prevents oneOf validation ambiguity), security-critical
payloads (where unknown fields may indicate tampering), or protocol envelopes (where strictness is useful to catch
typos in core metadata like the `ucp` block).

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
python3 scripts/validate_examples.py --schema-base source/schemas/ --file docs/specification/checkout-rest.md docs/specification/cart.md
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
