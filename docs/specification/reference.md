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

# Schema Reference

This page provides a reference for all the capability data models and types used
within the UCP.

## Capability Schemas

{{ auto_generate_schema_reference('.', 'reference', include_extensions=False) }}

## Type Schemas

{{ auto_generate_schema_reference('types', 'reference', include_extensions=False) }}

## Extension Schemas

{{ auto_generate_schema_reference('.', 'reference', include_capability=False) }}

## UCP Metadata

The following schemas define the structure of UCP metadata used in discovery
and responses.

### Platform Discovery Profile

The top-level structure of a platform profile document (hosted at a URI advertised by the platform).

{{ extension_schema_fields('ucp.json#/$defs/platform_schema', 'reference') }}

### Business Discovery Profile

The top-level structure of a business discovery document (`/.well-known/ucp`).

{{ extension_schema_fields('ucp.json#/$defs/business_schema', 'reference') }}

### Checkout Response Metadata

The `ucp` object included in checkout responses.

{{ extension_schema_fields('ucp.json#/$defs/response_checkout_schema', 'reference') }}

### Order Response Metadata

The `ucp` object included in order responses or events.

{{ extension_schema_fields('ucp.json#/$defs/response_order_schema', 'reference') }}

### Capability

This object describes a single capability or extension. It appears in the
`capabilities` array in discovery profiles and responses, with slightly
different required fields in each context.

#### Capability (Discovery)

As seen in discovery profiles.

{{ extension_schema_fields('capability.json#/$defs/discovery', 'reference') }}

#### Capability (Response)

As seen in response messages.

{{ extension_schema_fields('capability.json#/$defs/response_schema', 'reference') }}
