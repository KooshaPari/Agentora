"""
Supabase storage adapter implementation.
"""

from __future__ import annotations

import os

from .base import StorageAdapter


class SupabaseStorageAdapter(StorageAdapter):
    """
    Supabase-based storage adapter.
    """

    def __init__(self, client=None):
        """Initialize Supabase storage adapter.

        Args:
            client: Supabase client instance (optional, will auto-initialize)
        """
        self._client = client

    def _get_client(self):
        """
        Get Supabase client, auto-initializing if needed.
        """
        if self._client is None:
            try:
                from supabase import create_client

                url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
                key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
                if not url or not key:
                    raise ValueError(
                        "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY",
                    )
                self._client = create_client(url, key)
            except ImportError:
                raise ImportError("supabase-py not installed. Install with: pip install supabase")
        return self._client

    async def upload(
        self,
        bucket: str,
        path: str,
        data: bytes,
        *,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
        Upload a file to Supabase storage.
        """
        try:
            client = self._get_client()
            storage = client.storage.from_(bucket)

            file_options = {}
            if content_type:
                file_options["content-type"] = content_type
            if metadata:
                file_options.update(metadata)

            result = storage.upload(path, data, file_options=file_options)

            if hasattr(result, "error") and result.error:
                raise RuntimeError(f"Failed to upload file: {result.error}")

            # Return public URL
            return self.get_public_url(bucket, path)

        except Exception as e:
            raise RuntimeError(f"Failed to upload file to {bucket}/{path}: {e}")

    async def download(self, bucket: str, path: str) -> bytes:
        """
        Download a file from Supabase storage.
        """
        try:
            client = self._get_client()
            storage = client.storage.from_(bucket)

            result = storage.download(path)

            if hasattr(result, "error") and result.error:
                raise RuntimeError(f"Failed to download file: {result.error}")

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to download file from {bucket}/{path}: {e}")

    async def delete(self, bucket: str, path: str) -> bool:
        """
        Delete a file from Supabase storage.
        """
        try:
            client = self._get_client()
            storage = client.storage.from_(bucket)

            result = storage.remove([path])

            return not (hasattr(result, "error") and result.error)

        except Exception:
            return False

    def get_public_url(self, bucket: str, path: str) -> str:
        """
        Get public URL for a file in Supabase storage.
        """
        base_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        if not base_url:
            raise ValueError("Missing NEXT_PUBLIC_SUPABASE_URL")

        return f"{base_url}/storage/v1/object/public/{bucket}/{path}"
