<!--
   Copyright 2025 UCP Authors

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

# {Handler Name} Payment Handler

* **Handler Name:** `{reverse-dns.name}`
* **Version:** `{YYYY-MM-DD}`

## 1. Introduction

{Brief description of what this handler enables and the payment flow it
supports.}

### 1.1 Key Benefits

- {Benefit 1}
- {Benefit 2}
- {Benefit 3}

### 1.2 Quick Start

| If you are a... | Start here |
|:----------------|:-----------|
| **Merchant** integrating this handler | [Merchant Integration](#3-merchant-integration) |
| **Agent** using this handler | [4. Agent Integration](#4-agent-integration) |

---

## 2. Participants

{Describe all participants in this handler and their roles.}

| Participant | Role | Prerequisites |
|:------------|:-----|:--------------|
| **Merchant** | {role description} | {Yes/No — brief description} |
| **Agent** | {role description} | {Yes/No — brief description} |
| **{Other Participant}** | {role description} | {Yes/No — brief description} |

{Optional: ASCII diagram showing participant relationships}

```
┌─────────┐     ┌───────────────┐     ┌────────────┐
│  Agent  │     │   {Provider}  │     │  Merchant  │
└────┬────┘     └───────┬───────┘     └──────┬─────┘
     │                  │                    │
     │  {step 1}        │                    │
     │─────────────────>│                    │
     │                  │                    │
     │  {step 2}        │                    │
     │<─────────────────│                    │
     │                  │                    │
     │  {step 3}                             │
     │──────────────────────────────────────>│
```

---

<!--
  PARTICIPANT INTEGRATION SECTIONS
  
  Include one section per participant. Each section follows the same structure:
  - Prerequisites (onboarding, setup)
  - Configuration or Protocol (what they need to do)
  - Examples
  
  Number sections starting from 3. Add more sections as needed for additional participants.
-->

## 3. Merchant Integration

### 3.1 Prerequisites

Before advertising this handler, merchants must complete:

1. {Prerequisite 1, e.g., "Register with {provider} to obtain a merchant
   identifier"}
2. {Prerequisite 2}

**Prerequisites Output:**

| Field | Description |
|:------|:------------|
| `identity.access_token` | {what identifier is assigned, e.g., merchant_id} |
| {additional config} | {any additional configuration from onboarding} |

### 3.2 Handler Configuration

Merchants advertise support for this handler in the checkout's
`payment.handlers` array.

#### Configuration Schema

**Schema URL:** `{url to config JSON schema}`

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| {field} | {type} | {Yes/No} | {description} |

#### Example Handler Declaration

```json
{
  "payment": {
    "handlers": [
      {
        "id": "{handler_id}",
        "name": "{handler_name}",
        "version": "{version}",
        "spec": "{spec_url}",
        "config_schema": "{config_schema_url}",
        "instrument_schemas": [
          "{instrument_schema_url}"
        ],
        "config": {
          // Handler-specific configuration
        }
      }
    ]
  }
}
```

### 3.3 Processing Payments

Upon receiving a payment with this handler's instrument, merchants MUST:

1. **Validate Handler:** Confirm `instrument.handler_name` matches an advertised handler
2. **{Step 2}:** {description}
3. **{Step 3}:** {description}
4. **Return Response:** Respond with the finalized checkout state

{Include example request/response if the merchant calls an external service}

---

## 4. Agent Integration

### 4.1 Prerequisites

Before using this handler, agents must complete:

1. {Prerequisite 1, e.g., "Register with {provider} to obtain a client identifier"}
2. {Prerequisite 2}

**Prerequisites Output:**

| Field | Description |
|:------|:------------|
| `identity.access_token` | {what identifier is assigned, e.g., client_id} |
| {additional config} | {any additional configuration from onboarding} |

### 4.2 Payment Protocol

Agents MUST follow this flow to acquire a payment instrument:

#### Step 1: Discover Handler

Agent identifies `{handler_name}` in the merchant's `payment.handlers` array.

```json
{
  "id": "{handler_id}",
  "name": "{handler_name}",
  "config": {
    // Merchant's configuration
  }
}
```

#### Step 2: {Action Name}

{Description of what the agent does in this step.}

{Code example if applicable:}

```javascript
// Example SDK usage or API call
```

#### Step 3: {Action Name}

{Continue for all steps...}

#### Step N: Complete Checkout

Agent submits the checkout with the constructed payment instrument.

```json
POST /checkout-sessions/{checkout_id}/complete
Content-Type: application/json

{
  "payment": {
    "instruments": [
      {
        "id": "{instrument_id}",
        "handler_name": "{handler_name}",
        "type": "{instrument_type}",
        "credential": {
          "type": "{credential_type}",
          // Credential fields
        }
        // Additional instrument fields
      }
    ],
    "selected_instrument_id": "{instrument_id}"
  }
}
```

---

<!--
  ADDITIONAL PARTICIPANT SECTIONS
  
  Add one section per additional participant (PSP, Tokenizer, Wallet Provider, etc.)
  following the same pattern as Merchant and Agent integration.
-->

## {N}. {Participant} Integration

### {N}.1 Prerequisites

Before participating in this handler's flow, {participants} must complete:

1. {Prerequisite 1}
2. {Prerequisite 2}

**Prerequisites Output:**

| Field | Description |
|:------|:------------|
| `identity.access_token` | {what identifier is assigned} |
| {additional config} | {any additional configuration from onboarding} |

### {N}.2 {Action or Configuration}

{Describe what this participant needs to do.}

{Include examples as appropriate.}

---

## {N+1}. Security Considerations

| Requirement | Description |
|:------------|:------------|
| **Binding required** | Credentials MUST be bound to `checkout_id` and `identity` to prevent reuse |
| **Binding verified** | Processing participant MUST verify binding matches before processing |
| **{Additional requirement}** | {description} |

---

## {N+2}. References

- **Handler Spec:** `{spec_url}`
- **Config Schema:** `{config_schema_url}`
- **Instrument Schema:** `{instrument_schema_url}`
- **Credential Schema:** `{credential_schema_url}`
