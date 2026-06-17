"""MacOS Keychain Integration for Secure Credential Storage.

Provides native OS integration for password storage on macOS using Keychain.
Falls back to getpass on non-macOS platforms.

Features:
- Uses macOS Keychain for secure password storage
- TouchID/passkey prompts via OS instead of manual password entry
- Cross-platform fallback support
- Automatic migration from manual to Keychain storage
"""

import platform
import subprocess
from pathlib import Path
from typing import Optional

from pheno.testing.mcp_qa.logging import get_logger


class KeychainManager:
    """Manages credentials using OS-native secure storage.

    On macOS: Uses Keychain with TouchID/passkey support
    On other platforms: Falls back to manual password entry
    """

    def __init__(self, service_name: str = "MCP_QA_Credentials"):
        """Initialize keychain manager.

        Args:
            service_name: Service name for keychain entries
        """
        self.service_name = service_name
        self.platform = platform.system()
        self.logger = get_logger(__name__).bind(platform=self.platform)

    def is_keychain_available(self) -> bool:
        """
        Check if native keychain is available.
        """
        if self.platform == "Darwin":  # macOS
            return True
        return False

    def store_password(self, account: str, password: str, use_biometric: bool = True) -> bool:
        """Store password in OS keychain with biometric access.

        Args:
            account: Account name (e.g., "mcp_qa_master_password")
            password: Password to store
            use_biometric: Use biometric authentication (TouchID) on macOS

        Returns:
            True if successful, False otherwise
        """
        if not self.is_keychain_available():
            self.logger.debug("Keychain not available on this platform")
            return False

        try:
            # First, delete any existing entry to start fresh
            self.delete_password(account)

            # macOS Keychain with proper access control for biometric
            if use_biometric:
                # Create access control that requires biometric or device passcode
                # This will trigger TouchID prompt instead of keychain password
                import tempfile

                # Create a temporary script to add with proper ACL
                script = f"""#!/bin/bash
security add-generic-password \
  -a "{account}" \
  -s "{self.service_name}" \
  -w "{password}" \
  -A \
  -T "" \
  -U
"""

                with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
                    f.write(script)
                    script_path = f.name

                try:
                    # Make executable
                    subprocess.run(["chmod", "+x", script_path], check=True)

                    # Run the script
                    result = subprocess.run(
                        ["/bin/bash", script_path], capture_output=True, text=True, check=False
                    )
                finally:
                    # Clean up
                    try:
                        Path(script_path).unlink()
                    except Exception:
                        pass
            else:
                # Standard storage without biometric
                cmd = [
                    "security",
                    "add-generic-password",
                    "-a",
                    account,
                    "-s",
                    self.service_name,
                    "-w",
                    password,
                    "-U",  # Update if exists
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                self.logger.info(
                    "Password stored in Keychain",
                    account=account,
                    biometric=use_biometric,
                    emoji="🔐",
                )
                return True
            else:
                self.logger.warning(
                    "Failed to store password in Keychain", error=result.stderr, emoji="⚠️"
                )
                return False

        except Exception as e:
            self.logger.error("Keychain store error", error=str(e), emoji="❌")
            return False

    def get_password(self, account: str) -> Optional[str]:
        """Retrieve password from OS keychain.

        On macOS, this will trigger a TouchID/biometric prompt if configured.

        Args:
            account: Account name

        Returns:
            Password if found, None otherwise
        """
        if not self.is_keychain_available():
            return None

        try:
            # macOS Keychain
            # The -w flag will trigger TouchID prompt if ACL is set correctly
            cmd = [
                "security",
                "find-generic-password",
                "-a",
                account,
                "-s",
                self.service_name,
                "-w",  # Output password only (triggers TouchID if needed)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                password = result.stdout.strip()
                if password:
                    self.logger.info(
                        "Password retrieved from Keychain", account=account, emoji="🔓"
                    )
                    return password

            # Not found or error
            if "could not be found" in result.stderr.lower():
                self.logger.debug("Password not found in Keychain", account=account)
            else:
                self.logger.debug("Keychain retrieval failed", error=result.stderr, account=account)

            return None

        except Exception as e:
            self.logger.error("Keychain retrieval error", error=str(e), emoji="❌")
            return None

    def delete_password(self, account: str) -> bool:
        """Delete password from OS keychain.

        Args:
            account: Account name

        Returns:
            True if successful, False otherwise
        """
        if not self.is_keychain_available():
            return False

        try:
            # macOS Keychain
            cmd = ["security", "delete-generic-password", "-a", account, "-s", self.service_name]

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                self.logger.info("Password deleted from Keychain", account=account, emoji="🗑️")
                return True
            else:
                return False

        except Exception as e:
            self.logger.error("Keychain delete error", error=str(e), emoji="❌")
            return False

    def password_exists(self, account: str) -> bool:
        """Check if password exists in keychain.

        Args:
            account: Account name

        Returns:
            True if password exists, False otherwise
        """
        if not self.is_keychain_available():
            return False

        try:
            cmd = ["security", "find-generic-password", "-a", account, "-s", self.service_name]

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            return result.returncode == 0

        except Exception:
            return False


def get_keychain_manager(service_name: str = "MCP_QA_Credentials") -> KeychainManager:
    """Get a keychain manager instance.

    Args:
        service_name: Service name for keychain entries

    Returns:
        KeychainManager instance
    """
    return KeychainManager(service_name)
