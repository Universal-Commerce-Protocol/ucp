# Core Concepts

The Universal Commerce Protocol (UCP) is an open standard designed to facilitate communication and interoperability between diverse commerce entities. In a fragmented landscape where consumer surfaces/platforms, businesses, payment providers, and identity providers operate on different systems, UCP provides a standardized common language and functional primitives.

This document provides the detailed technical specification for UCP. For a complete definition of all data models and schemas, see the [Schema Reference](https://ucp.dev/draft/specification/reference/index.md).

Its primary goal is to enable:

- **Consumer Surfaces/Platforms:** To discover business capabilities and facilitate purchases.
- **Businesses:** To expose their inventory and retail logic in a standard way without building custom integrations for every platform.
- **Payment & Credential Providers:** To securely exchange tokens and credentials to facilitate transactions.

## High level architecture

## Key Goals of UCP

- **Interoperability:** Bridge the gap between consumer surfaces, businesses, and payment ecosystems.
- **Discovery:** Allow consumer surfaces to dynamically discover what businesses support (e.g., "Do they support guest checkout?", "Do they have loyalty programs?").
- **Security:** Facilitate secure, standards-based (OAuth 2.0, PCI-DSS compliant patterns) exchanges of sensitive user and payment data.
- **Agentic Commerce:** Enable AI agents to act on behalf of users to complete complex tasks like "Find a headset under $100 and buy it."

## Roles & Participants

UCP defines the interactions between four primary distinct actors, each playing a specific role in the commerce lifecycle.

### Platform (Application/Agent)

The platform is the consumer-facing surface (such as an AI agent, mobile app, or social media site) acting on behalf of the User. It orchestrates the commerce journey by discovering businesses and facilitating user intent.

- **Responsibilities:** Discovering businesses capabilities via profiles, initiating checkout sessions, and presenting the UI or conversational interface to the user.
- **Examples:** AI Shopping Assistants, Super Apps, Search Engines.

### Business

The entity selling goods or services. In the UCP model, businesses act as the **Merchant of Record (MoR)**, retaining financial liability and ownership of the order.

- **Responsibilities:** Exposing commerce capabilities (inventory, pricing, tax calculation), fulfilling orders, and processing payments via their chosen PSP.
- **Examples:** Retailers, Airlines, Hotel Chains, Service Providers.

### Credential Provider (CP)

A trusted entity responsible for securely managing and sharing sensitive user data, particularly payment instruments and shipping addresses.

- **Responsibilities:** Authenticating the user, issuing payment tokens (to keep raw card data off the platform), and holding PII securely to minimize compliance scope for other parties.
- **Examples:** Digital Wallets (e.g., Google Wallet, Apple Pay), Identity Providers.

### Payment Service Provider (PSP)

The financial infrastructure provider that processes payments on behalf of businesses.

- **Responsibilities:** Authorizing and capturing transactions, handling settlements, and communicating with card networks. The PSP often interacts directly with tokens provided by the Credential Provider.
- **Examples:** Stripe, Adyen, PayPal, Braintree, Chase Paymentech.

## Core Concepts Summary

UCP revolves around three fundamental constructs that define how entities interact.

- **Capabilities:** Standalone core features that a business supports. These are the "verbs" of the protocol.
  - *Examples:* Checkout, Identity Linking, Order.
- **Extensions:** Optional capabilities that augment another capability via the `extends` field. Extensions appear in `ucp.capabilities[]` alongside core capabilities.
  - *Examples:* Discounts (extends Checkout), AP2 Mandates (extends Checkout).
- **Services:** The lower-level communication layers used to exchange data. UCP is transport-agnostic but defines specific bindings for interoperability.
  - *Examples:* REST API (primary), MCP (Model Context Protocol), A2A (Agent2Agent).
