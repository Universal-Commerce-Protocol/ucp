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

# UPI Intent Payment Handler

* **Handler Name:** `com.razorpay.upi_intent`
* **Type:** Payment Handler Example
* **Contributed by:** Razorpay

## Introduction

This example demonstrates a payment handler for **UPI Intent** — India's
device-native payment method that routes payments directly between bank
accounts over the NPCI UPI rail. The business generates an NPCI-compliant
intent URI via their PSP (e.g., Razorpay), returns it inside a
`requires_escalation` response, and the platform launches it to the buyer's
device. No card networks, no tokenization, and no platform-managed app
selection are involved.

UPI Intent processes 14+ billion monthly transactions in India and is
supported by all major UPI apps (Google Pay, PhonePe, Paytm, BHIM, and
200+ bank apps). Per NPCI mandate, the device OS presents the app chooser —
platforms MUST NOT hardcode or filter which UPI apps appear.

This flow reuses UCP's existing `requires_escalation` mechanism. Platforms
that already handle `requires_escalation` support this handler with no
additional protocol changes.

### Key Benefits

* **No credential exchange:** No card tokens, no sensitive data flows
  through the platform — the PSP handles the payment rail entirely.
* **OS-native app selection:** Android/iOS presents all installed UPI apps
  via the system chooser. Platforms do not control or restrict app choice.
* **QR fallback built-in:** The credential carries a QR code for desktop
  and web contexts where launching `upi://` is not supported.
* **Standard escalation:** Uses existing UCP `requires_escalation` +
  `continue_url` + polling — no new platform behavior required.

### Quick Start

| If you are a...                        | Start here                                    |
| :------------------------------------- | :-------------------------------------------- |
| **Business** accepting this handler    | [Business Integration](#business-integration) |
| **Platform** implementing this handler | [Platform Integration](#platform-integration) |

---

## Participants

| Participant  | Role                                                                             | Prerequisites                                           |
| :----------- | :------------------------------------------------------------------------------- | :------------------------------------------------------ |
| **Business** | Registers with PSP, generates intent URI, returns escalation response            | Yes — active Razorpay account with UPI enabled          |
| **PSP**      | Creates payment order, generates NPCI-compliant intent URI, delivers webhook     | Yes — Razorpay or equivalent NPCI-certified PSP         |
| **Platform** | Discovers handler, submits Complete Checkout, launches intent URI or displays QR | No — reuses existing `requires_escalation` handling     |
| **Buyer**    | Selects UPI app (OS chooser), authorizes payment in their bank app               | No — uses any installed UPI app; no platform enrollment |

### Payment Flow

```text
+------------+          +----------+           +---------+          +-------+
|  Business  |          |   PSP    |           | Platform|          | Buyer |
+-----+------+          +----+-----+           +----+----+          +---+---+
      |                      |                      |                   |
      |  1. Advertise upi_intent instrument in Create Checkout response |
      |<---------------------------------------------------------------------|
      |                      |                      |                   |
      |  2. Platform calls Complete Checkout         |                   |
      |<---------------------------------------------|                   |
      |                      |                      |                   |
      |  3. Create payment order                     |                   |
      |--------------------->|                      |                   |
      |                      |                      |                   |
      |  4. Intent URI + transaction_reference       |                   |
      |<---------------------|                      |                   |
      |                      |                      |                   |
      |  5. requires_escalation + credential (intent_uri, qr_code_data) |
      |--------------------------------------------->|                   |
      |                      |                      |                   |
      |                      |          6. Launch intent URI (mobile)   |
      |                      |             or display QR (desktop)      |
      |                      |          -------------------------------->|
      |                      |                      |                   |
      |                      |                 7. Buyer authorizes in UPI app
      |                      |<-----------------------------------------------------|
      |                      |                      |                   |
      |  8. PSP webhook (payment confirmed)         |                   |
      |<---------------------|                      |                   |
      |                      |                      |                   |
      |  9. Platform polls → Business confirms completed                |
      |<---------------------------------------------|                   |
```

---

## Business Integration

### Prerequisites

Before advertising this handler, businesses **MUST** complete:

1. **Create a Razorpay account** and enable UPI as a payment method in the
   Razorpay Dashboard.
2. **Obtain API credentials** — `key_id` and `key_secret` from the Razorpay
   Dashboard (Settings → API Keys).
3. **Configure a webhook endpoint** in the Razorpay Dashboard to receive
   `payment.captured` and `payment.failed` events, and record the webhook
   secret for HMAC verification.

**Prerequisites Output:**

| Field              | Description                                             |
| :----------------- | :------------------------------------------------------ |
| `key_id`           | Razorpay API key identifier (e.g., `rzp_live_abc123`)   |
| `key_secret`       | Razorpay API key secret — **never expose to platforms** |
| `webhook_secret`   | Shared secret for HMAC-SHA256 webhook signature verification |

### Handler Configuration

Businesses advertise the handler in their UCP profile's `payment_handlers`
registry. The instrument type `upi_intent` signals to the platform that UPI
Intent deep link payments are available. No constraints are supported —
the OS determines available apps.

#### Business Config Fields

| Field          | Type   | Required | Description                                              |
| :------------- | :----- | :------- | :------------------------------------------------------- |
| `environment`  | string | Yes      | `sandbox` or `production`                                |
| `merchant_id`  | string | Yes      | Razorpay merchant identifier                             |
| `display_name` | string | No       | Label shown in platform UI (e.g., `"Pay via UPI"`)       |
| `display_logo` | string | No       | HTTPS URL to UPI logo for platform UI                    |

#### Example Business Handler Declaration

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "payment_handlers": {
      "com.razorpay.upi_intent": [
        {
          "id": "razorpay_upi",
          "version": "{{ ucp_version }}",
          "spec": "https://razorpay.com/ucp/upi-intent-handler.json",
          "schema": "https://razorpay.com/ucp/upi-intent-handler/schema.json",
          "available_instruments": [
            {
              "type": "upi_intent"
            }
          ],
          "config": {
            "environment": "production",
            "merchant_id": "merchant_abc123",
            "display_name": "Pay via UPI",
            "display_logo": "https://cdn.razorpay.com/logos/upi.png"
          }
        }
      ]
    }
  }
}
```

### Processing Payments

When the platform submits `POST /checkout-sessions/{checkout_id}/complete`
with a `upi_intent` instrument, the business **MUST**:

1. **Validate the instrument:** Confirm `instrument.handler_id` matches the
   advertised handler ID (`razorpay_upi`).
2. **Ensure idempotency:** If the `checkout_id` matches a prior request,
   return the previous response immediately without re-creating the order.
3. **Create a Razorpay order:**

    ```bash
    POST https://api.razorpay.com/v1/orders
    Authorization: Basic base64(key_id:key_secret)
    Content-Type: application/json

    {
      "amount": 57700,
      "currency": "INR",
      "receipt": "checkout_abc123",
      "payment_capture": 1
    }
    ```

    Response fields used downstream:

    | Field    | Description                                       |
    | :------- | :------------------------------------------------ |
    | `id`     | Razorpay order ID — used to generate intent URI   |
    | `amount` | Amount in paise — verify matches checkout total   |

4. **Generate the NPCI-compliant intent URI:**

    Construct the URI using your VPA, display name, amount, and the
    Razorpay order ID as the transaction reference (`tr`):

    ```
    upi://pay?pa={vpa}&pn={display_name}&am={amount_decimal}&cu=INR
              &tr={razorpay_order_id}&tn={note}&mc={mcc}&mode=04
    ```

    **Example:**

    ```
    upi://pay?pa=bigbasket@icici&pn=BigBasket&am=577.00&cu=INR
              &tr=order_Abc123XYZ&tn=Order%20checkout_abc123&mc=5411&mode=04
    ```

    URI encoding rules (per NPCI spec and RFC 3986):

    * Spaces → `%20` (never `+`)
    * `pn`, `tn` values must be percent-encoded
    * `am` must be decimal with two decimal places (e.g., `577.00`)

5. **Optionally generate a QR code image** (base64 PNG or SVG data URI)
   encoding the same `intent_uri`. Return it in `qr_code_data` to support
   desktop/web buyers who cannot launch `upi://` schemes.

6. **Return `requires_escalation`** with the credential:

    ```json
    {
      "status": "requires_escalation",
      "continue_url": "https://merchant.example.com/checkout/checkout_abc123",
      "payment": {
        "instruments": [
          {
            "id": "instr_1",
            "handler_id": "razorpay_upi",
            "type": "upi_intent",
            "credential": {
              "type": "upi_intent",
              "intent_uri": "upi://pay?pa=bigbasket@icici&pn=BigBasket&am=577.00&cu=INR&tr=order_Abc123XYZ&tn=Order%20checkout_abc123&mc=5411&mode=04",
              "transaction_reference": "order_Abc123XYZ",
              "qr_code_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
              "qr_code_string": "upi://pay?pa=bigbasket@icici&pn=BigBasket&am=577.00&cu=INR&tr=order_Abc123XYZ&tn=Order%20checkout_abc123&mc=5411&mode=04",
              "expires_at": "2026-01-29T10:20:00Z"
            }
          }
        ]
      }
    }
    ```

7. **Process the PSP webhook** when the buyer completes payment:

    ```bash
    POST {webhook_endpoint}
    X-Razorpay-Signature: {hmac_sha256_hex}
    Content-Type: application/json

    {
      "event": "payment.captured",
      "payload": {
        "payment": {
          "entity": {
            "id": "pay_XYZ",
            "order_id": "order_Abc123XYZ",
            "amount": 57700,
            "currency": "INR",
            "status": "captured",
            "method": "upi"
          }
        }
      }
    }
    ```

    **MUST** verify the HMAC-SHA256 signature before processing:

    ```python
    import hmac, hashlib

    def verify_webhook(payload_body: bytes, signature: str, secret: str) -> bool:
        expected = hmac.new(
            secret.encode("utf-8"),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    ```

    Match `payload.payment.entity.order_id` to `transaction_reference` to
    correlate the webhook with the UCP checkout session.

8. **Update checkout status** to `completed` on the next platform poll.

---

## Platform Integration

### Prerequisites

Platforms require no registration with Razorpay or NPCI. UPI Intent reuses
the standard UCP `requires_escalation` mechanism — no new integration work
is required beyond what is already implemented for escalation handling.

### Handler Configuration

Platforms that support this handler advertise it in their UCP profile's
`payment_handlers` registry using `platform_config`.

#### Platform Config Fields

| Field         | Type   | Required | Description                          |
| :------------ | :----- | :------- | :----------------------------------- |
| `environment` | string | Yes      | `sandbox` or `production`            |
| `platform_id` | string | Yes      | Platform identifier                  |

#### Example Platform Handler Declaration

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "payment_handlers": {
      "com.razorpay.upi_intent": [
        {
          "id": "razorpay_upi",
          "version": "{{ ucp_version }}",
          "spec": "https://razorpay.com/ucp/upi-intent-handler.json",
          "schema": "https://razorpay.com/ucp/upi-intent-handler/schema.json",
          "available_instruments": [
            {
              "type": "upi_intent"
            }
          ],
          "config": {
            "environment": "production",
            "platform_id": "platform_xyz"
          }
        }
      ]
    }
  }
}
```

### Payment Protocol

#### Step 1: Discover Handler

The platform identifies `com.razorpay.upi_intent` in the business's UCP
profile (`/.well-known/ucp`) and renders a UPI payment option using
`display_name` and `display_logo` from the handler config.

```json
{
  "ucp": {
    "payment_handlers": {
      "com.razorpay.upi_intent": [
        {
          "id": "razorpay_upi",
          "available_instruments": [{ "type": "upi_intent" }],
          "config": {
            "display_name": "Pay via UPI",
            "display_logo": "https://cdn.razorpay.com/logos/upi.png"
          }
        }
      ]
    }
  }
}
```

#### Step 2: Submit Complete Checkout

When the buyer selects UPI, the platform submits a `upi_intent` instrument.
No credential is required at this stage — the business generates the intent
URI server-side.

```json
POST /checkout-sessions/{checkout_id}/complete
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json

{
  "payment": {
    "instruments": [
      {
        "id": "instr_1",
        "handler_id": "razorpay_upi",
        "type": "upi_intent"
      }
    ]
  },
  "signals": {
    "dev.ucp.buyer_ip": "203.0.113.42",
    "dev.ucp.user_agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36"
  }
}
```

#### Step 3: Handle `requires_escalation` Response

The business responds with `status: requires_escalation` and a `upi_intent`
credential containing the `intent_uri` and optional `qr_code_data`.

```json
{
  "status": "requires_escalation",
  "continue_url": "https://merchant.example.com/checkout/checkout_abc123",
  "payment": {
    "instruments": [
      {
        "id": "instr_1",
        "handler_id": "razorpay_upi",
        "type": "upi_intent",
        "credential": {
          "type": "upi_intent",
          "intent_uri": "upi://pay?pa=bigbasket@icici&pn=BigBasket&am=577.00&cu=INR&tr=order_Abc123XYZ&tn=Order%20checkout_abc123&mc=5411&mode=04",
          "transaction_reference": "order_Abc123XYZ",
          "qr_code_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
          "qr_code_string": "upi://pay?pa=bigbasket@icici&pn=BigBasket&am=577.00&cu=INR&tr=order_Abc123XYZ&tn=Order%20checkout_abc123&mc=5411&mode=04",
          "expires_at": "2026-01-29T10:20:00Z"
        }
      }
    ]
  }
}
```

#### Step 4: Launch Intent URI or Display QR Code

The platform's action depends on the runtime context. Refer to the decision
matrix below.

**Android Native App** — use an implicit Intent (NPCI mandated):

```kotlin
val upiUri = Uri.parse(credential.intent_uri)
val intent = Intent(Intent.ACTION_VIEW, upiUri)
val chooser = Intent.createChooser(intent, "Pay with")
startActivityForResult(chooser, UPI_PAYMENT_REQUEST_CODE)
```

**Android or iOS Mobile Web / WebView:**

```javascript
window.location.href = credential.intent_uri;
```

**iOS Native App:**

```swift
if let url = URL(string: credential.intent_uri) {
    UIApplication.shared.open(url, options: [:]) { success in
        if !success {
            self.displayQRCode(credential.qr_code_data)
        }
    }
}
```

**Desktop Browser** — `upi://` cannot be launched; display the QR code:

```html
<div class="upi-payment">
  <p>Scan with any UPI app</p>
  <img src="{{ credential.qr_code_data }}" alt="UPI QR Code" />
</div>
```

**Platform Decision Matrix:**

| Context               | Action                                    | Fallback            |
| :-------------------- | :---------------------------------------- | :------------------ |
| Android Native App    | Launch `intent_uri` with implicit Intent  | Display QR code     |
| Android Mobile Web    | Navigate to `intent_uri`                  | Display QR code     |
| iOS Native App        | Open `intent_uri` via `UIApplication`     | Display QR code     |
| iOS Safari / WebView  | Navigate to `intent_uri`                  | Display QR code     |
| Desktop Browser       | Display QR code from `qr_code_data`       | Redirect to `continue_url` |

#### Step 5: Poll for Completion

After launching the intent, the platform polls the checkout session until
the status transitions to `completed` or `canceled`. The business updates
the status upon receiving the PSP webhook.

```json
GET /checkout-sessions/{checkout_id}

{
  "status": "completed",
  "payment": {
    "instruments": [
      {
        "id": "instr_1",
        "handler_id": "razorpay_upi",
        "type": "upi_intent"
      }
    ]
  }
}
```

**Recommended polling schedule:** 2 s, 4 s, 8 s, 16 s (exponential backoff).
Stop polling and redirect to `continue_url` if `expires_at` is reached
without a terminal status.

---

## Security Considerations

| Requirement                       | Description                                                                                                                                   |
| :-------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------- |
| **Webhook signature verification** | Businesses **MUST** verify the `X-Razorpay-Signature` HMAC-SHA256 header before updating checkout status. Never trust unsigned webhook calls. |
| **No app targeting**              | Platforms **MUST NOT** use explicit intents to target specific UPI apps. Per NPCI mandate, only implicit intents (OS chooser) are permitted.   |
| **HTTPS for all URIs**            | `display_logo`, `continue_url`, and all business/PSP API calls **MUST** use HTTPS.                                                            |
| **Intent URI expiry**             | Platforms **MUST** check `expires_at` and redirect to `continue_url` if the intent has expired before the buyer completes payment.            |
| **Amount verification**           | Businesses **MUST** verify that the PSP order amount matches the UCP checkout total before accepting payment.                                  |
| **Idempotency**                   | Businesses **MUST** use `checkout_id` as the idempotency key when creating PSP orders to prevent duplicate charges on retry.                  |
| **No credential reuse**           | UPI Intent URIs are single-use and time-limited. Platforms **MUST NOT** cache or reuse credentials across sessions.                           |
| **Transaction reference binding** | Businesses **MUST** match `transaction_reference` (order ID) in the webhook to the active checkout session before confirming completion.       |

---

## NPCI UPI Intent URI Reference

The `intent_uri` must comply with NPCI UPI Linking Specification v1.7.

```
upi://pay?param-name=param-value&param-name=param-value
```

| Parameter | Name                   | M/C/O | Description                                                              |
| :-------- | :--------------------- | :---- | :----------------------------------------------------------------------- |
| `pa`      | Payee VPA              | M     | Payee Virtual Payment Address (e.g., `merchant@axis`)                    |
| `pn`      | Payee Name             | M     | Display name of payee (e.g., `BigBasket`)                                |
| `am`      | Amount                 | C     | Decimal amount (e.g., `577.00`). Required for merchant/dynamic payments. |
| `cu`      | Currency               | C     | Must be `INR` — only supported value.                                    |
| `tr`      | Transaction Reference  | C     | Unique order/bill reference. Required for merchant payments. Max 35 chars.|
| `tn`      | Transaction Note       | O     | Short description. Max 50 characters.                                    |
| `mc`      | Merchant Category Code | O     | 4-digit MCC (e.g., `5411` for grocery).                                  |
| `mode`    | Transaction Mode       | O     | `04` = Intent, `05` = Merchant Intent QR.                                |
| `url`     | Reference URL          | O     | HTTPS URL for transaction details. Must relate to the transaction.       |

*Legend: M = Mandatory, C = Conditional, O = Optional*

---

## References

* **Instrument Schema:** [schemas/shopping/types/upi_intent_instrument.json](site:schemas/shopping/types/upi_intent_instrument.json)
* **Credential Schema:** [schemas/shopping/types/upi_intent_credential.json](site:schemas/shopping/types/upi_intent_credential.json)
* **UCP Escalation Pattern:** [checkout.md](../checkout.md)
* **Payment Handler Guide:** [payment-handler-guide.md](../payment-handler-guide.md)
* **Razorpay UPI Docs:** https://razorpay.com/docs/payments/payment-methods/upi/
* **NPCI UPI Linking Specification v1.7:** https://www.npci.org.in/what-we-do/upi/product-overview
* **RFC 3986 (URI Encoding):** https://datatracker.ietf.org/doc/html/rfc3986
