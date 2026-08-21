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

# Checkout Capability

* **Capability Name:** `dev.ucp.shopping.checkout`

## Overview

Allows platforms to facilitate checkout sessions. The checkout has to be
finalized manually by the user through a trusted UI unless the AP2 Mandates
extension is supported.

The business remains the Merchant of Record (MoR), and they don't need to become
PCI DSS compliant to accept card payments through this Capability.

### Flow overview

![High-level checkout flow sequence diagram](site:specification/images/ucp-checkout-flow.png)

### Payments

Payment handlers are discovered from the business's UCP profile at
`/.well-known/ucp` and checkout.ucp.payment_handlers. The handlers define
the processing specifications for collecting payment instruments
(e.g., Google Pay, Shop Pay). When the buyer submits payment, the platform
populates the `payment.instruments` array with the collected instrument data.

The `payment` object is optional on checkout creation and may be omitted for
use cases that don't require payment processing (e.g., quote generation, cart
management).

Businesses may also populate `payment.instruments` on responses with
display-safe payment instruments from their own user state, such as payment
methods the authenticated buyer has saved with the business. Such an instrument
carries no raw credential: it is a display-safe, business-scoped reference (an
opaque `id` plus `display` fields) that the business resolves server-side when
the buyer selects it. The
[create checkout REST example](rest.md#create-checkout) already returns
this shape for a Shop Pay instrument. Returning user-specific saved state
requires a user-authenticated request; see
[Identity Linking](../../common/identity-linking/index.md#business-populated-response-values) for
the access levels and scopes that gate it.

The `display` fields let the platform present a saved instrument and let the
buyer recognize it. Whether the instrument can be charged as-is or still
requires credential collection is not distinguished by the base schema today, so
platforms should not infer readiness from the absence of a `credential` or from
`id` naming.

### Fulfillment

Fulfillment is modelled as an extension in UCP to account for diverse use cases.

Fulfillment is optional in the checkout object. This is done to enable a
platform to perform checkout for digital goods without needing to furnish
fulfillment details more relevant for physical goods.

### Quantity and sale basis

Checkout applies the shared
[quantities and units](../../overview/index.md#quantities-and-units) contract, including the
default (`C62`, `0`) identity. The Business determines each item's authoritative
sale basis for the transaction. The Business's response is authoritative, and
each `line_items[].quantity` is an integer step count in that basis.

**Discovering the sale basis.** The sale basis is item data: the Platform
**SHOULD** discover an item's `quantity_unit` — including `scale` and any
`increment` — from the
[catalog](../catalog/index.md#sale-basis-and-quantity-units) before transacting.
A Platform without catalog knowledge can omit the descriptor: the Business
applies its authoritative basis and confirms it on the response line, and the
Platform inspects the echoed descriptor and, if that interpretation is not
what it intended, resubmits the quantity denominated in the now-known basis.
Asserting `quantity_unit` on a request (below) is how the Platform checks that
a basis it previously discovered still holds; a Platform that does not know
the basis omits the descriptor rather than asserting a guess.

**Requesting a quantity.** When a Platform request omits
`line_items[].item.quantity_unit`, the Platform makes no assertion about the
sale-basis identity. The Business interprets `quantity` using the item's
authoritative sale basis. A request for a measure-denominated item can therefore
omit the descriptor without asserting the default identity.

The Platform **MAY** include `quantity_unit` on a request line to assert the
basis it believes it is ordering in. When the Platform includes it, the Business
**MUST** compare the asserted and authoritative
[machine identities](../../overview/index.md#quantities-and-units). An explicit assertion
with `unit: "C62"` and effective `scale` `0` matches the default identity
represented by an absent descriptor; a `display_text` difference is not a
mismatch.

If an asserted `quantity_unit` does not match the item's authoritative sale
basis, the requested quantity is denominated in a basis the Business does not
sell in. Silent conversion is forbidden in both directions: neither party may
reinterpret a quantity the other denominated without surfacing the change. The
Business resolves the mismatch in one of two ways:

* **Convert, visibly.** When the Business can convert the asserted
    basis to its authoritative basis (for example, pounds to kilograms), it
    **MAY** apply the request as a visible line revision: the line carries the
    authoritative descriptor and the converted quantity — rounded once to the
    authoritative `scale` according to its rules, with any ordering-increment
    policy applied after conversion — and the response includes a warning
    `messages[]` entry at the line. UCP defines no conversion factors or
    dimensions; whether to convert is the Business's own determination.
* **Reject, recoverably.** When it cannot or chooses not to convert (for
    example, a quantity of fasteners denominated in litres), the Business
    **MUST** reject the request's effect on that line with a recoverable
    business outcome naming the authoritative basis. On update, the line
    remains at its previous authoritative state. On create, the line is not created and the
    message identifies the item in `content`; when no line can be created, the
    Business **MAY** return an error response instead.

In both cases the response reflects authoritative state, never an echo of
rejected input, and every line present carries its authoritative sale basis
under the response-echo rule. The Platform recovers by reading the echoed
descriptor — or re-reading the catalog — and resubmitting; the message
`content` is explanatory text for humans, never the recovery input.

For example, an industrial supplier sells loose fasteners by the kilogram,
but stale data leads a Platform to believe they are sold by the pound. It
submits an update asserting that basis:

<!-- ucp:example schema=shopping/checkout op=update direction=request -->
```json
{
  "line_items": [
    {
      "id": "li_fasteners",
      "item": {
        "id": "var_fasteners",
        "quantity_unit": { "unit": "LBR", "scale": 2, "display_text": "lb" }
      },
      "quantity": 275
    }
  ]
}
```

A Business that converts applies the update as a visible revision.
The line is denominated in the authoritative basis — the requested 2.75 lb
converts to 1.25 kg, rounded once to `scale` 2 — and a warning marks the
revision:

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { "version": "{{ ucp_version }}", "status": "success", "payment_handlers": {} },
  "id": "chk_fasteners_1",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_fasteners",
      "item": {
        "id": "var_fasteners",
        "title": "Stainless Steel Fasteners",
        "price": 1299,
        "quantity_unit": { "unit": "KGM", "scale": 2, "display_text": "kg" }
      },
      "quantity": 125,
      "totals": [
        { "type": "subtotal", "amount": 1624 },
        { "type": "total", "amount": 1624 }
      ]
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "quantity_unit_converted",
      "path": "$.line_items[0].quantity",
      "content": "This item is sold by the kilogram. The requested 2.75 lb was converted to 1.25 kg."
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 1624 },
    { "type": "total", "amount": 1624 }
  ],
  "links": []
}
```

A Business that does not convert rejects the update instead. The line remains
unchanged — `quantity` stays `150` (1.50 kg), not a reinterpretation of the
requested `275` — and the error names the authoritative basis:

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { "version": "{{ ucp_version }}", "status": "success", "payment_handlers": {} },
  "id": "chk_fasteners_1",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_fasteners",
      "item": {
        "id": "var_fasteners",
        "title": "Stainless Steel Fasteners",
        "price": 1299,
        "quantity_unit": { "unit": "KGM", "scale": 2, "display_text": "kg" }
      },
      "quantity": 150,
      "totals": [
        { "type": "subtotal", "amount": 1949 },
        { "type": "total", "amount": 1949 }
      ]
    }
  ],
  "messages": [
    {
      "type": "error",
      "code": "quantity_unit_mismatch",
      "severity": "recoverable",
      "path": "$.line_items[0].item.quantity_unit",
      "content": "This item is sold by the kilogram, not by the pound. Resubmit the quantity as a count of 0.01-kg steps."
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 1949 },
    { "type": "total", "amount": 1949 }
  ],
  "links": []
}
```

**Ordering increment.** The sale basis **MAY** declare an
[`increment`](../../overview/index.md#ordering-increment) — the ordering granularity, in
steps, the Business sells in. The declaration lets the Platform build quantity
steppers and validate input before submission. Platform-authored quantities
**SHOULD** be integer multiples of the line's effective increment. The
increment is merchandising policy, not a representational bound, and schema
validation does not enforce it: on receiving an off-increment quantity, the
Business **MAY** accept it, revise the line to an increment multiple, or reject
it with a recoverable business outcome. A revision **MUST** be returned as a
revised line `quantity` with an explanatory `messages[]` entry; the Business
**MUST NOT** silently reinterpret the requested quantity. The Business **MAY**
also revise a quantity for its own reasons (for example, limited stock); such
revisions **SHOULD** stay on the increment grid so subsequent Platform stepper
edits from the revised value remain on-grid.

For example, bananas sold by the pound in quarter-pound multiples
(`increment` `25` at `scale` `2`). A request for `quantity` `137` (1.37 lb) is
off-increment; a Business that snaps it returns the line revised to `125` with
a warning:

<!-- ucp:example schema=shopping/checkout target=$.messages op=read -->
```json
[
  {
    "type": "warning",
    "code": "quantity_increment_revised",
    "path": "$.line_items[0].quantity",
    "content": "This item is sold in 0.25 lb increments. Your requested 1.37 lb was adjusted to 1.25 lb."
  }
]
```

**Echoing the sale basis.** The Business **MAY** omit `quantity_unit` from a
response line whose effective sale-basis identity is the default identity. The
Business **MUST** include `quantity_unit` on the item in every Cart, Checkout,
and Order line response whenever the effective identity differs from the
default identity. Omission would otherwise make a measure-denominated line read
as a count of whole items.

**Pricing a line.** `item.price` is the amount per one whole
`quantity_unit.unit` (for example, per kg or per hour); when `quantity_unit` is
absent, it is the price per `each`. Other characteristics of a sale unit may
affect the quoted `item.price`, but do not change its sale-basis denominator.
The Business **MUST** compute the line total as
`price × quantity × 10^-scale` and round once at the line. The presented
`totals[]` remain authoritative (see [Totals](index.md#totals)). The Platform
**MUST NOT** recompute a line total from the fractional quantity and substitute
its own rounding.

**Pricing basis.** `item.price` is always denominated against the sale basis,
but the Business MAY quote it from a different measurement basis — for
example, apples priced per pound and sold per `each`. On authoritative
responses the Business **MUST** include `item.unit_price` on every cart,
checkout, and order line whose pricing basis differs from its sale basis: the
rate that determines the charge travels with the line, exactly as the sale
basis itself does. When the pricing basis is the sale basis, `unit_price`
remains a catalog display comparator and MAY be omitted from lines. Presence
on a line is the marker: a line-level `unit_price` is transactional; a
catalog-only one is display.

For example, a Business sells bananas by the pound with `quantity_unit`
`{ "unit": "LBR", "scale": 2, "display_text": "lb", "increment": 25 }` and a
`price` of `79` ($0.79/lb). A Buyer orders 1.50 lb, so the Platform sends
`quantity` `150` — 150 hundredth-of-a-pound steps. The line total is
`79 × 150 × 10^-2 = 118.5`, rounded once per its pricing rules to `119`
($1.19):

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { "version": "{{ ucp_version }}", "status": "success", "payment_handlers": {} },
  "id": "chk_bananas_1",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_bananas",
      "item": {
        "id": "var_bananas",
        "title": "Bananas",
        "price": 79,
        "quantity_unit": { "unit": "LBR", "scale": 2, "display_text": "lb", "increment": 25 }
      },
      "quantity": 150,
      "totals": [
        { "type": "subtotal", "amount": 119 },
        { "type": "total", "amount": 119 }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 119 },
    { "type": "total", "amount": 119 }
  ],
  "links": []
}
```

### Checkout Status Lifecycle

The checkout `status` field indicates the current phase of the session and
determines what processing is required next. The business sets the status; the
platform receives messages indicating what's needed to progress.

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

* **`incomplete`**: Checkout session is missing required information or has
    issues that need resolution. Platform should inspect `messages` array for
    context and should attempt to resolve via Update Checkout. When an active
    extension surfaces an Action, that instance may identify work the Business
    needs completed before it can return `ready_for_complete`.

* **`requires_escalation`**: Checkout session requires information that
    cannot be provided via API, or buyer input is required. Platform should
    inspect `messages` to understand what's needed (see Error Handling below).
    If any `recoverable` errors exist, resolve those first.
    Then hand off to buyer via `continue_url`.

* **`ready_for_complete`**: Checkout session has all necessary information
    and platform can finalize programmatically. No Action remains outstanding.
    Platform can call Complete Checkout.

* **`complete_in_progress`**: The Complete Checkout request was accepted and the
    Business is processing the order. The response **MUST NOT** contain `order`.
    An Action can be outstanding in this state. See [Actions](#actions) for how
    the Platform proceeds.

* **`completed`**: Order placed successfully. `order` is present and no Action
    remains outstanding.

* **`canceled`**: Checkout session is invalid or expired. Platform should
    start a new checkout session if needed. No Action remains outstanding.

### Actions

When an active extension has outstanding work for the checkout, the Business
surfaces instances under the Action types that extension declares in the
response-only `actions` map. The common rules are defined in
[Overview — Actions](../../overview/index.md#actions); this section states only how the
checkout status lifecycle interprets them.
[Status Values](#status-values) is the authoritative home for the status
invariants governing outstanding Actions.

Every Action gates the effect specified for its Action type. While `incomplete`,
an Action may identify work the Business needs completed before it can return
`ready_for_complete`. After processing the Action according to its Action type's
contract, the Platform **SHOULD** use [Get Checkout](#get-checkout) or, outside
`complete_in_progress`, a subsequent [Update Checkout](#update-checkout)
response to obtain the latest Checkout.

An Action does not select the Checkout status, and a Message's type or severity
does not determine whether the Action gates its Action-defined effect. A Message
can report the outcome of a particular operation. An info or warning Message can
identify an outstanding Action without reporting failure. A recoverable error
Message can identify an Action to report that the requested effect was not
applied because of it. In that case, the Business returns the current Checkout
and sets the Message's `path` to the exact Action occurrence, as defined in
[Overview — Actions](../../overview/index.md#actions). The Message does not turn the Action
into a lock on unrelated Checkout operations.

If an Action prevents Complete Checkout from being accepted, the Business
**MUST** return the current Checkout with `status: incomplete` and an error
Message with `severity: "recoverable"` whose `path` selects that exact Action
occurrence. Processing the Action does not retry the rejected Complete Checkout
request. A later Complete Checkout request is a new operation under the existing
idempotency rules.

#### Accepted completion

`complete_in_progress` means Complete Checkout was accepted. The Checkout state
reported by the Business is authoritative. While a Checkout has this status, the
following operation contract applies:

| Operation | Contract |
| :-------- | :------- |
| Get Checkout | The Platform **MAY** invoke Get Checkout; the Business's response is authoritative. The Platform **MAY** repeat Get Checkout with bounded backoff set by the Action contract or Platform policy, and **MUST** stop repeated requests at `expires_at`. |
| Update Checkout | The Platform **MUST NOT** start a new Update Checkout operation. Duplicate requests remain subject to [Replay Protection](../../signatures.md#replay-protection). If the Business receives a new Update Checkout request, it **MUST** leave the Checkout unchanged and return the current Checkout with a recoverable error Message. |
| Complete Checkout | The Platform **MUST NOT** start a new Complete Checkout operation during `complete_in_progress`. See [Complete Checkout](#complete-checkout) for the narrow lost-response recovery retry. |
| Cancel Checkout | The Platform **MUST** follow the fallback, handoff, and cancellation race rules below before attempting Cancel Checkout. |

When a `complete_in_progress` Checkout includes an Action, the Platform
processes it according to its Action-type contract. When it contains no Action,
the Platform **SHOULD** use Get Checkout to observe Business processing.

Because Update Checkout is unavailable after Complete Checkout is accepted, the
Business **MUST** surface any Action that requires input through Update Checkout
before accepting Complete Checkout.

After an Action's extension-defined processing completes, the Business might
need time to receive and apply its result. The Action completion signal is not
authoritative for Checkout state. The Platform **MUST** use
[Get Checkout](#get-checkout) to confirm that the Business reflected the result,
for example by removing the Action or changing the Checkout status.

If the same Action key and `id` remain, the Platform **MUST NOT** process it
again unless its contract explicitly permits retry and every safe-retry
condition holds. A replacement with a fresh `id` is new work. If the Action
disappears, that Action is no longer outstanding.

If the Platform cannot complete an Action, or the Business does not update the
Checkout within a timeout set by the Action contract or Platform policy before
`expires_at`, the Platform **SHOULD** follow any applicable Action fallback. If
no fallback can continue the Checkout and `continue_url` is available, the
Platform **SHOULD** use it to hand off the Checkout to the Buyer. The Platform
**MUST NOT** attempt Cancel Checkout while either fallback or handoff can still
continue the Checkout.

If neither fallback nor handoff can continue, the Platform **SHOULD** use Get
Checkout to retrieve the latest state and attempt Cancel Checkout only if it
still reports `complete_in_progress`. Cancellation can race completion; the
Platform **MUST NOT** treat the Checkout as canceled unless the Business reports
`status: canceled`.

### Error Handling

The `messages` array contains errors, warnings, and informational messages
about the checkout state. `ucp.status` is the shape discriminator —
`"success"` means the response carries the expected payload, `"error"`
means it carries error information instead. Each error message carries a `type`,
`code`, `severity`, `content`, and an optional `path` that identifies the
specific response component the message refers to, including a field, line
item, or Action occurrence (see [The `path` Field](#the-path-field) below). The
`severity` field prescribes the recommended platform action:

| Severity                | Meaning                                       | Platform Action                                                               |
| :---------------------- | :-------------------------------------------- | :---------------------------------------------------------------------------- |
| `recoverable`           | Platform can resolve the condition in band    | Modify inputs or process a related Action; submit a new operation when needed |
| `requires_buyer_input`  | Business requires input not available via API | Hand off via `continue_url`                                                   |
| `requires_buyer_review` | Buyer review and authorization is required    | Hand off via `continue_url`                                                   |
| `unrecoverable`         | No resource exists to act on                  | Retry with new resource or inputs, or hand off via `continue_url`             |

Errors with `requires_*` severity contribute to `status: requires_escalation`.
Both result in buyer handoff, but represent different checkout states.

* `requires_buyer_input` means the checkout is **incomplete** — the business
requires information their API doesn't support collecting programmatically.
* `requires_buyer_review` means the checkout is **complete** — but policy,
regulatory, or entitlement rules require buyer authorization before order
placement (e.g., high-value order approval, first-purchase policy).

When the business cannot create a new resource or the requested resource
no longer exists, the response contains `ucp.status: "error"` with
`messages` describing the failure — no resource is included in the
response body. When no resource exists to act on, messages SHOULD use
`severity: "unrecoverable"`.
For example, a business may reject a create checkout request where all
items are unavailable:

<!-- ucp:example schema=common/types/error_response op=read -->
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

See [REST](rest.md#create-checkout) and
[MCP](mcp.md#create_checkout) binding examples.

#### Error Processing Algorithm

When status is `incomplete` or `requires_escalation`, platforms should process
errors as a prioritized stack. The example below illustrates a checkout with
three error types: a recoverable error (invalid phone), a buyer input
requirement (delivery scheduling), and a review requirement (high-value order).
The latter two require handoff and serve as explicit signals to the platform.
Businesses **SHOULD** surface such messages as early as possible, and platforms
**SHOULD** prioritize resolving recoverable errors before initiating handoff.
When a recoverable error's `path` selects an Action occurrence, the Platform
processes it according to [Actions](#actions) and re-evaluates the latest
Checkout before submitting another operation. The example algorithm below
covers recoverable input errors whose paths do not select Actions.

<!-- ucp:example schema=shopping/checkout target=$.messages op=read -->
```json
[
  {
    "type": "error",
    "code": "invalid_phone",
    "severity": "recoverable",
    "path": "$.buyer.phone_number",
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
    IF error.path is present
      IDENTIFY the field at error.path in the request payload
      ATTEMPT to fix that field (e.g., reformat phone at $.buyer.phone_number)
    ELSE
      ATTEMPT generic fix based on error.code
  CALL Update Checkout
  RETURN and re-evaluate response

IF requires_buyer_input is not empty
  handoff_context = "incomplete, additional input from buyer is required"
ELSE IF requires_buyer_review is not empty
  handoff_context = "ready for final review by the buyer"
```

#### Standard Errors

Standard errors are standardized error codes that platforms are expected to
handle with specific, appropriate UX rather than generic error treatment.

| Code                     | Description                                                                |
| :----------------------- | :------------------------------------------------------------------------- |
| `out_of_stock`           | Specific item or variant is unavailable                                    |
| `item_unavailable`       | Item cannot be purchased (e.g. delisted)                                   |
| `address_undeliverable`  | Cannot deliver to the provided address                                     |
| `payment_failed`         | Payment processing failed                                                  |
| `eligibility_invalid`    | Eligibility claim could not be verified at completion                      |

Businesses **SHOULD** mark standard errors with `severity: recoverable` to
signal that platforms should provide appropriate UX (out-of-stock messaging,
address validation prompts, payment method changes) rather than generic error
messages or deferring to checkout completion.

Example: `out_of_stock` requires specific upfront UX, whereas
`payment_required` can be handled generically at submission.

#### The `path` Field

The optional `path` field on a message anchors it to a specific component of the
response payload. Platforms use it to associate messages with an input field,
line item, or Action occurrence — for example, highlighting a specific buyer
field, flagging a cart line, or identifying the Action related to an operation
outcome.

`path` **MUST** be an [RFC 9535](https://www.rfc-editor.org/rfc/rfc9535)
JSONPath expression relative to the root of the UCP response object. When `path`
is omitted, the message applies to the response as a whole.

**Simple field reference:**

<!-- ucp:example skip reason="path schema example" -->
```json
{ "path": "$.buyer.email" }
```

**Indexed array element:**

<!-- ucp:example skip reason="path schema example" -->
```json
{ "path": "$.line_items[0].quantity" }
```

**Action occurrence:**

<!-- ucp:example skip reason="path schema example" -->
```json
{
  "path": "$.actions['com.example.identity.student_verification'][0]"
}
```

**Specificity rule:** A path to a specific field (e.g.,
`$.line_items[0].quantity`) takes precedence over a path to its parent
(e.g., `$.line_items[0]`). When multiple errors apply to the same field,
each message **SHOULD** carry the most specific path applicable.

#### Eligibility Verification at Completion

Platforms provide `context.eligibility` — buyer claims about eligible benefits
such as loyalty membership, payment instrument perks, and similar. These are
claims, not verified facts. Businesses **MAY** act on recognized claims during
the session (adjusting pricing, granting product access, applying provisional
discounts), but all accepted claims **MUST** be resolved before the
transaction can complete.

Unrecognized or inapplicable claims **MUST NOT** block the checkout.
Businesses **SHOULD** notify the buyer via `messages` with `type: "warning"`
when a claim is not accepted, and **MAY** use `type: "info"` to explain
the effects of accepted claims. At completion, accepted claims that remain
unverified **MUST** result in `type: "error"` with
`code: "eligibility_invalid"` (see below).

**Eligibility message codes:**

| Type      | Code                       | When                                               |
| --------- | -------------------------- | -------------------------------------------------- |
| `warning` | `eligibility_not_accepted` | Claim not recognized or not applicable             |
| `info`    | `eligibility_accepted`     | Effect of an accepted claim                        |
| `error`   | `eligibility_invalid`      | Accepted claim could not be verified at completion |

A claim is resolved when it is either **verified** or **rescinded**:

* **Verified**: The Business confirms the claim against a proof. UCP does not
  prescribe how verification occurs — proof may come from the payment
  credential, an Action surfaced by a negotiated extension, or any
  other mechanism negotiated between Platform and Business.
* **Rescinded**: The Platform removes the claim from `context.eligibility`
  before completion (e.g., buyer changes payment method, withdraws a
  membership claim). Once removed, the Business recalculates without it.

Businesses **MUST NOT** complete a transaction with unresolved eligibility
claims. Unverified claims may result in incorrect pricing or unauthorized
access to restricted products.

**When verification fails:**

The Business **MUST** return an error in `messages` with
`code: "eligibility_invalid"` and `severity: "recoverable"`. When an Action
prevents the requested effect, the Business **MUST** set that error
Message's `path` to select the exact Action occurrence as specified in
[Actions](#actions). Otherwise, the Business **SHOULD** use `path` to identify
which specific claim(s) could not be verified. Any Action or discount state
contributed by a negotiated extension **MAY** remain current according to that
extension. The Platform
**MAY** then retry that extension's verification flow, use
[Update Checkout](#update-checkout) for ordinary checkout changes (e.g.,
remove ineligible items) or to rescind the claim, or abandon the attempt.

##### Example: resolving a claim with a verification Action

This example is illustrative. It uses a negotiated vendor extension,
`com.example.identity.student_verification`, that declares a single Action type
under a key of the same name in `actions` and defines the instance `config` and
verification transport. It composes that extension with `context.eligibility`, a
provisional [Discount](../extensions/discount.md), an [Action](#actions), and
`messages`.

The provisional discount fields (`provisional`, `eligibility`) belong to the
[Discount extension](../extensions/discount.md#eligibility-claims) and are available only when
that extension is active for the checkout.

**1. Claim accepted, discount provisional, verification Action outstanding.**
The Platform submits `org.example.student` in `context.eligibility` on Create
Checkout. The Business accepts the claim and, with the Discount extension
active, returns a provisional discount, an explanatory `info` message, and a
verification Action. The claim is unresolved, so the checkout stays
`incomplete`:

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_student_1",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [ ... ],
  "discounts": {
    "applied": [
      {
        "title": "Student 10% Off",
        "amount": 500,
        "automatic": true,
        "provisional": true,
        "eligibility": "org.example.student"
      }
    ]
  },
  "totals": [ ... ],
  "links": [ ... ],
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
      "content": "Student discount applied provisionally. Verify your student status to keep it.",
      "path": "$.actions['com.example.identity.student_verification'][0]"
    }
  ]
}
```

The Platform runs the extension-defined verification flow. The Business receives
the outcome out of band. Once that flow is complete, the Platform uses
[Get Checkout](#get-checkout) to retrieve the updated state.

**2. Verified.** The Business resolves the claim: the verification Action is
removed from `actions`, the discount is confirmed (no longer `provisional`), and
the explanatory `info` message is updated. With the claim resolved, the checkout
**MAY** advance to `ready_for_complete`.

**3. Invalid proof.** If the submitted proof does not verify, the claim stays
unresolved. The Business returns an `eligibility_invalid` error with
`severity: recoverable` (per [When verification fails](#eligibility-verification-at-completion))
and the checkout does not reach `ready_for_complete`. The Platform **MAY**
provide valid proof and retry the verification flow, or rescind the claim.

**4. Rescission.** The Platform rescinds the claim with an
[Update Checkout](#update-checkout) that removes it from `context.eligibility`;
the Business then recalculates without the provisional discount.

### Warning Presentation

The `presentation` field on warning messages controls the rendering
contract the platform **MUST** follow. When omitted, it defaults to
`"notice"`.

| | `notice` (default) | `disclosure` |
| :--- | :--- | :--- |
| Display content | **MUST** | **MUST** |
| Proximity to `path` | **MAY** | **MUST** |
| Dismissible | **MAY** | **MUST NOT** |
| Render `image_url` | **MAY** | **MUST** |
| Render `url` | **MAY** | **SHOULD** |
| Escalate if cannot honor | — | **MUST** via `continue_url` |

#### `notice` (default)

The default rendering contract for warnings. Platforms **MUST** display
the warning content to the buyer. Platforms **MAY** render notices in a
banner, tray, or toast, and **MAY** allow the buyer to dismiss them.

#### `disclosure`

Warnings with `presentation: "disclosure"` carry notices — safety
warnings, allergen declarations, compliance content, etc. — that
**MUST** follow the prescribed rendering contract below.

**Platform requirements:**

* **MUST** display the warning `content` to the buyer.
* **MUST** display the warning in proximity to the component referenced
  by `path`, preserving the association between the disclosure and its
  subject. When `path` is omitted, the disclosure applies to the response
  as a whole.
* **MUST NOT** hide, collapse, or auto-dismiss the warning.
* **MUST** render `image_url` when present (e.g., warning symbol,
  energy class label).
* **SHOULD** render `url` as a navigable reference link when present.

Warnings with `presentation: "disclosure"` **SHOULD** be given rendering
priority over notices.

Platforms that cannot honor the disclosure rendering contract **MUST**
escalate to merchant UI via `continue_url` rather than silently
downgrading to a notice.

**Business requirements:**

* **MUST** set `presentation: "disclosure"` when the warning content must
  be displayed alongside a specific component and must not be hidden or
  auto-dismissed.
* **SHOULD** use the `path` field to associate disclosures with the
  relevant component in the response.
* **SHOULD** provide a `code` that identifies the disclosure category
  (e.g., `prop65`, `allergens`, `energy_label`). When the disclosure renders a
  structured `policies[]` entry, the `code` **MUST** equal that policy's `type`
  to link the two (see [Policies](../../overview/index.md#policies)).
* **SHOULD** provide `image_url` when the disclosure has an associated
  visual element (e.g., warning symbol, energy class label).
* **SHOULD** provide `url` when a reference link is available for the
  buyer to learn more.

#### Disclosure and Acknowledgment

The `presentation` field controls how the warning is rendered, not
whether the checkout can proceed. When affirmative buyer acknowledgment
or authorization is also required, the business **MAY** combine the
disclosure with the escalation mechanisms described in the
[Checkout Status Lifecycle](#checkout-status-lifecycle) to ensure the
appropriate buyer input is obtained.

#### Jurisdiction and Applicability

It is the business's responsibility to determine which disclosures apply
to a given session and return only those that are relevant. Businesses
**SHOULD** use buyer-provided data (`context` and other inputs) and
product attributes to resolve jurisdiction-specific requirements.
Platforms do not affect or resolve disclosure applicability — they render
what they receive from the business.

#### Example

A checkout response containing both a recoverable error and a disclosure
warning on a line item:

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { "version": "{{ ucp_version }}", "status": "success", "payment_handlers": { ... } },
  "id": "chk_abc123",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "item_456", "title": "Artisan Nut Butter Collection", "price": 1299, "image_url": "https://merchant.com/nut-butter.jpg" },
      "quantity": 1,
      "totals": [
        { "type": "subtotal", "amount": 1299 },
        { "type": "total", "amount": 1299 }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 1299 },
    { "type": "total", "amount": 1299 }
  ],
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

The platform resolves the recoverable error programmatically while
rendering the allergen disclosure in proximity to the referenced line
item.

## Continue URL

The `continue_url` field enables checkout handoff from platform to business UI,
allowing the buyer to continue and finalize the checkout session.

### Availability

Businesses **MUST** provide `continue_url` when returning `status` =
`requires_escalation`. For all other non-terminal statuses (`incomplete`,
`ready_for_complete`, `complete_in_progress`), businesses **SHOULD** provide
`continue_url`. For terminal states (`completed`, `canceled`), `continue_url`
**SHOULD** be omitted.

### Format

The `continue_url` **MUST** be an absolute HTTPS URL and **SHOULD** preserve
checkout state for seamless handoff. Businesses **MAY** implement state
preservation using either approach:

#### Server-Side State (Recommended)

An opaque URL backed by server-side checkout state:

```text
https://business.example.com/checkout-sessions/{checkout_id}
```

* Server maintains checkout state tied to `checkout_id`
* Simple, secure, recommended for most implementations
* URL lifetime typically tied to `expires_at`

#### Checkout Permalink

A stateless URL that encodes checkout state directly, allowing reconstruction
without server-side persistence. Businesses **SHOULD** implement support for
this format to facilitate checkout handoff and accelerated entry—for example, a
platform can prefill checkout state when initiating a buy-now flow.

> **Note:** Checkout permalinks are a REST-specific construct that extends the
> [REST transport binding](rest.md). Accessing a permalink returns a
> redirect to the checkout UI or renders the checkout page directly.

## Scopes

The Checkout capability defines the following well-known scopes for
user-authenticated access:

| Scope | Description |
| :--- | :--- |
| `dev.ucp.shopping.checkout:manage` | All checkout operations on behalf of the authenticated user — create, update, complete, and cancel checkout sessions. |

Scope declaration, derivation, and rules for extending this set with
custom scopes are defined in [Identity Linking — Scopes](../../common/identity-linking/index.md#scopes).

## Guidelines

(In addition to the overarching guidelines)

### Platform

* **MAY** engage an agent to facilitate the checkout session (e.g. add items
    to the checkout session, select fulfillment address). However, the
    agent must hand over the checkout session to a trusted and
    deterministic UI for the user to review the checkout details and place the
    order.
* **MAY** send the user from the trusted, deterministic UI back to the agent
    at any time. For example, when the user decides to exit the checkout screen
    to keep adding items to the cart.
* **MAY** provide agent context when the platform indicates that the request
    was done by an agent.
* **MUST** use `continue_url` when checkout status is `requires_escalation`.
* **MAY** use `continue_url` to hand off to business UI in other situations.
* When performing handoff, **SHOULD** prefer business-provided
    `continue_url` over platform-constructed checkout permalinks.

### Business

* **MUST** send a confirmation email after the checkout has been completed.
* **SHOULD** provide accurate error messages.
* Logic handling the checkout sessions **MUST** be deterministic.
* **MUST** provide `continue_url` when returning `status` =
    `requires_escalation`.
* **MUST** include at least one message with `severity` of
    `requires_buyer_input` or `requires_buyer_review` when returning
    `status` = `requires_escalation`.
* **SHOULD** provide `continue_url` in all non-terminal checkout responses.
* After a checkout session reaches the state "completed", it is considered
    immutable.

## Capability Schema Definition <span id="checkout"></span>

{{ schema_fields('checkout_resp', 'shopping/checkout') }}

## Operations

The Checkout capability defines the following logical operations.

| Operation             | Description                                                                        |
| :-------------------- | :--------------------------------------------------------------------------------- |
| **Create Checkout**   | Initiates a new checkout session. Called as soon as a user adds an item to a cart. |
| **Get Checkout**      | Retrieves the current state of a checkout session.                                 |
| **Update Checkout**   | Updates a checkout session.                                                        |
| **Complete Checkout** | Finalizes the checkout and places the order.                                       |
| **Cancel Checkout**   | Cancels a checkout session.                                                        |

### Create Checkout

To be invoked by the platform when the user has expressed purchase intent
(e.g., click on Buy) to initiate the checkout session with the item details.

**Recommendation**: To minimize discrepancies and a streamlined user experience,
product data (price/title etc.) provided by the business through the feeds
**SHOULD** match the actual attributes returned in the response.

When the [Cart](../cart/index.md) capability is negotiated, the request payload
should accept an additional `cart_id` field for cart-to-checkout conversion. See
[Cart → Cart-to-Checkout Conversion](../cart/index.md#cart-to-checkout-conversion) for
the field contract.

{{ method_fields('create_checkout', 'rest.openapi.json', 'shopping/checkout') }}

### Get Checkout

It provides the latest state of the checkout resource. After cancellation or
completion it is up to the business on what to return (i.e this can be a long
lived state or expire after a particular TTL - resulting in a 'not found'
error). From the platform there is no specific enforcement for a TTL of the
checkout.

The platform will honor the TTL provided by the business via `expires_at` at the
time of checkout session creation.

{{ method_fields('get_checkout', 'rest.openapi.json', 'shopping/checkout') }}

### Update Checkout

Performs a full replacement of the checkout resource.
The platform is **REQUIRED** to send the entire checkout resource containing any
data updates to write-only data fields. The resource provided in the request
will replace the existing checkout session state on the business side. This
general replacement rule does not apply during `complete_in_progress` because
Update Checkout is not permitted; see
[Accepted completion](#accepted-completion) for the frozen operation contract.

{{ method_fields('update_checkout', 'rest.openapi.json', 'shopping/checkout') }}

### Complete Checkout

This is the final checkout placement call. To be invoked when the user has
committed to pay and place an order for the chosen items. Complete Checkout
completes checkout and places the order from `ready_for_complete`.

The response is the checkout object:

* When completion finishes synchronously, `status` is `completed` and the
    `order` field is present, providing necessary identifiers such as `id` and
    `permalink_url` that can be used to reference the full state of the placed
    order.
* When completion is accepted for asynchronous processing, `status` is
    `complete_in_progress` and no `order` is present. The Platform follows
    [Accepted completion](#accepted-completion) for Business processing and any
    outstanding Action.
* Any other status retains its core
    [Checkout status lifecycle](#checkout-status-lifecycle) semantics — for
    example `incomplete` for a recoverable change, or `requires_escalation` for
    Buyer handoff.

The Platform **MUST NOT** use Complete Checkout to poll or resume accepted
processing. If the Platform does not receive a response to Complete Checkout, it
**SHOULD** use Get Checkout with bounded backoff to obtain the current state and
**MUST** stop at `expires_at`. Only if Get Checkout still does not establish
whether the Business processed the original request, the Platform **MAY** submit
the identical original Complete Checkout request again with the same idempotency
key. The Platform **MUST NOT** use a new idempotency key for that retry.
A genuinely new Complete Checkout operation after the Checkout returns to
`ready_for_complete`
**MUST** use a fresh idempotency key, even if the payload is unchanged.

At the time of order persistence, fields from `Checkout` **MAY** be used
to construct the order representation (i.e. information like `line_items`,
`fulfillment` will be used to create the initial order representation).

After the order is placed, other details will be updated through subsequent
events as the order, and its associated items, move through the supply chain.

{{ method_fields('complete_checkout', 'rest.openapi.json', 'shopping/checkout') }}

### Cancel Checkout

This operation will be used to cancel a checkout session, if it can be canceled.
If the checkout session cannot be canceled (e.g. checkout session is
already canceled or completed), then businesses **SHOULD** send back an error
indicating the operation is not allowed. Any checkout session with a status
that is not equal to `completed` or `canceled` **SHOULD** be cancelable.

{{ method_fields('cancel_checkout', 'rest.openapi.json', 'shopping/checkout') }}

## Transport Bindings

The abstract operations above are bound to specific transport protocols as
defined below:

* [REST Binding](rest.md): RESTful API mapping using standard HTTP verbs and JSON payloads.
* [MCP Binding](mcp.md): Model Context Protocol mapping for agentic interaction.
* [A2A Binding](a2a.md): Agent-to-Agent Protocol mapping for agentic interactions.
* [Embedded Checkout Binding](embedded.md): JSON-RPC for powering embedded checkout.

## Entities

### Buyer

{{ schema_fields('buyer', 'shopping/checkout') }}

### Context

Context signals are provisional—not authoritative data. Businesses SHOULD use
these values when verified inputs (e.g., shipping address) are absent, and MAY
ignore or down-rank them if inconsistent with higher-confidence signals
(authenticated account, risk detection) or regulatory constraints (export
controls). Eligibility and policy enforcement MUST occur at checkout time using
binding transaction data.

{{ schema_fields('context', 'shopping/checkout') }}

### Signals

Environment data provided by the platform to support authorization
and abuse prevention. Unlike `context` (buyer-asserted preferences) and `buyer`
(self-reported identity), signal values MUST NOT be buyer-asserted claims —
platforms provide signals based on direct observation or by relaying
independently verifiable third-party attestations. See
[Signals](../../overview/index.md#signals) for details and privacy
requirements.

{{ schema_fields('types/signals', 'shopping/checkout') }}

### Attribution

Platform-provided referral and conversion-event context — campaign IDs,
click identifiers, and source/medium markers communicated by the platform.
See [Attribution](../../overview/index.md#attribution) for details and consent
requirements.

{{ schema_fields('types/attribution', 'shopping/checkout') }}

### Item

#### Item Create Request

{{ schema_fields('types/item_create_req', 'shopping/checkout') }}

#### Item Update Request

{{ schema_fields('types/item_update_req', 'shopping/checkout') }}

#### Item

{{ schema_fields('types/item_resp', 'shopping/checkout') }}

### Line Item

#### Line Item Create Request

{{ schema_fields('types/line_item_create_req', 'shopping/checkout') }}

#### Line Item Update Request

{{ schema_fields('types/line_item_update_req', 'shopping/checkout') }}

#### Line Item

{{ schema_fields('types/line_item_resp', 'shopping/checkout') }}

### Link

{{ schema_fields('types/link', 'shopping/checkout') }}

#### Well-Known Link Types

Businesses **SHOULD** provide all relevant links for the transaction. The
following are the recommended well-known types:

| Type               | Description                                       |
| :----------------- | :------------------------------------------------ |
| `privacy_policy`   | Link to the business's privacy policy             |
| `terms_of_service` | Link to the business's terms of service           |
| `refund_policy`    | Link to the business's refund policy              |
| `shipping_policy`  | Link to the business's shipping policy            |
| `faq`              | Link to the business's frequently asked questions |

Businesses **MAY** define custom types for domain-specific needs. Platforms
**SHOULD** handle unknown types gracefully by displaying them using the `title`
field or omitting them.

### Policy

Policies (return/refund terms, warranty, and the like) that apply to the items
in this checkout. JSONPath targets in `applies_to` are relative to
this response root (e.g., `$.line_items[0]`). See
[Policies](../../overview/index.md#policies) for the full model.

{{ schema_fields('types/policy', 'shopping/checkout') }}

### Message

{{ schema_fields('message', 'shopping/checkout') }}

### Message Error

{{ schema_fields('types/message_error', 'shopping/checkout') }}

#### Error Code

{{ schema_fields('types/error_code', 'shopping/checkout') }}

### Message Info

{{ schema_fields('types/message_info', 'shopping/checkout') }}

### Message Warning

{{ schema_fields('types/message_warning', 'shopping/checkout') }}

### Payment

{{ schema_fields('payment', 'shopping/checkout') }}

#### Selected Payment Instrument

{{ extension_schema_fields('../common/types/payment_instrument.json#/$defs/selected_payment_instrument', 'shopping/checkout') }}

### Payment Credential

{{ schema_fields('payment_credential', 'shopping/checkout') }}

### Postal Address

{{ schema_fields('postal_address', 'shopping/checkout') }}

### Response

{{ extension_schema_fields('capability.json#/$defs/response_schema', 'shopping/checkout') }}

### Total {: #totals }

{{ schema_fields('types/total_resp', 'shopping/checkout') }}

#### Rendering Contract

Businesses are the authoritative source for presented totals — their content
and order — because the correct presentation is subject to regional, product,
and regulatory requirements that the business is obligated to satisfy (e.g.,
multi-jurisdiction tax itemization, mandatory fee disclosures).

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

Platforms MUST NOT interpret, filter, reorder, aggregate, or apply display
logic of their own.

Invariants of `totals[]`:

* Every entry carries a `type` and an `amount`. Platforms SHOULD use
  `display_text` when provided. Well-known types have default display labels
  as fallback (see table below); unknown types MUST include `display_text`.
* Amounts are signed integers — negative values are subtractive (e.g.,
  discounts), positive values are additive. The sign IS the direction.
* Exactly one `type: "subtotal"` MUST be present.
* Exactly one `type: "total"` MUST be present.

#### Verification

Platforms MUST NOT substitute their own computed totals for the business's
values. Platforms MAY verify the provided totals:

```python
assert sum(e.amount for e in totals if e.type != "total") == total_entry.amount
```

If the computed sum does not match the `type: "total"` entry, the platform
MUST NOT alter the rendered output — the business's presented totals are
authoritative for display. However, platforms MUST NOT autonomously complete
a checkout with mismatched totals. Platforms SHOULD reject the checkout or
escalate and ask for buyer review via `continue_url`.

#### Well-Known Types

| Type              | Sign | Default label    | Meaning                                   |
| ----------------- | ---- | ---------------- | ----------------------------------------- |
| `subtotal`        | +    | Subtotal         | Sum of line item prices                   |
| `discount`        | −    | Discount         | Order or line-item level discount         |
| `items_discount`  | −    | Item Discounts   | Rollup of line-item discounts             |
| `fulfillment`     | +    | Shipping         | Shipping, delivery, or pickup charges     |
| `tax`             | +    | Tax              | Tax charges                               |
| `fee`             | +    | Fee              | Fees and surcharges                       |
| `total`           | =    | Total            | Authoritative grand total (exactly one)   |

When `display_text` is provided, platforms MUST use it. When omitted on a
well-known type, platforms SHOULD use the default label above. The sign
convention for well-known types is schema-enforced: subtractive types
(discount, items_discount) MUST have negative amounts; additive types
(subtotal, fulfillment, tax, fee) MUST have non-negative amounts.

The `type` field is an open string — businesses MAY use values beyond the
well-known set. Unknown types MUST include `display_text` (schema-enforced)
and the sign on the amount is self-describing.

#### Repeating Types

All types except `subtotal` and `total` MAY appear multiple times —
for example, multi-jurisdiction tax lines or itemized fees.

#### Sub-Lines (`lines`)

Each top-level entry MAY include a `lines` array. Sub-lines share the same
base shape as top-level entries — `display_text` and `amount` — providing an
itemized breakdown under the parent.

**Invariant:** `sum(lines[].amount)` MUST equal the parent entry's `amount`.

The business controls what MUST be rendered (top-level entries) versus what
MAY be optionally surfaced (sub-lines). Platforms SHOULD render sub-lines
when provided.

#### Examples

**Split tax, itemized at top-level:**

<!-- ucp:example schema=shopping/checkout target=$.totals op=read -->
```json
[
  { "type": "subtotal",    "display_text": "Subtotal",    "amount": 5750 },
  { "type": "fulfillment", "display_text": "Shipping",    "amount": 899 },
  { "type": "tax",         "display_text": "Federal Tax", "amount": 332 },
  { "type": "tax",         "display_text": "State Tax",   "amount": 465 },
  { "type": "total",       "display_text": "Total",       "amount": 7446 }
]
```

**Collapsed fees with optional breakdown:**

<!-- ucp:example schema=shopping/checkout target=$.totals op=read -->
```json
[
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

<!-- ucp:example schema=shopping/checkout target=$.totals op=read -->
```json
[
  { "type": "subtotal",       "display_text": "Subtotal",       "amount": 10000 },
  { "type": "discount",       "display_text": "Summer Sale",    "amount": -1500 },
  { "type": "tax",            "display_text": "Tax",            "amount": 680 },
  { "type": "account_credit", "display_text": "Account Credit", "amount": -2500 },
  { "type": "total",          "display_text": "Amount Due",     "amount": 6680 }
]
```

### UCP Response Checkout {: #ucp-response-checkout-schema }

{{ extension_schema_fields('ucp.json#/$defs/response_checkout_schema', 'shopping/checkout') }}

### Order Confirmation

{{ schema_fields('order_confirmation', 'shopping/checkout') }}

### Error Response <span id="error-response"></span>

{{ schema_fields('types/error_response', 'shopping/checkout') }}
