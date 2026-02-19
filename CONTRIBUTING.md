<!--
   Copyright 2026 UCP Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
-->

# How to Contribute

We would love to accept your patches and contributions to this project.

## Before you begin

### Sign our Contributor License Agreement

Contributions to this project must be accompanied by a
[Contributor License Agreement](https://cla.developers.google.com/about) (CLA).
You (or your employer) retain the copyright to your contribution; this simply
gives us permission to use and redistribute your contributions as part of the
project.

If you or your current employer have already signed the Google CLA (even if it
was for a different project), you probably don't need to do it again.

Visit <https://cla.developers.google.com/> to see your current agreements or to
sign a new one.

### Review our Community Guidelines

This project follows [Google's Open Source Community
Guidelines](https://opensource.google/conduct/).

## Other Ways to Contribute

### Reporting Issues

If you find a bug, a mistake in the documentation, or have a feature request,
please open an issue.
This helps us track problems and improve the project.

### Discussions

If you want to start a conversation, share an idea, or ask a question, feel free
to use GitHub Discussions.

## Contribution Process

### Significant Changes

Any significant change to the protocol requires a formal
[Enhancement Proposal](../../issues/new?template=enhancement-proposal.md)
and will require Tech Council (TC) approval. Because a change to the protocol
requires the entire adopting ecosystem to implement the change, we consider
significant changes to include:

* Core Schema Modifications: Any change to JSON schemas, including
  adding/updating fields or field descriptions
* Protocol Changes: Alterations to communication flows or expected behaviors of
  operations
* New API Endpoints: Introduction of entirely new capabilities or services.
* Backwards Incompatibility: Any "breaking" change that requires a major version
  increment.

An [Enhancement Proposal](../../issues/new?template=enhancement-proposal.md)
is a living artifact that tracks a proposal through its lifecycle:

* **Proposal:** Anyone can submit; idea is proposed and debated.
* **Provisional:** TC majority vote to accept; enters working draft iteration.
* **Implemented:** TC majority vote to finalize; code complete and merged.

Every [Enhancement Proposal](../../issues/new?template=enhancement-proposal.md)
must follow a standard template requiring sections for a Summary, Motivation,
Detailed Design, Risks, a Test Plan, and Graduation Criteria. This creates a
permanent, public design record for the project's evolution.

### Capability Maturity Levels

After an Enhancement Proposal reaches "Provisional" status, the capability
enters the maturity lifecycle with the following stability guarantees:

#### Working Draft

* **Version:** `Working Draft`
* **Stability:** Breaking changes expected
* **Status:** Prototyping, gathering feedback, iterating on design
* **Exit criteria:** TC majority vote to advance

#### Candidate

* **Version:** `Candidate`
* **Stability:** API surface stable; implementation details may evolve
* **Status:** Early adopter implementations, production pilots
* **Exit criteria:** TC majority vote to advance

#### Stable

* **Version:** `YYYY-MM-DD` (date-based version assigned)
* **Stability:** Full backward compatibility within major version
* **Status:** Production deployments

### Voting and decision making

The path below should be followed for resolving issues that are technical in
nature.

* L1: routine changes (bug fixes, documentation, minor improvements) require
  approval from at least 2 Maintainers.
* L2: Any technical issues that span across topics and/or cannot be resolved
  amongst maintainers and DWGs will be escalated to the TC. Significant changes
  affecting core protocol architecture must follow the Enhancement Proposal
  process, requiring TC approval before implementation.
* L3: Any changes made to the Governance process (e.g updating the
  [GOVERNANCE.md](GOVERNANCE.md) file) or any changes that impact the core
  protocol’s scope or adoption, must be approved by Governance Council (GC).

The TC reserves the right to stop any discussions deemed non-critical to the
protocol.

### Versioning

The base protocol uses date based versioning. Major version increments (breaking
changes) require a majority Governing Council approval due to the high cost to
the ecosystem. A quorum requires all Governing Council members (or appropriate
representatives) to be present for decision-making. New features should
typically be attempted through the extensions framework first. If an extension
achieves significant usage, it can be considered for adoption into the next
minor version of the core.

### Adding new extensions and capabilities to the core protocol

UCP is designed to be extensible while keeping the core protocol light. A
core principle of UCP is to ensure that the set of extensions and capabilities
defined in UCP have broad ecosystem support. Vendors should first create
capabilities & extensions in vendor-specific namespace pattern
(e.g. com.{vendor}.*) for new use cases. Requests to add new capabilities and
extensions should only be submitted when there is proven widespread adoption of
vendor-specific capabilities and extensions. See
[Spec URL Binding](https://ucp.dev/specification/overview/#spec-url-binding)
and [Governance Model](https://ucp.dev/specification/overview/#governance-model)
for more details on using namespace pattern for creating vendor-specific
capabilities and extensions.

### Code Reviews

All submissions, including submissions by project members, require review. We
use [GitHub pull requests](https://docs.github.com/articles/about-pull-requests)
for this purpose.

### Pull Request Titles and Commit Messages

This repository enforces **Conventional Commits** for Pull Request titles.
Your PR title must follow this format: `type: description`. If your change
is a breaking change (e.g., removing a schema field or file), you **must**
add `!` before the colon: `type!: description`.

**Common Types:**

* `feat`: A new feature
* `fix`: A bug fix
* `docs`: Documentation only changes
* `style`: Changes that do not affect the meaning of the code
* `refactor`: A code change that neither fixes a bug nor adds a feature
* `perf`: A code change that improves performance
* `test`: Adding missing tests or correcting existing tests
* `chore`: Changes to the build process or auxiliary tools and libraries

**Examples:**

* `feat: add new payment gateway`
* `fix: resolve crash on checkout`
* `docs: update setup guide`
* `feat!: remove deprecated buyer field from checkout`

### Linting and Automated Checks

We use linters and automated checks to maintain code quality and consistency.
These checks run automatically via GitHub Actions when you open a pull request.
Your pull request must pass all checks before it can be merged.

You can run many of these checks locally before committing by installing and
using `pre-commit`:

```bash
uv tool install pre-commit
pre-commit install
```

This will set up pre-commit hooks to run automatically when you `git commit`.

You can also run [super-linter](https://github.com/super-linter/super-linter)
locally by running `./scripts/super_linter_local.py`. This assumes you have
either [docker](https://www.docker.com/) or [podman](https://podman.io/)
installed on your system.

### Submitting a Pull Request

1. Fork the repository and create your branch from `main`.
2. Make your changes, ensuring you follow the setup instructions below.
3. If you've installed `pre-commit`, it will run checks as you commit.
4. Ensure your pull request title follows the Conventional Commits format.
5. Fill out the pull request template in GitHub, providing details about
    your change.
6. Push your branch to GitHub and open a pull request.
7. Address any automated check failures or reviewer feedback.

## Local Development Setup

### Schema Development

Schemas live in `source/` and are published with `ucp_*` annotations intact.
Agents use [ucp-schema](https://github.com/universal-commerce-protocol/ucp-schema)
to resolve annotations for specific operations at runtime.

1. Ensure `ucp-schema` is installed:

   ```bash
   cargo install ucp-schema                 # from crates.io
   cargo install --git https://github.com/universal-commerce-protocol/ucp-schema  # from git
   ```

2. Make updates to JSON files in `source/`
3. Run `ucp-schema lint source/` to validate syntax and references

If you change any JSON schemas, you may need to regenerate SDK client libraries.
For example, to regenerate Python Pydantic models run
`bash sdk/python/generate_models.sh`. Our CI system runs
`scripts/ci_check_models.sh` to verify that models can be generated
successfully from the schemas.

### Documentation Development

This project uses [uv](https://docs.astral.sh/uv/) for Python dependency management.

1. Install Python dependencies: `uv sync`
2. Ensure `ucp-schema` is installed (see above)
3. Run the development server: `uv run mkdocs serve --watch source`
4. Open **<http://127.0.0.1:8000>** in your browser
5. Before submitting, run `uv run mkdocs build --strict` to check for warnings/errors
