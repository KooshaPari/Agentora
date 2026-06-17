"""Interactive Credential Manager with Auto Environment Setup.

Handles missing credentials by prompting user and auto-updating .env file. Includes
stubs for future MFA/VM simulator integration.
"""

import asyncio
import getpass
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# For future MFA integration
try:
    import pyotp

    HAS_TOTP = True
except ImportError:
    HAS_TOTP = False


class InteractiveCredentialManager:
    """Manages OAuth credentials with interactive setup and environment auto-update.

    Features:
    - Auto-detects missing credentials
    - Prompts user interactively
    - Updates .env file automatically
    - Handles multiple credential formats
    - Stubs for future MFA/VM simulator integration
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.env_file = self.project_root / ".env"
        self.backup_env = self.project_root / ".env.backup"

        # Credential mappings for different providers
        self.credential_mappings = {
            "authkit": {
                "email": ["OAUTH_AUTHKIT_EMAIL", "OAUTH_EMAIL", "ZEN_TEST_EMAIL", "TEST_EMAIL"],
                "password": [
                    "OAUTH_AUTHKIT_PASSWORD",
                    "OAUTH_PASSWORD",
                    "ZEN_TEST_PASSWORD",
                    "TEST_PASSWORD",
                ],
                "mfa_secret": ["OAUTH_AUTHKIT_MFA_SECRET", "MFA_SECRET", "TOTP_SECRET"],
            },
            "github": {
                "username": ["GITHUB_USERNAME", "OAUTH_GITHUB_USERNAME"],
                "password": ["GITHUB_PASSWORD", "OAUTH_GITHUB_PASSWORD", "GITHUB_TOKEN"],
                "mfa_secret": ["GITHUB_MFA_SECRET", "GITHUB_TOTP_SECRET"],
            },
            "google": {
                "email": ["GOOGLE_EMAIL", "OAUTH_GOOGLE_EMAIL"],
                "password": ["GOOGLE_PASSWORD", "OAUTH_GOOGLE_PASSWORD"],
                "mfa_secret": ["GOOGLE_MFA_SECRET", "GOOGLE_TOTP_SECRET"],
            },
        }

        # Future VM/simulator stubs
        self.vm_simulators = {
            "sms_receiver": None,  # Future: VM with SMS capability
            "phone_simulator": None,  # Future: Phone number simulator
            "biometric_simulator": None,  # Future: Biometric auth simulator
        }

    async def ensure_credentials(self, provider: str, required_creds: List[str]) -> Dict[str, str]:
        """Ensure all required credentials are available for provider.

        Interactively prompts and updates .env if missing.
        """
        print(f"\n🔐 Checking credentials for provider: {provider}")

        missing_creds = []
        available_creds = {}

        # Check which credentials are missing
        for cred_name in required_creds:
            value = self._get_credential(provider, cred_name)
            if value:
                available_creds[cred_name] = value
                print(f"   ✅ {cred_name}: Found")
            else:
                missing_creds.append(cred_name)
                print(f"   ❌ {cred_name}: Missing")

        # If any credentials are missing, prompt interactively
        if missing_creds:
            print(f"\n📝 Missing credentials detected for {provider}")
            print(f"   Required: {', '.join(required_creds)}")
            print(f"   Missing: {', '.join(missing_creds)}")

            # Prompt user
            collected_creds = await self._prompt_for_credentials(provider, missing_creds)

            # Update .env file
            if collected_creds:
                await self._update_env_file(provider, collected_creds)
                available_creds.update(collected_creds)

        # Validate we have everything
        for cred_name in required_creds:
            if cred_name not in available_creds:
                raise RuntimeError(
                    f"Failed to obtain credential '{cred_name}' for provider '{provider}'"
                )

        print(f"   ✅ All credentials ready for {provider}\n")
        return available_creds

    def _get_credential(self, provider: str, cred_name: str) -> Optional[str]:
        """
        Get credential from environment using multiple possible variable names.
        """

        # Get possible environment variable names for this credential
        if provider in self.credential_mappings:
            possible_vars = self.credential_mappings[provider].get(cred_name, [])
        else:
            # Fallback patterns
            possible_vars = [
                f"OAUTH_{provider.upper()}_{cred_name.upper()}",
                f"{provider.upper()}_{cred_name.upper()}",
                f"OAUTH_{cred_name.upper()}",
                f"ZEN_TEST_{cred_name.upper()}",
                f"TEST_{cred_name.upper()}",
            ]

        # Try each possible variable name
        for var_name in possible_vars:
            value = os.getenv(var_name)
            if value:
                return value

        return None

    async def _prompt_for_credentials(
        self, provider: str, missing_creds: List[str]
    ) -> Dict[str, str]:
        """
        Interactively prompt user for missing credentials.
        """

        print(f"\n🤔 I need to collect some credentials for {provider} OAuth.")
        print("   This will be saved to your .env file for future use.")

        # Ask for user consent
        consent = (
            input(f"\n   Would you like to set up {provider} credentials now? (y/n): ")
            .lower()
            .strip()
        )
        if consent not in ["y", "yes"]:
            print(f"   ⚠️ Skipping credential setup. Tests requiring {provider} will fail.")
            return {}

        collected = {}

        for cred_name in missing_creds:
            # Special handling for different credential types
            if cred_name in ["password", "token", "secret"]:
                # Secure input for passwords
                value = getpass.getpass(f"\n   Enter {provider} {cred_name}: ")
            elif cred_name == "mfa_secret":
                # Special handling for MFA secrets
                value = await self._prompt_for_mfa_secret(provider)
            else:
                # Regular input for non-sensitive data
                value = input(f"\n   Enter {provider} {cred_name}: ").strip()

            if value:
                collected[cred_name] = value
                print(f"   ✅ Got {cred_name}")
            else:
                print(f"   ⚠️ Skipped {cred_name}")

        return collected

    async def _prompt_for_mfa_secret(self, provider: str) -> Optional[str]:
        """
        Special handling for MFA/TOTP secrets with future VM integration.
        """

        print(f"\n🔐 MFA/TOTP Setup for {provider}")
        print("   This is optional but recommended for automated testing.")

        if not HAS_TOTP:
            print("   ⚠️ pyotp not available. Install with: pip install pyotp")
            return None

        # Future: Integrate with VM simulators for automated MFA
        if self.vm_simulators.get("sms_receiver"):
            print("   🤖 SMS Receiver VM detected - can automate SMS-based MFA")

        if self.vm_simulators.get("phone_simulator"):
            print("   📱 Phone Simulator detected - can handle phone-based auth")

        setup_type = input(
            "\n   MFA Setup Type:\n"
            + "   1) TOTP Secret (recommended)\n"
            + "   2) Skip MFA (manual entry during tests)\n"
            + "   3) Future: SMS Simulator (not implemented)\n"
            + "   Choose (1-3): "
        ).strip()

        if setup_type == "1":
            print("\n   📱 TOTP Secret Setup:")
            print(f"   • Go to {provider} security settings")
            print("   • Enable 2FA/TOTP")
            print("   • Scan QR code with authenticator app")
            print("   • Enter the secret key shown (not the 6-digit code)")

            secret = getpass.getpass("\n   Enter TOTP secret key: ").strip()

            if secret:
                # Validate TOTP secret
                try:
                    totp = pyotp.TOTP(secret)
                    current_code = totp.now()
                    print(f"   🔍 Current TOTP code: {current_code}")

                    verify = (
                        input("   Does this match your authenticator app? (y/n): ").lower().strip()
                    )
                    if verify in ["y", "yes"]:
                        print("   ✅ TOTP secret validated")
                        return secret
                    else:
                        print("   ❌ TOTP secret validation failed")
                        return None
                except Exception as e:
                    print(f"   ❌ Invalid TOTP secret: {e}")
                    return None

        elif setup_type == "3":
            # Future: SMS Simulator integration
            print("   🚧 SMS Simulator not yet implemented")
            print("   📋 Future features:")
            print("   • Virtual phone numbers for SMS MFA")
            print("   • Automated SMS code extraction")
            print("   • Integration with testing VMs")
            return None

        print("   ⚠️ Skipping MFA setup - will require manual entry during tests")
        return None

    async def _update_env_file(self, provider: str, credentials: Dict[str, str]):
        """
        Update .env file with new credentials.
        """

        print("   📝 Updating .env file...")

        # Create backup
        if self.env_file.exists():
            content = self.env_file.read_text()
            self.backup_env.write_text(content)
            print(f"   💾 Backup created: {self.backup_env}")

        # Read existing .env content
        env_content = []
        if self.env_file.exists():
            env_content = self.env_file.read_text().splitlines()

        # Add new credentials
        for cred_name, value in credentials.items():
            # Choose the primary environment variable name
            if provider in self.credential_mappings:
                var_names = self.credential_mappings[provider].get(cred_name, [])
                env_var = (
                    var_names[0] if var_names else f"OAUTH_{provider.upper()}_{cred_name.upper()}"
                )
            else:
                env_var = f"OAUTH_{provider.upper()}_{cred_name.upper()}"

            # Remove existing lines with this variable
            env_content = [line for line in env_content if not line.startswith(f"{env_var}=")]

            # Add new line
            env_content.append(f"{env_var}={value}")
            print(f"   ➕ Added {env_var}=***")

        # Write updated .env file
        self.env_file.write_text("\n".join(env_content) + "\n")
        print("   ✅ .env file updated")

        # Reload environment variables
        self._reload_env()

    def _reload_env(self):
        """
        Reload environment variables from .env file.
        """
        if not self.env_file.exists():
            return

        for line in self.env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

    async def setup_mfa_automation(self, provider: str) -> Optional[Dict[str, Any]]:
        """Set up MFA automation for provider.

        Future: Will integrate with VM simulators for automated MFA handling.
        """

        print(f"\n🤖 MFA Automation Setup for {provider}")

        # Check if we have TOTP secret
        totp_secret = self._get_credential(provider, "mfa_secret")

        if totp_secret and HAS_TOTP:
            print("   ✅ TOTP secret found - automated MFA available")

            def get_totp_code():
                totp = pyotp.TOTP(totp_secret)
                return totp.now()

            return {
                "type": "totp",
                "get_code": get_totp_code,
                "secret": totp_secret,
            }

        # Future VM simulator integrations
        mfa_config = {}

        # SMS Receiver VM (future)
        if self.vm_simulators.get("sms_receiver"):
            print("   📱 SMS Receiver VM available for automated SMS MFA")
            mfa_config["sms_automation"] = True

        # Phone Simulator (future)
        if self.vm_simulators.get("phone_simulator"):
            print("   ☎️ Phone Simulator available for call-based MFA")
            mfa_config["phone_automation"] = True

        # Biometric Simulator (future)
        if self.vm_simulators.get("biometric_simulator"):
            print("   👆 Biometric Simulator available for fingerprint/face auth")
            mfa_config["biometric_automation"] = True

        if mfa_config:
            return {"type": "vm_simulator", "config": mfa_config}

        print("   ⚠️ No MFA automation available - will require manual entry")
        return None

    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get debug information about credential setup.
        """

        return {
            "env_file": str(self.env_file),
            "env_exists": self.env_file.exists(),
            "backup_exists": self.backup_env.exists(),
            "available_providers": list(self.credential_mappings.keys()),
            "vm_simulators": {
                name: status is not None for name, status in self.vm_simulators.items()
            },
            "has_totp": HAS_TOTP,
        }


# Global instance
_credential_manager: Optional[InteractiveCredentialManager] = None


def get_credential_manager() -> InteractiveCredentialManager:
    """
    Get global credential manager instance.
    """
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = InteractiveCredentialManager()
    return _credential_manager


async def ensure_oauth_credentials(provider: str, required_creds: List[str]) -> Dict[str, str]:
    """Convenience function to ensure OAuth credentials are available.

    Usage:
        credentials = await ensure_oauth_credentials("authkit", ["email", "password"])
    """
    manager = get_credential_manager()
    return await manager.ensure_credentials(provider, required_creds)


def interactive_credential_setup():
    """
    CLI tool for interactive credential setup.
    """

    print("🔐 Interactive OAuth Credential Setup")
    print("=====================================")

    manager = get_credential_manager()
    debug_info = manager.get_debug_info()

    print("\nEnvironment:")
    print(f"• .env file: {debug_info['env_file']}")
    print(f"• Exists: {debug_info['env_exists']}")
    print(f"• TOTP support: {debug_info['has_totp']}")

    print(f"\nAvailable providers: {', '.join(debug_info['available_providers'])}")

    # Future: Show VM simulator status
    vm_status = debug_info["vm_simulators"]
    if any(vm_status.values()):
        print("\nVM Simulators:")
        for name, available in vm_status.items():
            status = "✅ Available" if available else "❌ Not configured"
            print(f"• {name}: {status}")

    provider = (
        input(f"\nWhich provider to configure? ({'/'.join(debug_info['available_providers'])}): ")
        .strip()
        .lower()
    )

    if provider not in debug_info["available_providers"]:
        print(f"❌ Unknown provider: {provider}")
        return

    # Determine required credentials for provider
    if provider == "authkit":
        required = ["email", "password"]
    elif provider == "github":
        required = ["username", "password"]
    elif provider == "google":
        required = ["email", "password"]
    else:
        required = ["email", "password"]  # Default

    print(f"\nRequired credentials for {provider}: {', '.join(required)}")

    # Run async credential setup
    asyncio.run(manager.ensure_credentials(provider, required))

    print(f"\n✅ Credential setup complete for {provider}")
    print("💡 You can now run tests with this provider")


if __name__ == "__main__":
    interactive_credential_setup()
