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

# Product Addons Extension

## Overview

The Product Addons extension enables shoppers to select and change
product addons (e.g., Warranty, Engraving, Gift Wrapping) directly within
cart and checkout sessions. Addons are optional purchasable extras associated
with a product — unlike variant-defining options (Size, Color) which are
handled at the catalog level, addons represent supplementary choices that
affect pricing without changing the base product variant.

Without this extension, businesses must either inflate their product catalogs
with pre-built variants for every addon permutation, or handle addon
selection entirely outside the checkout flow.

**Key features:**

- Select product addons when adding items to cart or checkout
- Change addons during the session (e.g., upgrade warranty from 1-year to 2-year)
- Each addon choice is an item with its own ID, title, and totals
- Business resolves line item pricing from product + selected addons

**Dependencies:**

- Cart Capability or Checkout Capability

## Discovery

Businesses advertise product addons support in their profile. The capability
can extend cart, checkout, or both:

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.product_addons": [
        {
          "version": "{{ ucp_version }}",
          "extends": ["dev.ucp.shopping.cart", "dev.ucp.shopping.checkout"],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/product-addons",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/product_addons.json"
        }
      ]
    }
  }
}
```

## Schema

When this capability is active, line items in cart and/or checkout are extended
with an `addons` array on the `item` object. Each addon follows the same
selection pattern as fulfillment groups: the platform sends
`selected_choice_id`, and the server responds with the full set of available
addon `choices` including totals.

### Item Addon

{{ extension_schema_fields('product_addons.json#/$defs/item_addon', 'product-addons') }}

### Addon Choice

{{ extension_schema_fields('product_addons.json#/$defs/addon_choice', 'product-addons') }}

## How It Works

### Addon discovery

When `item.id` refers to a product that has available addons, the server
returns `item.addons` in the response with all available addons and their
choices. The platform can create a checkout in three ways:

1. **Product ID only** — send `item.id` with no `addons`. The server
   selects the defaults and returns `addons` with pre-selected choices.
   The platform can then render addon selectors for the shopper.
2. **Product ID + partial addons** — send `item.id` with some addons
   specified (e.g., only Warranty). The server uses defaults for
   unspecified addons.
3. **Product ID + full addons** — send `item.id` with all addons
   specified. The server resolves the exact pricing.

When `item.addons` is absent and the product has no available addons,
the item behaves as a standard line item.

### Selection pattern

Each addon (Warranty, Engraving, etc.) has:

- `name` — the addon name (e.g., `"Warranty"`)
- `selected_choice_id` — the ID of the chosen addon choice, sent by the
  platform. May be omitted on create to let the server select the default.
- `choices` — all addon choices with pricing, returned by the server
  (response-only)

Each addon choice has `id`, `title`, and optional `image_url` — plus
`default` and `totals` representing the cost of that specific choice.

This mirrors the fulfillment group pattern where `selected_option_id`
chooses among `options[]`.

### Addon choices

Each entry in the `choices` array has:

| Field | Type | Description |
| :---- | :--- | :---------- |
| `id` | string | Addon choice identifier, used as `selected_choice_id` |
| `title` | string | Display title (e.g., "2-Year Extended Warranty") |
| `image_url` | string | Optional addon image URI |
| `default` | boolean | Whether this is the default selection when the platform does not specify one |
| `totals` | array | Totals for this specific addon choice |

The `totals` array represents the cost of the addon choice itself (e.g.,
a 2-Year Warranty at $300). The platform can use these to display addon
pricing and compute differences between choices.

### Changing addons

To change an addon, the platform sends an update with the new
`selected_choice_id`. The server recalculates pricing and returns
updated totals.

For example, upgrading warranty from 1-year to 2-year:

1. Platform sends update with `selected_choice_id: "warranty_2yr"` for
   the Warranty addon
2. Server recalculates the line item price with the new warranty
3. Response includes updated `item.price`, `item.title`, and refreshed
   addon `choices` with pricing

### Error handling

When a selected addon choice is invalid or unavailable, the server
communicates this via `messages[]`:

| Code | Description |
| :--- | :---------- |
| `invalid_addon` | The selected choice ID is not recognized for this addon |
| `addon_unavailable` | The selected addon choice is not available for this product |

## Examples

### Create checkout with product ID only

The platform sends just the product ID — no addons. The server recognizes
the product has available addons, selects defaults, and returns all addons
with pre-selected choices. Each addon choice has its own title and totals showing the addon cost.

=== "Request"

    ```json
    {
      "line_items": [
        {
          "item": {
            "id": "prod_smartphone_x"
          },
          "quantity": 1
        }
      ]
    }
    ```

=== "Response"

    ```json
    {
      "id": "chk_abc123",
      "status": "incomplete",
      "currency": "USD",
      "line_items": [
        {
          "id": "li_1",
          "item": {
            "id": "prod_smartphone_x",
            "title": "Smartphone X - 128 GB, Midnight",
            "price": 89900,
            "image_url": "https://merchant.example.com/smartphone-x-midnight.jpg",
            "addons": [
              {
                "name": "Warranty",
                "selected_choice_id": "warranty_none",
                "choices": [
                  {
                    "id": "warranty_none",
                    "title": "No Warranty",
                    "default": true,
                    "totals": [{"type": "subtotal", "amount": 0}, {"type": "total", "amount": 0}]
                  },
                  {
                    "id": "warranty_1yr",
                    "title": "1-Year Extended Warranty",
                    "totals": [{"type": "subtotal", "amount": 10000}, {"type": "total", "amount": 10000}]
                  },
                  {
                    "id": "warranty_2yr",
                    "title": "2-Year Extended Warranty",
                    "totals": [{"type": "subtotal", "amount": 30000}, {"type": "total", "amount": 30000}]
                  }
                ]
              },
              {
                "name": "Engraving",
                "selected_choice_id": "engraving_none",
                "choices": [
                  {
                    "id": "engraving_none",
                    "title": "No Engraving",
                    "default": true,
                    "totals": [{"type": "subtotal", "amount": 0}, {"type": "total", "amount": 0}]
                  },
                  {
                    "id": "engraving_text",
                    "title": "Custom Text Engraving",
                    "image_url": "https://merchant.example.com/engraving-text.jpg",
                    "totals": [{"type": "subtotal", "amount": 4000}, {"type": "total", "amount": 4000}]
                  },
                  {
                    "id": "engraving_emoji",
                    "title": "Emoji Engraving",
                    "image_url": "https://merchant.example.com/engraving-emoji.jpg",
                    "totals": [{"type": "subtotal", "amount": 2000}, {"type": "total", "amount": 2000}]
                  }
                ]
              },
              {
                "name": "Gift Wrapping",
                "selected_choice_id": "gift_none",
                "choices": [
                  {
                    "id": "gift_none",
                    "title": "No Gift Wrapping",
                    "default": true,
                    "totals": [{"type": "subtotal", "amount": 0}, {"type": "total", "amount": 0}]
                  },
                  {
                    "id": "gift_standard",
                    "title": "Standard Gift Box",
                    "image_url": "https://merchant.example.com/gift-box-standard.jpg",
                    "totals": [{"type": "subtotal", "amount": 4900}, {"type": "total", "amount": 4900}]
                  },
                  {
                    "id": "gift_premium",
                    "title": "Premium Gift Box",
                    "image_url": "https://merchant.example.com/gift-box-premium.jpg",
                    "totals": [{"type": "subtotal", "amount": 9900}, {"type": "total", "amount": 9900}]
                  }
                ]
              }
            ]
          },
          "quantity": 1,
          "totals": [
            {"type": "subtotal", "amount": 89900},
            {"type": "total", "amount": 89900}
          ]
        }
      ],
      "totals": [
        {"type": "subtotal", "display_text": "Subtotal", "amount": 89900},
        {"type": "total", "display_text": "Total", "amount": 89900}
      ]
    }
    ```

### Create checkout with selected addons

A shopper adds a smartphone with a warranty and engraving pre-selected.

=== "Request"

    ```json
    {
      "line_items": [
        {
          "item": {
            "id": "prod_smartphone_x",
            "addons": [
              {"name": "Warranty", "selected_choice_id": "warranty_1yr"},
              {"name": "Engraving", "selected_choice_id": "engraving_text"},
              {"name": "Gift Wrapping", "selected_choice_id": "gift_none"}
            ]
          },
          "quantity": 1
        }
      ]
    }
    ```

=== "Response"

    ```json
    {
      "id": "chk_abc123",
      "status": "incomplete",
      "currency": "USD",
      "line_items": [
        {
          "id": "li_1",
          "item": {
            "id": "prod_smartphone_x",
            "title": "Smartphone X - 128 GB, Midnight",
            "price": 103900,
            "image_url": "https://merchant.example.com/smartphone-x-midnight.jpg",
            "addons": [
              {
                "name": "Warranty",
                "selected_choice_id": "warranty_1yr",
                "choices": [
                  {
                    "id": "warranty_none",
                    "title": "No Warranty",
                    "default": true,
                    "totals": [{"type": "subtotal", "amount": 0}, {"type": "total", "amount": 0}]
                  },
                  {
                    "id": "warranty_1yr",
                    "title": "1-Year Extended Warranty",
                    "totals": [{"type": "subtotal", "amount": 10000}, {"type": "total", "amount": 10000}]
                  },
                  {
                    "id": "warranty_2yr",
                    "title": "2-Year Extended Warranty",
                    "totals": [{"type": "subtotal", "amount": 30000}, {"type": "total", "amount": 30000}]
                  }
                ]
              },
              {
                "name": "Engraving",
                "selected_choice_id": "engraving_text",
                "choices": [
                  {
                    "id": "engraving_none",
                    "title": "No Engraving",
                    "default": true,
                    "totals": [{"type": "subtotal", "amount": 0}, {"type": "total", "amount": 0}]
                  },
                  {
                    "id": "engraving_text",
                    "title": "Custom Text Engraving",
                    "totals": [{"type": "subtotal", "amount": 4000}, {"type": "total", "amount": 4000}]
                  },
                  {
                    "id": "engraving_emoji",
                    "title": "Emoji Engraving",
                    "totals": [{"type": "subtotal", "amount": 2000}, {"type": "total", "amount": 2000}]
                  }
                ]
              },
              {
                "name": "Gift Wrapping",
                "selected_choice_id": "gift_none",
                "choices": [
                  {
                    "id": "gift_none",
                    "title": "No Gift Wrapping",
                    "default": true,
                    "totals": [{"type": "subtotal", "amount": 0}, {"type": "total", "amount": 0}]
                  },
                  {
                    "id": "gift_standard",
                    "title": "Standard Gift Box",
                    "totals": [{"type": "subtotal", "amount": 4900}, {"type": "total", "amount": 4900}]
                  },
                  {
                    "id": "gift_premium",
                    "title": "Premium Gift Box",
                    "totals": [{"type": "subtotal", "amount": 9900}, {"type": "total", "amount": 9900}]
                  }
                ]
              }
            ]
          },
          "quantity": 1,
          "totals": [
            {"type": "subtotal", "amount": 103900},
            {"type": "total", "amount": 103900}
          ]
        }
      ],
      "totals": [
        {"type": "subtotal", "display_text": "Subtotal", "amount": 103900},
        {"type": "total", "display_text": "Total", "amount": 103900}
      ]
    }
    ```

### Upgrade warranty during checkout

The shopper upgrades from 1-Year to 2-Year warranty. The platform sends
an update with the new `selected_choice_id` — only the warranty selection
changes. The server recalculates pricing.

=== "Request"

    ```json
    {
      "line_items": [
        {
          "id": "li_1",
          "item": {
            "id": "prod_smartphone_x",
            "addons": [
              {"name": "Warranty", "selected_choice_id": "warranty_2yr"},
              {"name": "Engraving", "selected_choice_id": "engraving_text"},
              {"name": "Gift Wrapping", "selected_choice_id": "gift_none"}
            ]
          },
          "quantity": 1
        }
      ]
    }
    ```

=== "Response"

    ```json
    {
      "id": "chk_abc123",
      "status": "incomplete",
      "currency": "USD",
      "line_items": [
        {
          "id": "li_1",
          "item": {
            "id": "prod_smartphone_x",
            "title": "Smartphone X - 128 GB, Midnight",
            "price": 123900,
            "image_url": "https://merchant.example.com/smartphone-x-midnight.jpg",
            "addons": [
              {
                "name": "Warranty",
                "selected_choice_id": "warranty_2yr",
                "choices": [
                  {
                    "id": "warranty_none",
                    "title": "No Warranty",
                    "default": true,
                    "totals": [{"type": "subtotal", "amount": 0}, {"type": "total", "amount": 0}]
                  },
                  {
                    "id": "warranty_1yr",
                    "title": "1-Year Extended Warranty",
                    "totals": [{"type": "subtotal", "amount": 10000}, {"type": "total", "amount": 10000}]
                  },
                  {
                    "id": "warranty_2yr",
                    "title": "2-Year Extended Warranty",
                    "totals": [{"type": "subtotal", "amount": 30000}, {"type": "total", "amount": 30000}]
                  }
                ]
              },
              {
                "name": "Engraving",
                "selected_choice_id": "engraving_text",
                "choices": [
                  {
                    "id": "engraving_none",
                    "title": "No Engraving",
                    "default": true,
                    "totals": [{"type": "subtotal", "amount": 0}, {"type": "total", "amount": 0}]
                  },
                  {
                    "id": "engraving_text",
                    "title": "Custom Text Engraving",
                    "totals": [{"type": "subtotal", "amount": 4000}, {"type": "total", "amount": 4000}]
                  },
                  {
                    "id": "engraving_emoji",
                    "title": "Emoji Engraving",
                    "totals": [{"type": "subtotal", "amount": 2000}, {"type": "total", "amount": 2000}]
                  }
                ]
              },
              {
                "name": "Gift Wrapping",
                "selected_choice_id": "gift_none",
                "choices": [
                  {
                    "id": "gift_none",
                    "title": "No Gift Wrapping",
                    "default": true,
                    "totals": [{"type": "subtotal", "amount": 0}, {"type": "total", "amount": 0}]
                  },
                  {
                    "id": "gift_standard",
                    "title": "Standard Gift Box",
                    "totals": [{"type": "subtotal", "amount": 4900}, {"type": "total", "amount": 4900}]
                  },
                  {
                    "id": "gift_premium",
                    "title": "Premium Gift Box",
                    "totals": [{"type": "subtotal", "amount": 9900}, {"type": "total", "amount": 9900}]
                  }
                ]
              }
            ]
          },
          "quantity": 1,
          "totals": [
            {"type": "subtotal", "amount": 123900},
            {"type": "total", "amount": 123900}
          ]
        }
      ],
      "totals": [
        {"type": "subtotal", "display_text": "Subtotal", "amount": 123900},
        {"type": "total", "display_text": "Total", "amount": 123900}
      ]
    }
    ```

### Mixed items — with and without addons

A checkout containing a smartphone with addons and a phone case with no
addons (standard line item). The two patterns coexist within the same
session.

=== "Request"

    ```json
    {
      "line_items": [
        {
          "item": {
            "id": "prod_smartphone_x",
            "addons": [
              {"name": "Warranty", "selected_choice_id": "warranty_1yr"},
              {"name": "Engraving", "selected_choice_id": "engraving_none"},
              {"name": "Gift Wrapping", "selected_choice_id": "gift_standard"}
            ]
          },
          "quantity": 1
        },
        {
          "item": {
            "id": "sku_case_midnight_clear"
          },
          "quantity": 1
        }
      ]
    }
    ```

=== "Response"

    ```json
    {
      "id": "chk_def456",
      "status": "incomplete",
      "currency": "USD",
      "line_items": [
        {
          "id": "li_1",
          "item": {
            "id": "prod_smartphone_x",
            "title": "Smartphone X - 128 GB, Midnight",
            "price": 104800,
            "image_url": "https://merchant.example.com/smartphone-x-midnight.jpg",
            "addons": [
              {
                "name": "Warranty",
                "selected_choice_id": "warranty_1yr",
                "choices": [
                  {
                    "id": "warranty_none",
                    "title": "No Warranty",
                    "default": true,
                    "totals": [{"type": "subtotal", "amount": 0}, {"type": "total", "amount": 0}]
                  },
                  {
                    "id": "warranty_1yr",
                    "title": "1-Year Extended Warranty",
                    "totals": [{"type": "subtotal", "amount": 10000}, {"type": "total", "amount": 10000}]
                  },
                  {
                    "id": "warranty_2yr",
                    "title": "2-Year Extended Warranty",
                    "totals": [{"type": "subtotal", "amount": 30000}, {"type": "total", "amount": 30000}]
                  }
                ]
              },
              {
                "name": "Engraving",
                "selected_choice_id": "engraving_none",
                "choices": [
                  {
                    "id": "engraving_none",
                    "title": "No Engraving",
                    "default": true,
                    "totals": [{"type": "subtotal", "amount": 0}, {"type": "total", "amount": 0}]
                  },
                  {
                    "id": "engraving_text",
                    "title": "Custom Text Engraving",
                    "totals": [{"type": "subtotal", "amount": 4000}, {"type": "total", "amount": 4000}]
                  },
                  {
                    "id": "engraving_emoji",
                    "title": "Emoji Engraving",
                    "totals": [{"type": "subtotal", "amount": 2000}, {"type": "total", "amount": 2000}]
                  }
                ]
              },
              {
                "name": "Gift Wrapping",
                "selected_choice_id": "gift_standard",
                "choices": [
                  {
                    "id": "gift_none",
                    "title": "No Gift Wrapping",
                    "default": true,
                    "totals": [{"type": "subtotal", "amount": 0}, {"type": "total", "amount": 0}]
                  },
                  {
                    "id": "gift_standard",
                    "title": "Standard Gift Box",
                    "image_url": "https://merchant.example.com/gift-box-standard.jpg",
                    "totals": [{"type": "subtotal", "amount": 4900}, {"type": "total", "amount": 4900}]
                  },
                  {
                    "id": "gift_premium",
                    "title": "Premium Gift Box",
                    "image_url": "https://merchant.example.com/gift-box-premium.jpg",
                    "totals": [{"type": "subtotal", "amount": 9900}, {"type": "total", "amount": 9900}]
                  }
                ]
              }
            ]
          },
          "quantity": 1,
          "totals": [
            {"type": "subtotal", "amount": 104800},
            {"type": "total", "amount": 104800}
          ]
        },
        {
          "id": "li_2",
          "item": {
            "id": "sku_case_midnight_clear",
            "title": "Clear Case - Midnight",
            "price": 4900
          },
          "quantity": 1,
          "totals": [
            {"type": "subtotal", "amount": 4900},
            {"type": "total", "amount": 4900}
          ]
        }
      ],
      "totals": [
        {"type": "subtotal", "display_text": "Subtotal", "amount": 109700},
        {"type": "total", "display_text": "Total", "amount": 109700}
      ]
    }
    ```
