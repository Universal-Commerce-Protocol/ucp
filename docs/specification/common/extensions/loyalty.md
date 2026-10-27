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

The loyalty extension is designed to facilitate high-fidelity loyalty experiences:
ensuring existing loyalty members can seamlessly access their membership status,
balances, and benefits across upper-funnel Identity and Catalog discovery as well as
lower-funnel Cart and Checkout experiences. By enabling buyers to see their specific
tier, progress toward next-tier milestones, redeemable reward balances, available
credits, and applicable benefits before finalizing a purchase, it addresses a
foundational expectation for program members across retail and travel verticals.

Specifically the following core use cases of benefit recognition for known members are
addressed:

* Upper-Funnel Profile & Balance Visibility: Retrieval of verified loyalty memberships,
  active tiers, tier benefits, reward balances (including expiration dates), non-point
  credits or certificates, and tier progress metrics via the
  [Identity Capability](../identity/index.md).
* Price-Impacting Benefits: Real-time application of member-only discounts and free
  shipping offers with clear attribution of benefit sources.
* Non-Price Benefits: Transparent display of rewards earned or rewards applicable to
  future purchases.
* Status Recognition: Verification and display of the buyers’ specific loyalty tier within
  a program.

## Key Concepts

Loyalty is organized around the following core components:

**Memberships**: Distinct enrollment pathways or program categories that a user can join

* Independent programs offered by the same brand (e.g., a "Rewards Club" vs. a "Co-branded
  Credit Card") are modeled as separate, independently verifiable memberships. They are
  programmatically represented as separate sibling top-level keys in the loyalty extension
  map, namespaced by reverse-domain naming.

**Tiers and Tier Progress**: Specific achievement ranks or status milestones within a
membership that unlock escalating value as a member progresses through activity or spend

* A member typically holds a single active tier per membership. For programs with parallel
  status dimensions (e.g., holding both "Gold" and "Lifetime Platinum"), multiple tiers
  can be active concurrently.
* `tier_progress` tracks how close the member is to achieving a higher tier across one or
  more qualification metrics (such as `nights`, `stays`, `spend`, or `qualifying_points`),
  combined via `qualification_operator` (`any` or `all`).

**Benefits**: Ongoing perks and privileges granted to a customer based on their current
tier or membership status

* Contains both delayed (e.g. “Members have access to dedicated customer service”) and
  immediate-value (e.g. “Members get 5% off”) benefits.

**Rewards**: Quantifiable loyalty value accumulated or earned by the member

* One membership can offer multiple types of accumulable/collectable rewards, each having
  its own usage and redemption rules.
* Each `membership_reward` entry pairs a `currency` definition with an optional current
  redeemable `balance` (including optional `expires_at`) and an optional transactional
  `earning_forecast`. Executing points redemption at payment time is modeled by the
  negotiated payment instrument or a dedicated redemption capability.

**Credits**: Non-point entitlements held by the member

* `credits` represents non-point monetary credits (e.g., an annual travel credit) and award
  certificates (e.g., a Free Night Award voucher) with remaining value and expiration
  metadata.

<!-- ucp:example schema=common/loyalty def=loyalty extract=$.loyalty -->
```json
{
  "loyalty": {
    "com.example.loyalty": {
      "id": "membership_1",
      "display_id": "****5678",
      "name": "Example Rewards",
      "tiers": [
        {
          "id": "gold",
          "name": "Gold",
          "benefits": [
            {
              "id": "BEN_001",
              "description": "Complimentary standard shipping on all orders"
            }
          ]
        }
      ],
      "rewards": [
        {
          "currency": { "name": "LoyaltyStars", "code": "LST" },
          "balance": {
            "amount": 4500,
            "expires_at": "2027-12-31T23:59:59Z"
          }
        }
      ],
      "provisional": false
    }
  }
}
```

## Discovery

Businesses can follow the standard advertising mechanism to advertise loyalty support in
the Business profile. Currently the loyalty extension can decorate identity, catalog search,
catalog lookup, cart, and checkout capabilities. Businesses MAY advertise loyalty
support for any subset of these capabilities. Platforms SHOULD check which resources are
extended.

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.identity": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/identity",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/identity.json"
        }
      ],
      "dev.ucp.shopping.catalog.search": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/catalog/search",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/catalog_search.json"
        }
      ],
      "dev.ucp.shopping.catalog.lookup": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/catalog/lookup",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/catalog_lookup.json"
        }
      ],
      "dev.ucp.shopping.cart": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/cart",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/cart.json"
        }
      ],
      "dev.ucp.shopping.checkout": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/checkout",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.common.loyalty": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.common.identity",
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup",
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/extensions/loyalty",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/loyalty.json"
        }
      ]
    }
  }
}
```

**Dependencies:**

* Identity Capability
* Catalog Search Capability
* Catalog Lookup Capability
* Cart Capability
* Checkout Capability

## Schema

### Entities

#### Loyalty

{{ extension_schema_fields('loyalty.json#/$defs/loyalty', 'common/extensions/loyalty') }}

#### Loyalty Membership

{{ extension_schema_fields('loyalty.json#/$defs/loyalty_membership', 'common/extensions/loyalty') }}

#### Membership Tier

{{ extension_schema_fields('loyalty.json#/$defs/membership_tier', 'common/extensions/loyalty') }}

#### Membership Tier Benefit

{{ extension_schema_fields('loyalty.json#/$defs/membership_tier_benefit', 'common/extensions/loyalty') }}

#### Tier Progress

{{ extension_schema_fields('loyalty.json#/$defs/tier_progress', 'common/extensions/loyalty') }}

#### Tier Progress Metric

{{ extension_schema_fields('loyalty.json#/$defs/tier_progress_metric', 'common/extensions/loyalty') }}

#### Membership Reward

{{ extension_schema_fields('loyalty.json#/$defs/membership_reward', 'common/extensions/loyalty') }}

#### Reward Balance

{{ extension_schema_fields('loyalty.json#/$defs/reward_balance', 'common/extensions/loyalty') }}

#### Reward Amount

{{ extension_schema_fields('loyalty.json#/$defs/reward_amount', 'common/extensions/loyalty') }}

#### Reward Currency

{{ extension_schema_fields('loyalty.json#/$defs/reward_currency', 'common/extensions/loyalty') }}

#### Earning Forecast

{{ extension_schema_fields('loyalty.json#/$defs/earning_forecast', 'common/extensions/loyalty') }}

#### Earning Breakdown

{{ extension_schema_fields('loyalty.json#/$defs/earning_breakdown', 'common/extensions/loyalty') }}

#### Available Credit

{{ extension_schema_fields('loyalty.json#/$defs/available_credit', 'common/extensions/loyalty') }}

## Loyalty behavior

The loyalty extension holds a key-value map whose keys are reverse-domain identifiers —
the same convention as services, capabilities, and payment handlers in the business
profile. The keys represent eligibility claims about loyalty memberships that
businesses recognize. The values contain membership information corresponding to those
claims and use the required `provisional` field to indicate the verification state.

Programs that can be joined independently MUST be modeled as separate sibling entries
under the loyalty map, distinguished by their reverse-domain naming.

Platforms MAY send buyer loyalty membership claims via `context.eligibility` in the
request to activate the loyalty extension and claim loyalty benefits on capabilities that
accept `context` (catalog search, catalog lookup, cart, and checkout). Alternatively,
when the buyer is authenticated — including on `GET /identity` via
[`dev.ucp.common.identity`](../identity/index.md) — and the business can determine
loyalty membership from the authenticated identity, businesses MAY populate the loyalty
extension without an explicit eligibility claim. In this case, the map key MUST be the
same reverse-domain identifier the business would accept as a claim value. This is a
specific instance of the general pattern where identity linking lets a business return
its own user state on a response; see
[Business-Populated Response Values](../identity-linking/index.md#business-populated-response-values).

* When a business verifies a membership claim or determines membership from
  authenticated identity, it MUST return `provisional: false`. It MUST populate the
  active tier(s) the buyer holds within the `tiers` array **when the program has
  tier structure** — for programs with no tier concept (flat-rate cashback,
  single-status memberships), businesses MAY omit `tiers`. It also SHOULD set
  `display_id` as a masked unique identifier for the buyer, and MAY populate
  authenticated account state such as `rewards[].balance`, `tier_progress`, and
  `credits`.
* When a membership claim in the request is recognized and accepted but not verified by
  the business, the business MUST return `provisional: true`. It MAY return display-safe
  tier context for the state accepted during the session, and MUST NOT return
  `display_id`, `rewards[].balance`, `tier_progress`, or `credits` until the
  membership is verified.
* When a membership claim in the request is accepted but cannot be verified, the business
  MUST communicate the failure via a recoverable `message` with `type: "error"` and
  `code: "eligibility_invalid"`. Platforms MAY then choose to remove the membership claim
  and proceed through checkout without loyalty benefits applied.

At checkout completion, all accepted but unverified loyalty claims MUST be resolved per
the [Eligibility Verification at Completion](../../shopping/checkout/index.md#eligibility-verification-at-completion)
contract defined in the checkout capability.

### Monetary loyalty benefits

Monetary price-impacting loyalty benefits (e.g. member pricing/shipping) can have
conditions beyond membership, such as saving $10 only after a $500+ purchase. Businesses
MUST evaluate those conditions before applying the benefit.

When the benefit applies, businesses MUST surface the price impact through the base
capability's price fields. Catalog responses use `price` / `list_price` and
`price_range` / `list_price_range`; cart and checkout responses use `totals` or
`line_items[].totals` with `type: "items_discount"` (for member pricing) / `type: "discount"`
(for member shipping) and `display_text` to attribute the loyalty source when possible.

For cart and checkout responses, when the discount extension is active, businesses
SHOULD also populate `discounts.applied[]` for structured attribution. In that case,
`eligibility` identifies the claim required for the discount. If the discount still
requires verification, for example because one or more accepted loyalty claims remain
unverified, the corresponding applied discount MUST set `provisional: true`.

If the benefit does not apply, businesses SHOULD notify the buyer via messages with
`type: "warning"` and explain the inapplicability of those monetary loyalty benefits.
Businesses MUST NOT put inapplicable benefits in the discount extension. Instead they
MAY set them as part of `benefits` within the loyalty extension and set the warning
message `path` to reference the relevant membership for additional context.

When loyalty membership claims are accepted, businesses MAY use `type: "info"` to
explain the effects of applied monetary loyalty benefits.

**Loyalty benefits message codes:**

| Type      | Code                            | When                                                 |
| --------- | ------------------------------- | ---------------------------------------------------- |
| `info`    | `membership_benefit_eligible`   | Specific benefit confirmed applicable to this order  |
| `warning` | `membership_benefit_ineligible` | Benefit exists but conditions not met for this order |

The examples below are abbreviated to focus on loyalty and discount extension fields;
complete cart and checkout responses also include base required fields such as `ucp`,
`id`, `currency`, and `totals`.

Building on the store loyalty card example from
[Eligibility Verification at Completion](../../shopping/checkout/index.md#eligibility-verification-at-completion),
assume the card offers one unconditional product discount and one conditional discount
that the current checkout cart fails to satisfy. The platform can surface the first
provisional discount with disclaimers like "verified at purchase" and additionally show
a warning message to disclose the inapplicability of the second discount.

=== "Request"

    <!-- ucp:example schema=shopping/cart op=create direction=request -->
    ```json
    {
      "context": {
        "eligibility": ["com.example.loyalty.store_card"]
      },
      "line_items": [
        {
          "item": {
            "id": "prod_1"
          },
          "quantity": 1
        }
      ]
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/loyalty def=loyalty extract=$.loyalty -->
    ```json
    {
      "discounts": {
        "applied": [
          {
            "title": "Loyalty benefit 1",
            "amount": 10,
            "provisional": true,
            "eligibility": "com.example.loyalty.store_card",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 10}
            ]
          }
        ]
      },
      "loyalty": {
        "com.example.loyalty.store_card": {
          "id": "membership_1",
          "name": "My Loyalty Program",
          "tiers": [
            {
              "id": "cardholder",
              "name": "Store Cardholder",
              "benefits": [
                { "id": "BEN_001", "description": "Get $10 off with $500+ purchase." },
                { "id": "BEN_002", "description": "Early access to sales" }
              ]
            }
          ],
          "provisional": true
        }
      },
      "messages": [
        {
          "type": "warning",
          "code": "membership_benefit_ineligible",
          "path": "$.loyalty['com.example.loyalty.store_card']",
          "content": "Cart size is smaller than required to receive the $10 discount."
        }
      ]
    }
    ```

The buyer can proceed to checkout without any cart update. If the claim is verified
successfully by the business, the unconditional member-pricing discount becomes
non-provisional and `display_id` is returned.

=== "Request"

    <!-- ucp:example schema=shopping/cart op=create direction=request -->
    ```json
    {
      "context": {
        "eligibility": ["com.example.loyalty.store_card"]
      },
      "line_items": [
        {
          "item": {
            "id": "prod_1"
          },
          "quantity": 1
        }
      ]
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/loyalty def=loyalty extract=$.loyalty -->
    ```json
    {
      "discounts": {
        "applied": [
          {
            "title": "Loyalty benefit 1",
            "amount": 10,
            "provisional": false,
            "eligibility": "com.example.loyalty.store_card",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 10}
            ]
          }
        ]
      },
      "loyalty": {
        "com.example.loyalty.store_card": {
          "id": "membership_1",
          "display_id": "****5678",
          "name": "My Loyalty Program",
          "tiers": [
            {
              "id": "tier_1",
              "name": "Store Cardholder",
              "benefits": [
                { "id": "BEN_001", "description": "Get $10 off with $500+ purchase." },
                { "id": "BEN_002", "description": "Early access to sales" }
              ]
            }
          ],
          "provisional": false
        }
      }
    }
    ```

If the claim cannot be verified, the business MUST return a recoverable error via
`messages[]`  with `code: "eligibility_invalid"`.

=== "Request"

    <!-- ucp:example schema=shopping/cart op=create direction=request -->
    ```json
    {
      "context": {
        "eligibility": ["com.example.loyalty.store_card"]
      },
      "line_items": [
        {
          "item": {
            "id": "prod_1"
          },
          "quantity": 1
        }
      ]
    }
    ```

=== "Response"

    <!-- ucp:example schema=shopping/cart extract=$.messages target=$.messages -->
    ```json
    {
      "messages": [
        {
          "type": "error",
          "severity": "recoverable",
          "code": "eligibility_invalid",
          "content": "Buyer is not a store card holder."
        }
      ]
    }
    ```

## Use Cases and Examples

With the help of the loyalty extension, the identity, catalog, cart, and checkout
capabilities can be decorated to provide full visibility into buyers’ loyalty status,
redeemable balances, tier progress, available credits, and member-exclusive perks across
the commerce journey.

### Upper-Funnel Loyalty Profile Retrieval

When a buyer has linked their account with a business via
[Identity Linking](../identity-linking/index.md), the platform can invoke
[`GET /identity`](../identity/rest.md) (or the MCP [`get_identity`](../identity/mcp.md)
tool) to retrieve the buyer's verified loyalty memberships before initiating a cart,
checkout, or booking session. This allows the platform to surface loyalty status,
redeemable balances with expiration dates, available non-point credits or award
certificates, and progress toward higher tiers during upper-funnel search and
discovery.

=== "Request"

    ```http
    GET /identity HTTP/1.1
    Host: business.example.com
    Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Request-Id: 8a7b6c5d-4e3f-4210-89ab-cdef01234567
    Accept: application/json
    ```

=== "Response"

    <!-- ucp:example schema=common/identity op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.common.identity": [
            { "version": "{{ ucp_version }}" }
          ],
          "dev.ucp.common.loyalty": [
            {
              "version": "{{ ucp_version }}",
              "extends": "dev.ucp.common.identity"
            }
          ]
        }
      },
      "id": "usr_9f8e7d6c",
      "loyalty": {
        "com.example.hospitality.rewards": {
          "id": "mem_774411",
          "display_id": "****4411",
          "name": "Example Hospitality Rewards",
          "provisional": false,
          "tiers": [
            {
              "id": "explorist",
              "name": "Explorist",
              "benefits": [
                {
                  "id": "BEN_UPGRADE",
                  "description": "Upgrade to best available room (excluding suites) at check-in"
                },
                {
                  "id": "BEN_LATE_OUT",
                  "description": "2:00 PM late checkout upon request"
                }
              ]
            }
          ],
          "tier_progress": [
            {
              "target_tier_id": "globalist",
              "target_tier_name": "Globalist",
              "qualification_operator": "any",
              "qualification_period_ends_at": "2026-12-31T23:59:59Z",
              "metrics": [
                {
                  "metric_type": "nights",
                  "unit": "NIGHTS",
                  "current_amount": 48,
                  "target_amount": 60,
                  "remaining_amount": 12,
                  "description": "12 qualifying nights needed for Globalist"
                },
                {
                  "metric_type": "qualifying_points",
                  "unit": "BASE_PTS",
                  "current_amount": 75000,
                  "target_amount": 100000,
                  "remaining_amount": 25000,
                  "description": "25,000 base points needed for Globalist"
                }
              ]
            }
          ],
          "rewards": [
            {
              "currency": {
                "name": "Hospitality Points",
                "code": "EHP"
              },
              "balance": {
                "amount": 85000,
                "expires_at": "2027-12-31T23:59:59Z"
              }
            }
          ],
          "credits": [
            {
              "id": "cred_fna_cat4",
              "name": "Category 1-4 Free Night Award",
              "type": "certificate",
              "remaining_amount": 1,
              "total_amount": 1,
              "expires_at": "2026-11-15T23:59:59Z",
              "description": "Redeemable for one standard night at any Category 1-4 property."
            },
            {
              "id": "cred_dining_2026",
              "name": "$100 Property Dining Credit",
              "type": "monetary_credit",
              "remaining_amount": 6500,
              "total_amount": 10000,
              "currency": "USD",
              "expires_at": "2026-12-31T23:59:59Z",
              "description": "Remaining balance of annual on-property dining credit."
            }
          ]
        }
      }
    }
    ```

### Price-Impacting Benefits

The loyalty extension can provide buyer status information that helps the platform
explain member discounts. Price-impacting loyalty benefits are reflected in the base
capability's price fields. When the discount extension is also active, the platform can
explain each discount via `discounts.applied[].title` and correlate
`discounts.applied[].eligibility` back to `loyalty` entries to show which accepted
membership claims produced the monetary benefit. In the example below, the buyer
receives a 15% bonus discount and free shipping benefit respectively because they
hold the Retail Club membership and the Retail Card. The platform can then render
“Retail Club Gold Member and Retail Card benefits applied,” for example.

=== "Request"

    <!-- ucp:example schema=shopping/cart op=create direction=request -->
    ```json
    {
      "context": {
        "eligibility": [
          "com.example.retail_club",
          "com.example.retail_card"
        ]
      },
      "line_items": [
        {
          "item": {
            "id": "prod_1"
          },
          "quantity": 1
        }
      ]
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/loyalty def=loyalty extract=$.loyalty -->
    ```json
    {
      "line_items": [
        {
          "id": "li_1",
          "item": {
            "id": "prod_1",
            "title": "T-Shirt",
            "price": 1000
          },
          "quantity": 1,
          "totals": [
            {"type": "subtotal", "amount": 1000},
            {"type": "items_discount", "display_text": "Club member benefit", "amount": -150},
            {"type": "total", "amount": 850}
          ]
        }
      ],
      "discounts": {
        "applied": [
          {
            "title": "Club Members get 15% Bonus",
            "amount": 150,
            "method": "each",
            "provisional": false,
            "eligibility": "com.example.retail_club",
            "allocations": [
              {"path": "$.line_items[0]", "amount": 150}
            ]
          },
          {
            "title": "Free shipping for Retail Card holder",
            "amount": 199,
            "automatic": true,
            "provisional": false,
            "eligibility": "com.example.retail_card"
          }
        ]
      },
      "loyalty": {
        "com.example.retail_club": {
          "id": "membership_1",
          "display_id": "****5678",
          "name": "Retail Club",
          "provisional": false,
          "tiers": [
            {
              "id": "gold",
              "name": "Gold Member",
              "benefits": [
                { "id": "BEN_001", "description": "Early access to sales" }
              ]
            }
          ]
        },
        "com.example.retail_card": {
          "id": "membership_2",
          "display_id": "****1234",
          "name": "Retail Card",
          "provisional": false,
          "tiers": [
            {
              "id": "cardholder",
              "name": "Retail Card",
              "benefits": [
                { "id": "BEN_002", "description": "Exclusive customer support" }
              ]
            }
          ]
        }
      },
      "totals": [
        {"type": "subtotal", "display_text": "Subtotal", "amount": 1000},
        {"type": "items_discount", "display_text": "Club member benefit", "amount": -150},
        {"type": "discount", "display_text": "Free shipping for Retail Card holder", "amount": -199},
        {"type": "fulfillment", "display_text": "Shipping", "amount": 199},
        {"type": "total", "display_text": "Estimated Total", "amount": 850}
      ]
    }
    ```

### Reward Earnings Forecast

In addition to immediate-value benefits like member pricing/shipping, delayed-value
collectable reward benefits are another crucial element within the loyalty ecosystem.
Displaying earnings forecasts of these rewards before the buyer commits complements and
to some extent helps agents handle price objections: rewards earning becomes additional
value on top of any pricing discount. In this example, businesses provide the reward
earning forecast with a breakdown, using `benefit_id` to correlate the specific
`membership_tier_benefit` that produced the rule and giving platforms a way to explain
with full transparency into why the buyer is earning rewards and how the earning is
calculated.

=== "Request"

    <!-- ucp:example schema=shopping/cart op=create direction=request -->
    ```json
    {
      "context": {
        "eligibility": ["com.example.retail_club"]
      },
      "line_items": [
        {
          "item": {
            "id": "prod_1"
          },
          "quantity": 1
        }
      ]
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/loyalty def=loyalty extract=$.loyalty -->
    ```json
    {
      "line_items": [
        {
          "id": "li_1",
          "item": {
            "id": "prod_1",
            "title": "T-Shirt",
            "price": 1000
          },
          "quantity": 1,
          "totals": [
            {"type": "subtotal", "amount": 1000},
            {"type": "total", "amount": 1000}
          ]
        }
      ],
      "loyalty": {
        "com.example.retail_club": {
          "id": "membership_1",
          "display_id": "****5678",
          "name": "Retail Club",
          "provisional": false,
          "tiers": [
            {
              "id": "gold",
              "name": "Gold",
              "benefits": [
                { "id": "BEN_001", "description": "1 point per $1 on everything" },
                { "id": "BEN_002", "description": "2 extra point/dollar on footwear" }
              ]
            }
          ],
          "rewards": [
            {
              "currency": {
                "name": "LoyaltyStars",
                "code": "LST"
              },
              "earning_forecast": {
                "amount": 30,
                "breakdown": [
                  {
                    "id": "RULE_1",
                    "description": "1 point/dollar on everything",
                    "amount": 10,
                    "benefit_id": "BEN_001"
                  },
                  {
                    "id": "RULE_2",
                    "description": "2 extra point/dollar on footwear",
                    "amount": 20,
                    "benefit_id": "BEN_002"
                  }
                ]
              }
            }
          ]
        }
      },
      "totals": [
        {"type": "subtotal", "display_text": "Subtotal", "amount": 1000},
        {"type": "total", "display_text": "Estimated Total", "amount": 1000}
      ]
    }
    ```

## Implementation guidelines

* Loyalty extension response MUST be data-minimized and MUST NOT expose raw stable member
  identifiers (as this would allow the platform to uniquely identify individual buyers).
* Loyalty extension response MUST only include `display_id` after verified/authenticated
  memberships.
* Loyalty extension response MUST treat all `context.eligibility` values in the request as
  buyer claims rather than proof.
