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

# Item Inputs Extension

## Overview

Some products cannot be made until the buyer says something about them: the
text to engrave on a watch, the initials on a towel, the name on a shirt. The
Item Inputs extension lets a Business say what it needs to know, lets a
Platform send the buyer's answers with the line, and keeps those answers on the
resulting Order.

Without this extension a line item is a variant and a quantity. A Business that
sells a watch it can engrave cannot ask for the engraving in its catalog, a
Platform cannot send it, and a checkout for that watch is handed off to the
Business's website.

An **item input** is one question the Business asks about an item: an `id`, a
`label`, whether an answer is `required`, and the kind of answer it accepts.
The Business declares inputs on the variant. The Platform answers them on the
line by `id`. The Business checks every answer and is the only party that
decides whether it is acceptable.

This extension adds:

- `item_inputs[]` on a catalog variant and on a cart or checkout line — the
    questions the Business asks. Response-only.
- `item_input_values[]` on a cart or checkout line — the buyer's answers. A
    Platform writes them; the Business returns the ones it accepted.
- `item_input_values[]` on an Order line — the answers the Business accepted
    at checkout.
- Four error codes and one warning code for reporting problems with an answer.

**Dependencies:**

- One or more of the parent capabilities this extension extends: Catalog
  Search, Catalog Lookup, Cart, Checkout, or Order.

### Scope

An input describes how one line is to be made or prepared. The rest of this
specification keeps to that limit:

- An input never adds, removes, or changes other lines.
- An input never changes which payment handlers or capabilities are in effect.
- An answer never selects a different SKU or a different stock count. That is
  a variant option (see [Inputs and variant options](#inputs-and-variant-options)).
- A question about the order as a whole, such as delivery instructions, is not
  an item input.
- A value a store keeps for its own use is not an item input. An input is a
  question for the buyer.

## Discovery

Businesses advertise item inputs in their profile:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.item_inputs": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup",
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/item-inputs",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/item_inputs.json"
        }
      ]
    }
  }
}
```

Advertising this extension means the Business returns `item_inputs` for
variants that have them, accepts and validates `item_input_values` on cart and
checkout lines, and preserves accepted answers on the resulting Order line.

A Platform that advertises this extension **MUST** be able to collect an
answer for each of the five well-known input types.

## Schema

### Item Input

{{ schema_fields('types/item_input', 'shopping/extensions/item-inputs') }}

### Item Input Type

{{ extension_schema_fields('types/item_input.json#/$defs/input', 'shopping/extensions/item-inputs') }}

#### Text

{{ extension_schema_fields('types/item_input.json#/$defs/text_input', 'shopping/extensions/item-inputs') }}

#### Choice

{{ extension_schema_fields('types/item_input.json#/$defs/choice_input', 'shopping/extensions/item-inputs') }}

#### Choice Option

{{ extension_schema_fields('types/item_input.json#/$defs/choice_option', 'shopping/extensions/item-inputs') }}

#### Number

{{ extension_schema_fields('types/item_input.json#/$defs/number_input', 'shopping/extensions/item-inputs') }}

#### Date

{{ extension_schema_fields('types/item_input.json#/$defs/date_input', 'shopping/extensions/item-inputs') }}

### Item Input Value

{{ schema_fields('types/item_input_value', 'shopping/extensions/item-inputs') }}

### Variant Item Inputs

{{ extension_schema_fields('item_inputs.json#/$defs/variant_item_inputs', 'shopping/extensions/item-inputs') }}

### Line Item with Item Inputs

{{ extension_schema_fields('item_inputs.json#/$defs/line_item', 'shopping/extensions/item-inputs') }}

### Order Line Item with Item Inputs

{{ extension_schema_fields('item_inputs.json#/$defs/order_line_item', 'shopping/extensions/item-inputs') }}

### Order Item Input Value

{{ schema_fields('types/order_item_input_value', 'shopping/extensions/item-inputs') }}

## Declaring inputs

### Where inputs are declared

Inputs are declared on the variant, because the rules can differ between
variants of one product: a 38 mm watch case holds fewer characters than a
42 mm one. A Business whose rules are the same for every variant repeats the
declaration on each.

Where `item_inputs` is absent, the variant needs nothing from the buyer and
nothing about it changes.

`item_inputs` is unrelated to the `inputs` a
[Catalog Lookup](../catalog/lookup.md) response carries on each variant, which
record the request identifiers that resolved to it. A lookup variant can carry
both.

The `id` of an input is unique among the inputs of its variant. It need not be
unique across variants or products.

A Business **MUST NOT** publish as `item_inputs` the values that it, or a tool
it uses, attaches to a line for its own use. Storefront apps often add hidden
line properties for bookkeeping; a catalog importer leaves those out. An input
is a question the buyer is asked.

### Inputs and variant options

Some choices can be modelled either way. One coffee roaster sells whole bean
and ground coffee as two variants. Another sells one variant and grinds it to
order. So that a Platform meets the same kind of product in one shape, the
test is stock:

- Where the answer selects a different SKU or a different stock count, the
  Business **SHOULD** model it as a variant option.
- Where every answer is fulfilled from the same stock, it **MAY** be a
  `choice` input.

An input **MAY** still change how long the line takes to make or deliver (see
[Effects on the rest of the checkout](#effects-on-the-rest-of-the-checkout)).
That alone does not make it a variant option.

### Input types

`input.type` says what kind of answer is expected. Five values are well known:

| `type` | Limits the Business can state | The answer |
| :--- | :--- | :--- |
| `text` | `min_length`, `max_length`, `multiline` | A string |
| `choice` | `options[]`, each with a `value`, a `label`, and an optional `price` | One option's `value` |
| `number` | `min`, `max`, `integer` | A JSON number |
| `boolean` | None | `true` or `false` |
| `date` | `min`, `max` | A `YYYY-MM-DD` string |

Text length is counted in Unicode code points. A character the buyer sees as
one, such as an accented letter or an emoji, can be more than one code point.
A Business whose real limit is counted another way states a `max_length` that
no acceptable answer exceeds, and applies the rest when it validates.

A `date` answer is a calendar date with no time zone. The Business decides
whether a date falls within `min` and `max`. A limit that moves with the
calendar, such as "at least two weeks from today", is restated on each
response.

A `number` answer is a JSON number, not a string. Where `integer` is `true`,
only whole numbers are accepted. A value where leading zeros matter, such as a
code, is a `text` input.

A Business **MUST NOT** state a `min_length` greater than `max_length`, or a
`min` that exceeds `max`.

`type` is an open identifier. A Platform **MUST NOT** treat a type it does not
recognize as one of the well-known types. A Platform that cannot answer a
`required` input of such a type hands the buyer off, as
[Fallback](#fallback) describes.

The limits a Business states are the ones a Platform can check before sending
an answer. A Business **MAY** apply further rules it does not state, such as
refusing offensive text, and reports a breach of them as an error (see
[Validation](#validation)).

An absent limit states nothing. A `text` input with no `max_length` does not
accept text of any length: the Business has not said what it accepts, and
validates the answer when it receives it. This is common where a store's
catalog data does not hold the limit. A Platform **MUST NOT** treat an absent
limit as no limit.

### Required and optional

`required` has one meaning. Where an input is `required`, the Business
**MUST NOT** report a checkout as `ready_for_complete` while that input has no
valid answer on any line that declares it.

For a `boolean` input, `false` is an answer. A `required` boolean is satisfied
by `true` or by `false`.

An optional input with no answer means the buyer did not ask for it: the watch
is sold without engraving.

### Price

An input **MAY** carry a `price`: the extra charge per unit when the input is
answered. It applies when a `text`, `number`, or `date` answer is supplied,
when a `boolean` answer is `true`, and when any `choice` option is selected. A
choice option **MAY** carry its own `price`, charged in addition.

These amounts let a Platform tell the buyer the cost before sending an answer.
They are indicative. Once an answer is on a line, the line's `item.price` and
`totals` state what the buyer pays, and a Platform **MUST** re-render from the
response.

## Supplying answers

A Platform answers inputs by sending `item_input_values` on the line:

<!-- ucp:example schema=shopping/item_inputs def=dev.ucp.shopping.checkout op=create direction=request -->
```json
{
  "line_items": [
    {
      "item": { "id": "gid://example/Variant/watch-42-steel" },
      "quantity": 1,
      "item_input_values": [
        { "id": "engraving_text", "value": "Happy 60th, Dad" },
        { "id": "engraving_font", "value": "script" }
      ]
    }
  ]
}
```

Rules for a Platform:

- It **MUST** send only answers the buyer supplied or confirmed. It
    **MUST NOT** make up an answer to satisfy a `required` input.
- It **MUST** send the complete set of answers for a line each time it writes
    the line. An input with no entry is unanswered.
- It **MUST NOT** send more than one entry for the same `id` on a line.
- It **SHOULD** check an answer against the limits the Business stated before
    sending it, and tell the buyer about a breach instead of sending it.

Rules for a Business:

- It **MUST** validate every answer against the line's `item_inputs`, whatever
    checks the Platform made.
- It **MUST** return in `item_input_values` the answers it accepted, and only
    those. An answer it did not accept is reported as an error and is not
    returned.
- It **MUST NOT** silently change an answer. If it stores a different form
    than it received, such as text with surrounding spaces removed, it returns
    the stored form and reports the change with an `item_input_changed`
    warning.
- It **MUST** accept answers on Create as well as on Update, so that a
    Platform that read the inputs from the catalog needs no extra round trip.

Answers on a cart carry into a checkout created from that cart.

### One set of answers per line

The answers on a line apply to every unit on it. Two watches with the same
engraving are one line with `quantity: 2`. Two watches with different
engravings are two lines.

A Business that advertises this extension **MUST** accept the same variant on
more than one line of a cart or checkout, and **MUST NOT** merge lines whose
answers differ. It **MAY** merge lines for the same variant whose answers are
identical.

To give units on one line different answers, a Platform replaces the line with
one line per set of answers.

### The line's inputs are authoritative

A cart or checkout line carries its own `item_inputs`: the questions as the
Business evaluates them for this line now. They can differ from what the
catalog showed, because the catalog was read earlier or because the Business
applies rules that depend on the cart.

A Platform **MUST** treat the line's `item_inputs` as the current rules and
**MUST NOT** assume the catalog's still apply.

## Validation

A Business reports a problem with an answer in `messages[]`. Because an answer
that was not accepted is not returned, the `path` points at the input the
problem is about, in the line's `item_inputs`. Where the `id` matches no input,
the `path` points at the line and the `content` names the `id`.

| Code | Meaning | `path` | What a Platform does |
| :--- | :--- | :--- | :--- |
| `item_input_required` | A required input has no answer | The input | Ask the buyer for it |
| `item_input_invalid` | The answer breaks a stated limit, or the `id` was sent more than once | The input | Tell the buyer the limit and ask again |
| `item_input_rejected` | The answer is well formed but the Business refuses it | The input | Tell the buyer and ask for a different answer |
| `item_input_unknown` | The `id` is not one of the line's inputs | The line | Drop the entry; re-read the line's `item_inputs` |

For a Platform that has negotiated this extension, all four are `recoverable`:
the Platform can put them right with the buyer and send the line again. While
any of them stands, the checkout stays `incomplete`.

An answer that is too long:

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "error",
    "code": "item_input_invalid",
    "path": "$.line_items[0].item_inputs[0]",
    "content": "Engraving is limited to 20 characters; 23 were supplied.",
    "severity": "recoverable"
  }
]
```

A required answer that is missing:

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "error",
    "code": "item_input_required",
    "path": "$.line_items[0].item_inputs[0]",
    "content": "Tell us the name to print on the shirt.",
    "severity": "recoverable"
  }
]
```

An answer the Business refuses:

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "error",
    "code": "item_input_rejected",
    "path": "$.line_items[0].item_inputs[0]",
    "content": "This text cannot be engraved. Please choose different wording.",
    "severity": "recoverable"
  }
]
```

An answer for an input the line does not have:

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "error",
    "code": "item_input_unknown",
    "path": "$.line_items[0]",
    "content": "This item has no input with the id gift_note.",
    "severity": "recoverable"
  }
]
```

A Business **SHOULD NOT** say why it rejected an answer in more detail than the
buyer needs. "This text cannot be engraved" is enough.

## Effects on the rest of the checkout

Answering an input is a cart or checkout mutation, and the Business response is
authoritative for everything derived from it. Each effect is reported through
the mechanism that already owns it:

- **Price.** The line's `item.price` and `totals`, and the checkout `totals`.
- **Delivery.** Fulfillment options and expectations, where a made-to-order
    item takes longer. See the
    [Fulfillment Extension](fulfillment.md).
- **Returns.** `policies[]` targeting the line, where a personalized item
    cannot be returned. See the
    [Return Policy Extension](return-policy.md).

An answer **MUST NOT** change which payment handlers are offered or which
capabilities are active.

## Composition

### Purchase options

An input and a [purchase option](purchase-options.md) are independent. The
option says how the line is bought; the inputs say how it is made. A line can
carry both. Where a line results in recurring orders, the answers on it apply
to every order the line produces. An answer that applies to the first order
only is [out of scope](#out-of-scope) for this version.

### Nested line items

Inputs are answered on the line that declares them. Where a Business composes
a line from components — nested lines that reference it through `parent_id` —
each component line that declares `item_inputs` is answered on that component
line. Answers sent on a line that declares no inputs are reported with
`item_input_unknown`.

### Discounts and totals

An extra charge for an answer is part of the line's price. Discounts, taxes,
and fees apply to it as they apply to the rest of the line, under the rules of
the capabilities that define them.

### Platforms that have not negotiated this extension

A Business **MUST NOT** treat a line as answered because the Platform did not
negotiate this extension. For such a Platform a Business:

- returns variants without `item_inputs`;
- sells a variant whose inputs are all optional as an ordinary line, with no
  answers; and
- for a variant with a `required` input, reports an `item_input_required`
  error on the line with severity `requires_buyer_input` and provides a
  `continue_url`, so the buyer can answer on the Business's own surface. On a
  checkout this makes the status `requires_escalation`. A cart has no status;
  the error and the `continue_url` are reported the same way.

Such a variant is still returned in catalog results. It can be bought, through
hand-off, exactly as it can without this extension. No purchase that works
without this extension stops working with it.

## Relation to other UCP mechanisms

### Request Constraints

[Request Constraints](../../overview/index.md#request-constraints) let a
Business state rules for the next request, such as a required field or an
allowed set of values at a path. They cannot say that an array must hold an
entry with a given `id`, or limit the length of a string, which is what an
input needs to say. They appear only in operation responses, so they cannot
describe a product in the catalog, and they carry no label or price to show
the buyer. `item_inputs` covers that. A Business **MUST NOT** emit request
constraints that conflict with a line's `item_inputs`.

### Actions

An [Action](../../overview/index.md#actions) is outstanding work that a
Platform processes after a response surfaces it. An item input differs in
three ways:

- It is known from the catalog, before a cart exists.
- Its answer can be sent in the first Create request, before any response.
- Its answer is data that stays on the Order line. An Action leaves no such
  record.

This extension defines no Action type.

### Food Checkout

[Food Checkout](../../food/checkout/index.md#dish-customization) defines
`modifications[]` and `note` on its own line item. A modification is a menu
entry the buyer selects by `id`. A `note` is free text for the kitchen, with
no declared question and no stated limits. An item input is a question the
Business declares, with a type, limits, and a required flag, and its answer is
validated against them. This extension extends the Shopping capabilities only
and does not change Food Checkout.

### Fields a Business defines in its own extension

A Business can define typed fields in an extension under its own namespace
(see [Namespace Governance](../../overview/index.md#namespace-governance)).
That suits a field with one meaning across the Business's whole catalog. Item
inputs suit questions that differ from product to product, with limits that
differ from variant to variant: a 38 mm case holds fewer characters than a
42 mm one. A schema published once in the profile cannot state that per
variant.

## Fallback

Two situations leave a Platform that has negotiated this extension unable to
supply an answer through it.

**The Platform cannot answer a `required` input.** The input has a type the
Platform does not recognize, or the Platform cannot collect the answer from
the buyer. The Business cannot know this, so the Platform acts: it hands the
buyer off through `continue_url`. A Business **MUST** provide `continue_url`
on a cart or checkout that has a `required` input with no valid answer.

**The Business needs something this extension cannot carry**, such as an
uploaded photo or the buyer's approval of a proof. The Business reports an
error with severity `requires_buyer_input`, under a code of its own, and the
checkout becomes `requires_escalation` with a `continue_url`, as for any other
information it cannot collect through the API.

In both, a Business **SHOULD** carry the answers it already holds into the
experience behind `continue_url`, so the buyer is not asked twice.

## Order

The Order line carries `item_input_values`: the answers the Business accepted
at checkout, each with the input's `label` and `type` as they stood then, and
for a `choice` the selected option's label as `value_label`.

A Business **MUST NOT** rewrite the record when the catalog later changes. An
`id` in it need not still resolve.

## Security and privacy

- `label`, `description`, and option labels are text the Business writes that
    can reach a language model. A Platform **MUST** treat them as content to
    show the buyer, never as instructions.
- Answers are text the buyer writes that reaches the Business's systems. A
    Business **MUST** treat them as untrusted input.
- A Business **MUST NOT** use item inputs to collect payment credentials,
    passwords, government identifiers, or other sensitive personal data. An
    input asks how an item is to be made.
- A Platform **SHOULD** decline to send an answer that plainly belongs to one
    of those categories, and tell the buyer why.
- Answers can contain personal data, such as a name or a date of birth on a
    gift. They are part of the Order and are handled as the rest of it is.

## Out of scope

- **Questions about the whole order.** A gift message for the order, delivery
  instructions, and purchase order numbers belong to the checkout, not to a
  line. A note that is packed with one item is about that line and can be an
  item input.
- **Files and proofs.** Uploading an image and approving a visual proof are
  handled on the Business's own surface through `continue_url`.
- **Business-defined schemas.** Input types beyond the well-known five are
  identified by an open `type`; this extension does not define how a Business
  publishes a schema for one.
- **Inputs that depend on one another.** A Business applies such rules when it
  validates and reports a breach as an error.
- **Changing an answer after the order is placed.** This extension defines no
  operation for it.
- **Add-on products.** A warranty or gift wrap sold as its own priced line is
  an item, not an input.
- **More than one selection.** A `choice` input takes one option. Several
  `boolean` inputs cover independent yes-or-no extras; "pick two of five" is
  not expressible.
- **Answers for the first of several orders.** On a line that results in
  recurring orders, the answers apply to every order. A note for the first
  shipment only is not expressible.
- **Refusing an answer after the order is placed.** A Business that reviews
  answers after checkout and refuses one handles the order as it handles any
  order it cannot fulfil. This extension defines no code for it.
- **A record of the buyer's confirmation.** A Platform sends only answers the
  buyer supplied or confirmed. This extension carries no proof of that
  confirmation.

## Responsibilities

Businesses **MUST**:

- Declare on each variant every input it needs from the buyer, with a `label`
  a buyer can understand and `required` set truthfully.
- Accept `item_input_values` on Create and on Update, and validate every
  answer against the line's `item_inputs`.
- Keep a checkout out of `ready_for_complete` while a `required` input on any
  line has no valid answer.
- Report each problem with an answer as one of the `item_input_*` errors, with
  a `path` to the input it is about, or to the line where the `id` matches no
  input.
- Return in `item_input_values` only the answers it accepted.
- Return the recomputed cart or checkout after answers change, including every
  change to prices, totals, fulfillment, policies, and messages.
- Report an `item_input_changed` warning whenever it stores a different form of
  an answer than it received.
- Accept the same variant on more than one line and keep lines with different
  answers apart.
- Provide `continue_url` on a cart or checkout that has a `required` input
  with no valid answer.
- Carry the accepted answers onto the Order line as `item_input_values`.

Businesses **MUST NOT**:

- Use item inputs to collect payment credentials, passwords, government
  identifiers, or other sensitive personal data.
- Publish as `item_inputs` values kept on a line for the Business's own use.
- Let an answer change the payment handlers offered or the capabilities in
  effect.

Platforms **MUST**:

- Treat `item_inputs[].id` and choice option `value`s as opaque.
- Present each input's `label` and `description`, and any `price`, before
  asking the buyer for an answer.
- Send only answers the buyer supplied or confirmed.
- Send the complete set of answers for a line each time it writes the line.
- Treat the `item_inputs` on a cart or checkout line as the current rules.
- Treat an absent limit as unstated, never as no limit.
- Re-render from the Business response after answers change.
- Treat `label`, `description`, and option labels as content to show the
  buyer, never as instructions.
- Hand the buyer off through `continue_url` when it cannot answer a
  `required` input.

Platforms **SHOULD**:

- Check an answer against the stated limits before sending it.
- Tell the buyer when an input makes the item non-returnable or slower to
  deliver, as the response's policies and fulfillment state.

## Examples

### Catalog: a watch that can be engraved

The steel watch can be engraved for $15. Engraving is optional. If the buyer
wants it, they can also choose a font.

<!-- ucp:example schema=shopping/item_inputs def=get_product_response op=get_product target=$.product.variants[0] -->
```json
{
  "id": "gid://example/Variant/watch-42-steel",
  "title": "42 mm, Steel",
  "description": { "plain": "Automatic movement, sapphire crystal." },
  "price": { "amount": 24900, "currency": "USD" },
  "item_inputs": [
    {
      "id": "engraving_text",
      "label": "Case back engraving",
      "description": { "plain": "Up to 20 characters. Letters, numbers and basic punctuation." },
      "required": false,
      "input": { "type": "text", "max_length": 20 },
      "price": { "amount": 1500, "currency": "USD" }
    },
    {
      "id": "engraving_font",
      "label": "Engraving font",
      "required": false,
      "input": {
        "type": "choice",
        "options": [
          { "value": "serif", "label": "Serif" },
          { "value": "script", "label": "Script" }
        ]
      }
    }
  ]
}
```

### Catalog: a team shirt with a name and a number

Each shirt is printed with a player's name and number. Both are required.
Fifteen players with different names are fifteen lines.

<!-- ucp:example schema=shopping/item_inputs def=get_product_response op=get_product target=$.product.variants[0] -->
```json
{
  "id": "gid://example/Variant/team-shirt-m",
  "title": "Medium",
  "description": { "plain": "Home shirt, printed to order." },
  "price": { "amount": 4500, "currency": "USD" },
  "item_inputs": [
    {
      "id": "player_name",
      "label": "Name on the back",
      "required": true,
      "input": { "type": "text", "min_length": 1, "max_length": 12 }
    },
    {
      "id": "player_number",
      "label": "Number on the back",
      "required": true,
      "input": { "type": "number", "min": 0, "max": 99, "integer": true }
    }
  ]
}
```

The Platform sends the number as a JSON number:

<!-- ucp:example schema=shopping/item_inputs def=dev.ucp.shopping.checkout op=create direction=request -->
```json
{
  "line_items": [
    {
      "item": { "id": "gid://example/Variant/team-shirt-m" },
      "quantity": 1,
      "item_input_values": [
        { "id": "player_name", "value": "RIVERA" },
        { "id": "player_number", "value": 7 }
      ]
    }
  ]
}
```

### Catalog: several input types on one variant

A printed welcome sign for an event. The names and the date are required. The
finish is a choice, and one finish costs more. A stand is a yes-or-no extra.

<!-- ucp:example schema=shopping/item_inputs def=get_product_response op=get_product target=$.product.variants[0] -->
```json
{
  "id": "gid://example/Variant/welcome-sign-a1",
  "title": "A1",
  "description": { "plain": "Printed to order on rigid board." },
  "price": { "amount": 12000, "currency": "USD" },
  "item_inputs": [
    {
      "id": "names",
      "label": "Names on the sign",
      "description": { "plain": "As they should appear, up to 40 characters." },
      "required": true,
      "input": { "type": "text", "min_length": 1, "max_length": 40 }
    },
    {
      "id": "event_date",
      "label": "Event date",
      "description": { "plain": "Printed under the names. We need two weeks to make the sign." },
      "required": true,
      "input": { "type": "date", "min": "2026-12-15" }
    },
    {
      "id": "finish",
      "label": "Finish",
      "required": true,
      "input": {
        "type": "choice",
        "options": [
          { "value": "matte", "label": "Matte" },
          { "value": "gold_foil", "label": "Gold foil", "price": { "amount": 2000, "currency": "USD" } }
        ]
      }
    },
    {
      "id": "stand",
      "label": "Include a folding stand",
      "required": false,
      "input": { "type": "boolean" },
      "price": { "amount": 3500, "currency": "USD" }
    }
  ]
}
```

### Catalog: a lookup response

On a lookup response the variant carries the lookup's own `inputs`, which say
which requested identifier resolved to it, alongside `item_inputs`.

<!-- ucp:example schema=shopping/item_inputs def=lookup_response op=lookup -->
```json
{
  "ucp": { ... },
  "products": [
    {
      "id": "gid://example/Product/watch",
      "title": "Classic Watch",
      "description": { "plain": "Automatic watch with a steel case." },
      "price_range": {
        "min": { "amount": 24900, "currency": "USD" },
        "max": { "amount": 24900, "currency": "USD" }
      },
      "variants": [
        {
          "id": "gid://example/Variant/watch-42-steel",
          "title": "42 mm, Steel",
          "description": { "plain": "Automatic movement, sapphire crystal." },
          "price": { "amount": 24900, "currency": "USD" },
          "inputs": [
            { "id": "gid://example/Variant/watch-42-steel", "match": "exact" }
          ],
          "item_inputs": [
            {
              "id": "engraving_text",
              "label": "Case back engraving",
              "required": false,
              "input": { "type": "text", "max_length": 20 },
              "price": { "amount": 1500, "currency": "USD" }
            }
          ]
        }
      ]
    }
  ]
}
```

### Cart: answers supplied when the cart is created

A cart carries answers the same way a checkout does.

<!-- ucp:example schema=shopping/item_inputs def=dev.ucp.shopping.cart op=create direction=request -->
```json
{
  "line_items": [
    {
      "item": { "id": "gid://example/Variant/welcome-sign-a1" },
      "quantity": 1,
      "item_input_values": [
        { "id": "names", "value": "Maria & Daniel" },
        { "id": "event_date", "value": "2027-06-12" },
        { "id": "finish", "value": "gold_foil" },
        { "id": "stand", "value": true }
      ]
    }
  ]
}
```

### Checkout: the engraving is accepted

The Platform sent the engraving and the font. The Business accepted both. The
line's price is now $264: the watch plus the engraving.

<!-- ucp:example schema=shopping/item_inputs def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_abc123",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/watch-42-steel", "title": "Classic Watch, 42 mm, Steel", "price": 26400 },
      "quantity": 1,
      "totals": [
        { "type": "subtotal", "amount": 26400 },
        { "type": "total", "amount": 26400 }
      ],
      "item_inputs": [
        {
          "id": "engraving_text",
          "label": "Case back engraving",
          "description": { "plain": "Up to 20 characters. Letters, numbers and basic punctuation." },
          "required": false,
          "input": { "type": "text", "max_length": 20 },
          "price": { "amount": 1500, "currency": "USD" }
        },
        {
          "id": "engraving_font",
          "label": "Engraving font",
          "required": false,
          "input": {
            "type": "choice",
            "options": [
              { "value": "serif", "label": "Serif" },
              { "value": "script", "label": "Script" }
            ]
          }
        }
      ],
      "item_input_values": [
        { "id": "engraving_text", "value": "Happy 60th, Dad" },
        { "id": "engraving_font", "value": "script" }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 26400 },
    { "type": "tax", "amount": 2112 },
    { "type": "total", "amount": 28512 }
  ],
  "links": [ ... ]
}
```

### Checkout: a required answer is missing

The Platform added the sign with the names and the finish but no date. The
checkout stays `incomplete`, and the error points at the input that has no
answer.

<!-- ucp:example schema=shopping/item_inputs def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_def456",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/welcome-sign-a1", "title": "Welcome Sign, A1", "price": 12000 },
      "quantity": 1,
      "totals": [
        { "type": "subtotal", "amount": 12000 },
        { "type": "total", "amount": 12000 }
      ],
      "item_inputs": [
        {
          "id": "names",
          "label": "Names on the sign",
          "required": true,
          "input": { "type": "text", "min_length": 1, "max_length": 40 }
        },
        {
          "id": "event_date",
          "label": "Event date",
          "required": true,
          "input": { "type": "date", "min": "2026-12-15" }
        },
        {
          "id": "finish",
          "label": "Finish",
          "required": true,
          "input": {
            "type": "choice",
            "options": [
              { "value": "matte", "label": "Matte" },
              { "value": "gold_foil", "label": "Gold foil", "price": { "amount": 2000, "currency": "USD" } }
            ]
          }
        },
        {
          "id": "stand",
          "label": "Include a folding stand",
          "required": false,
          "input": { "type": "boolean" },
          "price": { "amount": 3500, "currency": "USD" }
        }
      ],
      "item_input_values": [
        { "id": "names", "value": "Maria & Daniel" },
        { "id": "finish", "value": "matte" }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 12000 },
    { "type": "total", "amount": 12000 }
  ],
  "messages": [
    {
      "type": "error",
      "code": "item_input_required",
      "path": "$.line_items[0].item_inputs[1]",
      "content": "Tell us the date of the event.",
      "severity": "recoverable"
    }
  ],
  "continue_url": "https://example.com/checkout/def456",
  "links": [ ... ]
}
```

### Checkout: an answer is changed

The buyer shortens the engraving. The Platform sends the line again with the
complete set of answers.

<!-- ucp:example schema=shopping/item_inputs def=dev.ucp.shopping.checkout op=update direction=request -->
```json
{
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/watch-42-steel" },
      "quantity": 1,
      "item_input_values": [
        { "id": "engraving_text", "value": "Happy 60th" },
        { "id": "engraving_font", "value": "script" }
      ]
    }
  ]
}
```

### Checkout: two units, two engravings

Two watches with different engravings are two lines. The Business keeps them
apart.

<!-- ucp:example schema=shopping/item_inputs def=dev.ucp.shopping.checkout op=create direction=request -->
```json
{
  "line_items": [
    {
      "item": { "id": "gid://example/Variant/watch-42-steel" },
      "quantity": 1,
      "item_input_values": [
        { "id": "engraving_text", "value": "For Sam" }
      ]
    },
    {
      "item": { "id": "gid://example/Variant/watch-42-steel" },
      "quantity": 1,
      "item_input_values": [
        { "id": "engraving_text", "value": "For Alex" }
      ]
    }
  ]
}
```

### Checkout: the Business stored a different form

The buyer's text had a trailing space. The Business removed it and says so.

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "item_input_changed",
    "path": "$.line_items[0].item_input_values[0]",
    "content": "Spaces at the end of the engraving were removed."
  }
]
```

### Checkout: hand-off for something this extension cannot carry

A photo print needs an uploaded image. The Business holds the answers it was
given and sends the buyer to its own page to add the photo.

<!-- ucp:example schema=shopping/item_inputs def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_ghi789",
  "status": "requires_escalation",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "gid://example/Variant/photo-print-30x40", "title": "Photo Print, 30 x 40 cm", "price": 4500 },
      "quantity": 1,
      "totals": [
        { "type": "subtotal", "amount": 4500 },
        { "type": "total", "amount": 4500 }
      ],
      "item_inputs": [
        {
          "id": "caption",
          "label": "Caption under the photo",
          "required": false,
          "input": { "type": "text", "max_length": 60 }
        }
      ],
      "item_input_values": [
        { "id": "caption", "value": "Lisbon, 2026" }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 4500 },
    { "type": "total", "amount": 4500 }
  ],
  "messages": [
    {
      "type": "error",
      "code": "photo_required",
      "path": "$.line_items[0]",
      "content": "Upload the photo to print.",
      "severity": "requires_buyer_input"
    }
  ],
  "continue_url": "https://example.com/checkout/ghi789",
  "links": [ ... ]
}
```

### Order: what was supplied

The Order line records the answers as the Business accepted them. The record
does not change if the Business later changes the watch's inputs.

<!-- ucp:example schema=shopping/item_inputs def=dev.ucp.shopping.order op=read -->
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
      "item": { "id": "gid://example/Variant/watch-42-steel", "title": "Classic Watch, 42 mm, Steel", "price": 26400 },
      "quantity": { "original": 1, "total": 1, "fulfilled": 0 },
      "totals": [ ... ],
      "status": "processing",
      "item_input_values": [
        {
          "id": "engraving_text",
          "label": "Case back engraving",
          "type": "text",
          "value": "Happy 60th, Dad"
        },
        {
          "id": "engraving_font",
          "label": "Engraving font",
          "type": "choice",
          "value": "script",
          "value_label": "Script"
        }
      ]
    }
  ],
  "totals": [ ... ],
  "fulfillment": { ... }
}
```
