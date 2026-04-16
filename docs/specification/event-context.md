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

# Event Context Extension

## Overview

The Event Context extension enables referring platforms to pass referral context
and deduplication keys through agentic checkout flows. When a user discovers a
product through an external channel (a paid ad, an organic recommendation, an
influencer link, or an AI agent's suggestion) and completes a purchase via
agentic checkout, the merchant loses the referral context they normally receive
via URL parameters on their landing page. This extension preserves that data.

**Key features:**

- Pass structured UTM parameters for compatibility with existing analytics tools
- Provide deduplication keys so merchants can reconcile agentic transactions
  with their server-side reporting
- Support any referring platform via reverse domain naming
- Pass platform-specific identifiers through an opaque `custom` field

**Dependencies:**

- Cart Capability or Checkout Capability

## Discovery

Businesses advertise event context support in their profile:

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.event_context": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.cart",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/event-context",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/event_context.json"
        },
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.checkout",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/event-context",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/event_context.json"
        }
      ]
    }
  }
}
```

## Schema Composition

The event context extension extends both **cart** and **checkout** objects:

- **Base schemas extended**: `cart.json`, `checkout.json`
- **Path**: `cart.event_context`, `checkout.event_context`
- **Schema reference**: `event_context.json`

The `event_context` property is composed onto each object via `allOf`,
following the same extension pattern as `fulfillment.json` and `discount.json`.

## Schema Definition

### Event Context Payload

The `event_context` object contains referral context from the platform that
drove the cart or checkout:

| Field         | Type   | Required | Description                                                                                                                                               |
|---------------|--------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| `platform`    | string | Yes      | Referring platform identifier using reverse domain naming (e.g., `com.google`, `com.meta`)                                                                |
| `dedup_keys`  | object | No       | Deduplication keys for reconciling with the merchant's server-side reporting                                                                              |
| `utm`         | object | No       | Standard UTM parameters for web analytics compatibility                                                                                                   |
| `custom`      | object | No       | Platform-specific key-value pairs routed by the merchant based on the `platform` field. Values MUST be string, number, or boolean. Maximum 20 properties. |

### Deduplication Keys

The `dedup_keys` object prevents double-counting when both the referring
platform and the merchant report the same transaction independently. If
present, at least one key MUST be provided:

| Field        | Type   | Description                                                                            |
|--------------|--------|----------------------------------------------------------------------------------------|
| `event_id`   | string | Shared dedup key for reconciling with the merchant's server-side reporting             |
| `session_id` | string | Platform session identifier for cross-event correlation (e.g., `fbp`, `ga_session_id`) |

### UTM Parameters

Standard UTM parameters for compatibility with web analytics tools (Google
Analytics, Northbeam, Triple Whale, etc.):

| Field                  | Type   | Description                                                          |
|------------------------|--------|----------------------------------------------------------------------|
| `utm_source`           | string | Traffic source                                                       |
| `utm_medium`           | string | Marketing medium                                                     |
| `utm_campaign`         | string | Campaign name                                                        |
| `utm_content`          | string | Content identifier                                                   |
| `utm_term`             | string | Search term                                                          |
| `utm_id`               | string | Campaign ID                                                          |
| `utm_source_platform`  | string | Advertising platform that served the ad (e.g., Google, Meta, TikTok) |

### Request Behavior

The `event_context` property supports the following operations:

| Operation  | Behavior   | Description                                     |
|------------|------------|-------------------------------------------------|
| `create`   | `optional` | Platform MAY include event context on create    |
| `update`   | `optional` | Platform MAY update event context               |
| `complete` | `optional` | Platform MAY include event context on complete  |

## Privacy Note

This extension replaces referral context and conversion signals that
traditionally flow from the referring platform to the business via the
merchant's website. When a purchase occurs through an agentic flow, the website
is bypassed and these signals would otherwise be lost. While the fields
primarily carry marketing and campaign metadata, some values — such as click
identifiers and session identifiers in `dedup_keys` or `custom` — may be
considered advertising data subject to user consent under applicable privacy
regulations.

Implementations **MUST**:

- Only use event context data for the purposes of conversion measurement,
  reporting, attribution, and analytics
- **NOT** transmit personally identifiable information (e.g., email addresses,
  phone numbers, names) through any field in this extension
- Comply with applicable consent requirements for advertising and marketing
  data in the jurisdictions where they operate

## Usage Examples

### Google (Google Ads / Gemini)

A user discovers a product through a Google Shopping ad and completes the
purchase via Gemini's agentic checkout:

```json
{
  "event_context": {
    "platform": "com.google",
    "dedup_keys": {
      "event_id": "evt_abc123def456"
    },
    "utm": {
      "utm_source": "google",
      "utm_medium": "cpc",
      "utm_campaign": "spring_collection_2026",
      "utm_content": "60123456789",
      "utm_id": "18234567890",
      "utm_source_platform": "Google"
    },
    "custom": {
      "click_id": "EAIaIQobChMI8bXe7...",
      "ad_group_id": "142345678901",
      "placement": "Google_Shopping",
      "gbraid": "WVLA4QjBkaJkZW..."
    }
  }
}
```

The merchant includes this `event_id` when reporting the conversion via their
server-side integration to prevent double-counting.

### Meta

A user discovers a product through Meta's platform and their AI agent completes
the purchase:

```json
{
  "event_context": {
    "platform": "com.meta",
    "dedup_keys": {
      "event_id": "evt_abc123def456",
      "session_id": "fb.1.1710300000000.1234567890"
    },
    "utm": {
      "utm_source": "meta",
      "utm_medium": "paid_social",
      "utm_campaign": "spring_sale_2026",
      "utm_content": "6861203971771",
      "utm_id": "6861196821371",
      "utm_source_platform": "Meta"
    },
    "custom": {
      "click_id": "IwY2xjawOR56Fle...",
      "placement": "Meta_AI"
    }
  }
}
```

The merchant passes `event_id` and `fbp` (from `session_id`) to their
Conversions API integration. The shared `event_id` prevents duplicate event
counting between the platform's first-party event and the merchant's server-side
event.
