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
    carries a `checked` state, a `source` identifying who asserted that state,
    a human-readable `description`, and optional `links`.
- **Segment** — an optional refinement scoping the parent purpose to a
    specific channel (e.g., email, SMS), vendor (e.g., a measurement provider),
    or program. Each segment has the same shape (`checked`, `source`,
    `description`, optional `links`) and overrides the parent purpose for its
    specific scope.

The structure is bounded to one level of nesting: purposes have segments;
segments do not nest further.

The protocol carries only the binary state and its source attribution.
The operational meaning of `checked: true` vs `false` (granted, denied,
enabled, subscribed) is defined by the consent context — not by the field
name or by the protocol.

## Scope

This extension defines the mechanism by which businesses and platforms establish
and communicate buyer consent state. It does not dictate either party's behavior
in response to that state — how a business acts on it (e.g., sending emails,
sharing data) and how a platform surfaces existing decisions to the buyer (e.g.,
displaying current subscription state with an unsubscribe affordance) are
governed by business policy and applicable regulation, not by this
specification.

Businesses are responsible for selecting the initial `checked` value according
to their applicable policy before advertising consent options. The advertised
value with `source: "business"` is the business's authoritative default;
buyers may override it through the platform. Policy reasoning remains the
business's responsibility.

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

| Direction                | Who populates | Fields populated                                                          |
| ------------------------ | ------------- | ------------------------------------------------------------------------- |
| **Advertise** (response) | Business      | `checked`, `source`, `description`; `links` and `segments` when present   |
| **Confirm** (request)    | Platform      | `checked`, `source`; `segments` when present                              |

`description` and `links` are response-only; the platform does not echo them on
confirm. `checked` and `source` are required in both directions: businesses
send the current state and its source when advertising; platforms send the
current state and its source when confirming.

The `source` field carries the authorship of the current `checked` value:

- `source: "business"` means the value reflects the business's default; no
  buyer preference applies.
- `source: "platform"` means the value reflects the buyer's stated
  preference, captured by the platform.

The source signals how the platform should treat the current value:
`source: "business"` invites the platform to present the choice for buyer
engagement; `source: "platform"` indicates a recorded buyer preference that
MAY persist across subsequent transactions with the same business. Platforms
MAY suppress re-presentation.

### Example: purposes and segments

The simplest case is purpose-level consent capture — `analytics` here shows
the buyer's consent recorded at the parent. Purposes can also carry segments
for finer-grained control: `marketing` is set to off, but the buyer has
consented to SMS marketing. The segment's `checked: true`
overrides the parent's `checked: false` for that scope (more-specific values
win).

<!-- ucp:example schema=shopping/buyer_consent def=consent op=read extract=$.buyer.consent -->

```json
{
  "ucp": { ... },
  "id": "checkout_456",
  "status": "ready_for_complete",
  "currency": "USD",
  "buyer": {
    "consent": {
      "dev.ucp.consent.analytics": {
        "checked": true,
        "source": "platform",
        "description": "Site analytics and performance measurement"
      },
      "dev.ucp.consent.marketing": {
        "checked": false,
        "source": "business",
        "description": "Promotional communications",
        "segments": {
          "dev.ucp.consent.marketing.email": {
            "checked": false,
            "source": "business",
            "description": "Promotional emails"
          },
          "dev.ucp.consent.marketing.sms": {
            "checked": true,
            "source": "platform",
            "description": "Marketing text messages"
          }
        }
      }
    }
  }
}
```

The buyer has engaged with two specific choices (analytics broadly, SMS
marketing specifically); both carry `source: "platform"`. The remaining
values (parent `marketing`, `email` segment) carry `source: "business"`.

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
        "checked": false,
        "source": "business",
        "description": "Promotional communications across all channels",
        "links": [{ "type": "privacy_policy", "url": "https://example.com/privacy" }],
        "segments": {
          "dev.ucp.consent.marketing.email": {
            "checked": true,
            "source": "platform",
            "description": "Promotional emails and exclusive offers"
          },
          "dev.ucp.consent.marketing.sms": {
            "checked": false,
            "source": "business",
            "description": "Marketing text messages",
            "links": [{ "type": "terms_of_service", "url": "https://example.com/sms-terms" }]
          },
          "com.example.channel.marketing": {
            "checked": false,
            "source": "business",
            "description": "Marketing messages via a third-party channel"
          }
        }
      },
      "dev.ucp.consent.analytics": {
        "checked": true,
        "source": "business",
        "description": "Site analytics and performance measurement",
        "segments": {
          "com.example.analytics": {
            "checked": false,
            "source": "business",
            "description": "Third-party analytics measurement",
            "links": [{ "type": "privacy_policy", "url": "https://example.com/analytics-privacy" }]
          }
        }
      },
      "dev.ucp.consent.preferences": {
        "checked": true,
        "source": "business",
        "description": "Remember preferences and personalize the shopping experience"
      },
      "dev.ucp.consent.sale_or_sharing": {
        "checked": false,
        "source": "platform",
        "description": "Sale or sharing of personal data with third parties",
        "links": [{ "type": "privacy_policy", "url": "https://example.com/privacy" }]
      }
    }
  }
}
```

In this example, the buyer has previously opted in to promotional email
(`marketing.email` shows `source: "platform"`) and previously opted out of
data sale (`sale_or_sharing` shows `source: "platform"`). Every other choice
remains at its business-asserted default and is a candidate for the platform
to surface for explicit capture.

### Confirm example

Platforms submit the current state of every advertised purpose and segment in a
subsequent `update_checkout` or `complete_checkout` request. For each choice,
the platform echoes the advertised `checked` and `source` when no buyer
preference applies, or sets `source: "platform"` with the buyer's stated
`checked` value when one does.

<!-- ucp:example schema=shopping/buyer_consent def=consent op=complete direction=request extract=$.buyer.consent -->

```json
{
  "buyer": {
    "consent": {
      "dev.ucp.consent.marketing": {
        "checked": true,
        "source": "platform",
        "segments": {
          "dev.ucp.consent.marketing.email": { "checked": true,  "source": "platform" },
          "dev.ucp.consent.marketing.sms":   { "checked": true,  "source": "platform" },
          "com.example.channel.marketing":   { "checked": false, "source": "business" }
        }
      },
      "dev.ucp.consent.analytics": {
        "checked": true,
        "source": "business",
        "segments": {
          "com.example.analytics": { "checked": false, "source": "business" }
        }
      },
      "dev.ucp.consent.preferences":     { "checked": true,  "source": "business" },
      "dev.ucp.consent.sale_or_sharing": { "checked": false, "source": "platform" }
    }
  }
}
```

Here, the buyer opted in to marketing on email and SMS; other choices are
echoed at their advertised values, including `sale_or_sharing` which retains
a prior platform-captured choice.

## Data dependencies

Some consent states depend on additional buyer or checkout data. For example,
SMS marketing consent requires a buyer phone number. When the
platform confirms a consent value whose required dependency is missing,
businesses surface the gap through the standard [Checkout Status
Lifecycle](checkout.md#checkout-status-lifecycle) and [Error
Handling](checkout.md#error-handling) mechanisms.

On `create_cart`, `update_cart`, `create_checkout`, and `update_checkout`,
businesses SHOULD surface missing dependencies as `warning` messages so the
platform can collect the data on a subsequent operation. The advertised
consent decisions remain valid; the warning is informational.

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

On `complete_checkout`, businesses MUST NOT transition the checkout to
`completed` while a confirmed consent decision has unmet data dependencies.
Missing dependencies MUST be surfaced via the standard [Error
Handling](checkout.md#error-handling) flow.

## Normative requirements

1. **Use the advertised settings.** Businesses MUST advertise the complete
   set of consent options they support. Platforms decide which choices to
   present to the buyer and when; when presenting a choice, platforms MUST
   use the advertised `description`, `links`, `checked` value, and
   purpose/segment grouping. The `source` field informs platform decisions
   (see [Advertise and confirm](#advertise-and-confirm)) and is not
   user-facing content. Identifiers outside the `dev.ucp.consent.*` namespace
   are opaque handles; platforms MUST NOT infer semantics from such paths
   alone. UCP-defined identifiers carry the semantics established in this
   specification.

2. **Confirm semantics.** The `consent` field is optional on requests;
   omitting it provides no consent update and the business retains its prior
   position. When submitting `consent`, platforms MUST include every advertised
   purpose and segment key, carrying both `checked` and `source` for each.
   Omitting an advertised key within a submitted `consent` map MUST NOT be
   used to signal any value.

3. **Advertised set is authoritative.** Businesses MUST ignore purposes and
   segments in a request that were not advertised in a prior response. Platforms
   MUST NOT prompt for or transmit purposes or segments the business did not
   advertise.

4. **More-specific values win.** For an advertised segment, the segment's
   `checked` value overrides the parent purpose's `checked` for that segment.

5. **Source attribution requires a buyer-stated preference.** Platforms MUST
   set `source: "platform"` only when the `checked` value reflects the buyer's
   stated preference. For choices to which no buyer preference applies,
   platforms MUST echo the advertised `source` unchanged. The protocol does
   not prescribe what counts as a buyer-stated preference; that determination
   is made by the platform under applicable policy.

6. **Per-business attribution.** A consent decision captured with a specific
   business is attributable only to that business; platforms MUST NOT
   propagate it as the basis for `source: "platform"` in a different business's
   request. Broader buyer preferences that are not tied to a specific business
   are independent of per-business decisions and may be applied to each
   business's advertised choices on their own basis.

7. **Buyer review and revocation.** Platforms MUST provide a way for buyers
   to audit and revoke or change prior consent decisions.
