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

## Overarching guidelines

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this
document are to be interpreted as described in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.html){ target="_blank" } and
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174.html){ target="_blank" }.

Schema notes:

- Date format: Always specified as
    [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339.html){ target="_blank" }
    unless otherwise specified
- Amounts format: Minor units (cents)

## Discovery, Governance, and Negotiation

UCP employs a server-selects architecture where the business (server) chooses
the protocol version and capabilities from the intersection of both parties'
capabilities. Both business and platform profiles can be cached by both parties,
allowing efficient capability negotiation within the normal request/response
flow between platform and business.

### Namespace Governance

UCP uses reverse-domain naming to encode governance authority directly into
capability identifiers. This eliminates the need for a central registry.

#### Naming Convention

All capability and service names **MUST** use the format:

```text
{reverse-domain}.{service}.{capability}
```

**Components:**

- `{reverse-domain}` - Authority identifier derived from domain ownership
- `{service}` - Service/vertical category (e.g., `shopping`, `common`)
- `{capability}` - The specific capability name

**Examples:**

| Name                                | Authority   | Service  | Capability       |
| ----------------------------------- | ----------- | -------- | ---------------- |
| `dev.ucp.shopping.checkout`         | ucp.dev     | shopping | checkout         |
| `dev.ucp.shopping.fulfillment`      | ucp.dev     | shopping | fulfillment      |
| `dev.ucp.common.identity_linking`   | ucp.dev     | common   | identity_linking |
| `com.example.payments.installments` | example.com | payments | installments     |

#### Spec URL Binding

The `spec` and `schema` fields are **REQUIRED** for all capabilities. The origin
of these URLs **MUST** match the namespace authority:

| Namespace       | Required Origin           |
| --------------- | ------------------------- |
| `dev.ucp.*`     | `https://ucp.dev/...`     |
| `com.example.*` | `https://example.com/...` |

Platform **MUST** validate this binding and **SHOULD** reject capabilities where
the spec origin does not match the namespace authority.

#### Governance Model

| Namespace Pattern | Authority    | Governance          |
| ----------------- | ------------ | ------------------- |
| `dev.ucp.*`       | ucp.dev      | UCP governing body  |
| `com.{vendor}.*`  | {vendor}.com | Vendor organization |
| `org.{org}.*`     | {org}.org    | Organization        |

The `dev.ucp.*` namespace is reserved for capabilities sanctioned by the UCP
governing body. Vendors **MUST** use their own reverse-domain namespace for
custom capabilities.

### Services

A **service** defines the API surface for a vertical (shopping, common, etc.).
Services include operations, events, and transport bindings defined via
standard formats:

- **REST**: OpenAPI 3.x (JSON format)
- **MCP**: OpenRPC (JSON format)
- **A2A**: Agent Card Specification
- **EP(embedded)**: OpenRPC (JSON format)

#### Service Definition

| Field             | Type   | Required | Description                         |
| ----------------- | ------ | -------- | ----------------------------------- |
| `version`         | string | Yes      | Service version (YYYY-MM-DD format) |
| `spec`            | string | Yes      | URL to service documentation        |
| `rest`            | object | No       | REST transport binding              |
| `rest.schema`     | string | Yes      | URL to OpenAPI spec (JSON)          |
| `rest.endpoint`   | string | Yes      | Business's REST endpoint            |
| `mcp`             | object | No       | MCP transport binding               |
| `mcp.schema`      | string | Yes      | URL to OpenRPC spec (JSON)          |
| `mcp.endpoint`    | string | Yes      | Business's MCP endpoint             |
| `a2a`             | object | No       | A2A transport binding               |
| `a2a.endpoint`    | string | Yes      | Business's A2A Agent Card URL       |
| `embedded`        | string | No       | Embedded transport binding          |
| `embedded.schema` | string | Yes      | URL to OpenRPC spec (JSON)          |

Transport definitions **MUST** be thin: they declare method names and reference
base schemas only. See [Requirements](#requirements) for details.

#### Endpoint Resolution

The `endpoint` field provides the base URL for API calls. OpenAPI paths are
appended to this endpoint to form the complete URL.

**Example:**

```json
{
  "version": "2026-01-11",
  "transport": "rest",
  "schema": "https://ucp.dev/services/shopping/openapi.json",
  "endpoint": "https://business.example.com/api/v2"
}
```

With OpenAPI path `/checkout-sessions`, the resolved URL is:

```text
POST https://business.example.com/api/v2/checkout-sessions
```

**Rules:**

- `endpoint` **MUST** be a valid URL with scheme (https)
- `endpoint` **SHOULD NOT** have a trailing slash
- OpenAPI paths are relative and appended directly to endpoint
- Same resolution applies to MCP endpoints for JSON-RPC calls
- `endpoint` for A2A transport refers to the Agent Card URL for the agent

### Capabilities

A **capability** is a feature within a service. It declares what
functionality is supported and where to find documentation and schemas.

#### Capability Definition

{{ extension_schema_fields('capability.json#/$defs/platform_schema', 'capability-schema') }}

#### Extensions

An **extension** is an optional module that augments another capability.
Extensions use the `extends` field to declare their parent(s):

```json
{
  "dev.ucp.shopping.fulfillment": [
    {
      "version": "2026-01-23",
      "spec": "https://ucp.dev/2026-01-23/specification/fulfillment",
      "schema": "https://ucp.dev/2026-01-23/schemas/shopping/fulfillment.json",
      "extends": "dev.ucp.shopping.checkout"
    }
  ]
}
```

##### Multi-Parent Extensions

Extensions **MAY** extend multiple parent capabilities by using an array:

```json
{
  "dev.ucp.shopping.discount": [
    {
      "version": "2026-01-23",
      "spec": "https://ucp.dev/2026-01-23/specification/discount",
      "schema": "https://ucp.dev/2026-01-23/schemas/shopping/discount.json",
      "extends": ["dev.ucp.shopping.checkout", "dev.ucp.shopping.cart"]
    }
  ]
}
```

When an extension declares multiple parents:

- The extension **MAY** define different fields for each capability it extends
    (e.g., `loyalty_earned` for checkout, `loyalty_preview` for cart)
- See [Intersection Algorithm](#intersection-algorithm) for negotiation rules

Extensions can be:

- **Official**: `dev.ucp.shopping.fulfillment` extends `dev.ucp.shopping.checkout`
- **Vendor**: `com.example.installments` extends `dev.ucp.shopping.checkout`

### Schema Composition

Extensions can add new fields and modify shared structures (e.g., discounts
modify `totals`, fulfillment adds fulfillment to `totals.type`).

#### Requirements

- Transport definitions (OpenAPI/OpenRPC) **MUST** reference base schemas
    only. They **MUST NOT** enumerate fields or define payload shapes inline.
- Extensions **MUST** be self-describing. Each extension schema **MUST**
    declare the types it introduces and how it modifies base types using `allOf`
    composition.
- Platforms **MUST** resolve schemas client-side by fetching and composing
    base schemas with active extension schemas.

#### Extension Schema Pattern

Extension schemas define composed types using `allOf`. The `$defs` key **MUST**
use the full parent capability name (reverse-domain format) to enable
deterministic schema resolution:

```json
{
  "$defs": {
    "discounts_object": { ... },
    "dev.ucp.shopping.checkout": {
      "title": "Checkout with Discount",
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

**Requirements:**

- Extension schemas **MUST** have a `$defs` entry for each parent declared in
    `extends`
- The `$defs` key **MUST** match the parent's full capability name exactly

This convention ensures:

- **Self-documenting**: The schema declares exactly which parents it extends
- **Deterministic resolution**: The `extends` value maps directly to the `$defs` key
- **Verifiable**: Build-time checks can confirm each `extends` entry has a
    matching `$defs` key

#### Schema Resolution Convention

To validate payloads, implementations resolve extension schemas as follows:

1. Determine the root capability from the operation (e.g., checkout operations
    use `dev.ucp.shopping.checkout`)
2. For each active extension, resolve and apply its `$defs[{root_capability}]`

**Example:** A checkout response includes the discount extension.

- Root capability: `dev.ucp.shopping.checkout`
- Extension schema: `discount.json`
- Resolve: `discount.json#/$defs/dev.ucp.shopping.checkout`

#### Resolution Flow

Platforms **MUST** resolve schemas following this sequence:

1. **Discovery**: Fetch business profile from `/.well-known/ucp`
2. **Negotiation**: Compute capability intersection (see
    [Intersection Algorithm](#intersection-algorithm))
3. **Schema Fetch**: Fetch base schema and all active extension schemas
4. **Compose**: Merge schemas via `allOf` chains based on active extensions
5. **Validate**: Validate requests and responses against the composed schema

### Profile Structure

#### Business Profile

Businesses publish their profile at `/.well-known/ucp`. An example:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/overview",
          "transport": "rest",
          "endpoint": "https://business.example.com/ucp/v1",
          "schema": "https://ucp.dev/services/shopping/openapi.json"
        },
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/overview",
          "transport": "mcp",
          "endpoint": "https://business.example.com/ucp/mcp",
          "schema": "https://ucp.dev/services/shopping/mcp.openrpc.json"
        },
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/overview",
          "transport": "a2a",
          "endpoint": "https://business.example.com/.well-known/agent-card.json"
        },
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/overview",
          "transport": "embedded",
          "schema": "https://ucp.dev/services/shopping/embedded.openrpc.json"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/checkout",
          "schema": "https://ucp.dev/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.shopping.fulfillment": [
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/fulfillment",
          "schema": "https://ucp.dev/schemas/shopping/fulfillment.json",
          "extends": "dev.ucp.shopping.checkout"
        }
      ],
      "dev.ucp.shopping.discount": [
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/discount",
          "schema": "https://ucp.dev/schemas/shopping/discount.json",
          "extends": "dev.ucp.shopping.checkout"
        }
      ]
    },
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {
          "id": "processor_tokenizer",
          "version": "2026-01-11",
          "spec": "https://example.com/specs/payments/processor_tokenizer",
          "schema": "https://example.com/specs/payments/merchant_tokenizer.json",
          "config": {
            "type": "CARD",
            "tokenization_specification": {
              "type": "PUSH",
              "parameters": {
                "token_retrieval_url": "https://api.psp.example.com/v1/tokens"
              }
            }
          }
        }
      ]
    }
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

The `ucp` object contains protocol metadata: version, services, capabilities,
and payment handlers. The `signing_keys` array contains public keys (JWK format)
used to verify signatures on webhooks and other authenticated messages from the
business. See [Key Discovery](#key-discovery) for key lookup and resolution,
and [Message Signatures](signatures.md) for signing mechanics.

#### Platform Profile

Platform profiles are similar and include signing keys for capabilities
requiring cryptographic verification. Capabilities **MAY** include a `config`
object for capability-specific settings (e.g., callback URLs, feature flags). An
example:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/services/shopping/openapi.json"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/checkout",
          "schema": "https://ucp.dev/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.shopping.fulfillment": [
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/fulfillment",
          "schema": "https://ucp.dev/schemas/shopping/fulfillment.json",
          "extends": "dev.ucp.shopping.checkout"
        }
      ],
      "dev.ucp.shopping.order": [
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/order",
          "schema": "https://ucp.dev/schemas/shopping/order.json",
          "config": {
            "webhook_url": "https://platform.example.com/webhooks/ucp/orders"
          }
        }
      ]
    },
    "payment_handlers": {
      "com.google.pay": [
        {
          "id": "gpay_1234",
          "version": "2024-12-03",
          "spec": "https://developers.google.com/merchant/ucp/guides/gpay-payment-handler",
          "schema": "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/gpay_config.json"
        }
      ],
      "dev.shopify.shop_pay": [
        {
          "id": "shop_pay_1234",
          "version": "2026-01-11",
          "spec": "https://shopify.dev/ucp/shop-pay-handler",
          "schema": "https://shopify.dev/ucp/schemas/shop-pay-config.json"
        }
      ],
      "dev.ucp.processor_tokenizer": [
        {
          "id": "processor_tokenizer",
          "version": "2026-01-11",
          "spec": "https://example.com/specs/payments/processor_tokenizer-payment",
          "schema": "https://ucp.dev/schemas/payments/delegate-payment.json"
        }
      ]
    }
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

### Platform Advertisement on Request

Platforms **MUST** communicate their profile URI with each request to enable
capability negotiation.

**HTTP Transport:** Platforms **MUST** use Dictionary Structured Field syntax
([RFC 8941](https://datatracker.ietf.org/doc/html/rfc8941){ target="_blank" })
in the UCP-Agent header:

```text
POST /checkout HTTP/1.1
UCP-Agent: profile="https://agent.example/profiles/shopping-agent.json"
Content-Type: application/json

{"line_items": [...]}
```

**MCP Transport:** Platforms **MUST** include a `meta` object containing request
metadata:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "create_checkout",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://agent.example/profiles/shopping-agent.json"
        }
      },
      "checkout": {
        "line_items": [...]
      }
    }
  },
  "id": 1
}
```

### Negotiation Protocol

#### Platform Requirements

1. **Profile Advertisement**: Platforms **MUST** include their profile URI in
    every request using the transport-appropriate mechanism.
2. **Discovery**: Platforms **MAY** fetch the business profile from
    `/.well-known/ucp` before initiating requests. If fetched, platforms
    **SHOULD** cache the profile according to HTTP cache-control directives.
3. **Namespace Validation**: Platforms **MUST** validate that capability `spec`
    URI origins match namespace authorities.
4. **Schema Resolution**: Platforms **MUST** fetch and compose schemas for
    negotiated capabilities before making requests.

#### Business Requirements

1. **Profile Resolution**: Upon receiving a request with a platform profile
    URI, businesses **MUST** fetch and validate the platform profile unless
    already cached.
2. **Capability Intersection**: Businesses **MUST** compute the intersection of
    platform and business capabilities.
3. **Extension Validation**: Extensions without their parent capability in the
    intersection **MUST** be excluded.
4. **Response Requirements**: Businesses **MUST** include the `ucp` field in
    every response containing:
    - `version`: The UCP version used to process the request
    - `capabilities`: Array of active capabilities for this response

#### Intersection Algorithm

The capability intersection algorithm determines which capabilities are active
for a session:

1. **Compute intersection**: For each business capability, include it in the
    result if a platform capability with the same `name` exists.

2. **Prune orphaned extensions**: Remove any capability where `extends` is
    set but **none** of its parent capabilities are in the intersection.
    - For single-parent extensions (`extends: "string"`): parent must be present
    - For multi-parent extensions (`extends: ["a", "b"]`): at least one parent
        must be present

3. **Repeat pruning**: Continue step 2 until no more capabilities are removed
    (handles transitive extension chains).

The result is the set of capabilities both parties support, with extension
dependencies satisfied.

#### Error Handling

UCP negotiation can fail in two ways:

1. **Discovery failure**: The business cannot fetch or parse the platform's
   profile.

2. **Negotiation failure**: The provided profile is valid but capability
   intersection is empty or versions are incompatible.

These failure types require different handling:

- **Discovery failure** → transport error with optional `continue_url`
- **Negotiation failure** → UCP response with optional `continue_url`

##### Error Codes

**Negotiation Errors:**

| Code                        | Description                                          | REST | MCP    |
| --------------------------- | ---------------------------------------------------- | ---- | ------ |
| `invalid_profile_url`       | Profile URL is malformed, missing, or unresolvable   | 400  | -32001 |
| `profile_unreachable`       | Resolved URL but fetch failed (timeout, non-2xx)     | 424  | -32001 |
| `profile_malformed`         | Fetched content is not valid JSON or violates schema | 422  | -32001 |
| `capabilities_incompatible` | No compatible capabilities in intersection           | 200  | result |
| `version_unsupported`       | Platform's UCP version is not supported              | 200  | result |

**Signature Errors:**

| Code                   | Description                                            | REST | MCP    |
| ---------------------- | ------------------------------------------------------ | ---- | ------ |
| `signature_missing`    | Required signature header/field not present            | 401  | -32000 |
| `signature_invalid`    | Signature verification failed                          | 401  | -32000 |
| `key_not_found`        | Key ID not found in signer's `signing_keys`            | 401  | -32000 |
| `digest_mismatch`      | Body digest doesn't match `Content-Digest` header      | 400  | -32600 |
| `algorithm_unsupported`| Signature algorithm not supported                      | 400  | -32600 |

See [Message Signatures](signatures.md) for signature verification details.

**Protocol Errors:**

| HTTP | Description                                     | MCP        |
| ---- | ----------------------------------------------- | ---------- |
| 401  | Authentication required or credentials invalid  | -32000     |
| 403  | Authenticated but insufficient permissions      | -32000     |
| 409  | Idempotency key reused with different payload   | -32000     |
| 429  | Too many requests                               | -32000     |
| 500  | Unexpected server error                         | -32603     |
| 503  | Server temporarily unable to handle requests    | -32000     |

For MCP over HTTP, the HTTP status code is the primary signal; the JSON-RPC
`error.code` provides a secondary signal. Both transports **SHOULD** include
`Retry-After` header (REST) or `error.data.retry_after` (MCP) for 429 and 503
responses.

##### The `continue_url` Field

When UCP negotiation fails, `continue_url` provides a fallback web experience.
Businesses **SHOULD** provide the most contextually relevant URL:

- For checkout operations: link to the cart or checkout page
- For catalog operations: link to the product or search results
- As a fallback: link to the storefront homepage

This enables graceful degradation—agents can redirect buyers to complete their
task through the standard web interface.

##### Transport Bindings

=== "REST"

    **Discovery Failure (424):**

    ```http
    HTTP/1.1 424 Failed Dependency
    Content-Type: application/json

    {
      "code": "profile_unreachable",
      "content": "Unable to fetch agent profile: connection timeout",
      "continue_url": "https://merchant.com/cart"
    }
    ```

    **Negotiation Failure (200):**

    ```http
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "2026-01-11",
        "capabilities": {}
      },
      "messages": [
        {
          "type": "error",
          "code": "version_unsupported",
          "content": "UCP version 2024-01-01 is not supported",
          "severity": "requires_buyer_input"
        }
      ],
      "continue_url": "https://merchant.com"
    }
    ```

    **Protocol Error — Rate Limit (429):**

    ```http
    HTTP/1.1 429 Too Many Requests
    Retry-After: 60
    ```

    **Protocol Error — Unauthorized (401):**

    ```http
    HTTP/1.1 401 Unauthorized
    WWW-Authenticate: Bearer realm="ucp"
    ```

    Protocol errors use standard HTTP status codes and headers. Response bodies
    are optional.

=== "MCP"

    **Discovery Failure (JSON-RPC error):**

    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "error": {
        "code": -32001,
        "message": "UCP discovery failed",
        "data": {
          "code": "profile_unreachable",
          "content": "Unable to fetch agent profile: connection timeout",
          "continue_url": "https://merchant.com/cart"
        }
      }
    }
    ```

    **Negotiation Failure (JSON-RPC result):**

    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
          "ucp": {
            "version": "2026-01-11",
            "capabilities": {}
          },
          "messages": [
            {
              "type": "error",
              "code": "version_unsupported",
              "content": "UCP version 2024-01-01 is not supported",
              "severity": "requires_buyer_input"
            }
          ],
          "continue_url": "https://merchant.com"
        },
        "content": [
          {"type": "text", "text": "{\"ucp\":{...},\"messages\":[...],\"continue_url\":\"...\"}"}
        ]
      }
    }
    ```

    **Protocol Error — Rate Limit (JSON-RPC error):**

    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "error": {
        "code": -32000,
        "message": "Rate limit exceeded",
        "data": {
          "retry_after": 60
        }
      }
    }
    ```

    **Protocol Error — Unauthorized (JSON-RPC error):**

    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "error": {
        "code": -32000,
        "message": "Unauthorized"
      }
    }
    ```

    When using Streamable HTTP transport, servers **MUST** return the
    corresponding HTTP status code (e.g., `429` for rate limit) alongside
    the JSON-RPC error. The HTTP status code is the primary signal for
    error type.

#### Capability Declaration in Responses

The `capabilities` registry in responses indicates active capabilities:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {"version": "2026-01-11"}
      ],
      "dev.ucp.shopping.fulfillment": [
        {"version": "2026-01-11"}
      ]
    },
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {"id": "processor_tokenizer", "version": "2026-01-11"}
      ]
    }
  },
  "id": "checkout_123",
  "line_items": [...]
  ... other fields
}
```

#### Response Capability Selection

Businesses **MUST** include in `ucp.capabilities` only the capabilities that are:

1. In the negotiated intersection for this session, AND
2. Relevant to this response's operation type

**Root Capability Relevance:**

A root capability is relevant if it matches the operation type:

- `create_checkout` / `update_checkout` / `complete_checkout` →
    `dev.ucp.shopping.checkout`
- `create_cart` / `update_cart` → `dev.ucp.shopping.cart`
- Order webhooks → `dev.ucp.shopping.order`

**Extension Relevance:**

An extension is relevant if **any** of its `extends` values matches a relevant
root capability.

**Selection Examples:**

| Response Type | Includes                        | Does NOT Include             |
| ------------- | ------------------------------- | ---------------------------- |
| Checkout      | checkout, discount, fulfillment | cart, order                  |
| Cart          | cart, discount                  | checkout, fulfillment, order |
| Order         | order                           | checkout, cart, discount     |

## Identity & Authentication

UCP profiles serve dual purpose: they declare a party's **capabilities**
for negotiation (see [Profile Structure](#profile-structure)) and publish
**signing keys** for identity verification — enabling both capability
negotiation and cryptographic authentication from a single document.

Businesses publish their profile at `/.well-known/ucp` as the discovery
entry point — platforms fetch it to determine protocol support, locate
endpoints, and negotiate capabilities. Platforms advertise their profile
URL per-request via the `UCP-Agent` header, enabling businesses to
negotiate capabilities and verify identity. This design enables
**permissionless onboarding** — any platform with a discoverable profile
can interact with any business without prior registration.

### Authentication Mechanisms

Businesses **SHOULD** authenticate platforms to prevent impersonation and ensure
message integrity. UCP is compatible with multiple authentication mechanisms:

- **API Keys** — Pre-shared secrets exchanged out-of-band
- **OAuth 2.0** — Client credentials or other OAuth flows
- **mTLS** — Mutual TLS with client certificates
- **HTTP Message Signatures** — Cryptographic signatures per
  [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421) (see
  [Message Signatures](signatures.md) for full specification)

HTTP Message Signatures enable permissionless onboarding — businesses can
verify platforms by their advertised public keys without negotiating shared
secrets. The other mechanisms require prior credential exchange and imply a
pre-established relationship.

Business-to-platform webhooks **MUST** be signed. See
[Message Signatures — When Signatures Apply](signatures.md#when-signatures-apply).

#### Identity Binding

Regardless of authentication mechanism, verifiers **MUST** ensure the
authenticated identity is consistent with the `UCP-Agent` header:

- **HTTP Message Signatures** — The signer's profile (from `UCP-Agent`) is
    verified by signature validation; no additional check needed.
- **API keys / OAuth / mTLS** — Verifiers **MUST** confirm the authenticated
    principal is authorized to act on behalf of the profile identified in
    `UCP-Agent`. Reject requests where the authenticated identity and claimed
    profile conflict.

### Key Discovery

Both parties publish public keys in the `signing_keys` array of their
UCP profile. Platforms fetch the business profile at `/.well-known/ucp`;
businesses fetch the platform profile from the `UCP-Agent` header. The
same profile that provides capabilities also provides verification
keys — this is UCP's key resolution mechanism for
[RFC 9421](https://www.rfc-editor.org/rfc/rfc9421) HTTP Message
Signatures.

**Key Lookup:**

1. Obtain the signer's profile URL
2. Fetch profile (or serve from cache)
3. Extract `keyid` from `Signature-Input` and match to `kid` in
   `signing_keys[]`
4. Verify signature using the corresponding public key

For key format (JWK), supported algorithms, key rotation procedures, and
complete signing/verification mechanics, see
[Message Signatures](signatures.md).

### Profile Requirements

#### Hosting

Both profiles must be reliably hosted. An unreliable or misconfigured
profile endpoint may prevent the other party from processing requests.

1. Profiles **MUST** be served over HTTPS.
2. Profile endpoints **MUST NOT** use redirects (3xx).
3. Profile responses **MUST** include a `Cache-Control` header with
   `public` and `max-age` of at least 60 seconds. Profiles **MUST NOT**
   be served with `private`, `no-store`, or `no-cache` directives.

Profiles represent a party's stable identity and capabilities. Profile
URLs are expected to remain consistent across requests and not contain
per-transaction or per-session configuration — the caching policy above
enforces this by requiring shared cache support with a minimum TTL.

#### Fetching

Businesses fetch platform profiles to perform capability negotiation and
verify identity. UCP defines best practices that enable permissionless
onboarding, but businesses retain full control over their access policies
and **MAY** enforce additional rules based on established trust, observed
behavior, or operational requirements.

Businesses **SHOULD** maintain a registry of pre-approved platforms —
platforms whose profiles have been validated and whose trust is
established through out-of-band mechanisms (API key, OAuth credential,
mTLS certificate, or prior vetting). Known platforms can be served
efficiently based on cached identity and capabilities, and are not
subject to discovery budget constraints.

When a platform is *not recognized*, it triggers dynamic profile
discovery. Businesses **SHOULD** establish a fixed
discovery footprint so that resource consumption for resolving
unrecognized platforms remains constant regardless of how many platforms
request access. Strategies include:

- **Fixed-size profile cache** (e.g., LRU) — bounds memory regardless of
  the number of unique profile URLs encountered
- **Global rate limit** on discovery fetches — bounds outbound network
  without requiring per-origin state tracking
- **Backoff on repeated failures** — reduces retries to persistently
  unavailable or malicious profile endpoints
- **Asynchronous discovery** — defer profile resolution by responding
  with a `503` status code and `Retry-After` header, and resolve the
  profile in the background; when the platform retries, the validated
  profile is cached and capability negotiation proceeds synchronously

When fetching profiles, the following apply:

1. Implementations **MUST** reject profile URLs not served over HTTPS.
2. Implementations **MUST NOT** follow redirects (3xx) on profile fetches.
3. Implementations **SHOULD** enforce connect and response timeouts on
   profile fetches.
4. Implementations **SHOULD** cache profiles with a minimum TTL floor
   of 60 seconds, regardless of the origin's `Cache-Control` headers.
5. Implementations **MAY** refresh profiles asynchronously using
   stale-while-revalidate semantics.
6. On signature verification failure with an unknown `kid`,
   implementations **MAY** force-refresh the cached profile — but
   **MUST NOT** do so more than once per TTL floor per origin.

If a profile cannot be fetched (timeout, DNS failure, 5xx) or fails
validation (invalid schema, signing keys, signature mismatch),
businesses **MUST** reject the request with an appropriate error and
status code (see [Error Handling](#error-handling)).

## Payment Architecture

UCP adopts a decoupled architecture for payments to solve the "N-to-N"
complexity problem between **platforms**, **businesses**, and **payment
credential providers**. This design separates **Payment
Instruments** (what is accepted) from **Payment Handlers** (the specifications
for how instruments are processed), ensuring security and scalability.

### Security and Trust Model

The payment architecture is built on a "Trust-by-Design" philosophy. It assumes
that while the business and payment credential provider have a trusted legal
relationship, the platform (Client) acts as an intermediary that **SHOULD NOT**
touch raw financial credentials.

#### The Trust Triangle

1. **Business ↔ Payment Credential Provider:** A pre-existing legal and technical relationship. The business holds API keys and a contract with the payment credential provider.
2. **Platform ↔ Payment Credential Provider:** The platform interacts with the payment credential provider's interface (e.g., an iframe or API) to tokenize data but is not the "owner" of the funds.
3. **Platform ↔ Business:** The platform passes the result (a token or mandate) to the business to finalize the order.

#### Enhanced Security for Autonomous Commerce

For scenarios requiring cryptographic proof of user authorization (e.g.,
autonomous AI agents), UCP supports the **AP2 Mandates Extension**
(`dev.ucp.shopping.ap2_mandate`). This optional extension provides
non-repudiable authorization through verifiable digital credentials.

See [Transaction Integrity](#transaction-integrity-and-non-repudiation)
and [AP2 Mandates Extension](ap2-mandates.md) for details on when and how to
use this extension.

#### Credential Flow & PCI Scope

To minimize compliance overhead (PCI-DSS):

1. **Unidirectional Flow:** Credentials flow **Platform → Business** only. Businesses **MUST NOT** echo credentials back in responses.
2. **Opaque Credentials:** Platforms handle tokens (such as network tokens), encrypted payloads, or mandates, not raw PANs.
3. **Handler ID Routing:** The `handler_id` in the payload ensures the business knows exactly which payment credential provider key to use for decryption/charging, preventing key confusion attacks.

### Roles & Responsibilities: Who Implements What?

A common source of confusion is the division of labor. The UCP payment model
splits responsibilities as follows:

| Role                            | Responsibility             | Action                                                                                                                                                                                                                                                              |
| :------------------------------ | :------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Payment Credential Provider** | **Defines the Spec**       | Creates the **Handler Definition**. They publish the "Blueprint" (JSON Schemas) that dictates how to tokenize a card and what config inputs are needed.<br>*Example: "Here is the schema for the 'com.psp-x.tokenization' handler."*                                |
| **Business**                    | **Configures the Handler** | Selects the Handler they want to use and provides their specific **Configuration** (Public Keys, Merchant IDs) in the UCP Checkout Response. *Example: "I accept Visa using 'com.psp-x.tokenization' with this Publishable Key."*                                   |
| **Platform**                    | **Executes the Protocol**  | Reads the business's config and executes the logic defined by the payment credential provider's Spec to acquire a token. *Example: "I see the Business uses a payment credential provider. I will call the provider's SDK with the Business's Key to get a token."* |

### Payment in the Checkout Lifecycle

When payment is required, the payment process follows a standard 3-step lifecycle
within UCP: **Negotiation**, **Acquisition**, and **Completion**.

![High-level payment flow sequence diagram](site:specification/images/ucp-payment-flow.png)

1. **Negotiation (Business → Platform):** The business advertises available payment handlers in their UCP profile. This tells the platform *how* to pay (e.g., "Use this specific payment credential provider endpoint with this public key").
2. **Acquisition (Platform ↔ Payment Credential Provider):** The platform executes the handler's logic. This happens client-side or agent-side, directly with the payment credential provider (e.g., exchanging credentials for a network token). The business is not involved, ensuring raw data never touches the business's frontend API.
3. **Completion (Platform → Business):** The platform submits the opaque credential (token) to the business. The business uses it to capture funds via their backend integration with the payment credential provider.

### Payment Handlers

Payment Handlers are **specifications** (not entities) that define how payment
instruments are processed. They are the contract that binds the three
participants together.

**Important distinction:**

- **Payment Credential Provider** = The participant (entity like Google Pay, Shop Pay)
- **Payment Handler** = The specification the provider authors (e.g., `com.google.pay`, `dev.shopify.shop_pay`)

Payment handlers allow for a variety of different payment instruments and
token-types to be supported, including network tokens. They are standardized
definitions typically authored by payment credential providers or the UCP
governing body.

**Dynamic Filtering:** Businesses **MUST** filter the `handlers` list based on
the context of the cart (e.g., removing "Buy Now Pay Later" for subscription
items, or filtering regional methods based on shipping address).

### Risk Signals

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

### Implementation Scenarios

The following scenarios illustrate how different payment handlers and
instruments are negotiated and executed using concrete data examples.

#### Scenario A: Digital Wallet

In this scenario, the platform identifies a payment credential provider (e.g.,
`com.google.pay`, `dev.shopify.shop_pay`) and uses their API to acquire
an encrypted payment token.

##### 1. Business Advertisement (Response from Create Checkout)

```json
{
  "ucp": {
    "version": "2026-01-11",
    "payment_handlers": {
      "com.google.pay": [
        {
          "id": "8c9202bd-63cc-4241-8d24-d57ce69ea31c",
          "version": "2026-01-11",
          "config": {
            "api_version": 2,
            "api_version_minor": 0,
            "environment": "TEST",
            "merchant_info": {
              "merchant_name": "Example Merchant",
              "merchant_id": "01234567890123456789",
              "merchant_origin": "checkout.merchant.com"
            },
            "allowed_payment_methods": [
              {
                "type": "CARD",
                "parameters": {
                  "allowed_auth_methods": ["PAN_ONLY"],
                  "allowed_card_networks": ["VISA", "MASTERCARD"]
                },
                "tokenization_specification": {
                  "type": "PAYMENT_GATEWAY",
                  "parameters": {
                    "gateway": "example",
                    "gatewayMerchantId": "exampleGatewayMerchantId"
                  }
                }
              }
            ]
          }
        }
      ],
      "dev.shopify.shop_pay": [
        {
          "id": "shop_pay_1234",
          "version": "2026-01-11",
          "config": {
            "shop_id": "shopify-559128571",
            "environment": "production"
          }
        }
      ]
    }
  }
}
```

##### 2. Token Execution (Platform Side)

The platform recognizes `com.google.pay` or `dev.shopify.shop_pay`. It passes the `config` into the
respective handler API. The handler returns the encrypted token data.

##### 3. Complete Checkout (Request to Business)

The Platform wraps the payment handler response into a payment instrument.

```json
POST /checkout-sessions/{id}/complete

{
  "payment": {
    "instruments": [
      {
        "id": "pm_1234567890abc",
        "handler_id": "8c9202bd-63cc-4241-8d24-d57ce69ea31c",
        "type": "card",
        "selected": true,
        "display": {
          "brand": "visa",
          "last_digits": "4242"
        },
        "billing_address": {
          "street_address": "123 Main Street",
          "extended_address": "Suite 400",
          "address_locality": "Charleston",
          "address_region": "SC",
          "postal_code": "29401",
          "address_country": "US",
          "first_name": "Jane",
          "last_name": "Smith"
        },
        "credential": {
          "type": "PAYMENT_GATEWAY",
          "token": "{\"signature\":\"...\",\"protocolVersion\":\"ECv2\"...}"
        }
      }
    ]
  },
  "risk_signals": {
      // ...
  }
}
```

#### Scenario B: Direct Tokenization with Challenge (SCA)

In this scenario, the platform uses a generic tokenizer to request a session
token or network tokens. The bank requires Strong Customer
Authentication (SCA/3DS), forcing the business to pause completion and
request a challenge.

##### 1. Business Advertisement

```json
{
  "ucp": {
    "payment_handlers": {
      "com.example.tokenizer": [
        {
          "id": "merchant_tokenizer",
          "version": "2026-01-11",
          "spec": "https://example.com/specs/tokenizer",
          "schema": "https://example.com/schemas/tokenizer.json",
          "config": {
            "token_url": "https://api.psp.com/tokens",
            "public_key": "pk_123"
          }
        }
      ]
    }
  }
}
```

##### 2. Token Execution (Platform Side)

The platform calls `https://api.psp.com/tokens` which identity **SHOULD** have
previous legal binding connection with them and receives `tok_visa_123`
(which could represent a vaulted card or network token).

##### 3. Complete Checkout (Request to Business)

```json
POST /checkout-sessions/{id}/complete

{
  "payment": {
    "instruments": [
      {
        "handler_id": "merchant_tokenizer",
        // ... more instrument required field
        "credential": { "token": "tok_visa_123" }
      }
    ]
  },
  "risk_signals": {
    // ... host could send risk_signals here
  }
}
```

##### 4. Challenge Required (Response from Business)

The business attempts the charge, but the PSP returns a "Soft Decline"
requiring 3DS.

```json
HTTP/1.1 200 OK
{
  "status": "requires_escalation",
  "messages": [{
    "type": "error",
    "code": "requires_3ds",
    "content": "bank requires verification.",
    "severity": "requires_buyer_input"
  }],
  "continue_url": "https://psp.com/challenge/123"
}
```

*The platform **MUST** now open `continue_url` in a WebView/Window for the user
to complete the bank check, then retry the completion.*

#### Scenario C: Autonomous Agent (AP2)

This scenario demonstrates the **Recommended Flow for Agents**. Instead of a
session token, the agent generates cryptographic mandates.

##### 1. Business Advertisement

```json
{
  "ucp": {
    "payment_handlers": {
      "dev.ucp.ap2_mandate_compatible_handlers": [
        {
          "id": "ap2_234352",
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specs/ap2-handler",
          "schema": "https://ucp.dev/schemas/ap2-handler.json"
        }
      ]
    }
  }
}
```

##### 2. Agent Execution

The agent cryptographically signs objects using the user's private key on a
non-agentic surface.

##### 3. Complete Checkout

```json
POST /checkout-sessions/{id}/complete

{
  "payment": {
    "instruments": [
      {
        "handler_id": "ap2_234352",
        // other required instruments fields
        "credential": {
          "type": "card",
          "token": "eyJhbGciOiJ...", // Token would contain payment_mandate, the signed proof of funds auth
        }
      }
    ]
  },
  "risk_signals": {
    "session_id": "abc_123_xyz",
    "score": 0.95
  },
  "ap2": {
    "checkout_mandate": "eyJhbGciOiJ...", // Signed proof of checkout terms
  }
}
```

*This provides the business with non-repudiable proof that the user authorized
this specific transaction, enabling safe autonomous processing.*

### PCI-DSS Scope Management

#### Platform Scope

Most platform implementations can **avoid PCI-DSS scope** by:

- Using handlers that provide opaque credentials (encrypted data, token
    references, etc.)
- Never accessing or storing raw payment data (card numbers, CVV, etc.)
- Forwarding credentials without the ability to use them directly
- Using PSP tokenization payment handlers where raw credentials never pass
    through the platform

#### Business Scope

Businesses can minimize PCI scope by:

- Using payment credential provider-hosted tokenization (provider stores
    credentials, business receives token reference)
- Using wallet providers that provide encrypted credentials (Google Pay, Shop
    Pay)
- Never logging raw credentials
- Delegating credential processing to PCI-certified payment credential providers

#### Payment Credential Provider Scope

Payment credential providers (PSPs, wallets) are typically PCI-DSS Level 1
certified and handle:

- Raw credential collection
- Credential protection (tokenization, encryption, secure storage)
- Credential validation and processing
- PCI-compliant infrastructure

### Security Best Practices

**For Businesses:**

1. Validate handler_id before processing (ensure handler is in advertised set)
2. Use separate PSP credentials for TEST vs PRODUCTION environments
3. Implement idempotency for payment processing (prevent double-charges)
4. Log payment events without logging credentials
5. Set appropriate credential timeouts
6. For autonomous commerce scenarios requiring cryptographic proof, consider
    supporting the `dev.ucp.shopping.ap2_mandate` extension (see
    [AP2 Mandates Extension](ap2-mandates.md))

**For Platforms:**

1. Always use HTTPS for checkout API calls
2. Validate handler configurations before executing protocols
3. Implement timeout handling for credential acquisition
4. Clear credentials from memory after submission
5. Handle credential expiration gracefully (re-acquire if needed)
6. For autonomous agents, consider using the `dev.ucp.shopping.ap2_mandate`
    extension for cryptographic proof of authorization (see
    [AP2 Mandates Extension](ap2-mandates.md))

**For Payment Credential Providers:**

1. Secure credentials for the specific business (encryption, tokenization, or
    other handler-specific methods)
2. Implement rate limiting on credential acquisition
3. Validate platform authorization before providing credentials
4. Set reasonable credential expiration (e.g., 15 minutes for tokens, time-
    limited encrypted payloads)
5. Ensure credentials cannot be used by platforms directly (only by the
    intended business)

### Fraud Prevention Integration

While UCP does not define fraud prevention APIs, the payment architecture
supports fraud signal integration:

- Businesses can require additional fields in handler configurations (e.g.,
    3DS requirements)
- Platforms can submit device fingerprints and session data alongside credentials
- Payment credential providers can perform risk assessment during credential
    acquisition
- Businesses can reject high-risk transactions and request additional
    verification

Future extensions **MAY** standardize fraud signal schemas, but the current
architecture allows flexible integration with existing fraud prevention systems.

### Payment Architecture Extensions

The core payment architecture described above can be extended for specialized
use cases:

- **AP2 Mandates Extension** (`dev.ucp.shopping.ap2_mandate`): Adds
    cryptographic proof of user authorization for autonomous commerce scenarios
    where non-repudiable evidence is required. See
    [AP2 Mandates Extension](ap2-mandates.md).

- **Custom Handler Types**: Payment credential providers can define custom
    handlers to support new payment instruments. See
    [Payment Handler Guide](payment-handler-guide.md) for details.

The extension model ensures the core architecture remains simple while
supporting advanced security and compliance requirements when needed.

## Transport Layer

UCP supports multiple transport protocols. Platforms and businesses effectively
negotiate the transport via `services` on their profiles.

### REST Transport (Core)

UCP supports **HTTP/1.1** (or higher) using RESTful patterns.

- **Content-Type:** Requests and responses **MUST** use `application/json`.
- **Methods:** Implementations **MUST** use standard HTTP verbs (e.g., `POST`
    for creation, `GET` for retrieval).
- **Status Codes:** Implementations **MUST** use standard HTTP status codes
    (e.g., 200, 201, 400, 401, 500).

### Model Context Protocol (MCP)

UCP supports **[MCP protocol](https://modelcontextprotocol.io/specification/)**,
which operates over JSON-RPC.

#### Request Format

MCP requests use the `tools/call` method with the operation name in
`params.name` and UCP payload in `params.arguments`:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "create_checkout",
    "arguments": {
      "meta": {"ucp-agent": {"profile": "https://..."}},
      "checkout": {"line_items": [...]}
    }
  },
  "id": 1
}
```

#### Response Format

MCP tool responses use a dual-output pattern for backward compatibility. UCP
MCP servers:

- **MUST** return the UCP response payload in `structuredContent`
- **SHOULD** declare `outputSchema` in tool definitions, referencing the
    appropriate UCP JSON Schema for the capability
- **SHOULD** also return serialized JSON in `content[]` for backward
    compatibility with clients not supporting `structuredContent`

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "checkout": {
        "ucp": {"version": "2026-01-11", "capabilities": {...}},
        "id": "checkout_abc123",
        "status": "incomplete",
        ...
      }
    },
    "content": [
      {"type": "text", "text": "{\"checkout\":{\"ucp\":{...},\"id\":\"checkout_abc123\",...}}"}
    ]
  }
}
```

### Agent-to-Agent Protocol (A2A)

A business **MAY** expose an A2A agent that supports UCP as an A2A Extension,
allowing integration with platforms over structured UCP data types.

### Embedded Protocol (EP)

A business **MAY** embed an interface onto an eligible host that would
receive events as the user interacts with the interface and delegate key user
actions.

Initiation comes through a `continue_url` that is returned by the business.

## Standard Capabilities

UCP defines a set of standard capabilities:

| Capability Name      | ID (URI)                                       | Description                                                                                                  |
| :------------------- | :--------------------------------------------- | :----------------------------------------------------------------------------------------------------------- |
| **Checkout**         | `{{ ucp_url }}/schemas/shopping/checkout.json` | Facilitates the creation and management of checkout sessions, including cart management and tax calculation. |
| **Identity Linking** | -                                              | Enables platforms to obtain authorization via OAuth 2.0 to perform actions on a user's behalf.               |
| **Order**            | `{{ ucp_url }}/schemas/shopping/order.json`    | Allows businesses to push asynchronous updates about an order's lifecycle (shipping, delivery, returns).     |

### Definition & Extensions

Detailed definitions for endpoints, schemas, and valid extensions for each
capability are provided in their respective specification files. Extensions are
typically versioned and defined alongside their parent capability.

## Security

### Transport Security

All UCP communication **MUST** occur over **HTTPS**.

### Data Privacy

Sensitive data (such as Payment Credentials or PII) **MUST** be handled
according to PCI-DSS and GDPR guidelines. UCP encourages the use of tokenized
payment data to minimize business and platform liability.

### Transaction Integrity and Non-Repudiation

For scenarios requiring cryptographic proof of authorization (e.g., autonomous
agents, high-value transactions), UCP supports the **AP2 Mandates Extension**
(`dev.ucp.shopping.ap2_mandate`). When this optional extension is negotiated:

- Businesses provide a cryptographic signature on checkout terms
- Platforms provide cryptographic mandates proving user authorization

This mechanism provides strong, end-to-end cryptographic assurances about
transaction details and participant consent, significantly reducing risks of
tampering and disputes.

See [AP2 Mandates Extension](ap2-mandates.md) for complete specification,
implementation guide, and examples.

## Versioning

### Version Format

UCP uses date-based versioning in the format `YYYY-MM-DD`. This provides
clear chronological ordering and unambiguous version comparison.

### Version Discovery and Negotiation

UCP prioritizes strong backwards compatibility. Businesses implementing a
version **SHOULD** handle requests from platforms using that version or older.

Both businesses and platforms declare a single version in their profiles:

#### Example

=== "Business Profile"

    ```json
    {
      "ucp": {
        "version": "2026-01-11",
        "services": { ... },
        "capabilities": { ... },
        "payment_handlers": { ... }
      }
    }
    ```

=== "Platform Profile"

    ```json
    {
      "ucp": {
        "version": "2026-01-11",
        "services": { ... },
        "capabilities": { ... },
        "payment_handlers": { ... }
      }
    }
    ```

### Version Negotiation

![High-level resolution flow sequence diagram](site:specification/images/ucp-discovery-negotiation.png)

Businesses **MUST** validate the platform's version and determine compatibility:

1. Platform declares version via profile referenced in request
2. Business validates:
    - If platform version ≤ business version: Business **MUST**
        process the request
    - If platform version > business version: Business **MUST** return
        `version_unsupported` error
3. Businesses **MUST** include the version used for processing in every
    response.

Response with version confirmation:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": { ... },
    "payment_handlers": { ... }
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
    "content": "Version 2026-01-12 is not supported. This business implements version 2026-01-11.",
    "severity": "requires_buyer_input"
  }]
}
```

### Backwards Compatibility

#### Backwards-Compatible Changes

The following changes **MAY** be introduced without a new version:

- Adding new non-required fields to responses
- Adding new non-required parameters to requests
- Adding new endpoints, methods, or operations to a transport
- Adding new error codes with existing error structures
- Adding new values to enums (unless explicitly documented as exhaustive)
- Changing the order of fields in responses
- Changing the length or format of opaque strings (IDs, tokens)

#### Breaking Changes

The following changes **MUST NOT** be introduced without a new version:

- Removing or renaming existing fields
- Changing field types or semantics
- Making non-required fields required
- Removing operations, methods, or endpoints
- Changing authentication or authorization requirements
- Modifying existing protocol flow or state machine
- Changing the meaning of existing error codes

### Independent Component Versioning

- UCP protocol versions independently from capabilities.
- Each capability versions independently from other capabilities.
- Capabilities **MUST** follow the same backwards compatibility rules as the
    protocol.
- Businesses **MUST** validate capability version compatibility using the same
    logic as what's described above.
- Transports **MAY** define their own version handling mechanisms.

#### UCP Capabilities (`dev.ucp.*`)

UCP-authored capabilities version with protocol releases by default. Individual
capabilities **MAY** version independently when breaking changes are required
outside the protocol release cycle.

#### Vendor Capabilities (`com.{vendor}.*`)

Capabilities outside the `dev.ucp.*` namespace version fully independently.
Vendors control their own release schedules and versioning strategy.

## Glossary

| Term                              | Acronym | Definition                                                                                                                                                |
| :-------------------------------- | :------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agent Payments Protocol**       | AP2     | An open protocol designed to enable AI agents to securely interoperate and complete payments autonomously. UCP leverages AP2 for secure payment mandates. |
| **Agent2Agent Protocol**          | A2A     | An open standard for secure, collaborative communication between diverse AI agents. UCP can use A2A as a transport layer.                                 |
| **Capability**                    | -       | A standalone core feature that a business supports (e.g., Checkout, Identity Linking). Capabilities are the fundamental "verbs" of UCP.                   |
| **Credential Provider**           | CP      | A trusted entity (like a digital wallet) responsible for securely managing and executing the user's payment and identity credentials.                     |
| **Extension**                     | -       | An optional capability that augments another capability via the `extends` field. Extensions appear in `ucp.capabilities[]` alongside core capabilities.   |
| **Profile**                       | -       | A JSON document hosted by businesses and platforms at a well-known URI, declaring their identity, supported capabilities, and endpoints.                  |
| **Business**                      | -       | The entity selling goods or services. In UCP, they act as the **Merchant of Record (MoR)**, retaining financial liability and ownership of the order.     |
| **Model Context Protocol**        | MCP     | A protocol standardizing how AI models connect to external data and tools. UCP capabilities map 1:1 to MCP tools.                                         |
| **Universal Commerce Protocol**   | UCP     | The standard defined in this document, enabling interoperability between commerce entities via standardized capabilities and discovery.                   |
| **Payment Service Provider**      | PSP     | The financial infrastructure provider that processes payments, authorizations, and settlements on behalf of the business.                                 |
| **Platform**                      | -       | The consumer-facing surface (AI agent, app, website) acting on behalf of the user to discover businesses and facilitate commerce.                         |
| **Verifiable Digital Credential** | VDC     | An Issuer-signed credential (set of claims) whose authenticity can be verified cryptographically. Used in UCP for secure payment authorizations.          |
