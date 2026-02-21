# UCP-Hotels Extension Specification (Normative)  
Status: Draft – Governance Review Version  
Version: 2026-02-15  

---------------------------------------------------------------------
1. PURPOSE
---------------------------------------------------------------------
Hotels require a dedicated UCP extension because lodging commerce differs structurally from catalog-based retail and single-leg travel products. Hotel booking involves multi-dimensional identity context, time-bound inventory, conditional pricing, asynchronous confirmation, and post-booking lifecycle complexity that cannot be cleanly modeled using generic commerce primitives alone.

This extension formalizes those domain requirements while remaining fully aligned with UCP’s transport-agnostic, merchant-neutral design principles.

This extension standardizes hotel discovery, pricing, booking, and lifecycle servicing within UCP while remaining:

• Merchant-neutral
• Platform-neutral
• CRS/PMS-neutral
• Agent-runtime neutral
• Transport agnostic (HTTP, MCP, A2A)

This extension feeds into UCP Checkout and UCP Order capabilities. A dedicated extension enables explicit modeling of these dimensions without overloading generic Offer primitives.

---------------------------------------------------------------------
2. FLOW (NORMATIVE SEQUENCE)
---------------------------------------------------------------------

1. Product Discovery (pricing-agnostic, cacheable)
2. Early Identity Context (optional, influences ranking)
3. Variant Selection (room identity only)
4. Identity Confirmation (if needed before pricing)
5. Offer / Quotation (confirmation-ready)
6. CartIntent (optional)
7. Checkout (execution boundary + mandatory revalidation)
8. Order lifecycle (system-of-record)

---------------------------------------------------------------------
3. IDENTITY INFLUENCE ON DISCOVERY (NEW – CLOSED GAP)
---------------------------------------------------------------------

Discovery MAY accept identity_context_reference.

Discovery MUST:
• Work without identity.
• Not block anonymous exploration.

Discovery MAY:
• Adapt ranking based on loyalty tier or corporate contract.
• Surface eligibility hints at property or variant level.
• Adjust indicative availability signals based on eligibility.

Discovery MUST NOT:
• Require identity for property listing visibility.

---------------------------------------------------------------------
4. LEAD / INDICATIVE PRICE SEMANTICS (NEW – CLOSED GAP)
---------------------------------------------------------------------

If indicative_price is provided:

It MUST:
• Be labeled type = "INDICATIVE"
• Be marked non_binding = true
• Include valid_until
• Represent the lowest eligible public rate for provided dates and occupancy
• Clarify currency source and conversion basis if converted

It MUST NOT:
• Be treated as confirmation-ready
• Imply inventory reservation

Indicative pricing TTL SHOULD NOT exceed 24 hours.

---------------------------------------------------------------------
5. VARIANT-LEVEL ELIGIBILITY SIGNALING (NEW – CLOSED GAP)
---------------------------------------------------------------------

HotelVariant MAY include:

eligibility_signals: [
  {
    type: "LOYALTY_REQUIRED" | "CORPORATE_RATE_AVAILABLE" | "MEMBER_DISCOUNT_AVAILABLE",
    program_id: string (optional),
    description: string (optional)
  }
]

This allows agents to reason about eligibility prior to invoking pricing.

---------------------------------------------------------------------
6. OFFER / QUOTATION REQUIREMENTS
---------------------------------------------------------------------

Offer MUST include:
• offer_id (ephemeral)
• property_id
• variant_id
• stay window
• occupancy
• full pricing breakdown
• cancellation structure
• payment requirements
• offer_valid_until
• requires_reprice_before_checkout

Offer MUST be confirmation-ready.

Offer MUST NOT imply booking commitment.

---------------------------------------------------------------------
7. CHECKOUT REVALIDATION (NEW – CLOSED GAP)
---------------------------------------------------------------------

Before booking confirmation:

Business MUST:
• Revalidate price and availability at checkout completion.
• Return price_changed if discrepancy exists.
• Return not_available if inventory unavailable.
• Provide updated offer if applicable.

Platform MUST:
• Handle reprice scenario before completion.
• Respect idempotency for Complete Checkout.

Checkout remains the execution boundary.

---------------------------------------------------------------------
8. ASYNC CONFIRMATION CONTRACT (NEW – CLOSED GAP)
---------------------------------------------------------------------

If booking confirmation is asynchronous:

Order state MUST support:
• PENDING
• CONFIRMED
• FAILED

Business MUST:
• Provide confirmation SLA guidance (e.g., expected response window).
• Publish event or status update within reasonable operational timeframe.
• Ensure Complete Checkout remains idempotent.

Platform MUST:
• Support polling or event subscription for Order status changes.

---------------------------------------------------------------------
9. CART INTENT (OPTIONAL CAPABILITY)
---------------------------------------------------------------------

CartIntent:
• Stabilizes user intent.
• Is not an inventory hold.
• MUST expire via expires_at.
• MUST trigger reprice if expired.

Cart is optional. Direct Offer → Checkout MUST be supported.

---------------------------------------------------------------------
10. MERCHANT MODEL CLARIFICATION (NEW – CLOSED GAP)
---------------------------------------------------------------------

The following models are permitted:

1. Single-property merchant
2. Multi-property chain merchant
3. Aggregator merchant representing multiple hotels

Merchant registration MUST:
• Expose a UCP Business Profile
• Declare payment handler support
• Declare identity linking support if applicable

Property-level identity MUST map to merchant-level UCP capability.

---------------------------------------------------------------------
11. MCP / A2A COMPATIBILITY (NEW – CLOSED GAP)
---------------------------------------------------------------------

This extension MUST be transport-agnostic.

When using MCP:
• Correlation IDs MUST propagate end-to-end.
• Offer IDs MUST remain opaque tokens.
• State transitions MUST be idempotent.

When using A2A:
• Offer and Checkout requests MUST preserve identity context tokens.
• Event delivery MUST support asynchronous updates.

---------------------------------------------------------------------
12. DATA FRESHNESS GOVERNANCE (NEW – CLOSED GAP)
---------------------------------------------------------------------

Property discovery data MUST include:
• last_updated timestamp

Recommended:
• TTL guidance not exceeding 48 hours for static metadata
• Versioned catalog refresh via date-based schema versioning

---------------------------------------------------------------------
13. MULTI-ROOM SUPPORT (NEW)
---------------------------------------------------------------------

Offer MAY represent multiple rooms.

If multi-room:
• Offer MUST include quantity field.
• Cancellation and pricing breakdown MUST apply per room and total.

---------------------------------------------------------------------
14. ERROR TAXONOMY
---------------------------------------------------------------------

Standardized codes:

invalid_input  
not_available  
offer_expired  
price_changed  
identity_required  
identity_not_verified  
rate_not_eligible  
payment_failed  
supplier_timeout  
duplicate_request  

Each MUST indicate:
• severity
• retryable flag
• requires_user_action flag
 