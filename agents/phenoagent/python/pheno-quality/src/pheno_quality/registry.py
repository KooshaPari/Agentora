"""
Quality analysis tool registry.
"""

from typing import Any

from .core import QualityAnalyzer, QualityConfig


class QualityToolRegistry:
    """
    Registry for quality analysis tools.
    """

    def __init__(self):
        self._tools: dict[str, type[QualityAnalyzer]] = {}
        self._tool_configs: dict[str, dict[str, Any]] = {}
        self._tool_metadata: dict[str, dict[str, Any]] = {}

    def register_tool(
        self,
        name: str,
        tool_class: type[QualityAnalyzer],
        config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Register a quality analysis tool.
        """
        self._tools[name] = tool_class
        self._tool_configs[name] = config or {}
        self._tool_metadata[name] = metadata or {}

    def unregister_tool(self, name: str) -> None:
        """
        Unregister a tool.
        """
        if name in self._tools:
            del self._tools[name]
        if name in self._tool_configs:
            del self._tool_configs[name]
        if name in self._tool_metadata:
            del self._tool_metadata[name]

    def get_tool_class(self, name: str) -> type[QualityAnalyzer] | None:
        """
        Get a tool class by name.
        """
        return self._tools.get(name)

    def create_tool(
        self, name: str, config: QualityConfig | None = None,
    ) -> QualityAnalyzer | None:
        """
        Create a tool instance.
        """
        tool_class = self.get_tool_class(name)
        if tool_class:
            # Merge with registered config
            tool_config = self._tool_configs.get(name, {})
            if config:
                # Merge configs
                merged_config = QualityConfig()
                merged_config.enabled_tools = config.enabled_tools or tool_config.get(
                    "enabled_tools", [],
                )
                merged_config.thresholds = {
                    **tool_config.get("thresholds", {}),
                    **config.thresholds,
                }
                merged_config.filters = {**tool_config.get("filters", {}), **config.filters}
                merged_config.output_format = config.output_format or tool_config.get(
                    "output_format", "json",
                )
                merged_config.output_path = config.output_path or tool_config.get("output_path")
                merged_config.include_metadata = (
                    config.include_metadata
                    if config.include_metadata is not None
                    else tool_config.get("include_metadata", True)
                )
                merged_config.parallel_analysis = (
                    config.parallel_analysis
                    if config.parallel_analysis is not None
                    else tool_config.get("parallel_analysis", True)
                )
                merged_config.max_workers = config.max_workers or tool_config.get("max_workers", 4)
                merged_config.timeout_seconds = config.timeout_seconds or tool_config.get(
                    "timeout_seconds", 300,
                )
                return tool_class(name, merged_config)
            return tool_class(name, QualityConfig.from_dict(tool_config))
        return None

    def list_tools(self) -> list[str]:
        """
        List all registered tool names.
        """
        return list(self._tools.keys())

    def get_tool_info(self, name: str) -> dict[str, Any] | None:
        """
        Get tool information.
        """
        if name not in self._tools:
            return None

        return {
            "name": name,
            "class": self._tools[name].__name__,
            "config": self._tool_configs.get(name, {}),
            "metadata": self._tool_metadata.get(name, {}),
        }

    def get_tool_config(self, name: str) -> dict[str, Any]:
        """
        Get tool configuration.
        """
        return self._tool_configs.get(name, {})

    def update_tool_config(self, name: str, config: dict[str, Any]) -> None:
        """
        Update tool configuration.
        """
        if name in self._tool_configs:
            self._tool_configs[name].update(config)

    def get_tool_metadata(self, name: str) -> dict[str, Any]:
        """
        Get tool metadata.
        """
        return self._tool_metadata.get(name, {})

    def update_tool_metadata(self, name: str, metadata: dict[str, Any]) -> None:
        """
        Update tool metadata.
        """
        if name in self._tool_metadata:
            self._tool_metadata[name].update(metadata)

    def get_tools_by_category(self, category: str) -> list[str]:
        """
        Get tools by category.
        """
        return [
            name
            for name, metadata in self._tool_metadata.items()
            if metadata.get("category") == category
        ]

    def get_tools_by_extension(self, extension: str) -> list[str]:
        """
        Get tools that support a file extension.
        """
        return [
            name
            for name, metadata in self._tool_metadata.items()
            if extension in metadata.get("supported_extensions", [])
        ]


# Global tool registry
tool_registry = QualityToolRegistry()
