# Payment Handler Specification Guide

## Introduction

This guide defines the standard structure and vocabulary for specifying UCP payment handlers. All payment handler specifications **SHOULD** follow this structure to ensure consistency, completeness, and clarity for implementers.

### Purpose

Payment handlers enable "N-to-N" interoperability between platforms, businesses, and payment providers. A well-specified handler must answer these questions for each participant:

- **Who participates?** What participants are involved and what are their roles?
- **What are the prerequisites?** What onboarding or setup is required?
- **How is it configured?** What configuration is advertised or consumed?
- **How is it executed?** What protocol is followed to acquire or process instruments?

This guide provides a framework that ensures every handler specification answers these questions systematically.

### Scope

This guide applies to:

- **Handlers** (e.g., `com.google.pay`, `dev.shopify.shop_pay`) — Specific payment method implementations

______________________________________________________________________

## Core Concepts

Every payment handler specification **MUST** define the core elements below.

**Note on Protocol Signatures:**: The function signatures provided in this section (e.g., `PROCESSING(...)`) represent **logical data flows**, not literal function calls. Spec authors must map these logical flows to the actual transport protocol used by their implementation.

```text
+------------------------------------------------------------------------------+
|                        Payment Handler Framework                             |
+------------------------------------------------------------------------------+
|                                                                              |
|   +--------------+                                                           |
|   | PARTICIPANTS |  Who participates in this handler?                        |
|   +------+-------+                                                           |
|          |                                                                   |
|          v                                                                   |
|   +--------------+                                                           |
|   |PREREQUISITES |  How does each participant obtain identity & configs?     |
|   +------+-------+                                                           |
|          |                                                                   |
|          +--------------------+----------------------+                       |
|          v                    v                      v                       |
|   +--------------+    +--------------+      +--------------+                 |
|   |   HANDLER    |    |  INSTRUMENT  |      |  PROCESSING  |                 |
|   | DECLARATION  |    |  ACQUISITION |      |              |                 |
|   +--------------+    +--------------+      +--------------+                 |
|   Business advertises  platform acquires     Participant                     |
|   handler config       checkout instrument   processes instrument            |
|                                                                              |
+------------------------------------------------------------------------------+
```

### Participants

**Definition:** The distinct actors that participate in the payment handler's lifecycle. Every handler has at minimum two participants (business and platform), but **MAY** define additional participants with specific roles.

**Note on Terminology:**: While this guide refers to the participant as the **"Business"**, technical schema fields may retain the standard industry nomenclature **`merchant_*`** (e.g., `merchant_id`, `merchant_name`). Specifications **MUST** explicitly document these field mappings.

**Standard Participants:**

| Participant  | Role                                                               |
| ------------ | ------------------------------------------------------------------ |
| **Business** | Advertises handler configuration, processes payment instruments    |
| **Platform** | Discovers handlers, acquires payment instruments, submits checkout |

**Extended Participants** (example handler-specific participants):

| Participant   | Example Role                                                           |
| ------------- | ---------------------------------------------------------------------- |
| **Tokenizer** | Stores raw credentials and issues token credentials                    |
| **PSP**       | Processes payments on behalf of business using the checkout instrument |

### Prerequisites

**Definition:** The onboarding, setup, or configuration a participant must complete before participating in the handler's flows.

**Signature:**

```text
PREREQUISITES(participant, onboarding_input) → prerequisites_output
```

| Field                  | Description                                                |
| ---------------------- | ---------------------------------------------------------- |
| `participant`          | The participant being onboarded (business, platform, etc.) |
| `onboarding_input`     | What the participant provides during setup                 |
| `prerequisites_output` | The identity and any additional configuration received     |

**Prerequisites Output:**

The `prerequisites_output` contains what a participant receives from onboarding. At minimum, this includes an **identity** (see [Payment Identity](https://ucp.dev/schemas/shopping/types/payment_identity.json)). It **MAY** also include additional configuration, credentials, or settings specific to the handler.

Payment handler specifications **are not required** to define a formal schema for `prerequisites_output`. Instead, the specification **SHOULD** clearly document:

- What identity is assigned (and how it maps to `PaymentIdentity`)
- What additional configuration is provided
- How the prerequisites output is used in Handler Declaration, Instrument Acquisition, or Processing

**Notes:**

- Prerequisites typically occur out-of-band (portals, contracts, API calls)
- Multiple participants **MAY** have independent prerequisites
- The identity from prerequisites typically appears within the handler's `config` object (e.g., as `merchant_id` or similar handler-specific field)
- Participants receiving raw credentials (e.g., businesses, PSPs) typically must complete security acknowledgements during onboarding, accepting responsibility for credential handling and compliance

### Handler Declaration

**Definition:** The configuration a business advertises to indicate support for this handler and enable platforms to invoke it.

**Signature:**

```text
HANDLER_DECLARATION(prerequisites_output) → handler_declaration
```

| Field                  | Description                                                |
| ---------------------- | ---------------------------------------------------------- |
| `prerequisites_output` | The identity and configuration from business prerequisites |
| `handler_declaration`  | The handler object advertised in `ucp.payment_handlers`    |

**Output Structure:**

The handler declaration conforms to the [`PaymentHandler`](https://ucp.dev/schemas/payment_handler.json) schema. The specification **SHOULD** define the available config and instrument schemas, and how to construct each based on the business's prerequisites output and desired configuration.

```json
{
  "ucp": {
    "payment_handlers": {
      "com.example.handler": [
        {
          "id": "processor_tokenizer_1234",
          "version": "2026-01-11",
          "spec": "https://example.com/ucp/handler",
          "schema": "https://example.com/ucp/handler/schema.json",
          "config": {
            // Handler-specific configuration (see 2.3.1)
          }
        }
      ]
    }
  }
}
```

______________________________________________________________________

#### Handler Declaration Variants

The `PaymentHandler` schema defines three variants for different contexts. While only `id` and `version` are technically required, each variant serves a distinct purpose and typically includes different configuration:

| Variant             | Context                                 | Purpose                                                                                                                                                                                             |
| ------------------- | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **business_schema** | Business discovery (`/.well-known/ucp`) | Declares the business identity and how they're configured for this handler. Contains merchant-specific settings.                                                                                    |
| **platform_schema** | Platform profile (advertised URI)       | Declares the platform identity and how it supports this handler. Includes `spec` and `schema` URLs for implementers.                                                                                |
| **response_schema** | Checkout/Order API responses            | **Runtime configuration** with merged context: merchant identity, available payment methods, tokenization specs, and other state needed to process the transaction. Often the richest of the three. |

**Business Schema Example** (business declares handler configuration):

```json
{
  "id": "processor_tokenizer_1234",
  "version": "2026-01-11",
  "spec": "https://example.com/ucp/handler",
  "schema": "https://example.com/ucp/handler/schema.json",
  "config": {
    "environment": "production",
    "business_id": "business_xyz_789"
  }
}
```

**Platform Schema Example** (platform declares handler support):

```json
{
  "id": "platform_tokenizer_2345", // note: ids are for disambiguation, they may differ between business and platform
  "version": "2026-01-11",
  "spec": "https://example.com/ucp/handler",
  "schema": "https://example.com/ucp/handler/schema.json",
  "config": {
    "environment": "production",
    "platform_id": "platform_abc_123"
  }
}
```

**Response Schema Example** (runtime context for checkout):

```json
{
  "id": "processor_tokenizer_1234",
  "version": "2026-01-11",
  "config": {
    "api_version": 2,
    "environment": "production",
    "business_id": "business_xyz_789",
    "available_instruments": [
      {
        "type": "token_alt",
        "tokenization_specification": {
          "type": "merchant_gateway"
        }
      }
    ]
  }
}
```

______________________________________________________________________

#### Defining the Schema

The `schema` field points to a JSON schema that defines handler-specific shapes. Authors typically define each shape in its own file and reference them:

- **Config** — Configuration for platform/business declarations and runtime responses
- **Instrument** — The payment instrument structure returned to platforms
- **Credential** — The credential structure within instruments

**Example Handler Schema:**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/ucp/handlers/tokenizer/schema.json",
  "title": "Tokenizer Handler Schema",
  "description": "Schema for the com.example.tokenizer payment handler.",
  "name": "com.example.tokenizer",
  "version": "2026-01-11",

  "$defs": {
    "tokenizer_token": { "$ref": "types/tokenizer_token.json" },
    "tokenizer_alt_token": { "$ref": "types/tokenizer_alt_token.json" },

    "tokenizer_instrument": { "$ref": "types/tokenizer_instrument.json" },
    "tokenizer_alt_instrument": { "$ref": "types/tokenizer_alt_instrument.json" },

    "com.example.tokenizer": {
      "payment_instrument": {
        "title": "Tokenizer Payment Instrument",
        "description": "Any instrument type supported by this handler.",
        "oneOf": [
          { "$ref": "#/$defs/tokenizer_instrument" },
          { "$ref": "#/$defs/tokenizer_alt_instrument" }
        ]
      },
      "platform_schema": {
        "title": "Tokenizer (Platform)",
        "description": "Platform-level handler configuration for discovery.",
        "allOf": [
          { "$ref": "https://ucp.dev/schemas/payment_handler.json#/$defs/platform_schema" },
          {
            "properties": {
              "config": {
                "$ref": "types/platform_config.json",
                "description": "Platform configuration for this handler."
              }
            }
          }
        ]
      },
      "business_schema": {
        "title": "Tokenizer (Business)",
        "description": "Business-level handler configuration for discovery.",
        "allOf": [
          { "$ref": "https://ucp.dev/schemas/payment_handler.json#/$defs/business_schema" },
          {
            "properties": {
              "config": {
                "$ref": "types/business_config.json",
                "description": "Business configuration for this handler."
              }
            }
          }
        ]
      },
      "response_schema": {
        "title": "Tokenizer (Response)",
        "description": "Runtime handler configuration in checkout responses.",
        "allOf": [
          { "$ref": "https://ucp.dev/schemas/payment_handler.json#/$defs/response_schema" },
          {
            "properties": {
              "config": {
                "$ref": "types/response_config.json",
                "description": "Runtime configuration for this handler."
              }
            }
          }
        ]
      }
    }
  }
}
```

______________________________________________________________________

#### Config Shapes

Each variant has its own config schema tailored to its context:

| Variant             | Config File                  | Purpose                                                               |
| ------------------- | ---------------------------- | --------------------------------------------------------------------- |
| **business_schema** | `types/business_config.json` | Business identity and merchant-specific settings                      |
| **platform_schema** | `types/platform_config.json` | Platform identity and platform-level settings                         |
| **response_schema** | `types/response_config.json` | Full runtime state: identities, available methods, tokenization specs |

**Example `types/business_config.json`:**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/ucp/handlers/tokenizer/types/business_config.json",
  "title": "Tokenizer Business Config",
  "type": "object",
  "properties": {
    "environment": {
      "type": "string",
      "enum": ["sandbox", "production"],
      "default": "production"
    },
    "business_id": {
      "type": "string",
      "description": "Business identifier for this handler."
    }
  }
}
```

**Example `types/platform_config.json`:**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/ucp/handlers/tokenizer/types/platform_config.json",
  "title": "Tokenizer Platform Config",
  "type": "object",
  "properties": {
    "environment": {
      "type": "string",
      "enum": ["sandbox", "production"],
      "default": "production"
    },
    "platform_id": {
      "type": "string",
      "description": "Platform identifier for this handler."
    }
  }
}
```

**Example `types/response_config.json`:**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/ucp/handlers/tokenizer/types/response_config.json",
  "title": "Tokenizer Response Config",
  "type": "object",
  "properties": {
    "api_version": { "type": "integer" },
    "environment": {
      "type": "string",
      "enum": ["sandbox", "production"]
    },
    "business_id": {
      "type": "string",
      "description": "Business identifier for this handler."
    },
    "available_instruments": {
      "type": "array",
      "description": "Available instrument types for this checkout.",
      "items": {
        "type": "object",
        "properties": {
          "type": { "type": "string" },
          "tokenization_specification": { "type": "object" }
        }
      }
    }
  }
}
```

______________________________________________________________________

#### Instrument Shapes

**Base Instrument Schemas:**

| Schema                                                                                                | Description                                                      |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [`payment_instrument.json`](https://ucp.dev/schemas/shopping/types/payment_instrument.json)           | Base: id, handler_id, type, billing_address, credential, display |
| [`card_payment_instrument.json`](https://ucp.dev/schemas/shopping/types/card_payment_instrument.json) | Extends base with display: brand, last_digits, expiry, card art  |

UCP provides base schemas for universal payment instruments like `card`. Spec authors **MAY** extend any of the base instruments to add handler-specific display data or customize the credential reference. Handlers **MAY** define multiple instrument types for different payment flows.

**Example `types/tokenizer_instrument.json`** (card-based):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/ucp/handlers/tokenizer/types/tokenizer_instrument.json",
  "title": "Tokenizer Card Instrument",
  "description": "Card-based payment instrument for com.example.tokenizer.",
  "allOf": [
    { "$ref": "https://ucp.dev/schemas/shopping/types/card_payment_instrument.json" }
  ],
  "type": "object",
  "required": ["type"],
  "properties": {
    "type": { "const": "tokenizer_card" },
    "credential": {
      "oneOf": [
        { "$ref": "tokenizer_token.json" },
        { "$ref": "tokenizer_alt_token.json" }
      ]
    },
    "special_tokenizer_context": {
      "type": "object",
      "description": "Handler-specific context for tokenizer instruments."
    }
  }
}
```

**Example `types/tokenizer_alt_instrument.json`:**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/ucp/handlers/tokenizer/types/tokenizer_alt_instrument.json",
  "title": "Tokenizer Alt Instrument",
  "description": "Alternative payment instrument for com.example.tokenizer.",
  "allOf": [
    { "$ref": "https://ucp.dev/schemas/shopping/types/payment_instrument.json" }
  ],
  "type": "object",
  "required": ["type"],
  "properties": {
    "type": { "const": "tokenizer_alt" },
    "credential": {
      "oneOf": [
        { "$ref": "tokenizer_token.json" },
        { "$ref": "tokenizer_alt_token.json" }
      ]
    },
    "special_tokenizer_context": {
      "type": "object",
      "description": "Handler-specific context for tokenizer instruments."
    }
  }
}
```

______________________________________________________________________

#### Credential Shapes

**Base Credential Schemas:**

| Schema                                                                                      | Description                   |
| ------------------------------------------------------------------------------------------- | ----------------------------- |
| [`payment_credential.json`](https://ucp.dev/schemas/shopping/types/payment_credential.json) | Base: type discriminator only |
| [`token_credential.json`](https://ucp.dev/schemas/shopping/types/token_credential.json)     | Token: type + token string    |

UCP provides base schemas for universal payment credentials. Authors **MAY** extend these schemas to include handler-specific credential context. Handlers **MAY** define multiple credential types for different instrument flows.

The specification **MUST** define which credential types are accepted by the handler.

**Important:** If using token credentials, the schema **MUST** include an expiration field (`expiry`, `ttl`, or similar) to ensure platforms know when to refresh credentials.

**Example `types/tokenizer_token.json`** (expiring token):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/ucp/handlers/tokenizer/types/tokenizer_token.json",
  "title": "Tokenizer Card Token",
  "description": "Card token credential for com.example.tokenizer.",
  "allOf": [
    { "$ref": "https://ucp.dev/schemas/shopping/types/token_credential.json" }
  ],
  "type": "object",
  "required": ["type", "token", "expiry"],
  "properties": {
    "type": {
      "const": "tokenizer_card_token",
      "description": "Credential type discriminator."
    },
    "expiry": {
      "type": "string",
      "format": "date-time",
      "description": "Token expiration. Platforms must refresh before this time."
    }
  }
}
```

**Example `types/tokenizer_alt_token.json`** (alt token):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/ucp/handlers/tokenizer/types/tokenizer_alt_token.json",
  "title": "Tokenizer Alt Token",
  "description": "Alt token credential for com.example.tokenizer, adding routing hints",
  "allOf": [
    { "$ref": "https://ucp.dev/schemas/shopping/types/token_credential.json" }
  ],
  "type": "object",
  "required": ["type", "token", "expiry"],
  "properties": {
    "type": {
      "const": "tokenizer_alt_token",
      "description": "Credential type discriminator."
    },
    "expiry": {
      "type": "string",
      "format": "date-time",
      "description": "Token expiration. Platforms must refresh before this time."
    },
    "routing_hint": {
      "type": "string",
      "description": "Optional routing number hint."
    }
  }
}
```

### Instrument Acquisition

**Definition:** The protocol a platform follows to acquire a payment instrument that can be submitted to the business's checkout.

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
| ------------------------------- | ------------------------------------------------------------------------ |
| `platform_prerequisites_output` | platform's prerequisites output (config), if prerequisites were required |
| `handler_declaration.config`    | Handler-specific configuration from the business                         |
| `binding`                       | **(See 2.6)** Context for binding the credential to a specific checkout  |
| `buyer_input`                   | Buyer's payment selection or credentials                                 |
| `checkout_instrument`           | The payment instrument to submit at checkout                             |

Payment handler specifications do NOT need to define a formal process for instrument acquisition. Instead, the specification **SHOULD** clearly document:

- How to apply the handler's `config` to construct a valid `checkout_instrument`.
- How to create an effective credential binding to the specific checkout and business for usage, which is critical for security, based on the available `config` and `checkout`.

### Processing

**Definition:** The steps a participant (typically business or PSP) takes to process a received payment instrument and complete the transaction.

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
| --------------------- | ---------------------------------------------- |
| `identity`            | The processing participant's `PaymentIdentity` |
| `checkout_instrument` | The instrument received from the platform      |
| `binding`             | The binding context for verification           |
| `transaction_context` | Checkout totals, line items, etc.              |
| `processing_result`   | Success/failure with payment details           |

#### Error Handling

The specification **MUST** define a mapping for common failures (e.g., 'Declined', 'Insufficient Funds', 'Network Error') to standard UCP Error definitions. This ensures the platform can render localized, consistent error messages to the buyer regardless of the underlying processor.

### Key Definitions

| Term        | Definition                                                                                                                                                                                                                                    |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Binding** | A cryptographic or logical association of a payment instrument to a specific checkout transaction and business identity. This prevents replay attacks where a valid credential intended for Business A is intercepted and used at Business B. |

______________________________________________________________________

## Specification Template

Handler specifications **SHOULD** use the standard template structure. Sections marked **[REQUIRED]** **MUST** be present; sections marked **[CONDITIONAL]** are required only when applicable.

**→ [Payment Handler Template](https://ucp.dev/draft/specification/payment-handler-template/index.md)**

## Conformance Checklist for Spec Authors

Before publishing a payment handler specification, verify:

### Structure

- Uses the standard template structure
- All [REQUIRED] sections are present
- [CONDITIONAL] sections are present when applicable

### Participants

- All participants are listed
- Each participant's role is clearly described
- Note on "Business" vs "Merchant" terminology added if applicable

### Prerequisites

- Prerequisites process is documented for each participant that requires it
- Onboarding inputs are specified
- Prerequisites output is described (identity + any additional config)
- Identity maps to `PaymentIdentity` structure (`access_token`)

### Handler Declaration

- Identity schema is documented (base or extended)
- Configuration schema is documented (if applicable) and includes environment
- Instrument schema is documented (base or extended)

### Instrument Acquisition

- Protocol steps are enumerated and clear
- Logical flow is mapped to actual protocol
- API calls or SDK usage is shown with examples
- Binding requirements are specified
- Checkout Payment Instrument creation and shape is well-defined

### Processing

- Processing steps are enumerated and clear
- Verification requirements are specified
- Error handling and mapping is addressed

### Security

- Security requirements are listed
- Binding verification is required
- Credential handling guidance is provided
- Token expiry is defined (if applicable)

### General

- Handler name follows reverse-DNS convention
- Version follows YYYY-MM-DD format
- All schema URLs match namespace authority
- References section includes all schemas

______________________________________________________________________

## Best Practices

Follow these guidelines to create high-quality, maintainable handler specifications:

### Schema Design

| Practice                         | Description                                                                             |
| -------------------------------- | --------------------------------------------------------------------------------------- |
| **Extend, don't reinvent**       | Use `allOf` to compose base schemas. Don't redefine `brand`, `last_digits`, etc.        |
| **Use const for discriminators** | Define `credential.type` as a `const` to identify credential types unambiguously.       |
| **Validate early**               | Publish schemas at stable URLs before finalizing the spec so implementers can validate. |
| **Include Expiry**               | When designing token credentials, always include `expiry` or `ttl`.                     |

### Documentation

| Practice                  | Description                                                            |
| ------------------------- | ---------------------------------------------------------------------- |
| **Show, don't just tell** | Include complete JSON examples for every schema and protocol step.     |
| **Document error cases**  | Specify what errors can occur and how participants should handle them. |
| **Version independently** | The handler version evolves independently of UCP core versions.        |

### Security

| Practice                         | Description                                                                    |
| -------------------------------- | ------------------------------------------------------------------------------ |
| **Require binding**              | Always tie credentials to a specific checkout via `binding`.                   |
| **Minimize credential exposure** | Design flows so raw credentials (PANs, etc.) touch as few systems as possible. |
| **Specify token lifetimes**      | Document whether tokens are single-use, time-limited, or session-scoped.       |

### Maintainability

| Practice                        | Description                                                                                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Host schemas at stable URLs** | Schema URLs should not change; use versioned paths if needed.                                                                                    |
| **Fail gracefully**             | Define clear error responses for common failure scenarios.                                                                                       |
| **Link to examples**            | Reference existing handler specs and the [Tokenization Guide](https://ucp.dev/draft/specification/tokenization-guide/index.md) for common flows. |

______________________________________________________________________

## See Also

- **[Tokenization Guide](https://ucp.dev/draft/specification/tokenization-guide/index.md)** — Guide for building tokenization payment handlers
- **[Google Pay Handler](https://developers.google.com/merchant/ucp/guides/google-pay-payment-handler)** — Handler for Google Pay integration
- **[Shop Pay Handler](https://shopify.dev/docs/agents/checkout/shop-pay-handler)** — Handler for Shop Pay integration
