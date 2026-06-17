"""
Storage module.
"""

from .base import StorageAdapter
from .supabase import SupabaseStorageAdapter

__all__ = ["StorageAdapter", "SupabaseStorageAdapter"]
