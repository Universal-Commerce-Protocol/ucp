<!--
   Copyright 2025 Google LLC

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

## 1. Introduction

This guide defines the standard structure and vocabulary for specifying UCP
payment handlers. All payment handler specifications SHOULD follow this
structure to ensure consistency, completeness, and clarity for implementers.

### 1.1 Purpose

Payment handlers enable the "N-to-N" interoperability between agents, merchants,
and payment providers. A well-specified handler must answer these questions for
each participant:

- **Who participates?** What participants are involved and what are their roles?
- **What are my prerequisites?** What onboarding or setup is required?
- **How do I configure?** What configuration do I advertise or consume?
- **How do I execute?** What protocol do I follow to acquire or process instruments?

This guide provides a framework that ensures every handler specification answers
these questions systematically.

### 1.2 Scope

This guide applies to:

- **Handlers** (e.g., `com.google.pay`, `com.shopify.shop_pay`) — Specific
  payment method implementations

---

## 2. Core Concepts

Every payment handler specification MUST define five core elements:

```
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
│   Merchant advertises  Agent acquires        Participant                     │
│   handler config       checkout instrument   processes instrument            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Participants

**Definition:** The distinct actors that participate in the payment handler's
lifecycle. Every handler has at minimum two participants (merchant and agent),
but may define additional participants with specific roles.

**Standard Participants:**

| Participant | Role |
|:------------|:-----|
| **Merchant** | Advertises handler configuration, processes payment instruments |
| **Agent** | Discovers handlers, acquires payment instruments, submits checkout |

**Extended Participants** (example handler-specific participants):

| Participant | Example Role |
|:------------|:-------------|
| **Tokenizer** | Stores raw credentials and issues token credentials |
| **PSP** | Processes payments on behalf of merchant using the checkout instrument |

### 2.2 Prerequisites

**Definition:** The onboarding, setup, or configuration a participant must
complete before participating in the handler's flows.

**Signature:**

```
PREREQUISITES(participant, onboarding_input) → prerequisites_output
```

| Field | Description |
|:------|:------------|
| `participant` | The participant being onboarded (merchant, agent, etc.) |
| `onboarding_input` | What the participant provides during setup |
| `prerequisites_output` | The identity and any additional configuration received |

**Prerequisites Output:**

The `prerequisites_output` contains what a participant receives from onboarding.
At minimum, this includes an **identity** (see [PaymentIdentity schema](https://ucp.dev/schemas/shopping/types/payment_identity.json)).
It may also include additional configuration, credentials, or settings specific
to the handler.

Payment handler specifications do NOT need to define a formal schema for
`prerequisites_output`. Instead, the specification SHOULD clearly document:

- What identity is assigned (and how it maps to `PaymentIdentity`)
- What additional configuration is provided
- How the prerequisites output is used in Handler Declaration, Instrument Acquisition, or Processing

**Notes:**

- Prerequisites typically occur out-of-band (portals, contracts, API calls)
- Multiple participants may have independent prerequisites
- The identity from prerequisites typically appears within the handler's
  `config` object (e.g., as `merchant_id` or similar handler-specific field)
- Participants receiving raw credentials (e.g., merchants, PSPs) typically must complete security acknowledgements during onboarding, accepting responsibility for credential handling and compliance

### 2.3 Handler Declaration

**Definition:** The configuration a merchant advertises to indicate support for
this handler and enable agents to invoke it.

**Signature:**

```
HANDLER_DECLARATION(prerequisites_output) → handler_declaration
```

| Field | Description |
|:------|:------------|
| `prerequisites_output` | The identity and configuration from merchant prerequisites |
| `handler_declaration` | The complete handler object advertised in `payment.handlers[]` |

**Output Structure:**

The handler declaration conforms to the [`PaymentHandler`](https://ucp.dev/schemas/shopping/types/payment_handler.json)
schema. Your specification should define the available config and instrument
schemas, and how to construct each based on the merchant's prerequisites output
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

#### 2.3.1 Defining Your Config Schema

The `config_schema` field points to a JSON schema that validates the `config` object merchants provide. Both are optional, and there is no base config schema to extend — each handler defines its own, if needed, to assist agents in completing their Instrument Acquisition.

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
      "description": "The API environment this merchant supports for the example handler.",
      "default": "production"
    }
  }
}
```

---

#### 2.3.2 Defining Instrument Schemas

**Base Instrument Schemas:**

| Schema | Description |
|:-------|:------------|
| [`payment_instrument.json`](https://ucp.dev/schemas/shopping/types/payment_instrument.json) | Base: id, handler_id, type, credential, billing_address |
| [`card_payment_instrument.json`](https://ucp.dev/schemas/shopping/types/card_payment_instrument.json) | Card display: brand, last_digits, expiry |

UCP offers basic schemas for universal payment instruments like `card`. You can
extend any of the basic payment instruments if you want to add additional
handler-specific display data.

If your handler needs a custom instrument, extend the base `PaymentInstrument`
and define your own shape.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/handlers/my_wallet/instrument.json",
  "title": "MyWalletInstrument",
  "allOf": [
    { "$ref": "https://ucp.dev/schemas/shopping/types/payment_instrument.json" }
  ],
  "type": "object",
  "required": ["type", "account_type", "display_email"],
  "properties": {
    "type": { "const": "my_wallet" },
    "account_type": {
      "type": "string",
      "description": "The plan type for this wallet account."
    },
    "display_email": {
      "type": "string",
      "description": "The wallet account email to display."
    }
  }
}
```

#### 2.3.3 Defining Credential Schemas

**Base Credential Schemas:**

| Schema | Description |
|:-------|:------------|
| [`payment_credential.json`](https://ucp.dev/schemas/shopping/types/payment_credential.json) | Base: type discriminator only |
| [`token_credential.json`](https://ucp.dev/schemas/shopping/types/token_credential.json) | Token: type + token string |

UCP offers basic schemas for universal payment credentials like `card` and
`token`. You can extend any of the basic payment credentials if you want to add
additional handler-specific credential context.

When using credentials with your handler, be sure to define which credential
types are accepted in your handler specification.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/handlers/my_wallet/credential.json",
  "title": "MyWalletCredential",
  "type": "object",
  "required": ["type", "token", "verification_level"],
  "properties": {
    "verification_level": {
      "type": "string",
      "description": "The verification level of this wallet account."
    }
  }
}
```

### 2.4 Instrument Acquisition

**Definition:** The protocol an agent follows to acquire a payment instrument
that can be submitted to the merchant's checkout.

**Signature:**

```
INSTRUMENT_ACQUISITION(
  agent_prerequisites_output,
  handler_declaration,
  binding,
  buyer_input
) → checkout_instrument
```

| Field | Description |
|:------|:------------|
| `agent_prerequisites_output` | Agent's prerequisites output (config), if prerequisites were required |
| `handler_declaration.config` | Handler-specific configuration from the merchant |
| `binding` | Context for binding the credential to a specific checkout (`checkout_id` and `identity` should be used) |
| `buyer_input` | Buyer's payment selection or credentials |
| `checkout_instrument` | The payment instrument to submit at checkout |

Payment handler specifications do NOT need to define a formal process for
instrument acquisition. Instead, the specification SHOULD clearly document:

- How to leverage the handler's advertised `config` to respect merchant configuration and create a `checkout_instrument`.
- How to create an effective credential binding to the specific checkout and
  merchant for usage, which is critical for security, based off the available
  `config` and `checkout`.

### 2.5 Processing

**Definition:** The steps a participant (typically merchant or PSP) takes to
process a received payment instrument and complete the transaction.

**Signature:**

```
PROCESSING(
  identity,
  checkout_instrument,
  binding,
  transaction_context
) → processing_result
```

| Field | Description |
|:------|:------------|
| `identity` | The processing participant's `PaymentIdentity` |
| `checkout_instrument` | The instrument received from the agent |
| `binding` | The binding context for verification |
| `transaction_context` | Checkout totals, line items, etc. |
| `processing_result` | Success/failure with payment details |

---

## 3. Specification Template

Handler specifications SHOULD use the standard template structure. Sections
marked **[REQUIRED]** MUST be present; sections marked **[CONDITIONAL]**
are required only when applicable.

**→ [Payment Handler Template](payment-handler-template.md)**

## 4. Conformance Checklist for Spec Authors

Before publishing a payment handler specification, verify:

### 4.1 Structure

- [ ] Uses the standard template structure
- [ ] All [REQUIRED] sections are present
- [ ] [CONDITIONAL] sections are present when applicable

### 4.2 Participants

- [ ] All participants are listed
- [ ] Each participant's role is clearly described

### 4.3 Prerequisites

- [ ] Prerequisites process is documented for each participant that requires it
- [ ] Onboarding inputs are specified
- [ ] Prerequisites output is described (identity + any additional config)
- [ ] Identity maps to `PaymentIdentity` structure (`access_token`)

### 4.4 Handler Declaration

- [ ] Identity schema is documented (base or extended)
- [ ] Configuration schema is documented (if applicable)
- [ ] Instrument schema is documented (base or extended)

### 4.5 Instrument Acquisition

- [ ] Protocol steps are enumerated and clear
- [ ] API calls or SDK usage is shown with examples
- [ ] Binding requirements are specified
- [ ] Checkout PaymentInstrument creation and shape is well-defined

### 4.6 Processing

- [ ] Processing steps are enumerated and clear
- [ ] Verification requirements are specified
- [ ] Error handling is addressed

### 4.7 Security

- [ ] Security requirements are listed
- [ ] Binding verification is required
- [ ] Credential handling guidance is provided

### 4.8 General

- [ ] Handler name follows reverse-DNS convention
- [ ] Version follows YYYY-MM-DD format
- [ ] All schema URLs match namespace authority
- [ ] References section includes all schemas

---

## 5. Best Practices

Follow these guidelines to create high-quality, maintainable handler
specifications:

### 5.1 Schema Design

| Practice | Description |
|:---------|:------------|
| **Extend, don't reinvent** | Use `allOf` to compose base schemas. Don't redefine `brand`, `last_digits`, etc. |
| **Use const for discriminators** | Define `credential.type` as a `const` to identify your credential type unambiguously. |
| **Validate early** | Publish your schemas at stable URLs before finalizing the spec so implementers can validate. |

### 5.2 Documentation

| Practice | Description |
|:---------|:------------|
| **Show, don't just tell** | Include complete JSON examples for every schema and protocol step. |
| **Document error cases** | Specify what errors can occur and how participants should handle them. |
| **Version independently** | Your handler version evolves independently of UCP core versions. |

### 5.3 Security

| Practice | Description |
|:---------|:------------|
| **Require binding** | Always tie credentials to a specific checkout via `binding`. |
| **Minimize credential exposure** | Design flows so raw credentials (PANs, etc.) touch as few systems as possible. |
| **Specify token lifetimes** | Document whether tokens are single-use, time-limited, or session-scoped. |

### 5.4 Maintainability

| Practice | Description |
|:---------|:------------|
| **Host schemas at stable URLs** | Schema URLs should not change; use versioned paths if needed. |
| **Fail gracefully** | Define clear error responses for common failure scenarios. |
| **Link to examples** | Reference existing handler specs and the [Tokenization Guide](tokenization-guide.md) for common flows. |

---

## 6. See Also

- **[Tokenization Guide](tokenization-guide.md)** — Guide for building tokenization payment handlers
- **[Google Pay Handler](gpay-payment-handler.md)** — Handler for Google Pay integration
- **[Shop Pay Handler](shop-pay-handler.md)** — Handler for Shop Pay integration
