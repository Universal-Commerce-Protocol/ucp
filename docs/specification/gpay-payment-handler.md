<!--
   Copyright 2025 UCP Authors

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

# Google Pay Payment Handler Specification

* **Handler Name:** `com.google.pay`
* **Version:** `2026-01-11`

## 1. Introduction

The `com.google.pay` handler enables merchants to offer Google Pay as an
accelerated checkout option through UCP-compatible agents. The Google Pay API
enables fast, easy checkout by giving users access to payment methods stored in
their Google Account.

This handler enables a **headless integration model** where merchants provide
their Google Pay configuration (such as allowed card networks and gateway
parameters), and agents handle the client-side interaction with the Google Pay
API to generate a secure payment token.

![High-level flow sequence diagram](site:specification/images/ucp-gpay-payment-flow.png)

### 1.1 Key Benefits

-   **Universal Configuration:** Merchants configure Google Pay once using
    standard JSON, allowing any authorized agent to render the payment interface
    without custom frontend code.
-   **Decoupled Frontend:** Agents handle the complexity of the Google Pay
    JavaScript API or native Android integration, while merchants consume
    the resulting token.
-   **Secure Tokenization:** Leverages Google’s native tokenization to pass
    encrypted credentials directly to the merchant's Payment Service Provider
    (PSP).

## 2. Merchant Integration

### 2.1 Requirements

Before advertising Google Pay through UCP, merchants must:

1.  **Obtain Google Pay Merchant ID:** Required for processing in the
    `PRODUCTION` environment (register in the
    [Google Pay & Wallet Console](https://pay.google.com/business/)).
2.  **Verify PSP Support:** Ensure your Payment Service Provider (PSP) supports
    Google Pay tokenization.

### 2.2 Handler Configuration

Merchants advertise Google Pay support by including the handler in their payment
handlers array. The configuration strictly follows the structure required to
initialize the
[Google Pay API](https://developers.google.com/pay/api/web/reference/request-objects).

#### 2.2.1 Configuration Schema

The configuration object defines the environment, merchant identity, and allowed
payment methods.

{{ schema_fields('gpay_config', 'gpay-payment-handler') }}

### Merchant Info

{{ schema_fields('merchant_info', 'gpay-payment-handler') }}

### Gpay Payment Method

Based on [Google Pay's payment_method](https://developers.google.com/pay/api/web/reference/request-objects#PaymentMethod).

{{ schema_fields('gpay_payment_method', 'gpay-payment-handler') }}

### Tokenization Specification

Based on [Google Pay's tokenization_specification](https://developers.google.com/pay/api/web/reference/request-objects#PaymentMethodTokenizationSpecification).

{{ schema_fields('tokenization_specification', 'gpay-payment-handler') }}

### Processing Specification

Based on [Google Pay's processing_specification](https://developers.google.com/pay/api/web/reference/request-objects#PaymentMethodProcessingSpecification).

{{ schema_fields('processing_specification', 'gpay-payment-handler') }}

#### 2.2.2 Example Handler Declaration

```json
{
  "payment": {
    "handlers": [
      {
        "id": "gpay",
        "name": "com.google.pay",
        "version": "2026-01-11",
        "spec": "https://ucp.dev/handlers/google_pay",
        "config_schema": "https://ucp.dev/handlers/google_pay/config.json",
        "instrument_schemas": [
          "https://ucp.dev/handlers/google_pay/card_instrument.json"
        ],
        "config": {
          "api_version": 2,
          "api_version_minor": 0,
          "environment": "TEST",
          "merchant_info": {
            "merchant_name": "Example Merchant",
            "merchant_id": "01234567890123456789",
            "merchant_origin": "checkout.merchant.com",
            "auth_jwt": "edxsdfoaisjdfapsodjf....", // optional
          },
          "allowed_payment_methods": [
            {
              "type": "CARD",
              "parameters": {
                "allowed_auth_methods": ["PAN_ONLY", "CRYPTOGRAM_3DS"],
                "allowed_card_networks": ["VISA", "MASTERCARD"]
              },
              "tokenization_specification": {
                "type": "PAYMENT_GATEWAY",
                "parameters": {
                  "gateway": "example",
                  "gatewayMerchantId": "exampleGatewayMerchantId"
                }
              }
            }
          ]
        }
      }
    ]
  }
}
```

Here is the corrected **Section 2.3** including the missing rich media fields.

***

## 2.3 Entities

### 2.3.1 Instrument Schema

The GPay instrument (`gpay_card_payment_instrument`) extends the base
**Card Payment Instrument**. It inherits standard display fields (like `brand`
and `last_digits`) to ensure consistent receipt rendering, while refining the
`credential` field to carry the specific Google Pay tokenization payload.

**Agent Behavior:** The agent is responsible for mapping from the [Google Pay `PaymentMethodData`](https://developers.google.com/pay/api/web/reference/response-objects#PaymentMethodData) response into this structure before sending it to the merchant.

| Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| id | string | **Yes** | A unique identifier for this payment instrument, assigned by the agent. |
| handler_id | string | **Yes** | **Constant = `gpay`**. Identifier for the Google Pay handler. |
| type | string | **Yes** | **Constant = `card`**. Indicates this instrument behaves like a card (inherits card display fields). |
| credential | [Credential Payload](#credential-payload) | **Yes** | The secure tokenization data returned by Google Pay. |
| brand | string | **Yes** | The card network (e.g., `visa`, `mastercard`). Mapped from Google Pay's `info.cardNetwork`. |
| last_digits | string | **Yes** | The last 4 digits of the card. Mapped from Google Pay's `info.cardDetails`. |
| expiry_month | integer | No | The expiration month. |
| expiry_year | integer | No | The expiration year. |
| rich_text_description | string | No | An optional rich text description of the card (e.g., "Visa ending in 1234, expires 12/2025"). |
| rich_card_art | string (uri) | No | An optional URI to a rich image representing the card (e.g., issuer card art). |
| billing_address | [Postal Address](#postal-address) | No | The billing address associated with the card. |

### Credential Payload

This object serves as the `credential` for the instrument. It maps directly to [Google Pay Tokenization Data](https://developers.google.com/pay/api/web/reference/response-objects#PaymentMethodTokenizationData).

{{ schema_fields('tokenization_data', 'gpay-payment-handler') }}

### Postal Address

{{ schema_fields('postal_address', 'gpay-payment-handler') }}

## 3. Agent Integration

### 3.1 Requirements

Before handling `com.google.pay` payments, agents must:
1.  Be capable of loading the **Google Pay API for Web** (or Android native
    equivalent).
2.  Adhere to the
    [Google Pay Brand Guidelines](https://developers.google.com/pay/api/web/guides/brand-guidelines)
    when rendering the payment button.

### 3.2 Payment Protocol

Agents MUST follow this flow to process the handler:

#### Step 1: Discover & Configure
The agent initializes the client to manage the API lifecycle.

*   **Reference:** [PaymentsClient](https://developers.google.com/pay/api/web/reference/client#PaymentsClient)

#### Step 2: Check Readiness to Pay
The agent checks if the user has the ability to make a payment with the
specified payment methods before displaying the button.

*   **Reference:** [isReadyToPay](https://developers.google.com/pay/api/web/reference/client#isReadyToPay)

#### Step 3: Build Payment Request
The agent assembles the payment data request object, including the merchant
configuration, payment methods, and transaction details (price and currency).

*   **Reference:** [PaymentDataRequest](https://developers.google.com/pay/api/web/reference/request-objects#PaymentDataRequest)

#### Step 4: Invoke User Interaction
The agent triggers the payment sheet display when the user interacts with the
payment button.

*   **Reference:** [loadPaymentData](https://developers.google.com/pay/api/web/reference/client#loadPaymentData)

#### Step 5: Complete Checkout
Upon successful user interaction, the Google Pay API returns a
`PaymentInstrument` object with the key as `payment_data`.
The agent maps this response to the `card_payment_instrument` schema
and submits the checkout completion request.

```json
POST /checkout-sessions/{checkout_id}/complete

{
  "payment_data": {
    "id": "pm_1234567890abc",
    "handler_id": "gpay",
    "type": "card",
    "brand": "visa",
    "last_digits": "4242",
    "billing_address": {
      "street_address": "123 Main Street",
      "extended_address": "Suite 400",
      "address_locality": "Charleston",
      "address_region": "SC",
      "postal_code": "29401",
      "address_country": "US",
      "first_name": "Jane",
      "last_name": "Smith"
    },
    "credential": {
      "type": "DIRECT",
      "token": "{\"signature\":\"...\",\"protocolVersion\":\"ECv2\"...}"
    }
  }
}
```

## 4. Merchant Processing

Upon receiving a `gpay` payment instrument, merchants MUST:

1.  **Validate Handler:** Confirm `handler_id` corresponds to the Google Pay
    handler.
2.  **Extract Token:** Retrieve the token string from `tokenization_data.token`.
3.  **Process Payment:** Pass the token string and the transaction details to
    the PSP's endpoint.
    *   *Note: Most PSPs have a specific field for "Google Pay Payload" or
        "Network Token".*
4.  **Return Response:** Respond with the finalized checkout state
    (Success/Failure).

## 5. Security Considerations

### 5.1 Token Security

-   **PAYMENT_GATEWAY:** When using this tokenization type, the token is
    encrypted specifically for the tokenization party. The pass through party
    cannot decrypt this token and should pass it through to the tokenization
    party as-is.
-   **DIRECT:** If using `DIRECT` tokenization, the merchant receives encrypted
    card data that they must decrypt. This significantly increases PCI DSS
    compliance scope and is generally not recommended unless the merchant is a
    Level 1 PCI Compliant Service Provider.

### 5.2 Environment Isolation

-   **TEST Mode:** In `TEST` environment, Google Pay returns dummy tokens.
    These cannot be charged.
-   **PRODUCTION Mode:** Real cards are used. Merchants must ensure their PSP
    credentials in `config.allowed_payment_methods` match the environment.

## 6. References

-   **Handler Config Schema:**
    [`https://ucp.dev/handlers/google_pay/config.json`](https://ucp.dev/handlers/google_pay/config.json)
-   **Example Card Payment Instrument Schema:**
    [`https://ucp.dev/handlers/google_pay/card_instrument.json`](https://ucp.dev/handlers/google_pay/card_instrument.json)
-   **Google Pay Web API:**
    [`https://developers.google.com/pay/api/web/overview`](https://developers.google.com/pay/api/web/overview)
-   **Google Pay Brand Guidelines:**
    [`https://developers.google.com/pay/api/web/guides/brand-guidelines`](https://developers.google.com/pay/api/web/guides/brand-guidelines)
