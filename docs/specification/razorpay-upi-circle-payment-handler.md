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

This handler enables **UPI Circle** (delegated) payments in India via
[Razorpay](https://razorpay.com) as the payment service provider. UPI Circle is
an NPCI feature that lets a **primary account holder** authorise a **secondary
(delegate) user** to make UPI payments from the primary user's bank account,
without the secondary user needing their own bank account or knowing the
primary user's MPIN.

**UPI Circle flow** — The platform collects the secondary user's delegate VPA
and submits a Complete Checkout request with a `upi_circle` instrument and
credential containing that VPA. The business creates a Razorpay payment and
sends a collect request to NPCI via Razorpay. NPCI routes the request to the
secondary user's PSP app. The secondary user authenticates in their app using
biometrics or app PIN (no bank MPIN required). For **partial delegation**,
the primary account holder also approves in their PSP app. NPCI debits the
primary user's bank account and credits the merchant's bank. Razorpay notifies
the business via webhook and the business marks the checkout `completed`.

### UPI Circle vs UPI Intent — Key Differences

| Aspect                          | UPI Intent                              | UPI Circle                                      |
| :------------------------------ | :-------------------------------------- | :---------------------------------------------- |
| **Credential direction**        | Business → Platform (intent_uri)        | Platform → Business (delegate VPA)              |
| **Who authenticates**           | Buyer via their own UPI app (MPIN)      | Secondary user via biometrics / app PIN         |
| **Bank account debited**        | Buyer's own bank account                | Primary account holder's bank account           |
| **Platform action**             | Open `upi://` deep link or render QR    | Show VPA input + pending authorization screen   |
| **NPCI per-txn limit**          | No special limit                        | ₹5,000 per transaction                          |
| **NPCI monthly limit**          | No special limit                        | ₹15,000 per month (per circle link)             |
| **Additional approver**         | None                                    | Primary user (partial delegation only)          |
| **Biometric auth**              | Optional (PSP-dependent)                | Mandatory — no MPIN path for secondary user     |

### Key Benefits

* **No Razorpay SDK on platform** — The platform only needs to render a VPA
  input field and poll for completion. No PSP SDK required.
* **PSP-agnostic instrument** — The `upi_circle` instrument and credential
  schemas are NPCI-standard; any UPI-Circle-enabled PSP can implement this handler.
* **Zero PCI-DSS scope** — UPI is VPA-based. No card numbers involved.
* **Family-friendly payments** — Enables children, dependants, or employees to
  pay on behalf of a primary account holder within strict NPCI limits.
* **Backward-compatible escalation** — Platforms that do not implement this
  handler fall back to `continue_url` automatically.

### Integration Guide

| Participant  | Integration Section                           |
| :----------- | :-------------------------------------------- |
| **Business** | [Business Integration](#business-integration) |
| **Platform** | [Platform Integration](#platform-integration) |

---

## UPI Circle Concepts

### Participants in a UPI Circle

| Role                         | Description                                                                                                 |
| :--------------------------- | :---------------------------------------------------------------------------------------------------------- |
| **Primary Account Holder**   | The bank account owner who creates the UPI Circle. Sets delegation type and spending limits. Receives all transaction notifications. |
| **Secondary / Delegate User**| The person authorised to make payments from the primary user's account. Authenticates using biometrics or PSP app PIN. Cannot be linked to more than one primary user simultaneously. |
| **PSP App**                  | The UPI app used by both primary and secondary users (BHIM, PhonePe, Paytm, etc.). Enforces circle logic and authentication. |

### Delegation Types

| Type        | Who Authorizes               | Per-Transaction Max | Monthly Max  |
| :---------- | :--------------------------- | :------------------ | :----------- |
| **Full**    | Secondary user only          | ₹5,000              | ₹15,000      |
| **Partial** | Secondary user + Primary user| ₹5,000              | ₹15,000      |

> **New Circle Link Restriction:** During the first 24 hours after a new
> UPI Circle link is established, the per-transaction and monthly limits
> are reduced to ₹5,000 combined (NPCI mandated warm-up period).

### Pre-Condition: Circle Must Be Set Up

UPI Circle setup happens **out-of-band** — entirely within the primary user's
PSP app, before any merchant payment. The merchant and Razorpay are not
involved in this step.

```
[Primary Account Holder — Out of Band Setup]

1. Primary user opens their PSP app (BHIM / PhonePe / Paytm / etc.)
2. Navigates to UPI Circle → Create Circle
3. Adds secondary user via their UPI ID or QR code scan
4. Selects delegation type: Full or Partial
5. Sets spending limits (up to NPCI maximums)
6. Secondary user receives invitation in their PSP app
7. Secondary user accepts the invitation
8. UPI Circle is now active — secondary user's delegate VPA
   is linked to the primary user's bank account
```

---

## End-to-End Payment Flow

### Actors

| Actor                             | Role in Payment                                                                                 |
| :-------------------------------- | :---------------------------------------------------------------------------------------------- |
| **Customer (Secondary User)**     | The buyer making the payment using their delegate VPA.                                          |
| **Platform**                      | The shopping/commerce app — collects delegate VPA, submits checkout, polls for completion.      |
| **Business**                      | The merchant backend — receives checkout, calls Razorpay, handles webhook, marks completed.     |
| **Razorpay**                      | Payment gateway — creates order, sends collect request to NPCI, fires webhook on capture.       |
| **NPCI UPI Network**              | Routes collect request to secondary user's PSP; processes debit/credit via member banks.        |
| **Secondary User's PSP App**      | Displays authorization request; authenticates secondary user via biometrics/PIN.                |
| **Primary User's PSP App**        | (Partial delegation only) Receives approval request from secondary user's PSP; primary user approves. |
| **Remitter/Issuer Bank**          | Primary account holder's bank — source of funds.                                                |
| **Beneficiary Bank**              | Merchant's bank — receives the credit.                                                          |

### Flow Diagram

```
+------------+       +------------------+       +------------+     +----------+
|  Platform  |       |    Business      |       |  Razorpay  |     |   NPCI   |
+-----+------+       +--------+---------+       +------+-----+     +----+-----+
      |                       |                        |                 |
  ════╪═══════════════════════╪════════════════════════╪═════════════════╪════
  PRE-CONDITION: Primary account holder has already created UPI Circle
  delegation in their PSP app (out-of-band, no merchant involvement)
  ════╪═══════════════════════╪════════════════════════╪═════════════════╪════
      |                       |                        |                 |
      | 1. GET /.well-known/  |                        |                 |
      |    ucp                |                        |                 |
      |---------------------->|                        |                 |
      | 2. Handler config     |                        |                 |
      |    (env, merchant_    |                        |                 |
      |    name, limits)      |                        |                 |
      |<----------------------|                        |                 |
      |                       |                        |                 |
      | 3. POST /checkout     |                        |                 |
      |    (create)           |                        |                 |
      |---------------------->|                        |                 |
      | 4. Checkout response  |                        |                 |
      |    (upi_circle        |                        |                 |
      |    available,         |                        |                 |
      |    per_txn_limit,     |                        |                 |
      |    monthly_limit)     |                        |                 |
      |<----------------------|                        |                 |
      |                       |                        |                 |
  [Platform renders UPI Circle option with VPA input field]
  [Buyer enters their delegate VPA, e.g. buyer@paytm]
      |                       |                        |                 |
      | 5. POST checkout/     |                        |                 |
      |    complete           |                        |                 |
      |    instrument:        |                        |                 |
      |      type: upi_circle |                        |                 |
      |    credential:        |                        |                 |
      |      type: upi_circle |                        |                 |
      |      delegate_vpa:    |                        |                 |
      |        buyer@paytm    |                        |                 |
      |---------------------->|                        |                 |
      |                       | 6. POST /v1/orders     |                 |
      |                       |----------------------->|                 |
      |                       | 7. { order_id }        |                 |
      |                       |<-----------------------|                 |
      |                       | 8. POST /v1/payments/  |                 |
      |                       |    create/upi          |                 |
      |                       |    (method: upi,       |                 |
      |                       |     vpa: buyer@paytm,  |                 |
      |                       |     order_id)          |                 |
      |                       |----------------------->|                 |
      |                       |                        | 9. Collect      |
      |                       |                        |    Request      |
      |                       |                        | (VPA: buyer@    |
      |                       |                        |  paytm)         |
      |                       |                        |---------------->|
      |                       | 10. { payment_id,      |                 |
      |                       |      status: created } |                 |
      |                       |<-----------------------|                 |
      |                       |                        |                 |
      | 11. requires_         |                        |                 |
      |     escalation        |                        |                 |
      |  code: requires_      |                        |                 |
      |    buyer_             |                        |                 |
      |    authentication     |                        |                 |
      |  credential:          |                        |                 |
      |    type: upi_circle   |                        |                 |
      |    delegate_vpa:      |                        |                 |
      |      buyer@paytm      |                        |                 |
      |    razorpay_payment_  |                        |                 |
      |      id: pay_xxx      |                        |                 |
      |    expires_at: ...    |                        |                 |
      |<----------------------|                        |                 |
      |                       |                        |                 |
  [Platform shows "Open your UPI app and authorize the payment"]
  [Polling begins]
      |                       |                        |                 |
      :  (polling loop)       :                        :                 :
      |                       |                        |                 |
      ══════════════ NPCI routes collect request to secondary user's PSP ═══
      |                       |          +---------------------------+   |
      |                       |          | Secondary User's PSP App  |   |
      |                       |          +-----------+---------------+   |
      |                       |                      |                   |
      |                       |          12. Push notification:          |
      |                       |              "Authorize ₹X to           |
      |                       |               <merchant_name>"           |
      |                       |                      |<------------------+
      |                       |                      |                   |
      |                       |          [Secondary user sees             |
      |                       |           payment request in app]        |
      |                       |          [Authenticates via              |
      |                       |           biometrics / app PIN]          |
      |                       |          [No bank MPIN required]         |
      |                       |                      |                   |
      ══════ Full Delegation path (secondary user approval is sufficient) ══
      |                       |          13. Authorization              |
      |                       |              confirmed                  |
      |                       |                      +----------------->|
      |                       |                      |                   |
      ══════ Partial Delegation path (primary user must also approve) ══════
      |                       |          +---------------------------+   |
      |                       |          | Primary User's PSP App    |   |
      |                       |          +-----------+---------------+   |
      |                       |          13a. PSP sends approval         |
      |                       |               request to primary user    |
      |                       |                      |                   |
      |                       |          [Primary user approves or       |
      |                       |           rejects in their PSP app]      |
      |                       |          13b. Primary user approves      |
      |                       |                      +----------------->|
      ══════════════════════════════════════════════════════════════════════
      |                       |                        |                 |
      |                       |                        | 14. NPCI debits |
      |                       |                        |  primary user's |
      |                       |                        |  bank (Remitter)|
      |                       |                        |<--------------->|
      |                       |                        | 15. NPCI credits|
      |                       |                        |  merchant bank  |
      |                       |                        |  (Beneficiary)  |
      |                       |                        |<--------------->|
      |                       |                        |                 |
      |                       | 16. Webhook:           |                 |
      |                       |  payment.captured      |                 |
      |                       |<-----------------------|                 |
      |                       |                        |                 |
      |                       | 17. Verify signature   |                 |
      |                       |     Verify order_id    |                 |
      |                       |     Capture payment    |                 |
      |                       |     Mark checkout      |                 |
      |                       |     completed          |                 |
      |                       |                        |                 |
      | 18. GET /checkout     |                        |                 |
      |     (poll)            |                        |                 |
      |---------------------->|                        |                 |
      | 19. status: completed |                        |                 |
      |<----------------------|                        |                 |
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
   `payment.captured` event (and optionally `payment.failed`).

> **Note on NPCI Limits:** The business **MUST NOT** advertise this handler
> for checkout totals exceeding ₹5,000 (500,000 paise). Razorpay will reject
> the payment at the NPCI level if the amount exceeds the per-transaction limit.

### Handler Configuration

#### Handler Schema

**Schema URL:** `https://razorpay.com/ucp/handlers/upi-circle/schema.json`

| Config Variant    | Context              | Key Fields                                             |
| :---------------- | :------------------- | :----------------------------------------------------- |
| `business_config` | Business discovery   | `key_id`, `environment`, `merchant_name`, `max_amount` |
| `platform_config` | Platform discovery   | `environment`, `vpa_input`, `poll_interval_ms`         |
| `response_config` | Checkout responses   | `environment`, `merchant_name`, `per_txn_limit_paise`  |

#### Business Config Fields

| Field           | Type    | Required | Description                                                            |
| :-------------- | :------ | :------- | :--------------------------------------------------------------------- |
| `environment`   | string  | Yes      | `sandbox` or `production`                                              |
| `key_id`        | string  | Yes      | Public Razorpay API key                                                |
| `merchant_name` | string  | No       | Display name shown in the buyer's PSP app during authorization         |
| `currency`      | string  | No       | Must be `INR`. Defaults to `INR`.                                      |
| `max_amount`    | integer | No       | Max accepted amount in paise. Cannot exceed 500000. Defaults to 500000.|

#### Example Business Handler Declaration

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "payment_handlers": {
      "com.razorpay.upi.circle": [
        {
          "id": "razorpay_upi_circle",
          "version": "{{ ucp_version }}",
          "spec": "https://razorpay.com/ucp/handlers/upi-circle",
          "schema": "https://razorpay.com/ucp/handlers/upi-circle/schema.json",
          "available_instruments": [
            { "type": "upi_circle" }
          ],
          "config": {
            "environment": "production",
            "key_id": "rzp_live_XXXXXXXXXXXXXXX",
            "merchant_name": "Acme Store",
            "max_amount": 500000
          }
        }
      ]
    }
  }
}
```

### Processing Payments

When the business receives a Complete Checkout request with a `upi_circle`
instrument and `upi_circle` credential containing a `delegate_vpa`, it **MUST**:

1. **Validate handler.** Confirm `instrument.handler_id` matches a declared
   `com.razorpay.upi.circle` handler and `instrument.type == "upi_circle"`.

2. **Validate VPA format.** Verify `credential.delegate_vpa` matches the
   pattern `[a-zA-Z0-9._-+]+@[a-zA-Z0-9]+`. Reject malformed VPAs early.

3. **Validate amount.** Confirm the checkout total does not exceed ₹5,000
   (500,000 paise). Return `payment_failed` immediately if it does.

4. **Ensure idempotency.** If this `checkout_id` already has a Razorpay
   order and payment, return the existing escalation response.

5. **Create a Razorpay Order** (`POST /v1/orders`):

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

   | Field             | Description                                                  |
   | :---------------- | :----------------------------------------------------------- |
   | `amount`          | Amount in **paise** (1 INR = 100 paise). Max 500000.         |
   | `currency`        | Must be `"INR"` — UPI only supports INR.                     |
   | `receipt`         | The UCP `checkout.id` or internal order reference.           |
   | `payment_capture` | `0` = manual capture (business captures after webhook).      |

   Response: `{ "id": "order_Abcdef1234XXXX", ... }`

6. **Initiate UPI Collect via Razorpay** (`POST /v1/payments/create/upi`):

   ```http
   POST https://api.razorpay.com/v1/payments/create/upi
   Authorization: Basic base64(key_id:key_secret)
   Content-Type: application/json

   {
     "amount": 50000,
     "currency": "INR",
     "order_id": "order_Abcdef1234XXXX",
     "method": "upi",
     "vpa": "buyer@paytm",
     "email": "buyer@example.com",
     "contact": "+919876543210",
     "description": "Order checkout_abc123",
     "callback_url": "https://business.example.com/razorpay/callback"
   }
   ```

   | Field          | Description                                                       |
   | :------------- | :---------------------------------------------------------------- |
   | `method`       | Must be `"upi"`.                                                  |
   | `vpa`          | The delegate VPA from `credential.delegate_vpa`.                  |
   | `callback_url` | Razorpay posts payment status here (used alongside webhooks).     |

   Response: `{ "razorpay_payment_id": "pay_XXXXXXXXXXXXXXXX", "next": [...] }`

   > Razorpay sends a UPI collect request to NPCI, which routes it to the
   > buyer's PSP app. The PSP recognizes the VPA as belonging to a UPI Circle
   > delegation and presents the appropriate authorization UI.

7. **Return `requires_escalation`** with `requires_buyer_authentication`:

   ```json
   {
     "status": "requires_escalation",
     "continue_url": "https://business.example.com/checkout-sessions/checkout_abc123",
     "messages": [
       {
         "type": "error",
         "code": "requires_buyer_authentication",
         "severity": "requires_buyer_review",
         "content": "Open your UPI app to authorize this payment",
         "path": "$.payment.instruments[0]"
       }
     ],
     "payment": {
       "instruments": [
         {
           "id": "instr_1",
           "handler_id": "razorpay_upi_circle",
           "type": "upi_circle",
           "selected": true,
           "display": {
             "name": "Pay via UPI Circle",
             "logo": "https://upload.wikimedia.org/wikipedia/commons/f/fa/UPI-Logo.png"
           },
           "credential": {
             "type": "upi_circle",
             "delegate_vpa": "buyer@paytm",
             "razorpay_payment_id": "pay_XXXXXXXXXXXXXXXX",
             "push_sent_at": "2026-03-31T10:00:00Z",
             "expires_at": "2026-03-31T10:15:00Z"
           }
         }
       ]
     }
   }
   ```

8. **Receive Razorpay webhook.** On `payment.captured`:
   - Verify `X-Razorpay-Signature` using `HMAC_SHA256(webhook_body, webhook_secret)`.
   - Confirm `payment.order_id` matches the order created for this checkout.
   - Capture the payment (`POST /v1/payments/{id}/capture`) if not auto-captured.
   - Mark the UCP checkout as `completed`.

#### Handling Partial Delegation Timeout

For partial delegation, the primary account holder must approve the payment.
This can take several minutes. The business **MUST** configure the webhook
for `payment.failed` as well and handle timeout scenarios:

- If `payment.failed` is received with `description: "Payment was cancelled by the user"`,
  mark the checkout as `requires_escalation` again (allowing retry) or `canceled`.
- The escalation `expires_at` should be set to 5–15 minutes to cover approval time.

#### Error Mapping

| Condition                                          | UCP Error        | Action                                           |
| :------------------------------------------------- | :--------------- | :----------------------------------------------- |
| Checkout total exceeds ₹5,000                      | `payment_failed` | Reject at handler selection — do not call Razorpay |
| Invalid or unresolvable delegate VPA               | `payment_failed` | Return error; prompt buyer to re-enter VPA        |
| Order/payment creation fails                       | `payment_failed` | Return error; platform may retry                  |
| Webhook `payment.failed` — buyer rejected          | `payment_failed` | Retry or `canceled`                               |
| Webhook `payment.failed` — primary user rejected   | `payment_failed` | Return error with partial delegation context      |
| Authorization timed out (>15 min)                  | `payment_failed` | Business must create a new order                  |
| VPA not enrolled in UPI Circle                     | `payment_failed` | Return error; buyer must set up circle first      |
| Currency is not `INR`                              | `payment_failed` | Reject at handler selection stage                 |

---

## Platform Integration

### Prerequisites

Platforms do **not** need a Razorpay account. The platform only needs to:

1. Render a VPA input field to collect the buyer's delegate UPI ID.
2. Handle the `requires_buyer_authentication` error code in the
   `requires_escalation` response.
3. Display a "pending authorization" screen instructing the buyer to open
   their UPI app (no deep link needed — the push notification is automatic).
4. Poll for checkout completion.

### Handler Configuration

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
          ],
          "config": {
            "environment": "production",
            "vpa_input": {
              "placeholder": "Enter UPI Circle ID (e.g. name@upi)",
              "label": "UPI Circle ID"
            },
            "poll_interval_ms": 3000,
            "poll_timeout_ms": 300000
          }
        }
      ]
    }
  }
}
```

### Payment Protocol

#### Step 1: Discover Handler

The platform identifies `com.razorpay.upi.circle` in the business's profile
and confirms `upi_circle` in `available_instruments`.

Check that the checkout total does not exceed `response_config.per_txn_limit_paise`
(₹5,000). If it does, do not offer UPI Circle as a payment option.

#### Step 2: Create / Fetch Checkout

The platform creates or fetches the checkout session. The business returns
`response_config` with `environment`, `merchant_name`, and NPCI limits.

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
      "com.razorpay.upi.circle": [
        {
          "id": "razorpay_upi_circle",
          "version": "{{ ucp_version }}",
          "available_instruments": [{ "type": "upi_circle" }],
          "config": {
            "environment": "production",
            "merchant_name": "Acme Store",
            "per_txn_limit_paise": 500000,
            "monthly_limit_paise": 1500000
          }
        }
      ]
    }
  }
}
```

#### Step 3: Collect Delegate VPA from Buyer

The platform renders a VPA input. The buyer enters their delegate UPI ID
(the UPI ID they have registered as a secondary user in a UPI Circle).

```
┌─────────────────────────────────────────────────────┐
│  Pay via UPI Circle                                  │
│                                                      │
│  UPI Circle ID                                       │
│  ┌───────────────────────────────────────────────┐  │
│  │ Enter UPI Circle ID (e.g. name@upi)           │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  ℹ️  Limit: ₹5,000 per transaction · ₹15,000/month  │
│                                                      │
│  [Pay ₹500.00]                                      │
└─────────────────────────────────────────────────────┘
```

#### Step 4: Submit Complete Checkout (with VPA credential)

The platform submits Complete Checkout with the `upi_circle` instrument
**and** the delegate VPA as the credential. Unlike UPI Intent, the credential
is provided by the buyer, not generated by the business.

```http
POST /checkout-sessions/{checkout_id}/complete
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json

{
  "payment": {
    "instruments": [
      {
        "id": "instr_1",
        "handler_id": "razorpay_upi_circle",
        "type": "upi_circle",
        "display": {
          "name": "Pay via UPI Circle"
        },
        "credential": {
          "type": "upi_circle",
          "delegate_vpa": "buyer@paytm"
        }
      }
    ]
  }
}
```

#### Step 5: Handle Escalation Response

The business responds with `requires_escalation` and
`requires_buyer_authentication`. Unlike UPI Intent, there is **no deep link
to open** — the push notification was already sent to the buyer's PSP app.

```javascript
const response = await completeCheckout(checkoutId, instrument, credential);

if (response.status === "requires_escalation") {
  const authError = response.messages.find(
    m => m.code === "requires_buyer_authentication" &&
         m.severity === "requires_buyer_review"
  );
  const instrument = response.payment?.instruments?.[0];
  const cred = instrument?.credential;

  if (authError && cred?.type === "upi_circle") {
    // Check expiry before showing pending screen
    if (cred.expires_at && new Date(cred.expires_at) < new Date()) {
      fallbackToContinueUrl(response.continue_url);
      return;
    }

    // Show "check your UPI app" screen (no deep link needed)
    showUpiCirclePendingScreen({
      vpa: cred.delegate_vpa,
      expiresAt: cred.expires_at,
      merchantName: handlerConfig.merchant_name,
    });

    // Start polling — allow up to 5 minutes for partial delegation approval
    pollCheckoutStatus(checkoutId, response.continue_url);
  } else {
    fallbackToContinueUrl(response.continue_url);
  }
}
```

#### Step 6: Poll for Completion

After displaying the pending screen, the platform polls until `completed`,
`canceled`, or timeout:

```javascript
async function pollCheckoutStatus(checkoutId, continueUrl) {
  const POLL_INTERVAL_MS = 3000;
  const MAX_POLLS = 100;  // ~5 minutes (covers partial delegation approval)

  for (let i = 0; i < MAX_POLLS; i++) {
    await sleep(POLL_INTERVAL_MS);
    const checkout = await getCheckout(checkoutId);

    if (checkout.status === "completed") {
      showSuccessScreen(checkout);
      return;
    }
    if (checkout.status === "canceled") {
      showFailureScreen("Payment was declined or timed out.");
      return;
    }
  }

  // Timeout — fall back to continue_url
  fallbackToContinueUrl(continueUrl);
}
```

> **Partial delegation timeout:** Allow up to 5 minutes of polling
> (`poll_timeout_ms: 300000`). The primary account holder may need time
> to see and approve the notification on their device.

---

## Security Considerations

| Requirement                       | Description                                                                                                                                   |
| :-------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------- |
| **key_secret never exposed**      | The `key_secret` **MUST** remain on the business backend. **MUST NOT** appear in UCP profiles, responses, or client-side code.                |
| **Webhook signature**             | The business **MUST** verify `X-Razorpay-Signature` on every webhook using `HMAC_SHA256(body, webhook_secret)` before updating checkout state.|
| **Order-to-checkout binding**     | The business **MUST** verify that `payment.order_id` in the webhook matches the order created for this checkout.                              |
| **Amount enforcement**            | The business **MUST** reject any checkout exceeding ₹5,000 (500,000 paise) — the NPCI per-transaction limit for UPI Circle.                  |
| **VPA validation**                | The business **MUST** validate `delegate_vpa` format before calling Razorpay. Invalid VPAs will cause Razorpay API errors.                    |
| **Idempotency**                   | If a `checkout_id` already has a payment order, return the existing escalation response without creating a new order.                         |
| **Credential expiry**             | The platform **MUST NOT** display an expired pending screen. It **MUST** fall back to `continue_url` if `expires_at` has passed.              |
| **continue_url fallback**         | The platform **MUST** fall back to `continue_url` if: the handler is not implemented, the credential is expired, or polling times out.        |
| **No primary user data exposure** | The business response **MUST NOT** include any information about the primary account holder. Only the delegate VPA and payment reference are safe to return. |
| **INR only**                      | UPI only supports INR. Businesses **MUST NOT** advertise this handler for non-INR checkouts.                                                  |
| **TLS/HTTPS only**                | All traffic to Razorpay APIs and UCP endpoints **MUST** use TLS 1.2 or higher.                                                               |

---

## Testing

Razorpay provides a full sandbox environment for end-to-end testing.

### Setup

1. Toggle to **Test Mode** in the [Razorpay Dashboard](https://dashboard.razorpay.com).
2. From *Settings → API Keys*, generate test keys (`rzp_test_*`).
3. Use `environment: "sandbox"` in both business and platform configs.

### Simulating UPI Circle in Sandbox

In sandbox mode, use Razorpay test VPAs to simulate different scenarios:

| Test VPA              | Simulated Scenario                        |
| :-------------------- | :---------------------------------------- |
| `success@razorpay`    | Payment authorized (full delegation)      |
| `failure@razorpay`    | Payment declined by secondary user        |
| `partial@razorpay`    | Partial delegation — primary approves     |
| `timeout@razorpay`    | Authorization times out after 15 seconds  |

> Contact Razorpay support for the current list of sandbox UPI Circle test VPAs,
> as these may be updated with new sandbox releases.

### End-to-End Test Checklist

- [ ] Business profile at `/.well-known/ucp` declares `com.razorpay.upi.circle` with `rzp_test_*` key and `environment: "sandbox"`.
- [ ] Platform profile declares `com.razorpay.upi.circle` with `environment: "sandbox"`.
- [ ] Platform does **not** offer UPI Circle when checkout total exceeds ₹5,000.
- [ ] Platform renders VPA input field with correct label and placeholder from `response_config`.
- [ ] Platform submits Complete Checkout with `upi_circle` instrument **and** `upi_circle` credential containing `delegate_vpa`.
- [ ] Business validates VPA format before calling Razorpay.
- [ ] Business creates Razorpay order via `POST /v1/orders` in test mode.
- [ ] Business initiates collect via `POST /v1/payments/create/upi` with the delegate VPA.
- [ ] Business returns `requires_escalation` with `requires_buyer_authentication` + `upi_circle_credential`.
- [ ] Escalation response includes `continue_url` (always required).
- [ ] `credential.razorpay_payment_id` is present and non-empty.
- [ ] `credential.expires_at` is in the future.
- [ ] Platform shows "check your UPI app" screen — does NOT open a deep link.
- [ ] Platform polls with 3-second interval, up to 5-minute timeout.
- [ ] Business receives `payment.captured` webhook; verifies `X-Razorpay-Signature`.
- [ ] Business marks checkout `completed`.
- [ ] Platform polling returns `status: completed`.
- [ ] Platform falls back to `continue_url` when credential is expired.
- [ ] Platform falls back to `continue_url` when polling times out.
- [ ] `payment.failed` webhook correctly triggers checkout cancellation.

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

## Comparison with UPI Intent Handler

| Aspect                        | `com.razorpay.upi` (Intent)                     | `com.razorpay.upi.circle` (Circle)                     |
| :---------------------------- | :---------------------------------------------- | :----------------------------------------------------- |
| **Instrument type**           | `upi_intent`                                    | `upi_circle`                                           |
| **Platform submits credential?** | No — no credential on submit                 | Yes — delegate VPA                                    |
| **Business generates credential?** | Yes — `intent_uri` in escalation response  | No — returns payment reference only                   |
| **Platform action post-escalation** | Open `upi://` deep link or render QR      | Show "check your app" screen, start polling            |
| **Buyer auth in PSP app**     | MPIN                                            | Biometrics / app PIN (no MPIN)                        |
| **Additional approver**       | None                                            | Primary user (partial delegation only)                 |
| **Per-txn limit**             | No special limit                                | ₹5,000 (NPCI)                                         |
| **Monthly limit**             | No special limit                                | ₹15,000 per circle link (NPCI)                        |
| **Recommended for**           | Standard UPI payments by any buyer              | Secondary users paying via delegated access            |
| **Poll timeout**              | ~1 minute                                       | ~5 minutes (partial delegation needs more time)        |

---

## Applicability Beyond Razorpay

The `requires_buyer_authentication` error code and `upi_circle` credential
pattern are PSP-agnostic. Any UPI PSP (PayU, Cashfree, Juspay) that supports
NPCI UPI Circle delegated payments can implement this same handler by
accepting the `delegate_vpa` credential and processing the collect request
through the NPCI network.

---

## References

* **Handler Spec:** `https://razorpay.com/ucp/handlers/upi-circle`
* **Handler Schema:** `https://razorpay.com/ucp/handlers/upi-circle/schema.json`
* **UPI Circle Instrument Schema:** [upi_circle_instrument.json](site:schemas/shopping/types/upi_circle_instrument.json)
* **UPI Circle Credential Schema:** [upi_circle_credential.json](site:schemas/shopping/types/upi_circle_credential.json)
* **Razorpay Orders API:** `https://razorpay.com/docs/api/orders/`
* **Razorpay Payments API:** `https://razorpay.com/docs/api/payments/`
* **Razorpay UPI Docs:** `https://razorpay.com/docs/payments/payment-methods/upi/`
* **NPCI UPI Circle Overview:** `https://www.npci.org.in/what-we-do/upi/product-overview`
* **UPI Intent Handler:** [razorpay-upi-payment-handler.md](razorpay-upi-payment-handler.md)
* **UCP Payment Handler Guide:** [payment-handler-guide.md](payment-handler-guide.md)
* **UCP Checkout Specification:** [checkout.md](checkout.md)
