"""
QA module - hexagonal architecture for QA testing and automation.

This module provides QA testing and automation capabilities
following hexagonal architecture principles.

Domain concepts (this module):
- QualityAssurance: Core QA testing abstraction
- TestSuite: Collection of QA tests
- TestExecution: Test execution context
- QualityReport: QA results and reporting

Ports (pheno.ports.qa):
- QaProvider: Interface for QA implementations
- TestRunner: Interface for test execution
- ReportGenerator: Interface for QA reporting

Adapters (mcp-QA implementations):
- McpQaProvider, CustomQaProvider → QaProvider implementations
"""

from .qa_manager import QaManager
from .types import (
    QaResult,
    QualityAssurance,
    QualityReport,
    TestExecution,
    TestSuite,
)

__all__ = [
    # Manager
    "QaManager",
    "QaResult",
    # Domain types
    "QualityAssurance",
    "QualityReport",
    "TestExecution",
    "TestSuite",
]
