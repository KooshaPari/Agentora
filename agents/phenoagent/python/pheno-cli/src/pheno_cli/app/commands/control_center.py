#!/usr/bin/env python3
"""CLI entry point for Pheno Control Center.

Provides command-line interface for launching the control center in different modes:
- TUI: Interactive textual user interface
- Desktop: PyQt-based GUI application
- Monitor: Simple rich-based monitoring
- Demo: Demonstration mode

Usage:
    pheno-control-center [MODE] [OPTIONS]

Examples:
    pheno-control-center tui
    pheno-control-center desktop --config-dir ~/.kinfra/custom
    pheno-control-center monitor --debug
    pheno-control-center demo
"""

import asyncio
import logging
import sys
from pathlib import Path


def print_banner():
    """
    Print application banner.
    """
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                           Pheno Control Center                              ║
║                   Multi-Project Orchestration System                        ║
║                                                                              ║
║  Desktop GUI  │  Interactive TUI  │  Monitoring  │  Multi-tenant Support   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_dependencies():
    """
    Check for optional dependencies and provide installation instructions.
    """
    missing_deps = []

    # Check PyQt6 for desktop mode
    try:
        has_pyqt = True
    except ImportError:
        has_pyqt = False
        missing_deps.append(("PyQt6", "Desktop GUI", "pip install PyQt6"))

    # Check textual for enhanced TUI
    try:
        has_textual = True
    except ImportError:
        has_textual = False
        missing_deps.append(("textual", "Enhanced TUI", "pip install textual"))

    # Check rich for monitoring
    try:
        has_rich = True
    except ImportError:
        has_rich = False
        missing_deps.append(("rich", "Rich monitoring", "pip install rich"))

    return {"pyqt": has_pyqt, "textual": has_textual, "rich": has_rich, "missing": missing_deps}


def print_help():
    """
    Print help information.
    """
    help_text = """
Pheno Control Center - Multi-Project Orchestration System

USAGE:
    pheno-control-center [MODE] [OPTIONS]

MODES:
    tui       Interactive textual user interface (default)
    desktop   PyQt-based desktop GUI application
    monitor   Simple rich-based monitoring display
    demo      Demonstration mode showing capabilities

OPTIONS:
    --config-dir PATH    Configuration directory (default: ~/.kinfra/control_center)
    --debug             Enable debug logging
    --help              Show this help message
    --check-deps        Check optional dependencies
    --version           Show version information

EXAMPLES:
    pheno-control-center tui
    pheno-control-center desktop
    pheno-control-center monitor --debug
    pheno-control-center demo --config-dir /custom/path
    pheno-control-center --check-deps

FEATURES:
    • Project launcher with start/stop controls
    • Real-time monitoring and status display
    • Integrated terminal for command execution
    • Multi-tenant infrastructure management
    • System tray integration (desktop mode)
    • Configurable project registry
    • Plugin architecture for extensibility

REQUIREMENTS:
    Core: Python 3.8+, asyncio, pyyaml
    Desktop: PyQt6
    TUI: textual, rich
    Monitoring: psutil (optional)
"""
    print(help_text)


def main():
    """
    Main CLI entry point.
    """
    import argparse

    # Custom argument parser to handle --help before importing heavy modules
    if len(sys.argv) > 1:
        if sys.argv[1] in ["--help", "-h", "help"]:
            print_help()
            sys.exit(0)
        elif sys.argv[1] == "--version":
            print("Pheno Control Center v1.0.0")
            print("Part of the Pheno SDK - Building the future of development tools")
            sys.exit(0)
        elif sys.argv[1] == "--check-deps":
            print_banner()
            print("Checking dependencies...\n")
            deps = check_dependencies()

            print("✅ Available features:")
            if deps["pyqt"]:
                print("  • Desktop GUI (PyQt6)")
            if deps["textual"]:
                print("  • Enhanced TUI (textual)")
            if deps["rich"]:
                print("  • Rich monitoring displays")

            if deps["missing"]:
                print("\n⚠️  Missing optional dependencies:")
                for dep, feature, install_cmd in deps["missing"]:
                    print(f"  • {dep} - for {feature}")
                    print(f"    Install with: {install_cmd}")
            else:
                print("\n🎉 All optional dependencies are available!")

            sys.exit(0)

    # Print banner for interactive modes
    if not sys.argv[1:] or (len(sys.argv) > 1 and sys.argv[1] not in ["demo"]):
        print_banner()

    # Check for basic availability
    deps = check_dependencies()

    # Setup argument parser
    parser = argparse.ArgumentParser(
        description="Pheno Control Center - Multi-project orchestration system",
        add_help=False,  # We handle help ourselves
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="tui",
        choices=["tui", "monitor", "desktop", "demo"],
        help="Mode to run",
    )
    parser.add_argument("--config-dir", type=Path, help="Configuration directory path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    try:
        args = parser.parse_args()
    except SystemExit:
        print_help()
        sys.exit(1)

    mode = args.mode
    config_dir = args.config_dir
    debug = args.debug

    # Validate mode availability
    if mode == "desktop" and not deps["pyqt"]:
        print("❌ Desktop mode requires PyQt6")
        print("Install with: pip install PyQt6")
        sys.exit(1)

    if mode == "tui" and not deps["textual"] and not deps["rich"]:
        print("❌ TUI mode requires either textual or rich")
        print("Install with: pip install textual rich")
        sys.exit(1)

    # Setup logging for non-desktop modes
    if mode != "desktop":
        log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    # Import and run the main application
    try:
        # Import here to avoid loading heavy modules unnecessarily
        from .main import main as async_main
        from .main import run_desktop_gui

        if mode == "desktop":
            # Desktop mode runs synchronously with Qt event loop
            exit_code = run_desktop_gui(config_dir)
            sys.exit(exit_code)
        else:
            # All other modes run asynchronously
            sys.argv = (
                [sys.argv[0], mode]
                + (["--config-dir", str(config_dir)] if config_dir else [])
                + (["--debug"] if debug else [])
            )
            asyncio.run(async_main())

    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
        sys.exit(0)
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required dependencies are installed.")
        sys.exit(1)
    except Exception as e:
        if debug:
            import traceback

            traceback.print_exc()
        else:
            print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
