# Ask Capability

- **Capability Name:** `dev.ucp.common.ask`

## Overview

The Ask capability provides natural-language Q&A about a Business's resources, policies, and services. A Platform (acting on behalf of the Buyer) asks a free-form question and receives a text answer with an optional set of related links. A question may be grounded in specific Business resources (via `ids`) — a product, a location, an order, a booking — or apply to the Business broadly, such as a return-policy question. `ask` is the open-question complement to UCP's structured commerce capabilities: it covers open questions and Business-specific facts and knowledge that may not be directly available through the structured resources exposed by other capabilities.

Ask is a Common capability. It is bound to the `dev.ucp.common` service rather than to a vertical one, and the same capability answers questions about resources from every vertical the Business exposes — shopping, lodging, or any other (see [Relationship to Structured Capabilities](#relationship-to-structured-capabilities)).

`ask` answers; it does not act. A Business **MUST NOT** change the state of any resource exposed through another UCP capability or extension in response to an `ask` request. For example, an `ask` request does not create or modify a cart, checkout, order, or booking; apply a discount; or reserve inventory. When all or part of a `query` requests an operation that another capability or extension owns ("add two of these to my cart — do they come in blue?"), the Business **MUST** return a populated `answer` stating clearly that `ask` did not perform the requested operation. The Business **MAY** answer any informational part of the question from data it is permitted to use under [Access](#access), and **MAY** add an informational message with code `operation_not_performed` (see [Messages and Error Handling](#messages-and-error-handling)).

A Platform **MUST NOT** treat the `answer` or the message as evidence that the operation occurred, or as an instruction to perform it. Whether to invoke the capability or extension that owns the operation is the Platform's own decision, made from the Buyer's original request rather than from the `ask` response, and subject to the authorization, consent, and idempotency requirements of that capability or extension (see [Security Considerations](#security-considerations)).

`ask` draws on public Business information and on any resource the caller can address by a Global ID (GID) or other identifier it holds, subject to [Access](#access) (see [Scoping a Question](#scoping-a-question)).

Typical use cases:

- Product questions — fit, materials, compatibility, comparisons.
- Policy questions — returns, shipping, warranty, refunds.
- FAQ / how-to — store hours, shipping timelines, accepted payment methods.
- Clarification about a specific resource, grounded via `ids` — an item before purchase, parking or accessibility at a location, the cancellation terms of a booking.

## Operation

| Operation | Description                                                                               |
| --------- | ----------------------------------------------------------------------------------------- |
| **Ask**   | Ask a natural-language question; receive an answer with an optional set of related links. |

### Request

| Name         | Type                                               | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | -------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| query        | string                                             | **Required** | Natural-language question.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| conversation | object                                             | Optional     | Provide a conversation to continue it on a follow-up; omit to start a new one.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ids          | Array[string]                                      | Optional     | Optional identifiers that ground the question in any Business resource. A Business SHOULD accept its own Global IDs (GIDs) and MAY accept recognized secondary identifiers such as SKU, handle, or URL. GIDs self-describe to the Business; a Platform may send them as opaque grounding references. Examples include a product, location, cart, order, or booking.                                                                                                                                                                                                                                                                                                     |
| context      | [Context](/draft/specification/reference/#context) | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals      | [Signals](/draft/specification/reference/#signals) | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |

### Response

| Name         | Type                                                        | Requirement  | Description                                                                                                                                                                                                                                                                         |
| ------------ | ----------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | UCP Ask Response Schema                                     | **Required** | UCP metadata for ask responses.                                                                                                                                                                                                                                                     |
| answer       | object                                                      | **Required** | Answer provided by the Business. Plain text is required; Markdown and HTML are optional alternative encodings.                                                                                                                                                                      |
| conversation | object                                                      | Optional     | Business-issued conversation for multi-turn continuation. When returned, the business SHOULD retain its history until `expires_at` (or per its own policy) so a follow-up with the same `id` builds on it. An unresolved `id` starts a new conversation and is noted in `messages`. |
| links        | Array\[[Link](/draft/specification/reference/#link)\]       | Optional     | Optional links and references related to the answer. When a link refers to an addressable UCP resource, the Business SHOULD include its GID in the link's `id`.                                                                                                                     |
| messages     | Array\[[Message](/draft/specification/reference/#message)\] | Optional     | Errors, warnings, or informational messages about the answer or its grounding.                                                                                                                                                                                                      |

## Scoping a Question

A request carries a natural-language `query` and, optionally, a set of `ids` identifying the resources the question is about. With `ids`, the answer is grounded in specific resources ("is this washable?", "does this location have parking?"); without them, it applies to the Business broadly ("what is your return policy?").

`ids` is **optional** and may reference any resource the Business holds — a product or variant, a location, a cart, an order, a booking. A Business **SHOULD** accept its own GIDs, unless its access policy for a resource says otherwise (see [Access](#access)), and **MAY** also accept recognized secondary identifiers such as a SKU, a handle, or a URL. A GID self-describes to the Business that issued it, so a Platform can send one as an opaque grounding reference. A Business that does not recognize an identifier, or declines to use it, still answers what it can and **MAY** note the unresolved reference with an informational message (see [Messages and Error Handling](#messages-and-error-handling)).

**Future direction.** A later version may add an `attachments` array — for example, an image — for multimodal grounding, such as asking about a product from a photo.

## Access

What a Business may reveal through `ask` depends on the access it grants the current request. `ask` may draw on public information and, when authorized, on personalized or protected data — including data also represented by other UCP capabilities. Authorization never changes the read-only boundary of `ask`: regardless of the credential presented, a Business **MUST NOT** change the state of any resource exposed through another UCP capability in response to `ask`. Any such state change requires a separate request to the capability that owns the operation. Using protected data in an answer does not make the answer authoritative over the capability that represents it (see [Answer](#answer)).

- **Public** — with no credential, `ask` answers from public Business information and public resources.
- **Resource reference** — an identifier in `ids` grounds the question in a specific resource. Before using a protected resource — a cart or checkout, for example — a Business **MUST** apply its normal access policy for that resource. Depending on that policy, the Business **MAY** treat possession of the identifier as sufficient, require an additional credential, or decline to use the resource in its answer (see [Messages and Error Handling](#messages-and-error-handling)).
- **Authenticated Buyer** — when the caller presents a user identity token the Business recognizes ([user-authenticated access](http://ucp.dev/draft/specification/common/identity-linking/#access-levels); see [Scopes](#scopes)), the Business **MAY** return personalized answers permitted by its policy — member pricing, entitlements, gated availability, or information derived from protected resources. This tier is the `dev.ucp.common.ask:read` scope.

The `dev.ucp.common.ask:read` scope permits personalized `ask` responses; it is not a blanket entitlement to all of a Buyer's data. The Business remains responsible for authorizing every protected resource and every item of information it uses in an answer.

## Conversation

A Business **MAY** support multi-turn conversations by returning a `conversation` in its response — an object with an opaque `id` and an optional `expires_at`. When a Platform replays that `conversation` on a follow-up `ask`, the Business continues it where its access policy permits, and follow-up questions build on the prior turns the current request is permitted to use. Omitting `conversation` starts a new one. The `id` is opaque: a Platform **MUST NOT** parse or construct it, and **MUST** replay only a value the Business returned.

A Business that returns a `conversation` **SHOULD** retain the history it represents until `expires_at` — or per its own policy when `expires_at` is omitted — so a follow-up with the same `id` builds on it. If a provided `id` cannot be resolved, the Business **SHOULD** start a new conversation and add an informational message to `messages` noting that the provided `conversation` was not found.

Each follow-up is a new request for authorization. A Business **MUST** apply its access policy ([Access](#access)) using the credential presented with that request, if any. The `id` carries context, not authority: a Business **MUST NOT** treat a replayed `conversation` as carrying forward the access granted on an earlier turn or as expanding what the current caller may access, and **MUST NOT** use or disclose retained context that the current request is not authorized to access.

Where its access policy permits, a Business **MAY** continue a conversation on possession of the `id` alone — an anonymous conversation over public information, for example, as in the [multi-turn example](http://ucp.dev/draft/specification/common/ask/rest/#multi-turn-example). If the authorization of a follow-up differs from an earlier turn's — a credential presented on one turn but not the next, for example — the Business **MAY** continue with only the context the current request is permitted to use, or decline the continuation under its access policy (see [Messages and Error Handling](#messages-and-error-handling)).

A Platform **SHOULD** include an idempotency key on every request that carries a `conversation`, so a retried turn returns the earlier answer rather than appending a duplicate — as `Idempotency-Key` over [REST](http://ucp.dev/draft/specification/common/ask/rest/#http-headers), as `meta["idempotency-key"]` over [MCP](http://ucp.dev/draft/specification/common/ask/mcp/#request-metadata). A Business that recognizes a duplicate by its key **MUST NOT** append a second turn.

| Name       | Type   | Requirement  | Description                                                                         |
| ---------- | ------ | ------------ | ----------------------------------------------------------------------------------- |
| id         | string | **Required** | Opaque, business-issued conversation identifier.                                    |
| expires_at | string | Optional     | RFC 3339 timestamp after which the conversation context may be discarded. Optional. |

## Answer

The answer is free-form content authored by the Business. A Business **MUST** include `plain` — the answer as plain text — in every `answer`, and **MAY** additionally include `markdown` or `html` as alternative encodings of the same answer. `plain` is the universal fallback: a Platform **MAY** render a richer encoding it supports and can vouch for, and otherwise renders `plain`, ignoring any encoding it does not recognize. An `answer` without `plain` is schema-invalid and is rejected like any other invalid payload.

An answer is indicative, not authoritative. Prices, availability, totals, taxes, fulfillment estimates, and policy terms stated in an `answer` are not commitments. Where an `answer` conflicts with the representation returned by the capability that owns the resource — `catalog`, `cart`, `checkout`, `order`, or `booking`, for example — that representation is authoritative and the Platform **MUST** prefer it (see [Relationship to Structured Capabilities](#relationship-to-structured-capabilities)). A Platform **MUST NOT** treat an `answer` as the binding disclosure for a safety, allergen, or regulatory claim.

To keep answers useful and trustworthy, a Business **SHOULD**:

- keep the answer to what fits in conversation and link to the resource — a size chart, a compatibility table — rather than inlining it;
- link to the authoritative source behind an answer (a policy page, the product itself) so the Platform can point the Buyer there;
- carry any safety, allergen, or regulatory notice as a warning with `presentation: "disclosure"` rather than only in the answer text; and
- state clearly when a question can't be answered.

Answer provided by the Business. Plain text is required; Markdown and HTML are optional alternative encodings.

| Name     | Type   | Requirement  | Description                                                                                                                                                               |
| -------- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| plain    | string | **Required** | Plain text content.                                                                                                                                                       |
| html     | string | Optional     | HTML-formatted content. Security: Platforms MUST sanitize before rendering—strip scripts, event handlers, and untrusted elements. Treat all rich text as untrusted input. |
| markdown | string | Optional     | Markdown-formatted content.                                                                                                                                               |

## Context

Market and localization context for the question — country, language, intent, and similar. These are provisional signals: a Business **MAY** ignore or down-rank them when higher-confidence inputs are available. The resources the question is *about* live in `ids`, not in `context`.

| Name            | Type                                                                                | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --------------- | ----------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| address_country | string                                                                              | Optional    | The country, as a 2-letter ISO 3166-1 alpha-2 code (e.g. "US"). A 3-letter alpha-3 code or full country name MAY also be used.                                                                                                                                                                                                                                                                                                                                     |
| address_region  | string                                                                              | Optional    | The first-level administrative region within the country (e.g. a state or province such as California).                                                                                                                                                                                                                                                                                                                                                            |
| postal_code     | string                                                                              | Optional    | The postal code (e.g. "94043").                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| location        | string                                                                              | Optional    | Stable, opaque identifier for a Location in the Business's namespace. This provisional, non-binding hint is distinct from the Buyer's locality. The operation specification or an active capability/extension defines its effects. A common example in retail shopping is the default home store ID selected and saved by the user when purchasing groceries.                                                                                                      |
| intent          | string                                                                              | Optional    | Background context describing buyer's intent (e.g., 'looking for a gift under $50', 'need something durable for outdoor use'). Informs relevance, recommendations, and personalization.                                                                                                                                                                                                                                                                            |
| language        | string                                                                              | Optional    | Preferred language for content. Use IETF BCP 47 language tags (e.g., 'en', 'fr-CA', 'zh-Hans'). For REST, equivalent to Accept-Language header—platforms SHOULD fall back to Accept-Language when this field is absent; when provided, overrides Accept-Language. Businesses MAY return content in a different language if unavailable.                                                                                                                            |
| currency        | string                                                                              | Optional    | Preferred currency (ISO 4217, e.g., 'EUR', 'USD'). Businesses determine presentment currency from context and authoritative signals; this hint MAY inform selection in multi-currency markets. Also serves as the denomination for price filter values — platforms SHOULD include this field when sending price filters. Response prices include explicit currency confirming the resolution.                                                                      |
| eligibility     | Array\[[Reverse Domain Name](/draft/specification/reference/#reverse-domain-name)\] | Optional    | Buyer claims about eligible benefits such as loyalty membership, payment instrument perks, and similar. Recognized claims MAY inform the Business response (e.g., member-only product availability, adjusted pricing in catalog, provisional discounts at cart or checkout). Businesses MUST ignore unrecognized values without error. Values MUST use reverse-domain naming (e.g., 'com.example.loyalty_gold', 'org.school.student') and MUST be non-identifying. |
| payment         | Array[object]                                                                       | Optional    | Buyer-preferred payment handlers in priority order (most preferred first). Each entry names a handler advertised in the Business profile's `ucp.payment_handlers`, optionally narrowed to preferred instrument types. The Business SHOULD use it to preselect or prioritize the handler (and type, when given) and MAY ignore unavailable or ineligible entries; unrecognized values MUST be ignored without error.                                                |

## Signals

Environment data provided by the Platform to support authorization and abuse prevention. Signal values **MUST NOT** be buyer-asserted claims. See [Signals](http://ucp.dev/draft/specification/overview/#signals) for details and privacy requirements.

| Name               | Type   | Requirement | Description                                    |
| ------------------ | ------ | ----------- | ---------------------------------------------- |
| dev.ucp.buyer_ip   | string | Optional    | Client's IP address (IPv4 or IPv6).            |
| dev.ucp.user_agent | string | Optional    | Client's HTTP User-Agent header or equivalent. |

## Links

`links` enumerate the entities the answer mentions — a product, a location, an order, a policy page — where an addressable resource or page exists for them. A Business **SHOULD** return one link per such entity, so the Platform can tie the answer to the resources it names. A Platform **MAY** use a link for follow-up.

A link carries:

- `title` — display text that **SHOULD** capture the resource the link points to as it appears in the `answer` (the product, policy, or page the Buyer just heard about), so the Platform can tie the link back to the text it rendered.
- `url` — the page the Platform can direct the Buyer to. Required on every link; it is the fallback when a link carries no `id` or the `id` is not resolved.
- `id` — when the link refers to an addressable UCP resource, the Business **SHOULD** include the resource's GID alongside the `url`, unless the resource has no UCP identifier — a policy page, for example — in which case `id` is omitted. A Platform **MAY** use the GID, on a best-effort basis, to match the resource to an appropriate operation exposed by a capability it has negotiated with the Business. UCP does not prescribe how a Platform performs that match and does not guarantee that every GID resolves; the `url` remains the fallback. What a Platform does with a matched resource is its own decision (see [Security Considerations](#security-considerations)).

Each link also carries a `type` classifier. Well-known values are `refund_policy`, `shipping_policy`, `privacy_policy`, `terms_of_service`, and `faq`; a Business **MAY** supply other `type` values (a product, a size guide, a store-locator page). `type` is a display hint, not a routing discriminator: matching an `id` to an operation does not depend on it. A Platform **SHOULD** handle a `type` it does not recognize gracefully — display the link by its `title`, or omit it — rather than reject the response.

| Name  | Type   | Requirement  | Description                                                                                                                                                                                                                                                  |
| ----- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| type  | string | **Required** | Type of link. Well-known values: `privacy_policy`, `terms_of_service`, `refund_policy`, `shipping_policy`, `faq`. Consumers SHOULD handle unknown values gracefully by displaying them using the `title` field or omitting the link.                         |
| url   | string | **Required** | The actual URL pointing to the content to be displayed.                                                                                                                                                                                                      |
| title | string | Optional     | Optional display text for the link. When provided, use this instead of generating from type.                                                                                                                                                                 |
| id    | string | Optional     | Optional identifier for the linked resource when it is an addressable UCP resource (for example, a product or variant), so a platform can act on it through the capability that owns it. Omit for resources without a UCP identifier, such as a policy page. |

## Relationship to Structured Capabilities

`ask` and UCP's structured capabilities — `catalog`, `cart`, `checkout`, `order`, `booking`, and others — are independently adoptable: a Business **MAY** offer `ask` alone or alongside any of them, and advertising one does not imply another. `ask` is not coupled to `catalog` or to any single resource domain: a question may be grounded in, and an answer may link to, resources from any domain the Business exposes.

The two serve different needs. `ask` returns indicative, human-readable content; a structured capability returns the machine-readable representation of a resource, which is authoritative over the `answer` (see [Answer](#answer)).

Vertical integration guides map a vertical's concerns onto the capabilities that own them without changing this contract — see [Ask in Shopping](http://ucp.dev/draft/specification/shopping/ask/index.md) for the Shopping vertical.

## Messages and Error Handling

A Business **MAY** include a `messages` array of errors, warnings, or informational notes about the answer — for example, a warning that it draws on a regional policy variant, or a note that the question was re-scoped. The `answer` remains the primary response.

| Type      | When to Use                                                                                                                                                | Example Codes                                       |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `error`   | Business-level errors — e.g., a question requires a scope the caller's token lacks                                                                         | `insufficient_scope`                                |
| `warning` | Important conditions or disclaimers about the answer                                                                                                       | `disclaimer`                                        |
| `info`    | Additional context or non-blocking notes — e.g., a referenced resource could not be resolved, or the `query` asked for an operation `ask` does not perform | `not_found`, `operation_not_performed`, `promotion` |

Warnings with `presentation: "disclosure"` carry notices the Platform **MUST NOT** hide or dismiss — for example, a safety, allergen, or regulated disclosure. See [Warning Presentation](http://ucp.dev/draft/specification/shopping/checkout/#warning-presentation) for the rendering contract.

### Well-Known Codes

Message codes are open strings — the shared message schemas accept any code — and well-known codes carry standardized meaning. `ask` defines one:

| Type   | Code                      | Meaning                                                                                                                               |
| ------ | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `info` | `operation_not_performed` | The `query` requested an operation outside the read-only boundary of `ask`, and the Business performed no corresponding state change. |

The message reports that nothing changed. It does not instruct the Platform to invoke another capability, and it supplements — never replaces — the `answer` stating that `ask` did not perform the operation (see [Overview](#overview)).

For example, a Buyer asks: "Add three more widgets and tell me whether that qualifies for the volume discount." The `query` mixes an operation `ask` does not perform (adding to the cart) with a question it can answer (the discount condition). The Business answers the question and states that it did not change the cart, repeating that fact as an informational message. It performs no cart operation, and nothing in the response directs the Platform to a capability that would.

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.common.ask": [
        {"version": "draft"}
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

| Name         | Type                                                     | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------ | -------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                   | **Required** | **Constant = error**. Message type discriminator.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| code         | [Error Code](/draft/specification/reference/#error-code) | **Required** | Error code identifying the type of error. Standard errors are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| path         | string                                                   | Optional     | RFC 9535 JSONPath to the component the message refers to (e.g., $.line_items[0]).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| content_type | string                                                   | Optional     | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| content      | string                                                   | **Required** | Human-readable message.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| severity     | string                                                   | **Required** | Reflects the resource state and recommended action. 'recoverable': platform can resolve the condition in band, for example by modifying inputs or processing a related Action, and submit a new operation when needed. 'requires_buyer_input': merchant requires information their API doesn't support collecting programmatically (checkout incomplete). 'requires_buyer_review': buyer must authorize before order placement due to policy, regulatory, or entitlement rules. 'unrecoverable': no valid resource exists to act on, retry with new resource or inputs. Errors with 'requires\_*' severity contribute to 'status: requires_escalation'.* *Enum:*\* `recoverable`, `requires_buyer_input`, `requires_buyer_review`, `unrecoverable` |

### Message (Warning)

| Name         | Type                                                         | Requirement  | Description                                                                                                                                                                                                                                         |
| ------------ | ------------------------------------------------------------ | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                       | **Required** | **Constant = warning**. Message type discriminator.                                                                                                                                                                                                 |
| path         | string                                                       | Optional     | RFC 9535 JSONPath to the component the message refers to (e.g., $.line_items[0]).                                                                                                                                                                   |
| code         | [Warning Code](/draft/specification/reference/#warning-code) | **Required** | Warning code identifying the type of warning. Standard codes are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.                                                                 |
| content      | string                                                       | **Required** | Human-readable warning message that MUST be displayed.                                                                                                                                                                                              |
| content_type | string                                                       | Optional     | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                      |
| presentation | string                                                       | Optional     | Rendering contract for this warning. 'notice' (default): platform MUST display, MAY dismiss. 'disclosure': platform MUST display in proximity to the path-referenced component, MUST NOT hide or auto-dismiss. See specification for full contract. |
| image_url    | string                                                       | Optional     | URL to a required visual element (e.g., warning symbol, energy class label).                                                                                                                                                                        |
| url          | string                                                       | Optional     | Reference URL for more information (e.g., regulatory site, registry entry, policy page).                                                                                                                                                            |

### Message (Info)

| Name         | Type                                                   | Requirement  | Description                                                                                                                                                                                    |
| ------------ | ------------------------------------------------------ | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                 | **Required** | **Constant = info**. Message type discriminator.                                                                                                                                               |
| path         | string                                                 | Optional     | RFC 9535 JSONPath to the component the message refers to (e.g., $.line_items[0]).                                                                                                              |
| code         | [Info Code](/draft/specification/reference/#info-code) | Optional     | Info code identifying the type of informational message. Standard codes are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted. |
| content_type | string                                                 | Optional     | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                 |
| content      | string                                                 | **Required** | Human-readable message.                                                                                                                                                                        |

## Security Considerations

`ask` carries natural language across the party boundary in both directions: a Buyer's question reaches the Business's model, and the Business's answer reaches the Platform's. Both are untrusted content and **MUST** be treated as data, never as instructions.

A Business **MUST** treat `query` as untrusted input. It **MUST NOT** allow the question to alter its own instructions or its authorization decisions, and **MUST** enforce the tiers in [Access](#access) outside the model: what a caller may see is decided by the credential presented with the request, never by what the question says or by the `conversation` the request replays (see [Conversation](#conversation)). Authorization **MUST NOT** depend on model behavior.

A Platform **MUST** treat all Business-authored response content, including content contributed by negotiated extensions, as data rather than instructions. A Platform **MUST NOT** allow merely receiving or rendering that content to trigger a capability call or state change.

Whether and how to act on an `answer`, an identifier in `links[].id`, or an extension-defined affordance is the Platform's decision, made under its own authorization and Buyer-consent rules. A Platform **SHOULD** present an `answer` as content from the Business, distinguishable from its own output.

## Scopes

The Ask capability defines the following well-known scope for user-authenticated access:

| Scope                     | Description                                                                                                                     |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `dev.ucp.common.ask:read` | Ask on behalf of the authenticated Buyer — personalized answers reflecting member pricing, entitlements, or gated availability. |

Scope declaration, derivation, and rules for extending this set with custom scopes are defined in [Identity Linking — Scopes](http://ucp.dev/draft/specification/common/identity-linking/#scopes).

## Transport Bindings

The capability is bound to specific transport protocols:

- [REST Binding](http://ucp.dev/draft/specification/common/ask/rest/index.md): RESTful API mapping (`POST /ask`).
- [MCP Binding](http://ucp.dev/draft/specification/common/ask/mcp/index.md): Model Context Protocol mapping via JSON-RPC (`ask_business` tool).
