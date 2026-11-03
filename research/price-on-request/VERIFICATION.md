# Verification for the October 16 pricing-state review

Upstream base: `3ab41043b79373df33a6e2c377bc82a806175f78`.
Historical prototype: `565e7c3046f25e588f1f26871dc3a88811145b3a`.
Results below are local self-validation, not independent review or UCP adoption.

## Executed checks

- `python harness/run.py --baseline BASELINE --proposed ROOT --fuzz 300`:
  44 fixture vectors pass; 300 variant + 300 product priced-subset probes pass;
  300 variant + 300 mixed-product mode probes pass; no mismatches.
- `python -m unittest discover -s research/price-on-request/harness
  -p 'test_*.py' -v`: 10 tests pass.
- JSON Schema draft 2020-12 meta-validation runs over both local schema trees
  before fixture validation. Offline registry avoids remote schema drift.
- `ruff check research/price-on-request/harness/*.py`: passes.
- `ruff format --check research/price-on-request/harness/*.py`: passes.
- `git diff --check HEAD`: passes.
- `uv sync --frozen`: passes using the existing lockfile; no dependency changes.
- `uv run mkdocs build --strict`: passes. This command alone does not prove
  full multi-version specification rendering or example validation.

The first inherited harness run exposed nested-reference scope drift with
deprecated RefResolver on jsonschema 4.26.0. The current runner uses the
referencing registry and all local schemas; the successful results above were
rerun after that correction. Requirements pin the versions actually used.

## Blocked or unexecuted checks

- `ucp-schema lint source/`: blocked, executable absent (exit 127). Cargo is
  unavailable in this environment; the official v1.4.1 release has no binary
  assets. JSON Schema meta-validation is not a substitute for its UCP lint.
- `uv run python scripts/validate_examples.py --schema-base source/schemas/`:
  blocked with explicit ucp-schema-not-found message (exit 1).
- `pre-commit run --all-files`: initialization failed before hooks could run.
  npm rejected cspell-cli's local git package with EALLOWGIT. No hook or
  assertion was disabled. Ruff and whitespace checks were executed separately.
- `scripts/build_local.sh --draft-only`: not run; requires ucp-schema/Cargo.
- Generated Python/JavaScript SDKs were not regenerated or tested. The
  historical AGENTS.md command `sdk/python/generate_models.sh` does not exist
  at the reviewed root; external SDK generation remains an explicit gate.
- Docker/Podman super-linter: not run, neither runtime is available.
- No production buyer authentication, network cache, quotation service or
  Purchase Options integration was exercised. Consumer-map tests cover only
  their documented in-memory behavior.

The PR remains an experimental draft. Complete UCP lint, full documentation
examples/rendering, generated-SDK conditional enforcement, migration and
independent interoperability before any claim of upstream readiness.

## 2026-11-03 AirShelf review revision (separate from historical results)

The historical successful 44-vector / 1,200-probe / 10-consumer-test
results above apply to head 5ed98c9; AirShelf independently reported
reproducing that original harness on its saved two-seller data
([comment](https://github.com/Universal-Commerce-Protocol/ucp/issues/969#issuecomment-6599693166)).
This branch introduces NEW implementation and tests and **has not yet
executed the Python/jsonschema, official UCP CLI, pre-commit or generated SDK
suites**. Do not report 52/52 or 15/15 as passing until verified.

Changed artifacts: experimental `undisclosed` mode (including schema
rejections for price/list_price/reason/next_step), revised NDA semantics,
legacy-consumer guard requiring external buyer entitlement and pricing
profile support, eight synthetic schema fixtures and five consumer tests,
and updated spec/search documentation.

Local checks to execute with a pinned old-main checkout:

```sh
python -m pip install -r research/price-on-request/harness/requirements.txt
python research/price-on-request/harness/run.py \\
  --baseline ../ucp-pricing-baseline --proposed . --fuzz 300
python -m unittest discover -s research/price-on-request/harness -p 'test_*.py' -v
ruff check research/price-on-request/harness/*.py
ruff format --check research/price-on-request/harness/*.py
git diff --check 5ed98c923645f0700e24c6ad0117692b97627f67..HEAD
```

Expected scope after changes: 52 fixture vectors, 600 baseline-subset
compatibility probes, 600 mode probes, 15 consumer tests. These are targets,
not asserted outcomes. Official UCP CLI, generated SDK, multi-version docs,
privacy side-channel review, real capability negotiation, independent Platform
integration, mixed-variant and expired-entitlement runs remain unresolved.
