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
