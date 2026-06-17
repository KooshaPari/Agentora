"""
Suggestion helpers for WildcardStatusHandler.
"""

from __future__ import annotations

from typing import Any


def calculate_similarity(str1: str, str2: str) -> float:
    str1 = (str1 or "").lower()
    str2 = (str2 or "").lower()
    if str1 == str2:
        return 1.0
    if str1 in str2 or str2 in str1:
        return 0.8
    parts1 = set(str1.strip("/").split("/"))
    parts2 = set(str2.strip("/").split("/"))
    if not parts1 or not parts2:
        return 0.0
    intersection = len(parts1.intersection(parts2))
    union = len(parts1.union(parts2))
    if union == 0:
        return 0.0
    return intersection / union


def get_route_suggestions(
    requested_path: str, routes: list[dict[str, str]],
) -> list[dict[str, str]]:
    suggestions: list[dict[str, Any]] = []
    for route in routes:
        route_path = route.get("path", "")
        similarity = calculate_similarity(requested_path, route_path)
        if similarity > 0.3:
            suggestions.append({**route, "similarity": similarity})
    suggestions.sort(key=lambda x: x["similarity"], reverse=True)
    return [{k: v for k, v in s.items() if k != "similarity"} for s in suggestions]
