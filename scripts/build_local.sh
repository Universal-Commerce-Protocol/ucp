#!/bin/bash
set -e

# When did we run this build?
date

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

# Check UCP-Schema CLI version vs current Crates.io version and prompt
PURPLE='\033[1;35m'
NC='\033[0m' # No Color
echo "Using ucp-schema CLI: $(which ucp-schema)"
UCP_CLI_VERSION=$(ucp-schema --version | sed 's/ucp-schema //')
echo "Local ucp-schema version:  '$UCP_CLI_VERSION'"
UCP_CRATES_VERSION=$(cargo search ucp-schema -q | sed 's/ucp-schema = "//' | sed 's/".*$//')
echo "Crates ucp-schema version: '$UCP_CRATES_VERSION'"
if [[ $UCP_CLI_VERSION != "$UCP_CRATES_VERSION" ]]; then
	while true; do
		echo -e "${PURPLE}*ucp-schema version mismatch*${NC}"
		read -r -p " Continue? (y/n) " yn
		case $yn in
		[Yy]*)
			echo "proceed..."
			break
			;;
		[Nn]*)
			echo "exiting..."
			exit
			;;
		*) echo "invalid response" ;;
		esac
	done
fi

if ! command -v mike >/dev/null 2>&1; then
	echo "Error: mike executable not found in PATH."
	echo "Please ensure you have run 'uv sync' in the root."
	exit 1
fi

echo "Using Mike: $(which mike)"

MAIN_ONLY=false
if [[ "$1" == "--main-only" ]]; then
	MAIN_ONLY=true
	echo "Running in MAIN_ONLY mode. Skipping release branches."
fi

echo "=== Setup ==="
rm -rf "$OUTPUT_DIR"

echo "=== Syncing Release Branches ==="
if [ "$MAIN_ONLY" = false ]; then
	git fetch origin
	# Sync local gh-pages with remote to avoid divergence errors
	git branch -f gh-pages origin/gh-pages 2>/dev/null || true

	# Find all release branches (both local and remote, format: release/YYYY-MM-DD)
	RELEASE_BRANCHES=$(git branch -a | grep -E "(remotes/origin/)?release/[0-9]{4}-[0-9]{2}-[0-9]{2}" | sed -E 's|.*(release/[0-9]{4}-[0-9]{2}-[0-9]{2}).*|\1|' | sort -u)

	echo "Found branches: $RELEASE_BRANCHES"
fi

# List of folders we want to extract later
EXTRACT_LIST="draft latest versions.json"

if [ "$MAIN_ONLY" = false ]; then
	for branch in $RELEASE_BRANCHES; do
		version=$(echo "$branch" | sed 's/release\///')

		if git show-ref --verify --quiet "refs/heads/$branch"; then
			TREE_REF="$branch"
			echo ">>> Rebuilding Version: $version (from local $branch)"
		else
			TREE_REF="origin/$branch"
			echo ">>> Rebuilding Version: $version (from origin/$branch)"
		fi

		EXTRACT_LIST="$EXTRACT_LIST $version"

		rm -rf "$WORKTREE_DIR"
		git worktree prune
		git worktree add -f "$WORKTREE_DIR" "$TREE_REF"

		pushd "$WORKTREE_DIR" >/dev/null

		# Deploy
		# mike will now use the mkdocs in PATH (which is the root venv)
		export DOCS_MODE=spec
		export UCP_BUILD_VERSION="$version"
		mike deploy "$version"

		popd >/dev/null
		git worktree remove -f "$WORKTREE_DIR"
	done
fi

echo ">>> Building Current Version (Draft & Latest)"
export DOCS_MODE=spec
export UCP_BUILD_VERSION="draft"
mike deploy draft

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
