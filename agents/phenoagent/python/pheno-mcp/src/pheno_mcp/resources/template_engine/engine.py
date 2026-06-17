"""
Core engine implementation for resource templates.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from .models import ResourceContext, ResourceTemplate

logger = logging.getLogger(__name__)


class ResourceTemplateEngine:
    """
    Engine for managing and executing resource templates.
    """

    def __init__(self) -> None:
        self.templates: dict[str, ResourceTemplate] = {}
        self.schemes: dict[str, list[ResourceTemplate]] = {}
        self.cache: dict[str, tuple[Any, float]] = {}
        self.cache_ttl: int = 300

    # ------------------------------------------------------------------
    # Registration & lookup
    # ------------------------------------------------------------------
    def register_template(self, template: ResourceTemplate) -> bool:
        if not template.enabled:
            logger.debug("Template '%s' is disabled, skipping registration", template.name)
            return False

        existing = self.templates.get(template.name)
        if existing is not None:
            if existing.uri_pattern == template.uri_pattern and existing.scheme == template.scheme:
                logger.debug("Template '%s' already registered; skipping duplicate", template.name)
                return False
            logger.debug(
                "Template name '%s' already present; skipping duplicate registration", template.name,
            )
            return False

        for tpl in self.templates.values():
            if tpl.uri_pattern == template.uri_pattern and tpl.scheme == template.scheme:
                logger.debug(
                    "Template for '%s' already present as '%s'; skipping duplicate",
                    template.uri_pattern,
                    tpl.name,
                )
                return False

        self.templates[template.name] = template
        self.schemes.setdefault(template.scheme, [])
        if not any(
            t.name == template.name or t.uri_pattern == template.uri_pattern
            for t in self.schemes[template.scheme]
        ):
            self.schemes[template.scheme].append(template)

        logger.debug("Registered resource template: %s (%s)", template.name, template.uri_pattern)
        return True

    def find_template(self, uri: str) -> ResourceTemplate | None:
        parsed = json.loads(f"{{\"scheme\": \"{uri.split(':', 1)[0] or 'zen'}\"}}")
        scheme = parsed.get("scheme", "zen")

        for template in self.schemes.get(scheme, []):
            if template.matches(uri):
                return template

        for template in self.templates.values():
            if template.matches(uri):
                return template

        return None

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------
    def _get_cache_key(self, uri: str, params: dict[str, Any]) -> str:
        param_str = json.dumps(params, sort_keys=True) if params else ""
        return f"{uri}#{param_str}"

    def _is_cache_valid(self, cache_entry: tuple[Any, float], ttl: int) -> bool:
        if ttl <= 0:
            return False
        _, timestamp = cache_entry
        return time.time() - timestamp < ttl

    async def _cleanup_cache(self) -> None:
        current_time = time.time()
        expired_keys = [
            key for key, (_, ts) in self.cache.items() if current_time - ts > self.cache_ttl
        ]
        for key in expired_keys:
            self.cache.pop(key, None)
        if expired_keys:
            logger.debug("Cleaned %d expired cache entries", len(expired_keys))

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    async def execute_template(
        self,
        uri: str,
        server_state: dict[str, Any],
        request_metadata: dict[str, Any] | None = None,
        user_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        template = self.find_template(uri)
        if not template:
            raise ValueError(f"No template found for URI: {uri}")

        extracted_params = template.extract_parameters(uri)
        query_params = template.parse_query_parameters(uri)
        all_params = {**extracted_params, **query_params}

        for param_def in template.parameters:
            if param_def.name not in all_params and param_def.default is not None:
                all_params[param_def.name] = param_def.default

        valid, errors = template.validate_parameters(all_params)
        if not valid:
            raise ValueError(f"Parameter validation failed: {'; '.join(errors)}")

        cache_ttl = template.annotations.cache_ttl_seconds or 0
        if cache_ttl > 0:
            cache_key = self._get_cache_key(uri, all_params)
            cache_entry = self.cache.get(cache_key)
            if cache_entry and self._is_cache_valid(cache_entry, cache_ttl):
                logger.debug("Cache hit for URI: %s", uri)
                return cache_entry[0]

        context = ResourceContext(
            uri=uri,
            parameters=all_params,
            server_state=server_state,
            request_metadata=request_metadata or {},
            user_context=user_context,
            cache={},
        )

        start_time = time.time()
        result = await template.handler(context)
        execution_time = time.time() - start_time

        if isinstance(result, dict):
            result.setdefault("_metadata", {})
            result["_metadata"].update(
                {
                    "template": template.name,
                    "uri": uri,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "cache_enabled": cache_ttl > 0,
                    "timestamp": int(time.time()),
                },
            )

        if cache_ttl > 0:
            cache_key = self._get_cache_key(uri, all_params)
            self.cache[cache_key] = (result, time.time())
            if len(self.cache) > 1000:
                await self._cleanup_cache()

        logger.debug(
            "Executed template '%s' for URI '%s' in %.3fs", template.name, uri, execution_time,
        )
        return result

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def get_template_info(self, name: str) -> dict[str, Any] | None:
        template = self.templates.get(name)
        if not template:
            return None
        return {
            "name": template.name,
            "uri_pattern": template.uri_pattern,
            "description": template.description,
            "scheme": template.scheme,
            "parameters": [
                {
                    "name": param.name,
                    "type": param.type,
                    "required": param.required,
                    "default": param.default,
                    "description": param.description,
                    "pattern": param.pattern,
                    "choices": param.choices,
                }
                for param in template.parameters
            ],
            "annotations": template.annotations.to_dict(),
            "enabled": template.enabled,
        }

    def list_templates(
        self, scheme: str | None = None, enabled_only: bool = True,
    ) -> list[dict[str, Any]]:
        templates: list[dict[str, Any]] = []
        for template in self.templates.values():
            if enabled_only and not template.enabled:
                continue
            if scheme and template.scheme != scheme:
                continue
            info = self.get_template_info(template.name)
            if info:
                templates.append(info)
        return sorted(templates, key=lambda t: (t["scheme"], t["name"]))

    def get_cache_stats(self) -> dict[str, Any]:
        return {
            "total_entries": len(self.cache),
            "cache_ttl_seconds": self.cache_ttl,
            "memory_usage_estimate": len(str(self.cache)),
        }

    def clear_cache(self, uri_pattern: str | None = None) -> None:
        if uri_pattern:
            pattern = re.compile(uri_pattern)
            keys_to_remove = [key for key in self.cache if pattern.search(key.split("#")[0])]
            for key in keys_to_remove:
                self.cache.pop(key, None)
            logger.info(
                "Cleared %d cache entries matching pattern: %s", len(keys_to_remove), uri_pattern,
            )
        else:
            self.cache.clear()
            logger.info("Cleared all cache entries")
