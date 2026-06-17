"""
Neon database adapter with serverless PostgreSQL and branching support.
"""

from __future__ import annotations

import os
from typing import Any

from .postgres import PostgreSQLAdapter


class NeonAdapter(PostgreSQLAdapter):
    """Neon serverless PostgreSQL adapter with branching capabilities.

    Extends PostgreSQLAdapter with Neon-specific features like database branching.
    """

    def __init__(
        self,
        connection_string: str | None = None,
        api_key: str | None = None,
        project_id: str | None = None,
        **kwargs,
    ):
        """Initialize Neon adapter.

        Args:
            connection_string: Neon connection string (from dashboard)
            api_key: Neon API key for management operations
            project_id: Neon project ID
            **kwargs: Additional connection parameters
        """
        # Build connection string from env if not provided
        dsn = connection_string or os.getenv("NEON_DATABASE_URL")
        if not dsn:
            raise ValueError(
                "Missing Neon connection string. Provide connection_string or set NEON_DATABASE_URL",
            )

        # Initialize PostgreSQL adapter with Neon connection
        super().__init__(dsn=dsn, **kwargs)

        self.api_key = api_key or os.getenv("NEON_API_KEY")
        self.project_id = project_id or os.getenv("NEON_PROJECT_ID")
        self._api_client = None

    def _get_api_client(self):
        """
        Get Neon API client for management operations.
        """
        if not self._api_client:
            if not self.api_key:
                raise ValueError("Neon API key required for management operations")

            try:
                import httpx

                self._api_client = httpx.AsyncClient(
                    base_url="https://console.neon.tech/api/v2",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
            except ImportError:
                raise ImportError("httpx not installed. Install with: pip install httpx")

        return self._api_client

    async def create_branch(
        self, name: str, parent: str = "main", from_timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Create a new database branch.

        Neon's branching feature allows you to create instant copies of your database
        for development, testing, or preview environments.

        Args:
            name: Name for the new branch
            parent: Parent branch name (default: "main")
            from_timestamp: Optional timestamp to branch from

        Returns:
            Branch information including connection details

        Example:
            ```python
            adapter = NeonAdapter()
            branch = await adapter.create_branch("feature-branch", parent="main")
            print(f"New branch connection: {branch['connection_uri']}")
            ```
        """
        if not self.project_id:
            raise ValueError("project_id required for branch operations")

        client = self._get_api_client()

        payload = {
            "branch": {
                "name": name,
                "parent_id": parent,
            },
        }

        if from_timestamp:
            payload["branch"]["parent_timestamp"] = from_timestamp

        response = await client.post(f"/projects/{self.project_id}/branches", json=payload)
        response.raise_for_status()

        return response.json()

    async def delete_branch(self, branch_id: str) -> dict[str, Any]:
        """Delete a database branch.

        Args:
            branch_id: ID of the branch to delete

        Returns:
            Deletion confirmation
        """
        if not self.project_id:
            raise ValueError("project_id required for branch operations")

        client = self._get_api_client()
        response = await client.delete(f"/projects/{self.project_id}/branches/{branch_id}")
        response.raise_for_status()

        return response.json()

    async def list_branches(self) -> list[dict[str, Any]]:
        """List all branches in the project.

        Returns:
            List of branch information
        """
        if not self.project_id:
            raise ValueError("project_id required for branch operations")

        client = self._get_api_client()
        response = await client.get(f"/projects/{self.project_id}/branches")
        response.raise_for_status()

        data = response.json()
        return data.get("branches", [])

    async def get_branch_connection(self, branch_id: str) -> str:
        """Get connection string for a specific branch.

        Args:
            branch_id: Branch ID

        Returns:
            Connection string for the branch
        """
        if not self.project_id:
            raise ValueError("project_id required for branch operations")

        client = self._get_api_client()
        response = await client.get(f"/projects/{self.project_id}/branches/{branch_id}")
        response.raise_for_status()

        branch_data = response.json()
        return branch_data.get("connection_uri", "")

    async def close(self):
        """
        Close connection pool and API client.
        """
        await super().close()

        if self._api_client:
            await self._api_client.aclose()
            self._api_client = None
