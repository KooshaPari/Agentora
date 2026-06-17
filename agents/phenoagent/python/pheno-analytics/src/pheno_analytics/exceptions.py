from __future__ import annotations


class AnalyticsDependencyError(RuntimeError):
    """
    Raised when an analytics dependency is missing.
    """

    def __init__(self, package: str, extra: str | None = None) -> None:
        message = f"{package} is not installed. Install the optional extra to enable analytics."
        if extra:
            message += f" For example: pip install pheno-sdk[{extra}]"
        super().__init__(message)
