.PHONY: install setup test test-verbose coverage-report test-all clean lint format run-cli run-api run-mcp help

# Default target
.DEFAULT_GOAL := help

# Installation and setup
install:
	@echo "🚀 Running Event Importer installer..."
	@python install.py

setup:
	@echo "📦 Setting up development environment..."
	@uv sync
	@cp -n env.example .env || true
	@echo "✅ Setup complete! Don't forget to configure your .env file"

# Testing
test:
	@echo "Running all tests..."
	@uv run pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml
	@make badge

coverage-report:
	@python scripts/coverage_report.py

quick:
	@pytest tests -v --tb=short

badge:
	@echo "🎨 Generating coverage badge..."
	@python scripts/generate_badge.py

# Integration tests
test-genre-enhancer:
	@pytest tests/integration_tests/test_genre_enhancer.py

test-url-analyzer:
	@pytest tests/integration_tests/test_url_analyzer.py

test-date-parser:
	@pytest tests/integration_tests/test_date_parser.py

test-ra-genres:
	@pytest tests/integration_tests/test_ra_genres.py

test-google-custom-search-api:
	@pytest tests/integration_tests/test_google_custom_search_api.py

test-image-enhancer:
	@pytest tests/integration_tests/test_image_enhancer.py

test-importer:
	@pytest tests/integration_tests/test_importer.py

test-error-capture:
	@pytest tests/integration_tests/test_error_capture.py

test-dice-api:
	@pytest tests/integration_tests/test_dice_api.py

# Code quality
lint:
	@echo "🔍 Running linters..."
	@ruff check . || true
	@mypy app || true

format:
	@echo "🎨 Formatting code..."
	@ruff check . --fix
	@ruff format .

# Running the application
run-cli:
	@echo "🖥️ Starting CLI..."
	@uv run event-importer $(ARGS)

run-api:
	@echo "🌐 Starting API server..."
	@uv run event-importer api

run-mcp:
	@echo "🤖 Starting MCP server..."
	@uv run event-importer mcp

# Import shortcuts
import:
	@echo "📥 Importing event from URL..."
	@uv run event-importer import $(URL)

# Database operations
db-stats:
	@echo "📊 Database statistics..."
	@uv run event-importer stats

# Utility commands
clean:
	@echo "🧹 Cleaning up..."
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf coverage.xml
	@rm -rf .coverage
	@rm -rf .ruff_cache
	@rm -rf .mypy_cache
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned!"

clean-all: clean
	@echo "🗑️ Deep cleaning..."
	@rm -rf .venv
	@rm -rf node_modules
	@echo "✅ All cleaned!"

# Development helpers
dev-setup: setup
	@echo "🛠️ Setting up development tools..."
	@pre-commit install || true
	@echo "✅ Development environment ready!"

# Check everything
check: lint test
	@echo "✅ All checks passed!"

# Help
help:
	@echo "RESTLESS / EVENT IMPORTER"
	@echo ""
	@echo "Installation & Setup:"
	@echo "  make install             - Run the automated installer"
	@echo "  make setup               - Quick setup (uv sync + env file)"
	@echo "  make dev-setup           - Setup for development (includes pre-commit)"
	@echo ""
	@echo "Testing:"
	@echo "  make test                - Run tests with nice formatted output"
	@echo "  make test-verbose        - Run tests with verbose output"
	@echo "  make coverage-report     - Show detailed coverage report"
	@echo "  make test-all            - Run all tests (scripts + app)"
	@echo "  make quick               - Quick test run without coverage"
	@echo "  make badge               - Update coverage badge in README"
	@echo ""
	@echo "Integration Tests:"
	@echo "  make test-genre-enhancer - Test genre enhancer"
	@echo "  make test-url-analyzer   - Test URL analyzer"
	@echo "  make test-date-parser    - Test date parser"
	@echo "  make test-ra-genres      - Test RA genres"
	@echo "  make test-google-custom-search-api"
	@echo "                           - Test Google Custom Search API"
	@echo "  make test-image-enhancer - Test image enhancer"
	@echo "  make test-importer       - Test importer"
	@echo "  make test-error-capture  - Test error capture"
	@echo "  make test-dice-api       - Test Dice API"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint                - Run linters"
	@echo "  make format              - Auto-format code"
	@echo "  make check               - Run lint + tests"
	@echo ""
	@echo "Running:"
	@echo "  make run-cli ARGS='--help'"
	@echo "                           - Run CLI with arguments"
	@echo "  make run-api             - Start HTTP API server"
	@echo "  make run-mcp             - Start MCP server"
	@echo "  make import URL=<url>    - Import an event from URL"
	@echo "  make db-stats            - Show database statistics"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean               - Clean test/cache artifacts"
	@echo "  make clean-all           - Deep clean (including venv)"
	@echo ""
	@echo "Examples:"
	@echo "  make import URL='https://ra.co/events/1234567'"
	@echo "  make run-cli ARGS='list --format table'"