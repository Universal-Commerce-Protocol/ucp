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

<!-- cspell:ignore titres -->

# Restricted Tender Programs

!!! note "Prototype"
    This page is a prototype for Enhancement Proposal
    [#1143](https://github.com/Universal-Commerce-Protocol/ucp/issues/1143).
    The proposal has not been accepted by the Tech Council. Field names and
    rules may change.

## Overview

Some payment instruments may pay only for some items. US SNAP benefits on an
EBT card pay only for eligible food: not hot prepared food, not household goods,
not delivery or service fees, not tips. Health savings and flexible spending
cards, meal-voucher cards and similar tenders follow the same pattern.

A checkout that accepts such a tender needs three things:

1. A way to say which **program** an instrument draws on.
2. A mark on each **line item** saying which programs may pay for it.
3. A **cap** on what instruments of a program may contribute, so the rest of
   the order goes to another instrument.

UCP carries all three with optional fields. The business decides which items
qualify and computes the cap; the platform shows the result and submits the
instruments. No PIN, and nothing from which a PIN could be derived, ever passes
through a UCP payload.

## Program Codes

A program code is the lowercase ISO 3166-1 alpha-2 code of the jurisdiction
whose law or rules define the program, an underscore, and a lowercase slug
naming the scheme: `us_snap`. The slug names the scheme, not an issuer or a
brand. One issuer brand can operate under several national schemes, and one
scheme can have many issuers.

{{ schema_fields('types/tender_program', 'payment/tender-programs') }}

### Registry

| Code          | Jurisdiction | Item-restricted | Governing rules                                                                                                                |
| :------------ | :----------- | :-------------- | :----------------------------------------------------------------------------------------------------------------------------- |
| `us_snap`     | US           | Yes             | SNAP food benefits paid from an EBT card; eligible foods per [7 CFR 271.2](https://www.ecfr.gov/current/title-7/section-271.2) |
| `us_ebt_cash` | US           | No              | Cash benefits paid from the same EBT card                                                                                      |

New programs are added to this table by pull request, with no schema change.

**Tolerance.** Platforms **MUST** carry codes they do not recognize in
`tender_eligibility` and `eligible_amounts` unchanged. A business **MUST**
reject an instrument whose `program` it does not accept, with `payment_failed`
and `path` pointing at the instrument.

## Schema

### Program on Payment Instruments

Every payment instrument may carry an optional `program`. It is present on
instruments that draw on a tender program and absent on ordinary instruments.
Instruments that run on card networks (most health savings, flexible spending
and meal-voucher cards) use `type: "card"` with a `program`.

An instrument is **restricted** when its `program` is listed in
`payment.eligible_amounts`. Restriction is signalled in the payload itself, so a
platform can apply the cap to a program code it has never seen.

### Benefit Card Instrument

For benefit cards that run outside the card networks and need a step hosted by
the payment handler, such as PIN entry for a US EBT card.

{{ schema_fields('types/benefit_card_payment_instrument', 'payment/tender-programs') }}

One physical EBT card that carries both food and cash benefits appears as two
instruments with the same `handler_id`: one with `program: "us_snap"` and one
with `program: "us_ebt_cash"`.

The `credential` is whatever the handler returns after the buyer enters the PIN
in the handler's own secure field (for example, a single-use token).

### Line Item Eligibility

Line items carry an optional, business-set `tender_eligibility` list of the
item-restricted programs that may pay for the line. It is omitted from requests:
platforms **MUST NOT** set or change it. Absence means no item-restricted
program may pay for the line.

### Eligible Amounts

`payment.eligible_amounts` lists, per item-restricted program, the most that
instruments of that program may contribute. It is response-only.

{{ schema_fields('types/eligible_amount', 'payment/tender-programs') }}

The business computes these amounts, not the platform, because discounts,
deposits and tax rules vary by merchant and jurisdiction.

## Requirements

### Business

* A business that accepts an item-restricted program **MUST** list it in
  `payment.eligible_amounts` on every checkout response, with `amount: 0` when
  no line qualifies.
* Programs that are not item-restricted (such as `us_ebt_cash`) **MUST NOT** be
  listed in `eligible_amounts`.
* `tender_eligibility` and `eligible_amounts` **MUST** reflect the business's
  own split of eligible and ineligible items, the same split it makes before
  charging the program.
* When a restricted instrument pays for items that would otherwise be taxed,
  the business **MUST** recompute tax once the split is known, where the
  program's rules require it (US SNAP purchases are exempt from state and local
  sales tax).
* When more than one instrument is submitted, the cap is enforced by the
  [Split Payments](extensions/split-payments.md#restricted-instruments) rule.
  When a restricted instrument is the only instrument, the business **MUST**
  reject the payment with `payment_failed` if the eligible amount does not
  cover the checkout total.

### Platform

* A platform **MUST NOT** submit a restricted instrument with a specified
  `amount` above its program's eligible amount.
* A platform **SHOULD** show the buyer the eligible amount before completion,
  and which items will be paid by another instrument.
* A platform or agent **MUST NOT** collect, store or relay a benefit card PIN.
* A platform **MUST NOT** use an instrument's `program` for anything other than
  completing the payment: not for profiling, advertising or ranking.

## Advertising Accepted Programs

A business advertises which programs a handler accepts with
`ucp.request_constraints`, because `program` is a field the platform submits:

<!-- ucp:example schema=payment_handler def=business_schema -->
```json
{
  "id": "ebt_tpp",
  "version": "{{ ucp_version }}",
  "spec": "https://example.com/ucp/ebt-handler",
  "schema": "https://example.com/ucp/ebt-handler/schema.json",
  "available_instruments": [
    {
      "type": "benefit_card",
      "ucp": {
        "request_constraints": {
          "path": "$['payment']['instruments'][?@['handler_id'] == 'ebt_tpp' && @['type'] == 'benefit_card']",
          "required": ["program", "credential"],
          "properties": {
            "program": { "enum": ["us_snap", "us_ebt_cash"] }
          }
        }
      }
    }
  ]
}
```

EBT PIN entry and routing stay with approved third-party processors, published
as payment handlers under their own namespaces. This page defines no handler.

## Security and Privacy

* **PIN.** The schema has no PIN field. The buyer types the PIN into the
  handler's secure field, and the handler returns an opaque credential.
* **Benefit status is sensitive.** An instrument whose `program` names a public
  benefit reveals that the household receives it. Display data is limited to
  the last four digits and the issuing region, and the platform's use of
  `program` is limited as stated above.
* **Wrong eligibility marks.** `tender_eligibility` is set only by the business
  and repeats the split it already makes before charging the program, so UCP
  adds no new source of truth for eligibility.

## Example: A SNAP Grocery Order

A delivery order: milk $4.29, bread $3.49 and apples $5.97 (all SNAP-eligible),
paper towels $8.99 and a hot rotisserie chicken $7.99 (not eligible), a $5.99
delivery fee, and $1.40 tax on the ineligible items.

**Checkout response.** The business marks the eligible lines and computes the
SNAP cap of $13.75:

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { "version": "{{ ucp_version }}", "status": "success", "payment_handlers": {} },
  "id": "chk_snap_1",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "milk-1gal", "title": "Milk, 1 gal", "price": 429 },
      "quantity": 1,
      "tender_eligibility": ["us_snap"],
      "totals": [
        { "type": "subtotal", "amount": 429 },
        { "type": "total", "amount": 429 }
      ]
    },
    {
      "id": "li_2",
      "item": { "id": "bread-ww", "title": "Whole wheat bread", "price": 349 },
      "quantity": 1,
      "tender_eligibility": ["us_snap"],
      "totals": [
        { "type": "subtotal", "amount": 349 },
        { "type": "total", "amount": 349 }
      ]
    },
    {
      "id": "li_3",
      "item": { "id": "apples-3lb", "title": "Apples, 3 lb", "price": 597 },
      "quantity": 1,
      "tender_eligibility": ["us_snap"],
      "totals": [
        { "type": "subtotal", "amount": 597 },
        { "type": "total", "amount": 597 }
      ]
    },
    {
      "id": "li_4",
      "item": { "id": "paper-towels-6", "title": "Paper towels, 6 rolls", "price": 899 },
      "quantity": 1,
      "totals": [
        { "type": "subtotal", "amount": 899 },
        { "type": "total", "amount": 899 }
      ]
    },
    {
      "id": "li_5",
      "item": { "id": "rotisserie-hot", "title": "Hot rotisserie chicken", "price": 799 },
      "quantity": 1,
      "totals": [
        { "type": "subtotal", "amount": 799 },
        { "type": "total", "amount": 799 }
      ]
    }
  ],
  "payment": {
    "eligible_amounts": [
      { "program": "us_snap", "amount": 1375 }
    ]
  },
  "totals": [
    { "type": "subtotal", "amount": 3073 },
    { "type": "fulfillment", "display_text": "Delivery", "amount": 599 },
    { "type": "tax", "amount": 140 },
    { "type": "total", "amount": 3812 }
  ],
  "links": []
}
```

**Complete request.** The platform submits the EBT SNAP instrument first, in
open-amount mode, and a card for the rest:

<!-- ucp:example schema=shopping/checkout op=complete direction=request extract=$.payment target=$.payment -->
```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_ebt",
        "handler_id": "ebt_tpp",
        "type": "benefit_card",
        "program": "us_snap",
        "display": { "last_digits": "4821", "issuer_region": "US-TX" },
        "credential": { "type": "ebt_pin_token", "token": "ebt_tok_7f3a" }
      },
      {
        "id": "pi_card",
        "handler_id": "card_psp",
        "type": "card",
        "credential": { "type": "card", "token": "tok_visa_xxxx" }
      }
    ]
  }
}
```

**Complete response.** The EBT instrument pays the $13.75 cap and the card pays
the remaining $24.37: the ineligible items, the delivery fee and the tax.

<!-- ucp:example schema=shopping/checkout extract=$.payment target=$.payment -->
```json
{
  "payment": {
    "eligible_amounts": [
      { "program": "us_snap", "amount": 1375 }
    ],
    "instruments": [
      {
        "id": "pi_ebt",
        "handler_id": "ebt_tpp",
        "type": "benefit_card",
        "program": "us_snap",
        "display": { "last_digits": "4821", "issuer_region": "US-TX" },
        "credential": { "type": "ebt_pin_token", "token": "ebt_tok_7f3a" },
        "amount": 1375
      },
      {
        "id": "pi_card",
        "handler_id": "card_psp",
        "type": "card",
        "credential": { "type": "card", "token": "tok_visa_xxxx" },
        "amount": 2437
      }
    ]
  }
}
```

If the SNAP balance were only $10.00, the EBT instrument would contribute
$10.00 and the card the rest. The $3.75 of food now paid by card may be taxable,
so the business recomputes tax and the card pays $28.12 plus that tax.

## A Second Program: France's Titres-Restaurant

The same fields carry a non-US program with no schema change:

* **Code:** `fr_titre_restaurant`, item-restricted, added to the registry by a
  later pull request.
* **Instrument:** `card` for network-branded cards, `benefit_card` otherwise,
  with `program: "fr_titre_restaurant"`.
* **Eligibility:** the business marks food lines; alcohol and non-food lines
  carry no mark.
* **Daily cap:** the 25-euro daily limit is held by the issuer and shows up as
  the instrument's available balance. The open-amount rule already caps a
  contribution at the lesser of balance and eligible amount.
