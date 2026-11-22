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
  (`period`)
- Who pays for returning goods, and how much (`return_costs`)
- Refund terms, including the delivery amount refunded (`refund`)
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
over its structured fields only when the body passes schema validation. A
platform that has not negotiated it still renders the policy from the base
`type` and `description`, because the withdrawal body is purely additive.

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
| `conditional` | The right covers the items but is lost when a condition occurs, for example unsealing a sealed hygiene product after delivery, or starting a download with the buyer's consent. |

A `not_available` or `conditional` availability **MUST** carry an `exception`
with `display_text`, the statement the buyer is shown: that there is no right,
or the circumstances in which it is lost. `code` identifies the exception in
the legal regime that defines it, namespaced by that regime (see
[EU consumer contracts](#eu-consumer-contracts) for the well-known codes).

Whether an exception applies to an item is the Business's determination.
A platform presents `display_text` as the Business's statement and **MUST NOT**
derive an exception from product data on its own. Because the period, costs,
refund, model form and withdrawal function do not apply to an item with no
right, a business **MUST NOT** carry them on a `not_available` policy; the
schema rejects the combination.

A business states the default terms once in a response-wide withdrawal policy
and adds an item-scoped policy for each excepted item, using `applies_to` and
same-type precedence (see [Targeting and precedence](#targeting-and-precedence)).

### Period and anchor

`period` states the length of the withdrawal period (`duration`) and the event
it is measured from (`anchor`), both required. Once the anchor event has
occurred, the business resolves the deadline and states it as `expires_at`.

`anchor` is an open vocabulary. The well-known values are:

| Anchor | The period starts when |
| :-- | :-- |
| `contract_concluded` | The order is placed. Used for services and for digital content not supplied on a tangible medium. |
| `possession` | The buyer, or a third party other than the carrier that the buyer indicated, acquires physical possession of the goods. |
| `possession_last_item` | The buyer acquires possession of the last item or lot of an order delivered in several shipments or lots. |
| `possession_first_item` | The buyer acquires possession of the first item, for a contract for regular delivery of goods. |

These anchors differ from the return policy's `delivered`. For goods sent to a
carrier pickup point or a parcel locker, possession is the buyer's collection,
not the carrier's deposit at the point. If the buyer never collects, the
anchor event has not occurred and `expires_at` is not stated. A business that
does not know at checkout whether an order ships in one shipment or several
**MAY** state `possession_last_item`.

A business **MUST NOT** state an `expires_at` earlier than the end of the period
its `duration` and `anchor` describe. Unlike a return window, `expires_at`
**MAY** move later after it is first stated: the governing law can extend the
period, for example when the Business did not give the required withdrawal
information. A platform **MUST** read `expires_at` from the latest response,
**MUST NOT** cache it as final, and **MUST NOT** tell the buyer the right has
expired from a date it computed itself. A withdrawal the buyer sends no later
than `expires_at` is in time, even if the Business processes it later.

A platform **MAY** present `expires_at` in any time zone and **MUST NOT**
present a later deadline, for example by showing only its date. Without
`expires_at`, it presents the terms, for example "14 days from the day you
collect the parcel".

### Return costs

`return_costs.payer` states who bears the direct cost of returning the goods.
When the buyer pays, `amount` with `amount_type` states the cost: `exact` for a
known cost, or `maximum` for a reasonable estimate of the highest cost, used for
goods that cannot normally be returned by post. When `return_costs` is omitted,
the terms are not stated structurally and a platform **MUST NOT** tell the buyer
that the buyer pays.

### Refund

`refund.deadline` states the longest time after the Business is informed of the
withdrawal within which it refunds. `refund.delivery_amount` states the
delivery cost the Business refunds when the buyer withdraws from the whole
order. Where the governing law limits that refund to the cheapest standard
delivery the Business offered, it is that price, not the price of a faster or
premium method the buyer chose. A business states it on a checkout from the
methods currently offered and records it on the order at placement, because
delivery prices change after checkout.

A business **MUST NOT** deduct a return-policy fee, such as
`dev.ucp.shopping.fee.restocking` or `dev.ucp.shopping.fee.handling`, from a
refund for a `statutory` withdrawal. A deduction the law allows for a reduced
value of the goods is assessed per item after the goods come back and is not a
flat fee. The return shipping cost under a withdrawal is the one
`return_costs` states, not a return-policy `dev.ucp.shopping.fee.return_shipping`.

### Instructions, model form, and withdrawal function

`instructions_url` links to the conditions, time limit, and procedure.
`model_form_url` links to the withdrawal form the buyer may use, where the
governing law provides one; it is in addition to the online function.

`withdrawal_function` describes the Business's online withdrawal function:

- `url` is the page where the buyer withdraws. A business **MUST** keep it
  reachable for the whole withdrawal period, without requiring the buyer to
  install an application they did not use to conclude the contract.
- `labels` gives the text of the function's two controls per language: the
  control that opens the withdrawal statement (`withdraw`) and the one that
  submits it (`confirm`). Labels are the Business's locale data. A platform that
  renders a control leading to `url` **MUST** use the `withdraw` label for the
  buyer's language verbatim, or the label of the language the Business uses for
  the contract when none matches.
- `statement_fields` states what the function asks the buyer to give or
  confirm. Any other question, such as the reason for withdrawing, is separate
  and optional for the buyer.
- `acknowledgement_channels` states how the Business sends the acknowledgement
  of receipt. The Business sends it itself, on a durable medium, with the
  content of the statement and the date and time it was submitted. A UCP
  response to the platform is not that acknowledgement.

This extension advertises the function; it does not define a UCP operation to
withdraw. A platform **MUST NOT** submit a withdrawal on the buyer's behalf
through the function without the buyer's explicit instruction.

## Withdrawal and return policies

The withdrawal and return policy types are independent. Precedence applies per
type, so a return policy never overrides a withdrawal policy, and the reverse.
A platform that models both:

- **MUST NOT** treat a return policy with `eligibility.type: not_accepted` as
  removing a withdrawal right. Only a withdrawal policy with
  `availability.type: not_available` states that there is none.
- **MUST** keep the withdrawal terms visible when it combines both into one
  presentation: the period and its start event, who pays for the return, the
  refund of delivery, and the link to the withdrawal function. A 30-day return
  window counted from `purchased` can end before a 14-day withdrawal period
  counted from the last possession; when the platform shows one deadline, it
  shows the later one, or both.
- **MUST NOT** apply return-policy fees to a withdrawal (see [Refund](#refund)).

A business that grants a voluntary right beyond the statutory one, such as a
longer period, states it in its return policy or in the withdrawal policy's
`description`. The `statutory` policy's structured fields state the legal
terms.

## Presenting the right

Withdrawal information is usually required before the order is placed. When a
business is required to show it, it emits a `messages[]` warning with
`presentation: "disclosure"` and `code` equal to
`dev.ucp.shopping.policy.withdrawal`, as defined in
[Presenting policies](../../overview/index.md#presenting-policies): one for the
response-wide terms and one per item-scoped exception. A platform that renders
a short summary, such as an agent conversation, still shows the existence of
the right in the summary before the buyer places the order, and links to
`instructions_url`, `model_form_url`, and `withdrawal_function.url`.

On an order, a platform **SHOULD** show the resolved `expires_at` and a control
leading to `withdrawal_function.url` labelled with the Business's `withdraw`
label for as long as the period runs.

## Targeting and precedence

Targeting and precedence are provided by the `policies[]` primitive and are not
redefined here. A withdrawal policy with no `applies_to` is the response-wide
default; an item-scoped withdrawal policy overrides it for the items it
governs, with the narrowest same-type target winning. See
[Targeting](../../overview/index.md#targeting) and
[Precedence](../../overview/index.md#precedence). An override inherits none of
the default's terms, so a business **MUST** restate in the override every term
that still applies.

## Responsibilities

Withdrawal policies are business-stated facts. They are response-only data
(`ucp_request: omit` on cart, checkout, and order) that a platform never
submits. They carry no buyer data. A business **SHOULD** localize them to the
buyer, using the buyer's `context` or shipping address, so the terms are those
of the law that governs that buyer's contract. A business that sells to buyers
for whom no withdrawal right applies, such as business buyers in a market where
only consumers have the right, omits the policy or states it as `contractual`.

A policy's `description` and its structured fields are two representations of
the same policy. A business **MUST NOT** let the `description` state terms worse
for the buyer than a structured field.

## EU consumer contracts

For a distance contract with a consumer governed by the law of an EU Member
State, Directive 2011/83/EU (Consumer Rights Directive) sets the right, and
Directive (EU) 2023/2673 adds the online withdrawal function, applicable from
2026-06-19 under national transposition. A business in that case typically
states:

| Field | Value | Source |
| :-- | :-- | :-- |
| `basis` | `statutory` | Art. 9(1) |
| `period.duration` | `P14D` | Art. 9(1) |
| `period.anchor` | `possession`, `possession_last_item`, `possession_first_item` for goods; `contract_concluded` for services and digital content | Art. 9(2) |
| `period.expires_at` | Can move later by up to 12 months if the withdrawal information was not given | Art. 10 |
| `availability.exception.code` | `eu.crd.art16.a` to `eu.crd.art16.m` | Art. 16, Art. 6(1)(k) |
| `return_costs` | `buyer` only if the consumer was told; an amount for goods that cannot be returned by post | Art. 6(1)(i), Art. 14(1) |
| `refund.deadline` | `P14D` | Art. 13(1) |
| `refund.delivery_amount` | Price of the cheapest standard delivery offered | Art. 13(2) |
| `instructions_url`, `model_form_url` | The withdrawal information and the Annex I(B) model form | Art. 6(1)(h), Annex I |
| `withdrawal_function` | The function, labelled "withdraw from contract here" and "confirm withdrawal" or an unambiguous equivalent in the contract language, with `name`, `contract_reference`, and `confirmation_channel` | Art. 11a, Art. 6(1)(h) |

Presenting a statutory right as a distinctive feature of the offer is an unfair
commercial practice in all circumstances under Directive 2005/29/EC, Annex I,
point 10; that is the reason for the `basis` rule. Labels and the transposition
date differ per Member State, so they are Business-supplied data, not fixed
values.

## Examples

### Checkout with the statutory default

A response-wide policy states the statutory right for a goods order. The buyer
pays return costs, delivery is refunded up to the cheapest standard option, and
the function is labelled in the contract language. A business that sells in
several languages adds one `labels` entry per language:

<!-- ucp:example schema=shopping/policy_withdrawal def=withdrawal_policy -->
```json
{
  "type": "dev.ucp.shopping.policy.withdrawal",
  "description": {
    "plain": "You can withdraw from this contract within 14 days without giving a reason. The period starts when you, or someone you name other than the carrier, receive the last item. You pay the cost of returning the goods. We refund your payment, including delivery up to the cost of our cheapest standard delivery, within 14 days."
  },
  "basis": "statutory",
  "legal_reference": "Directive 2011/83/EU, Art. 9-16",
  "availability": { "type": "available" },
  "period": { "duration": "P14D", "anchor": "possession_last_item" },
  "return_costs": {
    "payer": "buyer",
    "display_text": "You pay the cost of returning the goods."
  },
  "refund": { "deadline": "P14D", "delivery_amount": 999 },
  "instructions_url": "https://example.com/withdrawal",
  "model_form_url": "https://example.com/withdrawal/model-form.pdf",
  "withdrawal_function": {
    "url": "https://example.com/account/orders/withdraw",
    "labels": [
      { "language": "en", "withdraw": "Withdraw from contract here", "confirm": "Confirm withdrawal" }
    ],
    "statement_fields": ["name", "contract_reference", "confirmation_channel"],
    "acknowledgement_channels": ["email"]
  },
  "url": "https://example.com/withdrawal"
}
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

The paired disclosure that compels display of the exception before the order:

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

A sealed hygiene product keeps the right until the buyer unseals it. The
override restates the terms that still apply:

<!-- ucp:example schema=shopping/policy_withdrawal def=withdrawal_policy -->
```json
{
  "type": "dev.ucp.shopping.policy.withdrawal",
  "description": { "plain": "You can withdraw within 14 days of receiving this item unless you unseal it after delivery." },
  "applies_to": ["$.line_items[2]"],
  "basis": "statutory",
  "availability": {
    "type": "conditional",
    "exception": {
      "code": "eu.crd.art16.e",
      "display_text": "You lose the right to withdraw once you unseal this item after delivery."
    }
  },
  "period": { "duration": "P14D", "anchor": "possession_last_item" },
  "return_costs": { "payer": "buyer" },
  "refund": { "deadline": "P14D", "delivery_amount": 999 },
  "model_form_url": "https://example.com/withdrawal/model-form.pdf",
  "withdrawal_function": { "url": "https://example.com/account/orders/withdraw" }
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
  "withdrawal_function": { "url": "https://example.com/orders/cancel" }
}
```

### Order after collection from a parcel locker

The order was delivered to a parcel locker. The period started when the buyer
collected the parcel, not when the carrier deposited it, and the business
states the deadline. `delivery_amount` records the cheapest standard delivery
offered at checkout:

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
      "description": { "plain": "You can withdraw until 17 March 2026, 23:59 CET. You pay the cost of returning the goods." },
      "basis": "statutory",
      "availability": { "type": "available" },
      "period": {
        "duration": "P14D",
        "anchor": "possession_last_item",
        "expires_at": "2026-03-17T22:59:59Z"
      },
      "return_costs": { "payer": "buyer" },
      "refund": { "deadline": "P14D", "delivery_amount": 399 },
      "model_form_url": "https://example.com/withdrawal/model-form.pdf",
      "withdrawal_function": {
        "url": "https://example.com/account/orders/abc123/withdraw",
        "labels": [
          { "language": "en", "withdraw": "Withdraw from contract here", "confirm": "Confirm withdrawal" }
        ]
      }
    }
  ]
}
```
