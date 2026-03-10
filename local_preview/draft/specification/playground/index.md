# UCP Playground

Walk through a complete UCP checkout flow step-by-step. This interactive demo runs entirely in the browser, simulating payloads and validating against real UCP schemas at each stage.

## 1. Platform Profile

Select the capability profile for the Platform. This determines which extensions (e.g., fulfillment, discounts) are negotiated.

### Configuration

Platform Type Standard (Core Only) Advanced (All Extensions)

Supports basic checkout and order retrieval.

Capabilities Copy

Continue →

## 2. Discovery

The Platform fetches `/.well-known/ucp`. The response below is filtered to show the intersection of the Business's capabilities and the Platform's profile.

GET Request

```
GET /.well-known/ucp HTTP/1.1
Host: business.example.com
Accept: application/json
```

Response (Filtered)

← Back Continue →

## 3. Capability Negotiation

Intersection of Platform and Business capabilities. Orphaned extensions are pruned.

Business Capabilities

Resulting Intersection

← Back Continue →

## 4. Create Checkout

The Platform initiates a session. The error response below follows the strict `message.json` schema.

Request Payload

Response

Simulation Scenario:

Missing Buyer Email Missing Shipping Destination Run Request

← Back Next Step →

## 5. Update Checkout

Patch the checkout with missing information to resolve validation errors.

PATCH Request Run Update

Response

← Back Next Step →

## 6. Mint Instrument

Simulate the payment handler flow to acquire a payment credential.

### Select Handler

**Shop Pay**\
com.shopify.shop_pay

**Google Pay**\
com.google.pay

Mint Credential

Minted Instrument

← Back Next Step →

## 7. Complete Checkout

Submit the minted instrument to finalize the transaction and create an order.

Request Finalize

Response (Order Created)

**Success!** Order ID: created.

← Back Next Step →

## 8. Webhook Simulation

Simulate a backend event (e.g., shipping center update) triggering a webhook push to the Agent.

### Trigger Event

This action runs on the Business server and pushes data to the Platform's webhook URL.

Simulate "Shipped" Event

Webhook Payload (POST) Push Notification

```
// Waiting for event trigger...
```

← Back

About this demo

This playground is a simulation running entirely in your browser. It uses mocked logic to demonstrate the UCP protocol flow and isn't intended as a reference for production code. For real-world implementation examples and best practices, please check out our [samples on GitHub](https://github.com/Universal-Commerce-Protocol/samples).
