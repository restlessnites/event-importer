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
	@echo "🖥️  Starting CLI..."
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
	@echo "🗑️  Deep cleaning..."
	@rm -rf .venv
	@rm -rf node_modules
	@echo "✅ All cleaned!"

# Development helpers
dev-setup: setup
	@echo "🛠️  Setting up development tools..."
	@pre-commit install || true
	@echo "✅ Development environment ready!"

# Check everything
check: lint test
	@echo "✅ All checks passed!"

# Help
help:
	@echo "Event Importer - Makefile Commands"
	@echo "=================================="
	@echo ""
	@echo "📦 Installation & Setup:"
	@echo "  make install       - Run the automated installer"
	@echo "  make setup         - Quick setup (uv sync + env file)"
	@echo "  make dev-setup     - Setup for development (includes pre-commit)"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test          - Run tests with nice formatted output"
	@echo "  make test-verbose  - Run tests with verbose output"
	@echo "  make coverage-report - Show detailed coverage report"
	@echo "  make test-all      - Run all tests (scripts + app)"
	@echo "  make quick         - Quick test run without coverage"
	@echo "  make badge         - Update coverage badge in README"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  make lint          - Run linters (ruff, mypy)"
	@echo "  make format        - Auto-format code"
	@echo "  make check         - Run lint + tests"
	@echo ""
	@echo "🚀 Running:"
	@echo "  make run-cli ARGS='--help'  - Run CLI with arguments"
	@echo "  make run-api       - Start HTTP API server"
	@echo "  make run-mcp       - Start MCP server"
	@echo "  make import URL=<url> - Import an event from URL"
	@echo "  make db-stats      - Show database statistics"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean         - Clean test/cache artifacts"
	@echo "  make clean-all     - Deep clean (including venv)"
	@echo ""
	@echo "Examples:"
	@echo "  make import URL='https://ra.co/events/1234567'"
	@echo "  make run-cli ARGS='list --format table'"