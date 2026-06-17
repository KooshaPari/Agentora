from __future__ import annotations

import asyncio
import hashlib
from functools import lru_cache
from typing import TYPE_CHECKING, Protocol

from pheno.analytics.ast.models import AstNode
from pheno.analytics.exceptions import AnalyticsDependencyError
from pheno.logging.core.logger import get_logger

if TYPE_CHECKING:
    from pheno.utilities.cache.base import CacheProtocol

logger = get_logger("pheno.analytics.ast")

try:  # pragma: no cover - optional dependency
    from tree_sitter import Parser  # type: ignore
    from tree_sitter_languages import get_language  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    Parser = None
    get_language = None


class TreeSitterAdapter(Protocol):
    async def parse(self, source: str | bytes) -> AstNode: ...

    async def query(self, source: str | bytes, *, pattern: str) -> list[AstNode]: ...


@lru_cache(maxsize=16)
def get_adapter(language: str, *, cache: CacheProtocol | None = None) -> TreeSitterAdapter:
    if Parser is None or get_language is None:
        raise AnalyticsDependencyError("tree-sitter", extra="analytics-ast")
    language = language.lower()
    try:
        language_obj = get_language(language)
    except Exception as exc:  # pragma: no cover - defensive narrow path
        raise RuntimeError(f"Unsupported or unavailable tree-sitter grammar: {language}") from exc

    parser = Parser()
    parser.language = language_obj
    return _TreeSitterAdapter(parser=parser, language=language, cache=cache)


class _TreeSitterAdapter:
    def __init__(self, *, parser, language: str, cache: CacheProtocol | None) -> None:
        self._parser = parser
        self._language = language
        self._cache = cache

    async def parse(self, source: str | bytes) -> AstNode:
        key = None
        if self._cache is not None:
            digest = hashlib.sha256(_ensure_bytes(source)).hexdigest()
            key = ("ast.parse", self._language, digest)
            cached = await self._cache.get(key)
            if cached is not None:
                return cached

        tree = await asyncio.to_thread(self._parser.parse, _ensure_bytes(source))
        node = _convert_node(tree.root_node)

        if self._cache is not None and key is not None:
            await self._cache.set(key, node)
        return node

    async def query(self, source: str | bytes, *, pattern: str) -> list[AstNode]:
        root = await self.parse(source)
        return _query_nodes(root, pattern)


def _ensure_bytes(source: str | bytes) -> bytes:
    if isinstance(source, bytes):
        return source
    return source.encode("utf-8")


def _convert_node(ts_node) -> AstNode:  # type: ignore[no-untyped-def]
    text = ts_node.text.decode("utf-8", errors="ignore")
    children = tuple(_convert_node(child) for child in ts_node.children)
    return AstNode(
        type=ts_node.type,
        text=text,
        start_point=ts_node.start_point,
        end_point=ts_node.end_point,
        children=children,
    )


def _query_nodes(node: AstNode, pattern: str) -> list[AstNode]:
    # Basic substring matching fallback; tree-sitter query DSL would live here once available.
    results: list[AstNode] = []
    if pattern in node.type or pattern in node.text:
        results.append(node)
    for child in node.children:
        results.extend(_query_nodes(child, pattern))
    return results
