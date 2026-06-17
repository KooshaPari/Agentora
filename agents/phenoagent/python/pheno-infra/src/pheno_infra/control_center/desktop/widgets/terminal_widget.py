"""Terminal Widget Module.

Provides embedded terminal functionality for command execution and output display.
"""

import asyncio
import logging

try:
    from PyQt6.QtCore import QProcess, Qt, pyqtSignal
    from PyQt6.QtGui import QColor, QFont, QTextCursor
    from PyQt6.QtWidgets import (
        QComboBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

logger = logging.getLogger(__name__)


if HAS_PYQT:

    class TerminalWidget(QWidget):
        """
        Embedded terminal widget for command execution.
        """

        command_executed = pyqtSignal(str, int)
        output_received = pyqtSignal(str)
        error_received = pyqtSignal(str)

        def __init__(self, control_center):
            super().__init__()
            self.control_center = control_center
            self._current_process: QProcess | None = None
            self._output_history: list[str] = []
            self._current_directory = None
            self._init_ui()

        def _init_ui(self):
            """
            Initialize the user interface.
            """
            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)

            # Terminal header
            header_layout = QHBoxLayout()

            title_label = QLabel("Terminal")
            title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            header_layout.addWidget(title_label)

            header_layout.addStretch()

            # Current directory display
            self.directory_label = QLabel("/")
            self.directory_label.setStyleSheet("font-family: monospace;")
            header_layout.addWidget(self.directory_label)

            # Clear button
            clear_button = QPushButton("Clear")
            clear_button.setToolTip("Clear terminal output")
            clear_button.clicked.connect(self.clear_output)
            header_layout.addWidget(clear_button)

            layout.addLayout(header_layout)

            # Output display
            self.output_area = QTextEdit()
            self.output_area.setReadOnly(True)
            self.output_area.setFont(QFont("Monospace", 10))
            self.output_area.setStyleSheet("background-color: #1E1E1E; color: #CCCCCC;")
            layout.addWidget(self.output_area)

            # Command input area
            input_layout = QHBoxLayout()

            # Command prompt
            prompt_label = QLabel("$")
            prompt_label.setFixedWidth(15)
            prompt_label.setStyleSheet("color: #00FF00; font-weight: bold;")
            input_layout.addWidget(prompt_label)

            # Command input
            self.command_input = QLineEdit()
            self.command_input.setPlaceholderText("Enter command...")
            self.command_input.returnPressed.connect(self.execute_command)
            self.command_input.setStyleSheet("font-family: monospace;")
            input_layout.addWidget(self.command_input)

            # Shell selector
            self.shell_combo = QComboBox()
            self.shell_combo.addItems(
                ["/bin/bash", "/bin/zsh", "/bin/sh", "cmd.exe", "powershell.exe"],
            )
            self.shell_combo.setCurrentText("/bin/bash")
            self.shell_combo.setFixedWidth(120)
            input_layout.addWidget(self.shell_combo)

            # Execute button
            execute_button = QPushButton("Execute")
            execute_button.setToolTip("Execute command")
            execute_button.clicked.connect(self.execute_command)
            input_layout.addWidget(execute_button)

            layout.addLayout(input_layout)

        def append_output(self, text: str, color: str | None = None):
            """
            Append text to output area with optional color.
            """
            if not hasattr(self, "output_area"):
                return

            cursor = self.output_area.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)

            if color:
                cursor.insertHtml(f'<span style="color: {color};">{text}</span>')
            else:
                cursor.insertText(text)

            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.output_area.setTextCursor(cursor)
            self.output_area.ensureCursorVisible()

            # Keep output history
            self._output_history.append(text)
            if len(self._output_history) > 1000:  # Limit history size
                self._output_history.pop(0)

        def execute_command(self):
            """
            Execute the entered command.
            """
            command = self.command_input.text().strip()
            if not command:
                return

            # Clear input
            self.command_input.clear()

            # Show command
            self.append_output(f"$ {command}\n", "#00FF00")

            try:
                # Execute command using control center's command engine
                # Note: This would need integration with the CLI bridge
                asyncio.create_task(self._execute_async_command(command))

            except Exception as e:
                error_msg = f"Error executing command: {e}\n"
                self.append_output(error_msg, "#FF6B6B")
                self.error_received.emit(error_msg)

        async def _execute_async_command(self, command: str):
            """
            Execute command asynchronously.
            """
            try:
                # Use unified command engine

                if hasattr(self.control_center, "command_engine"):
                    result = await self.control_center.command_engine.execute_command(command)

                    # Display result
                    if result.stdout:
                        self.append_output(result.stdout)
                    if result.stderr:
                        self.append_output(result.stderr, "#FFA500")

                    # Signal completion
                    self.command_executed.emit(command, result.return_code)

                    self.append_output("\n", "#00FF00")
                else:
                    # Fallback: Use simple subprocess

                    shell = self.shell_combo.currentText()

                    if shell.endswith(".exe"):  # Windows
                        full_command = [shell, "/c", command]
                    else:  # Unix
                        full_command = [shell, "-c", command]

                    process = await asyncio.create_subprocess_exec(
                        *full_command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    stdout, stderr = await process.communicate()

                    if stdout:
                        self.append_output(stdout.decode())
                    if stderr:
                        self.append_output(stderr.decode(), "#FFA500")

                    self.command_executed.emit(command, process.returncode)

                    self.append_output("\n", "#00FF00")

            except Exception as e:
                error_msg = f"Async execution error: {e}\n"
                self.append_output(error_msg, "#FF6B6B")
                self.error_received.emit(error_msg)

        def clear_output(self):
            """
            Clear terminal output.
            """
            if hasattr(self, "output_area"):
                self.output_area.clear()
                self._output_history.clear()

        def set_current_directory(self, directory: str):
            """
            Set current working directory.
            """
            self._current_directory = directory
            if hasattr(self, "directory_label"):
                self.directory_label.setText(directory)

        def update_status(self, global_status: Dict[str, Any]):
            """
            Update terminal widget status.
            """
            # Terminal widget doesn't display project status directly
            # but could show command execution status

        def get_command_history(self) -> list[str]:
            """
            Get command execution history.
            """
            # Extract commands from output history
            commands = []
            for line in self._output_history:
                if line.startswith("$ "):
                    commands.append(line[2:].strip())
            return commands

        def set_shell(self, shell_path: str):
            """
            Set the shell to use for command execution.
            """
            if hasattr(self, "shell_combo"):
                self.shell_combo.setCurrentText(shell_path)

else:
    # Fallback when PyQt is not available
    class TerminalWidget:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "PyQt6 is not available. Please install PyQt6 to use the desktop GUI.",
            )
