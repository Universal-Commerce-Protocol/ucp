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

# Hosted Checkout Payment Handler

* **Handler Name:** `com.razorpay.magic_checkout`
* **Version:** `2026-01-23`
* **Pattern:** Hosted Checkout (Redirect-Based Escalation)

## Introduction

This handler demonstrates the **Hosted Checkout** pattern — a class of payment
integrations where the payment provider controls the complete payment experience,
including payment method selection, address capture, and authorization, within a
provider-hosted UI. The platform's sole responsibility is redirecting the buyer
to a `continue_url` and polling the checkout session for completion.

This contrasts with credential-based handlers (e.g., `com.google.pay`,
`dev.shopify.shop_pay`) where the platform acquires a payment token prior to
calling Complete Checkout.

The `com.razorpay.magic_checkout` handler is used here as a concrete, production ready
example of this pattern. Any provider operating a hosted checkout solution
(Eg. Razorpay, PayPal, Klarna, Shop Pay in redirect mode) can implement this same pattern using
the `hosted_checkout` instrument and credential types introduced in this
contribution.

### When to Use This Pattern

Use the hosted checkout pattern when:

- The payment provider offers a fully-managed, redirect-based checkout UI.
- The payment flow includes provider-specific steps the platform cannot
  orchestrate (e.g., regional payment methods, OTP, BNPL eligibility checks).
- The business wants to minimize platform-side payment logic and PCI scope.
- The provider's checkout UI has significant conversion optimization that the
  platform UI cannot replicate.

### Key Differences from Credential-Based Handlers

| Aspect | Credential-Based | Hosted Checkout (This Pattern) |
| :--- | :--- | :--- |
| **Platform acquires token?** | Yes, before Complete Checkout | No |
| **Platform SDK required?** | Yes (e.g., GPay SDK) | No |
| **Payment method selection** | Platform UI | Provider's hosted UI |
| **Instrument in response** | Carries credential (token/card) | Carries only a correlation `session_id` |
| **Escalation** | Exceptional (e.g., 3DS) | Standard (every transaction) |
| **Autonomous payments** | Possible with stored credentials | Not supported; requires human authentication |

### Key Benefits of `com.razorpay.magic_checkout`

- **Faster GTM:** 1000s of Merchants already use Razorpay's Magic Checkout Offering and can be enabled for UCP this pattern in almost no time (compared to native checkout which will require substiantial changes at both Merchant and Platform Level)
- **Complete hosted solution:** Handles payment collection, address capture, and
  method selection in a single Razorpay-owned UI.
- **Full India payment coverage:** UPI, Cards (Debit/Credit), Netbanking, Wallets,
  EMI, Buy Now Pay Later, Cash on Delivery — through a unified interface.
- **Zero platform SDK required:** Platforms redirect to `continue_url`. No SDK
  invocation, no credential handling, no PCI scope.
- **Proven conversion:** Leverages Razorpay's optimized checkout UI, trusted by
  10M+ merchants.

### Integration Guide

| Participant  | Integration Section                           |
| :----------- | :-------------------------------------------- |
| **Business** | [Business Integration](#business-integration) |
| **Platform** | [Platform Integration](#platform-integration) |

---

## Participants

Three participants interact within this handler's payment flow:

| Participant | Role | Prerequisites |
| :--- | :--- | :--- |
| **Business** | Is the MoR(Merchant Of Record) advertises handler config, creates Razorpay orders, processes webhook events, and updates the checkout session to `completed`. | Razorpay account, API credentials, webhook configured. See [Prerequisites](#prerequisites). |
| **Platform** | Discovers the handler, calls Complete Checkout, redirects buyer to `continue_url`, and polls for checkout completion. | None — no SDK or special registration required. |
| **Razorpay** | Hosts the Magic Checkout UI, processes payment via the selected payment rail, and delivers a signed webhook event on success. | N/A (third party) |

> **Note on Terminology:** This specification refers to merchants as
> **"businesses"** in alignment with UCP conventions. Razorpay API fields
> retain `merchant_*` naming (e.g., `key_id`).

### Flow Overview

```text
+------------+          +-----------+          +-----------+          
|  Platform  |          | Business  |          |  Razorpay |          
+-----+------+          +-----+-----+          +-----+-----+          
      |                       |                      |                
      |  1. Create Checkout   |                      |                
      |---------------------->|                      |                
      |                       |                      |                
      |  2. {status:incomplete,                      |                
      |     payment:{handlers,|                      |          
      |     instruments}}     |                      |          
      |<----------------------|                      |          
      |                       |                      |          
      |  3. Complete Checkout |                      |          
      |  (instrument ref)     |                      |          
      |---------------------->|                      |          
      |                       |  4. POST /v1/orders  |          
      |                       |--------------------->|          
      |                       |  5. {order_id}       |          
      |                       |<---------------------|          
      |                       |                      |          
      |  6. {status:requires_ |                      |          
      |     escalation,       |                      |          
      |     continue_url}     |                      |          
      |<----------------------|                      |          
      |                       |                      |          
      |  7. Redirect buyer    |  8. Buyer completes  |
      |  to continue_url      |         payment      |
      |--------------------------------------------->|
      |                       |                      |
      |                       |  9. Webhook (signed) |
      |                       |<---------------------|
      |                       |                      |
      | 10. Poll GET /checkout|                      |
      |---------------------->|                      |
      | 11. {status:completed}|                      |
      |<----------------------|                      |
```

---

## Business Integration

### Prerequisites

Before advertising this handler, businesses **MUST** complete all of the
following:

1. **Create a Razorpay account:** Register at
   [dashboard.razorpay.com](https://dashboard.razorpay.com) and complete merchant
   onboarding including KYC verification and bank account details.
2. **Obtain API credentials:** Generate a live `key_id` and `key_secret` from
   the Razorpay Dashboard under Settings → API Keys.
3. **Enable Magic Checkout:** Activate the Magic Checkout feature from your
   Razorpay Dashboard settings. See the
   [Magic Checkout Web Integration Guide](https://razorpay.com/docs/payments/magic-checkout/web/)
   for setup instructions.
4. **Configure a webhook endpoint:** Set up a publicly accessible HTTPS webhook
   URL in the Razorpay Dashboard. Note the `webhook_secret` — required for signature
   verification.

**Prerequisites Output:**

| Field | Description |
| :--- | :--- |
| `key_id` | Razorpay API key identifier (e.g., `rzp_live_abc123xyz`). Advertised in handler config. |
| `key_secret` | Razorpay API key secret. **MUST NOT** be shared with platforms or buyers. Business internal only. |
| `webhook_secret` | HMAC-SHA256 key for verifying Razorpay webhook signatures. **MUST NOT** be logged or exposed. |

> **Security:** `key_secret` and `webhook_secret` are for business internal use
> only. They **MUST NOT** be exposed to the platform, buyer, or in publicly
> accessible logs under any circumstances.

### Handler Configuration

Businesses advertise Magic Checkout support by including this handler in the
`ucp.payment_handlers` object of the Create Checkout response.

#### Configuration Schema

* **Schema URL:**
  `https://razorpay.com/ucp/handlers/magic_checkout/2026-01-23/schemas/config.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://razorpay.com/ucp/handlers/magic_checkout/2026-01-23/schemas/config.json",
  "title": "Razorpay Magic Checkout Handler Configuration",
  "type": "object",
  "required": ["environment", "key_id", "merchant_name"],
  "properties": {
    "environment": {
      "type": "string",
      "enum": ["sandbox", "production"],
      "description": "Target Razorpay environment."
    },
    "key_id": {
      "type": "string",
      "pattern": "^rzp_(test_|live_)?[a-zA-Z0-9]+$",
      "description": "Razorpay key_id. Used by the platform to identify the merchant in Razorpay's system."
    },
    "merchant_name": {
      "type": "string",
      "maxLength": 100,
      "description": "Display name shown in the Magic Checkout UI header."
    }
  }
}
```

#### Example — Handler Declaration in Create Checkout Response

This is the `ucp` envelope returned by the business in response to a Create
Checkout request. It advertises handler availability and pre-populates a
`hosted_checkout` instrument.

```json
{
  "ucp": {
    "version": "2026-01-23",
    "capabilities": {
      "dev.ucp.shopping.checkout": [{ "version": "2026-01-23" }]
    },
    "payment_handlers": {
      "com.razorpay.magic_checkout": [
        {
          "id": "razorpay_magic_001",
          "version": "2026-01-23",
          "spec": "https://razorpay.com/ucp/handlers/magic_checkout/2026-01-23/",
          "config_schema": "https://razorpay.com/ucp/handlers/magic_checkout/2026-01-23/schemas/config.json",
          "instrument_schemas": [
            "https://ucp.dev/schemas/shopping/types/hosted_checkout_instrument.json"
          ],
          "config": {
            "environment": "production",
            "key_id": "rzp_live_abc123xyz",
            "merchant_name": "ExampleMerchant"
          }
        }
      ]
    }
  }
}
```

### Payment Processing Protocol

Upon receiving a Complete Checkout request, the business **MUST** execute the
following steps:

#### Step 1: Create a Razorpay Order

Call the Razorpay Orders API. The `notes` field **SHOULD** include the UCP
`checkout_id` to enable webhook-to-session correlation.

**Request:**

```http
POST https://api.razorpay.com/v1/orders
Authorization: Basic base64(key_id:key_secret)
Content-Type: application/json

{
  "amount": 57700,
  "currency": "INR",
  "notes": {
    "ucp_checkout_id": "chk_abc123"
  }
}
```

**Response:**

```json
{
  "id": "order_xyz789",
  "entity": "order",
  "amount": 57700,
  "currency": "INR",
  "status": "created",
  "notes": { "ucp_checkout_id": "chk_abc123" }
}
```

> **Amount units:** Razorpay amounts are in the smallest currency unit (paise for
> INR). ₹577.00 → `amount: 57700`. Always convert from the UCP checkout `totals`
> before calling the Orders API.

#### Step 2: Construct the Magic Checkout URL

Build the `continue_url` for the Razorpay hosted checkout endpoint. Parameters
use **Nested array notation** — checkout options under `checkout[*]` and
redirect URLs under `url[*]`.

| Query Parameter | Source | Description |
| :--- | :--- | :--- |
| `checkout[key]` | `config.key_id` | Business's public Razorpay key |
| `checkout[order_id]` | Razorpay Order `id` | Created in Step 1 |
| `url[callback]` | Platform-provided callback URL | **Required.** POST destination after payment. Maps to `return_url` in the credential. |
| `url[cancel]` | Platform-provided cancel URL | Optional. Redirect destination on buyer cancellation. Maps to `cancel_url` in the credential. |

> **URL encoding:** All parameter values MUST be URL-encoded. `url[callback]` and
> `url[cancel]` must themselves be fully-qualified HTTPS URLs, percent-encoded
> when embedded as query parameter values.

**Example `continue_url`:**

```
https://api.razorpay.com/v1/checkout/hosted?
  checkout[key]=rzp_live_abc123xyz&
  checkout[order_id]=order_xyz789&
  url[callback]=https%3A%2F%2Fplatform.example.com%2Fpayment%2Fcallback&
  url[cancel]=https%3A%2F%2Fplatform.example.com%2Fpayment%2Fcancelled
```

> **Callback behavior:** After the buyer completes payment, Razorpay sends a
> **POST** (not a GET redirect) to `url[callback]` with form fields
> `razorpay_payment_id`, `razorpay_order_id`, and `razorpay_signature`. The
> business MUST verify the signature before acting on this POST. Platforms MUST
> rely on the UCP session poll for authoritative status — not the callback.

#### Step 3: Return Escalation to Platform

Respond to Complete Checkout with `status: "requires_escalation"` and the
`continue_url` at the checkout root level. Populate the instrument credential
with the Razorpay Order ID for correlation.

```json
{
  "id": "chk_abc123",
  "status": "requires_escalation",
  "currency": "INR",
  "continue_url": "https://api.razorpay.com/v1/checkout/hosted?checkout[key]=rzp_live_abc123xyz&checkout[order_id]=order_xyz789&...",
  "expires_at": "2026-01-28T13:00:00Z",
  "messages": [
    {
      "type": "info",
      "code": "payment_in_progress",
      "content": "Buyer is completing payment in Razorpay Magic Checkout",
      "severity": "requires_buyer_input"
    }
  ],
  "payment": {
    "instruments": [
      {
        "id": "inst_hosted_001",
        "handler_id": "razorpay_magic_001",
        "type": "hosted_checkout",
        "display_name": "Razorpay Magic Checkout",
        "display_logo": "https://cdn.razorpay.com/logos/magic-checkout.svg",
        "credential": {
          "type": "hosted_checkout",
          "session_id": "order_xyz789"
        }
      }
    ]
  }
}
```

### Webhook Processing

When the buyer completes payment, Razorpay sends a signed `HTTP POST` to the
configured webhook endpoint.

> **Security: Signature verification is mandatory.** Before processing any
> webhook, businesses **MUST** verify the `X-Razorpay-Signature` header using
> HMAC-SHA256 with the `webhook_secret`. Use constant-time comparison to prevent
> timing attacks.

**Verification algorithm:**

```
expected_signature = HMAC-SHA256(webhook_secret, raw_request_body)
assert constant_time_compare(X-Razorpay-Signature, expected_signature)
```

**`payment.captured` — Key Fields:**

```json
{
  "event": "payment.captured",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_abc123",
        "order_id": "order_xyz789",
        "status": "captured",
        "amount": 57700,
        "currency": "INR",
        "method": "upi",
        "notes": {
          "ucp_checkout_id": "chk_abc123"
        }
      }
    }
  }
}
```

After verifying the signature and extracting `ucp_checkout_id` from `notes`, the
business **MUST** update the corresponding UCP checkout session to `completed`
and populate the `order` object.

**Webhook processing MUST be idempotent.** Use `payment.entity.id` as the
idempotency key. If webhook delivery fails, Razorpay retries with exponential
backoff; the business can also poll the Razorpay Orders API to confirm payment
status.

---

## Platform Integration

### Prerequisites

Platforms require no special registration or SDK to support this handler.

Platforms **MUST** be capable of:

1. Detecting `type: "hosted_checkout"` instruments in checkout responses.
2. Calling `POST /checkout-sessions/{id}/complete` with the instrument reference.
3. Handling `requires_escalation` status by redirecting the buyer to `continue_url`.
4. Polling `GET /checkout-sessions/{id}` until status transitions to `completed`.

### Payment Protocol

#### Step 1: Discover the Handler

The platform reads the Create Checkout response and identifies the
`com.razorpay.magic_checkout` handler with a `hosted_checkout` instrument.

> **Platform action:** Recognize `type: "hosted_checkout"` as a redirect-based
> flow. No SDK invocation or token acquisition is required. Proceed directly to
> Complete Checkout.

#### Step 2: Complete Checkout

Submit the Complete Checkout request referencing the hosted checkout instrument.

```http
POST /checkout-sessions/chk_abc123/complete HTTP/1.1
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json

{
  "payment": {
    "selected_instrument_id": "inst_hosted_001"
  }
}
```

#### Step 3: Handle Escalation

The business responds with `status: "requires_escalation"` and a `continue_url`.

The platform **MUST**:

1. Extract `continue_url` from the checkout root (not from the payment object).
2. Redirect the buyer to `continue_url`.
3. Begin polling `GET /checkout-sessions/{id}` at a reasonable interval
   (recommended: every 2–5 seconds).

#### Step 4: Poll for Completion

Poll until the checkout status transitions from `requires_escalation` to
`completed`. At that point the `order` object is populated and the checkout
is finalized.

**While payment is in progress** (`status: "requires_escalation"`):

```json
{
  "id": "chk_abc123",
  "status": "requires_escalation",
  "continue_url": "https://api.razorpay.com/v1/checkout/hosted?checkout[key]=rzp_live_abc123xyz&..."
}
```

**After payment completes** (`status: "completed"`):

```json
{
  "id": "chk_abc123",
  "status": "completed",
  "order": {
    "id": "ORD-2026-001",
    "permalink_url": "https://bigbasket.com/orders/ORD-2026-001"
  },
  "buyer": {
    "email": "priya.sharma@example.com",
    "first_name": "Priya",
    "last_name": "Sharma"
  },
  "totals": [
    { "type": "subtotal", "amount": 57700 },
    { "type": "fulfillment", "display_text": "Delivery", "amount": 0 },
    { "type": "total", "amount": 57700 }
  ],
  "fulfillment": {
    "methods": [
      {
        "id": "shipping_1",
        "type": "shipping",
        "selected_destination_id": "dest_1",
        "destinations": [
          {
            "id": "dest_1",
            "street_address": "123 MG Road, Indiranagar",
            "address_locality": "Bangalore",
            "address_region": "KA",
            "postal_code": "560038",
            "address_country": "IN"
          }
        ]
      }
    ]
  }
}
```

---

## Status Transitions

```text
                              ┌──────────────────────────────────────┐
                              │          Standard UCP States         │
                              └──────────────────────────────────────┘

incomplete ──(fulfillment resolved)──> ready_for_complete
                                              │
                                   (POST /complete)
                                              │
                                              ▼
                                  complete_in_progress
                                              │
                               (Razorpay order created)
                                              │
                                              ▼
                               requires_escalation ◄──── (buyer retries payment)
                                              │
                                   (webhook received +
                                    checkout updated)
                                              │
                                              ▼
                                          completed
```

---

## Error Handling

### Configuration Errors

| Code | Cause | Resolution |
| :--- | :--- | :--- |
| `invalid_handler_config` | `key_id` invalid or inactive | Verify Razorpay key_id and account status |
| `handler_not_available` | Magic Checkout not enabled | Enable in Razorpay Dashboard settings |

### Checkout Errors

| Code | Cause | Resolution |
| :--- | :--- | :--- |
| `checkout_expired` | Session TTL exceeded | Buyer must initiate a new checkout |
| `amount_mismatch` | Razorpay order amount ≠ checkout total | Recalculate totals; create new session |
| `currency_not_supported` | Non-INR checkout | This handler only supports `INR` |

```json
{
  "id": "chk_abc123",
  "status": "incomplete",
  "messages": [
    {
      "type": "error",
      "code": "checkout_expired",
      "content": "Payment session has expired. Please start a new checkout.",
      "severity": "terminal"
    }
  ]
}
```

### Payment Errors (Handled by Razorpay UI)

Payment failures (insufficient funds, bank declines, OTP failures) are surfaced
directly to the buyer within the Magic Checkout hosted UI. The checkout session
remains in `requires_escalation` until either payment succeeds or the session
expires. The platform continues polling; no platform-side retry logic is needed.

### Webhook Delivery Failure

1. Razorpay retries failed webhooks with exponential backoff.
2. The business **SHOULD** implement a reconciliation job that polls the Razorpay
   Orders API (`GET https://api.razorpay.com/v1/orders/{order_id}`) for
   `status: "paid"` as a fallback.
3. The platform continues polling the checkout session independently and will
   see `completed` once the business updates the session, regardless of webhook
   delivery timing.

---

## Security Considerations

- **Credential confidentiality:** `key_secret` and `webhook_secret` are
  business-internal. They **MUST NOT** appear in UCP payloads, platform
  responses, or logs.
- **Webhook signature verification:** Mandatory before processing any webhook.
  Failure to verify opens the business to payment spoofing attacks.
- **Idempotent webhook processing:** Use `payment.entity.id` as idempotency key.
  Duplicate delivery is possible; processing the same event twice MUST be safe.
- **`session_id` is not a payment credential:** Platforms **MUST NOT** attempt
  to use the `hosted_checkout_credential.session_id` as a payment token or
  submit it to any payment API.
- **HTTPS only:** All URLs including `continue_url`, `display_logo`, and webhook
  endpoints **MUST** use HTTPS.

---

## References

| Resource | URL |
| :--- | :--- |
| Handler specification | `https://razorpay.com/ucp/handlers/magic_checkout/2026-01-23/` |
| Razorpay Orders API | `https://razorpay.com/docs/api/orders` |
| Magic Checkout docs | `https://razorpay.com/docs/payments/magic-checkout` |
| Razorpay Webhooks | `https://razorpay.com/docs/webhooks` |
| UCP Checkout Specification | [Checkout](../checkout.md) |
| UCP REST Binding | [HTTP/REST Binding](../checkout-rest.md) |
| UCP Payment Handler Guide | [Guide](../payment-handler-guide.md) |
| Hosted Checkout Instrument Schema | `https://ucp.dev/schemas/shopping/types/hosted_checkout_instrument.json` |
