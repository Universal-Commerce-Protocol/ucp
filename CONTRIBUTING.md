# Contributing to UCP

We welcome community contributions to the Universal Commerce Protocol (UCP)!

Please review the central [UCP Organization Contributing Guide](https://github.com/Universal-Commerce-Protocol/.github/blob/main/CONTRIBUTING.md) for overarching contribution policies, Technical Council governance, and licensing details.

## Code & Schema Formatting

JSON schemas and configuration files in this repository follow standard Prettier formatting rules:

- **Formatting Check**: `npx prettier --check "**/*.json"`
- **Formatting Fix**: `npx prettier --write "**/*.json"`

Pre-commit hooks and GitHub Actions Super-Linter automatically enforce JSON formatting via Prettier.

### Ignoring Formatting Commits in Git Blame

Large-scale formatting commits are recorded in `.git-blame-ignore-revs` to preserve historical line attribution in `git blame`.

GitHub natively ignores these revisions in the blame UI. To configure local `git blame` to ignore them as well, run:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```
