"""Framework adapters for multi-agent orchestration.

This module provides framework-specific adapters that implement the FrameworkAdapterPort
protocol for different orchestration frameworks.
"""

from .crewai_adapter import CrewAIAdapter

__all__ = ["CrewAIAdapter"]
