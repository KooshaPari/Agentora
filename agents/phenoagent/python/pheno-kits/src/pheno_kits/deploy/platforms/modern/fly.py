"""
Fly.io deployment client.
"""


class FlyClient:
    """
    Fly.io API client.
    """

    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.fly.io"

    async def deploy(self, app: str, config: dict):
        """
        Deploy to Fly.io.
        """
        # Placeholder for Fly.io API call
        return {"app": app, "status": "deployed"}
