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

# Buyer Consent Extension

## Overview

The Buyer Consent extension lets businesses communicate the consent options they
offer and lets platforms transmit buyers' consent decisions for data usage and
communication preferences — purposes like marketing, analytics, preferences, and
sale or sharing of data.

Consent is modeled as a two-level structure:

- **Purpose** — what the consent is for. Keyed at the top level by a
    reverse-DNS identifier (e.g., `dev.ucp.consent.marketing`). Each purpose
    carries an `allowed` state, a human-readable `description`, and optional
    `links`.
- **Segment** — an optional refinement scoping the parent purpose to a
    specific channel (e.g., email, SMS), vendor (e.g., a measurement provider),
    or program. Each segment has the same shape (`allowed`, `description`,
    optional `links`) and overrides the parent purpose for its specific scope.

The structure is bounded to one level of nesting: purposes have segments;
segments do not nest further.

## Scope

This extension defines the mechanism by which businesses and platforms establish
and communicate buyer consent state. It does not dictate either party's behavior
in response to that state — how a business acts on it (e.g., sending emails,
sharing data) and how a platform surfaces existing decisions to the buyer (e.g.,
displaying current subscription state with an unsubscribe affordance) are
governed by business policy and applicable regulation, not by this
specification.

Businesses are responsible for selecting the initial `allowed` value according
to applicable policy and regulation before advertising consent options. In
contexts that require affirmative opt-in, the business SHOULD advertise
`allowed: false` until the buyer chooses otherwise. In contexts that allow
opt-out, the business MAY advertise `allowed: true` as a default the buyer can
override. The protocol carries the precomputed `allowed` value; policy and
regulatory reasoning remain the business's responsibility.

## Discovery

Businesses advertise consent support in their profile. The capability can extend
cart, checkout, or both:

<!-- ucp:example schema=profile def=business_schema extract=$.capabilities target=$.ucp.capabilities -->

```json
{
  "capabilities": {
    "dev.ucp.shopping.buyer_consent": [
      {
        "version": "{{ ucp_version }}",
        "extends": [
          "dev.ucp.shopping.cart",
          "dev.ucp.shopping.checkout"
        ]
      }
    ]
  }
}
```

## Schema Composition

When this capability is active, the **buyer object** within cart and/or checkout
carries a `consent` field:

- **Cart path**: `cart.buyer.consent`
- **Checkout path**: `checkout.buyer.consent`

The `buyer` object (and therefore `consent`) is optional on all cart and
checkout operations — cart `create` / `update`, and checkout `create` / `update`
/ `complete`. Platforms MAY submit captured consent on `complete_checkout`
alongside payment.

## Schema Definition

### Consent Object

A map of per-purpose consent decisions. Keys are reverse-DNS purpose identifiers
such as `dev.ucp.consent.marketing` or `com.example.purpose.loyalty`. Values are
[Consent Purpose](#consent-purpose) objects. A purpose may contain nested
[Consent Segment](#consent-segment) refinements for channel, vendor, or program
scopes.

### Consent Purpose

{{ extension_schema_fields('buyer_consent.json#/$defs/consent_purpose', 'buyer-consent') }}

### Consent Segment

{{ extension_schema_fields('buyer_consent.json#/$defs/consent_segment', 'buyer-consent') }}

## Well-known purposes

This extension defines four well-known purpose identifiers under the
`dev.ucp.consent.*` namespace. Businesses may define additional purposes under
reverse-DNS namespaces they control. These identifiers are operational
definitions, not legal taxonomies.

| Identifier                        | Purpose                                                   |
| --------------------------------- | --------------------------------------------------------- |
| `dev.ucp.consent.analytics`       | Analytics and performance measurement                     |
| `dev.ucp.consent.marketing`       | Marketing communications                                  |
| `dev.ucp.consent.preferences`     | Remembering buyer preferences                             |
| `dev.ucp.consent.sale_or_sharing` | Sale or sharing of personal data with third parties       |

## Well-known segments

For the `dev.ucp.consent.marketing` purpose, this extension defines well-known
channel segment identifiers:

| Identifier                        | Channel |
| --------------------------------- | ------- |
| `dev.ucp.consent.marketing.email` | Email   |
| `dev.ucp.consent.marketing.sms`   | SMS     |

## Advertise and confirm

The same map shape carries two complementary directions of information:

| Direction                | Who populates | Fields populated                                               |
| ------------------------ | ------------- | -------------------------------------------------------------- |
| **Advertise** (response) | Business      | `description`, `links`, current `allowed`, optional `segments` |
| **Confirm** (request)    | Platform      | captured `allowed`, optional `segments`                        |

`description` and `links` are response-only; the platform does not echo them on
confirm. `allowed` is required in both directions: businesses send the current
or default state when advertising; platforms send the captured decision when
confirming.

### Advertise example

Businesses advertise available purposes and segments with the current consent
state (either the buyer's prior decision or the business default):

<!-- ucp:example schema=shopping/buyer_consent def=consent op=read extract=$.buyer.consent -->

```json
{
  "ucp": { ... },
  "id": "checkout_456",
  "status": "ready_for_complete",
  "currency": "USD",
  "buyer": {
    "consent": {
      "dev.ucp.consent.marketing": {
        "allowed": false,
        "description": "Promotional communications across all channels",
        "links": [{ "type": "privacy_policy", "url": "https://example.com/privacy" }],
        "segments": {
          "dev.ucp.consent.marketing.email": {
            "allowed": false,
            "description": "Promotional emails and exclusive offers"
          },
          "dev.ucp.consent.marketing.sms": {
            "allowed": false,
            "description": "Marketing text messages",
            "links": [{ "type": "terms_of_service", "url": "https://example.com/sms-terms" }]
          },
          "com.example.channel.marketing": {
            "allowed": false,
            "description": "Marketing messages via a third-party channel"
          }
        }
      },
      "dev.ucp.consent.analytics": {
        "allowed": true,
        "description": "Site analytics and performance measurement",
        "segments": {
          "com.example.analytics": {
            "allowed": false,
            "description": "Third-party analytics measurement",
            "links": [{ "type": "privacy_policy", "url": "https://example.com/analytics-privacy" }]
          }
        }
      },
      "dev.ucp.consent.preferences": {
        "allowed": true,
        "description": "Remember preferences and personalize the shopping experience"
      },
      "dev.ucp.consent.sale_or_sharing": {
        "allowed": false,
        "description": "Sale or sharing of personal data with third parties",
        "links": [{ "type": "privacy_policy", "url": "https://example.com/privacy" }]
      }
    }
  }
}
```

### Confirm example

Platforms submit current consent decisions in a subsequent `update_checkout` or
`complete_checkout` request, with buyer changes applied to the advertised
settings:

<!-- ucp:example schema=shopping/buyer_consent def=consent op=complete direction=request extract=$.buyer.consent -->

```json
{
  "buyer": {
    "consent": {
      "dev.ucp.consent.marketing": {
        "allowed": false,
        "segments": {
          "dev.ucp.consent.marketing.email": { "allowed": true },
          "dev.ucp.consent.marketing.sms": { "allowed": false },
          "com.example.channel.marketing": { "allowed": false }
        }
      },
      "dev.ucp.consent.analytics": {
        "allowed": true,
        "segments": {
          "com.example.analytics": { "allowed": false }
        }
      },
      "dev.ucp.consent.preferences": { "allowed": true },
      "dev.ucp.consent.sale_or_sharing": { "allowed": false }
    }
  }
}
```

## Data dependencies

Some consent states depend on additional buyer or checkout data. For example,
SMS marketing consent may require a buyer phone number. When required data is
missing, the business SHOULD use standard `messages[]` warnings or errors to
inform the platform or buyer.

For example:

<!-- ucp:example schema=shopping/checkout target=$.messages op=read -->

```json
[
  {
    "type": "warning",
    "code": "missing_consent_data",
    "content": "Phone number is required for SMS marketing.",
    "path": "$.buyer.phone_number"
  }
]
```

## Normative requirements

1. **Use the advertised settings.** Platforms MUST initialize and present
   consent using the advertised `description`, `links`, provided `allowed`
   values, and purpose/segment grouping. Identifiers are opaque handles; agents
   MUST NOT infer semantics from identifier paths alone.

2. **Complete confirm.** When submitting consent, platforms MUST include every
   advertised purpose and segment key, carrying either the advertised `allowed`
   value or the buyer's captured change.

3. **Advertised set is authoritative.** Businesses MUST ignore purposes and
   segments in a request that were not advertised in a prior response. Platforms
   MUST NOT prompt for or transmit purposes or segments the business did not
   advertise.

4. **More-specific values win.** For an advertised segment, the segment's
   `allowed` value overrides the parent purpose's `allowed` for that segment.
