#!/usr/bin/env python3
"""Update coverage percentage in README.md"""

import re
import subprocess  # noqa S404
import sys
from pathlib import Path


def get_coverage_percentage():
    """Run pytest with coverage and extract the percentage."""
    try:
        result = subprocess.run(
            ["pytest", "--cov=app", "--cov-report=term"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Look for the TOTAL line in the coverage report
        for line in result.stdout.split("\n"):
            if line.startswith("TOTAL"):
                # Extract percentage from line like: TOTAL  4749  2583  45.61%
                parts = line.split()
                if len(parts) >= 4 and parts[-1].endswith("%"):
                    return parts[-1].rstrip("%")

        print("Could not find coverage percentage in output")
        return None

    except Exception as e:
        print(f"Error running coverage: {e}")
        return None


def update_readme(coverage_pct):
    """Update the coverage percentage in README.md"""
    try:
        with Path.open("README.md") as f:
            content = f.read()

        # Update the coverage line
        pattern = r"Current test coverage: \*\*~?\d+%\*\*"
        replacement = f"Current test coverage: **~{coverage_pct}%**"

        updated_content = re.sub(pattern, replacement, content)

        if updated_content != content:
            with Path.open("README.md", "w") as f:
                f.write(updated_content)
            print(f"Updated README.md with coverage: {coverage_pct}%")
        else:
            print("No changes needed to README.md")

    except Exception as e:
        print(f"Error updating README: {e}")
        return False

    return True


def main():
    """Main function."""
    print("Running tests with coverage...")
    coverage = get_coverage_percentage()

    if coverage:
        # Round to nearest integer for display
        coverage_int = str(int(float(coverage)))
        success = update_readme(coverage_int)
        sys.exit(0 if success else 1)
    else:
        print("Failed to get coverage percentage")
        sys.exit(1)


if __name__ == "__main__":
    main()
