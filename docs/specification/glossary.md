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

# Glossary

This glossary provides a best-effort capture of acronyms and terms used
throughout the UCP specification. New entries should be added in alphabetical
order within their respective category.

**Note:** Even with this glossary, it is preferred that the first usage of an
acronym in each specification Markdown file spells out the full term (e.g.,
"Payment Card Industry Data Security Standard (PCI-DSS)").

## Protocol

| Term                            | Acronym | Definition                                                                                                                                                |
| :------------------------------ | :------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agent Payments Protocol**     | AP2     | An open protocol designed to enable AI agents to securely interoperate and complete payments autonomously. UCP leverages AP2 for secure payment mandates. |
| **Agent2Agent Protocol**        | A2A     | An open standard for secure, collaborative communication between diverse AI agents. UCP can use A2A as a transport layer.                                 |
| **Capability**                  | -       | A standalone core feature that a business supports (e.g., Checkout, Identity Linking). Capabilities are the fundamental "verbs" of UCP.                   |
| **Credential Provider**         | CP      | A trusted entity (like a digital wallet) responsible for securely managing and executing the user's payment and identity credentials.                     |
| **Extension**                   | -       | An optional capability that augments another capability via the `extends` field. Extensions appear in `ucp.capabilities[]` alongside core capabilities.   |
| **Model Context Protocol**      | MCP     | A protocol standardizing how AI models connect to external data and tools. UCP capabilities map 1:1 to MCP tools.                                         |
| **Profile**                     | -       | A JSON document hosted by businesses and platforms at a well-known URI, declaring their identity, supported capabilities, and endpoints.                  |
| **Universal Commerce Protocol** | UCP     | The standard defined in this document, enabling interoperability between commerce entities via standardized capabilities and discovery.                   |

## Commerce

| Term                         | Acronym | Definition                                                                                                                                            |
| :--------------------------- | :------ | :---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Business**                 | -       | The entity selling goods or services. In UCP, they act as the **Merchant of Record (MoR)**, retaining financial liability and ownership of the order. |
| **Merchant of Record**       | MoR     | The legal entity responsible for the sale, including financial liability and order ownership.                                                         |
| **Payment Service Provider** | PSP     | The financial infrastructure provider that processes payments, authorizations, and settlements on behalf of the business.                             |
| **Platform**                 | -       | The consumer-facing surface (AI agent, app, website) acting on behalf of the user to discover businesses and facilitate commerce.                     |

## Payments

| Term                                             | Acronym | Definition                                                                                                                                                       |
| :----------------------------------------------- | :------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Card Verification Value**                      | CVV     | The 3 or 4 digit security code on payment cards used to verify card-not-present transactions.                                                                    |
| **Payment Card Industry Data Security Standard** | PCI-DSS | A set of security standards designed to ensure that all companies that accept, process, store or transmit credit card information maintain a secure environment. |
| **Primary Account Number**                       | PAN     | The unique payment card number (typically 13-19 digits) that identifies the card issuer and cardholder account.                                                  |
| **Strong Customer Authentication**               | SCA     | A requirement under PSD2 that payment service providers apply multi-factor authentication for electronic payments.                                               |
| **3D Secure**                                    | 3DS     | A protocol designed to add an additional security layer for online credit and debit card transactions through cardholder authentication.                         |

## Compliance & Regulatory

| Term                                   | Acronym | Definition                                                                                                             |
| :------------------------------------- | :------ | :--------------------------------------------------------------------------------------------------------------------- |
| **California Consumer Privacy Act**    | CCPA    | A state statute intended to enhance privacy rights and consumer protection for residents of California, United States. |
| **General Data Protection Regulation** | GDPR    | A regulation in EU law on data protection and privacy in the European Union and the European Economic Area.            |
| **Know Your Customer**                 | KYC     | The process of verifying the identity of clients to prevent fraud, money laundering, and terrorist financing.          |

## Standards & Specifications

| Term                                               | Acronym | Definition                                                                                                                                                                                                                  |
| :------------------------------------------------- | :------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **International Organization for Standardization** | ISO     | An international standard-setting body composed of representatives from various national standards organizations. Referenced in UCP for country codes (ISO 3166-1), currency codes (ISO 4217), and date formats (ISO 8601). |
| **Verifiable Digital Credential**                  | VDC     | An Issuer-signed credential (set of claims) whose authenticity can be verified cryptographically. Used in UCP for secure payment authorizations.                                                                            |
