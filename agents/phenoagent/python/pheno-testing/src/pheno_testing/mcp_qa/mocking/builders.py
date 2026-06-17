"""
Response builders for common test scenarios.
"""

from typing import Any, Dict, List, Optional


def build_success_response(data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Build a successful tool response.

    Args:
        data: Data to include in response
        **kwargs: Additional fields to include

    Returns:
        Response dict with success=True

    Usage:
        response = build_success_response(
            data={"message": "Done"},
            model="gpt-4"
        )
    """
    response = {"success": True}
    if data:
        response.update(data)
    response.update(kwargs)
    return response


def build_error_response(error: str, error_code: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Build an error response.

    Args:
        error: Error message
        error_code: Optional error code
        **kwargs: Additional fields

    Returns:
        Response dict with success=False

    Usage:
        response = build_error_response(
            error="Invalid input",
            error_code="VALIDATION_ERROR"
        )
    """
    response = {
        "success": False,
        "error": error,
    }
    if error_code:
        response["error_code"] = error_code
    response.update(kwargs)
    return response


def build_list_response(
    items: List[Dict[str, Any]], total: Optional[int] = None, **kwargs
) -> Dict[str, Any]:
    """Build a list response.

    Args:
        items: List of items
        total: Total count (if different from len(items))
        **kwargs: Additional fields

    Returns:
        Response dict with items list

    Usage:
        response = build_list_response(
            items=[{"id": 1}, {"id": 2}],
            total=100,
            page=1
        )
    """
    response = {
        "success": True,
        "items": items,
        "count": len(items),
    }
    if total is not None:
        response["total"] = total
    response.update(kwargs)
    return response
