---------------------------------------------------------------------
UCP Hotels Extension

Status: Draft for Governance Review
Version: 3.0

---------------------------------------------------------------------
This directory contains a proposed domain extension to UCP to support lodging (hotel) commerce.

The extension defines interoperable semantics for:

• Discovery (non-binding)
• Identity enrichment
• Confirmation-ready offers
• Optional cart intent
• Checkout execution
• Order lifecycle
• Event publication

The extension is transport-agnostic and merchant-neutral.

---------------------------------------------------------------------
1. Normative Specification
---------------------------------------------------------------------

UCP-Hotels-Extension-Spec.md

Defines required and optional behaviors, state transitions, identity modeling, offer semantics, checkout requirements, and order lifecycle.

This document is the authoritative contract.
---------------------------------------------------------------------
2. Governance Submission Package

UCP-Hotels-Extension-Governance-Package.md

Provides rationale, scope boundaries, compatibility considerations, and review checklist.
---------------------------------------------------------------------
3. Canonical Schemas
---------------------------------------------------------------------

schemas/UCP-Hotels-Canonical-Schemas-V7.json

JSON Schema definitions for:
Discovery entities
IdentityContext
HotelOffer
CartIntent
Checkout
HotelOrder
OrderEvent

Schemas conform to Draft 2020-12.
---------------------------------------------------------------------
4. Example Payloads
---------------------------------------------------------------------

examples/

End-to-end reference flow:

Discovery → Variants → Offer → Cart → Checkout (Async) → OrderEvent

Examples demonstrate correlation propagation, identity enrichment, revalidation semantics, and asynchronous confirmation.
---------------------------------------------------------------------
Architectural Characteristics
---------------------------------------------------------------------

This extension:
Does not modify UCP core primitives
Does not assume specific transport protocols
Does not introduce vendor-specific constructs
Does not mandate cart usage
Does not define payment processing standards
It defines protocol-level hotel commerce semantics only.
---------------------------------------------------------------------
Review Order
---------------------------------------------------------------------
Governance Package
Normative Specification
Schemas
Example Payloads

---------------------------------------------------------------------
Scope Boundaries
---------------------------------------------------------------------
Out of scope:

Payment processing implementation
CRS/PMS internal behavior
Commission models
Loyalty verification mechanisms
OTA-specific business logic

---------------------------------------------------------------------
Objective
---------------------------------------------------------------------
To standardize interoperable hotel commerce semantics within UCP while preserving extensibility and core protocol neutrality.
