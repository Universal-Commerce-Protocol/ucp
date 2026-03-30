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

# Razorpay UPI Circle Payment Handler

* **Handler Name:** `com.razorpay.upi.circle`
* **Version:** `{{ ucp_version }}`

## Introduction

This handler enables **delegated UPI payments** in India via
[Razorpay](https://razorpay.com) as the payment service provider.
[UPI Circle](https://www.npci.org.in/what-we-do/upi/product-overview) is
NPCI's delegation framework — buyers authorize an AI agent to make payments
on their behalf within configurable per-transaction and monthly limits,
**without per-transaction MPIN authentication**.

This handler follows the **credential-before-Complete-Checkout** pattern
(same as `com.google.pay` and `dev.shopify.shop_pay`): the platform fetches
a one-time cryptogram from Razorpay AI Commerce TSP, embeds it in Complete
Checkout, and the business processes the delegated debit — resulting in a
straight `completed` status. No escalation, no app switch, no buyer
interaction at payment time.

!!! note "Delegation setup is out-of-band"
    This handler requires a one-time delegation setup between the buyer, the
    AI Platform, and Razorpay AI Commerce TSP **before** any payment can
    occur. This setup is a bilateral integration — analogous to a buyer
    saving a card on ChatGPT — and is **not part of the UCP protocol**.
    See [Delegation Setup](#delegation-setup-out-of-band) for details.

### Key Benefits

* **Truly agentic** — No per-transaction authentication. The agent pays
  autonomously within mandate limits.
* **Zero PCI-DSS scope** — VPA-based; no card data touches any system.
* **Zero buyer friction at payment time** — No app switch, no QR code, no
  MPIN. Like card-on-file for UPI.
* **NPCI-backed guardrails** — Per-transaction and monthly limits enforced
  at the mandate level by NPCI and the buyer's bank.
* **India scale** — 500M+ UPI users on India's dominant payment rail.

### Integration Guide

| Participant  | Integration Section                           |
| :----------- | :-------------------------------------------- |
| **Business** | [Business Integration](#business-integration) |
| **Platform** | [Platform Integration](#platform-integration) |

---

## Participants

> **Note on Terminology:**
> This specification refers to the payment-accepting party as the
> "business." Technical schema fields retain standard industry nomenclature
> (`merchant_*`, `key_id`). The mapping is: business ↔ merchant.

| Participant | Role | Prerequisites |
| :---------- | :--- | :------------ |
| **Business** | Advertises handler configuration, submits cryptogram to Razorpay PSP for delegated debit. | Yes — Razorpay account with KYC, `key_id`, `key_secret`. |
| **Platform** | Discovers handler, fetches cryptogram from Razorpay AI Commerce TSP, submits in Complete Checkout. | Yes — Razorpay AI Commerce TSP integration; active buyer delegation. |
| **Razorpay** | Processes delegated debit via NPCI using mandate UMN, sends payment webhook to business. | N/A — third-party PSP; business onboards via Razorpay dashboard. |

### Pattern Flow

```text
+------------+       +---------------------------+       +----------+       +---------+
|  Platform  |       | Razorpay AI Commerce TSP  |       | Business |       | Razorpay|
+-----+------+       +-------------+-------------+       +----+-----+       +----+----+
      |                            |                           |                  |
      | 1. POST /delegate/{id}/    |                           |                  |
      |    token_transactional_data|                           |                  |
      |--------------------------->|                           |                  |
      | 2. cryptogram + expires_at |                           |                  |
      |<---------------------------|                           |                  |
      |                            |                           |                  |
      | 3. POST complete-checkout  |                           |                  |
      |    (upi_circle instrument  |                           |                  |
      |     + cryptogram credential)                           |                  |
      |------------------------------------------------------->|                  |
      |                            |                           | 4. Delegated     |
      |                            |                           |    debit via NPCI|
      |                            |                           |----------------->|
      |                            |                           | 5. NPCI confirms |
      |                            |                           |<-----------------|
      | 6. status: completed       |                           |                  |
      |<-------------------------------------------------------|                  |
      |                            |                           | 7. payment.      |
      |                            |                           |    authorized    |
      |                            |                           |<-----------------|
```

---

## Delegation Setup (Out-of-Band)

Before any payment, the buyer must establish a delegation mandate. This
one-time setup happens **outside UCP** as a bilateral integration between
the AI Platform and Razorpay AI Commerce TSP.

### Setup Flow Summary

1. **OTP Verification** — Platform calls Razorpay TSP to send OTP to the
   buyer's registered mobile number. Buyer submits OTP to platform.
2. **Smart Intent / QR** — TSP returns a UPI intent link or QR code.
   Platform surfaces it to the buyer.
3. **Mandate Authorization** — Buyer opens their UPI PSP app, confirms
   delegation to the AI Platform, sets per-transaction and monthly limits,
   and enters MPIN. Bank and NPCI create the delegation mandate.
4. **Delegation Active** — TSP receives NPCI callback. Platform polls
   `GET /delegate/{delegate_id}` until `status: linked`. Platform securely
   stores `delegate_id` for future payments.

**Output:** `delegate_id` — a persistent mandate reference used for all
subsequent payments under this delegation.

### Setup API Reference

| API | Method | Purpose |
| :-- | :----- | :------ |
| `/v1/upi/ai-tpap/customers/generate_otp` | POST | Send OTP to buyer's registered mobile |
| `/v1/upi/ai-tpap/customers/{cust_id}/otp_submit` | POST | Verify OTP; receive UPI intent link / QR for mandate creation |
| `/v1/upi/ai-tpap/delegate/{delegate_id}` | GET | Poll delegation status until `linked` |

Detailed API specifications are maintained in the
[Razorpay AI Commerce TSP API Docs](https://razorpay.com/docs/ai-commerce-tsp/).

---

## Business Integration

### Prerequisites

Before advertising this handler, businesses **MUST** complete:

1. **Create a Razorpay account** at
   [dashboard.razorpay.com](https://dashboard.razorpay.com).
2. **Complete KYC** to activate live payments.
3. **Retrieve API keys** from *Settings → API Keys*:
   * `key_id` — Public key (`rzp_live_*` or `rzp_test_*`).
   * `key_secret` — Private key. **MUST remain on the business backend.**
     **MUST NOT appear in any UCP profile, response, or client-side code.**
4. **Configure webhooks** at *Settings → Webhooks* for the
   `payment.authorized` event. This is the mechanism by which the business
   learns the payment was authorized and can mark the checkout `completed`.

**Prerequisites Output:**

| Field                   | Description                                                                             |
| :---------------------- | :-------------------------------------------------------------------------------------- |
| `identity.access_token` | Maps to Razorpay `merchant_id` (visible in Dashboard).                                  |
| `key_id`                | Public API key for profile advertisement.                                               |
| `key_secret`            | Private key for Razorpay API calls. Store in a secret manager; never expose externally. |
| webhook secret          | Secret for verifying `X-Razorpay-Signature` on incoming webhook events.                |

### Handler Configuration

Businesses advertise support for this handler in their UCP profile's
`payment_handlers` registry at `/.well-known/ucp`.

#### Handler Schema

**Schema URL:** `https://razorpay.com/ucp/handlers/upi-circle/schema.json`

| Config Variant    | Context              | Key Fields                                |
| :---------------- | :------------------- | :---------------------------------------- |
| `business_config` | Business discovery   | `key_id`, `environment`, `merchant_name`  |
| `platform_config` | Platform discovery   | _(no required fields)_                    |
| `response_config` | Checkout responses   | `environment`, `merchant_name`            |

#### Business Config Fields

| Field           | Type   | Required | Description                                                    |
| :-------------- | :----- | :------- | :------------------------------------------------------------- |
| `environment`   | string | Yes      | `sandbox` or `production`                                      |
| `key_id`        | string | Yes      | Public Razorpay API key                                        |
| `merchant_name` | string | No       | Display name shown to the buyer during payment                 |

#### Response Config Fields

| Field           | Type   | Required | Description                              |
| :-------------- | :----- | :------- | :--------------------------------------- |
| `environment`   | string | Yes      | `sandbox` or `production`                |
| `merchant_name` | string | No       | Display name shown to the buyer          |

#### Example Business Handler Declaration

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "payment_handlers": {
      "com.razorpay.upi.circle": [
        {
          "id": "razorpay_upi_circle_live",
          "version": "{{ ucp_version }}",
          "spec": "https://razorpay.com/ucp/handlers/upi-circle",
          "schema": "https://razorpay.com/ucp/handlers/upi-circle/schema.json",
          "available_instruments": [
            { "type": "upi_circle" }
          ],
          "config": {
            "environment": "production",
            "key_id": "rzp_live_XXXXXXXXXXXXXXX",
            "merchant_name": "Acme Store"
          }
        }
      ]
    }
  }
}
```

### Processing Payments

When the business receives a Complete Checkout request with a `upi_circle`
instrument and a `upi_circle_cryptogram` credential, it **MUST**:

1. **Validate handler.** Confirm `instrument.handler_id` matches a declared
   `com.razorpay.upi.circle` handler and `instrument.type == "upi_circle"`.

2. **Ensure idempotency.** If this `checkout_id` already has a processed
   payment, return the existing result without re-processing.

3. **Extract cryptogram.** Retrieve `credential.cryptogram` and
   `credential.delegate_id` from the instrument.

4. **Initiate delegated debit.** Submit to Razorpay PSP to initiate a
   delegated debit via NPCI (PSP resolves the mandate UMN from `delegate_id`).

5. **Return result.** On immediate confirmation, respond `status: completed`.
   On async processing, respond `status: pending` and await the
   `payment.authorized` webhook before marking complete.

#### Success Response

```json
{
  "id": "checkout_abc123",
  "status": "completed",
  "order": {
    "id": "order_xyz789",
    "permalink_url": "https://store.example.com/orders/xyz789"
  }
}
```

#### Failure Response

```json
{
  "id": "checkout_abc123",
  "status": "canceled",
  "messages": [
    {
      "type": "error",
      "code": "payment_failed",
      "severity": "recoverable",
      "content": "Delegated UPI payment was declined. The mandate limit may have been exceeded or the mandate is no longer active.",
      "path": "$.payment"
    }
  ]
}
```

### Webhook Handling

Razorpay sends payment lifecycle events to the business's configured webhook
endpoint. Businesses **MUST** verify the `X-Razorpay-Signature` header
(HMAC-SHA256 of the raw request body using `webhook_secret`) before
processing any event.

| Event | Meaning | Required Business Action |
| :---- | :------ | :----------------------- |
| `payment.authorized` | NPCI confirmed the delegated debit | Mark checkout `completed`; create and fulfill order |
| `payment.failed` | Debit declined (limit exceeded, mandate expired, etc.) | Mark checkout `canceled`; surface appropriate error to platform |

#### Error Mapping

| Razorpay Condition               | UCP Error        | Action                                      |
| :------------------------------- | :--------------- | :------------------------------------------ |
| Cryptogram invalid or reused     | `payment_failed` | Return error; platform must fetch new cryptogram |
| Mandate limit exceeded           | `payment_failed` | Return error; buyer must adjust mandate limits |
| Mandate delinked or expired      | `payment_failed` | Return error; buyer must re-establish delegation |
| Currency is not `INR`            | `payment_failed` | Reject at handler selection stage            |

---

## Platform Integration

### Prerequisites

Before handling `com.razorpay.upi.circle` payments, platforms **MUST**:

1. **Complete delegation setup** — The buyer must have an active delegation
   mandate (see [Delegation Setup](#delegation-setup-out-of-band)).
   Platform must hold a valid `delegate_id` with `status: linked`.
2. **Integrate Razorpay AI Commerce TSP** — Platform must be able to call
   the cryptogram fetch API:
   `POST /v1/upi/ai-tpap/delegate/{delegate_id}/token_transactional_data`.
3. **Implement status polling** — Platform must be prepared to poll
   `GET /checkout-sessions/{checkout_id}` if the business responds
   `status: pending`.

### Handler Configuration

Platforms advertise UPI Circle support in their UCP profile.

#### Example Platform Handler Declaration

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "payment_handlers": {
      "com.razorpay.upi.circle": [
        {
          "id": "platform_razorpay_upi_circle",
          "version": "{{ ucp_version }}",
          "spec": "https://razorpay.com/ucp/handlers/upi-circle",
          "schema": "https://razorpay.com/ucp/handlers/upi-circle/schema.json",
          "available_instruments": [
            { "type": "upi_circle" }
          ]
        }
      ]
    }
  }
}
```

### Payment Protocol

Platforms **MUST** follow this four-step flow:

#### Step 1: Discover Handler

Identify `com.razorpay.upi.circle` in the business's `payment_handlers`
map from the UCP profile at `/.well-known/ucp`.

```json
{
  "id": "razorpay_upi_circle_live",
  "version": "{{ ucp_version }}",
  "spec": "https://razorpay.com/ucp/handlers/upi-circle",
  "schema": "https://razorpay.com/ucp/handlers/upi-circle/schema.json",
  "config": {
    "environment": "production",
    "key_id": "rzp_live_XXXXXXXXXXXXXXX",
    "merchant_name": "Acme Store"
  }
}
```

Platforms **SHOULD** only present UPI Circle as a payment option when:

* The buyer's delivery context indicates India (`address_country: "IN"`).
* The buyer has an active, linked delegation (`delegate_id` with
  `status: linked`).

#### Step 2: Fetch Cryptogram

Immediately before submitting Complete Checkout, call Razorpay AI Commerce
TSP to obtain a single-use cryptogram for this transaction:

```http
POST /v1/upi/ai-tpap/delegate/{delegate_id}/token_transactional_data
Authorization: Basic base64(key_id:secret)
Content-Type: application/json

{
  "delegate_id": "c894aa29a7da69"
}
```

**TSP Response:**

```json
{
  "delegate_id": "c894aa29a7da69",
  "cryptogram_value": "a345345dfgdfasdfh45jtyhgjkyutsdasd2",
  "expired_at": 1748716199
}
```

!!! warning "Cryptogram is single-use and time-limited"
    Platforms **MUST** fetch a fresh cryptogram for each transaction.
    Reusing a cryptogram will result in NPCI rejecting the debit.
    Convert `expired_at` (Unix timestamp) to RFC 3339 for the credential's
    `expires_at` field.

#### Step 3: Build Instrument and Credential

Construct the `upi_circle` instrument with the fetched cryptogram embedded
as the `credential`:

```json
{
  "id": "pi_001",
  "handler_id": "razorpay_upi_circle_live",
  "type": "upi_circle",
  "delegate_id": "c894aa29a7da69",
  "selected": true,
  "display": {
    "name": "UPI Autopay",
    "masked_vpa": "roh***@icici"
  },
  "credential": {
    "type": "upi_circle_cryptogram",
    "cryptogram": "a345345dfgdfasdfh45jtyhgjkyutsdasd2",
    "delegate_id": "c894aa29a7da69",
    "expires_at": "2026-03-26T12:15:00Z"
  }
}
```

#### Step 4: Submit Complete Checkout

```http
POST /checkout-sessions/{checkout_id}/complete
Content-Type: application/json
UCP-Agent: profile="https://agent.example.com/profile"

{
  "payment": {
    "instruments": [
      {
        "id": "pi_001",
        "handler_id": "razorpay_upi_circle_live",
        "type": "upi_circle",
        "delegate_id": "c894aa29a7da69",
        "selected": true,
        "display": {
          "name": "UPI Autopay",
          "masked_vpa": "roh***@icici"
        },
        "credential": {
          "type": "upi_circle_cryptogram",
          "cryptogram": "a345345dfgdfasdfh45jtyhgjkyutsdasd2",
          "delegate_id": "c894aa29a7da69",
          "expires_at": "2026-03-26T12:15:00Z"
        }
      }
    ]
  }
}
```

**Expected Response (straight to `completed`):**

```json
{
  "id": "checkout_abc123",
  "status": "completed",
  "order": {
    "id": "order_xyz789",
    "permalink_url": "https://store.example.com/orders/xyz789"
  }
}
```

If the business responds `status: pending`, platforms **MUST** poll
`GET /checkout-sessions/{checkout_id}` at reasonable intervals until a
terminal state (`completed` or `canceled`) is reached.

---

## Security Considerations

| Requirement | Description |
| :---------- | :---------- |
| **Cryptogram is single-use** | Platforms **MUST NOT** reuse cryptograms across transactions. Each Complete Checkout requires a freshly fetched cryptogram. |
| **Expiry enforcement** | Platforms **MUST** check `expires_at` before submitting. Fetch a new cryptogram if the session has been idle past expiry. |
| **Webhook signature verification** | Businesses **MUST** verify `X-Razorpay-Signature` (HMAC-SHA256) on all incoming webhooks before processing. |
| **Secure storage of `delegate_id`** | Platforms **MUST** treat `delegate_id` as a sensitive credential. Exposure allows an attacker to initiate payment flows on the buyer's behalf. |
| **HTTPS everywhere** | All API calls **MUST** use TLS 1.2+. |
| **Mandate limit enforcement** | Platforms **MUST NOT** attempt to circumvent per-transaction or monthly limits. Limits are enforced at the NPCI layer. |
| **No VPA exposure** | The full buyer VPA **MUST NOT** be exposed in `display.masked_vpa` or any platform-facing field. Always mask to `xxx***@provider` format. |
| **Idempotency** | Businesses **MUST** implement idempotent payment processing using `checkout_id` to prevent duplicate debits on network retries. |
| **Zero PCI-DSS scope** | This handler involves no card data. VPA-based routing means no PCI-DSS scope for platforms or businesses under this handler. |

---

## Schemas

| Schema | URI |
| :----- | :-- |
| Handler Schema | `https://razorpay.com/ucp/handlers/upi-circle/schema.json` |
| UPI Circle Instrument | `https://ucp.dev/schemas/shopping/types/upi_circle_instrument.json` |
| UPI Circle Credential | `https://ucp.dev/schemas/shopping/types/upi_circle_credential.json` |

---

## References

* **UCP Payment Handler Guide:** [specification/payment-handler-guide.md](payment-handler-guide.md)
* **UCP Checkout Specification:** [specification/checkout.md](checkout.md)
* **NPCI UPI Circle / Delegation:** <https://www.npci.org.in/what-we-do/upi/product-overview>
* **Razorpay AI Commerce TSP API Docs:** <https://razorpay.com/docs/ai-commerce-tsp/>
