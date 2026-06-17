"""
MCP-Specific Entry Point Constructors for Pheno SDK
==================================================

This module provides specialized entry point constructors for MCP (Model Context Protocol) servers,
building on top of the base ServiceLauncher and entry point templates.

Key Components:
- MCPEntryPoint: Base class for MCP server entry points
- AtomsMCPEntryPoint: Specialized entry point for Atoms MCP server
- ZenMCPEntryPoint: Specialized entry point for Zen MCP server
- MCPServiceConfig: Configuration class for MCP services
"""

from .atoms import AtomsMCPEntryPoint
from .base import MCPEntryPoint, MCPServiceConfig
from .zen import ZenMCPEntryPoint

__all__ = [
    "AtomsMCPEntryPoint",
    "MCPEntryPoint",
    "MCPServiceConfig",
    "ZenMCPEntryPoint",
]
