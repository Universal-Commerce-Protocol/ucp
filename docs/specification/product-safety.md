<!--
   Copyright 2026 DeepRecall

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

# Product Safety Extension

**Version:** `2026-01-27`  
**Namespace:** `io.deeprecall.shopping.product_safety`

## Overview

This extension defines a message contract for querying product recall databases. 
It enables platforms to retrieve recall evidence for a given product before checkout.

The extension returns similarity matches only. It does not make safety judgments, 
block transactions, or enforce compliance decisions.

## Scope

This extension covers:

- Pre-checkout recall evidence lookup
- Synchronous request/response pattern
- Evidence-only output (no decisions)

### Non-Goals

This extension explicitly does NOT:

- Block or prevent checkout completion
- Make legal or compliance judgments
- Enforce any regulatory requirements
- Replace platform or business safety policies
- Provide definitive product identification

Interpretation of results and any subsequent actions are the responsibility of the caller.

## Discovery

Platforms advertise product safety support in their profile:

```json
{
  "capabilities": {
    "io.deeprecall.shopping.product_safety": [
      {
        "version": "2026-01-27",
        "spec": "https://deeprecall.io/ucp/product-safety",
        "schema": "https://deeprecall.io/ucp/schemas/shopping/product_safety.json"
      }
    ]
  }
}
```

This is a standalone vendor capability and does not extend core UCP capabilities.

## Operations

### search

Query for recalled products similar to the provided product identifiers.

**Method:** `POST`  
**Path:** `/product-safety/search`

## Request Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `product` | object | Yes | Product identifiers for lookup |
| `product.description` | string | No* | Text description of the product |
| `product.name` | string | No* | Product name or title |
| `product.brand` | string | No | Product brand or manufacturer |
| `product.gtin` | string | No* | Global Trade Item Number |
| `product.image_urls` | array | No* | Product image URLs (max 5) |
| `filters` | object | No | Optional search filters |
| `filters.country` | string | No | ISO 3166-1 alpha-2 country code |
| `filters.data_sources` | array | No | Regulatory agencies to query |
| `filters.top_k` | integer | No | Max results (1-20, default 5) |

*At least one of `description`, `name`, `gtin`, or `image_urls` is required.

### Supported Data Sources

| ID | Agency | Jurisdiction |
|----|--------|--------------|
| `us_cpsc` | Consumer Product Safety Commission | United States |
| `us_fda` | Food and Drug Administration | United States |
| `safety_gate` | EU Safety Gate | European Union |
| `uk_opss` | Office for Product Safety & Standards | United Kingdom |
| `canada_recalls` | Health Canada | Canada |
| `oecd` | OECD GlobalRecalls | International |
| `rappel_conso` | RappelConso | France |
| `accc_recalls` | ACCC | Australia |

## Response Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `matches` | array | Yes | Recalls similar to the queried product |
| `matches[].recall_id` | string | Yes | Unique identifier for this recall |
| `matches[].similarity_score` | number | Yes | Similarity confidence (0.0 to 1.0) |
| `matches[].regulator` | string | Yes | Regulatory agency that issued recall |
| `matches[].regulator_case_id` | string | No | Agency's case ID |
| `matches[].title` | string | Yes | Title of the recall notice |
| `matches[].product_name` | string | No | Name of the recalled product |
| `matches[].hazard` | string | No | Description of the hazard |
| `matches[].remedy` | string | No | Recommended remedy |
| `matches[].recall_date` | string | No | Date recall was issued (YYYY-MM-DD) |
| `matches[].evidence_url` | string | Yes | URL to official recall notice |
| `query_timestamp` | string | Yes | Query execution time (RFC 3339) |

## Examples

### Request

```json
{
  "product": {
    "description": "Infant sleep rocker with vibrating seat",
    "brand": "Example Brand"
  },
  "filters": {
    "country": "US",
    "top_k": 3
  }
}
```

### Response

```json
{
  "matches": [
    {
      "recall_id": "rec_abc123",
      "similarity_score": 0.87,
      "regulator": "us_cpsc",
      "regulator_case_id": "21-123",
      "title": "Infant Sleeper Recalled Due to Safety Concern",
      "product_name": "Example Infant Rocker",
      "hazard": "Suffocation hazard when used on inclined surface",
      "remedy": "Refund",
      "recall_date": "2024-03-15",
      "evidence_url": "https://www.cpsc.gov/Recalls/2024/example"
    }
  ],
  "query_timestamp": "2026-01-27T14:30:00Z"
}
```

## Error Handling

Implementations MUST return standard HTTP error codes:

| Code | Condition |
|------|-----------|
| `400` | Invalid request (missing required fields, malformed input) |
| `401` | Authentication required or invalid credentials |
| `429` | Rate limit exceeded |
| `500` | Internal server error |
| `503` | Service temporarily unavailable |

Error responses SHOULD include a `message` field with a human-readable description:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "At least one of description, name, gtin, or image_urls is required"
  }
}
```

## Backward Compatibility

This extension is optional and does not modify any existing UCP schemas or flows. 
Platforms and businesses MAY implement this extension without affecting core 
checkout operations.

## Security Considerations

- Requests MUST be made over HTTPS
- Implementations SHOULD rate-limit queries to prevent abuse
- Response data is public regulatory information; no PII is transmitted

## References

- [JSON Schema: Request](https://deeprecall.io/ucp/schemas/shopping/product_safety.search_req.json)
- [JSON Schema: Response](https://deeprecall.io/ucp/schemas/shopping/product_safety_resp.json)
