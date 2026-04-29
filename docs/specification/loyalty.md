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

Businesses can follow standard advertisement mechanism to advertise loyalty support in the Business profile

```json
{
 "ucp": {
   "version": "2026-01-23",
   "capabilities": {
     "dev.ucp.common.loyalty": [
       {
         "version": "2026-01-23",
         "extends": "dev.ucp.shopping.checkout",
         "spec": "https://ucp.dev/2026-01-23/specification/loyalty",
         "schema": "https://ucp.dev/2026-01-23/schemas/common/loyalty.json"
       }
     ]
   }
 }
}
```

## Schema

### Entities

#### Loyalty

{{ schema_fields('loyalty', 'loyalty') }}

#### Loyalty Membership

{{ schema_fields('loyalty_membership', 'loyalty') }}

#### Membership Track

{{ schema_fields('membership_track', 'loyalty') }}

#### Membership Tier

{{ schema_fields('membership_tier', 'loyalty') }}

#### Membership Tier Benefit

{{ schema_fields('membership_tier_benefit', 'loyalty') }}

#### Membership Reward

{{ schema_fields('membership_reward', 'loyalty') }}

#### Balance Currency

{{ schema_fields('balance_currency', 'loyalty') }}

#### Membership Balance

{{ schema_fields('membership_balance', 'loyalty') }}

#### Earning Forecast

{{ schema_fields('earning_forecast', 'loyalty') }}

#### Earning Breakdown

{{ schema_fields('earning_breakdown', 'loyalty') }}

## Eligibility Claims

Given almost everything related to loyalty is provisional and requires eligible membership before benefits can be applied, [Context](checkout.md#context) naturally fits here where it allows buyers to claim eligibility for loyalty benefits and businesses to verify and communicate the result with the associated effects (financial-wise and rewards-wise). When loyalty extension is active and the request contains eligibility claims about loyalty, businesses that choose to accept eligibility claims MUST surface that as an indicator of buyer’s membership status, and if applicable, effects on pricing coming from monetary benefits. Platforms MUST display those provisional loyalty discounts to the buyer. Specifically, the loyalty extension is an object keyed by reverse_domain_name — same convention as services, capabilities, and payment_handlers in the business profile. The key is the eligibility claim, and value is the membership object that contains provisional to indicate the verification result.

```json
"com.example.loyalty": {
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
      ],
    }
  ],
  "provisional": false
}
```

### Loyalty behavior

Platforms MUST send buyer loyalty membership claims via `context.eligibility` to activate loyalty extension and claim for loyalty benefits. The key of the returned object within loyalty extension represents that buyer's claim to the loyalty program. If a business successfully verifies this claim, the business MUST update the `provisional` boolean to false and populate the `activated_tier` fields alongside the to reflect the buyer's verified status for that specific claim.

If a business chooses not to synchronously verify the membership claim, the value of the returned object MUST retain `provisional: true`, and the business MUST NOT populate `activated_tier`. Any applicable price-impacting benefits MUST be surfaced in the discounts object with `provisional: true`.

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
            }
          ],
          "provisional": false,
        }
      },
      "messages": [
        {
          "type": "error",
          "severity": "recoverable",
          "code": "eligibility_invalid",
          "path": "$.loyalty.memberships[0]",
          "content": "Buyer is not a valid loyalty member"
        }
      ]
    }
    ```

## Use Cases and Examples

With the help of the loyalty extension, the checkout capability can be further decorated to provide full visibility into buyers’ member-exclusive perks and allows the platform to render the extra information to facilitate the transaction.

### Price-Impacting Benefits

Alongside the discount extension, loyalty extension can provide buyer status info to allow the platform to transparently assert that correct and comprehensive member discounts are applied. In the example below, platform not only can explain the source of discounts via `discounts.applied.title` within discount extension, but also assure buyers that these member specific discounts are recognized because of their verified loyalty status via `memberships.tracks.tiers.name` within loyalty extension (e.g. “My Loyalty Program Gold and Benefit Visa Card benefit applied.”)

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
            {"type": "loyalty_gold_discount", "amount": -30},
            {"type": "loyalty_credit_card_discount", "amount": -50},
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
          "display_id": "****1234",
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
                    { "id": "BEN_002", "description": "1 point/dollar on everything" },
                    { "id": "BEN_002", "description": "2 extra point/dollar on footwear" },
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
                      { "source": "$.tiers[0].benefits[1]", "amount": 10 },
                      { "source": "$.tiers[0].benefits[2]", "amount": 20 }
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
