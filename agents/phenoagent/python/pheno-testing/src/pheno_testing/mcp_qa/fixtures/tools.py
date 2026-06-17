"""Tool-specific client fixtures for MCP-QA testing.

Provides pre-configured clients for specific MCP tools:
- Chat tool client
- Query tool client
- Entity tool client
- Workflow tool client
"""

from typing import Any, Dict, Optional

import pytest

from pheno.testing.mcp_qa.auth.adapters import MCPClientAdapter


@pytest.fixture
def tool_client_factory(authenticated_mcp_client: MCPClientAdapter):
    """Factory for creating tool-specific clients.

    Wraps the authenticated MCP client with tool-specific helpers
    for easier testing of individual tools.

    Usage:
        def test_tools(tool_client_factory):
            chat_client = tool_client_factory("chat")
            result = chat_client.send("Hello")
            assert result["success"]

    Returns:
        Callable: Factory function for tool clients
    """

    def create_tool_client(tool_name: str):
        """
        Create tool-specific client wrapper.
        """

        class ToolClient:
            def __init__(self, mcp_client: MCPClientAdapter, tool: str):
                self.mcp_client = mcp_client
                self.tool_name = tool

            async def call(self, **kwargs) -> Dict[str, Any]:
                """
                Call the tool with given arguments.
                """
                return await self.mcp_client.call_tool(self.tool_name, kwargs)

        return ToolClient(authenticated_mcp_client, tool_name)

    return create_tool_client


@pytest.fixture
def chat_tool_client(authenticated_mcp_client: MCPClientAdapter):
    """Chat tool specific client.

    Provides convenient methods for testing chat tool functionality.

    Usage:
        async def test_chat(chat_tool_client):
            result = await chat_tool_client.send("What is 2+2?")
            assert "4" in result["response"]

    Returns:
        ChatToolClient: Chat tool client
    """

    class ChatToolClient:
        def __init__(self, mcp_client: MCPClientAdapter):
            self.mcp_client = mcp_client

        async def send(self, prompt: str, **kwargs) -> Dict[str, Any]:
            """
            Send chat message.
            """
            return await self.mcp_client.call_tool("chat", {"prompt": prompt, **kwargs})

        async def send_with_model(self, prompt: str, model: str, **kwargs) -> Dict[str, Any]:
            """
            Send chat message with specific model.
            """
            return await self.mcp_client.call_tool(
                "chat", {"prompt": prompt, "model": model, **kwargs}
            )

    return ChatToolClient(authenticated_mcp_client)


@pytest.fixture
def query_tool_client(authenticated_mcp_client: MCPClientAdapter):
    """Query tool specific client.

    Provides convenient methods for testing query/RAG functionality.

    Usage:
        async def test_query(query_tool_client):
            result = await query_tool_client.search("test query")
            assert result["success"]
            assert len(result["results"]) > 0

    Returns:
        QueryToolClient: Query tool client
    """

    class QueryToolClient:
        def __init__(self, mcp_client: MCPClientAdapter):
            self.mcp_client = mcp_client

        async def search(self, query: str, **kwargs) -> Dict[str, Any]:
            """
            Execute search query.
            """
            return await self.mcp_client.call_tool("query", {"query": query, **kwargs})

        async def search_with_filters(
            self, query: str, filters: Dict[str, Any], **kwargs
        ) -> Dict[str, Any]:
            """
            Execute search with filters.
            """
            return await self.mcp_client.call_tool(
                "query", {"query": query, "filters": filters, **kwargs}
            )

    return QueryToolClient(authenticated_mcp_client)


@pytest.fixture
def entity_tool_client(authenticated_mcp_client: MCPClientAdapter):
    """Entity tool specific client.

    Provides CRUD operations for entity management testing.

    Usage:
        async def test_entity_crud(entity_tool_client):
            # Create
            result = await entity_tool_client.create(
                "organization",
                {"name": "Test Org"}
            )
            entity_id = result["entity_id"]

            # Read
            entity = await entity_tool_client.get(entity_id)
            assert entity["name"] == "Test Org"

            # Delete
            await entity_tool_client.delete(entity_id)

    Returns:
        EntityToolClient: Entity tool client
    """

    class EntityToolClient:
        def __init__(self, mcp_client: MCPClientAdapter):
            self.mcp_client = mcp_client

        async def create(self, entity_type: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
            """
            Create entity.
            """
            return await self.mcp_client.call_tool(
                "entity", {"operation": "create", "type": entity_type, "data": data, **kwargs}
            )

        async def get(self, entity_id: str, **kwargs) -> Dict[str, Any]:
            """
            Get entity by ID.
            """
            return await self.mcp_client.call_tool(
                "entity", {"operation": "get", "entity_id": entity_id, **kwargs}
            )

        async def update(self, entity_id: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
            """
            Update entity.
            """
            return await self.mcp_client.call_tool(
                "entity", {"operation": "update", "entity_id": entity_id, "data": data, **kwargs}
            )

        async def delete(self, entity_id: str, **kwargs) -> Dict[str, Any]:
            """
            Delete entity.
            """
            return await self.mcp_client.call_tool(
                "entity", {"operation": "delete", "entity_id": entity_id, **kwargs}
            )

        async def list(self, entity_type: Optional[str] = None, **kwargs) -> Dict[str, Any]:
            """
            List entities.
            """
            return await self.mcp_client.call_tool(
                "entity", {"operation": "list", "type": entity_type, **kwargs}
            )

    return EntityToolClient(authenticated_mcp_client)


@pytest.fixture
def workflow_tool_client(authenticated_mcp_client: MCPClientAdapter):
    """Workflow tool specific client.

    Provides workflow management operations for testing.

    Usage:
        async def test_workflow(workflow_tool_client):
            result = await workflow_tool_client.execute({
                "steps": [
                    {"tool": "chat", "args": {"prompt": "step 1"}},
                    {"tool": "query", "args": {"query": "step 2"}},
                ]
            })
            assert result["success"]
            assert len(result["step_results"]) == 2

    Returns:
        WorkflowToolClient: Workflow tool client
    """

    class WorkflowToolClient:
        def __init__(self, mcp_client: MCPClientAdapter):
            self.mcp_client = mcp_client

        async def execute(self, workflow: Dict[str, Any], **kwargs) -> Dict[str, Any]:
            """
            Execute workflow.
            """
            return await self.mcp_client.call_tool("workflow", {"workflow": workflow, **kwargs})

        async def execute_step(self, step: Dict[str, Any], **kwargs) -> Dict[str, Any]:
            """
            Execute single workflow step.
            """
            return await self.mcp_client.call_tool(
                "workflow", {"operation": "execute_step", "step": step, **kwargs}
            )

    return WorkflowToolClient(authenticated_mcp_client)
