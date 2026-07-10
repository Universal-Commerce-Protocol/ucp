# Loyalty Extension

## Overview

The loyalty extension is designed to facilitate high-fidelity loyalty experiences: ensuring existing loyalty members can seamlessly access their benefits during agentic Catalog, Cart, and Checkout experiences. By enabling buyers to see their specific tier, eligible rewards, and immediately applicable benefits before finalizing a purchase, it addresses a foundational expectation for program members and removes friction from the checkout funnel.

Specifically the following core use cases of benefit recognition for known members are addressed:

- Price-Impacting Benefits: Real-time application of member-only discounts and free shipping offers with clear attribution of benefit sources.
- Non-Price Benefits: Transparent display of rewards earned or rewards applicable to future purchases.
- Status Recognition: Verification and display of the buyers’ specific loyalty tier within a program.

## Key Concepts

Loyalty has four main components:

**Memberships**: Distinct enrollment pathways or program categories that a user can join

- Independent programs offered by the same brand (e.g., a "Rewards Club" vs. a "Co-branded Credit Card") are modeled as separate, independently verifiable memberships. They are programmatically represented as separate sibling top-level keys in the loyalty extension map, namespaced by reverse-domain naming.

**Tiers**: Specific achievement ranks or status milestones within a membership that unlock escalating value as a member progresses through activity or spend

- A member typically holds a single active tier per membership. For programs with parallel status dimensions (e.g., holding both "Gold" and "Lifetime Platinum"), multiple tiers can be active concurrently.

**Benefits**: Ongoing perks and privileges granted to a customer based on their current tier or membership status

- Contains both delayed (e.g. “Members have access to dedicated customer service”) and immediate-value (e.g. “Members get 5% off”) benefits.

**Rewards**: Quantifiable loyalty value that may be earned from the current transaction. Note: Redeemable balances and stored value are modeled by the negotiated payment instrument or a future redemption capability, not by this loyalty extension.

- One membership can offer multiple types of accumulable/collectable rewards, each having its own usage and redemption rules.

```json
{
  "loyalty": {
    "com.example.loyalty": {
      "id": "membership_1",
      "name": "Example Rewards",
      "tiers": [
        {
          "id": "gold",
          "name": "Gold",
          "benefits": [
            { "id": "BEN_001", "description": "Early access to sales" }
          ]
        }
      ],
      "rewards": [
        {
          "currency": { "name": "LoyaltyStars", "code": "LST" }
        }
      ],
      "provisional": false
    }
  }
}
```

## Discovery

Businesses can follow the standard advertising mechanism to advertise loyalty support in the Business profile. Currently the loyalty extension can decorate catalog search, catalog lookup, cart, and checkout capabilities. Businesses MAY advertise loyalty support for any subset of these capabilities. Platforms SHOULD check which resources are extended.

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/catalog/search",
          "schema": "https://ucp.dev/draft/schemas/shopping/catalog_search.json"
        }
      ],
      "dev.ucp.shopping.catalog.lookup": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/catalog/lookup",
          "schema": "https://ucp.dev/draft/schemas/shopping/catalog_lookup.json"
        }
      ],
      "dev.ucp.shopping.cart": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/cart",
          "schema": "https://ucp.dev/draft/schemas/shopping/cart.json"
        }
      ],
      "dev.ucp.shopping.checkout": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/checkout",
          "schema": "https://ucp.dev/draft/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.common.loyalty": [
        {
          "version": "draft",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup",
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout"
          ],
          "spec": "https://ucp.dev/draft/specification/loyalty",
          "schema": "https://ucp.dev/draft/schemas/common/loyalty.json"
        }
      ]
    }
  }
}
```

**Dependencies:**

- Catalog Search Capability
- Catalog Lookup Capability
- Cart Capability
- Checkout Capability

## Schema

### Entities

#### Loyalty

Key-value map whose keys represent buyer/platform asserted eligibility claims and whose values represent associated membership information. All loyalty keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.

#### Loyalty Membership

Loyalty membership the business has accepted for the eligibility claim represented by the parent map key. Programs that can be joined independently MUST be modeled as separate sibling entries under the loyalty map, distinguished by reverse-domain naming (e.g., 'com.example.rewards' and 'com.example.rewards.card').

| Name        | Type          | Required | Description                                                                                                                                                                                                                                                     |
| ----------- | ------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string        | **Yes**  | Unique loyalty membership identifier.                                                                                                                                                                                                                           |
| name        | string        | **Yes**  | Business specific name of the loyalty membership/program.                                                                                                                                                                                                       |
| display_id  | string        | No       | A masked or partial version of the membership id for user recognition (e.g., '\*\*\*\*5678'). MUST NOT be set if the membership has not been verified.                                                                                                          |
| tiers       | Array[object] | No       | Active or display-safe tier context for this membership. Most programs are single-status (one entry); programs with parallel status dimensions (e.g., current and lifetime) populate one entry per active tier. Omitted when no tier context has been resolved. |
| rewards     | Array[object] | No       | Reward types and earning forecasts associated with this membership. Each object encapsulates one type of reward.                                                                                                                                                |
| provisional | boolean       | **Yes**  | True if this membership requires additional verification.                                                                                                                                                                                                       |

#### Membership Tier

Specific achievement rank or status milestone that unlocks escalating value as a member progresses through activity or spend.

| Name     | Type          | Required | Description                                             |
| -------- | ------------- | -------- | ------------------------------------------------------- |
| id       | string        | **Yes**  | Unique identifier for the membership tier.              |
| name     | string        | **Yes**  | The human-readable name of the tier (e.g., 'Platinum'). |
| benefits | Array[object] | No       | List of benefits associated with this tier.             |

#### Membership Tier Benefit

Benefits associated with a membership tier.

| Name        | Type   | Required | Description                                                                                 |
| ----------- | ------ | -------- | ------------------------------------------------------------------------------------------- |
| id          | string | **Yes**  | Unique identifier for the tier benefit.                                                     |
| description | string | **Yes**  | A display-ready, human-readable explanation of this benefit (e.g. 'Early access to sales'). |

#### Membership Reward

Quantifiable reward type and optional earning forecast for the current transaction.

| Name             | Type   | Required | Description                                                                          |
| ---------------- | ------ | -------- | ------------------------------------------------------------------------------------ |
| currency         | object | **Yes**  | A unit of value that customers can accumulate through various commercial activities. |
| earning_forecast | object | No       | Preview of rewards to be earned from the current transaction.                        |

#### Reward Amount

Non-negative integer amount denominated in the minor unit of the associated reward currency. The associated reward currency's `decimal_places` defines the minor-to-major ratio and defaults to 0 when omitted.

#### Reward Currency

The currency of the loyalty reward.

| Name           | Type    | Required | Description                                                                                                |
| -------------- | ------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| name           | string  | **Yes**  | Human-readable name of the currency (e.g. 'LoyaltyStars').                                                 |
| code           | string  | **Yes**  | Business-specific representation of the currency (e.g. 'LST').                                             |
| decimal_places | integer | No       | The position of a digit to the right of a decimal point. Applies to all amount related fields for rewards. |

#### Earning Forecast

Preview of rewards to be earned from the current transaction.

| Name      | Type          | Required | Description                                              |
| --------- | ------------- | -------- | -------------------------------------------------------- |
| amount    | integer       | **Yes**  | Total rewards to be earned if the transaction completes. |
| breakdown | Array[object] | No       | List of breakdown of earning contributing to the total.  |

#### Earning Breakdown

Breakdown rule of the reward earnings

| Name        | Type    | Required | Description                                                                                                                                                            |
| ----------- | ------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string  | **Yes**  | Unique rewards breakdown rule identifier.                                                                                                                              |
| amount      | integer | **Yes**  | Rewards earned from this rule.                                                                                                                                         |
| description | string  | **Yes**  | A display-ready, human-readable rationale for the specific rewards (e.g. 2x on footwear).                                                                              |
| benefit_id  | string  | No       | Optional `id` of the membership_tier_benefit that produced this rewards rule. Resolves against `membership_tier_benefit.id` within the same parent loyalty membership. |

## Loyalty behavior

The loyalty extension holds a key-value map whose keys are reverse-domain identifiers — the same convention as services, capabilities, and payment handlers in the business profile. The keys represent eligibility claims about loyalty memberships that businesses recognize. The values contain membership information corresponding to those claims and use the required `provisional` field to indicate the verification state.

Programs that can be joined independently MUST be modeled as separate sibling entries under the loyalty map, distinguished by their reverse-domain naming.

Platforms MAY send buyer loyalty membership claims via `context.eligibility` in the request to activate the loyalty extension and claim loyalty benefits. Alternatively, when the buyer is authenticated and the business can determine loyalty membership from the authenticated identity, businesses MAY populate the loyalty extension without an explicit eligibility claim. In this case, the map key MUST be the same reverse-domain identifier the business would accept as a claim value.

- When a business verifies a membership claim or determines membership from authenticated identity, it MUST return `provisional: false`. It MUST populate the active tier(s) the buyer holds within the `tiers` array **when the program has tier structure** — for programs with no tier concept (flat-rate cashback, single-status memberships), businesses MAY omit `tiers`. It also SHOULD set `display_id` as a masked unique identifier for the buyer.
- When a membership claim in the request is recognized and accepted but not verified by the business, the business MUST return `provisional: true`. It MAY return display-safe tier context for the state accepted during the session, and MUST NOT return `display_id` until the membership is verified.
- When a membership claim in the request is accepted but cannot be verified, the business MUST communicate the failure via a recoverable `message` with `type: "error"` and `code: "eligibility_invalid"`. Platforms MAY then choose to remove the membership claim and proceed through checkout without loyalty benefits applied.

At checkout completion, all accepted but unverified loyalty claims MUST be resolved per the [Eligibility Verification at Completion](http://ucp.dev/draft/specification/checkout/#eligibility-verification-at-completion) contract defined in the checkout capability.

### Monetary loyalty benefits

Monetary price-impacting loyalty benefits (e.g. member pricing/shipping) can have conditions beyond membership, such as saving $10 only after a $500+ purchase. Businesses MUST evaluate those conditions before applying the benefit.

When the benefit applies, businesses MUST surface the price impact through the base capability's price fields. Catalog responses use `price` / `list_price` and `price_range` / `list_price_range`; cart and checkout responses use `totals` or `line_items[].totals` with `type: "items_discount"` (for member pricing) / `type: "discount"` (for member shipping) and `display_text` to attribute the loyalty source when possible.

For cart and checkout responses, when the discount extension is active, businesses SHOULD also populate `discounts.applied[]` for structured attribution. In that case, `eligibility` identifies the claim required for the discount. If the discount still requires verification, for example because one or more accepted loyalty claims remain unverified, the corresponding applied discount MUST set `provisional: true`.

If the benefit does not apply, businesses SHOULD notify the buyer via messages with `type: "warning"` and explain the inapplicability of those monetary loyalty benefits. Businesses MUST NOT put inapplicable benefits in the discount extension. Instead they MAY set them as part of `benefits` within the loyalty extension and set the warning message `path` to reference the relevant membership for additional context.

When loyalty membership claims are accepted, businesses MAY use `type: "info"` to explain the effects of applied monetary loyalty benefits.

**Loyalty benefits message codes:**

| Type      | Code                            | When                                                 |
| --------- | ------------------------------- | ---------------------------------------------------- |
| `info`    | `membership_benefit_eligible`   | Specific benefit confirmed applicable to this order  |
| `warning` | `membership_benefit_ineligible` | Benefit exists but conditions not met for this order |

The examples below are abbreviated to focus on loyalty and discount extension fields; complete cart and checkout responses also include base required fields such as `ucp`, `id`, `currency`, and `totals`.

Building on the store loyalty card example from [Eligibility Verification at Completion](http://ucp.dev/draft/specification/checkout/#eligibility-verification-at-completion), assume the card offers one unconditional product discount and one conditional discount that the current checkout cart fails to satisfy. The platform can surface the first provisional discount with disclaimers like "verified at purchase" and additionally show a warning message to disclose the inapplicability of the second discount.

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

The buyer can proceed to checkout without any cart update. If the claim is verified successfully by the business, the unconditional member-pricing discount becomes non-provisional and `display_id` is returned.

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

If the claim cannot be verified, the business MUST return a recoverable error via `messages[]` with `code: "eligibility_invalid"`.

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

With the help of the loyalty extension, the catalog, cart, and checkout capabilities can be further decorated to provide full visibility into buyers’ member-exclusive perks and allow the platform to render the extra information to facilitate the transaction.

### Price-Impacting Benefits

The loyalty extension can provide buyer status information that helps the platform explain member discounts. Price-impacting loyalty benefits are reflected in the base capability's price fields. When the discount extension is also active, the platform can explain each discount via `discounts.applied[].title` and correlate `discounts.applied[].eligibility` back to `loyalty` entries to show which accepted membership claims produced the monetary benefit. In the example below, the buyer receives a 15% bonus discount and free shipping benefit respectively because they hold the Retail Club membership and the Retail Card. The platform can then render “Retail Club Gold Member and Retail Card benefits applied,” for example.

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
    {"type": "fulfillment", "display_text": "Shipping", "amount": 0},
    {"type": "total", "display_text": "Estimated Total", "amount": 651}
  ]
}
```

### Reward Earnings Forecast

In addition to immediate-value benefits like member pricing/shipping, delayed-value collectable reward benefits are another crucial element within the loyalty ecosystem. Displaying earnings forecasts of these rewards before the buyer commits complements and to some extent helps agents handle price objections: rewards earning becomes additional value on top of any pricing discount. In this example, businesses provide the reward earning forecast with a breakdown, using `benefit_id` to correlate the specific `membership_tier_benefit` that produced the rule and giving platforms a way to explain with full transparency into why the buyer is earning rewards and how the earning is calculated.

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

- Loyalty extension response MUST be data-minimized and MUST NOT expose raw stable member identifiers (as this would allow the platform to uniquely identify individual buyers).
- Loyalty extension response MUST only include `display_id` after verified/authenticated memberships.
- Loyalty extension response MUST treat all `context.eligibility` values in the request as buyer claims rather than proof.
