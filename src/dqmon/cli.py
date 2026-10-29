"""dqmon CLI — pytest for your dbt project."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from dqmon.scanner import scan_dbt_project
from dqmon.checks import run_checks
from dqmon.report import print_report

app = typer.Typer(
    name="dqmon",
    help="Zero-config data quality monitoring for dbt projects.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def init(
    path: Optional[Path] = typer.Argument(
        None, help="Path to dbt project (default: current directory)"
    ),
):
    """Auto-detect dbt project and show what dqmon will monitor."""
    project_path = path or Path.cwd()
    manifest = _find_manifest(project_path)
    if not manifest:
        console.print("[red]No dbt manifest found.[/red]")
        console.print("Run [bold]dbt compile[/bold] or [bold]dbt run[/bold] first, then try again.")
        raise typer.Exit(1)

    project = scan_dbt_project(manifest)
    console.print(f"\n[green]Found dbt project:[/green] {project.name}")
    console.print(f"[green]Models:[/green] {len(project.models)}")
    console.print(f"[green]Sources:[/green] {len(project.sources)}")
    console.print(f"[green]Tests:[/green] {len(project.tests)}")

    table = Table(title="Models to Monitor")
    table.add_column("Model", style="cyan")
    table.add_column("Schema", style="green")
    table.add_column("Columns", justify="right")
    table.add_column("Has Tests", justify="center")

    for model in project.models[:20]:
        table.add_row(
            model.name,
            model.schema_name or "-",
            str(len(model.columns)),
            "[green]Yes[/green]" if model.has_tests else "[yellow]No[/yellow]",
        )

    if len(project.models) > 20:
        table.add_row(f"... and {len(project.models) - 20} more", "", "", "")

    console.print(table)
    console.print(f"\nRun [bold]dqmon check[/bold] to run quality checks.")


@app.command()
def check(
    path: Optional[Path] = typer.Argument(None, help="Path to dbt project"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """Run data quality checks on your dbt project."""
    project_path = path or Path.cwd()
    manifest = _find_manifest(project_path)
    if not manifest:
        console.print("[red]No dbt manifest found.[/red] Run dbt compile first.")
        raise typer.Exit(1)

    project = scan_dbt_project(manifest)
    console.print(f"\n[bold]Checking {len(project.models)} models...[/bold]\n")

    results = run_checks(project, verbose=verbose)
    print_report(results, console, verbose=verbose)

    failed = sum(1 for r in results if r.status == "fail")
    warned = sum(1 for r in results if r.status == "warn")
    passed = sum(1 for r in results if r.status == "pass")

    console.print(f"\n[bold]Results:[/bold] {passed} passed, {warned} warnings, {failed} failed")

    if failed > 0:
        raise typer.Exit(1)


@app.command()
def report(
    path: Optional[Path] = typer.Argument(None, help="Path to dbt project"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file (markdown)"),
    fail_on_warnings: bool = typer.Option(
        False,
        "--fail-on-warnings",
        help="Return exit code 1 when any check warns.",
    ),
):
    """Generate a data quality report."""
    project_path = path or Path.cwd()
    manifest = _find_manifest(project_path)
    if not manifest:
        console.print("[red]No dbt manifest found.[/red]")
        raise typer.Exit(1)

    project = scan_dbt_project(manifest)
    results = run_checks(project)

    if output:
        md = _generate_markdown_report(project, results)
        output.write_text(md)
        console.print(f"[green]Report saved to {output}[/green]")
    else:
        print_report(results, console, verbose=True)

    failed = sum(1 for r in results if r.status == "fail")
    warned = sum(1 for r in results if r.status == "warn")
    if failed > 0 or (fail_on_warnings and warned > 0):
        raise typer.Exit(1)


def _find_manifest(project_path: Path) -> Optional[Path]:
    """Search for dbt manifest.json in common locations."""
    candidates = [
        project_path / "target" / "manifest.json",
        project_path / "manifest.json",
        project_path / "dbt_packages" / "target" / "manifest.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _generate_markdown_report(project, results) -> str:
    """Generate markdown quality report."""
    failed = [r for r in results if r.status == "fail"]
    warned = [r for r in results if r.status == "warn"]
    passed = [r for r in results if r.status == "pass"]

    lines = [
        f"# dqmon Quality Report",
        f"",
        f"**Project:** {project.name}",
        f"**Models:** {len(project.models)} | **Sources:** {len(project.sources)}",
        f"**Results:** {len(passed)} passed | {len(warned)} warnings | {len(failed)} failed",
        f"",
    ]

    if failed:
        lines.append("## Failures")
        lines.append("")
        for r in failed:
            lines.append(f"- **{r.check_name}** on `{r.model_name}`: {r.message}")
        lines.append("")

    if warned:
        lines.append("## Warnings")
        lines.append("")
        for r in warned:
            lines.append(f"- **{r.check_name}** on `{r.model_name}`: {r.message}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    app()
