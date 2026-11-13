#   Copyright 2026 UCP Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Generate routes and types from a profile: `make generate`.

A profile names capabilities. `ucp-schema` turns it into an OpenAPI
document (the operations those capabilities expose, bound to composed
types) and a JSON Schema bundle (the types themselves). A stock generator
turns the bundle into Pydantic models. Nothing here is specific to this
sample: point it at another profile to bootstrap another server.

Output lands in `reference/generated/`, which is not committed. There is
one directory per combination of the profile's extensions, because the
shape of a payload depends on which extensions were negotiated:

    full/        every extension the profile declares
    base/        no extensions
    <names>/     any other combination, named after its extensions
"""

import copy
import importlib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
REPO = ROOT.parent
OUT = ROOT / "generated"

# `main` carries the label "draft", which is not a legal protocol version, so
# on `main` the sample stands in the latest released version. Release
# branches carry their own date in mkdocs.yml and do not use this. Doc
# examples use the same stand-in: UCP_VERSION_PLACEHOLDER in
# scripts/validate_examples.py. Change the two together.
DRAFT_VERSION = "2026-08-25"


def ucp_version() -> str:
  """Return the protocol version this checkout of the specification is."""
  text = (REPO / "mkdocs.yml").read_text()
  version = re.search(r'ucp_version: "([^"]+)"', text).group(1)
  return (
    version if re.fullmatch(r"\d{4}-\d{2}-\d{2}", version) else DRAFT_VERSION
  )


def load(path: Path) -> dict:
  """Read a profile template, filling in the protocol version."""
  return json.loads(
    path.read_text().replace("{{ ucp_version }}", ucp_version())
  )


def operations(openapi: dict):
  """Yield `(method, path, operation)` for every operation in a document."""
  for path, item in openapi["paths"].items():
    for method, operation in item.items():
      if method in ("get", "post", "put", "patch", "delete"):
        yield method.upper(), path, operation


def models(variant: str):
  """Import the Pydantic models generated for one extension combination."""
  return importlib.import_module(f"reference.generated.{variant}.models")


def response_type(operation: dict, reply: dict) -> str:
  """Name the model of a response: the operation's resource, or an error.

  `operation` is an entry of the generated OpenAPI document. An operation
  answers with its resource, or with an error response when there is none
  to return, which `ucp.status` says.
  """
  if reply["ucp"].get("status") == "error":
    return "ErrorResponse"
  response = next(iter(operation["responses"].values()))
  schema = response["content"]["application/json"]["schema"]
  return schema.get("oneOf", [schema])[0]["$ref"].rsplit("/", 1)[-1]


def wire(model) -> dict:
  """Serialize a model to the JSON that goes on the wire.

  Only what was set is sent: no nulls, and no defaults filled in.
  """
  return model.model_dump(mode="json", exclude_unset=True, exclude_none=True)


def platform_profiles() -> dict[str, dict]:
  """Return the sample Platform profiles by name."""
  return {
    path.stem: load(path)
    for path in sorted((ROOT / "platform" / "profiles").glob("*.json"))
  }


def extensions(profile: dict) -> list[str]:
  """Return the names of the extensions a profile declares."""
  capabilities = profile["ucp"]["capabilities"]
  return sorted(
    name
    for name, entries in capabilities.items()
    if any("extends" in entry for entry in entries)
  )


def variant(profile: dict, active) -> str:
  """Name the generated directory for a negotiated set of capabilities."""
  declared = extensions(profile)
  chosen = [name for name in declared if name in active]
  if chosen == declared:
    return "full"
  return "_".join(name.rsplit(".", 1)[-1] for name in chosen) or "base"


def _localize(node, published: str, local: str):
  """Point published schema URLs at this checkout's `source/` directory.

  A served profile carries `https://ucp.dev/...` URLs. Generation must read
  the schemas of this commit, so each such URL becomes a relative path.
  """
  if isinstance(node, dict):
    return {k: _localize(v, published, local) for k, v in node.items()}
  if isinstance(node, list):
    return [_localize(v, published, local) for v in node]
  if isinstance(node, str) and node.startswith(published):
    tail = node[len(published) :]
    if tail.startswith(("schemas/", "services/")):
      return f"{local}/{tail}"
  return node


INSTALL = """\
{problem}

The generate-types and generate-openapi commands are in the ucp-schema
revision this repository pins. Install it with:

    cargo install --locked \\
      --git https://github.com/Universal-Commerce-Protocol/ucp-schema \\
      --rev {revision}

That replaces the ucp-schema on your PATH. To keep the one you have, add
`--root <dir>` to the command and set UCP_SCHEMA_BIN=<dir>/bin/ucp-schema.
"""


def ucp_schema() -> str:
  """Locate a `ucp-schema` binary that has the generate commands."""
  binary = os.environ.get("UCP_SCHEMA_BIN") or shutil.which("ucp-schema")
  usable = binary and not any(
    subprocess.run([binary, command, "--help"], capture_output=True).returncode
    for command in ("generate-openapi", "generate-types")
  )
  if not usable:
    problem = (
      f"{binary} does not have the commands this needs."
      if binary
      else "ucp-schema is not installed."
    )
    revision = (REPO / ".ucp-schema-rev").read_text().strip()
    sys.exit(INSTALL.format(problem=problem, revision=revision))
  return binary


def generate(profile: dict, out: Path) -> None:
  """Write `openapi.json` and `types.json` for `profile` into `out`."""
  out.mkdir(parents=True, exist_ok=True)
  published = f"https://ucp.dev/{ucp_version()}/"
  local = os.path.relpath(REPO / "source", out)
  local_profile = out / "profile.json"
  local_profile.write_text(
    json.dumps(_localize(profile, published, local), indent=2) + "\n"
  )
  for command, name in (
    ("generate-openapi", "openapi.json"),
    ("generate-types", "types.json"),
  ):
    subprocess.run(
      [ucp_schema(), command, "--profile", local_profile, "-o", out / name],
      check=True,
    )


def python_models(bundle: Path, out: Path) -> None:
  """Turn a type bundle into Pydantic models with an off-the-shelf generator.

  The models parse requests and serialize responses. They are used as
  generated; the only tuning is in the flags below.
  """
  subprocess.run(
    [sys.executable, "-W", "ignore", "-m", "datamodel_code_generator"]
    + ["--input", bundle, "--input-file-type", "jsonschema"]
    + ["--output", out, "--output-model-type", "pydantic_v2.BaseModel"]
    + ["--use-title-as-name", "--use-standard-collections"]
    + ["--use-union-operator", "--enum-field-as-literal", "all"]
    + ["--disable-timestamp"]
    # Named string types become plain `str`, so that they can key a dict.
    + ["--collapse-root-models"]
    # URLs and timestamps stay as the strings that were sent. The default
    # types rewrite them on the way out (a trailing slash, a new offset).
    + ["--type-mappings", "string+uri=string", "string+date-time=string"],
    check=True,
  )


def main() -> None:
  """Generate everything the sample needs."""
  shutil.rmtree(OUT, ignore_errors=True)
  business = load(ROOT / "business" / "profile.json")
  generate(business, OUT / "full")

  # Schemas are composed for the extensions that were negotiated, so the
  # Business needs the types for each smaller combination as well.
  declared = extensions(business)
  for size in range(len(declared)):
    for chosen in itertools.combinations(declared, size):
      narrowed = copy.deepcopy(business)
      narrowed["ucp"]["capabilities"] = {
        name: entries
        for name, entries in business["ucp"]["capabilities"].items()
        if name not in declared or name in chosen
      }
      generate(narrowed, OUT / variant(business, chosen))
  for types in sorted(OUT.glob("*/types.json")):
    python_models(types, types.with_name("models.py"))
  print(f"Generated {OUT.relative_to(REPO)}/ for UCP {ucp_version()}")


if __name__ == "__main__":
  main()
