"""
Vercel deployment client.
"""

import httpx


class VercelClient:
    """
    Vercel API client.
    """

    def __init__(self, token: str, team_id: str | None = None):
        self.token = token
        self.team_id = team_id
        self.base_url = "https://api.vercel.com"

    async def deploy(self, project: str, files: dict):
        """
        Deploy to Vercel.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v13/deployments",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"name": project, "files": files},
            )
            return response.json()
