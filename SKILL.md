---
name: "UCP Contributor Playbook"
description: "Instructions for AI coding agents to contribute to the Universal Commerce Protocol ecosystem."
---

# AI Agent Skill: Universal Commerce Protocol (UCP) Contributor Playbook

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

### Documentation Sync & Server

* **Sync Dependencies:**

  ```bash
  uv sync
  ```

* **Run Dev Server:**

  ```bash
  uv run mkdocs serve
  ```

* **Strict Build Test:**

  ```bash
  uv run mkdocs build --strict
  ```

### Code Formatting and Quality

* **Local Linter Check (requires Docker or Podman):**

  ```bash
  ./scripts/super_linter_local.py
  ```

* **Run Pre-commit Manual Validation:**

  ```bash
  pre-commit run --all-files
  ```
