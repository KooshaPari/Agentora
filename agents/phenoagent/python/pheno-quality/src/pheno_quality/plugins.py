"""
Quality analysis plugin system.
"""

import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Any

from .core import QualityAnalyzer, QualityConfig


class QualityPlugin(ABC):
    """
    Abstract base class for quality analysis plugins.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Plugin name.
        """

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Plugin version.
        """

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Plugin description.
        """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """
        Supported file extensions.
        """

    @abstractmethod
    def create_analyzer(self, config: QualityConfig | None = None) -> QualityAnalyzer:
        """
        Create an analyzer instance.
        """

    @abstractmethod
    def get_default_config(self) -> dict[str, Any]:
        """
        Get default configuration for this plugin.
        """


class PluginRegistry:
    """
    Registry for quality analysis plugins.
    """

    def __init__(self):
        self._plugins: dict[str, QualityPlugin] = {}
        self._analyzers: dict[str, type[QualityAnalyzer]] = {}

    def register_plugin(self, plugin: QualityPlugin) -> None:
        """
        Register a quality analysis plugin.
        """
        self._plugins[plugin.name] = plugin

        # Register the analyzer class
        analyzer_class = plugin.create_analyzer().__class__
        self._analyzers[plugin.name] = analyzer_class

    def unregister_plugin(self, name: str) -> None:
        """
        Unregister a plugin.
        """
        if name in self._plugins:
            del self._plugins[name]
        if name in self._analyzers:
            del self._analyzers[name]

    def get_plugin(self, name: str) -> QualityPlugin | None:
        """
        Get a plugin by name.
        """
        return self._plugins.get(name)

    def get_analyzer_class(self, name: str) -> type[QualityAnalyzer] | None:
        """
        Get an analyzer class by name.
        """
        return self._analyzers.get(name)

    def create_analyzer(
        self, name: str, config: QualityConfig | None = None,
    ) -> QualityAnalyzer | None:
        """
        Create an analyzer instance.
        """
        plugin = self.get_plugin(name)
        if plugin:
            return plugin.create_analyzer(config)
        return None

    def list_plugins(self) -> list[str]:
        """
        List all registered plugin names.
        """
        return list(self._plugins.keys())

    def list_analyzers(self) -> list[str]:
        """
        List all registered analyzer names.
        """
        return list(self._analyzers.keys())

    def get_plugin_info(self, name: str) -> dict[str, Any] | None:
        """
        Get plugin information.
        """
        plugin = self.get_plugin(name)
        if not plugin:
            return None

        return {
            "name": plugin.name,
            "version": plugin.version,
            "description": plugin.description,
            "supported_extensions": plugin.supported_extensions,
            "default_config": plugin.get_default_config(),
        }

    def load_plugin_from_module(self, module_name: str, plugin_class_name: str) -> bool:
        """
        Load a plugin from a Python module.
        """
        try:
            module = importlib.import_module(module_name)
            plugin_class = getattr(module, plugin_class_name)

            if not inspect.isclass(plugin_class) or not issubclass(plugin_class, QualityPlugin):
                return False

            plugin_instance = plugin_class()
            self.register_plugin(plugin_instance)
            return True
        except (ImportError, AttributeError, TypeError):
            return False

    def load_plugins_from_package(self, package_name: str) -> int:
        """
        Load all plugins from a package.
        """
        loaded_count = 0

        try:
            package = importlib.import_module(package_name)

            # Look for plugin classes in the package
            for name in dir(package):
                obj = getattr(package, name)
                if inspect.isclass(obj) and issubclass(obj, QualityPlugin) and obj != QualityPlugin:
                    try:
                        plugin_instance = obj()
                        self.register_plugin(plugin_instance)
                        loaded_count += 1
                    except Exception:
                        continue

        except ImportError:
            pass

        return loaded_count


# Global plugin registry
plugin_registry = PluginRegistry()
