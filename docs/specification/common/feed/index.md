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

# Feed Capability

* **Capability Name:** `dev.ucp.common.feed`

A feed is a materialized publication of records: the same records a Platform
would receive from a capability's live operations, published in bulk as files
so the Platform can index, embed, and rank them offline, then call the live
operations at serving time for the authoritative values. The capability adds
one endpoint declaration and two document shapes (a feed list and a manifest);
it adds no record data model. The shape of a feed's records is declared by the
manifest's `ucp.capabilities`, and the capability that defines those records
remains authoritative at serving time. The feed and the live capability are
complementary: the feed is point-in-time, the live operations are
authoritative.

The capability is built from UCP primitives. Discovery is a capability whose
`config` names the endpoint that serves the feed list. Market scope is the UCP
`context` object. Records take the shape that an extension of this capability
defines; the examples in this document use
[Shopping Catalog Feed](../../shopping/catalog/feed.md), whose records are
catalog Products, as the illustrative domain. Access control is UCP's existing
Platform authentication on the feed endpoint. Extensions compose onto records
as they do onto operation responses.

## Discovery

The Business advertises the capability in its profile under `capabilities`
and **MUST** include `config.endpoint`, the absolute HTTPS URL that serves the
feed list. A Platform treats a declaration without `config.endpoint` as not
present and never activates it. The endpoint is the sole entry point to the
Business's feeds; see [Access and Provenance](#access-and-provenance) for why
the URLs reached through it are trusted.

The endpoint is declared once, on this capability, and serves one feed list
that may carry feeds of more than one record type. A capability that defines a
record type for feeds is an extension of this one: its profile entry declares
`extends: "dev.ucp.common.feed"`, and its specification defines its records and
any further manifest fields they require. A Platform activates an extension
only when its parent is in the negotiated set (see [Negotiation
Protocol](../../overview/index.md#negotiation-protocol)), so a record-type
extension declared without `dev.ucp.common.feed` is pruned and never activated.
The profile below declares both: `dev.ucp.common.feed`, carrying the endpoint,
and the [Shopping Catalog Feed](../../shopping/catalog/feed.md) extension
`dev.ucp.shopping.catalog.feed`.

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.common.feed": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/feed",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/feed.json",
        "config": {
          "endpoint": "https://merchant.example.com/ucp/feeds"
        }
      }],
      "dev.ucp.shopping.catalog.feed": [{
        "version": "{{ ucp_version }}",
        "extends": "dev.ucp.common.feed",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/catalog/feed",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/catalog_feed.json"
      }]
    },
    "payment_handlers": {}
  }
}
```

{{ extension_schema_fields('feed.json#/$defs/config', 'common/feed') }}

The Business **MAY** place `config.endpoint` on any HTTPS origin, and **MAY**
have it operated by a party other than the one serving its service endpoint
(a commerce platform or a delegated feed publisher). The operator acts for the
Business, and the Business controls the delegation through its profile:
changing or removing `config.endpoint` changes or revokes it.

## Feed List

A Platform fetches `config.endpoint` with an HTTPS `GET`, sending the
`UCP-Agent` header and, where the Business requires authentication, the same
mechanisms available for requests to the Business's service endpoint: an API
key, OAuth 2.0, mTLS, or a request signature per the
[Message Signatures](../../signatures.md) specification. The response is the
feed list document.

The feed list is provisioned for the caller: an unauthenticated fetch returns
the Business's public feeds, if any; an authenticated fetch returns the feeds
the Business has provisioned for that Platform, and it is authoritative and
complete for that caller: the feeds it lists are the feeds available to that
Platform. `feeds` can be empty. The order of entries carries no meaning,
except that a Platform applies supplemental feeds of the same base feed in
list order (see [Supplemental Feeds](#supplemental-feeds)). The feed list's
`ucp.capabilities` declares `dev.ucp.common.feed`; nothing more is required or
given meaning there, because the list is shared by every feed the Business
publishes, whatever its record type. `messages`, when present, carries errors,
warnings, or informational notices about the feed list in the shape UCP
responses use.

Provisioning is by caller identity, not by request parameters. A Business that
serves different feeds to different surfaces of one Platform (for example,
an advertising crawler and a search crawler) does so by provisioning different
feed lists to their different identities. The endpoint accepts no parameters
that select or shape a feed, because feeds are materialized ahead of time;
which feeds exist for a given caller is settled between the Business and the
Platform outside this capability.

<!-- ucp:example schema=common/feed op=list def=feed_list -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.feed": [
        {"version": "{{ ucp_version }}"}
      ]
    }
  },
  "feeds": [
    {
      "id": "us-en-usd",
      "context": {
        "address_country": "US",
        "language": "en-US",
        "currency": "USD"
      },
      "format": "jsonl+gzip",
      "interval": "P1D",
      "generated_at": "2026-09-22T06:00:00Z",
      "manifest": "https://merchant.example.com/feeds/us-en-usd/20260922T060000Z/manifest.json"
    },
    {
      "id": "ca-fr-cad",
      "context": {
        "address_country": "CA",
        "language": "fr-CA",
        "currency": "CAD"
      },
      "format": "jsonl+gzip",
      "interval": "P1D",
      "generated_at": "2026-09-22T06:10:00Z",
      "manifest": "https://merchant.example.com/feeds/ca-fr-cad/20260922T061000Z/manifest.json"
    }
  ]
}
```

{{ extension_schema_fields('feed.json#/$defs/feed_list', 'common/feed') }}

## Feed

A feed list entry is the Business's advertisement of one feed and a pointer to
its current snapshot. The entry is for discovery; the manifest is
authoritative for what a snapshot contains.

An entry does not name the record type of its feed; the manifest's
`ucp.capabilities` does. A feed list may mix feeds of several record types, so
a Platform that consumes only some of them fetches the manifest of an entry on
first sight and, if the manifest declares a record type the Platform does not
consume, remembers the `id` and skips the entry on later polls.

`id` is a Business-assigned, stable identifier, opaque to Platforms. The
Business **MUST** keep `id` unique within its feed list and stable across
snapshots: snapshots advance, `id` does not. A Platform that receives two
entries with the same `id` **MUST NOT** consume either.

`manifest` is the absolute HTTPS URL of the feed's current manifest. The
Business **MUST** issue a distinct manifest URL for each snapshot and **MUST
NOT** change the document at a manifest URL once published; a snapshot is
immutable at its URL. The Business **MAY** host the manifest on any HTTPS
origin; the URL is trusted because the feed list obtained from the Business's
declared `config.endpoint` returned it, not because of its hostname (see
[Access and Provenance](#access-and-provenance)). A Platform **MUST NOT**
dereference a `manifest` value that is not an absolute HTTPS URL.

`format` is the wire encoding of every file in the feed's current snapshot
(see [Formats](#formats)). It equals the current manifest's `format`, which is
authoritative; the Business **MUST** keep the two equal, and a Platform that
fetches the manifest and finds a different value **MUST NOT** consume that
snapshot. A Platform **MAY** skip an entry whose `format` it does not
recognize without fetching its manifest.

A Business **MAY** publish the same content in more than one format, as
separate entries with the same `context` and distinct `id`s. It **SHOULD**
keep those entries content-identical, except transiently while one entry's
snapshot has rolled and the other's has not. A Platform that consumes that
content picks one of the entries.

`interval` is the expected cadence between snapshots, an ISO 8601 duration
([RFC 3339](https://www.rfc-editor.org/rfc/rfc3339#appendix-A) Appendix A)
such as `P1D` or `PT2H`. It is advisory: it states the Business's intent, not
a guarantee, and a Business **MAY** publish a snapshot earlier or later than
`interval` suggests. The Business **MUST** publish a positive `interval`; a
Platform **MUST NOT** consume a feed whose `interval` is not a positive
duration. Where a Platform compares intervals (see [Etiquette](#etiquette)),
it compares nominal lengths.

`generated_at` is a copy of the current manifest's `generated_at`. The
Business **MUST** keep it equal to the `generated_at` of the manifest at
`manifest`; a Platform that fetches the manifest and finds a different value
**MUST NOT** consume that snapshot. A Platform uses `generated_at` to decide
whether to fetch: it **SHOULD** fetch the manifest only when `generated_at` is
later than that of the snapshot it holds, unless it holds none.

`extends` marks a supplemental feed; see
[Supplemental Feeds](#supplemental-feeds).

{{ extension_schema_fields('feed.json#/$defs/feed', 'common/feed') }}

## Manifest

The document at a feed list entry's `manifest` URL. A manifest is a complete
materialization of one feed as of `generated_at`; this version publishes only
complete snapshots.

!!! note "Design note"
    The feed list and the manifest are separate documents because they belong
    to different planes. The feed list is control plane: it answers which feeds
    exist for this caller, is provisioned per identity, changes whenever any of
    the Business's snapshots rolls, and is fetched on every poll. A manifest is
    data plane: it describes the bytes of one snapshot, is identical for every
    caller entitled to it, never changes once published, and is fetched once
    per snapshot. The two carry different cache semantics (private and
    short-lived; shared and immutable) and are often produced by different
    systems.

    Keeping them apart keeps the polled document small. An aggregated catalog
    of 100 million products materializes to roughly 3,000 files per snapshot at
    64 MB each, and a file entry with a URL and digest is about 150 bytes; a
    Business publishing 20 market feeds would otherwise serve about 9 MB of
    file metadata to every Platform on every poll, most of it unchanged. As
    separate documents, the feed list is a few kilobytes, and each manifest is
    fetched once and cached indefinitely at its URL.

    Separation also fixes the publishing order. The system that writes a
    snapshot's files writes its manifest beside them, so publication is files,
    then manifest, then a two-field update to the feed entry (`manifest`,
    `generated_at`); the feed endpoint never handles a file list, and the party
    operating the endpoint need not be the party producing the files. The
    fields that appear in both documents (`id`, `context`, `format`, and, for a
    supplemental feed, `extends`) are repeated deliberately so that each
    document stands on its own: a manifest URL is sufficient to fetch and
    verify a snapshot without the feed list.

`generated_at` is the logical point in time of the snapshot; every file in
the manifest is consistent as of that instant. `expires_at` is retention, not
validity: a snapshot does not become wrong at `expires_at`; it may become
unavailable. A Platform **MUST NOT** consume a manifest that lacks either.

The manifest for the first feed in the [Feed List](#feed-list) example is at
`https://merchant.example.com/feeds/us-en-usd/20260922T060000Z/manifest.json`.
A Platform fetches it with a plain HTTPS `GET`; it is not a UCP operation and
carries no UCP request headers:

<!-- ucp:example schema=common/feed op=list def=manifest -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.feed": [
        {"version": "{{ ucp_version }}"}
      ],
      "dev.ucp.shopping.catalog.feed": [
        {"version": "{{ ucp_version }}", "extends": "dev.ucp.common.feed"}
      ]
    }
  },
  "id": "us-en-usd",
  "format": "jsonl+gzip",
  "context": {
    "address_country": "US",
    "language": "en-US",
    "currency": "USD"
  },
  "generated_at": "2026-09-22T06:00:00Z",
  "expires_at": "2026-09-29T06:00:00Z",
  "files": [
    {
      "url": "https://merchant.example.com/feeds/us-en-usd/20260922T060000Z/part-00000.jsonl.gz",
      "digest": "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"
    },
    {
      "url": "part-00001.jsonl.gz",
      "digest": "sha-256=:d6wYF3+kJXsB1M2Hu1c0pV3xbFVQj4Kp0M4K0Zg2XqE=:"
    }
  ]
}
```

The second file's relative `url` resolves against the manifest URL
`https://merchant.example.com/feeds/us-en-usd/20260922T060000Z/manifest.json`
per [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986#section-5) to
`https://merchant.example.com/feeds/us-en-usd/20260922T060000Z/part-00001.jsonl.gz`;
files placed under the snapshot's path segment are as unguessable as it is.

The Business **MUST** set the manifest's `id` and `context` equal to those of
the feed list entry whose `manifest` URL served it. A Platform that finds a
mismatch in either **MUST NOT** consume the snapshot.

A snapshot is identified by (`id`, `generated_at`). The Business **MUST**
publish strictly increasing `generated_at` values within a feed. Once a
snapshot is published, the Business **MUST NOT** change the manifest document
or the files it references; a correction is a new snapshot with a later
`generated_at`.
`digest` lets a Platform verify file bytes against the manifest it holds; it
does not detect a Business that republishes a snapshot together with matching
replacement files, and it is not a signature. Authenticity of a manifest and
its files derives from the manifest URL having been obtained through the feed
list at the Business's declared `config.endpoint` (see
[Access and Provenance](#access-and-provenance)), not from `digest`.

`ucp` uses the same envelope shape as a UCP response. On a manifest it
declares the UCP version and the capabilities and extensions whose schemas the
records conform to; it does not record a negotiation, because a manifest is a
static document, not an operation response. The Business **MUST** declare
`dev.ucp.common.feed` in `ucp.capabilities`, together with every capability
and extension whose schemas the records conform to, and **MUST** include
`extends` on every extension entry, as in its profile. A Platform **MUST NOT**
consume a manifest that does not declare `dev.ucp.common.feed`; the manifest's
own shape is defined by that capability, so without the declaration there is
no version to validate the document against.

`extends` tells a Platform what kind of entry it is looking at:

* The entry that extends `dev.ucp.common.feed` is the feed's **record type**:
  it defines what a record is. A Platform that does not recognize the record
  type **MUST NOT** consume the snapshot.
* An entry that extends the record type adds fields to records. A Platform
  **MAY** ignore fields from one it does not recognize.

A Platform **MUST NOT** consume a snapshot that declares an extension entry it
cannot place in either group. A Platform validates records against the declared
schemas and handles records that do not conform as [Malformed
Records](#malformed-records); for a supplemental feed it validates the composed
record, since a supplemental record is partial by design.

`messages`, when present, carries errors, warnings, or informational notices
about the snapshot in the shape UCP responses use.

The extensions a snapshot can declare are bounded by the Business's profile: a
Platform reads the profile to learn which extensions the Business's feeds *may*
carry, and a manifest's `ucp.capabilities` to learn which ones a snapshot
*does* carry. The Business **MUST NOT** declare in a manifest a capability or
extension that its profile does not advertise; a Platform that finds one
**MUST NOT** consume the snapshot.

An extension that changes the file layout **MUST** register its own `format`
value, so that `format` remains the single compatibility signal. A Platform
that recognizes every declared extension but not the `format` **MUST NOT**
consume the snapshot, and a Platform that recognizes the record type and the
`format` **MAY** consume the snapshot regardless of unrecognized field-adding
extensions.

{{ extension_schema_fields('feed.json#/$defs/manifest', 'common/feed') }}

### File

One file in a snapshot, encoded per the manifest's `format`. `files` is a
flat list; a single file is a one-element list.

`url` is an absolute HTTPS URL or a reference that a Platform resolves
relative to the manifest's URL per
[RFC 3986](https://www.rfc-editor.org/rfc/rfc3986#section-5). Any origin is
permitted. The Business **MUST** publish every file over HTTPS; a Platform
**MUST NOT** dereference a file URL that resolves to a non-HTTPS URL and
**MUST** treat that snapshot as incomplete.

`digest` is an [RFC 9530](https://www.rfc-editor.org/rfc/rfc9530)
`Content-Digest` dictionary value over the file's bytes as served, for
example `sha-256=:BASE64:`, the same syntax UCP uses for `Content-Digest` in
signing. The Business **SHOULD** include `digest` on every file, unless the
serving path re-encodes the bytes in transit so that a digest of the bytes as
served cannot be computed in advance. A Platform that verifies `digest` and
finds a mismatch **MUST** treat the snapshot as incomplete. `digest` is an
integrity check over the bytes as served, not an authenticity check;
authenticity derives from how the manifest URL was obtained (see
[Access and Provenance](#access-and-provenance)).

{{ extension_schema_fields('feed.json#/$defs/file', 'common/feed') }}

## Contextual Feeds

A feed is resolved for one `context`: the conditions under which every record
in it was resolved, each member single-valued. The record type states which
members its feeds use and what each means. A Business that materializes more
than one `context` publishes separate feeds, one per `context`, or one per
`context` and `format` where it offers more than one encoding.

A Platform serves a feed's records only under conditions that match the feed's
`context`. A Platform **MUST NOT** consume a feed whose `context` carries a
member it does not honor when serving, because it cannot reproduce the
conditions under which the records were resolved.

The Business **MAY** publish a record with the same identifier in more than one
feed. Each feed is authoritative for its own context, and no cross-feed merge
is defined. A Platform **MUST NOT** infer removal of a record from its absence
in a different feed.

The Business **MAY** reference the same files from two feed entries when their
resolved content is identical. Each entry still has its own manifest, because
a manifest carries one `context` and one `id`, each equal to its entry's.

## Snapshot Semantics

### Snapshot and Removal

A manifest is a complete materialization of the feed for its `context` as of
`generated_at`. A Platform that applies a snapshot **MUST** replace its prior
copy of that feed with it. A Platform **MUST NOT** apply a snapshot whose
`generated_at` is earlier than that of the snapshot it holds for the same feed.
Absence of a record from the latest complete snapshot means the record is not
offered in this feed's `context`. Absence carries no reason: unpublished, sold
out, filtered, and deleted are indistinguishable. Absence in one feed says
nothing about other feeds.

### Consistency and Immutability

The Business **MUST** make all files in a manifest mutually consistent as of
`generated_at`, and **MUST** publish every file before publishing the
manifest that references it. The Business **MUST NOT** modify the manifest
document or the files a snapshot references after publication at a given
(`id`, `generated_at`); a correction is a new snapshot with a later
`generated_at`.

### Partial Fetch

A Platform that cannot retrieve every file in a manifest, or that verifies a
`digest` and finds a mismatch, **MUST NOT** treat the snapshot as complete and
**MUST NOT** apply removal semantics from it. The Platform keeps its prior
copy of the feed until it applies a complete snapshot.

### Malformed Records

A Platform **SHOULD** skip an individual malformed record and continue
processing the file, unless the number or proportion of malformed records
exceeds a threshold the Platform chooses, in which case it **MAY** reject the
snapshot. This document specifies no threshold.

### Etiquette

`interval` is advisory. A Platform **SHOULD** poll the feed endpoint
no more often than the shortest `interval` among the feeds it consumes, unless
the Business has agreed to a higher rate. A Platform **SHOULD** use
conditional requests when fetching the feed list and manifests, unless the
Business's responses carry no validators (for example, no `ETag` or
`Last-Modified`). When to fetch a manifest at all is governed by the entry's
`generated_at` (see [Feed](#feed)).

The Business **MAY** apply standard HTTP rate limiting to the feed endpoint,
manifests, and files, for example `429 Too Many Requests` or `503 Service
Unavailable` with `Retry-After`. A Platform that receives `Retry-After`
**MUST** wait at least the indicated time before retrying that resource.

### Retention

The Business **SHOULD** keep a manifest and its files retrievable until
`expires_at`, unless it is required to withdraw content it is no
longer permitted to distribute. A Platform that finds a manifest or file no
longer retrievable **SHOULD** re-read the feed list and fetch the current
snapshot rather than retry the missing URL, unless the Business signals a
transient failure (for example, HTTP 503 with `Retry-After`).

## Formats

`format` is an open string vocabulary naming the wire encoding of every file
in a manifest. Compression is part of the token, not a separate field. This
version registers two values:

| `format` | Encoding |
| :--- | :--- |
| `jsonl+gzip` | One JSON record per line, gzip-compressed. |
| `parquet` | One record per row across one or more files, with nested structures as nested columns per the record schema. Compression is internal to Parquet and not part of the token. |

The Business **MUST** use a registered value for `format`. A Platform **MUST**
support every value registered in the version of this capability it
advertises (in this version, both `jsonl+gzip` and `parquet`), so that any
conforming feed is consumable. A Platform that does not recognize a manifest's
`format` **MUST NOT** consume that snapshot.

The support obligation sits with Platforms because a Platform is one
implementation while Businesses are many; it also lets a Business materialize
each feed in a single format.

## Access and Provenance

The Business advertises the capability in its profile under `capabilities`,
with `config.endpoint` naming the feed endpoint (see [Discovery](#discovery)).
The profile carries exactly one feed URL, the entry point in
`config.endpoint`; it carries no manifest or file URLs. The Business **MUST
NOT** rely on the profile to convey any manifest or file URL; a Platform
**MUST NOT** dereference as a feed URL any URL it did not obtain from the feed
list at `config.endpoint` or from a manifest reached through it.

Manifest and file URLs are trusted because the feed list the Business declared
in its profile returned them, not because of their hostname; the Business
**MAY** host them on any HTTPS origin. The
[fetch-safety requirements](../../overview/index.md#fetching) in the Overview
apply when a Platform dereferences them.

The Business **MAY** serve the feed endpoint publicly, or **MAY** require
Platform authentication using any mechanism UCP already defines for requests
to the Business. The operator of `config.endpoint` **MUST** apply the same
request conventions and authentication mechanisms as the Business's service
endpoint would; a Platform treats a feed endpoint that does not as
unavailable. The feed list is provisioned for the caller; a Business offers
different feeds to different Platforms through this provisioning, not through
separate profile entries. The feed endpoint is the only place feed access
control runs: file URLs are not access control. For a feed the Business
returns only to authenticated callers, the Business **MUST** make each
snapshot's manifest URL unguessable, for example by using a UUID or a random
token of equivalent entropy as the per-snapshot path segment, and **MUST**
place file URLs under that segment or make them unguessable likewise, so that
neither can be derived from the feed's `id`, from `generated_at`, or from
other public information. For a public feed any unique per-snapshot segment,
such as a timestamp, suffices. Whether the host additionally authenticates
manifest and file requests (short-lived or scoped URLs, CDN credentials)
remains the Business's data-plane choice and is out of scope.

### Scopes

Feed access is Platform-level. No user-authenticated scope is defined for this
capability; Buyer-level authentication is out of scope.

## Extensibility and Supplemental Feeds

### Extensions

Record shape extends as operation responses do: an extension declared in the
manifest's `ucp.capabilities` adds typed fields to records, exactly as it does
for the responses of the capability that defines them.

An extension that changes the file layout **MUST** register a distinct
`format` value for it (see [Formats](#formats)); an extension **MAY** define
additional manifest fields, composing onto the manifest. Feed list entries
are shared by every feed in the list and take no extension fields. An
extension **MUST NOT** redefine the fields in this document.

### Supplemental Feeds

A feed entry with `extends` is a supplemental feed. `extends` names, by `id`,
another entry in the same feed list: its base feed. A supplemental record is a
partial record of the base feed's record type, optionally carrying fields of
the extensions its manifest declares. Its manifest declares the base feed's
record type and those extensions; the rules in [Manifest](#manifest) apply to
it as to any other manifest.

Records join on `id`. A record type that supports supplemental feeds **MUST**
give each record an `id`: a Business-assigned identifier, opaque to Platforms,
stable across snapshots, unique among the records of a feed, and the same
identifier the Business's operations for that record type accept. It **MUST**
declare which of its lists are identified and give each element of an
identified list an `id` with the same properties, unique within the list. A
Platform applies a supplemental record to the base record with the same `id`
and, inside an identified list, each supplemental element to the base element
with the same `id`; each matches at most one. Lists the record type does not
declare identified are replaced whole.

`id` is the Business's, whoever publishes the feed. A party that publishes a
supplemental feed for the Business **MUST** use the Business's identifiers in
`id`; identifiers of its own **MAY** travel as fields the extension defines and
**MUST NOT** replace `id`. A supplemental record whose `id` matches nothing in
the base is ignored, so a supplement keyed by any other identifier joins
nothing.

A supplemental record carries only the members it changes. Each member it
carries replaces the base record's member of the same name, whole, or adds it
where the base has none: a supplement that carries `price` carries the complete
price, `amount` and `currency`. A member set to `null` removes the base member.
One kind of member works differently: an *identified list*, such as a Product's
`variants`. An identified list is not replaced. Each element in the supplement
is applied to the base element with the same `id` by these same rules; base
elements the supplement does not mention stay as they are, and supplemental
elements that match nothing are ignored. Because members are replaced whole, an
incomplete member, such as a `price` without `currency`, produces a composed
record that fails validation and is handled as [Malformed
Records](#malformed-records), rather than one that silently keeps the base
currency.

!!! note "Design note"
    Supplemental feeds override as well as add because the product feeds
    Platforms consume today work that way: a supplemental feed replaces
    attributes of the record with the same identifier, and a regional feed
    replaces price and availability per region. A supplement applies at the
    record level rather than at a path within it, because a path that selects
    the join level reaches one level per feed: a supplement that changes
    variant prices could not also correct the Product's `price_range`. A list
    keyed by identifier merges element by element rather than being replaced,
    because a record-level replacement of `variants` could not change one
    variant without restating them all.

    Members replace whole rather than merging member by member so that the
    schema catches a partial member: a `price` without `currency` fails
    validation instead of inheriting the base currency. The keyed-list rule is
    the extension Kubernetes made to JSON Merge Patch for the same reason in
    its strategic merge patch (`patchStrategy: merge` with a `patchMergeKey`,
    today `listType: map` with `listMapKeys`), so that lists of containers or
    ports merge by `name`; it is also the shape of a database upsert keyed by
    primary key, applied to a nested record. One supplemental record can
    therefore correct a Product and the variants inside it in one step, and the
    Business, not the Platform, is responsible for the composed record being
    coherent. Joining on `id` is also why no join key is declared: `id` is the
    one member every record type guarantees present and unique. A publisher
    that carries a stable identifier of its own on the base, such as a feed
    manager's, could be allowed to name it as the join key in a later version,
    as an optional member defaulting to `id`.

An entry's `context` is the context of the feed a Platform obtains from it:
for a standalone entry, its records; for a supplemental entry, the base feed
with the supplement applied. A supplemental feed's `context` therefore need
not equal its base's. The Business **MUST** make the composed result correct
for that `context`: the supplement carries every member whose base value is
not valid there, including any member whose value depends on members it
changes.

* When more than one supplemental feed extends the same base, a Platform
  applies them in feed-list order; where two set the same member, the later
  feed's value stands.
* A base feed stands alone. The Business **MUST NOT** name as a base an entry
  that itself carries `extends`; a Platform **MUST NOT** consume a
  supplemental feed whose `extends` names no entry in the feed list or names
  one that itself carries `extends`.
* `extends` appears on the feed entry and on the manifest. The Business
  **MUST** keep the two equal; a Platform that finds a mismatch **MUST NOT**
  consume the snapshot.
* The Business **MUST NOT** publish a supplemental record that matches no
  record in the base feed; a Platform **MUST** ignore a supplemental record it
  cannot match in its copy of the base.
* Absence of a base record from a supplemental feed means the base record
  stands as it is; a supplemental feed never removes a base record. A
  supplemental feed cannot withhold a base record from its `context`; a
  Business that offers a different set of records in a market publishes a
  standalone feed for it.
* Base and supplemental feeds publish snapshots independently; no cross-feed
  atomicity is defined.
* A Business that wants the same supplement over two base feeds publishes two
  supplemental entries, which **MAY** reference the same files.
* A Platform validates the composed record, not the supplemental record on its
  own (see [Manifest](#manifest)).

[Shopping Catalog Feed](../../shopping/catalog/feed.md#supplemental-feeds)
shows two worked examples: per-market prices applied to the Variants inside a
base feed's Products, and Platform-specific fields added to its Products.

## Future Work

Reserved by name for future versions, and defined nowhere in this document:

* Incremental (delta) snapshots, including any finer-grained file layout
  needed to make them efficient.
* Push notification of new snapshots.
