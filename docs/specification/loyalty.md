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

* **Checkout**: For applying member-specific discounts/fulfillment benefits, calculating point earnings, or initiating reward redemptions, in conjunction with discount extension to specify the monetary effect of applicable loyalty benefits
* **Cart**: For displaying the loyalty benefits for potential usage on subsequent checkout (e.g. redeemable balance, tier evaluations), with or without the help of discount extension to upsell potential savings and non-monetary benefits from membership

In the future, for membership lifecycle management by agents (e.g. membership status fetching, program sign-up, balance transfer, etc.). it is possible that loyalty could be considered an independent capability. The other direction is fitting them within higher-order account and profile management capabilities that allow for broader operations, with loyalty being a subset and hence potentially represented by the same extension as it. This is not yet finalized among community discussion and pending future updates to achieve.

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

{{ schema_fields('types/loyalty', 'loyalty') }}

#### Loyalty Membership

{{ schema_fields('types/loyalty_membership', 'loyalty') }}

#### Membership Tier

{{ schema_fields('types/membership_tier', 'loyalty') }}

#### Membership Tier Condition

{{ schema_fields('types/membership_tier_condition', 'loyalty') }}

#### Membership Tier Benefit

{{ schema_fields('types/membership_tier_benefit', 'loyalty') }}

#### Membership Reward

{{ schema_fields('types/membership_reward', 'loyalty') }}

#### Balance Currency

{{ schema_fields('types/balance_currency', 'loyalty') }}

#### Membership Balance

{{ schema_fields('types/membership_balance', 'loyalty') }}

#### Expiring Balance

{{ schema_fields('types/expiring_balance', 'loyalty') }}

#### Balance Redemption

{{ schema_fields('types/balance_redemption', 'loyalty') }}

### Example

```json
{
  "memberships": [
    {
      "id": "membership_1",
      "member_id": "member_id_1",
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
              "title": "24-hour Early access",
              "description": "24-hour early access to seasonal sales"
            }
          ],
          "conditions": [
            {
              "id": "CON_001",
              "description": "Free to join",
              "condition_type": "free"
            }
          ],
          "links": [
            {
              "type": "terms_of_service",
              "url": "loyalty.com/terms",
              "title": "Sign-up Terms"
            }
          ]
        },
        {
          "id": "tier_2",
          "name": "PLATINUM",
          "level": 2,
          "benefits": [
            {
              "id": "BEN_001",
              "title": "Free shipping",
              "description": "Complimentary standard shipping on all orders",
              "applies_on": ["$.discounts.applied[0]"]
            },
            {
              "id": "BEN_002",
              "title": "48-hour Early access",
              "description": "48-hour early access to seasonal sales"
            },
            {
              "id": "BEN_003",
              "title": "Member discount",
              "description": "Members get $5 off",
              "applies_on": ["$.discounts.applied[1]"]
            }
          ],
          "enrollment_conditions": [
            {
              "id": "CON_002",
              "description": "$99/yr membership fee",
              "condition_type": "fee"
            }
          ],
          "links": [
            {
              "type": "terms_of_service",
              "url": "loyalty.com/terms",
              "title": "Sign-up Terms"
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
            "available": 4500,
            "pending": 250,
            "lifetime_earned": 25000,
            "lifetime_redeemed": 1000,
            "expiring": [
              {
                "amount": 500,
                "expiry_date": "2026-12-31T23:59:59Z",
                "reason": "ANNUAL_EXPIRATION"
              }
            ]
          },
          "redemption": {
            "amount": 100,
            "applies_on": ["$.discounts.applied[0]"]
          }
        }
      ]
    }
  ],
  "activated_memberships": ["membership_1"]
}
```

## Behavior and Expectations

### Request

* Non-empty `activated_memberships` and `activated_tiers` implies membership sign-up intention from the customer. No eligibility verification needed, but can rely on the `condition_type` of `membership_tier_condition` within each `membership_tier`to provide selections for customers (e.g. only offer `free` typed tier for sign up).
* Render applicable loyalty benefits based on the human-readable `title` and `description` provided, and highlight the source of immediate-value benefits alongside where they are applied based on the back referencing from `applies_on` to provide necessary disclosure or explanation.
* Only request rewards redemption when there is non-zero available balance but no need to run any extra check as redemption rules can be complicated even if there is sufficient available balance for example.

### Response

* Check and determine user’s eligibility in context (e.g. checkout with member benefits applied, checkout with rewards redemption, sign-up new membership etc) for both existing and prospective customers. When eligibility condition is not met, response clear ERROR message to indicate that.
* Populate `applies_on` when immediate-value membership benefits are applicable to the transaction and reference them to the corresponding line items.
* Provide a comprehensive list of tiers that the membership offers, but at the minimum it MUST contain the ones that the customer is activated with (if applicable).
* For memberships that do not have a tiered system (i.e. loyalty level can not be upgraded or downgraded), it MUST still be treated as a single-tiered membership.
* Businesses MUST respond with at least one benefit and SHOULD aim to provide a comprehensive list.
