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

`ask` draws on public store information and on resources the caller can address
by a GID it holds — products and variants, and optionally a cart or checkout.
Questions that require a buyer's private account data, such as order history,
are out of scope for this version.

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
a GID for, such as a cart or checkout. For resources like a cart or checkout, a
business **MAY** accept the held GID as a bearer reference — possessing it is
sufficient to ask about that resource, with no separate authentication. Access is
otherwise the business's to govern: it **MAY** require authentication to reach a
given resource (a gated catalog, for example).

## Conversation

A business **MAY** support multi-turn conversations by returning a `conversation`
GID in its response. When a platform replays that GID on a follow-up `ask`, the
business continues that conversation, and follow-up questions build on the prior
turns. Omitting `conversation` starts a new one. The `conversation` GID is
opaque: platforms **MUST NOT** parse or construct it, and **MUST** replay only a
value the business returned.

A business that returns a `conversation` GID **SHOULD** retain the conversation
history it represents so a follow-up `ask` with the same GID builds on it; the
retention policy is set by the business. If a provided GID cannot be resolved,
the business **SHOULD** start a new conversation and add an informational
message to `messages` noting that the provided `conversation` GID was not found.

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

`links` is an optional array of [`link.json`](../reference.md) entries pointing
to public resources related to the answer — for example, the policy page it
summarizes, an FAQ that elaborates, or product documentation the platform can
direct the buyer to. Well-known `type` values include `refund_policy`,
`shipping_policy`, `privacy_policy`, `terms_of_service`, and `faq`. Businesses
**MAY** also supply other `type` values and a `title`.

Businesses **SHOULD** include `links` to relevant public resources where such
resources exist.

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
