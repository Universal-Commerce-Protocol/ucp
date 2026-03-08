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

The fee extension allows businesses to surface itemized fees on checkout sessions
and carts, providing transparency into surcharges beyond the item subtotal.

**Key features:**

- Itemized fees with human-readable titles and descriptions
- Typed fees with open `fee_type` string for extensibility
- Allocation breakdown showing how fees map to specific targets
- Taxability and waivability metadata
- Supported on both Checkout and Cart

**Dependencies:**

- Checkout Capability and/or Cart Capability

## Discovery

Businesses advertise fee support in their profile. The extension can extend
checkout, cart, or both:

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

## Schema

When this capability is active, checkout and/or cart is extended with a `fees`
object.

### Fees Object

{{ extension_schema_fields('fee.json#/$defs/fees_object', 'fee') }}

### Fee

{{ schema_fields('types/fee', 'fee') }}

### Allocation

{{ extension_schema_fields('discount.json#/$defs/allocation', 'fee') }}

## Fee Semantics

### Fees vs Other Total Types

Fees are distinct from other components of the order total:

| Total Type    | Purpose                                                     |
| ------------- | ----------------------------------------------------------- |
| `subtotal`    | Sum of line item prices before adjustments                  |
| `discount`    | Reductions applied via codes or promotions                  |
| `fulfillment` | Shipping, delivery, or pickup costs                         |
| `tax`         | Government-imposed taxes                                    |
| `fee`         | Business-imposed surcharges and fees                        |
| `total`       | Final amount: subtotal - discount + fulfillment + tax + fee |

Fees represent charges imposed by the business (not the government). Unlike
taxes, fees are business-determined and may be waivable.

### Fee Types

The `fee_type` field is an **open string** — businesses MAY use any value.
Platforms SHOULD handle unknown values gracefully by displaying the fee `title`
to the user.

**Well-known values:**

| Fee Type        | Description                                        |
| --------------- | -------------------------------------------------- |
| `service`       | Service or platform fee                            |
| `handling`      | Order handling and processing fee                  |
| `recycling`     | Recycling or disposal fee                          |
| `processing`    | Payment processing surcharge                       |
| `regulatory`    | Regulatory compliance fee                          |
| `convenience`   | Convenience fee (e.g., online ordering surcharge)  |
| `restocking`    | Restocking fee for returns or exchanges            |
| `environmental` | Environmental or sustainability surcharge          |

## Multiple Fees

Businesses MAY apply multiple fees to a single checkout or cart. Each fee
appears as a separate entry in `fees.applied[]`.

**Invariants:**

- `totals[type=fee].amount` equals `sum(fees.applied[].amount)`
- Each fee's `allocations[].amount` sums to the fee's `amount`
- All amounts are positive integers in minor currency units

## Operations

Fees are entirely **business-determined**. Platforms cannot submit, modify, or
remove fees — they are read-only in all operations (`ucp_request: "omit"` for
create, update, and complete).

Fees appear in the response whenever the business determines they apply based on
cart contents, fulfillment method, buyer location, or other business rules.

## Rendering Guidance

Platforms SHOULD:

- Display each fee as a separate line in the order summary
- Use the fee `title` as the display label
- Show the fee `description` when available (tooltip or expandable detail)
- Sum all fees into a single `totals[type=fee]` entry for the total calculation
- Display fees as additive amounts (not subtractive like discounts)

**Example rendering:**

```text
Subtotal                    $50.00
Shipping                     $5.99
Service Fee                  $2.50
Recycling Fee                $0.75
Tax                          $4.74
                           -------
Total                       $63.98
```

## Calculation Formula

The total is calculated as:

```text
total = subtotal - discount + fulfillment + tax + fee
```

Where `fee` is the sum of all applied fees. This is consistent with the
existing formula documented in the `total.json` schema.

## Multi-Level Fee Support

Fees can be applied at multiple levels of the order:

### Checkout-Level Fees

Fees that apply to the entire order (e.g., a service fee or platform fee).
These appear in `fees.applied[]` at the checkout/cart root level with no
allocations, or with allocations that span multiple targets.

### Line-Item-Level Fees

Fees allocated to specific line items (e.g., recycling fee per item). These
use `allocations[]` with JSONPath references to line items:

```json
{
  "id": "fee_recycling",
  "title": "Recycling Fee",
  "amount": 150,
  "fee_type": "recycling",
  "allocations": [
    {"path": "$.line_items[0]", "amount": 100},
    {"path": "$.line_items[1]", "amount": 50}
  ]
}
```

### Fulfillment-Option-Level Fees

Fees tied to a specific fulfillment option (e.g., handling fee for express
shipping). These use `allocations[]` referencing fulfillment structures:

```json
{
  "id": "fee_handling",
  "title": "Express Handling Fee",
  "amount": 299,
  "fee_type": "handling",
  "allocations": [
    {"path": "$.fulfillment.methods[0].groups[0].options[0]", "amount": 299}
  ]
}
```

## Interaction with Discounts

Fees and discounts are independent extensions that can coexist. When both are
active:

- Discounts reduce the order total; fees increase it
- The calculation order is: `subtotal - discount + fulfillment + tax + fee`
- Discounts do NOT apply to fees unless the business explicitly allocates a
  discount to a fee target
- The `waivable` flag on a fee indicates the business may remove it under
  certain conditions (e.g., loyalty membership), but this is business logic —
  not controlled by the platform

## Examples

### Simple service fee

A single service fee on a checkout:

**Response:**

```json
{
  "fees": {
    "applied": [
      {
        "id": "fee_service",
        "title": "Service Fee",
        "amount": 250,
        "fee_type": "service"
      }
    ]
  },
  "totals": [
    {"type": "subtotal", "display_text": "Subtotal", "amount": 5000},
    {"type": "fee", "display_text": "Service Fee", "amount": 250},
    {"type": "total", "display_text": "Total", "amount": 5250}
  ]
}
```

### Multiple fees

Multiple fees of different types:

**Response:**

```json
{
  "fees": {
    "applied": [
      {
        "id": "fee_service",
        "title": "Service Fee",
        "amount": 250,
        "fee_type": "service",
        "waivable": true
      },
      {
        "id": "fee_recycling",
        "title": "Electronics Recycling Fee",
        "amount": 75,
        "fee_type": "recycling",
        "description": "State-mandated electronics recycling fee",
        "taxable": true
      }
    ]
  },
  "totals": [
    {"type": "subtotal", "display_text": "Subtotal", "amount": 5000},
    {"type": "fee", "display_text": "Fees", "amount": 325},
    {"type": "tax", "display_text": "Tax", "amount": 406},
    {"type": "total", "display_text": "Total", "amount": 5731}
  ]
}
```

### Fee with allocations

A recycling fee allocated across line items:

**Response:**

```json
{
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "prod_laptop",
        "quantity": 1,
        "title": "Laptop",
        "price": 99900
      }
    },
    {
      "id": "li_2",
      "item": {
        "id": "prod_phone",
        "quantity": 1,
        "title": "Phone",
        "price": 49900
      }
    }
  ],
  "fees": {
    "applied": [
      {
        "id": "fee_recycling",
        "title": "Electronics Recycling Fee",
        "amount": 500,
        "fee_type": "recycling",
        "taxable": true,
        "allocations": [
          {"path": "$.line_items[0]", "amount": 300},
          {"path": "$.line_items[1]", "amount": 200}
        ]
      }
    ]
  },
  "totals": [
    {"type": "subtotal", "display_text": "Subtotal", "amount": 149800},
    {"type": "fee", "display_text": "Recycling Fee", "amount": 500},
    {"type": "tax", "display_text": "Tax", "amount": 12024},
    {"type": "total", "display_text": "Total", "amount": 162324}
  ]
}
```

### Fees in cart

Fees also work in cart responses, providing estimated surcharges before checkout:

**Response:**

```json
{
  "id": "cart_abc123",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "prod_1",
        "quantity": 2,
        "title": "Widget",
        "price": 1500
      }
    }
  ],
  "fees": {
    "applied": [
      {
        "id": "fee_convenience",
        "title": "Online Ordering Fee",
        "amount": 199,
        "fee_type": "convenience",
        "waivable": true,
        "description": "Waived for loyalty members"
      }
    ]
  },
  "currency": "USD",
  "totals": [
    {"type": "subtotal", "display_text": "Subtotal", "amount": 3000},
    {"type": "fee", "display_text": "Convenience Fee", "amount": 199},
    {"type": "total", "display_text": "Estimated Total", "amount": 3199}
  ]
}
```
