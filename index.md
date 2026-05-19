UCP is expanding to new industries, starting with Lodging and Food

Detailed specifications coming soon!

# Universal Commerce Protocol

The common language for platforms, agents, and businesses.

UCP provides building blocks for agentic commerce across industries—from discovery to checkout and beyond—allowing the ecosystem to operate through one standard, without custom builds.

### Learn

Protocol overview, core concepts, and design principles

[Get Started](http://ucp.dev/latest/specification/overview/index.md)

### Implement

GitHub repo, technical spec, SDKs, and reference implementations

[View on GitHub](https://github.com/Universal-Commerce-Protocol/ucp)

## Co-developed by industry leaders

UCP is built by the industry, to enable seamless agentic experiences. It solves fragmented user journeys that lead to frustrated users and conversion drop off.

Shopping Lodging Food

Google

Shopify

Etsy

Wayfair

Target

Walmart

Amazon

Microsoft

Meta

Salesforce

Stripe

Amadeus

Booking.com

Expedia Group

Google

Hilton

Marriott

Trip.com

DoorDash

Google

Square

Toast

Uber Eats

## Built for flexibility, security, and scale

Agentic commerce requires interoperability. UCP is built on industry standards — REST and JSON-RPC transports; [Agent Payments Protocol (AP2)](https://ap2-protocol.org/), [Agent2Agent (A2A)](https://a2a-protocol.org/latest/), and [Model Context Protocol (MCP)](https://modelcontextprotocol.io/docs/getting-started/intro) support built-in — so different systems can work together without custom integration.

### Scalable and universal

Surface-agnostic design that scales to support any business (from small to enterprise), in every industry, across all modalities, including chat, visual commerce, and voice.

### Businesses at the center

Built to facilitate commerce, ensuring businesses retain control and remain the Merchant of Record, with full ownership of customer relationships.

### Open and extensible

Open and extensible by design, enabling development of community-driven capabilities and extensions across industries.

### Secure and private

Built on proven security standards for account linking (OAuth 2.0) and secure payment (AP2) via payment mandates and verifiable credentials.

### Frictionless payments

Open wallet ecosystem with interoperability between providers, ensuring buyers can use their preferred payment methods.

## See it in action

UCP is designed to facilitate the entire commerce lifecycle, from discovery and search to final sale and post-purchase support. The protocol supports a range of core capabilities, including: Catalog Search and Lookup, Cart Building, Identity Linking, Checkout, and Order Management.

Shopping Lodging Food

Checkout Identity Linking Order

### Checkout

Support complex cart logic, dynamic pricing, tax calculations, and more across millions of businesses through unified checkout sessions.

[Get Started](/latest/specification/checkout/)

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

### Identity Linking

OAuth 2.0 standard enables agents to maintain secure, authorized relationships without sharing credentials.

[Get Started](http://ucp.dev/latest/specification/identity-linking/index.md)

```json
Sample of /.well-known/oauth-authorization-server

{
  "issuer": "https://example.com",
  "authorization_endpoint": "https://example.com/oauth2/authorize",
  "token_endpoint": "https://example.com/oauth2/token",
  "revocation_endpoint": "https://example.com/oauth2/revoke",
  "scopes_supported": [
    "dev.ucp.shopping.checkout"
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

### Order

From purchase confirmation to delivery. Real-time webhooks power status updates, shipment tracking, and return processing across every channel.

[Get Started](http://ucp.dev/latest/specification/order/index.md)

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
      "line_items": [{ "id": "li_1", "quantity": -1 }],
      "totals": [{ "type": "total", "amount": -26550 }],
      "description": "Defective item"
    }
  ],
  "totals": [ ... ]
}
```

### Lodging

Enables high-quality booking flows within AI surfaces—complete with real-time pricing and availability checks, smooth handling of complex rate plans, easy guest registration, and secure checkout.

[Learn more](https://developers.google.com/hotels/ucp)

Detailed specifications coming soon

### Food

Powers conversational food ordering journeys that seamlessly handle nuanced meal customization, real-time availability and deals, tipping, and delivery instructions through a scalable checkout experience on AI surfaces.

[Learn more](https://developers.google.com/actions-center/verticals/ordering/ucp)

Detailed specifications coming soon

### Power native checkout

Integrate and negotiate directly with a seller's checkout API to power native UI and workflows for your platform.

[Get Started](http://ucp.dev/latest/specification/checkout-rest/index.md)

### Embed business checkout

Embed and render business checkout UI to support complex checkout flows, with advanced capabilities like bidirectional communication, and payment and shipping address delegation.

[See how it works](http://ucp.dev/latest/specification/embedded-checkout/index.md)

## Designed for the entire commerce ecosystem

### For Developers

Build the future of commerce on an open foundation. Join our community in evolving an open-source standard designed for the next generation of digital commerce.

[View the technical spec](http://ucp.dev/latest/specification/overview/index.md)

### For Businesses

UCP empowers businesses to meet customers wherever they are—AI assistants, agents, embedded experiences—without rebuilding your checkout for each. You remain the Merchant of Record and your business logic stays intact.

[Integrate with UCP](https://developers.google.com/merchant/ucp/)

### For AI Platforms

Simplify business onboarding with standardized APIs and provide your audience with an integrated agentic commerce experience. Compatible with MCP, A2A, and existing agent frameworks.

[Learn more about UCP core concepts](http://ucp.dev/documentation/core-concepts/index.md)

### For Payment Providers

Universal payments that are provable—every authorization backed by cryptographic proof of user consent. Open, modular payment handler design enables open interoperability and choice of payment methods.

[Learn more about UCP and AP2](http://ucp.dev/documentation/ucp-and-ap2/index.md)

## Endorsed across the ecosystem

Accor

Adore Beauty

Adyen

Affirm

Amadeus

Amex

Ant International

Best Buy

Block

Booking.com

Bunnings

Carrefour

Checkout.com

Chewy

Choice Hotels

Commerce

DoorDash

Expedia Group

Fiserv

Flipkart

Gap

Hilton

IHG

Klarna

Kogan

Kroger

Lowe's

Macy's

Marriott

Mastercard

Paypal

Petbarn

Salesforce

SAP

Sephora

Shopee

Splitit

Square

Stripe

The Home Depot

Toast

Trip.com

Uber Eats

Ulta

Visa

VTEX

Worldpay

Wyndham

Zalando

Accor

Adore Beauty

Adyen

Affirm

Amadeus

Amex

Ant International

Best Buy

Block

Booking.com

Bunnings

Carrefour

Checkout.com

Chewy

Choice Hotels

Commerce

DoorDash

Expedia Group

Fiserv

Flipkart

Gap

Hilton

IHG

Klarna

Kogan

Kroger

Lowe's

Macy's

Marriott

Mastercard

Paypal

Petbarn

Salesforce

SAP

Sephora

Shopee

Splitit

Square

Stripe

The Home Depot

Toast

Trip.com

Uber Eats

Ulta

Visa

VTEX

Worldpay

Wyndham

Zalando

## Get started today

UCP is an open standard designed to let AI agents, apps, businesses, and payment providers interact seamlessly without needing custom, one-off integrations for every connection. We actively seek your feedback and contributions to help build the future of commerce.

The complete technical specification, documentation, and reference implementations are hosted in our public GitHub repository.

### [Download](https://github.com/Universal-Commerce-Protocol/samples)

Download and run our code samples

### [Experiment](http://ucp.dev/latest/specification/playground/index.md)

Experiment with the protocol and its different agent roles

### [Contribute](https://github.com/Universal-Commerce-Protocol/.github/blob/main/CONTRIBUTING.md)

Contribute your feedback and code to the public repository

[Visit the GitHub repository](https://github.com/Universal-Commerce-Protocol/ucp)
