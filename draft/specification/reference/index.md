# Schema Reference

This page provides a reference for all the capability data models and types used within the UCP.

## Capability Schemas

### Cart

| Name         | Type                                                            | Requirement                       | Description                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | --------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | any                                                             | **Required**; omitted in requests | UCP metadata for cart responses. No payment handlers needed pre-checkout.                                                                                                                                                                                                                                                                                                                               |
| id           | string                                                          | **Required**; omitted on create   | Unique cart identifier.                                                                                                                                                                                                                                                                                                                                                                                 |
| line_items   | Array\[[Line Item](/draft/specification/reference/#line-item)\] | **Required**                      | Cart line items. Same structure as checkout. Full replacement on update.                                                                                                                                                                                                                                                                                                                                |
| context      | [Context](/draft/specification/reference/#context)              | Optional                          | Buyer signals for localization (country, region, postal_code). Merchant uses for pricing, availability, currency. Falls back to geo-IP if omitted.                                                                                                                                                                                                                                                      |
| signals      | [Signals](/draft/specification/reference/#signals)              | Optional                          | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace. |
| attribution  | [Attribution](/draft/specification/reference/#attribution)      | Optional                          | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                        |
| buyer        | [Buyer](/draft/specification/reference/#buyer)                  | Optional                          | Optional buyer information for personalized estimates.                                                                                                                                                                                                                                                                                                                                                  |
| currency     | string                                                          | **Required**; omitted in requests | ISO 4217 currency code. Determined by merchant based on context or geo-IP.                                                                                                                                                                                                                                                                                                                              |
| totals       | [Totals](/draft/specification/reference/#totals)                | **Required**; omitted in requests | Estimated cost breakdown. May be partial if shipping/tax not yet calculable.                                                                                                                                                                                                                                                                                                                            |
| actions      | [Actions](/draft/specification/reference/#actions)              | Optional; omitted in requests     | Outstanding extension-defined Actions for this cart.                                                                                                                                                                                                                                                                                                                                                    |
| messages     | Array\[[Message](/draft/specification/reference/#message)\]     | Optional; omitted in requests     | Validation messages, warnings, or informational notices.                                                                                                                                                                                                                                                                                                                                                |
| links        | Array\[[Link](/draft/specification/reference/#link)\]           | Optional; omitted in requests     | Optional merchant links (policies, FAQs).                                                                                                                                                                                                                                                                                                                                                               |
| policies     | Array\[[Policy](/draft/specification/reference/#policy)\]       | Optional; omitted in requests     | Policies (e.g., return/refund terms) that apply to the items in this cart. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                |
| continue_url | string                                                          | Optional; omitted in requests     | URL for cart handoff and session recovery. Enables sharing and human-in-the-loop flows.                                                                                                                                                                                                                                                                                                                 |
| expires_at   | string                                                          | Optional; omitted in requests     | Cart expiry timestamp (RFC 3339). Optional.                                                                                                                                                                                                                                                                                                                                                             |

______________________________________________________________________

### Catalog Lookup

Product/variant lookup by identifier. Supports batch retrieval (lookup_catalog) and single-product detail (get_product).

______________________________________________________________________

### Catalog Search

Product catalog search capability.

______________________________________________________________________

### Checkout

| Name         | Type                                                                     | Requirement                       | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ------------------------------------------------------------------------ | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | any                                                                      | **Required**; omitted in requests | UCP metadata for checkout responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| id           | string                                                                   | **Required**; omitted in requests | Unique identifier of the checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| line_items   | Array\[[Line Item](/draft/specification/reference/#line-item)\]          | **Required**; omitted on complete | List of line items being checked out.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| buyer        | [Buyer](/draft/specification/reference/#buyer)                           | Optional; omitted on complete     | Representation of the buyer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| context      | [Context](/draft/specification/reference/#context)                       | Optional; omitted on complete     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals      | [Signals](/draft/specification/reference/#signals)                       | Optional                          | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution  | [Attribution](/draft/specification/reference/#attribution)               | Optional                          | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| status       | string                                                                   | **Required**; omitted in requests | Checkout state indicating the current phase and required processing. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                     |
| currency     | string                                                                   | **Required**; omitted in requests | ISO 4217 currency code reflecting the merchant's market determination. Derived from address, context, and geo IP—buyers provide signals, merchants determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| totals       | [Totals](/draft/specification/reference/#totals)                         | **Required**; omitted in requests | Different cart totals.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| actions      | [Actions](/draft/specification/reference/#actions)                       | Optional; omitted in requests     | Outstanding extension-defined Actions for this checkout.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| messages     | Array\[[Message](/draft/specification/reference/#message)\]              | Optional; omitted in requests     | List of messages with error and info about the checkout session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| links        | Array\[[Link](/draft/specification/reference/#link)\]                    | **Required**; omitted in requests | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies     | Array\[[Policy](/draft/specification/reference/#policy)\]                | Optional; omitted in requests     | Policies (e.g., return/refund terms) that apply to the items in this checkout. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| expires_at   | string                                                                   | Optional; omitted in requests     | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| continue_url | string                                                                   | Optional; omitted in requests     | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| payment      | [Payment](/draft/specification/reference/#payment)                       | Optional; required on complete    | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| order        | [Order Confirmation](/draft/specification/reference/#order-confirmation) | Optional; omitted in requests     | Details about an order created for this checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

______________________________________________________________________

### Order

| Name          | Type                                                                        | Requirement                       | Description                                                                                                                                                        |
| ------------- | --------------------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ucp           | any                                                                         | **Required**                      | UCP metadata for order responses. No payment handlers needed post-purchase.                                                                                        |
| id            | string                                                                      | **Required**                      | Unique order identifier.                                                                                                                                           |
| label         | string                                                                      | Optional                          | Human-readable label for identifying the order. MUST only be provided by the business.                                                                             |
| checkout_id   | string                                                                      | **Required**                      | Associated checkout ID for reconciliation.                                                                                                                         |
| permalink_url | string                                                                      | **Required**                      | Permalink to access the order on merchant site.                                                                                                                    |
| line_items    | Array\[[Order Line Item](/draft/specification/reference/#order-line-item)\] | **Required**                      | Line items representing what was purchased — can change post-order via edits or exchanges.                                                                         |
| fulfillment   | object                                                                      | **Required**                      | Fulfillment data: buyer expectations and what actually happened.                                                                                                   |
| adjustments   | Array\[[Adjustment](/draft/specification/reference/#adjustment)\]           | Optional                          | Post-order events (refunds, returns, credits, disputes, cancellations, etc.) that exist independently of fulfillment.                                              |
| currency      | string                                                                      | **Required**; omitted in requests | ISO 4217 currency code. MUST match the currency from the originating checkout session.                                                                             |
| totals        | [Totals](/draft/specification/reference/#totals)                            | **Required**                      | Different totals for the order.                                                                                                                                    |
| policies      | Array\[[Policy](/draft/specification/reference/#policy)\]                   | Optional; omitted in requests     | Snapshot of the policies that applied to the items at checkout, captured on the order as a durable record. `applies_to` targets are relative to the response root. |
| messages      | Array\[[Message](/draft/specification/reference/#message)\]                 | Optional                          | Business outcome messages (errors, warnings, informational). Present when the business needs to communicate status or issues to the platform.                      |
| attribution   | [Attribution](/draft/specification/reference/#attribution)                  | Optional; omitted in requests     | Snapshot of the attribution associated with the originating checkout. Read-only on the order.                                                                      |

______________________________________________________________________

### Payment

| Name        | Type                                                                                                                                      | Requirement | Description                                                                                                                                                                                                                |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| instruments | Array\[[Payment Instrument Selected Payment Instrument](/draft/specification/reference/#payment-instrument-selected-payment-instrument)\] | Optional    | The payment instruments available for this payment. Each instrument is associated with a specific handler via the handler_id field. Handlers can extend the base payment_instrument schema to add handler-specific fields. |

______________________________________________________________________

## Type Schemas

### Actions

Outstanding extension-defined Action instances, keyed by reverse-domain Action type, not extension name.

______________________________________________________________________

### Amount

Monetary amount in the currency's minor unit as defined by ISO 4217. Refer to the currency's exponent to determine minor-to-major ratio (e.g., 2 for USD, 0 for JPY, 3 for KWD).

______________________________________________________________________

### Description

| Name     | Type   | Requirement | Description                                                                                                                                                               |
| -------- | ------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| plain    | string | Optional    | Plain text content.                                                                                                                                                       |
| html     | string | Optional    | HTML-formatted content. Security: Platforms MUST sanitize before rendering—strip scripts, event handlers, and untrusted elements. Treat all rich text as untrusted input. |
| markdown | string | Optional    | Markdown-formatted content.                                                                                                                                               |

______________________________________________________________________

### Error Code

Error code identifying the type of error. Standard errors are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.

______________________________________________________________________

### Error Response

| Name         | Type                                                        | Requirement  | Description                                                       |
| ------------ | ----------------------------------------------------------- | ------------ | ----------------------------------------------------------------- |
| ucp          | any                                                         | **Required** | UCP protocol metadata. Status MUST be 'error' for error response. |
| messages     | Array\[[Message](/draft/specification/reference/#message)\] | **Required** | Array of messages describing why the operation failed.            |
| continue_url | string                                                      | Optional     | URL for buyer handoff or session recovery.                        |

______________________________________________________________________

### Info Code

Info code identifying the type of informational message. Standard codes are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.

______________________________________________________________________

### Link

| Name  | Type   | Requirement  | Description                                                                                                                                                                                                                          |
| ----- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| type  | string | **Required** | Type of link. Well-known values: `privacy_policy`, `terms_of_service`, `refund_policy`, `shipping_policy`, `faq`. Consumers SHOULD handle unknown values gracefully by displaying them using the `title` field or omitting the link. |
| url   | string | **Required** | The actual URL pointing to the content to be displayed.                                                                                                                                                                              |
| title | string | Optional     | Optional display text for the link. When provided, use this instead of generating from type.                                                                                                                                         |

______________________________________________________________________

### Locality

| Name            | Type   | Requirement | Description                                                                                                                    |
| --------------- | ------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------ |
| address_country | string | Optional    | The country, as a 2-letter ISO 3166-1 alpha-2 code (e.g. "US"). A 3-letter alpha-3 code or full country name MAY also be used. |
| address_region  | string | Optional    | The first-level administrative region within the country (e.g. a state or province such as California).                        |
| postal_code     | string | Optional    | The postal code (e.g. "94043").                                                                                                |

______________________________________________________________________

### Media

| Name     | Type    | Requirement  | Description                                                  |
| -------- | ------- | ------------ | ------------------------------------------------------------ |
| type     | string  | **Required** | Media type. Well-known values: `image`, `video`, `model_3d`. |
| url      | string  | **Required** | URL to the media resource.                                   |
| alt_text | string  | Optional     | Accessibility text describing the media.                     |
| width    | integer | Optional     | Width in pixels (for images/video).                          |
| height   | integer | Optional     | Height in pixels (for images/video).                         |

______________________________________________________________________

### Message

This object MUST be one of the following types: [Message Error](/draft/specification/reference/#message-error), [Message Warning](/draft/specification/reference/#message-warning), [Message Info](/draft/specification/reference/#message-info).

______________________________________________________________________

### Message Error

| Name         | Type                                                     | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------ | -------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                   | **Required** | **Constant = error**. Message type discriminator.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| code         | [Error Code](/draft/specification/reference/#error-code) | **Required** | Error code identifying the type of error. Standard errors are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| path         | string                                                   | Optional     | RFC 9535 JSONPath to the component the message refers to (e.g., $.line_items[0]).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| content_type | string                                                   | Optional     | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| content      | string                                                   | **Required** | Human-readable message.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| severity     | string                                                   | **Required** | Reflects the resource state and recommended action. 'recoverable': platform can resolve the condition in band, for example by modifying inputs or processing a related Action, and submit a new operation when needed. 'requires_buyer_input': merchant requires information their API doesn't support collecting programmatically (checkout incomplete). 'requires_buyer_review': buyer must authorize before order placement due to policy, regulatory, or entitlement rules. 'unrecoverable': no valid resource exists to act on, retry with new resource or inputs. Errors with 'requires\_*' severity contribute to 'status: requires_escalation'.* *Enum:*\* `recoverable`, `requires_buyer_input`, `requires_buyer_review`, `unrecoverable` |

______________________________________________________________________

### Message Info

| Name         | Type                                                   | Requirement  | Description                                                                                                                                                                                    |
| ------------ | ------------------------------------------------------ | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                 | **Required** | **Constant = info**. Message type discriminator.                                                                                                                                               |
| path         | string                                                 | Optional     | RFC 9535 JSONPath to the component the message refers to (e.g., $.line_items[0]).                                                                                                              |
| code         | [Info Code](/draft/specification/reference/#info-code) | Optional     | Info code identifying the type of informational message. Standard codes are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted. |
| content_type | string                                                 | Optional     | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                 |
| content      | string                                                 | **Required** | Human-readable message.                                                                                                                                                                        |

______________________________________________________________________

### Message Warning

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

______________________________________________________________________

### Pagination

Cursor-based pagination for list operations.

______________________________________________________________________

### Postal Address

| Name             | Type   | Requirement | Description                                                                                                                                                                                                                               |
| ---------------- | ------ | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| extended_address | string | Optional    | An address extension such as an apartment number, C/O or alternative name.                                                                                                                                                                |
| street_address   | string | Optional    | The street address.                                                                                                                                                                                                                       |
| address_locality | string | Optional    | The locality in which the street address is, and which is in the region. For example, Mountain View.                                                                                                                                      |
| address_region   | string | Optional    | The region in which the locality is, and which is in the country. Required for applicable countries (i.e. state in US, province in CA). For example, California or another appropriate first-level Administrative division.               |
| address_country  | string | Optional    | The country. Recommended to be in 2-letter ISO 3166-1 alpha-2 format, for example "US". For backward compatibility, a 3-letter ISO 3166-1 alpha-3 country code such as "SGP" or a full country name such as "Singapore" can also be used. |
| postal_code      | string | Optional    | The postal code. For example, 94043.                                                                                                                                                                                                      |
| first_name       | string | Optional    | Optional. First name of the contact associated with the address.                                                                                                                                                                          |
| last_name        | string | Optional    | Optional. Last name of the contact associated with the address.                                                                                                                                                                           |
| phone_number     | string | Optional    | Optional. Phone number of the contact associated with the address.                                                                                                                                                                        |

______________________________________________________________________

### Price

| Name     | Type                                             | Requirement  | Description                                           |
| -------- | ------------------------------------------------ | ------------ | ----------------------------------------------------- |
| amount   | [Amount](/draft/specification/reference/#amount) | **Required** | Amount in ISO 4217 minor units. Use 0 for free items. |
| currency | string                                           | **Required** | ISO 4217 currency code (e.g., 'USD', 'EUR', 'GBP').   |

______________________________________________________________________

### Reverse Domain Name

Reverse-domain identifier used for collision-safe namespacing of capabilities, services, handlers, eligibility claims, and extension-contributed keys. Must contain at least two dot-separated segments (e.g., 'dev.ucp.shopping.checkout', 'com.example.loyalty_gold'). Segments after the first are domain- or identifier-derived: they may contain interior hyphens, may start with a digit, and may contain underscores (e.g., 'com.example-shop.checkout', 'com.2example.cart', 'dev.ucp.common.identity_linking'), but must not start or end with a hyphen. The first segment (the reversed top-level domain) is letters and digits, and may contain interior hyphens to support internationalized (punycode) top-level domains such as 'xn--p1ai'.

**Pattern:** `^[a-z](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9_-]*[a-z0-9_])?)+$`

______________________________________________________________________

### Signed Amount

Monetary amount in the currency's minor unit as defined by ISO 4217. Refer to the currency's exponent to determine minor-to-major ratio (e.g., 2 for USD, 0 for JPY, 3 for KWD). May be negative — the sign is intrinsic to the value (e.g., discounts are negative, charges are positive).

______________________________________________________________________

### Warning Code

Warning code identifying the type of warning. Standard codes are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.

______________________________________________________________________

### Payment Account Info

| Name                      | Type   | Requirement | Description                                                                                                                                   |
| ------------------------- | ------ | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| payment_account_reference | string | Optional    | EMVCo PAR. A unique identifier linking a payment card to a specific account, enabling tracking across tokens (Apple Pay, physical card, etc). |

______________________________________________________________________

### Adjustment

| Name        | Type                                                    | Requirement  | Description                                                                                                                                                                                     |
| ----------- | ------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string                                                  | **Required** | Adjustment event identifier.                                                                                                                                                                    |
| type        | string                                                  | **Required** | Type of adjustment (open string). Typically money-related like: refund, return, credit, price_adjustment, dispute, cancellation. Can be any value that makes sense for the merchant's business. |
| occurred_at | string                                                  | **Required** | RFC 3339 timestamp when this adjustment occurred.                                                                                                                                               |
| status      | string                                                  | **Required** | Adjustment status. **Enum:** `pending`, `completed`, `failed`                                                                                                                                   |
| line_items  | Array[object]                                           | Optional     | Which line items and quantities are affected (optional).                                                                                                                                        |
| totals      | Array\[[Total](/draft/specification/reference/#total)\] | Optional     | Adjustment totals breakdown. Signed values - negative for money returned to buyer (refunds, credits), positive for additional charges (exchanges).                                              |
| description | string                                                  | Optional     | Human-readable reason or description (e.g., 'Defective item', 'Customer requested').                                                                                                            |

______________________________________________________________________

### Attribution

Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.

______________________________________________________________________

### Availability

| Name      | Type    | Requirement | Description                                                                                                                         |
| --------- | ------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| available | boolean | Optional    | Whether this can be obtained. See status for fulfillment details.                                                                   |
| status    | string  | Optional    | Qualifies available with fulfillment state. Well-known values: `in_stock`, `backorder`, `preorder`, `out_of_stock`, `discontinued`. |

______________________________________________________________________

### Available Payment Instrument

| Name        | Type   | Requirement  | Description                                                                                                  |
| ----------- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------ |
| type        | string | **Required** | The instrument type identifier (e.g., 'card', 'gift_card'). References an instrument schema's type constant. |
| constraints | object | Optional     | Constraints on this instrument type. Structure depends on instrument type and active capabilities.           |

______________________________________________________________________

### Binding

| Name        | Type                                                                 | Requirement  | Description                                                                                                                                                                                    |
| ----------- | -------------------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| checkout_id | string                                                               | **Required** | The checkout session identifier this token is bound to.                                                                                                                                        |
| identity    | [Payment Identity](/draft/specification/reference/#payment-identity) | Optional     | The participant this token is bound to. Required when acting on behalf of another participant (e.g., agent tokenizing for merchant). Omit when the authenticated caller is the binding target. |

______________________________________________________________________

### Business Fulfillment Config

| Name                | Type          | Requirement | Description                                                                                                                                                                                                 |
| ------------------- | ------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| multi_destination   | Array[object] | Optional    | Method types that permit multiple destinations within one cart (e.g. split shipping across addresses). Listing a method permits it; an omitted method does not. Open — businesses MAY list any method type. |
| method_combinations | Array[array]  | Optional    | Method-type combinations the business permits within one cart. Each inner array is a permitted set of method `type` values (e.g. shipping + pickup).                                                        |

______________________________________________________________________

### Business Split Payments Config

| Name                 | Type         | Requirement  | Description                                                                                                                                  |
| -------------------- | ------------ | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| allowed_combinations | Array[array] | **Required** | Array of valid instrument combinations. Each combination is an array of instrument groups. A payment is valid if it matches any combination. |

______________________________________________________________________

### Buyer

| Name         | Type   | Requirement | Description              |
| ------------ | ------ | ----------- | ------------------------ |
| first_name   | string | Optional    | First name of the buyer. |
| last_name    | string | Optional    | Last name of the buyer.  |
| email        | string | Optional    | Email of the buyer.      |
| phone_number | string | Optional    | E.164 standard.          |

______________________________________________________________________

### Card Credential

| Name             | Type    | Requirement  | Description                                                                                                                                            |
| ---------------- | ------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| type             | string  | **Required** | The credential type discriminator. Specific schemas will constrain this to a constant value.                                                           |
| type             | any     | **Required** | **Constant = card**. The credential type identifier for card credentials.                                                                              |
| card_number_type | string  | **Required** | The type of card number. Network tokens are preferred with fallback to FPAN. See PCI Scope for more details. **Enum:** `fpan`, `network_token`, `dpan` |
| number           | string  | Optional     | Card number.                                                                                                                                           |
| expiry_month     | integer | Optional     | The month of the card's expiration date (1-12).                                                                                                        |
| expiry_year      | integer | Optional     | The year of the card's expiration date.                                                                                                                |
| name             | string  | Optional     | Cardholder name.                                                                                                                                       |
| cvc              | string  | Optional     | Card CVC number.                                                                                                                                       |
| cryptogram       | string  | Optional     | Cryptogram provided with network tokens.                                                                                                               |
| eci_value        | string  | Optional     | Electronic Commerce Indicator / Security Level Indicator provided with network tokens.                                                                 |

______________________________________________________________________

### Card Payment Instrument

| Name            | Type                                                                     | Requirement  | Description                                                                                                                                                  |
| --------------- | ------------------------------------------------------------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| id              | string                                                                   | **Required** | A unique identifier for this instrument instance, assigned by the platform.                                                                                  |
| handler_id      | string                                                                   | **Required** | The unique identifier for the handler instance that produced this instrument. This corresponds to the 'id' field in the Payment Handler definition.          |
| type            | string                                                                   | **Required** | The broad category of the instrument (e.g., 'card', 'tokenized_card'). Specific schemas will constrain this to a constant value.                             |
| billing_address | [Postal Address](/draft/specification/reference/#postal-address)         | Optional     | The billing address associated with this payment method.                                                                                                     |
| credential      | [Payment Credential](/draft/specification/reference/#payment-credential) | Optional     | The base definition for any payment credential. Handlers define specific credential types.                                                                   |
| display         | object                                                                   | Optional     | Display information for this payment instrument. Each payment instrument schema defines its specific display properties, as outlined by the payment handler. |
| type            | string                                                                   | **Required** | **Constant = card**. Indicates this is a card payment instrument.                                                                                            |
| display         | object                                                                   | Optional     | Display information for this card payment instrument.                                                                                                        |

______________________________________________________________________

### Category

| Name     | Type   | Requirement  | Description                                                                           |
| -------- | ------ | ------------ | ------------------------------------------------------------------------------------- |
| value    | string | **Required** | Category value or path (e.g., 'Apparel > Shirts', '1604').                            |
| taxonomy | string | Optional     | Source taxonomy. Well-known values: `google_product_category`, `shopify`, `merchant`. |

______________________________________________________________________

### Context

| Name            | Type                                                                                | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --------------- | ----------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| address_country | string                                                                              | Optional    | The country, as a 2-letter ISO 3166-1 alpha-2 code (e.g. "US"). A 3-letter alpha-3 code or full country name MAY also be used.                                                                                                                                                                                                                                                                                                                                     |
| address_region  | string                                                                              | Optional    | The first-level administrative region within the country (e.g. a state or province such as California).                                                                                                                                                                                                                                                                                                                                                            |
| postal_code     | string                                                                              | Optional    | The postal code (e.g. "94043").                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| intent          | string                                                                              | Optional    | Background context describing buyer's intent (e.g., 'looking for a gift under $50', 'need something durable for outdoor use'). Informs relevance, recommendations, and personalization.                                                                                                                                                                                                                                                                            |
| language        | string                                                                              | Optional    | Preferred language for content. Use IETF BCP 47 language tags (e.g., 'en', 'fr-CA', 'zh-Hans'). For REST, equivalent to Accept-Language header—platforms SHOULD fall back to Accept-Language when this field is absent; when provided, overrides Accept-Language. Businesses MAY return content in a different language if unavailable.                                                                                                                            |
| currency        | string                                                                              | Optional    | Preferred currency (ISO 4217, e.g., 'EUR', 'USD'). Businesses determine presentment currency from context and authoritative signals; this hint MAY inform selection in multi-currency markets. Also serves as the denomination for price filter values — platforms SHOULD include this field when sending price filters. Response prices include explicit currency confirming the resolution.                                                                      |
| eligibility     | Array\[[Reverse Domain Name](/draft/specification/reference/#reverse-domain-name)\] | Optional    | Buyer claims about eligible benefits such as loyalty membership, payment instrument perks, and similar. Recognized claims MAY inform the Business response (e.g., member-only product availability, adjusted pricing in catalog, provisional discounts at cart or checkout). Businesses MUST ignore unrecognized values without error. Values MUST use reverse-domain naming (e.g., 'com.example.loyalty_gold', 'org.school.student') and MUST be non-identifying. |
| payment         | Array[object]                                                                       | Optional    | Buyer-preferred payment handlers in priority order (most preferred first). Each entry names a handler advertised in the Business profile's `ucp.payment_handlers`, optionally narrowed to preferred instrument types. The Business SHOULD use it to preselect or prioritize the handler (and type, when given) and MAY ignore unavailable or ineligible entries; unrecognized values MUST be ignored without error.                                                |

______________________________________________________________________

### Detail Option Value

| Name      | Type    | Requirement | Description                                                                                    |
| --------- | ------- | ----------- | ---------------------------------------------------------------------------------------------- |
| available | boolean | Optional    | Whether a variant matching this value and the current option selections is purchasable.        |
| exists    | boolean | Optional    | Whether a variant matching this value and the current option selections exists in the catalog. |

______________________________________________________________________

### Expectation

| Name           | Type                                                             | Requirement  | Description                                                                                                 |
| -------------- | ---------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------- |
| id             | string                                                           | **Required** | Expectation identifier.                                                                                     |
| line_items     | Array[object]                                                    | **Required** | Which line items and quantities are in this expectation.                                                    |
| method_type    | string                                                           | **Required** | Delivery method type. Well-known values: `shipping`, `pickup`, `digital`; additional values MAY be used.    |
| destination    | [Postal Address](/draft/specification/reference/#postal-address) | **Required** | Delivery destination address.                                                                               |
| description    | string                                                           | Optional     | Human-readable delivery description (e.g., 'Arrives in 5-8 business days').                                 |
| fulfillable_on | string                                                           | Optional     | When this expectation can be fulfilled: 'now' or ISO 8601 timestamp for future date (backorder, pre-order). |

______________________________________________________________________

### Fulfillment

| Name              | Type                                                                                                  | Requirement                   | Description                         |
| ----------------- | ----------------------------------------------------------------------------------------------------- | ----------------------------- | ----------------------------------- |
| methods           | Array\[[Fulfillment Method](/draft/specification/reference/#fulfillment-method)\]                     | Optional                      | Fulfillment methods for cart items. |
| available_methods | Array\[[Fulfillment Available Method](/draft/specification/reference/#fulfillment-available-method)\] | Optional; omitted in requests | Inventory availability hints.       |

______________________________________________________________________

### Fulfillment Available Method

| Name           | Type               | Requirement                       | Description                                                                                                                          |
| -------------- | ------------------ | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| type           | string             | **Required**; omitted in requests | Fulfillment method type this availability applies to. Well-known values: `shipping`, `pickup`; businesses MAY use additional values. |
| line_item_ids  | Array[string]      | **Required**; omitted in requests | Line items available for this fulfillment method.                                                                                    |
| fulfillable_on | ['string', 'null'] | Optional; omitted in requests     | 'now' for immediate availability, or ISO 8601 date for future (preorders, transfers).                                                |
| description    | string             | Optional; omitted in requests     | Human-readable availability info (e.g., 'Available for pickup at Downtown Store today').                                             |

______________________________________________________________________

### Fulfillment Destination

This object MUST be one of the following types: [Shipping Destination](/draft/specification/reference/#shipping-destination), [Retail Location](/draft/specification/reference/#retail-location).

______________________________________________________________________

### Fulfillment Destination Filter

| Name            | Type   | Requirement | Description                                                                                                                    |
| --------------- | ------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------ |
| address_country | string | Optional    | The country, as a 2-letter ISO 3166-1 alpha-2 code (e.g. "US"). A 3-letter alpha-3 code or full country name MAY also be used. |
| address_region  | string | Optional    | The first-level administrative region within the country (e.g. a state or province such as California).                        |
| postal_code     | string | Optional    | The postal code (e.g. "94043").                                                                                                |
| location        | string | Optional    | A reference to the destination (e.g. store, pickup location, saved address).                                                   |

______________________________________________________________________

### Fulfillment Event

| Name            | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                             |
| --------------- | ------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id              | string        | **Required** | Fulfillment event identifier.                                                                                                                                                                                                                                                                                                           |
| occurred_at     | string        | **Required** | RFC 3339 timestamp when this fulfillment event occurred.                                                                                                                                                                                                                                                                                |
| type            | string        | **Required** | Fulfillment event type. Common values include: processing (preparing to ship), shipped (handed to carrier), in_transit (in delivery network), delivered (received by buyer), failed_attempt (delivery attempt failed), canceled (fulfillment canceled), undeliverable (cannot be delivered), returned_to_sender (returned to merchant). |
| line_items      | Array[object] | **Required** | Which line items and quantities are fulfilled in this event.                                                                                                                                                                                                                                                                            |
| tracking_number | string        | Optional     | Carrier tracking number (required if type != processing).                                                                                                                                                                                                                                                                               |
| tracking_url    | string        | Optional     | URL to track this shipment (required if type != processing).                                                                                                                                                                                                                                                                            |
| carrier         | string        | Optional     | Carrier name (e.g., 'FedEx', 'USPS').                                                                                                                                                                                                                                                                                                   |
| description     | string        | Optional     | Human-readable description of the shipment status or delivery information (e.g., 'Delivered to front door', 'Out for delivery').                                                                                                                                                                                                        |

______________________________________________________________________

### Fulfillment Group

| Name               | Type                                                                              | Requirement                       | Description                                                            |
| ------------------ | --------------------------------------------------------------------------------- | --------------------------------- | ---------------------------------------------------------------------- |
| id                 | string                                                                            | **Required**; omitted on create   | Group identifier for referencing merchant-generated groups in updates. |
| line_item_ids      | Array[string]                                                                     | **Required**; omitted in requests | Line item IDs included in this group/package.                          |
| options            | Array\[[Fulfillment Option](/draft/specification/reference/#fulfillment-option)\] | Optional; omitted in requests     | Available fulfillment options for this group.                          |
| selected_option_id | ['string', 'null']                                                                | Optional                          | ID of the selected fulfillment option for this group.                  |

______________________________________________________________________

### Fulfillment Method

| Name                    | Type                                                                                        | Requirement                                         | Description                                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| id                      | string                                                                                      | **Required**; omitted on create, optional on update | Unique fulfillment method identifier.                                                                        |
| type                    | string                                                                                      | **Required**; optional on update                    | Fulfillment method type. Well-known values: `shipping`, `pickup`. Businesses MAY use additional values.      |
| line_item_ids           | Array[string]                                                                               | **Required**; optional on create                    | Line item IDs fulfilled via this method.                                                                     |
| destinations            | Array\[[Fulfillment Destination](/draft/specification/reference/#fulfillment-destination)\] | Optional                                            | Available destinations. For shipping: addresses. For pickup: retail locations.                               |
| selected_destination_id | ['string', 'null']                                                                          | Optional                                            | ID of the selected destination.                                                                              |
| groups                  | Array\[[Fulfillment Group](/draft/specification/reference/#fulfillment-group)\]             | Optional                                            | Fulfillment groups for selecting options. Agent sets selected_option_id on groups to choose shipping method. |

______________________________________________________________________

### Fulfillment Option

| Name                      | Type                                                       | Requirement                       | Description                                                                                                                                             |
| ------------------------- | ---------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id                        | string                                                     | **Required**; omitted in requests | Unique identifier for this fulfillment option.                                                                                                          |
| title                     | string                                                     | **Required**; omitted in requests | Short label that distinguishes this option from its siblings (e.g. 'Standard', 'Express Shipping', 'Curbside Pickup').                                  |
| description               | [Description](/draft/specification/reference/#description) | Optional; omitted in requests     | Supplementary context for the title (e.g. 'Arrives in 4 business days', 'Arrives Dec 12-15 via FedEx'). Directly renderable; MUST NOT repeat the title. |
| carrier                   | string                                                     | Optional; omitted in requests     | Carrier name (for shipping).                                                                                                                            |
| earliest_fulfillment_time | string                                                     | Optional; omitted in requests     | Earliest fulfillment date.                                                                                                                              |
| latest_fulfillment_time   | string                                                     | Optional; omitted in requests     | Latest fulfillment date.                                                                                                                                |
| totals                    | Array\[[Total](/draft/specification/reference/#total)\]    | **Required**; omitted in requests | Fulfillment option totals breakdown.                                                                                                                    |

______________________________________________________________________

### Fulfillment Option Base

| Name        | Type                                                       | Requirement                       | Description                                                                                                                                             |
| ----------- | ---------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string                                                     | **Required**; omitted in requests | Unique identifier for this fulfillment option.                                                                                                          |
| title       | string                                                     | **Required**; omitted in requests | Short label that distinguishes this option from its siblings (e.g. 'Standard', 'Express Shipping', 'Curbside Pickup').                                  |
| description | [Description](/draft/specification/reference/#description) | Optional; omitted in requests     | Supplementary context for the title (e.g. 'Arrives in 4 business days', 'Arrives Dec 12-15 via FedEx'). Directly renderable; MUST NOT repeat the title. |

______________________________________________________________________

### Input Correlation

| Name  | Type   | Requirement  | Description                                                                                                                                                                                                                                                                                                                   |
| ----- | ------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id    | string | **Required** | The identifier from the lookup request that resolved to this variant.                                                                                                                                                                                                                                                         |
| match | string | Optional     | How the request identifier resolved to this variant. Well-known values: `exact` (input directly identifies this variant, e.g., variant ID, SKU), `featured` (server selected this variant as representative, e.g., product ID resolved to best match). Businesses MAY implement and provide additional resolution strategies. |

______________________________________________________________________

### Instrument Group

| Name  | Type          | Requirement  | Description                                                                                                   |
| ----- | ------------- | ------------ | ------------------------------------------------------------------------------------------------------------- |
| types | Array[string] | **Required** | Instrument types accepted by this group (OR logic). Any listed type qualifies.                                |
| min   | integer       | Optional     | Minimum number of instruments required from this group. Defaults to 0 (optional).                             |
| max   | integer       | Optional     | Maximum number of instruments allowed from this group. Defaults to 1. MUST be greater than or equal to `min`. |

______________________________________________________________________

### Item

| Name      | Type                                             | Requirement                       | Description                                                                                                                                                                 |
| --------- | ------------------------------------------------ | --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id        | string                                           | **Required**                      | The product identifier, often the SKU, required to resolve the product details associated with this line item. Should be recognized by both the Platform, and the Business. |
| title     | string                                           | **Required**; omitted in requests | Product title.                                                                                                                                                              |
| price     | [Amount](/draft/specification/reference/#amount) | **Required**; omitted in requests | Unit price in ISO 4217 minor units.                                                                                                                                         |
| image_url | string                                           | Optional; omitted in requests     | Product image URI.                                                                                                                                                          |

______________________________________________________________________

### Line Item

| Name      | Type                                                    | Requirement                                         | Description                                            |
| --------- | ------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------ |
| id        | string                                                  | **Required**; omitted on create, optional on update |                                                        |
| item      | [Item](/draft/specification/reference/#item)            | **Required**                                        |                                                        |
| quantity  | integer                                                 | **Required**                                        | Quantity of the item being purchased.                  |
| totals    | Array\[[Total](/draft/specification/reference/#total)\] | **Required**; omitted in requests                   | Line item totals breakdown.                            |
| parent_id | string                                                  | Optional; omitted on create                         | Parent line item identifier for any nested structures. |

______________________________________________________________________

### Option Value

| Name  | Type   | Requirement  | Description                                                                                                                                           |
| ----- | ------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| id    | string | Optional     | Optional server-assigned identifier for this option value. When present in a selected_option, the server SHOULD use it for matching instead of label. |
| label | string | **Required** | Display text for this option value (e.g., 'Small', 'Blue').                                                                                           |

______________________________________________________________________

### Order Confirmation

| Name          | Type   | Requirement  | Description                                                                            |
| ------------- | ------ | ------------ | -------------------------------------------------------------------------------------- |
| id            | string | **Required** | Unique order identifier.                                                               |
| label         | string | Optional     | Human-readable label for identifying the order. MUST only be provided by the business. |
| permalink_url | string | **Required** | Permalink to access the order on merchant site.                                        |

______________________________________________________________________

### Order Line Item

| Name      | Type                                                    | Requirement  | Description                                                                                                                                                                                                                                                         |
| --------- | ------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id        | string                                                  | **Required** | Line item identifier.                                                                                                                                                                                                                                               |
| item      | [Item](/draft/specification/reference/#item)            | **Required** | Product data (id, title, price, image_url).                                                                                                                                                                                                                         |
| quantity  | object                                                  | **Required** | Quantity tracking for the line item.                                                                                                                                                                                                                                |
| totals    | Array\[[Total](/draft/specification/reference/#total)\] | **Required** | Line item totals breakdown.                                                                                                                                                                                                                                         |
| status    | string                                                  | **Required** | Derived status: removed if quantity.total == 0, fulfilled if quantity.total > 0 and quantity.fulfilled == quantity.total, partial if quantity.total > 0 and quantity.fulfilled > 0, otherwise processing. **Enum:** `processing`, `partial`, `fulfilled`, `removed` |
| parent_id | string                                                  | Optional     | Parent line item identifier for any nested structures.                                                                                                                                                                                                              |

______________________________________________________________________

### Payment Credential

| Name | Type   | Requirement  | Description                                                                                  |
| ---- | ------ | ------------ | -------------------------------------------------------------------------------------------- |
| type | string | **Required** | The credential type discriminator. Specific schemas will constrain this to a constant value. |

______________________________________________________________________

### Payment Identity

| Name         | Type   | Requirement  | Description                                                                            |
| ------------ | ------ | ------------ | -------------------------------------------------------------------------------------- |
| access_token | string | **Required** | Unique identifier for this participant, obtained during onboarding with the tokenizer. |

______________________________________________________________________

### Payment Instrument

| Name            | Type                                                                     | Requirement  | Description                                                                                                                                                  |
| --------------- | ------------------------------------------------------------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| id              | string                                                                   | **Required** | A unique identifier for this instrument instance, assigned by the platform.                                                                                  |
| handler_id      | string                                                                   | **Required** | The unique identifier for the handler instance that produced this instrument. This corresponds to the 'id' field in the Payment Handler definition.          |
| type            | string                                                                   | **Required** | The broad category of the instrument (e.g., 'card', 'tokenized_card'). Specific schemas will constrain this to a constant value.                             |
| billing_address | [Postal Address](/draft/specification/reference/#postal-address)         | Optional     | The billing address associated with this payment method.                                                                                                     |
| credential      | [Payment Credential](/draft/specification/reference/#payment-credential) | Optional     | The base definition for any payment credential. Handlers define specific credential types.                                                                   |
| display         | object                                                                   | Optional     | Display information for this payment instrument. Each payment instrument schema defines its specific display properties, as outlined by the payment handler. |

______________________________________________________________________

### Platform Fulfillment Config

| Name                 | Type    | Requirement | Description                         |
| -------------------- | ------- | ----------- | ----------------------------------- |
| supports_multi_group | boolean | Optional    | Enables multiple groups per method. |

______________________________________________________________________

### Policy

| Name        | Type                                                                       | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ----------- | -------------------------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type        | [Reverse Domain Name](/draft/specification/reference/#reverse-domain-name) | **Required** | Policy type discriminator. Open reverse-DNS vocabulary. Well-known values: `dev.ucp.shopping.policy.return` (return terms), `dev.ucp.shopping.policy.warranty` (warranty terms). Businesses MAY define custom types in their own domain (e.g., `com.example.policy.price_match`). Platforms MUST tolerate unknown values.                                                                                                                                                                                                                                                                                                                                                          |
| description | [Description](/draft/specification/reference/#description)                 | **Required** | Human-readable policy summary in one or more formats (plain, markdown, html). Required on every policy so a platform can present it without understanding any type-specific fields. This is not the buyer-facing disclosure — display is compelled by a `messages[]` warning (see the Policies section).                                                                                                                                                                                                                                                                                                                                                                           |
| applies_to  | Array[string]                                                              | Optional     | RFC 9535 JSONPath expressions identifying the nodes this policy applies to, relative to the embedding response root (e.g., `$.line_items[0]` in cart/checkout, `$.products[2]` in catalog). Each target covers the node it names and everything nested under it, so a target on a product also covers its variants. A singular query (RFC 9535 Section 2.3.5.1; name and index selectors only) names a single node; filters, wildcards, and slices match a set. When omitted, the policy applies to the entire response. When policies of the same `type` contest a node, the narrowest target wins and overrides the rest. See the Policies section for how specificity resolves. |
| url         | string                                                                     | Optional     | Optional link to the full policy document.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

______________________________________________________________________

### Price Filter

| Name | Type                                             | Requirement | Description                            |
| ---- | ------------------------------------------------ | ----------- | -------------------------------------- |
| min  | [Amount](/draft/specification/reference/#amount) | Optional    | Minimum price in ISO 4217 minor units. |
| max  | [Amount](/draft/specification/reference/#amount) | Optional    | Maximum price in ISO 4217 minor units. |

______________________________________________________________________

### Price Range

| Name | Type                                           | Requirement  | Description                 |
| ---- | ---------------------------------------------- | ------------ | --------------------------- |
| min  | [Price](/draft/specification/reference/#price) | **Required** | Minimum price in the range. |
| max  | [Price](/draft/specification/reference/#price) | **Required** | Maximum price in the range. |

______________________________________________________________________

### Product

| Name             | Type                                                                      | Requirement  | Description                                                                                      |
| ---------------- | ------------------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------ |
| id               | string                                                                    | **Required** | Global ID (GID) uniquely identifying this product.                                               |
| handle           | string                                                                    | Optional     | URL-safe slug for SEO-friendly URLs (e.g., 'blue-runner-pro'). Use id for stable API references. |
| title            | string                                                                    | **Required** | Product title.                                                                                   |
| description      | [Description](/draft/specification/reference/#description)                | **Required** | Product description in one or more formats.                                                      |
| url              | string                                                                    | Optional     | Canonical product page URL.                                                                      |
| categories       | Array\[[Category](/draft/specification/reference/#category)\]             | Optional     | Product categories with optional taxonomy identifiers.                                           |
| price_range      | [Price Range](/draft/specification/reference/#price-range)                | **Required** | Price range across all variants.                                                                 |
| list_price_range | [Price Range](/draft/specification/reference/#price-range)                | Optional     | List price range before discounts (for strikethrough display).                                   |
| media            | Array\[[Media](/draft/specification/reference/#media)\]                   | Optional     | Product media (images, videos, 3D models). First item is the featured media for listings.        |
| options          | Array\[[Product Option](/draft/specification/reference/#product-option)\] | Optional     | Product options (Size, Color, etc.).                                                             |
| variants         | Array\[[Variant](/draft/specification/reference/#variant)\]               | **Required** | Purchasable variants of this product. First item is the featured variant for listings.           |
| rating           | [Rating](/draft/specification/reference/#rating)                          | Optional     | Aggregate product rating.                                                                        |
| tags             | Array[string]                                                             | Optional     | Product tags for categorization and search.                                                      |
| metadata         | object                                                                    | Optional     | Business-defined custom data extending the standard product model.                               |

______________________________________________________________________

### Product Option

| Name   | Type                                                                  | Requirement  | Description                          |
| ------ | --------------------------------------------------------------------- | ------------ | ------------------------------------ |
| name   | string                                                                | **Required** | Option name (e.g., 'Size', 'Color'). |
| values | Array\[[Option Value](/draft/specification/reference/#option-value)\] | **Required** | Available values for this option.    |

______________________________________________________________________

### Rating

| Name      | Type    | Requirement  | Description                                                |
| --------- | ------- | ------------ | ---------------------------------------------------------- |
| value     | number  | **Required** | Average rating value.                                      |
| scale_min | number  | Optional     | Minimum value on the rating scale (e.g., 1 for 1-5 stars). |
| scale_max | number  | **Required** | Maximum value on the rating scale (e.g., 5 for 5-star).    |
| count     | integer | Optional     | Number of reviews contributing to the rating.              |

______________________________________________________________________

### Retail Location

| Name    | Type                                                             | Requirement                       | Description                       |
| ------- | ---------------------------------------------------------------- | --------------------------------- | --------------------------------- |
| id      | string                                                           | **Required**; omitted in requests | Unique location identifier.       |
| name    | string                                                           | **Required**                      | Location name (e.g., store name). |
| address | [Postal Address](/draft/specification/reference/#postal-address) | Optional                          | Physical address of the location. |

______________________________________________________________________

### Search Filters

| Name       | Type                                                         | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ---------- | ------------------------------------------------------------ | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| categories | Array[string]                                                | Optional    | Filter by product categories (OR logic — matches products in any listed categories). Values match against the value field in product category entries. Valid values can be discovered from the categories field in search results, merchant documentation, or standard taxonomies that businesses may align with.                                                                                                                                                |
| price      | [Price Filter](/draft/specification/reference/#price-filter) | Optional    | Price range filter denominated in context.currency. When context.currency matches the presentment currency, businesses apply the filter directly. When it differs, businesses SHOULD convert filter values to the presentment currency before applying; if conversion is not supported, businesses MAY ignore the filter and SHOULD indicate this via a message. When context.currency is absent, filter denomination is ambiguous and businesses MAY ignore it. |

______________________________________________________________________

### Selected Option

| Name  | Type   | Requirement  | Description                                                                                                                                             |
| ----- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| name  | string | **Required** | Option name (e.g., 'Size').                                                                                                                             |
| id    | string | Optional     | Optional option value identifier from option_value.id. When present, the server SHOULD use it for matching; name and label remain required for display. |
| label | string | **Required** | Selected option label (e.g., 'Large').                                                                                                                  |

______________________________________________________________________

### Shipping Destination

| Name             | Type   | Requirement                        | Description                                                                                                                                                                                                                               |
| ---------------- | ------ | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| extended_address | string | Optional                           | An address extension such as an apartment number, C/O or alternative name.                                                                                                                                                                |
| street_address   | string | Optional                           | The street address.                                                                                                                                                                                                                       |
| address_locality | string | Optional                           | The locality in which the street address is, and which is in the region. For example, Mountain View.                                                                                                                                      |
| address_region   | string | Optional                           | The region in which the locality is, and which is in the country. Required for applicable countries (i.e. state in US, province in CA). For example, California or another appropriate first-level Administrative division.               |
| address_country  | string | Optional                           | The country. Recommended to be in 2-letter ISO 3166-1 alpha-2 format, for example "US". For backward compatibility, a 3-letter ISO 3166-1 alpha-3 country code such as "SGP" or a full country name such as "Singapore" can also be used. |
| postal_code      | string | Optional                           | The postal code. For example, 94043.                                                                                                                                                                                                      |
| first_name       | string | Optional                           | Optional. First name of the contact associated with the address.                                                                                                                                                                          |
| last_name        | string | Optional                           | Optional. Last name of the contact associated with the address.                                                                                                                                                                           |
| phone_number     | string | Optional                           | Optional. Phone number of the contact associated with the address.                                                                                                                                                                        |
| id               | string | **Required**; optional in requests | ID specific to this shipping destination.                                                                                                                                                                                                 |

______________________________________________________________________

### Signals

| Name               | Type   | Requirement | Description                                    |
| ------------------ | ------ | ----------- | ---------------------------------------------- |
| dev.ucp.buyer_ip   | string | Optional    | Client's IP address (IPv4 or IPv6).            |
| dev.ucp.user_agent | string | Optional    | Client's HTTP User-Agent header or equivalent. |

______________________________________________________________________

### Token Credential

| Name  | Type   | Requirement  | Description                                                                                  |
| ----- | ------ | ------------ | -------------------------------------------------------------------------------------------- |
| type  | string | **Required** | The credential type discriminator. Specific schemas will constrain this to a constant value. |
| type  | string | **Required** | The specific type of token produced by the handler (e.g., 'stripe_token').                   |
| token | string | **Required** | The token value.                                                                             |

______________________________________________________________________

### Total

| Name         | Type                                                           | Requirement                       | Description                                                                                                                                                                                                                                                                                 |
| ------------ | -------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                         | **Required**; omitted in requests | Cost category. Well-known values: subtotal, items_discount, discount, fulfillment, tax, fee, total. Businesses MAY use additional values.                                                                                                                                                   |
| display_text | string                                                         | Optional; omitted in requests     | Text to display against the amount. Should reflect appropriate method (e.g., 'Shipping', 'Delivery').                                                                                                                                                                                       |
| amount       | [Signed Amount](/draft/specification/reference/#signed-amount) | **Required**; omitted in requests | Monetary amount in the currency's minor unit as defined by ISO 4217. Refer to the currency's exponent to determine minor-to-major ratio (e.g., 2 for USD, 0 for JPY, 3 for KWD). May be negative — the sign is intrinsic to the value (e.g., discounts are negative, charges are positive). |

______________________________________________________________________

### Totals

Pricing breakdown provided by the business. MUST contain exactly one subtotal and one total entry. Detail types (tax, fee, discount, fulfillment) may appear multiple times for itemization. Platforms MUST render all entries in order using display_text and amount.

______________________________________________________________________

### Variant

| Name         | Type                                                                        | Requirement  | Description                                                                               |
| ------------ | --------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------- |
| id           | string                                                                      | **Required** | Global ID (GID) uniquely identifying this variant. Used as item.id in checkout.           |
| sku          | string                                                                      | Optional     | Business-assigned identifier for inventory and fulfillment.                               |
| barcodes     | Array[object]                                                               | Optional     | Industry-standard product identifiers for cross-reference and correlation.                |
| handle       | string                                                                      | Optional     | URL-safe variant handle/slug.                                                             |
| title        | string                                                                      | **Required** | Variant display title (e.g., 'Blue / Large').                                             |
| description  | [Description](/draft/specification/reference/#description)                  | **Required** | Variant description in one or more formats.                                               |
| url          | string                                                                      | Optional     | Canonical variant page URL.                                                               |
| categories   | Array\[[Category](/draft/specification/reference/#category)\]               | Optional     | Variant categories with optional taxonomy identifiers.                                    |
| price        | [Price](/draft/specification/reference/#price)                              | **Required** | Current selling price.                                                                    |
| list_price   | [Price](/draft/specification/reference/#price)                              | Optional     | List price before discounts (for strikethrough display).                                  |
| unit_price   | object                                                                      | Optional     | Price per standard unit of measurement. MAY be omitted when unit pricing does not apply.  |
| availability | [Availability](/draft/specification/reference/#availability)                | Optional     | Variant availability for purchase.                                                        |
| options      | Array\[[Selected Option](/draft/specification/reference/#selected-option)\] | Optional     | Option values that define this variant (e.g., Color: Blue, Size: Large).                  |
| media        | Array\[[Media](/draft/specification/reference/#media)\]                     | Optional     | Variant media (images, videos, 3D models). First item is the featured media for listings. |
| rating       | [Rating](/draft/specification/reference/#rating)                            | Optional     | Variant rating.                                                                           |
| tags         | Array[string]                                                               | Optional     | Variant tags for categorization and search.                                               |
| metadata     | object                                                                      | Optional     | Business-defined custom data extending the standard variant model.                        |
| seller       | object                                                                      | Optional     | Optional seller context for this variant.                                                 |

______________________________________________________________________

### Selected Payment Instrument

A payment instrument with selection state.

| Name            | Type    | Requirement  | Description                                                                                                                                                  |
| --------------- | ------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| id              | string  | **Required** | A unique identifier for this instrument instance, assigned by the platform.                                                                                  |
| handler_id      | string  | **Required** | The unique identifier for the handler instance that produced this instrument. This corresponds to the 'id' field in the Payment Handler definition.          |
| type            | string  | **Required** | The broad category of the instrument (e.g., 'card', 'tokenized_card'). Specific schemas will constrain this to a constant value.                             |
| billing_address | object  | Optional     | The billing address associated with this payment method.                                                                                                     |
| credential      | object  | Optional     | The base definition for any payment credential. Handlers define specific credential types.                                                                   |
| display         | object  | Optional     | Display information for this payment instrument. Each payment instrument schema defines its specific display properties, as outlined by the payment handler. |
| selected        | boolean | Optional     | Whether this instrument is selected by the user.                                                                                                             |

### Pagination Request

Pagination parameters for requests.

| Name   | Type    | Requirement | Description                                                        |
| ------ | ------- | ----------- | ------------------------------------------------------------------ |
| cursor | string  | Optional    | Opaque cursor from previous response.                              |
| limit  | integer | Optional    | Requested page size. Implementations MAY clamp to a lower maximum. |

### Pagination Response

Pagination information in responses.

| Name          | Type    | Requirement  | Description                                                                           |
| ------------- | ------- | ------------ | ------------------------------------------------------------------------------------- |
| cursor        | string  | Optional     | Cursor to fetch the next page of results. MUST be present when has_next_page is true. |
| has_next_page | boolean | **Required** | Whether more results are available.                                                   |
| total_count   | integer | Optional     | Total number of matching items, if available.                                         |

### Error Code

Error code identifying the type of error. Standard errors are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.

### Warning Code

Warning code identifying the type of warning. Standard codes are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.

### Info Code

Info code identifying the type of informational message. Standard codes are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.

## Extension Schemas

### AP2 Mandate Extension

#### Merchant Authorization

JWS Detached Content signature (RFC 7515 Appendix F) over the checkout response body (excluding ap2 field). Format: `<base64url-header>..<base64url-signature>`. The header MUST contain 'alg' (ES256/ES384/ES512) and 'kid' claims. The signature covers both the header and JCS-canonicalized checkout payload.

**Pattern:** `^[A-Za-z0-9_-]+\.\.[A-Za-z0-9_-]+$`

#### Checkout Mandate

SD-JWT+kb credential in `ap2.checkout_mandate`. Proving user authorization for the checkout. Contains the full checkout including `ap2.merchant_authorization`.

**Pattern:** `^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+(~[A-Za-z0-9_-]+)*$`

#### Ap2 With Merchant Authorization

AP2 extension data including merchant authorization.

| Name                   | Type   | Requirement | Description                                                |
| ---------------------- | ------ | ----------- | ---------------------------------------------------------- |
| merchant_authorization | string | Optional    | Merchant's signature proving checkout terms are authentic. |

#### Ap2 With Checkout Mandate

AP2 extension data including checkout mandate.

| Name             | Type   | Requirement | Description                                      |
| ---------------- | ------ | ----------- | ------------------------------------------------ |
| checkout_mandate | string | Optional    | SD-JWT+kb proving user authorized this checkout. |

#### Checkout with AP2 Mandate

Checkout extended with AP2 mandate support.

| Name         | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | any           | **Required** | UCP metadata for checkout responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| id           | string        | **Required** | Unique identifier of the checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| line_items   | Array[object] | **Required** | List of line items being checked out.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| buyer        | object        | Optional     | Representation of the buyer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| context      | object        | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals      | object        | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution  | object        | Optional     | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| status       | string        | **Required** | Checkout state indicating the current phase and required processing. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                     |
| currency     | string        | **Required** | ISO 4217 currency code reflecting the merchant's market determination. Derived from address, context, and geo IP—buyers provide signals, merchants determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| totals       | Array[Total]  | **Required** | Different cart totals.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| actions      | object        | Optional     | Outstanding extension-defined Actions for this checkout.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| messages     | Array[object] | Optional     | List of messages with error and info about the checkout session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| links        | Array[object] | **Required** | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies     | Array[object] | Optional     | Policies (e.g., return/refund terms) that apply to the items in this checkout. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| expires_at   | string        | Optional     | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| continue_url | string        | Optional     | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| payment      | object        | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| order        | object        | Optional     | Details about an order created for this checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ap2          | any           | Optional     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

#### AP2 Error Code

Error codes specific to AP2 mandate verification.

**Enum:** `mandate_required`, `agent_missing_key`, `mandate_invalid_signature`, `mandate_expired`, `mandate_scope_mismatch`, `merchant_authorization_invalid`, `merchant_authorization_missing`

______________________________________________________________________

### Buyer Consent Extension

#### Consent Purpose

A buyer's consent decision for a purpose (e.g., marketing, analytics). Carries the current binary state, its source (business default or platform-captured buyer decision), human-readable context, and optional refinements scoping the decision to specific channels, vendors, or programs.

| Name        | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                               |
| ----------- | ------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| granted     | boolean       | **Required** | Whether consent has been granted for this purpose. The `source` field identifies who asserted this state (business default or platform-captured buyer preference).                                                                                                                                                                                        |
| source      | string        | **Required** | Identifies the party that asserted the current `granted` value. `business` means the value reflects the business's default policy; `platform` means the value reflects an explicit buyer decision captured by the platform. **Enum:** `business`, `platform`                                                                                              |
| description | string        | **Required** | Human-readable description of what the buyer is consenting to (e.g., 'Promotional communications across all channels').                                                                                                                                                                                                                                   |
| links       | Array[object] | Optional     | Optional links providing context (e.g., privacy policy, terms).                                                                                                                                                                                                                                                                                           |
| segments    | object        | Optional     | Optional refinements scoping this purpose to specific channels, vendors, or programs. Keys are reverse-DNS identifiers. UCP currently defines two well-known segment identifiers under `dev.ucp.consent.marketing`: `dev.ucp.consent.marketing.email`, `dev.ucp.consent.marketing.sms`. Other segments follow vendor or merchant reverse-DNS conventions. |

#### Consent Segment

A buyer's consent decision for a specific refinement of a parent purpose (e.g., email marketing under the marketing purpose). Overrides the parent's `granted` value for this scope. Segments do not nest further.

| Name        | Type          | Requirement  | Description                                                                                                                                                                                                                                                                   |
| ----------- | ------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| granted     | boolean       | **Required** | Whether consent has been granted for this segment. Overrides the parent purpose's `granted` value for this specific scope.                                                                                                                                                    |
| source      | string        | **Required** | Identifies the party that asserted the current `granted` value for this segment. `business` means the value reflects the business's default policy; `platform` means the value reflects an explicit buyer decision captured by the platform. **Enum:** `business`, `platform` |
| description | string        | **Required** | Human-readable description of what the buyer is consenting to within this segment (e.g., 'Promotional emails and exclusive offers').                                                                                                                                          |
| links       | Array[object] | Optional     | Optional segment-specific links (e.g., channel terms or privacy disclosures).                                                                                                                                                                                                 |

#### Consent

Per-purpose consent. Keys are reverse-DNS purpose identifiers. UCP defines four well-known purposes: `dev.ucp.consent.marketing`, `dev.ucp.consent.analytics`, `dev.ucp.consent.preferences`, `dev.ucp.consent.sale_or_sharing`. Vendors and merchants may define additional purposes under their own reverse-DNS namespace.

#### Buyer with Consent

Buyer object extended with per-purpose consent.

| Name         | Type   | Requirement | Description                                                            |
| ------------ | ------ | ----------- | ---------------------------------------------------------------------- |
| first_name   | string | Optional    | First name of the buyer.                                               |
| last_name    | string | Optional    | Last name of the buyer.                                                |
| email        | string | Optional    | Email of the buyer.                                                    |
| phone_number | string | Optional    | E.164 standard.                                                        |
| consent      | object | Optional    | Per-purpose consent decisions and business-advertised consent options. |

#### Cart with Buyer Consent

Cart extended with buyer consent.

| Name         | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | any           | **Required** | UCP metadata for cart responses. No payment handlers needed pre-checkout.                                                                                                                                                                                                                                                                                                                               |
| id           | string        | **Required** | Unique cart identifier.                                                                                                                                                                                                                                                                                                                                                                                 |
| line_items   | Array[object] | **Required** | Cart line items. Same structure as checkout. Full replacement on update.                                                                                                                                                                                                                                                                                                                                |
| context      | object        | Optional     | Buyer signals for localization (country, region, postal_code). Merchant uses for pricing, availability, currency. Falls back to geo-IP if omitted.                                                                                                                                                                                                                                                      |
| signals      | object        | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace. |
| attribution  | object        | Optional     | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                        |
| buyer        | object        | Optional     | Optional buyer information for personalized estimates.                                                                                                                                                                                                                                                                                                                                                  |
| currency     | string        | **Required** | ISO 4217 currency code. Determined by merchant based on context or geo-IP.                                                                                                                                                                                                                                                                                                                              |
| totals       | Array[Total]  | **Required** | Estimated cost breakdown. May be partial if shipping/tax not yet calculable.                                                                                                                                                                                                                                                                                                                            |
| actions      | object        | Optional     | Outstanding extension-defined Actions for this cart.                                                                                                                                                                                                                                                                                                                                                    |
| messages     | Array[object] | Optional     | Validation messages, warnings, or informational notices.                                                                                                                                                                                                                                                                                                                                                |
| links        | Array[object] | Optional     | Optional merchant links (policies, FAQs).                                                                                                                                                                                                                                                                                                                                                               |
| policies     | Array[object] | Optional     | Policies (e.g., return/refund terms) that apply to the items in this cart. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                |
| continue_url | string        | Optional     | URL for cart handoff and session recovery. Enables sharing and human-in-the-loop flows.                                                                                                                                                                                                                                                                                                                 |
| expires_at   | string        | Optional     | Cart expiry timestamp (RFC 3339). Optional.                                                                                                                                                                                                                                                                                                                                                             |
| buyer        | any           | Optional     | Buyer with consent tracking.                                                                                                                                                                                                                                                                                                                                                                            |

#### Checkout with Buyer Consent

Checkout extended with buyer consent.

| Name         | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | any           | **Required** | UCP metadata for checkout responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| id           | string        | **Required** | Unique identifier of the checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| line_items   | Array[object] | **Required** | List of line items being checked out.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| buyer        | object        | Optional     | Representation of the buyer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| context      | object        | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals      | object        | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution  | object        | Optional     | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| status       | string        | **Required** | Checkout state indicating the current phase and required processing. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                     |
| currency     | string        | **Required** | ISO 4217 currency code reflecting the merchant's market determination. Derived from address, context, and geo IP—buyers provide signals, merchants determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| totals       | Array[Total]  | **Required** | Different cart totals.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| actions      | object        | Optional     | Outstanding extension-defined Actions for this checkout.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| messages     | Array[object] | Optional     | List of messages with error and info about the checkout session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| links        | Array[object] | **Required** | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies     | Array[object] | Optional     | Policies (e.g., return/refund terms) that apply to the items in this checkout. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| expires_at   | string        | Optional     | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| continue_url | string        | Optional     | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| payment      | object        | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| order        | object        | Optional     | Details about an order created for this checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| buyer        | any           | Optional     | Buyer with consent tracking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

______________________________________________________________________

### Discount Extension

#### Allocation

Breakdown of how a discount amount was allocated to a specific target.

| Name   | Type    | Requirement  | Description                                                                       |
| ------ | ------- | ------------ | --------------------------------------------------------------------------------- |
| path   | string  | **Required** | JSONPath to the allocation target (e.g., '$.line_items[0]', '$.totals.shipping'). |
| amount | integer | **Required** | Amount allocated to this target in ISO 4217 minor units.                          |

#### Applied Discount

A discount that was successfully applied.

| Name        | Type          | Requirement  | Description                                                                                                                                                                        |
| ----------- | ------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| code        | string        | Optional     | The discount code. Omitted for automatic discounts.                                                                                                                                |
| title       | string        | **Required** | Human-readable discount name (e.g., 'Summer Sale 20% Off').                                                                                                                        |
| amount      | integer       | **Required** | Total discount amount in ISO 4217 minor units.                                                                                                                                     |
| automatic   | boolean       | Optional     | True if applied automatically by merchant rules (no code required).                                                                                                                |
| method      | string        | Optional     | Allocation method. 'each' = applied independently per item. 'across' = split proportionally by value. **Enum:** `each`, `across`                                                   |
| priority    | integer       | Optional     | Stacking order for discount calculation. Lower numbers applied first (1 = first).                                                                                                  |
| provisional | boolean       | Optional     | True if this discount requires additional verification.                                                                                                                            |
| eligibility | string        | Optional     | The eligibility claim accepted by the Business for this discount. Corresponds to a value from context.eligibility. Omitted for code-based and non-eligibility automatic discounts. |
| allocations | Array[object] | Optional     | Breakdown of where this discount was allocated. Sum of allocation amounts equals total amount.                                                                                     |

#### Discounts Object

Discount codes input and applied discounts output.

| Name    | Type          | Requirement | Description                                                                                                |
| ------- | ------------- | ----------- | ---------------------------------------------------------------------------------------------------------- |
| codes   | Array[string] | Optional    | Discount codes to apply. Case-insensitive. Replaces previously submitted codes. Send empty array to clear. |
| applied | Array[object] | Optional    | Discounts successfully applied (code-based and automatic).                                                 |

#### Cart with Discount

Cart extended with discount capability.

| Name         | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | any           | **Required** | UCP metadata for cart responses. No payment handlers needed pre-checkout.                                                                                                                                                                                                                                                                                                                               |
| id           | string        | **Required** | Unique cart identifier.                                                                                                                                                                                                                                                                                                                                                                                 |
| line_items   | Array[object] | **Required** | Cart line items. Same structure as checkout. Full replacement on update.                                                                                                                                                                                                                                                                                                                                |
| context      | object        | Optional     | Buyer signals for localization (country, region, postal_code). Merchant uses for pricing, availability, currency. Falls back to geo-IP if omitted.                                                                                                                                                                                                                                                      |
| signals      | object        | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace. |
| attribution  | object        | Optional     | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                        |
| buyer        | object        | Optional     | Optional buyer information for personalized estimates.                                                                                                                                                                                                                                                                                                                                                  |
| currency     | string        | **Required** | ISO 4217 currency code. Determined by merchant based on context or geo-IP.                                                                                                                                                                                                                                                                                                                              |
| totals       | Array[Total]  | **Required** | Estimated cost breakdown. May be partial if shipping/tax not yet calculable.                                                                                                                                                                                                                                                                                                                            |
| actions      | object        | Optional     | Outstanding extension-defined Actions for this cart.                                                                                                                                                                                                                                                                                                                                                    |
| messages     | Array[object] | Optional     | Validation messages, warnings, or informational notices.                                                                                                                                                                                                                                                                                                                                                |
| links        | Array[object] | Optional     | Optional merchant links (policies, FAQs).                                                                                                                                                                                                                                                                                                                                                               |
| policies     | Array[object] | Optional     | Policies (e.g., return/refund terms) that apply to the items in this cart. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                |
| continue_url | string        | Optional     | URL for cart handoff and session recovery. Enables sharing and human-in-the-loop flows.                                                                                                                                                                                                                                                                                                                 |
| expires_at   | string        | Optional     | Cart expiry timestamp (RFC 3339). Optional.                                                                                                                                                                                                                                                                                                                                                             |
| discounts    | object        | Optional     | Discount codes input and applied discounts output.                                                                                                                                                                                                                                                                                                                                                      |

#### Checkout with Discount

Checkout extended with discount capability.

| Name         | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | any           | **Required** | UCP metadata for checkout responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| id           | string        | **Required** | Unique identifier of the checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| line_items   | Array[object] | **Required** | List of line items being checked out.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| buyer        | object        | Optional     | Representation of the buyer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| context      | object        | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals      | object        | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution  | object        | Optional     | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| status       | string        | **Required** | Checkout state indicating the current phase and required processing. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                     |
| currency     | string        | **Required** | ISO 4217 currency code reflecting the merchant's market determination. Derived from address, context, and geo IP—buyers provide signals, merchants determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| totals       | Array[Total]  | **Required** | Different cart totals.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| actions      | object        | Optional     | Outstanding extension-defined Actions for this checkout.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| messages     | Array[object] | Optional     | List of messages with error and info about the checkout session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| links        | Array[object] | **Required** | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies     | Array[object] | Optional     | Policies (e.g., return/refund terms) that apply to the items in this checkout. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| expires_at   | string        | Optional     | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| continue_url | string        | Optional     | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| payment      | object        | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| order        | object        | Optional     | Details about an order created for this checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| discounts    | object        | Optional     | Discount codes input and applied discounts output.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

______________________________________________________________________

### Fulfillment Extension

#### Fulfillment Option

A fulfillment option within a group (e.g., Standard Shipping $5, Express $15). Extends the fulfillment option base with cost and timing.

| Name                      | Type          | Requirement  | Description                                                                                                                                             |
| ------------------------- | ------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id                        | string        | **Required** | Unique identifier for this fulfillment option.                                                                                                          |
| title                     | string        | **Required** | Short label that distinguishes this option from its siblings (e.g. 'Standard', 'Express Shipping', 'Curbside Pickup').                                  |
| description               | object        | Optional     | Supplementary context for the title (e.g. 'Arrives in 4 business days', 'Arrives Dec 12-15 via FedEx'). Directly renderable; MUST NOT repeat the title. |
| carrier                   | string        | Optional     | Carrier name (for shipping).                                                                                                                            |
| earliest_fulfillment_time | string        | Optional     | Earliest fulfillment date.                                                                                                                              |
| latest_fulfillment_time   | string        | Optional     | Latest fulfillment date.                                                                                                                                |
| totals                    | Array[object] | **Required** | Fulfillment option totals breakdown.                                                                                                                    |

#### Fulfillment Group

A merchant-generated package/group of line items with fulfillment options.

| Name               | Type               | Requirement  | Description                                                            |
| ------------------ | ------------------ | ------------ | ---------------------------------------------------------------------- |
| id                 | string             | **Required** | Group identifier for referencing merchant-generated groups in updates. |
| line_item_ids      | Array[string]      | **Required** | Line item IDs included in this group/package.                          |
| options            | Array[object]      | Optional     | Available fulfillment options for this group.                          |
| selected_option_id | ['string', 'null'] | Optional     | ID of the selected fulfillment option for this group.                  |

#### Fulfillment Method

A fulfillment method with destinations and groups.

| Name                    | Type               | Requirement  | Description                                                                                                  |
| ----------------------- | ------------------ | ------------ | ------------------------------------------------------------------------------------------------------------ |
| id                      | string             | **Required** | Unique fulfillment method identifier.                                                                        |
| type                    | string             | **Required** | Fulfillment method type. Well-known values: `shipping`, `pickup`. Businesses MAY use additional values.      |
| line_item_ids           | Array[string]      | **Required** | Line item IDs fulfilled via this method.                                                                     |
| destinations            | Array[object]      | Optional     | Available destinations. For shipping: addresses. For pickup: retail locations.                               |
| selected_destination_id | ['string', 'null'] | Optional     | ID of the selected destination.                                                                              |
| groups                  | Array[object]      | Optional     | Fulfillment groups for selecting options. Agent sets selected_option_id on groups to choose shipping method. |

#### Fulfillment Available Method

Inventory availability hint for a fulfillment method type.

| Name           | Type               | Requirement  | Description                                                                                                                          |
| -------------- | ------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| type           | string             | **Required** | Fulfillment method type this availability applies to. Well-known values: `shipping`, `pickup`; businesses MAY use additional values. |
| line_item_ids  | Array[string]      | **Required** | Line items available for this fulfillment method.                                                                                    |
| fulfillable_on | ['string', 'null'] | Optional     | 'now' for immediate availability, or ISO 8601 date for future (preorders, transfers).                                                |
| description    | string             | Optional     | Human-readable availability info (e.g., 'Available for pickup at Downtown Store today').                                             |

#### Fulfillment

Container for fulfillment methods and availability.

| Name              | Type          | Requirement | Description                         |
| ----------------- | ------------- | ----------- | ----------------------------------- |
| methods           | Array[object] | Optional    | Fulfillment methods for cart items. |
| available_methods | Array[object] | Optional    | Inventory availability hints.       |

#### Catalog Fulfillment Method

A fulfillment method on a catalog variant: how the variant can be fulfilled, and its availability.

| Name         | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                  |
| ------------ | ------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string        | **Required** | Fulfillment method type. Well-known values: `shipping`, `pickup`. Businesses MAY use additional values.                                                                                                                                                                                                                                      |
| description  | object        | Optional     | Short buyer-facing summary (e.g. 'Ships in 2–4 business days').                                                                                                                                                                                                                                                                              |
| availability | object        | Optional     | Availability of this variant via this method at the specified or inferred location.                                                                                                                                                                                                                                                          |
| location     | string        | Optional     | The location resolved for this method, where appropriate (e.g. the pickup store or location), as a location id.                                                                                                                                                                                                                              |
| options      | Array[object] | Optional     | Fulfillment options for this method (e.g. Standard, Express) to describe per-choice details such as cost, time estimates, etc. Optional and selective: without a destination or full cart, a business SHOULD preview meaningful boundary options (e.g. cheapest, fastest); the full, high-resolution set is negotiated in cart and checkout. |

#### Catalog Fulfillment

How a catalog variant can be fulfilled. Mirrors checkout `fulfillment`.

| Name    | Type          | Requirement | Description                           |
| ------- | ------------- | ----------- | ------------------------------------- |
| methods | Array[object] | Optional    | Fulfillment methods for this variant. |

#### Fulfillment Variant

A catalog variant with fulfillment.

| Name         | Type          | Requirement  | Description                                                                               |
| ------------ | ------------- | ------------ | ----------------------------------------------------------------------------------------- |
| id           | string        | **Required** | Global ID (GID) uniquely identifying this variant. Used as item.id in checkout.           |
| sku          | string        | Optional     | Business-assigned identifier for inventory and fulfillment.                               |
| barcodes     | Array[object] | Optional     | Industry-standard product identifiers for cross-reference and correlation.                |
| handle       | string        | Optional     | URL-safe variant handle/slug.                                                             |
| title        | string        | **Required** | Variant display title (e.g., 'Blue / Large').                                             |
| description  | object        | **Required** | Variant description in one or more formats.                                               |
| url          | string        | Optional     | Canonical variant page URL.                                                               |
| categories   | Array[object] | Optional     | Variant categories with optional taxonomy identifiers.                                    |
| price        | object        | **Required** | Current selling price.                                                                    |
| list_price   | object        | Optional     | List price before discounts (for strikethrough display).                                  |
| unit_price   | object        | Optional     | Price per standard unit of measurement. MAY be omitted when unit pricing does not apply.  |
| availability | object        | Optional     | Variant availability for purchase.                                                        |
| options      | Array[object] | Optional     | Option values that define this variant (e.g., Color: Blue, Size: Large).                  |
| media        | Array[object] | Optional     | Variant media (images, videos, 3D models). First item is the featured media for listings. |
| rating       | object        | Optional     | Variant rating.                                                                           |
| tags         | Array[string] | Optional     | Variant tags for categorization and search.                                               |
| metadata     | object        | Optional     | Business-defined custom data extending the standard variant model.                        |
| seller       | object        | Optional     | Optional seller context for this variant.                                                 |
| fulfillment  | object        | Optional     | How a catalog variant can be fulfilled. Mirrors checkout `fulfillment`.                   |

#### Fulfillment Product

A catalog product whose variants are fulfillment-enriched. Used by search.

| Name             | Type           | Requirement  | Description                                                                                      |
| ---------------- | -------------- | ------------ | ------------------------------------------------------------------------------------------------ |
| id               | string         | **Required** | Global ID (GID) uniquely identifying this product.                                               |
| handle           | string         | Optional     | URL-safe slug for SEO-friendly URLs (e.g., 'blue-runner-pro'). Use id for stable API references. |
| title            | string         | **Required** | Product title.                                                                                   |
| description      | object         | **Required** | Product description in one or more formats.                                                      |
| url              | string         | Optional     | Canonical product page URL.                                                                      |
| categories       | Array[object]  | Optional     | Product categories with optional taxonomy identifiers.                                           |
| price_range      | object         | **Required** | Price range across all variants.                                                                 |
| list_price_range | object         | Optional     | List price range before discounts (for strikethrough display).                                   |
| media            | Array[object]  | Optional     | Product media (images, videos, 3D models). First item is the featured media for listings.        |
| options          | Array[object]  | Optional     | Product options (Size, Color, etc.).                                                             |
| variants         | Array[object]  | **Required** | Purchasable variants of this product. First item is the featured variant for listings.           |
| rating           | object         | Optional     | Aggregate product rating.                                                                        |
| tags             | Array[string]  | Optional     | Product tags for categorization and search.                                                      |
| metadata         | object         | Optional     | Business-defined custom data extending the standard product model.                               |
| variants         | Array[Variant] | **Required** |                                                                                                  |

#### Fulfillment Lookup Variant

A lookup variant (carrying input correlation) enriched with fulfillment.

| Name         | Type          | Requirement  | Description                                                                                                  |
| ------------ | ------------- | ------------ | ------------------------------------------------------------------------------------------------------------ |
| id           | string        | **Required** | Global ID (GID) uniquely identifying this variant. Used as item.id in checkout.                              |
| sku          | string        | Optional     | Business-assigned identifier for inventory and fulfillment.                                                  |
| barcodes     | Array[object] | Optional     | Industry-standard product identifiers for cross-reference and correlation.                                   |
| handle       | string        | Optional     | URL-safe variant handle/slug.                                                                                |
| title        | string        | **Required** | Variant display title (e.g., 'Blue / Large').                                                                |
| description  | object        | **Required** | Variant description in one or more formats.                                                                  |
| url          | string        | Optional     | Canonical variant page URL.                                                                                  |
| categories   | Array[object] | Optional     | Variant categories with optional taxonomy identifiers.                                                       |
| price        | object        | **Required** | Current selling price.                                                                                       |
| list_price   | object        | Optional     | List price before discounts (for strikethrough display).                                                     |
| unit_price   | object        | Optional     | Price per standard unit of measurement. MAY be omitted when unit pricing does not apply.                     |
| availability | object        | Optional     | Variant availability for purchase.                                                                           |
| options      | Array[object] | Optional     | Option values that define this variant (e.g., Color: Blue, Size: Large).                                     |
| media        | Array[object] | Optional     | Variant media (images, videos, 3D models). First item is the featured media for listings.                    |
| rating       | object        | Optional     | Variant rating.                                                                                              |
| tags         | Array[string] | Optional     | Variant tags for categorization and search.                                                                  |
| metadata     | object        | Optional     | Business-defined custom data extending the standard variant model.                                           |
| seller       | object        | Optional     | Optional seller context for this variant.                                                                    |
| inputs       | Array[object] | **Required** | Which request identifiers resolved to this variant, and how. Each entry maps a request ID to its match type. |
| fulfillment  | object        | Optional     | How a catalog variant can be fulfilled. Mirrors checkout `fulfillment`.                                      |

#### Fulfillment Lookup Product

A lookup product whose variants are fulfillment-enriched, preserving input correlation. Used by lookup.

| Name             | Type          | Requirement  | Description                                                                                      |
| ---------------- | ------------- | ------------ | ------------------------------------------------------------------------------------------------ |
| id               | string        | **Required** | Global ID (GID) uniquely identifying this product.                                               |
| handle           | string        | Optional     | URL-safe slug for SEO-friendly URLs (e.g., 'blue-runner-pro'). Use id for stable API references. |
| title            | string        | **Required** | Product title.                                                                                   |
| description      | object        | **Required** | Product description in one or more formats.                                                      |
| url              | string        | Optional     | Canonical product page URL.                                                                      |
| categories       | Array[object] | Optional     | Product categories with optional taxonomy identifiers.                                           |
| price_range      | object        | **Required** | Price range across all variants.                                                                 |
| list_price_range | object        | Optional     | List price range before discounts (for strikethrough display).                                   |
| media            | Array[object] | Optional     | Product media (images, videos, 3D models). First item is the featured media for listings.        |
| options          | Array[object] | Optional     | Product options (Size, Color, etc.).                                                             |
| variants         | Array[object] | **Required** | Purchasable variants of this product. First item is the featured variant for listings.           |
| rating           | object        | Optional     | Aggregate product rating.                                                                        |
| tags             | Array[string] | Optional     | Product tags for categorization and search.                                                      |
| metadata         | object        | Optional     | Business-defined custom data extending the standard product model.                               |
| variants         | Array[object] | **Required** |                                                                                                  |

#### Fulfillment Detail Product

A get_product detail product (carrying selected/options availability signals) whose variants are fulfillment-enriched. Used by get_product.

| Name     | Type           | Requirement | Description                                                                                                                                                                                          |
| -------- | -------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| selected | Array[object]  | Optional    | Effective option selections that anchor the featured variant and availability signals. Required when the product has configurable options; may be empty or omitted for products with no option axes. |
| options  | Array[object]  | Optional    | Product options with availability signals relative to the effective selections.                                                                                                                      |
| variants | Array[Variant] | Optional    |                                                                                                                                                                                                      |

#### Fulfillment Search Filters

Catalog filters extended with a fulfillment destination filter and a method-type filter.

| Name        | Type          | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ----------- | ------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| categories  | Array[string] | Optional    | Filter by product categories (OR logic — matches products in any listed categories). Values match against the value field in product category entries. Valid values can be discovered from the categories field in search results, merchant documentation, or standard taxonomies that businesses may align with.                                                                                                                                                |
| price       | object        | Optional    | Price range filter denominated in context.currency. When context.currency matches the presentment currency, businesses apply the filter directly. When it differs, businesses SHOULD convert filter values to the presentment currency before applying; if conversion is not supported, businesses MAY ignore the filter and SHOULD indicate this via a message. When context.currency is absent, filter denomination is ambiguous and businesses MAY ignore it. |
| fulfills_to | object        | Optional    | Where the order is fulfilled to — may differ from the buyer's `context` location (e.g. a gift). A `location` id, or a coarse address (`address_country`/`address_region`/`postal_code`). Restricts results to what can be fulfilled there and seeds method `availability`. Supersedes `context`.                                                                                                                                                                 |
| methods     | Array[string] | Optional    | Restrict results to these fulfillment method types (e.g. ["pickup"]). Well-known values: `shipping`, `pickup`.                                                                                                                                                                                                                                                                                                                                                   |

#### Fulfillment Search Request

| Name        | Type   | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------- | ------ | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| query       | string | Optional    | Free-text search query.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context     | object | Optional    | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals     | object | Optional    | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution | object | Optional    | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| filters     | object | Optional    | Filter criteria to narrow search results. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| pagination  | object | Optional    | Pagination parameters for requests.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| filters     | any    | Optional    | Catalog filters extended with a fulfillment destination filter and a method-type filter.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

#### Fulfillment Search Response

| Name       | Type           | Requirement  | Description                                                                                                                                                                                            |
| ---------- | -------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ucp        | any            | **Required** | UCP metadata for catalog responses.                                                                                                                                                                    |
| products   | Array[object]  | **Required** | Products matching the search criteria.                                                                                                                                                                 |
| pagination | object         | Optional     | Pagination information in responses.                                                                                                                                                                   |
| actions    | object         | Optional     | Outstanding extension-defined Actions for this catalog search response.                                                                                                                                |
| messages   | Array[object]  | Optional     | Errors, warnings, or informational messages about the search results.                                                                                                                                  |
| policies   | Array[object]  | Optional     | Policies (e.g., return/refund terms) that apply to the products in these search results. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`. |
| products   | Array[Product] | **Required** |                                                                                                                                                                                                        |

#### Fulfillment Lookup Request

| Name        | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------- | ------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ids         | Array[string] | **Required** | Identifiers to lookup. Implementations MUST support product ID and variant ID; MAY support secondary identifiers (SKU, handle, etc.).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| filters     | object        | Optional     | Filter criteria to narrow returned products and variants. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context     | object        | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals     | object        | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution | object        | Optional     | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| filters     | any           | Optional     | Catalog filters extended with a fulfillment destination filter and a method-type filter.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

#### Fulfillment Lookup Response

| Name     | Type           | Requirement  | Description                                                                                                                                                                                     |
| -------- | -------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp      | any            | **Required** | UCP metadata for catalog responses.                                                                                                                                                             |
| products | Array[Product] | **Required** | Products matching the requested identifiers. May contain fewer items if some identifiers not found, or more if identifiers match multiple products.                                             |
| actions  | object         | Optional     | Outstanding extension-defined Actions for this catalog lookup response.                                                                                                                         |
| messages | Array[object]  | Optional     | Errors, warnings, or informational messages about the requested items.                                                                                                                          |
| policies | Array[object]  | Optional     | Policies (e.g., return/refund terms) that apply to the products in this response. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`. |
| products | Array[Product] | **Required** |                                                                                                                                                                                                 |

#### Fulfillment Get Product Request

| Name        | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------- | ------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string        | **Required** | Product or variant identifier. Implementations MUST support product ID and variant ID.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| selected    | Array[object] | Optional     | Partial or full option selections for interactive variant narrowing. When provided, response option values include availability signals (available, exists) relative to these selections.                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| preferences | Array[string] | Optional     | Option names in relaxation priority order. When no exact variant matches all selections, the server drops options from the end of this list first. E.g., ['Color', 'Size'] keeps Color and relaxes Size.                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| filters     | object        | Optional     | Filter criteria to narrow returned variants. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| context     | object        | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals     | object        | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution | object        | Optional     | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| filters     | any           | Optional     | Catalog filters extended with a fulfillment destination filter and a method-type filter.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

#### Fulfillment Get Product Response

| Name     | Type          | Requirement  | Description                                                                                                                                                                    |
| -------- | ------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ucp      | any           | **Required** | UCP metadata for catalog responses.                                                                                                                                            |
| product  | object        | **Required** | The requested product with full detail. Singular — this is a single-resource operation.                                                                                        |
| actions  | object        | Optional     | Outstanding extension-defined Actions for this product response.                                                                                                               |
| messages | Array[object] | Optional     | Warnings or informational messages about the product (e.g., price recently changed, limited availability).                                                                     |
| policies | Array[object] | Optional     | Policies (e.g., return/refund terms) that apply to this product. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`. |
| product  | any           | **Required** | A get_product detail product (carrying selected/options availability signals) whose variants are fulfillment-enriched. Used by get_product.                                    |

#### Dev.Ucp.Shopping.Catalog.Search

*No properties defined.*

#### Dev.Ucp.Shopping.Catalog.Lookup

*No properties defined.*

#### Checkout with Fulfillment

Checkout extended with hierarchical fulfillment.

| Name         | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | any           | **Required** | UCP metadata for checkout responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| id           | string        | **Required** | Unique identifier of the checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| line_items   | Array[object] | **Required** | List of line items being checked out.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| buyer        | object        | Optional     | Representation of the buyer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| context      | object        | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals      | object        | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution  | object        | Optional     | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| status       | string        | **Required** | Checkout state indicating the current phase and required processing. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                     |
| currency     | string        | **Required** | ISO 4217 currency code reflecting the merchant's market determination. Derived from address, context, and geo IP—buyers provide signals, merchants determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| totals       | Array[Total]  | **Required** | Different cart totals.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| actions      | object        | Optional     | Outstanding extension-defined Actions for this checkout.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| messages     | Array[object] | Optional     | List of messages with error and info about the checkout session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| links        | Array[object] | **Required** | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies     | Array[object] | Optional     | Policies (e.g., return/refund terms) that apply to the items in this checkout. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| expires_at   | string        | Optional     | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| continue_url | string        | Optional     | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| payment      | object        | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| order        | object        | Optional     | Details about an order created for this checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| fulfillment  | object        | Optional     | Fulfillment details.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |

#### Dev.Ucp.Shopping.Fulfillment

*No properties defined.*

______________________________________________________________________

### Split Payments Extension

#### Instrument Group

A constraint within an allowed combination that defines which instrument types can fill this group and how many are permitted.

| Name  | Type          | Requirement  | Description                                                                                                   |
| ----- | ------------- | ------------ | ------------------------------------------------------------------------------------------------------------- |
| types | Array[string] | **Required** | Instrument types accepted by this group (OR logic). Any listed type qualifies.                                |
| min   | integer       | Optional     | Minimum number of instruments required from this group. Defaults to 0 (optional).                             |
| max   | integer       | Optional     | Maximum number of instruments allowed from this group. Defaults to 1. MUST be greater than or equal to `min`. |

#### Payment Instrument (Split Payments)

Payment instrument extended with an optional per-instrument amount for split payments.

| Name            | Type    | Requirement  | Description                                                                                                                                                                                                                                                 |
| --------------- | ------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id              | string  | **Required** | A unique identifier for this instrument instance, assigned by the platform.                                                                                                                                                                                 |
| handler_id      | string  | **Required** | The unique identifier for the handler instance that produced this instrument. This corresponds to the 'id' field in the Payment Handler definition.                                                                                                         |
| type            | string  | **Required** | The broad category of the instrument (e.g., 'card', 'tokenized_card'). Specific schemas will constrain this to a constant value.                                                                                                                            |
| billing_address | object  | Optional     | The billing address associated with this payment method.                                                                                                                                                                                                    |
| credential      | object  | Optional     | The base definition for any payment credential. Handlers define specific credential types.                                                                                                                                                                  |
| display         | object  | Optional     | Display information for this payment instrument. Each payment instrument schema defines its specific display properties, as outlined by the payment handler.                                                                                                |
| amount          | integer | Optional     | Contribution amount for this instrument in `checkout.currency` minor units (ISO 4217). On request: the platform's requested contribution (omit for open-amount). On response: the actual amount authorized or charged (omitted when not finally processed). |

#### Checkout with Split Payments

Checkout extended with split payment instrument amounts.

| Name         | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | any           | **Required** | UCP metadata for checkout responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| id           | string        | **Required** | Unique identifier of the checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| line_items   | Array[object] | **Required** | List of line items being checked out.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| buyer        | object        | Optional     | Representation of the buyer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| context      | object        | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals      | object        | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution  | object        | Optional     | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| status       | string        | **Required** | Checkout state indicating the current phase and required processing. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                     |
| currency     | string        | **Required** | ISO 4217 currency code reflecting the merchant's market determination. Derived from address, context, and geo IP—buyers provide signals, merchants determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| totals       | Array[Total]  | **Required** | Different cart totals.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| actions      | object        | Optional     | Outstanding extension-defined Actions for this checkout.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| messages     | Array[object] | Optional     | List of messages with error and info about the checkout session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| links        | Array[object] | **Required** | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies     | Array[object] | Optional     | Policies (e.g., return/refund terms) that apply to the items in this checkout. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| expires_at   | string        | Optional     | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| continue_url | string        | Optional     | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| payment      | object        | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| order        | object        | Optional     | Details about an order created for this checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| payment      | object        | Optional     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

#### Dev.Ucp.Shopping.Split Payments

*No properties defined.*

______________________________________________________________________

## UCP Metadata

The following schemas define the structure of UCP metadata used in discovery and responses.

### Platform Discovery Profile

The top-level structure of a platform profile document (hosted at a URI advertised by the platform).

Full UCP metadata for platform-level configuration. Hosted at a URI advertised by the platform in request headers.

| Name             | Type   | Requirement  | Description                                                                 |
| ---------------- | ------ | ------------ | --------------------------------------------------------------------------- |
| version          | string | **Required** | UCP version in YYYY-MM-DD format.                                           |
| status           | string | Optional     | Application-level status of the UCP operation. **Enum:** `success`, `error` |
| services         | object | **Required** | Service registry keyed by reverse-domain name.                              |
| capabilities     | object | Optional     | Capability registry keyed by reverse-domain name.                           |
| payment_handlers | object | **Required** | Payment handler registry keyed by reverse-domain name.                      |
| services         | any    | **Required** |                                                                             |
| capabilities     | any    | Optional     |                                                                             |
| payment_handlers | any    | **Required** |                                                                             |

### Business Discovery Profile

The top-level structure of a business discovery document (`/.well-known/ucp`).

UCP metadata for business/merchant-level configuration. Subset of platform schema with business-specific settings.

| Name               | Type   | Requirement  | Description                                                                                                                                                                                                                                                                                          |
| ------------------ | ------ | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| version            | string | **Required** | UCP version in YYYY-MM-DD format.                                                                                                                                                                                                                                                                    |
| status             | string | Optional     | Application-level status of the UCP operation. **Enum:** `success`, `error`                                                                                                                                                                                                                          |
| services           | object | **Required** | Service registry keyed by reverse-domain name.                                                                                                                                                                                                                                                       |
| capabilities       | object | Optional     | Capability registry keyed by reverse-domain name.                                                                                                                                                                                                                                                    |
| payment_handlers   | object | **Required** | Payment handler registry keyed by reverse-domain name.                                                                                                                                                                                                                                               |
| supported_versions | object | Optional     | Previous protocol versions this business supports, mapped to profile URIs. Businesses that support older protocol versions SHOULD advertise each version and link to its profile. Each URI points to a complete, self-contained profile for that version. When omitted, only `version` is supported. |
| services           | any    | **Required** |                                                                                                                                                                                                                                                                                                      |
| capabilities       | any    | Optional     |                                                                                                                                                                                                                                                                                                      |
| payment_handlers   | any    | **Required** |                                                                                                                                                                                                                                                                                                      |

### Checkout Response Metadata

The `ucp` object included in checkout responses.

UCP metadata for checkout responses.

| Name             | Type   | Requirement  | Description                                                                 |
| ---------------- | ------ | ------------ | --------------------------------------------------------------------------- |
| version          | string | **Required** | UCP version in YYYY-MM-DD format.                                           |
| status           | string | Optional     | Application-level status of the UCP operation. **Enum:** `success`, `error` |
| services         | object | Optional     | Service registry keyed by reverse-domain name.                              |
| capabilities     | object | Optional     | Capability registry keyed by reverse-domain name.                           |
| payment_handlers | object | **Required** | Payment handler registry keyed by reverse-domain name.                      |
| services         | any    | Optional     |                                                                             |
| capabilities     | any    | Optional     |                                                                             |
| payment_handlers | any    | **Required** |                                                                             |

### Cart Response Metadata

The `ucp` object included in cart responses.

UCP metadata for cart responses. No payment handlers needed pre-checkout.

| Name             | Type   | Requirement  | Description                                                                 |
| ---------------- | ------ | ------------ | --------------------------------------------------------------------------- |
| version          | string | **Required** | UCP version in YYYY-MM-DD format.                                           |
| status           | string | Optional     | Application-level status of the UCP operation. **Enum:** `success`, `error` |
| services         | object | Optional     | Service registry keyed by reverse-domain name.                              |
| capabilities     | object | Optional     | Capability registry keyed by reverse-domain name.                           |
| payment_handlers | object | Optional     | Payment handler registry keyed by reverse-domain name.                      |
| capabilities     | any    | Optional     |                                                                             |

### Catalog Response Metadata

The `ucp` object included in catalog responses.

UCP metadata for catalog responses.

| Name             | Type   | Requirement  | Description                                                                 |
| ---------------- | ------ | ------------ | --------------------------------------------------------------------------- |
| version          | string | **Required** | UCP version in YYYY-MM-DD format.                                           |
| status           | string | Optional     | Application-level status of the UCP operation. **Enum:** `success`, `error` |
| services         | object | Optional     | Service registry keyed by reverse-domain name.                              |
| capabilities     | object | Optional     | Capability registry keyed by reverse-domain name.                           |
| payment_handlers | object | Optional     | Payment handler registry keyed by reverse-domain name.                      |
| capabilities     | any    | Optional     |                                                                             |

### Order Response Metadata

The `ucp` object included in order responses or events.

UCP metadata for order responses. No payment handlers needed post-purchase.

| Name             | Type   | Requirement  | Description                                                                 |
| ---------------- | ------ | ------------ | --------------------------------------------------------------------------- |
| version          | string | **Required** | UCP version in YYYY-MM-DD format.                                           |
| status           | string | Optional     | Application-level status of the UCP operation. **Enum:** `success`, `error` |
| services         | object | Optional     | Service registry keyed by reverse-domain name.                              |
| capabilities     | object | Optional     | Capability registry keyed by reverse-domain name.                           |
| payment_handlers | object | Optional     | Payment handler registry keyed by reverse-domain name.                      |
| capabilities     | any    | Optional     |                                                                             |

### Capability

This object describes a single capability or extension. It appears in the `capabilities` array in discovery profiles and responses, with slightly different required fields in each context.

#### Capability (Discovery)

As seen in discovery profiles.

Full capability declaration for platform-level discovery. Includes spec/schema URLs for agent fetching.

| Name    | Type                       | Requirement  | Description                                                                                                                     |
| ------- | -------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| version | string                     | **Required** | Entity version in YYYY-MM-DD format.                                                                                            |
| spec    | string                     | **Required** | URL to human-readable specification document.                                                                                   |
| schema  | string                     | **Required** | URL to JSON Schema defining this entity's structure and payloads.                                                               |
| id      | string                     | Optional     | Unique identifier for this entity instance. Used to disambiguate when multiple instances exist.                                 |
| config  | object                     | Optional     | Entity-specific configuration. Structure defined by each entity's schema.                                                       |
| extends | OneOf\[`string`, `array`\] | Optional     | Parent capability(s) this extends. Present for extensions, absent for root capabilities. Use array for multi-parent extensions. |

#### Capability (Response)

As seen in response messages.

Capability reference in responses. Only name/version required to confirm active capabilities.

| Name    | Type                       | Requirement  | Description                                                                                                                     |
| ------- | -------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| version | string                     | **Required** | Entity version in YYYY-MM-DD format.                                                                                            |
| spec    | string                     | Optional     | URL to human-readable specification document.                                                                                   |
| schema  | string                     | Optional     | URL to JSON Schema defining this entity's structure and payloads.                                                               |
| id      | string                     | Optional     | Unique identifier for this entity instance. Used to disambiguate when multiple instances exist.                                 |
| config  | object                     | Optional     | Entity-specific configuration. Structure defined by each entity's schema.                                                       |
| extends | OneOf\[`string`, `array`\] | Optional     | Parent capability(s) this extends. Present for extensions, absent for root capabilities. Use array for multi-parent extensions. |
