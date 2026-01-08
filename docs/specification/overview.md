<!--
   Copyright 2025 UCP Authors

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

# Universal Commerce Protocol (UCP) Official Specification

**Version:** `2026-01-11`

## 1. Introduction

The Universal Commerce Protocol (UCP) is an open standard designed to facilitate
communication and interoperability between diverse commerce entities. In a
fragmented landscape where consumer surfaces/platforms, businesses, payment
providers, and identity providers operate on different systems, UCP provides
a standardized common language and functional primitives.

This document provides the detailed technical specification for UCP.
For a complete definition of all data models and schemas, see the [Schema Reference](reference.md).

Its primary goal is to enable:

*   **Consumer Surfaces/Platforms:** To discover business capabilities and
    facilitate purchases.
*   **Businesses:** To expose their inventory and retail logic in a standard
    way without building custom integrations for every platform.
*   **Payment & Credential Providers:** To securely exchange tokens and
    credentials to facilitate transactions.

### 1.1. Key Goals of UCP

*   **Interoperability:** Bridge the gap between consumer surfaces, businesses,
    and payment ecosystems.
*   **Discovery:** Allow consumer surfaces to dynamically discover what a
    business supports (e.g., "Do they support guest checkout?", "Do they have
    loyalty programs?").
*   **Security:** Facilitate secure, standards-based (OAuth 2.0, PCI-DSS
    compliant patterns) exchanges of sensitive user and payment data.
*   **Agentic Commerce:** Enable AI agents to act on behalf of users to complete
    complex tasks like "Find a headset under $100 and buy it."

### 1.2. Guiding Principles

The design and evolution of UCP are driven by the following core principles:

*   **Scalability & Universality:** The interface must scale to support diverse
    commerce entities—from small individual businesses to large enterprise store
    builders—across various locales, identity providers, and payment ecosystems
    without friction.
*   **Simplicity & Developer Experience:** We prioritize a clean, simple
    interface that is easy to implement for businesses and platforms alike.
    Complexity should be opt-in via extensions, not forced upon the core.
*   **Extensibility & Openness:** The protocol is designed as an extensible
    framework. It allows for future growth and community-driven Capabilities
    (e.g., new vertical supports) to pave the way for adoption as an
    industry-wide standard.
*   **Business Centricity (MoR Neutrality):** The business remains as Merchant
    of Record (MoR). UCP facilitates the transaction and data exchange, but the
    business retains ownership of the order, financial liability, and customer
    relationship. The platform acts as a facilitator, staying in the loop for
    order events to assist the user.
*   **Security & Privacy by Design:** The protocol must support strict
    enterprise-grade security and privacy standards. It ensures that sensitive
    data (PII, Payment Credentials) is handled securely, leveraging existing
    standards like OAuth 2.0 and minimizing data exposure.
*   **Multi-Modal & Future-Proof:** The specification is agnostic to the
    interaction surface. It supports experiences across diverse current and
    future modalities, including text-based chat, voice interfaces, visual
    commerce, and autonomous "auto-buy" scenarios.
*   **Frictionless Payments:** The protocol supports an open wallet ecosystem.
    It is designed to reduce friction by enabling interoperability between
    various Payment Service Providers (PSPs) and Credential Providers (CPs),
    ensuring users can pay with their preferred methods.

## 2. Roles & Participants

UCP defines the interactions between four primary distinct actors, each playing
a specific role in the commerce lifecycle.

### 2.1. Platform (Application/Agent)

The platform is the consumer-facing surface (such as an AI agent, mobile app, or
social media site) acting on behalf of the User. It orchestrates the commerce
journey by discovering businesses and facilitating user intent.

*   **Responsibilities:** Discovering business capabilities via profiles,
    initiating checkout sessions, and presenting the UI or conversational
    interface to the user.
*   **Examples:** AI Shopping Assistants, Super Apps, Search Engines.

### 2.2. Business

The entity selling goods or services. In the UCP model, the business acts as the
**Merchant of Record (MoR)**, retaining financial liability and ownership of the
order.

*   **Responsibilities:** Exposing commerce capabilities (inventory, pricing,
    tax calculation), fulfilling orders, and processing payments via their
    chosen PSP.
*   **Examples:** Retailers, Airlines, Hotel Chains, Service Providers.

### 2.3. Credential Provider (CP)

A trusted entity responsible for securely managing and sharing sensitive user
data, particularly payment instruments and shipping addresses.

*   **Responsibilities:** Authenticating the user, issuing payment tokens (to
    keep raw card data off the platform), and holding PII securely to minimize
    compliance scope for other parties.
*   **Examples:** Digital Wallets (e.g., Google Wallet, Apple Pay), Identity
    Providers.

### 2.4. Payment Service Provider (PSP)

The financial infrastructure provider that processes payments on behalf of the
business.

*   **Responsibilities:** Authorizing and capturing transactions, handling
    settlements, and communicating with card networks. The PSP often interacts
    directly with tokens provided by the Credential Provider.
*   **Examples:** Stripe, Adyen, PayPal, Braintree, Chase Paymentech.

## 3. Core Concepts Summary

UCP revolves around three fundamental constructs that define how entities
interact.

*   **Capabilities:** Standalone core features that a business supports. These
    are the "verbs" of the protocol.
    *   *Examples:* Checkout, Identity Linking, Order.
*   **Extensions:** Optional modules that augment a specific Capability. They
    allow for specialized functionality without bloating the core Capability.
    *   *Examples:* Discounts (extends Checkout), AP2 Mandates (extends
        Checkout).
*   **Transports:** The lower-level communication layers used to exchange data.
    UCP is transport-agnostic but defines specific bindings for
    interoperability.
    *   *Examples:* REST API (primary), MCP (Model Context Protocol), A2A
        (Agent2Agent).

## 4. Overarching guidelines

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT,
RECOMMENDED, MAY, and OPTIONAL in this document are to be interpreted as
described in RFC 2119 and RFC 8174.

Schema notes:

-   Date format: Always specified as RFC 3339 unless otherwise specified
-   Amounts format: Minor units (cents)

## 5. Discovery, Governance, and Negotiation

UCP employs a server-selects architecture where the business (server) chooses
the protocol version and capabilities from the intersection of both parties'
capabilities. Both business and platform profiles can be cached by both parties,
allowing efficient capability negotiation within the normal request/response
flow between platform and business.

### 5.1 Namespace Governance

UCP uses reverse-domain naming to encode governance authority directly into
capability identifiers. This eliminates the need for a central registry.

#### 5.1.1 Naming Convention

All capability and service names MUST use the format:

```
{reverse-domain}.{service}.{capability}
```

**Components:**

-   `{reverse-domain}` - Authority identifier derived from domain ownership
-   `{service}` - Service/vertical category (e.g., `shopping`, `common`)
-   `{capability}` - The specific capability name

**Examples:**

| Name                                | Authority   | Service  | Capability       |
| ----------------------------------- | ----------- | -------- | ---------------- |
| `dev.ucp.shopping.checkout`         | ucp.dev     | shopping | checkout         |
| `dev.ucp.shopping.fulfillment`      | ucp.dev     | shopping | fulfillment      |
| `dev.ucp.common.identity_linking`   | ucp.dev     | common   | identity_linking |
| `com.example.payments.installments` | example.com | payments | installments     |

#### 5.1.2 Spec URL Binding

The `spec` and `schema` fields are REQUIRED for all capabilities. The origin
of these URLs MUST match the namespace authority:

| Namespace       | Required Origin           |
| --------------- | ------------------------- |
| `dev.ucp.*`     | `https://ucp.dev/...`     |
| `com.example.*` | `https://example.com/...` |

Platform MUST validate this binding and SHOULD reject capabilities where the
spec origin does not match the namespace authority.

#### 5.1.3 Governance Model

| Namespace Pattern | Authority    | Governance          |
| ----------------- | ------------ | ------------------- |
| `dev.ucp.*`       | ucp.dev      | UCP governing body  |
| `com.{vendor}.*`  | {vendor}.com | Vendor organization |
| `org.{org}.*`     | {org}.org    | Organization        |

The `dev.ucp.*` namespace is reserved for capabilities sanctioned by the UCP
governing body. Vendors MUST use their own reverse-domain namespace for
custom capabilities.

### 5.2 Services

A **service** defines the API surface for a vertical (shopping, common, etc.).
Services include operations, events, and transport bindings defined via
standard formats:

-   **REST**: OpenAPI 3.x (JSON format)
-   **MCP**: OpenRPC (JSON format)
-   **A2A**: Agent Card Specification
-   **Embedded**: OpenRPC (JSON format)

#### 5.2.1 Service Definition

| Field           | Type   | Required | Description                          |
| --------------- | ------ | -------- | ------------------------------------ |
| `version`       | string | Yes      | Service version (YYYY-MM-DD format)  |
| `spec`          | string | Yes      | URL to service documentation         |
| `rest`          | object | No       | REST transport binding               |
| `rest.schema`   | string | Yes      | URL to OpenAPI spec (JSON)           |
| `rest.endpoint` | string | Yes      | Business's REST endpoint             |
| `mcp`           | object | No       | MCP transport binding                |
| `mcp.schema`    | string | Yes      | URL to OpenRPC spec (JSON)           |
| `mcp.endpoint`  | string | Yes      | Business's MCP endpoint              |
| `a2a`           | object | No       | A2A transport binding                |
| `a2a.endpoint`  | string | Yes      | Business's A2A Agent Card URL        |
| `embedded`      | string | No       | Embedded transport binding           |
|`embedded.schema`| string | Yes      | URL to OpenRPC spec (JSON)           |

Transport definitions MUST be thin: they declare method names and reference
base schemas only. See [5.4.1 Requirements](#541-requirements) for details.

#### 5.2.2 Endpoint Resolution

The `endpoint` field provides the base URL for API calls. OpenAPI paths are
appended to this endpoint to form the complete URL.

**Example:**

```json
"rest": {
  "schema": "https://ucp.dev/services/shopping/rest.openapi.json",
  "endpoint": "https://business.example.com/api/v2"
}
```

With OpenAPI path `/checkout-sessions`, the resolved URL is:
```
POST https://business.example.com/api/v2/checkout-sessions
```

**Rules:**

-   `endpoint` MUST be a valid URL with scheme (https)
-   `endpoint` SHOULD NOT have a trailing slash
-   OpenAPI paths are relative and appended directly to endpoint
-   Same resolution applies to MCP endpoints for JSON-RPC calls
-   `endpoint` for A2A transport refers to the Agent Card URL for the agent

### 5.3 Capabilities

A **capability** is a feature within a service. It declares what
functionality is supported and where to find documentation and schemas.

#### 5.3.1 Capability Definition

{{ extension_schema_fields('capability.json#/$defs/discovery', 'capability-schema') }}

#### 5.3.2 Extensions

An **extension** is an optional module that augments another capability.
Extensions use the `extends` field to declare their parent:

```json
{
  "name": "dev.ucp.shopping.fulfillment",
  "version": "2026-01-11",
  "spec": "https://ucp.dev/specs/shopping/fulfillment",
  "schema": "https://ucp.dev/schemas/shopping/fulfillment.json",
  "extends": "dev.ucp.shopping.checkout"
}
```

Extensions can be:

-   **Official**: `dev.ucp.shopping.fulfillment` extends `dev.ucp.shopping.checkout`
-   **Vendor**: `com.example.installments` extends `dev.ucp.shopping.checkout`

### 5.4 Schema Composition

Extensions can add new fields and modify shared structures (e.g., discounts
modify `totals`, fulfillment adds fulfillment to `totals.type`).

#### 5.4.1 Requirements

-   Transport definitions (OpenAPI/OpenRPC) MUST reference base schemas only.
    They MUST NOT enumerate fields or define payload shapes inline.
-   Extensions MUST be self-describing. Each extension schema MUST declare
    the types it introduces and how it modifies base types using `allOf`
    composition.
-   Clients MUST resolve schemas client-side by fetching and composing
    base schemas with active extension schemas.

#### 5.4.2 Extension Schema Pattern

Extension schemas define composed types using `allOf`. An example is as follows:

```json
{
  "$defs": {
    "discounts_object": { ... },
    "checkout": {
      "allOf": [
        {"$ref": "checkout.json"},
        {
          "type": "object",
          "properties": {
            "discounts": {
              "$ref": "#/$defs/discounts_object"
            }
          }
        }
      ]
    }
  }
}
```

Composed type names MUST use the pattern: `{capability-name}.{TypeName}`

#### 5.4.3 Resolution Flow

Platforms MUST resolve schemas following this sequence:

1.  **Discovery**: Fetch business profile from `/.well-known/ucp`
2.  **Negotiation**: Compute capability intersection (see
    [5.7.3](#573-intersection-algorithm))
3.  **Schema Fetch**: Fetch base schema and all active extension schemas
4.  **Compose**: Merge schemas via `allOf` chains based on active extensions
5.  **Validate**: Validate requests and responses against the composed schema

### 5.5 Profile Structure

#### 5.5.1 Business Profile

Businesses publish their profile at `/.well-known/ucp`. An example:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "services": {
      "dev.ucp.shopping": {
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specs/shopping",
        "rest": {
          "schema": "https://ucp.dev/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp/v1"
        },
        "mcp": {
          "schema": "https://ucp.dev/services/shopping/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
        }
      }
    },
    "capabilities": [
      {
        "name": "dev.ucp.shopping.checkout",
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specs/shopping/checkout",
        "schema": "https://ucp.dev/schemas/shopping/checkout.json"
      },
      {
        "name": "dev.ucp.shopping.fulfillment",
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specs/shopping/fulfillment",
        "schema": "https://ucp.dev/schemas/shopping/fulfillment.json",
        "extends": "dev.ucp.shopping.checkout"
      },
      {
        "name": "dev.ucp.shopping.discount",
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specs/shopping/discount",
        "schema": "https://ucp.dev/schemas/shopping/discount.json",
        "extends": "dev.ucp.shopping.checkout"
      }
    ]
  },
  "payment": {
    "handlers": [
      {
        "id": "merchant_tokenizer",
        "name": "dev.ucp.merchant_tokenizer",
        "version": "2026-01-11",
        "spec": "https://example.com/specs/payments/merchant_tokenizer-payment",
        "config_schema": "https://ucp.dev/schemas/payments/delegate-payment.json",
        "instrument_schemas": [
          "https://ucp.dev/schemas/shopping/types/card_payment_instrument.json"
        ],
        "config": {
          "endpoint": "https://merchant.example.com/tokenize",
          "public_key": "pk_live_abc123",
          "creates": "merchant.token"
        }
      }
    ]
  },
  "signing_keys": [
    {
      "kid": "merchant_2025",
      "kty": "EC",
      "crv": "P-256",
      "x": "WbbXwVYGdJoP4Xm3qCkGvBRcRvKtEfXDbWvPzpPS8LA",
      "y": "sP4jHHxYqC89HBo8TjrtVOAGHfJDflYxw7MFMxuFMPY",
      "use": "sig",
      "alg": "ES256"
    }
  ]
}
```

The `ucp` object contains protocol metadata: version, services, and
capabilities. Payment configuration is a sibling—see
[Payment Architecture](#6-payment-architecture). The `signing_keys` array
contains public keys (JWK format) used to verify signatures on webhooks and
other authenticated messages from the merchant.

#### 5.5.2 Platform Profile

Platform profiles are similar and include signing keys for capabilities
requiring cryptographic verification. Capabilities may include a `config` object
for capability-specific settings (e.g., callback URLs, feature flags). An
example:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {
        "name": "dev.ucp.shopping.checkout",
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specs/shopping/checkout",
        "schema": "https://ucp.dev/schemas/shopping/checkout.json"
      },
      {
        "name": "dev.ucp.shopping.fulfillment",
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specs/shopping/fulfillment",
        "schema": "https://ucp.dev/schemas/shopping/fulfillment.json",
        "extends": "dev.ucp.shopping.checkout"
      },
      {
        "name": "dev.ucp.shopping.order",
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specs/shopping/order",
        "schema": "https://ucp.dev/schemas/shopping/order.json",
        "config": {
          "webhook_url": "https://platform.example.com/webhooks/ucp/orders"
        }
      }
    ]
  },
  "payment": {
    "handlers": [
      {
        "id": "gpay",
        "name": "com.google.pay",
        "version": "2024-12-03",
        "spec": "https://ucp.dev/handlers/google_pay",
        "config_schema": "https://ucp.dev/handlers/google_pay/config.json",
        "instrument_schemas": [
          "https://ucp.dev/handlers/google_pay/card_payment_instrument.json"
        ]
      },
      {
        "id": "merchant_tokenizer",
        "name": "com.example.merchant_tokenizer",
        "version": "2026-01-11",
        "spec": "https://example.com/specs/payments/merchant_tokenizer",
        "config_schema": "https://example.com/specs/payments/merchant_tokenizer.json",
        "instrument_schemas": [
          "https://ucp.dev/schemas/shopping/types/card_payment_instrument.json"
        ]
      }
    ]
  },
  "signing_keys": [
    {
      "kid": "agent_2025",
      "kty": "EC",
      "crv": "P-256",
      "x": "MKBCTNIcKUSDii11ySs3526iDZ8AiTo7Tu6KPAqv7D4",
      "y": "4Etl6SRW2YiLUrN5vfvVHuhp7x8PxltmWWlbbM4IFyM",
      "use": "sig",
      "alg": "ES256"
    }
  ]
}
```

### 5.6 Platform Advertisement on Request

Platforms MUST communicate their profile URI with each request to enable
capability negotiation.

**HTTP Transport:** Platforms MUST use Dictionary Structured Field syntax
([RFC 8941](https://datatracker.ietf.org/doc/html/rfc8941)) in the UCP-Agent
header:

```
POST /checkout HTTP/1.1
UCP-Agent: profile="https://agent.example/profiles/shopping-agent.json"
Content-Type: application/json

{"line_items": [...]}
```

**MCP Transport:** Platforms MUST use native dictionary structure in
`_meta.ucp`:

```json
{
  "jsonrpc": "2.0",
  "method": "create_checkout",
  "params": {
    "_meta": {
      "ucp": {
        "profile": "https://agent.example/profiles/shopping-agent.json"
      }
    },
    "line_items": [...]
  },
  "id": 1
}
```

### 5.7 Negotiation Protocol

#### 5.7.1 Platform Requirements

1.  **Profile Advertisement**: Platforms MUST include their profile URI in every
    request using the transport-appropriate mechanism.
2.  **Discovery**: Platforms MAY fetch the business profile from
    `/.well-known/ucp` before initiating requests. If fetched, platforms
    SHOULD cache the profile according to HTTP cache-control directives.
3.  **Namespace Validation**: Platforms MUST validate that capability `spec` URL
    origins match namespace authorities.
4.  **Schema Resolution**: Platforms MUST fetch and compose schemas for
    negotiated capabilities before making requests.

#### 5.7.2 Business Requirements

1.  **Profile Resolution**: Upon receiving a request with an platform profile
    URI, businesses MUST fetch and validate the platform profile unless already
    cached.
2.  **Capability Intersection**: Businesses MUST compute the intersection of
    platform and business capabilities.
3.  **Extension Validation**: Extensions without their parent capability in the
    intersection MUST be excluded.
4.  **Response Requirements**: Businesses MUST include the `ucp` field in every
    response containing:
    -   `version`: The UCP version used to process the request
    -   `capabilities`: Array of active capabilities for this response

#### 5.7.3 Intersection Algorithm

The capability intersection algorithm determines which capabilities are active
for a session:

1.  **Compute intersection**: For each business capability, include it in the
    result if a platform capability with the same `name` exists.

2.  **Prune orphaned extensions**: Remove any capability where `extends` is
    set but the parent capability is not in the intersection.

3.  **Repeat pruning**: Continue step 2 until no more capabilities are removed
    (handles transitive extension chains).

The result is the set of capabilities both parties support, with extension
dependencies satisfied.

#### 5.7.4 Error Handling

If negotiation fails, businesses MUST return an error response:

```json
{
  "status": "error",
  "errors": [{
    "code": "VERSION_UNSUPPORTED",
    "message": "Version 2025-11-01 is not supported.",
    "severity": "critical"
  }]
}
```

#### 5.7.5 Capability Declaration in Responses

The `capabilities` array in responses indicates active capabilities:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {"name": "dev.ucp.shopping.checkout", "version": "2026-01-11"},
      {"name": "dev.ucp.shopping.fulfillment", "version": "2026-01-11"}
    ]
  },
  "id": "checkout_123",
  "line_items": [...]
}
```

## 6. Payment Architecture

UCP adopts a decoupled architecture for payments to solve the "N-to-N"
complexity problem between Platforms, Businesses, and Payment Providers by
separating payment methods (what types of payment are accepted) from payment
handlers (how instruments are acquired). This separation enables critical
capabilities: businesses can support multiple processing strategies for the same
payment instrument (e.g., accepting cards via direct tokenization, wallet apps),
platforms can choose the most appropriate handler based on their capabilities
and user preferences, and new payment handlers and instruments can be introduced
and adopted by the ecosystem in a permissionless way.

### 6.1 Payment in the Checkout Lifecycle

Payment is an integral part of the UCP checkout flow, not a standalone
transaction. The `payment` field is a required component of every checkout
response, enabling the following communication pattern between businesses and
platforms:

**Step 1: Checkout Creation — Handler Advertisement (Business → Platform)**

When a platform creates or updates a checkout, the business includes available
payment handlers in the response:

```json
POST /checkout-sessions HTTP/1.1
Content-Type: application/json
UCP-Agent: profile="https://agent.example/profile"

{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [...]
  },
  "id": "chk_123",
  "status": "incomplete",
  "line_items": [...],
  "currency": "USD",
  "payment": {
    "handlers": [
      // Payment handler configurations
    ]
  }
}
```

The `payment.handlers` array advertises which payment collection strategies the
business supports. Each handler tells the platform: "Here's how you can acquire
a payment instrument for me." This is a **response-only field**—businesses
advertise handlers, platforms never send them.

**Step 2: Instrument Acquisition — Client-Side Processing (Platform)**

The platform selects a compatible handler based on:

- Its own capabilities (e.g., can it execute Google Pay API calls?)
- User preferences (e.g., saved payment methods)
- Handler requirements (e.g., supported card networks)

The platform then executes the handler's protocol (defined by its `spec` URL) to
acquire a payment instrument. This happens **outside the business's checkout
API**—the handler protocol may involve calling PSP endpoints, launching wallet
UIs, or delegating to payment platforms. The business is not involved in this
step.

**Optional: Display Info for Embedded Checkout (Platform → Business)**

For embedded checkout scenarios, platforms MAY submit instruments with display
information (WITHOUT credentials) during checkout updates:

```json
PATCH /checkout-sessions/{id}
Request:
{
  "id": "chk_123",
  "line_items": [...],
  "currency": "USD",
  "payment": {
    "instruments": [{
      "id": "instr_1",
      "handler_id": "card_tokenizer",
      "type": "card",
      "brand": "visa",
      "last_digits": "4242"
      // Note: NO credential field - display info only
    }],
    "selected_instrument_id": "instr_1"
  }
}
```

This allows embedded checkout platforms to show which payment method will be
used in their UI before the actual completion. The `selected_instrument_id`
indicates which instrument from the array is selected. Credentials are NOT
included at this stage.

**Step 3: Checkout Completion — Credential Submission (Platform → Business)**

Once the platform is ready to complete the checkout, it submits the payment
instrument WITH credentials for payment processing:

```json
POST /checkout-sessions/{id}/complete
Content-Type: application/json

{
  "payment_data": {
    "id": "instr_1",
    "handler_id": "card_tokenizer",
    "type": "card",
    "brand": "visa",
    "last_digits": "4242",
    "credential": {
      "type": "token",
      "token": "tok_visa_123"
    }
  }
}
```

**Important: Display Info vs Credentials in Instruments**

Payment instruments have two distinct components that flow at different stages:

-   **Display Information** (brand, last 4 digits, billing address):
    -   Optional and only needed for **embedded checkout scenarios**
    -   Submitted by agents during checkout creation/updates (WITHOUT credentials)
    -   Enables embedded checkout platforms to show which payment method will be
        used in the UI
    -   Echoed back by businesses in responses
    -   Safe to display to users
-   **Credentials** (payment tokens, encrypted data):
    -   ONLY submitted by agents during checkout **completion**
    -   Required for payment processing—businesses cannot process payment without
        credentials

The `handler_id` links the instrument back to a handler configuration, telling
the business which integration to use for processing (e.g., which PSP endpoint,
which decryption key).

This architecture allows businesses to remain agnostic about how instruments are
acquired. The business only needs to:
1. Advertise which handlers it supports
2. Process the resulting instruments using its existing PSP integrations

The handler protocol (how instruments are acquired) is defined externally and
can evolve independently of the checkout API.

#### Example Configuration

This example shows the `payment` field from a checkout response:

```json
{
  "payment": {
    "handlers": [
      {
        "id": "merchant_tokenizer",
        "name": "com.example.merchant_tokenizer",
        "version": "2026-01-11",
        "spec": "https://example.com/specs/payments/merchant_tokenizer",
        "config_schema": "https://example.com/specs/payments/merchant_tokenizer.json",
        "instrument_schemas": [
          "https://ucp.dev/schemas/shopping/types/card_payment_instrument.json"
        ],
        "config": {
          "type": "CARD",
          "tokenization_specification": {
            "type": "PUSH",
            "parameters": {
              "token_retrieval_url": "https://api.psp.com/v1/tokens"
            }
          }
        }
      },
      {
        "id": "gpay",
        "name": "com.google.pay",
        "version": "2024-12-03",
        "spec": "https://ucp.dev/handlers/google_pay",
        "config_schema": "https://ucp.dev/handlers/google_pay/config.json",
        "instrument_schemas": [
          "https://ucp.dev/handlers/google_pay/card_payment_instrument.json"
        ],
        "config": {
          "allowed_payment_methods": [{
            "type": "CARD",
            "parameters": {
              "allowed_card_networks": ["VISA", "MASTERCARD", "AMEX"]
            }
          }]
        }
      },
      {
        "id": "shop_pay",
        "name": "dev.shopify.shop_pay",
        "version": "2026-01-11",
        "spec": "https://shopify.dev/docs/api/shop-pay-handler",
        "config_schema": "https://shopify.dev/ucp/shop-pay-handler/2026-01-11/config.json",
        "instrument_schemas": [
          "https://shopify.dev/ucp/shop-pay-handler/2026-01-11/instrument.json"
        ],
        "config": {
          "shop_id": "shopify-559128571"
        }
      }
    ]
  }
}
```

This configuration tells platforms what payment collection strategies the
business supports: PSP tokenization for direct card tokenization, Google Pay
for wallet payments, and Shop Pay for Shopify's accelerated checkout.

### 6.2 Payment Handlers

Payment handlers are capability declarations that define how the business can
collect payment instruments. They form a contract between businesses, platforms,
and payment providers:

-   A payment provider defines the handler specification, exposing a schema for
    custom payment instruments, token types, and a handler config. As well the
    provider defines a protocol for the platform to execute when processing the
    handler. This setup allows for a variety of different payment methods and
    token-types to be supported in the flow, including network tokens.
-   A business must implement support for receiving the defined instruments and
    tokens, as well as expose the well-structured handler config.
-   A platform must execute the handler's defined protocol to process the
    business's provided handler config and negotiate the resulting instrument
    into the business's checkout.

Following the same pattern as other UCP capabilities, handlers are
self-describing with namespaced identifiers, with independent versioning, and
external specifications.

#### Handler Structure

Each handler declaration contains:

| Field                | Type   | Required | Description                                                                          |
| :------------------- | :----- | :------- | :----------------------------------------------------------------------------------- |
| `id`                 | String | Yes      | Unique identifier for this handler instance (e.g., `gpay_handler`, `network_token`)                   |
| `name`               | String | Yes      | Handler type name using reverse-DNS identifier (e.g., com.google.pay, com.vendor.custom_handler)      |
| `version`            | String | Yes      | The version of the handler specification.                                            |
| `spec`               | String | Yes      | URI to the human-readable documentation for this handler.                            |
| `config_schema`      | String | Yes      | URI to the JSON schema validating the `config`.                                      |
| `instrument_schemas` | Array  | Yes      | Array of URIs to JSON schemas defining the payment instruments this handler produces.|
| `config`             | Object | Yes      | Handler-specific configuration as defined by the handler specification               |

Note: This schema is extensible. Additional fields may be present.

#### Namespace

Handlers follow the same reverse-DNS namespace convention as capabilities:

*   dev.ucp.\*: Core handlers defined by this specification
*   com.vendor.\*: Extension handlers defined by payment providers
*   Examples: com.google.pay, dev.shopify.shop_pay, com.stripe.tokenization

#### Example Handler Declarations

```json
{
  "payment": {
    "handlers": [
      {
        "id": "merchant_tokenizer",
        "name": "com.example.merchant_tokenizer",
        "version": "2026-01-11",
        "spec": "https://example.com/specs/payments/merchant_tokenizer",
        "config_schema": "https://example.com/specs/payments/merchant_tokenizer.json",
        "instrument_schemas": [
          "https://ucp.dev/schemas/shopping/types/card_payment_instrument.json"
        ],
        "config": {
          "type": "CARD",
          "tokenization_specification": {
            "type": "PUSH",
            "parameters": {
              "token_retrieval_url": "https://api.psp.com/v1/tokens"
            }
          }
        }
      },
      {
        "id": "gpay",
        "name": "com.google.pay",
        "version": "2024-12-03",
        "spec": "https://ucp.dev/handlers/google_pay",
        "config_schema": "https://ucp.dev/handlers/google_pay/config.json",
        "instrument_schemas": [
          "https://ucp.dev/handlers/google_pay/card_payment_instrument.json"
        ],
        "config": {
          "allowed_payment_methods": [{
            "type": "CARD",
            "parameters": {
              "allowed_card_networks": ["VISA", "MASTERCARD"]
            },
            "tokenization_specification": {
              "type": "PAYMENT_GATEWAY",
              "parameters": {
                "gateway": "stripe",
                "gateway_merchant_id": "acme_inc"
              }
            }
          }]
        }
      },
      {
        "id": "shop_pay",
        "name": "dev.shopify.shop_pay",
        "version": "2026-01-11",
        "spec": "https://shopify.dev/docs/api/shop-pay-handler",
        "config_schema": "https://shopify.dev/ucp/shop-pay-handler/2026-01-11/config.json",
        "instrument_schemas": [
          "https://shopify.dev/ucp/shop-pay-handler/2026-01-11/instrument.json"
        ],
        "config": {
          "shop_id": "shopify-559128571"
        }
      }
    ]
  }
}
```

This example illustrates a business supporting multiple payment processing
strategies. The card_tokenizer handler uses PSP
for secure tokenization of raw card credentials. The gpay handler integrates
with Google Pay for wallet-based payments. The shop_pay handler enables
Shopify's accelerated checkout experience. These handlers would be advertised in
the business's discovery profile, allowing platforms to understand capabilities
before starting a transaction. Additionally, the available payment handlers are
provided in Cart and Checkout responses, where they may be dynamically filtered
based on cart contents, buyer location, or other transaction-specific factors.

#### Handler Lifecycle and Dynamic Filtering

Payment handlers are not static—they can change during the checkout session as
conditions evolve. Understanding handler lifecycle is critical for platforms
implementing robust checkout flows.

**Initial Advertisement**

When a checkout is created, businesses MUST provide all potentially applicable
handlers based on the initial checkout state (line items, currency, buyer
information if known). This initial set represents the broadest possible payment
options available.

**Dynamic Filtering During Updates**

As the checkout progresses and more information becomes available, businesses
MAY filter the handlers array based on:

-   **Cart Contents**: Certain products may restrict payment methods (e.g., age-
    restricted items, high-value goods, subscriptions requiring recurring
    payments)
-   **Buyer Location**: Payment methods have geographic availability (e.g.,
    regional wallet providers, country-specific bank transfers)
-   **Transaction Amount**: Handlers may have minimum/maximum limits (e.g., buy-
    now-pay-later services with $50-$1000 limits)
-   **Fulfillment Method**: Shipping vs pickup vs digital delivery may affect
    available payment options
-   **Business Rules**: Time-of-day restrictions, fraud prevention rules, or
    promotional payment method requirements

**Example: Location-Based Filtering**

```json
// Initial checkout (no address provided)
{
  "payment": {
    "handlers": [
      {"id": "card", "name": "com.example.merchant_tokenizer", ...},
      {"id": "gpay", "name": "com.google.pay", ...},
      {"id": "shop_pay", "name": "dev.shopify.shop_pay", ...},
      {"id": "example_pay", "name": "com.example.pay", ...}
    ]
  }
}

// After address update (buyer in Netherlands)
PATCH /checkout-sessions/{id}
Request: {
  "id": "chk_123",
  "line_items": [...],
  "currency": "USD",
  "payment": {...},
  "fulfillment_address": {"address_country": "NL", ...}
}

Response: {
  "ucp": {...},
  "id": "chk_123",
  "status": "incomplete",
  "line_items": [...],
  "currency": "USD",
  "payment": {
    "handlers": [
      {"id": "card", "name": "com.example.merchant_tokenizer", ...},
      {"id": "gpay", "name": "com.google.pay", ...},
      {"id": "shop_pay", "name": "dev.shopify.shop_pay", ...}
      // example_pay filtered out - not available in Netherlands
    ]
  }
}
```

**Handler Stability Guarantee**

Once a checkout reaches `ready_for_complete` status, handlers SHOULD NOT change
unless the checkout state is modified (e.g., line items updated, address
changed). This allows platforms to cache handler information and begin
instrument acquisition with confidence.

If checkout state changes significantly after `ready_for_complete`, businesses
MAY return the checkout to `incomplete` status and update the handlers array
accordingly.

**Handling Orphaned Instruments**

If a platform submits a completion request with an instrument referencing a
`handler_id` that is not in the current handlers array, businesses MUST reject
the request with an error:

```json
{
  "status": "requires_escalation",
  "messages": [{
    "type": "error",
    "code": "invalid_handler_id",
    "content": "The handler 'example_pay' is no longer available for this checkout.",
    "severity": "requires_buyer_input"
  }]
}
```

**Platform Implementation Guidance**

Platforms SHOULD:
1. Refresh handler information after significant checkout updates (address,
   line items, totals changes)
2. Validate that the selected handler is still present before beginning
   credential acquisition
3. Handle `invalid_handler_id` errors gracefully by re-fetching checkout state
   and prompting for new payment method selection

### 6.3 Custom Payment Handlers

Payment providers and businesses can define custom handlers by following the
capability pattern. Each handler is self-describing through its specification
URL and can define its own configuration schema.

#### Example: Google Pay Payment Handler

The `com.google.pay` handler demonstrates integration with a customized
[specification](site:specification/gpay-payment-handler):

```json
{
  "id": "gpay",
  "name": "com.google.pay",
  "version": "2024-12-03",
  "spec": "https://ucp.dev/handlers/google_pay",
  "config_schema": "https://ucp.dev/handlers/google_pay/config.json",
  "instrument_schemas": [
    "https://ucp.dev/handlers/google_pay/card_payment_instrument.json"
  ],
  "config": {
    "allowed_payment_methods": [
      {
        "type": "CARD",
        "parameters": {
          "allowed_auth_methods": [
            "PAN_ONLY",
            "CRYPTOGRAM_3DS"
          ],
          "allowed_card_networks": [
            "VISA",
            "MASTERCARD",
            "AMEX",
            "DISCOVER"
          ]
        },
        "tokenization_specification": {
          "type": "PAYMENT_GATEWAY",
          "parameters": {
            "gateway": "stripe",
            "gateway_merchant_id": "acme_inc"
          }
        }
      }
    ],
    "merchant_info": {
      "merchant_id": "BCR2DN4TWXXXXXX",
      "merchant_name": "Acme Store"
    },
    "environment": "PRODUCTION"
  }
}
```

This handler implements Google Pay's configuration standard, showing how UCP
integrates with payment specifications rather than reinventing them.

#### Creating Your Own Handler

A complete handler definition requires three components: a **handler
declaration**, a **JSON Schema** for the config, and a **specification
document** describing the protocol.

##### Step 1: Choose a Namespace

Use your organization's reverse-DNS domain to ensure uniqueness:

```
{reverse-domain}.{category}.{handler_name}
```

For example, if ACME Corporation (acme.com) creates a "pay later" handler:
`com.acme.payments.pay_later`

##### Step 2: Define the Handler Config Schema

Create a JSON Schema that validates the `config` object businesses must provide.
The schema defines what configuration businesses expose, enabling agents to
understand how to invoke your payment method.

**Example Schema** (`https://acme.com/ucp/schemas/pay_later_handler.json`):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://acme.com/ucp/schemas/pay_later_handler.json",
  "title": "AcmePayLaterHandlerConfig",
  "description": "Configuration schema for the com.acme.pay_later handler.",
  "type": "object",
  "required": ["client_id", "environment", "payment_options"],
  "properties": {
    "client_id": {
      "type": "string",
      "description": "The merchant's ACME client identifier, obtained from the ACME Merchant Portal."
    },
    "environment": {
      "type": "string",
      "enum": ["sandbox", "production"],
      "description": "The ACME environment to use for API calls."
    },
    "locale": {
      "type": "string",
      "description": "Preferred locale for ACME UI elements (e.g., 'en-US', 'de-DE').",
      "default": "en-US"
    },
    "payment_options": {
      "type": "array",
      "description": "Available ACME payment options the merchant supports.",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["type"],
        "properties": {
          "type": {
            "type": "string",
            "enum": ["pay_in_4", "pay_in_30", "financing"],
            "description": "The ACME payment option type."
          },
          "min_amount": {
            "type": "integer",
            "description": "Minimum order amount in minor units (cents)."
          },
          "max_amount": {
            "type": "integer",
            "description": "Maximum order amount in minor units (cents)."
          }
        }
      }
    },
    "session_endpoint": {
      "type": "string",
      "format": "uri",
      "description": "ACME session creation endpoint. Defaults to ACME's standard API."
    }
  }
}
```

##### Step 3: Define the Instrument Schema (Optional)

If your handler produces custom instrument types, define a schema for the
payment instrument structure agents will submit:

**Example Instrument Schema**
(`https://acme.com/ucp/schemas/pay_later_instrument.json`):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://acme.com/ucp/schemas/pay_later_instrument.json",
  "title": "AcmePayLaterInstrument",
  "description": "Payment instrument structure for ACME Pay Later.",
  "allOf": [
    {
      "$ref": "https://ucp.dev/schemas/shopping/types/payment_instrument.json"
    },
    {
      "type": "object",
      "properties": {
        "type": {
          "const": "acme_pay_later"
        },
        "credential": {
          "type": "object",
          "required": ["type", "token"],
          "properties": {
            "type": {
              "type": "string",
              "enum": ["acme_session", "acme_authorization"],
              "description": "Credential type indicating the stage of ACME authorization."
            },
            "token": {
              "type": "string",
              "description": "The ACME session token or authorization token."
            }
          }
        },
        "acme_info": {
          "type": "object",
          "description": "ACME-specific information for display and processing.",
          "properties": {
            "payment_option": {
              "type": "string",
              "description": "The selected ACME payment option (e.g., 'pay_in_4')."
            },
            "installment_count": {
              "type": "integer",
              "description": "Number of installments if applicable."
            }
          }
        }
      }
    }
  ]
}
```

##### Step 4: Write the Specification Document

The specification document is human-readable documentation explaining how
platforms and businesses should implement your handler. It MUST include:

1.  **Introduction**: Purpose and use cases for the handler
2.  **Handler Configuration**: How businesses configure the handler
3.  **Agent Protocol**: Step-by-step flow for platforms to acquire tokens
4.  **Business Processing**: How businesses process the resulting instruments
5.  **Security Considerations**: Authentication, token handling, and compliance

**Example Specification** (`https://acme.com/ucp/specs/pay_later`):

---

**ACME Pay Later Handler Specification**

**Handler Name:** `com.acme.pay_later`
**Version:** `2025-06-01`

**1. Introduction**

The `com.acme.pay_later` handler enables businesses to offer ACME's
buy-now-pay-later options through UCP-compatible agents. Supported options
include Pay in 4, Pay in 30 days, and Financing.

**2. Handler Configuration**

Businesses advertising support for `com.acme.pay_later` MUST include the
handler in their checkout response:

```json
{
  "payment": {
    "handlers": [{
      "id": "acme",
      "name": "com.acme.pay_later",
      "version": "2025-06-01",
      "spec": "https://acme.com/ucp/specs/pay_later",
      "config_schema": "https://acme.com/ucp/schemas/pay_later_handler.json",
      "instrument_schemas": [
        "https://acme.com/ucp/schemas/pay_later_instrument.json"
      ],
      "config": {
        "client_id": "acme_live_abc123",
        "environment": "production",
        "locale": "en-US",
        "payment_options": [
          {
            "type": "pay_in_4",
            "min_amount": 350,
            "max_amount": 15000
          },
          {
            "type": "financing",
            "min_amount": 2000
          }
        ]
      }
    }]
  }
}
```

**3. Agent Protocol**

Agents MUST follow this flow to process a `com.acme.pay_later` handler:

1.  **Discover Handler**: Agent identifies `com.acme.pay_later` in the
    merchant's payment handlers array.

2.  **Display Options**: Agent presents available `payment_options` to the user,
    filtering by order amount eligibility.

3.  **Create Session**: Agent calls the ACME Sessions API:
    ```
    POST https://api.acme.com/payments/v1/sessions
    Authorization: Basic {base64(client_id:client_secret)}
    Content-Type: application/json

    {
      "purchase_country": "US",
      "purchase_currency": "USD",
      "locale": "en-US",
      "order_amount": 5000,
      "order_lines": [...],
      "merchant_reference1": "{checkout_id}"
    }
    ```

4.  **User Authorization**: Agent renders the ACME widget or redirects user
    to ACME for authorization. Upon success, ACME returns an
    `authorization_token`.

5.  **Complete Checkout**: Agent submits the authorization token to the
    merchant's complete endpoint.

**4. Payment Instrument Structure**

```json
{
  "payment": {
    "instruments": [{
      "id": "instr_acme",
      "handler_id": "acme",
      "type": "acme_pay_later",
      "credential": {
        "type": "acme_authorization",
        "token": "example_token_12345"
      },
      "acme_info": {
        "payment_option": "pay_in_4",
        "installment_count": 4
      }
    }],
    "selected_instrument_id": "instr_acme"
  }
}
```

**5. Merchant Processing**

Upon receiving an `acme_pay_later` instrument, merchants MUST:

1.  Validate the `handler_id` matches a configured ACME handler
2.  Extract the `authorization_token` from `token.value`
3.  Call ACME's Create Order API to capture the payment:
    ```
    POST https://api.acme.com/payments/v1/authorizations/{authorization_token}/order
    ```
4.  Store the ACME `order_id` for refunds and dispute handling

**6. Security Considerations**

-   Authorization tokens are single-use and time-limited (default: 60 minutes)
-   Merchants MUST NOT expose `client_secret` in handler configurations
-   All ACME API calls MUST use TLS 1.2+
-   Merchants SHOULD implement idempotency keys for order creation

---

##### Step 5: Publish and Version

1.  **Host Assets**: Publish your schema and specification at stable URLs
    matching your namespace authority
2.  **Version Independently**: Your handler version evolves independently of UCP
3.  **Maintain Backwards Compatibility**: Follow the same compatibility rules as
    UCP capabilities (see Section 10.4)

##### Complete Handler Declaration

```json
{
  "id": "acme",
  "name": "com.acme.pay_later",
  "version": "2025-06-01",
  "spec": "https://acme.com/ucp/specs/pay_later",
  "config_schema": "https://acme.com/ucp/schemas/pay_later_handler.json",
  "instrument_schemas": [
    "https://acme.com/ucp/schemas/pay_later_instrument.json"
  ],
  "config": {
    "client_id": "acme_live_abc123",
    "environment": "production",
    "locale": "en-US",
    "payment_options": [
      { "type": "pay_in_4", "min_amount": 350, "max_amount": 15000 },
      { "type": "financing", "min_amount": 2000 }
    ]
  }
}
```

This extensibility enables the payment ecosystem to innovate while maintaining
interoperability through the common UCP framework.

### 6.4 Payment Flow End-to-End

The payment flow in UCP is a **2-step process** involving **Token Acquisition**
(Client-side) and **Order Placement** (Server-side).

1.  **Select:** The Agent/User selects a payment handler from the
    `payment.handlers` array provided in the checkout response.
2.  **Acquire:** The Agent uses the handler's `config` to acquire a secure token
    (e.g., exchanging payment credentials for a network token via a PSP, or
    requesting a Google Pay payload).
3.  **Complete:** The Agent submits the instrument to the Merchant's `complete`
    endpoint.
4.  **Challenge (Conditional):** If the bank or PSP requires strong customer
    authentication (SCA), the merchant responds with a `requires_escalation`
    status, and the Agent facilitates the user interaction.

#### 6.4.1 Data Security & Schema Enforcement

To prevent the leakage of sensitive payment data, the handling of credentials is
strictly enforced at the schema level.

*   **Write-Only Credentials:** The `credential` object within a payment instrument is strictly **Write-Only**.
    *   It is defined in the JSON Schema using appropriate annotations.
    *   Agents MUST submit this field during the `complete` phase.
    *   Merchants **MUST NOT** echo this field in any API response.
*   **Display Information:** Non-sensitive fields (Brand, Last 4, Billing Address) MAY be echoed by the merchant in responses to confirm the payment method details for the UI.

**Field Flow Direction:**

| Field | Create/Update Request | Create/Update Response | Complete Request | Complete Response |
|-------|----------------------|----------------------|------------------|-------------------|
| `payment.handlers` | ❌ **Omitted** - Agents never send handlers | ✅ **Required** - Merchant advertises supported handlers | ❌ **Omitted** - Agents never send handlers | ✅ **Optional** - May be included in final state |
| `payment.instruments` | ✅ **Optional** - Display info only (for embedded checkout UI) | ✅ **Optional** - Echoed display info | ✅ **Required** - Display info + credentials | ✅ **Optional** - Display info only (credentials omitted) |
| `payment.instruments[].credential` | ❌ **Never included** - Not needed before completion | ❌ **Never included** - Security sensitive | ✅ **Required** - Contains payment token/data | ❌ **Omitted** - Never echoed back for security |
| `payment.selected_instrument_id` | ✅ **Optional** - May be provided with instruments | ✅ **Optional** - Echoed if provided | ✅ **Omitted** - Currently only provide one instrument instance | ✅ **Required** - Merchant confirms selected instrument |

#### 6.4.2 Example Flow A: Google Pay

In this scenario, the Agent uses a specific payment handler Google Pay.
The Merchant configures the handler using Google Pay's standard payment data
model.

**1. Merchant Configuration (Response from Create Checkout)**

The checkout response includes Google Pay handler (shown here is the `payment`
field only):

```json
{
  "payment": {
    "handlers": [{
      "id": "gpay",
      "name": "com.google.pay",
      "version": "2024-12-03",
      "spec": "https://ucp.dev/handlers/google_pay",
      "config_schema": "https://ucp.dev/handlers/google_pay/config.json",
      "instrument_schemas": [
        "https://ucp.dev/handlers/google_pay/card_payment_instrument.json"
      ],
      "config": {
        "allowed_payment_methods": [{
          "type": "CARD",
          "parameters": {
            "allowed_card_networks": ["VISA", "MASTERCARD"]
          },
          "tokenization_specification": {
            "type": "PAYMENT_GATEWAY",
            "parameters": {
              "gateway": "stripe",
              "gateway_merchant_id": "acme_inc"
            }
          }
        }]
      }
    }]
  }
}
```

**2. Token Execution (Client-Side)**
The Agent recognizes the `com.google.pay` handler.
1.  It passes the `config` into the Google Pay API (or executes an Agentic
    Wallet Request).
2.  Google Pay returns the encrypted token data.

**3. Complete Checkout**
The Agent wraps the Google Pay response into a payment instrument for the UCP
`complete` call.

```json
POST /checkout-sessions/{checkout_id}/complete
Content-Type: application/json

{
  "payment_data": {
    "id": "instr_1",
    "handler_id": "gpay",
    "type": "card",
    "brand": "visa",
    "last_digits": "4242",
    "rich_card_art": "https://cart-art-1.html",
    "rich_text_description": "Visa •••• 1234",
    "billing_address": {
      "street_address": "123 Main St",
      "address_locality": "Anytown",
      "address_region": "CA",
      "address_country": "US",
      "postal_code": "12345"
    },
    "credential": {
      "type": "PAYMENT_GATEWAY",
      "token": "examplePaymentMethodToken"
    }
  },
  "risk_signals": {
    // ... host could send risk_signals here
  }
}
```

#### 6.4.3 Example Flow B: Direct Card Tokenization

In this scenario, an AI Agent uses a secure vault to retrieve a token from a
PSP before sending it to the checkout. Transactions sometimes require Strong
Customer Authentication (SCA), such as a 3DS banking challenge. The Merchant
`complete` response utilizes a `status` field to handoff this flow.

**1. Merchant Configuration (Response from Create Checkout)**

The Merchant advertises the supported tokenizer in the `payment.handlers` array.

```json
{
  "payment": {
    "handlers": [
      {
        "id": "merchant_tokenizer",
        "name": "com.example.merchant_tokenizer",
        "version": "2026-01-11",
        "config": {
          "type": "CARD",
          "tokenization_specification": {
            "type": "token",
            "parameters": {
              "token_retrieval_url": "https://api.psp.com/v1/tokens"
            }
          }
        }
      }
    ]
  }
}
```

**2. Token Execution (Client-Side)**

The Agent retrieves a token securely from the PSP's tokenization endpoint
defined in the handler config. *Example Result:* `tok_visa_123`

**3. Complete Checkout (Request to Merchant)**

```json
POST /checkout-sessions/{checkout_id}/complete
Content-Type: application/json

{
  "payment_data": {
    "id": "instr_1",
    "handler_id": "merchant_tokenizer",
    "type": "card",
    "brand": "visa",
    "last_digits": "4242",
    "expiry_month": 12,
    "expiry_year": 2026,
    "credential": {
      "type": "token",
      "value": "tok_visa_123"
    }
  },
  "risk_signals": {
    // ... host could send risk_signals here
  }
}
```

**4. Action Required Response (Merchant to Agent)**

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "requires_escalation",
  "messages": [
    {
      "type": "error",
      "code": "requires_3ds",
      "content": "Your bank requires verification to complete this purchase.",
      "severity": "requires_buyer_input"
    }
  ],
  "continue_url": " ... " // this will host the handoff URL
}
```

### 6.4.4 Risk Signals

To aid in fraud assessment, the Agent MAY include additional risk signals in
the complete call, providing the Merchant with more context about the
transaction's legitimacy. The structure and content of these risk signals are
not strictly defined by this specification, allowing flexibility based on the
agreement between the Agent and Merchant or specific payment handler
requirements.

**Example (Flexible Structure):**

```json
{
  "risk_signal": {
    "session_id": "abc_123_xyz",
    "score": 0.95
  }
}
```

### 6.5 Security and Trust Model

The payment architecture establishes clear security boundaries and trust
relationships between agents, merchants, and payment providers. Understanding
this model is essential for secure implementation.

#### Trust Relationships

**Merchant ↔ Payment Provider**

The foundational trust relationship exists between merchants and payment
providers (PSPs, wallet providers, payment handlers). This relationship is
established **outside of UCP** through:

-   Merchant onboarding and KYC processes
-   API credentials and encryption keys
-   Gateway configurations and routing rules
-   Processing agreements and fee structures

The handler configuration in UCP **represents** this existing relationship but
does not create it. When a merchant advertises a handler, they are saying: "I
have an integration with this payment provider and can process instruments from
it."

**Agent as Untrusted Intermediary**

Agents are deliberately positioned as **untrusted intermediaries** in the
payment flow. This minimizes security scope and enables diverse agent
implementations without requiring each agent to become PCI-compliant.

Key principles:

-   Agents never see raw payment credentials (card numbers, CVV, bank accounts)
-   Agents forward opaque credentials they cannot use directly (encrypted data,
    token references, etc.)
-   Agents cannot access the underlying payment data from the credentials they
    receive
-   Agents do not need to be PCI-DSS certified for most flows

**Handler Provider Trust**

When an agent executes a handler protocol (e.g., Google Pay, PSP Tokenization),
the agent establishes a temporary trust relationship with the handler provider:

-   Agent authenticates to the handler provider (if required)
-   Handler provider validates agent's right to request credentials
-   Handler provider secures credentials for the specific merchant (via
    encryption, tokenization, or other methods)
-   Agent receives opaque credentials it cannot use directly

**Agent Authorization with AP2 (Optional)**

For scenarios requiring stronger guarantees of user authorization—such as
autonomous agents operating without real-time user interaction, recurring
payments, or high-value transactions—UCP supports the **Agent Payments Protocol
(AP2)** extension. AP2 adds a cryptographic authorization layer on top of the
credential security model.

When the `dev.ucp.shopping.ap2_mandate` capability is negotiated:

-   **Merchants** sign checkout responses to ensure agents receive authentic
    transaction terms (price, line items, totals)
-   **Agents** provide cryptographically signed mandates proving the user
    explicitly authorized both the specific checkout state and the funds
    transfer
-   **Both parties** create non-repudiable evidence of the transaction terms and
    authorization

This transforms the trust model from "agent as untrusted intermediary" to "agent
as verifiable intermediary":

| Without AP2 | With AP2 |
|-------------|----------|
| Agent forwards opaque credentials | Agent provides signed authorization proofs |
| Merchant trusts payment provider to secure credentials | Merchant verifies cryptographic proof of user consent |
| Security through encryption/tokenization | Security through digital signatures and verifiable credentials |
| Suitable for user-present flows | Enables autonomous agent operations |

**The Dual Mandate System:**

AP2 requires two distinct signed proofs:
1. **Checkout Mandate**: Proves user authorized the specific checkout terms
   (items, prices, totals) signed by the merchant
2. **Payment Mandate**: Proves user authorized the funds transfer to the
   merchant

These mandates can be generated through:

-   **Trusted Agent Provider**: Agent provider signs on user's behalf after
    obtaining explicit user consent through trusted UI
-   **Digital Payment Credential**: User holds a verifiable credential (e.g.,
    issued by bank/network) and signs directly

**Key Security Properties:**

-   **Non-repudiation**: Both parties hold cryptographic proof of transaction
    terms and authorization
-   **Tamper evidence**: Signatures are invalidated if checkout terms are
    modified after user consent
-   **Selective disclosure**: SD-JWT format enables minimal data exposure while
    proving authorization
-   **Trust framework agnostic**: Works with various credential issuers and
    agent models

For complete AP2 specification including mandate formats, signature
requirements, and verification procedures, see the
[AP2 Mandates Extension](site:specification/ap2-mandates).

**Important**: AP2 is an **optional extension** that complements but does not
replace the base credential security model. Merchants can support both AP2-
enabled autonomous flows and standard user-present checkout flows
simultaneously.

#### Credential Processing Model

**Handler ID as Processing Key**

The `handler_id` field in payment instruments tells the merchant which
integration to use for processing:

```json
{
  "id": "instr_1",
  "handler_id": "gpay",  // References handler configuration
  "credential": {
    "type": "PAYMENT_GATEWAY",
    "token": "eyJhbGc...encrypted_data"
  }
}
```

The merchant:
1. Looks up the handler configuration by `handler_id`
2. Routes the credential to the appropriate PSP/handler provider endpoint
3. Processes the credential using the handler-specific method
4. Completes the payment

Different handlers may route to different PSP endpoints, use different
credential processing methods, or apply different business rules—all transparent
to the agent.

**Credential Security Models**

UCP supports multiple approaches for securing payment credentials. The key
principle is that agents receive **opaque credentials** they cannot use
directly—only the merchant (via their payment provider relationship) can process
them.

**Approach 1: Encrypted Credentials (e.g., Google Pay)**

In this model, raw payment data is encrypted for the specific merchant:

-   **Handler Provider**: Encrypts raw credentials with merchant's public key or
    gateway credentials
-   **Agent**: Receives encrypted payload it cannot decrypt
-   **Merchant**: Decrypts using private key or sends to PSP for decryption
-   **Example**: Google Pay provides encrypted card data that only the
    merchant's PSP can decrypt

**Approach 2: Token References (e.g., Tokenization with PSP)**

In this model, a token references the actual credentials held by the payment
provider:

-   **Handler Provider**: Stores raw credentials securely and returns a token
    reference
-   **Agent**: Receives token it cannot use to access credentials directly
-   **Merchant**: Exchanges token with PSP to retrieve/process the underlying
    credentials
-   **Example**: Tokenization with PSP returns a session token
    that merchant uses to charge the card

**Approach 3: Handler-Specific Formats**

Custom handlers may define their own credential formats and security models,
provided they maintain the principle that agents cannot directly access or use
raw payment data.

**Transport Security**

Regardless of credential format, HTTPS/TLS MUST be used for all API calls to
protect credentials in transit between agent and merchant.

**Unidirectional Credential Flow**

Credentials flow in ONE direction only: **Agent → Merchant**

```
Agent acquires credential → Agent submits to merchant → Merchant processes
                                                      ↓
                                           Credential destroyed
```

Merchants MUST NOT:

-   Echo credentials back in API responses
-   Log raw credentials
-   Store credentials after processing (unless tokenized by PSP)
-   Return credentials in error messages

This is enforced by the schema annotation `"ucp_response": "omit"` on
credential fields.

#### PCI-DSS Scope Management

**Agent Scope**

Most agent implementations can **avoid PCI-DSS scope** by:

-   Using handlers that provide opaque credentials (encrypted data, token
    references, etc.)
-   Never accessing or storing raw payment data (card numbers, CVV, etc.)
-   Forwarding credentials without the ability to use them directly
-   Using PSP tokenization payment handlers where raw credentials never pass
    through the agent

**Merchant Scope**

Merchants can minimize PCI scope by:

-   Using PSP-hosted tokenization (PSP tokenization - PSP stores
    credentials, merchant receives token reference)
-   Using wallet providers that provide encrypted credentials (Google Pay, Apple
    Pay)
-   Never logging raw credentials
-   Delegating credential processing to PCI-certified PSPs

**Handler Provider Scope**

Payment handler providers (PSPs, wallets) are typically PCI-DSS Level 1
certified and handle:

-   Raw credential collection
-   Credential protection (tokenization, encryption, secure storage)
-   Credential validation and processing
-   PCI-compliant infrastructure

#### Security Best Practices

**For Merchants:**

1.  Validate handler_id before processing (ensure handler is in advertised set)
2.  Use separate PSP credentials for TEST vs PRODUCTION environments
3.  Implement idempotency for payment processing (prevent double-charges)
4.  Log payment events without logging credentials
5.  Set appropriate credential timeouts (tokens should expire)
6.  For highly sensitive transactions, consider supporting the
    `dev.ucp.shopping.ap2_mandate` extension. This allows merchants to
    cryptographically sign checkout terms, providing stronger assurances to
    agents and users.
7.  If using the AP2 Mandates Extension, rigorously verify the
    `checkout_mandate` and ensure your PSP can process the `payment_mandate`
    as per the [AP2 Protocol Specification](https://ap2-protocol.org/).

**For Agents:**

1.  Always use HTTPS for checkout API calls
2.  Validate handler configurations before executing protocols
3.  Implement timeout handling for credential acquisition
4.  Clear credentials from memory after submission
5.  Handle credential expiration gracefully (re-acquire if needed)
6.  When available, prefer merchants supporting the
    `dev.ucp.shopping.ap2_mandate` extension. Verify the
    `ap2.merchant_authorization` signature to ensure the checkout terms are
    authentically from the merchant and have not been tampered with.
7.  When the AP2 Mandates Extension is active, ensure a cryptographically signed
   `checkout_mandate` and `payment_mandate` are generated upon user consent, as
    detailed in the extension specification.

**For Handler Providers:**

1.  Secure credentials for the specific merchant (encryption, tokenization, or
    other handler-specific methods)
2.  Implement rate limiting on credential acquisition
3.  Validate agent authorization before providing credentials
4.  Set reasonable credential expiration (e.g., 60 minutes for tokens, time-
    limited encrypted payloads)
5.  Ensure credentials cannot be used by agents directly (only by the intended
    merchant)
6.  If applicable, provide mechanisms for merchants or PSPs to verify
    `payment_mandate` credentials received through the AP2 flow.

#### Fraud Prevention Integration

While UCP does not define fraud prevention APIs, the payment architecture
supports fraud signal integration:

-   Merchants can require additional fields in handler configurations (e.g.,
    3DS requirements)
-   Agents can submit device fingerprints and session data alongside credentials
-   Handler providers can perform risk assessment during credential acquisition
-   Merchants can reject high-risk transactions and request additional
    verification

Future extensions may standardize fraud signal schemas, but the current
architecture allows flexible integration with existing fraud prevention systems.

## 7. Transport Layer

UCP supports multiple transport protocols. Agents and Merchants effectively
negotiate the transport via their profiles.

### 7.1. REST Transport (Core)

The primary transport for UCP is **HTTP/1.1** (or higher) using RESTful
patterns.

*   **Content-Type:** Requests and responses MUST use `application/json`.
*   **Methods:** Implementations MUST use standard HTTP verbs (POST for
    creation/action, GET for retrieval).
*   **Status Codes:** Implementations MUST use standard HTTP status codes
    (200, 201, 400, 401, 500).

### 7.2. Model Context Protocol (MCP)

UCP Capabilities map 1:1 to MCP Tools. A merchant MAY expose an MCP server that
wraps their UCP implementation, allowing LLMs to call tools like
`create_checkout_session` directly.

### 7.2. Agent-to-Agent Protocol (A2A)

A merchant MAY expose an A2A Agent that supports UCP as an A2A Extension
allowing integration with client applications with structured UCP data types.

## 8. Standard Capabilities

The Universal Commerce Protocol defines a set of standard capabilities. Each
capability is identified by a versioned URI and is defined in a separate
specification document.

### 8.1. Core Capabilities

| Capability Name      | ID (URI)                                         | Description                                                                                                  |
| :------------------- | :----------------------------------------------- | :----------------------------------------------------------------------------------------------------------- |
| **Checkout**         | `{{ ucp_url }}/capabilities/checkout/v1`         | Facilitates the creation and management of checkout sessions, including cart management and tax calculation. |
| **Identity Linking** | `{{ ucp_url }}/capabilities/identity-linking/v1` | Enables platforms to obtain authorization via OAuth 2.0 to perform actions on a user's behalf.               |
| **Order**            | `{{ ucp_url }}/capabilities/order/v1`            | Allows merchants to push asynchronous updates about an order's lifecycle (shipping, delivery, returns).      |

### 8.2. Definition & Extensions

Detailed definitions for endpoints, schemas, and valid extensions for each
capability are provided in their respective specification files. Extensions are
typically versioned and defined alongside their parent capability.

## 9. Security & Authentication

### 9.1. Transport Security

All UCP communication **MUST** occur over **HTTPS**.

### 9.2. Request Authentication

*   **Consumer to Merchant:** Requests SHOULD be authenticated using standard
    headers (e.g., `Authorization: Bearer <token>`).
*   **Merchant to Consumer (Webhooks):** Webhooks MUST be signed using a shared
    secret or asymmetric key to verify integrity and origin.

### 9.3. Data Privacy

Sensitive data (such as Payment Credentials or PII) MUST be handled according to
PCI-DSS and GDPR guidelines. UCP encourages the use of tokenized payment data to
minimize Merchant and Platform liability.

### 9.4. Transaction Integrity and Non-Repudiation

For enhanced security and non-repudiation, UCP supports the
`dev.ucp.shopping.ap2_mandate` extension. When negotiated:

*   Merchants provide a cryptographic signature on the checkout terms (`ap2.merchant_authorization`).
*   Agents provide a cryptographic mandate from the user, authorizing the payment and a specific checkout state (`ap2.checkout_mandate` and a `payment_mandate`).

This mechanism, based on the [AP2 Protocol](https://ap2-protocol.org/), provides
strong, end-to-end cryptographic assurances about the transaction details and
participant consent, significantly reducing risks of tampering and disputes.
Implementers SHOULD consider supporting this extension for sensitive or
high-value transactions.

## 10. Versioning

### 10.1 Version Format

UCP uses date-based versioning in the format YYYY-MM-DD. This provides
clear chronological ordering and unambiguous version comparison.

### 10.2 Version Discovery and Negotiation

UCP prioritizes strong backwards compatibility. Merchants implementing a
version SHOULD handle requests from agents using that version or older
versions.

Both merchants and agents declare a single version in their profiles:

Merchant Profile:

```json
{
  "ucp": {
    "version": "2025-10-21",
    "transports": {
      "rest": { "endpoint": "https://example-merchant.com/ucp" }
    },
    "capabilities": []
  },
  "payment": {
    "handlers": [
      {
        "id": "merchant_tokenizer",
        "name": "com.example.merchant_tokenizer",
        "version": "2026-01-11",
        "spec": "https://example.com/specs/payments/merchant_tokenizer",
        "config_schema": "https://example.com/specs/payments/merchant_tokenizer.json",
        "instrument_schemas": [
          "https://ucp.dev/schemas/shopping/types/card_payment_instrument.json"
        ],
        "config": {
          "type": "CARD",
          "tokenization_specification": {
            "type": "PUSH",
            "parameters": {
              "token_retrieval_url": "https://api.psp.com/v1/tokens"
            }
          }
        }
      }
    ]
  }
}
```

Client Profile:

```json
{
  "ucp": {
    "version": "2025-10-21",
    "capabilities": []
  },
  "payment": {
    "handlers": []
  }
}
```

### 10.3 Version Negotiation

![High-level resolution flow sequence diagram](site:specification/images/ucp-discovery-negotiation.png)

Merchants MUST validate the client's version and determine compatibility:

1.  Client declares version via profile referenced in request
2.  Merchant validates:
    *   If client version ≤ merchant version: Merchant MUST process the request
    *   If client version > merchant version: Merchant MUST return
        VERSION_UNSUPPORTED error
3.  Merchants MUST include the version used for processing in every response

Response with version confirmation:

```json
{
  "ucp": {
    "version": "2025-10-21",
    "capabilities": []
  },
  "id": "cart_123",
  "status": "ok"
}
```

Version unsupported error:

```json
{
  "status": "error",
  "errors": [{
    "code": "VERSION_UNSUPPORTED",
    "message": "Version 2025-11-01 is not supported. This merchant implements version 2025-10-21.",
    "severity": "critical"
  }]
}
```

### 10.4 Backwards Compatibility

Backwards-Compatible Changes: The following changes MAY be introduced
without a new version:

*   Adding new OPTIONAL fields to responses
*   Adding new OPTIONAL parameters to requests
*   Adding new endpoints, methods, or operations
*   Adding new error codes with existing error structures
*   Adding new values to enums (unless explicitly documented as exhaustive)
*   Changing the order of fields in responses
*   Changing the length or format of opaque strings (IDs, tokens)

Breaking Changes: The following changes MUST NOT be introduced without a new
version:

*   Removing or renaming existing fields
*   Changing field types or semantics
*   Making optional fields required
*   Removing operations or endpoints
*   Changing authentication or authorization requirements
*   Modifying the core protocol flow or state machine
*   Changing the meaning of existing error codes

### 10.5 Independent Component Versioning

*   The core UCP protocol versions independently from capabilities.
*   Each capability versions independently from other capabilities.
*   Capabilities MUST follow the same backwards compatibility rules as the
    core protocol.
*   Merchants MUST validate capability version compatibility using the same
    logic as core version validation.
*   Transports MAY define their own version handling mechanisms.

## 11. Glossary

| Term                              | Acronym | Definition                                                                                                                                                    |
| :-------------------------------- | :------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Agent Payments Protocol**       | AP2     | An open protocol designed to enable AI agents to securely interoperate and complete payments autonomously. UCP leverages AP2 for secure payment mandates.     |
| **Agent2Agent Protocol**          | A2A     | An open standard for secure, collaborative communication between diverse AI agents. UCP can use A2A as a transport layer.                                     |
| **Capability**                    | -       | A standalone core feature that a merchant supports (e.g., Checkout, IdentityLinking). Capabilities are the fundamental "verbs" of UCP.                        |
| **Credential Provider**           | CP      | A trusted entity (like a digital wallet) responsible for securely managing and executing the user's payment and identity credentials.                         |
| **Extension**                     | -       | An optional module that augments a specific UCP Capability, allowing for specialized functionality (e.g., Discounts) without bloating the core specification. |
| **Profile**                       | -       | A JSON document hosted by businesses and platforms at a well-known URI, declaring their identity, supported capabilities, and endpoints.                        |
| **Merchant**                      | -       | The entity selling goods or services. In UCP, they act as the **Merchant of Record (MoR)**, retaining financial liability and ownership of the order.         |
| **Model Context Protocol**        | MCP     | A protocol standardizing how AI models connect to external data and tools. UCP capabilities map 1:1 to MCP tools.                                             |
| **Universal Commerce Protocol**   | UCP     | The standard defined in this document, enabling interoperability between commerce entities via standardized capabilities and discovery.                       |
| **Payment Service Provider**      | PSP     | The financial infrastructure provider (e.g., Stripe, Adyen) that processes payments, authorizations, and settlements on behalf of the Merchant.               |
| **Platform**                      | -       | The consumer-facing surface (AI agent, app, website) acting on behalf of the user to discover merchants and facilitate commerce.                              |
| **Verifiable Digital Credential** | VDC     | An Issuer-signed credential (set of claims) whose authenticity can be verified cryptographically. Used in UCP for secure payment authorizations.              |
| **Verifiable Presentation**       | VP      | A presentation of one or more VDCs that includes a cryptographic proof of binding, used to prove authorization to a Merchant or PSP.                          |