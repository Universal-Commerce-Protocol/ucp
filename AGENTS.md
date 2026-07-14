---
name: "UCP Contributor Playbook"
description: "Instructions for AI coding agents to contribute to the Universal Commerce Protocol ecosystem."
---

# UCP AI Contributor Playbook

You are the principal architect for this repository: the Universal Commerce Protocol (UCP) specification and ecosystem documentation. Your job is to ensure the protocol we ship is secure, standards-compliant, and easy for merchants, agents, and payment platforms to implement correctly.

This file is the operating contract for AI agents working in this repository.

---

## 1. Context Initialization & Resource Fetching

**When to fetch:** Only fetch external resources when you need to understand specific protocol details, integration patterns, or schema conventions. Do not fetch for every task. Use local `README.md` and inline documentation first.

The following resources are available to support code generation, architectural questions, and change proposals:

* **Local Context:** Read the local `README.md` for immediate repository scope and setup commands.
* **Protocol Architecture:** Fetch `https://ucp.dev/llms.txt` for comprehensive UCP documentation including architecture, core concepts, AP2 integration patterns, schema authoring guidelines, and versioning policies.
* **Contribution Rules:** Fetch `https://raw.githubusercontent.com/Universal-Commerce-Protocol/.github/main/CONTRIBUTING.md` for overarching organizational contribution guidelines.

---

## 2. Core Operational Guidelines

Adhere strictly to the following parameters when editing the repository:

* **Schemas:** Edit JSON schemas only in the `source/` directory. Maintain all `ucp_*` annotations.
* **Commits:** Use Conventional Commits (e.g., `feat: add gateway`, `docs: update guide`). Use a `!` for breaking changes (e.g., `feat!: remove buyer field`).
* **Quality Guardrails:** Never bypass, comment out, or disable linter rules, pre-commit hooks, or test assertions.
* **Significant Changes:** Core schema edits, new endpoints, or breaking changes require an approved Enhancement Proposal from the Tech Council. See [CONTRIBUTING.md](https://raw.githubusercontent.com/Universal-Commerce-Protocol/.github/main/CONTRIBUTING.md#significant-changes) for details.
* **Documentation:** Sync any MkDocs navigation additions (`mkdocs.yml`) with the `llmstxt` plugin section to ensure that content is discoverable and legible by agents.

---

## 3. Terminal Commands Reference

Validate your changes locally using these commands before considering a task complete.

### Code Quality & Schemas

**Installing ucp-schema:** If `ucp-schema` is not available in your environment, install it using Cargo:

* From crates.io: `cargo install ucp-schema`
* From git: `cargo install --git https://github.com/universal-commerce-protocol/ucp-schema`

Then validate your changes with:

* **Lint Schemas:** `ucp-schema lint source/` (after schema changes)
* **Regenerate SDK Models:** `bash sdk/python/generate_models.sh` (after schema changes)
* **Run Pre-commit Checks:** `pre-commit run --all-files` (after all changes)
* **Execute Local Super-Linter:** `./scripts/super_linter_local.py` (requires docker or podman)

### Documentation (MkDocs)

These commands should be run from the ucp root directory.

#### Build and serve full site

* **Build Full Multi-Version Site**: `./scripts/build_local.sh`. The resulting build will be placed in the local_preview/ directory. Add `[--draft-only]` to avoid building every version of the specification.
* **Serve the site locally after build**: `python3 -m http.server 8000 -d local_preview/`
* **Check Broken Links after build:** `uv run ./scripts/check_links.py local_preview/`

#### Optional: build and serve specification by version(s)

* **Deploy a Version (Mike):** `mike deploy [version] [alias]` (e.g., `mike deploy 2026-04-08 latest`)
* **Serve Versioned Site Locally (Mike):** `mike serve`

#### Optional: build and serve site overview (without specification)

* **Sync Dependencies:** `uv sync`
* **Run Live Dev Server Without Specification (strict mode):** `uv run mkdocs serve [--strict]`
