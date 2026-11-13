# Run these from reference/. Each target executes from the repository root,
# where `reference` is importable as a package.
RUN = cd .. && uv run --frozen --group reference

.PHONY: generate check update serve shop

# Routes and types from the profiles. Needs the pinned ucp-schema; see README.
generate:
	$(RUN) python -m reference.build

# The integration test: both transports, with and without the extension.
check: generate
	$(RUN) python -m reference.check

# Rewrite transcripts/ after a deliberate wire change, then review git diff.
update: generate
	$(RUN) python -m reference.check --update

# Local development only: the Business on http://localhost:8182.
serve: generate
	$(RUN) uvicorn --factory reference.business.app:serve --port 8182

# Shop at the Business started by `make serve`, over MCP. TRANSPORT=rest for REST.
shop:
	$(RUN) python -m reference.platform.client --transport $(or $(TRANSPORT),mcp)
