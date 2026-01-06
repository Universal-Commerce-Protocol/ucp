<!--  Copyright 2025 Google LLC

 Licensed under the Apache License, Version 2.0 (the "License");  you may not
use this file except in compliance with the License.  You may obtain a copy of
the License at

 http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,  WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
License for the specific language governing permissions and  limitations under
the License.
-->

# (WIP) Google guidelines for UCP implementation

Note: this will be migrated to a google.com site.

[TOC]

## Native Integrations

Merchants must provide this data via the Product Feed/Merchant API, or
dynamically through the Checkout API (in line with the Spec) to ensure legal
compliance and a trustworthy user experience.

### Agentic Checkout Eligibility

*   **Requirement**: Must be provided via a feed attribute:
    *   Single `native_commerce` attribute group containing a single
        `checkout_eligibility` boolean sub-attribute.
*   **Details**:
    *   [Recommended] Provide attributes incrementally via a supplemental data
        source:
        *   Via a supplemental feed file: File should include at least 2 columns
            (`id` and `native_commerce`).
        *   Via CustomAttributes in Content API/Merchant API.
        [TODO: Add API instructions]
    *   Can also provide attributes directly in primary data source, but proceed
        with caution as this may impact regular product ingestions if attribute
        is not set correctly.
*   **Purpose**: Agentic checkout eligibility will be gated by this attribute,
    which will relate to whether or not the “Buy” button will render on Google
    surfaces.

### Product Warnings

*   **Requirement**: Product Warnings must be provided via a feed attribute
    (e.g., Prop 65 warning).
    *   `consumer_notice` is an attribute group containing 2 sub-attributes:
        *   `consumer_notice_type`: string with one of the following values:
            `legal_disclaimer`, `safety_warning`, `prop_65`.
        *   `consumer_notice_message`: string with length <= 1000 characters
            (`b`, `br`, and `i` are accepted tags within the string).
*   **Details**:
    *   Additional Warnings to be provided via Checkout API (messages).
    *   Similar to Checkout Eligibility above, but adding an extra attribute.
*   **Purpose**: Displayed in the Checkout screen.

### Additional Fees

*   **Requirement**: Merchants must explicitly itemize and return any mandatory
    fees (e.g., eWaste fee, handling fee).
*   **Details**: Must be provided via a feed attribute:
    *   `product_fee` is an attribute group containing 2 sub-attributes:
        *   `product_fee_type`: string holding an accepted list (see appendix
            for the full list).
        *   `product_fee_amount`: price struct (see here for an example) that
            includes both actual amount and currency unit.
    *   Similar to Checkout Eligibility above, but adding an extra attribute.
*   **Purpose**: Displayed clearly in the Order Summary breakdown.

#### Example Supplemental Feed

You can see below an example Supplemental feed to cover the `native_commerce`,
`consumer_notice` and `product_fee` fields:

| ID | native_commerce | consumer_notice | product_fee |
|---|---|---|---|
| 11111 | TRUE | `prop_65:This product can expose you to chemicals including [name of one or more chemicals] which is [are] known to the State of California to cause cancer and birth defects or other reproductive harm` | `US_AZ_TIRE_FEE:2.75 USD` |
| 22222 | TRUE | | |

### Product Identifier

*   **Requirement**: The existing `id` feed attribute should be identical to the
    identifiers expected by the Checkout API.
*   **Details**: If above assumption does not hold, then the identifier used by
    Checkout API must be provided via a feed custom attribute:
    `merchant_item_id: string with length <= 255 characters`.
    *   Similar to Checkout Eligibility above, but add an extra attribute.
*   **Purpose**: Communicating products involved in the transaction between
    Google & merchants.

### Return Policy

TODO: disclaimer on this affecting the whole account

*   **Requirement**: Provided by merchant to Google Merchant Center.
*   **Details**: Include : Return cost, speed and policy link.
    *   Refer to https://support.google.com/merchants/answer/14011730 for
        detailed instructions.
*   **Purpose**: Referenced on the Checkout screen (Merchant of Record
    requirement).

### Merchant or Seller-level Contact Info

*   **Requirement**: Must be available in the Merchant Center (via Business Info
    tab).
*   **Details**: Refer to https://support.google.com/merchants/answer/13661344
    for detailed instructions.
*   **Purpose**: Used for the "Contact Merchant" link on the Order Confirmation
    screen.

## Required UCP implementation

### Identity Linking

*   The authorization endpoint MUST support `response_type=code`.
*   The token endpoint MUST support `grant_type=authorization_code` and
    `grant_type=refresh_token`.
*   MUST use the OAuth 2.0 Authorization Code flow
    ([RFC 6749 4.1](https://datatracker.ietf.org/doc/html/rfc6749#section-4.1)).
*   Scopes:
    *   SHOULD support requested UCP scopes as a single bundled consent screen;
        users must not be forced to individually select highly granular
        technical scopes during the linking process
    *   MAY give users the option to reject scopes in their platform (Google
        does not offer this capability)
    *   MUST allow future permission elevation.
    *   Merchant MAY choose how to present the consent, but the resulting
        authorization MUST cover the scopes defined below

### Checkout object

*   MUST provide applicable product warnings through the feed (field
    'customer_notice'), and MUST NOT provide them via the Checkout messages

### Order Status

TODO: add clear actions on what to implement here

*   You MUST send the following event updates post order creation:
    *   Order shipped with required fulfillment details as specified in the
        section below.
    *   Order delivered.
    *   Any item/order cancellations.
    *   Any item/order returns.

## Embedded Checkout

TODO