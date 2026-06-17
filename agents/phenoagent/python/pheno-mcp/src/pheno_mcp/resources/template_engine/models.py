"""
Dataclasses and helpers for resource templates.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from re import Pattern
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class ResourceParameter:
    """
    Resource template parameter definition.
    """

    name: str
    type: str = "string"
    required: bool = True
    default: Any | None = None
    description: str = ""
    pattern: str | None = None
    choices: list[Any] | None = None

    def validate(self, value: Any) -> tuple[bool, str]:
        """
        Validate parameter value.
        """
        if value is None:
            if self.required:
                return False, f"Parameter '{self.name}' is required"
            return True, ""

        if self.type == "integer":
            try:
                int(value)
            except (ValueError, TypeError):
                return False, f"Parameter '{self.name}' must be an integer"
        elif self.type == "boolean":
            if not isinstance(value, bool) and str(value).lower() not in {
                "true",
                "false",
                "1",
                "0",
            }:
                return False, f"Parameter '{self.name}' must be a boolean"
        elif self.type == "array" and not isinstance(value, (list, tuple)):
            if isinstance(value, str):
                value = [chunk.strip() for chunk in value.split(",")]
            else:
                return False, f"Parameter '{self.name}' must be an array"

        if self.pattern and isinstance(value, str):
            if not re.match(self.pattern, value):
                return False, f"Parameter '{self.name}' doesn't match required pattern"

        if self.choices and value not in self.choices:
            return (
                False,
                f"Parameter '{self.name}' must be one of: {', '.join(map(str, self.choices))}",
            )

        return True, ""


@dataclass
class ResourceAnnotation:
    """
    Resource annotation for LLM optimization and access control.
    """

    read_only_hint: bool = True
    idempotent_hint: bool = True
    destructive_hint: bool = False
    cache_ttl_seconds: int | None = None
    security_level: str = "public"
    performance_hint: str = "fast"
    content_type: str = "application/json"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "readOnlyHint": self.read_only_hint,
            "idempotentHint": self.idempotent_hint,
            "destructiveHint": self.destructive_hint,
            "cacheTtlSeconds": self.cache_ttl_seconds,
            "securityLevel": self.security_level,
            "performanceHint": self.performance_hint,
            "contentType": self.content_type,
            "description": self.description,
        }


@dataclass
class ResourceContext:
    """
    Context provided to resource handlers.
    """

    uri: str
    parameters: dict[str, Any]
    server_state: dict[str, Any]
    request_metadata: dict[str, Any]
    user_context: dict[str, Any] | None = None
    cache: dict[str, Any] | None = None

    def get_parameter(self, name: str, default: Any = None) -> Any:
        return self.parameters.get(name, default)

    def get_server_info(self, key: str, default: Any = None) -> Any:
        return self.server_state.get(key, default)

    def is_authenticated(self) -> bool:
        return self.user_context is not None

    def get_user_id(self) -> str | None:
        if self.user_context:
            return self.user_context.get("user_id")
        return None


@dataclass
class ResourceTemplate:
    """
    Resource template definition with URI pattern and handler.
    """

    name: str
    uri_pattern: str
    description: str
    handler: Callable[[ResourceContext], Awaitable[dict[str, Any]]]
    parameters: list[ResourceParameter] = field(default_factory=list)
    annotations: ResourceAnnotation = field(default_factory=ResourceAnnotation)
    scheme: str = "zen"
    enabled: bool = True

    _pattern: Pattern | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._compile_pattern()

    def _compile_pattern(self) -> None:
        try:

            def replace(match: re.Match[str]) -> str:
                group_name = match.group(1)
                return f"(?P<{group_name}>[^/]+)"

            pattern = re.sub(r"\{([^}]+)\}", replace, self.uri_pattern)
            pattern = pattern.replace("*", ".*")
            pattern = f"^{pattern}$"
            self._pattern = re.compile(pattern)
        except re.error as exc:
            logger.exception("Invalid URI pattern '%s': %s", self.uri_pattern, exc)
            self._pattern = None

    def matches(self, uri: str) -> bool:
        return bool(self._pattern and self._pattern.match(uri))

    def extract_parameters(self, uri: str) -> dict[str, str]:
        if not self._pattern:
            return {}
        match = self._pattern.match(uri)
        return match.groupdict() if match else {}

    def validate_parameters(self, params: dict[str, Any]) -> tuple[bool, list[str]]:
        errors: list[str] = []
        for param_def in self.parameters:
            value = params.get(param_def.name)
            valid, msg = param_def.validate(value)
            if not valid:
                errors.append(msg)
        return len(errors) == 0, errors

    def parse_query_parameters(self, uri: str) -> dict[str, Any]:
        parsed = urlparse(uri)
        query_params: dict[str, Any] = {}
        if parsed.query:
            for key, values in parse_qs(parsed.query).items():
                query_params[key] = values[0] if len(values) == 1 else values
        return query_params


__all__ = [
    "ResourceAnnotation",
    "ResourceContext",
    "ResourceParameter",
    "ResourceTemplate",
]
