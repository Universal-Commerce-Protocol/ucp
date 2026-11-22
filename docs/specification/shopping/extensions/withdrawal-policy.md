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
- Refund terms: deadline, withholding, and which delivery payments are
  refunded (`refund`)
- Links to the instructions and the model withdrawal form
  (`instructions_url`, `model_form_url`)
- Where the online withdrawal function is and how its controls are labelled
  in each language (`withdrawal_function`)

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

### Withdrawal Refund

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_refund', 'shopping/extensions/withdrawal-policy') }}

### Withdrawal Function

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_function', 'shopping/extensions/withdrawal-policy') }}

### Withdrawal Function Label

Each entry in `withdrawal_function.labels` uses this shape.

{{ extension_schema_fields('policy_withdrawal.json#/$defs/withdrawal_function_label', 'shopping/extensions/withdrawal-policy') }}

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
  authenticated session or an unguessable token, and verifies the buyer when
  the link is opened outside a session.
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
  Business will send the acknowledgement. A buyer who is logged in should not
  need to identify themselves or the contract again. Questions such as the reason
  for withdrawing are separate and optional.
- The buyer submits the statement through a separate confirmation control,
  labelled with the wording the governing law prescribes. `confirm` states that
  label for information; when it is omitted, a platform does not render a
  confirmation control or derive a label of its own.
- After submission, the Business sends, without undue delay and on a durable
  medium, an acknowledgement of receipt that states the content of the
  statement and the date and time it was submitted. The Business sends it
  itself; a UCP response to the platform is not that acknowledgement.

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
`extension` terms, `return_costs`, `refund`, and the links. `period.expires_at`
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

## Responsibilities

Withdrawal policies are business-stated facts. They are response-only data
(`ucp_request: omit` on cart, checkout, and order) that a platform never
submits. They carry no buyer data. A business **SHOULD** state the terms of the
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
**MUST NOT** state a different period, start event, cost, or refund term.

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
| `refund.withholding` | `until_goods_or_proof_of_dispatch` for goods, unless the trader offered to collect them | Art. 13(3) |
| `refund.delivery` | `up_to_least_expensive_standard` | Art. 13(1), 13(2) |
| `instructions_url`, `model_form_url` | The withdrawal information and the Annex I(B) model form | Art. 6(1)(h), Annex I |
| `withdrawal_function` | The function, labelled "withdraw from contract here" or an unambiguous corresponding formulation in the contract language | Art. 11a(1), Art. 6(1)(h) |

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
