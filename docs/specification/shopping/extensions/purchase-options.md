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

# Purchase Options Extension

## Overview

A product can be sold in several ways: once, as a subscription, on pre-order.
The Purchase Options extension lets a Business advertise those ways on a
variant, lets a Platform select one by opaque identifier, and preserves the
selected option on the resulting Order.

Today a variant has one price and one way to buy it. A Business that also
sells the same coffee on a monthly plan has no way to say so in its catalog, a
Platform has no way to choose, and a checkout has no way to know which was
chosen. The result is a late failure — an item that cannot be added without a
selection the Platform never learned about — and an incomplete comparison, where
the Business's best offer is invisible while the buyer is deciding.

A **purchase option** is an addressable, renderable choice: an `id`, a `title`,
a `price` for the current purchase and, where that price is a saving, the
`list_price` it saves against. An option that results in recurring orders also
carries their `schedules`. The Business enumerates the options it sells; the
Platform selects one. This is `options[]` plus a selected id, the same shape as
a [fulfillment option](fulfillment.md) and a
[payment term](../../payment/extensions/terms.md), applied on the axis where
the choice to subscribe actually lives: the item. As with payment terms, the
schedules of unselected options are indicative and the selected option's bind.

This extension adds:

- `purchase_options[]` on a catalog variant and on a cart or checkout line —
    the ways the variant can be bought. Response-only.
- `selected_purchase_option_id` on a cart or checkout line — the selected
    option. Present in a response whenever `purchase_options` is; a Platform
    writes it to change the selection.
- `purchase_option` on an Order line — the frozen record of the option the
    line was bought through, with the schedules agreed to.
- The `dev.ucp.shopping.policy.subscription` policy type, which governs every
    line whose selected option results in recurring orders and carries the
    disclosure the buyer must see before agreeing to them.

**Dependencies:**

- One or more of the parent capabilities this extension extends: Catalog
  Search, Catalog Lookup, Cart, Checkout, or Order.
- The core `policies[]` primitive (see
  [Policies](../../overview/index.md#policies)), on which this extension
  defines the [subscription policy](#subscription-policy) type.

An option states how the line it is selected on is bought — its price now and
the recurring orders that follow. It never adds, removes, or changes other
lines. When payment is due and how the item is fulfilled are stated by the
capabilities that own those concerns.

## Discovery

Businesses advertise purchase options in their profile:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.purchase_options": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup",
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/purchase-options",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/purchase_options.json"
        }
      ]
    }
  }
}
```

Advertising this extension means the Business returns `purchase_options` for
variants that offer them, accepts and echoes `selected_purchase_option_id` on
cart and checkout lines, and preserves the selected option on the resulting
Order line.

## Schema

### Purchase Option

{{ schema_fields('types/purchase_option', 'shopping/extensions/purchase-options') }}

### Variant Purchase Options

{{ extension_schema_fields('purchase_options.json#/$defs/variant_purchase_options', 'shopping/extensions/purchase-options') }}

### Line Item with Purchase Options

{{ extension_schema_fields('purchase_options.json#/$defs/line_item', 'shopping/extensions/purchase-options') }}

### Order Purchase Option

{{ extension_schema_fields('purchase_options.json#/$defs/order_purchase_option', 'shopping/extensions/purchase-options') }}

### Subscription Schedule

{{ schema_fields('types/subscription_schedule', 'shopping/extensions/purchase-options') }}

### Subscription Policy

{{ extension_schema_fields('purchase_options.json#/$defs/subscription_policy', 'shopping/extensions/purchase-options') }}

## Offering options

### Presence and the default

Purchase options are optional. A Business offers them when a variant can be
bought in more than one way, or in exactly one way that is not an ordinary
one-time purchase. Where a variant is bought the ordinary way at its `price`,
`purchase_options` is omitted entirely, and nothing about the variant changes.

Where `purchase_options` is present it **MUST** contain at least one option,
and exactly one of them is in effect. On a cart or checkout line,
`selected_purchase_option_id` **MUST** name it. In a catalog, the first entry is
the **default**: the option the Business selects when a Platform adds the
variant without choosing one, and the option whose `price` the variant's own
`price` states. A Business orders `purchase_options` by its preference, default
first.

A one-time purchase is an option like any other. A variant that can be bought
once or on a plan lists both; a variant whose list contains no one-time option
is sold only through the options listed. There is no implicit one-time purchase
alongside a list of options, and no separate signal is needed to say so — a
Platform reads presence exactly as it reads `payment.terms`.

A Business offering exactly one option is disclosing rather than asking, and a
Platform **SHOULD** present it without implying a choice. A variant sold only
as a subscription is one such case: a single option with `schedules`.

### Price

`purchase_options[].price` answers one question: what does one unit cost in
this purchase under this option? It reflects any discount or fixed pricing the
option defines and is stated before quantity, taxes, discounts, fees, and
fulfillment. Every option's `price` is directly comparable with every other's,
and with the variant's `price`, because all of them answer the same question.

The same rule holds across arrangements:

- A $10 item whose payment is collected in 14 days has a `price` of $10. When
  the $10 is collected is a [payment term](../../payment/extensions/terms.md).
- A subscription whose first order costs $8.50 has a `price` of $8.50. The
  recurring orders are stated in its `schedules`.
- A free trial has the first order's full `price`. Selecting it is what makes
  the Business defer that order's payment to the end of the trial under a
  payment term, and state the recurring orders in a subscription policy.
- `0` means the current purchase is genuinely free. It never means a non-zero
  amount is merely collected later.

On a cart or checkout line, the selected option's price is the line's
`item.price`, and the line's `totals` and the checkout `totals` follow from it.
Unselected options are indicative, priced by the Business for this cart or
checkout as best it can; only the selected option is reflected in the totals.
The option is the pricing mechanism: a "subscribe & save" option's saving is
its lower `price`. Where that price is a saving against a reference, the
option carries `list_price` — for a subscribe-and-save option, the one-time
price — mirroring `variant.list_price` for strikethrough display and a
derivable saving. The
catalog states a price and a reference price, never a breakdown; breakdowns
begin at the line. Whether a Business then itemizes the saving as a discount
entry in a line's `totals` is its choice, applied consistently to today's
order and to the option's `schedules`.

## Recurring orders

An option that results in recurring orders carries `schedules`: one or more
consecutive runs of recurring orders, each with its own complete
`description`, the order's `totals`, and a `starts_at`. Most options have one
schedule. An option whose terms change — an introductory price that steps up,
a weekly cadence that becomes monthly after a year — has one schedule per run,
in the order they take effect. The presence of `schedules` is what makes an
option a subscription; an option without it results in no recurring orders.

### Binding and indicative

On a catalog variant, and on the unselected options of a line, `schedules` are
**indicative**, like an unselected payment term: what choosing the option
would commit the buyer to, as the Business can best state it. On the selected
option of a cart or checkout line they **bind**: they state the recurring
orders the buyer agrees to by completing, and a
[subscription policy](#subscription-policy) and its disclosure accompany them
on the line. The Order line's `purchase_option` carries them unchanged.

### Description is the statement

A Business **MUST** make each schedule's `description` a complete buyer-facing
statement of that run of recurring orders — what each costs, how often one is
placed, from when, and until when — so that a Platform can render it verbatim.
There is no recurrence vocabulary on the wire — no interval, no cycle count,
no anchor — for the same reason a payment schedule states its timing in text:
the Business does the calendar arithmetic, and a Platform prints the result. A
Platform **MAY** use `totals` and `starts_at` for a richer presentation — a
budget check, a calendar reminder — but **MUST NOT** present derived terms that
contradict a `description`, and **MUST NOT** derive further order dates from
them.

Schedules are listed in the order they take effect. Each continues until the
next one's `starts_at`; the last continues until the subscription ends — until
cancelled, or until the end its `description` states.

### Totals

A recurring order is an order, and a schedule states what it costs the way a
line item does: `totals` follow the [line-item contract](../checkout/index.md#totals)
— entries carry a `type` and a signed `amount`, a Platform renders them in the
order provided and **MUST NOT** aggregate, filter, or reorder them, and a
`total` entry **MUST** be present. On a catalog variant they are for one unit;
on a cart or checkout line, for the line at its quantity. The option's own
`price` is always per unit.

`total` is the amount of the order **before** the taxes, fulfillment, and fees
the Business computes when it places it, because the rates that apply on a
future date are not knowable at checkout; the schedule `description` **MUST**
say so where they apply. A Business that *can* state one of those costs — a
flat shipping rate, a tax-exempt item — includes its entry, and `total` then
includes it. An omitted entry is not stated, not zero. A saving that expires
is a schedule that ends and another that begins.

### Start dates and the current purchase

The current purchase is the first order. Everything the buyer owes for it is in
the checkout `totals`, paid at completion or on the
[payment term](../../payment/extensions/terms.md) the buyer selected; the first
schedule's `starts_at` is when the first recurring order **after** it is
placed. An order is either this checkout or a recurring order under a schedule,
never both. `starts_at` **MAY** be omitted where the Business cannot yet
determine it — on a catalog surface, or on a cart that lacks the context its
first order date depends on — and **SHOULD** be present once a checkout is
`ready_for_complete`.

## Subscription policy

This extension also defines the `dev.ucp.shopping.policy.subscription` type on
the core [`policies[]`](../../overview/index.md#policies) primitive. The
selected option's `schedules` state what each recurring order costs and when;
the policy states the rest of the agreement — that the line results in
recurring orders and until when, and how the buyer cancels and manages it — and
carries the disclosure every jurisdiction requires before a buyer agrees to
recurring orders. It adds no fields to the base policy. Negotiating this
extension is how a Platform accepts the
[Platform obligations](#platform-obligations) below.

### Where

When a line's selected option carries `schedules`, the Business **MUST** emit a
subscription policy whose `applies_to` names that line, on every cart,
checkout, and order response that carries the line. Exactly one governs a
line; a line whose selected option has no `schedules` has none. Items on
different subscriptions are governed by separate policies, and two lines that
recur together on one set of terms are one policy with two targets.

On a catalog surface a Business **SHOULD** emit the policy targeting the
product or variant whose options carry `schedules`, so that a buyer can read
the renewal and cancellation terms before building a cart.

Nested line items are siblings in `line_items[]`, not JSON descendants of their
parent, so a policy that targets a parent line does not cover its components.
A bundle whose components recur on their own terms carries one policy per
recurring component line.

### What it says

The policy's `description` **MUST** state, in buyer-facing text:

- that the line results in recurring orders, and until when — until the buyer
    cancels, or until a stated end;
- how the buyer cancels, and any notice period or minimum commitment; and
- where the buyer manages the subscription.

The policy **MUST NOT** contradict the selected option's `schedules`, and
`url` **SHOULD** link to the full terms.

### The disclosure

Alongside every governing policy on a cart or checkout, the Business **MUST**
emit a `messages[]` warning with `presentation: "disclosure"`, `code` set to
`dev.ucp.shopping.policy.subscription`, and `path` naming the line, as
[Presenting policies](../../overview/index.md#presenting-policies) defines. Its
`content` **MUST** be sufficient on its own, because presenting a policy is
optional for a Platform and the disclosure is not. It **MUST** state:

- what the buyer pays today, where it differs from what each recurring order
    costs;
- what each recurring order costs, and whether taxes and shipping are added;
- how often recurring orders are placed, and when the first one is;
- until when they continue; and
- how to cancel.

A disclosure **MUST** agree with the governing policy and with the selected
option's `schedules`, and **MUST** be returned again whenever a change to the
checkout changes any of the terms it states.

### Platform obligations

A Platform that negotiates this extension **MUST**:

- present every subscription disclosure to the buyer under the
  [`disclosure` rendering contract](../checkout/index.md#warning-presentation):
  in proximity to the line, not hidden, collapsed, or dismissed;
- present it before completing the checkout, and not complete a checkout that
  carries a subscription disclosure the buyer has not been shown, unless the
  buyer has authorized the disclosed terms by another means the Business
  accepts, such as a signed [AP2 mandate](../../payment/extensions/ap2-mandates.md)
  over the checkout;
- escalate through `continue_url` when it cannot honor either of the above,
  rather than completing;
- honor an error with `severity: "requires_buyer_review"`, which a Business
  uses where it or a jurisdiction requires affirmative acknowledgment beyond
  display; and
- re-present the disclosure whenever a response returns it with changed
  content.

Completing a checkout under these obligations is the buyer's agreement to the
recurring orders, on the same trust model as a one-time purchase. This
extension adds no authorization field of its own.

### Payment eligibility

Recurring orders are paid with an instrument the Business can charge when the
buyer is not present. Checkout already requires a Business to filter the
payment handlers and instruments it offers to the context of the cart, and
names subscriptions as the example. A Business **MUST** offer only instruments
able to pay for the recurring orders the selected options state, and **MUST**
reject one that cannot. A Platform **MUST** treat the handlers in each response
as authoritative, and re-read them after any change that adds or removes a
subscription policy. How a handler stores an instrument, and how a payment for
a recurring order is executed or recovers from a decline, are payment-handler
and order-lifecycle behavior, outside this extension.

## Selecting an option

A Platform selects an option on a line by sending its identifier:

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.checkout op=create direction=request -->
```json
{
  "line_items": [
    {
      "item": { "id": "gid://example/Variant/coffee-340g" },
      "quantity": 2,
      "selected_purchase_option_id": "po_monthly"
    }
  ]
}
```

Selecting an option is a cart or checkout mutation, and the Business response
is **authoritative for all derived state**: `purchase_options` as priced for
this cart or checkout, the line's `item.price` and `totals`, the checkout
`totals`, `policies[]`, `messages[]`, the payment terms offered — a selection
can introduce a term, as a trial introduces a deferred one, or withdraw one —
and the payment handlers and instruments offered. A Platform **MUST NOT** assume the prices it
read in the catalog survive selection, and **MUST** re-render from the
response.

`selected_purchase_option_id` **MUST** match a `purchase_options[].id` from the
catalog or from the latest cart or checkout response for that line. A Platform
**SHOULD** always send an explicit selection. Where it sends none, the Business
selects the default and echoes it; a Platform that negotiated this extension is
expected to read the echoed selection and the policies and disclosures that
come with it. A Platform **MUST** omit the field on complete, because the
option is already agreed before a checkout can reach `ready_for_complete`.

The Business **MUST** make `purchase_options[].id` unique within a line, so
that a selection resolves to exactly one option.

### Selections that no longer resolve

An option can be withdrawn, repriced, or made ineligible between responses. A
Business receiving a selection that does not resolve against the options it
currently offers for that line **MUST NOT** silently substitute another. It
selects the default, returns the authoritative state, and **MUST** report the
change as a `purchase_option_changed` warning in `messages[]` with `path`
naming the line. A Business **MUST** report the same warning when it changes
the selected option in place — its price, or the terms a policy states for
it — without
naming a different one. A Platform can therefore detect a changed selection
from the code alone, rather than by comparing responses.

Changing the selected option can invalidate a selection accepted elsewhere in
the checkout: a deposit term a Business offers on one-time purchases but not
on subscriptions. The Business resolves the conflict and reports it through
that extension's own warning, `payment_term_changed`.

## Composition

### Payment terms

Payment terms answer when the current purchase is paid; a purchase option
answers what the current purchase is. They do not overlap. A try-before-you-buy
option is a one-time purchase at full `price` whose payment is deferred, so it
is expressed as an option plus a deferred payment term. A subscription's first
order is simply in the checkout `totals`, paid at completion like anything
else; the recurring orders are not owed yet and are not payment schedules. A
free trial composes the two: the option is the first order at full `price`
and its `schedules` state the recurring orders; its selection makes the
Business return a deferred payment term for that first order, and nothing is
paid at completion. In a catalog, when an option's purchase is paid is stated in its
`description`; a structured preview of payment timing there would be an
additive composition of payment terms onto catalog, title and description like
fulfillment's previews, not a field on the option.

### Nested line items

A purchase option is selected on the line it belongs to. Where a Business
composes a line from components — nested lines that reference it through
`parent_id` — the option is selected on the **parent**, and a selection sent
on a component line is not honored. The components' prices are a breakdown of
the parent's as that composition defines. Where components recur on their own
terms, the Business states them as the selected option of each component line
— response-only, set by the Business — each with a subscription policy
targeting that line. Purchase Options does not define composition and does not
infer it: an option never causes lines to be added or removed.

### Platforms that have not negotiated this extension

A Platform that has not negotiated this extension must not receive a variant
that looks ordinary but cannot be bought as one. For such a Platform a
Business:

- returns a variant that has a one-time option with that option's price as the
  variant's `price` and no extension fields, so it can be bought once as it
  always could;
- omits from search a variant that has no one-time option, and omits a product
  none of whose variants can be bought without this extension;
- returns an actionable `item_unavailable` message for such a variant on exact
  lookup, rather than an unusable result; and
- rejects an attempt to add such a variant to a cart or checkout with an
  `item_unavailable` error, never selling it the ordinary way.

## Order

When a checkout line carried `purchase_options`, the Business **MUST** include
`purchase_option` on the corresponding Order line, with the `id`, `title`, and
`schedules` of the option that was selected — including an explicitly listed
one-time option, which has no `schedules`. It is absent when the line's
variant carried no options.

The value is a historical snapshot. A Business **MUST NOT** change it when the
catalog option is later renamed, changed, or withdrawn, and a Platform **MUST
NOT** assume `purchase_option.id` still resolves through the catalog. The
snapshot records which offer produced the line and, in `schedules`, the
recurring orders agreed to; the Order line's `item.price` and `totals` record
what the current purchase cost. Available options are checkout state and are
not projected.

The Order also carries the subscription policies that governed its lines at
checkout as part of its `policies[]` snapshot, with `applies_to` re-targeted
to the Order's lines, together with the disclosure that paired with each, its
`path` naming the Order line. With the lines' `purchase_option` they are the
authoritative record of what was disclosed and agreed; a dispute is resolved
against them. They state what was agreed, not what has happened since: price
changes the Business notifies later, pauses, and cancellation belong to the
subscription, which a separate capability may expose. Recurring orders are
Orders in their own right, not adjustments to this one.

The Order is also where the buyer manages the subscription. Every Order carries
a `permalink_url` to the Business's order page, and the recurring orders
originate from this Order, so a buyer who can reach it can reach them.

## Out of scope

- **Subscription identity and management.** Status, modification, pause, and
  cancellation operations, and the lifecycle of the recurring orders, are a
  separate capability.
- **Payment execution.** Credential storage, recurring authorization models,
  mandates, and off-session recovery are payment-handler behavior.
- **When the current purchase is paid.** Payment terms.
- **Composition.** Which lines make up a bundle, how their totals relate, and
  how they are updated are defined by the capability that defines nested
  lines. An option is selected on one line and changes only that line.
- **Future deliveries.** A recurring option's delivery schedule is
  described in `description` until a capability for scheduled fulfillment
  exists. Billing cadence does not imply delivery cadence.
- **Platform-assembled options.** A Platform selects one id. It never composes
  a cadence, price, and commitment into an option the Business did not
  advertise.

## Responsibilities

Businesses **MUST**:

- List every way a variant can be bought, including a one-time purchase where
  one is offered, default first, with the variant's `price` stating the
  default option's price.
- Name one offered option in `selected_purchase_option_id` on every cart or
  checkout line that carries `purchase_options`, selecting the default where
  the Platform made no choice.
- Return the recomputed cart or checkout after a selection, including every
  change to prices, totals, policies, messages, payment terms, and payment
  handlers.
- Make each schedule's `description` a complete statement of that run of
  recurring orders, and keep its `totals` and `starts_at` consistent with it.
- Emit a subscription policy and its disclosure on every line whose selected
  option carries `schedules`, stating what [the policy](#what-it-says) and
  [the disclosure](#the-disclosure) require.
- Report a `purchase_option_changed` warning whenever a response changes the
  option in effect, by naming a different option or by rewriting the selected
  one in place.
- Honor a selection only on the line it is sent for; never add, remove, or
  change other lines as a consequence of a selection.
- Shape responses to Platforms that have not negotiated this extension so that
  no variant appears ordinarily purchasable when it is not.
- Carry the selected option onto the Order line as `purchase_option`, with its
  `schedules` as agreed.

Platforms **MUST**:

- Treat `purchase_options[].id` as opaque.
- Present `title`, `price`, `description`, and each schedule's `description`
  for each option so the buyer can compare them before selecting, unless only
  one option is offered.
- Re-render from the Business response after a selection.
- Treat the selected option's `schedules` and the line's subscription policy as
  the terms the buyer is agreeing to, and unselected options' `schedules` as
  indicative.
- Meet the [Platform obligations](#platform-obligations) for every
  subscription disclosure.
- Omit `selected_purchase_option_id` on complete.

Platforms **SHOULD**:

- Send an explicit `selected_purchase_option_id` rather than relying on the
  default.

## Examples

### Catalog: one-time or subscribe

A coffee that can be bought once for $10 or on a monthly plan for $8.50. The
one-time purchase is the default and first; the variant's `price` states it.
The monthly option's `list_price` is the one-time price it saves against, and
its `schedules` state the recurring orders for one unit — indicative, with no
start date yet.

<!-- ucp:example schema=shopping/purchase_options def=get_product_response op=get_product target=$.product.variants[0] -->
```json
{
  "id": "gid://example/Variant/coffee-340g",
  "title": "340g",
  "description": { "plain": "Medium roast, whole bean." },
  "price": { "amount": 1000, "currency": "USD" },
  "purchase_options": [
    {
      "id": "po_once",
      "title": "One-time",
      "price": { "amount": 1000, "currency": "USD" }
    },
    {
      "id": "po_monthly",
      "title": "Subscribe & save 15%",
      "description": { "plain": "Cancel anytime." },
      "price": { "amount": 850, "currency": "USD" },
      "list_price": { "amount": 1000, "currency": "USD" },
      "schedules": [
        {
          "description": { "plain": "$8.50 plus applicable tax and shipping every month until you cancel." },
          "totals": [
            { "type": "subtotal", "amount": 850 },
            { "type": "total", "amount": 850 }
          ]
        }
      ]
    }
  ]
}
```

A variant sold only on a plan lists no one-time option. Its `price` is the
default plan's price, and a Platform that adds it without choosing gets that
plan.

<!-- ucp:example schema=shopping/purchase_options def=get_product_response op=get_product target=$.product.variants[0] -->
```json
{
  "id": "gid://example/Variant/coffee-club",
  "title": "Coffee Club",
  "description": { "plain": "A rotating single-origin selection." },
  "price": { "amount": 1800, "currency": "USD" },
  "purchase_options": [
    {
      "id": "po_club_monthly",
      "title": "Monthly",
      "description": { "plain": "One bag a month. Cancel anytime." },
      "price": { "amount": 1800, "currency": "USD" },
      "schedules": [
        {
          "description": { "plain": "$18.00 plus applicable tax and shipping every month until you cancel." },
          "totals": [
            { "type": "subtotal", "amount": 1800 },
            { "type": "total", "amount": 1800 }
          ]
        }
      ]
    },
    {
      "id": "po_club_quarterly",
      "title": "Quarterly",
      "description": { "plain": "Three bags every three months. Cancel anytime." },
      "price": { "amount": 5100, "currency": "USD" },
      "list_price": { "amount": 5400, "currency": "USD" },
      "schedules": [
        {
          "description": { "plain": "$51.00 plus applicable tax and shipping every three months until you cancel." },
          "totals": [
            { "type": "subtotal", "amount": 5100 },
            { "type": "total", "amount": 5100 }
          ]
        }
      ]
    }
  ]
}
```

On either product, a subscription policy states the renewal and cancellation
terms before a cart exists:

<!-- ucp:example schema=shopping/purchase_options def=get_product_response op=get_product target=$.policies -->
```json
[
  {
    "type": "dev.ucp.shopping.policy.subscription",
    "description": { "plain": "Subscriptions renew until you cancel. Cancel anytime from your account; no minimum commitment." },
    "applies_to": ["$.product"],
    "url": "https://example.com/subscription-terms"
  }
]
```

### Checkout: the subscription selected

The Platform selected `po_monthly` for two bags. The line is priced under the
selected option and today's `totals` settle those two bags. The selected
option's `schedules` now bind — at the line's quantity, with a start date —
and the subscription policy and its disclosure accompany them. The one-time
option is echoed for comparison.

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_abc123",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/coffee-340g", "title": "House Blend 340g", "price": 850 },
      "quantity": 2,
      "totals": [
        { "type": "subtotal", "amount": 1700 },
        { "type": "total", "amount": 1700 }
      ],
      "selected_purchase_option_id": "po_monthly",
      "purchase_options": [
        {
          "id": "po_once",
          "title": "One-time",
          "price": { "amount": 1000, "currency": "USD" }
        },
        {
          "id": "po_monthly",
          "title": "Subscribe & save 15%",
          "description": { "plain": "Cancel anytime." },
          "price": { "amount": 850, "currency": "USD" },
          "list_price": { "amount": 1000, "currency": "USD" },
          "schedules": [
            {
              "description": { "plain": "$17.00 plus applicable tax and shipping every month from November 2, 2026, until you cancel." },
              "totals": [
                { "type": "subtotal", "amount": 1700 },
                { "type": "total", "amount": 1700 }
              ],
              "starts_at": "2026-11-02T00:00:00Z"
            }
          ]
        }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 1700 },
    { "type": "tax", "amount": 136 },
    { "type": "total", "amount": 1836 }
  ],
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": {
        "plain": "Renews monthly until you cancel. Cancel anytime from your account at example.com/account; no minimum commitment."
      },
      "applies_to": ["$.line_items[0]"],
      "url": "https://example.com/subscription-terms"
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "dev.ucp.shopping.policy.subscription",
      "path": "$.line_items[0]",
      "presentation": "disclosure",
      "content": "$18.36 today. Then $17.00 plus tax and shipping every month from November 2, 2026, until you cancel. Cancel anytime at example.com/account."
    }
  ],
  "links": [ ... ]
}
```

### Checkout: a free trial selected

A trial option is the first order at its full price, with `schedules` for the
recurring orders that follow. Selecting it makes the Business return a
deferred payment term for that first order — due at the end of the trial
unless the buyer cancels first. Nothing is paid at completion. The unselected
"Start today" option's schedules remain indicative, for comparison.

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_trial",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/pro-plan", "title": "Pro plan", "price": 1200 },
      "quantity": 1,
      "totals": [
        { "type": "subtotal", "amount": 1200 },
        { "type": "total", "amount": 1200 }
      ],
      "selected_purchase_option_id": "po_trial",
      "purchase_options": [
        {
          "id": "po_trial",
          "title": "Start with a 14-day free trial",
          "description": { "plain": "Cancel before October 16, 2026 and you owe nothing." },
          "price": { "amount": 1200, "currency": "USD" },
          "schedules": [
            {
              "description": { "plain": "$12.00 every month from November 16, 2026, until you cancel." },
              "totals": [
                { "type": "subtotal", "amount": 1200 },
                { "type": "total", "amount": 1200 }
              ],
              "starts_at": "2026-11-16T00:00:00Z"
            }
          ]
        },
        {
          "id": "po_monthly",
          "title": "Start today",
          "price": { "amount": 1200, "currency": "USD" },
          "schedules": [
            {
              "description": { "plain": "$12.00 every month from November 2, 2026, until you cancel." },
              "totals": [
                { "type": "subtotal", "amount": 1200 },
                { "type": "total", "amount": 1200 }
              ],
              "starts_at": "2026-11-02T00:00:00Z"
            }
          ]
        }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 1200 },
    { "type": "total", "amount": 1200 }
  ],
  "payment": {
    "terms": [
      {
        "id": "pt_trial",
        "title": "Free for 14 days",
        "description": { "plain": "Nothing today. Cancel before October 16, 2026 and you owe nothing." },
        "schedules": [
          {
            "id": "sched_after_trial",
            "type": "deferred",
            "description": { "plain": "$12.00 due October 16, 2026, unless you cancel before then." },
            "due_at": "2026-10-16T00:00:00Z",
            "amount": 1200
          }
        ]
      }
    ],
    "selected_term_id": "pt_trial"
  },
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": {
        "plain": "Renews monthly after the trial until you cancel. Cancel anytime from your account at example.com/account; no minimum commitment."
      },
      "applies_to": ["$.line_items[0]"],
      "url": "https://example.com/subscription-terms"
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "dev.ucp.shopping.policy.subscription",
      "path": "$.line_items[0]",
      "presentation": "disclosure",
      "content": "Free for 14 days. $12.00 on October 16, 2026 unless you cancel before then, and $12.00 every month after. Cancel anytime at example.com/account."
    }
  ],
  "links": [ ... ]
}
```

### Checkout: an introductory price

Today's order is the first of three months at an introductory rate. Two
schedules follow: the remaining two introductory months, then the standing
rate until cancelled. The first ends where the second begins; the Business
computed both dates.

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_intro",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/coffee-340g", "title": "House Blend 340g", "price": 500 },
      "quantity": 2,
      "totals": [
        { "type": "subtotal", "amount": 1000 },
        { "type": "total", "amount": 1000 }
      ],
      "selected_purchase_option_id": "po_intro",
      "purchase_options": [
        {
          "id": "po_once",
          "title": "One-time",
          "price": { "amount": 1000, "currency": "USD" }
        },
        {
          "id": "po_intro",
          "title": "Subscribe — half price for 3 months",
          "price": { "amount": 500, "currency": "USD" },
          "list_price": { "amount": 1000, "currency": "USD" },
          "schedules": [
            {
              "description": { "plain": "$10.00 plus applicable tax and shipping on November 2 and December 2, 2026." },
              "totals": [
                { "type": "subtotal", "amount": 1000 },
                { "type": "total", "amount": 1000 }
              ],
              "starts_at": "2026-11-02T00:00:00Z"
            },
            {
              "description": {
                "plain": "Then $17.00 plus applicable tax and shipping every month from January 2, 2027, until you cancel."
              },
              "totals": [
                { "type": "subtotal", "amount": 1700 },
                { "type": "total", "amount": 1700 }
              ],
              "starts_at": "2027-01-02T00:00:00Z"
            }
          ]
        }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 1000 },
    { "type": "tax", "amount": 80 },
    { "type": "total", "amount": 1080 }
  ],
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": {
        "plain": "Renews monthly until you cancel, at an introductory rate for the first three months including today's order. Cancel anytime from your account at example.com/account; no minimum commitment."
      },
      "applies_to": ["$.line_items[0]"],
      "url": "https://example.com/subscription-terms"
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "dev.ucp.shopping.policy.subscription",
      "path": "$.line_items[0]",
      "presentation": "disclosure",
      "content": "$10.80 today, then $10.00 plus tax and shipping on November 2 and December 2, then $17.00 plus tax and shipping every month from January 2, 2027, until you cancel. Cancel anytime at example.com/account."
    }
  ],
  "links": [ ... ]
}
```

### Checkout: a cadence that changes

Weekly for the first year, then monthly. The amount happens not to change; the
cadence does, so the two runs are two schedules.

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_weekly",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/coffee-340g", "title": "House Blend 340g", "price": 1500 },
      "quantity": 1,
      "totals": [
        { "type": "subtotal", "amount": 1500 },
        { "type": "total", "amount": 1500 }
      ],
      "selected_purchase_option_id": "po_weekly",
      "purchase_options": [
        {
          "id": "po_once",
          "title": "One-time",
          "price": { "amount": 1500, "currency": "USD" }
        },
        {
          "id": "po_weekly",
          "title": "Weekly for a year, then monthly",
          "price": { "amount": 1500, "currency": "USD" },
          "schedules": [
            {
              "description": {
                "plain": "$15.00 plus applicable tax and shipping every week from October 9, 2026 through October 1, 2027."
              },
              "totals": [
                { "type": "subtotal", "amount": 1500 },
                { "type": "total", "amount": 1500 }
              ],
              "starts_at": "2026-10-09T00:00:00Z"
            },
            {
              "description": {
                "plain": "Then $15.00 plus applicable tax and shipping every month from October 8, 2027, until you cancel."
              },
              "totals": [
                { "type": "subtotal", "amount": 1500 },
                { "type": "total", "amount": 1500 }
              ],
              "starts_at": "2027-10-08T00:00:00Z"
            }
          ]
        }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 1500 },
    { "type": "tax", "amount": 120 },
    { "type": "total", "amount": 1620 }
  ],
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": {
        "plain": "Renews weekly for the first year, then monthly, until you cancel. Cancel anytime from your account at example.com/account; no minimum commitment."
      },
      "applies_to": ["$.line_items[0]"],
      "url": "https://example.com/subscription-terms"
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "dev.ucp.shopping.policy.subscription",
      "path": "$.line_items[0]",
      "presentation": "disclosure",
      "content": "$16.20 today. Then $15.00 plus tax and shipping every week from October 9, 2026 through October 1, 2027, and every month from October 8, 2027, until you cancel. Cancel anytime at example.com/account."
    }
  ],
  "links": [ ... ]
}
```

### Checkout: a subscription that ends

A filter pack every two weeks for one year. One schedule whose `description`
states the end.

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_filters",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/filters-50", "title": "Filters (50)", "price": 600 },
      "quantity": 1,
      "totals": [
        { "type": "subtotal", "amount": 600 },
        { "type": "total", "amount": 600 }
      ],
      "selected_purchase_option_id": "po_year",
      "purchase_options": [
        {
          "id": "po_once",
          "title": "One-time",
          "price": { "amount": 600, "currency": "USD" }
        },
        {
          "id": "po_year",
          "title": "Every 2 weeks for a year",
          "price": { "amount": 600, "currency": "USD" },
          "schedules": [
            {
              "description": {
                "plain": "$6.00 plus applicable tax and shipping every 2 weeks from October 16, 2026 through October 1, 2027 (26 recurring orders), then stops."
              },
              "totals": [
                { "type": "subtotal", "amount": 600 },
                { "type": "total", "amount": 600 }
              ],
              "starts_at": "2026-10-16T00:00:00Z"
            }
          ]
        }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 600 },
    { "type": "tax", "amount": 48 },
    { "type": "total", "amount": 648 }
  ],
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": {
        "plain": "Ends on its own after October 1, 2027; does not renew. Cancel anytime before then from your account at example.com/account."
      },
      "applies_to": ["$.line_items[0]"],
      "url": "https://example.com/subscription-terms"
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "dev.ucp.shopping.policy.subscription",
      "path": "$.line_items[0]",
      "presentation": "disclosure",
      "content": "$6.48 today. Then $6.00 plus tax and shipping every 2 weeks from October 16, 2026 through October 1, 2027, then stops. Cancel anytime at example.com/account."
    }
  ],
  "links": [ ... ]
}
```

### Switching back to one-time

The Platform changes the selection with an update. The Business reprices the
line at $10; the subscription policy and its disclosure disappear with the
schedules, and any payment handlers it had withheld for the subscription
return.

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.checkout op=update direction=request -->
```json
{
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/coffee-340g" },
      "quantity": 2,
      "selected_purchase_option_id": "po_once"
    }
  ]
}
```

### A selection that no longer resolves

The monthly plan was withdrawn between responses. The Business selects the
default, reprices, and says so:

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "purchase_option_changed",
    "path": "$.line_items[0]",
    "content": "The monthly plan is no longer available for this item. It has been added as a one-time purchase at $10.00."
  }
]
```

### Order

The Order line records the option it was bought through and the schedules
agreed to. The Order's subscription policy and its disclosure travel with it,
as that extension shows.

<!-- ucp:example schema=shopping/purchase_options def=dev.ucp.shopping.order op=read -->
```json
{
  "ucp": { ... },
  "id": "ord_8f3e2a",
  "checkout_id": "chk_abc123",
  "permalink_url": "https://example.com/orders/8f3e2a",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/coffee-340g", "title": "House Blend 340g", "price": 850 },
      "quantity": { "original": 2, "total": 2, "fulfilled": 0 },
      "totals": [ ... ],
      "status": "processing",
      "purchase_option": {
        "id": "po_monthly",
        "title": "Subscribe & save 15%",
        "schedules": [
          {
            "description": { "plain": "$17.00 plus applicable tax and shipping every month from November 2, 2026, until you cancel." },
            "totals": [
              { "type": "subtotal", "amount": 1700 },
              { "type": "total", "amount": 1700 }
            ],
            "starts_at": "2026-11-02T00:00:00Z"
          }
        ]
      }
    }
  ],
  "totals": [ ... ],
  "fulfillment": { ... },
  "policies": [ ... ]
}
```
