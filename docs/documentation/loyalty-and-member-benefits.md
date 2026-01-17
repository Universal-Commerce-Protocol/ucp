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

# Loyalty and Member Benefits

This page outlines how an agent can discover and apply loyalty or member
benefits during checkout. It is a placeholder for future capability extensions
and examples.

## Goals

*   Discover whether a merchant supports loyalty or member pricing.
*   Link a user account or membership.
*   Apply eligible benefits to a checkout session.

## Suggested flow

1.  **Discover capabilities** in the merchant profile.
2.  **Link account** or verify membership (identity linking).
3.  **Apply benefits** to the checkout session.
4.  **Confirm pricing** and complete checkout.

## Extension points

*   Member pricing and tiered discounts.
*   Points accrual and redemption.
*   Benefit eligibility checks.

## Related specs

*   [Identity Linking Capability](../specification/identity-linking.md)
*   [Checkout Capability](../specification/checkout.md)
