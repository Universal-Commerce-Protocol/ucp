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
  `guest.id` as a stable, opaque reference.
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
    and platform can finalize programmatically. Platform can call
    Complete Booking Session.
* **`complete_in_progress`**: Business is processing the Complete Booking
    request.
* **`completed`**: Booking confirmed successfully.
* **`canceled`**: Booking session is invalid or expired. Platform should
    start a new booking session if needed.

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

The `presentation` field on warning messages controls the rendering
contract the platform **MUST** follow. When omitted, it defaults to
`"notice"`.

|                          | `notice` (default) | `disclosure`                |
| :----------------------- | :----------------- | :-------------------------- |
| Display content          | **MUST**           | **MUST**                    |
| Proximity to `path`      | **MAY**            | **MUST**                    |
| Dismissible              | **MAY**            | **MUST NOT**                |
| Render `image_url`       | **MAY**            | **MUST**                    |
| Render `url`             | **MAY**            | **SHOULD**                  |
| Escalate if cannot honor | —                  | **MUST** via `continue_url` |

#### `notice` (default)

The default rendering contract for warnings. Platforms **MUST** display
the warning content to the user. Platforms **MAY** render notices in a
banner, tray, or toast, and **MAY** allow the user to dismiss them.

#### `disclosure`

Warnings with `presentation: "disclosure"` carry notices — additional
terms & policies, compliance content, etc. — that **MUST** follow the
prescribed rendering contract.

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

* **MUST** supply valid `accommodation.id`, `room_rate.id`, `room_type.id`,
  and `rate_plan.id` identifiers sourced from upper-funnel discovery mechanisms
  when creating a booking session.
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

* **MUST** evaluate requested `room_rate.id`, `room_type.id`, and `rate_plan.id`
  bindings against real-time availability and inventory constraints, echoing
  authoritative room metadata, pricing totals, and policy terms.
* **MUST** preserve platform-supplied `guest.id` identifiers across session
  updates and responses without remapping, renaming, or mutating them.
* **MUST** validate that all `room_rates[].guest_assignments[].guest_id`
  references match an existing entry in the root `guests[]` array.
* **MUST** enforce physical room `capacity` limits against the total assigned
  occupants and guest ages.
* **MUST** send a confirmation email after the booking has been completed.
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

## Entities

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
