"""
Enhanced credential resolution for OAuth flows with auto-prompting and .env updates.
"""

from __future__ import annotations

import getpass
import os
from pathlib import Path
from typing import Dict, Mapping, Optional


class CredentialResolver:
    """
    Resolve OAuth credentials with auto-prompting and .env updates.
    """

    def __init__(self, auto_prompt: bool = True, update_env: bool = True):
        self.auto_prompt = auto_prompt
        self.update_env = update_env
        self.env_file = Path(".env")
        self.env_prefix = "OAUTH"

    def resolve(
        self,
        provider: str,
        required_keys: Mapping[str, Optional[str]],
        overrides: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Resolve credentials with fallback chain and auto-prompting.
        """
        resolved: Dict[str, str] = {}
        overrides = dict(overrides or {})
        provider_key = provider.upper().replace("-", "_")
        missing_credentials = []

        for key, fallback_env in required_keys.items():
            if key in overrides:
                resolved[key] = overrides[key]
                continue

            env_candidates = [
                f"{self.env_prefix}_{provider_key}_{key.upper()}",
                f"{self.env_prefix}_{key.upper()}",
            ]

            if fallback_env:
                env_candidates.append(fallback_env)

            # Check environment variables
            found = False
            for env_name in env_candidates:
                value = os.getenv(env_name)
                if value:
                    resolved[key] = value
                    found = True
                    break

            if not found:
                missing_credentials.append((key, env_candidates, fallback_env))

        # Handle missing credentials
        if missing_credentials:
            if self.auto_prompt:
                print(f"\n🔑 Missing OAuth credentials for {provider}:")
                for key, env_candidates, fallback_env in missing_credentials:
                    hint = DEFAULT_CREDENTIAL_HINTS.get(provider, {}).get(key, f"{provider} {key}")
                    value = self._prompt_for_credential(key, hint)
                    resolved[key] = value

                    # Update .env file
                    if self.update_env:
                        self._update_env_file(provider, key, value)
            else:
                # Raise error with all missing keys
                missing_info = []
                for key, env_candidates, _ in missing_credentials:
                    missing_info.append(f"{key}: {', '.join(env_candidates)}")

                raise KeyError(
                    f"Missing credentials for provider '{provider}': {missing_info}. "
                    f"Set environment variables or enable auto_prompt=True"
                )

        return resolved

    def _prompt_for_credential(self, key: str, hint: str) -> str:
        """
        Prompt user for missing credential with clean UX.
        """
        # Try to import enhanced progress flow
        try:
            from ..oauth_progress_enhanced import EnhancedOAuthProgressFlow

            flow = EnhancedOAuthProgressFlow()
            return flow.prompt_credential(key, hint)
        except ImportError:
            # Fallback to basic prompting
            is_password = (
                "password" in key.lower() or "secret" in key.lower() or "token" in key.lower()
            )

            prompt = f"Enter {hint} ({key}): "

            if is_password:
                value = getpass.getpass(prompt)
            else:
                value = input(prompt).strip()

            if not value:
                raise ValueError(f"Empty value provided for {key}")

            return value

    def _update_env_file(self, provider: str, key: str, value: str) -> None:
        """
        Update .env file with new credential.
        """
        env_var = f"{self.env_prefix}_{provider.upper()}_{key.upper()}"

        try:
            # Read existing .env content
            if self.env_file.exists():
                with open(self.env_file, "r") as f:
                    lines = f.readlines()
            else:
                lines = []

            # Check if variable already exists
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{env_var}="):
                    lines[i] = f"{env_var}={value}\n"
                    updated = True
                    break

            # Add new variable if not found
            if not updated:
                lines.append("\n# Added by OAuth credential resolver\n")
                lines.append(f"{env_var}={value}\n")

            # Write back to file
            with open(self.env_file, "w") as f:
                f.writelines(lines)

            # Try to use enhanced progress flow for clean notifications
            try:
                from ..oauth_progress_enhanced import EnhancedOAuthProgressFlow

                flow = EnhancedOAuthProgressFlow()
                flow.update_env_notification(env_var)
            except ImportError:
                print(f"✅ Updated .env with {env_var}")

            # Update current environment
            os.environ[env_var] = value

        except Exception as e:
            print(f"⚠️ Failed to update .env file: {e}")


# Default credential hints for common providers
DEFAULT_CREDENTIAL_HINTS = {
    "authkit": {
        "email": "Your AuthKit login email (e.g., user@example.com)",
        "password": "Your AuthKit login password",
    },
    "github": {
        "username": "Your GitHub username",
        "password": "Your GitHub password or personal access token",
    },
    "google": {
        "email": "Your Google account email",
        "password": "Your Google account password",
    },
    "azure": {
        "email": "Your Azure AD email",
        "password": "Your Azure AD password",
    },
}


# MFA handling stubs for future implementation
class MFAHandler:
    """Handler for MFA scenarios - future implementation with VM/simulators."""

    def __init__(self):
        self.handlers = {
            "totp": self._handle_totp,
            "sms": self._handle_sms,
            "email": self._handle_email_code,
            "push": self._handle_push_notification,
        }

    def _handle_totp(self, context: dict) -> str:
        """Handle TOTP MFA - future: integrate with authenticator apps."""
        # TODO: Integrate with pyotp or authenticator simulators
        return input("Enter TOTP code from authenticator app: ").strip()

    def _handle_sms(self, context: dict) -> str:
        """Handle SMS MFA - future: integrate with SMS APIs or simulators."""
        # TODO: Integrate with Twilio API or SMS simulators
        return input("Enter SMS code: ").strip()

    def _handle_email_code(self, context: dict) -> str:
        """Handle email code MFA - future: integrate with email APIs."""
        # TODO: Integrate with Gmail API or email simulators
        return input("Enter email verification code: ").strip()

    def _handle_push_notification(self, context: dict) -> bool:
        """Handle push notification MFA - future: automate approval."""
        # TODO: Integrate with push notification simulators
        input("Press Enter after approving push notification...")
        return True

    def handle_mfa(self, mfa_type: str, context: dict = None) -> str:
        """
        Handle MFA challenge based on type.
        """
        context = context or {}
        handler = self.handlers.get(mfa_type.lower())

        if not handler:
            raise ValueError(f"Unsupported MFA type: {mfa_type}")

        return handler(context)
