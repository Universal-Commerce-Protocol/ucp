---
name: "UCP Contributor Playbook"
description: "Instructions for AI coding agents to contribute to the Universal Commerce Protocol ecosystem."
---

# UCP AI Contributor Playbook

This document provides the core instructions for AI agents operating within the Universal Commerce Protocol (UCP) repository.

---

## 1. Context Initialization

Before generating code, answering architectural questions, or proposing changes, establish your context using your available tools:

* **Required Local Context:** Read the local `README.md` for immediate repository scope and setup commands.
* **Optional Protocol Architecture:** Fetch `https://ucp.dev/llms.txt` *only if needed* to understand comprehensive schema designs and endpoints.
* **Optional Contribution Rules:** Fetch `https://raw.githubusercontent.com/Universal-Commerce-Protocol/.github/main/CONTRIBUTING.md` *only if needed* for overarching organizational guidelines.

---

## 2. Core Operational Guidelines

Adhere strictly to the following parameters when editing the repository:

* **Schemas:** Edit JSON schemas only in the `source/` directory. Maintain all `ucp_*` annotations.
* **Commits:** Use Conventional Commits (e.g., `feat: add gateway`, `docs: update guide`). Use a `!` for breaking changes (e.g., `feat!: remove buyer field`).
* **Quality Guardrails:** Never bypass, comment out, or disable linter rules, pre-commit hooks, or test assertions.
* **Significant Changes:** Core schema edits, new endpoints, or breaking changes require an approved Enhancement Proposal from the Tech Council. See [CONTRIBUTING.md](https://raw.githubusercontent.com/Universal-Commerce-Protocol/.github/main/CONTRIBUTING.md#significant-changes) for details.
* **Documentation:** Sync any MkDocs navigation additions (`mkdocs.yml`) with the `llmstxt` plugin section.

---

## 3. Terminal Commands Reference

Always validate your changes locally using these exact commands before considering a task complete.

### Code Quality & Schemas

* **Lint Schemas:** `ucp-schema lint source/`
* **Regenerate SDK Models:** `bash sdk/python/generate_models.sh` (after schema changes)
* **Run Pre-commit Checks:** `pre-commit run --all-files`
* **Execute Local Super-Linter:** `./scripts/super_linter_local.py` (requires docker or podman)

### Documentation (MkDocs)

These commands should be run from the root directory.

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
