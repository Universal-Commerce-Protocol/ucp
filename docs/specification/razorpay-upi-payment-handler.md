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

# Razorpay UPI Payment Handler

* **Handler Name:** `com.razorpay.upi`
* **Version:** `{{ ucp_version }}`

## Introduction

This handler enables UPI (Unified Payments Interface) payments in India via
[Razorpay](https://razorpay.com) as the payment service provider. UPI is a
real-time payment system managed by NPCI (National Payments Corporation of
India) that enables instant bank-to-bank transfers via mobile.

The handler uses the **UPI Intent** flow: the platform deep-links the buyer
into their preferred UPI app (Google Pay, PhonePe, Paytm, BHIM, etc.) to
authorize the payment. The Razorpay SDK generates a `upi://` deep-link from a
Razorpay Order and returns a cryptographic payment proof upon authorization.

### Key Benefits

* **No card credentials** — UPI payments use bank-to-bank transfers; no PAN
  or card data is involved, so PCI DSS scope is minimal.
* **Checkout-scoped binding** — The `razorpay_order_id` ties every payment
  proof to a specific checkout, preventing replay attacks without any
  tokenization endpoint.
* **Local verification** — The `razorpay_signature` is an HMAC-SHA256 proof
  the business verifies using their own `key_secret`, with no additional
  network call to Razorpay required before capture.
* **Full sandbox support** — Razorpay's test environment enables end-to-end
  testing with no real money.

### Integration Guide

| Participant  | Integration Section                           |
| :----------- | :-------------------------------------------- |
| **Business** | [Business Integration](#business-integration) |
| **Platform** | [Platform Integration](#platform-integration) |

---

## Participants

> **Note on Terminology:**
> This specification refers to the Razorpay merchant account holder as the
> **"business."** Razorpay's own API uses `merchant_id` internally — this
> maps to `PaymentIdentity.access_token` after onboarding.

| Participant  | Role                                                                                                           | Prerequisites                                                     |
| :----------- | :------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------- |
| **Business** | Creates the Razorpay Order, advertises handler config, verifies payment proof, captures payment.               | Yes — Razorpay account, `key_id` and `key_secret`.                |
| **Platform** | Discovers handler, reads `razorpay_order_id` from response config, drives UPI Intent flow via Razorpay SDK.    | No Razorpay account needed — uses business's `key_id` and `order_id`. |
| **Razorpay** | Processes UPI payment via NPCI, generates cryptographic payment proof, routes settlement to business.          | N/A — third-party PSP; business onboards via Razorpay dashboard.  |

### Pattern Flow

```text
+------------+               +------------------+               +------------+
|  Platform  |               |    Business      |               |  Razorpay  |
+-----+------+               +--------+---------+               +------+-----+
      |                               |                                |
      |  1. GET /.well-known/ucp      |                                |
      |------------------------------>|                                |
      |                               |                                |
      |  2. Handler config            |                                |
      |  (key_id, env)                |                                |
      |<------------------------------|                                |
      |                               |                                |
      |  3. POST /checkout            |                                |
      |------------------------------>|  4. POST /v1/orders            |
      |                               |------------------------------->|
      |                               |  5. { order_id }              |
      |  6. Checkout response         |<-------------------------------|
      |  (key_id + razorpay_order_id) |                                |
      |<------------------------------|                                |
      |                               |                                |
      |  7. Init Razorpay SDK         |                                |
      |  8. Buyer selects UPI app     |                                |
      |  9. Platform opens upi://     |                                |
      |----------------------------------------------------+--------->|
      |  10. Buyer authorizes         |                    |           |
      |      in UPI app               |                    |           |
      |<---------------------------------------------------+-----------|
      |                               |                                |
      |  11. SDK callback:            |                                |
      |  { payment_id, order_id, sig }|                                |
      |                               |                                |
      |  12. POST checkout/complete   |                                |
      |  (upi_intent + credential)    |                                |
      |------------------------------>|  13. Verify HMAC signature     |
      |                               |  14. POST /payments/{id}/capture
      |                               |------------------------------->|
      |  15. Checkout complete        |  16. { captured: true }        |
      |<------------------------------|<-------------------------------|
```

---

## Business Integration

### Prerequisites

Before advertising this handler, businesses **MUST** complete:

1. **Create a Razorpay account** at
   [dashboard.razorpay.com](https://dashboard.razorpay.com).
2. **Complete KYC** to activate live payments.
3. **Retrieve API keys** from *Settings → API Keys*:
   * `key_id` — Public key (`rzp_live_*` or `rzp_test_*`). Safe to advertise
     in the UCP profile.
   * `key_secret` — Private key. **MUST remain on the business backend. MUST
     NOT appear in any UCP profile, checkout response, or client-side code.**
4. **Enable UPI** as an accepted payment method in the Razorpay dashboard
   (*Settings → Payment Methods → UPI*).
5. **Configure webhooks** (recommended) at *Settings → Webhooks* for
   `payment.authorized` and `payment.captured` events as a resilience layer.

**Prerequisites Output:**

| Field                   | Description                                                                                     |
| :---------------------- | :---------------------------------------------------------------------------------------------- |
| `identity.access_token` | Maps to Razorpay `merchant_id` (visible in the Dashboard). Used by Razorpay internally for routing. |
| `key_id`                | Public API key for SDK initialization and profile advertisement.                                |
| `key_secret`            | Private signing key for HMAC verification. Store in a secret manager; never expose externally.  |

### Handler Configuration

Businesses advertise support for this handler in their UCP profile's
`payment_handlers` registry at `/.well-known/ucp`.

#### Handler Schema

**Schema URL:** `https://razorpay.com/ucp/handlers/upi/schema.json`

| Config Variant    | Context              | Key Fields                                         |
| :---------------- | :------------------- | :------------------------------------------------- |
| `business_config` | Business discovery   | `key_id`, `environment`, `merchant_name`           |
| `platform_config` | Platform discovery   | `upi_apps` (optional constraint)                   |
| `response_config` | Checkout responses   | `key_id`, `razorpay_order_id`, `environment`       |

#### Business Config Fields

| Field           | Type   | Required | Description                                                         |
| :-------------- | :----- | :------- | :------------------------------------------------------------------ |
| `environment`   | string | Yes      | `sandbox` or `production`                                           |
| `key_id`        | string | Yes      | Public Razorpay API key (`rzp_test_*` or `rzp_live_*`)             |
| `merchant_name` | string | No       | Display name shown to the buyer during UPI payment                  |

#### Response Config Fields

| Field                | Type   | Required | Description                                                                       |
| :------------------- | :----- | :------- | :-------------------------------------------------------------------------------- |
| `environment`        | string | Yes      | `sandbox` or `production`                                                         |
| `key_id`             | string | Yes      | Public Razorpay key for SDK initialization                                        |
| `razorpay_order_id`  | string | Yes      | Razorpay Order ID for this checkout. Serves as the binding — credential must reference this. |
| `merchant_name`      | string | No       | Display name shown to the buyer during payment                                    |

#### Example Business Handler Declaration

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "payment_handlers": {
      "com.razorpay.upi": [
        {
          "id": "razorpay_upi_live",
          "version": "{{ ucp_version }}",
          "spec": "https://razorpay.com/ucp/handlers/upi",
          "schema": "https://razorpay.com/ucp/handlers/upi/schema.json",
          "available_instruments": [
            { "type": "upi_intent" }
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

### Creating the Razorpay Order

Before responding to a checkout request, the business backend **MUST** create a
Razorpay Order. The resulting `order_id` is the **binding** — it is included in
`response_config` and the platform must reference it verbatim in the payment
credential. The business **MUST** reject any credential whose `razorpay_order_id`
does not match the order created for this checkout.

**Request:**

```http
POST https://api.razorpay.com/v1/orders
Authorization: Basic base64(key_id:key_secret)
Content-Type: application/json

{
  "amount": 50000,
  "currency": "INR",
  "receipt": "checkout_abc123",
  "payment_capture": 0
}
```

| Field             | Description                                              |
| :---------------- | :------------------------------------------------------- |
| `amount`          | Amount in **paise** (1 INR = 100 paise)                  |
| `currency`        | Must be `"INR"` — UPI only supports INR                  |
| `receipt`         | The UCP `checkout.id` or internal order reference        |
| `payment_capture` | `0` = manual capture (recommended for UCP flow)          |

**Response:**

```json
{
  "id": "order_Abcdef1234XXXX",
  "entity": "order",
  "amount": 50000,
  "currency": "INR",
  "receipt": "checkout_abc123",
  "status": "created"
}
```

Include `id` as `razorpay_order_id` in the checkout `response_config`.

### Processing Payments

Upon receiving a checkout completion with a `com.razorpay.upi` instrument,
businesses **MUST**:

1. **Validate handler.** Confirm `instrument.handler_id` matches a declared
   `com.razorpay.upi` handler.
2. **Ensure idempotency.** If the `checkout_id` was already processed, return
   the previous result without re-capturing.
3. **Verify binding.** Confirm `credential.razorpay_order_id` exactly matches
   the `razorpay_order_id` created for this checkout. Reject if they differ —
   this indicates a misrouted or replayed credential.
4. **Verify signature.** Compute and compare:

   ```
   expected = HMAC_SHA256(
     razorpay_order_id + "|" + razorpay_payment_id,
     key_secret
   )
   assert constant_time_equals(expected, credential.razorpay_signature)
   ```

   Use a constant-time comparison to prevent timing attacks.

5. **Check payment status.** Query `GET /v1/payments/{razorpay_payment_id}` and
   confirm `status == "authorized"`.
6. **Capture payment.** Call `POST /v1/payments/{razorpay_payment_id}/capture`
   with the exact checkout total in paise.
7. **Return response.** Respond with the finalized checkout state.

**Capture Request:**

```http
POST https://api.razorpay.com/v1/payments/{razorpay_payment_id}/capture
Authorization: Basic base64(key_id:key_secret)
Content-Type: application/json

{
  "amount": 50000,
  "currency": "INR"
}
```

The `amount` **MUST** equal the checkout total. Razorpay will reject captures
with a mismatched amount.

#### Error Mapping

| Razorpay Condition                   | UCP Error            | Action                                          |
| :----------------------------------- | :------------------- | :---------------------------------------------- |
| Payment `status == "failed"`         | `Declined`           | Surface failure to buyer; allow retry           |
| Signature mismatch                   | `Invalid Credential` | Reject immediately; do not capture              |
| `razorpay_order_id` mismatch         | `Invalid Credential` | Reject immediately; possible replay attempt     |
| Payment already captured             | `Already Processed`  | Return previous result (idempotency)            |
| Razorpay API 5xx / timeout           | `Network Error`      | Safe to retry capture (idempotent by order_id)  |
| Currency is not `INR`                | `Unsupported`        | Reject at handler selection stage               |

---

## Platform Integration

### Prerequisites

Platforms do **not** need a Razorpay account. Everything required to drive the
UPI Intent flow is provided by the business in the checkout `response_config`:
`key_id` and `razorpay_order_id`.

Platforms **MUST** be capable of:

1. Loading the **Razorpay Standard SDK** (web) or the Razorpay Android/iOS SDK
   (native), initialized with the business's `key_id` and `razorpay_order_id`.
2. Handling the SDK's asynchronous `handler` callback, which fires after the
   buyer authorizes payment in their UPI app.

### Handler Configuration

Platforms advertise UPI Intent support in their UCP profile using
`platform_config`.

#### Platform Config Fields

| Field      | Type            | Required | Description                                                           |
| :--------- | :-------------- | :------- | :-------------------------------------------------------------------- |
| `upi_apps` | array of string | No       | UPI apps the platform can deep-link to. Absent = supports all apps.   |

#### Example Platform Handler Declaration

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "payment_handlers": {
      "com.razorpay.upi": [
        {
          "id": "platform_razorpay_upi",
          "version": "{{ ucp_version }}",
          "spec": "https://razorpay.com/ucp/handlers/upi",
          "schema": "https://razorpay.com/ucp/handlers/upi/schema.json",
          "available_instruments": [
            { "type": "upi_intent" }
          ],
          "config": {
            "upi_apps": ["gpay", "phonepe", "paytm", "bhim"]
          }
        }
      ]
    }
  }
}
```

### Payment Protocol

#### Step 1: Discover Handler

The platform identifies `com.razorpay.upi` in the business's UCP profile and
reads the advertised config.

```json
{
  "ucp": {
    "payment_handlers": {
      "com.razorpay.upi": [
        {
          "id": "razorpay_upi_live",
          "version": "{{ ucp_version }}",
          "available_instruments": [
            { "type": "upi_intent" }
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

#### Step 2: Create / Fetch Checkout

The platform creates or fetches the checkout session. The business backend
creates a Razorpay Order and includes its ID in `response_config`. The platform
**MUST** use this `razorpay_order_id` verbatim when initializing the SDK.

```json
{
  "id": "checkout_abc123",
  "status": "incomplete",
  "currency": "INR",
  "totals": [
    { "type": "subtotal", "amount": 49000 },
    { "type": "tax",      "amount": 1000  },
    { "type": "total",    "amount": 50000 }
  ],
  "ucp": {
    "payment_handlers": {
      "com.razorpay.upi": [
        {
          "id": "razorpay_upi_live",
          "version": "{{ ucp_version }}",
          "available_instruments": [
            { "type": "upi_intent" }
          ],
          "config": {
            "environment": "production",
            "key_id": "rzp_live_XXXXXXXXXXXXXXX",
            "razorpay_order_id": "order_Abcdef1234XXXX",
            "merchant_name": "Acme Store"
          }
        }
      ]
    }
  }
}
```

#### Step 3: Initiate UPI Intent via Razorpay SDK

The platform initializes the Razorpay SDK with `key_id` and `razorpay_order_id`
from `response_config`. The checkout total is read from the `totals` array
(entry with `type == "total"`).

```javascript
const handlerConfig = checkout.ucp.payment_handlers["com.razorpay.upi"][0].config;
const totalAmount   = checkout.totals.find(t => t.type === "total").amount;

const rzp = new Razorpay({
  key:      handlerConfig.key_id,
  order_id: handlerConfig.razorpay_order_id,
  amount:   totalAmount,              // in paise, from checkout totals
  currency: "INR",
  name:     handlerConfig.merchant_name,
  method:   "upi",
  upi: { flow: "intent" },
  handler: function(response) {
    // Payment authorized — proceed to Step 4
    completeCheckout(response);
  },
  modal: {
    ondismiss: function() {
      // Buyer cancelled — surface error and allow retry
    }
  }
});
rzp.open();
```

The SDK presents the buyer with a list of installed UPI apps. The buyer selects
an app, the platform deep-links via `upi://`, and the buyer authorizes in their
chosen UPI app. Upon authorization, the `handler` callback fires with:

```json
{
  "razorpay_payment_id": "pay_Abcdef1234XXXX",
  "razorpay_order_id":   "order_Abcdef1234XXXX",
  "razorpay_signature":  "a9f3...e7c1"
}
```

#### Step 4: Complete Checkout

The platform submits the checkout with the `upi_intent` instrument and the
payment proof credential.

```http
POST /checkout-sessions/{checkout_id}/complete
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json

{
  "payment": {
    "instruments": [
      {
        "id": "instr_1",
        "handler_id": "razorpay_upi_live",
        "type": "upi_intent",
        "display": {
          "upi_app": "gpay",
          "description": "UPI — Google Pay"
        },
        "credential": {
          "type": "razorpay_payment_proof",
          "razorpay_payment_id": "pay_Abcdef1234XXXX",
          "razorpay_order_id":   "order_Abcdef1234XXXX",
          "razorpay_signature":  "a9f3...e7c1"
        }
      }
    ]
  }
}
```

---

## Security Considerations

| Requirement                   | Description                                                                                                                                                     |
| :---------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **key_secret never exposed**  | The `key_secret` **MUST** remain on the business backend. It **MUST NOT** appear in UCP profiles, checkout responses, API responses, or any client-side code.  |
| **Binding verification**      | The business **MUST** verify `credential.razorpay_order_id` matches the `razorpay_order_id` created for this checkout before accepting or capturing.           |
| **Signature verification**    | The business **MUST** verify `razorpay_signature` using HMAC-SHA256 before calling capture. An invalid signature **MUST** be rejected immediately.             |
| **Constant-time comparison**  | Signature comparison **MUST** use a constant-time function (e.g., `hmac.compare_digest`) to prevent timing side-channel attacks.                               |
| **Idempotency**               | Businesses **MUST** implement idempotent capture: if the `checkout_id` was already processed, return the previous result without re-capturing.                  |
| **Payment status check**      | The business **SHOULD** query `GET /v1/payments/{id}` to confirm `status == "authorized"` before capture, to guard against already-captured or failed payments. |
| **Amount validation**         | The capture `amount` **MUST** match the checkout total. Razorpay will reject captures with a mismatched amount.                                                 |
| **INR only**                  | UPI via Razorpay only supports `INR`. Businesses **MUST** not advertise this handler for non-INR checkouts.                                                     |
| **TLS/HTTPS only**            | All traffic to Razorpay APIs and to the business's UCP endpoints **MUST** use TLS 1.2 or higher.                                                               |

---

## Testing

Razorpay provides a full sandbox environment for end-to-end testing without
using real money.

### Setup

1. Toggle to **Test Mode** in the [Razorpay Dashboard](https://dashboard.razorpay.com).
2. From *Settings → API Keys*, generate test keys starting with `rzp_test_`.
3. Use `environment: "sandbox"` in the business config.

### Simulating UPI Intent in Sandbox

With `rzp_test_*` keys, the Razorpay Standard SDK presents a **simulated UPI
app picker**. Selecting any app triggers a successful test payment. The SDK
callback fires with test `razorpay_payment_id`, `razorpay_order_id`, and
`razorpay_signature` values.

### End-to-End Test Checklist

- [ ] Business profile at `/.well-known/ucp` declares `com.razorpay.upi` with
      `key_id` prefixed `rzp_test_` and `environment: "sandbox"`.
- [ ] Checkout creation triggers `POST /v1/orders` to Razorpay in test mode;
      the resulting `order_id` is returned in `response_config`.
- [ ] Platform discovers handler and reads `key_id` + `razorpay_order_id` from
      `response_config`.
- [ ] Platform initializes Razorpay SDK with these values; SDK opens simulated
      intent flow.
- [ ] SDK callback fires with `{razorpay_payment_id, razorpay_order_id, razorpay_signature}`.
- [ ] `razorpay_order_id` in credential matches the order created for the checkout.
- [ ] Business backend computes HMAC-SHA256 and verifies `razorpay_signature`.
- [ ] Capture succeeds via `POST /v1/payments/{id}/capture`.
- [ ] Idempotent re-submission of the same `checkout_id` returns the previous
      result without re-capturing.
- [ ] Webhook `payment.captured` fires and is verified using the webhook secret.

### Signature Verification Reference

```python
import hmac
import hashlib

def verify_razorpay_signature(order_id: str, payment_id: str, signature: str, key_secret: str) -> bool:
    message = f"{order_id}|{payment_id}"
    expected = hmac.new(
        key_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    # constant-time comparison prevents timing attacks
    return hmac.compare_digest(expected, signature)
```

---

## References

* **Handler Spec:** `https://razorpay.com/ucp/handlers/upi`
* **Handler Schema:** `https://razorpay.com/ucp/handlers/upi/schema.json`
* **Razorpay Orders API:** `https://razorpay.com/docs/api/orders/`
* **Razorpay Payments API:** `https://razorpay.com/docs/api/payments/`
* **Razorpay UPI Docs:** `https://razorpay.com/docs/payments/payment-methods/upi/`
* **Razorpay Standard Checkout:** `https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/`
* **UCP Payment Handler Guide:** [payment-handler-guide.md](payment-handler-guide.md)
* **UCP Tokenization Guide:** [tokenization-guide.md](tokenization-guide.md)
