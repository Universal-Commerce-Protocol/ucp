# Checkout Capability

- **Capability Name:** `dev.ucp.shopping.checkout`

## Overview

Allows platforms to facilitate checkout sessions. The checkout has to be finalized manually by the user through a trusted UI unless the AP2 Mandates extension is supported.

The business remains the Merchant of Record (MoR), and they don't need to become PCI DSS compliant to accept card payments through this Capability.

### Flow overview

### Payments

Payment handlers are discovered from the business's UCP profile at `/.well-known/ucp` and checkout.ucp.payment_handlers. The handlers define the processing specifications for collecting payment instruments (e.g., Google Pay, Shop Pay). When the buyer submits payment, the platform populates the `payment.instruments` array with the collected instrument data.

The `payment` object is optional on checkout creation and may be omitted for use cases that don't require payment processing (e.g., quote generation, cart management).

### Fulfillment

Fulfillment is modelled as an extension in UCP to account for diverse use cases.

Fulfillment is optional in the checkout object. This is done to enable a platform to perform checkout for digital goods without needing to furnish fulfillment details more relevant for physical goods.

### Checkout Status Lifecycle

The checkout `status` field indicates the current phase of the session and determines what action is required next. The business sets the status; the platform receives messages indicating what's needed to progress.

```text
       +------------+                         +---------------------+
       | incomplete |<----------------------->| requires_escalation |
       +-----+------+                         |   (buyer handoff    |
             |                                |  via continue_url)  |
             | all info collected             +----------+----------+
             v                                           |
    +------------------+                                 |
    |ready_for_complete|                                 |
    |                  |                                 |
    | (platform can    |                                 | continue_url
    | call Complete    |                                 |
    |   Checkout)      |                                 |
    +--------+---------+                                 |
             |                                           |
             | Complete Checkout                         |
             v                                           |
   +--------------------+                                |
   |complete_in_progress|                                |
   +---------+----------+                                |
             |                                           |
             +-----------------------+-------------------+
                                     v
                               +-------------+
                               |  completed  |
                               +-------------+

                               +-------------+
                               |  canceled   |
                               +-------------+
          (session invalid/expired - can occur from any state)
```

### Status Values

- **`incomplete`**: Checkout session is missing required information or has issues that need resolution. Platform should inspect `messages` array for context and should attempt to resolve via Update Checkout.
- **`requires_escalation`**: Checkout session requires information that cannot be provided via API, or buyer input is required. Platform should inspect `messages` to understand what's needed (see Error Handling below). If any `recoverable` errors exist, resolve those first. Then hand off to buyer via `continue_url`.
- **`ready_for_complete`**: Checkout session has all necessary information and platform can finalize programmatically. Platform can call Complete Checkout.
- **`complete_in_progress`**: Business is processing the Complete Checkout request.
- **`completed`**: Order placed successfully.
- **`canceled`**: Checkout session is invalid or expired. Platform should start a new checkout session if needed.

### Error Handling

The `messages` array contains errors, warnings, and informational messages about the checkout state. `ucp.status` is the shape discriminator — `"success"` means the response carries the expected payload, `"error"` means it carries error information instead. The `severity` field on each error message prescribes the recommended action:

| Severity                | Meaning                                          | Platform Action                                                   |
| ----------------------- | ------------------------------------------------ | ----------------------------------------------------------------- |
| `recoverable`           | Platform can resolve by modifying inputs via API | Update resource and retry                                         |
| `requires_buyer_input`  | Business requires input not available via API    | Hand off via `continue_url`                                       |
| `requires_buyer_review` | Buyer review and authorization is required       | Hand off via `continue_url`                                       |
| `unrecoverable`         | No resource exists to act on                     | Retry with new resource or inputs, or hand off via `continue_url` |

Errors with `requires_*` severity contribute to `status: requires_escalation`. Both result in buyer handoff, but represent different checkout states.

- `requires_buyer_input` means the checkout is **incomplete** — the business requires information their API doesn't support collecting programmatically.
- `requires_buyer_review` means the checkout is **complete** — but policy, regulatory, or entitlement rules require buyer authorization before order placement (e.g., high-value order approval, first-purchase policy).

When the business cannot create a new resource or the requested resource no longer exists, the response contains `ucp.status: "error"` with `messages` describing the failure — no resource is included in the response body. When no resource exists to act on, messages SHOULD use `severity: "unrecoverable"`. For example, a business may reject a create checkout request where all items are unavailable:

```json
{
  "ucp": { "version": "2026-01-11", "status": "error" },
  "messages": [
    {
      "type": "error",
      "code": "out_of_stock",
      "content": "All requested items are currently out of stock",
      "severity": "unrecoverable"
    }
  ],
  "continue_url": "https://merchant.com/"
}
```

See [REST](http://ucp.dev/draft/specification/checkout-rest/#create-checkout) and [MCP](http://ucp.dev/draft/specification/checkout-mcp/#create_checkout) binding examples.

#### Error Processing Algorithm

When status is `incomplete` or `requires_escalation`, platforms should process errors as a prioritized stack. The example below illustrates a checkout with three error types: a recoverable error (invalid phone), a buyer input requirement (delivery scheduling), and a review requirement (high-value order). The latter two require handoff and serve as explicit signals to the platform. Businesses **SHOULD** surface such messages as early as possible, and platforms **SHOULD** prioritize resolving recoverable errors before initiating handoff.

```json
{
  "status": "requires_escalation",
  "messages": [
    {
      "type": "error",
      "code": "invalid_phone",
      "severity": "recoverable",
      "content": "Phone number format is invalid"
    },
    {
      "type": "error",
      "code": "schedule_delivery",
      "severity": "requires_buyer_input",
      "content": "Select delivery window for your purchase"
    },
    {
      "type": "error",
      "code": "high_value_order",
      "severity": "requires_buyer_review",
      "content": "Orders over $500 require additional verification"
    }
  ]
}
```

Example error processing algorithm:

```text
GIVEN response with messages array

FILTER errors FROM messages WHERE type = "error"

PARTITION errors INTO
  recoverable           WHERE severity = "recoverable"
  requires_buyer_input  WHERE severity = "requires_buyer_input"
  requires_buyer_review WHERE severity = "requires_buyer_review"
  unrecoverable         WHERE severity = "unrecoverable"

IF unrecoverable is not empty
  RETRY with new resource or inputs, or hand off via continue_url
  RETURN

IF recoverable is not empty
  FOR EACH error IN recoverable
    ATTEMPT to fix error (e.g., reformat phone number)
  CALL Update Checkout
  RETURN and re-evaluate response

IF requires_buyer_input is not empty
  handoff_context = "incomplete, additional input from buyer is required"
ELSE IF requires_buyer_review is not empty
  handoff_context = "ready for final review by the buyer"
```

#### Standard Errors

Standard errors are standardized error codes that platforms are expected to handle with specific, appropriate UX rather than generic error treatment.

| Code                    | Description                                           |
| ----------------------- | ----------------------------------------------------- |
| `out_of_stock`          | Specific item or variant is unavailable               |
| `item_unavailable`      | Item cannot be purchased (e.g. delisted)              |
| `address_undeliverable` | Cannot deliver to the provided address                |
| `payment_failed`        | Payment processing failed                             |
| `eligibility_invalid`   | Eligibility claim could not be verified at completion |

Businesses **SHOULD** mark standard errors with `severity: recoverable` to signal that platforms should provide appropriate UX (out-of-stock messaging, address validation prompts, payment method changes) rather than generic error messages or deferring to checkout completion.

Example: `out_of_stock` requires specific upfront UX, whereas `payment_required` can be handled generically at submission.

#### Eligibility Verification at Completion

Platforms provide `context.eligibility` — buyer claims about eligible benefits such as loyalty membership, payment instrument perks, and similar. These are claims, not verified facts. Businesses **MAY** act on recognized claims during the session (adjusting pricing, granting product access, applying provisional discounts), but all accepted claims **MUST** be resolved before the transaction can complete.

Unrecognized or inapplicable claims **MUST NOT** block the checkout. Businesses **SHOULD** notify the buyer via `messages` with `type: "warning"` when a claim is not accepted, and **MAY** use `type: "info"` to explain the effects of accepted claims. At completion, accepted claims that remain unverified **MUST** result in `type: "error"` with `code: "eligibility_invalid"` (see below).

**Eligibility message codes:**

| Type      | Code                       | When                                               |
| --------- | -------------------------- | -------------------------------------------------- |
| `warning` | `eligibility_not_accepted` | Claim not recognized or not applicable             |
| `info`    | `eligibility_accepted`     | Effect of an accepted claim                        |
| `error`   | `eligibility_invalid`      | Accepted claim could not be verified at completion |

A claim is resolved when it is either **verified** or **rescinded**:

- **Verified**: The Business confirms the claim against a proof provided at completion time. UCP does not prescribe how verification occurs — proof may come from the payment credential, an identity verification capability, or any other mechanism negotiated between Platform and Business.
- **Rescinded**: The Platform removes the claim from `context.eligibility` before completion (e.g., buyer changes payment method, withdraws a membership claim). Once removed, the Business recalculates without it.

Businesses **MUST NOT** complete a transaction with unresolved eligibility claims. Unverified claims may result in incorrect pricing or unauthorized access to restricted products.

**When verification fails:**

Verification failure **MUST** only affect the `messages` array. The Business **MUST** return an error in `messages` with `code: "eligibility_invalid"` and `severity: "recoverable"`. Messages **SHOULD** use the `path` field to identify which specific claim(s) could not be verified. The Platform **MAY** then provide valid proof and resubmit, restructure the checkout (e.g., remove ineligible items, update claims), or abandon the attempt.

For example, the Platform claims a store card benefit via `context.eligibility`. The Business applies member pricing during the session. At completion, the payment credential does not match the claimed instrument:

```json
{
  "ucp": { "version": "2026-01-11", "status": "success" },
  "id": "checkout_abc",
  "status": "ready_for_complete",
  "line_items": [ "..." ],
  "totals": [ "..." ],
  "messages": [
    {
      "type": "error",
      "code": "eligibility_invalid",
      "severity": "recoverable",
      "content": "Payment credential does not match the claimed store card benefit.",
      "path": "$.context.eligibility[0]"
    }
  ]
}
```

The Platform can resolve this by having the buyer switch to the qualifying payment instrument, or by removing the claim from `context.eligibility` to renegotiate the checkout (obtaining updated pricing, availability, etc.) and then resubmitting for completion.

### Warning Presentation

The `presentation` field on warning messages controls the rendering contract the platform **MUST** follow. When omitted, it defaults to `"notice"`.

|                          | `notice` (default) | `disclosure`                |
| ------------------------ | ------------------ | --------------------------- |
| Display content          | **MUST**           | **MUST**                    |
| Proximity to `path`      | **MAY**            | **MUST**                    |
| Dismissible              | **MAY**            | **MUST NOT**                |
| Render `image_url`       | **MAY**            | **MUST**                    |
| Render `url`             | **MAY**            | **SHOULD**                  |
| Escalate if cannot honor | —                  | **MUST** via `continue_url` |

#### `notice` (default)

The default rendering contract for warnings. Platforms **MUST** display the warning content to the buyer. Platforms **MAY** render notices in a banner, tray, or toast, and **MAY** allow the buyer to dismiss them.

#### `disclosure`

Warnings with `presentation: "disclosure"` carry notices — safety warnings, allergen declarations, compliance content, etc. — that **MUST** follow the prescribed rendering contract below.

**Platform requirements:**

- **MUST** display the warning `content` to the buyer.
- **MUST** display the warning in proximity to the component referenced by `path`, preserving the association between the disclosure and its subject. When `path` is omitted, the disclosure applies to the response as a whole.
- **MUST NOT** hide, collapse, or auto-dismiss the warning.
- **MUST** render `image_url` when present (e.g., warning symbol, energy class label).
- **SHOULD** render `url` as a navigable reference link when present.

Warnings with `presentation: "disclosure"` **SHOULD** be given rendering priority over notices.

Platforms that cannot honor the disclosure rendering contract **MUST** escalate to merchant UI via `continue_url` rather than silently downgrading to a notice.

**Business requirements:**

- **MUST** set `presentation: "disclosure"` when the warning content must be displayed alongside a specific component and must not be hidden or auto-dismissed.
- **SHOULD** use the `path` field to associate disclosures with the relevant component in the response.
- **SHOULD** provide a `code` that identifies the disclosure category (e.g., `prop65`, `allergens`, `energy_label`).
- **SHOULD** provide `image_url` when the disclosure has an associated visual element (e.g., warning symbol, energy class label).
- **SHOULD** provide `url` when a reference link is available for the buyer to learn more.

#### Disclosure and Acknowledgment

The `presentation` field controls how the warning is rendered, not whether the checkout can proceed. When affirmative buyer acknowledgment or authorization is also required, the business **MAY** combine the disclosure with the escalation mechanisms described in the [Checkout Status Lifecycle](#checkout-status-lifecycle) to ensure the appropriate buyer input is obtained.

#### Jurisdiction and Applicability

It is the business's responsibility to determine which disclosures apply to a given session and return only those that are relevant. Businesses **SHOULD** use buyer-provided data (`context` and other inputs) and product attributes to resolve jurisdiction-specific requirements. Platforms do not affect or resolve disclosure applicability — they render what they receive from the business.

#### Example

A checkout response containing both a recoverable error and a disclosure warning on a line item:

```json
{
  "ucp": { "version": "draft", "status": "success" },
  "id": "chk_abc123",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "item_456", "title": "Artisan Nut Butter Collection", "image_url": "https://merchant.com/nut-butter.jpg" },
      "quantity": 1,
      "totals": [{ "type": "subtotal", "amount": 1299 }]
    }
  ],
  "totals": [{ "type": "total", "amount": 1299 }],
  "messages": [
    {
      "type": "error",
      "code": "field_required",
      "path": "$.buyer.email",
      "content": "Buyer email is required",
      "severity": "recoverable"
    },
    {
      "type": "warning",
      "code": "allergens",
      "path": "$.line_items[0]",
      "content": "**Contains: tree nuts.** Produced in a facility that also processes peanuts, milk, and soy.",
      "content_type": "markdown",
      "presentation": "disclosure",
      "image_url": "https://merchant.com/allergen-tree-nuts.svg",
      "url": "https://merchant.com/allergen-info"
    }
  ],
  "links": []
}
```

The platform resolves the recoverable error programmatically while rendering the allergen disclosure in proximity to the referenced line item.

## Continue URL

The `continue_url` field enables checkout handoff from platform to business UI, allowing the buyer to continue and finalize the checkout session.

### Availability

Businesses **MUST** provide `continue_url` when returning `status` = `requires_escalation`. For all other non-terminal statuses (`incomplete`, `ready_for_complete`, `complete_in_progress`), businesses **SHOULD** provide `continue_url`. For terminal states (`completed`, `canceled`), `continue_url` **SHOULD** be omitted.

### Format

The `continue_url` **MUST** be an absolute HTTPS URL and **SHOULD** preserve checkout state for seamless handoff. Businesses **MAY** implement state preservation using either approach:

#### Server-Side State (Recommended)

An opaque URL backed by server-side checkout state:

```text
https://business.example.com/checkout-sessions/{checkout_id}
```

- Server maintains checkout state tied to `checkout_id`
- Simple, secure, recommended for most implementations
- URL lifetime typically tied to `expires_at`

#### Checkout Permalink

A stateless URL that encodes checkout state directly, allowing reconstruction without server-side persistence. Businesses **SHOULD** implement support for this format to facilitate checkout handoff and accelerated entry—for example, a platform can prefill checkout state when initiating a buy-now flow.

> **Note:** Checkout permalinks are a REST-specific construct that extends the [REST transport binding](http://ucp.dev/draft/specification/checkout-rest/index.md). Accessing a permalink returns a redirect to the checkout UI or renders the checkout page directly.

## Guidelines

(In addition to the overarching guidelines)

### Platform

- **MAY** engage an agent to facilitate the checkout session (e.g. add items to the checkout session, select fulfillment address). However, the agent must hand over the checkout session to a trusted and deterministic UI for the user to review the checkout details and place the order.
- **MAY** send the user from the trusted, deterministic UI back to the agent at any time. For example, when the user decides to exit the checkout screen to keep adding items to the cart.
- **MAY** provide agent context when the platform indicates that the request was done by an agent.
- **MUST** use `continue_url` when checkout status is `requires_escalation`.
- **MAY** use `continue_url` to hand off to business UI in other situations.
- When performing handoff, **SHOULD** prefer business-provided `continue_url` over platform-constructed checkout permalinks.

### Business

- **MUST** send a confirmation email after the checkout has been completed.
- **SHOULD** provide accurate error messages.
- Logic handling the checkout sessions **MUST** be deterministic.
- **MUST** provide `continue_url` when returning `status` = `requires_escalation`.
- **MUST** include at least one message with `severity` of `requires_buyer_input` or `requires_buyer_review` when returning `status` = `requires_escalation`.
- **SHOULD** provide `continue_url` in all non-terminal checkout responses.
- After a checkout session reaches the state "completed", it is considered immutable.

## Capability Schema Definition

| Name         | Type                                                                     | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ------------------------------------------------------------------------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | any                                                                      | **Yes**  | UCP metadata for checkout responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| id           | string                                                                   | **Yes**  | Unique identifier of the checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| line_items   | Array\[[Line Item Response](/draft/specification/reference/#line-item)\] | **Yes**  | List of line items being checked out.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| buyer        | [Buyer](/draft/specification/reference/#buyer)                           | No       | Representation of the buyer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| context      | [Context](/draft/specification/reference/#context)                       | No       | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals      | [Signals](/draft/specification/reference/#signals)                       | No       | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| status       | string                                                                   | **Yes**  | Checkout state indicating the current phase and required action. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                         |
| currency     | string                                                                   | **Yes**  | ISO 4217 currency code reflecting the merchant's market determination. Derived from address, context, and geo IP—buyers provide signals, merchants determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| totals       | [Totals](/draft/specification/reference/#totals)                         | **Yes**  | Different cart totals.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| messages     | Array\[[Message](/draft/specification/reference/#message)\]              | No       | List of messages with error and info about the checkout session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| links        | Array\[[Link](/draft/specification/reference/#link)\]                    | **Yes**  | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| expires_at   | string                                                                   | No       | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| continue_url | string                                                                   | No       | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| payment      | [Payment](/draft/specification/checkout/#payment)                        | No       | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| order        | [Order Confirmation](/draft/specification/reference/#order-confirmation) | No       | Details about an order created for this checkout session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

## Operations

The Checkout capability defines the following logical operations.

| Operation             | Description                                                                        |
| --------------------- | ---------------------------------------------------------------------------------- |
| **Create Checkout**   | Initiates a new checkout session. Called as soon as a user adds an item to a cart. |
| **Get Checkout**      | Retrieves the current state of a checkout session.                                 |
| **Update Checkout**   | Updates a checkout session.                                                        |
| **Complete Checkout** | Finalizes the checkout and places the order.                                       |
| **Cancel Checkout**   | Cancels a checkout session.                                                        |

### Create Checkout

To be invoked by the platform when the user has expressed purchase intent (e.g., click on Buy) to initiate the checkout session with the item details.

**Recommendation**: To minimize discrepancies and a streamlined user experience, product data (price/title etc.) provided by the business through the feeds **SHOULD** match the actual attributes returned in the response.

**Inputs**

| Name       | Type                                                            | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ---------- | --------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| line_items | Array\[[Line Item](/draft/specification/reference/#line-item)\] | **Yes**  | List of line items being checked out.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| buyer      | [Buyer](/draft/specification/reference/#buyer)                  | No       | Representation of the buyer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| context    | [Context](/draft/specification/reference/#context)              | No       | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals    | [Signals](/draft/specification/reference/#signals)              | No       | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| payment    | [Payment](/draft/specification/checkout/#payment)               | No       | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

**Output**

This object MUST be one of the following types: [Checkout](/draft/specification/checkout/#checkout), [Error Response](/draft/specification/checkout/#error-response).

### Get Checkout

It provides the latest state of the checkout resource. After cancellation or completion it is up to the business on what to return (i.e this can be a long lived state or expire after a particular TTL - resulting in a 'not found' error). From the platform there is no specific enforcement for a TTL of the checkout.

The platform will honor the TTL provided by the business via `expires_at` at the time of checkout session creation.

**Inputs**

| Name | Type   | Required | Description                                                    |
| ---- | ------ | -------- | -------------------------------------------------------------- |
| id   | string | **Yes**  | The unique identifier of the checkout session.Defined in path. |

**Output**

This object MUST be one of the following types: [Checkout](/draft/specification/checkout/#checkout), [Error Response](/draft/specification/checkout/#error-response).

### Update Checkout

Performs a full replacement of the checkout resource. The platform is **REQUIRED** to send the entire checkout resource containing any data updates to write-only data fields. The resource provided in the request will replace the existing checkout session state on the business side.

**Inputs**

| Name       | Type                                                            | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ---------- | --------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id         | string                                                          | **Yes**  | The unique identifier of the checkout session.Defined in path.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| line_items | Array\[[Line Item](/draft/specification/reference/#line-item)\] | No       | List of line items being checked out.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| buyer      | [Buyer](/draft/specification/reference/#buyer)                  | No       | Representation of the buyer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| context    | [Context](/draft/specification/reference/#context)              | No       | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals    | [Signals](/draft/specification/reference/#signals)              | No       | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| payment    | [Payment](/draft/specification/checkout/#payment)               | No       | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

**Output**

This object MUST be one of the following types: [Checkout](/draft/specification/checkout/#checkout), [Error Response](/draft/specification/checkout/#error-response).

### Complete Checkout

This is the final checkout placement call. To be invoked when the user has committed to pay and place an order for the chosen items. The response of this call is the checkout object with the `order` field populated in it. The returned `order` provides necessary identifiers, such as `id` and `permalink_url`, that can be used to reference the full state of the placed order. At the time of order persistence, fields from `Checkout` **MAY** be used to construct the order representation (i.e. information like `line_items`, `fulfillment` will be used to create the initial order representation).

After this call, other details will be updated through subsequent events as the order, and its associated items, moves through the supply chain.

**Inputs**

| Name    | Type                                               | Required | Description                                                                                                                                                                                                                                                                                                                                                                                             |
| ------- | -------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id      | string                                             | **Yes**  | The unique identifier of the checkout session.Defined in path.                                                                                                                                                                                                                                                                                                                                          |
| signals | [Signals](/draft/specification/reference/#signals) | No       | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace. |
| payment | [Payment](/draft/specification/checkout/#payment)  | No       | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                              |

**Output**

This object MUST be one of the following types: [Checkout](/draft/specification/checkout/#checkout), [Error Response](/draft/specification/checkout/#error-response).

### Cancel Checkout

This operation will be used to cancel a checkout session, if it can be canceled. If the checkout session cannot be canceled (e.g. checkout session is already canceled or completed), then businesses **SHOULD** send back an error indicating the operation is not allowed. Any checkout session with a status that is not equal to `completed` or `canceled` **SHOULD** be cancelable.

**Inputs**

| Name | Type   | Required | Description                                                    |
| ---- | ------ | -------- | -------------------------------------------------------------- |
| id   | string | **Yes**  | The unique identifier of the checkout session.Defined in path. |

**Output**

This object MUST be one of the following types: [Checkout](/draft/specification/checkout/#checkout), [Error Response](/draft/specification/checkout/#error-response).

## Transport Bindings

The abstract operations above are bound to specific transport protocols as defined below:

- [REST Binding](http://ucp.dev/draft/specification/checkout-rest/index.md): RESTful API mapping using standard HTTP verbs and JSON payloads.
- [MCP Binding](http://ucp.dev/draft/specification/checkout-mcp/index.md): Model Context Protocol mapping for agentic interaction.
- [A2A Binding](http://ucp.dev/draft/specification/checkout-a2a/index.md): Agent-to-Agent Protocol mapping for agentic interactions.
- [Embedded Checkout Binding](http://ucp.dev/draft/specification/embedded-checkout/index.md): JSON-RPC for powering embedded checkout.

## Entities

### Buyer

| Name         | Type   | Required | Description              |
| ------------ | ------ | -------- | ------------------------ |
| first_name   | string | No       | First name of the buyer. |
| last_name    | string | No       | Last name of the buyer.  |
| email        | string | No       | Email of the buyer.      |
| phone_number | string | No       | E.164 standard.          |

### Context

Context signals are provisional—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data.

| Name            | Type                                                                                | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --------------- | ----------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| address_country | string                                                                              | No       | The country. Recommended to be in 2-letter ISO 3166-1 alpha-2 format, for example "US". For backward compatibility, a 3-letter ISO 3166-1 alpha-3 country code such as "SGP" or a full country name such as "Singapore" can also be used. Optional hint for market context (currency, availability, pricing)—higher-resolution data (e.g., shipping address) supersedes this value.                                                                                |
| address_region  | string                                                                              | No       | The region in which the locality is, and which is in the country. For example, California or another appropriate first-level Administrative division. Optional hint for progressive localization—higher-resolution data (e.g., shipping address) supersedes this value.                                                                                                                                                                                            |
| postal_code     | string                                                                              | No       | The postal code. For example, 94043. Optional hint for regional refinement—higher-resolution data (e.g., shipping address) supersedes this value.                                                                                                                                                                                                                                                                                                                  |
| intent          | string                                                                              | No       | Background context describing buyer's intent (e.g., 'looking for a gift under $50', 'need something durable for outdoor use'). Informs relevance, recommendations, and personalization.                                                                                                                                                                                                                                                                            |
| language        | string                                                                              | No       | Preferred language for content. Use IETF BCP 47 language tags (e.g., 'en', 'fr-CA', 'zh-Hans'). For REST, equivalent to Accept-Language header—platforms SHOULD fall back to Accept-Language when this field is absent; when provided, overrides Accept-Language. Businesses MAY return content in a different language if unavailable.                                                                                                                            |
| currency        | string                                                                              | No       | Preferred currency (ISO 4217, e.g., 'EUR', 'USD'). Businesses determine presentment currency from context and authoritative signals; this hint MAY inform selection in multi-currency markets. Also serves as the denomination for price filter values — platforms SHOULD include this field when sending price filters. Response prices include explicit currency confirming the resolution.                                                                      |
| eligibility     | Array\[[Reverse Domain Name](/draft/specification/reference/#reverse-domain-name)\] | No       | Buyer claims about eligible benefits such as loyalty membership, payment instrument perks, and similar. Recognized claims MAY inform the Business response (e.g., member-only product availability, adjusted pricing in catalog, provisional discounts at cart or checkout). Businesses MUST ignore unrecognized values without error. Values MUST use reverse-domain naming (e.g., 'com.example.loyalty_gold', 'org.school.student') and MUST be non-identifying. |

### Signals

Environment data provided by the platform to support authorization and abuse prevention. Unlike `context` (buyer-asserted preferences) and `buyer` (self-reported identity), signal values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or by relaying independently verifiable third-party attestations. See [Signals](http://ucp.dev/draft/specification/overview/#signals) for details and privacy requirements.

| Name               | Type   | Required | Description                                    |
| ------------------ | ------ | -------- | ---------------------------------------------- |
| dev.ucp.buyer_ip   | string | No       | Client's IP address (IPv4 or IPv6).            |
| dev.ucp.user_agent | string | No       | Client's HTTP User-Agent header or equivalent. |

### Fulfillment Option

A fulfillment option within a group (e.g., Standard Shipping $5, Express $15).

| Name                      | Type          | Required | Description                                                                |
| ------------------------- | ------------- | -------- | -------------------------------------------------------------------------- |
| id                        | string        | **Yes**  | Unique fulfillment option identifier.                                      |
| title                     | string        | **Yes**  | Short label (e.g., 'Express Shipping', 'Curbside Pickup').                 |
| description               | string        | No       | Complete context for buyer decision (e.g., 'Arrives Dec 12-15 via FedEx'). |
| carrier                   | string        | No       | Carrier name (for shipping).                                               |
| earliest_fulfillment_time | string        | No       | Earliest fulfillment date.                                                 |
| latest_fulfillment_time   | string        | No       | Latest fulfillment date.                                                   |
| totals                    | Array[object] | **Yes**  | Fulfillment option totals breakdown.                                       |

### Item

#### Item Create Request

| Name | Type   | Required | Description                                                                                                                                                                 |
| ---- | ------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id   | string | **Yes**  | The product identifier, often the SKU, required to resolve the product details associated with this line item. Should be recognized by both the Platform, and the Business. |

#### Item Update Request

| Name | Type   | Required | Description                                                                                                                                                                 |
| ---- | ------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id   | string | **Yes**  | The product identifier, often the SKU, required to resolve the product details associated with this line item. Should be recognized by both the Platform, and the Business. |

#### Item

| Name      | Type                                             | Required | Description                                                                                                                                                                 |
| --------- | ------------------------------------------------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id        | string                                           | **Yes**  | The product identifier, often the SKU, required to resolve the product details associated with this line item. Should be recognized by both the Platform, and the Business. |
| title     | string                                           | **Yes**  | Product title.                                                                                                                                                              |
| price     | [Amount](/draft/specification/reference/#amount) | **Yes**  | Unit price in ISO 4217 minor units.                                                                                                                                         |
| image_url | string                                           | No       | Product image URI.                                                                                                                                                          |

### Line Item

#### Line Item Create Request

| Name     | Type                                         | Required | Description                           |
| -------- | -------------------------------------------- | -------- | ------------------------------------- |
| item     | [Item](/draft/specification/reference/#item) | **Yes**  |                                       |
| quantity | integer                                      | **Yes**  | Quantity of the item being purchased. |

#### Line Item Update Request

| Name      | Type                                         | Required | Description                                            |
| --------- | -------------------------------------------- | -------- | ------------------------------------------------------ |
| id        | string                                       | No       |                                                        |
| item      | [Item](/draft/specification/reference/#item) | **Yes**  |                                                        |
| quantity  | integer                                      | **Yes**  | Quantity of the item being purchased.                  |
| parent_id | string                                       | No       | Parent line item identifier for any nested structures. |

#### Line Item

| Name      | Type                                                    | Required | Description                                            |
| --------- | ------------------------------------------------------- | -------- | ------------------------------------------------------ |
| id        | string                                                  | **Yes**  |                                                        |
| item      | [Item](/draft/specification/reference/#item)            | **Yes**  |                                                        |
| quantity  | integer                                                 | **Yes**  | Quantity of the item being purchased.                  |
| totals    | Array\[[Total](/draft/specification/reference/#total)\] | **Yes**  | Line item totals breakdown.                            |
| parent_id | string                                                  | No       | Parent line item identifier for any nested structures. |

### Link

| Name  | Type   | Required | Description                                                                                                                                                                                                                          |
| ----- | ------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| type  | string | **Yes**  | Type of link. Well-known values: `privacy_policy`, `terms_of_service`, `refund_policy`, `shipping_policy`, `faq`. Consumers SHOULD handle unknown values gracefully by displaying them using the `title` field or omitting the link. |
| url   | string | **Yes**  | The actual URL pointing to the content to be displayed.                                                                                                                                                                              |
| title | string | No       | Optional display text for the link. When provided, use this instead of generating from type.                                                                                                                                         |

#### Well-Known Link Types

Businesses **SHOULD** provide all relevant links for the transaction. The following are the recommended well-known types:

| Type               | Description                                       |
| ------------------ | ------------------------------------------------- |
| `privacy_policy`   | Link to the business's privacy policy             |
| `terms_of_service` | Link to the business's terms of service           |
| `refund_policy`    | Link to the business's refund policy              |
| `shipping_policy`  | Link to the business's shipping policy            |
| `faq`              | Link to the business's frequently asked questions |

Businesses **MAY** define custom types for domain-specific needs. Platforms **SHOULD** handle unknown types gracefully by displaying them using the `title` field or omitting them.

### Message

This object MUST be one of the following types: [Message Error](/draft/specification/reference/#message-error), [Message Warning](/draft/specification/reference/#message-warning), [Message Info](/draft/specification/reference/#message-info).

### Message Error

| Name         | Type                                                     | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------ | -------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                   | **Yes**  | **Constant = error**. Message type discriminator.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| code         | [Error Code](/draft/specification/reference/#error-code) | **Yes**  | Error code identifying the type of error. Standard errors are defined in specification (see examples), and have standardized semantics; freeform codes are permitted.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| path         | string                                                   | No       | RFC 9535 JSONPath to the component the message refers to (e.g., $.items[1]).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| content_type | string                                                   | No       | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| content      | string                                                   | **Yes**  | Human-readable message.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| severity     | string                                                   | **Yes**  | Reflects the resource state and recommended action. 'recoverable': platform can resolve by modifying inputs and retrying via API. 'requires_buyer_input': merchant requires information their API doesn't support collecting programmatically (checkout incomplete). 'requires_buyer_review': buyer must authorize before order placement due to policy, regulatory, or entitlement rules. 'unrecoverable': no valid resource exists to act on, retry with new resource or inputs. Errors with 'requires\_*' severity contribute to 'status: requires_escalation'.* *Enum:*\* `recoverable`, `requires_buyer_input`, `requires_buyer_review`, `unrecoverable` |

#### Error Code

Error code identifying the type of error. Standard errors are defined in specification (see examples), and have standardized semantics; freeform codes are permitted.

### Message Info

| Name         | Type   | Required | Description                                                    |
| ------------ | ------ | -------- | -------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = info**. Message type discriminator.               |
| path         | string | No       | RFC 9535 JSONPath to the component the message refers to.      |
| code         | string | No       | Info code for programmatic handling.                           |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown` |
| content      | string | **Yes**  | Human-readable message.                                        |

### Message Warning

| Name         | Type   | Required | Description                                                                                                                                                                                                                                         |
| ------------ | ------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = warning**. Message type discriminator.                                                                                                                                                                                                 |
| path         | string | No       | JSONPath (RFC 9535) to related field (e.g., $.line_items[0]).                                                                                                                                                                                       |
| code         | string | **Yes**  | Warning code. Machine-readable identifier for the warning type (e.g., final_sale, prop65, fulfillment_changed, age_restricted, etc.).                                                                                                               |
| content      | string | **Yes**  | Human-readable warning message that MUST be displayed.                                                                                                                                                                                              |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                      |
| presentation | string | No       | Rendering contract for this warning. 'notice' (default): platform MUST display, MAY dismiss. 'disclosure': platform MUST display in proximity to the path-referenced component, MUST NOT hide or auto-dismiss. See specification for full contract. |
| image_url    | string | No       | URL to a required visual element (e.g., warning symbol, energy class label).                                                                                                                                                                        |
| url          | string | No       | Reference URL for more information (e.g., regulatory site, registry entry, policy page).                                                                                                                                                            |

### Payment

| Name        | Type                                                                                                                                      | Required | Description                                                                                                                                                                                                                |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| instruments | Array\[[Payment Instrument Selected Payment Instrument](/draft/specification/reference/#payment-instrument-selected-payment-instrument)\] | No       | The payment instruments available for this payment. Each instrument is associated with a specific handler via the handler_id field. Handlers can extend the base payment_instrument schema to add handler-specific fields. |

#### Selected Payment Instrument

A payment instrument with selection state.

| Name            | Type    | Required | Description                                                                                                                                                  |
| --------------- | ------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| id              | string  | **Yes**  | A unique identifier for this instrument instance, assigned by the platform.                                                                                  |
| handler_id      | string  | **Yes**  | The unique identifier for the handler instance that produced this instrument. This corresponds to the 'id' field in the Payment Handler definition.          |
| type            | string  | **Yes**  | The broad category of the instrument (e.g., 'card', 'tokenized_card'). Specific schemas will constrain this to a constant value.                             |
| billing_address | object  | No       | The billing address associated with this payment method.                                                                                                     |
| credential      | object  | No       | The base definition for any payment credential. Handlers define specific credential types.                                                                   |
| display         | object  | No       | Display information for this payment instrument. Each payment instrument schema defines its specific display properties, as outlined by the payment handler. |
| selected        | boolean | No       | Whether this instrument is selected by the user.                                                                                                             |

### Payment Credential

| Name | Type   | Required | Description                                                                                  |
| ---- | ------ | -------- | -------------------------------------------------------------------------------------------- |
| type | string | **Yes**  | The credential type discriminator. Specific schemas will constrain this to a constant value. |

### Postal Address

| Name             | Type   | Required | Description                                                                                                                                                                                                                               |
| ---------------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| extended_address | string | No       | An address extension such as an apartment number, C/O or alternative name.                                                                                                                                                                |
| street_address   | string | No       | The street address.                                                                                                                                                                                                                       |
| address_locality | string | No       | The locality in which the street address is, and which is in the region. For example, Mountain View.                                                                                                                                      |
| address_region   | string | No       | The region in which the locality is, and which is in the country. Required for applicable countries (i.e. state in US, province in CA). For example, California or another appropriate first-level Administrative division.               |
| address_country  | string | No       | The country. Recommended to be in 2-letter ISO 3166-1 alpha-2 format, for example "US". For backward compatibility, a 3-letter ISO 3166-1 alpha-3 country code such as "SGP" or a full country name such as "Singapore" can also be used. |
| postal_code      | string | No       | The postal code. For example, 94043.                                                                                                                                                                                                      |
| first_name       | string | No       | Optional. First name of the contact associated with the address.                                                                                                                                                                          |
| last_name        | string | No       | Optional. Last name of the contact associated with the address.                                                                                                                                                                           |
| phone_number     | string | No       | Optional. Phone number of the contact associated with the address.                                                                                                                                                                        |

### Response

Capability reference in responses. Only name/version required to confirm active capabilities.

| Name    | Type    | Required | Description                                                                                                                     |
| ------- | ------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| version | string  | **Yes**  | Entity version in YYYY-MM-DD format.                                                                                            |
| spec    | string  | No       | URL to human-readable specification document.                                                                                   |
| schema  | string  | No       | URL to JSON Schema defining this entity's structure and payloads.                                                               |
| id      | string  | No       | Unique identifier for this entity instance. Used to disambiguate when multiple instances exist.                                 |
| config  | object  | No       | Entity-specific configuration. Structure defined by each entity's schema.                                                       |
| extends | OneOf[] | No       | Parent capability(s) this extends. Present for extensions, absent for root capabilities. Use array for multi-parent extensions. |

### Total

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
|      |      |          |             |

#### Rendering Contract

Businesses are the authoritative source for presented totals — their content and order — because the correct presentation is subject to regional, product, and regulatory requirements that the business is obligated to satisfy (e.g., multi-jurisdiction tax itemization, mandatory fee disclosures).

Platforms MUST render all top-level entries in the order provided:

```python
for entry in totals:
    render_line(entry.display_text, entry.amount)
```

Platforms MAY render sub-lines as supplementary detail:

```python
for entry in totals:
    render_line(entry.display_text, entry.amount)
    if entry.lines:
        for sub in entry.lines:
            render_detail_line(sub.display_text, sub.amount)
```

Platforms MUST NOT interpret, filter, reorder, aggregate, or apply display logic of their own.

Invariants of `totals[]`:

- Every entry carries a `type` and an `amount`. Platforms SHOULD use `display_text` when provided. Well-known types have default display labels as fallback (see table below); unknown types MUST include `display_text`.
- Amounts are signed integers — negative values are subtractive (e.g., discounts), positive values are additive. The sign IS the direction.
- Exactly one `type: "subtotal"` MUST be present.
- Exactly one `type: "total"` MUST be present.

#### Verification

Platforms MUST NOT substitute their own computed totals for the business's values. Platforms MAY verify the provided totals:

```python
assert sum(e.amount for e in totals if e.type != "total") == total_entry.amount
```

If the computed sum does not match the `type: "total"` entry, the platform MUST NOT alter the rendered output — the business's presented totals are authoritative for display. However, platforms MUST NOT autonomously complete a checkout with mismatched totals. Platforms SHOULD reject the checkout or escalate and ask for buyer review via `continue_url`.

#### Well-Known Types

| Type             | Sign | Default label  | Meaning                                 |
| ---------------- | ---- | -------------- | --------------------------------------- |
| `subtotal`       | +    | Subtotal       | Sum of line item prices                 |
| `discount`       | −    | Discount       | Order or line-item level discount       |
| `items_discount` | −    | Item Discounts | Rollup of line-item discounts           |
| `fulfillment`    | +    | Shipping       | Shipping, delivery, or pickup charges   |
| `tax`            | +    | Tax            | Tax charges                             |
| `fee`            | +    | Fee            | Fees and surcharges                     |
| `total`          | =    | Total          | Authoritative grand total (exactly one) |

When `display_text` is provided, platforms MUST use it. When omitted on a well-known type, platforms SHOULD use the default label above. The sign convention for well-known types is schema-enforced: subtractive types (discount, items_discount) MUST have negative amounts; additive types (subtotal, fulfillment, tax, fee) MUST have non-negative amounts.

The `type` field is an open string — businesses MAY use values beyond the well-known set. Unknown types MUST include `display_text` (schema-enforced) and the sign on the amount is self-describing.

#### Repeating Types

All types except `subtotal` and `total` MAY appear multiple times — for example, multi-jurisdiction tax lines or itemized fees.

#### Sub-Lines (`lines`)

Each top-level entry MAY include a `lines` array. Sub-lines share the same base shape as top-level entries — `display_text` and `amount` — providing an itemized breakdown under the parent.

**Invariant:** `sum(lines[].amount)` MUST equal the parent entry's `amount`.

The business controls what MUST be rendered (top-level entries) versus what MAY be optionally surfaced (sub-lines). Platforms SHOULD render sub-lines when provided.

#### Examples

**Split tax, itemized at top-level:**

```json
"totals": [
  { "type": "subtotal",    "display_text": "Subtotal",    "amount": 5750 },
  { "type": "fulfillment", "display_text": "Shipping",    "amount": 899 },
  { "type": "tax",         "display_text": "Federal Tax", "amount": 332 },
  { "type": "tax",         "display_text": "State Tax",   "amount": 465 },
  { "type": "total",       "display_text": "Total",       "amount": 7446 }
]
```

**Collapsed fees with optional breakdown:**

```json
"totals": [
  { "type": "subtotal", "display_text": "Subtotal", "amount": 4999 },
  {
    "type": "fee", "display_text": "Fees", "amount": 549,
    "lines": [
      { "display_text": "Service Fee", "amount": 399 },
      { "display_text": "Recycling Fee", "amount": 150 }
    ]
  },
  { "type": "tax",   "display_text": "Tax",   "amount": 444 },
  { "type": "total", "display_text": "Total", "amount": 5992 }
]
```

**Discount and account credit — negative amounts:**

```json
"totals": [
  { "type": "subtotal",       "display_text": "Subtotal",       "amount": 10000 },
  { "type": "discount",       "display_text": "Summer Sale",    "amount": -1500 },
  { "type": "tax",            "display_text": "Tax",            "amount": 680 },
  { "type": "account_credit", "display_text": "Account Credit", "amount": -2500 },
  { "type": "total",          "display_text": "Amount Due",     "amount": 6680 }
]
```

### UCP Response Checkout

UCP metadata for checkout responses.

| Name             | Type   | Required | Description                                                                 |
| ---------------- | ------ | -------- | --------------------------------------------------------------------------- |
| version          | string | **Yes**  | UCP version in YYYY-MM-DD format.                                           |
| status           | string | No       | Application-level status of the UCP operation. **Enum:** `success`, `error` |
| services         | object | No       | Service registry keyed by reverse-domain name.                              |
| capabilities     | object | No       | Capability registry keyed by reverse-domain name.                           |
| payment_handlers | object | **Yes**  | Payment handler registry keyed by reverse-domain name.                      |
| services         | any    | No       |                                                                             |
| capabilities     | any    | No       |                                                                             |
| payment_handlers | any    | **Yes**  |                                                                             |

### Order Confirmation

| Name          | Type   | Required | Description                                                                            |
| ------------- | ------ | -------- | -------------------------------------------------------------------------------------- |
| id            | string | **Yes**  | Unique order identifier.                                                               |
| label         | string | No       | Human-readable label for identifying the order. MUST only be provided by the business. |
| permalink_url | string | **Yes**  | Permalink to access the order on merchant site.                                        |

### Error Response

| Name         | Type                                                        | Required | Description                                                       |
| ------------ | ----------------------------------------------------------- | -------- | ----------------------------------------------------------------- |
| ucp          | any                                                         | **Yes**  | UCP protocol metadata. Status MUST be 'error' for error response. |
| messages     | Array\[[Message](/draft/specification/reference/#message)\] | **Yes**  | Array of messages describing why the operation failed.            |
| continue_url | string                                                      | No       | URL for buyer handoff or session recovery.                        |
