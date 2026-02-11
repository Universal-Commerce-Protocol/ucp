# {Handler Name} Payment Handler

- **Handler Name:** `{reverse-dns.name}`
- **Version:** `{YYYY-MM-DD}`

## Introduction

{Brief description of what this handler enables and the payment flow it supports.}

### Key Benefits

- {Benefit 1}
- {Benefit 2}
- {Benefit 3}

### Integration Guide

| Participant  | Integration Section                           |
| ------------ | --------------------------------------------- |
| **Business** | [Business Integration](#business-integration) |
| **Platform** | [Platform Integration](#platform-integration) |

______________________________________________________________________

## Participants

{Describe all participants in this handler and their roles.}

> **Note on Terminology:** While this specification refers to the participant as the **"business,"** technical schema fields may retain the standard industry nomenclature **`merchant_*`** (e.g., `merchant_id`). Mappings are documented below.

| Participant             | Role               | Prerequisites                |
| ----------------------- | ------------------ | ---------------------------- |
| **Business**            | {role description} | {Yes/No — brief description} |
| **Platform**            | {role description} | {Yes/No — brief description} |
| **{Other Participant}** | {role description} | {Yes/No — brief description} |

{Optional: ASCII diagram showing participant relationships}

```text
+---------+     +---------------+     +------------+
|Platform |     |   {Provider}  |     |  Business  |
+----+----+     +-------+-------+     +------+-----+
     |                  |                    |
     |  {step 1}        |                    |
     |----------------->|                    |
     |                  |                    |
     |  {step 2}        |                    |
     |<-----------------|                    |
     |                  |                    |
     |  {step 3}                             |
     |-------------------------------------->|
```

______________________________________________________________________

## Business Integration

### Prerequisites

Before advertising this handler, businesses **MUST** complete:

1. {Prerequisite 1, e.g., "Register with {provider} to obtain a business identifier"}
1. {Prerequisite 2}

**Prerequisites Output:**

| Field                   | Description                                      |
| ----------------------- | ------------------------------------------------ |
| `identity.access_token` | {what identifier is assigned, e.g., business_id} |
| {additional config}     | {any additional configuration from onboarding}   |

### Handler Configuration

Businesses advertise support for this handler in their UCP profile's `payment_handlers` registry.

#### Handler Schema

**Schema URL:** `{schema_url}`

The handler schema defines three config variants for different contexts. See [Payment Handler Guide: Defining the Schema](https://ucp.dev/draft/specification/payment-handler-guide/#defining-the-schema) for the full pattern.

| Config Variant    | Context            | Purpose                             |
| ----------------- | ------------------ | ----------------------------------- |
| `business_config` | Business discovery | {describe business-specific fields} |
| `platform_config` | Platform discovery | {describe platform-specific fields} |
| `response_config` | Checkout responses | {describe runtime fields}           |

#### Business Config Fields

| Field   | Type   | Required | Description   |
| ------- | ------ | -------- | ------------- |
| {field} | {type} | {Yes/No} | {description} |

#### Response Config Fields

| Field   | Type   | Required | Description                                                       |
| ------- | ------ | -------- | ----------------------------------------------------------------- |
| {field} | {type} | {Yes/No} | {description — include runtime fields like available instruments} |

#### Example Handler Declaration

```json
{
  "ucp": {
    "version": "2026-01-11",
    "payment_handlers": {
      "{handler_name}": [
        {
          "id": "{handler_id}",
          "version": "{version}",
          "spec": "{spec_url}",
          "schema": "{schema_url}",
          "config": {
            // Handler-specific configuration
          }
        }
      ]
    }
  }
}
```

### Processing Payments

Upon receiving a payment with this handler's instrument, businesses **MUST**:

1. **Validate Handler:** Confirm `instrument.handler_id` matches an advertised handler.
1. **Ensure Idempotency:** If the request is a retry (matches a previous `checkout_id` or idempotency key), return the previous result immediately without re-processing funds.
1. **{Step 3}:** {description}
1. **{Step 4}:** {description}
1. **Return Response:** Respond with the finalized checkout state.

{Include example request/response if the business calls an external service}

______________________________________________________________________

## Platform Integration

### Prerequisites

Before using this handler, Platforms **MUST** complete:

1. {Prerequisite 1, e.g., "Register with {provider} to obtain a Platform identifier"}
1. {Prerequisite 2}

**Prerequisites Output:**

| Field                   | Description                                    |
| ----------------------- | ---------------------------------------------- |
| `identity.access_token` | {what identifier is assigned}                  |
| {additional config}     | {any additional configuration from onboarding} |

### Handler Configuration

Platforms advertise support for this handler in their UCP profile's `payment_handlers` registry using `platform_config`.

#### Platform Config Fields

| Field   | Type   | Required | Description   |
| ------- | ------ | -------- | ------------- |
| {field} | {type} | {Yes/No} | {description} |

#### Example Platform Handler Declaration

```json
{
  "ucp": {
    "version": "2026-01-11",
    "payment_handlers": {
      "{handler_name}": [
        {
          "id": "{handler_id}",
          "version": "{version}",
          "spec": "{spec_url}",
          "schema": "{schema_url}",
          "config": {
            // Platform-specific configuration
          }
        }
      ]
    }
  }
}
```

### Payment Protocol

Platforms **MUST** follow this flow to acquire a payment instrument:

#### Step 1: Discover Handler

The Platform identifies `{handler_name}` in the business's UCP profile `payment_handlers` registry (from `/.well-known/ucp`).

```json
{
  "ucp": {
    "payment_handlers": {
      "{handler_name}": [
        {
          "id": "{handler_id}",
          "version": "{version}",
          "config": {
            // Business's configuration
          }
        }
      ]
    }
  }
}
```

#### Step 2:

{Description of what the Platform does in this step.}

{Code example if applicable:}

```javascript
// Example SDK usage or API call
```

#### Step 3:

{Continue for all steps...}

#### Step N: Complete Checkout

The Platform submits the checkout with the constructed payment instrument.

```json
POST /checkout-sessions/{checkout_id}/complete
Content-Type: application/json

{
  "payment": {
    "instruments": [
      {
        "id": "{instrument_id}",
        "handler_id": "{handler_id}",
        "type": "{instrument_type}",
        "credential": {
          "type": "{credential_type}",
          // Credential fields
        }
        // Additional instrument fields
      }
    ]
  },
  "risk_signals": {
    // risk signal objects here
  }
}
```

______________________________________________________________________

## {Participant} Integration

### Prerequisites

Before participating in this handler's flow, {participants} **MUST** complete:

1. {Prerequisite 1}
1. {Prerequisite 2}

**Prerequisites Output:**

| Field                   | Description                                    |
| ----------------------- | ---------------------------------------------- |
| `identity.access_token` | {what identifier is assigned}                  |
| {additional config}     | {any additional configuration from onboarding} |

### {Action or Configuration}

{Describe what this participant needs to do.}

{Include examples as appropriate.}

______________________________________________________________________

## Security Considerations

| Requirement                  | Description                                                                                                                                                           |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Binding required**         | Credentials **MUST** be bound to `checkout_id` and `identity` to prevent reuse.                                                                                       |
| **Binding placement**        | Binding data (e.g., `checkout_id`) **SHOULD** be included within the `credential` payload to ensure it is covered by the signature, rather than in transport headers. |
| **Binding verified**         | The processing participant **MUST** verify binding matches before processing.                                                                                         |
| **Token Expiry**             | {If using tokens: Tokens **MUST** expire after {duration} or single-use.}                                                                                             |
| **Data Residency**           | {Specify if PII **MUST** be processed/stored in specific geographic regions (e.g., EU, US) to comply with local laws.}                                                |
| **{Additional requirement}** | {description}                                                                                                                                                         |

______________________________________________________________________

## References

- **Handler Spec:** `{spec_url}`
- **Handler Schema:** `{schema_url}` (defines config, instrument, and credential shapes)
