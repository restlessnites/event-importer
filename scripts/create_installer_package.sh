#!/bin/bash

# Event Importer Installer Package Creator
# This script creates a zip file that users can download and run

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}RESTLESS / EVENT IMPORTER INSTALLER GENERATOR${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Read version from pyproject.toml
VERSION=$(grep "^version =" "$PROJECT_ROOT/pyproject.toml" | awk -F'"' '{print $2}')

# Output directory
OUTPUT_DIR="$PROJECT_ROOT/dist"
PACKAGE_NAME="restless-event-importer-v$VERSION"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Create temporary directory for package
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/$PACKAGE_NAME"

echo "Creating package in temporary directory..."

# Copy necessary files
mkdir -p "$PACKAGE_DIR"
cp -r "$PROJECT_ROOT/app" "$PACKAGE_DIR/"
cp -r "$PROJECT_ROOT/installer" "$PACKAGE_DIR/"
cp "$PROJECT_ROOT/pyproject.toml" "$PACKAGE_DIR/"
cp "$PROJECT_ROOT/env.example" "$PACKAGE_DIR/"
cp "$PROJECT_ROOT/README.md" "$PACKAGE_DIR/"
cp "$PROJECT_ROOT/install.py" "$PACKAGE_DIR/"
cp "$PROJECT_ROOT/Makefile.dist" "$PACKAGE_DIR/Makefile"
cp "$PROJECT_ROOT/LICENSE" "$PACKAGE_DIR/"

# Create data directory (empty)
mkdir -p "$PACKAGE_DIR/data"

# Create a simplified README for the installer
cat > "$PACKAGE_DIR/INSTALL_README.md" << 'EOF'
# Event Importer Quick Install

## Installation Steps

1. Open Terminal (press Cmd+Space, type "Terminal", press Enter)

2. Navigate to this folder:
   ```bash
   cd ~/Downloads/restless-event-importer-installer
   ```

3. Run the installer:
   ```bash
   make install
   ```

4. Follow the on-screen instructions to:
   - Install required dependencies
   - Configure your API keys
   - Set up Claude Desktop integration

## Requirements

- macOS 10.15 or later
- Python 3.10 or later
- Internet connection for downloading dependencies

## Getting Help

If you encounter any issues:
- Check the full documentation in README.md
- Visit https://github.com/restlessnites/event-importer

## What This Installer Does

1. Checks your system for required software
2. Installs Homebrew (if needed)
3. Installs uv package manager
4. Sets up the Python environment
5. Helps you configure API keys
6. Automatically configures Claude Desktop
7. Validates the installation

The entire process takes about 5-10 minutes.
EOF

# Create the zip file
cd "$TEMP_DIR"
zip -r "$OUTPUT_DIR/$PACKAGE_NAME.zip" "$PACKAGE_NAME" -x "*.pyc" "*__pycache__*" "*.DS_Store"

# Clean up
rm -rf "$TEMP_DIR"

# Get the size of the zip file
SIZE=$(ls -lh "$OUTPUT_DIR/$PACKAGE_NAME.zip" | awk '{print $5}')

echo -e "\n${GREEN}✓ Package created successfully!${NC}"
echo -e "Location: ${BLUE}$OUTPUT_DIR/$PACKAGE_NAME.zip${NC}"
echo -e "Size: ${BLUE}$SIZE${NC}"
echo -e "\nUsers can now:"
echo "1. Download this zip file"
echo "2. Extract it"
echo "3. Run: make install"