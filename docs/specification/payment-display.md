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

# Payment Display Extension

* **Capability Name:** `com.mercadopago.payments.display`
* **Schema:** `https://ucp.dev/schemas/shopping/payment_display.json`

## Overview

The Payment Display extension lets a Business complete an **in-session,
out-of-band payment method** — such as **Pix** in Brazil — without redirecting
the buyer or handing off a `continue_url`. When the buyer chooses such a method,
the Business surfaces an **inert display artifact** (a QR image, a
copy-and-paste code, and/or hosted instructions) as an outstanding Action on the
checkout. The Platform renders it, the buyer pays in their bank app, and the
**same** Complete Checkout operation resolves once payment is confirmed.

This is a concrete, vendor-namespaced Action type stacked on the generic
[Actions](overview.md#actions) primitive. It defines the Action type
`com.mercadopago.payments.display` and the shape of its `config`.

**Key features:**

* Display Pix (and equivalent QR/code methods) natively — no iframe, no redirect
* Works across surfaces: web, native app, and voice (a `code` fallback exists
  when no screen can show an image)
* Payment resolves in-session by polling Get Checkout — the Platform never
  re-drives Complete
* Strict render/trust contract: display data only, inert fields, single
  allowlisted loadable field

**Dependencies:**

* Checkout Capability
* The [Actions](overview.md#actions) primitive on Checkout

## Discovery

Businesses advertise this extension in their profile, extending the Checkout
capability:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "com.mercadopago.payments.display": [
        {
          "version": "{{ ucp_version }}",
          "extends": ["dev.ucp.shopping.checkout"],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/payment-display",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/payment_display.json"
        }
      ]
    }
  }
}
```

## Schema

When this extension is active, the checkout `actions` map MAY carry outstanding
`com.mercadopago.payments.display` instances. Each instance is a common Action
instance (`id`, optional `config`) whose `config` is the display artifact below.

### Payment Display Config

{{ extension_schema_fields('payment_display.json#/$defs/config', 'payment_display') }}

At least one of `code`, `image`, or `instructions_url` MUST be present so the
Platform always has something renderable.

## Render and Trust Contract

The artifact carries **public display data only** and is designed to be safe to
render on any surface. Implementations MUST honor the following:

* **No secrets transit the artifact.** It never contains a PAN, CVV, OTP,
  token, credential, or any other sensitive value — only data already meant to
  be shown to the buyer.
* **`image` is inert.** It is rendered as a static image only. The Platform MUST
  NOT execute, interpret, or fetch it as anything other than image bytes, and
  MUST restrict it to `data:` or `https:` URIs.
* **`code` is display text.** The Platform SHOULD present it with a copy
  affordance. It MUST NOT be interpreted as a URL, deep link, or executable
  content.
* **`instructions_url` is the only loadable field.** When present, the Platform
  MUST constrain it to an `https:` origin allowlist advertised for the handler,
  MUST open it as a plain document, and MUST NOT auto-submit forms or forward
  buyer data to it.
* **`expires_at` bounds the artifact.** After it passes, the Platform stops
  rendering the artifact and re-fetches checkout state rather than continuing to
  show a stale QR/code.

## Resolution Flow

```text
1. Platform → Business : Complete Checkout (buyer chose Pix)
2. Business → Platform : status = complete_in_progress
                         actions {
                           "com.mercadopago.payments.display": [
                             { "id": "...", "config": { "type": "qr_code", ... } }
                           ]
                         }
3. Platform            : renders QR image + copy button for `code`
                         (works on web / native / voice — no frame)
4. Buyer               : pays via bank app (out of band)
5. Platform → Business : polls Get Checkout (MUST NOT re-drive Complete)
6. Mercado Pago        : confirms payment → Business resolves
7. Business → Platform : status = completed, order present, Action gone
```

On expiry or failure, the Business returns the checkout with a `recoverable`
error [Message](overview.md#messages) whose `path` points at the exact Action
occurrence, e.g. `$.actions['com.mercadopago.payments.display'][0]`. The Platform
surfaces the recovery path (for example, refreshing the artifact) rather than
re-driving Complete.

## Scope: In-Session vs. Out-of-Session Settlement

This extension covers artifacts that resolve **within the checkout session's
lifetime**: the Business holds the checkout in `complete_in_progress`, the buyer
pays out of band, and the Platform observes the outcome by polling Get Checkout
before the session's viability window closes.

The dividing line is **not the payment method** but **whether settlement
completes while the checkout session is still alive**:

* **In-session (this extension).** The artifact's `expires_at` fits within the
  session's viability window, so the outcome is observable by polling — for
  example, an immediate Pix QR paid within minutes.
* **Out-of-session (out of scope here).** Settlement may land after the checkout
  session is gone — for example, **Pix with a long expiry or due date (Pix com
  vencimento)**, boleto, or cash vouchers. A Platform cannot hold
  `complete_in_progress` open for hours or days, so these MUST NOT be surfaced
  as a checkout Action resolved by polling. They belong to an order-level flow
  where the same display artifact lives on the `order` and the outcome arrives
  via an order lifecycle webhook (addressed separately).

Note that the discriminator is temporal, not the method label: a long-expiry
Pix charge behaves like boleto for this purpose. Accordingly, a Business using
this extension MUST issue an artifact whose `expires_at` is bounded by the
checkout session's viability; if the intended expiry exceeds it, use the
order-level async-payment flow instead.
