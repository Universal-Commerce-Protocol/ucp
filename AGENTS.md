---
name: "UCP AI Agent Playbook"
description: "Operating contract and reference guide for AI agents implementing UCP or contributing to the UCP specification."
---

# Universal Commerce Protocol (UCP) AI Agent Playbook

Welcome! This file serves as the operating contract for AI agents working with the Universal Commerce Protocol (UCP).

---

## 🎯 Step 1: Identify Your Task Persona

Before executing any commands or writing code, determine your primary task:

* **Persona A: UCP Implementer / Integrator**

    * *Goal:* Implementing UCP endpoints for a business node, platform, or service provider.
    * ➡️ **Proceed to Section 1: UCP Implementer Guide**

* **Persona B: UCP Protocol & Documentation Contributor**

    * *Goal:* Editing specification JSON schemas, modifying documentation, or contributing to the `Universal-Commerce-Protocol/ucp` repository.
    * ➡️ **Proceed to Section 2: UCP Contributor Playbook**

---

## 1. UCP Implementer Guide (Platforms & Service Providers)

Use these guidelines when helping a business node or service provider implement UCP endpoints or integrate with UCP platforms.

> [!NOTE]
> UCP protocol releases (including schemas and specifications) are versioned by date (YYYY-MM-DD) and are located in dedicated release branches named like **`release/YYYY-MM-DD`** (for example: `release/2026-04-08`).

### Core Architecture & Key Concepts

* **Capabilities:** Standardized functional primitives (e.g., discovery, transactions, identity linking).
* **Extensions:** Modular enhancements to capabilities to support specific use cases without bloating base interfaces.
* **Dynamic Discovery:** Business nodes declare supported capabilities via `.well-known/ucp` (or profile endpoints) to enable autonomous discovery and connection by client platforms.

### Protocol Specifications & Schema Resources

*When to fetch:* Only fetch external resource links (like `llms.txt` or spec pages) when you need to understand specific schema details, integration patterns, or protocol rules. Avoid fetching for simple coding tasks.

* **Latest Stable Specification Index:** [`https://ucp.dev/latest/llms.txt`](https://ucp.dev/latest/llms.txt)
  *Use when:* You are developing new integrations, updating to the latest version, or when no specific version is requested (defaults to latest). This index contains links to LLM-optimized markdown specifications for all UCP capabilities (Discovery, Checkout, Identity, Order).
* **UCP Specification Index (All Versions):** [`https://ucp.dev/llms.txt`](https://ucp.dev/llms.txt)
  *Use when:* You need to find specifications for a specific historical version (e.g., matching a release branch like `release/2026-04-08` being used by the target node).
* **Conformance Testing:** Use the [UCP Conformance Test Suite](https://github.com/Universal-Commerce-Protocol/conformance) to validate endpoint compliance.
* **All Sample Implementations:** [GitHub Repo](https://github.com/Universal-Commerce-Protocol/samples)

### Language-Specific SDKs & Sample Code

* **Python Developer Stack:**
    * **SDK:** [GitHub Repo](https://github.com/Universal-Commerce-Protocol/python-sdk) | [PyPI Package](https://pypi.org/project/ucp-sdk/) (`pip install ucp-sdk`)
    * **Reference Implementation (FastAPI):** [Python Sample Server & Client](https://github.com/Universal-Commerce-Protocol/samples/tree/main/rest/python)
* **JavaScript / Node.js Developer Stack:**
    * **SDK:** [GitHub Repo](https://github.com/Universal-Commerce-Protocol/js-sdk) | [npm Package](https://www.npmjs.com/package/@ucp-js/sdk) (`npm install @ucp-js/sdk`)
    * **Reference Implementation (Hono):** [Node.js Sample Server](https://github.com/Universal-Commerce-Protocol/samples/tree/main/rest/nodejs)

### Implementation Checklist for Agents

1. **Declare Capabilities:** Expose `.well-known/ucp` listing supported capability versions and transport bindings.
2. **Implement Handlers:** Create API handlers matching UCP JSON schemas for request/response payloads.
3. **Handle Security & Protocol Rules:** Support UCP transport bindings, security tokens, and identity authorization where applicable.
4. **Validate:** Test endpoints against UCP schema definitions and the Conformance Suite.

---

## 2. UCP Contributor Playbook (Repository Maintainers)

Follow these parameters when editing and contributing directly to this repository (`Universal-Commerce-Protocol/ucp`).

### Core Operational Rules

* **Schema Source of Truth:** Edit JSON schemas only inside the `source/` directory. Always preserve `ucp_*` annotations.
* **Commit Messages:** Follow Conventional Commits (e.g., `feat: add transaction extension`, `docs: update guide`). Use `!` for breaking changes (e.g., `feat!: update profile schema`).
* **Quality Guardrails:** Never bypass or comment out linter rules, pre-commit hooks, or test assertions.
* **Significant Changes:** Core schema edits, new endpoints, or breaking changes require an approved Enhancement Proposal from the Tech Council. See [CONTRIBUTING.md](https://raw.githubusercontent.com/Universal-Commerce-Protocol/.github/main/CONTRIBUTING.md#significant-changes).

### Local Command Reference

#### Schema Validation & Resolution

* **Lint Schemas:** `ucp-schema lint source/` (checks syntax, broken references, and annotation structures).
* **Resolve Annotations:** `ucp-schema resolve source/schemas/shopping/checkout.json --op create --request --pretty` (compiles a master schema for a specific direction/operation, resolving `ucp_*` annotations).
* **Validate Payloads:** `ucp-schema validate --schema source/schemas/shopping/checkout.json --op create --request source/examples/checkout_create_request.json` (validates a sample payload against a schema).
* **Run Pre-Commit Checks:** `PIP_INDEX_URL=https://pypi.org/simple/ pre-commit run --all-files`

#### Documentation (MkDocs)

* **Build Full Preview (All Versions):** `./scripts/build_local.sh`
* **Build Draft Preview (Faster, local only):** `./scripts/build_local.sh --draft-only`
* **Serve Local Preview:** `python3 -m http.server 8000 -d local_preview/`
* **Live Dev Server (Quick Edits):** `uv run mkdocs serve`
* **Check Broken Links:** `uv run ./scripts/check_links.py local_preview/`
