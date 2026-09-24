# Booking Capability

Draft - Work in Progress

This capability is in **draft status**. Implementers are cautioned that data models, protocol bindings, and operational flows are under active iteration and may undergo breaking changes as the specification evolves.

- **Capability Name:** `dev.ucp.lodging.booking`

## Overview

The Lodging Booking capability allows Platforms to facilitate and manage end-to-end lodging reservation sessions with Businesses.

The Business remains the Merchant of Record (MoR) and does not need to become PCI DSS compliant to accept card payments through this capability. Unless the AP2 Mandates extension is supported, the booking must be finalized manually by the user through a trusted UI.

### Flow Overview

Booking follows a progressive session lifecycle:

1. **Session Initiation**: The Platform initiates a booking session using property, stay, rate plan, and stay date details discovered from upper-funnel search.
1. **Progressive Enrichment**: The Platform updates the session with guest profiles, stay guest assignments, booker information, and payment details across one or more operations.
1. **Session Completion**: The Platform finalizes the booking to create a confirmed, immutable reservation.

```text
        +------------+                         +---------------------+
        | incomplete |<----------------------->| requires_escalation |
        +-----+------+                         |   (user handoff     |
              |                                |   via continue_url) |
              | all info collected             +----------+----------+
              v                                           |
     +------------------+                                 |
     |ready_for_complete|                                 |
     |                  |                                 |
     | (platform can    |                                 | continue_url
     |  call Complete   |                                 |
     | Booking Session) |                                 |
     +--------+---------+                                 |
              |                                           |
              | Complete Booking                          |
              v                                           |
    +--------------------+                                |
    |complete_in_progress|                                |
    +---------+----------+                                |
              |                                           |
              +-----------------------+-------------------+
                                      v
                                +-------------+
                                |  completed  |
                                +-------------+

                                +-------------+
                                |  canceled   |
                                +-------------+
           (session invalid/expired - can occur from any state)
```

## Key Concepts

- **Compound Stay Binding (`stay`)**: A lodging reservation is composed of one or more stay units. A `stay` is a compound binding linking a physical accommodation type (`accommodation_type`), a commercial rate contract (`rate_plan`), stay dates (`stay_dates`), occupancy requirements (`occupancy`), and guest assignments (`guest_assignments`).
- **Platform-Generated Guest Identifiers (`guest.id`)**: Unlike business-scoped catalog, property, and stay identifiers, guest identifiers are generated, allocated, and managed by the Platform within the Platform's namespace. The Business treats `guest.id` as a stable, opaque reference. Guest identifiers are opaque strings scoped strictly to the individual booking session (e.g., `"gst_01"`, `"gst_02"`). Platforms **MUST NOT** use persistent cross-merchant user tracking identifiers or expose personally identifiable information (PII) within `guest.id`. Businesses **MUST NOT** infer or link identity across distinct booking sessions based on `guest.id`.
  - **Timing**: Platform **SHOULD NOT** send `guests[]` identity fields beyond `id` before the booking reaches `ready_for_complete`, and **SHOULD** send only the fields the business requests via `messages[]`.
- **Guest Pool & Stay Assignment Model**: Guest data is structured into a two-level relational model:
  - **Root Guest Pool (`guests[]`)**: A flat collection of all individual guest profiles associated with the entire reservation.
  - **Stay Assignments (`stays[].guest_assignments[]`)**: Granular mappings associating specific stay units with guests from the root pool via `guest_id` and designating occupancy roles (such as `primary` or `accompanying`).
- **Separation of Booker and Guests**: The data model strictly separates the legal purchaser from the physical accommodation occupants:
  - **`booker`**: The legal contracting party responsible for payment, contact obligations, and reservation ownership.
  - **`guests`**: The individuals who will physically occupy the accommodations. A booker **MAY** also be listed as a guest in the root pool, but the entities remain decoupled to support corporate, proxy, and multi-stay bookings.
- **Provisional Discovery vs. Authoritative Booking**:
  - *Discovery Phase (Provisional)*: Search, quotation, and accommodation lookup responses provide provisional rates, available accommodation types, and policy summaries based on search parameters.
  - *Booking Session (Authoritative)*: Creating a booking session transitions from provisional discovery to an authoritative state. The Business validates real-time inventory availability (or establishes a temporary soft hold per its policy), resolves binding rate rules, enforces accommodation unit capacity bounds, calculates authoritative totals (`totals[]`), and attaches binding cancellation terms (`policies[]`). A confirmed reservation is not created until the session is finalized via Complete Booking Session.

### Pricing Scope

Lodging reservations follow strict all-in pricing rules to comply with consumer protection regulations (such as FTC and EU price transparency directives). In lodging, the full financial commitment for a stay is often divided between charges prepaid at the time of reservation confirmation and charges collected directly by the accommodation property upon check-in or check-out (e.g., resort fees, municipal occupancy taxes, or a remaining stay balance).

#### Pricing Architecture & Scope Guidelines

- **Authoritative Root Total (`totals`)**: The top-level `totals` array represents the binding, authoritative pricing breakdown and aggregate financial commitment for the entire reservation stay across all requested stay units.
- **Stay-Level Total (`stays[].totals`)**: Each entry in `stays[].totals` reflects the total charges for that specific stay unit across the entire stay duration (`stay_dates`, i.e., check-in to check-out), **NOT** a per-night figure.
- **Itemized Subtotals and Nightly Breakdown (`lines`)**: The `lines` array under a total item provides supplementary, itemized clarity:
  - `subtotal` total items **MAY** carry `lines` representing the per-night stay rate breakdown.
  - `tax` total items **MAY** carry `lines` delineating separate tax authorities (e.g., state sales tax vs. local occupancy or tourism tax).
  - `fee` total items **MAY** carry `lines` detailing mandatory charges (e.g., daily resort fees, cleaning fees).
- **Price Transparency and All-Inclusive Cost**: Platforms and Businesses **MUST** ensure that the guest is presented with the complete stay liability before booking confirmation. Hidden fees or undisclosed property charges violate price transparency standards.

#### Payment Timing & Terms (`dev.ucp.common.payment.terms`)

- **Authoritative Stay Liability (`total`)**: In accordance with the core `totals.json` contract, the standard `type: "total"` entry strictly represents the authoritative all-in stay liability for the entire reservation across all requested units. Every booking session **MUST** contain exactly one `total` entry, ensuring that Platforms display the full, transparent cost of the stay upfront in compliance with applicable consumer price-display laws.
- **Pricing Breakdown vs. Payment Timing**: In lodging reservations, pricing breakdown and payment timing are decoupled:
  - `totals[]` defines the **pricing breakdown** (`subtotal`, `fee`, `tax`, and optional `discount`). All non-total entries are price addends that sum to `total` (`sum(non-total entries) == total`).
  - `payment.terms[]` (`dev.ucp.common.payment.terms`) defines the **payment timing** and schedules for moving funds.
- **Schedules and `totals` Alignment**:
  - A payment term is composed of one or more `schedules[]`.
  - The sum of all `schedules[].amount` within the selected term **MUST** equal `totals[].type: "total"` (satisfying the core `common/payment_terms.json` invariant).
  - Schedules with `type: "immediate"` represent payments due upon booking completion.
  - Schedules with `type: "deferred"` represent payments due at a specified future date or event (e.g., balance due upon check-in or a scheduled deposit date indicated in `description` or `due_at`).
  - Schedules with `type: "at_property"` represent payments collected directly by the accommodation property (e.g., local tourist taxes or mandatory resort fees paid upon arrival/departure).
- **Payment Terms & Rate Plans**: In lodging distribution, pay-now savings or prepayment incentives are typically modeled as separate rate plans (e.g., Non-Refundable Advance Purchase vs. Flexible Best Available Rate) rather than alternative payment terms on the same rate plan. When flexible payment terms are offered for a rate plan (such as deposit & balance), the Business provides the applicable schedule breakdown in `payment.terms[]`.

#### Local Tax & Fee Disclosures

When mandatory taxes or fees are collected locally by the lodging property and cannot be remitted at booking, the Business **SHOULD** provide a warning message in `messages[]` with `presentation: "disclosure"` and a `path` pointing directly to the relevant payment schedule (e.g., `$.payment.terms[0].schedules[1]`). This disclosure notice **MUST** state the applicable local rates, exemptions, and payment instructions, complemented by formal policy links in `links[]`.

The following snippets illustrate how `totals[]` is structured alongside payment terms across canonical lodging pricing patterns:

A 3-night Tokyo hotel stay where base room rates (`64,000`) and prepaid service fees (`6,400`) are charged immediately, while mandatory resort fees (`6,000`) and Tokyo Accommodation Tax (`1,200`) are collected at the property. In `totals[]`, non-total addends sum strictly to the total stay cost (`77,600`):

```json
[
  {
    "type": "subtotal",
    "display_text": "Room Rate (3 nights for 1 room, includes 10% consumption tax)",
    "amount": 64000
  },
  {
    "type": "fee",
    "display_text": "Service Fee (10% prepaid)",
    "amount": 6400
  },
  {
    "type": "fee",
    "display_text": "Resort & Facility Amenity Fee (Pay at hotel, ¥2,000/night)",
    "amount": 6000
  },
  {
    "type": "tax",
    "display_text": "Tokyo Accommodation Tax (Pay at hotel, ~¥200/guest/night)",
    "amount": 1200
  },
  {
    "type": "total",
    "display_text": "Total Stay Cost",
    "amount": 77600
  }
]
```

A 3-night stay under a deposit & balance term, with an itemized nightly breakdown in `subtotal.lines`. The upfront deposit covers the 1st night (`40,000`) plus service fee (`3,000`) and initial tax (`4,000`), while the remaining balance (`88,000`) is deferred until check-in. In `totals[]`, all room nights, fees, and taxes sum to the full stay liability (`135,000`):

```json
[
  {
    "type": "subtotal",
    "display_text": "Room Rate (3 nights @ $400)",
    "amount": 120000,
    "lines": [
      {
        "display_text": "Night 1 (Deposit): Sep 1, 2026",
        "amount": 40000
      },
      {
        "display_text": "Night 2: Sep 2, 2026",
        "amount": 40000
      },
      {
        "display_text": "Night 3: Sep 3, 2026",
        "amount": 40000
      }
    ]
  },
  {
    "type": "fee",
    "display_text": "Service Fee",
    "amount": 3000
  },
  {
    "type": "tax",
    "display_text": "State Lodging Tax (10%)",
    "amount": 12000
  },
  {
    "type": "total",
    "display_text": "Total Stay Cost",
    "amount": 135000
  }
]
```

> [!TIP] For complete, end-to-end booking session payloads with stay bindings, lead guest assignments, messages, and payment terms, see [Pricing & Payment Terms Examples](#pricing-examples).

### Payments

Payment handlers are discovered from the business's UCP profile at `/.well-known/ucp`. The handlers define the processing specifications for collecting payment instruments (e.g., Google Pay, Shop Pay). When the user submits payment, the platform populates the `payment.instruments` array with the collected instrument data.

The `payment` object is optional on booking session creation and update operations. At completion (`complete_booking_session`), `payment` is **REQUIRED** to establish the binding payment agreement:

- **Immediate Card Payments**: For immediate charges or upfront card guarantees, `payment.instruments` is populated with the collected instrument data.
- **Payment Terms Confirmation**: Complete confirms the already-selected payment term; it does **not** transmit finalized terms. `selected_term_id` is intentionally omitted on Complete because term selection occurs through Update (`update_booking_session`) which can change pricing and derived state before the session reaches `ready_for_complete`.
- **No Instrument Required**: When no instrument is needed (e.g., deferred or pay-at-property reservations requiring no upfront card guarantee), an empty payment object (`payment: {}`) validates the completion requirement.

### Booking Status Lifecycle

The booking `status` field indicates the current phase of the session and determines what action is required next. The business sets the status; the platform receives messages indicating what's needed to progress.

#### Status Values

- **`incomplete`**: Booking session is missing required information or has issues that need resolution. Platform should inspect `messages` array for context and should attempt to resolve via Update Booking Session.
- **`requires_escalation`**: Booking session requires information that cannot be provided via API, or user input is required. Platform should inspect `messages` to understand what's needed. If any `recoverable` errors exist, resolve those first. Then hand off to user via `continue_url`.
- **`ready_for_complete`**: Booking session has all necessary information (confirmed pricing totals, valid stay dates, payment instrument collected if required, lead guest identification via `booker` or primary guest assignment (`role: "primary"`), and all outstanding gating actions resolved) and platform can finalize programmatically. Platform can call Complete Booking Session.
- **`complete_in_progress`**: Business is processing the Complete Booking request. The response **MUST NOT** contain a `confirmation` field. See [Accepted Completion](http://ucp.dev/draft/specification/shopping/checkout/#accepted-completion) for permitted operations.
- **`completed`**: Booking confirmed successfully.
- **`canceled`**: Booking session is invalid or expired. Platform should start a new booking session if needed.

#### Session Expiry & Inventory Management

- **Ephemeral Session Lifetime (`expires_at`)**: A booking session is an in-flight, pre-confirmation resource. The Business **MAY** provide an `expires_at` timestamp indicating how long the session state, quoted pricing, and any temporary inventory holds remain valid.
- **Inventory Hold Strategies**: Businesses **MAY** place a temporary soft hold on inventory for the duration of `expires_at`, or **MAY** employ optimistic concurrency by verifying inventory availability in real-time on session updates and performing final allocation upon Complete Booking Session.
- **Release Mechanisms**: If the booking flow is abandoned, the Platform **MAY** call Cancel Booking Session to explicitly release any held inventory and session state. Otherwise any held resources are automatically released when `expires_at` elapses.

### Actions

When an active capability or extension has outstanding step-up work for the booking session (such as PSD2 / 3D Secure strong customer authentication, biometric step-up, or identity verification), the Business surfaces instances in the response-only `actions` map. The common rules are defined in [Overview — Actions](http://ucp.dev/draft/specification/overview/#actions); this section states how the booking status lifecycle interprets them.

Every Action gates the effect specified for its Action type. While `incomplete`, an Action may identify work the Business needs completed before it can return `ready_for_complete`. After processing the Action according to its Action type contract (e.g., redirecting buyer via `url_redirect`), the Platform **SHOULD** use Get Booking Session or a subsequent Update Booking Session to obtain the latest booking state.

If an Action prevents Complete Booking Session from being accepted, the Business **MUST** return the current booking session with `status: incomplete` (or `status: requires_escalation` if user handoff is required) and an error Message with `severity: "recoverable"` whose `path` selects that exact Action occurrence.

### Error Handling

The `messages` array contains errors, warnings, and informational messages about the booking state. `ucp.status` is the shape discriminator — `"success"` means the response carries the expected payload, `"error"` means it carries error information instead. The `severity` field on each error message prescribes the recommended action:

| Severity                | Meaning                                          | Platform Action                                                   |
| ----------------------- | ------------------------------------------------ | ----------------------------------------------------------------- |
| `recoverable`           | Platform can resolve by modifying inputs via API | Update resource and retry                                         |
| `requires_buyer_input`  | Business requires input not available via API    | Hand off via `continue_url`                                       |
| `requires_buyer_review` | User review and authorization is required        | Hand off via `continue_url`                                       |
| `unrecoverable`         | No resource exists to act on                     | Retry with new resource or inputs, or hand off via `continue_url` |

Errors with `requires_*` severity contribute to `status: requires_escalation`. Both result in user handoff, but represent different booking session states:

- `requires_buyer_input` means the booking session is **incomplete** — the business requires information their API doesn't support collecting programmatically.
- `requires_buyer_review` means the booking session is **complete** — but policy, regulatory, or entitlement rules require user authorization before completion.

#### Standard Errors

| Code                          | Description                                                              |
| ----------------------------- | ------------------------------------------------------------------------ |
| `inventory_exhausted`         | The selected accommodation unit or inventory hold is no longer available |
| `occupancy_exceeded_capacity` | Number of assigned guests exceeds physical capacity bounds               |
| `payment_failed`              | Payment processing failed                                                |
| `eligibility_invalid`         | Eligibility claim could not be verified at completion                    |

### Warning Presentation

The `presentation` field on warning messages controls the rendering contract the platform **MUST** follow (e.g., `notice` vs. `disclosure`). For the authoritative rendering rules, see [Checkout — Warning Presentation](http://ucp.dev/draft/specification/shopping/checkout/#warning-presentation).

#### Totals Changes

When stay rates, taxes, or mandatory fees fluctuate during an active booking session, the Business returns the updated session with recomputed `totals[]` and **MUST** report the modification using a warning message in `messages[]` with `code: "totals_changed"` and `path: "$.totals"`.

The Business **MUST** set `presentation: "disclosure"` when the revised amount requires prominent Buyer awareness. The Platform **MUST** present the updated totals and the warning content to the buyer, and **MUST NOT** auto-dismiss or hide the disclosure.

## Continue URL

The `continue_url` field enables booking handoff from platform to business UI, allowing the user to continue and finalize the booking session.

### Availability

Businesses **MUST** provide `continue_url` when returning `status` = `requires_escalation`. For all other non-terminal statuses (`incomplete`, `ready_for_complete`, `complete_in_progress`), businesses **SHOULD** provide `continue_url`. For terminal states (`completed`, `canceled`), `continue_url` **SHOULD** be omitted.

## Guidelines

### Platform

- **MUST** supply valid `property.id`, and either a pre-composed `stay.id` OR both `accommodation_type.id` and `rate_plan.id` identifiers sourced from upper-funnel discovery mechanisms when creating a booking session.
- **MUST** present each `stays[]` entry as a unit — `accommodation_type.title`, `rate_plan.title`, `rate_plan.description` (when present), `occupancy`, and the entry's `totals` under the totals rendering contract — and **MUST NOT** merge or de-duplicate entries that share a `accommodation_type` or `rate_plan`.
- **MUST** identify a lead guest by providing `booker` details or designating at least one guest with `role: "primary"` (including full legal name and contact details) prior to invoking Complete Booking Session. A Platform that receives `ready_for_complete` without an identified lead **MUST NOT** call Complete Booking Session, and **SHOULD** correct the session via Update Booking Session or escalate via `continue_url` if available.
- **MUST** generate unique, stable, session-scoped string identifiers in the Platform namespace for each entry in the root `guests[]` array (e.g., `"gst_01"`, `"gst_02"`).
- **MUST** ensure every `guest_assignments[].guest_id` references a valid `id` present in the root `guests[]` pool.
- **SHOULD NOT** send `guests[]` personal identity fields beyond `id` before the booking reaches `ready_for_complete`, and **SHOULD** send only the fields the business requests via `messages[]`.
- **MAY** engage an agent to facilitate the booking session (e.g. select stay, dates, collect guest information). However, the agent must hand over the booking session to a trusted and deterministic UI for the user to review the booking details and complete the booking.
- **MAY** send the user from the trusted, deterministic UI back to the agent at any time.
- **MAY** provide agent context when the platform indicates that the request was done by an agent.
- **MUST** use `continue_url` when booking status is `requires_escalation`.
- **MAY** use `continue_url` to hand off to business UI in other situations.
- When performing handoff, **SHOULD** prefer business-provided `continue_url`.

### Business

- **MUST** evaluate requested `stay.id`, or the compound `accommodation_type.id` and `rate_plan.id` bindings against real-time availability and inventory constraints, echoing authoritative metadata, pricing totals, and policy terms.
- **MUST** make `rate_plan.title` distinguish the rate plan and, together with `rate_plan.description` when present,is sufficient for a Buyer to understand its material commercial terms without having to read into `policies[]`; both fields **MUST NOT** contradict `policies[]`.
- **MUST** preserve platform-supplied `guest.id` identifiers across session updates and responses without remapping, renaming, or mutating them.
- **MUST** validate that all `stays[].guest_assignments[].guest_id` references match an existing entry in the root `guests[]` array.
- **MUST NOT** return a booking session with statuses `ready_for_complete`, `complete_in_progress`, or `completed` without an identified lead - a `booker` with full legal name and a contact channel, a guest in `guests[]` with full legal name and a contact channel who is assigned as `primary` in some `stays[].guest_assignments[]`, or in corporate or proxy bookings, a named primary guest alongside a `booker` providing the contact channel. Additional identity fields a Business needs (such as passport number, nationality, or date of birth) **MUST** be negotiated per Business through `messages[]`.
- **MUST** enforce physical `capacity` limits against the total assigned occupants and guest ages:
  - Guest age is evaluated in completed years as of the stay check-in date.
  - A guest whose age falls within a defined `child_age_ranges[].ages` bracket is classified as a child; any guest whose age falls in no child bracket is classified as an adult.
  - The requested occupancy **MUST** satisfy: `occupancy.adults <= capacity.adults`, `occupancy.children <= capacity.children`, and `occupancy.total <= capacity.total`.
  - For each entry in `child_age_ranges[]` with a `limit`, the number of children whose ages fall in that bracket **MUST NOT** exceed `limit`.
- **MUST** send a confirmation email after the booking has been completed when a valid email address is available in `booker` or primary guest details.
- **SHOULD** provide accurate error and warning messages.
- Logic handling the booking sessions **MUST** be deterministic.
- **MUST** provide `continue_url` when returning `status` = `requires_escalation`.
- **MUST** include at least one message with `severity` of `requires_buyer_input` or `requires_buyer_review` when returning `status` = `requires_escalation`.
- **SHOULD** provide `continue_url` in all non-terminal booking responses.
- After a booking session reaches the state "completed", it is considered immutable.

## Capability Schema Definition

| Name           | Type                                                                         | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ---------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp            | any                                                                          | **Required** | UCP metadata for booking responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| id             | string                                                                       | **Required** | Unique identifier of the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| status         | string                                                                       | **Required** | Booking state indicating the current phase and required action. See Booking Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                           |
| property       | [Property](/draft/specification/reference/#property)                         | **Required** | The physical establishment or geographic location where the lodging is situated (e.g., hotel, resort, villa estate, cabin park).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| stays          | Array\[[Stay Response](/draft/specification/reference/#stay)\]               | **Required** | List of stay line-items for the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| booker         | [Booker](/draft/specification/reference/#booker)                             | Optional     | Representation of the legal contracting party making the reservation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| guests         | Array\[[Guest](/draft/specification/reference/#guest)\]                      | Optional     | List of guest profiles associated with the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| travel_purpose | string                                                                       | Optional     | Purpose of the trip or reservation, supplied by the Platform. Well-known values: `business`, `leisure`. Platforms MAY send additional values; a Business MUST ignore values it does not recognize and treat the purpose as unspecified.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context        | [Context](/draft/specification/reference/#context)                           | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals        | [Signals](/draft/specification/reference/#signals)                           | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| currency       | string                                                                       | **Required** | ISO 4217 currency code reflecting the business's market determination. Derived from address, context, and geo IP—buyers provide signals, businesses determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| totals         | [Totals](/draft/specification/reference/#totals)                             | **Required** | Authoritative pricing breakdown for the booking. The `total` entry represents the authoritative all-in stay liability across all requested units. All non-total entries are price addends that sum to `total`. When payment timing is split across schedules or property-collected charges apply, timing breakdowns are conveyed via payment terms (`payment.terms[]`) schedules rather than within `totals`.                                                                                                                                                                                                                                                           |
| actions        | [Actions](/draft/specification/reference/#actions)                           | Optional     | Outstanding extension-defined Actions for this booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| messages       | Array\[[Message](/draft/specification/reference/#message)\]                  | Optional     | List of messages with error and info about the booking session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| links          | Array\[[Link](/draft/specification/reference/#link)\]                        | **Required** | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies       | Array\[[Policy](/draft/specification/reference/#policy)\]                    | Optional     | Policies (e.g., cancellation terms) that apply to the booking session. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| expires_at     | string                                                                       | Optional     | RFC 3339 timestamp after which the booking session is no longer valid. Indicates how long session state, quoted pricing, and any temporary inventory holds remain valid. Businesses MUST NOT complete a booking at a modified price without first returning updated totals to the platform.                                                                                                                                                                                                                                                                                                                                                                             |
| continue_url   | string                                                                       | Optional     | URL for booking handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| payment        | [Payment](/draft/specification/reference/#payment)                           | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| confirmation   | [Booking Confirmation](/draft/specification/reference/#booking-confirmation) | Optional     | Details about the booking created from this specific session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

## Operations

The Booking capability defines the following logical operations:

| Operation                    | Description                                                                         |
| ---------------------------- | ----------------------------------------------------------------------------------- |
| **Create Booking Session**   | Initiates a new booking session. Called as soon as a user expresses booking intent. |
| **Get Booking Session**      | Retrieves the current state of a booking session.                                   |
| **Update Booking Session**   | Updates a booking session via full resource replacement.                            |
| **Complete Booking Session** | Finalizes the booking and confirms the reservation.                                 |
| **Cancel Booking Session**   | Cancels a booking session.                                                          |

### Create Booking Session

Invoked by the platform when the user expresses booking intent to initiate a session with upper-funnel property, stay, and stay date parameters.

**Inputs**

| Name           | Type                                                    | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| property       | [Property](/draft/specification/reference/#property)    | **Required** | The physical establishment or geographic location where the lodging is situated (e.g., hotel, resort, villa estate, cabin park).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| stays          | Array\[[Stay](/draft/specification/reference/#stay)\]   | **Required** | List of stay line-items for the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| booker         | [Booker](/draft/specification/reference/#booker)        | Optional     | Representation of the legal contracting party making the reservation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| guests         | Array\[[Guest](/draft/specification/reference/#guest)\] | Optional     | List of guest profiles associated with the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| travel_purpose | string                                                  | Optional     | Purpose of the trip or reservation, supplied by the Platform. Well-known values: `business`, `leisure`. Platforms MAY send additional values; a Business MUST ignore values it does not recognize and treat the purpose as unspecified.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context        | [Context](/draft/specification/reference/#context)      | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals        | [Signals](/draft/specification/reference/#signals)      | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| payment        | [Payment](/draft/specification/reference/#payment)      | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

**Output**

This object MUST be one of the following types: [Booking](/draft/specification/lodging/booking/#booking), [Error Response](/draft/specification/reference/#error-response).

### Get Booking Session

Retrieves the latest state of the booking session resource.

**Inputs**

| Name | Type   | Requirement  | Description                                           |
| ---- | ------ | ------------ | ----------------------------------------------------- |
| id   | string | **Required** | The unique identifier of the booking.Defined in path. |

**Output**

This object MUST be one of the following types: [Booking](/draft/specification/lodging/booking/#booking), [Error Response](/draft/specification/reference/#error-response).

### Update Booking Session

Performs a full replacement of the booking session resource. The platform is **REQUIRED** to send the complete booking state containing any data updates (e.g., guest profiles, guest assignments, booker details).

**Inputs**

| Name           | Type                                                    | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id             | string                                                  | **Required** | The unique identifier of the booking.Defined in path.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| property       | [Property](/draft/specification/reference/#property)    | **Required** | The physical establishment or geographic location where the lodging is situated (e.g., hotel, resort, villa estate, cabin park).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| stays          | Array\[[Stay](/draft/specification/reference/#stay)\]   | **Required** | List of stay line-items for the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| booker         | [Booker](/draft/specification/reference/#booker)        | Optional     | Representation of the legal contracting party making the reservation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| guests         | Array\[[Guest](/draft/specification/reference/#guest)\] | Optional     | List of guest profiles associated with the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| travel_purpose | string                                                  | Optional     | Purpose of the trip or reservation, supplied by the Platform. Well-known values: `business`, `leisure`. Platforms MAY send additional values; a Business MUST ignore values it does not recognize and treat the purpose as unspecified.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context        | [Context](/draft/specification/reference/#context)      | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals        | [Signals](/draft/specification/reference/#signals)      | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| payment        | [Payment](/draft/specification/reference/#payment)      | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

**Output**

This object MUST be one of the following types: [Booking](/draft/specification/lodging/booking/#booking), [Error Response](/draft/specification/reference/#error-response).

### Complete Booking Session

Final booking placement call. Invoked when payment has been collected and the user commits to finalize the reservation.

**Inputs**

| Name    | Type                                               | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                             |
| ------- | -------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id      | string                                             | **Required** | The unique identifier of the booking.Defined in path.                                                                                                                                                                                                                                                                                                                                                   |
| signals | [Signals](/draft/specification/reference/#signals) | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace. |
| payment | [Payment](/draft/specification/reference/#payment) | **Required** | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                              |

**Output**

This object MUST be one of the following types: [Booking](/draft/specification/lodging/booking/#booking), [Error Response](/draft/specification/reference/#error-response).

### Cancel Booking Session

Cancels an active booking session prior to completion.

**Inputs**

| Name | Type   | Requirement  | Description                                           |
| ---- | ------ | ------------ | ----------------------------------------------------- |
| id   | string | **Required** | The unique identifier of the booking.Defined in path. |

**Output**

This object MUST be one of the following types: [Booking](/draft/specification/lodging/booking/#booking), [Error Response](/draft/specification/reference/#error-response).

## Transport Bindings

The abstract operations above are bound to specific transport protocols:

- [REST Binding](http://ucp.dev/draft/specification/lodging/booking/rest/index.md): RESTful API mapping using standard HTTP verbs and JSON payloads.
- [MCP Binding](http://ucp.dev/draft/specification/lodging/booking/mcp/index.md): Model Context Protocol mapping for agentic interaction.

## Examples

### Pricing Examples

The following examples provide complete, authoritative booking sessions demonstrating property-collected charges and flexible payment terms integration.

A complete 3-night Tokyo hotel reservation where base room rates and service fees are prepaid immediately, while local Tokyo Accommodation Tax and resort fees are collected directly at check-in. Payment timing is explicitly modeled via `payment.terms[]` under capability `dev.ucp.common.payment.terms`, and the tax disclosure warning in `messages[]` references the property-collected schedule:

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.lodging.booking": [
        {
          "version": "draft"
        }
      ],
      "dev.ucp.common.payment.terms": [
        {
          "version": "draft"
        }
      ]
    },
    "payment_handlers": {
      "com.example.card_handler": [
        {
          "id": "card_handler",
          "version": "draft",
          "available_instruments": [
            {
              "type": "card"
            }
          ]
        }
      ]
    }
  },
  "id": "bks_example_01",
  "status": "incomplete",
  "currency": "JPY",
  "property": {
    "id": "pp_ginza_hotel",
    "name": "Ginza Grand Hotel"
  },
  "stays": [
    {
      "id": "stay_dlx_king_std",
      "accommodation_type": {
        "id": "at_dlx_king",
        "title": "Deluxe King Room"
      },
      "rate_plan": {
        "id": "rp_standard",
        "title": "Standard Flexible Rate"
      },
      "occupancy": {
        "adults": 2,
        "total": 2
      },
      "stay_dates": {
        "start_date": "2026-10-01",
        "end_date": "2026-10-04"
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 64000
        },
        {
          "type": "total",
          "amount": 64000
        }
      ]
    }
  ],
  "totals": [
    {
      "type": "subtotal",
      "display_text": "Room Rate (3 nights for 1 room, includes 10% consumption tax)",
      "amount": 64000
    },
    {
      "type": "fee",
      "display_text": "Service Fee (10% prepaid)",
      "amount": 6400
    },
    {
      "type": "fee",
      "display_text": "Resort & Facility Amenity Fee (Pay at hotel, ¥2,000/night)",
      "amount": 6000
    },
    {
      "type": "tax",
      "display_text": "Tokyo Accommodation Tax (Pay at hotel, ~¥200/guest/night)",
      "amount": 1200
    },
    {
      "type": "total",
      "display_text": "Total Stay Cost",
      "amount": 77600
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "local_tax",
      "path": "$.payment.terms[0].schedules[1]",
      "presentation": "disclosure",
      "content": "**Tokyo Accommodation Tax Notice**: In accordance with Tokyo Metropolitan Government regulations, a local accommodation tax of JPY 200 per guest per night applies to room rates of JPY 15,000 or higher. This tax is collected directly by the property upon check-in.",
      "content_type": "markdown",
      "url": "https://hotel.example.com/policies/tokyo-accommodation-tax"
    }
  ],
  "links": [
    {
      "type": "tax_policy",
      "title": "Tokyo Local Accommodation Tax Schedule",
      "url": "https://hotel.example.com/policies/tokyo-accommodation-tax"
    },
    {
      "type": "terms_of_service",
      "title": "Hotel Booking Terms & Conditions",
      "url": "https://hotel.example.com/terms"
    },
    {
      "type": "refund_policy",
      "title": "Cancellation and Refund Policy",
      "url": "https://hotel.example.com/cancellation-policy"
    }
  ],
  "payment": {
    "selected_term_id": "pt_standard",
    "terms": [
      {
        "id": "pt_standard",
        "title": "Standard Settlement",
        "description": {
          "plain": "Pay room rate and service fee today; mandatory resort fee and Tokyo Accommodation Tax are paid at check-in."
        },
        "schedules": [
          {
            "id": "sched_room",
            "type": "immediate",
            "description": {
              "plain": "Due today when you book (Room rate + service fee)."
            },
            "amount": 70400
          },
          {
            "id": "sched_property",
            "type": "at_property",
            "description": {
              "plain": "Due at check-in on October 1, 2026 (Resort fee + Tokyo Accommodation Tax)."
            },
            "amount": 7200
          }
        ]
      }
    ]
  }
}
```

A complete 3-night hotel reservation offering a deposit and balance payment term (`pt_deposit_balance`). The first night's room rate along with prepaid fees and initial tax are charged immediately, while the remaining 2 nights' room rate and balance tax are deferred until check-in:

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.lodging.booking": [
        {
          "version": "draft"
        }
      ],
      "dev.ucp.common.payment.terms": [
        {
          "version": "draft"
        }
      ]
    },
    "payment_handlers": {
      "com.example.card_handler": [
        {
          "id": "card_handler",
          "version": "draft",
          "available_instruments": [
            {
              "type": "card"
            }
          ]
        }
      ]
    }
  },
  "id": "bks_example_02",
  "status": "incomplete",
  "currency": "USD",
  "property": {
    "id": "pp_grand_hotel",
    "name": "Grand Hotel"
  },
  "stays": [
    {
      "id": "stay_king_std",
      "accommodation_type": {
        "id": "at_king",
        "title": "King Room"
      },
      "rate_plan": {
        "id": "rp_flex",
        "title": "Flexible Rate"
      },
      "occupancy": {
        "adults": 2,
        "total": 2
      },
      "stay_dates": {
        "start_date": "2026-09-01",
        "end_date": "2026-09-04"
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 120000
        },
        {
          "type": "total",
          "amount": 120000
        }
      ]
    }
  ],
  "totals": [
    {
      "type": "subtotal",
      "display_text": "Room Rate (3 nights @ $400)",
      "amount": 120000,
      "lines": [
        {
          "display_text": "Night 1 (Deposit): Sep 1, 2026",
          "amount": 40000
        },
        {
          "display_text": "Night 2: Sep 2, 2026",
          "amount": 40000
        },
        {
          "display_text": "Night 3: Sep 3, 2026",
          "amount": 40000
        }
      ]
    },
    {
      "type": "fee",
      "display_text": "Service Fee (Prepaid)",
      "amount": 3000
    },
    {
      "type": "tax",
      "display_text": "State Lodging Tax (10%)",
      "amount": 12000
    },
    {
      "type": "total",
      "display_text": "Total Stay Cost",
      "amount": 135000
    }
  ],
  "links": [
    {
      "type": "terms_of_service",
      "title": "Terms of Service",
      "url": "https://example.com/tos"
    }
  ],
  "payment": {
    "selected_term_id": "pt_deposit_balance",
    "terms": [
      {
        "id": "pt_deposit_balance",
        "title": "First night now, balance at check-in",
        "description": {
          "plain": "Hold your room with one night's rate plus initial taxes & fees."
        },
        "schedules": [
          {
            "id": "sched_first_night",
            "type": "immediate",
            "description": {
              "plain": "Due today when you book (Deposit: First night + service fee + tax)."
            },
            "amount": 47000
          },
          {
            "id": "sched_balance",
            "type": "deferred",
            "description": {
              "plain": "Due at check-in on September 1, 2026 at 3:00 PM PDT (Remaining 2 nights + remaining tax)."
            },
            "due_at": "2026-09-01T15:00:00-07:00",
            "amount": 88000
          }
        ]
      }
    ]
  }
}
```

## Entities

### Actions

Step-up action directives required to progress the booking session (e.g., 3D Secure / PSD2 buyer redirection or identity verification).

Outstanding extension-defined Action instances, keyed by reverse-domain Action type, not extension name.

### Property

The physical establishment or geographic location where the lodging is situated (e.g., hotel, resort, villa estate, cabin park).

| Name    | Type                                                             | Requirement  | Description                                                                                    |
| ------- | ---------------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------------------------- |
| id      | string                                                           | **Required** | Stable, opaque, Business-scoped Location identifier.                                           |
| name    | string                                                           | **Required** | Buyer-facing, Business-owned display name.                                                     |
| address | [Postal Address](/draft/specification/reference/#postal-address) | Optional     | Physical address of the location.                                                              |
| media   | Array\[[Media](/draft/specification/reference/#media)\]          | Optional     | Property media (images, videos, 3D models). First item is the featured media for presentation. |

### Booking Confirmation

Confirmation and locator details returned upon successful booking completion.

| Name          | Type   | Requirement  | Description                                                                                                                                           |
| ------------- | ------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| id            | string | **Required** | Unique booking identifier.                                                                                                                            |
| label         | string | Optional     | Human-readable label (e.g., confirmation number) for identifying the booking if it differs from the unique id. MUST only be provided by the business. |
| pincode       | string | Optional     | Additional code provided for secure access of the booking. SHOULD be used alongside the unique identifier or confirmation number.                     |
| permalink_url | string | Optional     | Permalink to access the booking directly on business's website.                                                                                       |

### Booker

The legal contracting party and primary point of contact making the reservation.

| Name         | Type                                                             | Requirement | Description                                                                                                          |
| ------------ | ---------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------- |
| first_name   | string                                                           | Optional    | First name of the booker.                                                                                            |
| last_name    | string                                                           | Optional    | Last name of the booker.                                                                                             |
| email        | string                                                           | Optional    | Email address of the booker.                                                                                         |
| phone_number | string                                                           | Optional    | E.164 standard. Phone number of the booker.                                                                          |
| birthdate    | string                                                           | Optional    | Date of birth of the booker in ISO 8601 format.                                                                      |
| company      | string                                                           | Optional    | The booker's company or organization name, used for corporate invoicing.                                             |
| address      | [Postal Address](/draft/specification/reference/#postal-address) | Optional    | Physical or registered address of the booker or company for legal contracting, regulatory compliance, and invoicing. |

### Capacity

Occupancy limits and child age thresholds supported by a physical accommodation type.

| Name             | Type          | Requirement | Description                                                                                                                                             |
| ---------------- | ------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| adults           | integer       | Optional    | Maximum number of adult occupants.                                                                                                                      |
| children         | integer       | Optional    | Maximum number of child occupants.                                                                                                                      |
| child_age_ranges | Array[object] | Optional    | Child age brackets and optional per-bracket capacity limits. A guest whose age falls within a bracket is counted as a child; otherwise as an adult.     |
| total            | integer       | Optional    | Maximum number of total occupants (adult or child). If adults and/or children are present, this MUST be greater than or equal to max(adults, children). |

### Context

Buyer location and market context hints.

| Name            | Type                                                                                | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --------------- | ----------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| address_country | string                                                                              | Optional    | The country, as a 2-letter ISO 3166-1 alpha-2 code (e.g. "US"). A 3-letter alpha-3 code or full country name MAY also be used.                                                                                                                                                                                                                                                                                                                                     |
| address_region  | string                                                                              | Optional    | The first-level administrative region within the country (e.g. a state or province such as California).                                                                                                                                                                                                                                                                                                                                                            |
| postal_code     | string                                                                              | Optional    | The postal code (e.g. "94043").                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| location        | string                                                                              | Optional    | Stable, opaque identifier for a Location in the Business's namespace. This provisional, non-binding hint is distinct from the Buyer's locality. The operation specification or an active capability/extension defines its effects. A common example in retail shopping is the default home store ID selected and saved by the user when purchasing groceries.                                                                                                      |
| intent          | string                                                                              | Optional    | Background context describing buyer's intent (e.g., 'looking for a gift under $50', 'need something durable for outdoor use'). Informs relevance, recommendations, and personalization.                                                                                                                                                                                                                                                                            |
| language        | string                                                                              | Optional    | Preferred language for content. Use IETF BCP 47 language tags (e.g., 'en', 'fr-CA', 'zh-Hans'). For REST, equivalent to Accept-Language header—platforms SHOULD fall back to Accept-Language when this field is absent; when provided, overrides Accept-Language. Businesses MAY return content in a different language if unavailable.                                                                                                                            |
| currency        | string                                                                              | Optional    | Preferred currency (ISO 4217, e.g., 'EUR', 'USD'). Businesses determine presentment currency from context and authoritative signals; this hint MAY inform selection in multi-currency markets. Also serves as the denomination for price filter values — platforms SHOULD include this field when sending price filters. Response prices include explicit currency confirming the resolution.                                                                      |
| eligibility     | Array\[[Reverse Domain Name](/draft/specification/reference/#reverse-domain-name)\] | Optional    | Buyer claims about eligible benefits such as loyalty membership, payment instrument perks, and similar. Recognized claims MAY inform the Business response (e.g., member-only product availability, adjusted pricing in catalog, provisional discounts at cart or checkout). Businesses MUST ignore unrecognized values without error. Values MUST use reverse-domain naming (e.g., 'com.example.loyalty_gold', 'org.school.student') and MUST be non-identifying. |
| payment         | Array[object]                                                                       | Optional    | Buyer-preferred payment handlers in priority order (most preferred first). Each entry names a handler advertised in the Business profile's `ucp.payment_handlers`, optionally narrowed to preferred instrument types. The Business SHOULD use it to preselect or prioritize the handler (and type, when given) and MAY ignore unavailable or ineligible entries; unrecognized values MUST be ignored without error.                                                |

### Date Interval

Check-in (`start_date`) and check-out (`end_date`) date range for the stay.

| Name       | Type   | Requirement  | Description                                                                    |
| ---------- | ------ | ------------ | ------------------------------------------------------------------------------ |
| start_date | string | **Required** | Start date of the interval in ISO 8601 format.                                 |
| end_date   | string | **Required** | End date of the interval in ISO 8601 format. MUST be on or after `start_date`. |

### Guest

Individual guest profile. The `id` is generated and supplied by the Platform to uniquely identify the occupant within the booking session.

| Name         | Type    | Requirement  | Description                                                                                     |
| ------------ | ------- | ------------ | ----------------------------------------------------------------------------------------------- |
| id           | string  | **Required** | Stable, opaque session-scoped identifier for a guest in the Platform's namespace.               |
| first_name   | string  | Optional     | First name of the guest.                                                                        |
| last_name    | string  | Optional     | Last name of the guest.                                                                         |
| email        | string  | Optional     | Email of the guest.                                                                             |
| phone_number | string  | Optional     | E.164 standard. Phone number of the guest.                                                      |
| age          | integer | Optional     | Age of the guest, used to enforce any age-restriction for check-in and accommodation occupancy. |

### Guest Assignment

Relational link mapping a stay unit to an occupant from the root `guests[]` pool via `guest_id` with a designated role.

| Name     | Type   | Requirement  | Description                                                                                                                                                                                                                                                    |
| -------- | ------ | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| guest_id | string | **Required** | Stable, opaque identifier of the assigned guest. MUST be consistent with platform supplied identifiers in the root `guests` pool.                                                                                                                              |
| role     | string | Optional     | Role of the guest in this stay. Well-known values: `primary` (the guest the reservation is attached to), `accompanying` (every other occupant). Platforms MAY send additional values; a Business MUST treat any value it does not recognize as `accompanying`. |

### Link

Compliance and legal links (e.g., Privacy Policy, Terms of Service).

| Name  | Type   | Requirement  | Description                                                                                                                                                                                                                          |
| ----- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| type  | string | **Required** | Type of link. Well-known values: `privacy_policy`, `terms_of_service`, `refund_policy`, `shipping_policy`, `faq`. Consumers SHOULD handle unknown values gracefully by displaying them using the `title` field or omitting the link. |
| url   | string | **Required** | The actual URL pointing to the content to be displayed.                                                                                                                                                                              |
| title | string | Optional     | Optional display text for the link. When provided, use this instead of generating from type.                                                                                                                                         |

### Message Error

| Name         | Type                                                     | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------ | -------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                   | **Required** | **Constant = error**. Message type discriminator.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| code         | [Error Code](/draft/specification/reference/#error-code) | **Required** | Error code identifying the type of error. Standard errors are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| path         | string                                                   | Optional     | RFC 9535 JSONPath to the component the message refers to (e.g., $.line_items[0]).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| content_type | string                                                   | Optional     | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| content      | string                                                   | **Required** | Human-readable message.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| severity     | string                                                   | **Required** | Reflects the resource state and recommended action. 'recoverable': platform can resolve the condition in band, for example by modifying inputs or processing a related Action, and submit a new operation when needed. 'requires_buyer_input': merchant requires information their API doesn't support collecting programmatically (checkout incomplete). 'requires_buyer_review': buyer must authorize before order placement due to policy, regulatory, or entitlement rules. 'unrecoverable': no valid resource exists to act on, retry with new resource or inputs. Errors with 'requires\_*' severity contribute to 'status: requires_escalation'.* *Enum:*\* `recoverable`, `requires_buyer_input`, `requires_buyer_review`, `unrecoverable` |

### Message Info

| Name         | Type                                                   | Requirement  | Description                                                                                                                                                                                    |
| ------------ | ------------------------------------------------------ | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                 | **Required** | **Constant = info**. Message type discriminator.                                                                                                                                               |
| path         | string                                                 | Optional     | RFC 9535 JSONPath to the component the message refers to (e.g., $.line_items[0]).                                                                                                              |
| code         | [Info Code](/draft/specification/reference/#info-code) | Optional     | Info code identifying the type of informational message. Standard codes are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted. |
| content_type | string                                                 | Optional     | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                 |
| content      | string                                                 | **Required** | Human-readable message.                                                                                                                                                                        |

### Message Warning

| Name         | Type                                                         | Requirement  | Description                                                                                                                                                                                                                                         |
| ------------ | ------------------------------------------------------------ | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                       | **Required** | **Constant = warning**. Message type discriminator.                                                                                                                                                                                                 |
| path         | string                                                       | Optional     | RFC 9535 JSONPath to the component the message refers to (e.g., $.line_items[0]).                                                                                                                                                                   |
| code         | [Warning Code](/draft/specification/reference/#warning-code) | **Required** | Warning code identifying the type of warning. Standard codes are defined in capability specifications (see examples) and have standardized semantics; freeform codes are permitted.                                                                 |
| content      | string                                                       | **Required** | Human-readable warning message that MUST be displayed.                                                                                                                                                                                              |
| content_type | string                                                       | Optional     | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                      |
| presentation | string                                                       | Optional     | Rendering contract for this warning. 'notice' (default): platform MUST display, MAY dismiss. 'disclosure': platform MUST display in proximity to the path-referenced component, MUST NOT hide or auto-dismiss. See specification for full contract. |
| image_url    | string                                                       | Optional     | URL to a required visual element (e.g., warning symbol, energy class label).                                                                                                                                                                        |
| url          | string                                                       | Optional     | Reference URL for more information (e.g., regulatory site, registry entry, policy page).                                                                                                                                                            |

### Occupancy

Requested adult and child guest count breakdown for a stay.

| Name       | Type           | Requirement  | Description                                                                                                                             |
| ---------- | -------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| adults     | integer        | Optional     | Number of adults occupying the accommodation unit.                                                                                      |
| children   | integer        | Optional     | Number of children occupying the accommodation unit.                                                                                    |
| child_ages | Array[integer] | Optional     | Ages of children occupying the accommodation unit. If present length(child_ages) MUST equal children.                                   |
| total      | integer        | **Required** | Total number of occupants in the accommodation unit. If adults and/or children fields are specified, this MUST equal adults + children. |

### Payment

Payment details and collected payment instruments.

| Name        | Type                                                                                                                                      | Requirement | Description                                                                                                                                                                                                                |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| instruments | Array\[[Payment Instrument Selected Payment Instrument](/draft/specification/reference/#payment-instrument-selected-payment-instrument)\] | Optional    | The payment instruments available for this payment. Each instrument is associated with a specific handler via the handler_id field. Handlers can extend the base payment_instrument schema to add handler-specific fields. |

### Policy

Policies (cancellation terms, house rules, and the like) that apply to the booking session or stays. JSONPath targets in `applies_to` are relative to this response root (e.g., `$.stays[0]`). See [Policies](http://ucp.dev/draft/specification/overview/#policies) for the full model.

| Name        | Type                                                                       | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ----------- | -------------------------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type        | [Reverse Domain Name](/draft/specification/reference/#reverse-domain-name) | **Required** | Policy type discriminator. Open reverse-DNS vocabulary. See specification documentation for the registry of well-known policy types. Businesses MAY define custom types in their own domain (e.g., `com.example.policy.price_match`). Platforms MUST tolerate unknown values.                                                                                                                                                                                                                                                                                                                                                                                                      |
| description | [Description](/draft/specification/reference/#description)                 | **Required** | Human-readable policy summary in one or more formats (plain, markdown, html). Required on every policy so a platform can present it without understanding any type-specific fields. This is not the buyer-facing disclosure — display is compelled by a `messages[]` warning (see the Policies section).                                                                                                                                                                                                                                                                                                                                                                           |
| applies_to  | Array[string]                                                              | Optional     | RFC 9535 JSONPath expressions identifying the nodes this policy applies to, relative to the embedding response root (e.g., `$.line_items[0]` in cart/checkout, `$.products[2]` in catalog). Each target covers the node it names and everything nested under it, so a target on a product also covers its variants. A singular query (RFC 9535 Section 2.3.5.1; name and index selectors only) names a single node; filters, wildcards, and slices match a set. When omitted, the policy applies to the entire response. When policies of the same `type` contest a node, the narrowest target wins and overrides the rest. See the Policies section for how specificity resolves. |
| url         | string                                                                     | Optional     | Optional link to the full policy document.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

### Rate Plan

Commercial rate plan contract, cancellation policy rules, and rate inclusions. The `id` is discovered from upper-funnel search.

| Name        | Type   | Requirement  | Description                            |
| ----------- | ------ | ------------ | -------------------------------------- |
| id          | string | **Required** | Unique identifier of the rate plan.    |
| title       | string | **Required** | Human-readable name of the rate plan.  |
| description | string | Optional     | Detailed description of the rate plan. |

### Stay

Compound binding uniting physical accommodation real estate (`accommodation_type.id`), commercial rate terms (`rate_plan.id`), stay dates (`stay_dates`), occupancy, and guest assignments.

| Name               | Type                                                                          | Requirement  | Description                                                                                         |
| ------------------ | ----------------------------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------- |
| id                 | string                                                                        | **Required** | Stable, opaque unique identifier of the stay binding.                                               |
| stay_dates         | [Date Interval](/draft/specification/reference/#date-interval)                | **Required** | Stay duration (check-in and check-out dates) for this unit based on the local time of the property. |
| accommodation_type | [Accommodation Type](/draft/specification/reference/#accommodation-type)      | **Required** | Category or specification of the rentable physical space (e.g. room, apartment, villa, campsite).   |
| rate_plan          | [Rate Plan](/draft/specification/reference/#rate-plan)                        | **Required** | Commercial rate policy contract.                                                                    |
| occupancy          | [Occupancy](/draft/specification/reference/#occupancy)                        | Optional     | Occupancy breakdown and guest count for this stay.                                                  |
| guest_assignments  | Array\[[Guest Assignment](/draft/specification/reference/#guest-assignment)\] | Optional     | List of guest assignments for this stay.                                                            |
| totals             | [Totals](/draft/specification/reference/#totals)                              | **Required** | Totals breakdown for this stay.                                                                     |

### Accommodation Type

Category or specification of the rentable physical space (e.g., room, apartment, villa, campsite pitch) and capacity limits.

| Name        | Type                                                    | Requirement  | Description                                                                                              |
| ----------- | ------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------- |
| id          | string                                                  | **Required** | Unique identifier of the accommodation type.                                                             |
| title       | string                                                  | **Required** | Human-readable title of the accommodation type.                                                          |
| description | string                                                  | Optional     | Detailed description of the accommodation type.                                                          |
| capacity    | [Capacity](/draft/specification/reference/#capacity)    | Optional     | Capacity details of the accommodation type.                                                              |
| media       | Array\[[Media](/draft/specification/reference/#media)\] | Optional     | Accommodation type media (images, videos, 3D models). First item is the featured media for presentation. |

### Signals

Platform-supplied fraud and security context.

| Name               | Type   | Requirement | Description                                    |
| ------------------ | ------ | ----------- | ---------------------------------------------- |
| dev.ucp.buyer_ip   | string | Optional    | Client's IP address (IPv4 or IPv6).            |
| dev.ucp.user_agent | string | Optional    | Client's HTTP User-Agent header or equivalent. |

### Total

Authoritative itemized price components and aggregate booking total.

| Name         | Type                                                           | Requirement  | Description                                                                                                                                                                                                                                                                                 |
| ------------ | -------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                         | **Required** | Cost category. Well-known values: subtotal, items_discount, discount, fulfillment, tax, fee, total. Businesses MAY use additional values.                                                                                                                                                   |
| display_text | string                                                         | Optional     | Text to display against the amount. Should reflect appropriate method (e.g., 'Shipping', 'Delivery').                                                                                                                                                                                       |
| amount       | [Signed Amount](/draft/specification/reference/#signed-amount) | **Required** | Monetary amount in the currency's minor unit as defined by ISO 4217. Refer to the currency's exponent to determine minor-to-major ratio (e.g., 2 for USD, 0 for JPY, 3 for KWD). May be negative — the sign is intrinsic to the value (e.g., discounts are negative, charges are positive). |
