#!/usr/bin/env python3
"""Enhanced test runner with better output formatting."""

import argparse
import re
import subprocess  # noqa S404
import sys

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

console = Console()


class TestRunner:
    def __init__(self):
        self.console = Console()
        self.passed = 0
        self.failed = 0
        self.test_results = []

    def count_tests(self, test_path: str) -> int:
        """Count the number of tests to run."""
        cmd = ["pytest", test_path, "--collect-only", "-q"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Count lines that contain test names (they have :: in them)
        test_count = 0
        for line in result.stdout.split("\n"):
            if "::" in line and "test_" in line:
                test_count += 1

        # If that didn't work, try the summary line
        if test_count == 0:
            for line in result.stdout.split("\n"):
                # Look for patterns like "28 tests collected"
                match = re.search(r"(\d+)\s+test[s]?\s+collected", line)
                if match:
                    return int(match.group(1))

        return test_count if test_count > 0 else 28  # Fallback to known count

    def run_tests(self, test_path: str = "scripts") -> None:
        """Run tests with enhanced output and progress bar."""
        self.console.print(
            Panel.fit(
                "[bold cyan]Running Event Importer Tests[/bold cyan]",
                border_style="cyan",
            )
        )

        # Count tests first
        total_tests = self.count_tests(test_path)
        if total_tests == 0:
            # If we can't count, set a reasonable default
            total_tests = 30
            self.console.print("\n[cyan]Running tests...[/cyan]\n")
        else:
            self.console.print(f"\n[cyan]Found {total_tests} tests to run[/cyan]\n")

        # Build pytest command
        cmd = [
            "pytest",
            test_path,
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-report=xml",
            "--cov-fail-under=50",
            "-v",
            "--tb=short",
        ]

        # Run tests with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[cyan]{task.completed}/{task.total}[/cyan] tests"),
            TimeRemainingColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("Running tests", total=total_tests)

            # Start the pytest process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            output_lines = []
            current_test = 0

            # Process output line by line
            for line in process.stdout:
                output_lines.append(line)
                line = line.strip()

                # Parse test results
                if "::" in line and ("PASSED" in line or "FAILED" in line):
                    current_test += 1

                    # Extract test name and result
                    if "PASSED" in line:
                        self.passed += 1
                        test_name = line.split("PASSED")[0].strip()
                        # Store for summary
                        self.test_results.append(("PASSED", test_name))
                    elif "FAILED" in line:
                        self.failed += 1
                        test_name = line.split("FAILED")[0].strip()
                        self.test_results.append(("FAILED", test_name))

                    # Update progress (but don't exceed total)
                    progress.update(task, completed=min(current_test, total_tests))

            process.wait()
            output = "".join(output_lines)

        # Show results
        self._show_results(total_tests)

        # Parse and show coverage
        self._show_coverage(output)

        # If coverage parsing failed, show raw stats
        if "TOTAL" not in output:
            self.console.print(
                "\n[yellow]Coverage data not available in output[/yellow]"
            )
            self.console.print(
                "[dim]Run 'pytest scripts --cov=app' for full coverage report[/dim]"
            )

        # Exit with appropriate code
        sys.exit(0 if self.failed == 0 else 1)

    def _show_results(self, total_tests: int):
        """Display test results summary."""
        self.console.print()  # Add spacing

        if self.failed == 0:
            self.console.print(
                Panel(
                    f"[bold green]✅ All {total_tests} tests passed![/bold green]",
                    border_style="green",
                    box=box.ROUNDED,
                )
            )
        else:
            self.console.print(
                Panel(
                    f"[bold red]❌ {self.failed} tests failed out of {total_tests}[/bold red]",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )

            # Show failed tests
            self.console.print("\n[bold red]Failed Tests:[/bold red]")
            for status, test_name in self.test_results:
                if status == "FAILED":
                    # Clean up test name
                    clean_name = test_name.replace("scripts/", "")
                    self.console.print(f"  • {clean_name}")

    def _parse_coverage_lines(self, output: str) -> list[str]:
        """Parse coverage detail lines from pytest output."""
        lines = output.split("\n")
        coverage_lines = []
        for i, line in enumerate(lines):
            if "Name" in line and "Stmts" in line and "Miss" in line:
                j = i + 1
                while j < len(lines) and lines[j].startswith("-"):
                    j += 1
                while j < len(lines):
                    line = lines[j]
                    if "TOTAL" in line:
                        break
                    if line.strip() and not line.startswith("-"):
                        coverage_lines.append(line)
                    j += 1
                break
        return coverage_lines

    def _display_coverage_breakdown(self, coverage_lines: list[str]):
        """Display a table with coverage breakdown by module."""
        if not coverage_lines:
            return

        coverage_table = Table(
            title="Coverage by Module",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold cyan",
        )
        coverage_table.add_column("Module", style="cyan")
        coverage_table.add_column("Coverage", justify="right")
        coverage_table.add_column("Status", justify="center")

        coverage_data = []
        for line in coverage_lines[:10]:
            parts = line.split()
            if len(parts) >= 4:
                module = parts[0]
                try:
                    cov = float(parts[3].rstrip("%"))
                    coverage_data.append((module, cov))
                except (ValueError, IndexError):
                    pass

        coverage_data.sort(key=lambda x: x[1], reverse=True)

        for module, cov in coverage_data:
            style = "green" if cov >= 80 else "yellow" if cov >= 60 else "red"
            status = f"[{style}]●[/{style}]"
            cov_str = f"[{style}]{cov:.1f}%[/{style}]"

            short_module = module.replace("app/", "")
            if len(short_module) > 40:
                short_module = "..." + short_module[-37:]
            coverage_table.add_row(short_module, cov_str, status)

        self.console.print()
        self.console.print(coverage_table)

    def _show_test_summary_table(self):
        """Display the test summary table."""
        self.console.print()
        summary_table = Table(
            title="Test Summary",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", justify="right")
        total_ran = self.passed + self.failed
        summary_table.add_row("Tests Run", str(total_ran))
        summary_table.add_row("[green]Passed[/green]", f"[green]{self.passed}[/green]")
        summary_table.add_row("[red]Failed[/red]", f"[red]{self.failed}[/red]")
        if total_ran > 0:
            summary_table.add_row(
                "Success Rate", f"{(self.passed / total_ran * 100):.1f}%"
            )
        self.console.print(summary_table)

    def _show_coverage(self, output: str):
        """Parse and display coverage information."""
        total_match = re.search(r"TOTAL\s+\d+\s+\d+\s+([\d.]+)%", output)
        if total_match:
            total_coverage = float(total_match.group(1))

            self._show_test_summary_table()

            self.console.print()
            coverage_color = "green" if total_coverage >= 50 else "red"
            self.console.print(
                Panel(
                    f"[bold {coverage_color}]Total Coverage: {total_coverage:.1f}%[/bold {coverage_color}]",
                    border_style=coverage_color,
                    box=box.DOUBLE,
                )
            )

            coverage_lines = self._parse_coverage_lines(output)
            self._display_coverage_breakdown(coverage_lines)

            if total_coverage < 50:
                self.console.print(
                    "\n[bold red]❌ Coverage requirement not met (minimum: 50%)[/bold red]"
                )
            else:
                self.console.print(
                    "\n[bold green]✅ Coverage requirement met![/bold green]"
                )

        self.console.print("\n[dim]Reports:[/dim]")
        self.console.print("  • [cyan]HTML:[/cyan] htmlcov/index.html")
        self.console.print("  • [cyan]XML:[/cyan] coverage.xml")
        self.console.print(
            "  • [cyan]Run:[/cyan] make coverage-report for detailed analysis"
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run tests with enhanced output")
    parser.add_argument(
        "path", nargs="?", default="scripts", help="Test path (default: scripts)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    runner = TestRunner()
    runner.run_tests(args.path, args.verbose)


if __name__ == "__main__":
    main()
