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

# Fee Extension

## Overview

The Fee Extension allows businesses to surface itemized fees on checkout
sessions and carts, giving platforms and agents full visibility into surcharges
such as service fees, handling charges, regulatory fees, and other additional
costs beyond the item subtotal.

**Key features:**

- Itemized fees with human-readable titles and descriptions
- Typed fees with an open `fee_type` string for extensibility
- Allocation breakdowns showing how fees are distributed across line items
- Taxability and waivability metadata per fee
- Supported on both Checkout and Cart

**Dependencies:**

- Checkout Capability and/or Cart Capability

## Discovery

Businesses advertise fee support in their profile. The `extends` field uses the
multi-parent array form to declare which base capabilities the fee extension
augments:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": {
      "dev.ucp.shopping.fee": [
        {
          "version": "2026-01-11",
          "extends": ["dev.ucp.shopping.checkout", "dev.ucp.shopping.cart"],
          "spec": "https://ucp.dev/specification/fee",
          "schema": "https://ucp.dev/schemas/shopping/fee.json"
        }
      ]
    }
  }
}
```

!!! note "Partial adoption"
    A business MAY support fees on checkout only, cart only, or both. When
    extending only one parent, use a single-element array or a plain string.
    Platforms should check which base capabilities the fee extension extends
    before expecting `fees` in responses.

## Schema

When this capability is active, checkout and/or cart responses are extended with
a `fees` object.

### Fees Object

{{ extension_schema_fields('fee.json#/$defs/fees_object', 'fee') }}

### Fee

{{ schema_fields('types/fee', 'fee') }}

### Allocation

{{ schema_fields('types/allocation', 'fee') }}

## Fee Semantics

### Relationship to Totals

Fees surface in two places: the `fees.applied` array provides the itemized
breakdown, while `totals[]` contains a single aggregated entry that rolls all
fees into the order total calculation.

| Total Type       | Description                                                   |
| ---------------- | ------------------------------------------------------------- |
| `subtotal`       | Sum of line item prices before any adjustments                |
| `items_discount` | Discounts allocated to line items                             |
| `discount`       | Order-level discounts (shipping, flat amount)                 |
| `fulfillment`    | Shipping, delivery, or pickup costs                           |
| `tax`            | Tax amount                                                    |
| `fee`            | **Single aggregated fee total** — sum of all `fees.applied[]` |
| `total`          | Grand total: `subtotal - discount + fulfillment + tax + fee`  |

**Invariant:** `totals[type=fee].amount` equals `sum(fees.applied[].amount)`.
Businesses MUST ensure this invariant holds. If a platform detects a mismatch
between the aggregated fee total and the sum of itemized fees, the platform
SHOULD treat the response as potentially invalid and SHOULD surface the
discrepancy to the user. Platforms MAY use `continue_url` to hand off to the
business UI for resolution rather than attempting to complete the checkout with
inconsistent fee data.

!!! note "When the Fee Extension is absent"
    When the Fee Extension is present, there MUST be at most one `totals[]`
    entry with `type: "fee"`, and its `amount` MUST equal
    `sum(fees.applied[].amount)`. When the Fee Extension is not advertised,
    the interpretation of any `totals[type=fee]` entry is business-defined —
    platforms SHOULD render it using `display_text` but MUST NOT assume
    itemized fee data is available.

### Fee Types

The `fee_type` field is an open string. Businesses MAY use any value, including
custom types not listed below. Platforms SHOULD handle unknown values gracefully
by displaying the fee's `title` to the user.

**Well-known values:**

| Fee Type        | Description                                      | Example                            |
| --------------- | ------------------------------------------------ | ---------------------------------- |
| `service`       | General service fee for order processing         | Platform service fee               |
| `handling`      | Physical handling and packaging of goods         | Oversized item handling fee        |
| `recycling`     | Disposal or recycling of materials               | Electronics recycling fee          |
| `processing`    | Payment or order processing surcharge            | Credit card processing fee         |
| `regulatory`    | Government-mandated fee or compliance charge     | Mattress recycling surcharge       |
| `convenience`   | Fee for using a particular ordering channel      | Online ordering convenience fee    |
| `restocking`    | Fee for processing returns or exchanges          | Return restocking fee              |
| `environmental` | Environmental impact or sustainability surcharge | Carbon offset fee                  |

### Why `id` Is Required

Unlike applied discounts — where `code` serves as a natural key and automatic
discounts may not need a stable identifier — fees are entirely
business-determined and read-only. Platforms need a reliable way to reference
individual fees across checkout updates (e.g., to track which fees changed
between updates or to display consistent UI elements). Therefore, `id` is
required on every fee.

Fee IDs are scoped to a single checkout or cart session. The same fee retains
its `id` across requests within a session (create → update → complete), but the
`id` is not guaranteed to be consistent across separate sessions. Businesses
control ID generation.

## Multiple Fees

A checkout or cart may include multiple fees. The following invariants hold:

1. **Single aggregated total:** There SHOULD be exactly one `totals[]` entry
   with `type: "fee"` whose `amount` equals the sum of all `fees.applied[]`
   amounts.

2. **Allocation sums:** When a fee includes `allocations`, the sum of
   `allocations[].amount` MUST equal the fee's `amount`.

3. **Positive amounts only:** All fee amounts use `exclusiveMinimum: 0` —
   zero-amount fees are not permitted. If a fee does not apply, it MUST be
   omitted from the `applied` array entirely. This includes waived fees: when a
   fee marked `waivable: true` is actually waived, the business omits it rather
   than including a zero-amount entry.

4. **Communicating waived fees:** To inform the platform and user that a fee was
   waived, businesses MAY include a `messages[]` entry with `type: "info"`:

    ```json
    {
      "messages": [
        {
          "type": "info",
          "code": "fee_waived",
          "content": "Service Fee waived for loyalty members."
        }
      ]
    }
    ```

## Operations

Fees are fully read-only. The `fees` object uses `ucp_request: "omit"` for all
operations, meaning platforms never send fee data in requests — fees are
determined entirely by the business and returned in responses.

Business receivers MUST reject any `fees` fields provided by platforms in
requests. Because fees directly affect money movement, silently ignoring
client-supplied fee data is insufficient — an explicit error response prevents
parameter-smuggling attacks where a platform attempts to influence fee amounts.
Businesses SHOULD use the `readonly_field_not_allowed` error code when rejecting
such requests.

**Checkout operations:**

| Operation  | `fees` in Request | `fees` in Response |
| ---------- | ----------------- | ------------------ |
| `create`   | Omit              | Present            |
| `update`   | Omit              | Present            |
| `complete` | Omit              | Present            |

**Cart operations:**

| Operation | `fees` in Request | `fees` in Response |
| --------- | ----------------- | ------------------ |
| `create`  | Omit              | Present            |
| `update`  | Omit              | Present            |

!!! note "Cart vs. Checkout"
    Cart has no `complete` operation (carts are converted to checkouts before
    completion), so only `create` and `update` are specified as "omit".

## Rendering Guidance

Platforms SHOULD display each fee as a separate line item in the order summary,
using the fee's `title` for display.

!!! warning "Sanitization"
    Fee `title`, `description`, and totals `display_text` fields are plain text.
    Renderers MUST escape or sanitize these values before inserting them into
    HTML, logs, or other output contexts to prevent markup injection or XSS.

Example text rendering:

```text
Order Summary
─────────────────────────────
  Subtotal                $120.00
  Shipping                  $8.99
  Service Fee               $3.99
  Recycling Fee             $1.50
  Tax                       $9.60
  ─────────────────────────
  Total                   $144.08
```

When a fee includes a `description`, platforms MAY display it as supplementary
text (e.g., a tooltip or fine print) to help users understand why the fee is
charged. The `description` field is plain text — for richer content such as
regulatory disclosures, images, or formatted copy, businesses should use the
Disclosures capability (see [#222](https://github.com/Universal-Commerce-Protocol/ucp/issues/222))
when available.

If a fee has `waivable: true`, platforms MAY indicate this to the user (e.g.,
"This fee is waived for members").

## Calculation Formula

The grand total follows the standard UCP calculation:

```text
total = subtotal - discount + fulfillment + tax + fee
```

Where `fee` is the single aggregated fee total amount from `totals[type=fee]`.

## Multi-Level Fee Support

Fees can apply at different levels of an order, expressed through the
`allocations` array.

### Checkout-Level Fees

Fees without allocations apply to the order as a whole:

```json
{
  "id": "fee_svc_1",
  "title": "Service Fee",
  "amount": 399,
  "fee_type": "service"
}
```

### Line-Item-Level Fees

Fees allocated to specific line items use JSONPath in `allocations`:

```json
{
  "id": "fee_recycle_1",
  "title": "Recycling Fee",
  "amount": 300,
  "fee_type": "recycling",
  "allocations": [
    { "path": "$.line_items[0]", "amount": 150 },
    { "path": "$.line_items[1]", "amount": 150 }
  ]
}
```

### Fulfillment-Option-Level Fees

Fees allocated to fulfillment options:

```json
{
  "id": "fee_handling_1",
  "title": "Oversized Handling Fee",
  "amount": 1500,
  "fee_type": "handling",
  "allocations": [
    { "path": "$.fulfillment.options[0]", "amount": 1500 }
  ]
}
```

## Interaction with Discounts

The Fee Extension and Discount Extension are independent extensions that can
coexist on the same checkout or cart. Key rules:

- **Independent calculation:** Fees and discounts are calculated independently.
  A discount does not reduce fees, and a fee does not increase the discount
  base, unless the business explicitly structures it that way.

- **Separate totals entries:** Fees appear in `totals[type=fee]` and discounts
  in `totals[type=discount]` (or `totals[type=items_discount]`). They are never
  combined into a single entry.

- **Waivable fees:** The `waivable` flag indicates a fee *can* be waived under
  certain conditions (e.g., membership tier, promotional period). The waivability
  is informational — when a fee is actually waived, the business simply omits it
  from the `fees.applied` array. The flag helps platforms communicate potential
  savings to users.

- **Grand total formula remains the same:**
  `total = subtotal - discount + fulfillment + tax + fee`

## Examples

### Simple Service Fee

A single service fee with no allocations.

**Request:**

```json
{
  "line_items": [
    {
      "item": {
        "id": "prod_1",
        "quantity": 1
      }
    }
  ]
}
```

**Response:**

```json
{
  "id": "chk_abc123",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "prod_1",
        "quantity": 1,
        "title": "Wireless Headphones",
        "price": 7999
      }
    }
  ],
  "fees": {
    "applied": [
      {
        "id": "fee_svc_1",
        "title": "Service Fee",
        "amount": 399,
        "fee_type": "service"
      }
    ]
  },
  "totals": [
    { "type": "subtotal", "display_text": "Subtotal", "amount": 7999 },
    { "type": "fee", "display_text": "Service Fee", "amount": 399 },
    { "type": "tax", "display_text": "Tax", "amount": 672 },
    { "type": "total", "display_text": "Total", "amount": 9070 }
  ]
}
```

### Multiple Fees

Service fee and recycling fee, with a single aggregated `totals[type=fee]`
entry.

**Request:**

```json
{
  "line_items": [
    {
      "item": {
        "id": "prod_tv",
        "quantity": 1
      }
    }
  ]
}
```

**Response:**

```json
{
  "id": "chk_def456",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "prod_tv",
        "quantity": 1,
        "title": "55\" 4K Television",
        "price": 49999
      }
    }
  ],
  "fees": {
    "applied": [
      {
        "id": "fee_svc_1",
        "title": "Service Fee",
        "amount": 999,
        "fee_type": "service"
      },
      {
        "id": "fee_recycle_1",
        "title": "Electronics Recycling Fee",
        "amount": 500,
        "fee_type": "recycling",
        "taxable": true,
        "description": "State-mandated electronics recycling fee."
      }
    ]
  },
  "totals": [
    { "type": "subtotal", "display_text": "Subtotal", "amount": 49999 },
    { "type": "fulfillment", "display_text": "Shipping", "amount": 0 },
    { "type": "fee", "display_text": "Fees", "amount": 1499 },
    { "type": "tax", "display_text": "Tax", "amount": 4080 },
    { "type": "total", "display_text": "Total", "amount": 55578 }
  ]
}
```

### Fee with Allocations

A recycling fee split across two line items.

**Request:**

```json
{
  "line_items": [
    {
      "item": {
        "id": "prod_battery_1",
        "quantity": 2
      }
    },
    {
      "item": {
        "id": "prod_battery_2",
        "quantity": 1
      }
    }
  ]
}
```

**Response:**

```json
{
  "id": "chk_ghi789",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "prod_battery_1",
        "quantity": 2,
        "title": "AA Battery Pack (8ct)",
        "price": 899
      }
    },
    {
      "id": "li_2",
      "item": {
        "id": "prod_battery_2",
        "quantity": 1,
        "title": "9V Battery Pack (4ct)",
        "price": 1299
      }
    }
  ],
  "fees": {
    "applied": [
      {
        "id": "fee_recycle_1",
        "title": "Battery Recycling Fee",
        "amount": 150,
        "fee_type": "recycling",
        "taxable": true,
        "allocations": [
          { "path": "$.line_items[0]", "amount": 100 },
          { "path": "$.line_items[1]", "amount": 50 }
        ]
      }
    ]
  },
  "totals": [
    { "type": "subtotal", "display_text": "Subtotal", "amount": 3097 },
    { "type": "fee", "display_text": "Recycling Fee", "amount": 150 },
    { "type": "tax", "display_text": "Tax", "amount": 260 },
    { "type": "total", "display_text": "Total", "amount": 3507 }
  ]
}
```

### Fees in Cart

A convenience fee applied to a cart response.

**Request:**

```json
{
  "line_items": [
    {
      "item": {
        "id": "prod_pizza",
        "quantity": 2
      }
    },
    {
      "item": {
        "id": "prod_soda",
        "quantity": 3
      }
    }
  ]
}
```

**Response:**

```json
{
  "id": "cart_jkl012",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "prod_pizza",
        "quantity": 2,
        "title": "Large Pepperoni Pizza",
        "price": 1499
      }
    },
    {
      "id": "li_2",
      "item": {
        "id": "prod_soda",
        "quantity": 3,
        "title": "Cola (2L)",
        "price": 299
      }
    }
  ],
  "currency": "USD",
  "fees": {
    "applied": [
      {
        "id": "fee_conv_1",
        "title": "Online Ordering Fee",
        "amount": 299,
        "fee_type": "convenience",
        "waivable": true,
        "description": "Waived for loyalty members."
      }
    ]
  },
  "totals": [
    { "type": "subtotal", "display_text": "Subtotal", "amount": 3895 },
    { "type": "fee", "display_text": "Online Ordering Fee", "amount": 299 },
    { "type": "total", "display_text": "Estimated Total", "amount": 4194 }
  ]
}
```

!!! note "Read-only"
    The request does not include `fees` in any of the above examples. This
    demonstrates the read-only nature of the fee extension — fees are determined
    entirely by the business and returned in responses.
