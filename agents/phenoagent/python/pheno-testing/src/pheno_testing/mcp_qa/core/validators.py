"""Response Validators.

Provides validation helpers for test assertions.
"""

from typing import Any, Dict, List, Optional


class ResponseValidator:
    """
    Validates MCP tool responses.
    """

    @staticmethod
    def has_fields(response: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Check if response has all required fields.
        """
        if not isinstance(response, dict):
            return False
        return all(field in response for field in required_fields)

    @staticmethod
    def has_any_fields(response: Dict[str, Any], fields: List[str]) -> bool:
        """
        Check if response has any of the specified fields.
        """
        if not isinstance(response, dict):
            return False
        return any(field in response for field in fields)

    @staticmethod
    def validate_pagination(response: Dict[str, Any]) -> bool:
        """
        Validate pagination structure.
        """
        required = ["total", "limit", "offset"]
        return ResponseValidator.has_fields(response, required)

    @staticmethod
    def validate_list_response(response: Dict[str, Any], data_key: str = "data") -> bool:
        """
        Validate list response structure.
        """
        if not isinstance(response, dict):
            return False
        if data_key not in response:
            return False
        return isinstance(response[data_key], list)

    @staticmethod
    def validate_success_response(result: Dict[str, Any]) -> bool:
        """
        Validate standard success response.
        """
        return result.get("success", False) and result.get("error") is None

    @staticmethod
    def extract_id(response: Dict[str, Any]) -> Optional[str]:
        """
        Extract ID from response, handling multiple formats.
        """
        if not isinstance(response, dict):
            return None
        if "id" in response:
            return response["id"]
        if "data" in response and isinstance(response["data"], dict):
            return response["data"].get("id")
        return None

    @staticmethod
    async def get_existing_entity_id(client, entity_type: str) -> Optional[str]:
        """Get an existing entity ID from list operation.

        Returns the ID of the first entity of the given type, or None if none exist.
        """
        list_result = await client.call_tool(
            "entity_tool", {"entity_type": entity_type, "operation": "list", "limit": 1}
        )

        if not list_result.get("success"):
            return None

        entities = list_result.get("response", {}).get("data", [])
        if not entities:
            return None

        return entities[0].get("id")

    @staticmethod
    async def create_test_entity(
        client, entity_type: str, data_generator_func, **data_kwargs
    ) -> Optional[str]:
        """Create test entity and return ID, or None if create fails.

        This helper ensures proper CREATE→OPERATE→DELETE pattern with skip propagation.
        Automatically resolves parent IDs for nested entities (project→org, document→project, etc)

        Args:
            client: MCP client
            entity_type: Type of entity to create
            data_generator_func: Function that returns entity data dict
            **data_kwargs: Additional keyword arguments to pass to data_generator_func

        Returns:
            entity_id if create succeeded, None if failed (caller should skip/return)
        """

        # Auto-resolve parent IDs for nested entity types
        if entity_type == "project" and "organization_id" not in data_kwargs:
            org_id = await ResponseValidator.get_or_create_organization(client)
            if org_id:
                data_kwargs["organization_id"] = org_id

        elif entity_type == "document" and "project_id" not in data_kwargs:
            project_id = await ResponseValidator.get_or_create_project(client)
            if project_id:
                data_kwargs["project_id"] = project_id

        elif entity_type == "requirement" and "document_id" not in data_kwargs:
            doc_id = await ResponseValidator.get_or_create_document(client)
            if doc_id:
                data_kwargs["document_id"] = doc_id

        elif entity_type == "test" and "project_id" not in data_kwargs:
            project_id = await ResponseValidator.get_or_create_project(client)
            if project_id:
                data_kwargs["project_id"] = project_id

        data = data_generator_func(**data_kwargs)
        create_result = await client.call_tool(
            "entity_tool", {"entity_type": entity_type, "operation": "create", "data": data}
        )

        if not create_result.get("success"):
            return None

        return ResponseValidator.extract_id(create_result.get("response", {}))

    @staticmethod
    async def get_or_create_organization(client) -> Optional[str]:
        """Get existing organization ID or create a new test organization.

        Returns:
            organization_id if successful, None otherwise
        """
        # Try to get existing org first
        org_id = await ResponseValidator.get_existing_entity_id(client, "organization")
        if org_id:
            return org_id

        # Create new org
        from pheno.testing.mcp_qa.data_generators import DataGenerator

        return await ResponseValidator.create_test_entity(
            client, "organization", DataGenerator.organization_data
        )

    @staticmethod
    async def get_or_create_project(client, organization_id: Optional[str] = None) -> Optional[str]:
        """Get existing project ID or create a new test project.

        Args:
            organization_id: Optional organization ID. If not provided, will get/create one.

        Returns:
            project_id if successful, None otherwise
        """
        # Get org_id if not provided
        if not organization_id:
            organization_id = await ResponseValidator.get_or_create_organization(client)
            if not organization_id:
                return None

        # Try to get existing project first
        project_id = await ResponseValidator.get_existing_entity_id(client, "project")
        if project_id:
            return project_id

        # Create new project
        from pheno.testing.mcp_qa.data_generators import DataGenerator

        return await ResponseValidator.create_test_entity(
            client, "project", DataGenerator.project_data, organization_id=organization_id
        )

    @staticmethod
    async def get_or_create_document(client, project_id: Optional[str] = None) -> Optional[str]:
        """Get existing document ID or create a new test document.

        Args:
            project_id: Optional project ID. If not provided, will get/create one.

        Returns:
            document_id if successful, None otherwise
        """
        # Get project_id if not provided
        if not project_id:
            project_id = await ResponseValidator.get_or_create_project(client)
            if not project_id:
                return None

        # Try to get existing document first
        doc_id = await ResponseValidator.get_existing_entity_id(client, "document")
        if doc_id:
            return doc_id

        # Create new document
        from pheno.testing.mcp_qa.data_generators import DataGenerator

        return await ResponseValidator.create_test_entity(
            client, "document", DataGenerator.document_data, project_id=project_id
        )


class FieldValidator:
    """
    Validates specific field types and values.
    """

    @staticmethod
    def is_uuid(value: Any) -> bool:
        """
        Check if value is a valid UUID string.
        """
        if not isinstance(value, str):
            return False
        import re

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))

    @staticmethod
    def is_iso_timestamp(value: Any) -> bool:
        """
        Check if value is ISO 8601 timestamp.
        """
        if not isinstance(value, str):
            return False
        try:
            from datetime import datetime

            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except Exception:
            return False

    @staticmethod
    def is_in_range(
        value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None
    ) -> bool:
        """
        Check if value is within range.
        """
        try:
            num = float(value)
            if min_val is not None and num < min_val:
                return False
            if max_val is not None and num > max_val:
                return False
            return True
        except Exception:
            return False
