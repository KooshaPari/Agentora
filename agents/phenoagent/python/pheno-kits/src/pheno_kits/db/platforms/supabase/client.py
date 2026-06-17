"""
Supabase database adapter.
"""


class SupabaseAdapter:
    """
    Supabase adapter with RLS support.
    """

    def __init__(self, url: str, anon_key: str, service_key: str | None = None):
        self.url = url
        self.anon_key = anon_key
        self.service_key = service_key

        try:
            from supabase import create_client

            self.client = create_client(url, anon_key)
            self.admin = create_client(url, service_key) if service_key else None
        except ImportError:
            print("supabase-py not installed")
            self.client = None
            self.admin = None

    def from_(self, table: str):
        """
        Query table with RLS.
        """
        if self.client:
            return self.client.table(table)
        return None
