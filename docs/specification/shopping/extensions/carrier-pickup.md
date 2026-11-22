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

<!-- cspell:ignore inpost orlenpaczka orlen packeta Paczka Orlen Paczkomat Prosta Warszawa mondialrelay Mondial postnord Postnord Euratom gls Poczta poczta Polska polska Pocztex Krakowskie Przedmieście -->

# Carrier Pickup Extension

## Overview

The Carrier Pickup Extension defines the `carrier_pickup` fulfillment method.
The Business ships the parcel to a parcel locker or a staffed pickup point that
a carrier network operates, and the recipient collects it there. The point
belongs to the network, not to the Business, which is what separates this
method from `pickup` at a Business Location.

A carrier point differs from a Business Location in four ways that matter to an
agent:

- **The network owns the point identifier.** Point IDs are issued by the
  network, are unique only within a network and country, and are usually chosen
  in the network's or a broker's point selector.
- **Several networks serve one market and one site.** A Buyer may choose among
  several networks in one checkout, and one shop counter can be a point of
  several networks, each with its own ID, holding period and limits.
- **The service needs recipient data.** Networks send the collection code or
  the deposit notice to the recipient's phone or email, and some deliver only to
  their registered customers. A street address of the recipient is not needed
  for delivery to the point.
- **Delivery has two steps.** The carrier deposits the parcel at the point, and
  the recipient later collects it, or does not collect it before the holding
  period ends.

**Key features:**

- A Carrier Point Destination keyed by (`network`, `country`, `point_id`),
  with an optional broker identifier, point type, location details, host site
  and parcel limits
- Options that are carrier services, each with its price, holding period and
  recipient requirements
- Platform-writable point selection, by point key or by broker identifier, with
  Business re-validation on every update
- Machine-readable reasons why a point cannot be used
- Order expectations that keep the selected point, and parcel-level events that
  separate deposit at the point from collection

**Dependencies:**

- [Fulfillment Extension](fulfillment.md). The Checkout part of this
  extension narrows the `fulfillment` object that Fulfillment defines, so it
  depends on Fulfillment. The Order part (expectations and events) does not.

  The intended declaration is a transitive extension chain,
  `extends: ["dev.ucp.shopping.fulfillment", "dev.ucp.shopping.order"]`, which
  the [intersection algorithm](../../overview/index.md#intersection-algorithm)
  already supports: without Fulfillment, the Checkout part is pruned. Today
  `ucp-schema generate-types` does not compose a chained extension onto
  Checkout, so generated Checkout types would miss the carrier pickup method.
  Until the tool supports chains, this extension is declared with
  `extends: ["dev.ucp.shopping.checkout", "dev.ucp.shopping.order"]`, and its
  Checkout composition also applies when Fulfillment is not negotiated. In that
  case a Business **MUST NOT** send `fulfillment` in a Checkout response, and a
  Platform **MUST NOT** send it in a request. Once the tool composes chains,
  the declaration moves to the chain without a change to the payloads.
- Checkout, and Order for the post-purchase data.

## Discovery

Businesses advertise carrier pickup in their profile, and **MAY** list the
networks they ship to so a Platform can offer the right point selector before
Checkout:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.fulfillment.carrier_pickup": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/carrier-pickup",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/fulfillment_carrier_pickup.json",
          "config": {
            "networks": [
              { "network": "eu.inpost", "name": "InPost", "countries": ["PL"] },
              { "network": "pl.orlenpaczka", "name": "Orlen Paczka", "countries": ["PL"] },
              { "network": "com.packeta", "name": "Packeta", "countries": ["CZ", "SK", "HU"] }
            ]
          }
        }
      ]
    }
  }
}
```

## Schema

### Carrier Point Destination

{{ schema_fields('types/carrier_point_destination_resp', 'shopping/extensions/carrier-pickup') }}

### Carrier Point Key

{{ extension_schema_fields('types/carrier_point_destination.json#/$defs/point_key', 'shopping/extensions/carrier-pickup') }}

### Pickup Period

{{ extension_schema_fields('types/carrier_point_destination.json#/$defs/pickup_period', 'shopping/extensions/carrier-pickup') }}

### Carrier Point Option Terms

{{ extension_schema_fields('types/carrier_point_destination.json#/$defs/option_terms', 'shopping/extensions/carrier-pickup') }}

### Carrier Point Address

{{ extension_schema_fields('types/carrier_point_destination.json#/$defs/point_address', 'shopping/extensions/carrier-pickup') }}

### Unavailable Reason

{{ extension_schema_fields('types/carrier_point_destination.json#/$defs/unavailable_reason', 'shopping/extensions/carrier-pickup') }}

### Carrier Pickup Option

{{ extension_schema_fields('fulfillment_carrier_pickup.json#/$defs/carrier_pickup_option', 'shopping/extensions/carrier-pickup') }}

### Recipient Requirement

{{ extension_schema_fields('fulfillment_carrier_pickup.json#/$defs/recipient_requirement', 'shopping/extensions/carrier-pickup') }}

### Network Summary

{{ extension_schema_fields('fulfillment_carrier_pickup.json#/$defs/network_summary', 'shopping/extensions/carrier-pickup') }}

### Carrier Pickup Expectation

{{ extension_schema_fields('fulfillment_carrier_pickup.json#/$defs/carrier_pickup_expectation', 'shopping/extensions/carrier-pickup') }}

### Carrier Pickup Event Fields

{{ schema_fields('types/carrier_pickup_event', 'shopping/extensions/carrier-pickup') }}

## Method contract

A Fulfillment Method whose `type` is `carrier_pickup` follows the base
[Fulfillment](fulfillment.md) contract, with these additions:

| Field | Direction | Meaning |
| :-- | :-- | :-- |
| `destinations[]` | Request and response | Carrier Point Destinations. The Platform **MAY** write the point the recipient chose; the Business returns the resolved point. |
| `groups[].options[]` | Response | Carrier services. Each option names its `network` and carries its `pickup_period` and `recipient_requirements`. |

The method opts into a Platform-writable request shape, as the
[Destinations](fulfillment.md#destinations) contract permits: under a
`carrier_pickup` method, a request destination that omits `type` is a
`carrier_point`, and only `id`, `network`, `country`, `point_id`, `broker` and
`recipient` are request fields. Everything else about a point is
Business-authored.

### Options and price

Each option is one carrier service, priced as a whole. The price depends on the
service and the line items, not on which point of that service is selected, and
a Business **MUST NOT** change an option's totals because the recipient picked
another point of the same service. This matches how commerce platforms already
model carriers: one shipping method or rate per carrier service.

The Business **SHOULD** return the options before a point is selected, so a
Platform can show "network A, price X; network B, price Y" first and then open
the selector of the chosen network. The selected point **MUST** belong to the
`network` of the selected option. When it does not, the Business rejects the
selection with the reason `option_mismatch`; it **MUST NOT** switch the
selected option by itself.

A Business that prefers one method per carrier service **MAY** instead return
several `carrier_pickup` methods, as its method combination rules allow; the
rules on this page apply to each.

### Point identity

A carrier point is identified by the tuple (`network`, `country`, `point_id`).

- The Business and Platform **MUST** compare `point_id` as an exact,
  case-sensitive string. They **MUST NOT** trim leading zeros, change case or
  parse structure out of it.
- The Platform **MUST NOT** infer `country` from `point_id` or from the
  Buyer's address. A network that operates in several countries can reuse the
  same `point_id` in each.
- `id` is the destination identifier used by `selected_destination_id`, as for
  every destination. It is not the point identifier.

#### Network identifier

`network` names the operating network, whose point directory and rules apply.
It is a reverse-domain name of the operator's primary domain. Where a
well-known value is listed below, Businesses and Platforms **MUST** use it, so
that two integrations name the same directory the same way. For other
networks, they use the reversed primary domain of the operator; a new
well-known value is added to this list by a change to this specification.

| Value | Network |
| :-- | :-- |
| `eu.inpost` | InPost lockers and points (all countries except those served under the Mondial Relay brand) |
| `com.mondialrelay` | Mondial Relay points and lockers |
| `pl.orlenpaczka` | Orlen Paczka |
| `pl.poczta-polska` | Poczta Polska and Pocztex points |
| `com.dhl` | DHL points and lockers |
| `com.dpd` | DPD Pickup points and lockers |
| `com.gls-group` | GLS points and lockers |
| `com.packeta` | Packeta (Z-BOX and points) |
| `com.postnord` | PostNord service points and lockers |

These values are proposed by this specification and are not registered or
endorsed by the operators. `network` is a namespace, not an authentication:
the Business **MUST** resolve `point_id` only against the directory it has
configured for that `network` value, so a point written with the wrong
`network` fails to resolve.

- A buyer-facing brand that sells several networks' points under one name, or
  a marketplace delivery program, is not a network. The point keeps the network
  that operates it.
- A host site, such as a convenience store chain, is not a network. See
  [Host sites](#host-sites).
- When one carrier delivers to another network's lockers, `network` names the
  locker network; the option's base `carrier` field names the delivering
  carrier.

#### Brokers

A Platform or Business can reach a network through a broker that runs its own
point selector or directory. When the broker's identifier for the point differs
from the network's own, the destination carries both: `point_id` is always the
network's identifier, and `broker.point_id` is the broker's. A Platform that
knows only the broker's identifier **MUST NOT** put it in `point_id`. It writes
`broker` without the point key, and the Business resolves it through the same
broker and returns the full point key, or rejects it with `point_not_found`.

#### Host sites

One physical site can be a point of several networks. Each is a separate
destination with its own point key and terms. A Business that knows the site,
typically through a broker, **MAY** set the same `host.id` on those
destinations within one response so the Platform can group them on a map. It
**MUST NOT** merge them into one destination, and `host.id` **MUST NOT** be an
identifier shared with other Businesses.

### Selection and re-validation

The Platform selects a point in one of two ways:

1. It writes the point the recipient chose as a destination with a
   Platform-chosen `id`, and sets `selected_destination_id` to that `id`.
2. It sets `selected_destination_id` to the `id` of a point the Business
   returned in `destinations[]`.

The Business resolves the written point against the network directory and
returns it with its Business-authored fields: at least `name` and `address`
(with `address_country`, plus `address_locality` or `street_address`), and `description` or
`geo` where they help the recipient find it. The rules of
[Selection and Location Identity](fulfillment.md#selection-and-location-identity)
apply unchanged: the response echoes the selection and contains exactly one
matching destination, and the Business **MUST NOT** substitute another point.

Points go full, close for maintenance or leave the network between selection
and order placement. The Business **MUST** re-validate the selected point on
every Update Checkout and before Complete Checkout, and **MUST** set
`available` on the selected destination. Re-validation uses the best data the
network offers; some networks report live capacity, others only an estimate.
`available: true` is the Business's assessment at the time of the response. It
does not reserve a compartment. When the point cannot be used, or the network
cannot be reached to check it, the Business rejects the selection with an
error Message with `severity: "recoverable"`, a `path` that selects the
method's `selected_destination_id`, and a `code` from the
[unavailable reason](#eligibility) codes. The Platform asks the Buyer to choose
another point, or offers another method.

A Business **MAY** list points it cannot use, with `available: false` and
`unavailable_reasons[]`, so the Platform can explain why a point the Buyer
knows is not offered. The Platform **MUST NOT** select a point marked
`available: false`.

### Eligibility

Lockers have fixed compartment sizes and networks have weight limits, so a cart
can be valid for courier delivery and invalid for some or all points. The
Business decides eligibility, because it knows the parcel it will build.
`limits` is informational. The well-known reason codes are:

| Code | Meaning |
| :-- | :-- |
| `exceeds_size_limit` | The parcel does not fit the largest compartment or the point's size limit. |
| `exceeds_weight_limit` | The parcel is heavier than the point accepts. |
| `item_not_eligible` | A line item cannot be sent to points of this network, for a reason other than size or weight. |
| `point_full` | The point has no free capacity. |
| `point_closed` | The point is temporarily out of service. |
| `point_not_found` | The network directory does not know the point, or it has been removed. |
| `network_not_supported` | The Business does not ship to this network for this cart. |
| `country_not_supported` | The Business does not ship to this network in this country. |
| `option_mismatch` | The point does not belong to the network of the selected option. |
| `point_type_not_supported` | The selected option does not deliver to this type of point. |

A reason that comes from particular line items **SHOULD** list them in
`line_item_ids`, so a Platform can propose splitting the cart across methods.
When no point of any network can take the cart, the Business **SHOULD** omit
the `carrier_pickup` method and **MAY** explain it in `available_methods[]`.

### Recipient data

The recipient is the person who collects the parcel. It can differ from the
Buyer, for example for a gift or a company purchase, so recipient data is
written on the selected destination's `recipient`, not taken from `buyer`.

Each option lists the recipient data it needs in `recipient_requirements[]`. A
requirement is met when at least one field in its `fields` carries a valid,
non-empty value, so "phone or email" is one requirement with two fields.
`countries` and `point_types` narrow where a requirement applies. The
requirements that apply are those of the selected option, for the selected
point's country and type. When a point has its own terms for that option
(`option_terms[]` on the destination), its `recipient_requirements` replace the
option's list, and its `pickup_period` replaces the option's period, for that
point only. A Business **MUST NOT** list the same `option_id` twice in one
destination's `option_terms[]`; a Platform that receives a duplicate uses the
first entry.

The Business:

- **MUST** list only data the service needs to deliver to the point and hand
  the parcel over. It **MUST NOT** list a postal address of the recipient or
  Buyer as needed for delivery to a point. A Business that needs an address for
  another purpose, such as an invoice, tax or customs, requests it through the
  field and the legal basis that purpose has (for example the billing address),
  not through this method.
- **MUST** return a recoverable error with a `path` that selects the field on
  the selected destination's `recipient` (for example
  `$.fulfillment.methods[0].destinations[0].recipient.phone_number`) when an
  applicable requirement is not met at Complete Checkout: with `code:
  "missing"` when no field of the requirement is present, and with a code
  naming the field, such as `invalid_phone`, when a value is present but the
  network does not accept it.
- **MUST** use recipient data received for this method only to deliver the
  parcel, and pass to the network only the data the requirement names.

The Platform:

- **SHOULD** collect the applicable requirements before Complete Checkout and
  tell the Buyer what each one is for. For a well-known `purpose` it **MAY** use
  its own wording; for any other value it shows the requirement's
  `description`. A `purpose` code is not a complete privacy notice; the
  information duties of the controllers involved still apply.
- **MUST NOT** send recipient fields that no applicable requirement names.
- **MUST NOT** fill a requirement from stored or identity-linked data without
  the Buyer seeing the value that will be shared.

## Order data

### Expectations

When an Order Expectation has `method_type: "carrier_pickup"`, it carries
`point` with the point key and the non-empty name of the selected point, from
the moment the Order exists, before any fulfillment event. The base
`destination` carries the point's address with the same minimum as in
Checkout: `address_country`, plus `address_locality` or `street_address`.

### Events

This extension defines five event types for parcels sent to a carrier point.
Each carries `parcel_id`, a Business-scoped identifier that stays the same for
the parcel across redirects and extensions. A Business **SHOULD** also put
`parcel_id` on the core events of the same parcel, such as `shipped`.

| Event `type` | Meaning | Required fields |
| :-- | :-- | :-- |
| `deposited_at_point` | The carrier reports the parcel placed at the point. The holding period runs from the event the applicable `pickup_period.starts` names: this deposit, or the later notification of the recipient. | `parcel_id`, `point`, `pickup_by` (`null` when unknown) |
| `pickup_deadline_changed` | The carrier reports a new deadline at the same point, for example an extension, without a new deposit. | `parcel_id`, `point`, `pickup_by` (`null` when unknown) |
| `collected_at_point` | The carrier reports the parcel collected. | `parcel_id`, `point` |
| `pickup_expired` | The holding period ended without collection. | `parcel_id`, `point` |
| `returning_to_sender` | The parcel is on its way back to the Business. | `parcel_id` |

The core `returned_to_sender` keeps its core meaning: the parcel is back at
the Business.

Ordering and correlation:

- Events of one parcel are ordered by `occurred_at`, not by array position or
  by the order in which they arrive. Events with equal `occurred_at` keep their
  array order.
- Event `id` values are unique within the Order. A Business **MUST NOT** reuse
  an `id` for a different event. A Platform that receives an `id` again with
  the same content treats it as a repeated delivery; with different content,
  it keeps the first and treats the Order's event log as needing the
  Business's correction.
- The latest `deposited_at_point` or `pickup_deadline_changed` of a parcel, by
  `occurred_at`, gives its current `point` and `pickup_by`. A redirect to
  another point is a new `deposited_at_point`; an extension at the same point
  is a `pickup_deadline_changed`. Neither affects another `parcel_id`.
- `collected_at_point` is terminal for the parcel. A Business **MUST NOT** emit
  a later `deposited_at_point`, `pickup_deadline_changed` or `pickup_expired`
  for the same `parcel_id`, except as a correction.
- When `pickup_by` is `null`, the Platform **MUST NOT** compute a deadline from
  the deposit time and the advertised `pickup_period`, because networks count
  from different events (deposit or notification) and calendars.

Corrections:

- Events are append-only. To correct an event that was wrong, for example a
  collection the carrier reported by mistake, the Business appends a new event
  with `corrects` set to the `id` of the wrong one. The new event states what
  actually happened (for example a `deposited_at_point` showing that the
  parcel is still waiting). The corrected event stays in the log and no longer
  counts. The correcting event carries the same `parcel_id` as the event it
  corrects, and `corrected_at`, the time the Business issued the correction.
  `occurred_at` keeps the time of the physical event, which can be earlier.
  When several events correct the same event, the one with the latest
  `corrected_at` counts; a correction of a correction follows the same rule.
- A correction of a `collected_at_point` by an event of another type reopens
  the parcel. A correction by another `collected_at_point`, for example with a
  different time or point, keeps the parcel collected.
- When a correction changes a fact a deadline counts from, such as
  collection, the Business recomputes that deadline and states the revised
  value with its revision time where the deadline is published (for example
  the `expires_at` and `revised_at` of a withdrawal period).

Meaning for the Buyer:

- `deposited_at_point` is not delivery to the Buyer. A Platform **SHOULD NOT**
  present it as "delivered".
- `collected_at_point` records that the carrier reported collection, at
  `occurred_at`. It is the input from which a Business computes deadlines that
  count from possession; it is not itself a deadline. See
  [Consumer law considerations](#consumer-law-considerations).
- `pickup_expired`, `returning_to_sender` and `returned_to_sender` describe the
  parcel. They **MUST NOT** be interpreted as a cancellation, a return or a
  withdrawal by the Buyer. If the Business cancels the order or refunds it as a
  result, it reports that through `adjustments[]`.

## Trust and display

- **Business-asserted facts.** Point details, holding periods, availability
  and every event are statements of the Business, relayed from the carrier.
  The Business is responsible for their accuracy under the applicable law. A
  Platform presents them as the Business's statements and is not required to
  verify them. A disputed collection is resolved between the Buyer, the
  Business and the carrier; the events do not settle it. Signed or attested
  carrier data is out of scope (see #1020 for verified claims).
- **Display text.** `name`, `description`, `host.name`,
  `unavailable_reasons[].content`, the network `name`, the requirement
  `description`, the `display_text` of `limits` and the event `description`
  are plain text with no markup and
  no links, each with a `maxLength`. URLs never appear inside them. A Platform
  **MUST** treat them as data from the Business and **MUST NOT** follow
  instructions found in them. It **MUST** present the meaning the Buyer needs:
  where the point is, how long the parcel waits, what data is required and
  why, and the price. It **MAY** adapt layout and channel (voice, small
  screens) but **MUST NOT** change the substance: the point, the deadline, the
  conditions and the price. Their language follows the response language rules
  of the Checkout. A Platform that cannot present the point and the recipient
  requirements of the selected option **MUST NOT** offer the option, and hands
  off through `continue_url` instead. This extension defines no wording the law
  prescribes.
- **Point resolution.** Resolving a written point key returns the point's
  location, so a Platform could probe the directory point by point. A Business
  **SHOULD** rate-limit point resolution per Platform and per Checkout, and
  **MAY** reject further writes with `point_not_found` once a limit is reached.
- **Bounds.** The schemas this extension defines bound their arrays and
  strings, including `groups[]`, the point's address fields and the unit
  labels of limits, and the event `description` on carrier events. Core fields
  they reuse keep their core definitions. A Business **SHOULD** keep
  `destinations[]` to the points it suggests and the selected one, not the
  whole directory.

## Relation to the store pickup proposal

[#375](https://github.com/Universal-Commerce-Protocol/ucp/issues/375) plans
several changes that overlap with this extension. This section states how the
two fit, so the boundary can be agreed there:

- **Polymorphic destinations.** #375 agreed that destinations under a method
  can be peers such as `retail_location`, `locker` and `pickup_point`.
  `carrier_point` is the concrete shape for the carrier-run `locker` and
  `pickup_point` cases; `point_type` keeps those words as values.
- **Hold durations.** #375 plans pickup windows and hold durations on
  `fulfillment_option`. This extension also puts the holding period on the
  option (`pickup_period`), with per-point terms keyed by option. If #375 defines a
  general hold field on options, `pickup_period` should be replaced by it.
- **Unavailability reasons.** #375 plans structured reasons distinct from
  availability. The codes here should become values of that vocabulary.
- **Events.** #375 plans store pickup events such as `ready_for_pickup` and
  corrected `tracking_number` semantics. The carrier events here have distinct
  names because they are carrier-reported and always need a point and a
  parcel; the schema can then require both without affecting store pickup.
- **Carrier handlers.**
  [#532](https://github.com/Universal-Commerce-Protocol/ucp/issues/532)
  discusses runtime carrier integrations and point choice tied to shipping
  options. Here, too, the service is the option; point lookup behind a handler
  would not change the shapes on this page.

## Consumer law considerations

This section is informative. It explains why the contract separates deposit
from collection and limits recipient data, for Businesses selling to consumers
in the European Union.

- **Passing of risk.** Under Article 20 of
  [Directive 2011/83/EU](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32011L0083)
  (Consumer Rights Directive), risk passes when the consumer, or a third party
  the consumer indicated other than the carrier, acquires physical possession.
  The European Consumer Centres Network, in non-binding guidance
  ([Parcel delivery issues, 2024, section 4](https://www.eccnet.eu/media/679/download)),
  treats a pickup point the trader offered as part of the carrier's delivery;
  on that reading risk passes at collection, not at deposit. The same guidance
  treats a point the consumer arranged with a carrier the trader did not offer
  differently.
- **Withdrawal period.** Under Article 9(2)(b), the 14-day period for goods
  counts from the day the consumer acquires physical possession of the goods.
  For several goods delivered separately it is the last good, for a good
  delivered in lots the last lot, and for regular delivery the first good
  (points (i) to (iii)). Under
  [Regulation (EEC, Euratom) No 1182/71](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:31971R1182),
  Article 3(1), the day of possession itself is not counted, and under Article
  3(4) a period whose last day is a public holiday, Saturday or Sunday ends at
  the end of the next working day. One `collected_at_point` event is therefore
  not always the start of the period, and a deadline is not `occurred_at` plus
  14 days. The Business computes it per contract. The consumer may also
  withdraw before collecting the parcel.
- **Not collecting is not withdrawing.** Withdrawal requires an unequivocal
  statement (Article 11(1)). `pickup_expired` and `returned_to_sender` are
  therefore not withdrawals; what follows depends on the contract and national
  law.
- **Data minimization.** Under Article 5(1)(c) and Article 25 of
  [Regulation (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
  (GDPR), personal data is limited to what is necessary for the purpose. The
  European Data Protection Board
  [Guidelines 2/2019](https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines-art_6-1-b-adopted_after_public_consultation_en.pdf)
  on Article 6(1)(b), Example 1, state that a home address is no longer
  necessary for the contract when the customer chose a pickup point. Other
  rules can still require an address for another purpose; for example, Article
  226(5) of Directive 2006/112/EC requires the customer's address on a full VAT
  invoice.

## Examples

### Checkout response: options before point selection

The Business returns one option per network with its price, holding period and
recipient requirements. No point is selected yet.

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_7f3a",
  "status": "incomplete",
  "currency": "PLN",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "fulfillment": {
    "methods": [
      {
        "id": "method_1",
        "type": "carrier_pickup",
        "line_item_ids": ["li_kettle"],
        "selected_destination_id": null,
        "groups": [
          {
            "id": "package_1",
            "line_item_ids": ["li_kettle"],
            "selected_option_id": "inpost_locker",
            "options": [
              {
                "id": "inpost_locker",
                "title": "InPost parcel locker",
                "network": "eu.inpost",
                "countries": ["PL"],
                "point_types": ["locker", "staffed"],
                "pickup_period": { "duration": "PT48H", "starts": "notification" },
                "recipient_requirements": [
                  { "fields": ["phone_number"], "purpose": "pickup_notification" },
                  { "fields": ["email"], "purpose": "pickup_notification" }
                ],
                "totals": [{ "type": "total", "amount": 1299 }]
              },
              {
                "id": "orlen_point",
                "title": "Orlen Paczka point",
                "network": "pl.orlenpaczka",
                "countries": ["PL"],
                "pickup_period": { "duration": "P3D", "starts": "notification", "counting": "business_days" },
                "recipient_requirements": [
                  { "fields": ["phone_number", "email"], "purpose": "pickup_notification" }
                ],
                "totals": [{ "type": "total", "amount": 999 }]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Platform writes the chosen point and the recipient

The Buyer buys a gift and picks a locker in the network's selector. The
Platform writes the point key and the recipient's phone and email.

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.checkout op=update direction=request -->
```json
{
  "line_items": [ ... ],
  "fulfillment": {
    "methods": [
      {
        "id": "method_1",
        "type": "carrier_pickup",
        "line_item_ids": ["li_kettle"],
        "selected_destination_id": "buyer_choice",
        "destinations": [
          {
            "id": "buyer_choice",
            "network": "eu.inpost",
            "country": "PL",
            "point_id": "WAW99X",
            "recipient": {
              "phone_number": "+48500100200",
              "email": "recipient@example.com"
            }
          }
        ],
        "groups": [
          { "id": "package_1", "selected_option_id": "inpost_locker" }
        ]
      }
    ]
  }
}
```

### Checkout response: point resolved, with alternatives

The Business resolves the locker and suggests a staffed point of another
network at the same site, and lists a locker it cannot use.

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_7f3a",
  "status": "incomplete",
  "currency": "PLN",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "fulfillment": {
    "methods": [
      {
        "id": "method_1",
        "type": "carrier_pickup",
        "line_item_ids": ["li_kettle"],
        "selected_destination_id": "buyer_choice",
        "destinations": [
          {
            "type": "carrier_point",
            "id": "buyer_choice",
            "network": "eu.inpost",
            "country": "PL",
            "point_id": "WAW99X",
            "point_type": "locker",
            "name": "Paczkomat WAW99X",
            "address": {
              "street_address": "ul. Prosta 5",
              "address_locality": "Warszawa",
              "postal_code": "00-850",
              "address_country": "PL"
            },
            "description": "Next to the shop entrance",
            "geo": { "latitude": 52.2319, "longitude": 20.9917 },
            "host": { "id": "site_17", "name": "Corner shop, ul. Prosta 5" },
            "limits": {
              "max_weight": { "value": 25, "unit": "KGM", "display_text": "kg" },
              "max_dimensions": [
                { "value": 64, "unit": "CMT", "display_text": "cm" },
                { "value": 41, "unit": "CMT", "display_text": "cm" },
                { "value": 38, "unit": "CMT", "display_text": "cm" }
              ]
            },
            "recipient": {
              "phone_number": "+48500100200",
              "email": "recipient@example.com"
            },
            "available": true
          },
          {
            "type": "carrier_point",
            "id": "pt_2",
            "network": "pl.orlenpaczka",
            "country": "PL",
            "point_id": "100417",
            "point_type": "staffed",
            "name": "Orlen Paczka, Corner shop",
            "option_terms": [
              {
                "option_id": "orlen_point",
                "pickup_period": { "duration": "P7D", "starts": "notification" }
              }
            ],
            "address": {
              "street_address": "ul. Prosta 5",
              "address_locality": "Warszawa",
              "address_country": "PL"
            },
            "host": { "id": "site_17", "name": "Corner shop, ul. Prosta 5" },
            "available": true
          },
          {
            "type": "carrier_point",
            "id": "pt_3",
            "network": "eu.inpost",
            "country": "PL",
            "point_id": "WAW12M",
            "point_type": "locker",
            "name": "Paczkomat WAW12M",
            "address": {
              "street_address": "Krakowskie Przedmieście 1",
              "address_locality": "Warszawa",
              "address_country": "PL"
            },
            "available": false,
            "unavailable_reasons": [
              { "code": "point_full", "content": "This locker is full today." }
            ]
          }
        ],
        "groups": [
          {
            "id": "package_1",
            "line_item_ids": ["li_kettle"],
            "selected_option_id": "inpost_locker",
            "options": [
              {
                "id": "inpost_locker",
                "title": "InPost parcel locker",
                "network": "eu.inpost",
                "pickup_period": { "duration": "PT48H", "starts": "notification" },
                "totals": [{ "type": "total", "amount": 1299 }]
              },
              {
                "id": "orlen_point",
                "title": "Orlen Paczka point",
                "network": "pl.orlenpaczka",
                "totals": [{ "type": "total", "amount": 999 }]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Platform knows only a broker's identifier

The Buyer picked a point in a broker's map, which returned only the broker's
identifier. The Business resolves it into the network's point key.

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.checkout op=update direction=request -->
```json
{
  "line_items": [ ... ],
  "fulfillment": {
    "methods": [
      {
        "id": "method_1",
        "type": "carrier_pickup",
        "line_item_ids": ["li_book"],
        "selected_destination_id": "buyer_choice",
        "destinations": [
          {
            "id": "buyer_choice",
            "broker": { "id": "com.example-broker", "point_id": "PK-CZ-004211" }
          }
        ]
      }
    ]
  }
}
```

### Selected point no longer available

On a later update the locker is full. The Business leaves the Checkout
unchanged and returns a recoverable error on the selection.

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_7f3a",
  "status": "incomplete",
  "currency": "PLN",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "messages": [
    {
      "type": "error",
      "code": "point_full",
      "path": "$.fulfillment.methods[0].selected_destination_id",
      "content": "Parcel locker WAW99X is full. Please choose another point.",
      "severity": "recoverable"
    }
  ]
}
```

### Order: expectation, deposit, redirect, collection

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.order op=read -->
```json
{
  "ucp": { ... },
  "id": "ord_51c2",
  "checkout_id": "chk_7f3a",
  "permalink_url": "https://shop.example.com/orders/ord_51c2",
  "currency": "PLN",
  "line_items": [ ... ],
  "totals": [ ... ],
  "fulfillment": {
    "expectations": [
      {
        "id": "exp_1",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "method_type": "carrier_pickup",
        "destination": {
          "street_address": "ul. Prosta 5",
          "address_locality": "Warszawa",
          "postal_code": "00-850",
          "address_country": "PL"
        },
        "point": {
          "network": "eu.inpost",
          "country": "PL",
          "point_id": "WAW99X",
          "name": "Paczkomat WAW99X"
        },
        "description": "Ready for pickup in 1-2 business days"
      }
    ],
    "events": [
      {
        "id": "evt_1",
        "occurred_at": "2026-11-23T09:12:00Z",
        "type": "shipped",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "parcel_id": "parcel_1",
        "tracking_number": "TRK123456789",
        "tracking_url": "https://tracking.example.com/TRK123456789"
      },
      {
        "id": "evt_2",
        "occurred_at": "2026-11-24T07:40:00Z",
        "type": "deposited_at_point",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "parcel_id": "parcel_1",
        "tracking_number": "TRK123456789",
        "tracking_url": "https://tracking.example.com/TRK123456789",
        "point": { "network": "eu.inpost", "country": "PL", "point_id": "WAW99X" },
        "pickup_by": "2026-11-26T07:40:00Z"
      },
      {
        "id": "evt_3",
        "occurred_at": "2026-11-26T08:05:00Z",
        "type": "deposited_at_point",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "parcel_id": "parcel_1",
        "tracking_number": "TRK123456789",
        "tracking_url": "https://tracking.example.com/TRK123456789",
        "point": { "network": "eu.inpost", "country": "PL", "point_id": "WAW01B" },
        "pickup_by": null,
        "description": "Not collected from the locker; moved to a staffed point."
      },
      {
        "id": "evt_4",
        "occurred_at": "2026-11-27T17:21:00Z",
        "type": "collected_at_point",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "parcel_id": "parcel_1",
        "tracking_number": "TRK123456789",
        "tracking_url": "https://tracking.example.com/TRK123456789",
        "point": { "network": "eu.inpost", "country": "PL", "point_id": "WAW01B" }
      }
    ]
  }
}
```

### Order: not collected, returning, returned

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.order op=read -->
```json
{
  "ucp": { ... },
  "id": "ord_88d1",
  "checkout_id": "chk_2b90",
  "permalink_url": "https://shop.example.com/orders/ord_88d1",
  "currency": "CZK",
  "line_items": [ ... ],
  "totals": [ ... ],
  "fulfillment": {
    "events": [
      {
        "id": "evt_2",
        "occurred_at": "2026-11-24T10:00:00Z",
        "type": "deposited_at_point",
        "line_items": [{ "id": "li_book", "quantity": 1 }],
        "parcel_id": "parcel_7",
        "tracking_number": "Z0042110001",
        "tracking_url": "https://tracking.example.com/Z0042110001",
        "point": { "network": "com.packeta", "country": "CZ", "point_id": "004211" },
        "pickup_by": "2026-12-01T10:00:00Z"
      },
      {
        "id": "evt_3",
        "occurred_at": "2026-12-01T10:00:00Z",
        "type": "pickup_expired",
        "line_items": [{ "id": "li_book", "quantity": 1 }],
        "parcel_id": "parcel_7",
        "tracking_number": "Z0042110001",
        "tracking_url": "https://tracking.example.com/Z0042110001",
        "point": { "network": "com.packeta", "country": "CZ", "point_id": "004211" }
      },
      {
        "id": "evt_4",
        "occurred_at": "2026-12-02T08:00:00Z",
        "type": "returning_to_sender",
        "line_items": [{ "id": "li_book", "quantity": 1 }],
        "parcel_id": "parcel_7",
        "tracking_number": "Z0042110001",
        "tracking_url": "https://tracking.example.com/Z0042110001"
      },
      {
        "id": "evt_5",
        "occurred_at": "2026-12-04T13:30:00Z",
        "type": "returned_to_sender",
        "line_items": [{ "id": "li_book", "quantity": 1 }],
        "parcel_id": "parcel_7",
        "tracking_number": "Z0042110001",
        "tracking_url": "https://tracking.example.com/Z0042110001"
      }
    ]
  }
}
```

### Order: collection reported by mistake

The carrier reported a collection, then confirmed the parcel was still in the
locker and extended the deadline. The Business appends a correction and a
deadline change; the collection no longer counts.

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.order op=read -->
```json
{
  "ucp": { ... },
  "id": "ord_51c2",
  "checkout_id": "chk_7f3a",
  "permalink_url": "https://shop.example.com/orders/ord_51c2",
  "currency": "PLN",
  "line_items": [ ... ],
  "totals": [ ... ],
  "fulfillment": {
    "events": [
      {
        "id": "evt_2",
        "occurred_at": "2026-11-24T07:40:00Z",
        "type": "deposited_at_point",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "parcel_id": "parcel_1",
        "point": { "network": "eu.inpost", "country": "PL", "point_id": "WAW99X" },
        "pickup_by": "2026-11-26T07:40:00Z"
      },
      {
        "id": "evt_3",
        "occurred_at": "2026-11-25T12:02:00Z",
        "type": "collected_at_point",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "parcel_id": "parcel_1",
        "point": { "network": "eu.inpost", "country": "PL", "point_id": "WAW99X" }
      },
      {
        "id": "evt_4",
        "occurred_at": "2026-11-25T16:30:00Z",
        "type": "deposited_at_point",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "parcel_id": "parcel_1",
        "corrects": "evt_3",
        "corrected_at": "2026-11-25T16:30:00Z",
        "point": { "network": "eu.inpost", "country": "PL", "point_id": "WAW99X" },
        "pickup_by": "2026-11-26T07:40:00Z",
        "description": "Collection was reported in error; the parcel is still in the locker."
      },
      {
        "id": "evt_5",
        "occurred_at": "2026-11-26T06:00:00Z",
        "type": "pickup_deadline_changed",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "parcel_id": "parcel_1",
        "point": { "network": "eu.inpost", "country": "PL", "point_id": "WAW99X" },
        "pickup_by": "2026-11-28T07:40:00Z"
      }
    ]
  }
}
```
