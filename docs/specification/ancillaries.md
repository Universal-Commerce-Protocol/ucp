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

# Ancillaries Extension

## Overview

The ancillaries extension allows businesses to offer additional goods and
services related to items in a checkout. This includes insurance/protection
plans, complementary products (cables, accessories), and services (installation,
setup).

**Key features:**

- Suggest ancillaries related to specific line items or the overall checkout
- Support for different categories: products, services, insurance
- Handle ancillaries that require buyer input (e.g., time slot selection,
  personalization)
- Group mutually exclusive alternatives (e.g., warranty tiers)
- Automatic ancillaries for legally required or promotional additions

**Dependencies:**

- Checkout Capability

## Discovery

Businesses advertise ancillaries support in their profile:

```json
{
    "ucp": {
        "version": "2026-02-17",
        "capabilities": {
            "dev.ucp.shopping.ancillaries": [
                {
                    "version": "2026-02-17",
                    "extends": "dev.ucp.shopping.checkout",
                    "spec": "https://ucp.dev/specification/ancillaries",
                    "schema": "https://ucp.dev/schemas/shopping/ancillaries.json"
                }
            ]
        }
    }
}
```

## Schema

When this capability is active, checkout is extended with an `ancillaries`
object.

### Ancillaries Object

{{ extension_schema_fields('ancillaries.json#/$defs/ancillaries_object', 'ancillaries') }}

### Ancillary Suggestion

{{ extension_schema_fields('ancillaries.json#/$defs/ancillary_suggestion', 'ancillaries') }}

### Applied Ancillary

{{ extension_schema_fields('ancillaries.json#/$defs/applied_ancillary', 'ancillaries') }}

**Invariant:** If `automatic = true` then `reason_code` must be set.

### Ancillary Input Schema

{{ extension_schema_fields('ancillaries.json#/$defs/ancillary_input_schema', 'ancillaries') }}

## Categories

Ancillaries are categorized to help platforms render appropriate UI and set
buyer expectations:

| Category    | Description                   | Examples                            |
| ----------- | ----------------------------- | ----------------------------------- |
| `product`   | Physical or digital goods     | Cables, cases, accessories          |
| `service`   | One-time services             | Installation, setup, gift wrapping  |
| `insurance` | Protection and warranty plans | Extended warranty, theft protection |

## Suggestion Types

The `type` field indicates the relationship between the ancillary and the
checkout:

| Type            | Description                                      | Use Case                           |
| --------------- | ------------------------------------------------ | ---------------------------------- |
| `complementary` | Directly related to a specific line item         | Charging cable for a phone         |
| `suggested`     | General recommendation for the checkout          | "Customers also bought" items      |
| `required`      | Legally or functionally required for a line item | Recycling fee, mandatory insurance |

## Input Handling

Some ancillaries require buyer input before they can be added. The
`requires_input` flag and `input_schema` fields enable this:

### Input Types

| Type        | Description                    | Example                                      |
| ----------- | ------------------------------ | -------------------------------------------- |
| `text`      | Free-form text input           | Engraving text, gift message                 |
| `selection` | Choice from predefined options | Time slots, service tiers, color preferences |

The `selection` type uses the `options` array. Platforms can render
appropriately based on the option content (e.g., calendar-style UI for time
slots, dropdowns for service tiers).

### Input Flow

1. Business returns suggestion with `requires_input: true` and `input_schema`
2. Platform presents input UI based on `input_schema`
3. Platform submits ancillary with `input` containing buyer's response
4. Business validates input and applies ancillary

When input is invalid, businesses communicate this via the `messages[]` array
with appropriate error codes.

## Mutually Exclusive Alternatives

Use `group_id` to indicate ancillaries that are mutually exclusive **products**.
Each grouped ancillary is a distinct SKU with its own price, title, and details.
Platforms **SHOULD** present grouped ancillaries as a radio-style selection
where only one can be chosen.

**When to use `group_id`:**

- Each option is a **separate product** with its own SKU and price
- Options have significantly different attributes (coverage, duration, features)
- The selected option becomes its own line item in the checkout

**When to use `input_schema.selection` instead:**

- Options are **configuration of a single product** (e.g., color, size)
- The base product is the same regardless of selection
- Options don't have independent pricing

**Common `group_id` use cases:**

- Warranty tiers (1-year at $99 vs 2-year at $149 — different SKUs)
- Insurance coverage levels (basic vs comprehensive — different products)
- Service packages (standard installation vs premium installation)

## Operations

Ancillaries are submitted via standard checkout create/update operations.

**Request behavior:**

- **Replacement semantics**: Submitting `ancillaries.items` replaces any
  previously added ancillaries
- **Clear ancillaries**: Send empty array `"ancillaries": { "items": [] }` to
  remove all non-automatic ancillaries
- **Input required**: Include `input` field when adding ancillaries with
  `requires_input: true`

**Invariant:** For relational ancillaries, `ancillaries.items[x].quantity` where
`ancillaries.items[x].for == line_item_id` **MUST** equal
`line_items[y].quantity` where `line_items[y].id == line_item_id`.

**Response behavior:**

- `ancillaries.suggested` contains available suggestions
- `ancillaries.applied` contains all active ancillaries (user-submitted and
  automatic)
- Applied ancillaries also appear in the checkout's `line_items` array

## Rejected Ancillaries

When a submitted ancillary cannot be added, businesses communicate this via the
`messages[]` array:

```json
{
    "messages": [
        {
            "type": "warning",
            "code": "ancillary_invalid_input",
            "path": "$.ancillaries.items[0].input",
            "content": "Selected installation date is not available. Please choose another date."
        }
    ]
}
```

> **Implementation guidance:** Operations that affect order totals, or the
> user's expectation of the total, **SHOULD** use `type: "warning"` to ensure
> they are surfaced to the user rather than silently handled by platforms.

**Error codes for rejected ancillaries:**

| Code                               | Description                                  |
| ---------------------------------- | -------------------------------------------- |
| `ancillary_invalid`                | Ancillary not found or malformed             |
| `ancillary_already_applied`        | Ancillary is already applied                 |
| `ancillary_combination_disallowed` | Cannot combine with another active ancillary |
| `ancillary_invalid_input`          | Required input is missing or invalid         |
| `ancillary_unavailable`            | Ancillary not available for this line item   |
| `ancillary_quantity_mismatch`      | Quantity doesn't match related line item     |

## Automatic Ancillaries

Businesses may apply ancillaries automatically:

- Appear in `ancillaries.applied` with `automatic: true`
- Include `reason_code` explaining why (e.g., `legal_requirement`,
  `promotional_gift`)
- Applied without platform action
- Cannot be removed by the platform
- Surfaced for transparency (platform can explain to user why ancillary was
  added)

**Reason codes:**

| Code                | Description                                      |
| ------------------- | ------------------------------------------------ |
| `legal_requirement` | Required by law (e.g., recycling fee, insurance) |
| `promotional_gift`  | Free gift with purchase                          |
| `bundle_component`  | Part of a product bundle                         |
| `loyalty_benefit`   | Benefit from loyalty/membership program          |

## Impact on Line Items and Totals

Applied ancillaries are reflected in the core checkout fields:

- Each applied ancillary appears as a line item in `line_items[]`
- The `ancillaries.applied` array provides relational context (which ancillary
  is for which line item)
- Totals are updated to include ancillary costs

Applied ancillaries include key metadata from the original suggestion (`type`,
`group_id`, `terms_url`) enabling platforms to:

- Show the applied ancillary alongside its alternatives (matching `group_id`
  between `applied` and `suggested`)
- Display relevant terms links without re-querying suggestions
- Provide context about the relationship type (complementary, suggested,
  required)

## Examples

### Insurance / Protection Plan

Insurance plans protect specific products. Multiple tiers can be offered using
`group_id`.

**Response (checkout with insurance suggestions):**

```json
{
    "line_items": [
        {
            "id": "li_1",
            "item": {
                "id": "sku_smartphone_256",
                "title": "Smartphone 256GB",
                "price": 99900,
                "image_url": "https://example.com/images/smartphone.jpg"
            },
            "quantity": 1,
            "totals": [
                { "type": "subtotal", "amount": 99900 },
                { "type": "total", "amount": 99900 }
            ]
        }
    ],
    "ancillaries": {
        "title": "Protect your new device",
        "suggested": [
            {
                "item": {
                    "id": "sku_protection_2yr",
                    "title": "2-Year Protection Plan",
                    "price": 19900,
                    "image_url": "https://example.com/images/protection.jpg"
                },
                "type": "complementary",
                "category": "insurance",
                "for": "li_1",
                "group_id": "insurance_phone",
                "description": "Covers accidental damage, battery service, and 24/7 support",
                "terms_url": "https://example.com/protection-plan/terms"
            },
            {
                "item": {
                    "id": "sku_protection_theft",
                    "title": "2-Year Protection Plan with Theft Coverage",
                    "price": 26900,
                    "image_url": "https://example.com/images/protection-theft.jpg"
                },
                "type": "complementary",
                "category": "insurance",
                "for": "li_1",
                "group_id": "insurance_phone",
                "description": "Full protection plus theft and loss coverage",
                "terms_url": "https://example.com/protection-plan-theft/terms"
            }
        ]
    }
}
```

**Request (adding insurance):**

```json
{
    "ancillaries": {
        "items": [
            {
                "item": { "id": "sku_protection_2yr" },
                "for": "li_1",
                "quantity": 1
            }
        ]
    }
}
```

**Response (insurance applied):**

```json
{
    "line_items": [
        {
            "id": "li_1",
            "item": {
                "id": "sku_smartphone_256",
                "title": "Smartphone 256GB",
                "price": 99900
            },
            "quantity": 1,
            "totals": [
                { "type": "subtotal", "amount": 99900 },
                { "type": "total", "amount": 99900 }
            ]
        },
        {
            "id": "li_2",
            "item": {
                "id": "sku_protection_2yr",
                "title": "2-Year Protection Plan",
                "price": 19900
            },
            "quantity": 1,
            "totals": [
                { "type": "subtotal", "amount": 19900 },
                { "type": "total", "amount": 19900 }
            ]
        }
    ],
    "ancillaries": {
        "applied": [
            {
                "id": "li_2",
                "for": "li_1",
                "type": "complementary",
                "category": "insurance",
                "group_id": "insurance_phone",
                "description": "2-Year Protection Plan for Smartphone 256GB",
                "terms_url": "https://example.com/protection-plan/terms"
            }
        ]
    },
    "totals": [
        { "type": "subtotal", "amount": 119800 },
        { "type": "total", "amount": 119800 }
    ]
}
```

### Complementary Products (Peripherals)

Accessories and peripherals related to purchased items.

**Response:**

```json
{
    "line_items": [
        {
            "id": "li_1",
            "item": {
                "id": "sku_smartphone_256",
                "title": "Smartphone 256GB",
                "price": 99900
            },
            "quantity": 1,
            "totals": [
                { "type": "subtotal", "amount": 99900 },
                { "type": "total", "amount": 99900 }
            ]
        }
    ],
    "ancillaries": {
        "title": "Complete your setup",
        "suggested": [
            {
                "item": {
                    "id": "sku_usbc_cable",
                    "title": "USB-C Charging Cable (2m)",
                    "price": 1900,
                    "image_url": "https://example.com/images/usbc-cable.jpg"
                },
                "type": "complementary",
                "category": "product",
                "for": "li_1",
                "description": "Fast charging cable for your new phone"
            },
            {
                "item": {
                    "id": "sku_wireless_charger",
                    "title": "Wireless Charging Pad",
                    "price": 3900,
                    "image_url": "https://example.com/images/wireless-charger.jpg"
                },
                "type": "complementary",
                "category": "product",
                "for": "li_1",
                "description": "Convenient wireless charging"
            },
            {
                "item": {
                    "id": "sku_phone_case",
                    "title": "Protective Phone Case",
                    "price": 4900,
                    "image_url": "https://example.com/images/case.jpg"
                },
                "type": "complementary",
                "category": "product",
                "for": "li_1",
                "description": "Protect your phone with a slim, durable case"
            }
        ]
    }
}
```

### Service with Required Input (Installation)

Services that require time slot selection or other buyer input.

**Response (service suggestion with input required):**

```json
{
    "line_items": [
        {
            "id": "li_1",
            "item": {
                "id": "sku_oled_tv_65",
                "title": "65\" OLED Smart TV",
                "price": 199900
            },
            "quantity": 1,
            "totals": [
                { "type": "subtotal", "amount": 199900 },
                { "type": "total", "amount": 199900 }
            ]
        }
    ],
    "ancillaries": {
        "suggested": [
            {
                "item": {
                    "id": "sku_tv_install",
                    "title": "Professional TV Installation",
                    "price": 14900,
                    "image_url": "https://example.com/images/installation.jpg"
                },
                "type": "complementary",
                "category": "service",
                "for": "li_1",
                "description": "Expert wall mounting and setup included",
                "requires_input": true,
                "input_schema": {
                    "type": "selection",
                    "label": "Select installation date and time",
                    "description": "A technician will arrive within a 2-hour window",
                    "required": true,
                    "options": [
                        {
                            "id": "slot_1",
                            "label": "Tuesday, Feb 18 - 9:00 AM to 11:00 AM"
                        },
                        {
                            "id": "slot_2",
                            "label": "Tuesday, Feb 18 - 2:00 PM to 4:00 PM"
                        },
                        {
                            "id": "slot_3",
                            "label": "Wednesday, Feb 19 - 9:00 AM to 11:00 AM"
                        },
                        {
                            "id": "slot_4",
                            "label": "Wednesday, Feb 19 - 2:00 PM to 4:00 PM"
                        }
                    ]
                }
            },
            {
                "item": {
                    "id": "sku_tv_calibration",
                    "title": "Professional Calibration",
                    "price": 9900
                },
                "type": "complementary",
                "category": "service",
                "for": "li_1",
                "description": "Optimize picture quality for your room",
                "requires_input": true,
                "input_schema": {
                    "type": "selection",
                    "label": "Select calibration appointment",
                    "required": true,
                    "options": [
                        {
                            "id": "cal_1",
                            "label": "Thursday, Feb 20 - 10:00 AM"
                        },
                        { "id": "cal_2", "label": "Friday, Feb 21 - 2:00 PM" }
                    ]
                }
            }
        ]
    }
}
```

**Request (adding service with input):**

```json
{
    "ancillaries": {
        "items": [
            {
                "item": { "id": "sku_tv_install" },
                "for": "li_1",
                "quantity": 1,
                "input": {
                    "type": "selection",
                    "value": "slot_2"
                }
            }
        ]
    }
}
```

**Response (service applied):**

```json
{
    "line_items": [
        {
            "id": "li_1",
            "item": {
                "id": "sku_oled_tv_65",
                "title": "65\" OLED Smart TV",
                "price": 199900
            },
            "quantity": 1,
            "totals": [
                { "type": "subtotal", "amount": 199900 },
                { "type": "total", "amount": 199900 }
            ]
        },
        {
            "id": "li_2",
            "item": {
                "id": "sku_tv_install",
                "title": "Professional TV Installation",
                "price": 14900
            },
            "quantity": 1,
            "totals": [
                { "type": "subtotal", "amount": 14900 },
                { "type": "total", "amount": 14900 }
            ]
        }
    ],
    "ancillaries": {
        "applied": [
            {
                "id": "li_2",
                "for": "li_1",
                "type": "complementary",
                "category": "service",
                "description": "Professional TV Installation - Tuesday, Feb 18, 2:00 PM to 4:00 PM",
                "input": {
                    "type": "selection",
                    "value": "slot_2"
                }
            }
        ]
    },
    "totals": [
        { "type": "subtotal", "amount": 214800 },
        { "type": "total", "amount": 214800 }
    ]
}
```

### Automatic Ancillary (Legal Requirement)

Ancillaries automatically added by the business.

**Request:**

```json
{
    "line_items": [
        {
            "item": { "id": "sku_laptop" },
            "quantity": 1
        }
    ]
}
```

**Response:**

```json
{
    "line_items": [
        {
            "id": "li_1",
            "item": {
                "id": "sku_laptop",
                "title": "Laptop 16\"",
                "price": 249900
            },
            "quantity": 1,
            "totals": [
                { "type": "subtotal", "amount": 249900 },
                { "type": "total", "amount": 249900 }
            ]
        },
        {
            "id": "li_2",
            "item": {
                "id": "sku_recycling_fee",
                "title": "Electronics Recycling Fee",
                "price": 500
            },
            "quantity": 1,
            "totals": [
                { "type": "subtotal", "amount": 500 },
                { "type": "total", "amount": 500 }
            ]
        }
    ],
    "ancillaries": {
        "applied": [
            {
                "id": "li_2",
                "for": "li_1",
                "type": "required",
                "category": "service",
                "description": "Electronics Recycling Fee (required by state law)",
                "automatic": true,
                "reason_code": "legal_requirement"
            }
        ]
    },
    "totals": [
        { "type": "subtotal", "amount": 250400 },
        { "type": "total", "amount": 250400 }
    ]
}
```

### Promotional Gift (Automatic)

Free items added automatically as part of a promotion.

**Response:**

```json
{
    "line_items": [
        {
            "id": "li_1",
            "item": {
                "id": "sku_phone",
                "title": "Smartphone Pro",
                "price": 119900
            },
            "quantity": 1,
            "totals": [
                { "type": "subtotal", "amount": 119900 },
                { "type": "total", "amount": 119900 }
            ]
        },
        {
            "id": "li_2",
            "item": {
                "id": "sku_earbuds",
                "title": "Wireless Earbuds",
                "price": 0
            },
            "quantity": 1,
            "totals": [
                { "type": "subtotal", "amount": 0 },
                { "type": "total", "amount": 0 }
            ]
        }
    ],
    "ancillaries": {
        "applied": [
            {
                "id": "li_2",
                "for": "li_1",
                "type": "complementary",
                "category": "product",
                "description": "Free Wireless Earbuds with your new phone!",
                "automatic": true,
                "reason_code": "promotional_gift"
            }
        ]
    },
    "totals": [
        { "type": "subtotal", "amount": 119900 },
        { "type": "total", "amount": 119900 }
    ]
}
```

## Platform Rendering Guidelines

### Grouping Suggestions

Platforms **SHOULD** group ancillary suggestions by:

1. **Category** - Show insurance options together, products together, etc.
2. **Related line item** - Group ancillaries for the same product
3. **Group ID** - Present mutually exclusive options as a single selection

### Handling Input Requirements

When `requires_input` is true:

1. Present the input UI based on `input_schema`
2. Validate input against `constraints` before submission
3. Include the `input` field in the request

### Automatic Ancillaries

Platforms **SHOULD** explain automatic ancillaries to users:

- Display the `reason_code` in human-readable form
- Indicate that the item cannot be removed
- Show the ancillary's relationship to the parent item
