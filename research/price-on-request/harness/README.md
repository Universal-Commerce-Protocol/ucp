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
