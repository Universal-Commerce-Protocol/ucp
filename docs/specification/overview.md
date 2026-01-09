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

# Universal Commerce Protocol (UCP) Official Specification

**Version:** `2026-01-11`

## Overarching guidelines

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this
document are to be interpreted as described in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.html){ target="_blank" } and
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174.html){ target="_blank" }.

Schema notes:

-   Date format: Always specified as
    [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339.html){ target="_blank" }
    unless otherwise specified
-   Amounts format: Minor units (cents)

## 1. Discovery, Governance, and Negotiation

UCP employs a server-selects architecture where the business (server) chooses
the protocol version and capabilities from the intersection of both parties'
capabilities. Both business and platform profiles can be cached by both parties,
allowing efficient capability negotiation within the normal request/response
flow between platform and business.

### 1.1 Namespace Governance

UCP uses reverse-domain naming to encode governance authority directly into
capability identifiers. This eliminates the need for a central registry.

#### 1.1.1 Naming Convention

All capability and service names **MUST** use the format:

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

#### 1.1.2 Spec URL Binding

The `spec` and `schema` fields are **REQUIRED** for all capabilities. The origin
of these URLs **MUST** match the namespace authority:

| Namespace       | Required Origin           |
| --------------- | ------------------------- |
| `dev.ucp.*`     | `https://ucp.dev/...`     |
| `com.example.*` | `https://example.com/...` |

Platform **MUST** validate this binding and SHOULD reject capabilities where the
spec origin does not match the namespace authority.

#### 1.1.3 Governance Model

| Namespace Pattern | Authority    | Governance          |
| ----------------- | ------------ | ------------------- |
| `dev.ucp.*`       | ucp.dev      | UCP governing body  |
| `com.{vendor}.*`  | {vendor}.com | Vendor organization |
| `org.{org}.*`     | {org}.org    | Organization        |

The `dev.ucp.*` namespace is reserved for capabilities sanctioned by the UCP
governing body. Vendors **MUST** use their own reverse-domain namespace for
custom capabilities.

### 1.2 Services

A **service** defines the API surface for a vertical (shopping, common, etc.).
Services include operations, events, and transport bindings defined via
standard formats:

-   **REST**: OpenAPI 3.x (JSON format)
-   **MCP**: OpenRPC (JSON format)
-   **A2A**: Agent Card Specification
-   **EP(embedded)**: OpenRPC (JSON format)

#### 1.2.1 Service Definition

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

Transport definitions **MUST** be thin: they declare method names and reference
base schemas only. See [1.4.1 Requirements](#141-requirements) for details.

#### 1.2.2 Endpoint Resolution

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

-   `endpoint` **MUST** be a valid URL with scheme (https)
-   `endpoint` **SHOULD NOT** have a trailing slash
-   OpenAPI paths are relative and appended directly to endpoint
-   Same resolution applies to MCP endpoints for JSON-RPC calls
-   `endpoint` for A2A transport refers to the Agent Card URL for the agent

### 1.3 Capabilities

A **capability** is a feature within a service. It declares what
functionality is supported and where to find documentation and schemas.

#### 1.3.1 Capability Definition

{{ extension_schema_fields('capability.json#/$defs/discovery', 'capability-schema') }}

#### 1.3.2 Extensions

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

### 1.4 Schema Composition

Extensions can add new fields and modify shared structures (e.g., discounts
modify `totals`, fulfillment adds fulfillment to `totals.type`).

#### 1.4.1 Requirements

-   Transport definitions (OpenAPI/OpenRPC) **SHOULD** reference base schemas
    only. They **SHOULD NOT** enumerate fields or define payload shapes inline.
-   Extensions **MUST** be self-describing. Each extension schema **MUST**
    declare the types it introduces and how it modifies base types using `allOf`
    composition.
-   Platforms **MUST** resolve schemas client-side by fetching and composing
    base schemas with active extension schemas.

#### 1.4.2 Extension Schema Pattern

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

#### 1.4.3 Resolution Flow

Platforms **MUST** resolve schemas following this sequence:

1.  **Discovery**: Fetch business profile from `/.well-known/ucp`
2.  **Negotiation**: Compute capability intersection (see
    [1.7.3](#173-intersection-algorithm))
3.  **Schema Fetch**: Fetch base schema and all active extension schemas
4.  **Compose**: Merge schemas via `allOf` chains based on active extensions
5.  **Validate**: Validate requests and responses against the composed schema

### 1.5 Profile Structure

#### 1.5.1 Business Profile

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
        },
        "a2a": {
          "endpoint": "https://business.example.com/.well-known/agent-card.json"
        },
        "embedded": {
          "schema": "https://ucp.dev/services/shopping/embedded.openrpc.json"
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
        "id": "business_tokenizer",
        "name": "dev.ucp.business_tokenizer",
        "version": "2026-01-11",
        "spec": "https://example.com/specs/payments/business_tokenizer-payment",
        "config_schema": "https://ucp.dev/schemas/payments/delegate-payment.json",
        "instrument_schemas": [
          "https://ucp.dev/schemas/shopping/types/card_payment_instrument.json"
        ],
        "config": {
          "endpoint": "https://business.example.com/tokenize",
          "public_key": "pk_live_abc123",
          "creates": "merchant.token"
        }
      }
    ]
  },
  "signing_keys": [
    {
      "kid": "business_2025",
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
[Payment Architecture](#2-payment-architecture). The `signing_keys` array
contains public keys (JWK format) used to verify signatures on webhooks and
other authenticated messages from the business.

#### 1.5.2 Platform Profile

Platform profiles are similar and include signing keys for capabilities
requiring cryptographic verification. Capabilities **MAY** include a `config`
object for capability-specific settings (e.g., callback URLs, feature flags). An
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
        "spec": "https://developers.google.com/merchant/ucp/guides/gpay-payment-handler",
        "config_schema": "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/gpay_config.json",
        "instrument_schemas": [
          "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/gpay_card_payment_instrument.json"
        ]
      },
       {
        "id": "business_tokenizer",
        "name": "dev.ucp.business_tokenizer",
        "version": "2026-01-11",
        "spec": "https://example.com/specs/payments/business_tokenizer-payment",
        "config_schema": "https://ucp.dev/schemas/payments/delegate-payment.json",
        "instrument_schemas": [
          "https://ucp.dev/schemas/shopping/types/card_payment_instrument.json"
        ]
      }
    ]
  },
  "signing_keys": [
    {
      "kid": "platform_2025",
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

### 1.6 Platform Advertisement on Request

Platforms **MUST** communicate their profile URI with each request to enable
capability negotiation.

**HTTP Transport:** Platforms **MUST** use Dictionary Structured Field syntax
([RFC 8941](https://datatracker.ietf.org/doc/html/rfc8941)) in the UCP-Agent
header:

```
POST /checkout HTTP/1.1
UCP-Agent: profile="https://agent.example/profiles/shopping-agent.json"
Content-Type: application/json

{"line_items": [...]}
```

**MCP Transport:** Platforms **MUST** use native dictionary structure in
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

### 1.7 Negotiation Protocol

#### 1.7.1 Platform Requirements

1.  **Profile Advertisement**: Platforms **MUST** include their profile URI in
    every request using the transport-appropriate mechanism.
2.  **Discovery**: Platforms **MAY** fetch the business profile from
    `/.well-known/ucp` before initiating requests. If fetched, platforms
    **SHOULD** cache the profile according to HTTP cache-control directives.
3.  **Namespace Validation**: Platforms **MUST** validate that capability `spec`
    URI origins match namespace authorities.
4.  **Schema Resolution**: Platforms **MUST** fetch and compose schemas for
    negotiated capabilities before making requests.

#### 1.7.2 Business Requirements

1.  **Profile Resolution**: Upon receiving a request with a platform profile
    URI, businesses **MUST** fetch and validate the platform profile unless
    already cached.
2.  **Capability Intersection**: Businesses **MUST** compute the intersection of
    platform and business capabilities.
3.  **Extension Validation**: Extensions without their parent capability in the
    intersection **MUST** be excluded.
4.  **Response Requirements**: Businesses **MUST** include the `ucp` field in
    every response containing:
    -   `version`: The UCP version used to process the request
    -   `capabilities`: Array of active capabilities for this response

#### 1.7.3 Intersection Algorithm

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

#### 1.7.4 Error Handling

If negotiation fails, businesses **MUST** return an error response:

```json
{
  "status": "requires_escalation",
  "messages": [{
    "type": "error",
    "code": "version_unsupported",
    "message": "Version 2026-01-11 is not supported.",
    "severity": "requires_buyer_input"
  }]
}
```

#### 1.7.5 Capability Declaration in Responses

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
  ... other fields
}
```

## 2. Payment Architecture

UCP adopts a decoupled architecture for payments to solve the "N-to-N"
complexity problem between platforms, business, and payment credential
providers. This design separates **Payment Methods** (what is accepted) from
**Payment Handlers** (how it is processed), ensuring security and scalability.

### 2.1 Security and Trust Model

The payment architecture is built on a "Trust-by-Design" philosophy. It assumes
that while the business and PSP have a trusted legal relationship, the platform
(Client) acts as an intermediary that **SHOULD NOT** touch raw financial
credentials unless necessary.

#### 2.1.1 The Trust Triangle

1.  **Business ↔ PSP:** A pre-existing legal and technical relationship. The business holds API keys and a contract with the PSP.
2.  **Platform ↔ PSP (Temporary):** The platform interacts with the PSP's interface (e.g., an iframe or API) to tokenize data but is not the "owner" of the funds.
3.  **Platform ↔ Business:** The platform passes the result (a token or mandate) to the business to finalize the order.

#### 2.1.2 The Standard for Agents: Agent Payments Protocol (AP2)

While standard tokenization is sufficient for
traditional "user-in-the-loop" flows, UCP recommends the AP2 as the default
integration standard when the platform is acting as an Agent (e.g., AI
Assistants, Search, Autonomous buyers).

AP2 provides the cryptographic guarantees required for secure, non-repudiable
autonomous commerce where a human **MAY** not be validating every specific step
in real-time.

| Feature | Legacy Tokenization | **AP2 (Recommended for Agents)** |
| :--- | :--- | :--- |
| **Trust Model** | Business trusts the Platform not to misuse credentials. | **Cryptographic Proof:** Business verifies signed User consent. |
| **Data Security** | Opaque tokens (security relies on bearer token). | **Verifiable Credentials:** Signatures bind payment to specific order terms. |
| **Liability** | Ambiguous (did the user authorize this specific amount?). | **Non-Repudiation:** Mathematical proof that User authorized Amount X for Items Y. |
| **Use Case** | Traditional Web/App Checkout (User present). | **Agentic Commerce** (User delegates authority). |

**Recommendation:** Platforms serving as agents and businesses supporting
autonomous commerce **SHOULD** prioritize the `dev.ucp.shopping.ap2_mandate`.

#### 2.1.3 Credential Flow & PCI Scope

To minimize compliance overhead (PCI-DSS):

1.  **Unidirectional Flow:** Credentials flow **Platform → Business** only. Businesses **MUST NOT** echo credentials back in responses.
2.  **Opaque Credentials:** Platforms handle tokens (such as network tokens), encrypted payloads, or mandates, not raw PANs (Primary Account Numbers).
3.  **Handler ID Routing:** The `handler_id` in the payload ensures the Business knows exactly which PSP key to use for decryption/charging, preventing key confusion attacks.

### 2.2 Roles & Responsibilities: Who Implements What?

A common source of confusion is the division of labor. The UCP payment model
splits responsibilities as follows:

| Role | Responsibility | Action |
| :--- | :--- | :--- |
| **PSP / Wallet**(e.g., PSP-X, Google Pay) | **Defines the Spec** | Creates the **Handler Definition**. They publish the "Blueprint" (JSON Schemas) that dictates how to tokenize a card and what config inputs are needed.<br>*Example: "Here is the schema for the 'com.psp-x.tokenization' handler."* |
| **Business**(e.g., Retailer) | **Configures the Handler** | Selects the Handler they want to use and provides their specific **Configuration** (Public Keys, Merchant IDs) in the UCP Checkout Response. *Example: "I accept Visa using 'com.psp-x.tokenization' with this Publishable Key."* |
| **Platform**(App, Website, or Agent) | **Executes the Protocol** | Reads the business's config and executes the logic defined by the PSP's Spec to acquire a token. *Example: "I see the Business uses PSP-X. I will call the PSP-X SDK with the Business's Key to get a token."* |

### 2.3 Payment in the Checkout Lifecycle

The payment process follows a standard 3-step lifecycle within UCP:
**Negotiation**, **Acquisition**, and **Completion**.

![High-level payment flow sequence diagram](site:specification/images/ucp-payment-flow.png)

1.  **Negotiation (Business → Platform):** The business analyzes the cart and advertises available `handlers`. This tells the platform *how* to pay (e.g., "Use this specific PSP endpoint with this public key").
2.  **Acquisition (Platform ↔ PSP):** The platform executes the handler's logic. This happens client-side or agent-side, directly with the payment credential provider (e.g., exchanging credentials for a network token via a PSP). The business is not involved, ensuring raw data never touches the business's frontend API.
3.  **Completion (Platform → Business):** The platform submits the opaque credential (token) to the business. The business uses it to capture funds via their backend integration with the PSP.

### 2.4 Payment Handlers

Payment Handlers are the contract that binds the three parties together. This
setup allows for a variety of different payment methods and token-types to be
supported, including network tokens. They are standardized definitions
typically authored by payment credential provider or the UCP governing body.

| Field | Description |
| :--- | :--- |
| `name` | The reverse-DNS ID of the handler protocol (e.g., `com.google.pay`). |
| `spec` | URL to the human-readable documentation for the Platform developer. |
| `config_schema` | JSON Schema validating the `config` object the Business **MUST** provide. |
| `instrument_schemas` | JSON Schema validating the payload the Platform **MUST** send to complete. |

**Dynamic Filtering:** Businesses **MUST** filter the `handlers` list based on
the context of the cart (e.g., removing "Buy Now Pay Later" for subscription
items, or filtering regional methods based on shipping address).

### 2.5 Risk Signals

To aid in fraud assessment, the Platform **MAY** include additional risk signals
in the `complete` call, providing the Business with more context about the
transaction's legitimacy. The structure and content of these risk signals are
not strictly defined by this specification, allowing flexibility based on the
agreement between the Platform and Business or specific payment handler
requirements.

**Example (Flexible Structure):**

```json
{
  "risk_signals": {
    "session_id": "abc_123_xyz",
    "score": 0.95,
  }
}
```

### 2.6 Implementation Scenarios

The following scenarios illustrate how different payment methods are negotiated
and executed using concrete data examples.

#### 2.6.1 Scenario A: Digital Wallet (Google Pay)
In this scenario, the platform identifies the `com.google.pay` handler and uses
the Google Pay API to acquire an encrypted payment token.

**1. Business Advertisement (Response from Create Checkout)**
```json
{
  "payment": {
    "handlers": [{
      "id": "gpay",
      "name": "com.google.pay",
      "version": "2026-01-11",
      "spec": "https://pay.google.com/gp/p/ucp/2026-01-11/",
      "config_schema": "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/config.json",
      "instrument_schemas": [
        "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/gpay_card_payment_instrument.json"
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

**2. Token Execution (Platform Side)**
The platform recognizes `com.google.pay`. It passes the `config` into the
Google Pay API. Google Pay returns the encrypted token data.

**3. Complete Checkout (Request to Business)**
The Platform wraps the Google Pay response into a payment instrument.

```json
POST /checkout-sessions/{id}/complete
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
      "token": "examplePaymentMethodToken..."
    }
  },
  "risk_signals": {
    // ... host could send risk_signals here
  }
}
```

#### 2.6.2 Scenario B: Direct Tokenization with Challenge (SCA)
In this scenario, the platform uses a generic tokenizer to request a session
token or network tokens. The bank requires Strong Customer
Authentication (SCA/3DS), forcing the business to pause completion and
request a challenge.

**1. Business Advertisement**

```json
{
  "payment": {
    "handlers": [{
      "id": "merchant_tokenizer",
      "name": "com.example.tokenizer",
      // ... more handler required field
      "config": {
        "token_url": "https://api.psp.com/tokens",
        "public_key": "pk_123"
      }
    }]
  }
}
```

**2. Token Execution (Platform Side)**

The platform calls `https://api.psp.com/tokens` which identity **SHOULD** have
previous legal binding connection with them and receives `tok_visa_123`
(which could represent a vaulted card or network token).

**3. Complete Checkout (Request to Business)**
```json
POST /checkout-sessions/{id}/complete
{
  "payment_data": {
    "handler_id": "merchant_tokenizer",
    // ... more instrument required field
    "credential": { "token": "tok_visa_123" }
  },
  "risk_signals": {
    // ... host could send risk_signals here
  }
}
```

**4. Challenge Required (Response from Business)**

The business attempts the charge, but the PSP returns a "Soft Decline"
requiring 3DS.

```json
HTTP/1.1 200 OK
{
  "status": "requires_escalation",
  "messages": [{
    "type": "error",
    "code": "requires_3ds",
    "content": "Your bank requires verification.",
    "severity": "requires_buyer_input"
  }],
  "continue_url": "https://psp.com/challenge/123"
}
```

*The platform **MUST** now open `continue_url` in a WebView/Window for the user
to complete the bank check, then retry the completion.*

#### 2.6.3 Scenario C: Autonomous Agent (AP2)

This scenario demonstrates the **Recommended Flow for Agents**. Instead of a
session token, the agent generates cryptographic mandates.

**1. Business Advertisement**
```json
{
  "payment": {
    "handlers": [{
      "id": "ap2_checkout",
      "name": "dev.ucp.ap2_mandate_compatible_handlers",
      // ... other fields handler required
    }]
  }
}
```

**2. Agent Execution**

The agent cryptographically signs objects using the user's private key on a
non-agentic surface.

**3. Complete Checkout**
```json
POST /checkout-sessions/{id}/complete
{
  "payment_data": {
    "handler_id": "ap2_checkout",
    "credential": {
      "type": "card",
      "token": "eyJhbGciOiJ...", // Token would contain payment_mandate, the signed proof of Funds Auth
    }
  },
  "risk_signals": {
    "session_id": "abc_123"
  },
  "ap2": {
    "checkout_mandate": "eyJhbGciOiJ...", // Signed proof of Checkout Terms
  }
}
```

*This provides the business with non-repudiable proof that the user authorized
this specific transaction, enabling safe autonomous processing.*

#### PCI-DSS Scope Management

**Agent Scope**

Most agent implementations can **avoid PCI-DSS scope** by:

-   Using handlers that provide opaque credentials (encrypted data, token
    references, etc.)
-   Never accessing or storing raw payment data (card numbers, CVV, etc.)
-   Forwarding credentials without the ability to use them directly
-   Using PSP tokenization payment handlers where raw credentials never pass
    through the agent

**Business Scope**

Businesses can minimize PCI scope by:

-   Using PSP-hosted tokenization (PSP tokenization - PSP stores
    credentials, business receives token reference)
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

**For Businesses:**

1.  Validate handler_id before processing (ensure handler is in advertised set)
2.  Use separate PSP credentials for TEST vs PRODUCTION environments
3.  Implement idempotency for payment processing (prevent double-charges)
4.  Log payment events without logging credentials
5.  Set appropriate credential timeouts
6.  For highly sensitive transactions, consider supporting the
    `dev.ucp.shopping.ap2_mandate` extension. This allows businesses to
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
6.  When available, prefer businesses supporting the
    `dev.ucp.shopping.ap2_mandate` extension. Verify the
    `ap2.merchant_authorization` signature to ensure the checkout terms are
    authentically from the business and have not been tampered with.
7.  When the AP2 Mandates Extension is active, ensure a cryptographically signed
   `checkout_mandate` and `payment_mandate` are generated upon user consent, as
    detailed in the extension specification.

**For Handler Providers:**

1.  Secure credentials for the specific business (encryption, tokenization, or
    other handler-specific methods)
2.  Implement rate limiting on credential acquisition
3.  Validate agent authorization before providing credentials
4.  Set reasonable credential expiration (e.g., 60 minutes for tokens, time-
    limited encrypted payloads)
5.  Ensure credentials cannot be used by agents directly (only by the intended
    business)
6.  If applicable, provide mechanisms for businesses or PSPs to verify
    `payment_mandate` credentials received through the AP2 flow.

#### Fraud Prevention Integration

While UCP does not define fraud prevention APIs, the payment architecture
supports fraud signal integration:

-   Businesses can require additional fields in handler configurations (e.g.,
    3DS requirements)
-   Agents can submit device fingerprints and session data alongside credentials
-   Handler providers can perform risk assessment during credential acquisition
-   Businesses can reject high-risk transactions and request additional
    verification

Future extensions **MAY** standardize fraud signal schemas, but the current
architecture allows flexible integration with existing fraud prevention systems.

## 3. Transport Layer

UCP supports multiple transport protocols. Platforms and businesses effectively
negotiate the transport via `services` on their profiles.

### 3.1 REST Transport (Core)

The primary transport for UCP is **HTTP/1.1** (or higher) using RESTful
patterns.

*   **Content-Type:** Requests and responses **MUST** use `application/json`.
*   **Methods:** Implementations **MUST** use standard HTTP verbs (e.g., `POST`
    for creation, `GET` for retrieval).
*   **Status Codes:** Implementations **MUST** use standard HTTP status codes
    (e.g., 200, 201, 400, 401, 500).

### 3.2 Model Context Protocol (MCP)

UCP capabilities map 1:1 to MCP tools. A business **MAY** expose an MCP server
that wraps their UCP implementation, allowing LLMs to call tools like
`create_checkout` directly.

### 3.2 Agent-to-Agent Protocol (A2A)

A business **MAY** expose an A2A agent that supports UCP as an A2A Extension,
allowing integration with platforms over structured UCP data types.

### 3.3 Embedded Protocol (EP)

A business **MAY** embed an interface onto an eligible host that would
receive events as the user interacts with the interface and delegate key user
actions.

Initiation comes through a `continue_url` that is returned by the business.

## 4. Standard Capabilities

UCP defines a set of standard capabilities:

| Capability Name      | ID (URI)                                         | Description                                                                                                  |
| :------------------- | :----------------------------------------------- | :----------------------------------------------------------------------------------------------------------- |
| **Checkout**         | `{{ ucp_url }}/schemas/shopping/checkout.json`         | Facilitates the creation and management of checkout sessions, including cart management and tax calculation. |
| **Identity Linking** | - | Enables platforms to obtain authorization via OAuth 2.0 to perform actions on a user's behalf.               |
| **Order**            | `{{ ucp_url }}/schemas/shopping/order.json`            | Allows businesses to push asynchronous updates about an order's lifecycle (shipping, delivery, returns).      |

### 4.2 Definition & Extensions

Detailed definitions for endpoints, schemas, and valid extensions for each
capability are provided in their respective specification files. Extensions are
typically versioned and defined alongside their parent capability.

## 5. Security & Authentication

### 5.1 Transport Security

All UCP communication **MUST** occur over **HTTPS**.

### 5.2 Request Authentication

*   **Platform to Business:** Requests **SHOULD** be authenticated using
    standard headers (e.g., `Authorization: Bearer <token>`).
*   **Business to Platform (Webhooks):** Webhooks **MUST** be signed using a
    shared secret or asymmetric key to verify integrity and origin.

### 5.3 Data Privacy

Sensitive data (such as Payment Credentials or PII) **MUST** be handled
according to PCI-DSS and GDPR guidelines. UCP encourages the use of tokenized
payment data to minimize business and platform liability.

### 5.4 Transaction Integrity and Non-Repudiation

For enhanced security and non-repudiation, UCP supports AP2 mandates extension.
When negotiated:

*   Businesses provide a cryptographic signature on the checkout terms (`ap2.merchant_authorization`).
*   Platforms provide a cryptographic mandate from the user, authorizing the payment and a specific checkout state (`ap2.checkout_mandate` and a `payment_mandate`).

This mechanism, based on the [AP2 Protocol](https://ap2-protocol.org/), provides
strong, end-to-end cryptographic assurances about the transaction details and
participant consent, significantly reducing risks of tampering and disputes.
Implementers **SHOULD** consider supporting this extension for sensitive or
high-value transactions.

## 6. Versioning

### 6.1 Version Format

UCP uses date-based versioning in the format `YYYY-MM-DD`. This provides
clear chronological ordering and unambiguous version comparison.

### 6.2 Version Discovery and Negotiation

UCP prioritizes strong backwards compatibility. Businesses implementing a
version **SHOULD** handle requests from platforms using that version or older.

Both businesses and platforms declare a single version in their profiles:

#### Example

=== Business Profile:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "services": { ... },
    "capabilities": [ ... ]
  },
  "payment": { ... }
}
```

=== Platform Profile:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [ ... ]
  },
  "payment": { ... }
}
```

### 6.3 Version Negotiation

![High-level resolution flow sequence diagram](site:specification/images/ucp-discovery-negotiation.png)

Businesses MUST validate the platform's version and determine compatibility:

1.  Platform declares version via profile referenced in request
2.  Business validates:
    *   If platform version ≤ business version: Business **MUST**
        process the request
    *   If platform version > business version: Business **MUST** return
        `version_unsupported` error
3.  Businesses **MUST** include the version used for processing in every
    response.

Response with version confirmation:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [ ... ]
  },
  "id": "checkout_123",
  "status": "incomplete"
  ...other checkout fields
}
```

Version unsupported error:

```json
{
  "status": "requires_escalation",
  "messages": [{
    "type": "error",
    "code": "version_unsupported",
    "message": "Version 2026-01-12 is not supported. This business implements version 2026-01-11.",
    "severity": "requires_buyer_input"
  }]
}
```

### 6.4 Backwards Compatibility

#### Backwards-Compatible Changes

The following changes **MAY** be introduced without a new version:

*   Adding new non-required fields to responses
*   Adding new non-required parameters to requests
*   Adding new endpoints, methods, or operations to a transport
*   Adding new error codes with existing error structures
*   Adding new values to enums (unless explicitly documented as exhaustive)
*   Changing the order of fields in responses
*   Changing the length or format of opaque strings (IDs, tokens)

#### Breaking Changes:

The following changes **MUST NOT** be introduced without a new version:

*   Removing or renaming existing fields
*   Changing field types or semantics
*   Making non-required fields required
*   Removing operations, methods, or endpoints
*   Changing authentication or authorization requirements
*   Modifying existing protocol flow or state machine
*   Changing the meaning of existing error codes

### 6.5 Independent Component Versioning

*   UCP protocol versions independently from capabilities.
*   Each capability versions independently from other capabilities.
*   Capabilities **MUST** follow the same backwards compatibility rules as the
    protocol.
*   Businesses **MUST** validate capability version compatibility using the same
    logic as what's described above.
*   Transports **MAY** define their own version handling mechanisms.

## 7. Glossary

| Term                              | Acronym | Definition                                                                                                                                                    |
| :-------------------------------- | :------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Agent Payments Protocol**       | AP2     | An open protocol designed to enable AI agents to securely interoperate and complete payments autonomously. UCP leverages AP2 for secure payment mandates.     |
| **Agent2Agent Protocol**          | A2A     | An open standard for secure, collaborative communication between diverse AI agents. UCP can use A2A as a transport layer.                                     |
| **Capability**                    | -       | A standalone core feature that a business supports (e.g., Checkout, Identity Linking). Capabilities are the fundamental "verbs" of UCP.                       |
| **Credential Provider**           | CP      | A trusted entity (like a digital wallet) responsible for securely managing and executing the user's payment and identity credentials.                         |
| **Extension**                     | -       | An optional module that augments a specific UCP Capability, allowing for specialized functionality (e.g., Discounts) without bloating the core specification. |
| **Profile**                       | -       | A JSON document hosted by businesses and platforms at a well-known URI, declaring their identity, supported capabilities, and endpoints.                      |
| **Business**                      | -       | The entity selling goods or services. In UCP, they act as the **Merchant of Record (MoR)**, retaining financial liability and ownership of the order.         |
| **Model Context Protocol**        | MCP     | A protocol standardizing how AI models connect to external data and tools. UCP capabilities map 1:1 to MCP tools.                                             |
| **Universal Commerce Protocol**   | UCP     | The standard defined in this document, enabling interoperability between commerce entities via standardized capabilities and discovery.                       |
| **Payment Service Provider**      | PSP     | The financial infrastructure provider (e.g., Stripe, Adyen) that processes payments, authorizations, and settlements on behalf of the business.               |
| **Platform**                      | -       | The consumer-facing surface (AI agent, app, website) acting on behalf of the user to discover businesses and facilitate commerce.                              |
| **Verifiable Digital Credential** | VDC     | An Issuer-signed credential (set of claims) whose authenticity can be verified cryptographically. Used in UCP for secure payment authorizations.              |
| **Verifiable Presentation**       | VP      | A presentation of one or more VDCs that includes a cryptographic proof of binding, used to prove authorization to a business or PSP.                          |