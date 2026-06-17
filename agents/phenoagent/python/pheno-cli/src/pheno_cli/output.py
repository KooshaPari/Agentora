"""
CLI Output Formatting Utilities

Provides utilities for formatting CLI output including tables, JSON,
progress indicators, and colored output.
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree


class OutputFormatter:
    """
    Formats output for CLI display.

    Supports:
    - JSON output
    - Tables
    - Trees
    - Syntax highlighting
    - Progress indicators
    """

    def __init__(self, console: Console | None = None) -> None:
        """
        Initialize output formatter.

        Args:
            console: Rich console instance (creates new if not provided)
        """
        self.console = console or Console()

    def format_json(self, data: Any, pretty: bool = True) -> str:
        """
        Format data as JSON.

        Args:
            data: Data to format
            pretty: Pretty-print JSON

        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)

    def print_json(self, data: Any, pretty: bool = True) -> None:
        """
        Print data as JSON with syntax highlighting.

        Args:
            data: Data to print
            pretty: Pretty-print JSON
        """
        json_str = self.format_json(data, pretty)
        syntax = Syntax(json_str, "json", theme="monokai")
        self.console.print(syntax)

    def create_table(
        self,
        title: str | None = None,
        columns: list[str | dict[str, Any]] | None = None,
        rows: list[list[Any]] | None = None,
        show_header: bool = True,
        show_lines: bool = False,
    ) -> Table:
        """
        Create a Rich table.

        Args:
            title: Table title
            columns: Column definitions (names or dicts with style)
            rows: Table rows
            show_header: Show table header
            show_lines: Show row lines

        Returns:
            Rich Table instance

        Example:
            table = formatter.create_table(
                title="Entities",
                columns=[
                    {"name": "ID", "style": "cyan"},
                    {"name": "Name", "style": "magenta"},
                    "Status"
                ],
                rows=[
                    ["e1", "Entity 1", "active"],
                    ["e2", "Entity 2", "inactive"]
                ]
            )
            formatter.console.print(table)
        """
        table = Table(title=title, show_header=show_header, show_lines=show_lines)

        # Add columns
        if columns:
            for col in columns:
                if isinstance(col, dict):
                    table.add_column(col.get("name", ""), style=col.get("style"))
                else:
                    table.add_column(str(col))

        # Add rows
        if rows:
            for row in rows:
                table.add_row(*[str(cell) for cell in row])

        return table

    def print_table(
        self,
        title: str | None = None,
        columns: list[str | dict[str, Any]] | None = None,
        rows: list[list[Any]] | None = None,
        show_header: bool = True,
        show_lines: bool = False,
    ) -> None:
        """
        Print a table.

        Args:
            title: Table title
            columns: Column definitions
            rows: Table rows
            show_header: Show table header
            show_lines: Show row lines
        """
        table = self.create_table(title, columns, rows, show_header, show_lines)
        self.console.print(table)

    def create_tree(self, label: str) -> Tree:
        """
        Create a Rich tree for hierarchical data.

        Args:
            label: Root label

        Returns:
            Rich Tree instance

        Example:
            tree = formatter.create_tree("Project")
            entities = tree.add("Entities")
            entities.add("Entity 1")
            entities.add("Entity 2")
            formatter.console.print(tree)
        """
        return Tree(label)

    def print_tree(self, tree: Tree) -> None:
        """
        Print a tree.

        Args:
            tree: Tree to print
        """
        self.console.print(tree)

    def create_panel(
        self,
        content: str,
        title: str | None = None,
        border_style: str = "blue",
    ) -> Panel:
        """
        Create a Rich panel.

        Args:
            content: Panel content
            title: Panel title
            border_style: Border style

        Returns:
            Rich Panel instance
        """
        return Panel(content, title=title, border_style=border_style)

    def print_panel(
        self,
        content: str,
        title: str | None = None,
        border_style: str = "blue",
    ) -> None:
        """
        Print a panel.

        Args:
            content: Panel content
            title: Panel title
            border_style: Border style
        """
        panel = self.create_panel(content, title, border_style)
        self.console.print(panel)

    def print_success(self, message: str) -> None:
        """
        Print success message.

        Args:
            message: Success message
        """
        self.console.print(f"[bold green]✓[/bold green] {message}")

    def print_error(self, message: str) -> None:
        """
        Print error message.

        Args:
            message: Error message
        """
        self.console.print(f"[bold red]✗[/bold red] {message}")

    def print_warning(self, message: str) -> None:
        """
        Print warning message.

        Args:
            message: Warning message
        """
        self.console.print(f"[bold yellow]⚠[/bold yellow] {message}")

    def print_info(self, message: str) -> None:
        """
        Print info message.

        Args:
            message: Info message
        """
        self.console.print(f"[cyan]ℹ[/cyan] {message}")

    def create_progress(
        self,
        spinner: bool = True,
        bar: bool = False,
    ) -> Progress:
        """
        Create a progress indicator.

        Args:
            spinner: Show spinner
            bar: Show progress bar

        Returns:
            Rich Progress instance

        Example:
            with formatter.create_progress() as progress:
                task = progress.add_task("Processing...", total=100)
                for i in range(100):
                    progress.update(task, advance=1)
        """
        columns = []
        if spinner:
            columns.append(SpinnerColumn())
        columns.append(TextColumn("[progress.description]{task.description}"))
        if bar:
            columns.append(BarColumn())

        return Progress(*columns, console=self.console)


class TableBuilder:
    """
    Builder pattern for creating tables more easily.

    Example:
        table = (TableBuilder("Users")
            .add_column("ID", style="cyan")
            .add_column("Name", style="magenta")
            .add_column("Email")
            .add_row("1", "John", "john@example.com")
            .add_row("2", "Jane", "jane@example.com")
            .build())
    """

    def __init__(self, title: str | None = None, show_lines: bool = False) -> None:
        """
        Initialize table builder.

        Args:
            title: Table title
            show_lines: Show row lines
        """
        self.title = title
        self.show_lines = show_lines
        self._columns: list[tuple[str, str | None]] = []
        self._rows: list[list[str]] = []

    def add_column(self, name: str, style: str | None = None) -> TableBuilder:
        """
        Add a column.

        Args:
            name: Column name
            style: Column style

        Returns:
            Self for chaining
        """
        self._columns.append((name, style))
        return self

    def add_row(self, *cells: Any) -> TableBuilder:
        """
        Add a row.

        Args:
            *cells: Cell values

        Returns:
            Self for chaining
        """
        self._rows.append([str(cell) for cell in cells])
        return self

    def build(self) -> Table:
        """
        Build the table.

        Returns:
            Rich Table instance
        """
        table = Table(title=self.title, show_lines=self.show_lines)

        for name, style in self._columns:
            table.add_column(name, style=style)

        for row in self._rows:
            table.add_row(*row)

        return table


def format_dict_as_table(data: dict[str, Any], title: str | None = None) -> Table:
    """
    Format dictionary as a two-column table (key-value).

    Args:
        data: Dictionary to format
        title: Table title

    Returns:
        Rich Table instance

    Example:
        table = format_dict_as_table({
            "ID": "e123",
            "Name": "Entity 1",
            "Status": "active"
        }, "Entity Details")
    """
    table = Table(title=title, show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="magenta")

    for key, value in data.items():
        table.add_row(str(key), str(value))

    return table


def format_list_as_table(
    data: list[dict[str, Any]],
    columns: list[str] | None = None,
    title: str | None = None,
) -> Table:
    """
    Format list of dictionaries as a table.

    Args:
        data: List of dictionaries
        columns: Column names (uses all keys if not specified)
        title: Table title

    Returns:
        Rich Table instance

    Example:
        table = format_list_as_table([
            {"id": "e1", "name": "Entity 1"},
            {"id": "e2", "name": "Entity 2"}
        ], columns=["id", "name"], title="Entities")
    """
    if not data:
        return Table(title=title)

    # Determine columns
    if columns is None:
        columns = list(data[0].keys())

    # Create table
    table = Table(title=title)
    for col in columns:
        table.add_column(col.title())

    # Add rows
    for item in data:
        table.add_row(*[str(item.get(col, "")) for col in columns])

    return table


__all__ = [
    "OutputFormatter",
    "TableBuilder",
    "format_dict_as_table",
    "format_list_as_table",
]
