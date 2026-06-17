"""
Configuration objects and loaders for defining reusable OAuth flows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional

FlowAction = Literal[
    "goto",
    "wait_for_selector",
    "fill",
    "click",
    "sleep",
    "press",
    "select_option",
    "upload_file",
    "wait_for_url",
    "assert_url_contains",
    "evaluate",
    "capture_url",
    "handle_mfa",
]


@dataclass(frozen=True)
class FlowStep:
    """
    Declarative representation of a single automation step.
    """

    action: FlowAction
    description: str = ""
    selector: Optional[str] = None
    value: Optional[str] = None
    credential_key: Optional[str] = None
    wait_for_selector: Optional[str] = None
    expect_navigation: bool = False
    optional: bool = False
    timeout: float = 10.0
    url_substring: Optional[str] = None
    store_key: Optional[str] = None
    query_param: Optional[str] = None
    javascript: Optional[str] = None
    options: Optional[List[str]] = None
    file_paths: Optional[List[str]] = None


@dataclass(frozen=True)
class OAuthFlowConfig:
    """
    Complete automation recipe for a provider.
    """

    provider: str
    steps: Iterable[FlowStep] = field(default_factory=list)
    browser_kwargs: Dict[str, object] = field(default_factory=dict)
    page_kwargs: Dict[str, object] = field(default_factory=dict)
    post_flow_sleep: float = 0.0

    def required_credentials(self) -> List[str]:
        """
        Return unique credential keys referenced by the flow.
        """
        keys = []
        for step in self.steps:
            if step.credential_key and step.credential_key not in keys:
                keys.append(step.credential_key)
        return keys


def flow_step_from_dict(data: Mapping[str, Any]) -> FlowStep:
    """
    Create a :class:`FlowStep` from a mapping (e.g. parsed YAML).
    """

    return FlowStep(
        action=data["action"],
        description=data.get("description", ""),
        selector=data.get("selector"),
        value=data.get("value"),
        credential_key=data.get("credential_key"),
        wait_for_selector=data.get("wait_for_selector"),
        expect_navigation=bool(data.get("expect_navigation", False)),
        optional=bool(data.get("optional", False)),
        timeout=float(data.get("timeout", 10.0)),
        url_substring=data.get("url_substring"),
        store_key=data.get("store_key"),
        query_param=data.get("query_param"),
        javascript=data.get("javascript"),
        options=list(data["options"]) if data.get("options") is not None else None,
        file_paths=list(data["file_paths"]) if data.get("file_paths") is not None else None,
    )


def flow_config_from_dict(data: Mapping[str, Any]) -> OAuthFlowConfig:
    """
    Create an :class:`OAuthFlowConfig` from mapping data.
    """

    steps = [flow_step_from_dict(step) for step in data.get("steps", [])]
    return OAuthFlowConfig(
        provider=data["provider"],
        steps=steps,
        browser_kwargs=dict(data.get("browser_kwargs", {})),
        page_kwargs=dict(data.get("page_kwargs", {})),
        post_flow_sleep=float(data.get("post_flow_sleep", 0.0)),
    )


def load_flow_config_from_yaml(path: Path | str) -> OAuthFlowConfig:
    """
    Load a flow configuration from a YAML file.
    """

    path = Path(path)
    try:
        import yaml  # type: ignore
    except Exception as exc:  # noqa: BLE001 - provide actionable error
        raise RuntimeError(
            "PyYAML is required to load flow configurations from YAML. Install it with 'pip install pyyaml'."
        ) from exc

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, Mapping):
        raise ValueError(f"Unexpected YAML payload in {path}: expected mapping, got {type(data)!r}")

    return flow_config_from_dict(data)
