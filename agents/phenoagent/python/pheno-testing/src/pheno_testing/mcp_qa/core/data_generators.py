"""Test Data Generators with pheno-sdk workflow-kit integration.

Provides factories for generating realistic test data.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class DataGenerator:
    """
    Generate test data for entities.
    """

    @staticmethod
    def timestamp() -> str:
        """
        Generate timestamp string for unique identifiers.
        """
        return datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]

    @staticmethod
    def unique_id(prefix: str = "") -> str:
        """
        Generate unique identifier.
        """
        ts = DataGenerator.timestamp()
        return f"{prefix}{ts}" if prefix else ts

    @staticmethod
    def uuid() -> str:
        """
        Generate a random UUID string.
        """
        return str(uuid.uuid4())

    @staticmethod
    def organization_data(name: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate organization test data with valid slug.
        """
        import re
        import uuid

        # Use UUID for guaranteed unique slug
        unique_slug = str(uuid.uuid4())[:8]
        # Ensure slug matches: ^[a-z][a-z0-9-]*$ (starts with letter, only lowercase letters, numbers, hyphens)
        unique_slug = re.sub(r"[^a-z0-9-]", "", unique_slug.lower())
        # Ensure starts with letter
        if not unique_slug or not unique_slug[0].isalpha():
            unique_slug = f"org{unique_slug}"

        return {
            "name": name or f"Test Org {unique_slug}",
            "slug": unique_slug,  # Just the unique slug, must match ^[a-z][a-z0-9-]*$
            "description": "Automated test organization",
            "type": "team",
        }

    @staticmethod
    def project_data(
        name: Optional[str] = None, organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate project test data.

        Args:
            name: Optional project name
            organization_id: Organization ID (required). Pass a real org ID from list operation.
                            Don't use 'auto' - it requires workspace context to be set.

        Returns:
            Dict with project data
        """
        import uuid

        unique_slug = str(uuid.uuid4())[:8]
        data = {
            "name": name or f"Test Project {unique_slug}",
            "slug": f"testproject-{unique_slug}",
            "description": "Automated test project",
        }
        # Only include organization_id if provided (let caller handle it)
        if organization_id:
            data["organization_id"] = organization_id
        return data

    @staticmethod
    def document_data(
        name: Optional[str] = None, project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate document test data.

        Args:
            name: Optional document name
            project_id: Project ID (required). Pass a real project ID from list operation.
                       Don't use 'auto' - it requires workspace context to be set.

        Returns:
            Dict with document data
        """
        import uuid

        unique_slug = str(uuid.uuid4())[:8]
        data = {
            "name": name or f"Test Document {unique_slug}",
            "slug": f"testdocument-{unique_slug}",
            "description": "Automated test document",
        }
        # Only include project_id if provided (let caller handle it)
        if project_id:
            data["project_id"] = project_id
        return data

    @staticmethod
    def requirement_data(
        name: Optional[str] = None, document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate requirement test data.

        Args:
            name: Optional requirement name
            document_id: Document ID (required). Pass a real document ID from list operation.
                        Don't use 'auto' - it requires workspace context to be set.

        Returns:
            Dict with requirement data
        """
        unique = DataGenerator.unique_id()
        data = {
            "name": name or f"REQ-TEST-{unique}",
            "description": f"Automated test requirement created at {unique}",
            "priority": "medium",
            "status": "active",
        }
        # Only include document_id if provided (let caller handle it)
        if document_id:
            data["document_id"] = document_id
        return data

    @staticmethod
    def test_data(title: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate test case data.

        Args:
            title: Optional test title
            project_id: Project ID (required). Pass a real project ID from list operation.
                       Don't use 'auto' - it requires workspace context to be set.

        Returns:
            Dict with test data
        """
        unique = DataGenerator.unique_id()
        data = {
            "title": title or f"Test Case {unique}",
            "description": f"Automated test case created at {unique}",
            "status": "pending",
            "priority": "medium",
        }
        # Only include project_id if provided (let caller handle it)
        if project_id:
            data["project_id"] = project_id
        return data

    @staticmethod
    def batch_data(entity_type: str, count: int = 3) -> List[Dict[str, Any]]:
        """
        Generate batch test data for entity type.
        """
        generators = {
            "organization": DataGenerator.organization_data,
            "project": DataGenerator.project_data,
            "document": DataGenerator.document_data,
            "requirement": DataGenerator.requirement_data,
            "test": DataGenerator.test_data,
        }

        generator = generators.get(entity_type)
        if not generator:
            return []

        return [generator() for _ in range(count)]
