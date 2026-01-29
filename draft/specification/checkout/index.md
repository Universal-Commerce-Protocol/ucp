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
┌────────────┐    ┌─────────────────────┐
│ incomplete │◀──▶│ requires_escalation │
└─────┬──────┘    │                     │
      │           │  (buyer handoff     │
      │           │   via continue_url) │
      │           └──────────┬──────────┘
      │                      │
      │ all info collected   │ continue_url
      ▼                      │
┌──────────────────┐         │
│ready_for_complete│         │
│                  │         │
│ (platform can    │         │
│ call Complete    │         │
│   Checkout).     │         │
└────────┬─────────┘         │
         │                   │
         │ Complete Checkout │
         ▼                   │
┌────────────────────┐       │
│complete_in_progress│       │
└─────────┬──────────┘       │
          │                  │
          └────────┬─────────┘
                   ▼
            ┌─────────────┐
            │  completed  │
            └─────────────┘

            ┌─────────────┐
            │  canceled   │  (session invalid/expired - can occur from any state)
            └─────────────┘
```

### Status Values

- **`incomplete`**: Checkout session is missing required information or has issues that need resolution. Platform should inspect `messages` array for context and should attempt to resolve via Update Checkout.
- **`requires_escalation`**: Checkout session requires information that cannot be provided via API, or buyer input is required. Platform should inspect `messages` to understand what's needed (see Error Handling below). If any `recoverable` errors exist, resolve those first. Then hand off to buyer via `continue_url`.
- **`ready_for_complete`**: Checkout session has all necessary information and platform can finalize programmatically. Platform can call Complete Checkout.
- **`complete_in_progress`**: Business is processing the Complete Checkout request.
- **`completed`**: Order placed successfully.
- **`canceled`**: Checkout session is invalid or expired. Platform should start a new checkout session if needed.

### Error Handling

The `messages` array contains errors, warnings, and informational messages about the checkout state. Error messages include a `severity` field that declares **who resolves the error**:

| Severity                | Meaning                                       | Platform Action               |
| ----------------------- | --------------------------------------------- | ----------------------------- |
| `recoverable`           | Platform can fix via API                      | Resolve using Update Checkout |
| `requires_buyer_input`  | Business requires input not available via API | Hand off via `continue_url`   |
| `requires_buyer_review` | Buyer review and authorization is required    | Hand off via `continue_url`   |

Errors with `requires_*` severity contribute to `status: requires_escalation`. Both result in buyer handoff, but represent different checkout states.

- `requires_buyer_input` means the checkout is **incomplete** — the business requires information their API doesn't support collecting programmatically.
- `requires_buyer_review` means the checkout is **complete** — but policy, regulatory, or entitlement rules require buyer authorization before order placement (e.g., high-value order approval, first-purchase policy).

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
GIVEN checkout with messages array
FILTER errors FROM messages WHERE type = "error"

PARTITION errors INTO
  recoverable           WHERE severity = "recoverable"
  requires_buyer_input  WHERE severity = "requires_buyer_input"
  requires_buyer_review WHERE severity = "requires_buyer_review"

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

> **Note:** Checkout permalinks are a REST-specific construct that extends the [REST transport binding](https://ucp.dev/draft/specification/checkout-rest/index.md). Accessing a permalink returns a redirect to the checkout UI or renders the checkout page directly.

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
- **MUST** include at least one message with `severity: escalation` when returning `status` = `requires_escalation`.
- **SHOULD** provide `continue_url` in all non-terminal checkout responses.
- After a checkout session reaches the state "completed", it is considered immutable.

## Capability Schema Definition

| Name         | Type                                                                                        | Required | Description                                                                                                                                                                                                                                                     |
| ------------ | ------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | [UCP Response Checkout Schema](/draft/specification/checkout/#ucp-response-checkout-schema) | **Yes**  | Protocol metadata for discovery profiles and responses. Uses slim schema pattern with context-specific required fields.                                                                                                                                         |
| id           | string                                                                                      | **Yes**  | Unique identifier of the checkout session.                                                                                                                                                                                                                      |
| line_items   | Array\[[Line Item Response](/draft/specification/checkout/#line-item-response)\]            | **Yes**  | List of line items being checked out.                                                                                                                                                                                                                           |
| buyer        | [Buyer](/draft/specification/checkout/#buyer)                                               | No       | Representation of the buyer.                                                                                                                                                                                                                                    |
| status       | string                                                                                      | **Yes**  | Checkout state indicating the current phase and required action. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled` |
| currency     | string                                                                                      | **Yes**  | ISO 4217 currency code reflecting the merchant's market determination. Derived from address, context, and geo IP—buyers provide signals, merchants determine currency.                                                                                          |
| totals       | Array\[[Total Response](/draft/specification/checkout/#total-response)\]                    | **Yes**  | Different cart totals.                                                                                                                                                                                                                                          |
| messages     | Array\[[Message](/draft/specification/checkout/#message)\]                                  | No       | List of messages with error and info about the checkout session state.                                                                                                                                                                                          |
| links        | Array\[[Link](/draft/specification/checkout/#link)\]                                        | **Yes**  | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                    |
| expires_at   | string                                                                                      | No       | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                    |
| continue_url | string                                                                                      | No       | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                 |
| payment      | [Payment](/draft/specification/checkout/#payment)                                           | No       | Payment configuration containing handlers.                                                                                                                                                                                                                      |
| order        | [Order Confirmation](/draft/specification/checkout/#order-confirmation)                     | No       | Details about an order created for this checkout session.                                                                                                                                                                                                       |

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

**Error processing OpenAPI:** [Errno 2] No such file or directory: 'source/services/shopping/rest.openapi.json'

### Get Checkout

It provides the latest state of the checkout resource. After cancellation or completion it is up to the business on what to return (i.e this can be a long lived state or expire after a particular TTL - resulting in a 'not found' error). From the platform there is no specific enforcement for a TTL of the checkout.

The platform will honor the TTL provided by the business via `expires_at` at the time of checkout session creation.

**Error processing OpenAPI:** [Errno 2] No such file or directory: 'source/services/shopping/rest.openapi.json'

### Update Checkout

Performs a full replacement of the checkout resource. The platform is **REQUIRED** to send the entire checkout resource containing any data updates to write-only data fields. The resource provided in the request will replace the existing checkout session state on the business side.

**Error processing OpenAPI:** [Errno 2] No such file or directory: 'source/services/shopping/rest.openapi.json'

### Complete Checkout

This is the final checkout placement call. To be invoked when the user has committed to pay and place an order for the chosen items. The response of this call is the checkout object with the `order` field populated in it. The returned `order` provides necessary identifiers, such as `id` and `permalink_url`, that can be used to reference the full state of the placed order. At the time of order persistence, fields from `Checkout` **MAY** be used to construct the order representation (i.e. information like `line_items`, `fulfillment` will be used to create the initial order representation).

After this call, other details will be updated through subsequent events as the order, and its associated items, moves through the supply chain.

**Error processing OpenAPI:** [Errno 2] No such file or directory: 'source/services/shopping/rest.openapi.json'

### Cancel Checkout

This operation will be used to cancel a checkout session, if it can be canceled. If the checkout session cannot be canceled (e.g. checkout session is already canceled or completed), then businesses **SHOULD** send back an error indicating the operation is not allowed. Any checkout session with a status that is not equal to `completed` or `canceled` **SHOULD** be cancelable.

**Error processing OpenAPI:** [Errno 2] No such file or directory: 'source/services/shopping/rest.openapi.json'

## Transport Bindings

The abstract operations above are bound to specific transport protocols as defined below:

- [REST Binding](https://ucp.dev/draft/specification/checkout-rest/index.md): RESTful API mapping using standard HTTP verbs and JSON payloads.
- [MCP Binding](https://ucp.dev/draft/specification/checkout-mcp/index.md): Model Context Protocol mapping for agentic interaction.
- [A2A Binding](https://ucp.dev/draft/specification/checkout-a2a/index.md): Agent-to-Agent Protocol mapping for agentic interactions.
- [Embedded Checkout Binding](https://ucp.dev/draft/specification/embedded-checkout/index.md): JSON-RPC for powering embedded checkout.

## Entities

### Buyer

| Name         | Type   | Required | Description              |
| ------------ | ------ | -------- | ------------------------ |
| first_name   | string | No       | First name of the buyer. |
| last_name    | string | No       | Last name of the buyer.  |
| email        | string | No       | Email of the buyer.      |
| phone_number | string | No       | E.164 standard.          |

### Context

Context signals are provisional hints. Businesses SHOULD use these values when authoritative data (e.g. address) is absent, and MAY ignore unsupported values without returning errors. This differs from authoritative selections which require explicit validation and error feedback.

| Name            | Type   | Required | Description                                                                                                                                                                                                                                                                                                                                                                         |
| --------------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| address_country | string | No       | The country. Recommended to be in 2-letter ISO 3166-1 alpha-2 format, for example "US". For backward compatibility, a 3-letter ISO 3166-1 alpha-3 country code such as "SGP" or a full country name such as "Singapore" can also be used. Optional hint for market context (currency, availability, pricing)—higher-resolution data (e.g., shipping address) supersedes this value. |
| address_region  | string | No       | The region in which the locality is, and which is in the country. For example, California or another appropriate first-level Administrative division. Optional hint for progressive localization—higher-resolution data (e.g., shipping address) supersedes this value.                                                                                                             |
| postal_code     | string | No       | The postal code. For example, 94043. Optional hint for regional refinement—higher-resolution data (e.g., shipping address) supersedes this value.                                                                                                                                                                                                                                   |
| intent          | string | No       | Background context describing buyer's intent (e.g., 'looking for a gift under $50', 'need something durable for outdoor use'). Informs relevance, recommendations, and personalization.                                                                                                                                                                                             |

### Fulfillment Option

**Error:** Schema file 'fulfillment_resp.json' not found in any schema directory.

### Item

#### Item Create Request

**Error:** Schema 'types/item.create' not found in any schema directory.

#### Item Update Request

**Error:** Schema 'types/item.update' not found in any schema directory.

#### Item Response

| Name      | Type    | Required | Description                                                                                                                                                                 |
| --------- | ------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id        | string  | **Yes**  | The product identifier, often the SKU, required to resolve the product details associated with this line item. Should be recognized by both the Platform, and the Business. |
| title     | string  | **Yes**  | Product title.                                                                                                                                                              |
| price     | integer | **Yes**  | Unit price in minor (cents) currency units.                                                                                                                                 |
| image_url | string  | No       | Product image URI.                                                                                                                                                          |

### Line Item

#### Line Item Create Request

**Error:** Schema 'types/line_item.create' not found in any schema directory.

#### Line Item Update Request

**Error:** Schema 'types/line_item.update' not found in any schema directory.

#### Line Item Response

| Name      | Type                                                   | Required | Description                                            |
| --------- | ------------------------------------------------------ | -------- | ------------------------------------------------------ |
| id        | string                                                 | **Yes**  |                                                        |
| item      | [Item](/draft/specification/checkout/#item)            | **Yes**  |                                                        |
| quantity  | integer                                                | **Yes**  | Quantity of the item being purchased.                  |
| totals    | Array\[[Total](/draft/specification/checkout/#total)\] | **Yes**  | Line item totals breakdown.                            |
| parent_id | string                                                 | No       | Parent line item identifier for any nested structures. |

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

This object MUST be one of the following types: [Message Error](/draft/specification/checkout/#message-error), [Message Warning](/draft/specification/checkout/#message-warning), [Message Info](/draft/specification/checkout/#message-info).

### Message Error

| Name         | Type   | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------ | ------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = error**. Message type discriminator.                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| code         | string | **Yes**  | Error code. Possible values include: missing, invalid, out_of_stock, payment_declined, requires_sign_in, requires_3ds, requires_identity_linking. Freeform codes also allowed.                                                                                                                                                                                                                                                                                                                                 |
| path         | string | No       | RFC 9535 JSONPath to the component the message refers to (e.g., $.items[1]).                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| content      | string | **Yes**  | Human-readable message.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| severity     | string | **Yes**  | Declares who resolves this error. 'recoverable': agent can fix via API. 'requires_buyer_input': merchant requires information their API doesn't support collecting programmatically (checkout incomplete). 'requires_buyer_review': buyer must authorize before order placement due to policy, regulatory, or entitlement rules (checkout complete). Errors with 'requires\_*' severity contribute to 'status: requires_escalation'.* *Enum:*\* `recoverable`, `requires_buyer_input`, `requires_buyer_review` |

### Message Info

| Name         | Type   | Required | Description                                                    |
| ------------ | ------ | -------- | -------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = info**. Message type discriminator.               |
| path         | string | No       | RFC 9535 JSONPath to the component the message refers to.      |
| code         | string | No       | Info code for programmatic handling.                           |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown` |
| content      | string | **Yes**  | Human-readable message.                                        |

### Message Warning

| Name         | Type   | Required | Description                                                                                                                           |
| ------------ | ------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = warning**. Message type discriminator.                                                                                   |
| path         | string | No       | JSONPath (RFC 9535) to related field (e.g., $.line_items[0]).                                                                         |
| code         | string | **Yes**  | Warning code. Machine-readable identifier for the warning type (e.g., final_sale, prop65, fulfillment_changed, age_restricted, etc.). |
| content      | string | **Yes**  | Human-readable warning message that MUST be displayed.                                                                                |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                        |

### Payment

| Name        | Type                                                                                               | Required | Description                                                                                                                                                                                                                |
| ----------- | -------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| instruments | Array\[[Selected Payment Instrument](/draft/specification/checkout/#selected-payment-instrument)\] | No       | The payment instruments available for this payment. Each instrument is associated with a specific handler via the handler_id field. Handlers can extend the base payment_instrument schema to add handler-specific fields. |

### Payment Instrument

| Name            | Type                                                                    | Required | Description                                                                                                                                                  |
| --------------- | ----------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| id              | string                                                                  | **Yes**  | A unique identifier for this instrument instance, assigned by the platform.                                                                                  |
| handler_id      | string                                                                  | **Yes**  | The unique identifier for the handler instance that produced this instrument. This corresponds to the 'id' field in the Payment Handler definition.          |
| type            | string                                                                  | **Yes**  | The broad category of the instrument (e.g., 'card', 'tokenized_card'). Specific schemas will constrain this to a constant value.                             |
| billing_address | [Postal Address](/draft/specification/checkout/#postal-address)         | No       | The billing address associated with this payment method.                                                                                                     |
| credential      | [Payment Credential](/draft/specification/checkout/#payment-credential) | No       | The base definition for any payment credential. Handlers define specific credential types.                                                                   |
| display         | object                                                                  | No       | Display information for this payment instrument. Each payment instrument schema defines its specific display properties, as outlined by the payment handler. |

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

| Name                                                                                        | Type | Required | Description |
| ------------------------------------------------------------------------------------------- | ---- | -------- | ----------- |
| **Error:** Failed to resolve ''. Ensure ucp-schema is installed: `cargo install ucp-schema` |      |          |             |

### Total

#### Total Response

| Name         | Type    | Required | Description                                                                                                                   |
| ------------ | ------- | -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| type         | string  | **Yes**  | Type of total categorization. **Enum:** `items_discount`, `subtotal`, `discount`, `fulfillment`, `tax`, `fee`, `total`        |
| display_text | string  | No       | Text to display against the amount. Should reflect appropriate method (e.g., 'Shipping', 'Delivery').                         |
| amount       | integer | **Yes**  | If type == total, sums subtotal - discount + fulfillment + tax + fee. Should be >= 0. Amount in minor (cents) currency units. |

### UCP Response Checkout

| Name                                                                                        | Type | Required | Description |
| ------------------------------------------------------------------------------------------- | ---- | -------- | ----------- |
| **Error:** Failed to resolve ''. Ensure ucp-schema is installed: `cargo install ucp-schema` |      |          |             |
| services                                                                                    | any  | No       |             |
| capabilities                                                                                | any  | No       |             |
| payment_handlers                                                                            | any  | **Yes**  |             |

### Order Confirmation

| Name          | Type   | Required | Description                                     |
| ------------- | ------ | -------- | ----------------------------------------------- |
| id            | string | **Yes**  | Unique order identifier.                        |
| permalink_url | string | **Yes**  | Permalink to access the order on merchant site. |
