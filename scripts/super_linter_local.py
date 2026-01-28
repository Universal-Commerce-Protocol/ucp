#!/usr/bin/env -S uv run

"""Run super-linter locally using configuration from GitHub Actions."""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


def map_action_to_image(action_str):
  """Map GitHub Action string to ghcr.io image."""
  # super-linter/super-linter/slim@v8 ->
  # ghcr.io/super-linter/super-linter:slim-v8
  match = re.match(r"super-linter/super-linter/(.*)@(.*)", action_str)

  if match:
    variant = match.group(1)
    version = match.group(2)
    return f"ghcr.io/super-linter/super-linter:{variant}-{version}"

  return action_str


def main():
  """Parse workflow and run linter."""
  default_runtime = "podman" if shutil.which("podman") else "docker"

  parser = argparse.ArgumentParser(
    description=(
      "Run super-linter locally using configuration from GitHub Actions."
    )
  )
  parser.add_argument(
    "--runtime",
    choices=["docker", "podman"],
    default=default_runtime,
    help="Container runtime to use (default: %(default)s)",
  )
  parser.add_argument(
    "--branch",
    default="main",
    help="Default branch to compare against (default: main)",
  )

  args = parser.parse_args()

  workflow_path = Path(".github/workflows/linter.yaml")

  if not workflow_path.exists():
    print(f"Error: {workflow_path} not found.")
    sys.exit(1)

  with workflow_path.open() as f:
    workflow = yaml.safe_load(f)

  lint_step = None
  jobs = workflow.get("jobs", {})

  for job_data in jobs.values():
    steps = job_data.get("steps", [])

    for step in steps:
      if step.get("name") == "Lint Code Base":
        lint_step = step
        break

  if not lint_step:
    print("Error: Could not find 'Lint Code Base' step in workflow.")
    sys.exit(1)

  assert lint_step is not None

  lint_env = lint_step.get("env", {})
  action_uses = lint_step.get("uses", "")
  image = map_action_to_image(action_uses)

  cmd = [
    args.runtime,
    "run",
    "--rm",
    "-e",
    "RUN_LOCAL=true",
    "-v",
    f"{Path.cwd()}:/tmp/lint:Z",
  ]

  for key, value in lint_env.items():
    if key == "DEFAULT_BRANCH":
      val_str = str(args.branch)
    elif isinstance(value, bool):
      val_str = str(value).lower()
    elif isinstance(value, str):
      if "${{" in value:
        continue
      val_str = value
    else:
      val_str = str(value)

    cmd.extend(["-e", f"{key}={val_str}"])

  cmd.append(image)

  print(f"Executing: {' '.join(cmd)}")

  try:
    result = subprocess.run(cmd, check=False)
    sys.exit(result.returncode)
  except KeyboardInterrupt:
    print("\nInterrupted by user")
    sys.exit(1)


if __name__ == "__main__":
  main()
