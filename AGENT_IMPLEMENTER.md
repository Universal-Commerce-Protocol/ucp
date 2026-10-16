---
name: "UCP Agent Implementer Guidelines"
description: "Instructions for AI agents implementing Universal Commerce Protocol (UCP) in applications, services, or nodes."
---

# UCP Agent Implementer Guidelines

You are an AI agent tasked with implementing the Universal Commerce Protocol (UCP) in a client, server, or UCP node. Your goal is to ensure the implementation conforms to the UCP specification and correctly handles UCP messages.

## 1. Core Architecture & Key Concepts

* **Capabilities:** Standardized functional primitives (e.g., discovery, transactions, identity linking).
* **Extensions:** Modular enhancements to capabilities to support specific use cases without bloating base interfaces.
* **Dynamic Discovery:** UCP nodes declare supported capabilities via `.well-known/ucp` (or profile endpoints) to enable autonomous discovery and connection by client platforms.

## 2. Protocol Specifications & Schema Resources

*When to fetch:* Only fetch external resource links (like `llms.txt` or spec pages) when you need to understand specific schema details, integration patterns, or protocol rules. Avoid fetching for simple coding tasks.

* **Latest Stable Specification Index:** [`https://ucp.dev/latest/llms.txt`](https://ucp.dev/latest/llms.txt)
  *Use when:* You are developing new integrations, updating to the latest version, or when no specific version is requested (defaults to latest). This index contains links to LLM-optimized markdown specifications for all UCP capabilities (Discovery, Checkout, Identity, Order).
* **UCP Specification Index (All Versions):** [`https://ucp.dev/llms.txt`](https://ucp.dev/llms.txt)
  *Use when:* You need to find specifications for a specific historical version (e.g., matching a release branch like `release/2026-04-08` being used by the target node).
* **Conformance Testing:** Use the [UCP Conformance Test Suite](https://github.com/Universal-Commerce-Protocol/conformance) to validate endpoint compliance.
* **All Sample Implementations:** [GitHub Repo](https://github.com/Universal-Commerce-Protocol/samples)

## 3. Language-Specific SDKs & Sample Code

* **Python Developer Stack:**
    * **SDK:** [GitHub Repo](https://github.com/Universal-Commerce-Protocol/python-sdk) | [PyPI Package](https://pypi.org/project/ucp-sdk/) (`pip install ucp-sdk`)
    * **Reference Implementation (FastAPI):** [Python Sample Server & Client](https://github.com/Universal-Commerce-Protocol/samples/tree/main/rest/python)
* **JavaScript / Node.js Developer Stack:**
    * **SDK:** [GitHub Repo](https://github.com/Universal-Commerce-Protocol/js-sdk) | [npm Package](https://www.npmjs.com/package/@ucp-js/sdk) (`npm install @ucp-js/sdk`)
    * **Reference Implementation (Hono):** [Node.js Sample Server](https://github.com/Universal-Commerce-Protocol/samples/tree/main/rest/nodejs)

## 4. Implementation Checklist for Agents

1. **Declare Capabilities:** Expose `.well-known/ucp` listing supported capability versions and transport bindings.
2. **Implement Handlers:** Create API handlers matching UCP JSON schemas for request/response payloads.
3. **Handle Security & Protocol Rules:** Support UCP transport bindings, security tokens, and identity authorization where applicable.
4. **Validate:** Test endpoints against UCP schema definitions and the Conformance Suite.
