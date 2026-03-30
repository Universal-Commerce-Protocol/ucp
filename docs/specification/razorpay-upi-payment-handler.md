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

This handler enables **UPI Intent** payments in India via
[Razorpay](https://razorpay.com) as the payment service provider. UPI
(Unified Payments Interface) is a real-time bank-to-bank payment system
managed by NPCI (National Payments Corporation of India) with 20B+ monthly
transactions and 500M+ active users.

**UPI Intent flow** — The platform submits a Complete Checkout request with a
`upi_intent` instrument and no credential. The business creates a Razorpay
payment order, receives an NPCI-compliant `upi://` intent URI, and returns it
to the platform in a `requires_escalation` response with error code
`requires_buyer_authentication`. The platform deep-links the buyer into their
UPI app (Google Pay, PhonePe, Paytm, BHIM, etc.). The buyer authorizes in the
app, Razorpay notifies the business via webhook, and the business marks the
checkout `completed`. The platform polls to confirm.

### Key Benefits

* **No Razorpay SDK on platform** — The platform only needs to open a
  `upi://` deep link or render a QR code. No PSP SDK required.
* **PSP-agnostic instrument** — The `upi_intent` instrument and credential
  are NPCI-standard schemas; any UPI PSP can implement this handler.
* **Zero PCI-DSS scope** — UPI is VPA-based. No card numbers involved.
* **QR fallback included** — `qr_code_data` in the credential supports
  desktop and web contexts where `upi://` launching is unavailable.
* **Backward-compatible escalation** — Platforms that do not implement this
  handler fall back to `continue_url` automatically.

### Integration Guide

| Participant  | Integration Section                           |
| :----------- | :-------------------------------------------- |
| **Business** | [Business Integration](#business-integration) |
| **Platform** | [Platform Integration](#platform-integration) |

---

## Participants

> **Note on Terminology:**
> This specification refers to the Razorpay merchant account holder as the
> **"business."** Razorpay API fields use `merchant_id` internally — this
> maps to `PaymentIdentity.access_token` after onboarding.

| Participant  | Role                                                                                                                                       | Prerequisites                                                   |
| :----------- | :----------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------- |
| **Business** | Receives Complete Checkout, creates Razorpay order + payment, returns `intent_uri` credential, confirms payment via webhook, marks complete. | Yes — Razorpay account, `key_id`, `key_secret`.                  |
| **Platform** | Submits Complete Checkout with `upi_intent` instrument, receives escalation with credential, executes deep link, polls for completion.      | No Razorpay account needed — only `upi://` deep-link capability. |
| **Razorpay** | Creates payment order, generates NPCI-compliant intent URI, routes UPI transaction via NPCI, notifies business via webhook.                | N/A — third-party PSP; business onboards via Razorpay dashboard. |

### Pattern Flow

```text
+------------+               +------------------+               +------------+
|  Platform  |               |    Business      |               |  Razorpay  |
+-----+------+               +--------+---------+               +------+-----+
      |                               |                                |
      |  1. GET /.well-known/ucp      |                                |
      |------------------------------>|                                |
      |  2. Handler config            |                                |
      |  (env, merchant_name)         |                                |
      |<------------------------------|                                |
      |                               |                                |
      |  3. POST /checkout (create)   |                                |
      |------------------------------>|                                |
      |  4. Checkout response         |                                |
      |  (upi_intent available,       |                                |
      |   no credential yet)          |                                |
      |<------------------------------|                                |
      |                               |                                |
      |  5. POST checkout/complete    |                                |
      |  (upi_intent instrument,      |                                |
      |   NO credential)              |                                |
      |------------------------------>|  6. POST /v1/orders            |
      |                               |------------------------------->|
      |                               |  7. POST /v1/payments          |
      |                               |------------------------------->|
      |                               |  8. { intent_uri, tr }        |
      |  9. requires_escalation       |<-------------------------------|
      |  code: requires_buyer_        |                                |
      |    authentication             |                                |
      |  credential: { intent_uri,   |                                |
      |    qr_code_data, expires_at } |                                |
      |  continue_url: https://...    |                                |
      |<------------------------------|                                |
      |                               |                                |
      |  10. Platform implements      |                                |
      |   handler?                    |                                |
      |                               |                                |
      |   YES: open upi:// deep link  |                                |
      |   or render QR code           |                                |
      |   (buyer authorizes in app)   |                                |
      |                               |  11. Webhook: payment.captured |
      |                               |<-------------------------------|
      |                               |  12. Mark checkout completed   |
      |                               |                                |
      |   NO: redirect to             |                                |
      |   continue_url                |                                |
      |                               |                                |
      |  13. GET /checkout (poll)     |                                |
      |------------------------------>|                                |
      |  14. status: completed        |                                |
      |<------------------------------|                                |
```

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
4. **Enable UPI** as an accepted payment method in the Razorpay dashboard
   (*Settings → Payment Methods → UPI*).
5. **Configure webhooks** at *Settings → Webhooks* for the
   `payment.captured` event. This is the mechanism by which the business
   learns the payment was authorized and can mark the checkout `completed`.

**Prerequisites Output:**

| Field                   | Description                                                                                    |
| :---------------------- | :--------------------------------------------------------------------------------------------- |
| `identity.access_token` | Maps to Razorpay `merchant_id` (visible in Dashboard).                                         |
| `key_id`                | Public API key for profile advertisement.                                                      |
| `key_secret`            | Private key for Razorpay API calls. Store in a secret manager; never expose externally.        |
| webhook secret          | Secret for verifying `X-Razorpay-Signature` on incoming webhook events.                       |

### Handler Configuration

Businesses advertise support for this handler in their UCP profile's
`payment_handlers` registry at `/.well-known/ucp`.

#### Handler Schema

**Schema URL:** `https://razorpay.com/ucp/handlers/upi/schema.json`

| Config Variant    | Context              | Key Fields                          |
| :---------------- | :------------------- | :---------------------------------- |
| `business_config` | Business discovery   | `key_id`, `environment`, `merchant_name` |
| `platform_config` | Platform discovery   | `upi_apps` (optional)               |
| `response_config` | Checkout responses   | `environment`, `merchant_name`      |

#### Business Config Fields

| Field           | Type   | Required | Description                                                     |
| :-------------- | :----- | :------- | :-------------------------------------------------------------- |
| `environment`   | string | Yes      | `sandbox` or `production`                                       |
| `key_id`        | string | Yes      | Public Razorpay API key                                         |
| `merchant_name` | string | No       | Display name shown to the buyer during payment                  |

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

### Processing Payments

When the business receives a Complete Checkout request with a `upi_intent`
instrument and no credential, it **MUST**:

1. **Validate handler.** Confirm `instrument.handler_id` matches a declared
   `com.razorpay.upi` handler and `instrument.type == "upi_intent"`.

2. **Ensure idempotency.** If this `checkout_id` already has a Razorpay
   order and payment, return the existing escalation response.

3. **Create a Razorpay Order** (`POST /v1/orders`):

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

   | Field             | Description                                           |
   | :---------------- | :---------------------------------------------------- |
   | `amount`          | Amount in **paise** (1 INR = 100 paise)               |
   | `currency`        | Must be `"INR"` — UPI only supports INR               |
   | `receipt`         | The UCP `checkout.id` or internal order reference     |
   | `payment_capture` | `0` = manual capture (business captures after webhook)|

   Response: `{ "id": "order_Abcdef1234XXXX", ... }`

4. **Create a Razorpay UPI Intent Payment** (`POST /v1/payments/create/upi`
   or equivalent SDK-generated intent):

   Razorpay returns an NPCI-compliant `intent_uri`:
   ```
   upi://pay?pa=merchant@rzp&pn=Acme+Store&tr=TXN123456&am=500.00&cu=INR
   ```

5. **Return `requires_escalation`** with `requires_buyer_authentication`:

   ```json
   {
     "status": "requires_escalation",
     "continue_url": "https://business.example.com/checkout-sessions/checkout_abc123",
     "messages": [
       {
         "type": "error",
         "code": "requires_buyer_authentication",
         "severity": "requires_buyer_review",
         "content": "Buyer must authorize this payment via UPI",
         "path": "$.payment.instruments[0]"
       }
     ],
     "payment": {
       "instruments": [
         {
           "id": "instr_1",
           "handler_id": "razorpay_upi_live",
           "type": "upi_intent",
           "selected": true,
           "display": {
             "name": "Pay via UPI",
             "logo": "https://razorpay.com/assets/upi-logo.png"
           },
           "credential": {
             "type": "upi_intent",
             "intent_uri": "upi://pay?pa=merchant@rzp&pn=Acme+Store&tr=TXN123456&am=500.00&cu=INR",
             "transaction_reference": "TXN123456",
             "qr_code_data": "data:image/png;base64,iVBORw0KGgo...",
             "qr_code_string": "upi://pay?pa=merchant@rzp&pn=Acme+Store&tr=TXN123456&am=500.00&cu=INR",
             "expires_at": "2026-03-27T10:20:00Z"
           }
         }
       ]
     }
   }
   ```

6. **Receive Razorpay webhook.** On `payment.captured`:
   - Verify `X-Razorpay-Signature` using `HMAC_SHA256(webhook_body, webhook_secret)`.
   - Confirm `payment.order_id` matches the order created for this checkout.
   - Capture the payment (`POST /v1/payments/{id}/capture`) if not auto-captured.
   - Mark the UCP checkout as `completed`.

#### Error Mapping

| Razorpay Condition               | UCP Error            | Action                                      |
| :------------------------------- | :------------------- | :------------------------------------------ |
| Order/payment creation fails     | `payment_failed`     | Return error; platform may retry             |
| Webhook `payment.failed` event   | `payment_failed`     | Update checkout to `requires_escalation` again or `canceled` |
| `intent_uri` expires (>15 min)  | `payment_failed`     | Business must create a new order             |
| Currency is not `INR`            | `payment_failed`     | Reject at handler selection stage            |

---

## Platform Integration

### Prerequisites

Platforms do **not** need a Razorpay account. The platform only needs to:

1. Be capable of opening `upi://` deep links on the buyer's device (iOS,
   Android), or rendering a QR code from `qr_code_data` / `qr_code_string`
   on desktop/web.
2. Handle the `requires_buyer_authentication` error code in the
   `requires_escalation` response.

### Handler Configuration

Platforms advertise UPI Intent support in their UCP profile.

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
          ]
        }
      ]
    }
  }
}
```

### Payment Protocol

#### Step 1: Discover Handler

The platform identifies `com.razorpay.upi` in the business's profile and
confirms `upi_intent` in `available_instruments`.

#### Step 2: Create / Fetch Checkout

The platform creates or fetches the checkout session. The business returns
`response_config` with `environment` and `merchant_name`.

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
          "available_instruments": [{ "type": "upi_intent" }],
          "config": {
            "environment": "production",
            "merchant_name": "Acme Store"
          }
        }
      ]
    }
  }
}
```

#### Step 3: Submit Complete Checkout (no credential)

The platform submits Complete Checkout with the `upi_intent` instrument.
**No credential is included** — the business generates it server-side.

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
          "name": "Pay via UPI"
        }
      }
    ]
  }
}
```

#### Step 4: Handle Escalation Response

The business responds with `requires_escalation` and
`requires_buyer_authentication`. The credential contains the `intent_uri`.

The platform checks the error code and whether it implements the handler:

```javascript
const response = await completeCheckout(checkoutId, instrument);

if (response.status === "requires_escalation") {
  const authError = response.messages.find(
    m => m.code === "requires_buyer_authentication"
  );
  const instrument = response.payment?.instruments?.[0];
  const credential = instrument?.credential;

  if (authError && credential?.type === "upi_intent" && platformImplementsHandler) {
    // Check expiry
    if (credential.expires_at && new Date(credential.expires_at) < new Date()) {
      fallbackToContinueUrl(response.continue_url);
      return;
    }

    // Mobile: launch deep link
    if (isMobile()) {
      window.location.href = credential.intent_uri;
    } else {
      // Desktop: render QR code
      renderQRCode(credential.qr_code_data ?? credential.qr_code_string);
    }

    // Poll for completion
    pollCheckoutStatus(checkoutId);
  } else {
    // Handler not implemented or credential missing — fall back
    fallbackToContinueUrl(response.continue_url);
  }
}
```

#### Step 5: Poll for Completion

After executing the intent, the platform polls `GET /checkout-sessions/{id}`
until `status` is `completed` or `canceled`.

```javascript
async function pollCheckoutStatus(checkoutId) {
  const POLL_INTERVAL_MS = 3000;
  const MAX_POLLS = 20; // ~1 minute

  for (let i = 0; i < MAX_POLLS; i++) {
    await sleep(POLL_INTERVAL_MS);
    const checkout = await getCheckout(checkoutId);

    if (checkout.status === "completed") {
      showSuccessScreen(checkout);
      return;
    }
    if (checkout.status === "canceled") {
      showFailureScreen();
      return;
    }
  }
  // Timeout — fall back to continue_url
  fallbackToContinueUrl(response.continue_url);
}
```

---

## Security Considerations

| Requirement                     | Description                                                                                                                                                  |
| :------------------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **key_secret never exposed**    | The `key_secret` **MUST** remain on the business backend. **MUST NOT** appear in UCP profiles, responses, or any client-side code.                           |
| **Webhook signature**           | The business **MUST** verify `X-Razorpay-Signature` on every webhook using `HMAC_SHA256(body, webhook_secret)` before updating checkout state.               |
| **Order-to-checkout binding**   | The business **MUST** verify that the Razorpay `payment.order_id` in the webhook matches the order created for this checkout before marking it complete.     |
| **Idempotency**                 | If a `checkout_id` already has a payment order, return the existing escalation response without creating a new order.                                         |
| **Credential expiry**           | The platform **MUST NOT** execute an `intent_uri` after `expires_at`. It **MUST** fall back to `continue_url` if the credential has expired.                 |
| **continue_url fallback**       | The platform **MUST** fall back to `continue_url` if: the handler is not implemented, `upi://` cannot be launched, the credential is expired, or polling times out. |
| **INR only**                    | UPI only supports INR. Businesses **MUST NOT** advertise this handler for non-INR checkouts.                                                                  |
| **TLS/HTTPS only**              | All traffic to Razorpay APIs and UCP endpoints **MUST** use TLS 1.2 or higher.                                                                               |
| **Amount validation**           | The Razorpay order `amount` **MUST** equal the checkout total in paise. Razorpay will reject payments with a mismatched amount.                              |

---

## Testing

Razorpay provides a full sandbox environment for end-to-end testing.

### Setup

1. Toggle to **Test Mode** in the [Razorpay Dashboard](https://dashboard.razorpay.com).
2. From *Settings → API Keys*, generate test keys (`rzp_test_*`).
3. Use `environment: "sandbox"` in the business config.

### Sandbox Behavior

In test mode, Razorpay generates real-format `intent_uri` values and
`order_id`/`payment_id` pairs. Webhooks fire normally. No real money moves.

### End-to-End Test Checklist

- [ ] Business profile at `/.well-known/ucp` declares `com.razorpay.upi` with `rzp_test_*` key and `environment: "sandbox"`.
- [ ] Platform submits Complete Checkout with `upi_intent` instrument and no `credential`.
- [ ] Business creates Razorpay order via `POST /v1/orders` in test mode.
- [ ] Business returns `requires_escalation` with `requires_buyer_authentication` + `upi_intent_credential`.
- [ ] Escalation response includes `continue_url` (always required).
- [ ] `credential.intent_uri` matches pattern `upi://pay?...pa=...`.
- [ ] `credential.transaction_reference` ≤ 35 characters.
- [ ] `credential.expires_at` is in the future.
- [ ] Platform detects `requires_buyer_authentication` and executes `intent_uri`.
- [ ] Business receives `payment.captured` webhook; verifies `X-Razorpay-Signature`.
- [ ] Business marks checkout `completed`.
- [ ] Platform polling returns `status: completed`.
- [ ] Platform falls back to `continue_url` when credential is expired.
- [ ] Platform falls back to `continue_url` when handler is not implemented.

### Webhook Signature Verification Reference

```python
import hmac
import hashlib

def verify_razorpay_webhook(body: bytes, signature: str, webhook_secret: str) -> bool:
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## Applicability Beyond Razorpay

The `requires_buyer_authentication` error code and `upi_intent` credential
pattern are PSP-agnostic. Any UPI PSP (PayU, Cashfree, PayTM, Juspay) that
generates NPCI-compliant `upi://` intent URIs can implement this same handler.
The `upi_intent_instrument` and `upi_intent_credential` schemas are defined in
the UCP base schema space for this reason.

The broader `requires_buyer_authentication` pattern also applies to other
real-time payment systems: PIX (Brazil), PayNow (Singapore), PromptPay
(Thailand), and any BNPL or wallet flow where credential execution is
platform-side but credential generation is business/PSP-side.

---

## References

* **Handler Spec:** `https://razorpay.com/ucp/handlers/upi`
* **Handler Schema:** `https://razorpay.com/ucp/handlers/upi/schema.json`
* **UPI Intent Instrument Schema:** [upi_intent_instrument.json](site:schemas/shopping/types/upi_intent_instrument.json)
* **UPI Intent Credential Schema:** [upi_intent_credential.json](site:schemas/shopping/types/upi_intent_credential.json)
* **Razorpay Orders API:** `https://razorpay.com/docs/api/orders/`
* **Razorpay Payments API:** `https://razorpay.com/docs/api/payments/`
* **Razorpay UPI Docs:** `https://razorpay.com/docs/payments/payment-methods/upi/`
* **NPCI UPI Linking Specification:** `https://www.npci.org.in/what-we-do/upi/product-overview`
* **UCP Payment Handler Guide:** [payment-handler-guide.md](payment-handler-guide.md)
* **UCP Checkout Specification:** [checkout.md](checkout.md)
