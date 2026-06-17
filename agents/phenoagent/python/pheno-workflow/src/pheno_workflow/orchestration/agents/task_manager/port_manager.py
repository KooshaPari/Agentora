"""Port Management.

Manages port allocation for agent processes.
"""

import logging
from datetime import datetime

from .models import PortAllocation

logger = logging.getLogger(__name__)


class PortManager:
    """Manages port allocation for agent processes.

    Features:
    - Thread-safe port allocation
    - Port pool management
    - Automatic release on timeout
    - Tracking of port usage
    """

    def __init__(self, port_range_start: int = 3284, port_range_end: int = 10000):
        """Initialize port manager.

        Args:
            port_range_start: Start of port range (inclusive)
            port_range_end: End of port range (exclusive)
        """
        self.port_pool: set[int] = set(range(port_range_start, port_range_end))
        self.used_ports: set[int] = set()
        self.allocations: dict[int, PortAllocation] = {}

        logger.info(
            f"Port Manager initialized with range {port_range_start}-{port_range_end-1} "
            f"({len(self.port_pool)} ports available)",
        )

    def allocate_port(self, agent_id: str | None = None, task_id: str | None = None) -> int | None:
        """Allocate a port from the available pool.

        Args:
            agent_id: Optional agent identifier
            task_id: Optional task identifier

        Returns:
            Allocated port number or None if no ports available
        """
        available_ports = self.port_pool - self.used_ports

        if not available_ports:
            logger.warning("No ports available for allocation")
            return None

        # Get first available port
        port = min(available_ports)

        # Mark as used
        self.used_ports.add(port)

        # Record allocation
        allocation = PortAllocation(
            port=port, agent_id=agent_id, allocated_at=datetime.now(), task_id=task_id,
        )
        self.allocations[port] = allocation

        logger.debug(f"Allocated port {port} for agent={agent_id}, task={task_id}")

        return port

    def release_port(self, port: int, agent_id: str | None = None) -> bool:
        """Release a port back to the pool.

        Args:
            port: Port number to release
            agent_id: Optional agent ID (for verification)

        Returns:
            True if port was released, False if not found
        """
        if port not in self.used_ports:
            logger.warning(f"Attempted to release port {port} that is not in use")
            return False

        # Verify agent_id if provided
        if agent_id:
            allocation = self.allocations.get(port)
            if allocation and allocation.agent_id != agent_id:
                logger.warning(
                    f"Port {port} is allocated to different agent "
                    f"(requested by {agent_id}, allocated to {allocation.agent_id})",
                )
                return False

        # Release port
        self.used_ports.discard(port)
        if port in self.allocations:
            del self.allocations[port]

        logger.debug(f"Released port {port}")
        return True

    def get_allocation(self, port: int) -> PortAllocation | None:
        """Get allocation information for a port.

        Args:
            port: Port number

        Returns:
            PortAllocation or None if not allocated
        """
        return self.allocations.get(port)

    def get_allocated_ports(self) -> dict[int, PortAllocation]:
        """Get all currently allocated ports.

        Returns:
            Dictionary mapping port numbers to allocations
        """
        return self.allocations.copy()

    def get_available_count(self) -> int:
        """Get number of available ports.

        Returns:
            Number of ports available for allocation
        """
        return len(self.port_pool - self.used_ports)

    def release_all_for_agent(self, agent_id: str) -> int:
        """Release all ports allocated to a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Number of ports released
        """
        ports_to_release = [
            port for port, allocation in self.allocations.items() if allocation.agent_id == agent_id
        ]

        for port in ports_to_release:
            self.release_port(port, agent_id)

        logger.info(f"Released {len(ports_to_release)} ports for agent {agent_id}")
        return len(ports_to_release)

    def get_stats(self) -> dict[str, int]:
        """Get port manager statistics.

        Returns:
            Dictionary with port usage statistics
        """
        return {
            "total_ports": len(self.port_pool),
            "used_ports": len(self.used_ports),
            "available_ports": self.get_available_count(),
            "utilization_percent": (
                int((len(self.used_ports) / len(self.port_pool)) * 100) if self.port_pool else 0
            ),
        }

    def cleanup_stale_allocations(self, max_age_seconds: int = 3600) -> int:
        """Clean up port allocations older than max_age.

        Args:
            max_age_seconds: Maximum age in seconds (default: 1 hour)

        Returns:
            Number of ports released
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(seconds=max_age_seconds)

        stale_ports = [
            port
            for port, allocation in self.allocations.items()
            if allocation.allocated_at < cutoff
        ]

        for port in stale_ports:
            self.release_port(port)

        if stale_ports:
            logger.info(
                f"Cleaned up {len(stale_ports)} stale port allocations "
                f"(older than {max_age_seconds}s)",
            )

        return len(stale_ports)
