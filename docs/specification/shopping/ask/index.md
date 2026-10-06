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

# Ask Capability

* **Capability Name:** `dev.ucp.shopping.ask`

## Overview

The Ask capability provides natural-language Q&A about a Business's resources,
policies, and services. A Platform (acting on behalf of the Buyer) asks a
free-form question and receives a text answer with an optional set of related
links. A question may be grounded in specific Business resources (via `ids`) —
a product, a location, an order — or apply to the Business broadly, such as a
return-policy question. `ask` is the open-question complement to UCP's
structured commerce capabilities: it covers open questions and
Business-specific facts and knowledge that may not be directly available
through the structured resources exposed by other capabilities.

`ask` answers; it does not act. A Business **MUST NOT** change the state of any
resource exposed through another UCP capability in response to an `ask`
request — it **MUST NOT** create or modify a cart, checkout, or order, apply a
discount, or reserve inventory. When all or part of a `query` requests an
operation that another capability owns ("add two of these to my cart — do they
come in blue?"), the Business **MUST** return a populated `answer` stating
clearly that `ask` did not perform the requested operation. The Business
**MAY** answer any informational part of the question from data it is permitted
to use under [Access](#access), and **MAY** add an informational message with
code `operation_not_performed` (see
[Messages and Error Handling](#messages-and-error-handling)).

A Platform **MUST NOT** treat the `answer` or the message as evidence that the
operation occurred, or as an instruction to perform it. Whether to invoke the
capability that owns the operation is the Platform's own decision, made from
the Buyer's original request rather than from the `ask` response, and subject
to that capability's authorization, consent, and idempotency requirements (see
[Security Considerations](#security-considerations)).

`ask` draws on public Business information and on any resource the caller can
address by a Global ID (GID) or other identifier it holds, subject to
[Access](#access) (see [Scoping a Question](#scoping-a-question)).

Typical use cases:

* Product questions — fit, materials, compatibility, comparisons.
* Policy questions — returns, shipping, warranty, refunds.
* FAQ / how-to — store hours, shipping timelines, accepted payment methods.
* Clarification about a specific resource, grounded via `ids` — an item before
  purchase, parking or accessibility at a location, the cancellation terms of
  a booking.

## Operation

| Operation | Description |
| :--- | :--- |
| **Ask** | Ask a natural-language question; receive an answer with an optional set of related links. |

### Request

{{ extension_schema_fields('ask.json#/$defs/ask_request', 'shopping/ask') }}

### Response

{{ extension_schema_fields('ask.json#/$defs/ask_response', 'shopping/ask') }}

## Scoping a Question

A request carries a natural-language `query` and, optionally, a set of `ids`
identifying the resources the question is about. With `ids`, the answer is
grounded in specific resources ("is this washable?", "does this location have
parking?"); without them, it applies to the Business broadly ("what is your
return policy?").

`ids` is **optional** and may reference any resource the Business holds — a
product or variant, a location, a cart, an order, a booking. A Business
**SHOULD** accept its own GIDs, unless its access policy for a resource says
otherwise (see [Access](#access)), and **MAY** also accept recognized
secondary identifiers such as a SKU, a handle, or a URL. A GID self-describes
to the Business that issued it, so a Platform can send one as an opaque
grounding reference. A Business that does not recognize an identifier, or
declines to use it, still answers what it can and **MAY** note the unresolved
reference with an informational message (see
[Messages and Error Handling](#messages-and-error-handling)).

**Future direction.** A later version may add an `attachments` array — for
example, an image — for multimodal grounding, such as asking about a product
from a photo.

## Access

What a Business may reveal through `ask` depends on the access it grants the
current request. `ask` may draw on public information and, when authorized, on
personalized or protected data — including data also represented by other UCP
capabilities. Authorization never changes the read-only boundary of `ask`:
regardless of the credential presented, a Business **MUST NOT** change the
state of any resource exposed through another UCP capability in response to
`ask`. Any such state change requires a separate request to the capability
that owns the operation. Using protected data in an answer does not make the
answer authoritative over the capability that represents it (see
[Answer](#answer)).

* **Public** — with no credential, `ask` answers from public Business
  information and public resources.
* **Resource reference** — an identifier in `ids` grounds the question in a
  specific resource. Before using a protected resource — a cart or checkout,
  for example — a Business **MUST** apply its normal access policy for that
  resource. Depending on that policy, the Business **MAY** treat possession of
  the identifier as sufficient, require an additional credential, or decline
  to use the resource in its answer (see
  [Messages and Error Handling](#messages-and-error-handling)).
* **Authenticated Buyer** — when the caller presents a user identity token the
  Business recognizes
  ([user-authenticated access](../../common/identity-linking/index.md#access-levels);
  see [Scopes](#scopes)), the Business **MAY** return personalized answers
  permitted by its policy — member pricing, entitlements, gated availability,
  or information derived from protected resources. This tier is the
  `dev.ucp.shopping.ask:read` scope.

The `dev.ucp.shopping.ask:read` scope permits personalized `ask` responses; it
is not a blanket entitlement to all of a Buyer's data. The Business remains
responsible for authorizing every protected resource and every item of
information it uses in an answer.

## Conversation

A business **MAY** support multi-turn conversations by returning a `conversation`
in its response — an object with an opaque `id` and an optional `expires_at`.
When a platform replays that `conversation` on a follow-up `ask`, the business
continues it, and follow-up questions build on the prior turns. Omitting
`conversation` starts a new one. The `id` is opaque: platforms **MUST NOT** parse
or construct it, and **MUST** replay only a value the business returned.

A business that returns a `conversation` **SHOULD** retain the history it
represents until `expires_at` — or per its own policy when `expires_at` is
omitted — so a follow-up with the same `id` builds on it. If a provided `id`
cannot be resolved, the business **SHOULD** start a new conversation and add an
informational message to `messages` noting that the provided `conversation` was
not found.

A Platform **SHOULD** include an idempotency key on every request that carries
a `conversation`, so a retried turn returns the earlier answer rather than
appending a duplicate — as `Idempotency-Key` over [REST](rest.md#http-headers),
as `meta["idempotency-key"]` over [MCP](mcp.md#request-metadata). A Business
that recognizes a duplicate by its key **MUST NOT** append a second turn.

{{ extension_schema_fields('ask.json#/$defs/conversation', 'shopping/ask') }}

## Answer

The answer is free-form content authored by the Business. A Business **MUST**
include `plain` — the answer as plain text — in every `answer`, and **MAY**
additionally include `markdown` or `html` as alternative encodings of the same
answer. `plain` is the universal fallback: a Platform **MAY** render a richer
encoding it supports and can vouch for, and otherwise renders `plain`,
ignoring any encoding it does not recognize. An `answer` without `plain` is
schema-invalid and is rejected like any other invalid payload.

An answer is indicative, not authoritative. Prices, availability, totals, taxes,
fulfillment estimates, and policy terms stated in an `answer` are not
commitments. Where an `answer` conflicts with the representation returned by the
capability that owns the resource — `catalog`, `cart`, `checkout`, `order`, or
`booking`, for example — that representation is authoritative and the Platform
**MUST** prefer it (see
[Relationship to Structured Capabilities](#relationship-to-structured-capabilities)).
A Platform **MUST NOT** treat an `answer` as the binding disclosure for a
safety, allergen, or regulatory claim.

To keep answers useful and trustworthy, a Business **SHOULD**:

* keep the answer to what fits in conversation and link to the resource — a
  size chart, a compatibility table — rather than inlining it;
* link to the authoritative source behind an answer (a policy page, the product
  itself) so the Platform can point the Buyer there;
* carry any safety, allergen, or regulatory notice as a warning with
  `presentation: "disclosure"` rather than only in the answer text; and
* state clearly when a question can't be answered.

{{ extension_schema_fields('ask.json#/$defs/ask_response/properties/answer', 'shopping/ask') }}

## Context

Market and localization context for the question — country, language, intent,
and similar. These are provisional signals: implementations **MAY** ignore or
down-rank them when higher-confidence inputs are available. The resources the
question is *about* live in `ids`, not in `context`.

{{ schema_fields('types/context', 'shopping/ask') }}

## Signals

Environment data provided by the platform to support authorization and abuse
prevention. Signal values **MUST NOT** be buyer-asserted claims. See
[Signals](../../overview/index.md#signals) for details and privacy requirements.

{{ schema_fields('types/signals', 'shopping/ask') }}

## Attribution

Platform-provided referral and conversion-event context — campaign IDs, click
identifiers, and source/medium markers communicated by the platform. See
[Attribution](../../overview/index.md#attribution) for details and consent requirements.

{{ schema_fields('types/attribution', 'shopping/ask') }}

## Links

`links` enumerate the entities the answer mentions — a product, a location, an
order, a policy page — where an addressable resource or page exists for them.
A Business **SHOULD** return one link per such entity, so the Platform can tie
the answer to the resources it names. A Platform **MAY** use a link for
follow-up.

A link carries:

* `title` — display text that **SHOULD** capture the resource the link points to
  as it appears in the `answer` (the product, policy, or page the Buyer just
  heard about), so the Platform can tie the link back to the text it rendered.
* `url` — the page the Platform can direct the Buyer to. Required on every
  link; it is the fallback when a link carries no `id` or the `id` is not
  resolved.
* `id` — when the link refers to an addressable UCP resource, the Business
  **SHOULD** include the resource's GID alongside the `url`, unless the
  resource has no UCP identifier — a policy page, for example — in which case
  `id` is omitted. A Platform **MAY** use the GID, on a best-effort basis, to
  match the resource to an appropriate operation exposed by a capability it
  has negotiated with the Business. UCP does not prescribe how a Platform
  performs that match and does not guarantee that every GID resolves; the
  `url` remains the fallback. What a Platform does with a matched resource is
  its own decision (see [Security Considerations](#security-considerations)).

Each link also carries a `type` classifier. Well-known values are
`refund_policy`, `shipping_policy`, `privacy_policy`, `terms_of_service`, and
`faq`; a Business **MAY** supply other `type` values (a product, a size guide, a
store-locator page). `type` is a display hint, not a routing discriminator:
matching an `id` to an operation does not depend on it. A Platform **SHOULD**
handle a `type` it does not recognize gracefully — display the link by its
`title`, or omit it — rather than reject the response.

{{ schema_fields('types/link', 'shopping/ask') }}

## Relationship to Structured Capabilities

`ask` and UCP's structured capabilities — `catalog`, `cart`, `checkout`,
`order`, `booking`, and others — are independently adoptable: a Business
**MAY** offer `ask` alone or alongside any of them, and advertising one does
not imply another. `ask` is not coupled to `catalog` or to any single resource
domain: a question may be grounded in, and an answer may link to, resources
from any domain the Business exposes.

The two serve different needs. `ask` returns indicative, human-readable
content; a structured capability returns the machine-readable representation
of a resource, which is authoritative over the `answer` (see
[Answer](#answer)).

## Messages and Error Handling

A Business **MAY** include a `messages` array of errors, warnings, or
informational notes about the answer — for example, a warning that it draws on
a regional policy variant, or a note that the question was re-scoped. The
`answer` remains the primary response.

| Type | When to Use | Example Codes |
| :--- | :--- | :--- |
| `error` | Business-level errors — e.g., a question requires a scope the caller's token lacks | `insufficient_scope` |
| `warning` | Important conditions or disclaimers about the answer | `disclaimer` |
| `info` | Additional context or non-blocking notes — e.g., a referenced resource could not be resolved, or the `query` asked for an operation `ask` does not perform | `not_found`, `operation_not_performed`, `promotion` |

Warnings with `presentation: "disclosure"` carry notices the platform **MUST NOT**
hide or dismiss — for example, a safety, allergen, or regulated disclosure. See
[Warning Presentation](../checkout/index.md#warning-presentation) for the rendering
contract.

### Well-Known Codes

Message codes are open strings — the shared message schemas accept any code —
and well-known codes carry standardized meaning. `ask` defines one:

| Type | Code | Meaning |
| :--- | :--- | :--- |
| `info` | `operation_not_performed` | The `query` requested an operation outside the read-only boundary of `ask`, and the Business performed no corresponding state change. |

The message reports that nothing changed. It does not instruct the Platform to
invoke another capability, and it supplements — never replaces — the `answer`
stating that `ask` did not perform the operation (see [Overview](#overview)).

For example, a Buyer asks: "Add three more widgets and tell me whether that
qualifies for the volume discount." The `query` mixes an operation `ask` does
not perform (adding to the cart) with a question it can answer (the discount
condition). The Business answers the question and states that it did not
change the cart, repeating that fact as an informational message. It performs
no cart operation, and nothing in the response directs the Platform to a
capability that would.

<!-- ucp:example schema=shopping/ask def=ask_response op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.ask": [
        {"version": "{{ ucp_version }}"}
      ]
    }
  },
  "answer": {
    "plain": "I haven't added anything to your cart; it is unchanged. Orders of 10 or more widgets qualify for the volume discount, which takes 15% off each widget."
  },
  "messages": [
    {
      "type": "info",
      "code": "operation_not_performed",
      "content": "No cart operation was performed."
    }
  ]
}
```

### Message (Error)

{{ schema_fields('types/message_error', 'shopping/ask') }}

### Message (Warning)

{{ schema_fields('types/message_warning', 'shopping/ask') }}

### Message (Info)

{{ schema_fields('types/message_info', 'shopping/ask') }}

## Security Considerations

`ask` carries natural language across the party boundary in both directions:
a Buyer's question reaches the Business's model, and the Business's answer
reaches the Platform's. Both are untrusted content and **MUST** be treated as
data, never as instructions.

A Business **MUST** treat `query` as untrusted input. It **MUST NOT** allow the
question to alter its own instructions or its authorization decisions, and
**MUST** enforce the tiers in [Access](#access) outside the model: what a
caller may see is decided by the credential presented, never by what the
question says. Authorization **MUST NOT** depend on model behavior.

A Platform **MUST** treat the response as content authored by the Business —
an answer and, where present, suggestions about what to do next. It is input
to the Platform's own decisions, not directions to carry out. A Platform
**MUST NOT** act on text in `answer` or on identifiers in `links[].id` as if
they were instructions; whether and how to act on them — resolving an
identifier through a negotiated capability, adding an item to a cart,
directing the Buyer to a `url` — is the Platform's decision, made under its
own authorization and Buyer-consent rules, exactly as for any other
Business-authored content such as a product description. A Platform
**SHOULD** present an `answer` as content from the Business, attributed and
distinguishable from its own output.

## Scopes

The Ask capability defines the following well-known scope for user-authenticated
access:

| Scope | Description |
| :--- | :--- |
| `dev.ucp.shopping.ask:read` | Ask on behalf of the authenticated Buyer — personalized answers reflecting member pricing, entitlements, or gated availability. |

Scope declaration, derivation, and rules for extending this set with custom
scopes are defined in
[Identity Linking — Scopes](../../common/identity-linking/index.md#scopes).

## Transport Bindings

The capability is bound to specific transport protocols:

* [REST Binding](rest.md): RESTful API mapping (`POST /ask`).
* [MCP Binding](mcp.md): Model Context Protocol mapping via JSON-RPC (`ask_business` tool).
