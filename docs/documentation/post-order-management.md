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

# Post-Order Management

This page outlines how agents should manage the lifecycle after checkout. It is
an outline for future documentation and examples.

## Goals

*   Retrieve order details and status updates.
*   Surface shipping and delivery updates to the user.
*   Support cancellations, returns, and exchanges where available.

## Suggested flow

1.  **Fetch order** after checkout completion.
2.  **Poll or receive updates** for shipment and delivery.
3.  **Initiate changes** such as cancel, return, or exchange.
4.  **Confirm final status** and notify the user.

## Extension points

*   Partial returns and refunds.
*   Exchanges and replacements.
*   Post-order upsell or cross-sell offers.

## Related specs

*   [Order Capability](../specification/order.md)
