"""
OpenRouter LLM Provider for Content Generation.
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx

from ..content_generation import ContentGenerationConfig, ContentResponse

logger = logging.getLogger(__name__)


class OpenRouterProvider:
    """
    OpenRouter provider for LLM content generation.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = base_url or "https://openrouter.ai/api/v1"

    async def generate_content(
        self, prompt: str, system_prompt: str, config: ContentGenerationConfig,
    ) -> ContentResponse:
        """
        Generate content using OpenRouter API.
        """
        if not self.api_key:
            raise ValueError("OpenRouter API key not found")

        start_time = asyncio.get_event_loop().time()

        try:
            async with httpx.AsyncClient(timeout=config.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": config.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": config.max_tokens,
                        "temperature": config.temperature,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"].strip()

                    # Clean up content
                    if not config.include_quotes:
                        content = content.strip("\"'.,!?")

                    # Apply length constraints
                    if len(content) > config.max_length:
                        content = content[: config.max_length].strip() + "..."

                    generation_time = asyncio.get_event_loop().time() - start_time

                    return ContentResponse(
                        content=content,
                        success=True,
                        provider_used="openrouter",
                        generation_time=generation_time,
                        tokens_used=data.get("usage", {}).get("total_tokens"),
                    )
                error_msg = f"OpenRouter API error: {response.status_code}"
                logger.warning(error_msg)
                raise Exception(error_msg)

        except Exception as e:
            logger.warning(f"OpenRouter generation failed: {e}")
            raise
