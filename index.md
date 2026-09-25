UCP is expanding beyond retail: Lodging draft specification now available. **Food coming soon.**

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

Catalog Cart Checkout Identity Linking Order

### Catalog

Enables platforms to search and browse business product catalogs through free-text search, category filtering, and batch retrieval to drive user journeys like price comparisons, sale price and back-in-stock/low-stock alerts.

[Get Started](http://ucp.dev/latest/specification/shopping/catalog/index.md)

```json
{
  "ucp": { ... },
  "products": [
    {
      "id": "prod_abc123",
      "handle": "blue-runner-pro",
      "title": "Blue Runner Pro",
      "description": {
        "plain": "Lightweight running shoes with responsive cushioning."
      },
      "url": "https://business.example.com/products/blue-runner-pro",
      "categories": [
        { "value": "187", "taxonomy": "google_product_category" },
        { "value": "aa-8-1", "taxonomy": "shopify" },
        { "value": "Footwear > Running", "taxonomy": "merchant" }
      ],
      "price_range": {
        "min": { "amount": 12000, "currency": "USD" },
        "max": { "amount": 12000, "currency": "USD" }
      },
      "media": [
        {
          "type": "image",
          "url": "https://cdn.example.com/products/blue-runner-pro.jpg",
          "alt_text": "Blue Runner Pro running shoes"
        }
      ],
      "options": [
        {
          "name": "Size",
          "values": [
            {"label": "8"},
            {"label": "9"},
            {"label": "10"},
            {"label": "11"},
            {"label": "12"}
          ]
        }
      ],
      "variants": [
        {
          "id": "prod_abc123_size10",
          "sku": "BRP-BLU-10",
          "title": "Size 10",
          "description": { "plain": "Size 10 variant" },
          "price": { "amount": 12000, "currency": "USD" },
          "availability": { "available": true },
          "options": [
            { "name": "Size", "label": "10" }
          ],
          "tags": ["running", "road", "neutral"],
          "seller": {
            "name": "Example Store",
            "links": [
              {
                "type": "refund_policy",
                "url": "https://business.example.com/refunds"
              }
            ]
          }
        }
      ],
      "rating": {
        "value": 4.5,
        "scale_max": 5,
        "count": 128
      },
      "metadata": {
        "collection": "Winter 2026",
        "technology": {
          "midsole": "React foam",
          "outsole": "Continental rubber"
        }
      }
    }
  ],
  "pagination": {
    "cursor": "eyJwYWdlIjoxfQ==",
    "has_next_page": true,
    "total_count": 47
  }
}
```

### Cart

Enables multi-item cart building and management across AI surfaces, allowing shoppers to seamlessly transfer carts directly to the merchant's site or complete purchases in-place through unified, multi-item checkout.

[Get Started](http://ucp.dev/latest/specification/shopping/cart/index.md)

```json
{
  "ucp": { ... },
  "id": "cart_88392A",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "item_luggage_01",
        "title": "Monos Carry-On Pro Suitcase",
        "price": 26500,
        "image_url": "https://example.com/images/carry-on-pro.jpg"
      },
      "quantity": 1,
      "totals": [ ... ]
    },
    {
      "id": "li_2",
      "item": {
        "id": "item_backpack_02",
        "title": "Monos Metro Backpack",
        "price": 18000,
        "image_url": "https://example.com/images/metro-backpack.jpg"
      },
      "quantity": 1,
      "totals": [ ... ]
    }
  ],
  "context": {
    "address_country": "US",
    "address_region": "CA",
    "postal_code": "94105",
    "intent": "travel gear",
    "language": "en-US",
    "currency": "USD"
  },
  "signals": {
    "dev.ucp.buyer_ip": "198.51.100.42",
    "dev.ucp.user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
  },
  "attribution": {
    "source": "google_search",
    "medium": "ai_mode",
    "campaign": "spring_travel_2026",
    "click_id": "gclid_987654321_abc",
    "referrer_url": "https://www.google.com/search"
  },
  "buyer": {
    "first_name": "Elisa",
    "last_name": "Beckett",
    "email": "e.beckett@example.com",
    "phone_number": "+16505550199"
  },
  "currency": "USD",
  "totals": [ ... ],
  "messages": [
    {
      "type": "info",
      "content": "You qualify for free standard delivery on orders over $100."
    }
  ],
  "links": [
    {
      "type": "privacy_policy",
      "url": "https://example.com/policies/privacy",
      "title": "Privacy Policy"
    },
    {
      "type": "terms_of_service",
      "url": "https://example.com/terms",
      "title": "Terms of Service"
    },
    {
      "type": "faq",
      "url": "https://example.com/help/faq",
      "title": "Frequently Asked Questions"
    }
  ],
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.return",
      "description": {
        "plain": "Free returns and exchanges within 30 days of delivery on unused items in original packaging."
      },
      "url": "https://example.com/policies/refunds",
      "applies_to": [
        "$.line_items[0]",
        "$.line_items[1]"
      ]
    }
  ],
  "continue_url": "https://example.com/cart?cart_id=cart_88392A",
  "expires_at": "2026-08-31T12:00:00Z"
}
```

### Checkout

Support complex cart logic, dynamic pricing, tax calculations, and more across millions of businesses through unified checkout sessions.

[Get Started](http://ucp.dev/latest/specification/shopping/checkout/index.md)

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
            "type": "shipping_address",
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

### Checkout

Support complex cart logic, dynamic pricing, tax calculations, and more across millions of businesses through unified checkout sessions.

[Get Started](http://ucp.dev/latest/specification/shopping/checkout/index.md)

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
            "type": "shipping_address",
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

[Get Started](http://ucp.dev/latest/specification/common/identity-linking/index.md)

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

[Get Started](http://ucp.dev/latest/specification/shopping/order/index.md)

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

### Booking

Enable high-quality booking flows within AI surfaces with real time pricing and availability checks for rooms, easy guest registration and secure checkout with complex payments schedules.

[Get Started](http://ucp.dev/draft/specification/lodging/booking/index.md)

```json
{
  "ucp": { ... },
  "id": "bk_fb_88392A",
  "status": "ready_for_complete",
  "booker": {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com",
    "phone_number": "+14085550199"
  },
  "property": {
    "id": "hotel_juniper_cupt",
    "name": "Juniper Hotel Cupertino",
    "address": {
      "street_address": "123 De Anza Blvd",
      "address_locality": "Cupertino",
      "address_region": "CA",
      "address_country": "US",
      "postal_code": "95014"
    },
    "media": [
      {
        "type": "image",
        "url": "https://example.com/juniper-cupertino.jpg"
      }
    ]
  },
  "stays": [
    {
      "id": "rt_luxury_queen__rp_avg_base_rate",
      "accommodation_type": {
        "id": "rt_luxury_queen",
        "title": "Deluxe Room, 2 Queens",
        "capacity": {
          "adults": 2,
          "total": 2
        }
      },
      "rate_plan": {
        "id": "rp_avg_base_rate",
        "title": "Best Available Rate"
      },
      "occupancy": {
        "adults": 2,
        "total": 2
      },
      "stay_dates": {
        "start_date": "2026-05-12",
        "end_date": "2026-05-17"
      },
      "totals": [ ... ]
    }
  ],
  "currency": "USD",
  "totals": [ ... ],
  "policies": [
    {
      "type": "dev.ucp.lodging.policy.cancellation",
      "refundability": "non_refundable",
      "description": {
        "plain": "Non-refundable rate. If you cancel or modify this reservation, or in the event of a no-show, no refund will be issued and the full booking amount is retained."
      },
      "url": "https://hotel.example.com/terms#non-refundable"
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "dev.ucp.lodging.policy.cancellation",
      "path": "$.stays[0]",
      "presentation": "disclosure",
      "content": "This reservation is non-refundable. Cancellations or changes will not be refunded."
    }
  ],
  "payment": {
    "selected_term_id": "pt_deposit_balance",
    "terms": [
      {
        "id": "pt_deposit_balance",
        "title": "Deposit today, balance at check-in",
        "description": {
          "plain": "Pay 2 night deposit ($1200.00) today and the remaining balance upon arrival."
        },
        "schedules": [
          {
            "id": "sched_deposit",
            "type": "immediate",
            "description": {
              "plain": "Due today upon booking confirmation."
            },
            "amount": 120000
          },
          {
            "id": "sched_balance_checkin",
            "type": "deferred",
            "description": {
              "plain": "FlightBulb will charge you the remaining on May 12, 2026."
            },
            "due_at": "2026-05-12T15:00:00-07:00",
            "amount": 8445
          }
        ]
      }
    ],
    "instruments": [
      {
        "id": "pi_card_88392A",
        "handler_id": "handler_1",
        "type": "card",
        "selected": true,
        "display": {
          "brand": "amex",
          "last_digits": "1234",
          "description": "Amex ending in 1234"
        },
        "billing_address": {
          "street_address": "123 De Anza Blvd",
          "address_locality": "Cupertino",
          "address_region": "CA",
          "address_country": "US",
          "postal_code": "95014"
        }
      }
    ]
  },
  "links": [
    {
      "type": "privacy_policy",
      "url": "https://hotel.example.com/privacy"
    },
    {
      "type": "terms_of_service",
      "url": "https://hotel.example.com/terms"
    },
    {
      "type": "refund_policy",
      "title": "Cancellation Policy",
      "url": "https://hotel.example.com/cancellation"
    }
  ],
  "continue_url": "https://business.example.com/booking-sessions/bk_fb_88392A",
  "expires_at": "2026-05-12T06:30:00Z"
}
```

### Food

Powers conversational food ordering journeys that seamlessly handle nuanced meal customization, real-time availability and deals, tipping, and delivery instructions through a scalable checkout experience on AI surfaces.

[Learn more](https://developers.google.com/actions-center/verticals/ordering/ucp)

Detailed specifications coming soon

### Power native checkout

Integrate and negotiate directly with a seller's checkout API to power native UI and workflows for your platform.

[Get Started](http://ucp.dev/latest/specification/shopping/checkout/rest/index.md)

### Embed business checkout

Embed and render business checkout UI to support complex checkout flows, with advanced capabilities like bidirectional communication, and payment and shipping address delegation.

[See how it works](http://ucp.dev/latest/specification/shopping/checkout/embedded/index.md)

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

Iconic

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

Iconic

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

### [Experiment](http://ucp.dev/latest/specification/shopping/playground/index.md)

Experiment with the protocol and its different agent roles

### [Contribute](https://github.com/Universal-Commerce-Protocol/.github/blob/main/CONTRIBUTING.md)

Contribute your feedback and code to the public repository

[Visit the GitHub repository](https://github.com/Universal-Commerce-Protocol/ucp)
