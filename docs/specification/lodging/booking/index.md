<!--
   Copyright 2026 UCP Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
-->

# Booking Capability

* **Capability Name:** `dev.ucp.lodging.booking`

## Overview

The Lodging Booking capability allows Platforms to facilitate and manage end-to-end
lodging reservation sessions with Businesses.

The Business remains the Merchant of Record (MoR) and does not need to become
PCI DSS compliant to accept card payments through this capability. Unless the
AP2 Mandates extension is supported, the booking must be finalized manually
by the user through a trusted UI.

### Flow Overview

Booking follows a progressive session lifecycle:

1. **Session Initiation**: The Platform initiates a booking session using property,
   stay, rate plan, and stay date details discovered from upper-funnel search.
2. **Progressive Enrichment**: The Platform updates the session with guest
   profiles, stay guest assignments, booker information, and payment details across
   one or more operations.
3. **Session Completion**: The Platform finalizes the booking to create a
   confirmed, immutable reservation.

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

* **Compound Stay Binding (`stay`)**: A lodging reservation is composed
  of one or more stay units. A `stay` is a compound binding linking
  a physical accommodation type (`accommodation_type`), a commercial rate contract
  (`rate_plan`), stay dates (`stay_dates`), occupancy requirements (`occupancy`), and guest
  assignments (`guest_assignments`).
* **Platform-Generated Guest Identifiers (`guest.id`)**: Unlike business-scoped
  catalog, property, and stay identifiers, guest identifiers are generated, allocated, and
  managed by the Platform within the Platform's namespace. The Business treats
  `guest.id` as a stable, opaque reference. Guest identifiers are opaque strings
  scoped strictly to the individual booking session (e.g., `"gst_01"`, `"gst_02"`).
  Platforms **MUST NOT** use persistent cross-merchant user tracking identifiers or
  expose personally identifiable information (PII) within `guest.id`. Businesses
  **MUST NOT** infer or link identity across distinct booking sessions based on `guest.id`.
    * **Timing**: Platform **SHOULD NOT** send `guests[]` identity fields beyond `id` before the
      booking reaches `ready_for_complete`, and **SHOULD** send only the fields the business
      requests via `messages[]`.
* **Guest Pool & Stay Assignment Model**: Guest data is structured into a
  two-level relational model:
    * **Root Guest Pool (`guests[]`)**: A flat collection of all individual guest
      profiles associated with the entire reservation.
    * **Stay Assignments (`stays[].guest_assignments[]`)**: Granular mappings
      associating specific stay units with guests from the root pool via
      `guest_id` and designating occupancy roles (such as `primary` or
      `accompanying`).
* **Separation of Booker and Guests**: The data model strictly separates the
  legal purchaser from the physical accommodation occupants:
    * **`booker`**: The legal contracting party responsible for payment, contact
      obligations, and reservation ownership.
    * **`guests`**: The individuals who will physically occupy the accommodations.
      A booker **MAY** also be listed as a guest in the root pool, but the entities
      remain decoupled to support corporate, proxy, and multi-stay bookings.
* **Provisional Discovery vs. Authoritative Booking**:
    * *Discovery Phase (Provisional)*: Search, quotation, and accommodation lookup
      responses provide provisional rates, available accommodation types, and policy
      summaries based on search parameters.
    * *Booking Session (Authoritative)*: Creating a booking session transitions
      from provisional discovery to an authoritative state. The Business validates
      real-time inventory availability (or establishes a temporary soft hold per its
      policy), resolves binding rate rules, enforces accommodation unit
      capacity bounds, calculates authoritative totals (`totals[]`), and attaches
      binding cancellation terms (`policies[]`). A confirmed reservation is not created
      until the session is finalized via Complete Booking Session.

### Pricing Scope

Lodging reservations follow strict all-in pricing rules to comply with consumer protection regulations
(such as FTC and EU price transparency directives). In lodging, the full financial commitment for a stay
is often divided between charges prepaid at the time of reservation confirmation and charges collected
directly by the accommodation property upon check-in or check-out (e.g., resort fees, municipal
occupancy taxes, or a remaining stay balance).

#### Pricing Architecture & Scope Guidelines

* **Authoritative Root Total (`totals`)**: The top-level `totals` array represents the binding,
  authoritative pricing breakdown and aggregate financial commitment for the entire reservation
  stay across all requested stay units.
* **Stay-Level Total (`stays[].totals`)**: Each entry in `stays[].totals`
  reflects the total charges for that specific stay unit across the entire stay
  duration (`stay_dates`, i.e., check-in to check-out), **NOT** a per-night figure.
* **Itemized Subtotals and Nightly Breakdown (`lines`)**: The `lines` array under a total item
  provides supplementary, itemized clarity:
    * `subtotal` total items **MAY** carry `lines` representing the per-night stay rate breakdown.
    * `tax` total items **MAY** carry `lines` delineating separate tax authorities (e.g., state
      sales tax vs. local occupancy or tourism tax).
    * `fee` total items **MAY** carry `lines` detailing mandatory charges (e.g., daily resort
      fees, cleaning fees).
* **Price Transparency and All-Inclusive Cost**: Platforms and Businesses **MUST** ensure that
  the guest is presented with the complete stay liability before booking confirmation. Hidden
  fees or undisclosed property charges violate price transparency standards.

#### Payment Timing & Terms (`dev.ucp.common.payment.terms`)

* **Authoritative Stay Liability (`total`)**: In accordance with the core `totals.json`
  contract, the standard `type: "total"` entry strictly represents the authoritative all-in stay liability
  for the entire reservation across all requested units. Every booking session **MUST** contain exactly one
  `total` entry, ensuring that Platforms display the full, transparent cost of the stay upfront in compliance
  with applicable consumer price-display laws.
* **Pricing Breakdown vs. Payment Timing**: In lodging reservations, pricing breakdown and payment timing
  are decoupled:
    * `totals[]` defines the **pricing breakdown** (`subtotal`, `fee`, `tax`, and optional `discount`).
      All non-total entries are price addends that sum to `total` (`sum(non-total entries) == total`).
    * `payment.terms[]` (`dev.ucp.common.payment.terms`) defines the **payment timing** and schedules
      for moving funds.
* **Schedules and `totals` Alignment**:
    * A payment term is composed of one or more `schedules[]`.
    * The sum of all `schedules[].amount` within a term **MUST** equal `totals[].type: "total"`
      (satisfying the core `common/payment_terms.json` invariant).
    * Schedules with `type: "immediate"` represent payments due upon booking completion.
    * Schedules with `type: "deferred"` represent payments due at a specified future date or
      event (e.g., balance due upon check-in or a scheduled deposit date indicated in `description` or `due_at`).
    * Schedules with `type: "at_property"` represent payments collected directly by the accommodation property
      (e.g., local tourist taxes or mandatory resort fees paid upon arrival/departure).
* **Payment Terms & Rate Plans**: In lodging distribution, pay-now savings or prepayment incentives are
  typically modeled as separate rate plans (e.g., Non-Refundable Advance Purchase vs. Flexible Best Available Rate)
  rather than alternative payment terms on the same rate plan. When flexible payment terms are offered for a rate plan
  (such as deposit & balance), the Business provides the applicable schedule breakdown in `payment.terms[]`.

#### Local Tax & Fee Disclosures

When mandatory taxes or fees are collected locally by the lodging property and cannot be
remitted at booking, the Business **SHOULD** provide a warning message in `messages[]` with
`presentation: "disclosure"` and a `path` pointing directly to the relevant payment schedule
(e.g., `$.payment.terms[0].schedules[1]`). This disclosure notice **MUST** state the applicable local rates,
exemptions, and payment instructions, complemented by formal policy links in `links[]`.

The following snippets illustrate how `totals[]` is structured alongside payment terms across canonical lodging pricing patterns:

=== "Pattern 1: Property-Collected Charges"

    A 3-night Tokyo hotel stay where base room rates (`64,000`) and prepaid service fees (`6,400`) are charged immediately, while mandatory resort fees (`6,000`) and Tokyo Accommodation Tax (`1,200`) are collected at the property. In `totals[]`, non-total addends sum strictly to the total stay cost (`77,600`):

    <!-- ucp:example schema=lodging/booking target=$.totals op=read -->
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

=== "Pattern 2: Deposit & Check-in Balance"

    A 3-night stay under a deposit & balance term, with an itemized nightly breakdown in `subtotal.lines`. The upfront deposit covers the 1st night (`40,000`) plus service fee (`3,000`) and initial tax (`4,000`), while the remaining balance (`88,000`) is deferred until check-in. In `totals[]`, all room nights, fees, and taxes sum to the full stay liability (`135,000`):

    <!-- ucp:example schema=lodging/booking target=$.totals op=read -->
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

> [!TIP]
> For complete, end-to-end booking session payloads with stay bindings, lead guest assignments,
> messages, and payment terms, see [Pricing & Payment Terms Examples](#pricing-examples).

### Payments

Payment handlers are discovered from the business's UCP profile at
`/.well-known/ucp`. The handlers define the processing specifications for
collecting payment instruments (e.g., Google Pay, Shop Pay). When the user
submits payment, the platform populates the `payment.instruments` array with the
collected instrument data.

The `payment` object is optional on booking session creation and update operations.
At completion (`complete_booking_session`), `payment` is **REQUIRED** to establish the binding
payment agreement. For immediate card payments, `payment.instruments` is populated; for deferred
or pay-at-property reservations, `payment` conveys the finalized terms (e.g., via the Payment
Terms extension) and `instruments` may be omitted if no upfront card guarantee is required.

### Booking Status Lifecycle

The booking `status` field indicates the current phase of the session and
determines what action is required next. The business sets the status; the
platform receives messages indicating what's needed to progress.

#### Status Values

* **`incomplete`**: Booking session is missing required information or has
    issues that need resolution. Platform should inspect `messages` array for
    context and should attempt to resolve via Update Booking Session.
* **`requires_escalation`**: Booking session requires information that
    cannot be provided via API, or user input is required. Platform should
    inspect `messages` to understand what's needed. If any `recoverable` errors
    exist, resolve those first. Then hand off to user via `continue_url`.
* **`ready_for_complete`**: Booking session has all necessary information
    (confirmed pricing totals, valid stay dates, payment instrument
    collected if required, lead guest identification via `booker` or
    primary guest assignment (`role: "primary"`), and all outstanding gating
    actions resolved) and platform
    can finalize programmatically. Platform can call Complete Booking Session.
* **`complete_in_progress`**: Business is processing the Complete Booking
    request. The response **MUST NOT** contain a `confirmation` field.
    See [Accepted Completion](../../shopping/checkout/index.md#accepted-completion)
    for permitted operations.
* **`completed`**: Booking confirmed successfully.
* **`canceled`**: Booking session is invalid or expired. Platform should
    start a new booking session if needed.

#### Session Expiry & Inventory Management

* **Ephemeral Session Lifetime (`expires_at`)**: A booking session is an in-flight,
  pre-confirmation resource. The Business **MAY** provide an `expires_at` timestamp
  indicating how long the session state, quoted pricing, and any temporary inventory
  holds remain valid.
* **Inventory Hold Strategies**: Businesses **MAY** place a temporary soft hold on inventory
  for the duration of `expires_at`, or **MAY** employ optimistic concurrency by
  verifying inventory availability in real-time on session updates and performing final allocation
  upon Complete Booking Session.
* **Release Mechanisms**: If the booking flow is abandoned, the Platform **MAY**
  call Cancel Booking Session to explicitly release any held inventory and session state.
  Otherwise any held resources are automatically released when `expires_at` elapses.

### Actions

When an active capability or extension has outstanding step-up work for the
booking session (such as PSD2 / 3D Secure strong customer authentication,
biometric step-up, or identity verification), the Business surfaces instances in
the response-only `actions` map. The common rules are defined in
[Overview — Actions](../../overview/index.md#actions); this section states how
the booking status lifecycle interprets them.

Every Action gates the effect specified for its Action type. While `incomplete`,
an Action may identify work the Business needs completed before it can return
`ready_for_complete`. After processing the Action according to its Action type
contract (e.g., redirecting buyer via `url_redirect`), the Platform **SHOULD** use
Get Booking Session or a subsequent Update Booking Session to obtain the latest
booking state.

If an Action prevents Complete Booking Session from being accepted, the Business
**MUST** return the current booking session with `status: incomplete` (or
`status: requires_escalation` if user handoff is required) and an error Message
with `severity: "recoverable"` whose `path` selects that exact Action occurrence.

### Error Handling

The `messages` array contains errors, warnings, and informational messages
about the booking state. `ucp.status` is the shape discriminator —
`"success"` means the response carries the expected payload, `"error"`
means it carries error information instead. The `severity` field on each
error message prescribes the recommended action:

| Severity                | Meaning                                          | Platform Action                                                   |
| :---------------------- | :----------------------------------------------- | :---------------------------------------------------------------- |
| `recoverable`           | Platform can resolve by modifying inputs via API | Update resource and retry                                         |
| `requires_buyer_input`  | Business requires input not available via API    | Hand off via `continue_url`                                       |
| `requires_buyer_review` | User review and authorization is required        | Hand off via `continue_url`                                       |
| `unrecoverable`         | No resource exists to act on                     | Retry with new resource or inputs, or hand off via `continue_url` |

Errors with `requires_*` severity contribute to `status: requires_escalation`.
Both result in user handoff, but represent different booking session states:

* `requires_buyer_input` means the booking session is **incomplete** — the business
  requires information their API doesn't support collecting programmatically.
* `requires_buyer_review` means the booking session is **complete** — but policy,
  regulatory, or entitlement rules require user authorization before completion.

#### Standard Errors

| Code                          | Description                                                              |
| :---------------------------- | :----------------------------------------------------------------------- |
| `inventory_exhausted`         | The selected accommodation unit or inventory hold is no longer available |
| `occupancy_exceeded_capacity` | Number of assigned guests exceeds physical capacity bounds               |
| `payment_failed`              | Payment processing failed                                                |
| `eligibility_invalid`         | Eligibility claim could not be verified at completion                    |

### Warning Presentation

The `presentation` field on warning messages controls the rendering contract the
platform **MUST** follow (e.g., `notice` vs. `disclosure`). For the authoritative
rendering rules, see [Checkout — Warning Presentation](../../shopping/checkout/index.md#warning-presentation).

#### Totals Changes

When stay rates, taxes, or mandatory fees fluctuate during an active booking
session, the Business returns the updated session with recomputed `totals[]` and
**MUST** report the modification using a warning message in `messages[]` with
`code: "totals_changed"` and `path: "$.totals"`.

The Business **MUST** set `presentation: "disclosure"` when the revised amount
requires prominent Buyer awareness. The Platform **MUST** present the updated
totals and the warning content to the buyer, and **MUST NOT** auto-dismiss or hide
the disclosure.

## Continue URL

The `continue_url` field enables booking handoff from platform to business UI,
allowing the user to continue and finalize the booking session.

### Availability

Businesses **MUST** provide `continue_url` when returning `status` =
`requires_escalation`. For all other non-terminal statuses (`incomplete`,
`ready_for_complete`, `complete_in_progress`), businesses **SHOULD** provide
`continue_url`. For terminal states (`completed`, `canceled`), `continue_url`
**SHOULD** be omitted.

## Guidelines

### Platform

* **MUST** supply valid `property.id`, and either a pre-composed `stay.id`
  OR both `accommodation_type.id` and `rate_plan.id` identifiers sourced from upper-funnel
  discovery mechanisms when creating a booking session.
* **MUST** present each `stays[]` entry as a unit — `accommodation_type.title`,
  `rate_plan.title`, `rate_plan.description` (when present), `occupancy`, and the
  entry's `totals` under the totals rendering contract — and **MUST NOT** merge or
  de-duplicate entries that share a `accommodation_type` or `rate_plan`.
* **MUST** identify a lead guest by providing `booker` details or designating at
  least one guest with `role: "primary"` (including full legal name and contact
  details) prior to invoking Complete Booking Session. A Platform that receives
  `ready_for_complete` without an identified lead **MUST NOT** call Complete
  Booking Session, and **SHOULD** correct the session via Update Booking Session
  or escalate via `continue_url` if available.
* **MUST** generate unique, stable, session-scoped string identifiers in the Platform
  namespace for each entry in the root `guests[]` array (e.g., `"gst_01"`, `"gst_02"`).
* **MUST** ensure every `guest_assignments[].guest_id` references a valid `id`
  present in the root `guests[]` pool.
* **SHOULD NOT** send `guests[]` personal identity fields beyond `id` before the
  booking reaches `ready_for_complete`, and **SHOULD** send only the fields the
  business requests via `messages[]`.
* **MAY** engage an agent to facilitate the booking session (e.g. select stay,
  dates, collect guest information). However, the agent must hand over
  the booking session to a trusted and deterministic UI for the user to review
  the booking details and complete the booking.
* **MAY** send the user from the trusted, deterministic UI back to the agent
  at any time.
* **MAY** provide agent context when the platform indicates that the request
  was done by an agent.
* **MUST** use `continue_url` when booking status is `requires_escalation`.
* **MAY** use `continue_url` to hand off to business UI in other situations.
* When performing handoff, **SHOULD** prefer business-provided `continue_url`.

### Business

* **MUST** evaluate requested `stay.id`, or the compound `accommodation_type.id` and
  `rate_plan.id` bindings against real-time availability and inventory constraints,
  echoing authoritative metadata, pricing totals, and policy terms.
* **MUST** make `rate_plan.title` distinguish the rate plan and, together with
  `rate_plan.description` when present,is sufficient for a Buyer to understand its
  material commercial terms without having to read into `policies[]`; both
  fields **MUST NOT** contradict `policies[]`.
* **MUST** preserve platform-supplied `guest.id` identifiers across session
  updates and responses without remapping, renaming, or mutating them.
* **MUST** validate that all `stays[].guest_assignments[].guest_id`
  references match an existing entry in the root `guests[]` array.
* **MUST NOT** return a booking session with statuses `ready_for_complete`,
  `complete_in_progress`, or `completed` without an identified lead - a `booker`
  with full legal name and a contact channel, a guest in `guests[]` with full
  legal name and a contact channel who is assigned as `primary` in some
  `stays[].guest_assignments[]`, or in corporate or proxy bookings, a named primary guest
  alongside a `booker` providing the contact channel. Additional identity fields
  a Business needs (such as passport number, nationality, or date of birth)
  **MUST** be negotiated per Business through `messages[]`.
* **MUST** enforce physical `capacity` limits against the total assigned occupants and guest ages:
    * Guest age is evaluated in completed years as of the stay check-in date.
    * A guest whose age falls within a defined `child_age_ranges[].ages` bracket is classified as a child; any guest whose age falls in no child bracket is classified as an adult.
    * The requested occupancy **MUST** satisfy: `occupancy.adults <= capacity.adults`, `occupancy.children <= capacity.children`, and `occupancy.total <= capacity.total`.
    * For each entry in `child_age_ranges[]` with a `limit`, the number of children whose ages fall in that bracket **MUST NOT** exceed `limit`.
* **MUST** send a confirmation email after the booking has been completed when a
  valid email address is available in `booker` or primary guest details.
* **SHOULD** provide accurate error and warning messages.
* Logic handling the booking sessions **MUST** be deterministic.
* **MUST** provide `continue_url` when returning `status` = `requires_escalation`.
* **MUST** include at least one message with `severity` of `requires_buyer_input`
  or `requires_buyer_review` when returning `status` = `requires_escalation`.
* **SHOULD** provide `continue_url` in all non-terminal booking responses.
* After a booking session reaches the state "completed", it is considered
  immutable.

## Capability Schema Definition <span id="booking"></span>

{{ schema_fields('booking_resp', 'lodging/booking') }}

## Operations

The Booking capability defines the following logical operations:

| Operation                    | Description                                                                         |
| :--------------------------- | :---------------------------------------------------------------------------------- |
| **Create Booking Session**   | Initiates a new booking session. Called as soon as a user expresses booking intent. |
| **Get Booking Session**      | Retrieves the current state of a booking session.                                   |
| **Update Booking Session**   | Updates a booking session via full resource replacement.                            |
| **Complete Booking Session** | Finalizes the booking and confirms the reservation.                                 |
| **Cancel Booking Session**   | Cancels a booking session.                                                          |

### Create Booking Session

Invoked by the platform when the user expresses booking intent to initiate a
session with upper-funnel property, stay, and stay date parameters.

{{ method_fields('create_booking_session', 'lodging/rest.openapi.json', 'lodging/booking') }}

### Get Booking Session

Retrieves the latest state of the booking session resource.

{{ method_fields('get_booking_session', 'lodging/rest.openapi.json', 'lodging/booking') }}

### Update Booking Session

Performs a full replacement of the booking session resource. The platform is
**REQUIRED** to send the complete booking state containing any data updates
(e.g., guest profiles, guest assignments, booker details).

{{ method_fields('update_booking_session', 'lodging/rest.openapi.json', 'lodging/booking') }}

### Complete Booking Session

Final booking placement call. Invoked when payment has been collected and the
user commits to finalize the reservation.

{{ method_fields('complete_booking_session', 'lodging/rest.openapi.json', 'lodging/booking') }}

### Cancel Booking Session

Cancels an active booking session prior to completion.

{{ method_fields('cancel_booking_session', 'lodging/rest.openapi.json', 'lodging/booking') }}

## Transport Bindings

The abstract operations above are bound to specific transport protocols:

* [REST Binding](rest.md): RESTful API mapping using standard HTTP verbs and JSON payloads.
* [MCP Binding](mcp.md): Model Context Protocol mapping for agentic interaction.

## Examples {: #examples }

### Pricing Examples

The following examples provide complete, authoritative booking sessions demonstrating
property-collected charges and flexible payment terms integration.

=== "Property-Collected Taxes & Fees"

    A complete 3-night Tokyo hotel reservation where base room rates and service fees are prepaid immediately, while local Tokyo Accommodation Tax and resort fees are collected directly at check-in. Payment timing is explicitly modeled via `payment.terms[]` under capability `dev.ucp.common.payment.terms`, and the tax disclosure warning in `messages[]` references the property-collected schedule:

    <!-- ucp:example schema=lodging/booking op=read -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.lodging.booking": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.common.payment.terms": [
            {
              "version": "{{ ucp_version }}"
            }
          ]
        },
        "payment_handlers": {
          "com.example.card_handler": [
            {
              "id": "card_handler",
              "version": "{{ ucp_version }}",
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

=== "Flexible Payment Terms — Deposit & Balance"

    A complete 3-night hotel reservation offering a deposit and balance payment term (`pt_deposit_balance`). The first night's room rate along with prepaid fees and initial tax are charged immediately, while the remaining 2 nights' room rate and balance tax are deferred until check-in:

    <!-- ucp:example schema=lodging/booking op=read -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.lodging.booking": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.common.payment.terms": [
            {
              "version": "{{ ucp_version }}"
            }
          ]
        },
        "payment_handlers": {
          "com.example.card_handler": [
            {
              "id": "card_handler",
              "version": "{{ ucp_version }}",
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

{{ schema_fields('types/actions', 'lodging/booking') }}

### Property

The physical establishment or geographic location where the lodging is situated (e.g., hotel, resort, villa estate, cabin park).

{{ schema_fields('types/property_resp', 'lodging/booking') }}

### Booking Confirmation

Confirmation and locator details returned upon successful booking completion.

{{ schema_fields('types/booking_confirmation', 'lodging/booking') }}

### Booker

The legal contracting party and primary point of contact making the reservation.

{{ schema_fields('types/booker', 'lodging/booking') }}

### Capacity

Occupancy limits and child age thresholds supported by a physical accommodation type.

{{ schema_fields('types/capacity', 'lodging/booking') }}

### Context

Buyer location and market context hints.

{{ schema_fields('types/context', 'lodging/booking') }}

### Date Interval

Check-in (`start_date`) and check-out (`end_date`) date range for the stay.

{{ schema_fields('types/date_interval', 'lodging/booking') }}

### Guest

Individual guest profile. The `id` is generated and supplied by the Platform to
uniquely identify the occupant within the booking session.

{{ schema_fields('types/guest', 'lodging/booking') }}

### Guest Assignment

Relational link mapping a stay unit to an occupant from the root `guests[]` pool
via `guest_id` with a designated role.

{{ schema_fields('types/guest_assignment', 'lodging/booking') }}

### Link

Compliance and legal links (e.g., Privacy Policy, Terms of Service).

{{ schema_fields('types/link', 'lodging/booking') }}

### Message Error

{{ schema_fields('types/message_error', 'lodging/booking') }}

### Message Info

{{ schema_fields('types/message_info', 'lodging/booking') }}

### Message Warning

{{ schema_fields('types/message_warning', 'lodging/booking') }}

### Occupancy

Requested adult and child guest count breakdown for a stay.

{{ schema_fields('types/occupancy', 'lodging/booking') }}

### Payment

Payment details and collected payment instruments.

{{ schema_fields('payment', 'lodging/booking') }}

### Policy

Policies (cancellation terms, house rules, and the like) that apply to the booking session or stays.
JSONPath targets in `applies_to` are relative to this response root (e.g., `$.stays[0]`).
See [Policies](../../overview/index.md#policies) for the full model.

{{ schema_fields('types/policy', 'lodging/booking') }}

### Rate Plan

Commercial rate plan contract, cancellation policy rules, and rate inclusions.
The `id` is discovered from upper-funnel search.

{{ schema_fields('types/rate_plan', 'lodging/booking') }}

### Stay

Compound binding uniting physical accommodation real estate (`accommodation_type.id`),
commercial rate terms (`rate_plan.id`), stay dates (`stay_dates`), occupancy, and guest assignments.

{{ schema_fields('types/stay', 'lodging/booking') }}

### Accommodation Type

Category or specification of the rentable physical space (e.g., room, apartment, villa, campsite pitch) and capacity limits.

{{ schema_fields('types/accommodation_type', 'lodging/booking') }}

### Signals

Platform-supplied fraud and security context.

{{ schema_fields('types/signals', 'lodging/booking') }}

### Total

Authoritative itemized price components and aggregate booking total.

{{ schema_fields('types/total_resp', 'lodging/booking') }}
