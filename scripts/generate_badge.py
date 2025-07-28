#!/usr/bin/env python3
"""Generate a coverage badge for the README."""

import subprocess  # noqa: S404
import sys
import xml.etree.ElementTree as ET  # noqa: S405
from pathlib import Path


def get_coverage_percentage():
    """Get the current coverage percentage."""
    try:
        result = subprocess.run(
            ["coverage", "report", "--format=total"],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        # Try to get from XML if available
        coverage_xml = Path("coverage.xml")
        if coverage_xml.exists():
            try:
                tree = ET.parse(coverage_xml)  # noqa: S314
                root = tree.getroot()
                return float(root.attrib.get("line-rate", 0)) * 100
            except (ET.ParseError, ValueError):
                pass
        return 0


def get_badge_color(percentage):
    """Get badge color based on coverage percentage."""
    if percentage >= 80:
        return "brightgreen"
    if percentage >= 60:
        return "yellow"
    if percentage >= 40:
        return "orange"
    return "red"


def generate_badge_url(percentage):
    """Generate shields.io badge URL."""
    color = get_badge_color(percentage)
    label = "coverage"
    message = f"{percentage:.1f}%25"  # %25 is URL encoded %
    return f"https://img.shields.io/badge/{label}-{message}-{color}"


def update_readme_badge(badge_url):
    """Update the coverage badge in README.md."""
    readme_path = Path("README.md")
    if not readme_path.exists():
        print("README.md not found")
        return False

    content = readme_path.read_text()

    # Look for the coverage badge line
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "Coverage" in line and "img.shields.io/badge/coverage" in line:
            # Replace with static badge
            lines[i] = (
                f"[![Coverage]({badge_url})](https://github.com/restlessnites/event-importer)"
            )
            break

    # Write back
    readme_path.write_text("\n".join(lines))
    return True


def main():
    """Generate and update coverage badge."""
    coverage = get_coverage_percentage()

    if coverage == 0:
        print("❌ No coverage data found. Run tests first: make test")
        sys.exit(1)

    print(f"📊 Current coverage: {coverage:.1f}%")

    badge_url = generate_badge_url(coverage)
    print(f"🎨 Badge URL: {badge_url}")

    if update_readme_badge(badge_url):
        print("✅ README.md updated with coverage badge")
        print("📝 Remember to commit the changes!")
    else:
        print("❌ Failed to update README.md")


if __name__ == "__main__":
    main()
