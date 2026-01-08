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

# Universal Commerce Protocol (UCP)

## Overview

**An open standard enabling interoperability between various commerce entities
to facilitate seamless commerce integrations.**

The Universal Commerce Protocol (UCP) addresses a fragmented commerce landscape
by providing a standardized common language and functional primitives. It
enables consumer surfaces (like AI agents and apps), merchants, Payment Service
Providers (PSPs), and Credential Providers (CPs) to communicate effectively,
ensuring secure and consistent commerce experiences across the web.

With UCP, merchants can:

*   **Declare** supported capabilities to enable autonomous discovery by
    consumer surfaces.
*   **Facilitate** secure checkout sessions, with or without human intervention.
*   **Offer** personalized shopping experiences through standardized data
    exchange.

## Why UCP?

As commerce becomes increasingly agentic and distributed, the ability for
different systems to interoperate without custom, one-off integrations is vital.
UCP aims to:

*   **Standardize Interaction:** Provide a uniform way for agents and platforms
    to interact with merchants, regardless of the underlying backend.
*   **Modularize Commerce:** Break down commerce into distinct **Capabilities**
    (e.g., Checkout, Order Status) and **Extensions** (e.g., Discounts,
    Loyalty), allowing for flexible implementation.
*   **Enable Agentic Commerce:** Designed from the ground up to support AI
    agents acting on behalf of users to discover products, fill carts, and
    complete purchases securely.
*   **Enhance Security:** Support for advanced security patterns like AP2
    mandates and verifiable credentials.

### Key Features

*   **Composable Architecture:** UCP defines core **Capabilities** (such as
    "Checkout" or "Identity Linking") that merchants implement to enable easy
    integration. On top of that, specific **Extensions** can be added to enhance
    the consumer experience without bloating the core protocol.
*   **Dynamic Discovery:** Merchants declare their supported Capabilities in a
    standardized profile, allowing applications and agents to autonomously
    discover and configure themselves.
*   **Transport Agnostic:** The protocol is designed to work across various
    transports. Merchants can offer Capabilities via REST APIs, MCP (Model
    Context Protocol), or A2A, depending on their infrastructure.
*   **Built on Standards:** UCP leverages existing open standards for payments,
    identity, and security wherever applicable, rather than reinventing the
    wheel.
*   **Developer Friendly:** A comprehensive set of SDKs and libraries
    facilitates rapid development and integration.

## Key Capabilities

The initial release focuses on the essential primitives for transacting:

*   **Checkout:** Facilitates checkout sessions including cart management and
    tax calculation, supporting flows with or without human intervention.
*   **Identity Linking:** Enables platforms to obtain authorization to perform
    actions on a user's behalf via OAuth 2.0.
*   **Order Status:** Webhook-based updates for order lifecycle events (shipped,
    delivered, returned).
*   **Payment Token Exchange:** Protocols for PSPs and Credential Providers to
    securely exchange payment tokens and credentials.

## Getting Started

📚 **Explore the Documentation:** Visit ucp.dev for a complete overview, the
full protocol specification, tutorials, and guides.

## Contributing

We welcome community contributions to enhance and evolve UCP\.

*   **Questions & Discussions:** Join our GitHub Discussions.
*   **Issues & Feedback:** Report issues or suggest improvements via
    GitHub Issues.
*   **Contribution Guide:** See our [CONTRIBUTING.md](CONTRIBUTING.md) for
    details on how to contribute.

## What's Next

Future enhancements include:

*   **New Verticals:** Applications beyond Shopping (e.g., Travel, Services).
*   **Loyalty:** Standardized management of loyalty programs and rewards.
*   **Personalization:** Enhanced signals for personalized product discovery.

## About

UCP is an open-source project under the [Apache License 2.0](LICENSE) and is
open to contributions from the community.
