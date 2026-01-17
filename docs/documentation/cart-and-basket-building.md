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

# Cart and Basket Building

This page outlines how agents should build multi-item carts and baskets for
UCP-compatible merchants. It provides a structure for docs and examples that
will evolve alongside the Checkout capability.

## Goals

*   Support multi-item checkout sessions.
*   Respect merchant-specific basket rules and validation.
*   Handle promotions, taxes, and shipping requirements.

## Core concepts

*   **Cart vs. checkout session:** A cart is user intent; a checkout session is
    the merchant-authoritative state used to complete payment.
*   **Basket rules:** Constraints such as quantity limits, item exclusivity, or
    shipping restrictions.
*   **Price calculation:** Taxes, discounts, shipping, and fees are resolved by
    the merchant.

## Suggested flow

1.  **Create session** with initial items.
2.  **Update session** as the user adds or removes items.
3.  **Validate session** and surface merchant validation errors to the user.
4.  **Confirm totals** and proceed to checkout completion.

## Extension points

*   Discounts and promotions (see [Discounts Extension](../specification/discount.md)).
*   Fulfillment options (see [Fulfillment Extension](../specification/fulfillment.md)).
*   Buyer consent requirements (see [Buyer Consent Extension](../specification/buyer-consent.md)).

## Example payloads

Add example request and response payloads here once a cart schema is finalized.

## Related specs

*   [Checkout Capability](../specification/checkout.md)
*   [HTTP/REST Binding](../specification/checkout-rest.md)
