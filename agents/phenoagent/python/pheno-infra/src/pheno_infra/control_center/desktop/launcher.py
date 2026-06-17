"""Desktop launcher for Pheno Control Center PyQt application.

Provides command-line entry point and setup for running the desktop GUI.
"""

import logging
import sys
from pathlib import Path

try:
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication, QMessageBox

    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

if HAS_PYQT:
    from .main_window import PhenoControlCenterGUI

logger = logging.getLogger(__name__)


def run_desktop_app(config_dir: Path | None = None) -> int:
    """Run the Pheno Control Center desktop application.

    Args:
        config_dir: Optional configuration directory

    Returns:
        Exit code (0 for success)
    """
    if not HAS_PYQT:
        print("PyQt6 is not installed. Please install PyQt6 to use the desktop GUI:")
        print("  pip install PyQt6")
        return 1

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        # Create QApplication
        app = QApplication(sys.argv)
        app.setApplicationName("Pheno Control Center")
        app.setApplicationDisplayName("Pheno Control Center")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("PhenoSDK")
        app.setOrganizationDomain("pheno-sdk.org")

        # Set application icon (if available)
        try:
            icon_path = Path(__file__).parent / "icons" / "app_icon.png"
            if icon_path.exists():
                app.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass  # Ignore icon loading errors

        # Create and show main window
        try:
            main_window = PhenoControlCenterGUI(config_dir)
            main_window.show()

            logger.info("Pheno Control Center desktop application started")

            # Run the application
            return app.exec()

        except Exception as e:
            logger.exception(f"Failed to create main window: {e}")

            # Show error dialog
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Startup Error")
            error_dialog.setText("Failed to start Pheno Control Center")
            error_dialog.setDetailedText(str(e))
            error_dialog.exec()

            return 1

    except Exception as e:
        logger.exception(f"Application startup failed: {e}")
        return 1


def main():
    """
    Main entry point for desktop launcher.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Pheno Control Center Desktop Application")
    parser.add_argument("--config-dir", type=Path, help="Configuration directory path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run the desktop application
    exit_code = run_desktop_app(args.config_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
