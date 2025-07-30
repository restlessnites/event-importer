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
package-app: clean ## Build standalone Event Importer executable
	@echo "📦 Packaging Event Importer application..."
	@uv run pyinstaller --noconfirm event-importer.spec
	@echo "📦 Creating zip with preserved symlinks..."
	@cd dist && zip -ry ../event-importer.zip event-importer
	@echo "✅ Created event-importer.zip"

package-app-x86_64: clean ## Build Event Importer for Intel Mac (x86_64)
	@echo "📦 Packaging Event Importer for Intel Mac (x86_64)..."
	@uv run pyinstaller --noconfirm event-importer-x86_64.spec
	@echo "📦 Creating zip with preserved symlinks..."
	@cd dist && zip -ry ../event-importer-x86_64.zip event-importer
	@echo "✅ Created event-importer-x86_64.zip"

package-installer: clean ## Build standalone installer executable
	@echo "📦 Packaging Event Importer installer..."
	@uv run pyinstaller --noconfirm event-importer-installer.spec
	@echo "📦 Creating installer zip..."
	@cd dist && zip -r ../event-importer-installer.zip event-importer-installer
	@echo "✅ Created event-importer-installer.zip"

package-installer-x86_64: clean ## Build installer for Intel Mac (x86_64)
	@echo "📦 Packaging installer for Intel Mac (x86_64)..."
	@uv run pyinstaller --noconfirm event-importer-installer-x86_64.spec
	@echo "✅ Intel Mac installer built successfully"

package: package-app package-installer ## Build both app and installer executables

package-x86_64: package-app-x86_64 package-installer-x86_64 ## Build both for Intel Mac

##@ Cross-Platform Notes

package-universal: ## Build universal binary for macOS (requires both architectures)
	@echo "📦 Building universal binary for macOS..."
	@echo "⚠️  This requires building on both Intel and Apple Silicon Macs"
	@echo "⚠️  Then using 'lipo' to combine the binaries"
	@echo "📚 See docs/CROSS_PLATFORM.md for details"

package-windows: ## Build for Windows (must run on Windows)
	@echo "📦 Building for Windows..."
	@echo "⚠️  This must be run on a Windows machine with Python and uv installed"
	@echo "⚠️  Use: uv run pyinstaller --noconfirm event-importer-windows.spec"
	@echo "📚 See docs/CROSS_PLATFORM.md for details"



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