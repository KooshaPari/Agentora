"""
Database engine abstraction.
"""


class Database:
    """
    Universal database abstraction.
    """

    def __init__(self, adapter):
        self.adapter = adapter

    def from_(self, table: str):
        """
        Query table.
        """
        return self.adapter.from_(table)

    async def auth_context(self, jwt: str):
        """
        Set auth context.
        """
        if hasattr(self.adapter, "with_auth"):
            return await self.adapter.with_auth(jwt)
        return self
