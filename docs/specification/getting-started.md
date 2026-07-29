---
description: Getting started guide for building UCP servers in Python and Node.js.
---

<!-- cspell:ignore uuidv4 uuidv autonumber -->

# Getting Started with UCP

This guide will walk you through building a basic Universal Commerce Protocol (UCP) server. We provide examples for both **Python (FastAPI)** and **Node.js (Express)** using the official [Python SDK](https://github.com/Universal-Commerce-Protocol/python-sdk) and [TypeScript SDK](https://github.com/Universal-Commerce-Protocol/js-sdk).

We will implement a simple checkout server that allows a platform to initiate a checkout session and retrieve it.

## Prerequisites

=== "Python"

    * Python 3.10 or higher installed.
    * Basic familiarity with FastAPI and Pydantic.
    * We recommend using [`uv`](https://docs.astral.sh/uv/) for package management.

=== "Node.js"

    * Node.js 18 or higher installed.
    * Basic familiarity with Express and Zod.

---

## Project Setup

=== "Python"

    Create a new directory and initialize the project:

    ```bash
    mkdir ucp-quickstart-python
    cd ucp-quickstart-python
    uv init
    ```

    Add the required dependencies. [`ucp-sdk`](https://github.com/Universal-Commerce-Protocol/python-sdk) contains the Pydantic models generated from UCP schemas:

    ```bash
    uv add fastapi uvicorn ucp-sdk
    ```

=== "Node.js"

    Create a new directory and initialize the project:

    ```bash
    mkdir ucp-quickstart-nodejs
    cd ucp-quickstart-nodejs
    npm init -y
    ```

    Configure your `package.json` to use ES Modules by adding `"type": "module"`.

    Add the required dependencies. [`@ucp-js/sdk`](https://github.com/Universal-Commerce-Protocol/js-sdk) contains the TypeScript types and Zod schemas:

    ```bash
    npm install express uuid @ucp-js/sdk
    npm install --save-dev typescript @types/express @types/node ts-node
    ```

    Initialize TypeScript configuration:

    ```bash
    npx tsc --init
    ```

---

## Implementing the Server

We will implement the server step-by-step. The server needs to handle:

1. **Create Checkout (`POST /checkout-sessions`)**: Receives desired items and returns a checkout session with totals and available payment handlers.
2. **Get Checkout (`GET /checkout-sessions/{id}`)**: Allows the platform to poll the session status.

### High-Level Flow

Here is how the components interact during the checkout process:

```mermaid
sequenceDiagram
    autonumber
    actor Platform as Platform
    participant Server as Checkout Server (Your App)
    database DB as In-Memory DB

    Note over Platform,Server: Create Checkout Session
    Platform->>+Server: POST /checkout-sessions\n(Items, Headers: Idempotency-Key, UCP-Agent)
    Note over Server: 1. Validate Headers & Body\n2. Calculate Totals (Minor Units)\n3. Advertise Payment Handlers
    Server->>DB: Store Session
    Server-->>-Platform: 201 Created (Checkout Object)

    Note over Platform,Server: Retrieve Checkout Session (Polling)
    Platform->>+Server: GET /checkout-sessions/{id}
    Server->>DB: Fetch Session
    Server-->>-Platform: 200 OK (Checkout Object)
```

### How it fits into the E2E Flow

In a complete UCP integration, the flow follows these phases:

1. **Discovery:** The Platform discovers your UCP endpoints (like `/checkout-sessions`) by fetching your UCP Discovery Profile at `/.well-known/ucp`.
2. **Create Checkout (Implemented in this guide):** The Platform initiates the checkout session with the items the user wants to buy.
3. **Update Checkout:** The Platform updates the checkout session with buyer details (e.g., shipping address, email) to calculate final taxes and shipping options.
4. **Complete Checkout:** The Platform submits the payment credentials to finalize the order.

This guide focuses on step 2 (Create Checkout) and the subsequent retrieval of the checkout session state.

### 1. Imports and Setup

Initialize the application and define an in-memory database to store sessions.

=== "Python"

    ```python
    # main.py
    import uuid
    from typing import Annotated
    from fastapi import FastAPI, Header, HTTPException, status

    # Import UCP SDK models
    from ucp_sdk.models.schemas.ucp import ResponseCheckoutSchema
    from ucp_sdk.models.schemas.shopping.checkout import Checkout
    from ucp_sdk.models.schemas.shopping.checkout_create_request import CheckoutCreateRequest
    from ucp_sdk.models.schemas.shopping.types.line_item import LineItem
    from ucp_sdk.models.schemas.shopping.types.item import Item
    from ucp_sdk.models.schemas.shopping.types.totals import Total
    from ucp_sdk.models.schemas.shopping.types.link import Link
    from ucp_sdk.models.schemas.shopping.types.available_payment_instrument import AvailablePaymentInstrument
    from ucp_sdk.models.schemas.payment_handler import ResponseSchema as PaymentHandlerResponse

    # Initialize FastAPI app
    app = FastAPI(title="UCP Quickstart Server")

    # Simple in-memory database
    checkout_sessions = {}
    ```

=== "Node.js"

    ```typescript
    // server.ts
    import express from 'express';
    import { v4 as uuidv4 } from 'uuid';

    // Import validation schemas from JS SDK
    import {
      CheckoutCreateRequestSchema,
      CheckoutResponseSchema,
      CheckoutResponse
    } from '@ucp-js/sdk';

    // Initialize Express app
    const app = express();
    app.use(express.json());

    // Simple in-memory database
    const checkoutSessions: Record<string, CheckoutResponse> = {};
    ```

### 2. Create Checkout Endpoint (Route & Header Validation)

Define the endpoint to create a checkout session. UCP requires `Idempotency-Key` and `UCP-Agent` headers.

=== "Python"

    ```python
    # main.py
    @app.post(
        "/checkout-sessions",
        response_model=Checkout,
        status_code=status.HTTP_201_CREATED,
        response_model_exclude_none=True
    )
    async def create_checkout(
        body: CheckoutCreateRequest,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
        ucp_agent: Annotated[str, Header(alias="UCP-Agent")]
    ):
        """Create a new UCP checkout session."""
        # Note: In a production environment, you must use the Idempotency-Key
        # to prevent duplicate processing of the same request.

        # Generate a unique checkout session ID
        session_id = f"chk_{uuid.uuid4().hex[:10]}"
    ```

=== "Node.js"

    ```typescript
    // server.ts
    app.post('/checkout-sessions', (req, res) => {
      // 1. Validate required UCP headers
      const idempotencyKey = req.header('Idempotency-Key');
      const ucpAgent = req.header('UCP-Agent');

      if (!idempotencyKey || !ucpAgent) {
        return res.status(400).json({
          error: 'Missing required headers (Idempotency-Key, UCP-Agent)'
        });
      }

      // 2. Validate request body against UCP schema using Zod
      const validation = CheckoutCreateRequestSchema.safeParse(req.body);
      if (!validation.success) {
        return res.status(400).json({ errors: validation.error.errors });
      }

      const body = validation.data;

      // Generate a unique checkout session ID
      const sessionId = `chk_${uuidv4().substring(0, 10)}`;
    ```

### 3. Business Logic (Process Items & Calculate Totals)

Process the incoming line items, resolve their prices, and calculate the subtotal, tax, and total. Prices are always in **minor units** (e.g., cents for USD).

=== "Python"

    ```python
    # main.py
        # Map input line items to output line items with pricing
        output_line_items = []
        subtotal = 0
        tax = 0

        for index, item_req in enumerate(body.line_items):
            # Mock product database lookup
            price = 2500  # $25.00 in minor units (cents)
            title = f"Flower Bouquet {item_req.item.id}"
            item_subtotal = price * item_req.quantity
            item_tax = int(item_subtotal * 0.08)  # 8% tax
            item_total = item_subtotal + item_tax

            subtotal += item_subtotal
            tax += item_tax

            output_line_items.append(
                LineItem(
                    id=f"li_{index}",
                    item=Item(id=item_req.item.id, title=title, price=price),
                    quantity=item_req.quantity,
                    totals=[
                        Total(type="subtotal", amount=item_subtotal),
                        Total(type="tax", amount=item_tax),
                        Total(type="total", amount=item_total)
                    ]
                )
            )

        total = subtotal + tax
    ```

=== "Node.js"

    ```typescript
    // server.ts
      // Map input line items to output line items with pricing
      const outputLineItems = body.line_items.map((item, index) => {
        // Mock product database lookup
        const price = 2500; // $25.00 in minor units (cents)
        const title = `Flower Bouquet ${item.item.id}`;
        const itemSubtotal = price * item.quantity;
        const itemTax = Math.floor(itemSubtotal * 0.08); // 8% tax
        const itemTotal = itemSubtotal + itemTax;

        return {
          id: `li_${index}`,
          item: { id: item.item.id, title, price },
          quantity: item.quantity,
          totals: [
            { type: 'subtotal', amount: itemSubtotal },
            { type: 'tax', amount: itemTax },
            { type: 'total', amount: itemTotal }
          ]
        };
      });

      // Calculate order totals from line items
      const subtotal = outputLineItems.reduce((acc, item) => {
        const subtotalEntry = item.totals.find(t => t.type === 'subtotal');
        return acc + (subtotalEntry ? subtotalEntry.amount : 0);
      }, 0);
      const tax = outputLineItems.reduce((acc, item) => {
        const taxEntry = item.totals.find(t => t.type === 'tax');
        return acc + (taxEntry ? taxEntry.amount : 0);
      }, 0);
      const total = subtotal + tax;
    ```

### 4. UCP Response Construction

Construct the UCP metadata block, advertising supported payment handlers, and assemble the final checkout response.

=== "Python"

    ```python
    # main.py
        # Configure available payment handlers.
        # We advertise support for a generic mock payment handler.
        payment_handlers = {
            "com.example.mock_pay": [
                PaymentHandlerResponse(
                    id="mock_pay_handler_1",
                    version="2026-04-08",
                    available_instruments=[
                        AvailablePaymentInstrument(type="mock_instrument")
                    ]
                )
            ]
        }

        # Construct UCP protocol metadata
        ucp_metadata = ResponseCheckoutSchema(
            version="2026-04-08",
            status="success",
            payment_handlers=payment_handlers
        )

        # Assemble the final Checkout payload
        checkout = Checkout(
            ucp=ucp_metadata,
            id=session_id,
            status="incomplete",
            currency="USD",
            line_items=output_line_items,
            totals=[
                Total(type="subtotal", amount=subtotal),
                Total(type="tax", amount=tax),
                Total(type="total", amount=total)
            ],
            links=[
                Link(type="terms_of_service", url="https://example.com/terms"),
                Link(type="privacy_policy", url="https://example.com/privacy")
            ]
        )

        # Save to database and return
        checkout_sessions[session_id] = checkout
        return checkout
    ```

=== "Node.js"

    ```typescript
    // server.ts
      // Configure available payment handlers.
      // We advertise support for a generic mock payment handler.
      const ucpMetadata = {
        version: '2026-04-08',
        status: 'success' as const,
        payment_handlers: {
          'com.example.mock_pay': [
            {
              id: 'mock_pay_handler_1',
              version: '2026-04-08',
              available_instruments: [
                { type: 'mock_instrument' }
              ]
            }
          ]
        }
      };

      // Assemble the final Checkout payload
      const checkout: CheckoutResponse = {
        ucp: ucpMetadata,
        id: sessionId,
        status: 'incomplete',
        currency: 'USD',
        line_items: outputLineItems,
        totals: [
          { type: 'subtotal', amount: subtotal },
          { type: 'tax', amount: tax },
          { type: 'total', amount: total }
        ],
        links: [
          { type: 'terms_of_service', url: 'https://example.com/terms' },
          { type: 'privacy_policy', url: 'https://example.com/privacy' }
        ]
      };

      // Validate output matches CheckoutResponse schema before sending
      const outputValidation = CheckoutResponseSchema.safeParse(checkout);
      if (!outputValidation.success) {
        console.error('Output validation failed:', outputValidation.error);
        return res.status(500).json({ error: 'Internal server error' });
      }

      // Save to database and return
      checkoutSessions[sessionId] = checkout;
      res.status(201).json(checkout);
    });
    ```

### 5. Get Checkout Endpoint

Implement the retrieval route so the platform can fetch the checkout state.

=== "Python"

    ```python
    # main.py
    @app.get(
        "/checkout-sessions/{id}",
        response_model=Checkout,
        response_model_exclude_none=True
    )
    async def get_checkout(id: str):
        """Retrieve an existing checkout session."""
        if id not in checkout_sessions:
            raise HTTPException(status_code=404, detail="Checkout session not found")
        return checkout_sessions[id]
    ```

=== "Node.js"

    ```typescript
    // server.ts
    app.get('/checkout-sessions/:id', (req, res) => {
      const session = checkoutSessions[req.params.id];
      if (!session) {
        return res.status(404).json({ error: 'Checkout session not found' });
      }
      res.json(session);
    });

    const PORT = 8000;
    app.listen(PORT, () => {
      console.log(`Server is running on port ${PORT}`);
    });
    ```

---

## Running the Server

=== "Python"

    Start the server using Uvicorn:

    ```bash
    uv run uvicorn main:app --port 8000 --reload
    ```

=== "Node.js"

    Add a start script to your `package.json`:

    <!-- ucp:example skip reason="package.json snippet" -->
    ```json
    "scripts": {
      "start": "ts-node server.ts"
    }
    ```

    Start the server:

    ```bash
    npm start
    ```

Your server is now running at `http://127.0.0.1:8000`.

---

## Testing the Server

You can test your server using `curl`.

### 1. Create a Checkout Session

Send a `POST` request to create a checkout session with one item:

```bash
curl -X POST http://127.0.0.1:8000/checkout-sessions \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-key-123" \
  -H "UCP-Agent: profile=\"https://platform.example/profile\"" \
  -d '{
    "line_items": [
      {
        "item": {
          "id": "prod_roses"
        },
        "quantity": 2
      }
    ]
  }'
```

You should receive a response containing the UCP metadata, calculated totals, and the configured payment handler:

<!-- ucp:example skip reason="FastAPI/Express response mock" -->
```json
{
  "ucp": {
    "version": "2026-04-08",
    "status": "success",
    "payment_handlers": {
      "com.example.mock_pay": [
        {
          "version": "2026-04-08",
          "id": "mock_pay_handler_1",
          "available_instruments": [
            {
              "type": "mock_instrument"
            }
          ]
        }
      ]
    }
  },
  "id": "chk_...",
  "line_items": [
    {
      "id": "li_0",
      "item": {
        "id": "prod_roses",
        "title": "Flower Bouquet prod_roses",
        "price": 2500
      },
      "quantity": 2,
      "totals": [
        {
          "type": "subtotal",
          "amount": 5000
        },
        {
          "type": "tax",
          "amount": 400
        },
        {
          "type": "total",
          "amount": 5400
        }
      ]
    }
  ],
  "status": "incomplete",
  "currency": "USD",
  "totals": [
    {
      "type": "subtotal",
      "amount": 5000
    },
    {
      "type": "tax",
      "amount": 400
    },
    {
      "type": "total",
      "amount": 5400
    }
  ],
  "links": [
    {
      "type": "terms_of_service",
      "url": "https://example.com/terms"
    },
    {
      "type": "privacy_policy",
      "url": "https://example.com/privacy"
    }
  ]
}
```

### 2. Retrieve the Checkout Session

Retrieve the session using the `id` returned from the previous step:

```bash
curl http://127.0.0.1:8000/checkout-sessions/<replace-with-your-checkout-id>
```

---

## Next Steps

To build a fully compliant UCP server, you will also need to:

* Implement the checkout update endpoint (`PUT /checkout-sessions/{id}`) to handle buyer information updates (like shipping address).
* Implement the checkout completion endpoint (`POST /checkout-sessions/{id}/complete`) to process the payment instrument provided by the platform.
* Advertise your service using a [UCP Discovery Profile](../documentation/core-concepts.md#discovery-capability-negotiation) at `/.well-known/ucp`.
* Run the conformance suite from the [UCP Conformance repository](https://github.com/Universal-Commerce-Protocol/conformance) against your server to verify protocol compliance.

For a complete reference implementation, check out the [UCP Samples repository](https://github.com/Universal-Commerce-Protocol/samples).
