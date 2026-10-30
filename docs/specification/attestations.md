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
<!-- cspell:ignore bistrolumiere alpinegear ecocertifier lumiere marais paris publicsuffix -->

# Verifiable Attestations

* **Schema:** `https://ucp.dev/{{ ucp_version }}/schemas/common/types/attestation.json`
* **Token Media Type:** `application/ucp-attestation+jwt` (`typ: "ucp-attestation+jwt"`)

## Overview

[Business Summary](reference.md#business-summary) (`common/types/business_summary.json`, reused by `dev.ucp.common.business` on discovery profiles and by response-normalized `sellers` maps in Catalog, Cart, Checkout, and Order) and [Location](common/location/index.md) (`dev.ucp.common.location.*`) let a Business or seller declare who it is and where its physical branches operate, while [Authority Binding](overview/index.md#authority-binding) proves that a profile was published by the party controlling its domain. Those mechanisms establish provenance, not third-party verification: self-declared fields are presented as stated, and any merchant or seller can self-declare an ISO 18245 Merchant Category Code (`mcc`), claim authorized-retailer status for a brand, display a sustainability badge, or claim a culinary distinction.

**Verifiable Attestations** let a Business, marketplace seller, or regional legal entity publish statements that an accountable third party (such as a culinary guide like the Michelin Guide, a brand, an acquiring bank, a marketplace host, an accredited certification body, or a trade association) has checked and cryptographically signed:

1. **Issuer signs once:** The issuer signs a compact JSON Web Signature (JWS, [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515)) profiled from [OpenID Federation 1.0 §7 Trust Marks](https://openid.net/specs/openid-federation-1_0.html#section-7), bound to a canonical `/.well-known/ucp` profile URL (`sub`) and optionally scoped to a physical branch (`location_id`) or a response-normalized seller entry (`seller_id`).
2. **Business or marketplace publishes inline:** The publisher places the opaque token in `attestations[]` on `common/types/business_summary.json` (covering profile `dev.ucp.common.business`, catalog `sellers[seller_id]`, and cart/checkout/order `sellers[seller_id]`) or on `common/types/location.json` (`Location.attestations[]`).
3. **Any Platform or agent verifies:** Verifiers check namespace provenance via UCP's [Authority Binding](overview/index.md#derivation-algorithm), apply their own issuer trust policy, and verify the JWS signature against `keys[]` published at the issuer's `iss` URL.

UCP standardizes the token profile, placement, symmetric scope binding, and verification rules only. It does not operate a central trust list or standardize vertical-specific attestation types; each domain owner defines its own reverse-domain attestation types, claim schemas, and renewal lifetimes.

---

## Token Format

An attestation token is a compact JWS ([RFC 7515](https://www.rfc-editor.org/rfc/rfc7515)) whose payload uses the [OpenID Federation 1.0 §7 Trust Mark](https://openid.net/specs/openid-federation-1_0.html#section-7) claims.

### Protected Header

The JWS Protected Header **MUST** be a JSON object containing:

| Parameter | Requirement | Description |
| :--- | :--- | :--- |
| `typ` | **REQUIRED** | **MUST** equal `"ucp-attestation+jwt"`. Explicit typing prevents cross-JWT confusion with other tokens signed by the same `keys[]`, such as AP2 mandates or onboarding assertions ([RFC 8725 §3.11](https://www.rfc-editor.org/rfc/rfc8725#section-3.11)). |
| `alg` | **REQUIRED** | Asymmetric JWS algorithm identifier per [Signature Algorithms](signatures.md#signature-algorithms). Verifiers **MUST** support `ES256`; `ES384` and `EdDSA` (`Ed25519`) are **OPTIONAL**. Unsecured (`"none"`) and symmetric (`"HS256"`, `"HS384"`, `"HS512"`) algorithms **MUST** be rejected. |
| `kid` | **REQUIRED** | Non-empty key identifier selecting the signing key in `keys[]` at `iss`. |

<!-- ucp:example skip reason="Decoded JWS Protected Header, not a UCP payload" -->
```json
{
  "typ": "ucp-attestation+jwt",
  "alg": "ES256",
  "kid": "guide-2026"
}
```

### Payload Claims

The JWS Payload **MUST** be a JSON object conforming to `attestation.json#/$defs/claims`. Issuers **MAY** define additional top-level claims governed by `trust_mark_type`, and **MUST NOT** include both `location_id` and `seller_id` in the same token.

<!-- ucp:example schema=common/types/attestation def=claims -->
```json
{
  "iss": "https://guide.example/.well-known/jwks.json",
  "sub": "https://bistrolumiere.example/.well-known/ucp",
  "location_id": "loc_paris_marais",
  "trust_mark_type": "example.guide.culinary_distinction",
  "iat": 1788220800,
  "exp": 1819756800,
  "logo_uri": "https://guide.example/marks/one-star-2026.svg",
  "ref": "https://guide.example/restaurants/bistro-lumiere",
  "distinction": "one_star"
}
```

---

## Publishing Attestations

Businesses and marketplaces publish attestations as `{ "type": "<reverse-domain>", "token": "<compact-jws>" }` entries in `attestations[]` on `common/types/business_summary.json` and `common/types/location.json`:

* **Outer `type` selector:** `type` **MUST** equal the signed `trust_mark_type` claim inside `token`. Consumers inspect `type` to select attestations of interest without decoding irrelevant tokens or fetching unrecognized issuer keys.
* **Opaque token handling:** Publishers treat `token` as an opaque ASCII string so JSON serialization or formatting changes in a profile, catalog, checkout, or Location response never invalidate the issuer's signature.

### Surfaces Powered by `business_summary.json` and `location.json`

Attaching `attestations[]` to [Business Summary](reference.md#business-summary) (`common/types/business_summary.json`) and [Location](common/location/index.md) (`common/types/location.json`) enables verifiable attestations across four UCP surfaces with a single container schema:

1. **Profile Brand Card (`dev.ucp.common.business` `config` in `/.well-known/ucp`):** Publishes business-wide attestations for the profile host (`sub` equals the canonical `/.well-known/ucp` URL; `location_id` and `seller_id` are absent). Because each version-specific profile referenced via `supported_versions` is a self-contained document, leaf profiles **SHOULD** include `attestations[]` in `dev.ucp.common.business` when present.
2. **Catalog Seller Attribution (`sellers[seller_id]` in Catalog Search and Lookup):** Publishes attestations for first-party or third-party sellers in catalog `search_response`, `lookup_response`, and `get_product_response` payloads (for example, a brand-signed `authorized_retailer` mark or a marketplace-signed `verified_trader` status for a third-party seller).
3. **Transactional Seller of Record (`sellers[seller_id]` in Cart, Checkout, and Order):** Publishes attestations for the resolved contracting legal entity (such as a regional subsidiary or a marketplace merchant) once buyer context or shipping address is known.
4. **Physical Branches (`Location` objects in `common/types/location.json`):** Publishes branch-specific attestations returned by [Location Search](common/location/search.md) and [Location Lookup](common/location/lookup.md), with `location_id` set to `Location.id`.

### Business and Seller Attestations (`business_summary.json`)

Facts that apply to a business entity, marketplace seller, or contracting legal entity (such as an acquirer's underwritten MCC, verified trader status, a brand's authorized-retailer credential, or a business-wide sustainability certification) are published in the optional `attestations[]` array on `common/types/business_summary.json`:

<!-- cspell:disable -->
<!-- ucp:example schema=common/types/business_summary -->
```json
{
  "name": "Bistro Lumiere",
  "legal_name": "Bistro Lumiere SAS",
  "links": [
    {
      "type": "website",
      "url": "https://bistrolumiere.example"
    }
  ],
  "address": {
    "street_address": "14 Rue des Rosiers",
    "address_locality": "Paris",
    "postal_code": "75004",
    "address_country": "FR"
  },
  "attestations": [
    {
      "type": "example.acquirer.merchant_verification",
      "token": "eyJ0eXAiOiJ1Y3AtYXR0ZXN0YXRpb24rand0IiwiYWxnIjoiRVMyNTYiLCJraWQiOiJhY3EtMjAyNiJ9.eyJpc3MiOiJodHRwczovL2FjcXVpcmVyLmV4YW1wbGUvLndlbGwta25vd24vdWNwIiwic3ViIjoiaHR0cHM6Ly9iaXN0cm9sdW1pZXJlLmV4YW1wbGUvLndlbGwta25vd24vdWNwIiwidHJ1c3RfbWFya190eXBlIjoiZXhhbXBsZS5hY3F1aXJlci5tZXJjaGFudF92ZXJpZmljYXRpb24iLCJpYXQiOjE3ODgyMjA4MDAsImV4cCI6MTgxOTc1NjgwMCwibGVnYWxfbmFtZSI6IkJpc3RybyBMdW1pZXJlIFNBUyIsIm1jYyI6IjU4MTIifQ.AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0-Pw"
    }
  ]
}
```
<!-- cspell:enable -->

### Location-Scoped Attestations (`location.json`)

Facts scoped to one physical branch (such as a culinary guide distinction for a single restaurant branch, a municipal health inspection grade, or a physical storefront verification) are published in `attestations[]` on that `Location` object (`common/types/location.json`, returned by [Location Search](common/location/search.md) and [Location Lookup](common/location/lookup.md)), with `location_id` matching `Location.id`:

<!-- cspell:disable -->
<!-- ucp:example schema=common/location_lookup op=lookup direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.location.lookup": [
        {
          "version": "{{ ucp_version }}"
        }
      ]
    }
  },
  "locations": [
    {
      "id": "loc_paris_marais",
      "inputs": [
        {
          "id": "loc_paris_marais"
        }
      ],
      "name": "Bistro Lumiere Marais",
      "address": {
        "street_address": "14 Rue des Rosiers",
        "address_locality": "Paris",
        "postal_code": "75004",
        "address_country": "FR"
      },
      "attestations": [
        {
          "type": "example.guide.culinary_distinction",
          "token": "eyJ0eXAiOiJ1Y3AtYXR0ZXN0YXRpb24rand0IiwiYWxnIjoiRVMyNTYiLCJraWQiOiJndWlkZS0yMDI2In0.eyJpc3MiOiJodHRwczovL2d1aWRlLmV4YW1wbGUvLndlbGwta25vd24vandrcy5qc29uIiwic3ViIjoiaHR0cHM6Ly9iaXN0cm9sdW1pZXJlLmV4YW1wbGUvLndlbGwta25vd24vdWNwIiwibG9jYXRpb25faWQiOiJsb2NfcGFyaXNfbWFyYWlzIiwidHJ1c3RfbWFya190eXBlIjoiZXhhbXBsZS5ndWlkZS5jdWxpbmFyeV9kaXN0aW5jdGlvbiIsImlhdCI6MTc4ODIyMDgwMCwiZXhwIjoxODE5NzU2ODAwLCJsb2dvX3VyaSI6Imh0dHBzOi8vZ3VpZGUuZXhhbXBsZS9tYXJrcy9vbmUtc3Rhci0yMDI2LnN2ZyIsInJlZiI6Imh0dHBzOi8vZ3VpZGUuZXhhbXBsZS9yZXN0YXVyYW50cy9iaXN0cm8tbHVtaWVyZSIsImRpc3RpbmN0aW9uIjoib25lX3N0YXIifQ.AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0-Pw"
        }
      ]
    }
  ]
}
```
<!-- cspell:enable -->

---

## Three Attestation Privacy Tiers

Attaching `attestations[]` to `business_summary.json` and `location.json` supports three privacy-appropriate publishing tiers across public discovery and authenticated transactions:

| Tier | Where Published | What Goes in the Token | Example Use Cases |
| :--- | :--- | :--- | :--- |
| **1. Public Discovery Attestations** | `/.well-known/ucp` (`dev.ucp.common.business`), Catalog `sellers[seller_id]`, and `Location` | Publicly cacheable brand, credential, or branch endorsements | Brand-signed authorized retailer status (`example.alpinegear.authorized_retailer`), accredited sustainability certifications (`example.ecocertifier.certified_sustainable`), culinary guide distinctions (`example.guide.culinary_distinction`) |
| **2. Status-Only Public Attestations** | `/.well-known/ucp` (`dev.ucp.common.business`) and Catalog `sellers[seller_id]` | Public boolean or classification claims signed after the issuer verifies private KYB, tax, or identity documents offline (zero raw PII, home addresses, or private tax numbers in the JWT) | EU DSA Art. 30 verified trader status (`verified_trader: true`), acquirer-underwritten merchant category (`mcc: "5812"`), age-verified merchant standing |
| **3. Transactional / Context-Gated Attestations** | `checkout.sellers[seller_id]` (and `order.sellers[seller_id]`) returned to an authenticated Platform | Market-specific legal-entity attestations, statutory registration claims, or selective-disclosure credentials bound after buyer `context` or shipping `address` fixes the jurisdiction | Regional legal-entity verification (such as US Inc. vs. Canada Ltd. subsidiaries), jurisdiction-specific VAT or statutory registration attestations, B2B tax-exemption or compliance credentials |

* **No private underwriting or personal data in public tokens:** Issuers and Businesses **MUST NOT** place non-public financial, underwriting, or personal data (such as payment volume, chargeback rates, proprietary risk scores, personal national identification numbers, sole-proprietor residential addresses, or private tax filings) in publicly served Tier 1 or Tier 2 attestations. When discovery requires proof of compliance or underwriting, issuers verify private documents offline and sign a status-only claim (`verified_trader: true`, `mcc: "5812"`).
* **Context-gated transactional disclosures:** When statutory disclosures, regional legal-entity verification, or B2B compliance credentials should only be disclosed in an authenticated transaction once buyer `context` or shipping `address` fixes the market, the Business or marketplace returns those attestations in Tier 3 on `checkout.sellers[seller_id].attestations[]` (and snapshots them on `order.sellers[seller_id].attestations[]`) rather than in static `/.well-known/ucp` files.
* **Hosting is not vouching:** A commerce platform, marketplace, or directory that hosts a merchant's profile or serves its catalog is not attesting to the business's identity or standing unless it signs an attestation token.

---

## Issuer Key Discovery (`iss`)

An issuer publishes its verification keys as an RFC 7517 JWK Set (`keys[]`) at its `iss` URL:

* **Issuers with a UCP profile (`/.well-known/ucp`):** Any party that already hosts a UCP profile at `https://<host>/.well-known/ucp` reuses that URL as `iss` because every UCP profile carrying `keys[]` is already a valid JWK Set (see [Profile Structure](overview/index.md#profile-structure)).
* **Non-commerce issuers (`/.well-known/jwks.json`):** Issuers that do not offer UCP commerce capabilities (such as culinary guides, certification bodies, acquiring banks, or brands without UCP endpoints) **MAY** publish a standalone RFC 7517 JWK Set at `https://<host>/.well-known/jwks.json` without UCP protocol metadata:

<!-- ucp:example skip reason="Standalone RFC 7517 JWK Set hosted by a non-UCP issuer" -->
```json
{
  "keys": [
    {
      "kid": "guide-2026",
      "kty": "EC",
      "crv": "P-256",
      "x": "MKBCTNIcKUSDii11ySs3526iDZ8AiTo7Tu6KPAqv7D4",
      "y": "4Etl6SRW2YiLUrN5vfvVHuhp7x8PxltmWWlbbM4IFyM",
      "use": "sig",
      "alg": "ES256"
    }
  ]
}
```

Unless a verifier's local trust configuration explicitly pins an exact `iss` URL (such as a known Platform Profile URL), verifiers **MUST** require `iss` to use `https` with an [RFC 8615](https://www.rfc-editor.org/rfc/rfc8615) well-known path of `/.well-known/ucp` or `/.well-known/jwks.json` (with no query or fragment components). Constraining `iss` to origin-controlled well-known paths prevents unprivileged user-content paths on a domain from publishing rogue key sets under that domain's authority.

---

## Verification Algorithm

Verifiers evaluate each entry in `attestations[]` independently. A single attestation that is expired, untrusted, signed with an unsupported algorithm, or otherwise invalid **MUST** be discarded individually and **MUST NOT** cause the verifier to reject the enclosing business profile, `sellers[seller_id]` entry, or `Location`.

To verify an attestation entry `{ type, token }` against the host's canonical `/.well-known/ucp` profile URL `host_profile_url`:

1. **Pre-filter by `type`:** Check that `type` is a syntactically valid reverse-domain identifier (`reverse_domain_name.json`). If the verifier has no interest in `type`, skip the entry without decoding `token`.
2. **Parse JWS structure and header:** Split `token` into its three base64url-encoded compact JWS segments and decode the Protected Header and Payload without performing network I/O:
    * `typ` **MUST** equal `"ucp-attestation+jwt"`.
    * `kid` **MUST** be a non-empty string.
    * `alg` **MUST** be a supported asymmetric JWS signature algorithm (`ES256` mandatory baseline; `ES384` and `EdDSA` optional per [Signature Algorithms](signatures.md#signature-algorithms)). Reject `"none"` and symmetric algorithms (`"HS*"`).
3. **Validate payload claims and lifetime:**
    * `trust_mark_type` **MUST** equal the outer entry's `type`.
    * `iat` and `exp` **MUST** be integers, and the current time `now` **MUST** satisfy `iat <= now < exp` (and `nbf <= now` if `nbf` is present). Verifiers **MAY** allow a small clock-skew leeway (up to 60 seconds) per [RFC 7519 §4.1.4](https://www.rfc-editor.org/rfc/rfc7519#section-4.1.4), and **MAY** reject lifetimes (`exp - iat`) exceeding their local maximum for that type.
4. **Validate symmetric subject and scope binding (`sub`, `location_id`, `seller_id`):**
    * **On `dev.ucp.common.business` (`config` in `/.well-known/ucp`):** `sub` **MUST** equal `host_profile_url` by exact character-for-character string comparison, and both `location_id` and `seller_id` **MUST** be absent. Rejecting `location_id` and `seller_id` on profile-level `config` prevents a branch-scoped or marketplace-seller credential from being treated as business-wide for the host.
    * **On `Location.attestations[]`:** `sub` **MUST** equal `host_profile_url` (the canonical URL of the business profile from which that Location capability was discovered), `location_id` **MUST** equal `Location.id`, and `seller_id` **MUST** be absent.
    * **On `sellers[seller_id].attestations[]` (in Catalog, Cart, Checkout, or Order):** `location_id` **MUST** be absent, and `sub` **MUST** satisfy one of two symmetric bindings:
        1. *Seller with its own UCP profile:* `seller.profile` is present on the seller entry, `sub` equals `seller.profile` (the canonical `/.well-known/ucp` URL of that seller), and `seller_id` is absent in the JWT claims.
        2. *Platform-hosted third-party seller or regional legal entity without a separate UCP profile:* `sub` equals `host_profile_url`, and `seller_id` in the JWT claims equals the entry's key in the `sellers` map. Requiring `seller_id` when `sub` is the host profile prevents an attestation issued for one marketplace seller or regional entity from being replayed on another seller entry under the same host.
5. **Enforce namespace provenance and verifier trust policy (pre-fetch gate):**
    * Unless `iss` matches an exact URL explicitly pinned in the verifier's local trust configuration, `iss` **MUST** parse as an `https` URL with no userinfo, query, or fragment, and its path **MUST** be `/.well-known/ucp` or `/.well-known/jwks.json`.
    * The `iss` URL host **MUST** satisfy UCP's [Authority Binding Derivation Algorithm](overview/index.md#derivation-algorithm) for `trust_mark_type` (reversed hostname equals `trust_mark_type` or is a label-aligned prefix of it). As noted in [Authority Binding](overview/index.md#derivation-algorithm), multi-tenant public suffixes (`publicsuffix.org`) are shared across independent co-tenants; issuers **MUST** declare types under a registrable domain they exclusively control, and verifiers **MUST NOT** treat a co-tenant host on a shared suffix as authoritative for sibling tenants.
    * Check whether `(iss, trust_mark_type)` is accepted by the verifier's trust policy. If untrusted, the verifier **MUST** stop immediately and **MUST NOT** dereference `iss` or `status.status_list.uri`.
6. **Fetch issuer keys and verify JWS signature:**
    * Dereference `iss` (or read from cache) under UCP's [Profile Fetching rules](overview/index.md#fetching): HTTPS only, no `3xx` redirects, [RFC 6890](https://www.rfc-editor.org/rfc/rfc6890) special-use IP rejection on resolved addresses, minimum 60-second cache TTL floor, at most one unknown-`kid` force-refresh per TTL floor per origin, and bounded response body size.
    * Select the JWK in `keys[]` matching `kid` after filtering out keys unusable for signature verification (`use: "enc"`, `key_ops` omitting `"verify"`, or private/symmetric key material per [Message Signatures](signatures.md)).
    * Confirm that the JWK's key type, curve, and optional `alg` match the JWS header `alg` (`EC`/`P-256` with `ES256`, `EC`/`P-384` with `ES384`, `OKP`/`Ed25519` with `EdDSA`), and cryptographically verify the compact JWS signature per [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515).
7. **Check revocation status (when `status` is present):**
    * If `status` is present (or required by verifier policy for `trust_mark_type`), verify that `status.status_list.uri` is an `https` URL whose host satisfies Authority Binding for `trust_mark_type` (or matches the `iss` origin).
    * Fetch and cache the Status List Token from `status.status_list.uri` under the same [Profile Fetching](overview/index.md#fetching) SSRF, redirect, and caching rules, verify its signature against `keys[]` at `iss`, and confirm per [IETF Token Status List](https://datatracker.ietf.org/doc/draft-ietf-oauth-status-list/) that the status value at `status.status_list.idx` is `0` (`VALID`).

### Attribute Binding (Signed Claims vs. Unsigned Fields)

An attestation cryptographically binds **only the claims inside its signed JWS payload**. It does **not** sign sibling fields in the enclosing `business_summary.json` object (`dev.ucp.common.business` or `sellers[seller_id]`) or `Location` object.

On a merchant-controlled domain, the Business can edit `name`, `legal_name`, `address`, `geo`, `contacts`, or `categories` in its profile, `sellers` map, or `Location` response after an attestation is issued without changing `sub`, `location_id`, or `seller_id`. Accordingly:

* When an attestation vouches for specific mutable attributes (such as a verified `legal_name`, registered or physical `address`, underwritten ISO 18245 `mcc`, or a verified phone number or email channel), the issuer **SHOULD** include those attested values (or a canonical digest) as claims inside the JWT payload.
* Verifiers **MUST** rely on the signed claims inside the attestation (or verify that the corresponding fields in the enclosing `business_summary.json` or `Location` object match those signed claims) before treating any mutable business, seller, or Location attribute as verified.

---

## Revocation and Lifetimes

Because profiles, catalog responses, checkout sessions, and Location endpoints are served by the Business or marketplace, an external issuer cannot delete a previously issued token from a merchant's infrastructure. UCP bounds stale attestations through three layers:

1. **Bounded lifetimes (`exp`):** Every UCP attestation requires `exp`. Type owners define renewal cadences matched to the underlying check (for example, annual renewal for culinary distinctions or sustainability audits, and quarterly renewal for merchant standing or dealer status).
2. **Token Status Lists (`status`):** Issuers needing immediate mid-cycle revocation include a `status` claim referencing an [IETF Token Status List](https://datatracker.ietf.org/doc/draft-ietf-oauth-status-list/). Because verifiers fetch and cache the compressed status list in bulk rather than querying per-merchant OCSP-style endpoints, issuers do not observe which businesses or sellers an agent or Platform is evaluating.
3. **Key rotation or removal:** Removing a signing key (`kid`) from `keys[]` at `iss` invalidates all attestations signed by that key once verifier caches expire. Issuers **MAY** use dedicated keys per attestation type or issuance period to limit the blast radius of key removal.

---

## Defining Attestation Types

Any domain owner can define an attestation type under its reverse-domain namespace (`reverse_domain_name.json`), following the same authority model as UCP capabilities. Type specifications **SHOULD** document:

* The exact `trust_mark_type` identifier, privacy tier, and whether tokens attach to `business_summary.json` (`dev.ucp.common.business` and `sellers[seller_id]`) or `Location.attestations[]`.
* Required and optional type-specific claims (including scope claims `location_id` or `seller_id`, and attribute-binding claims such as `legal_name`, `mcc`, `verified_trader`, `address`, or `regions`).
* Recommended `exp` lifetime and whether `status` list support is used.

Illustrative (non-normative) examples:

| Example `trust_mark_type` | Issuer (`iss`) | Tier and Placement | Example Signed Claims |
| :--- | :--- | :--- | :--- |
| `example.guide.culinary_distinction` | Culinary guide (`/.well-known/jwks.json`) | Tier 1 (Public Discovery, on `Location`) | `location_id`, `distinction`, `logo_uri`, `ref` |
| `example.alpinegear.authorized_retailer` | Brand (`/.well-known/ucp`) | Tier 1 (Public Discovery, on `business_summary.json`) | `seller_id` (optional), `regions[]`, `product_lines[]` |
| `example.ecocertifier.certified_sustainable` | Accredited certifier (`/.well-known/jwks.json`) | Tier 1 (Public Discovery, on `business_summary.json`) | `scheme`, `certificate_id`, `logo_uri`, `ref` |
| `example.marketplace.verified_trader` | Marketplace or PSP (`/.well-known/ucp`) | Tier 2 (Status-Only Public, on `business_summary.json`) | `seller_id`, `verified_trader`, `jurisdiction` |
| `example.acquirer.merchant_verification` | Acquiring bank or PSP (`/.well-known/ucp`) | Tier 2 (Status-Only Public) or Tier 3 (Transactional on `checkout.sellers[seller_id]`) | `seller_id` (optional), `legal_name`, `mcc`, `address`, `registration_id` |

---

## Schema

### Attestation {: #attestation }

{{ schema_fields('types/attestation', 'attestations') }}

### Attestation Claims {: #claims }

{{ extension_schema_fields('types/attestation.json#/$defs/claims', 'attestations') }}

### Attestation Status {: #status }

{{ extension_schema_fields('types/attestation.json#/$defs/status', 'attestations') }}

### Status List Reference {: #status-list }

{{ extension_schema_fields('types/attestation.json#/$defs/status_list', 'attestations') }}
