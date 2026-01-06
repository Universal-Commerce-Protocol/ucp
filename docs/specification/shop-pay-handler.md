<!--
   Copyright 2025 Google LLC

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

# Shop Pay Payment Handler Specification

**Handler Name:** `com.shopify.shop_pay`
**Version:** `2026-01-11`

## 1. Introduction

The `com.shopify.shop_pay` handler enables merchants to offer Shop Pay as an
accelerated checkout option through UCP-compatible agents. Shop Pay is
Shopify's native payment solution that provides a streamlined checkout
experience by securely storing buyer payment and shipping information.

This handler enables a **delegated payment flow** where agents can securely
generate a Shop Token for a buyer's selected payment instrument in Shop Pay.
Merchants can then process these tokens, and agents can leverage the same
Shop Pay integration across all participating merchants.

### 1.1 Key Benefits

- **Accelerated Checkout:** Buyers with Shop Pay accounts can complete
  purchases faster using their saved payment and shipping details.
- **Delegated Payments:** Agents can orchestrate Shop Pay payments without
  directly handling sensitive payment credentials.
- **Standardized Integration:** A single Shop Pay integration works across
  all UCP-compatible merchants.

## 2. Merchant Integration

### 2.1 Requirements

Before advertising Shop Pay through UCP, merchants must:

1. **Register for Shop Pay:** Obtain your `shop_id` by registering your shop
   for Shop Pay.

!!! note "Shopify Merchants"
    If you are a Shopify merchant, Shopify automatically advertises all UCP
    payment handlers on your behalf, including Shop Pay. No additional
    configuration is required.

### 2.2 Handler Configuration

Merchants advertise Shop Pay support by including the handler in their
payment handlers array. The handler uses a minimal configuration containing
only the merchant's Shop Pay identifier today.

#### 2.2.1 Configuration Schema

| Field     | Type   | Required | Description                                                                           |
| :-------- | :----- | :------- | :------------------------------------------------------------------------------------ |
| `shop_id` | String | Yes      | The merchant's unique Shop Pay identifier.                                            |

#### 2.2.2 Example Handler Declaration

```json
{
  "payment": {
    "handlers": [
      {
        "id": "shop_pay",
        "name": "com.shopify.shop_pay",
        "version": "2026-01-11",
        "spec": "https://shopify.dev/ucp/handlers/shop_pay",
        "config_schema": "https://shopify.dev/ucp/handlers/shop_pay/config.json",
        "instrument_schemas": [
          "https://shopify.dev/ucp/handlers/shop_pay/instrument.json"
        ],
        "config": {
          "shop_id": "shopify-559128571"
        }
      }
    ]
  }
}
```

### 2.3 Payment Instrument Support

By advertising the Shop Pay handler, merchants indicate they can accept and
process Shop Pay payment instruments. Merchants MUST be able to handle payment
objects conforming to the Shop Pay instrument schema.

#### 2.3.1 Instrument Schema

Shop Pay instruments extend the base UCP payment instrument with
Shop Pay-specific fields and credential types.

| Field             | Type   | Required | Description                                                    |
| :---------------- | :----- | :------- | :------------------------------------------------------------- |
| `id`              | String | Yes      | Unique identifier for this payment instrument.                 |
| `handler_id`      | String | Yes      | Must match the handler's `id` (e.g., `shop_pay`).              |
| `type`            | String | Yes      | Must be `shop_pay`.                                            |
| `credential`      | Object | Yes      | The Shop Pay credential containing the token.                  |
| `credential.type` | String | Yes      | Must be `shop_token`.                                          |
| `credential.token`| String | Yes      | The Shop Token from the delegated payment flow.                |
| `billing_address` | Object | Yes      | Billing address associated with the Shop Pay account.          |
| `email`           | String | No       | The buyer's email address associated with the Shop Pay account.|

#### 2.3.2 Example Payment Object

Merchants will receive a payment object structured as follows when an agent
submits a Shop Pay payment:

```json
{
  "payment": {
    "instruments": [
      {
        "id": "instr_shop_pay_1",
        "handler_id": "shop_pay",
        "type": "shop_pay",
        "credential": {
          "type": "shop_token",
          "token": "shop_abc123xyz789..."
        },
        "email": "buyer@example.com",
        "billing_address": {
          "full_name": "Jane Doe",
          "street_address": "123 Main St",
          "address_locality": "San Francisco",
          "address_region": "CA",
          "postal_code": "94102",
          "address_country": "US"
        }
      }
    ],
    "selected_instrument_id": "instr_shop_pay_1"
  }
}
```

## 3. Agent Integration

### 3.1 Requirements

Before handling delegated Shop Pay payments, agents must:

1. **Register with Shop Pay:** Obtain a `client_id` that supports delegated
   experiences by registering your agent application with Shop Pay.

### 3.2 Delegated Payment Protocol

Agents MUST follow this flow to process a `com.shopify.shop_pay` handler:

#### Step 1: Discover Handler

Agent identifies `com.shopify.shop_pay` in the merchant's payment handlers
array from the checkout response or merchant profile.

```json
{
    "id": "shop_pay",
    "name": "com.shopify.shop_pay",
    "version": "2026-01-11",
    "spec": "https://shopify.dev/ucp/handlers/shop_pay",
    "config_schema": "https://shopify.dev/ucp/handlers/shop_pay/config.json",
    "instrument_schemas": [
        "https://shopify.dev/ucp/handlers/shop_pay/instrument.json"
    ],
    "config": {
        "shop_id": "shopify-559128571"
    }
}
```

#### Step 2: Configure Delegated Payment Request

Agent configures the Shop Pay SDK with the merchant's `shop_id` and the
agent's own `client_id`:

```javascript
ShopPay.PaymentRequest.configure({
  delegatedShopId: "shopify-559128571",
  clientId: "agent-7438291"
});
```

#### Step 3: Build Payment Request

Agent builds the payment request using standardized UCP checkout data
including totals, fulfillment options, and line items:

```javascript
ShopPay.PaymentRequest.build({
  totals: [
    { type: "subtotal", display_text: "Subtotal", amount: 5000 },
    { type: "shipping", display_text: "Shipping", amount: 500 },
    { type: "tax", display_text: "Tax", amount: 524 },
    { type: "total", display_text: "Total", amount: 6024 }
  ],
  currency: "usd",
  locale: "en"
});
```

#### Step 4: Complete Checkout

Upon buyer confirmation, Shop Pay returns a Shop Token. The agent wraps this
token in a UCP payment instrument conforming to the Shop Pay instrument schema
(see Section 2.3.1) and submits the complete checkout request to the merchant:

```json
POST /checkout-sessions/{checkout_id}/complete
Content-Type: application/json
UCP-Agent: profile="https://agent.example/profile"

{
  "payment_data": {
    "id": "instr_shop_pay_1",
    "handler_id": "shop_pay",
    "type": "shop_pay",
    "credential": {
      "type": "shop_token",
      "token": "shop_abc123xyz789..."
    },
    "email": "buyer@example.com",
    "billing_address": {
      "full_name": "Jane Doe",
      "street_address": "123 Main St",
      "address_locality": "San Francisco",
      "address_region": "CA",
      "postal_code": "94102",
      "address_country": "US"
    }
  }
}
```

Upon successful processing, the merchant returns the completed checkout state
with an `order_id` confirming the purchase.

## 4. Merchant Processing

Upon receiving a `shop_pay` payment instrument, merchants MUST:

1. **Validate Handler:** Confirm `handler_id` matches a configured Shop Pay
   handler.

2. **Extract Token:** Retrieve the `token` from `credential.token`.

3. **Process Payment:** Use the Shop Token to complete the payment through
   Shop Pay's payment processing API.

4. **Return Response:** Respond with the finalized checkout state including
   order confirmation details.

## 5. Security Considerations

### 5.1 Token Security

- **Single-Use Tokens:** Shop Tokens are designed to be single-use and CANNOT
  be reused across transactions.
- **Time-Limited:** Tokens have a limited validity period and should be used
  promptly after generation.
- **Checkout-Scoped:** Tokens have context about the checkout and merchant,
  preventing usage outside of the verified checkout.
- **Secure Transmission:** All token exchanges MUST occur over TLS 1.2+.

### 5.2 Agent Authorization

- Agents MUST register with Shop Pay to obtain a valid `client_id` before
  processing delegated payments.
- The `client_id` identifies the agent to Shop Pay and enables proper
  authorization tracking.

## 6. References

- **Handler Config Schema:**
  `https://shopify.dev/ucp/handlers/shop_pay/config.json`
- **Instrument Schema:**
  `https://shopify.dev/ucp/handlers/shop_pay/instrument.json`
- **Credential Schema:**
  `https://shopify.dev/ucp/handlers/shop_pay/credential.json`
