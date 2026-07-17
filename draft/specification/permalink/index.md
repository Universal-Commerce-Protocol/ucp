# Permalink Capability

- **Capability Name:** `dev.ucp.shopping.permalink`
- **Schema:** `https://ucp.dev/schemas/shopping/permalink.json`

## Overview

A UCP shopping permalink is a **browser-addressable shopping intent** that initializes shopping state from the provided inputs and navigates the browser to an appropriate buyer-facing destination.

A permalink is a **GET browser navigation**, not a REST API operation. A permalink request resolves by redirecting the browser. The Business MAY retain initialized shopping state as a Cart, a Checkout, session state, or any internal representation; the permalink contract does not require a particular UCP resource.

A Business MUST NOT treat loading a permalink as authorization to place an order, charge payment, or complete checkout, and MUST NOT return a UCP JSON resource as the primary response.

The capability defines:

- discovery of the permalink endpoint;
- compact item path syntax;
- the `continue_to` destination preference;
- UCP field-path mapping for initialized shopping state;
- redirect resolution semantics.

## Discovery

Businesses advertise permalink support with `dev.ucp.shopping.permalink`. Business declarations MUST include `config.endpoint`. The endpoint MUST be an absolute HTTPS browser endpoint with a non-empty authority and without userinfo, query, fragment, whitespace, backslashes, or trailing slash.

Permalinks can also open native apps. A native app can register as a link handler for the endpoint's `https` URLs — Universal Links on iOS, App Links on Android. When the app is installed it intercepts the permalink and handles it in native UI; when it is not, the navigation is handled by the web browser.

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.shopping.permalink": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/permalink",
          "schema": "https://ucp.dev/draft/schemas/shopping/permalink.json",
          "config": {
            "endpoint": "https://merchant.example/buy"
          }
        }
      ]
    }
  }
}
```

## Schema

### Configuration

Business browser endpoint configuration for shopping permalinks.

| Name     | Type   | Requirement  | Description                                                                                                                                                                                                                  |
| -------- | ------ | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| endpoint | string | **Required** | Absolute HTTPS browser endpoint with a non-empty authority and without userinfo, query, fragment, whitespace, backslashes, or trailing slash. Optional compact item path and query parameters are appended to this endpoint. |

## URL Shape and Route Binding

Given a discovered endpoint:

```text
https://merchant.example/buy
```

a Platform or Business appends an optional compact item path and query string.

```text
https://merchant.example/buy/{items}?{query}
```

where:

```text
items     = item_pair *( "," item_pair )
item_pair = item_id_token ":" quantity
quantity  = positive base-10 integer without leading zeros
```

If no compact items are present, the endpoint MAY still use UCP field-path query parameters when supported by the Business, for example:

```text
https://merchant.example/buy?context/postal_code=94105&continue_to=/
```

This URL initializes shopping context with `postal_code` set to `94105` and requests continuation to `/`.

The browser route binding is documented separately at:

```text
https://ucp.dev/draft/services/shopping/permalink.openapi.json
```

It defines these routes:

```text
GET /
GET /{items}
```

The OpenAPI document describes route shape and redirect responses. This specification remains normative for item-token encoding, query partitioning, UCP field-path semantics, redirect semantics, and safety rules.

## Compact Item Path

The compact item path initializes shopping `line_items`.

When the compact item identifiers are purchasable item IDs, this URL:

```text
/buy/sku_123:2,sku_456:1
```

is equivalent to the initialized data:

```json
{
  "line_items": [
    { "item": { "id": "sku_123" }, "quantity": 2 },
    { "item": { "id": "sku_456" }, "quantity": 1 }
  ]
}
```

### Purchasable Item Resolution

The compact item path identifies the item the Business should place into the requested shopping flow. Platforms and Businesses SHOULD use the purchasable variant or sellable-unit ID returned by catalog operations when available.

A Business MAY accept another item identifier, including a product ID, when it can unambiguously resolve that identifier to a purchasable sellable unit for the requested context. If the identifier resolves to zero or more than one purchasable unit, the Business SHOULD handle the request as a shopping error or route the buyer to a selection or remediation page.

When the Business produces UCP data from the permalink, `line_items[].item.id` MUST identify the resolved purchasable sellable unit.

### Item ID Token

`item_id_token` is a path-safe reversible encoding of the compact item identifier. It is not a second identifier; it preserves the identifier supplied in the URL.

If the item identifier matches:

```text
^[A-Za-z0-9._-]+$
```

a Platform or Business MAY use it directly:

```text
/buy/sku_123:2
```

Otherwise, the item identifier MUST be encoded as:

```text
"~" + base64url_no_padding(utf8(item_identifier))
```

Item identifiers MUST NOT be percent-encoded to make them fit the compact path. If an item identifier contains any character outside the raw token grammar, including `/`, `:`, `,`, `%`, `~`, whitespace, or non-ASCII characters, the `~` encoded form MUST be used instead. This avoids percent-encoded path separators such as `%2F`, which HTTP servers, proxies, and routers may reject, decode, or normalize before resolution.

Example:

```text
gid://shopify/ProductVariant/70881412
```

becomes:

```text
/buy/~Z2lkOi8vc2hvcGlmeS9Qcm9kdWN0VmFyaWFudC83MDg4MTQxMg:1
```

A Business MUST treat a leading `~` as the encoding marker and decode the remainder as base64url without padding. A Business MUST reject a token whose remainder is not canonical base64url without padding, and MUST reject a decoded value that is not valid UTF-8 or that contains control characters. The raw and `~`-encoded forms of an identifier MUST resolve to the same decoded identity. An identifier that looks like a URI is still just an identifier: a Business resolves it against its own catalog, and MAY parse formats it owns (for example, a numeric key inside a `gid://…`).

## Query Processing

The query string carries initialized shopping state, destination preferences, and non-UCP query parameters. Platforms construct UCP field names as JSON Pointer paths with the leading `/` omitted, such as `buyer/email` or `line_items/0/quantity`.

A Business classifies each decoded query parameter name as follows:

1. If the name is `continue_to`, process it as the destination preference.
1. Otherwise, normalize the name to a canonical JSON Pointer by ensuring exactly one leading `/`. For example, `buyer/email` and `/buyer/email` both normalize to `/buyer/email`, and `buyer` normalizes to `/buyer`.
1. Parse the normalized pointer into JSON Pointer tokens. The first token is the UCP root candidate.
1. If the root candidate matches a top-level field in a Business-supported UCP Cart or Checkout schema, including active profiles and extensions, or a field defined by this capability, process the parameter as a UCP field-path query parameter.
1. Otherwise, process the parameter as a non-UCP query parameter.

Distinct raw keys can normalize to the same pointer (for example `buyer/email` and `/buyer/email`), and `continue_to` can appear more than once. A Business MUST detect these collisions after normalization and MUST NOT resolve them by query-parameter order; it handles them as ambiguous (see [Merge Rules](#merge-rules) and [Error Handling](#error-handling)).

For UCP field-path query parameters, the Business resolves the remaining pointer tokens against the applicable schema. Permalink inputs are untrusted: a Business applies them only to fields its Cart or Checkout schema accepts as input — as it would for any UCP request — so server-owned or response-only fields (totals, presentment currency, status, identifiers, order) are never set from the URL. If the full field path is recognized and applicable, the Business applies it to the initialized shopping state; if it is not recognized or not applicable, the Business SHOULD consume and remove it by default. A Business MAY expose selected field paths on the destination URL only when it explicitly selects and, where appropriate, rewrites them for a defined purpose, such as preserving attribution. A Business MUST NOT forward sensitive values.

### Destination Preference (`continue_to`)

`continue_to` is a destination preference, not shopping-state data. It requests the same-origin path where the buyer should continue after the Business applies permalink inputs:

```text
/buy/sku_123:1?continue_to=/collections/spring
```

`continue_to` is untrusted, externally supplied input, so a Business MUST validate it server-side, in this order:

1. Percent-decode the value once (a single RFC 3986 percent-decoding pass).
1. Reject it unless, after decoding, it starts with a single `/` (not `//`) and contains no URL scheme, backslash, whitespace, or control character (including TAB, CR, and LF).
1. Resolve the decoded value as a relative reference against the permalink endpoint's origin, applying RFC 3986 dot-segment removal.
1. Reject it unless the resulting absolute URL is same-origin with the endpoint.
1. Emit the re-encoded canonical path in `Location`. A Business MUST NOT reflect the raw value, and the emitted `Location` MUST NOT contain CR, LF, or other control characters.

A Business MUST fall back to its default destination for any value that fails this validation.

### UCP Fields

UCP field paths address the initialized shopping state. That state is interpreted against the Business's Cart or Checkout schema for the flow, including any active profiles and extensions. The permalink contract does not require the Business to instantiate that UCP resource; the Business's schema determines which URL fields have UCP meaning.

```text
context/postal_code=94105
context/payment/0/handler=com.example.wallet
buyer/email=alice%40example.com
attribution/utm_source=social
```

map to:

```json
{
  "context": {
    "postal_code": "94105",
    "payment": [{ "handler": "com.example.wallet" }]
  },
  "buyer": { "email": "alice@example.com" },
  "attribution": { "utm_source": "social" }
}
```

Recognized fields can come from base UCP, a profile, or an extension. Platforms and Businesses SHOULD NOT rely on profile- or extension-specific fields unless they know the Business supports the defining semantics.

### No-Slash Query Parameters

A no-slash query parameter can still be a UCP field-path query parameter. For example, `buyer` normalizes to `/buyer`. It is UCP-shaped when `buyer` is a UCP root recognized by the Business; otherwise it is a non-UCP query parameter.

### Extension-Defined Fields

Extensions and profiles can define additional UCP field paths. Permalinks use the same JSON Pointer path syntax for those fields; they do not need extension-specific alias syntax.

For example, when `dev.ucp.shopping.discount` is active for the intended shopping flow, this URL:

```text
/buy/sku_123:1?discounts/codes/0=SAVE10&discounts/codes/1=WELCOME
```

writes:

```json
{ "discounts": { "codes": ["SAVE10", "WELCOME"] } }
```

If the Business does not support the discount extension for that flow, those field paths are not applied as discount input. The Business handles them using the query-processing rules above.

Profile-defined fields use the same mechanism:

```text
/buy/sku_123:1?line_items/0/selling_plan=plan_monthly
```

Base UCP does not define `line_items[].selling_plan`; Platforms and Businesses SHOULD use this only when they know the Business supports the profile or extension that defines it.

Field paths address top-level Cart or Checkout fields and positional entries within them, and their values MAY reference identifiers the buyer already knows, such as a variant or destination ID. They cannot address entries keyed by identifiers the Business generates only while constructing purchasable state — line-item or fulfillment-group IDs — since those do not exist when the link is authored.

### Non-UCP Query Parameters

UCP does not insert non-UCP query parameters into initialized shopping data.

```text
utm_source=social&ref=creator_42&gclid=...
```

If attribution must enter the UCP object, use explicit UCP fields:

```text
attribution/ref=creator_42&attribution/utm_source=social
```

See [Redirect Resolution](#redirect-resolution) for non-UCP query parameter preservation and filtering rules.

## Merge Rules

The compact item path is authoritative for line-item IDs and quantities; query fields targeting the same line items MUST NOT change them.

Examples:

```text
/buy/sku_123:2?line_items/0/quantity=5
```

resolves `line_items/0/quantity` to `2` from the compact path.

Query fields MAY extend path-created line items when profile or extension semantics define those fields and they do not override path fields. For example, an extension-defined `line_items/0/selling_plan` field can add selling-plan state without changing the item ID or quantity from the compact path.

Platforms MUST NOT generate multiple query parameters that normalize to the same UCP pointer. When multiple values are needed, Platforms MUST use distinct field paths, such as indexed array paths.

```text
/buy/sku_123:1?discounts/codes/0=SAVE10&discounts/codes/1=WELCOME
```

A Business MUST NOT rely on query-parameter order to resolve duplicate writes. If two query parameters normalize to the same UCP pointer, a Business MUST treat the request as ambiguous and handle it according to [Error Handling](#error-handling), unless the Business has a documented, order-independent policy for that field.

## Redirect Resolution

A Business MUST resolve a handled permalink request with `303 See Other` and a `Location` header pointing to a buyer-facing destination. The response MUST include `Cache-Control: no-store` and MUST include a referrer policy (such as `Referrer-Policy: no-referrer`) that prevents leaking the permalink URL to third parties.

```http
HTTP/1.1 303 See Other
Location: https://merchant.example/checkout/session/chk_123
Cache-Control: no-store
Referrer-Policy: no-referrer
```

The Business selects the `Location`, and it MAY be cross-origin — for example, an off-site or hosted checkout. A Business MUST validate and canonicalize untrusted input before it influences the destination, and SHOULD gate any cross-origin destination derived from that input behind an explicit policy or allow-list.

A Business MUST NOT use permanent redirects such as `301` or `308` for permalink resolution.

A Business SHOULD construct a purchasable cart, checkout, or equivalent server-side state when the provided inputs are sufficient. When purchasable state can be constructed and `continue_to` is absent, a Business SHOULD redirect to its default purchase destination. If purchasable state cannot be constructed, a Business SHOULD route the buyer to a valid `continue_to` destination when present; otherwise it SHOULD route the buyer to a safe fallback, such as the storefront root, cart, or a buyer-facing remediation page.

A Business decides how to construct that state: it MAY merge the permalink items into an existing cart, create a new cart, or stage a separate checkout, and MAY either offer the buyer a choice or apply an automated policy. The permalink expresses buyer intent; the response conveys the resulting state. A Business MAY also require additional steps — such as verification, eligibility or age gating, or authentication — before it constructs purchasable state, and routes the buyer accordingly.

A Business SHOULD apply query parameters it understands. Applied parameters may affect server-side state or destination selection, and are not required to appear on the redirect URL. UCP field-path query parameters SHOULD be consumed and removed by default.

A Business SHOULD preserve non-UCP query parameters on the redirect destination by default so client-side analytics, routing, compatibility, and frontend behavior can continue to work. The Business MAY drop or rewrite non-UCP query parameters when preserving them would be unsafe, incompatible with the destination, or disallowed by Business policy. When a selected UCP field path is exposed on the destination URL, the Business SHOULD rewrite it to an appropriate non-UCP query parameter. For attribution fields, the usual rewrite is to strip the `attribution/` prefix.

For example, this permalink request:

```text
/buy/sku_123:1?continue_to=/collections/spring&buyer/email=alice%40example.com&buyer/unknown=foo&attribution/utm_source=email&utm_medium=sms&color=black&access_token=secret
```

can resolve to:

```http
HTTP/1.1 303 See Other
Location: https://merchant.example/collections/spring?utm_source=email&utm_medium=sms&color=black
```

In this example:

- consumed: `sku_123:1` initializes server-side shopping state, `continue_to` selects the destination path, and `buyer/email` is applied to server-side state;
- dropped: `buyer/unknown` is a UCP field-path query parameter because `buyer` is a UCP root, but the full field path is not recognized or applicable;
- rewritten: `attribution/utm_source` is selected for client-side analytics and emitted as `utm_source`;
- passed through: `utm_medium` and `color` are non-UCP query parameters preserved for client-side analytics and storefront behavior;
- dropped: `access_token` is a non-UCP query parameter, but it is sensitive.

A Business MUST NOT echo sensitive values (see [Privacy](#privacy)) onto redirect destinations.

## Error Handling

Handled shopping errors occur when the URL can be parsed, but the provided inputs cannot be fully applied. Examples include item unavailability, quantity capping, invalid discount codes, unavailable payment handlers, ignored buyer fields, unsupported extension fields, or checkout ineligibility.

For handled shopping errors, the Business SHOULD keep the `303` redirect model and present buyer-facing remediation at the destination. If a valid `continue_to` value is present, the Business SHOULD route to that destination after applying any safe inputs; otherwise it SHOULD route to a purchase, shopping, or remediation destination appropriate for the failure.

Malformed or unsafe requests include malformed item tokens, invalid quantities, invalid base64url tokens, unsafe `continue_to` values, unparseable queries, or control characters. A Business SHOULD redirect malformed browser requests to a safe buyer-facing fallback when possible, but MAY return `4xx` when the request cannot be safely interpreted.

Error presentation SHOULD prefer server-side session state or destination-page state.

## Examples

### Single item default purchase

```text
https://merchant.example/buy/sku_123:1
```

Initialized data:

```json
{
  "line_items": [
    {
      "item": { "id": "sku_123" },
      "quantity": 1
    }
  ]
}
```

Possible resolution:

```http
HTTP/1.1 303 See Other
Location: https://checkout.merchant.example/session/chk_123
```

### Campaign link with discount and continuation

```text
https://merchant.example/buy/sku_123:1,sku_456:2?continue_to=/collections/spring&discounts/codes/0=SPRING10&attribution/utm_source=email
```

Initialized data:

```json
{
  "line_items": [
    {
      "item": { "id": "sku_123" },
      "quantity": 1
    },
    {
      "item": { "id": "sku_456" },
      "quantity": 2
    }
  ],
  "discounts": {
    "codes": ["SPRING10"]
  },
  "attribution": {
    "utm_source": "email"
  }
}
```

`continue_to` requests browser navigation after the Business applies the permalink inputs. The Business consumes `attribution/utm_source` and may rewrite it as `utm_source` on the redirect destination for client-side analytics.

Possible resolution:

```http
HTTP/1.1 303 See Other
Location: https://merchant.example/collections/spring?utm_source=email
```

### Buyer-directed purchase link

```text
https://merchant.example/buy/sku_kit:3,~Z2lkOi8vc2hvcGlmeS9Qcm9kdWN0VmFyaWFudC83MDg4MTQxMg:2?discounts/codes/0=VIP20&discounts/codes/1=WELCOME&buyer/email=alice%40foo.com&buyer/phone_number=123-456-7890&context/address_country=US&context/postal_code=94105&context/language=en-US&attribution/ref=creator_42&attribution/utm_source=social&context/payment/0/handler=com.example.wallet
```

Initialized data:

```json
{
  "line_items": [
    {
      "item": { "id": "sku_kit" },
      "quantity": 3
    },
    {
      "item": {
        "id": "gid://shopify/ProductVariant/70881412"
      },
      "quantity": 2
    }
  ],
  "discounts": {
    "codes": ["VIP20", "WELCOME"]
  },
  "buyer": {
    "email": "alice@foo.com",
    "phone_number": "123-456-7890"
  },
  "context": {
    "address_country": "US",
    "postal_code": "94105",
    "language": "en-US",
    "payment": [{ "handler": "com.example.wallet" }]
  },
  "attribution": {
    "ref": "creator_42",
    "utm_source": "social"
  }
}
```

`context/payment` is a preference hint: a Business SHOULD use it to preselect or prioritize the handler (and type) and MAY ignore unavailable or ineligible values.

Possible resolution:

```http
HTTP/1.1 303 See Other
Location: https://checkout.merchant.example/session/chk_123
```

### Pickup with a pre-selected destination

```text
https://merchant.example/buy/sku_123:1?fulfillment/methods/0/type=pickup&fulfillment/methods/0/selected_destination_id=loc_1375
```

Initialized data:

```json
{
  "line_items": [{ "item": { "id": "sku_123" }, "quantity": 1 }],
  "fulfillment": {
    "methods": [{ "type": "pickup", "selected_destination_id": "loc_1375" }]
  }
}
```

When the fulfillment extension is active for the flow, a permalink can pre-select a fulfillment method and a destination the buyer already knows — for example, a store chosen from a locator. This uses the same field-path mechanism as any extension: `methods/0` addresses cart-level fulfillment positionally, because the cart — and any per-line-item or per-group fulfillment keyed on server-generated IDs — does not exist until the Business resolves the link.

Possible resolution:

```http
HTTP/1.1 303 See Other
Location: https://checkout.merchant.example/session/chk_123
```

## Security Considerations

A permalink endpoint is an unauthenticated browser GET. Every component of the URL is externally supplied and untrusted, and browsers, prefetchers, link-preview bots, and security scanners load permalink URLs without buyer intent.

A Business MUST validate every input as untrusted: compact-path and `~`-encoded item tokens (see [Item ID Token](#item-id-token)), `continue_to` (see [Destination Preference](#destination-preference-continue_to)), and field-path query parameters (see [Query Processing](#query-processing)). Those rules prevent open redirects, response-header injection, mass-assignment of server-owned fields, and log injection or parser confusion from control characters in decoded tokens and values.

A permalink URL exposes the inputs it carries: the referring page's `Referer` may leak the URL itself, and the `303` response's `Cache-Control` and referrer policy (see [Redirect Resolution](#redirect-resolution)) keep it from being cached or forwarded to the destination.

### Privacy

Permalink URLs leak via browser history, logs, analytics, referrers, screenshots, link previews, and copied messages. Platforms and Businesses SHOULD include only data that is appropriate for the channel.

Broad-campaign links SHOULD prefer item IDs, quantities, coarse context, compact extension fields such as discount codes, `continue_to`, a `context/payment` preference, and non-UCP campaign query parameters.

Buyer-directed links MAY include minimal buyer prefill, such as:

```text
buyer/email=alice%40example.com
buyer/first_name=Alice
```

when appropriate for the channel and active schema/profile semantics. Platforms and Businesses SHOULD avoid PII in broadly shared links. A Business SHOULD redirect to a URL that does not contain the original buyer values, redact PII from logs where practical, and let buyers edit prefilled values.

Permalinks MUST NOT contain payment credentials, payment instrument tokens, customer access tokens, session cookies, AP2 mandates, API keys, bearer tokens, or one-time secrets.

## URL Budget

Platforms and Businesses SHOULD size the fully serialized absolute URL, after URL encoding, in UTF-8 octets. Different browsers, messengers, scanners, CDNs, and origin servers impose different practical limits, so broadly distributed permalinks SHOULD be intentionally small.

Recommended URL budgets:

| Channel                               | Recommended maximum |
| ------------------------------------- | ------------------- |
| QR codes, print, short social posts   | 512 octets          |
| SMS and broadly shared campaign links | 1,024 octets        |
| Email and authenticated handoff       | 2,048 octets        |

Platforms and Businesses SHOULD stay within these budgets, and SHOULD exceed the QR budget only after testing the intended print size, distance, contrast, and scanner environment.

When a link would exceed the appropriate budget, reduce it to the compact subset described in [Privacy](#privacy). Private or highly personalized state SHOULD be consumed server-side and MUST NOT be forwarded to redirect destinations.

A Business SHOULD accept absolute permalink URLs of at least 2,048 octets. A Business MAY enforce documented limits for URL length, compact item count, query parameter count, pointer depth, and decoded value length. Requests that exceed those limits MAY be redirected to buyer-facing remediation or rejected with an appropriate `4xx` response.
