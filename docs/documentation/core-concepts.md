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

# Core Concepts

The Universal Commerce Protocol (UCP) is an open standard for interoperability
between commerce entities. It defines a common language and functional
primitives so that platforms and businesses can interoperate securely and
reliably across commercial verticals.

This document provides the detailed technical specification for UCP.
For a complete definition of all data models and schemas, see the
[Schema Reference](../specification/reference.md).

!!! note "Terminology"
    Throughout this documentation, **Platform** refers to any entity that
    *consumes* capabilities — an app, an AI agent, a procurement system, or
    another business. **Business** refers to any entity that *exposes*
    capabilities — a retailer, a supplier, a service provider, or any other
    participant offering commerce functionality. These roles are defined by
    direction of capability flow, not by industry vertical, making UCP equally
    applicable to B2C, B2B, and agent-to-agent commerce.

Its primary goal is to enable:

* **Platforms:** To dynamically discover and consume the capabilities a
    business exposes.
* **Businesses:** To declare what they offer and how they operate — once —
    and have any compatible platform discover and use it without bespoke
    integrations.
* **Payment & Credential Providers:** To expose their services —
    tokenization, vaulting, credential issuance — once, and power secure
    commerce for users across any compatible platform and business.

## High level architecture

<!-- Responsive image: shows ucp-diagram-mobile.jpg on small screens (<=600px)
     and ucp-diagram.jpg on larger screens. -->
<picture>
  <source media="(max-width: 600px)" srcset="../assets/ucp-diagram-mobile.jpg">
  <img alt="UCP Diagram" src="../assets/ucp-diagram.jpg">
</picture>

## Key Goals of UCP

* **Interoperability:** Bridge the gap between platforms, businesses,
    and payment ecosystems.
* **Discovery:** Allow platforms to dynamically discover what
    capabilities a business supports (e.g., "Do they support checkout?",
    "Do they support fulfillment options or identity linking?").
* **Security:** Facilitate secure, standards-based (OAuth 2.0, PCI-DSS
    compliant patterns) exchanges of sensitive user and payment data.
* **Agentic Commerce:** Enable AI agents to act on behalf of varied principals
    (an individual, organization, or another agent) and support different
    modalities (human-in-the-loop, fully autonomous).

## Roles & Participants

UCP defines the interactions between four distinct actors, each playing
a specific role in the interaction lifecycle.

### Platform (Application/Agent)

The platform is any entity that consumes capabilities exposed by a business —
an AI agent, a mobile app, a procurement system, or another business acting
as a capability consumer. It orchestrates the interaction by discovering what
the business supports and invoking the appropriate capabilities on behalf of
its principal (a user, an automated process, or another system).

* **Responsibilities:** Discovering business capabilities via profiles,
    initiating and managing capability sessions, and acting on behalf of its
    principal within the bounds of negotiated capabilities.
* **Examples:** AI Shopping Assistants, Super Apps, Search Engines,
    B2B Procurement Systems.

### Business

The entity exposing capabilities. In transactional contexts, the business
typically acts as the **Merchant of Record (MoR)**, retaining financial
liability and ownership of the transaction — though UCP's capability model
is not limited to transactional use cases.

* **Responsibilities:** Publishing a UCP profile, declaring supported
    services, capabilities and extensions, processing capability invocations
    which may be stateful or stateless.
* **Examples:** Retailers, Airlines, Hotel Chains, Service Providers,
    Suppliers, Distributors.

### Credential Provider (CP)

A trusted entity responsible for securely managing and sharing sensitive user
data, particularly payment instruments and shipping addresses.

* **Responsibilities:** Authenticating the user, issuing payment tokens (to
    keep raw card data off the platform), and holding PII securely to minimize
    compliance scope for other parties.
* **Examples:** Digital Wallets (e.g., Google Wallet, Apple Pay), Identity
    Providers.

### Payment Service Provider (PSP)

The financial infrastructure provider that processes payments on behalf of
businesses.

* **Responsibilities:** Authorizing and capturing transactions, handling
    settlements, and communicating with card networks. The PSP often interacts
    directly with tokens provided by the Credential Provider.
* **Examples:** Stripe, Adyen, PayPal, Braintree, Chase Paymentech.

## Core Concepts Summary

UCP revolves around three fundamental constructs that define how entities
interact.

### Capabilities

Capabilities are standalone, independently versioned features that
a business declares it supports. They are the "verbs" of the protocol —
discrete units of functionality that platforms can discover, negotiate, and
invoke.

Each capability is identified by a reverse-domain name (e.g.,
`dev.ucp.shopping.checkout`) and carries a date-based version. Capabilities
are declared in the business's UCP profile at `/.well-known/ucp` and
negotiated and confirmed in every response so that the platform always knows
the active feature set for a given interaction.

The following are examples of capabilities defined in UCP — see the
[Specification](../specification/overview.md) for the authoritative and
up-to-date list.

| Capability | Description |
| :--- | :--- |
| `dev.ucp.shopping.checkout` | Initiates and completes purchase sessions |
| `dev.ucp.shopping.cart` | Pre-checkout cart management |
| `dev.ucp.shopping.catalog.search` | Search across a business catalog |
| `dev.ucp.shopping.catalog.lookup` | Retrieve a specific product by ID |
| `dev.ucp.shopping.order` | Order lifecycle events |
| `dev.ucp.common.identity_linking` | OAuth-based account linking |

### Extensions

Extensions optionally augment a base capability. They use the
`extends` field to declare their parent(s) and compose onto the base schema
using JSON Schema `allOf`. Extensions appear in `ucp.capabilities[]` alongside
core capabilities.

```json
{
  "dev.ucp.shopping.fulfillment": [
    {
      "version": "2026-04-08",
      "extends": "dev.ucp.shopping.checkout",
      "spec": "https://ucp.dev/2026-04-08/specification/fulfillment",
      "schema": "https://ucp.dev/2026-04-08/schemas/shopping/fulfillment.json"
    }
  ]
}
```

An extension that declares `extends` without its parent in the negotiated
intersection is automatically pruned. This ensures extension coherence —
you never activate a discount extension without the checkout it extends.

The following are examples of extensions defined in UCP — see the
[Specification](../specification/overview.md) for the authoritative and
up-to-date list.

| Extension | Extends | Description |
| :--- | :--- | :--- |
| `dev.ucp.shopping.discount` | checkout, cart | Discount codes and promotions |
| `dev.ucp.shopping.fulfillment` | checkout | Shipping and delivery options |
| `dev.ucp.shopping.ap2_mandate` | checkout | Non-repudiable authorization for autonomous commerce |
| `dev.ucp.shopping.buyer_consent` | checkout | Explicit consent capture |

### Services

**Services** group the operations and events for a vertical under a
reverse-domain namespace (e.g., `dev.ucp.shopping`).
A service declares *what* functionality exists for that vertical; transport
bindings declare *how* it is accessed on the wire.

A single service can be accessed via multiple transport bindings:

| Transport | Format | Best For |
| :--- | :--- | :--- |
| **REST** | OpenAPI 3.1.0 | Standard server-to-server integrations |
| **MCP** | OpenRPC | AI agents via Model Context Protocol |
| **A2A** | Agent Card | Agent-to-Agent protocol integrations |
| **Embedded** | OpenRPC | Embedded integrations |

A business declares which transport bindings it supports within each service;
platforms pick whichever fits their context — an AI agent may prefer MCP, a
traditional web app may use REST.

Service namespaces are also UCP's extensibility mechanism for new
verticals — e.g., `dev.ucp.hotels` may be introduced in the future.
Businesses opt in by declaring which services they support.

## Discovery & Capability Negotiation

UCP uses a profile-based discovery model. Every business publishes a
machine-readable profile at `/.well-known/ucp` that declares which services,
capabilities, and payment handlers they support. Platforms advertise their
own profile URL on each request via the `UCP-Agent` header.

```text
POST /checkout-sessions HTTP/1.1
UCP-Agent: profile="https://agent.example/profiles/shopping-agent.json"
```

This design enables **permissionless onboarding** — any platform with a
discoverable profile can interact with any business without prior registration.
Businesses may additionally establish trust with known platforms through
out-of-band onboarding & verification mechanisms (API keys, OAuth
credentials, mTLS certificates).

### Capability Intersection

Capability negotiation follows a **server-selects** architecture. The business
determines the active capabilities by computing the intersection of its own
declared capabilities with those in the platform's profile:

1. **Intersect by name** — Only capabilities both parties declare are
   candidates.
2. **Select version** — For each matched capability, compute the set of
   versions present in both the business and platform arrays. Select the
   highest (latest date). If no mutual version exists, exclude the capability.
3. **Prune orphaned extensions** — Extensions are removed if **none** of their
   parent capabilities are in the intersection. Pruning repeats until stable
   (handles chains).

The result is a minimal, mutually compatible capability set. Businesses
include the active capabilities in every response so platforms always know
which features apply to a given interaction.

### Profile Structure

Both business and platform profiles share a common base structure — a `ucp`
object declaring protocol version, services, capabilities, and payment handlers,
alongside a `signing_keys` array of JWK public keys. The `ucp` object differs
between the two: the business profile uses a business-specific schema (hosted at
`/.well-known/ucp`), while the platform profile uses a platform-specific schema
(hosted at a URI the platform advertises per-request). This dual-purpose profile
— capabilities *and* keys in a single document — means discovery and
authentication are resolved together.

```json
{
  "ucp": {
    "version": "2026-04-08",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "2026-04-08",
          "spec": "https://ucp.dev/2026-04-08/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/2026-04-08/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp/v1"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.checkout": [{
        "version": "2026-04-08",
        "spec": "https://ucp.dev/2026-04-08/specification/checkout",
        "schema": "https://ucp.dev/2026-04-08/schemas/shopping/checkout.json"
      }],
      "dev.ucp.shopping.fulfillment": [{
        "version": "2026-04-08",
        "spec": "https://ucp.dev/2026-04-08/specification/fulfillment",
        "schema": "https://ucp.dev/2026-04-08/schemas/shopping/fulfillment.json",
        "extends": "dev.ucp.shopping.checkout"
      }]
    },
    "payment_handlers": {
      "com.example.processor_tokenizer": [{
        "id": "processor_tokenizer",
        "version": "2026-04-08",
        "spec": "https://example.com/specs/payments/processor_tokenizer",
        "schema": "https://example.com/specs/payments/merchant_tokenizer.json"
      }]
    }
  },
  "signing_keys": [{ "kid": "key_2026", "kty": "EC", "crv": "P-256", "alg": "ES256" }]
}
```

## Namespace Governance

UCP uses reverse-domain naming to embed governance authority directly into
capability and service identifiers. This eliminates the need for a central
registry — domain owners control their own namespace.

```text
{reverse-domain}.{service}.{capability}
```

| Name | Authority | Who governs |
| :--- | :--- | :--- |
| `dev.ucp.shopping.checkout` | ucp.dev | UCP governing body |
| `dev.shopify.catalog` | shopify.dev | Shopify |
| `com.example.payments.installments` | example.com | example.com |

The `spec` and `schema` URLs declared in a capability must originate from the
namespace authority domain. Platforms **MUST** validate this binding to prevent
spoofed capabilities.

The `dev.ucp.*` namespace is reserved exclusively for capabilities governed by
the UCP Tech Council. Any vendor can define and publish capabilities under their
own domain — `org.acme.*` — without UCP maintainer approval. Vendor
capabilities follow the same extension model, meaning they can extend UCP base
capabilities (e.g., `org.acme.loyalty` extending `dev.ucp.shopping.checkout`)
or define entirely new ones. Because negotiation is always opt-in, vendor
capabilities only activate when both parties declare them, keeping the protocol
decentralized by design.

## Payment Architecture

UCP decouples payment instrument acceptance from payment processing to solve
the N-to-N complexity problem between platforms, businesses, and payment
processors.

### The Trust Triangle

In this section, "Payment Credential Provider" refers to the CP and/or PSP
roles defined above; depending on the payment handler, they may be the same
entity or distinct.

The payment model is built on three bilateral trust relationships:

1. **Business ↔ Payment Credential Provider** — A pre-existing legal and
   technical relationship; the business holds API keys and a contract with
   the payment credential provider.
2. **Platform ↔ Payment Credential Provider** — The platform interacts with
   the payment credential provider's interface (e.g., an iframe or API) to
   tokenize data, but is not the "owner" of the funds.
3. **Platform ↔ Business** — The platform passes the result (a token or
   mandate) to the business to finalize the order.

Credentials flow **platform → business** only; businesses **MUST NOT** echo
credentials back in responses.

### Payment Handlers

Payment Handlers are **specifications**, not entities. They define how a
particular payment instrument is acquired and processed. The distinction:

* **Credential Provider (CP) / PSP** — The participant(s) that issue tokens
  and process payments. Depending on the handler, these may be the same
  entity or separate ones (e.g., Google Pay tokenizes; the business's PSP
  processes).
* **Payment Handler** — The specification that defines the protocol
  (e.g., `com.google.pay`, `dev.shopify.shop_pay`)

The 3-step payment lifecycle:

1. **Negotiation** — The business advertises available payment handlers in its
   profile and checkout response based on contents and negotiated
   properties of the checkout.
2. **Acquisition** — The platform executes the handler's logic to acquire a
   payment instrument (token or encrypted payload) directly from the CP.
3. **Completion** — The platform submits the instrument to the business, which
   charges funds via its PSP integration.

## Security & Authentication

### Identity & Key Discovery

UCP profiles serve a dual purpose: declaring capabilities **and** publishing
signing keys. Both parties resolve keys from the same profile document used for
capability negotiation, eliminating a separate key management step.

Key lookup:

1. Obtain the signer's profile URL (from `UCP-Agent` header or
   `/.well-known/ucp`).
2. Fetch and cache the profile.
3. Match the `keyid` from `Signature-Input` to a `kid` in `signing_keys[]`.
4. Verify the signature using the corresponding public key.

### Authentication Mechanisms

UCP supports multiple authentication models:

| Mechanism | Onboarding | Notes |
| :--- | :--- | :--- |
| **HTTP Message Signatures** ([RFC 9421](https://www.rfc-editor.org/rfc/rfc9421)) | Permissionless | Keys discovered from profile; no prior exchange needed |
| **OAuth 2.0** | Pre-established | Client credentials or authorization code |
| **API Keys** | Pre-established | Pre-shared secrets exchanged out-of-band |
| **mTLS** | Pre-established | Mutual TLS with client certificates |

HTTP Message Signatures are the only mechanism that enables permissionless
interaction — public keys are discovered from each party's profile, with no
prior credential exchange.

When a business emits updates via webhook, its identity is asserted the same
way: the request carries a `UCP-Agent` header pointing to the business's
profile, and the platform verifies the signature against the signing keys
published there.

### Identity Linking

The `dev.ucp.common.identity_linking` capability enables a platform to obtain
OAuth 2.0 authorization to act on behalf of a user at a business — unlocking
loyalty benefits, personalized offers, wishlists, and authenticated checkouts.
Businesses publish their OAuth 2.0 server metadata at
`/.well-known/oauth-authorization-server`.

## Versioning

UCP uses date-based version identifiers (`YYYY-MM-DD`). The version represents
the date of the last backwards-incompatible change.

* **Non-breaking additions** do not increment the date.
* **Breaking changes** require a `!` prefix in the PR title and a 2-week
  advance notice to the community before merging.
* Businesses that support older protocol versions **SHOULD** publish
  version-specific profiles and advertise them via the `supported_versions`
  field in their profile, enabling platforms to discover the exact capability
  set for each supported version.

Capability schemas carry their version inline, which enables independent
versioning — a discount extension can version on a different cadence than
the checkout capability it extends.

See [Versioning](../versioning.md) for the release branch process and the
full breaking-change procedure.
