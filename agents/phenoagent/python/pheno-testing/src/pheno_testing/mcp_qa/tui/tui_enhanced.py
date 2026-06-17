"""
Enhanced TUI for TDD Testing with Session-Scoped OAuth

This integrates the existing TUI with the new TDD session OAuth system:
- Shows OAuth status from session broker
- Real-time test execution with session credentials
- Individual tool testing interface
- Same rich UX as before, but with faster auth
"""

import asyncio
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from rich.align import Align
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from .auth_session import AuthCredentials, AuthSessionBroker
from .oauth_progress import OAuthProgressFlow


class TDDTestDashboard:
    """Enhanced test dashboard with session OAuth integration."""

    def __init__(self, auth_broker: AuthSessionBroker):
        self.auth_broker = auth_broker
        self.console = Console() if HAS_RICH else None
        self.credentials: Optional[AuthCredentials] = None
        self.test_results = []
        self.running_tests = False

    async def setup_and_run(self):
        """Setup OAuth and run the dashboard."""
        if not self.console:
            print("Rich not available - falling back to basic mode")
            return

        # Setup OAuth session
        await self.setup_oauth_session()

        # Run dashboard
        await self.run_dashboard()

    async def setup_oauth_session(self):
        """Setup session OAuth with rich progress display."""
        layout = Layout()

        # Create OAuth status panel
        oauth_panel = Panel(
            "[bold blue]🔐 Setting up Session-Scoped OAuth...[/bold blue]",
            title="Authentication",
            border_style="blue"
        )

        with Live(oauth_panel, console=self.console, refresh_per_second=4) as live:
            try:
                with OAuthProgressFlow() as progress:
                    progress.step("Checking cached credentials...")
                    live.update(Panel(
                        "[yellow]⏳ Checking cached credentials...[/yellow]",
                        title="Authentication",
                        border_style="yellow"
                    ))

                    self.credentials = await self.auth_broker.get_authenticated_credentials(
                        provider="authkit",
                        force_refresh=False
                    )

                    if self.credentials.is_valid():
                        progress.complete("OAuth session ready - using cached credentials")
                        live.update(Panel(
                            f"[green]✅ OAuth credentials cached until {self.credentials.expires_at}[/green]",
                            title="Authentication",
                            border_style="green"
                        ))
                    else:
                        progress.step("Performing fresh OAuth authentication...")
                        live.update(Panel(
                            "[yellow]🔑 Performing fresh OAuth authentication...[/yellow]",
                            title="Authentication",
                            border_style="yellow"
                        ))

                        self.credentials = await self.auth_broker.get_authenticated_credentials(
                            provider="authkit",
                            force_refresh=True
                        )

                        progress.complete("OAuth authentication complete")
                        live.update(Panel(
                            "[green]✅ Fresh OAuth credentials acquired[/green]",
                            title="Authentication",
                            border_style="green"
                        ))

                # Brief pause to show success
                await asyncio.sleep(1)

            except Exception as e:
                live.update(Panel(
                    f"[red]❌ OAuth setup failed: {e}[/red]",
                    title="Authentication Error",
                    border_style="red"
                ))
                await asyncio.sleep(2)
                raise

    async def run_dashboard(self):
        """Run the main test dashboard."""
        if not self.credentials:
            self.console.print("[red]❌ No OAuth credentials available[/red]")
            return

        while True:
            # Clear screen and show dashboard
            self.console.clear()

            # Create dashboard layout
            dashboard = self.create_dashboard_layout()
            self.console.print(dashboard)

            # Show menu options
            self.console.print("\n[bold cyan]Test Options:[/bold cyan]")
            self.console.print("[1] Run all tests")
            self.console.print("[2] Run unit tests only")
            self.console.print("[3] Run integration tests only")
            self.console.print("[4] Test specific tool")
            self.console.print("[5] Run custom filter")
            self.console.print("[6] Show OAuth status")
            self.console.print("[q] Quit")

            # Get user choice
            choice = input("\n👉 Choose option: ").strip().lower()

            if choice == 'q':
                break
            elif choice == '1':
                await self.run_all_tests()
            elif choice == '2':
                await self.run_unit_tests()
            elif choice == '3':
                await self.run_integration_tests()
            elif choice == '4':
                await self.test_specific_tool()
            elif choice == '5':
                await self.run_custom_filter()
            elif choice == '6':
                await self.show_oauth_status()
            else:
                self.console.print("[red]Invalid option. Press Enter to continue.[/red]")
                input()\n    \n    def create_dashboard_layout(self) -> Panel:\n        \"\"\"Create the main dashboard layout.\"\"\"\n        # OAuth Status Section\n        oauth_status = self.get_oauth_status_display()\n        \n        # Test Results Section\n        test_results = self.get_test_results_display()\n        \n        # Combine sections\n        content = f\"\"\"{oauth_status}\n\n{test_results}\"\"\"\n        \n        return Panel(\n            content,\n            title=\"[bold green]🧪 TDD Test Dashboard with Session OAuth[/bold green]\",\n            border_style=\"green\"\n        )\n    \n    def get_oauth_status_display(self) -> str:\n        \"\"\"Get OAuth status display string.\"\"\"\n        if not self.credentials:\n            return \"[red]❌ No OAuth credentials[/red]\"\n        \n        status_color = \"green\" if self.credentials.is_valid() else \"red\"\n        status_icon = \"✅\" if self.credentials.is_valid() else \"❌\"\n        \n        return f\"\"\"[bold]{status_icon} OAuth Status[/bold]\nProvider: [{status_color}]{self.credentials.provider}[/{status_color}]\nExpires: [{status_color}]{self.credentials.expires_at}[/{status_color}]\nUser ID: [cyan]{self.credentials.user_id or 'Unknown'}[/cyan]\"\"\"\n    \n    def get_test_results_display(self) -> str:\n        \"\"\"Get test results display string.\"\"\"\n        if not self.test_results:\n            return \"[dim]No tests run yet[/dim]\"\n        \n        # Show last few test results\n        recent_results = self.test_results[-5:]\n        result_lines = []\n        \n        for result in recent_results:\n            status_icon = \"✅\" if result.get(\"passed\", False) else \"❌\"\n            test_name = result.get(\"name\", \"Unknown\")\n            duration = result.get(\"duration\", 0)\n            result_lines.append(f\"{status_icon} {test_name} ({duration:.2f}s)\")\n        \n        return \"\\n\".join([\"[bold]📊 Recent Test Results[/bold]\"] + result_lines)\n    \n    async def run_all_tests(self):\n        \"\"\"Run all tests with progress display.\"\"\"\n        await self.run_pytest_with_progress([\"tests/\", \"-v\"], \"Running all tests...\")\n    \n    async def run_unit_tests(self):\n        \"\"\"Run unit tests only.\"\"\"\n        await self.run_pytest_with_progress(\n            [\"tests/unit/\", \"-m\", \"unit\", \"-v\"], \n            \"Running unit tests...\"\n        )\n    \n    async def run_integration_tests(self):\n        \"\"\"Run integration tests only.\"\"\"\n        await self.run_pytest_with_progress(\n            [\"tests/integration/\", \"-m\", \"integration\", \"-v\"],\n            \"Running integration tests...\"\n        )\n    \n    async def test_specific_tool(self):\n        \"\"\"Test a specific tool.\"\"\"\n        tool_name = input(\"\\n🔧 Enter tool name (e.g., workspace, entity): \").strip()\n        if not tool_name:\n            return\n        \n        test_paths = [\n            f\"tests/unit/tools/test_{tool_name}_tool.py\",\n            f\"tests/integration/test_{tool_name}_integration.py\"\n        ]\n        \n        existing_paths = [p for p in test_paths if Path(p).exists()]\n        \n        if not existing_paths:\n            self.console.print(f\"[red]❌ No tests found for tool: {tool_name}[/red]\")\n            input(\"Press Enter to continue...\")\n            return\n        \n        await self.run_pytest_with_progress(\n            existing_paths + [\"-v\"],\n            f\"Testing {tool_name} tool...\"\n        )\n    \n    async def run_custom_filter(self):\n        \"\"\"Run tests with custom filter.\"\"\"\n        filter_expr = input(\"\\n🔍 Enter test filter (pytest -k expression): \").strip()\n        if not filter_expr:\n            return\n        \n        await self.run_pytest_with_progress(\n            [\"tests/\", \"-k\", filter_expr, \"-v\"],\n            f\"Running tests matching: {filter_expr}\"\n        )\n    \n    async def show_oauth_status(self):\n        \"\"\"Show detailed OAuth status.\"\"\"\n        if not self.credentials:\n            self.console.print(\"[red]❌ No OAuth credentials available[/red]\")\n            return\n        \n        # Refresh credentials status\n        await self.auth_broker._load_cached_credentials()\n        \n        status_table = Table(title=\"OAuth Credential Details\")\n        status_table.add_column(\"Property\", style=\"cyan\")\n        status_table.add_column(\"Value\", style=\"green\")\n        \n        status_table.add_row(\"Provider\", self.credentials.provider)\n        status_table.add_row(\"Token (last 8 chars)\", f\"...{self.credentials.access_token[-8:]}\")\n        status_table.add_row(\"Valid\", \"✅ Yes\" if self.credentials.is_valid() else \"❌ No\")\n        status_table.add_row(\"Expires At\", str(self.credentials.expires_at))\n        status_table.add_row(\"Base URL\", self.credentials.base_url)\n        status_table.add_row(\"User ID\", self.credentials.user_id or \"Unknown\")\n        \n        self.console.print(status_table)\n        input(\"\\nPress Enter to continue...\")\n    \n    async def run_pytest_with_progress(self, pytest_args: List[str], description: str):\n        \"\"\"Run pytest with rich progress display.\"\"\"\n        cmd = [\"python\", \"-m\", \"pytest\"] + pytest_args\n        \n        self.console.print(f\"\\n[bold green]{description}[/bold green]\")\n        self.console.print(f\"Command: [cyan]{' '.join(cmd)}[/cyan]\\n\")\n        \n        with Progress(\n            SpinnerColumn(),\n            TextColumn(\"[progress.description]{task.description}\"),\n            BarColumn(),\n            TimeElapsedColumn(),\n            console=self.console\n        ) as progress:\n            task = progress.add_task(description, total=None)\n            \n            # Run pytest\n            process = await asyncio.create_subprocess_exec(\n                *cmd,\n                stdout=asyncio.subprocess.PIPE,\n                stderr=asyncio.subprocess.STDOUT,\n                cwd=Path(__file__).parent.parent.parent\n            )\n            \n            output_lines = []\n            while True:\n                line = await process.stdout.readline()\n                if not line:\n                    break\n                \n                line_str = line.decode().strip()\n                if line_str:\n                    output_lines.append(line_str)\n                    # Update progress with current test\n                    if \"::\" in line_str and (\"PASSED\" in line_str or \"FAILED\" in line_str):\n                        test_name = line_str.split(\"::\")[1].split(\" \")[0]\n                        progress.update(task, description=f\"Running: {test_name}\")\n            \n            await process.wait()\n            \n            # Show results\n            success = process.returncode == 0\n            result_color = \"green\" if success else \"red\"\n            result_icon = \"✅\" if success else \"❌\"\n            \n            progress.update(task, description=f\"{result_icon} {'Passed' if success else 'Failed'}\")\n            \n            # Store result\n            self.test_results.append({\n                \"name\": description,\n                \"passed\": success,\n                \"duration\": 0,  # Could calculate from timestamps\n                \"timestamp\": datetime.now()\n            })\n        \n        # Show summary\n        self.console.print(f\"\\n[{result_color}]{result_icon} Test run {'completed successfully' if success else 'failed'}[/{result_color}]\")\n        \n        # Show last few lines of output\n        if output_lines:\n            self.console.print(\"\\n[bold]Last few lines of output:[/bold]\")\n            for line in output_lines[-10:]:\n                self.console.print(f\"  {line}\")\n        \n        input(\"\\nPress Enter to continue...\")\n\n\nasync def run_tdd_dashboard(auth_broker: AuthSessionBroker):\n    \"\"\"Run the TDD test dashboard.\"\"\"\n    dashboard = TDDTestDashboard(auth_broker)\n    await dashboard.setup_and_run()
