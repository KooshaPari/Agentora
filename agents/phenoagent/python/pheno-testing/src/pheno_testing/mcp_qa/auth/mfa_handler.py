"""MFA/OTP Handler with TOTP Automation.

Supports:
- TOTP (Time-based One-Time Password) automation via pyotp
- SMS code prompting
- Email code prompting
- Backup code usage
- Integration with credential manager for TOTP secrets

Usage:
    # TOTP automation
    handler = MFAHandler(credential_manager)
    code = await handler.get_totp_code("my_service")

    # SMS prompting
    code = await handler.prompt_sms_code()

    # Email prompting
    code = await handler.prompt_email_code()

    # In OAuth flow
    adapter = PlaywrightOAuthAdapter(
        email="user@example.com",
        password="password",
        mfa_handler=handler
    )
"""

import asyncio
from datetime import datetime
from typing import Awaitable, Callable, Optional

try:
    import pyotp

    HAS_PYOTP = True
except ImportError:
    HAS_PYOTP = False

from .credential_manager import CredentialManager, CredentialType


class MFAHandler:
    """Handles Multi-Factor Authentication codes.

    Features:
    - TOTP automation using pyotp
    - SMS/Email prompting
    - Backup code support
    - Integration with CredentialManager
    """

    def __init__(
        self,
        credential_manager: Optional[CredentialManager] = None,
        totp_secret: Optional[str] = None,
        custom_prompt: Optional[Callable[[str], Awaitable[str]]] = None,
    ):
        """Initialize MFA handler.

        Args:
            credential_manager: CredentialManager instance for TOTP secrets
            totp_secret: Static TOTP secret (alternative to credential manager)
            custom_prompt: Custom prompt function for codes
        """
        self.credential_manager = credential_manager
        self.totp_secret = totp_secret
        self.custom_prompt = custom_prompt

    async def get_totp_code(self, service_name: Optional[str] = None) -> str:
        """Get TOTP code from secret.

        Args:
            service_name: Service name to lookup in credential manager

        Returns:
            6-digit TOTP code

        Raises:
            RuntimeError: If pyotp not installed or secret not found
        """
        if not HAS_PYOTP:
            raise RuntimeError("pyotp not installed. Install with: pip install pyotp")

        # Get TOTP secret
        secret = self.totp_secret

        if not secret and self.credential_manager and service_name:
            # Try to get from credential manager
            cred = self.credential_manager.get_credential(service_name)
            if cred and cred.credential_type == CredentialType.TOTP_SECRET:
                secret = cred.value

        if not secret:
            raise RuntimeError(
                f"TOTP secret not found. "
                f"Either provide totp_secret or store in credential manager with name '{service_name}'"
            )

        # Generate TOTP code
        totp = pyotp.TOTP(secret)
        code = totp.now()

        return code

    async def prompt_sms_code(self, phone_last_digits: Optional[str] = None) -> str:
        """Prompt user for SMS code.

        Args:
            phone_last_digits: Last digits of phone number for display

        Returns:
            User-entered code
        """
        if self.custom_prompt:
            return await self.custom_prompt("sms")

        # Default prompt
        message = "📱 SMS code"
        if phone_last_digits:
            message += f" (sent to ***{phone_last_digits})"
        message += ": "

        # Run input in thread to avoid blocking event loop
        loop = asyncio.get_event_loop()
        code = await loop.run_in_executor(None, input, message)

        return code.strip()

    async def prompt_email_code(self, email: Optional[str] = None) -> str:
        """Prompt user for email verification code.

        Args:
            email: Email address for display

        Returns:
            User-entered code
        """
        if self.custom_prompt:
            return await self.custom_prompt("email")

        # Default prompt
        message = "📧 Email code"
        if email:
            message += f" (sent to {email})"
        message += ": "

        # Run input in thread to avoid blocking event loop
        loop = asyncio.get_event_loop()
        code = await loop.run_in_executor(None, input, message)

        return code.strip()

    async def prompt_backup_code(self) -> str:
        """Prompt user for backup code.

        Returns:
            User-entered backup code
        """
        if self.custom_prompt:
            return await self.custom_prompt("backup")

        # Default prompt
        message = "🔑 Backup code: "

        # Run input in thread to avoid blocking event loop
        loop = asyncio.get_event_loop()
        code = await loop.run_in_executor(None, input, message)

        return code.strip()

    async def prompt_generic_code(self, prompt_text: str = "Enter code: ") -> str:
        """Prompt user for a generic verification code.

        Args:
            prompt_text: Custom prompt text

        Returns:
            User-entered code
        """
        if self.custom_prompt:
            return await self.custom_prompt("generic")

        # Run input in thread to avoid blocking event loop
        loop = asyncio.get_event_loop()
        code = await loop.run_in_executor(None, input, prompt_text)

        return code.strip()

    async def get_code(
        self, method: str = "totp", service_name: Optional[str] = None, **kwargs
    ) -> str:
        """Get MFA code using specified method.

        Args:
            method: Method to use ("totp", "sms", "email", "backup")
            service_name: Service name (for TOTP lookup)
            **kwargs: Additional method-specific arguments

        Returns:
            MFA code

        Example:
            # TOTP
            code = await handler.get_code("totp", service_name="github")

            # SMS
            code = await handler.get_code("sms", phone_last_digits="1234")

            # Email
            code = await handler.get_code("email", email="user@example.com")
        """
        if method == "totp":
            return await self.get_totp_code(service_name)
        elif method == "sms":
            return await self.prompt_sms_code(kwargs.get("phone_last_digits"))
        elif method == "email":
            return await self.prompt_email_code(kwargs.get("email"))
        elif method == "backup":
            return await self.prompt_backup_code()
        else:
            return await self.prompt_generic_code(f"Enter {method} code: ")


class TOTPSimulator:
    """Standalone TOTP code generator (no credential manager needed).

    Usage:
        simulator = TOTPSimulator("JBSWY3DPEHPK3PXP")
        code = simulator.now()
    """

    def __init__(self, secret: str):
        """Initialize TOTP simulator.

        Args:
            secret: Base32-encoded TOTP secret
        """
        if not HAS_PYOTP:
            raise RuntimeError("pyotp not installed. Install with: pip install pyotp")

        self.secret = secret
        self.totp = pyotp.TOTP(secret)

    def now(self) -> str:
        """
        Get current TOTP code.
        """
        return self.totp.now()

    def verify(self, code: str) -> bool:
        """
        Verify a TOTP code.
        """
        return self.totp.verify(code)

    def at(self, for_time: datetime) -> str:
        """
        Get TOTP code at specific time.
        """
        return self.totp.at(for_time)


__all__ = [
    "MFAHandler",
    "TOTPSimulator",
]
