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

<!-- cspell:ignore inpost InPost orlenpaczka Poczta poczta Polska polska Odstąp umowy tutaj Potwierdź odstąpienie -->

# Withdrawal Policy Extension

## Overview

The Withdrawal Policy Extension defines the
`dev.ucp.shopping.policy.withdrawal` policy type on the core
[`policies[]`](../../overview/index.md#policies) primitive. It states the
buyer's right to withdraw from a distance contract within a set period without
giving a reason, often called a cooling-off right, whether the law that governs
the contract grants it or the Business does. It lets platforms and agents
answer "Can I cancel this purchase?", "How long do I have, and from when?",
"Who pays to send it back?", and "Where do I withdraw?" from structured data.

A withdrawal right is not a return policy. A return policy states the
Business's own commercial terms; a statutory withdrawal right exists whatever
those terms say, has its own exceptions, and has its own refund rules. The two
are separate policy types so that both can govern the same item: an item can be
final sale under the return policy and still be covered by a statutory
withdrawal right. See
[Withdrawal and return policies](#withdrawal-and-return-policies).

**Key features:**

- Why the right exists (`basis`): granted by law, or by the Business
- Whether it covers the targeted items, with an exception code and text for
  items excluded from it or that can lose it (`availability`)
- The period and the event it starts from, resolved to a deadline once known
  (`period`), and a longer contractual period on top of a statutory one
  (`extension`)
- Who pays for returning goods, and how much (`return_costs`)
- How the goods go back: collection by the Business, a carrier network's
  points, a courier, post, or a shop, and whether the Business issues a label
  or a return code (`return_methods`)
- Refund terms: deadline, withholding, and which delivery payments are
  refunded (`refund`)
- Links to the instructions and the model withdrawal form
  (`instructions_url`, `model_form_url`)
- Where the online withdrawal function is and how its controls are labelled
  in each language (`withdrawal_function`)
- On the order, after a withdrawal or a return request: the return shipments
  the Business set up, with a return label or a carrier return code and the
  time to send the goods back (`return_shipments`), and return-side
  fulfillment events

**Dependencies:**

- The core `policies[]` primitive (see
  [Policies](../../overview/index.md#policies)).
- One or more of the parent capabilities this type extends: Catalog Search,
  Catalog Lookup, Cart, Checkout, or Order.

This extension only structures the type-specific body. The `policies[]`
container, `applies_to` targeting, same-type precedence, and buyer-facing
disclosure through `messages[]` are defined once by the primitive and are
**unchanged** here.

**Scope:** this version describes one contract with one trader per checkout or
order. A checkout that covers contracts with several sellers is out of scope
until seller attribution on line items is defined; a Business **MUST NOT** use
a response-wide withdrawal policy for lines that belong to different traders.

## Discovery

Businesses advertise withdrawal policy support in their profile. The type
extends any surface that carries `policies[]`:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.policy.withdrawal": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup",
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/withdrawal-policy",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/policy_withdrawal.json"
        }
      ]
    }
  }
}
```

A business **MAY** advertise support on a subset of these surfaces. A platform
that has negotiated this type validates the withdrawal body and **MAY** reason
over its structured fields only when the body passes schema validation. For a
platform that has not negotiated it, the policy stays presentable from the base
`type` and `description`. Whether a platform must present it is decided by the
disclosure mechanism (see [Presenting the right](#presenting-the-right)), not
by negotiation.

## Schema

When this type is active, a `policies[]` entry whose `type` is
`dev.ucp.shopping.policy.withdrawal` carries `basis` and **MAY** carry the
other fields below, in addition to the base `type`, `description`,
`applies_to`, and `url`. An omitted optional field means the term is not stated
structurally, not that it is absent from the Business's terms.

### Withdrawal Policy

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_body', 'shopping/extensions/withdrawal-policy') }}

### Withdrawal Availability

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_availability', 'shopping/extensions/withdrawal-policy') }}

### Withdrawal Exception

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_exception', 'shopping/extensions/withdrawal-policy') }}

### Withdrawal Period

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_period', 'shopping/extensions/withdrawal-policy') }}

### Withdrawal Extension

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_extension', 'shopping/extensions/withdrawal-policy') }}

### Withdrawal Return Costs

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_return_costs', 'shopping/extensions/withdrawal-policy') }}

### Withdrawal Return Method

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_return_method', 'shopping/extensions/withdrawal-policy') }}

### Withdrawal Refund

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_refund', 'shopping/extensions/withdrawal-policy') }}

### Withdrawal Function

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_function', 'shopping/extensions/withdrawal-policy') }}

### Withdrawal Function Label

Each entry in `withdrawal_function.labels` uses this shape.

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_function_label', 'shopping/extensions/withdrawal-policy') }}

### Return Shipment

{{ schema_fields('types/return_shipment', 'shopping/extensions/withdrawal-policy') }}

### Return Code

{{ extension_schema_fields('types/return_shipment.json#/$defs/return_code', 'shopping/extensions/withdrawal-policy') }}

### Return Label

{{ extension_schema_fields('types/return_shipment.json#/$defs/return_label', 'shopping/extensions/withdrawal-policy') }}

### Return Point

{{ extension_schema_fields('types/return_shipment.json#/$defs/return_point', 'shopping/extensions/withdrawal-policy') }}

### Return Fulfillment Event

{{ extension_schema_fields('types/return_shipment.json#/$defs/return_event', 'shopping/extensions/withdrawal-policy') }}

## Withdrawal terms

### Basis

`basis` says why the right exists. A `statutory` right is granted by the law
that governs the contract, so the Business's terms cannot narrow it. A
`contractual` right is one the Business grants where no law requires it. A
business **MUST** state `basis`, and the schema requires it.

A platform **MUST NOT** present a `statutory` right as a distinctive feature of
the Business's offer, for example as "our 14-day free cancellation" in a list
of the Business's advantages. It presents it as a right the buyer has. A
platform that does not recognize the `basis` value presents the policy from its
`description` and **MUST NOT** present the right as statutory.

### Availability and exceptions

`availability` states whether the right covers the targeted items:

| Type | Meaning |
| :-- | :-- |
| `available` | The right covers the items. |
| `not_available` | There is no withdrawal right for the items, for example goods made to the buyer's specifications. |
| `conditional` | The right covers the items but is lost when a condition occurs, for example unsealing, after delivery, a sealed item not suitable for return for health or hygiene reasons. |

A `not_available` or `conditional` availability **MUST** carry an `exception`
with `display_text`, the statement the buyer is shown: that there is no right,
or the circumstances in which it is lost. `code` identifies the exception in
the legal regime that defines it, namespaced by that regime (see
[EU consumer contracts](#eu-consumer-contracts) for the well-known codes).

Whether an exception applies to an item is the Business's determination.
A platform presents `display_text` as the Business's statement and **MUST NOT**
derive an exception from product data on its own, nor from a return policy's
final-sale flag. Because the period, costs, refund, extension, model form and
withdrawal function do not apply to an item with no right, a business **MUST
NOT** carry them on a `not_available` policy; the schema rejects the
combination.

A business states the default terms once in a response-wide withdrawal policy
and adds an item-scoped policy for each excepted item, using `applies_to` and
same-type precedence (see [Targeting and precedence](#targeting-and-precedence)).
An item-scoped policy states which items the right covers; it does not state
that the buyer may withdraw from those items alone. Withdrawal from part of a
contract is a matter for the governing law and the Business's terms.

### Period and anchor

`period` states the length of the withdrawal period (`duration`) and the event
it is measured from (`anchor`), both required, with an optional
`display_text` stating the same in words. Once the anchor event has occurred,
the business resolves the deadline under the calendar rules of the governing
law and states it as `expires_at`.

`anchor` is an open vocabulary. The well-known values are:

| Anchor | The period is measured from |
| :-- | :-- |
| `contract_concluded` | The conclusion of the contract under the law that governs it. This can be later than the order being placed, for example on the Business's acceptance. Used for services and for digital content not supplied on a tangible medium. |
| `possession` | The buyer, or a third party other than the carrier that the buyer indicated, acquiring physical possession of the goods. |
| `possession_last_item` | That possession of the last item, lot, or piece of an order delivered in several shipments, lots, or pieces. |
| `possession_first_item` | That possession of the first item, for a contract for regular delivery of goods. |

The Business determines when the anchor event occurred. These anchors differ
from the return policy's `delivered`. For goods sent to a carrier pickup point
or a parcel locker, the usual case is that possession occurs when the buyer
collects the parcel (the carrier pickup event `collected_at_point`), not when
the carrier deposits it (`deposited_at_point`), because the point is operated
by or for the carrier. A Business that applies a different reading,
for example for a point the buyer chose that is not part of the carrier's
network, states it in `description`. What follows when a parcel is never
collected is governed by the contract and the governing law, not by this
extension.

A business that does not know at checkout whether an order ships in one
shipment or several **MAY** state `possession_last_item`. The `display_text`
of every policy that uses it describes the start the same way, for example
"14 days from the day after you receive the last item of your order".

A business **MUST NOT** state an `expires_at` earlier than the end of the period
its `duration` and `anchor` describe. It **MUST** update `expires_at` when the
legal deadline changes, and set `revised_at` to the time of the change. The
change can go either way. When the Business did not give the required
withdrawal information, the governing law can extend the period; when it gives
that information later, within a set time counted from the anchor event, the
period can then end a set time after the buyer receives it, which can be
earlier than the extended deadline, though never before the end of the original
period. A platform **MUST** re-read the policy
before it tells the buyer a deadline, **MUST NOT** cache `expires_at` as final,
and **MUST NOT** tell the buyer the right has expired from a date it computed
itself. A withdrawal the buyer sends at or before the instant `expires_at`
names is in time, even if the Business processes it later.

The right can be exercised before the anchor event. A missing `expires_at`
means the deadline is not yet resolved, not that the buyer cannot withdraw yet;
a platform **MUST NOT** present it that way.

A platform **MAY** present `expires_at` in any time zone and **MUST NOT**
present a later deadline, for example by showing only its date. Without
`expires_at`, it presents the terms from `period.display_text`, or from
`duration` and `anchor`, for example "14 days from the day after you collect
the parcel".

### Contractual extension

A Business that grants more than the statutory period, for example 30 days
instead of 14, keeps one `statutory` policy and adds `extension`. The
policy's `period` and other fields state the statutory terms. `extension.period`
states the full contractual period, and `extension.display_text` the terms that
apply to a withdrawal sent after the statutory period ends. The contractual
period can end before the statutory one, for example when the governing law
extends the statutory period; the statutory period then governs until its own
`expires_at`. Only a `statutory`
policy carries `extension`; the schema rejects it elsewhere. A Business does
not publish a second withdrawal policy for the same items, since two policies
of one type at the same target collide under
[Precedence](../../overview/index.md#precedence).

A platform that presents an `extension` shows both periods, each with its own
deadline and label, for example "Legal withdrawal right: until 17 March" and
"Extended by the seller: until 2 April, store credit only". It **MUST NOT**
merge them into one period that hides which terms apply when.

### Return costs

`return_costs.payer` states who bears the direct cost of returning the goods.
When the buyer pays, `cost` states the amount with its currency, `cost_type`
whether it is `exact` or a `maximum` (a reasonable estimate of the highest
cost, used for goods that cannot normally be returned by post), and `cost_unit`
what one `cost` covers: all goods returned together (`per_return`), each return
shipment (`per_shipment`), or each item (`per_item`). When `return_costs` is
omitted, the terms are not stated structurally and a platform **MUST NOT** tell
the buyer that the buyer pays.

### Return methods

`return_methods` lists how the buyer can send the goods back or have them
collected after withdrawing. It is part of the procedure for exercising the
right that the Business states before the contract, so it is static: the
label or code for one order comes later, on the order (see
[Return shipments](#return-shipments)). When `return_methods` is omitted, the
methods are not stated structurally and `instructions_url` remains the
statement of the procedure.

| `type` | The buyer | `network` |
| :-- | :-- | :-- |
| `trader_collects` | hands the goods over; the Business collects them itself or through a carrier it sends | no |
| `carrier_point` | drops the parcel at a locker or a staffed point of the network | required |
| `carrier_pickup_at_address` | has a courier of the network collect the parcel, using the Business's label or code | required |
| `postal` | posts the goods through a postal or parcel service to the return address in the instructions | required when the Business issues a label or code |
| `in_store` | hands the goods over at the Business's premises | no |

`type` is an open string. A platform that does not recognize a value presents
the entry's `display_text` and does not describe the method itself; an
unrecognized entry without `display_text` is not presented.

`network` uses the network identifier format proposed for carrier pickup
points ([#1139](https://github.com/Universal-Commerce-Protocol/ucp/pull/1139)):
a reverse-domain name of the operator's primary domain, such as `eu.inpost`,
`pl.orlenpaczka`, `pl.poczta-polska`, `com.dhl` or `com.dpd`. Where that
proposal lists a well-known value for a network, Businesses and platforms use
it, so that a return and a delivery name the same network the same way. A host site that serves several networks, such as a
convenience store chain, is not a network: a return through such a site names
the network whose code or label it accepts. Two entries with the same `type`
and different `network` values are two methods; a Business that accepts
returns at the points of several networks lists each.

`artifacts` says what the Business issues for a return by the method once
the buyer has withdrawn: a `label`, a return `code`, or both. When it is
omitted or empty, the Business issues neither. A platform that does not
recognize an `artifacts` value claims nothing about it and relies on the
entry's `display_text`. `printer_required` is `true` when the buyer needs a
printer for the method, whether for the Business's label or for one the buyer
buys, as with `postal` at the buyer's own carrier. A Business that offers a
method with a code and no label **MUST** accept the parcel on the code alone
and **MUST NOT** require the buyer to print anything for that method; the
schema rejects `printer_required: true` on such a method. A platform **MUST
NOT** tell the buyer a printer is needed unless `printer_required` is `true`.

`return_costs` on a method states the return costs for that method, and only
where they differ from the policy-level `return_costs`. When present, it
replaces the policy-level `return_costs` for returns by that method; when
omitted, the policy-level `return_costs` applies. A Business **MUST NOT**
repeat the policy-level terms on every method. When the buyer bears a cost by
one method and not by another, a platform presents both and does not present
the lower one as the cost of returning.

`trader_collects` means the Business has offered to collect the goods itself.
The Business lists it only when it has made that offer for the goods the policy
covers. Only `trader_collects` carries that meaning in this extension: a
Business that books the courier itself and only asks the buyer to hand the
goods over lists `trader_collects`, not `carrier_pickup_at_address`. The
method's effective `return_costs` (its own, or else the policy-level one)
says whether the collection is at the Business's expense.

Under EU law the offer affects the refund (CRD Art. 13(3)) and the buyer's
duty to send the goods back (Art. 14(1)). The Commission's guidance on the
directive (2021/C 525/01, sections 5.5.2 and 5.5.3) reads both by who pays:
an offer to collect binds the buyer only if the trader also offered to bear
the cost, and the trader cannot withhold the refund if the buyer accepts the
offer or the trader offered to collect at its own expense. For a `statutory`
policy under EU law this extension follows that reading:

- When a `trader_collects` method is at the Business's expense (its own
  `return_costs`, or else the policy-level one, has `payer: business`), the
  Business **MUST NOT** state `refund.withholding:
  until_goods_or_proof_of_dispatch`. The schema does not enforce this,
  because a policy has no field that says which law governs it, and the rule
  does not hold for statutory rights under other laws.
- When the buyer pays for the collection, the policy may still state
  withholding, because it applies to returns by the other methods. For a
  return the buyer has the Business collect, the Business **MUST NOT**
  withhold the refund, and a platform **MUST NOT** present withholding as
  applying to that return.
- A paid collection does not oblige the buyer to use it; the buyer may send
  the goods back by another method within the time Art. 14(1) allows.

For a `contractual` policy, and for statutory rights under other laws, the
Business's own terms and that law decide.

### Refund

`refund.deadline` is the outer limit for refunding the payments received,
counted from the day the Business is informed of the withdrawal. The Business
refunds without undue delay and in any event within it; the limit is not a
waiting period. `refund.withholding`
states whether, for a sale of goods, the Business may hold the refund until it
receives the goods back or the buyer shows they were sent, whichever is
earlier. A platform **MUST NOT** present `deadline` as unconditional when
`withholding` is `until_goods_or_proof_of_dispatch`.

`refund.delivery` states which delivery payments are refunded on a withdrawal
from the whole contract. `up_to_least_expensive_standard` means the delivery
payments received are refunded, except the extra cost of a delivery option the
buyer chose over the least expensive standard delivery the Business offered.
It is a rule, not a price: the refund depends on what the buyer paid, after any
promotion. A platform **MUST NOT** compute a refund amount from it. This
extension does not state how delivery payments are treated when the buyer
withdraws from part of a contract.

For a `statutory` withdrawal, a business **MUST NOT** deduct a return-policy
fee, such as `dev.ucp.shopping.fee.restocking` or
`dev.ucp.shopping.fee.handling`, from the refund. A deduction the law allows
for a reduced value of the goods is assessed per item after the goods come back
and is not a flat fee. The return shipping cost under a statutory withdrawal is
the one `return_costs` states, not a return-policy
`dev.ucp.shopping.fee.return_shipping`. For a `contractual` right and for the
`extension` period, the Business's own terms apply.

### Instructions, model form, and withdrawal function

`instructions_url` links to the conditions, time limit, and procedure.
`model_form_url` links to the withdrawal form the buyer may use, where the
governing law provides one; it is in addition to the online function.

`withdrawal_function` describes the Business's online withdrawal function:

- `url` is the page where the buyer withdraws. It is the Business's own
  interface, so the Business displays it prominently there, keeps it easy to
  reach and available for the whole withdrawal period, including before the
  goods arrive, and does not require the buyer to install an application they
  did not use to conclude the contract. Advertising `url` here does not show
  that the function meets the governing law.
- `url` **MUST NOT** carry a contract identifier that gives access without
  authenticating the buyer. A Business that deep-links to a contract uses an
  authenticated session or an unguessable token. A link opened outside a
  session opens the withdrawal statement without the contract details filled
  in, so the buyer provides them; it does not open a login step.
- `labels` gives, per language, the label of the control that opens the
  withdrawal statement (`withdraw`) and, for information, the label of the
  control on the Business's function that submits it (`confirm`). Each
  language appears at most once. Exactly one entry has
  `contract_language: true`, marking the language the contract is concluded
  in or, on a catalog or cart surface before a contract exists, the language
  it will be concluded in; the schema requires it.

A platform that renders a control leading to `url` **MUST** label it with the
Business's `withdraw` text. It picks the entry by applying the Lookup scheme
of RFC 4647, Section 3.4, to the buyer's language tag, with the entries'
`language` tags as the available tags. With no match, it uses the entry with
`contract_language: true`. If it cannot show that wording, for
example in a voice channel, it **MUST NOT** substitute its own label. On a
checkout it hands off through `continue_url`; on an order it gives the buyer
`url` to open in the buyer's own client, where the Business's interface shows
its own label.

The function itself is the Business's obligation on its own interface:

- The withdrawal statement lets the buyer easily give or confirm their name,
  details identifying the contract, and the electronic means by which the
  Business will send the acknowledgement.
- Once the buyer has completed the statement, the Business enables them to
  submit it through the confirmation control (Art. 11a(3)). The Business
  **MUST NOT** make the confirmation control depend on anything else: not on
  a reason for withdrawing (the right exists "without giving any reason",
  Art. 9(1)), not on an answer to a survey, and not on accepting or
  dismissing an offer.
- A buyer who is already identified in the session, for example by being
  logged in, **MUST NOT** be asked to log in again; the statement lets them
  "easily provide or confirm" their name and the contract details
  (Art. 11a(2)), so the Business fills in what it knows and the buyer
  confirms it.
- The Business **SHOULD NOT** require a buyer who is not logged in to log in
  or create an account, since the statement itself carries the name and the
  contract details; **SHOULD NOT** ask an identified buyer to identify the
  contract again where the session already identifies it; and **SHOULD NOT**
  add any other step between opening the function and confirming. These rest
  on Recital 37 of Directive (EU) 2023/2673, which says the consumer should
  be able to withdraw "just as easily" as they concluded the contract and
  that an identified consumer should not have to provide their
  identification again.
- Questions, such as the reason for withdrawing, **MAY** be asked if answering
  is optional and the confirmation control works without an answer.
- The Business **SHOULD NOT** show an offer meant to keep the contract, such
  as a discount or an exchange, inside the function at all, even one that does
  not block the confirmation.
- The buyer submits the statement through a separate confirmation control,
  labelled with the wording the governing law prescribes. `confirm` states that
  label for information; when it is omitted, a platform does not render a
  confirmation control or derive a label of its own.
- After submission, the Business sends, without undue delay and on a durable
  medium, an acknowledgement of receipt that states the content of the
  statement and the date and time it was submitted. The Business sends it
  itself; a UCP response to the platform is not that acknowledgement. The
  Business **MUST NOT** delay the acknowledgement until a return label or
  code exists, and **MUST NOT** make it depend on the buyer answering an
  offer. An offer the Business makes after the acknowledgement does not affect
  the withdrawal the buyer has already exercised.

This extension advertises the function; it does not define a UCP operation to
withdraw. A platform **MUST NOT** submit a withdrawal on the buyer's behalf,
and **MUST NOT** pass the buyer's contact details to the function, without the
buyer's explicit instruction.

## Withdrawal and return policies

The withdrawal and return policy types are independent. Precedence applies per
type, so a return policy never overrides a withdrawal policy, and the reverse.
A platform that models both:

- **MUST NOT** treat a return policy with `eligibility.type: not_accepted` as
  removing a withdrawal right. Only a withdrawal policy with
  `availability.type: not_available` states that there is none.
- **MUST** keep the withdrawal terms visible when it presents both: the period
  and its start event, who pays for the return, the refund terms, and the link
  to the withdrawal function.
- **MUST** show the withdrawal deadline and the return deadline separately,
  each labelled with the terms that apply to it. A 30-day return window counted
  from `purchased` can end before a 14-day withdrawal period counted from the
  last possession, and a return window that ends later can carry fees or
  resolutions the statutory right does not allow.
- **MUST NOT** apply return-policy fees to a statutory withdrawal (see
  [Refund](#refund)).

## Presenting the right

Withdrawal information is usually required before the order is placed. When a
business is required to show it, it emits a `messages[]` warning with
`presentation: "disclosure"` and `code` equal to
`dev.ucp.shopping.policy.withdrawal`, as defined in
[Presenting policies](../../overview/index.md#presenting-policies): one for the
response-wide terms and one per item-scoped exception. The disclosure content
states the conditions, the time limit, and the procedure for withdrawing,
including the existence and placement of the withdrawal function.

A platform that shows a short summary, such as an agent conversation, **MUST**
include those elements in the summary itself before the buyer places the order:
links alone are not enough. The model form **MAY** be supplied through
`model_form_url` instead.

On an order, a platform **SHOULD** show the resolved `expires_at`, and a control
leading to `withdrawal_function.url` labelled as described above, for as long
as the period runs.

### Business-supplied text

`description`, every `display_text`, `legal_reference`, and the labels are
written by the Business:

- Each string is plain text. It has no markup and no links; URLs go in the
  `format: uri` fields. The schema bounds each string's length.
- A platform **MUST** treat the strings as data from the Business and **MUST
  NOT** follow instructions found in them.
- A platform **MUST** present the meaning the law requires. It **MAY** adapt the
  layout or the channel, such as voice or a small screen, but **MUST NOT** change
  the substance: periods, start events, amounts, conditions, and the party that
  bears a cost.
- Where the law prescribes the wording, a platform uses the Business-supplied
  wording for the buyer's language. For this extension that is the `withdraw`
  label (see above).
- The language of each string follows the response language rules; the labels
  carry their own `language` tag.
- A platform that cannot present a required withdrawal disclosure **MUST NOT**
  present the right, or its absence, in its own words. It hands off through
  `continue_url`.

Every URL in this extension a buyer may open (`url`, `instructions_url`,
`model_form_url`, `withdrawal_function.url`, `extension.url`) is `https`, and
the schema requires it; for the base policy `url` this type narrows the core
field. A platform **MUST NOT** fetch such a URL server-side at all, including
for link previews or unfurling. It only hands the URL to the buyer's own
client, for example as a link the buyer opens.

`description` is also narrowed for this type: it carries a bounded `plain`
text, and the `html` and `markdown` formats are not allowed.

### Trust

The basis, availability, exceptions, period, deadline, costs, and refund terms
are statements by the Business. The Business is responsible for their accuracy
under the governing law. A platform presents them as the Business's statements
and is not required to verify them. Signed or attested statements are out of
scope; see the
[Verifiable Attestations proposal](https://github.com/Universal-Commerce-Protocol/ucp/pull/1020)
for verified claims.

`applies_to` is the core JSONPath targeting of `policies[]`, used the same way
by the return policy. A platform scopes an item-scoped withdrawal policy only to
the nodes it names in the same response and **SHOULD** flag, rather than
present, a policy whose target does not resolve to a line or product in that
response.

## Targeting and precedence

Targeting and precedence are provided by the `policies[]` primitive and are not
redefined here. A withdrawal policy with no `applies_to` is the response-wide
default; an item-scoped withdrawal policy overrides it for the items it
governs, with the narrowest same-type target winning. See
[Targeting](../../overview/index.md#targeting) and
[Precedence](../../overview/index.md#precedence). An override inherits none of
the default's terms, so a business **MUST** restate in the override every term
that still applies.

## Order snapshot and resolved deadline

On an order, `policies` record the terms that applied at checkout (see
[Order](../order/index.md#policies)). The terms of a withdrawal policy are that
snapshot and **MUST NOT** change after the order is placed: `basis`,
`availability`, `period.duration`, `period.anchor`, `period.display_text`,
`extension` terms, `return_costs`, `return_methods`, `refund`, and the links. `period.expires_at`
(and `extension.period.expires_at`) is a fact the Business adds once the anchor
event has occurred and updates, with `revised_at`, when the legal deadline
changes (see [Period and anchor](#period-and-anchor)), as the return policy
resolves its own `expires_at`. Adding or updating it does not change the
terms. A business
**MAY** split the policy into per-line copies with `applies_to` to state a
deadline per line, each copy carrying the checkout terms unchanged.

The contract confirmation on a durable medium, which the governing law usually
requires and which repeats the withdrawal information, is sent by the
Business. A policy, its URLs, or a UCP response do not fulfil that duty.

## Return shipments

After the buyer withdraws, or asks for a commercial return, the Business can
set up the return of the goods and issue a return label, a return code for a
specific network, or both. That is per order and per return, so it is on the
order in `return_shipments`, not in the policy. Each entry names the `method`
(a `return_methods` type), the `network` and, when the code works at one point
only, that `point`; the `line_items` and quantities that go back; the `label`
and the `return_code`; the time it was issued; and `return_by`, the time by
which the buyer must send the goods back. `policy_type` says whether the
return proceeds under the withdrawal policy or the return policy.

### Return code and label

`return_code` follows the displayable code of the payment render artifact
proposal ([#778](https://github.com/Universal-Commerce-Protocol/ucp/issues/778)):
an open `type` (`text`, `qr_code`, `barcode`), copyable `code` text, an inert
`image`, and `expires_at`. A platform renders the fields that are present: a
`qr_code` with only `code` is shown as text, and a platform **MUST NOT**
generate an image from `code`. When the network needs a scannable code, the
Business supplies `image`. `label.url` links to a label document (PDF or
image).

Unlike a payment artifact, a return code is not public. Whoever holds it can
drop a parcel into the network on the Business's account. Therefore:

- A platform **MUST** show `return_code` and `label.url` only to the buyer of
  that order, in the buyer's own session.
- A platform **MUST NOT** log or store `code`, `image` or `label.url` beyond
  what keeping the order record requires, and **MUST NOT** pass them to a
  third party, including when rendering.
- A platform **MUST NOT** fetch `label.url`, `tracking_url` or an HTTPS
  `image` server-side, including for previews; it hands them to the buyer's
  own client.
- An `image` is a raster image with the bounds of #778: `image/png`,
  `image/jpeg` or `image/webp`, at most 1 MiB decoded, and at most 4096
  pixels on either axis and 16 million pixels in total. The schema bounds the
  length of a `data:` URI; the platform checks the decoded size, the file
  signature and the dimensions. The buyer's client loads an HTTPS `image`
  without credentials or a referrer, does not follow redirects, applies a
  finite timeout, and accepts the response only if its media type is one of
  those three, its signature matches and it is within the bounds. An image
  that fails any check is not shown; the platform shows `code`, or
  `display_text` when there is no `code`. A valid image is shown as pixels
  only.
- `code` is data. A platform **MUST NOT** open, resolve or execute it, and
  **MUST NOT** follow instructions found in it or in `display_text`.
- The code is issued by the network or the Business, not designed by this
  extension. The Business **MUST** treat it as a secret bound to this return
  shipment, **SHOULD** use a single-use code bound to the shipment where the
  network supports it, and **MUST** be able to revoke a code and issue a new
  one, for example when the buyer reports it exposed.
- `label.url` **SHOULD** be unguessable and **SHOULD** stop working after a
  short time, and **MUST NOT** contain buyer data in the URL itself. The
  lifetime of that download link is not stated in the schema and is separate
  from `label.expires_at`, which is when the carrier stops accepting the
  label, even one already downloaded or printed. The label document holds personal data (the buyer's name and
  address, the return address and the tracking number) and opens this one
  label and nothing else.
- A Business **MUST NOT** put a credential to the buyer's account or to the
  network's systems in `code`, `image` or `label.url`.

### Withdrawal first, label second

Under EU law the withdrawal takes effect when the buyer sends the statement
within the period (CRD Art. 11(2), Art. 11a(5)). A return label or code is a
service for sending the goods back; it is not part of the withdrawal.

- A Business **MUST NOT** make the withdrawal, or its acknowledgement, depend
  on a label or code being issued, requested or used.
- `return_by` is the Business's statement of when the buyer must send the
  goods back. For a statutory withdrawal under EU law, the buyer sends them
  within 14 days from the day they communicated the withdrawal, and the
  deadline is met if they send them before it expires (Art. 14(1)). The 14
  days are counted under Regulation (EEC, Euratom) No 1182/71, as for the
  withdrawal period (see [Period and anchor](#period-and-anchor)): they start
  the day after the withdrawal was communicated, and a last day on a
  Saturday, Sunday or public holiday moves to the end of the next working
  day. A Business **MUST NOT** state a `return_by` earlier than that.
- `return_code.expires_at` and `label.expires_at` are about the network, not
  about the buyer's right. A code or label that expires before `return_by`
  does not shorten the buyer's time, and a platform **MUST NOT** tell the
  buyer that the time to send the goods back ends when the code expires.
- As a rule of this extension, not of the directive, a Business that issued a
  code or label for a return **SHOULD** issue a new one on request until
  `return_by`. The directive does not require a Business to issue a label or
  code at all.
- When `trader_collects` is the method, the buyer does not send the goods and
  the schema rejects `return_by`; `display_text` says how the collection is
  arranged.
- The deadline to send the goods back is met by sending them in time
  (Art. 14(1)); it does not depend on the label or code. A platform **MUST
  NOT** present a label or code as a condition of the withdrawal.

### Return events

Progress of a return uses the core
[Fulfillment Event](../order/index.md#fulfillment-event) log with two
well-known values of its open `type`:

- `return_dropped_off`: the buyer handed the parcel to the network, the
  carrier or the Business, as the Business reports it. Its `occurred_at` is
  the Business's own record. It is not by itself the buyer's evidence of
  having sent the goods back under Art. 13(3), which the Commission's
  guidance describes as, in principle, a written statement from an
  established transport or postal service provider naming the sender and the
  recipient. Once the Business records `return_dropped_off`, it has the
  information that the goods were sent and **SHOULD NOT** withhold the refund
  on the ground that it lacks proof of dispatch.
- `return_received`: the Business received the goods back.

Both carry `return_shipment_id`, the `return_shipments[].id` they belong to,
and the `line_items` that went back: the returned goods, not newly fulfilled
quantities. The core event describes `tracking_number` and `tracking_url` as
present on every event other than `processing`; on these two events they are
present only when a carrier or network carries the parcel, and an `in_store`
handover or a `trader_collects` collection without carrier tracking omits
them. They do not change `fulfilled`
quantities; the Business records the quantity taken back and the refund as a
`return` or `refund` [adjustment](../order/index.md#adjustments).

## Responsibilities

Withdrawal policies are business-stated facts. They are response-only data
(`ucp_request: omit` on cart, checkout, and order) that a platform never
submits. They carry no buyer data. `return_shipments` on the order is
response-only as well, but it does carry personal data of the buyer: the
drop-off `point`, the `tracking_number` and `tracking_url` of the buyer's
parcel, and the label, which names the buyer and their address. A Business
includes in it only what the buyer needs to return the goods, and a platform
keeps it only as long as the order record needs it, in line with the data
minimization principle of Regulation (EU) 2016/679, Art. 5(1)(c) ("adequate,
relevant and limited to what is necessary"). Its return code and label are
also bearer data, handled as [Return code and label](#return-code-and-label)
describes. A business **SHOULD** state the terms of the
law that governs the buyer's contract. Which law that is can depend on more
than the buyer's language or shipping address; the Business decides it, and
uses the request's `context` and addresses only as inputs.

When the Business has determined that no statutory right applies to a buyer,
for example a business buyer in a market where only consumers have the right,
it **SHOULD** state that with `availability.type: not_available` and an
`exception`, rather than omit the policy, because an omitted policy says
nothing. It states a `contractual` right only if it grants one. Who is
protected differs by market: some Member States extend the right to certain
sole traders.

A policy's `description` and its structured fields are two representations of
the same policy and **MUST** agree. The `description` **MAY** add detail, but
**MUST NOT** state a different period, start event, cost, return method, or
refund term.

## EU consumer contracts

For a distance contract with a consumer governed by the law of an EU Member
State, Directive 2011/83/EU (Consumer Rights Directive) sets the right.
Directive (EU) 2023/2673 adds the online withdrawal function (Art. 11a). Member
States had to adopt and publish their rules by 2025-12-19 and apply them from
2026-06-19; where a Member State transposes late, its national law decides. A
business in that case typically states:

| Field | Value | Source |
| :-- | :-- | :-- |
| `basis` | `statutory` | Art. 9(1) |
| `period.duration` | `P14D` | Art. 9(1) |
| `period.anchor` | `possession`, `possession_last_item`, `possession_first_item` for goods; `contract_concluded` for services and digital content not on a tangible medium | Art. 9(2) |
| `period.expires_at` | The period starts the day after the anchor event; if its last day is a Saturday, Sunday, or public holiday, it ends at the end of the next working day. If the withdrawal information was not given, it ends 12 months after the end of the initial period. If the information is given within 12 months from the anchor day (the day referred to in Art. 9(2), the start of the original period), it ends 14 days after the day the consumer receives it. | Recital 41 and Regulation (EEC, Euratom) No 1182/71 Art. 3(1), 3(4); Art. 10 |
| `availability.exception.code` | `eu.crd.art16.a` to `eu.crd.art16.m` | Art. 16, Art. 6(1)(k) |
| `return_costs` | `buyer` only if the consumer was told; a cost for goods that cannot normally be returned by post | Art. 6(1)(i), Art. 14(1) |
| `refund.deadline` | `P14D`: without undue delay and in any event within 14 days, with the same means of payment unless the consumer expressly agrees otherwise, at no fee | Art. 13(1) |
| `return_methods` | The procedure for sending the goods back; `trader_collects` when the trader offers to collect them, with its cost | Art. 6(1)(h), Art. 13(3), Art. 14(1) |
| `refund.withholding` | `until_goods_or_proof_of_dispatch` for goods, unless the trader offered to collect them at its expense; never for a return the buyer has the trader collect | Art. 13(3); Commission guidance 2021/C 525/01, 5.5.3 |
| `refund.delivery` | `up_to_least_expensive_standard` | Art. 13(1), 13(2) |
| `instructions_url`, `model_form_url` | The withdrawal information and the Annex I(B) model form | Art. 6(1)(h), Annex I |
| `withdrawal_function` | The function, labelled "withdraw from contract here" or an unambiguous corresponding formulation in the contract language | Art. 11a(1), Art. 6(1)(h) |
| `return_shipments[].return_by` | At least 14 days from the day the consumer communicated the withdrawal, counted under Reg. 1182/71; sending before it is in time | Art. 14(1), Recital 41 |

The consumer sends the goods back within 14 days of communicating the
withdrawal, unless the trader offered to collect them (Art. 14(1)); the
instructions state this. For digital content not on a tangible medium, the
Art. 16(m) exception applies only once performance has begun. Where the
contract obliges the consumer to pay, it also needs the consumer's prior
express consent, the acknowledgement that the right is lost, and the trader's
confirmation under Art. 8(7). A `conditional` exception states those conditions
in `display_text`, and a platform **MUST NOT** present the right as lost before
the Business says performance has begun.

For services, the instructions and the pre-order disclosure also state that a
consumer who expressly asks for the service to start during the withdrawal
period and then withdraws pays an amount in proportion to what was provided
(Art. 6(1)(j), Art. 14(3)). That payment is owed only if the trader gave the
Art. 6(1)(h) and (j) information and the consumer made the express request;
otherwise the consumer pays nothing for performance during the period
(Art. 14(4)(a)). Collecting that request at checkout is not covered by this
extension.

On a medium with limited space or time, the conditions, time limit, and
procedure for withdrawal are given on that medium before the contract; the
model form may be given another way (Art. 8(4); Court of Justice, Case C-430/17). That
is the reason for the short-summary rule in
[Presenting the right](#presenting-the-right).

Presenting a statutory right as a distinctive feature of the offer is an unfair
commercial practice in all circumstances under Directive 2005/29/EC, Annex I,
point 10; that is the reason for the `basis` rule. Label wording differs per
language and per national transposition, so labels are Business-supplied data,
not fixed values.

## Examples

### Checkout with the statutory default

A response-wide policy states the statutory right for a goods order. The buyer
pays return costs, the refund can wait for the goods, and delivery is refunded
up to the least expensive standard option. The function's `url` is the account
page, not a per-order link:

<!-- ucp:example schema=shopping/policy_withdrawal def=withdrawal_policy -->
```json
{
  "type": "dev.ucp.shopping.policy.withdrawal",
  "description": {
    "plain": "You can withdraw from this contract within 14 days without giving a reason. The period starts the day after you, or someone you name other than the carrier, receive the last item of your order. Withdraw online from your account, by the model form, or by any clear statement to us. You pay the cost of returning the goods. We refund your payments, including delivery up to our least expensive standard delivery, within 14 days, and may wait until we receive the goods or proof you sent them."
  },
  "basis": "statutory",
  "legal_reference": "Directive 2011/83/EU, Art. 9-16",
  "availability": { "type": "available" },
  "period": {
    "duration": "P14D",
    "anchor": "possession_last_item",
    "display_text": "14 days from the day after you receive the last item of your order"
  },
  "return_costs": {
    "payer": "buyer",
    "display_text": "You pay the cost of returning the goods."
  },
  "refund": {
    "deadline": "P14D",
    "withholding": "until_goods_or_proof_of_dispatch",
    "delivery": "up_to_least_expensive_standard"
  },
  "instructions_url": "https://example.com/withdrawal",
  "model_form_url": "https://example.com/withdrawal/model-form.pdf",
  "withdrawal_function": {
    "url": "https://example.com/account/withdraw",
    "labels": [
      { "language": "en", "contract_language": true, "withdraw": "Withdraw from contract here", "confirm": "Confirm withdrawal" }
    ]
  },
  "url": "https://example.com/withdrawal"
}
```

The paired disclosure that compels display of the terms before the order:

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "dev.ucp.shopping.policy.withdrawal",
    "presentation": "disclosure",
    "content": "You can withdraw within 14 days from the day after you receive the last item, without giving a reason. Withdraw online with 'Withdraw from contract here' in your account, with the model form, or by any clear statement. You pay the return cost."
  }
]
```

### Item with no withdrawal right

An item-scoped policy states that a made-to-measure item (line 1) has no
withdrawal right. It governs that line under same-type precedence; the other
lines keep the default:

<!-- ucp:example schema=shopping/policy_withdrawal def=withdrawal_policy -->
```json
{
  "type": "dev.ucp.shopping.policy.withdrawal",
  "description": { "plain": "This item is made to your measurements, so there is no right of withdrawal." },
  "applies_to": ["$.line_items[1]"],
  "basis": "statutory",
  "availability": {
    "type": "not_available",
    "exception": {
      "code": "eu.crd.art16.c",
      "display_text": "This item is made to your measurements, so there is no right of withdrawal."
    }
  }
}
```

The paired disclosure for the exception:

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "dev.ucp.shopping.policy.withdrawal",
    "path": "$.line_items[1]",
    "presentation": "disclosure",
    "content": "This item is made to your measurements, so there is no right of withdrawal."
  }
]
```

### Item that can lose the right

A sealed hygiene product keeps the right until the buyer unseals it after
delivery. The override restates the terms that still apply, with the same
contract-wide start as the default:

<!-- ucp:example schema=shopping/policy_withdrawal def=withdrawal_policy -->
```json
{
  "type": "dev.ucp.shopping.policy.withdrawal",
  "description": { "plain": "You can withdraw within 14 days from the day after you receive the last item of your order, unless you unseal this item after delivery." },
  "applies_to": ["$.line_items[2]"],
  "basis": "statutory",
  "availability": {
    "type": "conditional",
    "exception": {
      "code": "eu.crd.art16.e",
      "display_text": "You lose the right to withdraw once you unseal this item after delivery."
    }
  },
  "period": {
    "duration": "P14D",
    "anchor": "possession_last_item",
    "display_text": "14 days from the day after you receive the last item of your order"
  },
  "return_costs": { "payer": "buyer" },
  "refund": {
    "deadline": "P14D",
    "withholding": "until_goods_or_proof_of_dispatch",
    "delivery": "up_to_least_expensive_standard"
  },
  "model_form_url": "https://example.com/withdrawal/model-form.pdf",
  "withdrawal_function": {
    "url": "https://example.com/account/withdraw",
    "labels": [
      { "language": "en", "contract_language": true, "withdraw": "Withdraw from contract here" }
    ]
  }
}
```

### Statutory right with a longer contractual period

The Business gives 30 days from delivery on top of the 14 legal days. The
policy's fields state the statutory terms; `extension` states the longer
period and its own terms. A bulky item is returned at a maximum cost per
return:

<!-- ucp:example schema=shopping/policy_withdrawal def=withdrawal_policy -->
```json
{
  "type": "dev.ucp.shopping.policy.withdrawal",
  "description": { "plain": "14-day legal withdrawal right from the day after delivery, extended by us to 30 days. Returning the sofa costs at most EUR 60." },
  "basis": "statutory",
  "availability": { "type": "available" },
  "period": { "duration": "P14D", "anchor": "possession" },
  "extension": {
    "period": { "duration": "P30D", "anchor": "possession" },
    "display_text": "We extend your withdrawal period to 30 days from the day after delivery. After the 14 legal days, refunds are store credit."
  },
  "return_costs": {
    "payer": "buyer",
    "cost": { "amount": 6000, "currency": "EUR" },
    "cost_type": "maximum",
    "cost_unit": "per_return"
  },
  "refund": { "deadline": "P14D", "withholding": "until_goods_or_proof_of_dispatch", "delivery": "up_to_least_expensive_standard" },
  "withdrawal_function": {
    "url": "https://example.com/account/withdraw",
    "labels": [{ "language": "en", "contract_language": true, "withdraw": "Withdraw from contract here" }]
  }
}
```

### Contractual cooling-off period

A business in a market without a statutory right grants a 7-day cancellation
period from delivery and pays return shipping:

<!-- ucp:example schema=shopping/policy_withdrawal def=withdrawal_policy -->
```json
{
  "type": "dev.ucp.shopping.policy.withdrawal",
  "description": { "plain": "Cancel within 7 days of delivery for a full refund. We pay return shipping." },
  "basis": "contractual",
  "availability": { "type": "available" },
  "period": { "duration": "P7D", "anchor": "possession" },
  "return_costs": { "payer": "business" },
  "withdrawal_function": {
    "url": "https://example.com/account/cancel",
    "labels": [{ "language": "en", "contract_language": true, "withdraw": "Cancel your order here" }]
  }
}
```

### Order after collection from a parcel locker

The contract is governed by German law. The order was delivered to a parcel
locker and collected on Tuesday 2027-03-02. The period started the day after
collection, not on the day the carrier deposited the parcel. The last day,
2027-03-16, is a Tuesday and, for this example, assumed not to be a public
holiday, so the period ends at the end of that day.
The Business states the instant in the time zone it applies under the governing
law, here Central European Time (UTC+1). The checkout terms are unchanged; only
`expires_at` is added:

<!-- ucp:example schema=shopping/policy_withdrawal def=dev.ucp.shopping.order -->
```json
{
  "ucp": {...},
  "id": "order_abc123",
  "checkout_id": "checkout_xyz789",
  "permalink_url": "https://example.com/orders/abc123",
  "currency": "EUR",
  "line_items": [
    {
      "id": "li_kettle",
      "item": { "id": "prod_kettle", "title": "Electric Kettle", "price": 4900 },
      "quantity": { "original": 1, "total": 1, "fulfilled": 1 },
      "totals": [...],
      "status": "fulfilled"
    }
  ],
  "fulfillment": {...},
  "totals": [...],
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.withdrawal",
      "description": { "plain": "You can withdraw within 14 days from the day after you receive the last item of your order. You pay the cost of returning the goods." },
      "basis": "statutory",
      "availability": { "type": "available" },
      "period": {
        "duration": "P14D",
        "anchor": "possession_last_item",
        "display_text": "14 days from the day after you receive the last item of your order",
        "expires_at": "2027-03-16T22:59:59Z"
      },
      "return_costs": { "payer": "buyer" },
      "refund": {
        "deadline": "P14D",
        "withholding": "until_goods_or_proof_of_dispatch",
        "delivery": "up_to_least_expensive_standard"
      },
      "model_form_url": "https://example.com/withdrawal/model-form.pdf",
      "withdrawal_function": {
        "url": "https://example.com/account/withdraw",
        "labels": [
          { "language": "en", "contract_language": true, "withdraw": "Withdraw from contract here", "confirm": "Confirm withdrawal" }
        ]
      }
    }
  ]
}
```

### Return methods: locker with a code, collection, and post

A Business in Poland offers three ways to send the goods back after a
withdrawal. A return through InPost lockers is free and uses a return code,
so no printer is needed. The Business also offers to collect the goods for a
fee. Because the buyer pays for that collection, the policy still states
withholding for returns by the other methods, but the Business does not
withhold the refund for a return it collects. The buyer can also post the
goods at their own cost, and may need a printer for their own carrier's
label:

<!-- ucp:example schema=shopping/policy_withdrawal def=withdrawal_policy -->
```json
{
  "type": "dev.ucp.shopping.policy.withdrawal",
  "description": {
    "plain": "You can withdraw within 14 days from the day after you receive the last item of your order. Return the goods free at an InPost locker with the code we email you, have us collect them for PLN 49, or post them at your own cost. We refund your payments within 14 days of your withdrawal; for a locker or postal return we may wait until we receive the goods or proof you sent them, and for a return we collect we do not wait."
  },
  "basis": "statutory",
  "availability": { "type": "available" },
  "period": {
    "duration": "P14D",
    "anchor": "possession_last_item",
    "display_text": "14 days from the day after you receive the last item of your order"
  },
  "return_costs": {
    "payer": "buyer",
    "display_text": "You pay the cost of posting the goods back."
  },
  "return_methods": [
    {
      "type": "carrier_point",
      "network": "eu.inpost",
      "artifacts": ["code"],
      "printer_required": false,
      "return_costs": { "payer": "business" },
      "display_text": "Free return at any InPost locker in Poland. We email you a return code to type on the locker screen; no printer needed."
    },
    {
      "type": "trader_collects",
      "return_costs": {
        "payer": "buyer",
        "cost": { "amount": 4900, "currency": "PLN" },
        "cost_type": "exact",
        "cost_unit": "per_return"
      },
      "display_text": "We collect the goods from your address for PLN 49."
    },
    {
      "type": "postal",
      "printer_required": true,
      "display_text": "Post the goods to the return address in the instructions, with any carrier."
    }
  ],
  "refund": {
    "deadline": "P14D",
    "withholding": "until_goods_or_proof_of_dispatch",
    "delivery": "up_to_least_expensive_standard"
  },
  "instructions_url": "https://example.com/withdrawal",
  "model_form_url": "https://example.com/withdrawal/model-form.pdf",
  "withdrawal_function": {
    "url": "https://example.com/account/withdraw",
    "labels": [
      { "language": "pl", "contract_language": true, "withdraw": "Odstąp od umowy tutaj", "confirm": "Potwierdź odstąpienie" },
      { "language": "en", "withdraw": "Withdraw from contract here", "confirm": "Confirm withdrawal" }
    ]
  }
}
```

### Order with a locker return code and a return label

The buyer withdrew from the whole order on Friday 2027-03-05. The Business
sent the acknowledgement the same day and then set up two returns. The kettle
goes back through an InPost locker with a fictional 10-digit return code,
which the buyer writes on the box. The code is valid for 72 hours, but the
buyer's 14 days to send the goods start on 2027-03-06 and end on Friday
2027-03-19, a working day, so the Business issues a new code on request until
then. The lamp goes back by post with a Poczta Polska label. The buyer
dropped the kettle off on 2027-03-07:

<!-- ucp:example schema=shopping/policy_withdrawal def=dev.ucp.shopping.order -->
```json
{
  "ucp": {...},
  "id": "order_pl_5521",
  "checkout_id": "checkout_pl_5521",
  "permalink_url": "https://example.com/orders/5521",
  "currency": "PLN",
  "line_items": [
    {
      "id": "li_kettle",
      "item": { "id": "prod_kettle", "title": "Electric Kettle", "price": 19900 },
      "quantity": { "original": 1, "total": 1, "fulfilled": 1 },
      "totals": [...],
      "status": "fulfilled"
    },
    {
      "id": "li_lamp",
      "item": { "id": "prod_lamp", "title": "Desk Lamp", "price": 14900 },
      "quantity": { "original": 1, "total": 1, "fulfilled": 1 },
      "totals": [...],
      "status": "fulfilled"
    }
  ],
  "fulfillment": {
    "expectations": [...],
    "events": [
      {
        "id": "evt_delivered",
        "occurred_at": "2027-03-01T10:12:00Z",
        "type": "delivered",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }, { "id": "li_lamp", "quantity": 1 }],
        "tracking_number": "620000123456789",
        "tracking_url": "https://example.com/track/620000123456789"
      },
      {
        "id": "evt_return_kettle_dropped",
        "occurred_at": "2027-03-07T11:20:00Z",
        "type": "return_dropped_off",
        "return_shipment_id": "ret_kettle",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "tracking_number": "RT6200009876543",
        "tracking_url": "https://example.com/returns/ret_kettle/track"
      }
    ]
  },
  "totals": [...],
  "policies": [...],
  "return_shipments": [
    {
      "id": "ret_kettle",
      "policy_type": "dev.ucp.shopping.policy.withdrawal",
      "method": "carrier_point",
      "network": "eu.inpost",
      "line_items": [{ "id": "li_kettle", "quantity": 1 }],
      "return_code": {
        "type": "text",
        "code": "6081937254",
        "expires_at": "2027-03-08T14:03:00Z"
      },
      "issued_at": "2027-03-05T14:03:00Z",
      "return_by": "2027-03-19T22:59:59Z",
      "tracking_number": "RT6200009876543",
      "tracking_url": "https://example.com/returns/ret_kettle/track",
      "display_text": "Write the code on the box and remove the old label. At any InPost locker in Poland choose to send a parcel and type the code. The code is valid for 72 hours; ask us for a new one if it expires. You have until 19 March to send the kettle."
    },
    {
      "id": "ret_lamp",
      "policy_type": "dev.ucp.shopping.policy.withdrawal",
      "method": "postal",
      "network": "pl.poczta-polska",
      "line_items": [{ "id": "li_lamp", "quantity": 1 }],
      "label": {
        "url": "https://example.com/returns/ret_lamp/label.pdf",
        "media_type": "application/pdf"
      },
      "issued_at": "2027-03-05T14:03:00Z",
      "return_by": "2027-03-19T22:59:59Z",
      "display_text": "Print the label, stick it on the parcel and post it at any Poczta Polska office."
    }
  ]
}
```
