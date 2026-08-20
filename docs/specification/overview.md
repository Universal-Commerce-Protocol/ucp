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

# Universal Commerce Protocol (UCP) Official Specification

## Overarching guidelines

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this
document are to be interpreted as described in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.html){ target="_blank" } and
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174.html){ target="_blank" }.

Schema notes:

- Date format: Always specified as
    [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339.html){ target="_blank" }
    unless otherwise specified
- Amounts format: Minor units (cents)

## Quantities and units

UCP uses a shared quantity representation wherever a schema contains an integer
`quantity`, a `quantity_unit`, or the shared measure type.

A `quantity` is an integer count of **steps**. A unit descriptor consists of:

- `unit` — a required, stable machine identifier.
- `scale` — an optional nonnegative integer, at most 15 (a bound derived from
    the integer range; see below). Its effective value is the provided value or
    `0` when omitted.
- `display_text` — a required printable label for the unit.

One step is `10^-scale` of `unit`. The shared measure type adds a required
integer `value`, which is also a count of those steps. Because these counts are
integers, `scale` fixes the representation's granularity. A unit descriptor's
machine identity is the (`unit`, effective `scale`) pair; `display_text` is not
part of that identity. This identity applies only to the unit descriptor; it
does not identify the purchasable item or exhaustively describe one sale unit.

The default sale basis is `each`, with machine identity (`C62`, `0`). `C62` is
the United Nations Centre for Trade Facilitation and Electronic Business
(UN/CEFACT) Recommendation 20 (Rec20) Common Code for one/each. The Business
**MAY** omit `quantity_unit` from an authoritative Business representation to
encode this default. When a Business or Platform includes a
descriptor whose `unit` is `C62`, it **MUST** use an effective `scale` of `0`;
`scale` can only be omitted or explicitly set to `0`.

UCP does not put floating-point numbers on the wire. Quantity arithmetic
feeds money — `price × quantity × 10^-scale` prices a line, `fulfilled`
accumulates across fulfillment events, and status derives from
`fulfilled == total` — so quantities get money's representation: an integer
count plus a declared interpretation, exactly as an `amount` relates to its
`currency`. Integer counts keep every total and comparison exact in every
language, and UCP therefore defines no rounding tolerances and no epsilon
comparisons anywhere in the quantity lifecycle. A fulfilled quantity that
legitimately differs from the ordered quantity — a 1.90 lb pick against a
2.00 lb order — is a commercial fact reconciled through
[adjustments](order.md#adjustments) that move money together with quantity,
not a numeric error absorbed by comparison fuzz.

Reading a quantity requires no arithmetic and no unit knowledge: shift the
decimal point `scale` places and append `display_text`. `150` with
`{ "scale": 2, "display_text": "kg" }` renders as `1.50 kg`, by the same code
path for a Rec20 code and for a custom unit. Unlike a currency exponent,
`scale` is per-item data rather than a static table — which is why
authoritative responses always carry their own descriptor on every non-`each`
line.

### Integer range and ingestion

Every integer-valued field in UCP — amounts, quantity step counts, measure
values — is a JSON integer; each field's schema declares its sign and
bounds, and all are capped at ±(2^53 − 1) (±9,007,199,254,740,991) — the
range within which every JSON implementation agrees exactly on integer
values
([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259.html){ target="_blank" },
Section 6) and within which
[JCS](https://www.rfc-editor.org/rfc/rfc8785.html){ target="_blank" }
canonicalization, required for
[AP2 mandate signing](ap2-mandates.md#canonicalization), is defined. The
same cap derives `scale`'s maximum of 15: at scale 16, one whole unit
(10^16 steps) would be unrepresentable. An out-of-range value is
schema-invalid and is rejected like any other invalid payload.

Arithmetic over these values **MUST** be exact. Within the wire range,
IEEE 754 binary64 — a JavaScript `Number` from `JSON.parse` — holds every
integer exactly; products such as `amount × quantity` can exceed 64 bits, so
use wider or arbitrary-precision integers, or overflow checks. An
implementation that cannot produce an exact, in-range result **MUST**
surface an error rather than emit, display, or act on an approximate or
wrapped value.

When UCP data crosses into external systems, implementations **SHOULD**
convert once at ingestion — apply the declared scale (or currency exponent)
into an exact decimal type (SQL `NUMERIC`, Java `BigDecimal`, Python
`Decimal`), or carry the (value, scale) pair unchanged — and **SHOULD NOT**
perform scale application or value-bearing arithmetic in binary floating
point.

### Unit vocabulary

The Business **SHOULD** use the exact Rec20 Common Code unless no code
accurately identifies the unit. When no Rec20 code accurately identifies the
unit, the Business **MAY** use a custom unit identifier. If it does, the Business
**MUST** use that identifier consistently for the same unit. The Platform
**MUST** treat an unrecognized `unit` value as opaque. The following table is
non-exhaustive:

| Code  | Unit         |
| :---- | :----------- |
| `C62` | one / `each` |
| `KGM` | kilogram     |
| `GRM` | gram         |
| `LBR` | pound        |
| `MLT` | millilitre   |
| `LTR` | litre        |
| `MTR` | metre        |
| `INH` | inch         |
| `YRD` | yard         |
| `FTK` | square foot  |
| `MTK` | square metre |
| `HUR` | hour         |
| `MIN` | minute       |

Rec20 includes X-prefixed package units derived from UN/CEFACT Recommendation
21 (Rec21). UCP deliberately excludes those values from `quantity_unit`. The
Business **MUST** make package form part of the purchasable variant's identity
and count packages as `each`. The Business **MUST NOT** use an X-prefixed
Rec21-derived package code as `quantity_unit`.

### Display text

When sending a unit descriptor, a Business or Platform **MUST** include
`display_text`. The Platform **MUST** use that value when it does not recognize
`unit`. For a recognized Rec20 code, the Platform **MAY** substitute its own
localized label. The Business and Platform **MUST NOT** use `display_text` when
matching machine identities or as an input to quantity conversion.

### Ordering increment

A sale-basis descriptor (`quantity_unit`) **MAY** declare an `increment`: an
optional positive integer, denominated in steps, whose effective value is the
provided value or `1` when omitted. Only the sale basis carries an increment;
the bare unit descriptor and the shared measure type do not. It declares the
ordering granularity the Business sells in — for example, an item sold by the
pound with `scale` `2` and `increment` `25` is sold in 0.25 lb multiples.

`scale` and `increment` play different roles: `scale` bounds what any quantity
can express; `increment` shapes what the Platform asks for. The increment is
advisory merchandising policy, not a representational bound — Platform-authored
quantities **SHOULD** be integer multiples of the line's effective increment,
while Business-authored quantities (checkout revisions, fulfillment events,
adjustments) are bounded only by `scale`. `increment` is not part of the
unit-descriptor machine identity and **MUST NOT** participate in mismatch
comparison.

Request assertions, mismatch handling, response echo, off-increment request
handling, pricing, and lifecycle behavior are defined by the capability that
uses the shared representation.

## Request Constraints

After capabilities and extensions are negotiated, the resolved UCP request
schema defines the fields and structure allowed for an operation. In an
authoritative response, a Business can use `ucp.request_constraints` to signal
additional rules it will apply when evaluating request data in the next
Platform request. For example, it can constrain a Line Item quantity to exactly
`100` sale-basis steps or require a submitted payment instrument to include
`billing_address`. A Platform can evaluate these constraints before submission,
avoiding a round trip for request data the Business has already indicated it
will reject.

`ucp.request_constraints` is used only in authoritative operation responses and
has no effect in discovery profiles or operation requests.

### Validation model

A submitted request is valid under Request Constraints only if it satisfies the
resolved request schema and every object selected by Request Constraints
satisfies the corresponding Constraint Expression. Request Constraints only
narrow the resolved request schema; they cannot make a request valid when that
schema rejects it. A Business evaluates the request as follows:

```text
valid = validate(resolved_request_schema, request)

for each constraint:
  objects = select(request, effective_path(constraint))
  valid = valid AND validate_all(
    constraint_expression(constraint),
    objects
  )

return valid
```

A Platform **MAY** perform the same checks as preflight. For each chosen value,
the Platform **MUST** use its effective path and complete Constraint Expression.
The Platform **MAY** submit the request regardless of the preflight result;
Business evaluation is authoritative.

### Constraint Expression

A `request_constraints` value and every nested constraint object use embedded
JSON Schema Draft 2020-12 language. The outer value may additionally contain an
optional `path`; nested constraint objects may not. The grammar does not admit
`ucp`. Keys in `properties` name fields on selected request objects.

The constraint begins at an Object Constraint. Object Constraints may nest
through `properties`; Value Constraints occur only as values in an Object
Constraint's `properties` map.

| Position | Admitted members | Shape and behavior |
| :-- | :-- | :-- |
| Object Constraint | `required`, `properties` | `required` is an array of unique field names. `properties` maps field names to Object or Value Constraints. An empty Object Constraint is a valid no-op at any Object Constraint position. |
| Value Constraint | `enum`, `const` | `enum` is a non-empty array of unique JSON values. `const` is any JSON value. At least one member is present; when both are present, both apply. |

No other member is admitted at either grammar position.

### Path

Every `request_constraints` value has exactly one effective path. When `path`
is omitted, the effective path is the
[RFC 9535](https://www.rfc-editor.org/rfc/rfc9535.html){ target="_blank" }
Normalized Path from the authoritative response root to the structured response
object whose `ucp` member contains `request_constraints`. When the Business
provides `path`, that value becomes the effective path and supersedes the
Normalized Path that would otherwise be derived; the Business **MUST** make it
a complete RFC 9535 JSONPath query. In both cases, the effective path is
evaluated against the next logical UCP request to that resource. The effective
path therefore differs from response-targeting paths elsewhere in UCP, such as
`messages[].path`, which are evaluated against the response that carries them.

An omitted path establishes positional correspondence for the next request, not
stable identity: an array index still identifies that position if items reorder
before that request. A Business **MUST** provide an explicit `path` when the
Normalized Path of that structured response object does not identify the
intended request objects. When a constraint must follow a stable identity into
the next request, the Business **MUST** use an explicit query that encodes that
association.

A Business that constructs a query from data **MUST** serialize and escape each
dynamic value as a valid RFC 9535 literal and **MUST NOT** use unsafe string
concatenation.

Before emitting a value, a Business **MUST** validate the complete value against
the shared
[Request Constraints](site:schemas/common/types/request_constraints.json)
schema, and a Platform **MUST** do the same before using that value for
preflight; `path` selects the objects and the remaining members form the
[Constraint Expression](site:schemas/common/types/constraint_expression.json).

A constraint is not tied to an operation name; it applies to every object its
path selects. A path that selects zero objects has no effect. When
`request_constraints` is in the response root's `ucp` member and `path` is
omitted, the effective path is `$`.

If multiple paths select the same object, every corresponding Constraint
Expression applies. The shared Request Constraints schema validates each value
independently and cannot guarantee that expressions across overlapping paths can
all be satisfied. A Business **MUST** ensure expressions that can apply to the
same object are jointly satisfiable. Contradictory requirements on the same
property are a Business authoring error.

A Platform that performs preflight on overlapping values evaluates every value
it chose; if any chosen value fails for the concrete request, preflight fails.
There is no precedence or override.

### Guidelines

#### Business

A Business **MAY** include `ucp.request_constraints` in an authoritative
response to describe rules it will enforce against request data in the next
Platform request. The Business **MUST** emit Request Constraints that conform to
the shared Request Constraints schema, **MUST** use valid effective paths that
select only objects, and **MUST** enforce every constraint it emits against that
next request.

A Business **SHOULD NOT** emit Request Constraints for rules that may change
before the next request unless it can continue to enforce the advertised
constraint. Execution-time conditions such as inventory availability, fraud
decisions, and payment authorization remain governed by the operation's existing
outcomes and `messages`.

#### Platform

A Platform **MAY** use `ucp.request_constraints` for preflight before submitting
request data. It **MAY** evaluate any supported subset of values. This preflight
is optional and advisory.

A malformed or unsupported value, a value whose path selects a non-object, or a
value the Platform cannot evaluate within its resource limits is unavailable
for preflight, not a pass or failure. A Platform performing preflight **MUST**
skip the whole unavailable value and continue with any other chosen values. If
complete evaluation finds a violation, that value fails preflight.

A successful preflight result covers only the values the Platform evaluated.
UCP defines no new wire status or issue-marker field for preflight results.

### Scope and lifecycle

Each authoritative resource response from the Business supplies Request
Constraints for the next request to that resource. The authoritative response
to that request supplies the constraints for the following request and replaces
the prior set. Omission clears the set. Invalid values in the new set do not
preserve stale values, and sets are not merged by `path`.

Only `request_constraints` values attached to eligible structured response
objects under the [Reserved `ucp` Member](#the-ucp-protocol-namespace) rules
make up the set; dictionary keys are data.

A response without an authoritative resource supplies no Request Constraints
set for a following request. A response containing an authoritative resource
supplies the set even when it reports an application error. A partial
authoritative resource representation supplies a set only when the resource
contract defines its scope.

### Operation outcomes

Request Constraints provide proactive, machine-evaluable preflight for the next
request; `messages` report outcomes from a submitted request, including runtime
outcomes. Passing validation against both the resolved request schema and
Request Constraints establishes only schema validity; the request can still
fail other Business rules. The containing operation's existing semantics and
outcome/error contract, including `messages`, continue to govern
submitted-request and runtime outcomes. Request Constraints add no outcome or
error code.

### Examples

#### Basket-wide and targeted quantities

The following Cart responses are alternatives that illustrate different scopes.

=== "Basket-wide"

    <!-- ucp:example schema=shopping/cart op=read direction=response -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "request_constraints": {
          "path": "$['line_items'][*]",
          "properties": {
            "quantity": {"const": 1}
          }
        }
      },
      "id": "cart_123",
      "line_items": [
        {
          "id": "line_123",
          "item": {
            "id": "sku_123",
            "title": "Bulk screws",
            "price": 1200
          },
          "quantity": 1,
          "totals": [
            {"type": "subtotal", "amount": 1200},
            {"type": "total", "amount": 1200}
          ]
        }
      ],
      "currency": "USD",
      "totals": [
        {"type": "subtotal", "amount": 1200},
        {"type": "total", "amount": 1200}
      ]
    }
    ```

=== "Targeted"

    <!-- ucp:example schema=shopping/cart op=read direction=response -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}"
      },
      "id": "cart_123",
      "line_items": [
        {
          "id": "line_123",
          "item": {
            "id": "sku_123",
            "title": "Bulk screws",
            "price": 1200
          },
          "quantity": 100,
          "totals": [
            {"type": "subtotal", "amount": 120000},
            {"type": "total", "amount": 120000}
          ],
          "ucp": {
            "request_constraints": {
              "path": "$['line_items'][?@['id'] == 'line_123']",
              "properties": {
                "quantity": {"const": 100}
              }
            }
          }
        }
      ],
      "currency": "USD",
      "totals": [
        {"type": "subtotal", "amount": 120000},
        {"type": "total", "amount": 120000}
      ]
    }
    ```

The basket-wide response emits a root constraint that applies quantity `1` to
every Line Item in the next request. The targeted response uses ambient local
authoring and a stable-ID path to apply quantity `100` only to the Line Item
whose `id` is `line_123`; stable-ID rebinding survives reorder. If that path
finds no match, it selects zero objects and has no effect. These are separate
responses and alternatives. Combining them as written would create
contradictory constraints for `line_123` and is a Business authoring error.

#### Locked negotiated discount codes

This Checkout response has the Discount extension active and advertises Request
Constraints for the next Checkout Update request. Because `request_constraints`
is in the Checkout response root's `ucp`, omitting `path` derives that
structured response object's Normalized Path. For this root placement, the
derived path is `$`, which selects the next request root.

<!-- ucp:example schema=shopping/discount def=dev.ucp.shopping.checkout op=update direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "success",
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {"version": "{{ ucp_version }}"}
      ],
      "dev.ucp.shopping.discount": [
        {"version": "{{ ucp_version }}"}
      ]
    },
    "payment_handlers": {},
    "request_constraints": {
      "required": ["discounts"],
      "properties": {
        "discounts": {
          "required": ["codes"],
          "properties": {
            "codes": {"const": ["ACME-X7Q9-L2M4"]}
          }
        }
      }
    }
  },
  "id": "checkout_123",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [
    {
      "id": "line_123",
      "item": {
        "id": "sku_123",
        "title": "Bulk screws",
        "price": 1200
      },
      "quantity": 24,
      "totals": [
        {"type": "subtotal", "amount": 28800},
        {"type": "total", "amount": 28800}
      ]
    }
  ],
  "totals": [
    {"type": "subtotal", "amount": 28800},
    {"type": "total", "amount": 28800}
  ],
  "links": [
    {
      "type": "terms_of_service",
      "url": "https://business.example/terms"
    }
  ],
  "discounts": {
    "codes": ["ACME-X7Q9-L2M4"]
  }
}
```

The next Checkout Update request is valid only if it satisfies the resolved
request schema, contains `discounts.codes`, and supplies exactly
`["ACME-X7Q9-L2M4"]`.

#### Billing address on a submitted card instrument

In this example, a Business emits `ucp.request_constraints` on an available card
instrument to require `billing_address` in the next request if it contains a
matching submitted card instrument:

<!-- ucp:example schema=shopping/types/available_payment_instrument op=read direction=response -->
```json
{
  "type": "card",
  "ucp": {
    "request_constraints": {
      "path": "$['payment']['instruments'][?@['handler_id'] == 'processor_1' && @['type'] == 'card']",
      "required": ["billing_address"]
    }
  }
}
```

This fragment assumes its containing authoritative response payment-handler
declaration has `id: processor_1`. The explicit `path` crosses from the
response's `available_instruments[]` shape to submitted `payment.instruments[]`
and matches instruments by `handler_id` and `type`. If the next request contains
a match, the constraint requires `billing_address` on every matching instrument.
The payment-handler or instrument contract defines any stronger association.
This example does not define card brands, credentials, support, availability, or
payment policy.

## Actions

An Action is an outstanding unit of extension-defined work for a Platform to
process. Its presence means the effect defined by its Action type is gated.
Actions appear only in responses, under the `actions` map. The common
fields identify the work but do not define how to process it; the active
extension does.

This section defines the common Actions shape and the invariants every adopting
response shares. The shape is reusable, but a capability supports Actions only
when its specification explicitly adopts it and defines the parent-specific
behavior: where Actions appear, the effect each Action type gates, how Messages
apply, and how a later response reflects processing. Schema composition alone
does not establish support. Cart, Checkout, and Catalog adopt this shape; see
[Cart — Actions](cart.md#actions),
[Checkout — Actions](checkout.md#actions), and
[Catalog — Actions](catalog/index.md#actions) for their parent-specific
contracts.

Actions and Messages have different roles. An Action represents outstanding
work: it carries an identity and extension-owned processing configuration. A
Message communicates explanatory or diagnostic context about the current
response and can identify an exact Action occurrence through its RFC 9535
`path`. When a Message includes `path`, the Business **MUST** make it an RFC
9535 JSONPath expression relative to the root of the containing UCP response
object.
Messages do not define how an Action is processed or determine its outcome, and
neither an Action nor a Message requires the other.

For example, a Business can surface one outstanding Action beside an
explanatory Message (an illustrative, partial fragment):

<!-- ucp:example skip reason="illustrative fragment" -->
```json
{
  "actions": {
    "com.example.identity.student_verification": [
      {
        "id": "verify-student-1",
        "config": {
          "verification_url": "https://business.example.com/verify/abc"
        }
      }
    ]
  },
  "messages": [
    {
      "type": "info",
      "code": "eligibility_accepted",
      "content": "Student discount applied provisionally. Verify your status.",
      "path": "$.actions['com.example.identity.student_verification'][0]"
    }
  ]
}
```

The Action identifies the outstanding work and carries extension-owned
processing configuration under `config`. The Message's `path` selects the exact
Action occurrence it explains. The
[checkout eligibility example](checkout.md#eligibility-verification-at-completion)
composes this pattern into a complete Student Verification flow.

For a newly processed successful response from a capability that adopts Actions,
the Business **MUST** include every outstanding Action and **MUST** omit
`actions` when none are outstanding.

Cart and Checkout define request idempotency separately. Duplicate requests
follow those existing rules and can return the original cached response,
including its `actions` (see
[Message Signatures — Replay Protection](signatures.md#replay-protection)).

An Action's gate and an operation-specific outcome are orthogonal. Neither a
parent status nor a Message's type or severity determines whether an Action
gates its Action-defined effect. A Message explains the response or reports the
outcome of a particular requested effect. A Business **MAY** include an info or
warning Message whose `path` selects an outstanding Action to explain the
current response without reporting an operation failure. For a state-changing
operation whose requested effect was not applied because of an Action, the
Business **MUST** instead return the current resource with a `recoverable` error
Message whose `path` selects the exact Action occurrence.

The Business's response is authoritative for the state after an operation: the
returned resource, together with any parent lifecycle its capability defines, is
the source of truth. The Action-type contract defines how the Business observes
processing, and the Platform then follows the containing capability's operation
contract.

When an Action prevents a Cart or Checkout operation from succeeding,
processing the Action does not repeat that operation. If the Platform wants to
try again, it submits a new operation under the existing
[Replay Protection](signatures.md#replay-protection) rules.

Each Action key is a reverse-domain **Action type**: the name identifies the
type of outstanding work, which is not necessarily the name of the extension
that declares it. An active extension declares each Action type and defines its
`config`, how a Platform processes it, its trust and fallback, and its outcomes.
A single extension can declare more than one Action type. Each declaring
extension contributes its Action-type keys to the containing capability's
schema through `allOf` composition (see
[Schema Composition](#schema-composition)), and capability negotiation selects
which extensions are active. Negotiating an extension activates the whole
contract it declares, including every Action type within it.

Action type keys follow existing [Namespace Governance](#namespace-governance)
rules: an extension can declare only types within a reverse-domain namespace
controlled by its schema authority. An extension can use its own name as the key
for a single Action type — as the
[Student Verification example](checkout.md#eligibility-verification-at-completion)
does — or declare several Action types under distinct keys. Each value is a
non-empty array of outstanding instances of that one Action type. The key
identifies the type, so an instance carries no separate type discriminator; a
Business surfaces multiple outstanding instances of the same type as multiple
entries in that array.

The `actions` map does not define a processing order across Action types. Within
a single type's array, JSON preserves the order of its instances, and the
extension that declares the type defines whether that order carries processing
meaning. When ordering across Action types matters, the declaring extension
defines the sequencing and which Action types become outstanding at each step.

For example (illustrative only), a negotiated vendor extension
`com.example.payment.authentication` declares two Action types:
`com.example.payment.authentication.device_data_collection`, an invisible
device- and browser-data collection step, and
`com.example.payment.authentication.three_ds_challenge`, a Buyer-facing
authentication step. Because the collection step precedes the challenge, the
Business can emit the `device_data_collection` type first and, once its instance
is processed, emit the `three_ds_challenge` type in a later response. This shows
one extension declaring multiple Action types and sequencing them across
responses; it does not standardize device data collection or the authentication
challenge, which are illustrative here.

Every instance shares a set of common fields:

- `id` — a non-empty identifier for the Action instance.
- `config` — an optional extension-owned configuration object.

`id` is required on every instance; `config` is optional. An extension defines
the instance-specific data a Platform needs to process its work under `config`;
`config` is the extension-owned channel for that data.

An Action instance also remains open to additional top-level fields for forward
compatibility. A Platform **MUST** tolerate and ignore Action instance
fields it does not recognize.

The Business **MUST** use a distinct `id` for each Action instance in a response.

When successive responses represent the same parent resource, the Business
**MUST** keep the same Action type key and `id` while the same work remains
outstanding. Replacement work **MUST** have a new `id`, and the Business
**MUST NOT** reuse an `id` during that resource's lifetime.

Otherwise, the common Actions contract defines no identity relationship between
Actions in independent responses. Equal `id` values alone do not identify the
same work.

A Business **MUST** emit an Action type only when an extension that declares it
is active for the containing capability in the negotiated intersection. The
composed JSON Schema can validate the common fields and each declared type's key
and `config` shape, but confirming that the declaring extension is active also
requires the negotiated capability context.

### Trust and Execution Boundaries

Negotiating an extension confirms support for its complete Action-type contract
before runtime. That agreement does not make every future runtime value or
delegate trusted. Each instance remains subject to the composed schema, the
Action-type contract, and Platform policy.

The active Action-type contract defines which `config` fields a Platform processes
and what they mean. A Platform **MUST NOT** treat any other field as an
instruction to load content, render HTML, execute code, run a shell command, or
invoke a native API.

A Platform **MAY** apply additional trust or runtime policy and **MAY** decline
any instance that does not satisfy it. Supporting a whole extension does not
require a Platform to accept every runtime value.

A Platform **MUST NOT** assume that the effect gated by an Action succeeded
merely because an Action surface or external interaction completed. A later
response from the Business, together with any parent lifecycle its capability
defines, remains authoritative for that outcome.

The declaring extension defines the concrete trust, execution, and fallback rules.
The common Actions contract defines no generic machinery: no URL scheme, origin,
or delegate policy; no sandbox, permission, or presentation model; no timeout,
failure, or recovery model; and no callback, result, state, polling, or
executor. Each concrete Action type adds only the machinery its own processing
requires.

## Discovery, Governance, and Negotiation

UCP separates [protocol version selection](#protocol-version) from
[capability negotiation](#capability-versions). A Business advertises its current
protocol version and links to profiles for older supported versions. After the
Platform selects one exact version, the Business determines the active
capabilities from the versions both parties advertise. Version lifecycle,
including when to remove an older version, is a Business policy decision; UCP
does not prescribe a deprecation schedule. Business and Platform profiles can be
cached by both parties.

### Namespace Governance

UCP uses reverse-domain naming to encode governance authority directly into
capability identifiers. This eliminates the need for a central registry.

#### Naming Convention

All capability and service names **MUST** use the format:

```text
{reverse-domain}.{service}.{capability}
```

**Components:**

- `{reverse-domain}` - Authority identifier derived from domain ownership
- `{service}` - Service/vertical category (e.g., `shopping`, `common`)
- `{capability}` - The specific capability name

**Examples:**

| Name                                | Authority   | Service  | Capability       |
| ----------------------------------- | ----------- | -------- | ---------------- |
| `dev.ucp.shopping.checkout`         | ucp.dev     | shopping | checkout         |
| `dev.ucp.shopping.fulfillment`      | ucp.dev     | shopping | fulfillment      |
| `dev.ucp.common.identity_linking`   | ucp.dev     | common   | identity_linking |
| `com.example.payments.installments` | example.com | payments | installments     |

#### Authority Binding

Reverse-domain names serve two purposes: collision-safe **identifiers** (keys
and references), and **entities** — capabilities, services, and payment
handlers — that declare a fetched `schema` URL describing them. Authority
binding applies to every entity with a remote `schema`: a declared `schema`
URL's origin **MUST** match the namespace authority in its name.

A capability **MUST** declare a `schema`; services and payment handlers declare
one where their transport or handler defines it. Each entity **MAY** also
declare a `spec` URL (human-readable documentation).

This binding guarantees **provenance, not trust**: a valid binding proves only
that the reverse-domain name is controlled by the party that owns the
corresponding domain — an entity cannot be published under a namespace its
author does not control. It does **not** assert that the entity is trustworthy,
correct, or worth supporting. Whether to negotiate, trust, or implement it is
always the client's decision; this binding only tells the client *who* is making
the claim. Provenance is established from domain ownership and evaluated at
negotiation time.

The `spec` URL is documentation, not part of the machine trust path, so its
origin is **not** authority-bound: it **MUST** be `https` but **MAY** be served
from any host (e.g. a docs subdomain or third-party docs host). Only the
`schema` URL carries the authority binding defined below.

##### Derivation algorithm

The authority is derived **from the `schema` URL host** — which names the
owning domain directly, with no ambiguity about where the domain ends — and
validated as a label-aligned prefix of, or an exact match for, the entity's
name. For the `schema` URL of an entity whose name is `name`, a platform
**MUST** apply the following:

1. Parse the URL with a conformant (WHATWG) URL parser. It **MUST** parse,
   **MUST** use the `https` scheme, and **MUST NOT** contain userinfo (a
   `user:pass@` component). Substring matching on the raw URL is **NOT**
   permitted — e.g. `https://ucp.dev@evil.example/x.json` has host
   `evil.example`, not `ucp.dev`.
2. The host **MUST** be a registered domain name of at least two labels.
   IP-literal hosts (`https://203.0.113.10/...`) and single-label hosts
   (`https://localhost/...`) are invalid authorities.
3. Take the URL's hostname (the host without any port), normalize it (lowercase;
   strip a trailing `.`; internationalized domains in A-label / punycode form),
   and **reverse its labels** to form the `authority_prefix` (host `ucp.dev` →
   `dev.ucp`).
4. The binding is valid if and only if **either** of the following holds:
   - **Exact match** — `name` equals `authority_prefix`. The name is itself the
     reversed host, so the publisher demonstrably controls the entire namespace.
     This is the shape for an entity whose identity is a bare controlled domain,
     such as a payment handler `com.example.pay` served from `pay.example.com`
     (reversed host `com.example.pay` equals the name).
   - **Prefixed** — `name` is `authority_prefix`, then a `.`, then one or more
     further labels; that is, the character immediately after `authority_prefix`
     in `name` is a `.`. Requiring that separating `.` keeps the match on a
     label boundary — it stops `com.example` (host `example.com`) from matching
     a neighboring namespace like `com.examplecorp.*`, where `com.example` is a
     textual prefix but not a label-aligned one.

Authority binding establishes **provenance only** — that the name is controlled
by the party serving its `schema`. It does **not** require any label beyond the
authority itself. The `{reverse-domain}.{service}.{capability}` shape is a
separate [Naming Convention](#naming-convention) that governs capability and
service names — it does not apply to payment handlers — and is validated
independently of this check.

Any labels after the authority prefix are treated as opaque by this check; they
are not inspected or split.

| Entity name                         | `schema` host      | `authority_prefix` | Result              |
| ----------------------------------- | ------------------ | ------------------ | ------------------- |
| `dev.ucp.shopping.checkout`         | `ucp.dev`          | `dev.ucp`          | **accept** (prefix) |
| `dev.ucp.shopping.checkout`         | `shopping.ucp.dev` | `dev.ucp.shopping` | **accept** (prefix) |
| `com.example.payments.installments` | `example.com`      | `com.example`      | **accept** (prefix) |
| `com.example.pay`                   | `pay.example.com`  | `com.example.pay`  | **accept** (exact)  |
| `com.example.pay`                   | `example.com`      | `com.example`      | **accept** (prefix) |
| `com.example.pay`                   | `evil.example`     | `example.evil`     | **reject**          |
| `dev.ucp.shopping.checkout`         | `evil.example`     | `example.evil`     | **reject**          |
| `com.examplecorp.pay`               | `example.com`      | `com.example`      | **reject**          |
| `com.example.pay`                   | `cdn.example.com`  | `com.example.cdn`  | **reject**          |

An entity's `schema` is served from a host whose reversed labels either **equal**
its name or are a **label-aligned prefix** of it. A host whose reversed labels
are exactly the name (`pay.example.com` for `com.example.pay`) satisfies the
exact case; a canonical apex host (`example.com` for `com.example.*`) satisfies
the prefix case; a subdomain satisfies the prefix case only when its labels line
up with the namespace path (`shopping.ucp.dev` for `dev.ucp.shopping.*`). Because
a parent domain's reversed labels are also a prefix, a name such as
`com.example.pay` binds equally from its exact host (`pay.example.com`) or a
parent authority (`example.com`) — both prove control. Unrelated subdomains such
as a shared CDN do **not** satisfy any case — host the canonical schema on a
name-aligned origin.

The check uses the `schema` URL host directly and does not consult the
[Public Suffix List](https://publicsuffix.org/), so it treats a **public
suffix** — a domain under which independent parties can register names, from
`co.uk` to the list's private-section suffixes operated by services that let
third parties register subdomains or buckets (`github.io`, object storage, app
platforms) — as an ordinary authority. Co-tenants under such a suffix satisfy
the same prefix, so declare entities only under a **registrable domain** (a
public suffix plus one label) that you exclusively control.

##### Enforcement

A platform **MUST** validate each business-declared `schema` URL before fetching
it. If the URL's origin does not match the entity's namespace authority (per
[Derivation algorithm](#derivation-algorithm)), the platform **MUST NOT** fetch
it and **MUST** reject the entity — treated as not present and never
activated. A `spec` URL **MUST** be a valid `https` URL. A platform **MUST NOT** follow redirects (`3xx`) when fetching a `schema` URL, consistent with profile fetches.

The platform fetches and composes business-declared schemas to validate every
request and response, so validating the binding ensures each composed schema is
sourced from the party that owns the entity's namespace. A business **SHOULD**
apply the same check to the platform profile and exclude any entity whose
binding fails.

Binding validates the declared hostname for provenance; it is **not** a
fetch-safety control and does not authorize dereferencing. Fetching the `schema`
URL — like any URL fetched during discovery — is additionally subject to the
protocol's URL fetch-safety requirements, which guard the *resolved* address
(not just the hostname) against server-side request forgery toward special-use
or cloud-metadata addresses and DNS rebinding. The hostname check and the
resolved-address check are independent, and both apply.

#### Governance Model

| Namespace Pattern | Authority    | Governance          |
| ----------------- | ------------ | ------------------- |
| `dev.ucp.*`       | ucp.dev      | UCP governing body  |
| `com.{vendor}.*`  | {vendor}.com | Vendor organization |
| `org.{org}.*`     | {org}.org    | Organization        |

The `dev.ucp.*` namespace is reserved for capabilities sanctioned by the UCP
governing body. Vendors **MUST** use their own reverse-domain namespace for
custom capabilities.

### Services

A **service** defines the API surface for a vertical (shopping, common, etc.).
Services include operations, events, and transport bindings defined via
standard formats:

- **REST**: OpenAPI 3.x (JSON format)
- **MCP**: OpenRPC (JSON format)
- **A2A**: Agent Card Specification
- **EP(embedded)**: OpenRPC (JSON format)

A service is identified by its reverse-domain registry key (e.g.,
`dev.ucp.shopping`). In a profile, services are keyed by that name, and each
entry in `services[name][]` pairs the service with one transport binding and
declares the service `version`: in release `D` that version is `D`. This is the
service version, not a transport version — the binding has no separate version.
The OpenAPI or OpenRPC artifact a binding references carries its own
`info.version` as release metadata, not a separate version to negotiate. See
[Component Versioning and Release Snapshots](#component-versioning-and-release-snapshots).

#### Service Definition

{{ extension_schema_fields('service.json#/$defs/platform_schema', 'overview') }}

Transport definitions **MUST** be thin: they declare method names and reference
base schemas only. See [Requirements](#requirements) for details.

#### Endpoint Resolution

The `endpoint` field provides the base URL for API calls. OpenAPI paths are
appended to this endpoint to form the complete URL.

**Example:**

<!-- ucp:example schema=service def=business_schema -->
```json
{
  "version": "{{ ucp_version }}",
  "transport": "rest",
  "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/rest.openapi.json",
  "endpoint": "https://business.example.com/api/v2"
}
```

With OpenAPI path `/checkout-sessions`, the resolved URL is:

```text
POST https://business.example.com/api/v2/checkout-sessions
```

**Rules:**

- `endpoint` **MUST** be a valid URL with scheme (https)
- `endpoint` **SHOULD NOT** have a trailing slash
- OpenAPI paths are relative and appended directly to endpoint
- Same resolution applies to MCP endpoints for JSON-RPC calls
- `endpoint` for A2A transport refers to the Agent Card URL for the agent

### Capabilities

A **capability** is a feature within a service. It declares what
functionality is supported and where to find documentation and schemas.

#### Capability Definition

{{ extension_schema_fields('capability.json#/$defs/platform_schema', 'capability-schema') }}

#### Extensions

An **extension** is an optional module that augments another capability.
Extensions use the `extends` field to declare their parent(s):

<!-- ucp:example schema=profile def=business_schema target=$.ucp.capabilities -->
```json
{
  "dev.ucp.shopping.fulfillment": [
    {
      "version": "{{ ucp_version }}",
      "spec": "https://ucp.dev/{{ ucp_version }}/specification/fulfillment",
      "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/fulfillment.json",
      "extends": "dev.ucp.shopping.checkout"
    }
  ]
}
```

##### Multi-Parent Extensions

Extensions **MAY** extend multiple parent capabilities by using an array:

<!-- ucp:example schema=profile def=business_schema target=$.ucp.capabilities -->
```json
{
  "dev.ucp.shopping.discount": [
    {
      "version": "{{ ucp_version }}",
      "spec": "https://ucp.dev/{{ ucp_version }}/specification/discount",
      "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/discount.json",
      "extends": ["dev.ucp.shopping.checkout", "dev.ucp.shopping.cart"]
    }
  ]
}
```

When an extension declares multiple parents:

- The extension **MAY** define different fields for each capability it extends
    (e.g., `loyalty_earned` for checkout, `loyalty_preview` for cart)
- See [Intersection Algorithm](#intersection-algorithm) for negotiation rules

Extensions can be:

- **Official**: `dev.ucp.shopping.fulfillment` extends `dev.ucp.shopping.checkout`
- **Vendor**: `com.example.installments` extends `dev.ucp.shopping.checkout`

### Schema Composition

Extensions can add new fields and modify shared structures (e.g., discounts
modify `totals`, fulfillment adds fulfillment to `totals.type`).

#### Requirements

- Transport definitions (OpenAPI/OpenRPC) **MUST** reference base schemas
    only. They **MUST NOT** enumerate fields or define payload shapes inline.
- Extensions **MUST** be self-describing. Each extension schema **MUST**
    declare the types it introduces and how it modifies base types using `allOf`
    composition.
- Platforms **MUST** resolve schemas client-side by fetching and composing
    base schemas with active extension schemas.

#### Extension Schema Pattern

Extension schemas define composed types using `allOf`. The `$defs` key **MUST**
use the full parent capability name (reverse-domain format) to enable
deterministic schema resolution:

<!-- ucp:example skip reason="schema definition" -->
```json
{
  "$defs": {
    "discounts_object": { ... },
    "dev.ucp.shopping.checkout": {
      "title": "Checkout with Discount",
      "allOf": [
        {"$ref": "checkout.json"},
        {
          "type": "object",
          "properties": {
            "discounts": {
              "$ref": "#/$defs/discounts_object"
            }
          }
        }
      ]
    }
  }
}
```

**Requirements:**

- Extension schemas **MUST** have a `$defs` entry for each parent declared in
    `extends`
- The `$defs` key **MUST** match the parent's full capability name exactly

This convention ensures:

- **Self-documenting**: The schema declares exactly which parents it extends
- **Deterministic resolution**: The `extends` value maps directly to the `$defs` key
- **Verifiable**: Build-time checks can confirm each `extends` entry has a
    matching `$defs` key

##### Version Requirements

Extension authors **SHOULD** declare a `requires` object in the extension
schema (alongside its `name`, `title`, and `description`) stating the versions
the extension depends on. A third-party extension schema declares its own
author-controlled `version`, which advances independently of `ucp.version`;
a UCP-authored `dev.ucp.*` extension declares version `D` in release `D`.
`requires.protocol` constrains the selected `ucp.version`, and
`requires.capabilities` constrains the selected versions of the named
capabilities:

<!-- ucp:example skip reason="schema definition" -->
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://acme.com/ucp/schemas/loyalty.json",
  "name": "com.acme.shopping.loyalty",
  "version": "2026-06-15",
  "title": "Acme Loyalty Points",
  "requires": {
    "protocol": { "min": "2026-01-23" },
    "capabilities": {
      "dev.ucp.shopping.checkout": { "min": "2026-06-01" }
    }
  },
  "$defs": {
    "dev.ucp.shopping.checkout": { ... }
  }
}
```

The schema author — not the profile publisher — declares version
requirements. The profile publisher selects and advertises compatible
versions in their profile.

Each constraint is an object with a required `min` (inclusive) and
optional `max` (inclusive) version. When `max` is absent, there is
no upper bound:

<!-- ucp:example skip reason="schema definition" -->
```json
"requires": {
  "protocol": { "min": "2026-01-23", "max": "2026-09-01" },
  "capabilities": {
    "dev.ucp.shopping.checkout": { "min": "2026-06-01" }
  }
}
```

Keys in `requires.capabilities` **MUST** be a subset of the
extension's `$defs` keys. These ranges verify dependencies after exact
versions are selected; they do not select versions. The `ucp.version` is
fixed first by [profile selection](#protocol-version) and capability versions
by the [intersection algorithm](#intersection-algorithm); then, if `requires`
is present, Platforms and Businesses **MUST** verify that the selected
`ucp.version` and capability versions satisfy the declared constraints during
schema resolution. Incompatible extensions are excluded from the active
capability set (see [Resolution Flow](#resolution-flow)). If `requires` is
absent, the extension is assumed to be compatible with the versions declared
by the profile.

#### Schema Resolution Convention

To validate payloads, implementations resolve extension schemas as follows:

1. Determine the root capability from the operation (e.g., checkout operations
    use `dev.ucp.shopping.checkout`)
2. For each active extension, resolve and apply its `$defs[{root_capability}]`

**Example:** A checkout response includes the discount extension.

- Root capability: `dev.ucp.shopping.checkout`
- Extension schema: `discount.json`
- Resolve: `discount.json#/$defs/dev.ucp.shopping.checkout`

#### Resolution Flow

Platforms **MUST** resolve schemas following this sequence:

1. **Discovery**: Fetch business profile from `/.well-known/ucp`
2. **Negotiation**: Compute capability intersection (see
    [Intersection Algorithm](#intersection-algorithm))
3. **Schema Fetch**: Fetch base schema and all active extension schemas
4. **Version Compatibility**: For each fetched extension schema,
    if `requires` is present, verify the negotiated protocol version
    and capability versions satisfy the declared constraints. Exclude
    incompatible extensions and re-prune orphaned extensions
    (steps 3-4 of the [Intersection Algorithm](#intersection-algorithm))
5. **Compose**: Merge schemas via `allOf` chains based on active extensions
6. **Validate**: Validate requests and responses against the composed schema

### Profile Structure

Profile documents are machine-readable discovery documents. Businesses publish
their profile at `/.well-known/ucp`; platforms publish their profile at the URI
advertised in `UCP-Agent`.

A profile document is a JSON object with a required `ucp` member. The `ucp`
member contains protocol metadata: protocol version, services, optional
capabilities, and payment handlers.

For both business and platform profiles, `ucp.version`, `ucp.services`, and
`ucp.payment_handlers` are required. The `services` and `payment_handlers`
registries **MUST** be present even when empty. `ucp.capabilities` is optional
and **MAY** be omitted, though useful commerce profiles normally advertise at
least one capability.

Profiles **MAY** include public JSON Web Keys used for HTTP Message
Signatures and signed webhooks. When a profile publishes signing keys,
they **MUST** appear in the top-level `keys[]` array — the canonical
UCP profile field that every UCP verifier reads. `keys[]` is a JWK Set
per [RFC 7517](https://datatracker.ietf.org/doc/html/rfc7517), so the
same document is simultaneously a UCP profile and a valid JWK Set —
which a signer can reuse as its Web Bot Auth key source. See
[Deployment Patterns for WBA Interop](#deployment-patterns-for-wba-interop)
below.

Adding, rotating, or removing a key updates this single array. Removal
is the security-critical case: a revoked or compromised key is not
effectively revoked until it is absent from `keys[]`.

UCP defines two well-known key types: **EC** (ECDSA P-256, P-384) and
**OKP** (EdDSA Ed25519); the key-type, curve, and algorithm
vocabularies are open and verifiers skip keys they do not recognize.
See [Message Signatures](signatures.md) for key format, algorithms,
lookup, and rotation.

#### Business Profile

Businesses publish their profile at `/.well-known/ucp`. An example:

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "rest",
          "endpoint": "https://business.example.com/ucp/v1",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/rest.openapi.json"
        },
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "mcp",
          "endpoint": "https://business.example.com/ucp/mcp",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/mcp.openrpc.json"
        },
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "a2a",
          "endpoint": "https://business.example.com/.well-known/agent-card.json"
        },
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "embedded",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/embedded.openrpc.json"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/checkout",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.shopping.fulfillment": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/fulfillment",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/fulfillment.json",
          "extends": "dev.ucp.shopping.checkout"
        }
      ],
      "dev.ucp.shopping.discount": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/discount",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/discount.json",
          "extends": "dev.ucp.shopping.checkout"
        }
      ],
      "dev.ucp.common.identity_linking": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/identity-linking",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/identity_linking.json",
          "config": {
            "providers": {
              "com.example.idp": [
                { "type": "oauth2", "auth_url": "https://accounts.example.com/" }
              ]
            },
            "scopes": {
              "dev.ucp.shopping.order:read":   {},
              "dev.ucp.shopping.order:manage": {}
            }
          }
        }
      ]
    },
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {
          "id": "processor_tokenizer",
          "version": "{{ ucp_version }}",
          "spec": "https://example.com/specs/payments/processor_tokenizer",
          "schema": "https://example.com/specs/payments/merchant_tokenizer.json",
          "available_instruments": [
            {
              "type": "card",
              "constraints": {
                "brands": ["visa", "mastercard", "amex"]
              }
            }
          ],
          "config": {
            "type": "CARD",
            "tokenization_specification": {
              "type": "PUSH",
              "parameters": {
                "token_retrieval_url": "https://api.psp.example.com/v1/tokens"
              }
            }
          }
        }
      ]
    }
  },
  "keys": [
    {
      "kid": "poqkLGiymh_W0uP6PZFw-dvez3QJT5SolqXBCW38r0U",
      "kty": "OKP",
      "crv": "Ed25519",
      "x": "JrQLj5P_89iXES9-vFgrIy29clF9CC_oPPsw3c5D0bs",
      "use": "sig",
      "alg": "EdDSA"
    },
    {
      "kid": "business_2025",
      "kty": "EC",
      "crv": "P-256",
      "x": "qIVYZVLCrPZHGHjP17CTW0_-D9Lfw0EkjqF7xB4FivA",
      "y": "Mc4nN9LTDOBhfoUeg8Ye9WedFRhnZXZJA12Qp0zZ6F0",
      "use": "sig",
      "alg": "ES256"
    }
  ]
}
```

The business profile advertises the business's available transports,
capabilities, payment handlers, and public verification keys. This
example publishes signing keys in the canonical top-level `keys[]`
array (an RFC 7517 JWK Set), so the same document is also a valid JWK
Set — reusable as a Web Bot Auth key source. Every UCP verifier reads
`keys[]`, whether it resolved the key via `UCP-Agent` or via
`Signature-Agent`.

A WBA-shape verifier reads `keys[]` from this profile **only when the
`Signature-Agent` header selects it** with `type=jwks_uri` (or `type=cimd`)
pointing at the profile URL. The default `type=directory` (when `type` is
omitted) instead expects a *signed* directory document at
`/.well-known/http-message-signatures-directory`, not a static profile, so
it will not read `keys[]` from a static `/.well-known/ucp`. See
[Deployment Patterns for WBA Interop](#deployment-patterns-for-wba-interop).

This example uses two keys. Whether a deployment needs one or two depends
on the algorithms its counterparties accept — many need only one; see
[Signature Algorithms](signatures.md#signature-algorithms). The two keys
here:

- An **Ed25519** key (OKP) for HTTP transport identity, WBA-compatible.
  The `kid` is the JWK SHA-256 Thumbprint per RFC 7638.
- An **ECDSA P-256** key (EC) for AP2 mandate signing
  (`ap2.merchant_authorization`).

A business that does not interact with AP2 or WBA may publish a single
ES256 key in `keys[]` (the universal baseline). See
[Key Discovery](#key-discovery) for key lookup and resolution,
[Deployment Patterns for WBA Interop](#deployment-patterns-for-wba-interop)
for hosting choices, and [Message Signatures](signatures.md) for
signing mechanics.

Businesses that support older protocol versions **SHOULD** include a
`supported_versions` object mapping each older version to a
version-specific profile URI. See [Protocol Version](#protocol-version)
for details.

#### Platform Profile

Platform profiles are similar and include signing keys for capabilities
requiring cryptographic verification. Capabilities **MAY** include a `config`
object for capability-specific settings (e.g., callback URLs, feature flags). An
example:

<!-- ucp:example schema=profile def=platform_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/rest.openapi.json",
          "endpoint": "https://platform.example.com/ucp/v1"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/checkout",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.shopping.fulfillment": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/fulfillment",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/fulfillment.json",
          "extends": "dev.ucp.shopping.checkout"
        }
      ],
      "dev.ucp.shopping.order": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/order",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/order.json",
          "config": {
            "webhook_url": "https://platform.example.com/webhooks/ucp/orders"
          }
        }
      ],
      "dev.ucp.common.identity_linking": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/identity-linking",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/identity_linking.json"
        }
      ]
    },
    "payment_handlers": {
      "com.google.pay": [
        {
          "id": "gpay_1234",
          "version": "2024-12-03",
          "spec": "https://developers.google.com/merchant/ucp/guides/gpay-payment-handler",
          "schema": "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/gpay_config.json"
        }
      ],
      "dev.shopify.shop_pay": [
        {
          "id": "shop_pay_1234",
          "version": "{{ ucp_version }}",
          "spec": "https://shopify.dev/ucp/shop-pay-handler",
          "schema": "https://shopify.dev/ucp/schemas/shop-pay-config.json",
          "available_instruments": [
            {"type": "shop_pay"}
          ]
        }
      ],
      "com.example.processor_tokenizer": [
        {
          "id": "processor_tokenizer",
          "version": "{{ ucp_version }}",
          "spec": "https://example.com/specs/payments/processor_tokenizer-payment",
          "schema": "https://example.com/schemas/payments/delegate-payment.json",
          "available_instruments": [
            {"type": "card", "constraints": {"brands": ["visa", "mastercard"]}}
          ]
        }
      ]
    }
  },
  "keys": [
    {
      "kid": "platform_2025",
      "kty": "EC",
      "crv": "P-256",
      "x": "MKBCTNIcKUSDii11ySs3526iDZ8AiTo7Tu6KPAqv7D4",
      "y": "4Etl6SRW2YiLUrN5vfvVHuhp7x8PxltmWWlbbM4IFyM",
      "use": "sig",
      "alg": "ES256"
    }
  ]
}
```

### The `ucp` Protocol Namespace

The member name `ucp` is reserved as the **protocol namespace** in every
structured UCP object scope — an object whose members are schema-defined
fields. The top-level `ucp` member that profiles and responses carry —
described in [Profile Structure](#profile-structure) above — is not a special
wrapper; it is the root manifestation of this reservation: a reserved member
of the root object. The reservation does not apply to a dictionary container,
whose keys are data rather than fields. A dictionary key named `ucp` is
ordinary data. A structured object used as a dictionary value remains an
eligible scope. Schema authors **MUST NOT** define a domain field named `ucp`
in structured object schemas or extensions.

At each eligible structured scope, `ucp` carries the protocol's statements
about that scope: protocol metadata at the root (version, services,
capabilities, payment handlers) and structural annotations such as
[`map_order`](#map_order).

**Openness.** The `ucp` container is open. Consumers **MUST** ignore members
inside `ucp` that they do not recognize (tolerant reader). Openness exists so
documents produced under a newer UCP version remain readable by older
consumers — it is *not* extension space. Only UCP core defines members inside
`ucp`, and extension authors **MUST NOT** place extension data there. An
unrecognized member inside `ucp` means "defined by a newer UCP version,"
never "extension data."

**No direct recursion.** Producers **MUST NOT** emit a `ucp` member as a direct
child of another `ucp` member (`ucp.ucp`). If one is present, a receiving
Business or Platform **MUST NOT** interpret it as another protocol namespace and
**MUST** ignore that child. Structured objects beneath the namespace, such as a
capability's `config`, remain eligible for their own `ucp` member.

**Ambient vocabulary.** The protocol namespace is ambient within structured
UCP objects: a Business or Platform **MAY** include a `ucp` member at any
eligible structured scope, and its contents are defined exclusively by UCP
core's vocabulary — the member is part of the UCP document grammar, like the
name reservation itself. The reservation stops at a dictionary container. A
Business or Platform **MUST NOT** interpret a dictionary key named `ucp` as
the protocol namespace; the key and its value are ordinary dictionary data.
For example, `attribution` is a dictionary of string values, so an attribution
key named `ucp` is ordinary attribution data, not a protocol-namespace member.
Guidance for schema authors on working within this reservation lives in the
Schema Authoring Guide's
[The Reserved `ucp` Member](/documentation/schema-authoring/#the-reserved-ucp-member)
section. A Business or Platform encountering a `ucp` member at an eligible
structured scope processes the members it recognizes, each per its own
definition, and **MUST** ignore unrecognized members (see *Openness* above).
A member is admitted to the vocabulary only if it is safe to ignore: a
Business or Platform that does not process it loses only that member's
benefit, never correctness. A Business or Platform that ignores `map_order`,
for example, simply traverses the map unordered — the status quo before
ordering existed.

**Scope determines obligations.** At the root of profiles and responses, the
`ucp` envelope additionally carries the required protocol metadata exactly as
specified elsewhere in this document — this section changes none of those
obligations. A Business or Platform **MAY** omit the member at every other
eligible structured scope. Dictionary containers are not eligible scopes and
carry no protocol-namespace obligation. Conformance to the vocabulary is
defined by this specification's processing rules, not by ordinary instance
validation against open UCP source schemas; that validation treats ambient
`ucp` members as ignored unknown objects.

**Vocabulary applicability.** Each registered protocol-namespace member defines
the document contexts and message directions where it applies.

**Schema processing.** UCP source schemas are open by default, so ordinary
validation against them may accept ambient `ucp` without applying the protocol
vocabulary. For a selected message direction, a UCP-aware resolver **MUST**
produce a resolved schema that recognizes and validates ambient `ucp` at every
eligible structured scope against the central vocabulary in
`ucp.json#/$defs/members`, subject to that vocabulary's applicability in the
selected direction. The `ucp` namespace remains open to unrecognized members
for forward compatibility, even if the resolved schema rejects other unknown
domain fields. The result is ordinary JSON Schema that standard validators and
code generators can consume.

#### `map_order`

JSON object members are unordered: member order is not guaranteed to survive
parsing, and
[RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html){ target="_blank" }
(JSON Canonicalization Scheme), which UCP signing relies on, sorts object
member names while preserving array element order. `map_order` uses an array
so its declared order survives canonicalization and signing.

`map_order` declares a preferred key-traversal order for map-valued fields in
the scope annotated by its containing `ucp` member. At a nested scope, each
key of `map_order` names a map field on the object that contains `ucp`. At the
document root, each key instead names a sibling map field inside the root `ucp`
envelope. Root domain fields outside `ucp`, such as a checkout response's
`actions`, are not targets. Each value is an array of the target map's keys in
preferred traversal order.

`map_order` does not apply to UCP operation requests.

For a target map field `<field>` and its companion array `map_order.<field>`:

1. Producers **MUST NOT** rely on JSON object member order for UCP map-valued
    registries; `map_order` is the order carrier.
2. `map_order.<field>` contains keys from the target map field `<field>` in
    preferred traversal order.
3. The order array **MAY** be partial: listed keys are traversed first, in
    array order.
4. Unlisted map keys remain valid and available; consumers traverse them
    after the listed keys, using the field-defined fallback order or, if the
    field defines none, the
    [property-name ordering defined by RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html#section-3.2.3){ target="_blank" }.
5. The order array is not an allowlist: consumers **MUST NOT** interpret
    omission of a key as removal, ineligibility, or reduced support.
6. Producers **MUST** name a present, map-valued target and **MUST** list only
    keys present in that target map. A receiving Business
    or Platform **MUST NOT** reject the containing document solely because an
    entry names an absent, unrecognized, or non-map target, or a key absent from
    its target map. If it processes `map_order`, it **MUST** ignore the unusable
    entry.
7. Producers **MUST NOT** list the same map key more than once in an order
    array. Consumers **MUST NOT** reject the containing document solely because
    an order array repeats a map key. Consumers that process `map_order`
    **MUST** honor the first occurrence and ignore later repetitions.
8. If `map_order`, or its entry for a field, is absent, no order is declared;
    consumers **MUST NOT** fall back to object member order.
9. A field's own specification defines what ordered traversal *means* for it
    (presentation, negotiation priority, and so on) — `map_order` carries
    order and nothing else.

Rules 3–5 are a deliberate divergence from conventions in which unlisted keys
are an error or are dropped: partial lists are always valid, and unlisted
keys are always retained.

A business profile ordering its payment handlers:

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": { ... },
    "payment_handlers": {
      "com.google.pay": [
        { "id": "gpay", "version": "{{ ucp_version }}" }
      ],
      "dev.shopify.shop_pay": [
        { "id": "shop_pay", "version": "{{ ucp_version }}" }
      ]
    },
    "map_order": {
      "payment_handlers": ["dev.shopify.shop_pay", "com.google.pay"]
    }
  }
}
```

`map_order` is scope-generic — the same mechanism orders sibling maps at any
eligible structured scope, as when a Business orders the identity-provider
registry inside a capability's `config`:

<!-- ucp:example skip reason="illustrative fragment" -->
```json
{
  "providers": {
    "app.example.login": [
      {"type": "oauth2", "auth_url": "https://login.example.app"}
    ],
    "com.google": [
      {"type": "oauth2", "auth_url": "https://accounts.google.com"}
    ]
  },
  "ucp": {
    "map_order": {"providers": ["app.example.login", "com.google"]}
  }
}
```

What an order *means* remains per-field (rule 9); the one traversal semantics
defined today is the business's presentation preference for
`payment_handlers` — see [Payment Handlers](#payment-handlers).

### Platform Advertisement on Request

Platforms **MUST** communicate their profile URI with each request to enable
capability negotiation.

**HTTP Transport:** Platforms **MUST** use Dictionary Structured Field syntax
([RFC 8941](https://datatracker.ietf.org/doc/html/rfc8941){ target="_blank" })
in the UCP-Agent header:

```text
POST /checkout HTTP/1.1
UCP-Agent: profile="https://agent.example/profiles/shopping-agent.json"
Content-Type: application/json

{"line_items": [...]}
```

**MCP Transport:** Platforms **MUST** include a `meta` object containing request
metadata:

<!-- ucp:example schema=shopping/checkout op=create direction=request extract=$.params.arguments.checkout -->
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "create_checkout",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://agent.example/profiles/shopping-agent.json"
        }
      },
      "checkout": {
        "line_items": [...]
      }
    }
  },
  "id": 1
}
```

### Negotiation Protocol

#### Platform Requirements

1. **Profile Advertisement**: Platforms **MUST** include their profile URI in
    every request using the transport-appropriate mechanism.
2. **Discovery**: Platforms **MAY** fetch the business profile from
    `/.well-known/ucp` before initiating requests. If fetched, platforms
    **SHOULD** cache the profile according to HTTP cache-control directives.
3. **Namespace Validation**: Before fetching, platforms **MUST** validate that
    each capability's `schema` URL origin matches its namespace authority (see
    [Authority Binding](#authority-binding)) and **MUST** reject capabilities
    that fail this binding.
4. **Schema Resolution**: Platforms **MUST** fetch and compose schemas for
    negotiated capabilities before making requests.

#### Business Requirements

1. **Profile Resolution**: Upon receiving a request with a platform profile
    URI, businesses **MUST** fetch and validate the platform profile unless
    already cached. Because businesses negotiate by capability name and serve
    their own schemas, they do not normally dereference platform-declared
    `schema` URLs; they **SHOULD** nonetheless verify the namespace binding (see
    [Authority Binding](#authority-binding)) as defense in depth.
2. **Capability Intersection**: Businesses **MUST** compute the intersection of
    platform and business capabilities.
3. **Extension Validation**: Extensions without their parent capability in the
    intersection **MUST** be excluded.
4. **Response Requirements**: Businesses **MUST** include the `ucp` field in
    every response containing:
    - `version`: The UCP version used to process the request
    - `capabilities`: Array of active capabilities for this response

#### Intersection Algorithm

The capability intersection algorithm determines which capabilities are active
for a session:

1. **Compute intersection**: For each business capability, include it in the
    result if a platform capability with the same `name` exists.

2. **Select version**: For each capability in the intersection, compute the
    set of version strings present in **both** the business and platform
    arrays. If the set is non-empty, select the **highest** version
    (latest date). If the set is empty (no mutual version), **exclude** the
    capability from the intersection.

3. **Prune orphaned extensions**: Remove any capability where `extends` is
    set but **none** of its parent capabilities are in the intersection.
    - For single-parent extensions (`extends: "string"`): parent must be present
    - For multi-parent extensions (`extends: ["a", "b"]`): at least one parent
        must be present

4. **Repeat pruning**: Continue step 3 until no more capabilities are removed
    (handles transitive extension chains).

The result is the set of capabilities both parties support at mutually
compatible versions, with extension dependencies satisfied.

#### Error Handling

UCP negotiation can fail in two ways:

1. **Discovery failure**: The business cannot fetch or parse the platform's
   profile.

2. **Negotiation failure**: The provided profile is valid but capability
   intersection is empty or versions are incompatible.

Discovery failures are transport errors — the required inputs could
not be retrieved or were malformed. Negotiation failures are business
outcomes — the handler executed on the provided inputs and reported
the result in the UCP response:

- **Discovery or version failure** → transport error with optional `continue_url`
- **Capability negotiation failure** → UCP response with optional `continue_url`

##### Error Codes

**Negotiation Errors:**

| Code                        | Description                                          | REST | MCP    |
| --------------------------- | ---------------------------------------------------- | ---- | ------ |
| `invalid_profile_url`       | Profile URL is malformed, missing, or unresolvable   | 400  | -32001 |
| `profile_unreachable`       | Resolved URL but fetch failed (timeout, non-2xx)     | 424  | -32001 |
| `profile_malformed`         | Fetched content is not valid JSON or violates schema | 422  | -32001 |
| `version_unsupported`       | Platform's protocol version not supported            | 422  | -32001 |
| `capabilities_incompatible` | No compatible capabilities in intersection           | 200  | result |

**Signature Errors:**

| Code                   | Description                                            | REST | MCP    |
| ---------------------- | ------------------------------------------------------ | ---- | ------ |
| `signature_missing`    | Required signature header/field not present            | 401  | -32000 |
| `signature_invalid`    | Signature verification failed                          | 401  | -32000 |
| `key_not_found`        | Key ID not found in signer's published key set         | 401  | -32000 |
| `digest_mismatch`      | Body digest doesn't match `Content-Digest` header      | 400  | -32600 |
| `algorithm_unsupported`| Signature algorithm not supported                      | 400  | -32600 |

See [Message Signatures](signatures.md) for signature verification details.

**Protocol Errors:**

| HTTP | Description                                     | MCP        |
| ---- | ----------------------------------------------- | ---------- |
| 401  | Authentication required or credentials invalid  | -32000     |
| 403  | Authenticated but insufficient permissions      | -32000     |
| 409  | Idempotency key reused with different payload   | -32000     |
| 429  | Too many requests                               | -32000     |
| 500  | Unexpected server error                         | -32603     |
| 503  | Server temporarily unable to handle requests    | -32000     |

For MCP over HTTP, the HTTP status code is the primary signal; the JSON-RPC
`error.code` provides a secondary signal. Both transports **SHOULD** include
`Retry-After` header (REST) or `error.data.retry_after` (MCP) for 429 and 503
responses.

The Embedded Protocol uses the same JSON-RPC error codes for peer-to-peer
communication between host and embedded context. Server-specific scenarios
(rate limiting, idempotency) do not apply to the embedded transport. See
[Embedded Protocol — Response Handling](embedded-protocol.md#response-handling)
for the full error handling specification.

##### The `continue_url` Field

When UCP negotiation fails, `continue_url` provides a fallback web experience.
Businesses **SHOULD** provide the most contextually relevant URL:

- For checkout operations: link to the cart or checkout page
- For catalog operations: link to the product or search results
- As a fallback: link to the storefront homepage

This enables graceful degradation—agents can redirect buyers to complete their
task through the standard web interface.

##### Transport Bindings

=== "REST"

    **Discovery Failure (424):**

    ```http
    HTTP/1.1 424 Failed Dependency
    Content-Type: application/json

    {
      "code": "profile_unreachable",
      "content": "Unable to fetch agent profile: connection timeout",
      "continue_url": "https://merchant.com/cart"
    }
    ```

    **Version Unsupported (422):**

    ```http
    HTTP/1.1 422 Unprocessable Content
    Content-Type: application/json

    {
      "code": "version_unsupported",
      "content": "Protocol version 2026-01-12 is not supported. This business supports versions 2026-01-11 and 2026-01-23.",
      "continue_url": "https://merchant.com/cart"
    }
    ```

    **Capabilities Incompatible (200):**

    ```http
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "error",
        "capabilities": {}
      },
      "messages": [
        {
          "type": "error",
          "code": "capabilities_incompatible",
          "content": "No compatible capabilities in the intersection",
          "severity": "unrecoverable"
        }
      ],
      "continue_url": "https://merchant.com"
    }
    ```

    **Protocol Error — Rate Limit (429):**

    ```http
    HTTP/1.1 429 Too Many Requests
    Retry-After: 60
    ```

    **Protocol Error — Unauthorized (401):**

    ```http
    HTTP/1.1 401 Unauthorized
    WWW-Authenticate: Bearer realm="ucp"
    ```

    Protocol errors use standard HTTP status codes and headers. Response bodies
    are optional.

=== "MCP"

    **Discovery Failure (JSON-RPC error):**

    <!-- ucp:example schema=transports/jsonrpc def=error_response -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "error": {
        "code": -32001,
        "message": "UCP discovery failed",
        "data": {
          "code": "profile_unreachable",
          "content": "Unable to fetch agent profile: connection timeout",
          "continue_url": "https://merchant.com/cart"
        }
      }
    }
    ```

    **Version Unsupported (JSON-RPC error):**

    <!-- ucp:example schema=transports/jsonrpc def=error_response -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "error": {
        "code": -32001,
        "message": "Protocol version not supported",
        "data": {
          "code": "version_unsupported",
          "content": "Protocol version 2026-01-12 is not supported. This business supports versions 2026-01-11 and 2026-01-23.",
          "continue_url": "https://merchant.com/cart"
        }
      }
    }
    ```

    **Capabilities Incompatible (JSON-RPC result):**

    <!-- ucp:example schema=common/types/error_response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
          "ucp": {
            "version": "{{ ucp_version }}",
            "status": "error"
          },
          "messages": [
            {
              "type": "error",
              "code": "capabilities_incompatible",
              "content": "No compatible capabilities in the intersection",
              "severity": "unrecoverable"
            }
          ],
          "continue_url": "https://merchant.com"
        },
        "content": [
          {"type": "text", "text": "{\"ucp\":{…},…}"}
        ]
      }
    }
    ```

    **Protocol Error — Rate Limit (JSON-RPC error):**

    <!-- ucp:example schema=transports/jsonrpc def=error_response -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "error": {
        "code": -32000,
        "message": "Rate limit exceeded",
        "data": {
          "retry_after": 60
        }
      }
    }
    ```

    **Protocol Error — Unauthorized (JSON-RPC error):**

    <!-- ucp:example schema=transports/jsonrpc def=error_response -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "error": {
        "code": -32000,
        "message": "Unauthorized"
      }
    }
    ```

    When using Streamable HTTP transport, servers **MUST** return the
    corresponding HTTP status code (e.g., `429` for rate limit) alongside
    the JSON-RPC error. The HTTP status code is the primary signal for
    error type.

#### Capability Declaration in Responses

The `capabilities` registry in responses indicates active capabilities:

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {"version": "{{ ucp_version }}"}
      ],
      "dev.ucp.shopping.fulfillment": [
        {"version": "{{ ucp_version }}"}
      ]
    },
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {"id": "processor_tokenizer", "version": "{{ ucp_version }}", "available_instruments": [{"type": "card"}]}
      ]
    }
  },
  "id": "checkout_123",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ]
}
```

#### Response Capability Selection

Businesses **MUST** include in `ucp.capabilities` only the capabilities that are:

1. In the negotiated intersection for this session, AND
2. Relevant to this response's operation type

**Root Capability Relevance:**

A root capability is relevant if it matches the operation type:

- `create_checkout` / `update_checkout` / `complete_checkout` →
    `dev.ucp.shopping.checkout`
- `create_cart` / `update_cart` → `dev.ucp.shopping.cart`
- Order webhooks → `dev.ucp.shopping.order`

**Extension Relevance:**

An extension is relevant if **any** of its `extends` values matches a relevant
root capability.

**Selection Examples:**

| Response Type | Includes                        | Does NOT Include             |
| ------------- | ------------------------------- | ---------------------------- |
| Checkout      | checkout, discount, fulfillment | cart, order                  |
| Cart          | cart, discount                  | checkout, fulfillment, order |
| Order         | order                           | checkout, cart, discount     |

## Identity & Authentication

UCP profiles serve dual purpose: they declare a party's **capabilities**
for negotiation (see [Profile Structure](#profile-structure)) and publish
**signing keys** for identity verification — enabling both capability
negotiation and cryptographic authentication from a single document.

Businesses publish their profile at `/.well-known/ucp` as the discovery
entry point — platforms fetch it to determine protocol support, locate
endpoints, and negotiate capabilities. Platforms advertise their profile
URL per-request via the `UCP-Agent` header, enabling businesses to
negotiate capabilities and verify identity. This design enables
**permissionless onboarding** — any platform with a discoverable profile
can interact with any business without prior registration.

**Web Bot Auth interop.** Signers opting into WBA-shape signatures
additionally emit a `Signature-Agent` header advertising their keys. See
[Identity Resolution Algorithm](#identity-resolution-algorithm) for how
verifiers resolve identity and
[Message Signatures — WBA Interop](signatures.md#wba-interop) for the
signature shape.

### Authentication Mechanisms

Businesses **SHOULD** authenticate platforms to prevent impersonation and ensure
message integrity. UCP is compatible with multiple authentication mechanisms:

- **API Keys** — Pre-shared secrets exchanged out-of-band
- **OAuth 2.0** — Client credentials or other OAuth flows
- **mTLS** — Mutual TLS with client certificates
- **HTTP Message Signatures** — Cryptographic signatures per
  [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421) (see
  [Message Signatures](signatures.md) for full specification)

HTTP Message Signatures enable permissionless onboarding — businesses can
verify platforms by their advertised public keys without negotiating shared
secrets. The other mechanisms require prior credential exchange and imply a
pre-established relationship.

Business-to-platform webhooks **MUST** be signed. See
[Message Signatures — When Signatures Apply](signatures.md#when-signatures-apply).

#### Identity Binding

Regardless of authentication mechanism, verifiers **MUST** ensure the
authenticated identity is consistent with the `UCP-Agent` header:

- **HTTP Message Signatures** — The signer's profile (from `UCP-Agent`) is
    verified by signature validation; no additional check needed.
- **API keys / OAuth / mTLS** — Verifiers **MUST** confirm the authenticated
    principal is authorized to act on behalf of the profile identified in
    `UCP-Agent`. Reject requests where the authenticated identity and claimed
    profile conflict.

### Key Discovery

Both parties publish public keys in their UCP profile. Platforms fetch
the business profile at `/.well-known/ucp`; businesses fetch the
platform profile from the `UCP-Agent` header (or `Signature-Agent`
header when Web Bot Auth interop is in use). The same profile that
provides capabilities also provides verification keys — this is UCP's
key resolution mechanism for
[RFC 9421](https://www.rfc-editor.org/rfc/rfc9421) HTTP Message
Signatures.

See [Profile Structure](#profile-structure) for the publishing
contract (the canonical top-level `keys[]` JWK Set). Both resolution
paths read the same list:

- **Resolved via `UCP-Agent`** (default UCP key lookup) — read `keys[]`.
- **Resolved via `Signature-Agent`** (Web Bot Auth, optional) — read
  `keys[]`; the `cimd`/`directory` variants reach the JWK Set through
  their own documents.

For the full verifier algorithm — capability-based key resolution,
profile fetching, and covered-component enforcement — see
[Identity Resolution Algorithm](#identity-resolution-algorithm) below.
For key format (JWK), supported algorithms, key rotation procedures,
and the Web Bot Auth interop signature shape, see
[Message Signatures](signatures.md).

### Profile Requirements

#### Hosting

Profiles, and the schema and transport-description artifacts they reference,
must be reliably hosted. An unreliable or misconfigured endpoint may prevent
the other party from processing requests.

1. Published artifacts **MUST** be served over HTTPS.
2. Profile endpoints **MUST NOT** use redirects (3xx).
3. Published artifacts **MUST** include a `Cache-Control` header with
   `public` and `max-age` of at least 60 seconds, and **MUST NOT** be
   served with `private`, `no-store`, or `no-cache` directives.
4. Published artifacts **SHOULD** include a validator (`ETag` or
   `Last-Modified`) so consumers can revalidate cached copies efficiently.

Profiles represent a party's stable identity and capabilities. Profile
URLs are expected to remain consistent across requests and not contain
per-transaction or per-session configuration — the caching policy above
enforces this by requiring shared cache support with a minimum TTL.

#### Fetching

Businesses fetch platform profiles to perform capability negotiation and
verify identity. UCP defines best practices that enable permissionless
onboarding, but businesses retain full control over their access policies
and **MAY** enforce additional rules based on established trust, observed
behavior, or operational requirements.

Businesses **SHOULD** maintain a registry of pre-approved platforms —
platforms whose profiles have been validated and whose trust is
established through out-of-band mechanisms (API key, OAuth credential,
mTLS certificate, or prior vetting). Known platforms can be served
efficiently based on cached identity and capabilities, and are not
subject to discovery budget constraints.

When a platform is *not recognized*, it triggers dynamic profile
discovery. Businesses **SHOULD** establish a fixed
discovery footprint so that resource consumption for resolving
unrecognized platforms remains constant regardless of how many platforms
request access. Strategies include:

- **Fixed-size profile cache** (e.g., LRU) — bounds memory regardless of
  the number of unique profile URLs encountered
- **Global rate limit** on discovery fetches — bounds outbound network
  without requiring per-origin state tracking
- **Backoff on repeated failures** — reduces retries to persistently
  unavailable or malicious profile endpoints
- **Asynchronous discovery** — defer profile resolution by responding
  with a `503` status code and `Retry-After` header, and resolve the
  profile in the background; when the platform retries, the validated
  profile is cached and capability negotiation proceeds synchronously

These rules apply to any URL dereferenced during identity resolution —
the profile, and any `jwks_uri` or CIMD document a verifier follows:

1. Implementations **MUST** reject URLs not served over HTTPS.
2. Implementations **MUST NOT** follow redirects (3xx).
3. Implementations **SHOULD** enforce connect and response timeouts.
4. Implementations **SHOULD** cache profiles with a minimum TTL floor
   of 60 seconds, regardless of the origin's `Cache-Control` headers.
5. Implementations **MAY** refresh profiles asynchronously using
   stale-while-revalidate semantics.
6. On signature verification failure with an unknown `kid`,
   implementations **SHOULD** force-refresh the cached profile once —
   but **MUST NOT** do so more than once per TTL floor per origin.
7. Implementations **MUST** reject URLs that resolve to special-use IP
   addresses ([RFC 6890](https://www.rfc-editor.org/rfc/rfc6890) —
   loopback, link-local including the cloud-metadata address
   `169.254.169.254`, private, and other reserved ranges), except a
   loopback target when the verifier itself runs on the same loopback
   interface (local development). Verifiers **SHOULD** validate the
   resolved address, not just the hostname (to resist DNS rebinding),
   and **SHOULD NOT** dereference a URL contained within a fetched
   document (e.g. a CIMD `jwks_uri`) that resolves to such an address.
8. Implementations **SHOULD** bound the response body size to prevent
   unbounded-response resource exhaustion. A UCP profile is an
   identity/capability manifest, not a data payload (documented profiles
   are under 5 KiB); since the schema sets no size limit, this bound is a
   deployment guard, and verifiers **SHOULD** set it no lower than
   128 KiB so it does not reject conformant profiles.

If a profile cannot be fetched (timeout, DNS failure, 5xx) or fails
validation (invalid schema, signing keys, signature mismatch),
businesses **MUST** reject the request with an appropriate error and
status code (see [Error Handling](#error-handling)).

### Deployment Patterns for WBA Interop

A UCP profile carrying a top-level `keys[]` array is a valid RFC 7517
JWK Set, which a signer can optionally reuse as its Web Bot Auth key
source. The `Signature-Agent` header's `type` parameter selects
how a verifier resolves the advertised keys. The parameter and
its `jwks_uri`/`cimd`/`directory` values are defined in §4.1 of
[draft-meunier-webbotauth-httpsig-directory-00](https://datatracker.ietf.org/doc/draft-meunier-webbotauth-httpsig-directory/00/).
Each variant can stand alone or point back at the UCP profile:

- **`type=jwks_uri`** — the member value is a JWK Set URL, fetched
  directly. Point it at the UCP profile URL and the profile's `keys[]`
  serves as the JWK Set: one document is both profile and key source.
  Integrity derives from TLS to the profile origin, with no per-key
  self-signature. Set `type=jwks_uri` explicitly: omitting `type`
  defaults to `directory` (below), which expects a signed
  directory, not a static profile.

  ```text
  Signature-Agent: sig1="https://platform.example/.well-known/ucp";type=jwks_uri
  ```

- **`type=cimd`** — the member value is a Client ID Metadata Document
  ([draft-ietf-oauth-client-id-metadata-document](https://datatracker.ietf.org/doc/draft-ietf-oauth-client-id-metadata-document/))
  whose `jwks_uri` **MAY** point back at the UCP profile. Use when a
  counterparty consumes CIMD-shaped agent identity.

  ```text
  Signature-Agent: sig1="https://platform.example/agent";type=cimd
  ```

- **`type=directory`** *(default)* — when `type` is omitted or set to
  `directory`, the member value is an **origin** (not a full URL): the
  verifier appends the registered well-known path
  (`/.well-known/http-message-signatures-directory`) to that origin and
  fetches a signed directory there. Its format, per-key self-signatures,
  and media type are defined by the directory draft §5.2.

  ```text
  Signature-Agent: sig1="https://platform.example"  # type omitted -> directory
  Signature-Agent: sig1="https://platform.example";type=directory  # explicit
  ```

### Identity Resolution Algorithm

UCP and Web Bot Auth define two key-resolution mechanisms. Which one a
verifier uses is chosen by **verifier capability and the headers
present**, not by the signature's `tag` — the `tag` is a hint, not a
gate. Default UCP key lookup (`UCP-Agent`) is supported by every UCP
verifier and works for any UCP signature; Web Bot Auth key lookup
(`Signature-Agent`) is an optional, additive layer.

A request MAY carry multiple signatures per
[RFC 9421 §4.3](https://www.rfc-editor.org/rfc/rfc9421#section-4.3).
Verifiers attempt each signature independently; the request is
authenticated when at least one signature verifies. The algorithm
below processes a single signature.

1. **Resolve the signing key.** A verifier uses a resolution mechanism
   it supports whose header is present:
    - **`UCP-Agent` — default UCP key lookup, supported by every UCP
      verifier.** Resolve the `UCP-Agent` profile URL and read
      `keys[]`. This path applies to UCP signatures that are
      untagged (default UCP) or carry `tag="web-bot-auth"` (the
      dual-audience shape); the verifier resolves them via `UCP-Agent`,
      treats `signature-agent` as an ordinary covered component, and
      need not implement Web Bot Auth key discovery. (Verifying a
      dual-audience signature does still require supporting the key's
      algorithm — whichever the signer used, per
      [Signature Algorithms](signatures.md#signature-algorithms) — and
      RFC 9421 §2.1.2 Dictionary-member component selection to cover
      `signature-agent;key="<label>"`.) Signatures with tags
      other than `web-bot-auth` are skipped unless UCP defines
      or explicitly accepts that tag.
    - **`Signature-Agent` — Web Bot Auth key lookup, OPTIONAL
      (WBA-aware verifiers).** For a signature carrying
      `tag="web-bot-auth"`, a WBA-aware verifier **MAY** instead resolve
      via the `Signature-Agent` member, parsed per the
      [Signature-Agent parsing rules](signatures.md#rest-request-verification).
      Such a signature **MUST** satisfy the WBA agent-signature
      requirements in
      [draft-meunier-webbotauth-httpsig-protocol-00](https://datatracker.ietf.org/doc/draft-meunier-webbotauth-httpsig-protocol/00/)
      §4.2 (see [WBA Interop](signatures.md#wba-interop) for the
      signer-side shape). The member value **MUST** be an HTTPS URL.
      Its `type` selects resolution: `jwks_uri` and `cimd` reach the
      keys through the signer's profile and are resolved by the steps
      below; the `directory` mechanism is defined by the directory draft
      (see [Deployment Patterns](#deployment-patterns-for-wba-interop)).
      `data:` URI inline form is out of scope for UCP-WBA interop.
   **Skip** this signature if no mechanism the verifier supports can
   resolve its key — the required header is absent, no `Signature-Agent`
   member matches the signature label, the URL is non-HTTPS, or the
   `tag` is scoped to a purpose this verifier does not handle.
2. **Fetch the document** per [§Fetching](#fetching). If the fetch
   fails (DNS error, network failure, non-2xx response, parse failure),
   **skip** this signature.
3. **Locate the key list.** The profile's top-level `keys[]` (RFC 7517
   JWK Set) when resolved via `UCP-Agent` or via `Signature-Agent`
   `type=jwks_uri`; for `type=cimd`, dereference the document's
   `jwks_uri` to obtain the JWK Set. Integrity derives from TLS to the
   resolved origin.
4. **Match the signature's `keyid`** to a `kid` in the resolved key
   list. When resolving, **skip keys not usable for signature
   verification**: any key marked `use:"enc"`, or whose `key_ops` is
   present but does not include `"verify"`
   ([RFC 7517](https://www.rfc-editor.org/rfc/rfc7517) §4.2, §4.3). Keys
   that set `use:"sig"` or omit both members remain eligible. **Skip**
   this signature if no eligible key matches. For WBA-shape signatures
   (`tag="web-bot-auth"`), the verifier **MUST** also confirm `keyid`
   equals the [RFC 7638](https://www.rfc-editor.org/rfc/rfc7638) SHA-256
   thumbprint of the matched JWK — the WBA architecture draft §4.2
   requires this, binding the advertised key identity to its bytes. If
   it fails, skip this signature.
5. **Enforce covered-component requirements, in every regime.**
   Independent of `tag` and transport, the signature **MUST** cover the
   request target (`@method`, `@authority`, `@path`; `@query` when a
   query string is present), the body when present (`content-digest`,
   `content-type`), and each of these request headers when present:
   `ucp-agent`, `signature-agent`, `idempotency-key` (a closed set — a
   header added to UCP later is gate-required only if its defining
   section says so). If any
   such component is absent from the signature's covered set, **skip**
   this signature — a target, body, or header the signature does not
   cover is treated as unsigned. This prevents a signature satisfying only
   Web Bot Auth's minimal covered set (`@authority`, `signature-agent`)
   from authenticating a UCP request whose body, method, or path is
   unbound. (Whether a request must carry `Idempotency-Key` at all is a
   binding-level rule, separate from this coverage check.)
6. **Verify the signature** using the matched key. The signing
   algorithm is derived from the JWK's `kty`/`crv`. If the verifier
   does not support the matched key's `kty`, `crv`, or `alg`, **skip**
   this signature; it yields `algorithm_unsupported` if no other
   signature authenticates the request.

The request **MUST** be rejected (`key_not_found`,
`algorithm_unsupported`, or related error) only when every signature
has been skipped or fails verification.

**Authenticated identity.** When a signature verifies, the
authenticated signer is identified by the URL that supplied the
verifying key — the `Signature-Agent` URL for WBA-shape signatures,
the `UCP-Agent` URL for default UCP signatures.
Both URLs may be present in the same request; the identity attached
to the request is determined by which signature verified, not by
which headers were sent. When multiple signatures verify, each
identifies the signer only as the URL that supplied its key — a key
resolved via `Signature-Agent` proves control of that key source, not
of the `UCP-Agent` profile (whose URL is merely a signed header value).
Implementations **MUST** treat the request as a single authenticated
identity only when those URLs are the same after normalization;
otherwise they are distinct identities and policy decides whether
either suffices.

This rule governs **HTTP transport identity**. Payload-layer
assertions (e.g., AP2 mandate JWTs carried in the request body) have
their own identity binding and key-resolution rules; see
[AP2 Mandates](ap2-mandates.md).

## Payment Architecture

UCP adopts a decoupled architecture for payments to solve the "N-to-N"
complexity problem between **platforms**, **businesses**, and **payment
credential providers**. This design separates **Payment
Instruments** (what is accepted) from **Payment Handlers** (the specifications
for how instruments are processed), ensuring security and scalability.

### Security and Trust Model

The payment architecture is built on a "Trust-by-Design" philosophy. It assumes
that while the business and payment credential provider have a trusted legal
relationship, the platform (Client) acts as an intermediary that **SHOULD NOT**
touch raw financial credentials.

#### The Trust Triangle

1. **Business ↔ Payment Credential Provider:** A pre-existing legal and technical relationship. The business holds API keys and a contract with the payment credential provider.
2. **Platform ↔ Payment Credential Provider:** The platform interacts with the payment credential provider's interface (e.g., an iframe or API) to tokenize data but is not the "owner" of the funds.
3. **Platform ↔ Business:** The platform passes the result (a token or mandate) to the business to finalize the order.

#### Enhanced Security for Autonomous Commerce

For scenarios requiring cryptographic proof of user authorization (e.g.,
autonomous AI agents), UCP supports the **AP2 Mandates Extension**
(`dev.ucp.shopping.ap2_mandate`). This optional extension provides
non-repudiable authorization through verifiable digital credentials.

See [Transaction Integrity](#transaction-integrity-and-non-repudiation)
and [AP2 Mandates Extension](ap2-mandates.md) for details on when and how to
use this extension.

#### Credential Flow & PCI Scope

To minimize compliance overhead (PCI-DSS):

1. **Unidirectional Flow:** Credentials flow **Platform → Business** only. Businesses **MUST NOT** echo credentials back in responses.
2. **Opaque Credentials:** Platforms handle tokens (such as network tokens), encrypted payloads, or mandates, not raw PANs.
3. **Handler ID Routing:** The `handler_id` in the payload ensures the business knows exactly which payment credential provider key to use for decryption/charging, preventing key confusion attacks.

### Roles & Responsibilities: Who Implements What?

A common source of confusion is the division of labor. The UCP payment model
splits responsibilities as follows:

| Role                            | Responsibility             | Action                                                                                                                                                                                                                                                              |
| :------------------------------ | :------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Payment Credential Provider** | **Defines the Spec**       | Creates the **Handler Definition**. They publish the "Blueprint" (JSON Schemas) that dictates how to tokenize a card and what config inputs are needed.<br>*Example: "Here is the schema for the 'com.psp-x.tokenization' handler."*                                |
| **Business**                    | **Configures the Handler** | Selects the Handler they want to use and provides their specific **Configuration** (Public Keys, Merchant IDs) in the UCP Checkout Response. *Example: "I accept Visa using 'com.psp-x.tokenization' with this Publishable Key."*                                   |
| **Platform**                    | **Executes the Protocol**  | Reads the business's config and executes the logic defined by the payment credential provider's Spec to acquire a token. *Example: "I see the Business uses a payment credential provider. I will call the provider's SDK with the Business's Key to get a token."* |

### Payment in the Checkout Lifecycle

When payment is required, the payment process follows a standard 3-step lifecycle
within UCP: **Negotiation**, **Acquisition**, and **Completion**.

![High-level payment flow sequence diagram](site:specification/images/ucp-payment-flow.png)

1. **Negotiation (Business → Platform):** The business advertises available payment handlers in their UCP profile. This tells the platform *how* to pay (e.g., "Use this specific payment credential provider endpoint with this public key").
2. **Acquisition (Platform ↔ Payment Credential Provider):** The platform executes the handler's logic. This happens client-side or agent-side, directly with the payment credential provider (e.g., exchanging credentials for a network token). The business is not involved, ensuring raw data never touches the business's frontend API.
3. **Completion (Platform → Business):** The platform submits the opaque credential (token) to the business. The business uses it to capture funds via their backend integration with the payment credential provider.

### Payment Handlers

Payment Handlers are **specifications** (not entities) that define how payment
instruments are processed. They are the contract that binds the three
participants together.

**Important distinction:**

- **Payment Credential Provider** = The participant (entity like Google Pay, Shop Pay)
- **Payment Handler** = The specification the provider authors (e.g., `com.google.pay`, `dev.shopify.shop_pay`)

Payment handlers allow for a variety of different payment instruments and
token-types to be supported, including network tokens. They are standardized
definitions typically authored by payment credential providers or the UCP
governing body.

**Dynamic Filtering:** Businesses **MUST** filter the `handlers` list based on
the context of the cart (e.g., removing "Buy Now Pay Later" for subscription
items, or filtering regional methods based on shipping address).

**Presentation Order:** Businesses **MAY** declare a preferred presentation
order for their advertised handlers via `map_order.payment_handlers` in their
profile and response envelopes (see
[The `ucp` Protocol Namespace](#the-ucp-protocol-namespace)). The preference
is suggestive: it communicates the business's preferred presentation —
typically a conversion or risk judgment — and platforms **SHOULD** take it
into account but **MAY** apply their own ordering. The same suggestive
preference applies within a handler: the order of the business's advertised
`available_instruments` array communicates preferred instrument presentation,
earliest first. It is distinct from, and does not override, the buyer-side
preference a platform submits in `context.payment[]` (buyer-preferred
handlers, on the request side); the platform arbitrates between the two.

**Available Instrument Resolution:** Within each active handler, both the
platform and the business independently advertise `available_instruments` — the
set of instrument types and constraints each party supports. The business is
responsible for resolving these into an authoritative value in the checkout
response. The platform's declaration (from its profile) signals what it can
handle; the business intersects that with its own `business_schema` declaration
and cart context, then returns the resolved result. Platforms **MUST** treat the
`available_instruments` in the response as authoritative for that checkout. See
the [Payment Handler Guide](payment-handler-guide.md#resolving-available_instruments)
for the full resolution semantics.

**Instrument Cardinality:** A checkout submission **MUST** contain exactly one
payment instrument unless the `dev.ucp.shopping.split_payments` capability is
active. Businesses **MUST** reject submissions that violate this constraint with
a `payment_failed` error in `messages[]`. See
[Split Payments](split-payments.md) for the extension that relaxes this
constraint.

### Implementation Scenarios

The following scenarios illustrate how different payment handlers and
instruments are negotiated and executed using concrete data examples.

#### Scenario A: Digital Wallet

In this scenario, the platform identifies a payment credential provider (e.g.,
`com.google.pay`, `dev.shopify.shop_pay`) and uses their API to acquire
an encrypted payment token.

##### 1. Business Advertisement (Response from Create Checkout)

<!-- ucp:example schema=shopping/checkout target=$.ucp -->
```json
{
  "version": "{{ ucp_version }}",
  "payment_handlers": {
      "com.google.pay": [
        {
          "id": "8c9202bd-63cc-4241-8d24-d57ce69ea31c",
          "version": "{{ ucp_version }}",
          "config": {
            "api_version": 2,
            "api_version_minor": 0,
            "environment": "TEST",
            "merchant_info": {
              "merchant_name": "Example Merchant",
              "merchant_id": "01234567890123456789",
              "merchant_origin": "checkout.merchant.com"
            },
            "allowed_payment_methods": [
              {
                "type": "CARD",
                "parameters": {
                  "allowed_auth_methods": ["PAN_ONLY"],
                  "allowed_card_networks": ["VISA", "MASTERCARD"]
                },
                "tokenization_specification": {
                  "type": "PAYMENT_GATEWAY",
                  "parameters": {
                    "gateway": "example",
                    "gatewayMerchantId": "exampleGatewayMerchantId"
                  }
                }
              }
            ]
          }
        }
      ],
      "dev.shopify.shop_pay": [
        {
          "id": "shop_pay_1234",
          "version": "{{ ucp_version }}",
          "available_instruments": [
            {"type": "shop_pay"}
          ],
          "config": {
            "shop_id": "shopify-559128571",
            "environment": "production"
          }
        }
      ]
    }
}
```

##### 2. Token Execution (Platform Side)

The platform recognizes `com.google.pay` or `dev.shopify.shop_pay`. It passes the `config` into the
respective handler API. The handler returns the encrypted token data.

##### 3. Complete Checkout (Request to Business)

The Platform wraps the payment handler response into a payment instrument.

<!-- ucp:example schema=shopping/checkout op=complete direction=request -->
```json
POST /checkout-sessions/{id}/complete

{
  "payment": {
    "instruments": [
      {
        "id": "pm_1234567890abc",
        "handler_id": "8c9202bd-63cc-4241-8d24-d57ce69ea31c",
        "type": "card",
        "selected": true,
        "display": {
          "brand": "visa",
          "last_digits": "4242"
        },
        "billing_address": {
          "street_address": "123 Main Street",
          "extended_address": "Suite 400",
          "address_locality": "Charleston",
          "address_region": "SC",
          "postal_code": "29401",
          "address_country": "US",
          "first_name": "Jane",
          "last_name": "Smith"
        },
        "credential": {
          "type": "PAYMENT_GATEWAY",
          "token": "{\"signature\":\"...\",\"protocolVersion\":\"ECv2\"...}"
        }
      }
    ]
  },
  "signals": {
    "dev.ucp.buyer_ip": "203.0.113.42",
    "dev.ucp.user_agent": "Mozilla/5.0 ..."
  }
}
```

#### Scenario B: Direct Tokenization with Challenge (SCA)

In this scenario, the platform uses a generic tokenizer to request a session
token or network tokens. The bank requires Strong Customer
Authentication (SCA/3DS), forcing the business to pause completion and
request a challenge.

##### 1. Business Advertisement

<!-- ucp:example schema=shopping/checkout target=$.ucp -->
```json
{
  "version": "{{ ucp_version }}",
  "payment_handlers": {
    "com.example.tokenizer": [
        {
          "id": "merchant_tokenizer",
          "version": "{{ ucp_version }}",
          "spec": "https://example.com/specs/tokenizer",
          "schema": "https://example.com/schemas/tokenizer.json",
          "available_instruments": [
            {
              "type": "card",
              "constraints": {
                "brands": ["visa", "mastercard"]
              }
            }
          ],
          "config": {
            "token_url": "https://api.psp.com/tokens",
            "public_key": "pk_123"
          }
        }
      ]
  }
}
```

##### 2. Token Execution (Platform Side)

The platform calls `https://api.psp.com/tokens` which identity **SHOULD** have
previous legal binding connection with them and receives `tok_visa_123`
(which could represent a vaulted card or network token).

##### 3. Complete Checkout (Request to Business)

<!-- ucp:example schema=shopping/checkout op=complete direction=request -->
```json
POST /checkout-sessions/{id}/complete

{
  "payment": {
    "instruments": [
      {
        "handler_id": "merchant_tokenizer",
        // ... more instrument required field
        "credential": { "token": "tok_visa_123" }
      }
    ]
  },
  "signals": {
    "dev.ucp.buyer_ip": "203.0.113.42",
    "dev.ucp.user_agent": "Mozilla/5.0 ..."
  }
}
```

##### 4. Challenge Required (Response from Business)

The business attempts the charge, but the PSP returns a "Soft Decline"
requiring 3DS.

<!-- ucp:example schema=shopping/checkout extract=$.messages target=$.messages -->
```json
HTTP/1.1 200 OK

{
  "status": "requires_escalation",
  "messages": [{
    "type": "error",
    "code": "requires_3ds",
    "content": "bank requires verification.",
    "severity": "requires_buyer_input"
  }],
  "continue_url": "https://psp.com/challenge/123"
}
```

*The platform **MUST** now open `continue_url` in a WebView/Window for the user
to complete the bank check, then retry the completion.*

#### Scenario C: Autonomous Agent (AP2)

This scenario demonstrates the **Recommended Flow for Agents**. Instead of a
session token, the agent generates cryptographic mandates.

##### 1. Business Advertisement

<!-- ucp:example schema=shopping/checkout target=$.ucp -->
```json
{
  "version": "{{ ucp_version }}",
  "payment_handlers": {
    "dev.ucp.ap2_mandate_compatible_handlers": [
        {
          "id": "ap2_234352",
          "version": "{{ ucp_version }}",
          "spec": "https://example.com/specs/ap2-handler",
          "schema": "https://example.com/schemas/ap2-handler.json",
          "available_instruments": [
            {"type": "ap2_mandate"}
          ]
        }
      ]
  }
}
```

##### 2. Agent Execution

The agent cryptographically signs objects using the user's private key on a
non-agentic surface.

##### 3. Complete Checkout

<!-- ucp:example schema=shopping/checkout op=complete direction=request -->
```json
POST /checkout-sessions/{id}/complete

{
  "payment": {
    "instruments": [
      {
        "handler_id": "ap2_234352",
        // other required instruments fields
        "credential": {
          "type": "card",
          "token": "eyJhbGciOiJ..." // Token would contain payment_mandate, the signed proof of funds auth
        }
      }
    ]
  },
  "signals": {
    "dev.ucp.buyer_ip": "203.0.113.42",
    "com.example.risk_score": 0.95
  },
  "ap2": {
    "checkout_mandate": "eyJhbGciOiJ..." // Signed proof of checkout terms
  }
}
```

*This provides the business with non-repudiable proof that the user authorized
this specific transaction, enabling safe autonomous processing.*

### PCI-DSS Scope Management

#### Platform Scope

Most platform implementations can **avoid PCI-DSS scope** by:

- Using handlers that provide opaque credentials (encrypted data, token
    references, etc.)
- Never accessing or storing raw payment data (card numbers, CVV, etc.)
- Forwarding credentials without the ability to use them directly
- Using PSP tokenization payment handlers where raw credentials never pass
    through the platform

#### Business Scope

Businesses can minimize PCI scope by:

- Using payment credential provider-hosted tokenization (provider stores
    credentials, business receives token reference)
- Using wallet providers that provide encrypted credentials (Google Pay, Shop
    Pay)
- Never logging raw credentials
- Delegating credential processing to PCI-certified payment credential providers

#### Payment Credential Provider Scope

Payment credential providers (PSPs, wallets) are typically PCI-DSS Level 1
certified and handle:

- Raw credential collection
- Credential protection (tokenization, encryption, secure storage)
- Credential validation and processing
- PCI-compliant infrastructure

### Security Best Practices

**For Businesses:**

1. Validate handler_id before processing (ensure handler is in advertised set)
2. Use separate PSP credentials for TEST vs PRODUCTION environments
3. Implement idempotency for payment processing (prevent double-charges)
4. Log payment events without logging credentials
5. Set appropriate credential timeouts
6. For autonomous commerce scenarios requiring cryptographic proof, consider
    supporting the `dev.ucp.shopping.ap2_mandate` extension (see
    [AP2 Mandates Extension](ap2-mandates.md))

**For Platforms:**

1. Always use HTTPS for checkout API calls
2. Validate handler configurations before executing protocols
3. Implement timeout handling for credential acquisition
4. Clear credentials from memory after submission
5. Handle credential expiration gracefully (re-acquire if needed)
6. For autonomous agents, consider using the `dev.ucp.shopping.ap2_mandate`
    extension for cryptographic proof of authorization (see
    [AP2 Mandates Extension](ap2-mandates.md))

**For Payment Credential Providers:**

1. Secure credentials for the specific business (encryption, tokenization, or
    other handler-specific methods)
2. Implement rate limiting on credential acquisition
3. Validate platform authorization before providing credentials
4. Set reasonable credential expiration (e.g., 15 minutes for tokens, time-
    limited encrypted payloads)
5. Ensure credentials cannot be used by platforms directly (only by the
    intended business)

### Fraud Prevention Integration

UCP supports fraud prevention through [Signals](#signals) and the
payment architecture:

- Platforms provide transaction environment [signals](#signals) (IP, user
    agent) on catalog, cart, and checkout requests
- Businesses can require additional fields in handler configurations (e.g.,
    3DS requirements)
- Payment credential providers can perform risk assessment during credential
    acquisition
- Businesses can reject high-risk transactions and request additional
    verification via signal feedback

### Payment Architecture Extensions

The core payment architecture described above can be extended for specialized
use cases:

- **AP2 Mandates Extension** (`dev.ucp.shopping.ap2_mandate`): Adds
    cryptographic proof of user authorization for autonomous commerce scenarios
    where non-repudiable evidence is required. See
    [AP2 Mandates Extension](ap2-mandates.md).

- **Custom Handler Types**: Payment credential providers can define custom
    handlers to support new payment instruments. See
    [Payment Handler Guide](payment-handler-guide.md) for details.

The extension model ensures the core architecture remains simple while
supporting advanced security and compliance requirements when needed.

## Transport Layer

UCP supports multiple transport protocols. Platforms and businesses effectively
negotiate the transport via `services` on their profiles.

### REST Transport (Core)

UCP supports **HTTP/1.1** (or higher) using RESTful patterns.

- **Content-Type:** Requests and responses **MUST** use `application/json`.
- **Methods:** Implementations **MUST** use standard HTTP verbs (e.g., `POST`
    for creation, `GET` for retrieval).
- **Status Codes:** Implementations **MUST** use standard HTTP status codes
    (e.g., 200, 201, 400, 401, 500).

### Model Context Protocol (MCP)

UCP supports **[MCP protocol](https://modelcontextprotocol.io/specification/)**,
which operates over JSON-RPC.

#### Request Format

MCP requests use the `tools/call` method with the operation name in
`params.name` and UCP payload in `params.arguments`:

<!-- ucp:example schema=shopping/checkout op=create direction=request extract=$.params.arguments.checkout -->
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "create_checkout",
    "arguments": {
      "meta": {"ucp-agent": {"profile": "https://..."}},
      "checkout": {"line_items": [...]}
    }
  },
  "id": 1
}
```

#### Response Format

MCP tool responses use a dual-output pattern for backward compatibility. UCP
MCP servers:

- **MUST** return the UCP response payload in `structuredContent`
- **SHOULD** declare `outputSchema` in tool definitions, referencing the
    appropriate UCP JSON Schema for the capability
- **SHOULD** also return serialized JSON in `content[]` for backward
    compatibility with clients not supporting `structuredContent`. Documentation
    examples abbreviate that serialized JSON string with `…` for readability.

<!-- ucp:example schema=shopping/checkout extract=$.result.structuredContent.ucp target=$.ucp -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "{{ ucp_version }}",
        "payment_handlers": {},
        "capabilities": {...}
      },
      "id": "checkout_abc123",
      "status": "incomplete"
      // ... other checkout fields
    },
    "content": [
      {"type": "text", "text": "{\"ucp\":{…},…}"}
    ]
  }
}
```

### Agent-to-Agent Protocol (A2A)

A business **MAY** expose an A2A agent that supports UCP as an A2A Extension,
allowing integration with platforms over structured UCP data types.

### Embedded Protocol (EP)

A business **MAY** embed an interface onto an eligible host that would
receive events as the user interacts with the interface and delegate key user
actions.

Initiation comes through a `continue_url` that is returned by the business.

## Standard Capabilities

UCP defines a set of standard capabilities:

| Capability Name      | ID (URI)                                                              | Description                                                                                                  |
| :------------------- | :-------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------- |
| **Cart**.            | [schemas/shopping/cart.json](site:schemas/shopping/cart.json)         | Enables basket building before purchase intent is established.                                               |
| **Checkout**         | [schemas/shopping/checkout.json](site:schemas/shopping/checkout.json) | Facilitates the creation and management of checkout sessions, including cart management and tax calculation. |
| **Identity Linking** | -                                                                     | Enables platforms to obtain authorization via OAuth 2.0 to perform actions on a user's behalf.               |
| **Order**            | [schemas/shopping/order.json](site:schemas/shopping/order.json)       | Allows businesses to push asynchronous updates about an order's lifecycle (shipping, delivery, returns).     |

### Definition & Extensions

Detailed definitions for endpoints, schemas, and valid extensions for each
capability are provided in their respective specification files. Extensions are
typically versioned and defined alongside their parent capability.

## Policies

A policy is a business rule — return terms, warranty, subscription
terms, and the like — that applies to the items in a response at the time of
purchase, carried in a core `policies[]` array alongside `messages[]` and
`links[]`.

### Policy types

A Business publishes well-known and custom policies. Every policy carries a
`type` drawn from an open, reverse-DNS vocabulary.

| Well-known type | Description |
| :-- | :-- |
| `dev.ucp.shopping.policy.return` | Return terms. |
| `dev.ucp.shopping.policy.warranty` | Warranty terms. |

A Business **MAY** define custom types in its own domain (e.g.,
`com.example.policy.price_match`) and **MAY** add type-specific fields that a
Platform modeling that `type` can read for structured context. Because the
vocabulary is open, a Platform **MUST** tolerate unknown `type` values,
presenting the policy from its `description` (see
[Presenting policies](#presenting-policies)).

### Targeting

`applies_to` is an array of RFC 9535 JSONPath expressions, evaluated relative to
the **embedding response root** — the same convention `messages[].path` uses.
The root differs by surface: `$.line_items[N]` on cart, checkout, and order,
`$.products[N]` on catalog search and lookup, `$.product` on get_product. A
policy targets nodes in one of three forms:

- **Singular query** — an expression naming exactly one node using only name
  and index selectors ([RFC 9535
  §2.3.5.1](https://www.rfc-editor.org/rfc/rfc9535#section-2.3.5.1)), e.g.
  `$.line_items[2]`.
- **Set match** — a filter, wildcard, or slice matching a set of nodes, e.g.
  `$.products[?@.category=='electronics']`.
- **Response-wide** — an omitted `applies_to`; the policy applies to the entire
  response. This is the common case: a single site-wide policy is one entry with
  no targeting, never repeated per item.

A target covers the node it names **and everything nested under it** — a policy
on `$.products[0]` covers the product and all its variants, while one on
`$.products[0].variants[3]` covers only that variant. To give one variant a
different term, a Business names it directly; the narrower target wins where the
two overlap (see Precedence, below).

### Precedence

Policies of **different** `type` are independent: each applies on its own, so a
single node can carry a warranty policy and a price-match policy at once.

Policies of the **same** `type` can contest a node. When they do, exactly one
governs and **replaces** the rest — a Platform **MUST NOT** merge their bodies.
Merging would mean inferring whether policies combine or replace, which a
Platform cannot read from the data; resolution selects one governing policy by
structure alone. When terms genuinely stack, the Business folds them into the
most-specific policy — composition is authored, not resolved. Resolving which
one governs is a **longest-prefix match** against the response in hand.

Every node has a canonical identity: its **Normalized Path** ([RFC 9535
§2.7](https://www.rfc-editor.org/rfc/rfc9535#section-2.7)), the sequence of
segments locating it from the root — `$.products[0].variants[3]` is `products`,
`0`, `variants`, `3`, and the root `$` is the empty sequence. A target
**covers** a node when a node it matches is that node or an ancestor of it —
equivalently, when the matched node's Normalized Path is a prefix of the target
node's. The length of that prefix is its **depth**.

To resolve which policy of a given `type` governs a node:

1. Take the same-`type` policies with a target covering the node. A
   Response-wide policy (omitted `applies_to`) targets the root `$`, so it
   covers every node at depth 0. If none cover the node, no policy of that
   `type` governs it.
2. Score each by its **deepest** covering match as the pair `(depth,
   precision)`: *depth* is that match's prefix length; *precision* is `1`
   when the target is a **singular query** ([RFC 9535
   §2.3.5.1](https://www.rfc-editor.org/rfc/rfc9535#section-2.3.5.1) — name and
   index selectors only, so it names a single node) and `0` when it is a **Set
   match** (filter, wildcard, or slice). If several covering matches share the
   greatest depth, take the greatest precision among them.
3. The policy with the greatest score governs — **depth first, then
   precision**.
4. When the greatest score is shared, the outcome is **undefined**. A tie
   requires two policies to cover the node at the same depth and precision;
   since a node has one ancestor at each depth, they contest the *same* node —
   two overlapping Set matches, or two Response-wide entries of one `type`. This
   is an authoring error, not an artifact of path targeting: naming the node by
   an id would collide the same way. A Business **MUST NOT** publish such a
   collision. Because resolution is undefined, a Platform **SHOULD** flag the
   ambiguity rather than resolve it silently; the treatment is left to the
   Platform.

### Absent vs. empty

When `policies[]` is absent or empty for a given response, the Platform
**SHOULD** refer to the general policy resources in `links[]` (e.g.,
`refund_policy`, or per-variant `seller.links` in catalog).

### Presenting policies

Policies describe the business rules applied to the items. A Platform **MAY**
reason over them for its own decisions — eligibility, a computed return
deadline. So that a policy is always presentable — even by a Platform that does
not model its `type` — a Business **MUST** provide a `description`, a
human-readable summary a Platform **MAY** surface to the Buyer. Presenting a
policy is optional.

When a Business **requires** a policy to be shown to the Buyer — a final-sale
item, a regulatory notice — it **MUST** emit a `messages[]` warning that:

- sets `presentation: "disclosure"`, so the Platform displays the content and
  cannot hide or dismiss it (see
  [Warning Presentation](checkout.md#warning-presentation));
- sets `path` to the item the notice concerns; and
- sets `code` to the policy's `type`, linking the notice to its policy.

The warning is type-agnostic: the Platform shows its content without
understanding the policy behind it, so one channel handles everything from
final-sale terms to regulatory notices.

A disclosure pairs with the policy that **governs** its `path` node — the one
[Precedence](#precedence) selects when several policies of the same `type` cover
that node. Precedence yields at most one, so the pairing is unambiguous. Two
rules apply:

1. A disclosure's content **MUST** agree with the policy it pairs with — the
   notice and the policy are two statements about the same node.
2. A disclosure **SHOULD** resolve to a governing policy: when its `code` names
   a `type` no policy covers at that node, the notice still displays, but
   nothing structured stands behind it.

For example, an engraved line item is final sale. A response-wide return policy
applies to the whole cart, but the item-scoped final-sale policy governs line 2,
so the disclosure on that line pairs with it — notice and policy agree:

<!-- ucp:example schema=shopping/checkout target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.return",
    "description": { "plain": "Free 30-day returns from delivery." }
  },
  {
    "type": "dev.ucp.shopping.policy.return",
    "description": { "plain": "This engraved item is final sale and cannot be returned." },
    "applies_to": ["$.line_items[2]"],
    "url": "https://example.com/returns#final-sale"
  }
]
```

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "dev.ucp.shopping.policy.return",
    "path": "$.line_items[2]",
    "presentation": "disclosure",
    "content": "This engraved item is final sale and cannot be returned."
  }
]
```

### Relationship to `links[]`

`links[]` and `policies[]` are complementary. `links[]` is the always-present
fallback — a labeled URL, response-wide, usually one per type. `policies[]` is
the structured layer when available — typed, with optional per-item
`applies_to` targeting and multiple entries (a response-wide default plus
overrides).

### Examples

A site-wide warranty with a per-item override, both the same `type`. On line
item 2 the singular query governs, overriding the Response-wide default; every
other line item keeps it:

<!-- ucp:example schema=shopping/checkout target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.warranty",
    "description": { "plain": "1-year limited warranty on all items." }
  },
  {
    "type": "dev.ucp.shopping.policy.warranty",
    "description": { "plain": "3-year extended warranty on this item." },
    "applies_to": ["$.line_items[2]"]
  }
]
```

A Set match overridden by a singular query, again the same `type`. Product 0 is
an electronics item, so both entries reach it; the singular query governs
there, while other electronics keep the 2-year term:

<!-- ucp:example schema=shopping/catalog_search op=search direction=response target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.warranty",
    "description": { "plain": "2-year warranty on electronics." },
    "applies_to": ["$.products[?@.category=='electronics']"]
  },
  {
    "type": "dev.ucp.shopping.policy.warranty",
    "description": { "plain": "5-year manufacturer-certified warranty on this item." },
    "applies_to": ["$.products[0]"]
  }
]
```

A custom `type` a Platform does not model is still presentable from its
`description`:

<!-- ucp:example schema=shopping/catalog_search op=search direction=response target=$.policies -->
```json
[
  {
    "type": "com.example.policy.price_match",
    "description": { "plain": "We match a competitor's lower price for 14 days after purchase." },
    "applies_to": ["$.products[0]"]
  }
]
```

## Security

### Transport Security

All UCP communication **MUST** occur over **HTTPS**.

### Data Privacy

Sensitive data (such as Payment Credentials or PII) **MUST** be handled
according to PCI-DSS and GDPR guidelines. UCP encourages the use of tokenized
payment data to minimize business and platform liability.

### Signals

Businesses require environment data for authorization, rate
limiting, and abuse prevention. Signal values **MUST NOT** be buyer-asserted
claims — platforms provide signals based on direct observation (e.g.,
connection IP, user agent) or by relaying independently verifiable
third-party attestations, such as cryptographically signed results from an
external verifier that the business can validate against the provider's
published key set.

All signal keys **MUST** use reverse-domain naming to ensure provenance and
prevent collisions when multiple extensions contribute to the shared namespace.
Well-known signals use the `dev.ucp` namespace (e.g., `dev.ucp.buyer_ip`);
extension signals use their own namespace (e.g., `com.example.device_id`).

<!-- ucp:example schema=shopping/checkout op=create direction=request target=$.signals -->
```json
{
  "dev.ucp.buyer_ip": "203.0.113.42",
  "dev.ucp.user_agent": "Mozilla/5.0 ...",
  "com.example.attestation": {
    "provider_jwks": "https://example.com/.well-known/jwks.json",
    "kid": "example-key-2026-01",
    "payload": { "id": "att-7c3e9f", "pass": true, "...": "..." },
    "sig": "base64url..."
  }
}
```

Signal fields may contain personally identifiable information
(PII). Platforms **SHOULD** include only signals relevant to the current
transaction. Businesses **SHOULD NOT** persist signal data beyond the
operational needs of the transaction (e.g., order finalization, fraud review).

Businesses **MAY** use messages with code `signal` to request additional
data. The `path` field identifies the requested signal; the message `type`
determines enforcement. An `error` blocks status progression until the
signal is provided; an `info` is advisory and non-blocking.

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "error",
    "code": "signal",
    "path": "$.signals['dev.ucp.buyer_ip']",
    "content": "Buyer IP is required to proceed.",
    "severity": "recoverable"
  },
  {
    "type": "info",
    "code": "signal",
    "path": "$.signals['dev.ucp.user_agent']",
    "content": "Providing user agent may improve checkout outcomes."
  }
]
```

### Attribution

Platforms refer users to businesses through many channels — paid ads,
organic recommendations, influencer links, AI agents. In a browser-based
flow, the referral context (campaigns, click identifiers, source/medium
markers) flows through URL query parameters. The `attribution` field
enables platforms to communicate the same parameters to businesses.

UCP does **NOT** prescribe attribution models, windows, or assignment
logic. Platforms use their existing conventions (GA4 campaign parameters,
click identifiers like `gclid` / `fbclid` / `ttclid`, etc.); businesses
receive and process them according to their own analytics needs.

<!-- ucp:example schema=shopping/checkout op=create direction=request target=$.attribution -->
```json
{
  "campaign_id": "18234567890",
  "campaign_source": "google",
  "campaign_medium": "cpc",
  "campaign_name": "spring_2026",
  "gclid": "EAIaIQobChMI..."
}
```

Attribution is informational and optionally provided by the platform.
Businesses do not negotiate or advertise support; the field's presence or
absence MUST NOT affect the response or negotiation.

The data can carry pseudonymous identifiers (click IDs, session keys)
treated as personal data under applicable data protection laws. Platforms
and businesses are each responsible for compliance in their respective
jurisdictions: platforms determine what to emit and disclose; businesses
apply their own data handling, retention, and consent policies. The
`buyer_consent` extension provides a structured channel for buyers to
communicate consent state.

Attribution appears on cart, checkout, and catalog requests as
platform-provided attribution context; on order it appears as a
business-emitted snapshot of the originating checkout's attribution.

### Transaction Integrity and Non-Repudiation

For scenarios requiring cryptographic proof of authorization (e.g., autonomous
agents, high-value transactions), UCP supports the **AP2 Mandates Extension**
(`dev.ucp.shopping.ap2_mandate`). When this optional extension is negotiated:

- Businesses provide a cryptographic signature on checkout terms
- Platforms provide cryptographic mandates proving user authorization

This mechanism provides strong, end-to-end cryptographic assurances about
transaction details and participant consent, significantly reducing risks of
tampering and disputes.

See [AP2 Mandates Extension](ap2-mandates.md) for complete specification,
implementation guide, and examples.

## Versioning

### Version Format

UCP uses date-based versioning in the format `YYYY-MM-DD`. This provides
clear chronological ordering and unambiguous version comparison.

### Versioned Profiles

UCP prioritizes strong backwards compatibility. Each profile document declares
one core release version in `ucp.version`; its services, capabilities,
extensions, and payment handlers also carry explicit versions. A Business
advertises its current profile and links to profiles for older supported releases
through `supported_versions`; see [Protocol Version](#protocol-version).

#### Example

=== "Business Profile"

    <!-- ucp:example schema=profile def=business_schema -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "services": { ... },
        "capabilities": { ... },
        "payment_handlers": { ... }
      }
    }
    ```

=== "Platform Profile"

    <!-- ucp:example schema=profile def=platform_schema -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "services": { ... },
        "capabilities": { ... },
        "payment_handlers": { ... }
      }
    }
    ```

### Version Selection

![High-level resolution flow sequence diagram](site:specification/images/ucp-discovery-negotiation.png)

Protocol version selection chooses one complete Business profile first.
Capability negotiation then selects active capabilities and extensions by exact
version intersection within that profile. The sections below define each step;
see [Component Versioning and Release Snapshots](#component-versioning-and-release-snapshots)
for release alignment and version ownership.

#### Protocol Version

The `version` field declares the business's current protocol version.
The profile at `/.well-known/ucp` describes the capabilities, services,
and payment handlers available at that version.

Businesses that support older protocol versions **SHOULD** declare a
`supported_versions` object mapping each older version to a profile
URI. Each URI points to a complete, self-contained profile for that
version — whose `ucp.version` equals its map key and which includes
its own capabilities, services, payment handlers, and signing keys.
When `supported_versions` is omitted, only `version` is supported.

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "2026-01-23",
    "supported_versions": {
      "2026-01-11": "https://business.example.com/.well-known/ucp/2026-01-11"
    },
    "services": {},
    "payment_handlers": {}
  }
}
```

##### Initial Service and Capability Discovery

Platforms discover a business's capabilities through the following flow:

1. The Platform fetches `/.well-known/ucp` — this is the current version
    profile.
2. The Platform selects a mutually supported protocol version from the
    Business's `version` and `supported_versions` keys; Platforms **SHOULD**
    prefer the most recent. If the selected version matches `version`, the
    Platform uses this profile directly and proceeds to capability
    negotiation.
3. If the selected version is a key in
    `supported_versions`: fetch the profile at the mapped URI. The
    Platform **MUST** verify that the fetched profile's `ucp.version`
    equals the `supported_versions` key it selected; on mismatch the
    Platform **MUST NOT** use that profile. Otherwise this profile
    describes the capabilities available at that protocol version —
    proceed to capability negotiation.
4. If no mutually supported version exists, the Business does not support
    the Platform's protocol version. Platforms **SHOULD NOT** send requests
    with an incompatible version; Businesses **MUST** respond with a
    `version_unsupported` error.

Version-specific profiles are leaf documents — they describe exactly
one protocol version and **MUST NOT** contain a `supported_versions`
field.

A selected profile guarantees compatibility among its declared capabilities at
its declared version; across versions, resource representations may differ.
Platforms **MAY** run separate negotiations with the same Business at different
supported versions, and **SHOULD NOT** combine or intersect capabilities across
profiles within the same negotiation.

##### Request-Time Validation

Businesses **MUST** validate the platform's protocol version on
every request:

1. Platform declares the protocol version it uses via the
    `version` field in the profile referenced in the request.
2. Business validates:
    - If the platform's `version` matches the business's `version`
        or is a key in `supported_versions`: the request **MAY**
        proceed to capability negotiation using the matching
        version of the business profile.
    - Otherwise: Business **MUST** return a `version_unsupported`
        error.
3. If capability negotiation yields no mutually supported version
    for a capability required by the requested operation, the
    business **MUST** return a `capabilities_incompatible` error
    (see [Error Handling](#error-handling)).
4. Businesses **MUST** include the negotiated protocol version in
    every response.

Response with version confirmation:

<!-- ucp:example schema=shopping/checkout extract=$.ucp target=$.ucp -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": { ... },
    "payment_handlers": { ... }
  },
  "id": "checkout_123",
  "status": "incomplete"
  // ... other checkout fields
}
```

Version unsupported error — no resource is created:

<!-- ucp:example schema=common/types/error_response op=read -->
```json
{
  "ucp": { "version": "2026-01-11", "status": "error" },
  "messages": [{
    "type": "error",
    "code": "version_unsupported",
    "content": "Version 2026-01-12 is not supported. This business implements version 2026-01-11.",
    "severity": "unrecoverable"
  }],
  "continue_url": "https://merchant.com/"
}
```

##### Pre-release Versions

The protocol version **MUST** be a dated release in `YYYY-MM-DD` format.
Businesses **MUST NOT** advertise a non-date version string (e.g.
`"draft"`) in their profile `version` field or in `supported_versions`.
Pre-release implementations are not stable and MUST NOT be surfaced
through public discovery — doing so would expose the general ecosystem
to undefined behavior and incompatible changes without notice.

Platforms and businesses **MAY** coordinate on pre-release implementations outside of
public discovery. Such use carries no stability or compatibility
guarantees — the underlying behavior may change at any time without
notice.

#### Capability Versions

Capability compatibility is established only by exact version equality, not by
inferring compatibility from date order. Each capability in the profile is an
array; multiple entries with different `version` values advertise support for
multiple versions where the applicable publication policy permits it. When the
exact shared set contains more than one version, the intersection algorithm
orders those shared dates to select the latest one. Supported third-party
extension versions advance independently of `ucp.version`. UCP-authored
`dev.ucp.*` entries declare version `D` in release `D`: a profile for
`ucp.version = D` advertises version `D` for those entries. Older `dev.ucp.*`
versions are advertised only through `supported_versions` leaf profiles, never
as additional entries in a newer profile: the registry mechanism supports
multi-version arrays, but the core publication contract does not exercise them
for `dev.ucp.*` entries. Multi-version arrays therefore arise for third-party
extensions whose authors support multiple versions concurrently. The capability
intersection algorithm considers only capability versions supported by both
parties.

Businesses **MUST** include only capabilities compatible with the
negotiated protocol version in their response. A capability that
depends on features introduced in a newer protocol version **MUST
NOT** be included when processing at an older protocol version.

### Backwards Compatibility

UCP classifies changes as backwards-compatible or breaking and applies this
classification to its own components to govern how a UCP release advances.
Publication and backport policy for both classes is defined in
[Component Versioning and Release Snapshots](#component-versioning-and-release-snapshots).
The lists below describe which changes preserve and which break conforming
integrations; third-party extension and payment-handler authors control their own
version policy and can apply the same distinction on their own cadence.

#### Backwards-Compatible Changes

The following changes are **backwards-compatible**: they do not break conforming
integrations.

- Adding new non-required fields to responses
- Adding new non-required parameters to requests
- Adding new endpoints, methods, or operations to a transport
- Adding new error codes with existing error structures
- Adding new values to enums (unless explicitly documented as exhaustive)
- Changing the order of fields in responses
- Changing the length or format of opaque strings (IDs, tokens)

#### Breaking Changes

The following changes are **breaking**: they break conforming integrations and
require a new component version.

- Removing or renaming existing fields
- Changing field types or semantics
- Making non-required fields required
- Removing operations, methods, or endpoints
- Changing authentication or authorization requirements
- Modifying existing protocol flow or state machine
- Changing the meaning of existing error codes

### Component Versioning and Release Snapshots

A UCP release `D` is a snapshot of the core protocol — its services and transport
bindings, capabilities, extensions, and shared schemas — published and certified
together as internally compatible. Selecting `ucp.version` `D` selects that
snapshot. For a release `D`:

1. `ucp.version` is `D`.
2. Every UCP-defined service declares `version` `D`. Each service entry pairs the
    service with one transport binding, so every entry under a service repeats
    that service `version`; transport bindings have no separate version. The
    referenced OpenAPI/OpenRPC artifacts are published under `D` as release
    metadata.
3. Every UCP-defined capability and extension declares `version` `D`, even when
    its own schema did not change directly.
4. Shared schemas are published as part of the same snapshot.
5. UCP certifies the snapshot — components, bindings, and supported
    compositions — together before publishing it.

UCP **MAY** backport an approved backward-compatible change — a feature, or a
security, correctness, or interoperability fix — to a supported release and its
generated `D` artifacts. Breaking changes enter the next release and are not
backported by default; in exceptional cases, the Governance Council **MAY**
approve backporting a breaking change to a supported release, limited to
defects that compromise the security, correctness, or interoperability of the
release as published, and following the breaking-change notice process. UCP
**MUST** re-certify the snapshot before publishing any updated artifacts.

A dated release works like a long-term-support channel: the date names a
compatibility line, and backported changes amend the published `D` snapshot in
place — `D` stays the same while its contents change, so parties that fetched
at different times can hold different copies of the same `D`. This skew is
safe by construction: backports default to the backwards-compatible class, so
an earlier copy is missing later additions, never in conflict with them.
Parties that fetch artifacts at runtime **SHOULD** follow standard HTTP
caching semantics, revalidating a cached copy once its `max-age` expires (see
[Hosting](#hosting)); refresh frequency is therefore controlled by the
publisher. Parties that consume artifacts at build time pick up amendments on
their own release cadence. An exceptional breaking backport
is announced through the breaking-change notice process and enforced at
request time by the amended contract; it invalidates earlier copies only
because the release was defective as published.

A Business or Platform that selects `ucp.version` `D` **MUST** declare version
`D` on every `dev.ucp.*` service, capability, and extension entry in its
profile. A Platform that encounters a `dev.ucp.*` entry whose `version`
differs from the profile's `ucp.version` **MUST** reject that entry — treated
as not present and never activated — and **MAY** continue with the remaining
entries. An older release is selected only through a separate
`supported_versions` leaf profile whose own `ucp.version` is that older release
date (see [Protocol Version](#protocol-version)). Payment-handler versions are
controlled by their authors: UCP defines the shared declaration structure but
currently no concrete handler, so no handler version is constrained to `D`.
Declaring `version` `D` does not change negotiation: `dev.ucp.*`
capabilities and extensions are still selected by exact-version intersection (see
[Capability Versions](#capability-versions)).

#### Third-party extensions (`com.{vendor}.*`, `org.{org}.*`)

Third-party capabilities version independently of `ucp.version`: their authors
control both the version and the release cadence. The common form is an
**extension** over one or more UCP-defined root capabilities. A third-party
extension:

- declares `extends` over one or more UCP-defined root capabilities, composed
    via `allOf` (see [Extension Schema Pattern](#extension-schema-pattern));
- uses the UCP-defined services and transport bindings selected by
    `ucp.version`; and
- advertises exact extension versions in Business and Platform profiles and is
    negotiated by exact-version intersection like every capability.

A third-party extension's version is never tied to `ucp.version`. The author
declares the UCP releases and capability versions the extension needs through
`requires` (see [Version Requirements](#version-requirements)); those ranges
verify compatibility with the versions a profile selects, they do not select
versions.

## Glossary

For definitions of acronyms and terms used throughout the UCP specification, see the [Glossary](glossary.md).
