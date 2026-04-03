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

The loyalty extension is designed to facilitate high-fidelity loyalty experiences across various commerce journeys, ensuring that shoppers can for example sign-up for membership, access personalized benefits, redeem rewards, and manage memberships seamlessly across various capabilities.

In its current format, it can be used to decorate the following Capabilities for example:

* **Catalog**: For discovering potential immediate (e.g. price discounts) or delayed (e.g. cash back for future use) savings from being a member
* **Checkout**: For applying member-specific discounts/fulfillment benefits, calculating point earnings, or initiating reward redemptions, in conjunction with discount extension to specify the monetary effect of applicable loyalty benefits
* **Cart**: For displaying the loyalty benefits for potential usage on subsequent checkout (e.g. redeemable balance, tier evaluations), with or without the help of discount extension to upsell potential savings and non-monetary benefits from membership

In the future, for membership lifecycle management by agents (e.g. membership status fetching, program sign-up, balance transfer, etc.), it is possible that loyalty could be considered an independent capability. The other direction is fitting them within higher-order account and profile management capabilities that allow for broader operations, with loyalty being a subset and hence potentially represented by the same extension as it. This is not yet finalized among community discussion and pending future updates to achieve.

## Key Concepts

Loyalty has four main components:

**Memberships**: the overarching framework of a loyalty program, as well as the specific enrollment status and standing of a customer within it

* Usually represents a customer lifecycle solution the businesses have, which offer a tiered ecosystem of access, convenience, and identity.
* Encompasses the metadata of the concrete offerings as well as the customer level information associated with (if applicable).
* Customers can have multiple memberships that are relevant to the business (e.g. self-owned program and third-party program).

**Tiers**: progressive achievement levels within a membership that unlock increasing value based on activity or spend/fee payment

* Defines achievable levels within a membership for a customer, with various types of qualification methods and conditions.
* Customers can simultaneously be activated on and eligible for multiple tiers if the program allows.

**Benefits**: ongoing perks and privileges granted to a customer based on their current tier or membership status

* Contains both delayed (e.g. “Members have access to dedicated customer service”) and immediate-value (e.g. “Members get 5% off”) benefits.

**Rewards**: the accumulated balances and/or stored value available for the customer to redeem on transactions

* One membership can offer multiple types of accumulable/collectable rewards, each having its own usage and redemption rules.

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

#### Membership Tier

{{ schema_fields('membership_tier', 'loyalty') }}

#### Membership Tier Condition

{{ schema_fields('membership_tier_condition', 'loyalty') }}

#### Membership Tier Benefit

{{ schema_fields('membership_tier_benefit', 'loyalty') }}

#### Membership Reward

{{ schema_fields('membership_reward', 'loyalty') }}

#### Balance Currency

{{ schema_fields('balance_currency', 'loyalty') }}

#### Membership Balance

{{ schema_fields('membership_balance', 'loyalty') }}

#### Expiring Balance

{{ schema_fields('expiring_balance', 'loyalty') }}

#### Balance Redemption

{{ schema_fields('balance_redemption', 'loyalty') }}

## Eligibility Claims

Given almost everything related to loyalty is provisional and requires eligible membership before benefits can be applied, [Context](checkout.md#context) naturally fits here where it allows buyers to claim eligibility for loyalty benefits. When loyalty extension is active and the request contains eligibility claims about loyalty, businesses that choose to accept eligibility claims MUST surface that as an indicator of buyer’s membership status, and if applicable, effects on pricing coming from monetary benefits. Platforms MUST display those provisional loyalty discounts to the buyer.

### Loyalty behavior

In the case platforms run in a “discovery” mode where buyer’s loyalty membership is unknown and there is no interest to request membership sign-up, platforms MAY not pass any loyalty related info in `context.eligibility`. Business MAY respond with a loyalty extension for upsell, if applicable and available. The responded loyalty extension normally contains program information/sign-up conditions/benefit descriptions to entice the buyer and prompt for a sign-up action.

```json
{
  "loyalty": {
    "memberships": [
      {
        "id": "membership_1",
        "name": "My Loyalty Program",
        "tiers": [
          {
            "id": "tier_1",
            "name": "GOLD",
            "level": 1,
            "benefits": [
              {
                "id": "BEN_001",
                "title": "Members save $5",
                "description": "Members receive $5 discount on eligible products"
              }
            ],
            "enrollment_conditions": [
              {
                "id": "CON_001",
                "description": "Free to join"
              }
            ],
            "links": [
              {
                "type": "terms_of_service",
                "url": "loyalty_store.com/terms",
                "title": "Sign-up Terms"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

In the case platforms have prior knowledge about buyer’s membership info, or wish to request membership sign up, they MUST send buyer loyalty membership claims via `context.eligibility`. Businesses MAY run required verification for the membership claim and communicate back the result via `provisional` and `eligibility` fields under membership. The `eligibility` sitting under the membership holds the claim for the general loyalty membership. In case businesses run the verification and the claim is valid/sign up is successful, businesses MUST additionally populate `activated_tiers` on top of `provisional` and `eligibility` fields to communicate the tiers the buyer has. When verification runs but fails, businesses MUST communicate the failure via a recoverable error message that platforms can choose to either remove the claim on the membership entirely and proceed with no member benefits applied or keep the claim but proceed with the membership activation/sign-up flow.

=== "Request with known buyer membership claim"

    ```json
    {
      "context": {
        "eligibility": ["com.example.loyalty"]
      }
    }
    ```

=== "Request"

    ```json
    {
      "context": {
        "eligibility": ["com.example.loyalty"]
      },
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "activated_tiers": ["tier_1"]
          }
        ]
      }
    }
    ```

=== "Response without verification"

    ```json
    {
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "name": "My Loyalty Program",
            "tiers": [
              {
                "id": "tier_1",
                "name": "GOLD",
                "level": 1
              }
            ],
            "provisional": true,
            "eligibility": "com.example.loyalty"
          }
        ]
      }
    }
    ```

=== "Response with verification and valid membership"

    ```json
    {
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "user_id": "user_id_1",
            "name": "My Loyalty Program",
            "enrollment_date": "2022-11-12T00:00:00Z",
            "last_activity_date": "2026-01-12T00:00:00Z",
            "end_date": "2036-01-12T00:00:00Z",
            "tiers": [
              {
                "id": "tier_1",
                "name": "GOLD",
                "level": 1
              }
            ],
            "activated_tiers": ["tier_1"],
            "provisional": false,
            "eligibility": "com.example.loyalty"
          }
        ]
      }
    }
    ```

=== "Response with verification and invalid membership"

    ```json
    {
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "name": "My Loyalty Program",
            "tiers": [
              {
                "id": "tier_1",
                "name": "GOLD",
                "level": 1
              }
            ],
            "provisional": false,
            "eligibility": "com.example.loyalty"
          }
        ]
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

### Loyalty benefits behavior

An eligible membership is sometimes only a preliminary prerequisite of a member-only benefit and a verified claiming of loyalty membership does not necessarily result in a valid claim of associated member-only benefit. For example, in the event of a $50 order, the member-only benefit "Free shipping for all orders" applies while the other member-only discount "Save $10 with $100+ purchase" does not, assuming the buyer is an eligible member. As such, business MUST additionally surface all monetary price impacting benefits as provisional discounts using the `provisional` and `eligibility` fields within the `discounts.applied` object (referenced by the `applies_on` field within `benefit`). When membership is valid but there are benefits that are inapplicable, businesses MUST communicate this via the message[] array. Depending on the type of inapplicable benefits (e.g. they are affecting the order totals), businesses can choose the message type between warning or info to get them surfaced.

=== "Response without verification"

    ```json
    {
      "discounts": {
        "applied": [
          {
            "title": "Free shipping",
            "amount": 200,
            "method": "each",
            "provisional": true,
            "eligibility": "com.example.loyalty",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 200}
            ]
          },
          {
            "title": "Save $10 with $100+ order",
            "amount": 100,
            "method": "each",
            "provisional": true,
            "eligibility": "com.example.loyalty",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 100}
            ]
          }
        ]
      },
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "name": "My Loyalty Program",
            "tiers": [
              {
                "id": "tier_1",
                "name": "GOLD",
                "level": 1,
                "benefits": [
                  {
                    "id": "BEN_001",
                    "title": "Free shipping",
                    "description": "Complimentary standard shipping on all orders",
                    "applies_on": "$.discounts.applied[0]"
                  },
                  {
                    "id": "BEN_002",
                    "title": "Early access",
                    "description": "24-hour early access to seasonal sales"
                  },
                  {
                    "id": "BEN_003",
                    "title": "Save $10 with $100+ order",
                    "description": "Get $10 discount when purchase order is $100+",
                    "applies_on": "$.discounts.applied[1]"
                  }
                ]
              }
            ],
            "provisional": true,
            "eligibility": "com.example.loyalty"
          }
        ]
      }
    }
    ```

=== "Response with valid membership and benefits"

    ```json
    {
      "discounts": {
        "applied": [
          {
            "title": "Free shipping",
            "amount": 200,
            "method": "each",
            "provisional": false,
            "eligibility": "com.example.loyalty",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 200}
            ]
          },
          {
            "title": "Save $10 with $100+ order",
            "amount": 100,
            "method": "each",
            "provisional": false,
            "eligibility": "com.example.loyalty",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 100}
            ]
          }
        ]
      },
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "user_id": "user_id_1",
            "name": "My Loyalty Program",
            "enrollment_date": "2022-11-12T00:00:00Z",
            "last_activity_date": "2026-01-12T00:00:00Z",
            "end_date": "2036-01-12T00:00:00Z",
            "tiers": [
              {
                "id": "tier_1",
                "name": "GOLD",
                "level": 1,
                "benefits": [
                  {
                    "id": "BEN_001",
                    "title": "Free shipping",
                    "description": "Complimentary standard shipping on all orders",
                    "applies_on": "$.discounts.applied[0]"
                  },
                  {
                    "id": "BEN_002",
                    "title": "Early access",
                    "description": "24-hour early access to seasonal sales"
                  },
                  {
                    "id": "BEN_003",
                    "title": "Save $10 with $100+ order",
                    "description": "Get $10 discount when purchase order is $100+",
                    "applies_on": "$.discounts.applied[1]"
                  }
                ]
              }
            ],
            "activated_tiers": ["tier_1"],
            "provisional": false,
            "eligibility": "com.example.loyalty"
          }
        ]
      }
    }
    ```

=== "Response with valid membership and partially valid benefits"

    ```json
    {
      "discounts": {
        "applied": [
          {
            "title": "Free shipping",
            "amount": 200,
            "method": "each",
            "provisional": false,
            "eligibility": "com.example.loyalty",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 200}
            ]
          }
        ]
      },
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "user_id": "user_id_1",
            "name": "My Loyalty Program",
            "enrollment_date": "2022-11-12T00:00:00Z",
            "last_activity_date": "2026-01-12T00:00:00Z",
            "end_date": "2036-01-12T00:00:00Z",
            "tiers": [
              {
                "id": "tier_1",
                "name": "GOLD",
                "level": 1,
                "benefits": [
                  {
                    "id": "BEN_001",
                    "title": "Free shipping",
                    "description": "Complimentary standard shipping on all orders",
                    "applies_on": "$.discounts.applied[0]"
                  },
                  {
                    "id": "BEN_002",
                    "title": "Early access",
                    "description": "24-hour early access to seasonal sales"
                  },
                  {
                    "id": "BEN_003",
                    "title": "Save $10 with $100+ order",
                    "description": "Get $10 discount when purchase order is $100+",
                  }
                ]
              }
            ],
            "activated_tiers": ["tier_1"],
            "provisional": false,
            "eligibility": "com.example.loyalty"
          }
        ]
      },
      "messages": [
        {
          "type": "info",
          "code": "membership_benefit_ineligible",
          "path": "$.loyalty.memberships[0].tiers[0].benefits[2]",
          "content": "Member benefit is not eligible for the buyer"
        }
      ]
    }
    ```

## Use Cases and Examples

### Loyalty benefits discovery and upsell

Potential savings from member-only benefits can be shown in the upper-funnel discovery stage. No buyer membership is known or claimed in the request and business responses with the saving and program info for upsell.

=== "Request"

    ```json
    {
      "line_items": [
        {
          "item": {
            "id": "prod_1",
            "quantity": 1,
            "title": "T-Shirt",
            "price": 4000
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
            "price": 4000
          },
          "totals": [
            {"type": "subtotal", "amount": 4000},
            {"type": "total", "amount": 4000}
          ]
        }
      ],
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "name": "My Loyalty Program",
            "tiers": [
              {
                "id": "tier_1",
                "name": "GOLD",
                "level": 1,
                "benefits": [
                  {
                    "id": "BEN_001",
                    "title": "Members save $5",
                    "description": "Members receive $5 discount on eligible products"
                  },
                  {
                    "id": "BEN_002",
                    "title": "Early access",
                    "description": "24-hour early access to seasonal sales",
                  }
                ],
                "enrollment_conditions": [
                  {
                    "id": "CON_001",
                    "description": "Free to join"
                  }
                ],
                "links": [
                  {
                    "type": "terms_of_service",
                    "url": "loyalty_store.com/terms",
                    "title": "Sign-up Terms"
                  }
                ]
              }
            ]
          }
        ]
      },
      "totals": [
        {"type": "subtotal", "display_text": "Subtotal", "amount": 4000},
        {"type": "total", "display_text": "Estimated Total", "amount": 4000}
      ]
    }
    ```

### Membership sign-up

Buyer requests for membership sign-up after learning the benefits and business successfully register the buyer. Note that membership sign-up flow may or may not involve any product (i.e. may happen in early checkout phase, or in a pure account-linking flow), and thus the associated capability that loyalty extension attaches to is open.

=== "Request"

    ```json
    {
      "context": {
        "eligibility": ["com.example.loyalty"]
      },
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "activated_tiers": ["tier_1"]
          }
        ]
      }
    }
    ```

=== "Response"

    ```json
    {
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "member_id": "user_id_1",
            "name": "My Loyalty Program",
            "enrollment_date": "2026-01-12T00:00:00Z",
            "last_activity_date": "2026-01-12T00:00:00Z",
            "end_date": "2036-01-12T00:00:00Z",
            "tiers": [
              {
                "id": "tier_1",
                "name": "GOLD",
                "level": 1,
                "benefits": [
                  {
                    "id": "BEN_001",
                    "title": "Members save $5",
                    "description": "Members receive $5 discount on eligible products",
                  },
                  {
                    "id": "BEN_002",
                    "title": "Early access",
                    "description": "24-hour early access to seasonal sales",
                  }
                ]
              }
            ],
            "activated_tiers": ["tier_1"],
            "rewards": [
              {
                "currency": {
                  "name": "LoyaltyStars",
                  "code": "LST",
                },
                "balance": {
                  "available": 0,
                }
              }
            ],
            "provisional": false,
            "eligibility": "com.example.loyalty"
          }
        ]
      }
    }
    ```

### Member pricing

Buyer, as a loyalty member, receives a special lower price on eligible items. Business immediately runs the verification to check that the buyer is a valid member and the member pricing discount is no longer provisional.

=== "Request"

    ```json
    {
      "context": {
        "eligibility": ["com.example.loyalty"]
      },
      "line_items": [
        {
          "item": {
            "id": "prod_shirt",
            "quantity": 1,
            "title": "T-Shirt",
            "price": 4000
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
            "price": 4000
          },
          "totals": [
            {"type": "subtotal", "amount": 4000},
            {"type": "items_discount", "amount": -500},
            {"type": "total", "amount": 3500}
          ]
        }
      ],
      "discounts": {
        "applied": [
          {
            "title": "Members save $5",
            "amount": 500,
            "automatic": true,
            "provisional": false,
            "eligibility": "com.example.loyalty",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 500}
            ]
          }
        ]
      },
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "member_id": "user_id_1",
            "name": "My Loyalty Program",
            "enrollment_date": "2026-01-12T00:00:00Z",
            "last_activity_date": "2026-01-12T00:00:00Z",
            "end_date": "2036-01-12T00:00:00Z",
            "tiers": [
              {
                "id": "tier_1",
                "name": "GOLD",
                "level": 1,
                "benefits": [
                  {
                    "id": "BEN_001",
                    "title": "Members save $5",
                    "description": "Members receive $5 discount on eligible products",
                    "applies_on": "$.discounts.applied[0]"
                  },
                  {
                    "id": "BEN_002",
                    "title": "Early access",
                    "description": "24-hour early access to seasonal sales",
                  }
                ]
              }
            ],
            "activated_tiers": ["tier_1"],
            "rewards": [
              {
                "currency": {
                  "name": "LoyaltyStars",
                  "code": "LST",
                },
                "balance": {
                  "available": 1000,
                }
              }
            ],
            "provisional": false,
            "eligibility": "com.example.loyalty"
          }
        ]
      },
      "totals": [
        {"type": "subtotal", "display_text": "Subtotal", "amount": 4000},
        {"type": "items_discount", "display_text": "Member Discounts", "amount": -500},
        {"type": "total", "display_text": "Estimated Total", "amount": 3500}
      ]
    }
    ```

### Point redemption

Buyer accumulates rewards through past transactions and they can be redeemed for total cost reduction. Rewards redemption also requires valid membership.

=== "Request"

    ```json
    {
      "context": {
        "eligibility": ["com.example.loyalty"]
      },
      "line_items": [
        {
          "item": {
            "id": "prod_shirt",
            "quantity": 1,
            "title": "T-Shirt",
            "price": 4000
          }
        }
      ],
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "member_id": "member_id_1",
            "rewards": [
              {
                "currency": {
                  "code": "LST"
                },
                "redemption": {
                  "amount": 500
                }
              }
            ]
          }
        ]
      }
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
            "price": 4000
          },
          "totals": [
            {"type": "subtotal", "amount": 4000},
            {"type": "items_discount", "amount": -500},
            {"type": "total", "amount": 3500}
          ]
        }
      ],
      "discounts": {
        "applied": [
          {
            "title": "Point Redemption",
            "amount": 500,
            "automatic": true,
            "provisional": false,
            "eligibility": "com.example.loyalty",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 500}
            ]
          }
        ]
      },
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "member_id": "user_id_1",
            "name": "My Loyalty Program",
            "enrollment_date": "2026-01-12T00:00:00Z",
            "last_activity_date": "2026-01-12T00:00:00Z",
            "end_date": "2036-01-12T00:00:00Z",
            "tiers": [
              {
                "id": "tier_1",
                "name": "GOLD",
                "level": 1,
                "benefits": [
                  {
                    "id": "BEN_001",
                    "title": "Early access",
                    "description": "24-hour early access to seasonal sales",
                  }
                ]
              }
            ],
            "activated_tiers": ["tier_1"],
            "rewards": [
              {
                "currency": {
                  "name": "LoyaltyStars",
                  "code": "LST"
                },
                "balance": {
                  "available": 500
                },
                "redemption": {
                  "amount": 500,
                  "applies_on": "$.discounts.applied[0]"
                }
              }
            ],
            "provisional": false,
            "eligibility": "com.example.loyalty"
          }
        ]
      },
      "totals": [
        {"type": "subtotal", "display_text": "Subtotal", "amount": 4000},
        {"type": "items_discount", "display_text": "Point Redemption", "amount": -500},
        {"type": "total", "display_text": "Estimated Total", "amount": 3500}
      ]
    }
    ```

### Membership-based Card Benefit

For a large portion of loyalty programs, membership-based credit cards (i.e. co-branded credit cards) are a key way for buyers to receive the most valuable benefits and for businesses to reward their core customers. Such a use case can be modeled as one of the tiers of the loyalty program (and usually the highest tier) and naturally fits with the data modeling.

In the example below, the buyer has two eligibility claims related to loyalty: one as being a regular member of the program (when buyers sign up for a co-branded credit card that belongs to a loyalty program, they are normally required to have an account with the business that naturally put them into the loyalty program with the lowest tier), and the other being the co-branded credit card holder.

=== "Request"

    ```json
    {
      "context": {
        "eligibility": ["com.example.loyalty", "com.example.loyalty.benefit_card"]
      },
      "line_items": [
        {
          "item": {
            "id": "prod_shirt",
            "quantity": 1,
            "title": "T-Shirt",
            "price": 4000
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
            "price": 4000
          },
          "totals": [
            {"type": "subtotal", "amount": 4000},
            {"type": "items_discount", "amount": -200},
            {"type": "total", "amount": 3500}
          ]
        }
      ],
      "discounts": {
        "applied": [
          {
            "title": "Membership credit card holder saves 5%",
            "amount": 200,
            "automatic": true,
            "provisional": false,
            "eligibility": "com.example.loyalty.benefit_card",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 200}
            ]
          }
        ]
      },
      "loyalty": {
        "memberships": [
          {
            "id": "membership_1",
            "member_id": "user_id_1",
            "name": "My Loyalty Program",
            "enrollment_date": "2026-01-12T00:00:00Z",
            "last_activity_date": "2026-01-12T00:00:00Z",
            "end_date": "2036-01-12T00:00:00Z",
            "tiers": [
              {
                "id": "tier_1",
                "name": "GOLD",
                "level": 1,
                "benefits": [
                  {
                    "id": "BEN_001",
                    "title": "Early access",
                    "description": "24-hour early access to seasonal sales",
                  }
                ]
              },
              {
                "id": "tier_2",
                "name": "CREDIT_CARD",
                "level": 2,
                "benefits": [
                  {
                    "id": "BEN_001",
                    "title": "Membership credit card holder saves 5%",
                    "description": "Members receive $5 discount on eligible products",
                    "applies_on": "$.discounts.applied[0]"
                  },
                  {
                    "id": "BEN_002",
                    "title": "Early access",
                    "description": "24-hour early access to seasonal sales",
                  }
                ]
              }
            ],
            "activated_tiers": ["tier_1", "tier_2"],
            "provisional": false,
            "eligibility": "com.example.loyalty"
          }
        ]
      },
      "totals": [
        {"type": "subtotal", "display_text": "Subtotal", "amount": 4000},
        {"type": "items_discount", "display_text": "Member Discounts", "amount": -200},
        {"type": "total", "display_text": "Estimated Total", "amount": 3800}
      ]
    }
    ```
