# Pricing-state checks

See the parent README for exact reproduction commands, source pins and limits.
Requirements are pinned in requirements.txt. The fixture matrix includes
expected verdicts for both current upstream and the experimental schema.
All JSON Schema references resolve offline from the respective source trees.

The Python consumer map is an isolated reference, not a production cache or
buyer authentication system. Its historical ten tests exercised actual helper behavior; the AirShelf
review revision adds five more tests requiring BOTH independently determined
buyer authorization and negotiated pricing-profile support before the
reference consumer returns restricted prices. There are now 52 schema vectors
and 15 consumer tests to execute. Neither the consumer nor these added tests
implement authentication, transport negotiation, HTTP caching or SDK
conformance. New test execution is unverified in this branch.
