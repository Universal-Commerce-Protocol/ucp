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

## Contribution Process

### Code Reviews

All submissions, including submissions by project members, require review. We
use [GitHub pull requests](https://docs.github.com/articles/about-pull-requests)
for this purpose.

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

1.  Ensure dependencies are installed: `pip install -r requirements-docs.txt`
2.  Run the development server: `mkdocs serve --watch spec`
3.  Open **http://127.0.0.1:8000** in your browser

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
