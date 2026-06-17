"""Process Management Utilities.

Common utilities for port checking, process detection, and termination.
Extracted from smart_allocator.py, service_manager.py, and tunnel_manager.py.

This module re-exports process functionality from specialized modules:
- Process lifecycle management: terminate_process, cleanup_orphaned_processes
- Platform-specific shims: port checking, process detection
- Process monitoring: ProcessMonitor, ProcessMetrics
"""

from pheno.infra.utils.platform_shims import (
    _is_likely_our_cmd,
    _kill_via_lsof,
    free_port_if_likely_ours,
    get_port_occupant,
    is_port_free,
    kill_processes_on_port,
)

# Import for circular dependency handling
from pheno.infra.utils.process_lifecycle import (
    cleanup_orphaned_processes,
    terminate_process,
)
from pheno.infra.utils.process_monitoring import ProcessMetrics, ProcessMonitor

# Re-export all functionality for backward compatibility
__all__ = [
    # Process monitoring
    "ProcessMetrics",
    "ProcessMonitor",
    "_is_likely_our_cmd",
    "_kill_via_lsof",
    "cleanup_orphaned_processes",
    "free_port_if_likely_ours",
    "get_port_occupant",
    # Platform shims
    "is_port_free",
    "kill_processes_on_port",
    # Process lifecycle
    "terminate_process",
]
