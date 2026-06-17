"""
ML Resource Templates - Opinionated defaults for common local inference backends.

These helpers mirror the style of :mod:`pheno.kits.infra.templates.resources`
and return dictionaries that can be consumed by the resource factory layer.
"""

from __future__ import annotations

from typing import Any


def _server_template(
    resource_type: str,
    scope: str,
    mode: str,
    start_command: list[str],
    stop_command: list[str],
    health_check: dict[str, Any],
) -> dict[str, Any]:
    """Shared builder for ML server templates."""
    return {
        "type": resource_type,
        "scope": scope,
        "mode": mode,
        "start_command": start_command,
        "stop_command": stop_command,
        "health_check": health_check,
    }


def mlx_server(port: int, model: str, scope: str, mode: str) -> dict[str, Any]:
    """Template for an `mlx_lm` OpenAI-compatible server.

    Args:
        port: Host port the server should bind to.
        model: Identifier passed to ``mlx_lm serve`` (e.g. ``mlx-community/phi-2``).
        scope: Logical grouping used by the orchestration layer.
        mode: Execution mode such as ``local`` or ``remote``.

    Returns:
        Dictionary describing the MLX resource configuration.

    Example:
        >>> from pheno.kits.infra.templates.ml import mlx_server
        >>> config = mlx_server(
        ...     port=8080,
        ...     model="mlx-community/phi-2",
        ...     scope="devtools",
        ...     mode="local",
        ... )
        >>> config["start_command"]
        ['mlx_lm', 'serve', 'mlx-community/phi-2', '--host', '0.0.0.0', '--port', '8080']
    """
    start_cmd = [
        "mlx_lm",
        "serve",
        model,
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]
    stop_cmd = ["pkill", "-f", f"mlx_lm.*--port {port}"]
    health = {"type": "http", "port": port, "path": "/health"}

    return _server_template("mlx", scope, mode, start_cmd, stop_cmd, health)


def vllm_server(
    port: int,
    model: str,
    gpu_memory_utilization: float,
    scope: str,
    mode: str,
) -> dict[str, Any]:
    """Template for a :mod:`vllm` OpenAI-compatible server.

    Args:
        port: Host port to expose the API server.
        model: Model identifier (e.g. ``meta-llama/Meta-Llama-3-8B-Instruct``).
        gpu_memory_utilization: Fraction of VRAM vLLM can use (0-1].
        scope: Logical grouping used by the orchestration layer.
        mode: Execution mode such as ``local`` or ``remote``.

    Returns:
        Dictionary describing the vLLM resource configuration.

    Example:
        >>> from pheno.kits.infra.templates.ml import vllm_server
        >>> config = vllm_server(
        ...     port=9000,
        ...     model="meta-llama/Meta-Llama-3-8B-Instruct",
        ...     gpu_memory_utilization=0.85,
        ...     scope="labs",
        ...     mode="local",
        ... )
        >>> config["health_check"]
        {'type': 'http', 'port': 9000, 'path': '/health'}
    """
    start_cmd = [
        "python",
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        model,
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
        "--gpu-memory-utilization",
        str(gpu_memory_utilization),
    ]
    stop_cmd = ["pkill", "-f", f"vllm.entrypoints.openai.api_server.*--port {port}"]
    health = {"type": "http", "port": port, "path": "/health"}

    return _server_template("vllm", scope, mode, start_cmd, stop_cmd, health)


def ollama_server(port: int, scope: str, mode: str) -> dict[str, Any]:
    """Template for an Ollama background server.

    Args:
        port: Host port the Ollama API should listen on.
        scope: Logical grouping used by the orchestration layer.
        mode: Execution mode such as ``local`` or ``remote``.

    Returns:
        Dictionary describing the Ollama resource configuration.

    Example:
        >>> from pheno.kits.infra.templates.ml import ollama_server
        >>> config = ollama_server(port=11434, scope="research", mode="local")
        >>> config["start_command"][0:3]
        ['env', 'OLLAMA_HOST=0.0.0.0:11434', 'ollama']
    """
    start_cmd = [
        "env",
        f"OLLAMA_HOST=0.0.0.0:{port}",
        "ollama",
        "serve",
    ]
    stop_cmd = ["pkill", "-f", f"OLLAMA_HOST=0.0.0.0:{port}"]
    health = {"type": "http", "port": port, "path": "/api/tags"}

    return _server_template("ollama", scope, mode, start_cmd, stop_cmd, health)

