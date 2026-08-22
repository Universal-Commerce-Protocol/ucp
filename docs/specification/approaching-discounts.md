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

# Approaching Discounts (Part of the Discounts Extension)

## Overview

Approaching discounts enables buyers to be informed when they are approaching
a cart (\$10 off orders >= \$100) or shipping discount (free shipping on orders >= $100).

Approaching discounts are for promotions that trigger based on a qualifying amount 
and contain an upsell threshold, enabling the merchant to specify when the approaching discount
message is shown to the buyer.  

This enhancement to the discount extension, enables merchants to upsell buyers and increase
both conversion and average order value.  

**Key features:**

- Promotional messaging for promotions the buyer is near (within the upsell threshold)

**Dependencies:**

- Cart or Checkout Capability with Discount Extension 

## Discovery

Businesses advertise discount extension support in their profile. Approaching discounts
are part of the base discount extension.  

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.discount": [
        {
          "extends": "dev.ucp.shopping.checkout",
          "schema": "https://ucp.dev/schemas/shopping/discount.json",
          "spec": "https://ucp.dev/specs/shopping/discount",
          "version": "2026-04-08"
        }
      ]
    }
  }
}
```

## Schema

When the discount extension capability is active, an additional object, approaching, is added to the discount response within
the cart and checkout APIs.  This object contains up to two sections: cart and shipping. 

### Approaching Discount

{{ schema_fields('types/approaching-discount', 'approaching') }}

### Cart

Cart contains approaching discounts that apply to the entire cart (i.e. $10 off )

{{ extension_schema_fields('types/approaching-discount.json#/$defs/cart', 'cart') }}

### Shipping

Shipping contains approaching discounts that apply to an individual fulfillment group (or shipment).

{{ extension_schema_fields('types/approaching-discount.json#/$defs/shipping', 'shipping') }}

## How It Works

### Cart

Expanding on the above example, \$10 off orders >= \$100, the qualifying amount is \$100.
If the upsell threshold is set to \$25, the message will be returned once the cart exceeds
\$75 in value (but less than \$100 when the promotion applies).

### Shipping

Similarly, shipping approaching discounts are used to convey discounted or free shipping. 
Shipping approaching discounts are calculated based on the amount of qualifying products within the fulfillment group.  
i.e. Free shipping on orders >= \$100, upsell threshold \$25

### Re-evaluation

As with discounts, approaching discounts are re-evaluated each time the cart is accessed.  If the cart no longer meets the 
threshold for the approaching discount, qualifies for the promotion, or the promotion has expired, the approaching message
is not returned.

## Examples

### Cart Approaching Discount 

    $10 off orders >= $100, upsell threshold $25
    Cart contains 1, $75 item

    Checkout / Cart response

```json
 "discounts": {
        "approaching": {
            "cart": [
                {
                    "threshold": 10000,
                    "title": "$10 off orders over $100",
                    "total": 7500
                }
            ]
        }
    }
```
The quantity of the cart is increased to 2, the cart now contains $150.  The approaching message disappears and is 
replaced with the discount. 

```json
"discounts": {
        "applied": [
            {
                "allocations": [
                    {
                        "amount": 1000,
                        "path": "$.line_items[0]"
                    }
                ],
                "amount": 1000,
                "automatic": true,
                "method": "across",
                "title": "$10 off orders over $100"
            }
        ]
    }
```
### Shipping Approaching Discount

    Free shipping on orders >= $100, upsell threshold $25
    Cart contains 1, $75 item

    Checkout / Cart response (relevant sections)

Groups
```json
  "groups": [
                    {
                        "id": "group1",
                        "line_item_ids": [
                            "a2d4b6fe79289963ac7543bcf6"
                        ],
                        "options": [
                            {
                                "description": "Order received within 7-10 business days",
                                "id": "001",
                                "title": "Ground",
                                "totals": [
                                    {
                                        "amount": 599,
                                        "type": "subtotal"
                                    },
                                    {
                                        "amount": 30,
                                        "type": "tax"
                                    },
                                    {
                                        "amount": 629,
                                        "type": "total"
                                    }
                                ]
                            }
                      ],
                      "selected_option_id": "001"
                    }
  ]
```

Discounts
```json 
    "discounts": {
        "approaching": {
            "shipping": [
                {
                    "fulfillment_group_id": "group1",
                    "threshold": 10000,
                    "title": "Free Shipping on Orders over $100",
                    "total": 7500
                }
            ]
        }
    }
```

The quantity of the cart is increased to 2, the cart now contains $150.  The approaching message disappears and is
replaced with the discount.

```json
 "discounts": {
        "applied": [
            {
                "allocations": [
                    {
                        "amount": 599,
                        "path": "$.fulfillment.methods[0]"
                    }
                ],
                "amount": 799,
                "automatic": true,
                "method": "across",
                "title": "Free Shipping on Orders over $100"
            }
        ]
    }
```

