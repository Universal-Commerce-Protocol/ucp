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

The Ask capability provides natural-language Q&A about a business's products,
policies, and services. A platform (acting on behalf of the buyer) asks a
free-form question and receives a text answer with an optional set of related
links. A question may target specific products (via `ids`) or apply to the
storefront broadly, such as a return-policy question. `ask` is the open-question
complement to UCP's structured shopping capabilities: a question that maps to a
dedicated operation is owned by that capability; `ask` covers open questions and
business-specific facts and knowledge that may not be directly available through
the structured resources exposed by other capabilities.

`ask` draws on public business information and on resources the caller can address
by a GID it holds — products and variants, and optionally a cart or checkout.

Typical use cases:

* Product questions — fit, materials, compatibility, comparisons.
* Policy questions — returns, shipping, warranty, refunds.
* FAQ / how-to — store hours, shipping timelines, accepted payment methods.
* Pre-purchase clarification about a specific item, grounded via `ids`.

## Operation

| Operation | Description |
| :--- | :--- |
| **Ask** | Ask a natural-language question; receive an answer with an optional set of related links. |

### Request

{{ extension_schema_fields('ask.json#/$defs/ask_request', 'ask') }}

### Response

{{ extension_schema_fields('ask.json#/$defs/ask_response', 'ask') }}

## Scoping a Question

A request carries a natural-language `query` and, optionally, a set of `ids`
identifying the resources the question is about. With `ids`, the answer can be
grounded against specific items ("is this washable?"); without them, it applies
to the storefront broadly ("what is your return policy?").

`ids` is **optional**. A business **SHOULD** accept the identifiers that ground a
question, with product and variant IDs as the recommended minimum; it **MAY**
also accept secondary identifiers (SKU, handle, URL) and other resources it holds
a GID for, such as a cart or checkout. How a business authorizes access to those
resources is described under [Access](#access).

**Future direction.** A later version may add an `attachments` array — for
example, an image — for multimodal grounding, such as asking about a product
from a photo.

## Access

What a business may reveal through `ask` depends on the credential the caller
presents:

* **Public** — with no credential, `ask` answers from public business information
  and public catalog items (product and variant IDs).
* **Resource reference** — a GID the caller holds for a specific resource, such
  as a cart or checkout, is itself a bearer reference: where a business honors
  it, possessing the GID is sufficient to ask about that resource, with no
  separate authentication.
* **Business posture** — a business **MAY** require a stronger credential than a
  bare GID to reach a given resource (a gated catalog, for example). The required
  posture is the business's to set.
* **Authenticated user** — when the caller presents a bearer token the business
  recognizes for user authentication (see [Scopes](#scopes) and
  [Identity Linking](../identity-linking.md)), the business **MAY** return
  personalized results — member pricing, entitlements, or gated availability.
  This tier is the `dev.ucp.shopping.ask:read` scope.

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

{{ extension_schema_fields('ask.json#/$defs/conversation', 'ask') }}

## Answer

The answer is free-form content authored by the business, in one or more
formats — plain text, HTML, or Markdown. To keep answers useful and
trustworthy, businesses **SHOULD**:

* indicate how authoritative or provisional an answer is;
* link to the related and authoritative sources behind it, so the platform can
  point the buyer there; and
* state clearly when a question can't be answered.

{{ schema_fields('types/description', 'ask') }}

## Context

Market and localization context for the question — country, language, intent,
and similar. These are provisional signals: implementations **MAY** ignore or
down-rank them when higher-confidence inputs are available. The items the
question is *about* live in `ids`, not in `context`.

{{ schema_fields('types/context', 'ask') }}

## Signals

Environment data provided by the platform to support authorization and abuse
prevention. Signal values **MUST NOT** be buyer-asserted claims. See
[Signals](../overview.md#signals) for details and privacy requirements.

{{ schema_fields('types/signals', 'ask') }}

## Attribution

Platform-provided referral and conversion-event context — campaign IDs, click
identifiers, and source/medium markers communicated by the platform. See
[Attribution](../overview.md#attribution) for details and consent requirements.

{{ schema_fields('types/attribution', 'ask') }}

## Links

`links` are an array of addressable references to the resources the answer
names. The array is optional in the schema, but a business **SHOULD** return a
link for each resource the answer references, so the platform can act on the
response provided to the buyer.

A link carries:

* `title` — display text that **SHOULD** capture the resource the link points to
  as it appears in the `answer` (the product, policy, or page the buyer just
  heard about), so the platform can tie the link back to the text it rendered.
* `url` — the page the platform can direct the buyer to. Required on every link.
* `id` — when the link points to an addressable UCP resource (a product or
  variant the answer recommends, say), the business **SHOULD** include the
  resource's `id` (a GID) alongside the `url`. The `url` is for display; the `id`
  lets the platform act on the resource through the capability that owns it —
  resolve it in `catalog`, add it to a `cart` — without re-deriving it from the
  answer text. Omit `id` for resources without a UCP identifier, such as a
  policy page.

Each link also carries a `type` classifier. Well-known values are
`refund_policy`, `shipping_policy`, `privacy_policy`, `terms_of_service`, and
`faq`; a business **MAY** supply other `type` values (a product, a size guide, a
store-locator page).

{{ schema_fields('types/link', 'ask') }}

## Relationship to Catalog

`ask` and `catalog` are independent capabilities that **MAY** be adopted
separately. A business **SHOULD** offer them together where possible: `catalog`
lets a platform find and resolve products, and `ask` answers the open-ended
questions buyers have about them — together covering a complete pre-purchase
path.

## Messages and Error Handling

Ask responses **MAY** include a `messages` array of errors, warnings, or
informational notes about the answer — for example, a warning that it draws on
a regional policy variant, or a note that the question was re-scoped. The
`answer` remains the primary response.

| Type | When to Use | Example Codes |
| :--- | :--- | :--- |
| `error` | Business-level errors — e.g., a question requires a scope the caller's token lacks | `insufficient_scope` |
| `warning` | Important conditions or disclaimers about the answer | `disclaimer` |
| `info` | Additional context or non-blocking notes — e.g., a referenced item could not be resolved | `not_found`, `promotion` |

Warnings with `presentation: "disclosure"` carry notices the platform **MUST NOT**
hide or dismiss — for example, a safety, allergen, or regulated disclosure. See
[Warning Presentation](../checkout.md#warning-presentation) for the rendering
contract.

### Message (Error)

{{ schema_fields('types/message_error', 'ask') }}

### Message (Warning)

{{ schema_fields('types/message_warning', 'ask') }}

### Message (Info)

{{ schema_fields('types/message_info', 'ask') }}

## Scopes

The Ask capability defines the following well-known scope for user-authenticated
access:

| Scope | Description |
| :--- | :--- |
| `dev.ucp.shopping.ask:read` | Ask on behalf of the authenticated user — personalized answers reflecting member pricing, entitlements, or gated availability. |

Scope declaration, derivation, and rules for extending this set with custom
scopes are defined in
[Identity Linking — Scopes](../identity-linking.md#scopes).

## Transport Bindings

The capability is bound to specific transport protocols:

* [REST Binding](rest.md): RESTful API mapping (`POST /ask`).
* [MCP Binding](mcp.md): Model Context Protocol mapping via JSON-RPC (`ask_business` tool).
