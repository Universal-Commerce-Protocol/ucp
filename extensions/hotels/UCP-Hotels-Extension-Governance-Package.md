UCP Hotels Extension
Governance Submission Package

Version: 1.0
Status: Draft for Review
Authors: [Your Name / Organization]
Target: Google UCP Governance Review

---------------------------------------------------------------------
1. Executive Summary
---------------------------------------------------------------------
This submission proposes a Hotels (Lodging) Extension to UCP to formally support:
• Static discovery
• Identity-enriched eligibility
• Confirmation-ready offers
• Optional cart intent stabilization
• Checkout as execution boundary
• Asynchronous confirmation handling
• Order lifecycle and event publication

Hotels represent a structurally distinct commerce domain that cannot be safely modeled using generic Offer primitives alone.

This extension preserves:
• UCP core principles
• Transport neutrality
• Merchant neutrality
• Agent compatibility

---------------------------------------------------------------------
2. Why Hotels Require a Dedicated Extension
---------------------------------------------------------------------
Hotels differ from retail-style commerce in the following ways:

2.1 Time-Bound Inventory

Hotel pricing depends on:

• Check-in / Check-out dates
• Occupancy
• Availability window

Unlike static SKUs, hotel products are temporal.

2.2 Multi-Dimensional Pricing

Pricing varies by:

• Loyalty tier
• Corporate agreements
• Market/POS
• Stay window
• Add-ons
• Cancellation flexibility

Without structured identity-aware pricing, implementations diverge.

2.3 Strict Discovery vs Pricing Separation

Discovery must:

• Be cacheable
• Be non-binding
• Support ranking and filtering
• Expose indicative price signals only

Pricing must:

• Be confirmation-ready
• Include taxes and fees
• Include cancellation rules
• Be time-bound and revalidated

The extension formalizes this boundary.

2.4 Asynchronous Confirmation

Hotel suppliers frequently:

• Revalidate inventory
• Confirm asynchronously
• Issue confirmation after payment authorization

Generic synchronous checkout assumptions are insufficient.

2.5 Complex Order Lifecycle

Hotels require:

• Cancellation deadlines
• Modification rules
• Refund logic
• Status updates via events

Order state modeling must be explicit.
---------------------------------------------------------------------
3. Scope of the Extension
---------------------------------------------------------------------
The Hotels Extension defines:
• HotelProduct (discovery)
• RoomVariant (room identity, not rate plan)
• IdentityContext
• HotelOffer (confirmation-ready)
• Cart (optional intent stabilization)
• Checkout
• HotelOrder
• OrderEvent

---------------------------------------------------------------------
4. Architecture Overview
---------------------------------------------------------------------
Flow:

Discovery
→ Identity Enrichment
→ Offer / Pricing
→ Cart (Optional)
→ Checkout
→ Order
→ Events

The extension maintains strict state transitions and idempotency boundaries.

---------------------------------------------------------------------
5. Specification Summary
---------------------------------------------------------------------
5.1 Discovery Layer (Non-Binding)

Defines:
• product_id
• location
• star_rating
• amenities
• image_urls
• variant modeling
• indicative price range

Discovery MUST NOT:

• Represent live guarantees
• Represent confirmation-ready pricing
• Trigger reservation holds

5.2 IdentityContext

Supports:
• traveler_id
• loyalty_program_id
• loyalty_tier
• corporate_id
• rate_access_code
• market/POS
• identity_confidence_level

Identity:
• Enriches pricing and eligibility
• Does not gate discovery
• May be verified at offer or checkout

5.3 Offer Model (Binding)

HotelOffer:

• offer_id
• stay_dates
• occupancy
• total_price
• taxes_and_fees
• cancellation_policy
• expires_at
• requires_reprice_before_checkout

Offers are:
• Time-bound
• Confirmation-ready
• Revalidation-aware

5.4 Cart (Optional)

Cart:
• Stabilizes intent
• Does NOT reserve inventory
• May reference offer_id
• May expire
• Cart ≠ booking commitment.

5.5 Checkout (Execution Boundary)

Checkout requires:
• Offer or cart-backed selection
• Guest details
• Payment method reference
• Idempotency key

Checkout may result in:
• CONFIRMED
• PENDING
• FAILED

Async confirmation is supported.

5.6 Order Model

HotelOrder defines:
• order_id
• confirmation_number
• booking_status
• order_state
• cancellation_deadline
• modification_rules
• refund_rules
• merchant_reference

Order and booking state are independent.

5.7 Event Model

OrderEvent:

• ORDER_CONFIRMED
• ORDER_CANCELLED
• ORDER_MODIFIED
• PAYMENT_FAILED

Supports agent subscription.
---------------------------------------------------------------------
6. Explicit Non-Goals
---------------------------------------------------------------------
This extension does NOT:

• Define payment processing standards
• Mandate cart usage
• Standardize CRS/PMS internals
• Define OTA commission flows
• Mandate loyalty verification mechanisms
• Replace core UCP primitives

It defines protocol-level interoperability only.
---------------------------------------------------------------------
7. Backward Compatibility & Versioning
---------------------------------------------------------------------
• Discovery attributes are additive
• IdentityContext fields are additive
• Order state expansion must remain backward-compatible
• Breaking changes require major version increment
---------------------------------------------------------------------
8. Governance Checklist
---------------------------------------------------------------------
8.1 Architectural Compliance

• Transport-agnostic
• Merchant-neutral
• No dependency on specific CRS/PMS
• No Sabre-specific constructs
• Does not modify UCP core primitives

8.2 Semantic Integrity
• Discovery is non-binding
• Offer is confirmation-ready
• Cart does not reserve inventory
• Checkout is execution boundary
• Async confirmation supported
• Order state model defined

8.3 Identity Governance
• Identity does not gate discovery
• Confidence levels supported
• Corporate and loyalty modeled
• Market/POS explicitly modeled

8.4 Event Model
• Explicit event types
• State transition clarity
• Async-safe updates
• Polling + event patterns supported

8.5 Risk Mitigation

This extension prevents:
• Merchant-specific divergence
• Unsafe overloading of Offer primitives
• Ambiguity in async confirmation
• Identity inconsistency across implementations
---------------------------------------------------------------------
9. Open Questions for Governance
---------------------------------------------------------------------
• Should Cart be standardized or remain optional?
• Should IdentityContext be elevated to UCP core?
• Should async confirmation be required capability?
• Should hotel-specific Offer fields remain extension-only?
• Should modification/cancellation be mandatory V1 capabilities?

---------------------------------------------------------------------
10. Conclusion
---------------------------------------------------------------------
The Hotels Extension enables:
• Scalable discovery
• Identity-aware pricing
• Confirmation-ready offer handling
• Async-safe checkout
• Explicit order lifecycle modeling
• Event-driven updates

It formalizes hotel commerce semantics while preserving UCP’s extensibility and neutrality.
Approval of this extension prevents fragmentation and establishes a reusable foundation for multi-merchant hotel interoperability within UCP.