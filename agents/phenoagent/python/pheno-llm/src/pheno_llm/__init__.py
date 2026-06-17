"""LLM Content Generation Module.

Provides generic functionality for generating titles, status updates, and other content
using various LLM providers.
"""

from .content_generation import (
    ContentGenerationConfig,
    ContentGenerator,
    ContentRequest,
    ContentResponse,
    ContentType,
    generate_session_title,
    generate_status_update,
    get_content_generator,
)
from .task_management import (
    EnhancedTaskManager,
    EnhancedTaskResult,
    ProgressUpdate,
    get_task_manager,
)

__all__ = [
    "ContentGenerationConfig",
    "ContentGenerator",
    "ContentRequest",
    "ContentResponse",
    "ContentType",
    "EnhancedTaskManager",
    "EnhancedTaskResult",
    "ProgressUpdate",
    "generate_session_title",
    "generate_status_update",
    "get_content_generator",
    "get_task_manager",
]
