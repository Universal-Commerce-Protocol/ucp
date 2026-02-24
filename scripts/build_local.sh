#!/bin/bash
set -e

# Ensure we are running from the project root (parent of scripts/)
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

# Configuration
WORKTREE_DIR="build_temp"
OUTPUT_DIR="local_preview"
GH_PAGES_BRANCH="gh-pages"

# Ensure tools are available
# Prepend the project's venv bin to PATH so mike finds mkdocs properly
# Also add ucp-schema binary from sibling directory
export PATH="$PROJECT_ROOT/.venv/bin:$PROJECT_ROOT/../ucp-schema/target/release:$PATH:$HOME/.cargo/bin"

if ! command -v mike >/dev/null 2>&1; then
	echo "Error: mike executable not found in PATH."
	echo "Please ensure you have run 'uv sync' in the root."
	exit 1
fi

echo "Using Mike: $(which mike)"

echo "=== Setup ==="
rm -rf "$OUTPUT_DIR"

echo "=== Syncing Release Branches ==="
git fetch origin
# Sync local gh-pages with remote to avoid divergence errors
git branch -f gh-pages origin/gh-pages 2>/dev/null || true

# Find all release branches (format: release/YYYY-MM-DD)
RELEASE_BRANCHES=$(git branch -r | grep "origin/release/[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}" | sed 's/ *origin\///')

echo "Found branches: $RELEASE_BRANCHES"

# List of folders we want to extract later
EXTRACT_LIST="draft latest versions.json"

for branch in $RELEASE_BRANCHES; do
	version=$(echo "$branch" | sed 's/release\///')
	echo ">>> Rebuilding Version: $version (from $branch)"
	EXTRACT_LIST="$EXTRACT_LIST $version"

	rm -rf "$WORKTREE_DIR"
	git worktree prune
	git worktree add -f "$WORKTREE_DIR" "origin/$branch"

	pushd "$WORKTREE_DIR" >/dev/null

	# Copy latest hooks from project root (main) to ensure consistent build logic
	cp "$PROJECT_ROOT/hooks.py" .

	# Deploy
	# mike will now use the mkdocs in PATH (which is the root venv)
	export DOCS_MODE=spec
	export UCP_BUILD_VERSION="$version"
	mike deploy "$version"

	popd >/dev/null
	git worktree remove -f "$WORKTREE_DIR"
done

echo ">>> Building Current Version (Draft & Latest)"
export DOCS_MODE=spec
export UCP_BUILD_VERSION="draft"
mike deploy draft

LATEST_VERSION=$(echo "$RELEASE_BRANCHES" | sed 's/release\///' | sort -r | head -n 1)

if [ -n "$LATEST_VERSION" ]; then
	echo "Aliasing 'latest' to $LATEST_VERSION"
	mike alias "$LATEST_VERSION" latest --update-aliases
else
	echo "No release found, aliasing latest to draft"
	mike alias draft latest --update-aliases
fi

echo ">>> Building Root Site"
# Build root site FIRST so we establish the base (index.html, etc.)
# Run in sub-shell or unset variable to be safe, though later steps don't use it
export DOCS_MODE=root
uv run mkdocs build --strict -d "$OUTPUT_DIR"

echo ">>> Merging Spec Versions"
# Extract ONLY the spec folders (versions) to avoid overwriting Root Site's index.html
echo "Extracting: $EXTRACT_LIST"
git archive "$GH_PAGES_BRANCH" $EXTRACT_LIST | tar -x -C "$OUTPUT_DIR"

echo "=== Build Complete! ==="
echo "Run this command to serve:"
echo "python3 -m http.server 8000 -d $OUTPUT_DIR"
