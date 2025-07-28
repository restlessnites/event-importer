.PHONY: install setup test test-verbose coverage-report test-all clean lint format run-cli run-api run-mcp help dist

# Default target
.DEFAULT_GOAL := help

##@ Installation & Setup
install: ## Run the interactive installer
	@python install.py

setup: ## Set up the development environment
	@uv sync
	@cp -n env.example .env || true
	@echo "✅ Setup complete! Don't forget to configure your .env file"

dev-setup: setup ## Set up for development (includes pre-commit hooks)
	@pre-commit install || true
	@echo "✅ Development environment ready!"


##@ Testing
test: ## Run all tests with coverage
	@uv run pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml
	@make badge

coverage-report: ## Show detailed coverage report in the console
	@python scripts/coverage_report.py

quick: ## Run a quick test run without coverage
	@pytest tests -v --tb=short

badge: ## Generate and update the coverage badge in README.md
	@python scripts/generate_badge.py


##@ Integration Tests
test-genre-enhancer: ## Run the Genre Enhancer integration tests
	@pytest tests/integration_tests/test_genre_enhancer.py

test-url-analyzer: ## Run the URL Analyzer integration tests
	@pytest tests/integration_tests/test_url_analyzer.py

test-date-parser: ## Run the Date Parser integration tests
	@pytest tests/integration_tests/test_date_parser.py

test-ra-genres: ## Run the RA Genres integration tests
	@pytest tests/integration_tests/test_ra_genres.py

test-google-custom-search-api: ## Run the Google Custom Search API integration tests
	@pytest tests/integration_tests/test_google_custom_search_api.py

test-image-enhancer: ## Run the Image Enhancer integration tests
	@pytest tests/integration_tests/test_image_enhancer.py

test-importer: ## Run the Importer integration tests
	@pytest tests/integration_tests/test_importer.py

test-error-capture: ## Run the Error Capture integration tests
	@pytest tests/integration_tests/test_error_capture.py

test-dice-api: ## Run the Dice API integration tests
	@pytest tests/integration_tests/test_dice_api.py


##@ Code Quality
lint: ## Run linters (ruff and mypy)
	@ruff check . || true
	@mypy app || true

format: ## Auto-format code with ruff
	@ruff check . --fix
	@ruff format .

check: lint test ## Run all checks (linting and tests)
	@echo "✅ All checks passed!"


##@ Running
run-cli: ## Run the CLI interface (pass args with ARGS="...")
	@uv run event-importer $(ARGS)

run-api: ## Start the HTTP API server
	@uv run event-importer api

run-mcp: ## Start the MCP server
	@uv run event-importer mcp

import: ## Import an event from a URL (pass url with URL="...")
	@uv run event-importer import $(URL)

db-stats: ## Show database statistics
	@uv run event-importer stats


##@ Cleanup
clean: ## Clean up test and cache artifacts
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf coverage.xml
	@rm -rf .coverage
	@rm -rf .ruff_cache
	@rm -rf .mypy_cache
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned!"

clean-all: clean ## Deep clean the project (includes venv)
	@rm -rf .venv
	@rm -rf node_modules
	@echo "✅ All cleaned!"


##@ Distribution
dist: ## Generate the installer package
	@bash scripts/create_installer_package.sh
	@echo "✅ Installer package created in dist/ directory"


##@ Validation
validate: ## Validate the installation
	@uv run event-importer validate


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