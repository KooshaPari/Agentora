"""Environment Variable Scheme Handler.

Provides access to environment variables via env:// URIs.
"""

import os
import re
from typing import Any

from pheno.ports.mcp import ResourceSchemeHandler


class EnvSchemeHandler(ResourceSchemeHandler):
    """Handler for env:// scheme.

    Provides access to environment variables.

    URI Format:
        env://VARIABLE_NAME
        env://PREFIX_*  (list all with prefix)

    Example:
        >>> handler = EnvSchemeHandler()
        >>> path = await handler.get_resource("env://PATH")
        >>> app_vars = await handler.list_resources("env://APP_*")
    """

    async def get_resource(self, uri: str) -> Any:
        """Get environment variable value.

        Args:
            uri: URI in format env://VARIABLE_NAME

        Returns:
            Environment variable value

        Raises:
            ValueError: If variable not found

        Example:
            >>> value = await handler.get_resource("env://HOME")
        """
        _, var_name = uri.split("://", 1)

        if var_name not in os.environ:
            raise ValueError(f"Environment variable not found: {var_name}")

        return os.environ[var_name]

    async def list_resources(self, uri: str) -> list[str]:
        """List environment variables matching pattern.

        Args:
            uri: URI pattern (e.g., env://APP_*)

        Returns:
            List of matching variable URIs

        Example:
            >>> vars = await handler.list_resources("env://APP_*")
            >>> # ["env://APP_NAME", "env://APP_DEBUG", ...]
        """
        _, pattern = uri.split("://", 1)

        # Convert glob pattern to regex
        regex_pattern = pattern.replace("*", ".*")
        regex = re.compile(regex_pattern)

        return [f"env://{var}" for var in os.environ if regex.match(var)]


    def supports_scheme(self, scheme: str) -> bool:
        """
        Check if scheme is supported.
        """
        return scheme == "env"


__all__ = ["EnvSchemeHandler"]
