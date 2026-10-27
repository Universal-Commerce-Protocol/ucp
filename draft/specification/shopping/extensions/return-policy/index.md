# Return Policy Extension

## Overview

The Return Policy Extension defines the `dev.ucp.shopping.policy.return` policy type on the core [`policies[]`](http://ucp.dev/draft/specification/overview/#policies) primitive. It adds machine-readable return terms to policies that carry this type, from catalog through cart, checkout, and order, so platforms and agents can answer questions like "How long do I have to return this?", "Do I get my money back or store credit?", "Where and at what cost do I send it back?", and "Can I return this at all?" without leaving to read a policy page.

Policy pages often lack product-level granularity: one page covers the standard terms, final-sale items, category exceptions, and marketplace sellers in prose, leaving buyers and agents unable to tell which terms govern a given item. Because each return policy targets items through `applies_to`, the terms a platform reads for an item are the ones that apply to it.

**Key features:**

- A return eligibility statement (`eligibility`): a minimum return window with an explicit anchor, no time limit, or returns not accepted
- What the buyer receives on an accepted return (`supported_resolutions`)
- Return channels (`methods`)
- Return fees, each typed by what it is for and optionally scoped to channels (`fees`)

**Dependencies:**

- The core `policies[]` primitive (see [Policies](http://ucp.dev/draft/specification/overview/#policies)).
- One or more of the parent capabilities this type extends: Catalog Search, Catalog Lookup, Cart, Checkout, or Order.

This extension only structures the type-specific body. The `policies[]` container, `applies_to` targeting, same-type precedence, and buyer-facing disclosure through `messages[]` are defined once by the primitive and are **unchanged** here.

## Discovery

Businesses advertise return policy support in their profile. The type extends any surface that carries `policies[]`:

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.shopping.policy.return": [
        {
          "version": "draft",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup",
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/draft/specification/shopping/extensions/return-policy",
          "schema": "https://ucp.dev/draft/schemas/shopping/policy_return.json"
        }
      ]
    }
  }
}
```

A business **MAY** advertise support on a subset of these surfaces. A platform that has negotiated this type validates the return body and **MAY** reason over its structured fields (for example, presenting a return deadline) only when the body passes schema validation. A platform that has not negotiated it still renders the policy from the base `type` and `description`, because the return body is purely additive.

## Schema

When this type is active, a `policies[]` entry whose `type` is `dev.ucp.shopping.policy.return` **MAY** carry the following fields in addition to the base `type`, `description`, `applies_to`, and `url`. Each top-level field is optional, and an omitted field means the term is not stated structurally; a return policy with no structured fields is still presentable from its `description`.

### Return Policy

Return terms for a `dev.ucp.shopping.policy.return` policy.

| Name                  | Type                                                                                             | Requirement | Description                                                                                                                                                                                                                                                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------------ | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| eligibility           | [Return Eligibility](/draft/specification/shopping/extensions/return-policy/#return-eligibility) | Optional    | Structured return eligibility statement. Omitted means eligibility is not stated structurally, not that returns are unlimited or not accepted. When `type` is `not_accepted`, the business's return policy does not accept returns of the covered items, and `supported_resolutions`, `methods`, and `fees` MUST be omitted. |
| supported_resolutions | Array[string]                                                                                    | Optional    | Return outcomes guaranteed for every eligible return, as an unordered set; not an exhaustive list. Well-known values: `original_payment_method`, `store_credit`, `gift_card`, `exchange`, `replacement`.                                                                                                                     |
| methods               | Array[string]                                                                                    | Optional    | Return channels guaranteed for every eligible return, as an unordered set; not an exhaustive list. Well-known values: `in_store`, `by_mail`, `kiosk`. Omit when channels are not stated structurally.                                                                                                                        |
| fees                  | Array[Return Fee]                                                                                | Optional    | Estimated maximum charges on a return, each typed by what it is for and optionally scoped to channels; not an exhaustive list. Omitted means fees are not stated structurally, not that none are charged.                                                                                                                    |

### Return Eligibility

An open return eligibility statement. `window` states a guaranteed minimum period after an anchor event and, once resolved, the instant it ends; expiration does not signal non-returnability. `unlimited` states no time restriction, not unconditional eligibility. `not_accepted` states that the business's return policy does not accept returns of the covered items; it does not describe remedies under applicable law or third-party guarantees. Unknown types establish no eligibility inference; consumers may use the base policy's `description`.

| Name       | Type                                                 | Requirement  | Description                                                                                                                                                                                                                                                                                                                         |
| ---------- | ---------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type       | string                                               | **Required** | Eligibility kind. Well-known values: `window`, `unlimited`, `not_accepted`. Unknown values establish no eligibility inference.                                                                                                                                                                                                      |
| duration   | [Duration](/draft/specification/reference/#duration) | Optional     | Length of the return window after the `anchor` event. It states the term for presentation; the Business resolves the deadline as `expires_at`.                                                                                                                                                                                      |
| anchor     | string                                               | Optional     | Event the window is measured from. Well-known values: `purchased`, `fulfilled`, `delivered`.                                                                                                                                                                                                                                        |
| expires_at | string                                               | Optional     | RFC 3339 instant at which the window ends, resolved by the Business once the `anchor` event has occurred (e.g., on an order after delivery). When covered quantities reach the anchor at different times, it states the earliest of their deadlines. An otherwise eligible return requested no later than this instant is accepted. |

### Return Fee

Each entry in `fees` uses this shape.

A charge on a return, typed by what it is for, as an estimated maximum. `amount` states a flat charge, where `0` means nothing is charged; `basis_points` states a percentage, optionally capped by `max_amount`; with neither, the fee is charged at its actual cost and no maximum is stated.

| Name         | Type                                                                       | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------------ | -------------------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | [Reverse Domain Name](/draft/specification/reference/#reverse-domain-name) | Optional    | Fee kind, as a reverse-domain name. Well-known values: `dev.ucp.shopping.fee.restocking` (a deduction from the refund, charged per one whole `quantity_unit.unit` returned, for example per lb, or per `each` when `quantity_unit` is absent), `dev.ucp.shopping.fee.return_shipping` (the cost of shipping the return, charged per return shipment), `dev.ucp.shopping.fee.handling` (charged per return request). Vendor kinds use the vendor's own namespace (e.g., `com.example.fee.eco`) and are charged per return request. A vendor fee charged on another basis, such as per item, omits `amount` and states its terms in `display_text`. A fee with an unknown `type` MUST carry `display_text`. Omitted only on an entry with `amount: 0`, which states that the business charges no fee of any kind in its scope, including vendor kinds and kinds defined later. |
| methods      | Array[string]                                                              | Optional    | Return channels this fee applies to; omitted means every channel. A channel need not be listed in the policy's `methods`. When more than one entry applies to a fee on a channel, an entry that lists the channel takes precedence over one that does not; among entries that both list the channel or both do not, an entry with a `type` takes precedence over one without.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| amount       | [Amount](/draft/specification/reference/#amount)                           | Optional    | Estimated maximum flat charge, in ISO 4217 minor units of the currency the covered items are priced in, charged per the unit of the fee `type`. `0` states that nothing is charged. Mutually exclusive with `basis_points`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| basis_points | integer                                                                    | Optional    | Estimated maximum charge in basis points (hundredths of a percent; `1250` = 12.5%) of the amount paid for the returned quantity, after item-level discounts and excluding tax, shipping, and other fees. On catalog surfaces, where no amount has been paid, it applies to the covered product's price. Mutually exclusive with `amount`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| max_amount   | [Amount](/draft/specification/reference/#amount)                           | Optional    | Cap on a `basis_points` charge: the charge is at most this amount, in ISO 4217 minor units of the currency the covered items are priced in, per the unit of the fee `type`. Requires `basis_points`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| display_text | string                                                                     | Optional    | Human-readable fee label, naming any condition under which the fee applies (e.g., '15% restocking fee on opened items'). Required when `type` is not a well-known fee kind, and when the fee has neither `amount` nor `basis_points`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

## Return terms

### Eligibility

`eligibility` states whether, and for how long, the covered items can be returned. Its `type` is required and is an open vocabulary. The well-known kinds are:

| `type`         | States that                                                                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `window`       | Otherwise eligible returns are accepted for at least `duration` from the event named by `anchor`; both are required (see [Window and anchor](#window-and-anchor)). |
| `unlimited`    | Otherwise eligible returns are subject to no time restriction.                                                                                                     |
| `not_accepted` | The business's return policy does not accept returns of the covered items (see [Non-returnable items](#non-returnable-items)).                                     |

`duration`, `anchor`, and `expires_at` have meaning only on a `window`, so a business **MUST NOT** carry them on an `unlimited` or `not_accepted` eligibility; the schema rejects the combination.

`not_accepted` states that the business's return policy accepts no returns of the covered items. `window` and `unlimited` state a time bound, not a verdict on a particular return: `window` guarantees a period for returns that are otherwise eligible, and `unlimited` removes the time restriction and nothing else, so neither kind alone establishes that a particular attempted return meets every requirement. A business **MAY** describe eligibility requirements beyond the time bound, such as tags attached or original packaging, in `description`.

An omitted `eligibility` means eligibility is not stated structurally; it states neither that returns are unrestricted nor that they are unavailable, and the `description` carries the terms. A platform **MUST NOT** infer eligibility from an omitted `eligibility` or from an eligibility `type` it does not recognize, for example by presenting the items as returnable without a time limit or as not returnable; it **MAY** present the policy from its `description`.

### Window and anchor

A `window` eligibility states the length of the return window as a **policy statement**, not a live countdown. It is a guaranteed minimum for otherwise eligible returns: a return requested within the window is accepted through a listed method, with a listed resolution that method accepts. `duration` and `anchor` state the terms, for example "30 days from delivery"; once the anchor event has occurred, the business resolves the guaranteed deadline and states it as `expires_at`. A return requested no later than `expires_at` is within the window; later steps, such as sending the item back within a set period, are eligibility requirements a business **MAY** describe in `description`. The window is a floor, not a ceiling: its expiry does not establish that an item is non-returnable (see [Responsibilities](#responsibilities)).

A platform **MAY** present `expires_at` in any time zone and **MUST NOT** present a later deadline, for example by showing only its date, which reads as the end of that date. Without `expires_at`, a platform presents the terms, for example "30 days from delivery", and **MUST NOT** present a date it computed from them as the deadline.

A business **SHOULD** state `expires_at` once it can resolve the deadline, typically on an order after the anchor event. It **MUST NOT** state an `expires_at` earlier than the end of the window its `duration` and `anchor` describe; when covered quantities reach the anchor at different times, such as a line delivered in two shipments, that is the earliest of their window ends, so a return requested by then is within the window for every covered quantity. A business scopes policies per line with `applies_to` for finer resolution.

On an order, `policies` record the terms that applied at checkout (see [Order](http://ucp.dev/draft/specification/shopping/order/#policies)). Stating `expires_at` resolves those terms; it does not change them. A business adds `expires_at` to the governing return policy and **MAY** split that policy into per-line copies with `applies_to` to state a deadline for each line, but every copy carries the terms of the checkout policy unchanged: its `eligibility` kind, `duration` and `anchor`, `supported_resolutions`, `methods`, and `fees`.

For a 30-day window anchored on `delivered` and an item delivered on 2026-03-02, the business states `"expires_at": "2026-04-01T18:00:00Z"`, and the platform shows "Return by Apr 1, 6:00 PM UTC" or its local equivalent (see [Order after delivery](#order-after-delivery)).

When the window's length varies with a choice the buyer makes at return time, such as the resolution, `duration` states the shortest of those periods, since a guarantee field holds for every eligible return (see [Responsibilities](#responsibilities)), and `description` states the longer ones. A condition the business requires, such as the item being unworn or unopened, is an eligibility requirement, not a shorter window: the window applies only to otherwise eligible returns (see [Eligibility](#eligibility)).

Businesses differ on whether the clock starts at purchase, fulfillment, or delivery, so a business that states a `window` **MUST** provide both `duration` and `anchor`, and the schema requires them. There is no default anchor, and a platform **MUST NOT** assume one. A business states no time restriction with an `unlimited` eligibility; when the window is not stated structurally, it omits `eligibility` and conveys the terms in `description`.

`anchor` is an open vocabulary. The well-known values are:

| Anchor      | The clock starts when                                                                                                                                     |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `purchased` | The order is placed.                                                                                                                                      |
| `fulfilled` | The business completes its fulfillment step for the method: handing the items to a carrier, readying them for pickup, or making a digital item available. |
| `delivered` | The buyer receives the items, including collecting a pickup order or gaining access to a digital item.                                                    |

`fulfilled` and `delivered` differ in whose action starts the clock: the business completing its step, or the buyer receiving the items. If its clock starts at an event no well-known anchor names, a business **MAY** use its own anchor value or an earlier well-known one, such as `purchased`. A platform that does not recognize an `anchor` value presents the window from `description`, and still presents `expires_at` when the business states it.

### Non-returnable items

To state that its return policy does not accept returns of the covered items, such as a final-sale item, a business **MUST** set `eligibility.type` to `not_accepted`. Because return terms do not apply, a business **MUST NOT** carry `supported_resolutions`, `methods`, or `fees` on a `not_accepted` policy; the schema rejects the combination, so no precedence between fields of one policy is ever needed. A business **MUST NOT** use an empty `supported_resolutions` or `methods` array to signal non-returnability, and the schema requires at least one entry in each; omit a field that is not stated structurally. A `not_accepted` eligibility is the single, unambiguous signal a platform acts on. A `not_accepted` eligibility describes the business's return policy only (see [Responsibilities](#responsibilities)).

When a business requires the buyer to be shown that an item is final sale, it emits a `messages[]` warning with `presentation: "disclosure"` and `code` equal to `dev.ucp.shopping.policy.return`, targeting the item. The disclosure pairs with the governing return policy at that node, as defined in [Presenting policies](http://ucp.dev/draft/specification/overview/#presenting-policies).

### Return fees

`fees` lists the charges a return can incur, each as a [Return Fee](#return-fee): `type` states what the charge is for, `methods` the channels it applies to, and `amount`, `basis_points`, and `max_amount` how much. A restocking fee deducts from the refund however the item comes back, so it is an entry that applies to every channel; a channel's cost, such as return shipping by mail, is an entry scoped to that channel. This lets a business state, for example, "free return shipping with a 15% restocking fee".

`methods` is an open vocabulary of return channels. The well-known values are `in_store`, `by_mail`, and `kiosk`; a business **MAY** use others, and a platform that does not recognize one presents it from `description`.

`type` is a reverse-domain fee kind, and `amount` and `max_amount` are charged per the kind's unit. The well-known kinds are:

| `type`                                 | Charged per                                                                                                                                                                                           |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dev.ucp.shopping.fee.restocking`      | One whole `quantity_unit.unit` returned, or one `each` when `quantity_unit` is absent, as `price` is (see [Quantities and units](http://ucp.dev/draft/specification/overview/#quantities-and-units)). |
| `dev.ucp.shopping.fee.return_shipping` | Return shipment, so units returned together incur it once and a return split across shipments incurs it for each one.                                                                                 |
| `dev.ucp.shopping.fee.handling`        | Return request.                                                                                                                                                                                       |

A vendor kind, such as `com.example.fee.eco`, is charged per return request and carries `display_text`, which the schema requires for any kind other than the three above. A vendor fee charged on another basis, such as per item, omits `amount` and states its terms in `display_text` (for example, "Eco fee, $1 per item"); such an entry states no maximum, so a platform presents its text and never an understated cap.

How much a fee charges is stated by the pricing fields it carries:

| Fields                                       | States                                                                                               |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `amount` of 1 or more                        | Up to that flat charge.                                                                              |
| `amount: 0`                                  | Nothing is charged.                                                                                  |
| `basis_points`, optionally with `max_amount` | Up to that percentage, and at most `max_amount` when present.                                        |
| Neither `amount` nor `basis_points`          | The fee is charged at its actual cost, and no maximum is stated; the schema requires `display_text`. |

An entry may omit `type` only with `amount: 0`; such an entry states that the business charges no fee of any kind in its scope, including vendor kinds and kinds defined later.

`basis_points` applies to the amount paid for the returned quantity, after item-level discounts and excluding tax, shipping, and other fees; on catalog surfaces, where nothing has been paid, it applies to the covered product's price. An entry carries `amount` or `basis_points` but not both, and `max_amount` only with `basis_points`; the schema rejects either combination.

An entry that lists `methods` applies only to those channels; an entry without `methods` applies to every channel. When more than one entry applies to a fee on a channel, an entry that lists the channel takes precedence over one that does not; among entries that both list the channel or both do not, an entry with a `type` takes precedence over one without. For example, `{ "methods": ["in_store"], "amount": 0 }` makes in-store returns free even when another entry charges a restocking fee on every channel. An entry may list a channel the policy's `methods` does not.

A business **MUST NOT** carry two entries of the same `type`, or two entries without `type`, that apply to the same channel. If it does, a platform treats those fees as not stated for that channel.

`max_amount` caps a percentage. For items priced in USD, `{ "type": "dev.ucp.shopping.fee.restocking", "basis_points": 1500, "max_amount": 5000 }` means 15% of the amount paid, at most $50.00 per unit. For 3 units bought at $200.00 each, the estimated maximum deduction is 3 × min($30.00, $50.00) = $90.00.

Fees are estimated maximums. A business **MUST NOT** state an `amount`, `basis_points`, or `max_amount` lower than its policy charges for that fee, including a fee that applies only in some cases, such as a restocking fee on opened items, which it states at its full value with `display_text` naming the condition; a fee it cannot bound omits them. The business sets the charge for a particular return when it processes the return, and that charge can differ from an amount derived from these fields, for example with the item's condition, return shipping rates, taxes, or how the order's discounts are refunded. A platform **MUST NOT** present a fee, or an amount derived from it, as the final charge for a particular return.

For example, a policy that charges a capped restocking fee, offers free returns in store and at kiosks, and charges return shipping and an eco fee by mail states:

```json
[
  {
    "type": "dev.ucp.shopping.policy.return",
    "description": {...},
    "methods": ["in_store", "kiosk", "by_mail"],
    "fees": [
      { "type": "dev.ucp.shopping.fee.restocking", "basis_points": 1500, "max_amount": 5000, "display_text": "15% restocking fee on opened items" },
      { "methods": ["in_store", "kiosk"], "amount": 0 },
      { "type": "dev.ucp.shopping.fee.return_shipping", "methods": ["by_mail"], "amount": 500 },
      { "type": "com.example.fee.eco", "methods": ["by_mail"], "amount": 100, "display_text": "Eco packaging fee" }
    ]
  }
]
```

Per channel, its entries resolve to the following; a fee type with no entry for a channel is not stated:

| Channel             | Resulting fees                                                                                                                                                                                                     |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `in_store`, `kiosk` | Free, since no fee of any kind is charged (the `amount: 0` entry without `type`).                                                                                                                                  |
| `by_mail`           | Restocking: up to 15% of the amount paid, at most 5000 minor units per unit returned. Return shipping: up to 500 minor units per return shipment. `com.example.fee.eco`: up to 100 minor units per return request. |

Only `amount: 0` states that nothing is charged. A platform **MUST NOT** treat any other state as zero cost, including an omitted `fees` or a fee type with no entry for a channel, whether it presents the terms, for example as "free" or "no restocking fee", or estimates a return's charges (see [Responsibilities](#responsibilities)). A platform **MAY** present a channel as free only when an entry without `type` covers it and no entry with `type` resolves to a charge there.

Amounts (`amount` and `max_amount` on a fee) carry no currency of their own. They are in the currency the covered items are priced in, which in a cart, checkout, or order is its `currency`. A business **MUST** limit a policy that carries an amount to items priced in a single currency. A catalog response can price products in more than one currency, so a business scopes such a policy with `applies_to`. A platform **MUST NOT** interpret an amount on a policy whose covered items are priced in different currencies.

## Targeting and precedence

Targeting and precedence are provided by the `policies[]` primitive and are not redefined here. In short: a policy with no `applies_to` is the response-wide default; a policy that targets specific items overrides it where they overlap, with the narrowest same-type target winning. See [Targeting](http://ucp.dev/draft/specification/overview/#targeting) and [Precedence](http://ucp.dev/draft/specification/overview/#precedence).

For return policies this means a business states a single default return policy once, then adds targeted overrides only for the exceptions (a final-sale item, a category with a different window), rather than repeating a policy on every line. An override replaces the default for the items it governs and inherits none of its terms, so a business **MUST** restate in the override every term that still applies. A term the override omits, including `fees`, is not stated for the items it governs.

## Responsibilities

Return policies are business-stated facts. They are response-only data (`ucp_request: omit` on cart, checkout, and order) that a platform never submits; there is no buyer selection and no request-side machinery. They carry no buyer-asserted claims and no PII, so they cross no new trust boundary beyond the base response.

A return policy states the business's own terms. A business **SHOULD** localize them to the buyer where it can, using what the request provides, such as the buyer's `context` or a shipping address, so the terms are those that apply to that buyer. The policy does not describe remedies the buyer may have under applicable law or a third-party guarantee; those are outside this specification.

The return-term fields (`eligibility`, `supported_resolutions`, `methods`, and `fees`) are not an exhaustive statement of the policy's terms. `eligibility`, `supported_resolutions`, and `methods` are guarantees that hold for every eligible return in the policy's scope: within a `window` eligibility, each listed resolution is available through at least one listed method, and each listed method accepts at least one listed resolution (see [Window and anchor](#window-and-anchor)). The lists do not state which resolutions each method accepts; a platform **MUST NOT** present a specific resolution as available through a specific method unless a single method or a single resolution is listed. `fees` is a return term but not a guarantee: it states estimated maximums (see [Return fees](#return-fees)). A business **MAY** describe eligibility requirements, such as tags attached or original packaging, in `description` (see [Eligibility](#eligibility)). A condition the business requires of the item or return, such as unopened, tags attached, or proof of purchase, is an eligibility requirement: the guarantee fields state the terms for returns that meet it, and `description` states the requirement and any terms for returns that don't. A choice the buyer makes at return time, such as the resolution, is not a requirement; the guarantee fields state what holds for every such choice.

A business **SHOULD** populate the fields it can state as guarantees and **MUST NOT** populate a guarantee field with a value that does not hold for every eligible return. It omits such a field when it cannot state the term as a guarantee, and conveys the term in `description` or links to it through `url`. `fees` follows [Return fees](#return-fees) instead. Where a term depends on something known when the response is built, such as the seller, the purchase date, an authenticated buyer's membership, or a selected payment instrument, a business **SHOULD** resolve it, scoping policies with `applies_to` where it differs per item.

A policy's `description` and its structured fields are two representations of the same policy. The `description` **MAY** state better terms than a field (a longer window for one resolution) or the conditions under which a fee applies, but a business **MUST NOT** let it state terms worse for the buyer than a field for the returns that field covers. It is the human-readable summary a platform renders, and the fallback for a platform that does not model the type. A platform **SHOULD** surface `url` alongside the structured terms so the buyer can review the full policy.

A platform that models this type **MAY** present a guaranteed return deadline from `expires_at` (see [Window and anchor](#window-and-anchor)) and **MAY** estimate a return's charges from `fees` (see [Return fees](#return-fees)). It **MUST NOT** treat an elapsed window as making an item non-returnable, since the `description` may allow later returns; only a `not_accepted` eligibility states that its return policy accepts no returns.

## Examples

### Checkout with a default policy and a final-sale override

A response-wide return policy states the standard terms once. An item-scoped `not_accepted` policy marks the engraved line (line 2) as final sale; because it names that line with a singular query (`$.line_items[2]`), it governs it under same-type precedence, outranking any Set match at the same depth, while every other line keeps the default. A paired disclosure compels the final-sale notice to be shown. The default policy's 15% restocking fee is an estimated maximum; its `display_text` names the condition (opened items) under which it applies.

```json
[
  {
    "type": "dev.ucp.shopping.policy.return",
    "description": {
      "plain": "30-day returns from delivery. Refund to original payment or exchange. No return shipping cost in store; $5 by mail. 15% restocking fee on opened items."
    },
    "eligibility": { "type": "window", "duration": "P30D", "anchor": "delivered" },
    "supported_resolutions": ["original_payment_method", "exchange"],
    "methods": ["in_store", "by_mail"],
    "fees": [
      { "type": "dev.ucp.shopping.fee.restocking", "basis_points": 1500, "display_text": "15% restocking fee on opened items" },
      { "amount": 0 },
      { "type": "dev.ucp.shopping.fee.return_shipping", "methods": ["by_mail"], "amount": 500, "display_text": "Return shipping" }
    ],
    "url": "https://example.com/returns"
  },
  {
    "type": "dev.ucp.shopping.policy.return",
    "description": { "plain": "This engraved item is final sale and cannot be returned." },
    "applies_to": ["$.line_items[2]"],
    "eligibility": { "type": "not_accepted" },
    "url": "https://example.com/returns#final-sale"
  }
]
```

The paired disclosure that compels display of the final-sale term:

```json
[
  {
    "type": "warning",
    "code": "dev.ucp.shopping.policy.return",
    "path": "$.line_items[2]",
    "presentation": "disclosure",
    "content": "This engraved item is final sale and cannot be returned."
  }
]
```

### Catalog with a store-credit-only return policy

On a catalog surface, a return policy targets one product whose returns are store credit only, a material purchase-decision factor. Store credit is the only resolution the policy guarantees, and its `description` rules out any other:

```json
[
  {
    "type": "dev.ucp.shopping.policy.return",
    "description": { "plain": "Returns accepted within 30 days for store credit only." },
    "applies_to": ["$.products[0]"],
    "eligibility": { "type": "window", "duration": "P30D", "anchor": "purchased" },
    "supported_resolutions": ["store_credit"]
  }
]
```

### Returns with no time limit

A business accepts returns of items with their tags attached at any time, for store credit. An `unlimited` eligibility states that no time restriction applies, and only that: the tags-attached requirement is stated in the `description`, and the fields alone do not establish that a particular attempted return meets it. Stating `unlimited` differs from omitting `eligibility`, which says nothing structurally about time and leaves a platform to read any window from the `description`:

```json
[
  {
    "type": "dev.ucp.shopping.policy.return",
    "description": { "plain": "Items with tags attached can be returned at any time for store credit." },
    "eligibility": { "type": "unlimited" },
    "supported_resolutions": ["store_credit"]
  }
]
```

### Order after delivery

Once the first line of an order has been delivered, the business resolves its 30-day window and states the deadline as `expires_at`, copying the checkout policy's terms and scoping the copy to that line with `applies_to` so a line delivered later carries its own deadline:

```json
{
  "ucp": {...},
  "id": "order_abc123",
  "checkout_id": "checkout_xyz789",
  "permalink_url": "https://example.com/orders/abc123",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_jacket",
      "item": { "id": "prod_jacket", "title": "Trail Jacket", "price": 12000 },
      "quantity": { "original": 1, "total": 1, "fulfilled": 1 },
      "totals": [...],
      "status": "fulfilled"
    }
  ],
  "fulfillment": {...},
  "totals": [...],
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.return",
      "description": { "plain": "30-day returns from delivery. Refund to original payment method." },
      "applies_to": ["$.line_items[0]"],
      "eligibility": {
        "type": "window",
        "duration": "P30D",
        "anchor": "delivered",
        "expires_at": "2026-04-01T18:00:00Z"
      },
      "supported_resolutions": ["original_payment_method"],
      "url": "https://example.com/returns"
    }
  ]
}
```
