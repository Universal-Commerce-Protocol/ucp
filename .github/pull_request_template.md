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

# Description

Please include a summary of the changes and the related issue. Please also
include relevant motivation and context.

## Type of change

Please delete options that are not relevant.

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] **Breaking change** (fix or feature that would cause existing
      functionality to not work as expected, **including removal of schema files
      or fields**)
- [ ] Documentation update

---

### Is this a Breaking Change or Removal?

If you checked "Breaking change" above, or if you are removing **any** schema
files or fields:

- [ ] **I have added `!` to my PR title** (e.g., `feat!: remove field`).
- [ ] **I have added justification below.**

```text
## Breaking Changes / Removal Justification

(Please provide a detailed technical and strategic rationale here for why this
breaking change or removal is necessary.)
```

---

## Checklist

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published in downstream modules

---

### Pull Request Title

This repository enforces **Conventional Commits**. Your PR title must follow
this format: `type: description` or `type!: description` for breaking changes.

**Types:**

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space,
  formatting, etc)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools and libraries

**Breaking Changes:**

If your change is a breaking change (e.g., removing a field or file), you
**must** add `!` before the colon in your title:
`type!: description`

**Examples:**

- `feat: add new payment gateway`
- `fix: resolve crash on checkout`
- `docs: update setup guide`
- `feat!: remove deprecated buyer field from checkout`
