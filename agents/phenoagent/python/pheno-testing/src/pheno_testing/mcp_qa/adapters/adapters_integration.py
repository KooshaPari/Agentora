"""Integration adapters for MCP client, resources, and database.

This module implements adapters for:
- MCPClientAdapter: MCP client communication
- MCPResourceAdapter: Resource monitoring operations
- MCPDatabaseAdapter: Database operations
"""

import logging
from typing import Any, Dict, List, Optional, Union

from pheno.testing.mcp_qa.process.monitor import HealthStatus, ProcessInfo, ProcessMonitor
from pheno.testing.mcp_qa.utils.database_utils import DatabaseAdapter

logger = logging.getLogger(__name__)


class MCPClientAdapter:
    """Adapter for MCP client communication.

    Wraps the existing MCPClientAdapter from core.adapters to implement
    the ClientAdapter protocol.

    Example:
        from pheno.testing.mcp_qa.core.adapters import MCPClientAdapter as CoreAdapter

        core_adapter = CoreAdapter(client, debug=True)
        adapter = MCPClientAdapter(core_adapter)

        result = await adapter.call_tool("get_organization", {"slug": "test-org"})
    """

    def __init__(self, client_adapter):
        """Initialize MCP client adapter.

        Args:
            client_adapter: Core MCPClientAdapter instance to wrap
        """
        self._adapter = client_adapter
        logger.debug(f"Initialized client adapter for endpoint: {client_adapter.endpoint}")

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call MCP tool and return normalized result.

        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments/parameters

        Returns:
            Normalized result dictionary with keys:
                - success: bool
                - result: Any (tool response)
                - duration_ms: float
                - error: Optional[str]

        Raises:
            Exception: If tool call fails critically
        """
        try:
            logger.debug(f"Calling tool: {tool_name}")
            result = await self._adapter.call_tool(tool_name, arguments)

            if not result.get("success"):
                logger.warning(f"Tool call failed: {tool_name} - {result.get('error')}")

            return result
        except Exception as e:
            logger.error(f"Exception during tool call {tool_name}: {e}")
            return {
                "success": False,
                "result": None,
                "duration_ms": 0.0,
                "error": str(e),
            }

    async def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools.

        Returns:
            Dictionary with keys:
                - success: bool
                - tools: List[Tool]
                - duration_ms: float
                - error: Optional[str]
        """
        try:
            logger.debug("Listing available tools")
            result = await self._adapter.list_tools()

            if result.get("success"):
                tool_count = len(result.get("tools", []))
                logger.info(f"Found {tool_count} available tools")

            return result
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return {
                "success": False,
                "tools": [],
                "duration_ms": 0.0,
                "error": str(e),
            }

    async def ping(self) -> Dict[str, Any]:
        """Ping server for health check.

        Returns:
            Dictionary with keys:
                - success: bool
                - latency_ms: float
                - error: Optional[str]
        """
        try:
            result = await self._adapter.ping()

            if result.get("success"):
                logger.debug(f"Server ping successful: {result.get('latency_ms')}ms")
            else:
                logger.warning(f"Server ping failed: {result.get('error')}")

            return result
        except Exception as e:
            logger.error(f"Exception during ping: {e}")
            return {
                "success": False,
                "latency_ms": 0.0,
                "error": str(e),
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics.

        Returns:
            Dictionary with keys:
                - total_calls: int
                - total_duration_ms: float
                - avg_duration_ms: float
                - endpoint: str
        """
        try:
            stats = self._adapter.get_stats()
            logger.debug(
                f"Client stats: {stats['total_calls']} calls, avg {stats['avg_duration_ms']:.2f}ms"
            )
            return stats
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_calls": 0,
                "total_duration_ms": 0.0,
                "avg_duration_ms": 0.0,
                "endpoint": "unknown",
            }


class MCPResourceAdapter:
    """Adapter for resource monitoring operations.

    Wraps the ProcessMonitor from mcp_qa.process.monitor to implement
    the ResourceMonitor protocol.

    Example:
        monitor = ProcessMonitor()
        adapter = MCPResourceAdapter(monitor)

        # Register server process
        info = adapter.register_process("mcp-server", port=8000)

        # Check health
        health = adapter.check_health("mcp-server")
    """

    def __init__(self, process_monitor: ProcessMonitor):
        """Initialize resource monitor adapter.

        Args:
            process_monitor: ProcessMonitor instance to wrap
        """
        self._monitor = process_monitor
        logger.debug("Initialized resource monitor adapter")

    def get_process_info(self, pid: int) -> Optional[ProcessInfo]:
        """Get detailed information about a process.

        Args:
            pid: Process ID

        Returns:
            ProcessInfo if process exists, None otherwise
        """
        try:
            info = self._monitor.get_process_info(pid)
            if info:
                logger.debug(f"Found process info for PID {pid}: {info.name}")
            else:
                logger.debug(f"No process found for PID {pid}")
            return info
        except Exception as e:
            logger.error(f"Error getting process info for PID {pid}: {e}")
            return None

    def find_pid_by_port(self, port: int) -> Optional[int]:
        """Find PID of process listening on a port.

        Args:
            port: Port number

        Returns:
            PID if found, None otherwise
        """
        try:
            pid = self._monitor.find_pid_by_port(port)
            if pid:
                logger.debug(f"Found PID {pid} listening on port {port}")
            else:
                logger.debug(f"No process found on port {port}")
            return pid
        except Exception as e:
            logger.error(f"Error finding PID for port {port}: {e}")
            return None

    def register_process(
        self,
        name: str,
        port: Optional[int] = None,
        pid: Optional[int] = None,
        command_pattern: Optional[str] = None,
    ) -> ProcessInfo:
        """Register a process for monitoring.

        Args:
            name: Display name for process
            port: Port to check (will find PID automatically)
            pid: Known PID
            command_pattern: Pattern to find PID by command

        Returns:
            ProcessInfo object
        """
        try:
            info = self._monitor.register_process(name, port, pid, command_pattern)
            logger.info(f"Registered process: {name} (PID: {info.pid or 'unknown'})")
            return info
        except Exception as e:
            logger.error(f"Failed to register process {name}: {e}")
            raise

    def update_process(self, name: str) -> Optional[ProcessInfo]:
        """Update information for a registered process.

        Args:
            name: Process name

        Returns:
            Updated ProcessInfo, or None if not found
        """
        try:
            info = self._monitor.update_process(name)
            if info:
                logger.debug(f"Updated process: {name}")
            else:
                logger.warning(f"Process not found: {name}")
            return info
        except Exception as e:
            logger.error(f"Error updating process {name}: {e}")
            return None

    def check_health(self, name: str, health_url: Optional[str] = None) -> HealthStatus:
        """Check health of a process.

        Args:
            name: Process name
            health_url: Optional URL to check health endpoint

        Returns:
            HealthStatus enum value
        """
        try:
            health = self._monitor.check_health(name, health_url)
            logger.debug(f"Health check for {name}: {health.value}")
            return health
        except Exception as e:
            logger.error(f"Error checking health for {name}: {e}")
            return HealthStatus.UNKNOWN


class MCPDatabaseAdapter:
    """Adapter for database operations.

    Wraps a DatabaseAdapter instance to implement the DatabaseProvider protocol.

    Example:
        from pheno.testing.mcp_qa.utils.database_utils import SupabaseDatabaseAdapter

        db_adapter = SupabaseDatabaseAdapter()
        db_adapter.set_access_token(user_token)

        adapter = MCPDatabaseAdapter(db_adapter)

        # Query users
        users = await adapter.query("users", filters={"active": True}, limit=10)
    """

    def __init__(self, database_adapter: DatabaseAdapter):
        """Initialize database adapter.

        Args:
            database_adapter: DatabaseAdapter instance to wrap
        """
        self._adapter = database_adapter
        logger.debug("Initialized database adapter")

    def set_access_token(self, token: str):
        """Set user access token for RLS context.

        Args:
            token: User's JWT access token
        """
        try:
            self._adapter.set_access_token(token)
            logger.debug("Access token set for RLS context")
        except Exception as e:
            logger.error(f"Failed to set access token: {e}")
            raise

    async def query(
        self,
        table: str,
        *,
        select: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a query on a table.

        Args:
            table: Table name
            select: Columns to select (default: "*")
            filters: Filter conditions
            order_by: Order by clause (e.g., "created_at:desc")
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of records as dictionaries
        """
        try:
            logger.debug(f"Querying table: {table}")
            results = await self._adapter.query(
                table,
                select=select,
                filters=filters,
                order_by=order_by,
                limit=limit,
                offset=offset,
            )
            logger.debug(f"Query returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Query failed on table {table}: {e}")
            raise

    async def get_single(
        self,
        table: str,
        *,
        select: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a single record from a table.

        Args:
            table: Table name
            select: Columns to select (default: "*")
            filters: Filter conditions

        Returns:
            Single record as dictionary, or None if not found
        """
        try:
            logger.debug(f"Getting single record from table: {table}")
            result = await self._adapter.get_single(table, select=select, filters=filters)
            if result:
                logger.debug(f"Found record in {table}")
            else:
                logger.debug(f"No record found in {table}")
            return result
        except Exception as e:
            logger.error(f"Get single failed on table {table}: {e}")
            raise

    async def insert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        *,
        returning: Optional[str] = None,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Insert one or more records.

        Args:
            table: Table name
            data: Record(s) to insert
            returning: Columns to return (default: all)

        Returns:
            Inserted record(s)
        """
        try:
            record_count = len(data) if isinstance(data, list) else 1
            logger.debug(f"Inserting {record_count} record(s) into {table}")
            result = await self._adapter.insert(table, data, returning=returning)
            logger.info(f"Successfully inserted into {table}")
            return result
        except Exception as e:
            logger.error(f"Insert failed on table {table}: {e}")
            raise

    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any],
        *,
        returning: Optional[str] = None,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Update records.

        Args:
            table: Table name
            data: Data to update
            filters: Filter conditions for which records to update
            returning: Columns to return (default: all)

        Returns:
            Updated record(s)
        """
        try:
            logger.debug(f"Updating records in {table}")
            result = await self._adapter.update(table, data, filters, returning=returning)
            logger.info(f"Successfully updated records in {table}")
            return result
        except Exception as e:
            logger.error(f"Update failed on table {table}: {e}")
            raise

    async def delete(self, table: str, filters: Dict[str, Any]) -> int:
        """Delete records.

        Args:
            table: Table name
            filters: Filter conditions for which records to delete

        Returns:
            Number of deleted records
        """
        try:
            logger.debug(f"Deleting records from {table}")
            count = await self._adapter.delete(table, filters)
            logger.info(f"Deleted {count} record(s) from {table}")
            return count
        except Exception as e:
            logger.error(f"Delete failed on table {table}: {e}")
            raise


def create_resource_adapter() -> MCPResourceAdapter:
    """Create a resource monitor adapter.

    Returns:
        MCPResourceAdapter instance

    Example:
        adapter = create_resource_adapter()
        adapter.register_process("server", port=8000)
    """
    monitor = ProcessMonitor()
    return MCPResourceAdapter(monitor)


__all__ = [
    "MCPClientAdapter",
    "MCPResourceAdapter",
    "MCPDatabaseAdapter",
    "create_resource_adapter",
]
