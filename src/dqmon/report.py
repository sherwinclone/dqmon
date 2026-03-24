"""Report formatting for dqmon check results."""

from rich.console import Console
from rich.table import Table

from dqmon.checks import CheckResult


STATUS_ICONS = {
    "pass": "[green]PASS[/green]",
    "warn": "[yellow]WARN[/yellow]",
    "fail": "[red]FAIL[/red]",
}


def print_report(results: list[CheckResult], console: Console, verbose: bool = False):
    """Print formatted check results to console."""
    if not results:
        console.print("[yellow]No checks to report.[/yellow]")
        return

    # Group by status
    fails = [r for r in results if r.status == "fail"]
    warns = [r for r in results if r.status == "warn"]
    passes = [r for r in results if r.status == "pass"]

    # Always show failures
    if fails:
        console.print("\n[red bold]Failures[/red bold]")
        _print_results_table(fails, console, show_details=True)

    # Always show warnings
    if warns:
        console.print("\n[yellow bold]Warnings[/yellow bold]")
        _print_results_table(warns, console, show_details=verbose)

    # Only show passes in verbose mode
    if verbose and passes:
        console.print("\n[green bold]Passed[/green bold]")
        _print_results_table(passes, console, show_details=False)


def _print_results_table(
    results: list[CheckResult], console: Console, show_details: bool = False
):
    """Print a table of check results."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Status", width=6)
    table.add_column("Check", style="cyan")
    table.add_column("Model", style="white")
    table.add_column("Message")

    for r in results:
        table.add_row(
            STATUS_ICONS.get(r.status, r.status),
            r.check_name,
            r.model_name,
            r.message,
        )
        if show_details and r.details:
            table.add_row("", "", "", f"[dim]{r.details}[/dim]")

    console.print(table)
