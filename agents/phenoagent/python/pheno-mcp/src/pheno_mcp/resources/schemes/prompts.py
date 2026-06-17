"""
System prompt resource scheme.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from .base import ResourceSchemeHandler

if TYPE_CHECKING:
    from ..template_engine import ResourceContext


class PromptsResourceScheme(ResourceSchemeHandler):
    """Handler for prompts:// resources - system prompts."""

    def __init__(self):
        super().__init__("prompts")

    async def handle_request(self, context: ResourceContext) -> dict[str, Any]:
        """
        Default to listing prompts.
        """
        return await self.list_prompts(context)

    async def get_system_prompt(self, context: ResourceContext) -> dict[str, Any]:
        """
        Get a specific system prompt.
        """
        prompt_name = context.get_parameter("prompt_name")

        if not prompt_name:
            return {"error": "prompt_name parameter is required"}

        system_prompts = context.get_server_info("system_prompts", {})
        prompt_content = system_prompts.get(prompt_name)

        if not prompt_content:
            return {"error": f"System prompt '{prompt_name}' not found"}

        return {
            "prompt": {
                "name": prompt_name,
                "content": prompt_content,
                "length": len(prompt_content),
                "lines": len(prompt_content.splitlines()),
            },
            "timestamp": int(time.time()),
        }

    async def list_prompts(self, context: ResourceContext) -> dict[str, Any]:
        """
        List all available system prompts.
        """
        system_prompts = context.get_server_info("system_prompts", {})

        prompts = []
        for name, content in system_prompts.items():
            prompts.append(
                {
                    "name": name,
                    "description": f"System prompt for {name} tool",
                    "length": len(content),
                    "lines": len(content.splitlines()),
                    "uri": f"prompts://zen/system/{name}",
                },
            )

        prompts.sort(key=lambda prompt: prompt["name"])

        return {
            "prompts": prompts,
            "total": len(prompts),
            "timestamp": int(time.time()),
        }


__all__ = ["PromptsResourceScheme"]
