#!/usr/bin/env python3
"""Generate a clean coverage report."""

import subprocess  # noqa S404
import sys

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def get_coverage_data():
    """Run coverage and get the data."""
    # Run coverage report
    result = subprocess.run(
        ["coverage", "report", "--format=total"], capture_output=True, text=True
    )

    total_coverage = float(result.stdout.strip())

    # Get detailed report
    result = subprocess.run(["coverage", "report"], capture_output=True, text=True)

    return result.stdout, total_coverage


def parse_coverage_output(output: str):
    """Parse coverage output into structured data."""
    lines = output.strip().split("\n")

    # Skip header lines
    data_lines = []
    for i, line in enumerate(lines):
        if line.startswith("----"):
            data_lines = lines[i + 1 :]
            break

    files = []
    for line in data_lines:
        if line.strip() and not line.startswith("TOTAL"):
            parts = line.split()
            if len(parts) >= 4:
                files.append(
                    {
                        "name": parts[0],
                        "stmts": int(parts[1]),
                        "miss": int(parts[2]),
                        "cover": float(parts[3].rstrip("%")),
                    }
                )

    return files


def group_files_by_category(files):
    """Group files into categories based on their path."""
    categories = {
        "Interfaces": [],
        "Core": [],
        "Services": [],
        "Agents": [],
        "Integrations": [],
        "Other": [],
    }
    for file_data in files:
        name = file_data["name"]
        if "interfaces/" in name:
            categories["Interfaces"].append(file_data)
        elif "core/" in name:
            categories["Core"].append(file_data)
        elif "services/" in name:
            categories["Services"].append(file_data)
        elif "agents/" in name:
            categories["Agents"].append(file_data)
        elif "integrations/" in name:
            categories["Integrations"].append(file_data)
        else:
            categories["Other"].append(file_data)
    return categories


def display_category_table(category, files_in_category):
    """Display a table of coverage data for a category."""
    if not files_in_category:
        return

    table = Table(
        title=f"{category} Coverage",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("File", style="cyan")
    table.add_column("Coverage", justify="right")
    table.add_column("Lines", justify="right")

    files_in_category.sort(key=lambda x: x["cover"], reverse=True)

    for file_data in files_in_category:
        coverage = file_data["cover"]
        style = "green" if coverage >= 80 else "yellow" if coverage >= 60 else "red"
        name = file_data["name"].replace("app/", "")
        if len(name) > 50:
            name = "..." + name[-47:]
        table.add_row(
            name,
            f"[{style}]{coverage:.1f}%[/{style}]",
            f"{file_data['stmts'] - file_data['miss']}/{file_data['stmts']}",
        )
    console.print(table)
    console.print()


def display_summary(total_files, files, total_coverage):
    """Display the final summary of the coverage report."""
    coverage_color = "green" if total_coverage >= 50 else "red"
    console.print(
        Panel(
            f"[bold {coverage_color}]Total Coverage: {total_coverage:.1f}%[/bold {coverage_color}]",
            border_style=coverage_color,
            box=box.DOUBLE,
        )
    )

    console.print("\n[bold]Quick Stats:[/bold]")
    well_tested = len([f for f in files if f["cover"] >= 80])
    needs_work = len([f for f in files if f["cover"] < 50])
    console.print(f"  • Well tested (≥80%): [green]{well_tested}[/green] files")
    console.print(f"  • Needs work (<50%): [red]{needs_work}[/red] files")
    console.print(f"  • Total files: {total_files}")


def main():
    """Generate coverage report."""
    console.print(
        Panel.fit("[bold cyan]Coverage Report[/bold cyan]", border_style="cyan")
    )

    try:
        output, total_coverage = get_coverage_data()
        files = parse_coverage_output(output)

        categories = group_files_by_category(files)

        for category, files_in_category in categories.items():
            display_category_table(category, files_in_category)

        display_summary(len(files), files, total_coverage)

    except Exception as e:
        console.print(f"[red]Error generating report: {e}[/red]")
        console.print("Make sure to run tests first: pytest scripts")
        sys.exit(1)


if __name__ == "__main__":
    main()
