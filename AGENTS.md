---
name: "UCP Contributor Playbook"
description: "Instructions for AI coding agents to contribute to the Universal Commerce Protocol ecosystem."
---

# Universal Commerce Protocol (UCP) AI Contributor Playbook

This document provides structured rules, constraints, and commands for AI coding agents to successfully contribute to the Universal Commerce Protocol (UCP) ecosystem.

---

## Context & Scope

The Universal Commerce Protocol (UCP) is a date-based versioned protocol designed to unify commerce operations.

* **Schemas:** Raw JSON schemas live in the `source/` directory and are annotated with custom `ucp_*` annotations.
* **Documentation:** Standard documentation is written in Markdown (inside `docs/`) and served via MkDocs.
* **Deployment & Versioning:** Built version directories are managed and output using `mike`.
* **SDKs/Client Libraries:** Code schemas are consumed by external repository SDK builders to generate client libraries. Do not look for local SDK files or shell scripts for model generation in this repository.

---

## Crucial Rules for AI Agents

AI agents operating in this repository MUST strictly adhere to the following guidelines:

### 1. Schema Guidelines

* **Annotations:** Ensure all custom annotations (e.g., `ucp_*`) remain fully intact. Use the `ucp-schema` utility for validation and annotations resolution.
* **Validation:** Always validate schema changes immediately after editing JSON files in `source/`. Do not wait for CI.

### 2. Documentation Guidelines

* **Navigation Sync:** Any page added or modified in the MkDocs navigation (`mkdocs.yml`) should be documented and described in the `llmstxt` plugin section.

### 3. Code Quality & Linting

* **Do Not Disable Checks:** Never bypass, comment out, or disable linter rules, pre-commit hooks, or test assertions.
* **Local Validation:** Always run the local super-linter or pre-commit manual tests before considering a task complete.

### 4. Commit Standards

* **Conventional Commits:** Every pull request title and commit message must follow **Conventional Commits** (`type: description`).
    * **Common Types:**
        * `feat`: A new feature
        * `fix`: A bug fix
        * `docs`: Documentation only changes
        * `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc.)
        * `refactor`: A code change that neither fixes a bug nor adds a feature
        * `perf`: A change to the code that improves performance
        * `test`: Adding missing tests or correcting existing tests
        * `chore`: Changes to the build process or auxiliary tools and libraries
    * **Examples:**
        * `feat: add new payment gateway`
        * `fix: resolve crash on checkout`
        * `docs: update setup guide`
        * `feat!: remove deprecated buyer field from checkout`
* **Breaking Changes:** If a change introduces a breaking schema or protocol adjustment (e.g., removing a schema field or file), you **must** append `!` to the type (e.g., `feat!: remove deprecated buyer field from checkout`).

### 5. Significant Changes & Protocol Evolution

* **Tech Council Approval:** Any significant change to the protocol requires a formal **Enhancement Proposal** and Tech Council (TC) approval. If you are asked to make a significant change, verify if an Enhancement Proposal has been approved.
* **What Constitutes a Significant Change:**
    * **Core Schema Modifications:** Any change to JSON schemas under `source/`, including adding/updating fields or field descriptions.
    * **Protocol Changes:** Alterations to communication flows or expected behaviors of operations.
    * **New API Endpoints:** Introduction of entirely new capabilities or services.
    * **Backwards Incompatibility:** Any "breaking" change that requires a major version increment.
* **Capability Maturity Levels:** Be aware of the capability maturity lifecycle stages when contributing:
    * **Working Draft:** Prototyping and iterating on design. Breaking changes are expected. Version: `Working Draft`.
    * **Candidate:** API surface is stable; implementation details may evolve. Version: `Candidate`.
    * **Stable:** Full backward compatibility within a major version. Version: `YYYY-MM-DD` (date-based version assigned).

---

## Verification & Execution Command Reference

Use the following exact commands to execute, validate, and verify tasks:

### Schema Operations

* **Lint Schemas:**

  ```bash
  ucp-schema lint source/
  ```

* **External SDK Integration:**

  Core JSON schemas are consumed by external SDK repositories to generate client libraries. Ensure your schema edits validate successfully with the linter.

### Documentation Build, Preview & Validation

* **Sync Dependencies:**

  ```bash
  uv sync
  ```

* **Run Dev Server (Live Reload for Current Branch):**

  ```bash
  uv run mkdocs serve
  ```

* **Strict Single-Version Build Test:**

  ```bash
  uv run mkdocs build --strict
  ```

* **Build Full Multi-Version Site (`scripts/build_local.sh`):**

  Rebuilds all versioned release branches along with the current `draft` and `latest` docs using `mike` and `mkdocs`, merging them into a unified preview site inside `local_preview/`.
    * Pass `--main-only` to skip release branches and quickly build only the current branch.

  ```bash
  ./scripts/build_local.sh [--main-only]
  ```

* **Validate Internal Links & Anchors (`scripts/check_links.py`):**

  Scans HTML output in `local_preview/` (generated by `build_local.sh`) to catch broken internal links, missing pages, and invalid anchor `#fragments` across all versioned docs. Respects regex ignore patterns defined in `.linkignore`.

  ```bash
  uv run ./scripts/check_links.py [path/to/built_site]
  ```

### Code Formatting and Quality

* **Local Linter Check (`scripts/super_linter_local.py`):**

  Executes GitHub Actions `super-linter` locally using Docker or Podman. Automatically parses `.github/workflows/linter.yaml` to ensure local linting environment and rule configurations exactly match CI. Supports `--runtime` (`podman`|`docker`) and `--branch`.

  ```bash
  ./scripts/super_linter_local.py
  ```

* **Run Pre-commit Manual Validation:**

  ```bash
  pre-commit run --all-files
  ```
