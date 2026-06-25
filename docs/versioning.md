# Versioning

UCP uses date-based version identifiers following the format `YYYY-MM-DD` to
indicate the last date backwards-incompatible changes were made to a given
component.

## Layered Versioning

UCP versions three layers independently. Each layer evolves on its own
cadence and is negotiated by its own mechanism:

1. **Transport bindings.** Each service entry — REST, MCP, A2A, or
    embedded — declares its own `version`. The wire contract for each
    transport lives in the OpenAPI / OpenRPC / Agent Card document referenced
    from the service entry's `schema` field. Transports **MAY** evolve their
    version handling independently from the core protocol release.
2. **Core protocol** (`ucp.version`). Governs the cross-cutting mechanisms
    every transport binding inherits: discovery, negotiation flow, signature
    requirements, profile structure, and the error envelope. Validated as a
    pre-negotiation gate; mismatch returns `version_unsupported`.
3. **Capabilities and extensions.** Each capability entry declares its own
    `version`, and each extension that augments a capability versions
    independently. Capability versions are intersected at negotiation; the
    highest mutual version wins, and extensions **MAY** declare
    `requires.protocol` and `requires.capabilities` constraints that further
    filter the active set.

For the negotiation algorithm and version-compatibility rules, see
[Version Negotiation](specification/overview.md#version-negotiation) and
[Independent Component Versioning](specification/overview.md#independent-component-versioning)
in the Architecture Overview.

## Release Process

New development occurs on the `main` branch. We will maintain long-lived
branches for all supported releases of the spec.

* When the Tech Council approves a new version of UCP, we will cut a
  new branch named `release/YYYY-MM-DD` directly from the current state of
  `main`.
    * We will implement a code freeze on the release branch the moment a
      `release/YYYY-MM-DD` branch is cut. Only critical bug fixes should move
      during this window.
    * Critical issues discovered after cutting a release branch should be fixed
      in one of two ways:
      1. The fix is made on the release branch and merged to `main`.
      2. The fix is made on `main` and cherry-picked to the release branch.
* Once finalized, we will merge the release branch into `main` and tag it (e.g.,
  `git tag -a vYYYY-MM-DD`).  We will use a GitHub Action to detect the new tag
  and automatically generate a release notes draft and upload artifacts.
* Unlike temporary feature branches, release/YYYY-MM-DD branches are long-lived
  and correspond to specific versions of the spec for historical reference and
  maintenance.

## Breaking PRs

* Breaking changes should include `!` in the PR title
* Timing: We will announce the breaking change in Discussions 2 weeks
  before the change is merged.
