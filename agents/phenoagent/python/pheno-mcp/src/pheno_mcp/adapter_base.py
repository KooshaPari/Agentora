"""
Generic MCP Tool Adapter Base Classes

Provides reusable patterns for MCP tool adapters extracted from atoms_mcp-old.

Patterns extracted:
1. Auth validation and user extraction from FastMCP context
2. Error handling and result formatting
3. Database query patterns
4. Tool registration with FastMCP

Usage:
    class MyToolAdapter(MCPToolAdapterBase):
        def __init__(self, database_port, auth_port=None):
            super().__init__(database_port, auth_port)

        def register(self, mcp: FastMCP):
            @mcp.tool()
            async def my_tool(ctx: Context, ...):
                user_id = await self.extract_user_id(ctx)
                return self.format_success(data={"user": user_id})
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastmcp import Context, FastMCP


class MCPToolAdapterBase(ABC):
    """
    Base class for MCP tool adapters.

    Provides common functionality:
    - Auth token extraction from FastMCP context
    - User ID extraction and validation
    - Standardized error handling
    - Result formatting patterns
    - Database query helpers
    """

    def __init__(self, database_port: Any, auth_port: Any | None = None):
        """
        Initialize adapter with ports.

        Args:
            database_port: Database port for persistence operations
            auth_port: Optional auth port for authentication
        """
        self.database_port = database_port
        self.auth_port = auth_port
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def register(self, mcp: FastMCP) -> None:
        """
        Register tool(s) with MCP server.

        This method should use @mcp.tool() decorator to register tools.

        Args:
            mcp: FastMCP server instance
        """

    # ===== Auth Patterns =====

    async def extract_auth_token(self, ctx: Context | None) -> str | None:
        """
        Extract auth token from FastMCP context.

        Supports multiple patterns:
        - Authorization header (with or without "Bearer " prefix)
        - auth_token in metadata
        - Direct token in context

        Args:
            ctx: FastMCP context

        Returns:
            Auth token string or None if not found
        """
        if not ctx:
            return None

        # Try to extract from context metadata
        auth_token = None
        if hasattr(ctx, "meta") and ctx.meta:
            auth_token = ctx.meta.get("authorization") or ctx.meta.get("auth_token")

            # Strip "Bearer " prefix if present
            if auth_token and auth_token.startswith("Bearer "):
                auth_token = auth_token[7:]

        return auth_token

    async def extract_user_id(
        self, ctx: Context | None, default: str = "default-user",
    ) -> str:
        """
        Extract user ID from FastMCP context with auth validation.

        Extraction strategy:
        1. Try to get auth token from context
        2. Validate token using auth port if available
        3. Extract user ID from validated token
        4. Check for authenticated_user property
        5. Fallback to default user

        Args:
            ctx: FastMCP context containing auth info
            default: Default user ID if auth fails

        Returns:
            User ID string
        """
        # Try token-based auth first
        auth_token = await self.extract_auth_token(ctx)

        if auth_token and self.auth_port:
            try:
                user_data = await self.auth_port.get_user_from_token(auth_token)
                if user_data and "id" in user_data:
                    return user_data["id"]
            except Exception as e:
                self.logger.warning(f"Failed to validate auth token: {e}")

        # Fallback: Check authenticated_user property
        if ctx and hasattr(ctx, "authenticated_user") and ctx.authenticated_user:
            if isinstance(ctx.authenticated_user, dict):
                return ctx.authenticated_user.get("id", default)
            if hasattr(ctx.authenticated_user, "id"):
                return ctx.authenticated_user.id

        # Default fallback
        return default

    # ===== Result Formatting Patterns =====

    def format_success(
        self,
        data: Any = None,
        message: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """
        Format successful result.

        Args:
            data: Result data
            message: Optional success message
            **extra: Additional fields to include

        Returns:
            Standardized success response dictionary
        """
        result: dict[str, Any] = {"success": True}

        if data is not None:
            result["data"] = data

        if message:
            result["message"] = message

        result.update(extra)
        return result

    def format_error(
        self,
        error: str | Exception,
        operation: str | None = None,
        **context: Any,
    ) -> dict[str, Any]:
        """
        Format error result.

        Args:
            error: Error message or exception
            operation: Optional operation that failed
            **context: Additional context fields

        Returns:
            Standardized error response dictionary
        """
        result: dict[str, Any] = {
            "success": False,
            "error": str(error),
        }

        if operation:
            result["operation"] = operation

        result.update(context)
        return result

    def format_validation_error(
        self,
        message: str,
        field: str | None = None,
        valid_values: list[Any] | None = None,
        **context: Any,
    ) -> dict[str, Any]:
        """
        Format validation error result.

        Args:
            message: Validation error message
            field: Field that failed validation
            valid_values: List of valid values for the field
            **context: Additional context

        Returns:
            Standardized validation error response
        """
        result = self.format_error(message, **context)

        if field:
            result["field"] = field

        if valid_values:
            result["valid_values"] = valid_values

        return result

    # ===== Database Query Patterns =====

    async def db_get_by_id(
        self, entity_class: type, entity_id: str,
    ) -> Any | None:
        """
        Get entity by ID from database.

        Args:
            entity_class: Entity class type
            entity_id: Entity ID

        Returns:
            Entity instance or None if not found
        """
        try:
            return await self.database_port.get_by_id(entity_class, entity_id)
        except Exception as e:
            self.logger.exception(f"Database get_by_id failed: {e}")
            return None

    async def db_save(self, entity: Any) -> Any:
        """
        Save entity to database.

        Args:
            entity: Entity instance to save

        Returns:
            Saved entity instance

        Raises:
            Exception: If save operation fails
        """
        return await self.database_port.save(entity)

    async def db_delete(self, entity_class: type, entity_id: str) -> None:
        """
        Delete entity from database.

        Args:
            entity_class: Entity class type
            entity_id: Entity ID to delete

        Raises:
            Exception: If delete operation fails
        """
        await self.database_port.delete(entity_class, entity_id)

    async def db_list(
        self,
        entity_class: type,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Any]:
        """
        List entities from database with filters.

        Args:
            entity_class: Entity class type
            filters: Optional filter criteria
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of entity instances
        """
        try:
            return await self.database_port.list(
                entity_class, filters or {}, limit, offset,
            )
        except Exception as e:
            self.logger.exception(f"Database list failed: {e}")
            return []

    # ===== Domain Entity Helpers =====

    def entity_to_dict(self, entity: Any) -> dict[str, Any]:
        """
        Convert entity to dictionary.

        Args:
            entity: Entity instance

        Returns:
            Dictionary representation of entity
        """
        if hasattr(entity, "to_dict"):
            return entity.to_dict()
        if isinstance(entity, dict):
            return entity
        # Fallback: convert object attributes to dict
        return {
            k: v
            for k, v in entity.__dict__.items()
            if not k.startswith("_")
        }

    def entities_to_list(self, entities: list[Any]) -> list[dict[str, Any]]:
        """
        Convert list of entities to list of dictionaries.

        Args:
            entities: List of entity instances

        Returns:
            List of dictionaries
        """
        return [self.entity_to_dict(e) for e in entities]


class CRUDToolAdapterBase(MCPToolAdapterBase):
    """
    Base class for CRUD-style MCP tool adapters.

    Extends MCPToolAdapterBase with CRUD operation patterns:
    - Create: Create new entity
    - Read: Get entity by ID
    - Update: Update existing entity
    - Delete: Delete entity
    - List: List entities with filters

    This pattern is commonly used for entity management tools.
    """

    def __init__(
        self,
        database_port: Any,
        auth_port: Any | None = None,
        entity_classes: dict[str, type] | None = None,
    ):
        """
        Initialize CRUD adapter.

        Args:
            database_port: Database port
            auth_port: Optional auth port
            entity_classes: Mapping of entity type names to classes
        """
        super().__init__(database_port, auth_port)
        self.entity_classes = entity_classes or {}

    def get_entity_class(self, entity_type: str) -> type | None:
        """
        Get entity class by type name.

        Args:
            entity_type: Entity type name (e.g., "organization", "project")

        Returns:
            Entity class or None if not found
        """
        return self.entity_classes.get(entity_type)

    def validate_entity_type(self, entity_type: str) -> dict[str, Any] | None:
        """
        Validate entity type and return error if invalid.

        Args:
            entity_type: Entity type to validate

        Returns:
            Error dict if invalid, None if valid
        """
        if entity_type not in self.entity_classes:
            return self.format_validation_error(
                message=f"Unknown entity type: {entity_type}",
                field="entity_type",
                valid_values=list(self.entity_classes.keys()),
            )
        return None

    async def handle_create(
        self,
        entity_type: str,
        data: dict[str, Any],
        user_id: str,
    ) -> dict[str, Any]:
        """
        Handle create operation.

        Args:
            entity_type: Type of entity to create
            data: Entity data
            user_id: ID of user creating entity

        Returns:
            Result dictionary
        """
        # Validate entity type
        error = self.validate_entity_type(entity_type)
        if error:
            return error

        try:
            entity_class = self.get_entity_class(entity_type)

            # Add owner_id if not present
            if "owner_id" not in data:
                data["owner_id"] = user_id

            # Create entity using domain factory
            entity = entity_class.create(**data)

            # Save to database
            saved_entity = await self.db_save(entity)

            return self.format_success(
                data=self.entity_to_dict(saved_entity),
                entity_type=entity_type,
                operation="create",
            )

        except Exception as e:
            self.logger.exception(f"Create failed for {entity_type}: {e}")
            return self.format_error(e, operation="create", entity_type=entity_type)

    async def handle_read(
        self,
        entity_type: str,
        entity_id: str | None,
        include_relations: bool = False,
    ) -> dict[str, Any]:
        """
        Handle read operation.

        Args:
            entity_type: Type of entity to read
            entity_id: ID of entity to read
            include_relations: Whether to include related entities

        Returns:
            Result dictionary
        """
        if not entity_id:
            return self.format_validation_error(
                message="entity_id is required for read operation",
                field="entity_id",
                entity_type=entity_type,
                operation="read",
            )

        # Validate entity type
        error = self.validate_entity_type(entity_type)
        if error:
            return error

        try:
            entity_class = self.get_entity_class(entity_type)
            entity = await self.db_get_by_id(entity_class, entity_id)

            if not entity:
                return self.format_error(
                    error=f"{entity_type} not found",
                    operation="read",
                    entity_type=entity_type,
                    entity_id=entity_id,
                )

            return self.format_success(
                data=self.entity_to_dict(entity),
                entity_type=entity_type,
                operation="read",
            )

        except Exception as e:
            self.logger.exception(f"Read failed for {entity_type}:{entity_id}: {e}")
            return self.format_error(
                e,
                operation="read",
                entity_type=entity_type,
                entity_id=entity_id,
            )

    async def handle_list(
        self,
        entity_type: str,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, Any]:
        """
        Handle list operation.

        Args:
            entity_type: Type of entities to list
            filters: Filter criteria
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Result dictionary
        """
        # Validate entity type
        error = self.validate_entity_type(entity_type)
        if error:
            return error

        try:
            entity_class = self.get_entity_class(entity_type)
            entities = await self.db_list(
                entity_class,
                filters or {},
                limit or 100,
                offset or 0,
            )

            return self.format_success(
                data=self.entities_to_list(entities),
                count=len(entities),
                entity_type=entity_type,
                operation="list",
            )

        except Exception as e:
            self.logger.exception(f"List failed for {entity_type}: {e}")
            return self.format_error(e, operation="list", entity_type=entity_type)
