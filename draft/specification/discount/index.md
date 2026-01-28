# Discount Extension

## Overview

Discount extension allows businesses to indicate that they support discount codes on checkout sessions, and specifies how the discount codes are to be shared between the platform and the business.

**Key features:**

- Submit one or more discount codes
- Receive applied discounts with human-readable titles and amounts
- Rejected codes communicated via `messages[]` with detailed error codes
- Automatic discounts surfaced alongside code-based discounts

**Dependencies:**

- Checkout Capability

## Discovery

Businesses advertise discount support in their profile:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": {
      "dev.ucp.shopping.discount": [
        {
          "version": "2026-01-11",
          "extends": "dev.ucp.shopping.checkout",
          "spec": "https://ucp.dev/specification/discount",
          "schema": "https://ucp.dev/schemas/shopping/discount.json"
        }
      ]
    }
  }
}
```

## Schema

When this capability is active, checkout is extended with a `discounts` object.

### Discounts Object

**Error:** Schema file 'discount_resp.json' not found in any schema directory.

### Applied Discount

**Error:** Schema file 'discount_resp.json' not found in any schema directory.

### Allocation

**Error:** Schema file 'discount_resp.json' not found in any schema directory.

## Allocation Details

The `applied` array explains how discounts were calculated and distributed.

### Allocation Method

The `method` field indicates how the discount was calculated:

| Method   | Meaning                                 | Example                                          |
| -------- | --------------------------------------- | ------------------------------------------------ |
| `each`   | Applied independently per eligible item | "10% off each item" → 10% × item price           |
| `across` | Split proportionally by value           | "$10 off order" → $6 to $60 item, $4 to $40 item |

### Stacking Order

When multiple discounts are applied, `priority` indicates the calculation order. Lower numbers are applied first:

```text
Cart: $100
Discount A (priority: 1): 20% off → $100 × 0.8 = $80
Discount B (priority: 2): $10 off → $80 - $10 = $70
```

The order matters because percentage discounts compound differently depending on when they're applied.

### Allocations Array

The `allocations` array breaks down where each discount dollar landed, using JSONPath to identify targets:

| Path Pattern        | Target           |
| ------------------- | ---------------- |
| `$.line_items[0]`   | First line item  |
| `$.line_items[1]`   | Second line item |
| `$.totals.shipping` | Shipping cost    |

This enables platforms to explain exactly how much each discount contributed to each line item, even when multiple discounts stack.

**Invariant:** Sum of `allocations[].amount` equals `applied_discount.amount`.

## Operations

Discount codes are submitted via standard checkout create/update operations.

**Request behavior:**

- **Replacement semantics**: Submitting `discounts.codes` replaces any previously submitted codes
- **Clear codes**: Send empty array `"codes": []` to remove all discount codes
- **Case-insensitive**: Codes are matched case-insensitively by business

**Response behavior:**

- `discounts.applied` contains all active discounts (code-based + automatic)
- Rejected codes communicated via `messages[]` (see below)
- Discount amounts reflected in `totals[]` and `line_items[].discount`

## Rejected Codes

When a submitted discount code cannot be applied, businesses communicate this via the `messages[]` array:

```json
{
  "messages": [
    {
      "type": "warning",
      "code": "discount_code_expired",
      "path": "$.discounts.codes[0]",
      "content": "Code 'SUMMER20' expired on December 1st"
    }
  ]
}
```

> **Implementation guidance:** Operations that affect order totals, or the user's expectation of the total, **SHOULD** use `type: "warning"` to ensure they are surfaced to the user rather than silently handled by platforms. Rejected discounts are a prime example—the user expects a discount but won't receive it, so they should be informed.

**Error codes for rejected discounts:**

| Code                                   | Description                                 |
| -------------------------------------- | ------------------------------------------- |
| `discount_code_expired`                | Code has expired                            |
| `discount_code_invalid`                | Code not found or malformed                 |
| `discount_code_already_applied`        | Code is already applied                     |
| `discount_code_combination_disallowed` | Cannot combine with another active discount |
| `discount_code_user_not_logged_in`     | Code requires authenticated user            |
| `discount_code_user_ineligible`        | User does not meet eligibility criteria     |

## Automatic Discounts

Businesses may apply discounts automatically based on cart contents, customer segment, or promotional rules:

- Appear in `discounts.applied` with `automatic: true` and no `code` field
- Applied without platform action
- Cannot be removed by the platform
- Surfaced for transparency (platform can explain to user why discount was applied)

## Impact on Line Items and Totals

Applied discounts are reflected in the core checkout fields using two distinct total types:

| Total Type       | When to Use                                               |
| ---------------- | --------------------------------------------------------- |
| `items_discount` | Discounts allocated to line items (`$.line_items[*]`)     |
| `discount`       | Order-level discounts (shipping, fees, flat order amount) |

**Determining the type:** If a discount has `allocations` pointing to line items, it contributes to `items_discount`. Discounts without allocations, or with allocations to shipping/fees, contribute to `discount`.

| Discount Type        | Where Reflected                            |
| -------------------- | ------------------------------------------ |
| Line-item discount   | `line_items[].discount` + `items_discount` |
| Order-level discount | `totals[]` with `type: "discount"`         |

**Invariant:** `totals[type=items_discount].amount` equals `sum(line_items[].discount)`.

The `discounts.applied` array shows **what** was applied. The `totals[]` and `line_items[].discount` show **where** and **how much**.

**Amount convention:** All discount amounts are positive integers in minor currency units. When presenting totals to users, display discount types as subtractive (e.g., "-$13.99").

## Examples

### Order-level discount

A flat discount applied to the order total. No allocations—the discount applies to the order as a whole and uses `type: "discount"` in totals.

**Request:**

```json
{
  "discounts": {
    "codes": ["SAVE10"]
  }
}
```

**Response:**

```json
{
  "discounts": {
    "codes": ["SAVE10"],
    "applied": [
      {
        "code": "SAVE10",
        "title": "$10 Off Your Order",
        "amount": 1000
      }
    ]
  },
  "totals": [
    {"type": "subtotal", "display_text": "Subtotal", "amount": 5000},
    {"type": "discount", "display_text": "Order Discount", "amount": 1000},
    {"type": "total", "display_text": "Total", "amount": 4000}
  ]
}
```

### Mixed discounts (item + order level)

This example shows both discount types: a per-item discount (20% off) allocated to line items, and an automatic shipping discount at the order level.

**Request:**

```json
{
  "discounts": {
    "codes": ["SUMMER20"]
  }
}
```

**Response:**

```json
{
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "prod_1",
        "quantity": 2,
        "title": "T-Shirt",
        "price": 2000
      },
      "totals": [
        {"type": "subtotal", "amount": 4000},
        {"type": "items_discount", "amount": 800},
        {"type": "total", "amount": 3200}
      ]
    }
  ],
  "discounts": {
    "codes": ["SUMMER20"],
    "applied": [
      {
        "code": "SUMMER20",
        "title": "Summer Sale 20% Off",
        "amount": 800,
        "allocations": [
          {"path": "$.line_items[0]", "amount": 800}
        ]
      },
      {
        "title": "Free shipping on orders over $30",
        "amount": 599,
        "automatic": true
      }
    ]
  },
  "totals": [
    {"type": "subtotal", "display_text": "Subtotal", "amount": 4000},
    {"type": "items_discount", "display_text": "Item Discounts", "amount": 800},
    {"type": "discount", "display_text": "Order Discounts", "amount": 599},
    {"type": "fulfillment", "display_text": "Shipping", "amount": 0},
    {"type": "total", "display_text": "Total", "amount": 2601}
  ]
}
```

### Rejected discount code

When a discount code cannot be applied, the rejection is communicated via the `messages[]` array. The code still appears in `discounts.codes` (echoed back) but not in `discounts.applied`.

**Request:**

```json
{
  "discounts": {
    "codes": ["SAVE10", "EXPIRED50"]
  }
}
```

**Response:**

```json
{
  "discounts": {
    "codes": ["SAVE10", "EXPIRED50"],
    "applied": [
      {
        "code": "SAVE10",
        "title": "$10 Off Your Order",
        "amount": 1000
      }
    ]
  },
  "totals": [
    {"type": "subtotal", "display_text": "Subtotal", "amount": 5000},
    {"type": "discount", "display_text": "Order Discount", "amount": 1000},
    {"type": "total", "display_text": "Total", "amount": 4000}
  ],
  "messages": [
    {
      "type": "warning",
      "code": "discount_code_expired",
      "path": "$.discounts.codes[1]",
      "content": "Code 'EXPIRED50' expired on December 1st"
    }
  ]
}
```

### Stacked discounts with allocations

Multiple discounts applied with full allocation breakdown:

**Response:**

```json
{
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "title": "T-Shirt",
        "price": 6000
      },
      "totals": [
        {"type": "subtotal", "amount": 6000},
        {"type": "items_discount", "amount": 1500},
        {"type": "total", "amount": 4500}
      ]
    },
    {
      "id": "li_2",
      "item": {
        "title": "Socks",
        "price": 4000
      },
      "totals": [
        {"type": "subtotal", "amount": 4000},
        {"type": "items_discount", "amount": 1000},
        {"type": "total", "amount": 3000}
      ]
    }
  ],
  "discounts": {
    "codes": ["SUMMER20", "LOYALTY5"],
    "applied": [
      {
        "code": "SUMMER20",
        "title": "Summer Sale 20% Off",
        "amount": 2000,
        "method": "each",
        "priority": 1,
        "allocations": [
          {"path": "$.line_items[0]", "amount": 1200},
          {"path": "$.line_items[1]", "amount": 800}
        ]
      },
      {
        "code": "LOYALTY5",
        "title": "$5 Loyalty Reward",
        "amount": 500,
        "method": "across",
        "priority": 2,
        "allocations": [
          {"path": "$.line_items[0]", "amount": 300},
          {"path": "$.line_items[1]", "amount": 200}
        ]
      }
    ]
  },
  "totals": [
    {"type": "subtotal", "display_text": "Subtotal", "amount": 10000},
    {"type": "items_discount", "display_text": "Item Discounts", "amount": 2500},
    {"type": "total", "display_text": "Total", "amount": 7500}
  ]
}
```

With this data, an agent can explain:

> "Your T-Shirt ($60) got $12 off from the 20% summer sale, plus $3 from your
