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

# Loyalty Extension

## Overview

The loyalty extension is designed to facilitate high-fidelity loyalty experiences: ensuring existing loyalty members can seamlessly access their benefits during an agentic checkout experience. By enabling buyers to see their specific tier and eligible rewards before finalizing a purchase, it addresses a foundational expectation for program members and remove friction from the checkout funnel.

Specifically the following core use cases of benefit recognition for known members are addressed:

* Price-Impacting Benefits: Real-time application of member-only discounts and free shipping offers with clear attribution of benefit sources
* Non-Price Benefits: Transparent display of rewards earned or rewards applicable to future purchases
* Status Recognition: Verification and display of the buyers’ specific loyalty tier

## Key Concepts

Loyalty has four main components:

**Tracks**: distinct enrollment pathways or program categories that a user can join independently or simultaneously

* Acts as a logical container for related status levels, grouping tiers by their entry requirements (e.g., a "Paid Track" for subscribers vs. an "Earned Track" for shoppers).
* Allows for parallel participation, enabling a customer to belong to multiple tracks at once and aggregate their respective benefits (e.g., simultaneously holding "Premium" status in a delivery track and "Gold" status in a spend track).

**Tiers**: specific achievement ranks or status milestones within a track that unlock escalating value as a member progresses through activity or spend

* Defines the progressive ranks within a specific Track, where each level is unlocked by meeting defined criteria such as spending thresholds, transaction counts, or membership tenure.
* A member typically holds a single active Tier per Track; however, they can simultaneously benefit from multiple Tiers if they are enrolled in multiple Tracks (e.g., holding a "Subscriber" Tier in the Paid Track and a "Gold" Tier in the Earned Track).

**Benefits**: ongoing perks and privileges granted to a customer based on their current tier or membership status

* Contains both delayed (e.g. “Members have access to dedicated customer service”) and immediate-value (e.g. “Members get 5% off”) benefits.

**Rewards**: the fungible balances and/or stored value available for the customer to redeem on transactions

* One membership can offer multiple types of accumulable/collectable rewards, each having its own usage and redemption rules.

```json
{
  "tracks": [
    {
      "tiers": [
        {
          "benefits": [
            {
              ...
            }
          ]
        }
      ],
      "rewards": [
        {
          ...
        }
      ]
    }
  ]
}
```

## Discovery

Businesses can follow standard advertisement mechanism to advertise loyalty support in the Business profile. Currently loyalty extension can ONLY decorate checkout capability and the profile should contain both.

```json
{
  "ucp": {
    "version": "2026-04-08",
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "2026-04-08",
          "spec": "https://ucp.dev/2026-04-08/specification/checkout",
          "schema": "https://ucp.dev/2026-04-08/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.common.loyalty": [
        {
          "version": "2026-04-08",
          "extends": "dev.ucp.shopping.checkout",
          "spec": "https://ucp.dev/2026-04-08/specification/loyalty",
          "schema": "https://ucp.dev/2026-04-08/schemas/common/loyalty.json"
        }
      ]
    }
  }
}
```

## Schema

### Entities

#### Loyalty

{{ extension_schema_fields('loyalty.json#/$defs/loyalty', 'loyalty') }}

#### Loyalty Membership

{{ extension_schema_fields('loyalty.json#/$defs/loyalty_membership', 'loyalty') }}

#### Membership Track

{{ extension_schema_fields('loyalty.json#/$defs/membership_track', 'loyalty') }}

#### Membership Tier

{{ extension_schema_fields('loyalty.json#/$defs/membership_tier', 'loyalty') }}

#### Membership Tier Benefit

{{ extension_schema_fields('loyalty.json#/$defs/membership_tier_benefit', 'loyalty') }}

#### Membership Reward

{{ extension_schema_fields('loyalty.json#/$defs/membership_reward', 'loyalty') }}

#### Balance Currency

{{ extension_schema_fields('loyalty.json#/$defs/balance_currency', 'loyalty') }}

#### Membership Balance

{{ extension_schema_fields('loyalty.json#/$defs/membership_balance', 'loyalty') }}

#### Earning Forecast

{{ extension_schema_fields('loyalty.json#/$defs/earning_forecast', 'loyalty') }}

#### Earning Breakdown

{{ extension_schema_fields('loyalty.json#/$defs/earning_breakdown', 'loyalty') }}

## Platform & Business Interactions

When loyalty extension is active and the request contains eligibility claims about loyalty, businesses that recognize those eligibility claims MUST return them as the keys of the loyalty extension, which is an object keyed by the reverse-domain identifier — same convention as services, capabilities, and payment handlers in the business profile. The values of the returned object contain detailed membership info corresponding to the claims, and specifically contains a `provisional` field to indicate the status of the claim.

If monetary price impacting loyalty benefits (e.g. member pricing/shipping) are available and discount extension is supported by both business and platform, businesses MUST set the same `provisional` value in each of `applied` object within discount extension as in the loyalty extension. Platform can then follow the same rendering pattern for discount extension to surface these loyalty benefits to buyers.

```json
"discounts": {
  "applied": [
    {
      "title": "Loyalty benefit 1",
      "amount": 10,
      "provisional": false,
      "eligibility": "com.example.loyalty_1",
      "allocations": [
        {"path": "$.line_items[0]", "amount": 10}
      ]
    },
    {
      "title": "Loyalty benefit 2",
      "amount": 50,
      "provisional": true,
      "eligibility": "com.example.loyalty_2",
      "allocations": [
        {"path": "$.line_items[0]", "amount": 50}
      ]
    }
  ]
}
"loyalty": {
  "com.example.loyalty_1": {
    "tracks": [
      {
        "tiers": [
          {
            "id": "tier_1",
            "name": "GOLD",
            "benefits": [
              { "id": "BEN_001", "description": "Early access to sales" }
            ]
          }
        ]
      }
    ],
    "provisional": false
  },
  "com.example.loyalty_2": {
    "tracks": [
      {
        "tiers": [
          {
            "id": "tier_1",
            "name": "Basic"
          }
        ]
      }
    ],
    "provisional": true
  }
}
```

### Loyalty behavior

Platforms MUST send buyer loyalty membership claims via `context.eligibility` to activate loyalty extension and claim for loyalty benefits. The key of the returned object within loyalty extension represents that buyer's claim to the loyalty program. If a business successfully verifies this claim, the business MUST update the `provisional` boolean to false and populate the `activated_tier` fields alongside the to reflect the buyer's verified status for that specific claim.

If a business chooses not to validate the membership claim, the value of the returned object MUST retain `provisional: true`, and the business MUST NOT populate `activated_tier`. Applicable price-impacting benefits MAY be surfaced by businesses in the discount extension, and if so, they MUST hold `provisional: true`.

If verification fails, businesses MUST communicate the failure via a recoverable error. Platforms MAY then choose to remove the membership claim and proceed the checkout without benefits applied.

=== "Request with known buyer membership claim"

    ```json
    {
      "context": {
        "eligibility": ["com.example.loyalty"]
      }
    }
    ```

=== "Response without verification"

    ```json
    {
      "loyalty": {
        "com.example.loyalty": {
          "id": "membership_1",
          "name": "My Loyalty Program",
          "tracks": [
            {
              "id": "track_1",
              "name": "track_name_1",
              "tiers": [
                {
                  "id": "tier_1",
                  "name": "GOLD",
                  "benefits": [
                    { "id": "BEN_001", "description": "Early access to sales" }
                  ]
                }
              ]
            }
          ],
          "provisional": true,
        }
      }
    }
    ```

=== "Response with verification and valid membership"

    ```json
    {
      "loyalty": {
        "com.example.loyalty": {
          "id": "membership_1",
          "display_id": "****5678",
          "name": "My Loyalty Program",
          "tracks": [
            {
              "id": "track_1",
              "name": "track_name_1",
              "tiers": [
                {
                  "id": "tier_1",
                  "name": "GOLD",
                  "benefits": [
                    { "id": "BEN_001", "description": "Early access to sales" }
                  ]
                }
              ],
              "activated_tier": "tier_1"
            }
          ],
          "provisional": false,
        }
      }
    }
    ```

=== "Response with verification and invalid membership"

    ```json
    {
      "loyalty": {
        "com.example.loyalty": {
          "id": "membership_1",
          "name": "My Loyalty Program",
          "provisional": false,
        }
      },
      "messages": [
        {
          "type": "error",
          "severity": "recoverable",
          "code": "eligibility_invalid",
          "path": "$.loyalty['com.example.loyalty']",
          "content": "Buyer is not a valid loyalty member"
        }
      ]
    }
    ```

## Use Cases and Examples

With the help of the loyalty extension, the checkout capability can be further decorated to provide full visibility into buyers’ member-exclusive perks and allows the platform to render the extra information to facilitate the transaction.

### Price-Impacting Benefits

Alongside the discount extension, loyalty extension can provide buyer status info to allow the platform to transparently assert that correct and comprehensive member discounts are applied. In the example below, platform not only can explain the source of discounts via `discounts.applied[0].title` within discount extension, but also assure buyers that these member specific discounts are recognized because of their verified loyalty status via `tracks[0].tiers[0].name` within loyalty extension, which can be sourced from correlating `discounts.applied[0].eligibility` to `loyalty['com.example.loyalty']` to identify which membership provides which monetary benefit. Platform can then render “My Loyalty Program Gold and Benefit Visa Card benefit applied.” for example.

=== "Request"

    ```json
    {
      "context": {
        "eligibility": ["com.example.loyalty", "com.example.loyalty.credit_card"]
      },
      "line_items": [
        {
          "item": {
            "id": "prod_1",
            "quantity": 1,
            "title": "T-Shirt",
            "price": 1000
          }
        }
      ]
    }
    ```

=== "Response"

    ```json
    {
      "line_items": [
        {
          "id": "li_1",
          "item": {
            "id": "prod_1",
            "quantity": 1,
            "title": "T-Shirt",
            "price": 1000
          },
          "totals": [
            {"type": "subtotal", "amount": 1000},
            {"type": "items_discount", "display_text": "Loyalty member benefit", "amount": -30},
            {"type": "items_discount", "display_text": "Credit Card Members save 5%", "amount": -50},
            {"type": "total", "amount": 920}
          ]
        }
      ],
      "discounts": {
        "applied": [
          {
            "title": "Loyalty member benefit",
            "amount": 30,
            "method": "each",
            "provisional": false,
            "eligibility": "com.example.loyalty",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 30}
            ]
          },
          {
            "title": "Credit Card Members save 5%",
            "amount": 50,
            "method": "each",
            "provisional": false,
            "eligibility": "com.example.loyalty.credit_card",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 50}
            ]
          }
        ]
      },
      "loyalty": {
        "com.example.loyalty": {
          "id": "membership_1",
          "display_id": "****5678",
          "name": "My Loyalty Program",
          "tracks": [
            {
              "id": "track_1",
              "name": "track_name_1",
              "tiers": [
                {
                  "id": "tier_1",
                  "name": "Gold",
                  "benefits": [
                    { "id": "BEN_001", "description": "Early access to sales" },
                  ]
                }
              ],
              "activated_tier": "tier_1",
            }
          ],
          "provisional": false
        },
        "com.example.loyalty.credit_card": {
          "id": "membership_2",
          "name": "Program Visa Card",
          "tracks": [
            {
              "id": "track_2",
              "name": "track_name_2",
              "tiers": [
                {
                  "id": "tier_2",
                  "name": "Visa Card",
                  "benefits": [
                    { "id": "BEN_001", "description": "Same day delivery" },
                  ]
                }
              ],
              "activated_tier": "tier_2",
            }
          ],
          "provisional": false
        }
      },
      "totals": [
        {"type": "subtotal", "display_text": "Subtotal", "amount": 1000},
        {"type": "items_discount", "display_text": "Loyalty member benefit", "amount": -30},
        {"type": "items_discount", "display_text": "Credit Card Members save 5%", "amount": -50},
        {"type": "total", "display_text": "Estimated Total", "amount": 920}
      ]
    }
    ```

### Reward Earnings Forecast

In addition to immediate-value benefits like member pricing/shipping, delayed-value collectable reward benefits are another crucial element within the loyalty ecosystem. Displaying earnings forecasts of these rewards before the buyer commits complements and to some extent helps agents handle price objections - rewards earning becomes additional value on top of any pricing discount. In this example, businesses provide the reward earning forecast with a breakdown, giving platforms to explain with full transparency on why the buyer is earning and how the earning is calculated.

=== "Request"

    ```json
    {
      "context": {
        "eligibility": ["com.example.loyalty"]
      },
      "line_items": [
        {
          "item": {
            "id": "prod_1",
            "quantity": 1,
            "title": "T-Shirt",
            "price": 1000
          }
        }
      ]
    }
    ```

=== "Response"

    ```json
    {
      "line_items": [
        {
          "id": "li_1",
          "item": {
            "id": "prod_1",
            "quantity": 1,
            "title": "T-Shirt",
            "price": 1000
          },
          "totals": [
            {"type": "subtotal", "amount": 1000},
            {"type": "total", "amount": 1000}
          ]
        }
      ],
      "loyalty": {
        "com.example.loyalty": {
          "id": "membership_1",
          "display_id": "****5678",
          "name": "My Loyalty Program",
          "tracks": [
            {
              "id": "track_1",
              "name": "track_name_1",
              "tiers": [
                {
                  "id": "tier_1",
                  "name": "Gold",
                  "benefits": [
                    { "id": "BEN_001", "description": "Early access to sales" },
                    { "id": "BEN_002", "description": "Birthday gift" },
                    { "id": "BEN_003", "description": "Extended return window to 180 days" },
                  ]
                }
              ],
              "activated_tier": "tier_1",
              "rewards": [
                {
                  "currency": {
                    "name": "LoyaltyStars",
                    "code": "LST"
                  },
                  "earning_forecast": {
                    "amount": 30,
                    "breakdown": [
                      { "id": "RULE_1", "description": "1 point/dollar on everything", "amount": 10 },
                      { "id": "RULE_2", "description": "2 extra point/dollar on footwear", "amount": 20 }
                    ]
                  }
                }
              ]
            }
          ],
          "provisional": false
        }
      },
      "totals": [
        {"type": "subtotal", "display_text": "Subtotal", "amount": 1000},
        {"type": "total", "display_text": "Estimated Total", "amount": 1000}
      ]
    }
    ```
