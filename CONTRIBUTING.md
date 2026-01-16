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

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools and libraries

**Examples:**

- `feat: add new payment gateway`
- `fix: resolve crash on checkout`
- `docs: update setup guide`
- `feat!: remove deprecated buyer field from checkout`

### Linting and Automated Checks

We use linters and automated checks to maintain code quality and consistency.
These checks run automatically via GitHub Actions when you open a pull request.
Your pull request must pass all checks before it can be merged.

You can run many of these checks locally before committing by installing and
using `pre-commit`:

```bash
pip install pre-commit
pre-commit install
```

This will set up pre-commit hooks to run automatically when you `git commit`.

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

### Spec Development

1. Make relevant updates to JSON files in `source/`
2. Run `python generate_schemas.py` to generate updated files in `spec/`
3. Check outputs from step above to ensure deltas are expected. You may need to
   extend `generate_schemas.py` if you are introducing a new generation concept

To validate JSON and YAML files format and references in `spec/`, run
`python validate_specs.py`.

If you change any JSON schemas in `spec/`, you must regenerate any SDK client
libraries that depend on them. For example, to regenerate Python Pydantic
models run `bash sdk/python/generate_models.sh`. Our CI system runs
`scripts/ci_check_models.sh` to verify that models can be generated
successfully from the schemas.

It is also important to go through documentation locally whenever spec files
are updated to ensure there are no broken references or stale/missing contents.

### Documentation Development

1. Ensure dependencies are installed: `pip install -r requirements-docs.txt`
2. Run the development server: `mkdocs serve --watch spec`
3. Open **<http://127.0.0.1:8000>** in your browser
4. Before submitting a pull request with documentation changes, run
    `mkdocs build --strict` to ensure there are no warnings or errors. Our CI
    build uses this command and will fail if warnings are present (e.g.,
    broken links).

### Using a virtual environment (Recommended)

To avoid polluting your global environment, use a virtual environment. Prefix
the virtual environment name with a `.` so the versioning control systems don't
track pip install files:

```bash
$ sudo apt-get install virtualenv python3-venv
$ virtualenv .ucp # or python3 -m venv .ucp
$ source .ucp/bin/activate
(.ucp) $ pip install -r requirements-docs.txt
(.ucp) $ mkdocs serve --watch spec
(.ucp) $ deactivate # when done
```
