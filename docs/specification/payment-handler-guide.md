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

# Payment Handler Specification Guide

**Version:** `2026-01-11`

## Introduction

This guide defines the standard structure and vocabulary for specifying UCP
payment handlers. All payment handler specifications **SHOULD** follow this
structure to ensure consistency, completeness, and clarity for implementers.

### Purpose

Payment handlers enable "N-to-N" interoperability between platforms, businesses,
and payment providers. A well-specified handler must answer these questions for
each participant:

- **Who participates?** What participants are involved and what are their roles?
- **What are the prerequisites?** What onboarding or setup is required?
- **How is it configured?** What configuration is advertised or consumed?
- **How is it executed?** What protocol is followed to acquire or process instruments?

This guide provides a framework that ensures every handler specification answers
these questions systematically.

### Scope

This guide applies to:

- **Handlers** (e.g., `com.google.pay`, `dev.shopify.shop_pay`) — Specific
  payment method implementations

---

## Core Concepts

Every payment handler specification **MUST** define the core elements below.

**Note on Protocol Signatures:**: The function signatures provided in this
section (e.g., `PROCESSING(...)`) represent **logical data flows**, not literal
function calls. Spec authors must map these logical flows to the actual
transport protocol used by their implementation.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Payment Handler Framework                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐                                                           │
│   │ PARTICIPANTS │  Who participates in this handler?                        │
│   └──────┬───────┘                                                           │
│          │                                                                   │
│          ▼                                                                   │
│   ┌──────────────┐                                                           │
│   │PREREQUISITES │  How does each participant obtain identity & configs?     │
│   └──────┬───────┘                                                           │
│          │                                                                   │
│          ├────────────────────┬──────────────────────┐                       │
│          ▼                    ▼                      ▼                       │
│   ┌──────────────┐    ┌──────────────┐      ┌──────────────┐                 │
│   │   HANDLER    │    │  INSTRUMENT  │      │  PROCESSING  │                 │
│   │ DECLARATION  │    │  ACQUISITION │      │              │                 │
│   └──────────────┘    └──────────────┘      └──────────────┘                 │
│   Business advertises  platform acquires     Participant                     │
│   handler config       checkout instrument   processes instrument            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Participants

**Definition:** The distinct actors that participate in the payment handler's
lifecycle. Every handler has at minimum two participants (business and
platform), but **MAY** define additional participants with specific roles.

**Note on Terminology:**: While this guide refers to the participant as the
**"Business"**, technical schema fields may retain the standard industry
nomenclature **`merchant_*`** (e.g., `merchant_id`, `merchant_name`).
Specifications **MUST** explicitly document these field mappings.

**Standard Participants:**

| Participant  | Role                                                               |
| :----------- | :----------------------------------------------------------------- |
| **Business** | Advertises handler configuration, processes payment instruments    |
| **Platform** | Discovers handlers, acquires payment instruments, submits checkout |

**Extended Participants** (example handler-specific participants):

| Participant   | Example Role                                                           |
| :------------ | :--------------------------------------------------------------------- |
| **Tokenizer** | Stores raw credentials and issues token credentials                    |
| **PSP**       | Processes payments on behalf of business using the checkout instrument |

### Prerequisites

**Definition:** The onboarding, setup, or configuration a participant must
complete before participating in the handler's flows.

**Signature:**

```text
PREREQUISITES(participant, onboarding_input) → prerequisites_output
```

| Field                  | Description                                                |
| :--------------------- | :--------------------------------------------------------- |
| `participant`          | The participant being onboarded (business, platform, etc.) |
| `onboarding_input`     | What the participant provides during setup                 |
| `prerequisites_output` | The identity and any additional configuration received     |

**Prerequisites Output:**

The `prerequisites_output` contains what a participant receives from onboarding.
At minimum, this includes an **identity** (see [Payment Identity](https://ucp.dev/schemas/shopping/types/payment_identity.json)).
It **MAY** also include additional configuration, credentials, or settings
specific to the handler.

Payment handler specifications **are not required** to define a formal schema
for `prerequisites_output`. Instead, the specification **SHOULD** clearly
document:

- What identity is assigned (and how it maps to `PaymentIdentity`)
- What additional configuration is provided
- How the prerequisites output is used in Handler Declaration, Instrument Acquisition, or Processing

**Notes:**

- Prerequisites typically occur out-of-band (portals, contracts, API calls)
- Multiple participants **MAY** have independent prerequisites
- The identity from prerequisites typically appears within the handler's
  `config` object (e.g., as `merchant_id` or similar handler-specific field)
- Participants receiving raw credentials (e.g., businesses, PSPs) typically must complete security acknowledgements during onboarding, accepting responsibility for credential handling and compliance

### Handler Declaration

**Definition:** The configuration a business advertises to indicate support for
this handler and enable platforms to invoke it.

**Signature:**

```text
HANDLER_DECLARATION(prerequisites_output) → handler_declaration
```

| Field                  | Description                                                    |
| :--------------------- | :------------------------------------------------------------- |
| `prerequisites_output` | The identity and configuration from business prerequisites     |
| `handler_declaration`  | The complete handler object advertised in `payment.handlers[]` |

**Output Structure:**

The handler declaration conforms to the [`PaymentHandler`](https://ucp.dev/schemas/shopping/types/payment_handler.json)
schema. The specification **SHOULD** define the available config and instrument
schemas, and how to construct each based on the business's prerequisites output
and desired configuration.

```json
{
  "id": "handler_instance_id",
  "name": "com.example.handler",
  "version": "2026-01-11",
  "spec": "https://example.com/ucp/handler",
  "config_schema": "https://example.com/ucp/handler/config.json",
  "instrument_schemas": [
    "https://example.com/ucp/handler/instruments/card.json"
  ],
  "config": {
    // Handler-specific configuration (see 2.3.1)
  }
}
```

---

#### Defining the Config Schema

The `config_schema` field points to a JSON schema that validates the `config`
object businesses provide. Both are optional.

**Recommendation:** Most handlers require an environment setting (e.g., Sandbox
vs. Production). It is recommended to include this in the config schema to
**standardize** testing flows.

**Example Config Schema:**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/ucp/handlers/my_handler/config.json",
  "title": "MyHandlerConfig",
  "description": "Configuration for the com.example.my_handler payment handler.",
  "type": "object",
  "properties": {
    "environment": {
      "type": "string",
      "enum": ["sandbox", "production"],
      "description": "The API environment this business supports for the example handler.",
      "default": "production"
    }
  }
}
```

---

#### Defining Instrument Schemas

**Base Instrument Schemas:**

| Schema                                                                                                | Description                                             |
| :---------------------------------------------------------------------------------------------------- | :------------------------------------------------------ |
| [`payment_instrument.json`](https://ucp.dev/schemas/shopping/types/payment_instrument.json)           | Base: id, handler_id, type, credential, billing_address |
| [`card_payment_instrument.json`](https://ucp.dev/schemas/shopping/types/card_payment_instrument.json) | Card display: brand, last_digits, expiry                |

UCP provides base schemas for universal payment instruments like `card`. Spec
authors **MAY** extend any of the basic payment instruments to add additional
handler-specific display data.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/ucp/handlers/my_wallet/instrument.json",
  "title": "MyWalletInstrument",
  "allOf": [
    { "$ref": "https://ucp.dev/schemas/shopping/types/payment_instrument.json" }
  ],
  "type": "object",
  "required": ["type", "account_type"],
  "properties": {
    "type": { "const": "my_wallet" },
    // base payment instrument or specific payment instrument defined by handler
  }
}
```

#### Defining Credential Schemas

**Base Credential Schemas:**

| Schema                                                                                      | Description                   |
| :------------------------------------------------------------------------------------------ | :---------------------------- |
| [`payment_credential.json`](https://ucp.dev/schemas/shopping/types/payment_credential.json) | Base: type discriminator only |
| [`token_credential.json`](https://ucp.dev/schemas/shopping/types/token_credential.json)     | Token: type + token string    |

UCP provides base schemas for universal payment credentials like `card` and
`token`. Authors **MAY** extend these schemas to include handler-specific
credential context.

The specification **MUST** define which credential types are accepted by the
handler.

**Important:** If using token credentials, the schema MUST include an
expiration field (`expiry`, `ttl`, or similar) to ensure platforms know when to
refresh credentials.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/ucp/handlers/my_wallet/credential.json",
  "title": "MyWalletCredential",
  "type": "object",
  "required": ["type", "token"],
  "properties": {
    // base credential object or credential context defined by handler
  }
}
```

### Instrument Acquisition

**Definition:** The protocol a platform follows to acquire a payment instrument
that can be submitted to the business's checkout.

**Signature:**

```text
INSTRUMENT_ACQUISITION(
  platform_prerequisites_output,
  handler_declaration,
  binding,
  buyer_input
) → checkout_instrument
```

| Field                           | Description                                                              |
| :------------------------------ | :----------------------------------------------------------------------- |
| `platform_prerequisites_output` | platform's prerequisites output (config), if prerequisites were required |
| `handler_declaration.config`    | Handler-specific configuration from the business                         |
| `binding`                       | **(See 2.6)** Context for binding the credential to a specific checkout  |
| `buyer_input`                   | Buyer's payment selection or credentials                                 |
| `checkout_instrument`           | The payment instrument to submit at checkout                             |

Payment handler specifications do NOT need to define a formal process for
instrument acquisition. Instead, the specification **SHOULD** clearly document:

- How to apply the handler's `config` to construct a valid `checkout_instrument`.
- How to create an effective credential binding to the specific checkout and
  business for usage, which is critical for security, based on the available
  `config` and `checkout`.

### Processing

**Definition:** The steps a participant (typically business or PSP) takes to
process a received payment instrument and complete the transaction.

**Signature:**

```text
PROCESSING(
  identity,
  checkout_instrument,
  binding,
  transaction_context
) → processing_result
```

| Field                 | Description                                    |
| :-------------------- | :--------------------------------------------- |
| `identity`            | The processing participant's `PaymentIdentity` |
| `checkout_instrument` | The instrument received from the platform      |
| `binding`             | The binding context for verification           |
| `transaction_context` | Checkout totals, line items, etc.              |
| `processing_result`   | Success/failure with payment details           |

#### Error Handling

The specification **MUST** define a mapping for common failures (e.g.,
'Declined', 'Insufficient Funds', 'Network Error') to standard UCP Error
definitions. This ensures the platform can render localized, consistent
error messages to the buyer regardless of the underlying processor.

### Key Definitions

| Term        | Definition                                                                                                                                                                                                                                    |
| :---------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Binding** | A cryptographic or logical association of a payment instrument to a specific checkout transaction and business identity. This prevents replay attacks where a valid credential intended for Business A is intercepted and used at Business B. |

---

## Specification Template

Handler specifications **SHOULD** use the standard template structure. Sections
marked **[REQUIRED]** **MUST** be present; sections marked **[CONDITIONAL]**
are required only when applicable.

**→ [Payment Handler Template](payment-handler-template.md)**

## Conformance Checklist for Spec Authors

Before publishing a payment handler specification, verify:

### Structure

- [ ] Uses the standard template structure
- [ ] All [REQUIRED] sections are present
- [ ] [CONDITIONAL] sections are present when applicable

### Participants

- [ ] All participants are listed
- [ ] Each participant's role is clearly described
- [ ] Note on "Business" vs "Merchant" terminology added if applicable

### Prerequisites

- [ ] Prerequisites process is documented for each participant that requires it
- [ ] Onboarding inputs are specified
- [ ] Prerequisites output is described (identity + any additional config)
- [ ] Identity maps to `PaymentIdentity` structure (`access_token`)

### Handler Declaration

- [ ] Identity schema is documented (base or extended)
- [ ] Configuration schema is documented (if applicable) and includes environment
- [ ] Instrument schema is documented (base or extended)

### Instrument Acquisition

- [ ] Protocol steps are enumerated and clear
- [ ] Logical flow is mapped to actual protocol
- [ ] API calls or SDK usage is shown with examples
- [ ] Binding requirements are specified
- [ ] Checkout Payment Instrument creation and shape is well-defined

### Processing

- [ ] Processing steps are enumerated and clear
- [ ] Verification requirements are specified
- [ ] Error handling and mapping is addressed

### Security

- [ ] Security requirements are listed
- [ ] Binding verification is required
- [ ] Credential handling guidance is provided
- [ ] Token expiry is defined (if applicable)

### General

- [ ] Handler name follows reverse-DNS convention
- [ ] Version follows YYYY-MM-DD format
- [ ] All schema URLs match namespace authority
- [ ] References section includes all schemas

---

## Best Practices

Follow these guidelines to create high-quality, maintainable handler
specifications:

### Schema Design

| Practice                         | Description                                                                             |
| :------------------------------- | :-------------------------------------------------------------------------------------- |
| **Extend, don't reinvent**       | Use `allOf` to compose base schemas. Don't redefine `brand`, `last_digits`, etc.        |
| **Use const for discriminators** | Define `credential.type` as a `const` to identify credential types unambiguously.       |
| **Validate early**               | Publish schemas at stable URLs before finalizing the spec so implementers can validate. |
| **Include Expiry**               | When designing token credentials, always include `expiry` or `ttl`.                     |

### Documentation

| Practice                  | Description                                                            |
| :------------------------ | :--------------------------------------------------------------------- |
| **Show, don't just tell** | Include complete JSON examples for every schema and protocol step.     |
| **Document error cases**  | Specify what errors can occur and how participants should handle them. |
| **Version independently** | The handler version evolves independently of UCP core versions.        |

### Security

| Practice                         | Description                                                                    |
| :------------------------------- | :----------------------------------------------------------------------------- |
| **Require binding**              | Always tie credentials to a specific checkout via `binding`.                   |
| **Minimize credential exposure** | Design flows so raw credentials (PANs, etc.) touch as few systems as possible. |
| **Specify token lifetimes**      | Document whether tokens are single-use, time-limited, or session-scoped.       |

### Maintainability

| Practice                        | Description                                                                                            |
| :------------------------------ | :----------------------------------------------------------------------------------------------------- |
| **Host schemas at stable URLs** | Schema URLs should not change; use versioned paths if needed.                                          |
| **Fail gracefully**             | Define clear error responses for common failure scenarios.                                             |
| **Link to examples**            | Reference existing handler specs and the [Tokenization Guide](tokenization-guide.md) for common flows. |

---

## See Also

- **[Tokenization Guide](tokenization-guide.md)** — Guide for building
  tokenization payment handlers
- **[Google Pay Handler](https://developers.google.com/merchant/ucp/guides/google-pay-payment-handler){ target="_blank" }**
  — Handler for Google Pay integration
- **[Shop Pay Handler](https://shopify.dev/docs/agents/checkout/shop-pay-handler){ target="_blank" }**
  — Handler for Shop Pay integration
