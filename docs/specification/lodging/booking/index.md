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

1. **Session Initiation**: The Platform initiates a booking session using room,
   rate, and itinerary details discovered from upper-funnel search.
2. **Progressive Enrichment**: The Platform updates the session with guest
   profiles, room assignments, booker information, and payment details across
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

* **Compound Room Rate Binding (`room_rate`)**: A lodging reservation is composed
  of one or more room rate units. A `room_rate` is a compound binding linking
  a physical room type (`room_type`), a commercial rate contract
  (`rate_plan`), occupancy requirements (`occupancy`), and guest room
  assignments (`guest_assignments`).
* **Platform-Generated Guest Identifiers (`guest.id`)**: Unlike business-scoped
  catalog and room identifiers, guest identifiers are generated, allocated, and
  managed by the Platform within the Platform's namespace. The Business treats
  `guest.id` as a stable, opaque reference. Guest identifiers are opaque strings
  scoped strictly to the individual booking session (e.g., `"gst_01"`, `"gst_02"`).
  Platforms **MUST NOT** use persistent cross-merchant user tracking identifiers or
  expose personally identifiable information (PII) within `guest.id`. Businesses
  **MUST NOT** infer or link identity across distinct booking sessions based on `guest.id`.
* **Guest Pool & Room Assignment Model**: Guest data is structured into a
  two-level relational model:
    * **Root Guest Pool (`guests[]`)**: A flat collection of all individual guest
      profiles associated with the entire reservation.
    * **Room Assignments (`room_rates[].guest_assignments[]`)**: Granular mappings
      associating specific room units with guests from the root pool via
      `guest_id` and designating occupancy roles (such as `primary_guest` or
      `additional_guest`).
* **Separation of Booker and Guests**: The data model strictly separates the
  legal purchaser from the physical room occupants:
    * **`booker`**: The legal contracting party responsible for payment, contact
      obligations, and reservation ownership.
    * **`guests`**: The individuals who will physically occupy the accommodations.
      A booker **MAY** also be listed as a guest in the root pool, but the entities
      remain decoupled to support corporate, proxy, and multi-room bookings.
* **Provisional Discovery vs. Authoritative Booking**:
    * *Discovery Phase (Provisional)*: Search, quotation, and room lookup
      responses provide provisional rates, available room types, and policy
      summaries based on search parameters.
    * *Booking Session (Authoritative)*: Creating a booking session transitions
      from provisional discovery to an authoritative state. The Business locks
      or evaluates real-time inventory, resolves binding rate rules, enforces
      room capacity bounds, calculates totals (`totals[]`), and attaches
      authoritative cancellation terms (`policies[]`).

### Pricing Scope

Lodging reservations follow strict all-in pricing rules to comply with consumer protection regulations (such as FTC and EU price transparency directives). In lodging, the full financial commitment for a stay is often divided between charges prepaid at the time of reservation confirmation and charges collected directly by the accommodation property upon check-in or check-out (e.g., resort fees, municipal occupancy taxes, or a remaining room balance).

#### Pricing Architecture & Scope Guidelines

* **Authoritative Root Total (`totals`)**: The top-level `totals` array represents the binding, authoritative pricing breakdown and aggregate financial commitment for the entire reservation stay across all requested room units.
* **Stay-Level Room Rate Total (`room_rates[].totals`)**: Each entry in `room_rates[].totals` reflects the total charges for that specific room rate unit across the entire itinerary stay duration (i.e., check-in to check-out), **NOT** a per-night figure.
* **Itemized Subtotals and Nightly Breakdown (`lines`)**: The `lines` array under a total item provides supplementary, itemized clarity:
    * `subtotal` total items **MAY** carry `lines` representing the per-night room rate breakdown.
    * `tax` total items **MAY** carry `lines` delineating separate tax authorities (e.g., state sales tax vs. local occupancy or tourism tax).
    * `fee` total items **MAY** carry `lines` detailing mandatory charges (e.g., daily resort fees, cleaning fees).
* **Price Transparency and All-Inclusive Cost**: Platforms and Businesses **MUST** ensure that the guest is presented with the complete stay liability before booking confirmation. Hidden fees or undisclosed property charges violate price transparency standards.

#### Immediate vs. Deferred Payment Breakdown

* **Amount Due Now (`total`)**: The standard `type: "total"` entry strictly represents the immediate amount charged to the buyer's payment instrument upon booking confirmation. In full prepayment terms, this equals the entire cost of the stay. In deposit-based terms, this equals only the initial deposit and prepaid taxes/fees. The sum of all standard prepaid items (`subtotal` + prepaid `fee` + prepaid `tax` + `discount`) **MUST** equal `total`.
* **Deferred & Property-Collected Well-Known Types**: To model post-booking and property-collected charges consistently, the following well-known `type` values are introduced:
    * `postpaid_subtotal`: The lodging room rate balance collected directly at the property (e.g., remaining room nights due at check-in after a partial deposit).
    * `postpaid_fee`: Mandatory amenity, resort, cleaning, or facility fees collected directly by the property during the stay.
    * `postpaid_tax`: Mandatory municipal, occupancy, or tourism taxes collected locally by the property (e.g., city accommodation tax).
    * `due_at_property`: The aggregate sum of all property-collected charges (`postpaid_subtotal` + `postpaid_fee` + `postpaid_tax`). Present whenever any postpaid charges exist.
    * `grand_total`: The all-inclusive stay cost (`total` + `due_at_property`), representing the Buyer's total financial commitment for the entire reservation. Present whenever deferred or property-collected amounts exist, ensuring full compliance with FTC and EU price display requirements.
    * `grand_total`: The all-inclusive stay cost (`total` + `due_at_property`), representing the

##### Well-Known Totals Types & Accounting Invariants

| Type | Accounting Group | Description | Constraints & Invariants |
| :--- | :--- | :--- | :--- |
| `subtotal` | Immediate (Due Now) | Immediate room rate charges (or upfront deposit) | Exactly one entry in `totals[]` |
| `fee` | Immediate (Due Now) | Prepaid service, processing, or booking fees | Optional, repeatable |
| `tax` | Immediate (Due Now) | Prepaid state, value-added, or sales taxes | Optional, repeatable |
| `discount` | Immediate (Due Now) | Rate reductions, promotional discounts, or pay-now savings | Optional, negative amount |
| `total` | Immediate (Due Now) | Aggregate amount charged upon confirmation | Exactly one entry in `totals[]`; equals sum of immediate group |
| `postpaid_subtotal` | Deferred (Property) | Remaining room rate balance collected at hotel | Requires `display_text` |
| `postpaid_fee` | Deferred (Property) | Mandatory resort, facility, or cleaning fees paid at hotel | Requires `display_text` |
| `postpaid_tax` | Deferred (Property) | Municipal, city, or occupancy taxes paid at hotel | Requires `display_text` |
| `due_at_property` | Deferred (Property) | Aggregate total collected upon arrival/departure | Requires `display_text`; equals sum of deferred group |
| `grand_total` | Summary | Total stay liability across all payment timings | Requires `display_text`; equals `total` + `due_at_property` |

#### Local Tax & Fee Disclosures

When mandatory taxes or fees are collected locally by the lodging property and cannot be remitted at booking, the Business **SHOULD** provide a warning message in `messages[]` with `presentation: "disclosure"` and a `path` pointing directly to the relevant postpaid entry (e.g., `$.totals[4]`). This disclosure notice **MUST** state the applicable local rates, exemptions, and payment instructions, complemented by formal policy links in `links[]`.

#### Payment Terms Integration (`dev.ucp.common.payment.terms`)

When a Business supports flexible payment timing, it advertises the `dev.ucp.common.payment.terms` capability and populates `payment.terms[]` with the available payment terms alongside `payment.selected_term_id` indicating the active selection:

* **Schedules and `totals` Alignment**:
    * A payment term is composed of one or more `schedules[]`.
    * Schedules with `type: "immediate"` represent payments due today upon booking completion and **MUST** sum to `totals[].type: "total"`.
    * Schedules with `type: "deferred"` represent payments due at a specified future date or event (e.g., `due_at` timestamp or check-in) and **MUST** sum to `totals[].type: "due_at_property"`.
* **Selection Mutations**:
    * When the Platform updates `payment.selected_term_id` via Update Booking Session (e.g., switching from "Pay now" to "First night now, balance at check-in"), the Business authoritatively recomputes `totals[]`.
    * The recomputed `totals[]` reflects the newly selected term's immediate amount in `total`, partitions remaining nights into `postpaid_subtotal` and `postpaid_tax`, and updates `due_at_property` and `grand_total`.

The following snippets illustrate how `totals[]` is structured across three canonical lodging pricing patterns:

=== "Pattern 1: Property-Collected Charges"

    Prepaid room rate and service fee charged immediately (`total: 70400`), while resort fee and Tokyo Accommodation Tax are collected at check-in (`due_at_property: 6000`), totaling `grand_total: 76400`:

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
        "type": "total",
        "display_text": "Total Due Now (Charged Today)",
        "amount": 70400
      },
      {
        "type": "postpaid_fee",
        "display_text": "Resort & Facility Amenity Fee (Pay at hotel, ¥2,000/night)",
        "amount": 6000
      },
      {
        "type": "postpaid_tax",
        "display_text": "Tokyo Accommodation Tax (Pay at hotel, ~¥200/guest/night)",
        "amount": 0
      },
      {
        "type": "due_at_property",
        "display_text": "Total Due at Property (Pay upon Check-in)",
        "amount": 6000
      },
      {
        "type": "grand_total",
        "display_text": "Grand Total (Total Stay Cost)",
        "amount": 76400
      }
    ]
    ```

=== "Pattern 2: Upfront Payment with Savings"

    Upfront payment term selected (`pt_pay_now`), offering a $50 discount (`discount: -5000`) for paying in full today. No deferred balance remains (`due_at_property: 0`):

    <!-- ucp:example schema=lodging/booking target=$.totals op=read -->
    ```json
    [
      { "type": "subtotal", "display_text": "Room Rate (3 nights)", "amount": 120000 },
      { "type": "fee", "display_text": "Service Fee", "amount": 3000 },
      { "type": "tax", "display_text": "State Lodging Tax (10%)", "amount": 12000 },
      { "type": "discount", "display_text": "Pay-now saving", "amount": -5000 },
      { "type": "total", "display_text": "Total Due Now (Charged Today)", "amount": 130000 },
      { "type": "due_at_property", "display_text": "Total Due at Property", "amount": 0 },
      { "type": "grand_total", "display_text": "Grand Total (Total Stay Cost)", "amount": 130000 }
    ]
    ```

=== "Pattern 3: Deposit & Check-in Balance"

    Deposit term selected (`pt_deposit_balance`), charging the 1st night deposit and initial taxes/fees today (`total: 47000`), with the remaining 2 nights rate and tax collected at check-in (`due_at_property: 88000`), yielding `grand_total: 135000`:

    <!-- ucp:example schema=lodging/booking target=$.totals op=read -->
    ```json
    [
      {
        "type": "subtotal",
        "display_text": "Room Deposit (1st night, 1 room)",
        "amount": 40000
      },
      {
        "type": "fee",
        "display_text": "Service Fee (Prepaid)",
        "amount": 3000
      },
      {
        "type": "tax",
        "display_text": "State Lodging Tax on Deposit (10%)",
        "amount": 4000
      },
      {
        "type": "total",
        "display_text": "Total Due Now (Deposit Charged Today)",
        "amount": 47000
      },
      {
        "type": "postpaid_subtotal",
        "display_text": "Remaining Room Balance (2 nights @ $400, pay at hotel)",
        "amount": 80000
      },
      {
        "type": "postpaid_tax",
        "display_text": "State Lodging Tax on Remaining Balance (10%, pay at hotel)",
        "amount": 8000
      },
      {
        "type": "due_at_property",
        "display_text": "Total Due at Property (Pay upon Check-in)",
        "amount": 88000
      },
      {
        "type": "grand_total",
        "display_text": "Grand Total (Total Stay Cost)",
        "amount": 135000
      }
    ]
    ```

> [!TIP]
> For complete, end-to-end booking session payloads with room rate bindings, lead guest assignments, messages, and payment terms, see [Pricing & Payment Terms Examples](#pricing-examples).

### Payments

Payment handlers are discovered from the business's UCP profile at
`/.well-known/ucp`. The handlers define the processing specifications for
collecting payment instruments (e.g., Google Pay, Shop Pay). When the user
submits payment, the platform populates the `payment.instruments` array with the
collected instrument data.

The `payment` object is optional on booking creation and may be omitted for
use cases that don't require immediate payment processing (e.g., pay after
arrival or hold-with-card).

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
    (confirmed pricing totals, valid itinerary dates, payment instrument
    collected if required, lead guest identification via `booker` or
    `primary_guest`, and all outstanding gating actions resolved) and platform
    can finalize programmatically. Platform can call Complete Booking Session.
* **`complete_in_progress`**: Business is processing the Complete Booking
    request.
* **`completed`**: Booking confirmed successfully.
* **`canceled`**: Booking session is invalid or expired. Platform should
    start a new booking session if needed.

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

| Code                  | Description                                                |
| :-------------------- | :--------------------------------------------------------- |
| `inventory_exhausted` | The selected room or inventory hold is no longer available |
| `payment_failed`      | Payment processing failed                                  |
| `eligibility_invalid` | Eligibility claim could not be verified at completion      |

### Warning Presentation

The `presentation` field on warning messages controls the rendering contract the
platform **MUST** follow (e.g., `notice` vs. `disclosure`). For the authoritative
rendering rules, see [Checkout — Warning Presentation](../../shopping/checkout/index.md#warning-presentation).

#### Price Changes

When inventory rates or commercial pricing terms fluctuate during an active booking
session, the Business informs the Platform using a standard warning with
`code: "price_changed"` and `severity: "recoverable"`.

The Business **MUST NOT** complete a booking session if unacknowledged price
changes occur. When a `price_changed` warning is received, the Platform **MUST**
present the updated totals to the buyer for explicit confirmation before submitting
a Complete Booking Session request.

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

* **MUST** supply valid `accommodation.id`, and either a pre-composed `room_rate.id`
  OR both `room_type.id` and `rate_plan.id` identifiers sourced from upper-funnel
  discovery mechanisms when creating a booking session.
* **MUST** identify a lead guest by providing `booker` details or designating at
  least one guest with `role: "primary_guest"` (including full legal name and contact
  details) prior to invoking Complete Booking Session.
* **MUST** generate unique, stable string identifiers in the Platform namespace
  for each entry in the root `guests[]` array (e.g., `"gst_01"`, `"gst_02"`).
* **MUST** ensure every `guest_assignments[].guest_id` references a valid `id`
  present in the root `guests[]` pool.
* **MAY** engage an agent to facilitate the booking session (e.g. select room,
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

* **MUST** evaluate requested `room_rate.id`, or the compound `room_type.id` and
  `rate_plan.id` bindings against real-time availability and inventory constraints,
  echoing authoritative room metadata, pricing totals, and policy terms.
* **MUST** preserve platform-supplied `guest.id` identifiers across session
  updates and responses without remapping, renaming, or mutating them.
* **MUST** validate that all `room_rates[].guest_assignments[].guest_id`
  references match an existing entry in the root `guests[]` array.
* **MUST** enforce physical room `capacity` limits against the total assigned
  occupants and guest ages.
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
session with upper-funnel room, rate, and itinerary parameters.

{{ method_fields('create_booking_session', 'lodging/rest.openapi.json', 'lodging/booking') }}

### Get Booking Session

Retrieves the latest state of the booking session resource.

{{ method_fields('get_booking_session', 'lodging/rest.openapi.json', 'lodging/booking') }}

### Update Booking Session

Performs a full replacement of the booking session resource. The platform is
**REQUIRED** to send the complete booking state containing any data updates
(e.g., guest profiles, room assignments, booker details).

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

The following examples provide complete, authoritative booking sessions demonstrating property-collected charges and flexible payment terms integration.

=== "Property-Collected Taxes & Fees"

    A complete 3-night Tokyo hotel reservation where base room rates and service fees are prepaid immediately, while local Tokyo Accommodation Tax and resort fees are collected directly at check-in. Notice the tax disclosure warning in `messages[]` referencing the local tax line:

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
      "itinerary": {
        "start_date": "2026-10-01",
        "end_date": "2026-10-04"
      },
      "accommodation": {
        "id": "acc_ginza_hotel",
        "name": "Ginza Grand Hotel"
      },
      "room_rates": [
        {
          "id": "rr_dlx_king_std",
          "room_type": {
            "id": "rt_dlx_king",
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
          "display_text": "Room Rate (3 nights for 1 room, also includes 10% consumption tax)",
          "amount": 64000
        },
        {
          "type": "fee",
          "display_text": "Service Fee (10% prepaid)",
          "amount": 6400
        },
        {
          "type": "total",
          "display_text": "Total Due Now (Charged Today)",
          "amount": 70400
        },
        {
          "type": "postpaid_fee",
          "display_text": "Resort & Facility Amenity Fee (Pay at hotel, ¥2,000/night)",
          "amount": 6000
        },
        {
          "type": "postpaid_tax",
          "display_text": "Tokyo Accommodation Tax (Pay at hotel, ~¥200/guest/night)",
          "amount": 0
        },
        {
          "type": "due_at_property",
          "display_text": "Total Due at Property (Pay upon Check-in)",
          "amount": 6000
        },
        {
          "type": "grand_total",
          "display_text": "Grand Total (Total Stay Cost)",
          "amount": 76400
        }
      ],
      "messages": [
        {
          "type": "warning",
          "code": "local_tax",
          "path": "$.totals[4]",
          "presentation": "disclosure",
          "content": "**Tokyo Accommodation Tax Notice**: In accordance with Tokyo Metropolitan Government regulations, a local accommodation tax of JPY 200 per guest per night applies to room rates of JPY 15,000 or higher. This tax is not included in the booking total and must be paid directly to the property upon check-in.",
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
      ]
    }
    ```

=== "Payment Terms — Pay Now"

    A complete booking session offering payment terms (`pt_pay_now` and `pt_deposit_balance`), where the buyer currently has `pt_pay_now` selected, paying $1,300.00 today and saving $50:

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
      "itinerary": {
        "start_date": "2026-09-01",
        "end_date": "2026-09-04"
      },
      "accommodation": {
        "id": "acc_grand_hotel",
        "name": "Grand Hotel"
      },
      "room_rates": [
        {
          "id": "rr_king_std",
          "room_type": {
            "id": "rt_king",
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
          "display_text": "Room Rate (3 nights)",
          "amount": 120000
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
          "type": "discount",
          "display_text": "Pay-now saving",
          "amount": -5000
        },
        {
          "type": "total",
          "display_text": "Total Due Now (Charged Today)",
          "amount": 130000
        },
        {
          "type": "due_at_property",
          "display_text": "Total Due at Property",
          "amount": 0
        },
        {
          "type": "grand_total",
          "display_text": "Grand Total (Total Stay Cost)",
          "amount": 130000
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
        "selected_term_id": "pt_pay_now",
        "terms": [
          {
            "id": "pt_pay_now",
            "title": "Pay now",
            "description": {
              "plain": "Save $50 by paying for your stay today."
            },
            "schedules": [
              {
                "id": "sched_full",
                "type": "immediate",
                "description": {
                  "plain": "Due today when you book."
                },
                "amount": 130000
              }
            ]
          },
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

=== "Payment Terms — Deposit & Balance"

    The recomputed booking session after selecting `pt_deposit_balance`, reflecting a $470.00 deposit charged today and an $880.00 balance due at check-in, for an all-in stay liability of $1,350.00:

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
      "id": "bks_example_03",
      "status": "incomplete",
      "currency": "USD",
      "itinerary": {
        "start_date": "2026-09-01",
        "end_date": "2026-09-04"
      },
      "accommodation": {
        "id": "acc_grand_hotel",
        "name": "Grand Hotel"
      },
      "room_rates": [
        {
          "id": "rr_king_std",
          "room_type": {
            "id": "rt_king",
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
          "display_text": "Room Deposit (1st night, 1 room)",
          "amount": 40000
        },
        {
          "type": "fee",
          "display_text": "Service Fee (Prepaid)",
          "amount": 3000
        },
        {
          "type": "tax",
          "display_text": "State Lodging Tax on Deposit (10%)",
          "amount": 4000
        },
        {
          "type": "total",
          "display_text": "Total Due Now (Deposit Charged Today)",
          "amount": 47000
        },
        {
          "type": "postpaid_subtotal",
          "display_text": "Remaining Room Balance (2 nights @ $400, pay at hotel)",
          "amount": 80000
        },
        {
          "type": "postpaid_tax",
          "display_text": "State Lodging Tax on Remaining Balance (10%, pay at hotel)",
          "amount": 8000
        },
        {
          "type": "due_at_property",
          "display_text": "Total Due at Property (Pay upon Check-in)",
          "amount": 88000
        },
        {
          "type": "grand_total",
          "display_text": "Grand Total (Total Stay Cost)",
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
            "id": "pt_pay_now",
            "title": "Pay now",
            "description": {
              "plain": "Save $50 by paying for your stay today."
            },
            "schedules": [
              {
                "id": "sched_full",
                "type": "immediate",
                "description": {
                  "plain": "Due today when you book."
                },
                "amount": 130000
              }
            ]
          },
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

### Accommodation

Physical property details associated with the reservation.

{{ schema_fields('types/accommodation_resp', 'lodging/booking') }}

### Booking Confirmation

Confirmation and locator details returned upon successful booking completion.

{{ schema_fields('types/booking_confirmation', 'lodging/booking') }}

### Booker

The legal contracting party and primary point of contact making the reservation.

{{ schema_fields('types/booker', 'lodging/booking') }}

### Capacity

Occupancy limits and child age thresholds supported by a physical room type.

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

Relational link mapping a room unit to an occupant from the root `guests[]` pool
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

Requested adult and child guest count breakdown for a room.

{{ schema_fields('types/occupancy', 'lodging/booking') }}

### Payment

Payment details and collected payment instruments.

{{ schema_fields('payment', 'lodging/booking') }}

### Rate Plan

Commercial rate plan contract, cancellation policy rules, and rate inclusions.
The `id` is discovered from upper-funnel search.

{{ schema_fields('types/rate_plan', 'lodging/booking') }}

### Room Rate

Compound binding uniting physical room real estate (`room_type.id`),
commercial rate terms (`rate_plan.id`), occupancy, and guest assignments.

{{ schema_fields('types/room_rate', 'lodging/booking') }}

### Room Type

Physical room real estate attributes and capacity limits.

{{ schema_fields('types/room_type', 'lodging/booking') }}

### Signals

Platform-supplied fraud and security context.

{{ schema_fields('types/signals', 'lodging/booking') }}

### Total

Authoritative itemized price components and aggregate booking total.

{{ schema_fields('types/total_resp', 'lodging/booking') }}
