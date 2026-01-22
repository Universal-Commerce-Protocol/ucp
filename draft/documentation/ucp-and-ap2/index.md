# UCP and AP2

UCP is fully compatible with [Agent Payments Protocol (AP2)](https://ap2-protocol.org/). AP2 serves as the trust layer for agent-led transactions completed on behalf of a user, mandating a secure, verifiable exchange of intents and authorizations between Platforms and businesses. By using Verifiable Digital Credentials (VDCs), AP2 eliminates the need for middleman "trust referees." It allows businesses to receive signed checkout commitments—ensuring the price and terms don't change mid-flow—and allows Platforms to provide cryptographically signed payment authorizations that are mathematically tied to the specific state of the cart.

## Key benefits

- **Binding proof:** Both parties have cryptographic evidence of exactly what was offered and what was agreed upon, ensuring the transaction is final and authentic.
- **Fraud reduction:** Payment mandates are scoped specifically to a checkout hash, preventing "token replay" or amount manipulation.
- **Agentic readiness:** Allows autonomous AI agents to transact on behalf of users with pre-defined, verifiable boundaries.

## Protocol flow

1. **Discovery:** The business publishes their discovery document, declaring support for the AP2 extension.
1. **Session Activation:** When creating or updating a checkout session, the Platform signals the activation of AP2.
1. **Signing (business):** The business responds with a `checkoutSignature` (a detached JWT signing the checkout state) and lists supported verifiable presentation formats (e.g., `sd-jwt`).
1. **Authorization:** Upon user consent, the Platform generates two credentials:
   - **CheckoutMandate:** Contains the hash of the `CheckoutObject`.
   - **PaymentMandate:** An SD-JWT-VC containing the payment authorization.
1. **Completion:** The Platform submits both mandates to the business’ `/complete` endpoint.
1. **Verification:**
   - The business verifies the `CheckoutMandate`.
   - The Payment Processor verifies the `PaymentMandate`.
1. **Confirmation:** If valid, the payment is processed, and the order is confirmed.

**Dependencies:** Checkout capability

[See here for full AP2 mandates extension](https://ucp.dev/draft/specification/ap2-mandates/index.md)

[Learn more about AP2](https://ap2-protocol.org)
