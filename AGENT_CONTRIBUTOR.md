---
name: "UCP Agent Contributor Guidelines"
description: "Instructions for AI coding agents contributing to the UCP specification and documentation repository."
---

# UCP Agent Contributor Guidelines

You are an AI agent contributing directly to this repository (`Universal-Commerce-Protocol/ucp`). Your job is to ensure the protocol we ship is secure, standards-compliant, and easy for businesses, agents, and payment platforms to implement correctly.

## 1. Core Operational Rules

Adhere strictly to the following parameters when editing the repository:

* **Schema Source of Truth:** Edit JSON schemas only inside the `source/` directory (see `docs/documentation/schema-authoring.md`). Always preserve `ucp_*` annotations.
* **PR Titles & Commit Messages:** Follow Conventional Commits (e.g., `feat: add transaction extension`, `docs: update guide`). Use `!` for breaking changes (e.g., `feat!: update profile schema`).
* **Documentation Navigation:** Sync any MkDocs navigation additions (`mkdocs.yml` `nav`) with `plugins.llmstxt.sections` so new pages remain discoverable via `llms.txt`.
* **JSON Examples:** Annotate every fenced `json` code block in `docs/**/*.md` with `<!-- ucp:example schema=... -->` or `<!-- ucp:example skip reason="..." -->`.
* **Quality Guardrails:** Never bypass or comment out linter rules, pre-commit hooks, or test assertions.
* **Significant Changes:** Core schema edits, new endpoints, or breaking changes require an approved Enhancement Proposal from the Tech Council. See [CONTRIBUTING.md](https://github.com/Universal-Commerce-Protocol/.github/blob/main/CONTRIBUTING.md#significant-changes) and `docs/documentation/contributing.md`.

## 2. Local Command Reference

Validate your changes locally using these commands before considering a task complete.

### Prerequisites

* **Install `ucp-schema`:** `cargo install ucp-schema` (from crates.io) or `cargo install --git https://github.com/Universal-Commerce-Protocol/ucp-schema`
* **Sync Python Dependencies:** `uv sync`

### Schema Validation & Resolution

* **Lint Schemas:** `ucp-schema lint source/` (checks syntax, broken references, and annotation structures).
* **Resolve Annotations:** `ucp-schema resolve source/schemas/<domain>/<schema_name>.json --op <operation> (--request|--response) [--bundle] --pretty` (compiles a schema for a specific direction/operation, resolving `ucp_*` annotations; add `--bundle` to inline referenced child schemas).
* **Validate Payloads:** `ucp-schema validate --schema source/schemas/<domain>/<schema_name>.json --op <operation> [--request|--response] <path_to_payload.json>` (validates a sample payload against a schema).
* **Run Pre-Commit Checks:** `pre-commit run --all-files`

### Documentation (MkDocs)

These commands should be run from the ucp root directory.

#### Build and serve full site

* **Build Full Preview (All Versions):** `./scripts/build_local.sh`
* **Build Draft Preview (Faster, local only):** `./scripts/build_local.sh --draft-only`
* **Serve Local Preview:** `python3 -m http.server 8000 -d local_preview/`
* **Check Broken Links:** `uv run ./scripts/check_links.py local_preview/`

#### Optional: live dev server & strict check

* **Live Dev Server (Quick Edits):** `uv run mkdocs serve`
* **Strict Build Check:** `uv run mkdocs build --strict`
