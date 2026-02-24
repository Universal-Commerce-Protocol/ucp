# Universal Commerce Protocol

The common language for platforms, agents and businesses.

UCP defines building blocks for agentic commerce—from discovering and buying to post purchase experiences—allowing the ecosystem to interoperate through one standard, without custom builds.

### Learn

Protocol overview, core concepts, and design principles

[Read the docs](https://ucp.dev/latest/specification/overview/index.md)

### Implement

GitHub repo, technical spec, SDKs, and reference implementations

[View on GitHub](https://github.com/Universal-Commerce-Protocol/ucp)

## Co-developed and adopted by industry leaders

UCP was built by the industry, for the industry to solve for fragmented commerce journeys that lead to abandoned carts and frustrated shoppers, and enable agentic commerce.

Google

Shopify

Etsy

Wayfair

Target

Walmart

## Built for flexibility, security, and scale

Agentic commerce demands interoperability. UCP is built on industry standards — REST and JSON-RPC transports; [Agent Payments Protocol (AP2)](https://ap2-protocol.org/), [Agent2Agent (A2A)](https://a2a-protocol.org/latest/), and [Model Context Protocol (MCP)](https://modelcontextprotocol.io/docs/getting-started/intro) support built-in — so different systems can work together without custom integration.

### Scalable and universal

Surface-agnostic design that can scale to support any commerce entity (from small businesses to enterprise scale) and all modalities (chat, visual commerce, voice, etc).

### Businesses at the center

Built to facilitate commerce, ensuring retailers retain control of their business rules and remain the Merchant of Record with full ownership of the customer relationship.

### Open and extensible

Open and extensible by design, enabling development of community-driven capabilities and extensions across verticals.

### Secure and private

Built on proven security standards for account linking (OAuth 2.0) and secure payment (AP2) via payment mandates and verifiable credentials.

### Frictionless payments

Open wallet ecosystem with interoperability between providers to ensure buyers can pay with their preferred payment methods.

## See it in action

UCP is designed to facilitate the entire commerce lifecycle, from initial product discovery and search to final sale and post-purchase support. The protocol's initial launch focuses on three core capabilities: Checkout, Identity Linking, and Order Management.

Checkout Identity Linking Order

SEE IT IN ACTION

### Checkout

Support complex cart logic, dynamic pricing, tax calculations, and more across millions of businesses through unified checkout sessions.

[Learn more](https://ucp.dev/latest/specification/checkout-rest/index.md)

```json
{
  "ucp": { ... },
  "id": "chk_123456789",
  "status": "ready_for_complete",
  "currency": "USD",
  "buyer": {
    "email": "e.beckett@example.com",
    "first_name": "Elisa",
    "last_name": "Beckett"
  },
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "item_123",
        "title": "Monos Carry-On Pro suitcase",
        "price": 26550
      },
      "quantity": 1,
      ...
    }
  ],
  "totals": [ ... ],
  "links": [ ... ],
  "payment": { ... },
  "fulfillment": {
    "methods": [
      {
        "id": "method_1",
        "type": "shipping",
        "line_item_ids": ["li_1"],
        "selected_destination_id": "dest_1",
        "destinations": [
          {
            "id": "dest_1",
            "first_name": "Elisa",
            "last_name": "Beckett",
            "street_address": "1600 Amphitheatre Pkwy",
            "address_locality": "Mountain View",
            "address_region": "CA",
            "postal_code": "94043",
            "address_country": "US"
          }
        ],
        "groups": [
          {
            "id": "group_1",
            "line_item_ids": ["li_1"],
            "selected_option_id": "free-shipping",
            "options": [
              {
                "id": "free-shipping",
                "title": "Free Shipping",
                "totals": [ {"type": "total", "amount": 0} ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

SEE IT IN ACTION

### Identity Linking

OAuth 2.0 standard enables agents to maintain secure, authorized relationships without sharing credentials.

[Learn more](https://ucp.dev/latest/specification/identity-linking/index.md)

```json
Sample of /.well-known/oauth-authorization-server

{
  "issuer": "https://example.com",
  "authorization_endpoint": "https://example.com/oauth2/authorize",
  "token_endpoint": "https://example.com/oauth2/token",
  "revocation_endpoint": "https://example.com/oauth2/revoke",
  "scopes_supported": [
    "ucp:scopes:checkout_session",
  ],
  "response_types_supported": [
    "code"
  ],
  "grant_types_supported": [
    "authorization_code",
    "refresh_token"
  ],
  "token_endpoint_auth_methods_supported": [
    "client_secret_basic"
  ],
  "service_documentation": "https://example.com/docs/oauth2"
}
```

SEE IT IN ACTION

### Order

From purchase confirmation to delivery. Real-time webhooks power status updates, shipment tracking, and return processing across every channel.

[Learn more](https://ucp.dev/latest/specification/order/index.md)

```json
{
  "ucp": { ... },
  "id": "order_123456789",
  "checkout_id": "chk_123456789",
  "permalink_url": ...,
  "line_items": [ ... ],
  "fulfillment": {
    "expectations": [
      {
        "id": "exp_1",
        "line_items": [{ "id": "li_1", "quantity": 1 }],
        "method_type": "shipping",
        "destination": {
          "first_name": "Elisa",
          "last_name": "Beckett",
          "street_address": "1600 Amphitheatre Pkwy",
          "address_locality": "Mountain View",
          "address_region": "CA",
          "postal_code": "94043",
          "address_country": "US"
        },
        "description": "Arrives in 2-3 business days",
        "fulfillable_on": "now"
      }
      ...
    ],
    "events": [
      {
        "id": "evt_1",
        "occurred_at": "2026-01-11T10:30:00Z",
        "type": "delivered",
        "line_items": [{ "id": "li_1", "quantity": 1 }],
        "tracking_number": "123456789",
        "tracking_url": "https://fedex.com/track/123456789",
        "description": "Delivered to front door"
      }
    ]
  },
  "adjustments": [
    {
      "id": "adj_1",
      "type": "refund",
      "occurred_at": "2026-01-12T14:30:00Z",
      "status": "completed",
      "line_items": [{ "id": "li_1", "quantity": 1 }],
      "amount": 26550,
      "description": "Defective item"
    }
  ],
  "totals": [ ... ]
}
```

### Power native checkout

Integrate and negotiate directly with a seller's checkout API to power native UI and workflows for your platform.

[See how it works](https://ucp.dev/latest/specification/checkout-rest/index.md)

### Embed business checkout

Embed and render business checkout UI to support complex checkout flows, with advanced capabilities like bidirectional communication, and payment and shipping address delegation.

[Learn more](https://ucp.dev/latest/specification/embedded-checkout/index.md)

## Designed for the entire commerce ecosystem

### For Developers

Build the future of commerce on an open foundation. Join our community in evolving an open-source standard designed for the next generation of digital commerce.

[View the technical spec](https://ucp.dev/latest/specification/overview/index.md)

### For Businesses

UCP empowers retailers to meet customers wherever they are—AI assistants, shopping agents, embedded experiences—without rebuilding your checkout for each. You remain the Merchant of Record and your business logic stays intact.

[Integrate with UCP](https://developers.google.com/merchant/ucp/)

### For AI Platforms

Simplify business onboarding with standardized APIs and provide your audience with an integrated shopping experience. Compatible with MCP, A2A, and existing agent frameworks.

[Learn more about UCP core concepts](https://ucp.dev/documentation/core-concepts/index.md)

### For Payment Providers

Universal payments that are provable—every authorization backed by cryptographic proof of user consent. Open, modular payment handler design enables open interoperability and choice of payment methods.

[Learn more about UCP and AP2](https://ucp.dev/documentation/ucp-and-ap2/index.md)

## Endorsed across the ecosystem

Adyen

Affirm

Amex

Ant International

Best Buy

Block

Carrefour

Chewy

Chewy

Commerce

Fiserv

Flipkart

Gap

Klarna

Kroger

Lowe's

Macy's

Mastercard

Paypal

Salesforce

Sephora

Shopee

Splitit

Stripe

The Home Depot

Ulta

Visa

Worldpay

Zalando

Adyen

Affirm

Amex

Ant International

Best Buy

Block

Carrefour

Chewy

Chewy

Commerce

Fiserv

Flipkart

Gap

Klarna

Kroger

Lowe's

Macy's

Mastercard

Paypal

Salesforce

Sephora

Shopee

Splitit

Stripe

The Home Depot

Ulta

Visa

Worldpay

Zalando

## Get started today

UCP is an open standard designed to let AI agents, apps, businesses, and payment providers interact seamlessly without needing custom, one-off integrations for every connection. We actively seek your feedback and contributions to help build the future of commerce.

The complete technical specification, documentation, and reference implementations are hosted in our public GitHub repository.

### [Download](https://github.com/Universal-Commerce-Protocol/samples)

Download and run our code samples

### [Experiment](https://ucp.dev/latest/specification/playground/index.md)

Experiment with the protocol and its different agent roles

### [Contribute](https://github.com/Universal-Commerce-Protocol/.github/blob/main/CONTRIBUTING.md)

Contribute your feedback and code to the public repository

[Visit the GitHub repository](https://github.com/Universal-Commerce-Protocol/ucp)
