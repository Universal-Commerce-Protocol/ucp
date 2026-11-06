# Pricing-state checks

See the parent README for exact reproduction commands, source pins and limits.
Requirements are pinned in requirements.txt. The fixture matrix includes
expected verdicts for both current upstream and the experimental schema.
All JSON Schema references resolve offline from the respective source trees.

The Python consumer map is an isolated reference, not a production cache or
buyer authentication system. The October 16 implementation included ten consumer tests. The review
revision added five more tests requiring independently determined buyer
authorization AND negotiated pricing-profile support. All 52 schema vectors,
1,200 seeded probes and 15 consumer tests passed on
[GitHub Actions](https://github.com/arjun2075/ucp/actions/runs/41685254592).
Official CLI lint, changed Catalog examples and strict MkDocs also passed
([verification run](https://github.com/arjun2075/ucp/actions/runs/41686106843)).
Neither the consumer nor the tests implement authentication, transport
negotiation, HTTP cache safety or generated SDK enforcement.

## Mixed public/free and unresolved review

AirShelf's November 4 correction prompted eight additional synthetic Product
fixtures and five consumer tests; executed totals are 60/60 schema vectors,
1,200/1,200 seeded probes and 20/20 consumer tests
([focused run](https://github.com/arjun2075/ucp/actions/runs/41857846611)).
Official CLI lint, Catalog examples and strict MkDocs also passed
([official-tooling run](https://github.com/arjun2075/ucp/actions/runs/41857846707)). These cases distinguish a real
public zero from an unpriced/undisclosed variant, exercise a partial range
of 0-0 and optional omitted range, and prevent a restricted priced variant
from entering a legacy consumer's aggregate. The intentionally inaccurate
range fixture can remain structurally schema-valid: the consumer recomputes
and does not trust that aggregate. The fixtures are not AirShelf's live data.
A generic sign-in affordance is a behavioral privacy review item; JSON
Schema alone cannot validate its non-disclosure across catalog messages.

## External mixed-plan follow-up (November 4)

AirShelf reported a redacted four-variant product: a public free plan (zero),
two public monthly priced plans, and an Enterprise quote-only plan. The saved
seller pricing-page capture was dated October 3 and the original page now
redirects. The synthetic fixture `fixtures/airshelf_mixed_four_plan_redacted.json`
preserves *shape only*, not verified current seller prices.

The additional reference-consumer regression checks that a 0–0 filter selects
only Free, that Enterprise never participates in numeric filtering, that the
visible range is 0–30000 synthetic minor units, and that recomputation detects
an inaccurate supplied aggregate. The deliberately mode-less, zero-priced
Enterprise mutation demonstrates a legacy semantic ambiguity: a consumer
cannot infer quote intent when a producer omits the pricing marker.

**Important limits:** JSON Schema does not enforce cross-variant numeric
range consistency. Consumer-side recomputation is a mitigation, not a schema
validation guarantee. Price-filtered search results can omit quote-only plans
entirely; absence from results does not prove that no quote-only plan exists.
The wire-level signaling for hidden or unfilterable plans and capability
negotiation remain Shopping TC architectural decisions. No independent
platform interoperability or current commercial price validation is claimed.
