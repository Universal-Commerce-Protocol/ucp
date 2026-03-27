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

# Razorpay Magic Checkout Payment Handler

* **Handler Name:** `com.razorpay.magic_checkout`
* **Version:** `2026-01-27`
* **Status:** Draft
* **Instrument Type:** [`hosted_checkout`](../../../source/schemas/shopping/types/hosted_checkout_instrument.json)

## Introduction

This handler implements the hosted checkout escalation pattern for UCP-compatible
platforms. Unlike credential-based handlers (e.g., `com.google.pay`, `dev.shopify.shop_pay`)
where the platform acquires a payment token, `com.razorpay.magic_checkout`
delegates the **entire payment flow** — including address capture, payment
method selection, and authorization — to Razorpay's hosted UI.

The platform's sole responsibility is redirecting the buyer to the
`continue_url` and polling for completion. No PSP-specific SDK integration
is required.

### Key Benefits

* **Full India Payment Coverage:** UPI, Cards (Debit/Credit), Netbanking,
  Wallets, EMI, BNPL, and Cash on Delivery through a single unified interface.
* **Zero Platform SDK Overhead:** Platforms implement only the standard UCP
  escalation pattern — no SDK, no credential handling, no tokenization.
* **Proven Conversion:** Razorpay's optimized checkout flow trusted by 10M+
  merchants across India.
* **Complete Compliance:** PCI DSS, NPCI, and RBI compliance handled entirely
  by Razorpay.

### Integration Guide

| Participant  | Integration Section                           |
| :----------- | :-------------------------------------------- |
| **Business** | [Business Integration](#business-integration) |
| **Platform** | [Platform Integration](#platform-integration) |

---

## Participants

| Participant  | Role                                                                                             | Prerequisites                                              |
| :----------- | :----------------------------------------------------------------------------------------------- | :--------------------------------------------------------- |
| **Business** | Advertises handler, creates Razorpay orders, processes webhooks, updates UCP checkout status.    | Yes — Razorpay merchant account with Magic Checkout enabled |
| **Platform** | Discovers handler, triggers escalation via Complete Checkout, redirects buyer, polls for status. | No — standard UCP escalation handling only                 |
| **Buyer**    | Completes payment in Magic Checkout UI, provides address, selects payment instrument.            | No — Magic Checkout handles buyer onboarding               |

```text
+------------+       +------------------+       +--------------+       +-----------------+
|  Platform  |       |     Business     |       | Razorpay API |       | Magic Checkout  |
+-----+------+       +--------+---------+       +------+-------+       +-------+---------+
      |                       |                        |                       |
      |-- POST /checkout ----->|                        |                       |
      |<-- 201 {handler} -----|                        |                       |
      |                       |                        |                       |
      |-- POST /complete ----->|                        |                       |
      |                       |-- POST /v1/orders ----->|                       |
      |                       |<-- {order_id} ---------|                       |
      |<-- requires_escalation|                        |                       |
      |    + continue_url -----|                        |                       |
      |                       |                        |                       |
      |-- Redirect buyer ----------------------------------------->|           |
      |                       |                        |  Payment  |           |
      |                       |<-- webhook: payment.captured -------|           |
      |                       |-- update status ------->|           |           |
      |                       |                        |           |           |
      |-- GET /checkout ------>|                        |           |           |
      |<-- status: completed--|                        |           |           |
```

---

## Business Integration

### Prerequisites

Before advertising this handler, businesses **MUST** complete all of the
following steps:

1. **Create a Razorpay Account:** Register at [dashboard.razorpay.com](https://dashboard.razorpay.com)
   and complete merchant onboarding, including KYC verification and bank account details.
2. **Obtain API Credentials:** Generate a live `key_id` and `key_secret` from
   the Razorpay Dashboard under **Settings → API Keys**.
3. **Enable Magic Checkout:** Activate the Magic Checkout feature from
   **Settings → Magic Checkout** in the Razorpay Dashboard.
4. **Configure Webhook Endpoint:** Register a publicly accessible HTTPS webhook
   URL in the Dashboard under **Settings → Webhooks**. Subscribe to at minimum
   the `payment.captured` and `order.paid` events.

> **Security:** `key_secret` and `webhook_secret` are for **Business Internal
> Use Only**. They **MUST NOT** be exposed to the Platform, Buyer, or in
> publicly accessible logs under any circumstances.

**Prerequisites Output:**

| Field            | Description                                                                   |
| :--------------- | :---------------------------------------------------------------------------- |
| `key_id`         | API key for authenticating requests to `api.razorpay.com`.                   |
| `key_secret`     | API secret. Passed as HTTP Basic Auth password. Internal use only.            |
| `webhook_secret` | Used to verify `X-Razorpay-Signature` on incoming webhook payloads. Internal use only. |

### Handler Configuration

Businesses advertise Magic Checkout support by including this handler in the
`payment_handlers` object of their UCP checkout response.

#### Handler Schema

**Schema URL:** `https://razorpay.com/ucp/handlers/magic_checkout/2026-01-27/schemas/config.json`

| Field           | Type   | Required | Description                                                          |
| :-------------- | :----- | :------- | :------------------------------------------------------------------- |
| `environment`   | string | Yes      | `"sandbox"` or `"production"`                                        |
| `merchant_id`   | string | Yes      | Razorpay merchant identifier. Pattern: `^rzp_(test_\|live_)?[a-zA-Z0-9]+$` |
| `merchant_name` | string | Yes      | Business display name shown in the Magic Checkout UI (max 100 chars) |

#### Example — Handler Declaration in Create Checkout Response

```json
{
  "id": "chk_abc123",
  "status": "incomplete",
  "currency": "INR",
  "payment": {
    "handlers": [
      {
        "id": "razorpay_magic_001",
        "name": "com.razorpay.magic_checkout",
        "version": "2026-01-27",
        "spec": "https://razorpay.com/ucp/handlers/magic_checkout/2026-01-27/",
        "schema": "https://razorpay.com/ucp/handlers/magic_checkout/2026-01-27/schemas/config.json",
        "available_instruments": [
          { "type": "hosted_checkout" }
        ],
        "config": {
          "environment": "production",
          "merchant_id": "rzp_live_abc123xyz",
          "merchant_name": "BigBasket"
        }
      }
    ],
    "instruments": [
      {
        "id": "inst_hosted_001",
        "handler_id": "razorpay_magic_001",
        "type": "hosted_checkout",
        "display_name": "Razorpay Magic Checkout",
        "display_logo": "https://cdn.razorpay.com/logos/magic-checkout.svg"
      }
    ]
  }
}
```

> **Note:** When the buyer's delivery address is not yet confirmed or is
> outside the serviceable area, businesses **SHOULD** omit the
> `instruments` array or return an empty array. The hosted checkout option
> **MUST NOT** be offered until serviceability is confirmed.

### Processing Payments (Complete Checkout)

Upon receiving a Complete Checkout request, the business **MUST** execute the
following steps before returning a response:

#### Step 1 — Create a Razorpay Order

`POST https://api.razorpay.com/v1/orders`

| Field             | Type    | Required | Notes                                                                      |
| :---------------- | :------ | :------- | :------------------------------------------------------------------------- |
| `amount`          | integer | Yes      | In paise (smallest INR unit). Minimum: 100 (₹1).                          |
| `currency`        | string  | Yes      | Must be `"INR"` for this handler.                                          |
| `receipt`         | string  | No       | Internal reference. Max 40 chars, must be unique.                          |
| `notes`           | object  | Yes*     | **MUST** include `ucp_checkout_id` for webhook-to-session correlation.     |
| `partial_payment` | boolean | No       | Default `false`. Do not enable for standard Magic Checkout flows.          |

```json
{
  "amount": 57700,
  "currency": "INR",
  "receipt": "order_internal_001",
  "notes": {
    "ucp_checkout_id": "chk_abc123"
  }
}
```

#### Step 2 — Construct Magic Checkout URL

Build the `continue_url` using the Razorpay Order ID. Include a
`callback_url` for post-payment redirect and set `redirect=true` for
redirect-mode flows:

```
https://checkout.razorpay.com/v1/checkout/{order_id}
  ?key_id={key_id}
  &callback_url={encoded_callback_url}
  &redirect=true
```

#### Step 3 — Store the Order Binding

Businesses **MUST** persist the `razorpay_order_id → ucp_checkout_id` mapping
before returning the escalation response. This binding is required for
webhook processing:

```sql
INSERT INTO ucp_checkout_orders (ucp_checkout_id, razorpay_order_id, status)
VALUES ('chk_abc123', 'order_xyz789', 'pending');
```

#### Step 4 — Return Escalation

Respond with `status: "requires_escalation"` and the `continue_url` at the
checkout root level:

```json
{
  "id": "chk_abc123",
  "status": "requires_escalation",
  "continue_url": "https://checkout.razorpay.com/v1/checkout/order_xyz789?key_id=rzp_live_abc123xyz&callback_url=https%3A%2F%2Fmerchant.com%2Fucp%2Fcallback%3Fcheckout_id%3Dchk_abc123&redirect=true",
  "payment": {
    "selected_instrument_id": "inst_hosted_001",
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

When the buyer completes payment, Razorpay delivers an HTTP POST to the
configured webhook endpoint. Businesses **MUST** handle the following events:

| Event               | When Triggered                   | Required Action                                                                   |
| :------------------ | :------------------------------- | :-------------------------------------------------------------------------------- |
| `payment.captured`  | Payment successfully captured    | Verify signature → look up checkout via `notes.ucp_checkout_id` → set `completed` |
| `order.paid`        | Order fully paid                 | May be used as an additional confirmation signal.                                 |
| `payment.failed`    | Payment declined or failed       | Buyer may retry within Magic Checkout UI. No UCP action required unless session expired. |

#### Signature Verification (Mandatory)

Businesses **MUST** verify the `X-Razorpay-Signature` header using HMAC-SHA256
before processing any webhook event. Signature comparison **MUST** use a
constant-time function to prevent timing side-channel attacks:

```
HMAC-SHA256(webhook_secret, request_body) == X-Razorpay-Signature
```

#### Idempotent Processing

Businesses **MUST** deduplicate `payment.captured` events using
`payload.payment.entity.id` as the idempotency key. Processing the same
payment event twice **MUST NOT** result in double-fulfillment.

---

## Platform Integration

### Prerequisites

Platforms require no special registration or SDK integration. Platforms **MUST**
be capable of:

1. Detecting `type: "hosted_checkout"` instruments in checkout responses.
2. Submitting `POST /checkout-sessions/{id}/complete` with the instrument reference.
3. Handling `requires_escalation` status by redirecting the buyer to `continue_url`.
4. Polling `GET /checkout-sessions/{id}` until status transitions to `completed`.

### Payment Protocol

#### Step 1 — Discover Handler

The platform identifies `com.razorpay.magic_checkout` in the handlers array
and locates the corresponding `hosted_checkout` instrument.

**Platform Action:** Recognize `type: "hosted_checkout"` as a redirect-based
flow requiring no SDK invocation or token acquisition.

#### Step 2 — Complete Checkout

Submit the Complete Checkout request, referencing the hosted checkout instrument:

```http
POST /checkout-sessions/chk_abc123/complete HTTP/1.1
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json
Idempotency-Key: 660e8400-e29b-41d4-a716-446655440001

{
  "payment_data": {
    "id": "inst_hosted_001",
    "handler_id": "razorpay_magic_001",
    "type": "hosted_checkout",
    "credential": {
      "type": "hosted_checkout"
    }
  }
}
```

#### Step 3 — Handle Escalation

Upon receiving `status: "requires_escalation"`, the platform **MUST**:

1. Extract `continue_url` from the response root.
2. Redirect the buyer to `continue_url` (browser redirect or webview open).
3. Begin polling `GET /checkout-sessions/{id}` for status updates.

#### Step 4 — Poll for Completion

Poll the checkout session until status transitions from `requires_escalation`
to `completed`. Businesses **SHOULD** respond with `Retry-After` headers;
platforms **SHOULD** implement exponential backoff.

| Status                | Meaning                          | Platform Action                              |
| :-------------------- | :------------------------------- | :------------------------------------------- |
| `requires_escalation` | Buyer is in Magic Checkout UI    | Continue polling                             |
| `completed`           | Payment captured, order created  | Display order confirmation                   |
| `canceled`            | Session abandoned or expired     | Prompt buyer to start a new checkout session |

---

## Security Considerations

| Requirement                  | Description                                                                                              |
| :--------------------------- | :------------------------------------------------------------------------------------------------------- |
| **Webhook Signature**        | Businesses **MUST** verify `X-Razorpay-Signature` using HMAC-SHA256 before processing any event.        |
| **Constant-Time Comparison** | Signature comparison **MUST** use a constant-time function to prevent timing side-channel attacks.       |
| **HTTPS Everywhere**         | All URLs — `continue_url`, webhook endpoint, `callback_url` — **MUST** use HTTPS.                       |
| **Session Binding**          | Businesses **MUST** store `razorpay_order_id → ucp_checkout_id` in `notes` before returning escalation. |
| **Idempotent Webhooks**      | Businesses **MUST** deduplicate `payment.captured` events using `payment.id` as the idempotency key.    |
| **Credential Minimization**  | The `hosted_checkout_credential` contains only a reference `session_id`. No sensitive payment data passes through UCP. |
| **Webhook Port Restriction** | Razorpay delivers webhooks only to ports 80 or 443.                                                     |

---

## Error Handling

### Configuration Errors

| Code                       | Severity | Description                               | Resolution                                             |
| :------------------------- | :------- | :---------------------------------------- | :----------------------------------------------------- |
| `invalid_merchant_id`      | `error`  | Merchant ID not found or inactive         | Verify Razorpay account and key mode (test vs. live)   |
| `magic_checkout_disabled`  | `error`  | Magic Checkout not enabled on account     | Activate in Razorpay Dashboard settings                |
| `unsupported_currency`     | `error`  | Currency is not INR                       | This handler supports INR only                         |

### Checkout Errors

| Code                    | Severity | Description                                        | Resolution                                          |
| :---------------------- | :------- | :------------------------------------------------- | :-------------------------------------------------- |
| `order_creation_failed` | `error`  | Failed to create Razorpay order (e.g., amount < ₹1) | Verify `amount ≥ 100` paise; retry with backoff    |
| `checkout_expired`      | `error`  | Session expired before buyer completed payment     | Platform creates a new checkout session             |

### Payment Errors (Handled by Razorpay UI)

These errors occur within the Magic Checkout hosted UI and are surfaced
directly to the buyer by Razorpay. No platform-side handling is required.

| Code                    | Description                                        |
| :---------------------- | :------------------------------------------------- |
| `payment_failed`        | Payment declined by the bank or issuer             |
| `insufficient_balance`  | UPI/wallet balance is insufficient                 |
| `payment_timeout`       | Payment not completed within the allowed time      |
| `authentication_failed` | OTP, PIN, or biometric verification failed         |

---

## Status Transitions

```text
  incomplete
      │ (PUT with fulfillment data)
      ▼
ready_for_complete
      │ (POST /complete → Razorpay order created)
      ▼
requires_escalation  ──── (buyer retry within Magic Checkout UI) ────┐
      │                                                               │
      │ (payment.captured webhook received)                          │
      ▼                                                               │
  completed                                                   requires_escalation
      │
   canceled (session expired or buyer abandoned)
```

---

## References

| Resource                          | URL                                                                             |
| :-------------------------------- | :------------------------------------------------------------------------------ |
| UCP Checkout Specification        | [ucp.dev/specification/checkout](https://ucp.dev/specification/checkout/)       |
| UCP REST Binding                  | [ucp.dev/specification/checkout-rest](https://ucp.dev/specification/checkout-rest/) |
| UCP Payment Handler Guide         | [ucp.dev/specification/payment-handler-guide](https://ucp.dev/specification/payment-handler-guide/) |
| Hosted Checkout Instrument Schema | [hosted_checkout_instrument.json](https://ucp.dev/schemas/shopping/types/hosted_checkout_instrument.json) |
| Hosted Checkout Credential Schema | [hosted_checkout_credential.json](https://ucp.dev/schemas/shopping/types/hosted_checkout_credential.json) |
| Razorpay Orders API               | [razorpay.com/docs/api/orders](https://razorpay.com/docs/api/orders/)           |
| Razorpay Webhooks                 | [razorpay.com/docs/webhooks](https://razorpay.com/docs/webhooks/)               |
| Magic Checkout Docs               | [razorpay.com/docs/payments/magic-checkout](https://razorpay.com/docs/payments/magic-checkout/) |

---

*Document Version: 1.0 · Last Updated: 2026-01-27 · Maintained by: Razorpay Product Team · License: Apache 2.0*
