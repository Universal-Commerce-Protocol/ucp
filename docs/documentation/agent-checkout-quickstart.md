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

# Agent Checkout Quickstart

This guide shows a minimal end-to-end flow for an agent or assistant that can
checkout across UCP-compatible merchants. It focuses on the happy path and
points to the detailed specs for each step.

## When to use this

Use this flow when your agent needs to:

*   Discover whether a merchant supports checkout.
*   Create and update a checkout session.
*   Complete checkout and retrieve the final order state.

## Flow overview

1.  **Discover capabilities**
    *   Fetch the merchant profile and confirm support for the Checkout
        capability.
    *   See: [Checkout Capability](../specification/checkout.md).
2.  **Create a checkout session**
    *   Submit the cart or item list, buyer context, and any required fields.
    *   See: [HTTP/REST Binding](../specification/checkout-rest.md).
3.  **Update and confirm**
    *   Apply shipping, taxes, discounts, and buyer consent as needed.
    *   See: [Buyer Consent Extension](../specification/buyer-consent.md).
4.  **Complete checkout**
    *   Finalize payment and receive the order response.
    *   See: [Order Capability](../specification/order.md).

## Minimal checklist

*   Merchant discovery confirms `dev.ucp.shopping.checkout` capability.
*   Your agent handles required fields for shipping, billing, and consent.
*   Your agent supports at least one payment handler flow.

## Example resources

*   **UCP Samples** (end-to-end flows):
    <https://github.com/Universal-Commerce-Protocol/samples>
*   **UCP Python SDK** (client helpers):
    <https://github.com/Universal-Commerce-Protocol/python-sdk>

## Next steps

*   Add cart and basket building for multi-item checkouts.
*   Add loyalty and member benefits.
*   Add post-order management for tracking, returns, and changes.
