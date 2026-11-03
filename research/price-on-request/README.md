# Experimental catalog pricing-state implementation

This is a research implementation supporting UCP issue #877. It is not
approved UCP behavior and must not be merged into upstream core before the
required TC decision. No standard capability identifier is allocated here.

evoleinik supplied the original use case and deployment observations;
juanferrub proposed the pricing-state object. Arjun Garg implemented the
schema prototype, compatibility analysis and tests. No coauthorship or
endorsement is implied.

## Baselines

- Current upstream base: `3ab41043b79373df33a6e2c377bc82a806175f78`.
- Historical prototype: `565e7c3046f25e588f1f26871dc3a88811145b3a`.
- This increment ports the eight schema/documentation changes to current main,
  repairs the harness's nested-reference resolution using an offline registry,
  adds unknown-mode range omission coverage, and supplies consumer helpers.

## Behavior

| Mode | Selling price | Anonymous disclosure |
| --- | --- | --- |
| Absent or public | Required | Ordinary public price |
| buyer_specific | Optional; retained if resolved for entitled caller | Only use without price if price-list membership may be disclosed |
| quote_required | Forbidden | Reveals that quoting is required; use only if this is public |
| contract_only | Forbidden | Commercial pricing contract required; NOT a synonym for disclosure-only NDA |
| undisclosed (review revision) | Forbidden | Does not reveal price-list membership, quote route, or expected outcome of identity linking |
| Unknown string | Structurally optional; unaware client must suppress price | Treat conservatively |

Missing price never means zero. Reference list prices are not selling prices.
Quote hints may coexist with a usable price. Price ranges and cache entries
retain the response's caller and authorization context.

The core schema cannot be relaxed by an ordinary allOf extension: its required
price constraint still applies. This explains the core EP request rather than
claiming vendor namespace support or ecosystem adoption that does not exist.

Purchase Options #901 was folded into the open #890 branch, not adopted on
main. This patch does not modify that branch's option schemas. The pricing
state must eventually qualify each price at its own granularity; mixed
public-buy/quote-only-lease options remain an explicit composition dependency.

## Reproduce

From the repository root, with a separate checkout of the upstream base:

```sh
python -m pip install -r research/price-on-request/harness/requirements.txt
python research/price-on-request/harness/run.py \
  --baseline ../ucp-pricing-baseline --proposed . --fuzz 300
python -m unittest discover -s research/price-on-request/harness -p 'test_*.py' -v
```

The original Oct 16 harness executed 44 schema vectors, 600 priced probes,
600 mode probes and 10 consumer tests (historical results). This review branch
adds eight synthetic AirShelf-inspired vectors (52 total), adds undisclosed to
the mode-probe pool, and adds five consumer authorization/neutrality tests
(15 total). The complete revision tests have been executed on GitHub Actions
against pinned upstream main, with **52/52 schema vectors, 1,200/1,200 seeded
probes, and 15/15 consumer tests passing**, plus Ruff and syntax/whitespace
checks. See [focused CI](https://github.com/arjun2075/ucp/actions/runs/41685254592).
These finite subsets do not prove interoperability.

`consumer.py` accepts schema-validated inputs. Its cache is a reference map,
not buyer authentication or an HTTP cache: callers must derive the correct
opaque context and enforce expiry, entitlement revalidation and freshness.
It does not demonstrate production cache security. Currency conversion and
cross-unit comparison are unsupported. Schema validation is not generated-SDK
validation or end-to-end Cart/Checkout interoperability.

## Compatibility and publication

Old validating consumers reject unpriced payloads. An old lenient consumer
may incorrectly show a missing amount as zero. Worse, older consumers can
accept a numeric buyer_specific price (and its derived product price_range),
ignore the unknown pricing marker, and treat it as public. Sending restricted
prices therefore requires BOTH authenticated buyer entitlement and explicit
pricing-profile support. No interoperable negotiation signal is approved by
this draft. The reference consumer now defaults to refusing buyer_specific
amounts unless both booleans are supplied by the caller; these booleans are
not an authentication implementation. Reserving the previously-open
pricing property also invalidates some formerly accepted payloads: malformed
pricing objects and a selling price alongside a newly unpriced known mode.
Release/version negotiation and the field-name collision survey require TC
review. Do not describe this as purely additive or select a release version.

The October 16 implementation is fork draft PR #1; the AirShelf follow-up is
a separate review branch, not a change to the existing PR. The revised
branch passed official `ucp-schema` v1.4.1 lint, changed Catalog example
validation (9/9) and strict MkDocs build
([official CI](https://github.com/arjun2075/ucp/actions/runs/41686106843)).
The upstream schema decision, generated SDK conditional enforcement,
buyer/client capability negotiation, independent Platform interoperability,
privacy side-channel review and Purchase Options composition remain open.

## November 3, 2026 review response (AirShelf #969)

AirShelf independently reports reproducing the original 44/1,200/10 harness
checks and mapping 12 saved Product records from seven products across two
B2B seller integrations. Those results are externally **reported**, not
reproduced by this branch. The redacted saved seller responses are not in
this repository, and no independent Platform or paid buyer exercised #969.
See [AirShelf's comment](https://github.com/Universal-Commerce-Protocol/ucp/issues/969#issuecomment-6599693166).

This review branch addresses three bounded findings:

1. A neutral anonymous `undisclosed` mode hides price-list membership and
   prohibits price, reference price, reason and next-step fields on that
   variant. Other response-side side channels still require Business review.
2. A disclosure-only NDA with a common restricted price list is
   `buyer_specific` after entitlement; `contract_only` means a *commercial*
   pricing contract, not merely an NDA. Schema alone cannot infer this.
3. Legacy client safety applies to **priced** buyer_specific records, not
   only records with missing prices. The consumer reference fails closed
   unless entitlement and profile support were established independently.

Pending: generated SDK enforcement, the exact negotiated client-version
signal, an independent Platform, actual mixed-variant and expired-entitlement
seller-to-platform integration, privacy side-channel review, and an agreed
anonymous price-filter policy. The synthetic mixed-variant regression is
passing but is not an independent cross-implementation test. This is
experimental review text, not a UCP council disposition.
