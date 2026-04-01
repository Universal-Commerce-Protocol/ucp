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

* **Handler Name:** `com.razorpay.upi_circle`
* **Version:** `{{ ucp_version }}`

## Introduction

The `com.razorpay.upi_circle` handler enables businesses to accept **delegated
UPI payments** through UCP-compatible platforms. UPI Circle is NPCI's
delegation framework — buyers authorize an AI agent to make payments on their
behalf within configurable limits, without per-transaction MPIN authentication.

This handler follows the standard credential-before-Complete-Checkout pattern — the same architecture as com.google.pay and dev.shopify.shop_pay: the platform fetches a one-time cryptogram from Razorpay AI Commerce TSP after authenticating the user, sends it in Complete Checkout and the business processes the payment by passing the cryptogram to its PSP(Razorpay) and marks the Checkout as complete. No escalation, no app switch, no buyer interaction at payment time.

> **Note:** This handler requires a **one-time delegation setup** between the
> buyer, the Platform and Razorpay. This setup happens outside UCP as a
> bilateral integration between the platform and Razorpay AI Commerce TSP 
> acting like a Credential Provider, similar to a buyer saving a card.
> See [Delegation Setup](#delegation-setup-outside-ucp).

### Key Benefits

* **Truly agentic** — No per-transaction authentication. Agent pays autonomously within mandate limits.
* **Zero PCI-DSS scope** — VPA-based; no card data touches any system.
* **Zero buyer friction** — No app switch, no QR code, no MPIN at payment time. Like card-on-file for UPI.
* **NPCI-backed guardrails** — Per-transaction and monthly limits enforced at the mandate level by NPCI and the buyer's bank.
* **500M+ UPI users** — Extends India's dominant payment rail to agentic commerce.

### Integration Guide

| Participant                      | Section                                                   |
| :------------------------------- | :-------------------------------------------------------- |
| **Business**                     | [Business Integration](#business-integration)             |
| **Platform**                     | [Platform Integration](#platform-integration)             |
| **PSP**                          | [PSP Integration](#psp-integration-razorpay)              |
| **AI Commerce TSP**              | [Credential Provider](#razorpay-ai-commerce-tsp-as-a-credential-provider-delegation-setup-and-cryptogram-issuance) |

---

## Participants

> **Note on Terminology:** This specification refers to the Razorpay merchant
> account holder as the **"business."** Technical schema fields retain standard
> industry nomenclature `key_*` where applicable.

| Participant                 | Role                                                                                         | Prerequisites                                                       |
| :-------------------------- | :------------------------------------------------------------------------------------------- | :------------------------------------------------------------------ |
| **Business**                         | Advertises handler configuration; processes cryptogram via Razorpay; responds `completed`  | Yes — Razorpay account with KYC, webhook endpoint (HTTPS, TLS 1.2+)         |
| **Platform**                         | Discovers handler; enables product discovery; takes UPI delegation from a user through a AI Commerce TSP; fetches one time cryptogram as payment credentials and submits in Complete Checkout          | Yes - Requires custom  integration with Razorpay AI Commerce TSP for setting up the delegation and fetching one time cryptogram, active `delegate_id`                         |
| **Razorpay (PSP)**                   | Processes delegated debit via NPCI using mandate UMN; fires webhook to business            | N/A — payment infrastructure                                                 |
| **Razorpay AI Commerce TSP (Credential Provider)**   |  Allows delegation to the platform and issues one-time cryptograms for established delegation mandates.                            | N/A — credential infrastructure (analogous to Google Pay token API)          |

---

## Delegation Setup (Outside UCP)

Before any payment can occur, the buyer must establish a delegation mandate.
This is a **one-time bilateral integration** between the Platform and Razorpay
— it is **not part of UCP**, just as saving a card on Gemini is not part of
the checkout protocol.

### Setup Flow

```
+----------+        +---------------------+        +---------------------+        +---------+
|   User   |        |  AI Agent (Platform)|        | RZP AI Commerce TSP |        | UPI App |
+----+-----+        +----------+----------+        +----------+----------+        +----+----+
     |                         |                              |                        |
     | 1. Initiates UPI set-up |                              |                        |
     |    with mobile number   |                              |                        |
     |------------------------>|                              |                        |
     |                         | 2. Initiate customer mobile  |                        |
     |                         |    number verification       |                        |
     |                         |----------------------------->|                        |
     |                         |                              |                        |
     |                         |                              |                        |
     |                         |                              |                        |
     | 3. One Time Password    |                              |                        |
     |    (OTP sent to User) - - - - - - - - - - - - - - - - -|                        |
     |<-------------------------------------------------------|                        |
     |                         |                              |                        |
     | 4. Customer provides    |                              |                        |
     |    OTP on Platform      |                              |                        |
     |------------------------>|                              |                        |
     |                         | 4. Submit OTP to Razorpay    |                        |
     |                         |----------------------------->|                        |
     |                         | 5. Return Delegation Intent  |                        |
     |                         |    URL and/or QR code        |                        |
     |                         |<-----------------------------|                        |
     |                         |                              |                        |
     | 6. Show Intent URL      |                              |                        |
     |<------------------------|                              |                        |
     |                         |                              |                        |
     | 7. Goes to UPI app, sets up limits & confirms          |                        |
     |    payment delegation to Platform                      |                        |
     |------------------------------------------------------->|----------------------->|
     |                         |                              |                        |
     |                         | 8. User redirected back      |                        |
     |                         |    to Platform               |                        |
     |                         |<------------------------------------------------------|
     |                         |                              |                        |
     |                         | 9. Check Delegation status   |                        |
     |                         |----------------------------->|                        |
     |                         | 10. Confirmation of          |                        |
     |                         |     delegation status        |                        |
     |                         |     with delegate_ID         |                        |
     |                         |<-----------------------------|                        |
     |                         |                              |                        |
```

### Setup API Reference

| Operation                          | Method | Purpose                                             |
| :--------------------------------- | :----- | :-------------------------------------------------- |
| Generate OTP                       | POST   | Send OTP to buyer's mobile                          |
| Submit OTP                         | POST   | Verify OTP; receive intent link / QR for delegation |
| Poll delegation status             | GET    | Poll until `delegate_id` reaches `status: linked`   |

**Output:** `delegate_id` — persistent mandate reference. All subsequent
payments use this ID to fetch cryptograms.

> Get in touch with Razorpay for API Docs 


---

## End-to-End Payment Flow

### Flow Diagram

```
+------------+       +---------------------------+     +------------------+     +------------------+
|  Platform  |       |  Razorpay (Cred. Provider)|     |    Business      |     | Razorpay (PSP)   |
+-----+------+       +-------------+-------------+     +--------+---------+     +--------+---------+
      |                            |                            |                      |
  ═════════════════════════════════╪════════════════════════════╪══════════════════════╪════
  PRE-CONDITION: Delegation setup completed .
  Platform holds a valid delegate_id (status: linked).
  ════╪════════════════════════════╪════════════════════════════╪══════════════════════╪════
      |                            |                            |                      |
      |  1. GET /.well-known/ucp   |                            |                      |
      |--------------------------->| (or business profile)      |                      |
      |  2. Handler config         |                            |                      |
      |<---------------------------|                            |                      |
      |                            |                            |                      |
      |  3. POST /checkout         |                            |                      |
      |   (create)                 |                            |                      |
      |-------------------------------------------------------->|                      |
      |  4. Checkout response      |                            |                      |
      |   (upi_circle available)   |                            |                      |
      |<--------------------------------------------------------|                      |
      |                            |                            |                      |
  [Platform selects upi_circle for buyer with active delegate_id]                      |
      |                            |                            |                      |
      |  5. GET payment cryptogram |                            |                      |
      |     for the saved          |                            |                      |
      |     delegation id.         |                            |                      |
      |                            |                            |                      |
      |--------------------------->|                            |                      |
      |  6. { cryptogram,          |                            |                      |
      |       expires_at }         |                            |                      |
      |<---------------------------|                            |                      |
      |                            |                            |                      |
  [Platform builds instrument + credential, submits Complete Checkout]                 |
      |                            |                            |                      |
      |  7. POST checkout/complete |                            |                      |
      |   instrument:              |                            |                      |
      |     type: upi_circle       |                            |                      |
      |     delegate_id: c894aa29  |                            |                      |
      |   credential:              |                            |                      |
      |     type: upi_circle_      |                            |                      |
      |       cryptogram           |                            |                      |
      |     cryptogram: a345345... |                            |                      |
      |     expires_at: ...        |                            |                      |
      |-------------------------------------------------------->|                      |
      |                            |                            |                      |
      |                            |                            |  8.Validate handler  |
      |                            |                            |    Validate idempot. |
      |                            |                            |    Extract cryptogram|
      |                            |                            |                      |
      |                            |                            |  9. Process payments |
      |                            |                            |     through PSP      |
      |                            |                           (delegate_id + cryptogram)
      |                            |                            |--------------------->|
      |                            |                            |                      |
      |                            |                            | 10. Webhook:         |
      |                            |                            |  payment.authorized  |
      |                            |                            |<---------------------|
      |                            |                            |                      |
      |                            |                            | 11. Verify signature |
      |                            |                            |     Update checkout  |
      |                            |                            |     completed        |
      |                            |                            |                      |
      |  12. status: completed     |                            |                      |
      |<--------------------------------------------------------|                      |
      |   (or complete_in_         |                            |                      |
      |    progress → poll)        |                            |                      |
```

---

## Business Integration

### Prerequisites

Before advertising this handler, businesses **MUST** complete:

1. **Create a Razorpay account** at [dashboard.razorpay.com](https://dashboard.razorpay.com).
2. **Complete KYC** to activate live payments.
3. **Configure webhook endpoint** — HTTPS endpoint (TLS 1.2+) to receive
   `payment.authorized` and `payment.failed` events.
4. **Retrieve credentials** from *Settings → API Keys*:
   * `key_id` / `key_secret` — for webhook signature verification and PSP API calls.

> **Note:** No merchant VPA is needed in the handler config. The payee VPA is
> resolved by Razorpay at payment time from the `delegate_id` and cryptogram.

### Handler Configuration

#### Handler Schema

| Config Variant    | Context              | Key Fields                        |
| :---------------- | :------------------- | :-------------------------------- |
| `business_config` | Business discovery   | `environment`, `key_id`           |
| `platform_config` | Platform discovery   | `environment`, `upi_apps`         |
| `response_config` | Checkout responses   | `environment`                     |

#### Business Config Fields

| Field           | Type   | Required | Description                                                                          |
| :-------------- | :----- | :------- | :----------------------------------------------------------------------------------- |
| `key_id`        | string | Yes      | Razorpay public API key (`rzp_test_*` or `rzp_live_*`)                               |
| `environment`   | string | Yes      | `sandbox` or `production`                                                            |
| `merchant_name` | string | No       | Business display name shown to the buyer during the UPI payment flow                 |
| `currency`      | string | No       | Currency accepted. Defaults to `INR`                                                 |

#### Platform Config Fields

| Field       | Type            | Required | Description                                                                                              |
| :---------- | :-------------- | :------- | :------------------------------------------------------------------------------------------------------- |
| `environment` | string        | Yes      | `sandbox` or `production`. Must match the business config environment.                                   |
| `upi_apps`  | array of strings | No      | UPI apps the platform is capable of deep-linking to (e.g., `["gpay", "phonepe", "paytm", "bhim"]`). Each value must be unique. |

#### Example Handler Declaration

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "payment_handlers": {
      "com.razorpay.upi_circle": [
        {
          "id": "razorpay_upi_circle",
          "name": "com.razorpay.upi_circle",
          "config": {
            "key_id": "rzp_live_KN2V9UHAlkas",
            "environment": "production"
          }
        }
      ]
    }
  }
}
```

### Processing Payments

Upon receiving a Complete Checkout with a `upi_circle` instrument and
`upi_circle_cryptogram` credential, businesses **MUST**:

1. **Validate handler.** Confirm `instrument.handler_id` matches a declared
   `com.razorpay.upi_circle` handler.

2. **Ensure idempotency.** If this `checkout_id` has already been processed,
   return the previous result without re-processing.

3. **Extract credential.** Retrieve `credential.cryptogram` and
   `credential.delegate_id` from the instrument.

4. **Process delegated debit.** Call Razorpay PSP to initiate a delegated
   debit via NPCI using the mandate's UMN (resolved internally by Razorpay from
   `delegate_id`, `cryptogram`).
5. **Receive Razorpay Webhook** On the configured URL

6. **Return result.**

**Success Response:**

```json
{
  "id": "checkout_abc123",
  "status": "completed",
  "order": {
    "id": "order_xyz789",
    "permalink_url": "https://store.com/orders/xyz789"
  }
}
```

**Failure Response:**

```json
{
  "id": "checkout_abc123",
  "status": "canceled",
  "messages": [
    {
      "type": "error",
      "code": "payment_declined",
      "severity": "recoverable",
      "content": "Delegated UPI payment was declined. The mandate limit may have been exceeded.",
      "path": "$.payment"
    }
  ]
}
```

### Webhook Handling

Razorpay sends payment events to the business's configured webhook endpoint.
Businesses **MUST** verify signatures before processing.

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

| Event                  | Meaning                              | Business Action                                         |
| :--------------------- | :----------------------------------- | :------------------------------------------------------ |
| `payment.authorized`   | NPCI confirmed delegated debit       | Update checkout to `completed`, populate `order`        |
| `payment.failed`       | Debit declined (limit, expiry, etc.) | Update checkout to `canceled` with error messages       |

---

## Platform Integration

### Prerequisites

Before handling `com.razorpay.upi_circle` payments, platforms **MUST**:

1. **Integrate with Razorpay AI Commerce TSP** — Razorpay AI Commerce TSP acting as
   a Credential Provider. Platform must authenticate the user to store delegation 
   against the unique delegate_id, and fetch one time cryptogram.
2. **Complete delegation setup** — Buyer must have an active delegation mandate
   setup via Razorpay AI Commerce TSP. Platform must hold a valid delegate_id.
3. **Instrument Selection** - Ability to select UPI Circle as one of the payment 
   instrument during checkout.
3. **Implement status polling** — Poll `GET /checkout-sessions/{id}` if the
   business processes asynchronously and returns `status: complete_in_progress`.

Platforms **SHOULD** only present UPI Circle as a payment instrument when:
- The buyer's context indicates India (e.g., `address_country: "IN"`)
- The buyer has an active delegation (`delegate_id` with `status: linked`)
  - Also allow the user to setup a delegation of not already done  

### Platform Handler Integration

The following is a sample platform profile declaring support for
`com.razorpay.upi_circle`:

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "payment_handlers": {
      "com.razorpay.upi_circle": [
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
            "upi_apps": ["gpay", "phonepe", "paytm", "bhim"]
          }
        }
      ]
    }
  }
}
```

| Field | Required | Description |
| :---- | :------- | :---------- |
| `id` | Yes | Unique platform-scoped identifier for this handler entry |
| `version` | Yes | UCP spec version the platform targets |
| `spec` | Yes | Canonical handler spec URL |
| `schema` | Yes | JSON schema URL for validation |
| `available_instruments[].type` | Yes | Must be `"upi_circle"` |
| `config.environment` | Yes | `"sandbox"` for test mode, `"production"` for live |
| `config.upi_apps` | No | UPI apps the platform can deep-link to for delegation setup |

> Use `"environment": "sandbox"` during development and integration testing.
> Switch to `"production"` only after completing Razorpay's go-live checklist.

### Payment Protocol

#### Step 1: Discover Handler

Identify `com.razorpay.upi_circle` in the business's `payment.handlers` array
from the Create Checkout response.

```json
{
  "id": "razorpay_upi_circle",
  "name": "com.razorpay.upi_circle",
  "config": {
    "key_id": "rzp_live_KN2V9UHAlkas",
    "environment": "production"
  }
}
```

#### Step 2: Fetch Cryptogram from Razorpay AI Commerce TSP 

Call Razorpay's cryptogram issuance API to get a one-time cryptogram for the
buyer's delegation. This **MUST** be done immediately before submitting
Complete Checkout — cryptograms are single-use and time-limited.

```http
POST /v1/upi/delegate/{delegate_id}/cryptogram
Authorization: Basic base64(key_id:key_secret)
Content-Type: application/json

{
  "delegate_id": "c894aa29a7da69"
}
```

> Exact API path subject to change. Refer to Razorpay developer documentation
> for the current endpoint.

**Response:**

```json
{
  "delegate_id": "c894aa29a7da69",
  "cryptogram_value": "a345345dfgdfasdfh45jtyhgjkyutsdasd2",
  "expired_at": 1748716199
}
```

> Cryptograms are **single-use** — NPCI rejects reuse. Fetch a fresh cryptogram
> for each transaction. Do not cache or reuse across retries.

#### Step 3: Build Instrument + Credential (Minting Credential)

```json
{
  "id": "pi_001",
  "handler_id": "razorpay_upi_circle",
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
UCP-Agent: profile="https://agent.example/profile"

{
  "payment": {
    "instruments": [
      {
        "id": "pi_001",
        "handler_id": "razorpay_upi_circle",
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
  },
  "risk_signals": {
    "ip_address": "203.0.113.42",
    "user_agent": "Mozilla/5.0..."
  }
}
```

#### Step 5: Handle Response

The Complete Checkout response falls into one of four shapes:

**Synchronous success** — Business responds directly with `completed`:

```json
{
  "id": "checkout_abc123",
  "status": "completed",
  "order": {
    "id": "order_xyz789",
    "permalink_url": "https://store.com/orders/xyz789"
  }
}
```

**Async processing** — Business returns `complete_in_progress`. Platform **MUST** poll `GET /checkout-sessions/{id}` until a terminal status is reached:

```json
{
  "id": "checkout_abc123",
  "status": "complete_in_progress"
}
```

**Failure** — Business returns `canceled` with structured `messages`:

```json
{
  "id": "checkout_abc123",
  "status": "canceled",
  "messages": [
    {
      "type": "recoverable",
      "code": "cryptogram_expired",
      "message": "The cryptogram has expired. Please retry."
    }
  ]
}
```

**Escalation** — Business returns `requires_escalation` (e.g. partial delegation awaiting primary holder approval):

```json
{
  "id": "checkout_abc123",
  "status": "requires_escalation",
  "escalation": {
    "type": "upi_circle_pending",
    "message": "Awaiting approval from primary account holder."
  }
}
```

#### Polling Logic

When `complete_in_progress` or `requires_escalation` is received, the platform
**MUST** poll with exponential backoff. Terminal statuses are `completed` and
`canceled`. Maximum polling window is **2 minutes**.

```javascript
const POLL_CONFIG = {
  initialDelayMs: 2000,   // start at 2 s
  maxDelayMs: 10000,      // cap at 10 s
  backoffFactor: 1.5,     // multiply delay each round
  timeoutMs: 120000,      // 2-minute hard stop
};

async function pollCheckout(checkoutId) {
  const deadline = Date.now() + POLL_CONFIG.timeoutMs;
  let delayMs = POLL_CONFIG.initialDelayMs;

  while (Date.now() < deadline) {
    await sleep(delayMs);

    let checkout;
    try {
      checkout = await getCheckout(checkoutId);
    } catch (err) {
      // Network error — retry without advancing backoff
      continue;
    }

    switch (checkout.status) {
      case "completed":
        return { success: true, order: checkout.order };

      case "canceled":
        return { success: false, messages: checkout.messages };

      case "complete_in_progress":
      case "requires_escalation":
        // Non-terminal — keep polling
        break;

      default:
        // Unknown status — treat as non-terminal, keep polling
        break;
    }

    // Advance backoff, capped at maxDelayMs
    delayMs = Math.min(delayMs * POLL_CONFIG.backoffFactor, POLL_CONFIG.maxDelayMs);
  }

  return { success: false, reason: "timeout", checkoutId };
}
```

#### Error Handling After Poll

| `messages[].type` | Action |
| :---------------- | :----- |
| `recoverable` | Fetch a fresh cryptogram and retry Complete Checkout (max 2 retries) |
| `requires_buyer_input` | Surface `messages[].message` to buyer (e.g. limit exceeded, mandate expired) |
| `timeout` (poll result) | Show generic failure; do **not** retry automatically |

> For `recoverable` retries, always call the cryptogram API again — never reuse
> the previous cryptogram, even if its `expired_at` has not yet passed.

---

## PSP Integration (Razorpay)

### Delegated Debit Processing

When the business submits a `upi_circle` instrument with a
`upi_circle_cryptogram` credential, Razorpay PSP:

1. **Resolves the mandate** — looks up the UMN (Unique Mandate Number) from `delegate_id`.
2. **Validates the cryptogram** — confirms it is valid, unexpired, and matches the delegation.
3. **Initiates delegated debit via NPCI** — sends a debit request within the mandate's
   configured limits. No MPIN required from the buyer.
4. **Receives NPCI response** — SUCCESS, FAILURE, or PENDING.
5. **Sends webhook to business** — `payment.authorized` or `payment.failed`.

### Razorpay AI Commerce TSP as a Credential Provider: Delegation Setup and Cryptogram Issuance

Razorpay acts as the **Credential Provider** — analogous to Google Pay's token
API or Stripe's Shared Payment Token (SPT) API. The cryptogram issuance
operation accepts a `delegate_id` and returns a single-use cryptogram:

| Operation                    | Method | Purpose                     |
| :--------------------------- | :----- | :--------------------------- |
| Delegation Setup          | POST   | Delegating the payment mandate to the platform  |
| Cryptogram issuance          | POST   | Issue a one-time cryptogram  |



**Response:**

```json
{
  "delegate_id": "c894aa29a7da69",
  "cryptogram_value": "a345345dfgdfasdfh45jtyhgjkyutsdasd2",
  "expired_at": 1748716199
}
```

The cryptogram is:
- **Single-use** — rejected on second attempt by NPCI.
- **Time-limited** — expires per `expired_at`.
- **Delegation-scoped** — valid only for the specific `delegate_id`.
- **Not merchant-scoped** — merchant identity comes from the payment request,
  not the token (differs from Stripe SPT).

---

## Error Handling

| NPCI / Mandate Error                  | UCP `code`         | `severity`            | Platform Action                                       |
| :------------------------------------ | :----------------- | :-------------------- | :---------------------------------------------------- |
| Mandate limit exceeded (per-txn)      | `payment_declined` | `requires_buyer_input`| Lower amount or use a different payment method        |
| Mandate limit exceeded (monthly)      | `payment_declined` | `requires_buyer_input`| Wait for limit reset or use a different payment method|
| Mandate expired                       | `payment_declined` | `requires_buyer_input`| Re-initiate delegation setup                          |
| Mandate delinked (buyer revoked)      | `payment_declined` | `requires_buyer_input`| Re-initiate delegation setup                          |
| Cryptogram expired                    | `payment_declined` | `recoverable`         | Fetch new cryptogram and retry                        |
| Cryptogram invalid / already used     | `payment_declined` | `recoverable`         | Fetch new cryptogram and retry                        |
| Insufficient balance                  | `payment_declined` | `recoverable`         | Suggest adding funds to primary account               |
| Bank error                            | `payment_declined` | `recoverable`         | Retry in 5 minutes                                    |
| NPCI downtime                         | `payment_declined` | `recoverable`         | Retry in 15 minutes                                   |

**Error Response Example:**

```json
{
  "status": "canceled",
  "messages": [
    {
      "type": "error",
      "code": "payment_declined",
      "severity": "requires_buyer_input",
      "content": "Monthly UPI delegation limit exceeded. Please increase your limit in your UPI app or use a different payment method.",
      "path": "$.payment"
    }
  ]
}
```

---

## Security Considerations

| Requirement                     | Description                                                                                                                                             |
| :------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Cryptogram single-use**       | Each cryptogram authorizes exactly one debit. NPCI rejects reuse. Platform MUST fetch a fresh cryptogram per transaction.                               |
| **Cryptogram expiry**           | Cryptograms are time-limited. Platform MUST check `expires_at` before submitting and fetch a new one if expired.                                        |
| **Mandate limits**              | Per-transaction and monthly limits are configured by the buyer at delegation setup and enforced by NPCI/bank. Cannot be overridden by platform or business.|
| **Mandate lifecycle**           | Buyer can delink (revoke) the mandate at any time from their UPI app. Platform MUST handle `mandate expired` and `mandate delinked` errors gracefully.   |
| **No PII in credential**        | The cryptogram is an opaque authorization token. It does not contain VPA, account number, or any buyer PII.                                             |
| **Data residency (RBI)**        | All payment records and delegation data MUST be stored in India data centers per RBI data localization mandate.                                          |
| **Webhook signature**           | Business MUST verify `X-Razorpay-Signature` on every webhook via `HMAC_SHA256(body, webhook_secret)` before updating checkout state.                    |
| **Idempotency**                 | Business MUST ensure each cryptogram is processed exactly once to prevent double-charge.                                                                |
| **Delegation setup security**   | Setup requires OTP verification + MPIN inside the buyer's UPI app. The platform never sees the buyer's MPIN or bank credentials.                        |
| **PCI-DSS scope**               | Zero for all participants — no card data, no CVV/PIN at payment time.                                                                                   |
| **TLS/HTTPS only**              | All API communication MUST use HTTPS with TLS 1.2+.                                                                                                    |

---

## Testing

### End-to-End Test Checklist

- [ ] Schemas pass JSON Schema draft 2020-12 validation.
- [ ] `snake_case` field names throughout.
- [ ] `const` type discriminators: `upi_circle` on instrument, `upi_circle_cryptogram` on credential.
- [ ] Instrument extends `payment_instrument.json` via `allOf`.
- [ ] Credential extends `payment_credential.json` via `allOf`.
- [ ] No `additionalProperties: false` on instrument or credential schemas.
- [ ] No base fields redeclared in extending schemas.
- [ ] `expires_at` uses RFC 3339 format.
- [ ] `delegate_id` required on instrument; `cryptogram` required on credential.
- [ ] Business profile at `/.well-known/ucp` declares `com.razorpay.upi_circle` with correct `key_id` and `environment`.
- [ ] Platform completes delegation setup and holds a `delegate_id` with `status: linked`.
- [ ] Platform calls Razorpay to fetch cryptogram immediately before Complete Checkout.
- [ ] Platform does **not** reuse a cryptogram across two transactions.
- [ ] Platform checks `expires_at` before submitting and fetches a fresh cryptogram if needed.
- [ ] Business processes cryptogram and responds `status: completed` — no escalation.
- [ ] Business receives `payment.authorized` webhook; verifies `X-Razorpay-Signature`.
- [ ] `payment.failed` webhook (limit exceeded / mandate revoked) triggers `canceled` with correct error.
- [ ] Platform handles `complete_in_progress` by polling until `completed` or `canceled`.
- [ ] Platform surfaces `requires_buyer_input` errors to buyer (mandate limit, mandate expired).
- [ ] Platform retries with fresh cryptogram on `recoverable` errors (cryptogram expired/invalid).
- [ ] `mkdocs build` completes without errors.

---

## References

| Resource                         | URL                                                                                    |
| :------------------------------- | :------------------------------------------------------------------------------------- |
| Razorpay Developer Docs          | `https://razorpay.com/docs/`                                                           |
| UCP Checkout Specification       | [checkout.md](checkout.md)                                                             |
| UCP Payment Handler Guide        | [payment-handler-guide.md](payment-handler-guide.md)                                  |
| UCP Payment Handler Template     | [payment-handler-template.md](payment-handler-template.md)                            |
| Base `payment_instrument.json`   | `https://ucp.dev/{{ ucp_version }}/schemas/shopping/types/payment_instrument.json`    |
| Base `payment_credential.json`   | `https://ucp.dev/{{ ucp_version }}/schemas/shopping/types/payment_credential.json`    |
| NPCI UPI Circle / Delegation     | `https://www.npci.org.in/what-we-do/upi/product-overview`                             |
| Stripe SPT (comparable pattern)  | `https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens`             |
