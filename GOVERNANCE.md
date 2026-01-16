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

# Governance

## Core Principles

* Members are chosen and promoted to various committees based on their actual
    contributions.
* Members work towards the overall health and adoption of a more open
    ecosystem and agnostic to interests of the companies they represent.

## Contributors

* Open - Anyone can contribute but needs to sign a contributor license.
    See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.
* All code changes need to be approved by at least 1 maintainer elected by
    Tech Council (TC) and all TC members are cc’ed.

## Maintainers

* Responsible for reviewing and approving code changes to ensure they align
    with the project's technical standards and governance principles.
* Build tools and documentation to facilitate adoption of the protocol.
* Tech Council (TC) can add, remove & nominate maintainers as needed.
* All code changes require approval from at least one Maintainer.

### Domain Working Groups (DWG)

* Because the TC cannot be experts in every field, Domain Working Groups
    (DWG) may be formed as a natural part of expanding the protocol.
* DWG are subject to TC oversight - all DWG artifacts must be reviewed and
    approved by the TC.
* Acts as the consensus venue for industry participants (e.g., multiple
    airlines) to agree on shared interoperability standards within the
    protocol, maintain the specific documentation and implementation guides for
    their domain's capabilities.
* A group of 3+ organizations can submit a charter to the Governing Council
    to form a DWG (e.g., "Travel WG"). Once chartered, the DWG has autonomy to
    define capabilities for their domain and submit for TC approvals.

## Tech Council (TC)

* Responsible for maintaining core technical changes to the spec, e.g., adding
    new features, reviewing enhancement proposals etc.
* Elected by the Governing Council (GC).
* Includes 8 core members, 4 from each founding organization (Google &
    Shopify), each with 1 vote (total 8 votes).
* Includes 4 members from any org, each with 1 vote (total 4 votes), elected
    by the TC every 6 months, based on their technical contributions towards the
    protocol. Members can be re-elected any number of times.
* Decisions are made with a majority vote.
* Any TC member may request a review from the Governing Council at any time
    for any additional inputs.

## Governing Council (GC)

* Responsible for governance, overall health and adoption of the protocol.
* GC serves as the ultimate owner of all UCP assets. Google
    acts as the custodian of the UCP.dev domain, holding and managing it solely
    for the benefit of the Council and the partnership’s collective interests.
* Includes a total of 2 core members, with each founding organization
    (Google & Shopify) having 1 core member, each with 1 vote (total 2 votes).
* Includes 1 member elected annually by the GC for contributions to the
    protocol's health and adoption from any organization. For the first year,
    this seat is open, and Google holds the proxy vote for this seat, to
    facilitate rapid early stage growth & adoption of the protocol.
* Can add/remove TC members via simple majority vote.
* May choose to review and veto TC decision or recommendation.
* Decisions are made with a majority vote.

## Operational Rules and Process

### Enhancement proposals

For any significant change to the protocol, such as adding a new capability,
altering a core construct, or changing a fundamental behavior, a written
enhancement proposal must be submitted to the TC.

An enhancement proposal is a living artifact that tracks a proposal through its
lifecycle:

* **Provisional:** The initial stage where the idea is proposed and debated
    within the community. In order to move to the next stage, the enhancement
    proposal will need to be approved by a simple majority of the TC.
* **Implementable:** The stage after the design has been finalized and has
    received formal approval from at least one maintainer and one member of the
    TC.
* **Implemented:** The final stage, reached when the code for the feature is
    complete, tested, documented, and merged.

Every enhancement proposal must follow a standard template requiring sections
for a Summary, Motivation, Detailed Design, Risks, a Test Plan, and Graduation
Criteria (defining the path from Alpha to Beta to General Availability). This
creates a permanent, public design record for the project's evolution.

### Voting and decision making

The path below should be followed for resolving issues that are technical in
nature.

* **L1:** routine changes (bug fixes, documentation, minor improvements) are
    auto-approved after 1 business day if no blocks are raised (silence =
    consent).
* **L2:** For non-major version increments and standard changes, proposals are
    auto-approved after 5 business days if no objections are raised and there is
    at least one +1 from a maintainer. If objections are raised, contributors
    have 3 business days to reach a resolution.
* **L3:** If unresolved after 5 business days, the relevant maintainer makes a
    binding decision based on technical merit and speed.
* **L4:** Any technical issues that span across topics and cannot be resolved
    amongst maintainers and DWGs will be escalated to the TC. Significant
    changes affecting core protocol architecture must follow the Enhancement
    Proposal process, requiring TC approval before implementation.
* **L5:** If a conflict impacts the core protocol’s scope or business
    strategy, it escalates to the Governing Council.

The TC reserves the right to stop any discussions deemed non-critical to the
protocol.

### Versioning

The base protocol uses date based versioning. Major version increments (breaking
changes) require a majority Governing Council approval due to the high cost
to the ecosystem. A quorum requires all Governing Council members (or
appropriate representatives) to be present for decision-making. New features
should typically be attempted through the extensions framework first. If an
extension achieves significant usage, it can be considered for adoption into the
next minor version of the core.

## Communication

To ensure the protocol remains open and agnostic, all governance activities must
be visible, accessible, and searchable. All communication that is intended to be
public (concerning, e.g., adding a capability before creating an extension,
debating one approach versus another, or announcements relating to upcoming
launches, etc.) shall take place on a shared Google group with a mailing list.
This includes discussion on enhancement proposals, announcements about official
specification changes and final governance votes.

* **TC & DWG Meetings:** Agendas should be posted 24 hours in advance. Minutes
    and meeting notes should be published to the repository within 1 week of the
    meeting conclusion. TC reserves the right to redact or edit meeting notes as
    needed.
* **Governing Council Meetings:** Summaries of strategic decisions and budget
    allocations will be published quarterly (specific sensitive partnership
    discussions may remain private).
