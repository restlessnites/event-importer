.PHONY: setup test test-verbose coverage-report test-all clean lint format run-cli run-api run-mcp help

# Default target
.DEFAULT_GOAL := help

##@ Installation & Setup
setup: ## Set up the development environment
	@if [ ! -d ".venv" ]; then uv venv; fi
	@. .venv/bin/activate && uv sync
	@cp -n env.example .env || true

dev-setup: setup ## Set up for development (includes pre-commit hooks)
	@. .venv/bin/activate && pre-commit install || true

update: ## Check for updates and install the latest version
	@uv run --active event-importer update


##@ Testing
test: ## Run all tests with coverage
	@uv run --active pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml

coverage-report: ## Show detailed coverage report in the console
	@python scripts/coverage_report.py

quick: ## Run a quick test run without coverage
	@uv run --active pytest tests -v --tb=short


##@ Code Quality
lint: ## Run linters (ruff)
	@uv run --active ruff check . || true

format: ## Auto-format code with ruff
	@uv run --active ruff check . --fix
	@uv run --active ruff format .

check: lint test ## Run all checks (linting and tests)

##@ Running
run-cli: ## Run the CLI interface (pass args with ARGS="...")
	@uv run --active event-importer $(ARGS)

run-api: ## Start the HTTP API server
	@uv run --active event-importer api

run-mcp: ## Start the MCP server
	@uv run --active event-importer mcp

import: ## Import an event from a URL (pass url with URL="...")
	@uv run --active event-importer import $(URL)

db-stats: ## Show database statistics
	@uv run --active event-importer stats


##@ Cleanup
clean: ## Clean up test and cache artifacts
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf coverage.xml
	@rm -rf .coverage
	@rm -rf .ruff_cache
	@rm -rf .mypy_cache
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

clean-all: clean ## Deep clean the project (includes venv)
	@rm -rf .venv
	@rm -rf node_modules


##@ Distribution
package: clean ## Build standalone executable with PyInstaller
	@echo "📦 Packaging application..."
	@uv run pyinstaller --noconfirm event-importer.spec

##@ Validation
validate: ## Validate the installation
	@uv run --active event-importer validate || true


##@ Help
help: ## Show this help message
	@echo "RESTLESS / EVENT IMPORTER"
	@echo ""
	@echo "Usage: make [target]"
	@awk 'BEGIN {FS = ":.*?## |^##@ "} \
		/^(##@|([a-zA-Z0-9_-]+:.*?##))/ { \
			if ($$1 == "") { \
				printf "\n\033[1;33m%s\033[0m\n", $$2; \
			} else { \
				printf "  \033[36m%-29s\033[0m %s\n", $$1, $$2; \
			} \
		}' $(MAKEFILE_LIST)