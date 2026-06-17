"""Generic LLM Content Generation Library.

Provides reusable functionality for generating titles, status updates, and other content
using various LLM providers. Designed to be provider-agnostic and easily configurable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """
    Types of content that can be generated.
    """

    TITLE = "title"
    STATUS_UPDATE = "status_update"
    DESCRIPTION = "description"
    SUMMARY = "summary"
    CUSTOM = "custom"


@dataclass
class ContentGenerationConfig:
    """
    Configuration for content generation.
    """

    # Provider settings
    provider: str = "openrouter"
    model: str = "gpt-oss-20b:free"
    api_key_env: str = "OPENROUTER_API_KEY"
    base_url: str | None = None

    # Generation settings
    max_tokens: int = 50
    temperature: float = 0.7
    max_retries: int = 3
    timeout: float = 10.0

    # Content settings
    max_length: int = 50
    max_words: int = 10
    include_quotes: bool = False
    include_punctuation: bool = False

    # Caching
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour

    # Fallback
    enable_fallback: bool = True
    fallback_strategies: list[str] = field(default_factory=lambda: ["truncate", "template"])


@dataclass
class ContentRequest:
    """
    Request for content generation.
    """

    content_type: ContentType
    prompt: str
    context: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_type": self.content_type.value,
            "prompt": self.prompt,
            "context": self.context or {},
            "constraints": self.constraints or {},
            "session_id": self.session_id,
        }


@dataclass
class ContentResponse:
    """
    Response from content generation.
    """

    content: str
    success: bool
    provider_used: str | None = None
    generation_time: float = 0.0
    tokens_used: int | None = None
    cached: bool = False
    fallback_used: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "success": self.success,
            "provider_used": self.provider_used,
            "generation_time": self.generation_time,
            "tokens_used": self.tokens_used,
            "cached": self.cached,
            "fallback_used": self.fallback_used,
            "error": self.error,
        }


class LLMProvider(Protocol):
    """
    Protocol for LLM providers.
    """

    async def generate_content(
        self, prompt: str, system_prompt: str, config: ContentGenerationConfig,
    ) -> ContentResponse:
        """
        Generate content using the LLM provider.
        """
        ...


class ContentGenerator:
    """
    Generic content generator using various LLM providers.
    """

    def __init__(
        self,
        config: ContentGenerationConfig | None = None,
        providers: dict[str, LLMProvider] | None = None,
    ):
        self.config = config or ContentGenerationConfig()
        self.providers = providers or {}
        self.cache: dict[str, ContentResponse] = {}

        # Register default providers
        self._register_default_providers()

    def _register_default_providers(self):
        """
        Register default LLM providers.
        """
        try:
            from .providers.openrouter_provider import OpenRouterProvider

            self.providers["openrouter"] = OpenRouterProvider()
        except ImportError:
            logger.warning("OpenRouter provider not available")

        try:
            from .providers.openai_provider import OpenAIProvider

            self.providers["openai"] = OpenAIProvider()
        except ImportError:
            logger.warning("OpenAI provider not available")

    async def generate_title(
        self, prompt: str, max_length: int = 50, session_id: str | None = None,
    ) -> ContentResponse:
        """
        Generate a title for a given prompt.
        """
        request = ContentRequest(
            content_type=ContentType.TITLE,
            prompt=prompt,
            constraints={"max_length": max_length},
            session_id=session_id,
        )
        return await self._generate_content(request)

    async def generate_status_update(
        self,
        prompt: str,
        current_step: str,
        progress: float,
        max_words: int = 10,
        session_id: str | None = None,
    ) -> ContentResponse:
        """
        Generate a status update message.
        """
        request = ContentRequest(
            content_type=ContentType.STATUS_UPDATE,
            prompt=prompt,
            context={"current_step": current_step, "progress": progress},
            constraints={"max_words": max_words},
            session_id=session_id,
        )
        return await self._generate_content(request)

    async def generate_custom_content(
        self,
        prompt: str,
        content_type: str,
        context: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> ContentResponse:
        """
        Generate custom content with specified type.
        """
        request = ContentRequest(
            content_type=ContentType.CUSTOM,
            prompt=prompt,
            context=context,
            constraints=constraints,
            session_id=session_id,
        )
        return await self._generate_content(request)

    async def _generate_content(self, request: ContentRequest) -> ContentResponse:
        """
        Generate content using the configured provider.
        """
        # Check cache first
        if self.config.enable_caching and request.session_id:
            cache_key = self._get_cache_key(request)
            if cache_key in self.cache:
                cached_response = self.cache[cache_key]
                cached_response.cached = True
                return cached_response

        # Get provider
        provider = self.providers.get(self.config.provider)
        if not provider:
            return self._create_fallback_response(request, "No provider available")

        # Generate system prompt
        system_prompt = self._create_system_prompt(request)

        # Generate content
        try:
            response = await provider.generate_content(
                prompt=request.prompt, system_prompt=system_prompt, config=self.config,
            )

            # Cache successful responses
            if self.config.enable_caching and request.session_id and response.success:
                cache_key = self._get_cache_key(request)
                self.cache[cache_key] = response

            return response

        except Exception as e:
            logger.warning(f"Content generation failed: {e}")
            return self._create_fallback_response(request, str(e))

    def _create_system_prompt(self, request: ContentRequest) -> str:
        """
        Create system prompt based on content type.
        """
        if request.content_type == ContentType.TITLE:
            return (
                "You are a title generator. Generate a concise, descriptive title "
                "for a task based on the user's prompt. The title should be 3-8 words, "
                "clear, and professional. Do not use quotes or punctuation at the end. "
                "Just return the title, nothing else."
            )
        if request.content_type == ContentType.STATUS_UPDATE:
            return (
                "You are a status message generator. Generate a brief, engaging status "
                "message that describes what's happening in a task. "
                "Be creative and friendly, like Vercel or Anthropic progress messages. "
                "Just return the status message, nothing else. No quotes or punctuation at the end."
            )
        return (
            "You are a content generator. Generate appropriate content based on the user's request. "
            "Be concise, clear, and professional. Just return the content, nothing else."
        )

    def _create_fallback_response(self, request: ContentRequest, error: str) -> ContentResponse:
        """
        Create fallback response when generation fails.
        """
        if not self.config.enable_fallback:
            return ContentResponse(content="", success=False, error=error)

        # Generate fallback content
        if request.content_type == ContentType.TITLE:
            content = self._fallback_title(request.prompt, request.constraints)
        elif request.content_type == ContentType.STATUS_UPDATE:
            content = self._fallback_status(request.context)
        else:
            content = self._fallback_generic(request.prompt)

        return ContentResponse(content=content, success=True, fallback_used=True, error=error)

    def _fallback_title(self, prompt: str, constraints: dict[str, Any] | None) -> str:
        """
        Generate fallback title.
        """
        max_length = constraints.get("max_length", 50) if constraints else 50
        title = prompt[:max_length].strip()
        if len(prompt) > max_length:
            title = title + "..."
        return title

    def _fallback_status(self, context: dict[str, Any] | None) -> str:
        """
        Generate fallback status message.
        """
        if not context:
            return "Processing..."

        current_step = context.get("current_step", "processing")
        return current_step.replace("_", " ").title()

    def _fallback_generic(self, prompt: str) -> str:
        """
        Generate fallback generic content.
        """
        return prompt[:50].strip()

    def _get_cache_key(self, request: ContentRequest) -> str:
        """
        Generate cache key for request.
        """
        return f"{request.content_type.value}:{request.prompt}:{request.session_id or 'default'}"


# Convenience functions for backward compatibility
async def generate_session_title(
    prompt: str,
    max_length: int = 50,
    session_id: str | None = None,
    config: ContentGenerationConfig | None = None,
) -> str:
    """
    Generate a session title (convenience function).
    """
    generator = ContentGenerator(config)
    response = await generator.generate_title(prompt, max_length, session_id)
    return response.content


async def generate_status_update(
    prompt: str,
    current_step: str,
    progress: float,
    max_words: int = 10,
    session_id: str | None = None,
    config: ContentGenerationConfig | None = None,
) -> str:
    """
    Generate a status update (convenience function).
    """
    generator = ContentGenerator(config)
    response = await generator.generate_status_update(
        prompt, current_step, progress, max_words, session_id,
    )
    return response.content


# Global instance for easy access
_default_generator: ContentGenerator | None = None


def get_content_generator(config: ContentGenerationConfig | None = None) -> ContentGenerator:
    """
    Get the global content generator instance.
    """
    global _default_generator
    if _default_generator is None:
        _default_generator = ContentGenerator(config)
    return _default_generator
