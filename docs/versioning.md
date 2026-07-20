# Versioning

This guide defines UCP's release-branch and backport process. UCP uses date-based
version identifiers in `YYYY-MM-DD` format; see
[Component Versioning and Release Snapshots](specification/overview.md#component-versioning-and-release-snapshots)
for the normative release model and
[Protocol Version](specification/overview.md#protocol-version) for profile
selection.

New development occurs on the `main` branch. We maintain long-lived branches for
all supported releases of the spec so that a published snapshot `D` stays
available for reference and maintenance. Approved backward-compatible changes —
features as well as security, correctness, and interoperability fixes — may be
backported to a maintained `release/D` branch and the artifacts generated from
it, and UCP re-certifies the snapshot before publishing the updated artifacts.
Breaking changes are never backported; they enter the next release.

* When the Tech Council approves a new version of UCP, we will cut a
  new branch named `release/YYYY-MM-DD` directly from the current state of
  `main`.
    * We will implement a code freeze on the release branch the moment a
      `release/YYYY-MM-DD` branch is cut. Only changes permitted by the policy
      above should move during this window.
    * Approved backward-compatible changes discovered after cutting a release branch should be made
      in one of two ways:
      1. The change is made on the release branch and merged to `main`.
      2. The change is made on `main` and cherry-picked to the release branch.
* Once finalized, we will merge the release branch into `main` and tag it (e.g.,
  `git tag -a vYYYY-MM-DD`).  We will use a GitHub Action to detect the new tag
  and automatically generate a release notes draft and upload artifacts.
* Unlike temporary feature branches, `release/YYYY-MM-DD` branches are
  long-lived and correspond to specific versions of the spec for historical
  reference and maintenance.

## Breaking PRs

* Breaking changes should include `!` in the PR title
* Timing: We will announce the breaking change in Discussions 2 weeks
  before the change is merged.
