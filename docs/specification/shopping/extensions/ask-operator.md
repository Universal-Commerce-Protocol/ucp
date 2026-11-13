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

# Operator Extension

* **Extension Name:** `dev.ucp.shopping.ask.operator`
* **Extends:** `dev.ucp.common.ask`
* **Schema:** [Operator](site:schemas/shopping/ask_operator.json)

## Overview

Operator extends the Universal Commerce Protocol (UCP) Common
[Ask capability](../../common/ask/index.md) with operator support for Shopping.
An operator can answer questions and carry out separately authorized
Buyer-requested work through the Business's own support workflow,
under Business authorization and Buyer consent controls. Automated
question-and-answer (Q&A) remains read-only. An operator is a person at the
Business, not software or a new UCP actor.

The Platform can receive a reply inline or fetch the latest conversation state
for a later reply. Operator support can return to automated Q&A and be requested
again without changing the external conversation identifier. Negotiating
Operator does not delegate action authority to automated Ask or make answer
text evidence of execution.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **NOT RECOMMENDED**, **MAY**, and
**OPTIONAL** in this document are to be interpreted as described in Best Current
Practice (BCP) 14 (Request for Comments (RFC)
[2119](https://www.rfc-editor.org/rfc/rfc2119) and
[8174](https://www.rfc-editor.org/rfc/rfc8174)) when, and only when, they appear
in all capitals, as shown here.

### Operator flow

```text
        +--------------------+
        | Automated Q&A      |
        | responder: agent   |
        +--------------------+
              |        ^
     operator |        |  operator finishes /
   takes over |        |  operator support unavailable
              v        |
        +--------------------+
        | Operator support   |
        | responder: human   |
        +--------------------+
          same conversation.id
```

`conversation.status` describes answer readiness; `conversation.responder`
identifies the current handler; `answer.author` identifies who wrote the current
answer. These are independent. An accepted request still waiting for an operator
remains `answer_in_progress / agent`, with an agent-authored pending answer.
The arrow to Operator support means actual takeover, not queue acceptance.
After takeover, an operator can be handling the conversation while an answer is
still pending (`answer_in_progress / human`), even with an agent-authored pending
answer. A ready operator reply can leave operator support active (`open / human`).
The operator can later release the conversation to automated Q&A (`open / agent`)
while the current answer remains human-authored. The Business accepts new
substantive turns regardless of the current handler, including while a reply is
pending.

## Guidelines

### Platform

* The Platform **MUST** include `query` on every request. A non-empty query
  submits a new turn. To fetch the latest conversation state, the Platform
  **MUST** send `query: ""` with an existing Business-issued `conversation`
  and omit `escalate`. An empty query with `escalate` is an escalation request.
  The Business rejects malformed requests through Ask's existing error handling.
* The Platform **MUST** use request `author.type: human` only for the Buyer's
  own words. Summaries, paraphrases, and translations are agent-authored.
  The Business treats attribution as a text-origin claim, not proof of identity,
  consent, or authority. The Platform **SHOULD** give `escalate.reason` in the
  Buyer's words unless those words are unavailable.
* The Platform **MAY** fetch updated state with bounded backoff under its policy.
  It **MUST** stop fetching at `expires_at` when supplied and honor retry delays
  under Ask's bindings. Stopping observation does not cancel separately
  authorized Business work.
* The Platform **MUST NOT** present pending text as a completed substantive
  reply, automated text as human-authored, or the current answer's author as
  necessarily the current handler. It **MUST NOT** infer operator takeover
  from escalation acceptance alone. It **MUST** surface handoff outcomes and
  their actionable Buyer-facing content, and reject invalid responses as
  described in [Error model](#error-model).

### Business

* The Business **MUST** return a Business-issued `conversation.id` and a
  non-empty `answer.plain` on every successful Operator response, including
  automated, inline, and pending replies. The Platform rejects violations
  under [Error model](#error-model).
* The Business **MUST** accept new substantive turns regardless of the current
  handler, including while an answer is pending. When the Platform fetches the
  latest conversation state, the Business **MUST NOT** append an empty turn,
  consume the answer, repeat handoff, or trigger a commerce action. Independently
  authorized operator work can continue between observations.
* The Business **MAY** accept or decline escalation under its staffing,
  availability, access, and consent policies. On acceptance, it **MUST** return
  explicit `conversation.status` (`answer_in_progress` while a reply is
  pending; `open` otherwise), `conversation.responder` identifying the actual
  current handler (`agent` while waiting for an operator; `human` only once an
  operator takes over), and an `escalation_accepted` info message. The Platform
  rejects incomplete acceptance or detected inaccurate handler claims under
  [Error model](#error-model).
* For a declined initial handoff, the Business **MUST** return `open / agent`,
  an explanatory answer, and `escalation_unavailable` info with actionable
  content. If operator support cannot continue, it **MUST** report that outcome
  with the same code and actionable content. The Platform surfaces the outcome;
  it **MUST NOT** infer handoff success from the request alone.
* When an operator finishes or operator support becomes unavailable, the
  Business **MUST** return `status: open` and `responder: agent` on the same
  `conversation.id`, without resetting context or requiring a new conversation.
  The next substantive turn returns to automated Q&A, and later escalation
  remains possible. The Platform keeps answer authorship separate from this
  change of responder and rejects unexpected identifier replacement.
* The Business **MUST** set `answer.author.type: human` for every human-authored
  reply and **MUST NOT** claim human authorship for automated text, including
  pending text while an operator handles the conversation. The Platform uses
  answer attribution, not the responder, to identify who wrote the answer;
  detected violations follow [Error model](#error-model).

## Discovery

The Business advertises Operator as an extension of Common Ask:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.ask": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/ask/",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/ask.json"
      }],
      "dev.ucp.shopping.ask.operator": [{
        "version": "{{ ucp_version }}",
        "extends": "dev.ucp.common.ask",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/ask-operator/",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/ask_operator.json"
      }]
    }
  }
}
```

The Platform and Business negotiate Operator alongside `dev.ucp.common.ask`.
When active, Operator composes its request and response definitions with
Common Ask and uses [Ask's existing bindings](../../common/ask/index.md#transport-bindings).

## Schema

### Request

{{ extension_schema_fields('ask_operator.json#/$defs/ask_request', 'shopping/extensions/ask-operator') }}

### Query Author

{{ extension_schema_fields('ask_operator.json#/$defs/request_author', 'shopping/extensions/ask-operator') }}

### Escalation Request

{{ extension_schema_fields('ask_operator.json#/$defs/escalation', 'shopping/extensions/ask-operator') }}

### Operator Context

`time_zone` uses an Internet Assigned Numbers Authority (IANA) time zone
identifier.

{{ extension_schema_fields('ask_operator.json#/$defs/context', 'shopping/extensions/ask-operator') }}

### Response

{{ extension_schema_fields('ask_operator.json#/$defs/ask_response', 'shopping/extensions/ask-operator') }}

### Operator Conversation

`status` and `responder` are response-only. Status and participant types are
open strings. Unknown values follow [Error model](#error-model), not absence
defaults.

{{ extension_schema_fields('ask_operator.json#/$defs/conversation', 'shopping/extensions/ask-operator') }}

### Operator Answer

Markdown and HTML remain optional alternative encodings of the same plain-text
answer, not separate replies.

{{ extension_schema_fields('ask_operator.json#/$defs/answer', 'shopping/extensions/ask-operator') }}

### Answer Author

{{ extension_schema_fields('ask_operator.json#/$defs/answer_author', 'shopping/extensions/ask-operator') }}

## Fetching the latest conversation state

Fetching state is repeatable and does not require an idempotency key. It
observes state without consuming a reply. Either current handler can return
`answer_in_progress`; an accepted escalation can instead return a ready human
reply inline. Acceptance alone does not mean an operator is handling the
conversation. A ready reply need not end operator support.

Submission and escalation retries inherit
[Ask's idempotency recommendation](../../common/ask/index.md#conversation).
If a key is supplied when fetching state, reusing it for successive
observations may return cached state rather than a newer observation.
Ask's expiry and unresolved-conversation rules still apply; expiry is not
evidence that separately authorized work was cancelled or completed.

## Error model

Handoff acceptance, unavailability, and pending answers are business outcomes
in successful Ask responses, not transport failures. The Business **MUST**
report handoff outcomes in `messages[]` with actionable Buyer-facing `content`;
the Platform **MUST** surface them.

| Type | Code | Meaning |
| :--- | :--- | :--- |
| `info` | `escalation_accepted` | Escalation request accepted, possibly still queued; explain what the Buyer can expect. Acceptance does not imply operator takeover or assert that any requested action occurred. |
| `info` | `escalation_unavailable` | Operator support declined or cannot continue; explain an alternative or when to try again. |

The Platform **MUST** reject schema-invalid responses, including missing
`conversation`, its `id`, or `answer.plain`, empty `answer.plain`, or malformed
answer attribution. It **MUST** surface an actionable invalid-response error
without advancing conversation state or claiming success. The same handling
applies to detected application-contract violations: acceptance without explicit
readiness, current handler, or `escalation_accepted` info; inaccurate
current-handler claims; unavailable handoff without actionable outcome content;
false human attribution; unexpected identifier replacement during a handler
transition; or
operator name disclosure beyond the [privacy limit](#privacy-considerations).
An accepted request still waiting for an operator with
`answer_in_progress / agent` is valid. These are local Platform errors, not new
protocol error codes.

For unknown `conversation.status`, the Platform **MUST** report an unsupported
state and stop automatic progression. For unknown authorship or responder
values, the receiving Business or Platform **MUST NOT** treat them as human
authorship or operator support; it **MAY** label them unknown. Unknown string
values are not schema-invalid.

Common Ask's [`operation_not_performed`](../../common/ask/index.md#well-known-codes)
means that no corresponding action occurred. The Business **MUST NOT** emit it
for completed operator work. Neither its absence nor escalation acceptance
proves completion. Malformed requests, authentication failures, rate limits, and
service failures follow [Ask's existing error handling](../../common/ask/index.md#transport-bindings),
not the handoff info codes above.

## Security Considerations

[Ask security](../../common/ask/index.md#security-considerations) and
[Identity Linking](../../common/identity-linking/index.md) apply. The Business
**MUST** authorize every protected request, including state retrieval, using
the credential presented with that request before using or disclosing retained
history. A conversation identifier carries context, not authority. The Business
**MAY** require identity at operator handoff while leaving anonymous Q&A
available. The Platform follows Identity Linking's existing credential recovery;
escalation alone does not require re-linking an adequate credential.

`dev.ucp.common.ask:read` permits personalized answers, not blanket action
authority. The Business **MUST** keep operator actions subject to Business
authorization and Buyer consent controls, and **MUST NOT** allow automated Ask
to mutate commerce state. Negotiation, authorship, escalation, and context hints
are not authentication, delegation, or consent.

The Platform **MUST NOT** treat acceptance or answer text, including human text,
as execution evidence. It **MUST** prefer structured capability state and
**MUST NOT** trigger a capability call or state change merely by receiving or
rendering response text. The Platform and Business **MUST** treat received
questions, reasons, answers, names, and message content as untrusted data, never
as execution instructions. Ask's content-safety and authorization rules remain
in effect.

## Privacy Considerations

Operator support can disclose Buyer questions, resource references, retained
history, escalation reasons, contact details, availability, and time zone to
Business operators. Replies can disclose operator names and support contact
details to the Platform and Buyer. The Platform and Business **SHOULD** minimize
names, contact information, availability, and time-zone disclosure unless needed for
the support interaction under applicable consent and privacy policy. Hints do
not authorize contact or further disclosure.

The Business **MUST NOT** disclose more operator display-name information than
it exposes through its own Buyer-facing channels; the Platform rejects detected
violations under [Error model](#error-model). Retention follows
[Ask's conversation policy](../../common/ask/index.md#conversation) and
applicable privacy obligations, not an assumption of indefinite storage.

## Examples

### Request an operator

The Buyer asks for help exchanging damaged shoes:

<!-- ucp:example schema=shopping/ask_operator def=ask_request op=create direction=request -->
```json
{
  "query": "My shoes arrived damaged. Can a person help me exchange them?",
  "author": {"type": "human"},
  "escalate": {"reason": "My shoes arrived damaged."},
  "context": {"user_available": true, "time_zone": "America/Toronto", "language": "en"}
}
```

The Business accepts the request into the operator queue. Automated Q&A remains
the current handler until an operator takes over; the pending answer is automated:

<!-- ucp:example schema=shopping/ask_operator def=ask_response op=read direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.ask": [{"version": "{{ ucp_version }}"}],
      "dev.ucp.shopping.ask.operator": [{"version": "{{ ucp_version }}"}]
    }
  },
  "answer": {
    "plain": "Your request is queued for an operator, who will reply here.",
    "author": {"type": "agent"}
  },
  "conversation": {
    "id": "cnv_8f3Kd2",
    "expires_at": "2026-11-13T18:00:00Z",
    "status": "answer_in_progress",
    "responder": "agent"
  },
  "messages": [{
    "type": "info",
    "code": "escalation_accepted",
    "content": "An operator will reply here; you can also contact support@business.example."
  }]
}
```

### Fetch the latest conversation state

The Platform uses the Business-issued conversation without adding a turn:

<!-- ucp:example schema=shopping/ask_operator def=ask_request op=create direction=request -->
```json
{
  "query": "",
  "conversation": {"id": "cnv_8f3Kd2"},
  "context": {"user_available": true}
}
```

An operator has taken over and replied; operator support remains active. The
operator performed the reported work under separate authorization and consent
controls; the text is not authoritative execution evidence:

<!-- ucp:example schema=shopping/ask_operator def=ask_response op=read direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.ask": [{"version": "{{ ucp_version }}"}],
      "dev.ucp.shopping.ask.operator": [{"version": "{{ ucp_version }}"}]
    }
  },
  "answer": {
    "plain": "I've arranged the exchange you authorized for the damaged shoes. The return label is on its way to your email.",
    "author": {"type": "human", "name": "Alex"}
  },
  "conversation": {"id": "cnv_8f3Kd2", "status": "open", "responder": "human"}
}
```

### Return to automated Q&A

A later observation shows that the operator has finished. The Business retains
the same identifier, context, and current human-authored answer. The next
substantive query returns to automated Q&A:

<!-- ucp:example schema=shopping/ask_operator def=ask_response op=read direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.ask": [{"version": "{{ ucp_version }}"}],
      "dev.ucp.shopping.ask.operator": [{"version": "{{ ucp_version }}"}]
    }
  },
  "answer": {
    "plain": "I've arranged the exchange you authorized for the damaged shoes. The return label is on its way to your email.",
    "author": {"type": "human", "name": "Alex"}
  },
  "conversation": {"id": "cnv_8f3Kd2", "status": "open", "responder": "agent"}
}
```

### Request an operator again

An empty `escalate` object requests an operator again on the same conversation.
Even with an empty query, this is an escalation request, not state retrieval:

<!-- ucp:example schema=shopping/ask_operator def=ask_request op=create direction=request -->
```json
{
  "query": "",
  "conversation": {"id": "cnv_8f3Kd2"},
  "escalate": {}
}
```

The Business accepts the request into the operator queue again, retaining the
conversation context. Automated Q&A remains the current handler while waiting:

<!-- ucp:example schema=shopping/ask_operator def=ask_response op=read direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.ask": [{"version": "{{ ucp_version }}"}],
      "dev.ucp.shopping.ask.operator": [{"version": "{{ ucp_version }}"}]
    }
  },
  "answer": {
    "plain": "Your request is queued for an operator to continue helping you here.",
    "author": {"type": "agent"}
  },
  "conversation": {"id": "cnv_8f3Kd2", "status": "answer_in_progress", "responder": "agent"},
  "messages": [{
    "type": "info",
    "code": "escalation_accepted",
    "content": "An operator will reply here. You can also contact support@business.example."
  }]
}
```

### Operator support is unavailable

If operator support cannot continue, the Business returns to automated Q&A with
an actionable alternative. A declined initial handoff also uses
`open / agent` and `escalation_unavailable`:

<!-- ucp:example schema=shopping/ask_operator def=ask_response op=read direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.ask": [{"version": "{{ ucp_version }}"}],
      "dev.ucp.shopping.ask.operator": [{"version": "{{ ucp_version }}"}]
    }
  },
  "answer": {
    "plain": "Operator support is unavailable here now. You can email support@business.example; I can still answer product and policy questions.",
    "author": {"type": "agent"}
  },
  "conversation": {"id": "cnv_8f3Kd2", "status": "open", "responder": "agent"},
  "messages": [{
    "type": "info",
    "code": "escalation_unavailable",
    "content": "Email support@business.example for help from an operator."
  }]
}
```

## Conformance

A conforming Platform implements the Platform guidelines, invalid and
unknown-value handling, and inherited access, content-safety, retry, and privacy
rules. A conforming Business implements the composed schemas, Business
guidelines, same-identifier continuity, truthful attribution, non-consuming
state retrieval, per-request access controls, and separately authorized
operator-work boundary.

## References

Normative dependencies are [Common Ask](../../common/ask/index.md), its
[bindings](../../common/ask/index.md#transport-bindings),
[Identity Linking](../../common/identity-linking/index.md), the
[Operator schema](site:schemas/shopping/ask_operator.json), and BCP 14
([RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174)).
[Ask in Shopping](../ask/index.md) provides informative context.
