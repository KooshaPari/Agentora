from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AstNode:
    """
    Simplified AST node representation.
    """

    type: str
    text: str
    start_point: tuple[int, int]
    end_point: tuple[int, int]
    children: tuple[AstNode, ...] = ()
