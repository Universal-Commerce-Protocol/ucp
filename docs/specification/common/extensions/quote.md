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

<!-- cspell:ignore quotable -->

# Quote Extension

!!! note "Draft - Work in Progress"
    This extension is in **draft status**. Implementers are cautioned that data
    models, protocol bindings, and operational flows are under active iteration
    and may undergo breaking changes as the specification evolves.

* **Capability Name:** `dev.ucp.common.quote`

## Overview

The Quote extension lets a Business price the line items of a Cart or Checkout
with a **quotation** the Buyer accepts by id, and lets a Buyer ask for one — by
proposing a price ("I'll pay $150 for these three") or by asking without
proposing ("quote me 500 units"). The Business accepts, declines, defers, or
quotes; the Buyer accepts the quotation or proposes again. An accepted
quotation is reflected in the authoritative `totals` and projected onto the
resulting Order.

The extension standardizes the **contract around** a quotation — how support
is discovered, a durable quotation identity, expiry, how acceptance reaches
`totals`, and how it reaches the Order — and nothing about how a Business
decides. Whether a Business answers from a rule, a model, or a person reading
a queue is its own concern, and so are reserve prices and customer-specific
pricing. A quotation formed outside the Cart or Checkout — on the Business's
own surface, in a conversation, or through a vendor extension — enters the
same way: the Buyer names its id and the Business binds it.

This extension adds one property to Cart and Checkout:

* `quote` — the Business's current quotation (`id`, `subtotal`, `expires_at`,
  `message`), the lifecycle `status` of the open cycle, and the Buyer's
  `proposal` or `accepted_id`.

and one property to Order:

* `quote` — the quotation accepted before the Order was placed.

Prices are never set by the Platform. A Buyer's proposal is an input the
Business evaluates; the only price that applies is the one the Business
returns in `totals`.

## When a Cart or Checkout carries a quote

Quotes are optional. A Business includes `quote` on a response when it will
consider a proposal for that Cart or Checkout, or when a quote cycle is open.
An empty object (`"quote": {}`) means the resource is quotable and no cycle is
open. The absence of `quote` means no quotation is available for the resource
in its current state — because the Business does not quote these items, this
Buyer, or this quantity — and a Platform **MUST NOT** offer to propose one.

Support advertised in the profile ([Discovery](#discovery)) says a Business
implements the extension. Whether a particular Cart or Checkout is quotable is
a runtime result, communicated by the presence of `quote` on the response.

## Lifecycle

`quote.status` names the state of the open cycle and is absent when none is
open. It is an open vocabulary with the following well-known values:

| Status      | Meaning                                                     |
| :---------- | :---------------------------------------------------------- |
| `pending`   | A proposal was received; the Business has not yet answered. |
| `quoted`    | The Business issued a quotation that awaits the Buyer.      |
| `accepted`  | The quotation was accepted; `totals` reflect it.            |
| `declined`  | The Business declined the proposal.                         |
| `expired`   | The quotation lapsed before acceptance.                     |
| `withdrawn` | The Business revoked the quotation before it lapsed.        |

A Platform that receives a `status` it does not recognize **MUST** treat no
quotation as acceptable and **MUST NOT** offer to accept one. `totals` remain
authoritative in every state, so an unknown state cannot change what the
Buyer pays; it only withholds the quote interaction.

A **cycle** opens when the Buyer submits a `proposal` or accepts a quotation by
id, and closes when a new `proposal` supersedes it, the Business invalidates
the quotation ([Scope and expiry](#scope-and-expiry)), the resource returns to
idle (`"quote": {}`), or the Checkout completes. The Business echoes the
`proposal` and `accepted_id` of the current cycle on every response while it
is open, so a Platform can show the Buyer what was asked next to what was
answered.

Transitions are driven by the Buyer's update, the Business's answer, the line
items, or the clock:

| From                                        | Trigger                                                 | To                                                                   | Side effects                                                         | Messages                                         |
| :------------------------------------------ | :------------------------------------------------------ | :------------------------------------------------------------------- | :------------------------------------------------------------------- | :----------------------------------------------- |
| idle · `declined` · `expired` · `withdrawn` | Buyer sends `proposal`                                  | `pending` · `quoted` (new `id`) · `accepted` (new `id`) · `declined` | proposal echoed; a prior quotation's `id` is dropped                 | —                                                |
| `quoted`                                    | Buyer sends `proposal`                                  | as above                                                             | the unaccepted quotation is superseded                               | — (the Buyer asked for it)                       |
| `pending`                                   | Buyer sends `proposal`                                  | `pending`                                                            | replaces the pending proposal                                        | —                                                |
| `accepted`                                  | Buyer sends `proposal`                                  | `pending` · `quoted` (new `id`) · `accepted` (new `id`) · `declined` | the accepted quotation is invalidated; its `totals` entry removed    | `quote_changed`                                  |
| any                                         | Buyer sends a `proposal` the Business will not consider | unchanged                                                            | —                                                                    | `quote_unavailable` error                        |
| `pending`                                   | Business answers                                        | `quoted` · `accepted` · `declined`                                   | —                                                                    | —                                                |
| any                                         | Buyer sends an `accepted_id` that resolves              | `accepted`                                                           | `totals` entry added; derived state recomputed; `accepted_id` echoed | —                                                |
| any                                         | Buyer sends an `accepted_id` that does not resolve      | unchanged                                                            | —                                                                    | `quote_changed`                                  |
| `accepted`                                  | Buyer repeats the current `accepted_id`                 | unchanged (no-op)                                                    | —                                                                    | —                                                |
| `quoted` · `accepted`                       | Business withdraws                                      | `withdrawn` (`id` kept)                                              | `totals` entry removed if it had been accepted                       | `quote_changed`                                  |
| `quoted`                                    | `expires_at` passes                                     | `expired` (`id` kept)                                                | —                                                                    | `quote_changed` if the Buyer attempted to accept |
| `quoted` · `accepted`                       | line items or `currency` change                         | `quoted` (new `id`) · `accepted` (new `id`) · idle · `quote` omitted | `totals` entry removed if it had been accepted                       | `quote_changed`                                  |
| `pending`                                   | line items or `currency` change                         | idle, or `pending` if the Business will answer for the new lines     | proposal cleared, or kept                                            | `quote_changed`                                  |
| `declined` · `expired` · `withdrawn`        | line items or `currency` change                         | idle · `quote` omitted                                               | —                                                                    | —                                                |
| any open cycle                              | Checkout completes                                      | cycle closed                                                         | Order carries `quote` only if the status was `accepted`              | —                                                |

## Proposing a price

A Platform opens a cycle by writing `quote.proposal` on Create or Update Cart,
or Create or Update Checkout. The proposal carries what the Buyer is asking
for, not an instruction:

* `subtotal` — the subtotal the Buyer proposes for the current line items,
  before fulfillment, tax, and fees.
* `message` — context for the Business. A Business **MUST NOT** require it,
  and **MUST NOT** require personal data in it; who the Buyer is travels
  through `buyer` and [Identity Linking](../identity-linking/index.md). A
  Platform **MUST NOT** place personal data in it beyond what the Buyer chose
  to say.

An empty `proposal` (`{}`) asks the Business to quote without proposing a
price.

Submitting `proposal` **replaces** any earlier proposal and supersedes a
quotation that has not been accepted. An update **MUST** carry at most one of
`proposal` and `accepted_id`; a Business receiving both **MUST** leave `quote`
unchanged and report a `quote_unavailable` error rather than guess which the
Buyer meant.

A Business that will not consider a proposal — because `quote` was absent, or
the Buyer has exhausted whatever allowance the Business sets — **MUST** respond
with a `quote_unavailable` error in `messages[]` and leave `quote` as it was.
Declining is a decision about the price; `quote_unavailable` says there was
nothing to decide. A Business is never obliged to quote, and this is the
sanctioned answer to repeated probing.

This draft defines no way to cancel a pending proposal: a Buyer who no longer
wants an answer proposes again, accepts a quotation it holds, or lets the
resource expire. A Business that queues proposals for a person treats a
replacing proposal as replacing the queued one, not as a second request.

## Answering a proposal

The Business answers in the response to the operation that carried the
proposal, or — when it needs time — later. Its options are:

* **Accept.** The Business applies the proposal: `status` becomes `accepted`,
  the quotation (`id`, `subtotal`, `expires_at`) records what was accepted,
  and `totals` reflect it ([Reflecting an accepted quotation](#reflecting-an-accepted-quotation)).
* **Quote.** The Business issues its own terms: `status` becomes `quoted`, with
  a new `id`, the `subtotal` it will honor, and an `expires_at`. A Business
  **MAY** quote in answer to a proposed price or to an empty proposal alike.
* **Decline.** `status` becomes `declined`. The Business **SHOULD** say why in
  `message`; it is never required to explain its pricing.
* **Defer.** `status` becomes `pending` ([Asynchronous review](#asynchronous-review)).

A quotation is immutable. Its `id` identifies exactly one `subtotal` for one
set of line items; a Business that wants to quote different terms **MUST**
issue a new quotation with a new `id`. The one field that may move is
`expires_at`, which the Business **MAY** extend in place and **MUST NOT**
shorten. A Platform can therefore rely on `id` to tell "the same quotation"
from "a different one" without comparing fields. Quotation ids are unique
within the Business, so an id read on a Cart, a Checkout, or an Order, or
received outside UCP, names the same quotation everywhere.

## Accepting a quotation

Accepting a quotation is a **mutation**. A Platform sets `accepted_id` on
Create or Update to either:

* the `id` from the latest response, whose `status` is `quoted`; or
* the `id` of a quotation this Business issued to this Buyer outside the Cart
  or Checkout — on its own storefront, in a conversation, or through a vendor
  extension — for the same line items.

The Business returns the recomputed Cart or Checkout. That response is
**authoritative for all derived state** — `totals`, line item prices, discount
eligibility, `policies[]`, `messages[]`, and, on a Checkout, the payment
handlers and payment terms offered. A Platform **MUST** re-render from the
response rather than reuse the amounts read from `quote` before acceptance. A
quotation is a statement of what the Business will honor for the line items;
fulfillment, tax, and fees are computed by the Business as for any other Cart
or Checkout.

A Business receiving an `accepted_id` that does not resolve — because the
quotation expired, was superseded, was invalidated by a change to the line
items, or was never issued to this Buyer for these items — **MUST NOT**
silently substitute another quotation, and **MUST** return the current state
with a `quote_changed` warning in `messages[]`. An update that repeats the
`accepted_id` of the current accepted quotation is a no-op. An update that
carries `accepted_id` together with a change to the line items is evaluated
against the changed line items, so the quotation does not resolve and the
Business reports `quote_changed`; a Platform that wants both applies the line
item change first.

A Platform **MUST** omit `accepted_id` on complete: a quotation is agreed, if
at all, before completion, and a Complete request carries no quote input.

## Reflecting an accepted quotation

When `status` is `accepted`, the Business **MUST** make `totals` state the
agreed price with exactly one entry of `type: "quote"`, whose `amount` is the
quotation `subtotal` minus the sum of the line item subtotals — negative where
the quotation is lower than the listed prices, positive where it is higher.
This extension defines the `totals[].type` value `quote`; because it is not
among the core well-known types, `display_text` is required on that entry, and
the Business **MUST** set it so the Buyer can see what the quotation
contributed.

Line items keep their listed `item.price` and `totals`; the quotation's effect
appears exactly once, at the Cart or Checkout level. The entry is present if
and only if `status` is `accepted`, so a Platform identifies it by `type`
alone and can check that the line item subtotals plus the `quote` entry equal
`quote.subtotal`. The Cart or Checkout `total` is the amount the Buyer pays.

The entry is not a discount: it is not allocated to line items, does not
contribute to `items_discount`, and does not appear in `discounts.applied`, so
the [Discount](../../shopping/extensions/discount.md) extension's invariants
over `line_items[].totals` and `discounts.applied` are unaffected when both
extensions are active.

The Business **MUST NOT** apply an accepted quotation to any line items other
than those it was issued against.

## Scope and expiry

A quotation is bound to the line items it was issued against — each
`line_items[].id` with its `item.id`, `quantity`, and `quantity_unit` — and to
the Cart or Checkout `currency`. When an update changes any of these, the
quotation no longer applies. The Business **MUST** then do one of:

* issue a new quotation for the current line items — a new `id` with `status`
  `quoted`, or `accepted` if it chooses to honor equivalent terms outright; or
* return `"quote": {}`, inviting a new proposal; or
* omit `quote`, if it will not quote the changed Cart or Checkout.

In every case it **MUST** report a `quote_changed` warning in `messages[]`, and
where the quotation had been accepted, **MUST** remove the `quote` entry from
`totals`. A Platform **MUST** surface that warning: the Buyer expected a price
and the price changed.

A quotation lapses at `expires_at`. A Business **MUST** report a lapsed
quotation as `status: "expired"` on the next response, with a `quote_changed`
warning if the Buyer had attempted to accept it. After acceptance, `expires_at`
records the validity the Buyer accepted under; an accepted quotation does not
lapse, and a Business that honors it through completion need not do anything
further.

A Business that revokes a `quoted` or `accepted` quotation before `expires_at`
— because it will no longer honor the price — **MUST** set
`status: "withdrawn"`, keep the quotation's `id` and `subtotal` so the Buyer
can see which quotation was revoked, remove the `quote` entry from `totals`,
and report a `quote_changed` warning in `messages[]`. It **SHOULD** say why in
`message`. Withdrawal is a Business decision taken before the clock runs out; a
quotation that reaches `expires_at` is `expired`, never `withdrawn`. The Buyer
may propose again.

`quote_changed` reports a change the Buyer did not ask for. A Buyer's own
`proposal` superseding an unaccepted quotation is not reported.

## Asynchronous review

A Business that routes a proposal to a person answers `status: "pending"`.
Nothing about the Cart or Checkout is otherwise changed. A Business **SHOULD**
set `message` to tell the Buyer what to expect, and **SHOULD** set the Cart or
Checkout `expires_at` to cover its review window, so the resource is still
there when the answer is.

A Platform **MAY** re-read the resource with Get Cart or Get Checkout, with
bounded backoff, to learn the outcome, and **MUST** stop repeated requests at
the resource's `expires_at`. It **SHOULD** also surface `continue_url` where
the Business provides one, so the Buyer can return to the Business's own
surface when notified. A Business **MUST NOT** require the Platform to remain
in session, and **MUST NOT** treat a Platform's silence as acceptance.

The answer to a pending proposal is reported exactly as a synchronous one would
be: `quoted`, `accepted`, or `declined`, on the next response.

## Checkout status and completion

A quote cycle does not change `checkout.status`. A Checkout **MAY** reach
`ready_for_complete` and be completed while `quote.status` is anything other
than `accepted`: the Buyer pays `totals` as they stand, completing closes the
open cycle, and the Order carries `quote` only when a quotation was accepted.
A Business whose policy forbids sale at list price while a proposal is
`pending` uses the core
[status lifecycle](../../shopping/checkout/index.md#checkout-status-lifecycle)
for that — it keeps the Checkout `incomplete` with a message whose `path` is
`$.quote`, or escalates with `requires_escalation` and `continue_url` when the
Buyer must finish on its own surface — and **MUST NOT** hold a Checkout
silently.

A Business **MUST NOT** complete a Checkout whose `totals` do not honor an
accepted quotation it has not withdrawn under
[Scope and expiry](#scope-and-expiry). Leaving `accepted` on a Checkout changes
`totals`, so it also carries whatever another active extension requires of a
totals change: a selected
[payment term](../../payment/extensions/terms.md#selecting-a-payment-term)
is re-summed and reported with `payment_term_changed`, and a Checkout whose
state was signed under
[AP2 mandates](../../payment/extensions/ap2-mandates.md#business-verification)
no longer matches that signature and must be authorized again before
completion. Accepting a quotation on a Checkout with a selected payment term
has the same consequences, in the other direction.

A Business **MAY** advertise, in `ucp.request_constraints`, that the only
acceptance it will honor on the next request is the current quotation, so a
Platform can preflight a stale `accepted_id`
([Request Constraints](../../overview/index.md#request-constraints)). A
Business cannot forbid a further proposal through constraints; it declines to
consider one with `quote_unavailable`.

## Cart to Checkout and Order

When a Checkout is created from a Cart via `cart_id`, the Business **MUST**
carry the Cart's `quote` state forward. An accepted quotation remains accepted
with the same `id`; a `pending` or `quoted` cycle continues with the same
identifiers. A `quote` sent on a Create Checkout that names `cart_id` is an
overlapping field and is ignored, as the
[Cart capability](../../shopping/cart/index.md#cart-to-checkout-conversion)
requires; the Platform proposes or accepts on the Checkout with an Update.
While a Cart and its Checkout are linked, the Checkout's `quote` is
authoritative, and the Business **SHOULD** reflect it back to the Cart as it
does other checkout modifications. The same extension applies to a Checkout
created directly.

On the Order, `quote` carries the accepted quotation — `id` and `subtotal`.
Businesses **MUST** carry it forward. The proposal and the lifecycle state are
checkout history and are not projected.

## Out of scope

**How the Business decides.** Reserve prices, margins, customer-specific
pricing, volume tiers, and whether a person or a rule answers are the
Business's own. The extension carries the question and the answer, not the
reasoning.

**Terms other than price.** A quotation prices the current line items. It does
not negotiate fulfillment, delivery dates, payment timing, or warranty.
[Payment Terms](../../payment/extensions/terms.md) and
[Fulfillment](../../shopping/extensions/fulfillment.md) continue to govern
those, and compose with an accepted quotation.

**Quotations that change the Cart.** A Business answer of the form "not at that
price, but take two and I will" proposes different line items. That is a
different Cart state, not a quotation on this one, and is left to mechanisms
that propose Cart transitions.

**Per-line prices, explicit Buyer decline, and cancellation of a pending
proposal.** Deferred until implementations show they are needed; a Business
that states per-line prices today does so in `message`.

**Auctions and multi-party mechanisms.** One Buyer, one Business, one Cart or
Checkout. Bidding, ranking, and supplier selection are outside UCP.

**Buyer identity and account data.** A business that requires a verified
account, a tax identifier, or a signed agreement before quoting obtains them
through [Identity Linking](../identity-linking/index.md) and its own
onboarding, not through `proposal.message`.

## Discovery

Businesses advertise quote support in their profile. The capability extends
Cart, Checkout, and Order:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.quote": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/extensions/quote",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/quote.json"
        }
      ]
    }
  }
}
```

A Business **MAY** extend Checkout only, or Cart and Checkout together. A
Business that extends Cart **MUST** also extend Checkout when it supports
creating a Checkout from a Cart via `cart_id`, so quote state can carry
forward. It **SHOULD** extend Order whenever it extends Checkout, so the
accepted quotation survives the purchase. Platforms **SHOULD** check which
resources are extended before proposing.

## Schema

### Quote

When this capability is active, Cart and Checkout carry `quote`.

{{ extension_schema_fields('quote.json#/$defs/quote', 'common/extensions/quote') }}

### Quote Proposal

{{ extension_schema_fields('quote.json#/$defs/quote_proposal', 'common/extensions/quote') }}

### Order Quote

On the Order, `quote` carries the accepted quotation only.

{{ extension_schema_fields('quote.json#/$defs/order_quote', 'common/extensions/quote') }}

## Examples

### A quotable Cart with no open cycle

<!-- ucp:example schema=common/quote def=quote op=read direction=response -->
```json
{}
```

The Business will consider a proposal; nothing has been asked.

### A proposal the Business accepts

> Three bookends listed at $56.56 each. The Buyer proposes $150 for the three;
> the Business's rules accept it.

**Update request — the Buyer proposes a subtotal:**

<!-- ucp:example schema=common/quote def=quote op=update direction=request -->
```json
{
  "proposal": {
    "subtotal": 15000
  }
}
```

**Cart response — accepted and reflected in totals:**

<!-- ucp:example schema=common/quote def=dev.ucp.shopping.cart op=update direction=response -->
```json
{
  "ucp": { ... },
  "id": "cart_8f1",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_bookends",
      "item": {
        "id": "sku_20003556",
        "title": "Iron Bridge Bookends",
        "price": 5656
      },
      "quantity": 3,
      "totals": [
        { "type": "subtotal", "amount": 16968 },
        { "type": "total", "amount": 16968 }
      ]
    }
  ],
  "quote": {
    "status": "accepted",
    "id": "qt_7f3a",
    "subtotal": 15000,
    "expires_at": "2026-10-10T23:30:00Z",
    "proposal": {
      "subtotal": 15000
    }
  },
  "totals": [
    { "type": "subtotal", "display_text": "Subtotal", "amount": 16968 },
    { "type": "quote", "display_text": "Quoted price", "amount": -1968 },
    { "type": "total", "display_text": "Estimated Total", "amount": 15000 }
  ]
}
```

The line items keep their listed prices; the $19.68 the quotation saved is
stated once, as the `quote` entry, where the purchase is priced. No
`accepted_id` is echoed: the Business accepted the proposal outright.

### A proposal the Business answers with its own quotation

> Same Cart. The Business will not take $150, and quotes $159 instead, good
> for ninety minutes.

**Cart response — quoted:**

<!-- ucp:example schema=common/quote def=dev.ucp.shopping.cart op=update direction=response -->
```json
{
  "ucp": { ... },
  "id": "cart_8f1",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_bookends",
      "item": {
        "id": "sku_20003556",
        "title": "Iron Bridge Bookends",
        "price": 5656
      },
      "quantity": 3,
      "totals": [
        { "type": "subtotal", "amount": 16968 },
        { "type": "total", "amount": 16968 }
      ]
    }
  ],
  "quote": {
    "status": "quoted",
    "id": "qt_8c21",
    "subtotal": 15900,
    "expires_at": "2026-10-10T23:30:00Z",
    "message": "We can do $159 for the set if you order today.",
    "proposal": {
      "subtotal": 15000
    }
  },
  "totals": [
    { "type": "subtotal", "display_text": "Subtotal", "amount": 16968 },
    { "type": "total", "display_text": "Estimated Total", "amount": 16968 }
  ]
}
```

Nothing has been agreed, so `totals` are unchanged. The Buyer may accept or
propose again.

**Update request — the Buyer accepts the quotation:**

<!-- ucp:example schema=common/quote def=quote op=update direction=request -->
```json
{
  "accepted_id": "qt_8c21"
}
```

**Cart response — accepted:**

<!-- ucp:example schema=common/quote def=quote op=update direction=response -->
```json
{
  "status": "accepted",
  "id": "qt_8c21",
  "subtotal": 15900,
  "expires_at": "2026-10-10T23:30:00Z",
  "message": "We can do $159 for the set if you order today.",
  "accepted_id": "qt_8c21",
  "proposal": {
    "subtotal": 15000
  }
}
```

`totals` now carry a `quote` entry of -1068 and a `total` of 15900, exactly as
in the first example.

### A proposal the Business declines

<!-- ucp:example schema=common/quote def=quote op=update direction=response -->
```json
{
  "status": "declined",
  "message": "This item is already at its lowest price.",
  "proposal": {
    "subtotal": 12000
  }
}
```

No quotation was issued, so there is no `id`. The Buyer may propose again.

### A quotation the Business withdraws

> The Business issued `qt_8c21` for the bookends, then its cost on the set
> changed. It revokes the quotation before it lapses.

**Get Cart response — withdrawn:**

<!-- ucp:example schema=common/quote def=quote op=read direction=response -->
```json
{
  "status": "withdrawn",
  "id": "qt_8c21",
  "subtotal": 15900,
  "expires_at": "2026-10-10T23:30:00Z",
  "message": "We can no longer offer $159 for the set.",
  "proposal": {
    "subtotal": 15000
  }
}
```

The quotation keeps its `id` and `subtotal` so the Buyer can see what was
revoked. The response carries a `quote_changed` warning, and any `quote` entry
in `totals` is gone. The Buyer may propose again.

### A request for quotation reviewed by a person

> A buyer agent for a facilities team wants 500 pairs of safety glasses and
> 200 boxes of gloves, and proposes a subtotal. The Business's account team
> answers within a day.

**Update request — a proposal with context:**

<!-- ucp:example schema=common/quote def=quote op=update direction=request -->
```json
{
  "proposal": {
    "subtotal": 940000,
    "message": "Recurring quarterly order for three sites."
  }
}
```

**Cart response — pending:**

<!-- ucp:example schema=common/quote def=dev.ucp.shopping.cart op=update direction=response -->
```json
{
  "ucp": { ... },
  "id": "cart_b2b_41",
  "currency": "USD",
  "expires_at": "2026-10-24T00:00:00Z",
  "line_items": [
    {
      "id": "li_glasses",
      "item": { "id": "sku_sg_clear", "title": "Safety glasses, clear", "price": 1200 },
      "quantity": 500,
      "totals": [
        { "type": "subtotal", "amount": 600000 },
        { "type": "total", "amount": 600000 }
      ]
    },
    {
      "id": "li_gloves",
      "item": { "id": "sku_ng_m_100", "title": "Nitrile gloves, box of 100", "price": 2500 },
      "quantity": 200,
      "totals": [
        { "type": "subtotal", "amount": 500000 },
        { "type": "total", "amount": 500000 }
      ]
    }
  ],
  "quote": {
    "status": "pending",
    "message": "Our account team reviews volume requests within one business day.",
    "proposal": {
      "subtotal": 940000,
      "message": "Recurring quarterly order for three sites."
    }
  },
  "continue_url": "https://supply.example.com/carts/b2b_41",
  "totals": [
    { "type": "subtotal", "display_text": "Subtotal", "amount": 1100000 },
    { "type": "total", "display_text": "Estimated Total", "amount": 1100000 }
  ]
}
```

The Business extended the Cart's `expires_at` to outlast its review. The
Platform may re-read the Cart until then, or the Buyer may return through
`continue_url`.

**Get Cart response, the next day — quoted:**

<!-- ucp:example schema=common/quote def=quote op=read direction=response -->
```json
{
  "status": "quoted",
  "id": "qt_b2b_41_1",
  "subtotal": 985000,
  "expires_at": "2026-10-18T00:00:00Z",
  "message": "Volume pricing: glasses at $10.50, gloves at $23.00 a box. Valid for 7 days.",
  "proposal": {
    "subtotal": 940000,
    "message": "Recurring quarterly order for three sites."
  }
}
```

### A quotation formed outside the Cart

> The Buyer negotiated quotation `qt_sw_1042` with the Business's sales team
> for the same two line items. The agent creates a Checkout and names it.

**Create Checkout request — `quote` fragment:**

<!-- ucp:example schema=common/quote def=quote op=create direction=request -->
```json
{
  "accepted_id": "qt_sw_1042"
}
```

The Business resolves the id, checks that the Checkout's line items are the
ones it quoted, and answers `accepted` with the `quote` entry in `totals` — or,
if the id does not resolve for these items, the current state with a
`quote_changed` warning.

### Pinning acceptance for the next request

> The Business has quoted `qt_8c21` and wants a Platform to preflight a stale
> acceptance before submitting it.

<!-- ucp:example schema=common/quote def=dev.ucp.shopping.checkout op=update direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "success",
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {"version": "{{ ucp_version }}"}
      ],
      "dev.ucp.common.quote": [
        {"version": "{{ ucp_version }}"}
      ]
    },
    "payment_handlers": {},
    "request_constraints": {
      "properties": {
        "quote": {
          "properties": {
            "accepted_id": {"const": "qt_8c21"}
          }
        }
      }
    }
  },
  "id": "checkout_8f1",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_bookends",
      "item": {
        "id": "sku_20003556",
        "title": "Iron Bridge Bookends",
        "price": 5656
      },
      "quantity": 3,
      "totals": [
        { "type": "subtotal", "amount": 16968 },
        { "type": "total", "amount": 16968 }
      ]
    }
  ],
  "quote": {
    "status": "quoted",
    "id": "qt_8c21",
    "subtotal": 15900,
    "expires_at": "2026-10-10T23:30:00Z"
  },
  "totals": [
    { "type": "subtotal", "display_text": "Subtotal", "amount": 16968 },
    { "type": "total", "display_text": "Estimated Total", "amount": 16968 }
  ],
  "links": [
    {
      "type": "terms_of_service",
      "url": "https://business.example/terms"
    }
  ]
}
```

The next Update request is valid only if any `quote.accepted_id` it carries is
`qt_8c21`. A new `proposal` remains possible; the Business answers it on its
merits or with `quote_unavailable`.

### The accepted quotation on the Order

> The facilities team accepted `qt_b2b_41_1` and completed checkout.

<!-- ucp:example schema=common/quote def=dev.ucp.shopping.order op=read direction=response -->
```json
{
  "ucp": { ... },
  "id": "order_3d9",
  "checkout_id": "chk_b2b_41",
  "permalink_url": "https://supply.example.com/orders/3d9",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_glasses",
      "item": { "id": "sku_sg_clear", "title": "Safety glasses, clear", "price": 1200 },
      "quantity": { "original": 500, "total": 500, "fulfilled": 0 },
      "totals": [
        { "type": "subtotal", "amount": 600000 },
        { "type": "total", "amount": 600000 }
      ],
      "status": "processing"
    },
    {
      "id": "li_gloves",
      "item": { "id": "sku_ng_m_100", "title": "Nitrile gloves, box of 100", "price": 2500 },
      "quantity": { "original": 200, "total": 200, "fulfilled": 0 },
      "totals": [
        { "type": "subtotal", "amount": 500000 },
        { "type": "total", "amount": 500000 }
      ],
      "status": "processing"
    }
  ],
  "fulfillment": {},
  "quote": {
    "id": "qt_b2b_41_1",
    "subtotal": 985000
  },
  "totals": [
    { "type": "subtotal", "display_text": "Subtotal", "amount": 1100000 },
    { "type": "quote", "display_text": "Quoted price", "amount": -115000 },
    { "type": "total", "display_text": "Total", "amount": 985000 }
  ]
}
```

The proposal and the lifecycle are gone; what the Buyer agreed to is kept, and
the `quote` entry still accounts for it: 1,100,000 − 115,000 = 985,000.

### Messages

A quotation invalidated by a quantity change:

<!-- ucp:example schema=shopping/cart target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "quote_changed",
    "path": "$.quote",
    "content": "Your quoted price applied to 3 bookends. Ask for a new quote for 5."
  }
]
```

A proposal the Business will not consider:

<!-- ucp:example schema=shopping/cart target=$.messages -->
```json
[
  {
    "type": "error",
    "code": "quote_unavailable",
    "severity": "recoverable",
    "path": "$.quote.proposal",
    "content": "Quotes are not available for this cart."
  }
]
```

**Message codes defined by this extension:**

| Code                | Type    | Meaning                                                                                                                            |
| :------------------ | :------ | :--------------------------------------------------------------------------------------------------------------------------------- |
| `quote_changed`     | warning | The quotation in effect changed without the Buyer asking: expired, withdrawn, or invalidated, or an `accepted_id` did not resolve. |
| `quote_unavailable` | error   | The proposal was not considered: the resource is not quotable, the Buyer's allowance is exhausted, or the update was malformed.    |

## What a Platform may show in each state

| `quote.status`                       | Platform **MAY**                                                                    | Platform **MUST NOT**                           |
| :----------------------------------- | :---------------------------------------------------------------------------------- | :---------------------------------------------- |
| absent (`"quote": {}`)               | Offer to propose, or to accept a quotation the Buyer holds.                         | Show any price other than `totals`.             |
| `pending`                            | Re-read with bounded backoff until `expires_at`; show `message` and `continue_url`. | Treat silence as an answer.                     |
| `quoted`                             | Show `quote.subtotal` as the Business's quotation beside `totals`; offer to accept. | Present `quote.subtotal` as the amount payable. |
| `accepted`                           | Show the `quote` entry as the agreed saving or premium.                             | Reuse amounts read before acceptance.           |
| `declined` · `expired` · `withdrawn` | Show `message`; offer a new proposal.                                               | Present the lapsed quotation as acceptable.     |
| unrecognized                         | Render `totals`.                                                                    | Offer to accept.                                |

## Platform responsibilities

Platforms **MUST**:

* Offer to propose only when the latest response carries `quote`.
* Send at most one of `proposal` and `accepted_id` per update, and omit
  `accepted_id` on complete.
* Re-render from the Business response after acceptance rather than reusing
  amounts read from `quote`.
* Surface every `quote_changed` warning.
* Treat an unrecognized `status` as "no acceptable quotation".

Platforms **SHOULD**:

* Show the Buyer the echoed `proposal` next to the Business's answer, with
  `quote.message`.
* Re-read a `pending` resource with bounded backoff, stopping at `expires_at`,
  and surface `continue_url` where provided, rather than hold a session open.

Platforms **MUST NOT**:

* Infer a price from a proposal, or from a declined, expired, or withdrawn
  quotation. The price is what `totals` say.
* Place personal data in `proposal.message` beyond what the Buyer chose to say.

## Business responsibilities

Businesses **MUST**:

* Echo the current cycle's `proposal` and `accepted_id` on every response while
  the cycle is open.
* Give every quotation an `id` that is unique within the Business, a
  `subtotal`, and — when `status` is `quoted` — an `expires_at`; issue a new
  `id` for different terms rather than rewriting a quotation in place.
* Reflect an accepted quotation in `totals` as exactly one `quote` entry with
  `display_text`, and remove that entry if the quotation is later invalidated.
* Bind a quotation to the line items and currency it was issued against, and
  report a `quote_changed` warning whenever the quotation in effect changes
  without the Buyer asking.
* Report `quote_unavailable` rather than silently ignoring a proposal that will
  not be considered.
* Carry `quote` state from Cart to Checkout, honor an accepted quotation
  through completion or withdraw it first (`status: "withdrawn"` with
  `quote_changed`), and carry the accepted quotation onto the Order as
  `quote`.

Businesses **SHOULD**:

* Set `message` when declining, deferring, or withdrawing, so the Buyer knows
  where they stand.
* Set the Cart or Checkout `expires_at` to cover a `pending` review window.

Businesses **MUST NOT**:

* Require personal data in `proposal.message`, treat a Platform's silence as
  acceptance of a quotation, or hold a Checkout silently while a proposal is
  `pending`.
