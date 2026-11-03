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
The revised implementation has now been executed in the author's GitHub
Actions CI. The following results were verified from completed job steps:

- [Focused suite](https://github.com/arjun2075/ucp/actions/runs/41685254592)
  on commit 8959be8: **52/52** pinned schema vectors, **600+600/1,200**
  generated probes, **15/15** reference consumer unit tests; Ruff lint
  and formatter, Python compileall and full-branch whitespace diff passed.
- [Official tooling](https://github.com/arjun2075/ucp/actions/runs/41686106843)
  on commit 735f287: official `ucp-schema` **v1.4.1** lint passed,
  changed Catalog specification examples **9 passed, 0 failed, 0 errors,
  0 skipped**, `uv sync --frozen` and strict MkDocs draft build passed.
- Both suites exercise authored code and synthetic fixtures. They are NOT
  an independent seller/platform interoperability run, UCP TC approval,
  actual privacy-side-channel guarantee, or production adoption.

Generated SDK conditional enforcement, full multi-version specification
build, pre-commit hooks, and production entitlement/cache behavior remain
**unverified** in this revision.

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

Executed scope: 52 fixture vectors, 600 baseline-subset compatibility
probes, 600 mode probes, 15 consumer tests. Official UCP CLI lint,
changed docs examples and strict draft MkDocs PASS. Generated SDK,
full multi-version docs, privacy side-channel review, real capability
negotiation, independent Platform integration, and full mixed-variant
and expired-entitlement seller-to-platform runs remain unresolved.
