"""
Vector Database Templates

Provides ready-to-use configuration dictionaries for popular vector database backends.
Each helper returns a dictionary that follows the same structure used by other KInfra
templates, making it simple to spin up local vector infrastructure or point to managed
deployments by adjusting the scope/mode metadata.
"""

from pathlib import Path
from typing import Any


def qdrant(
    port: int = 6333,
    scope: str = "project",
    mode: str = "local",
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a Qdrant vector database configuration.

    Args:
        port: Host port that forwards to Qdrant's HTTP API (container port 6333).
        scope: Resource scope identifier (e.g., ``"project"``, ``"workspace"``).
        mode: Resource mode (e.g., ``"local"``, ``"cloud"``) used by higher-level tooling.
        **kwargs: Additional configuration entries (environment, volumes, etc.).

    Returns:
        Dictionary describing the Qdrant deployment, suitable for ``ResourceFactory``.

    Example:
        >>> from pheno.kits.infra.templates import vectors
        >>> config = vectors.qdrant(port=7443, scope="workspace", mode="local")
        >>> config["ports"][7443]
        6333
    """
    image = kwargs.pop("image", "qdrant/qdrant:latest")
    container_name = kwargs.pop("container_name", f"kinfra-qdrant-{port}")
    cleanup_on_stop = kwargs.pop("cleanup_on_stop", True)
    restart_policy = kwargs.pop("restart_policy", "unless-stopped")
    grpc_port = kwargs.pop("grpc_port", None)
    health_check = kwargs.pop(
        "health_check", {"type": "http", "port": port, "path": "/health"},
    )

    ports = {port: 6333}
    if grpc_port is not None:
        ports[grpc_port] = 6334

    config: dict[str, Any] = {
        "type": "docker",
        "scope": scope,
        "mode": mode,
        "image": image,
        "container_name": container_name,
        "ports": ports,
        "health_check": health_check,
        "cleanup_on_stop": cleanup_on_stop,
        "restart_policy": restart_policy,
    }

    config.update(kwargs)
    return config


def milvus(
    port: int = 19530,
    scope: str = "project",
    mode: str = "local",
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a Milvus vector database configuration.

    Exposes Milvus' gRPC endpoint on ``port`` and, by default, also maps the HTTP
    management endpoint (19121 inside the container) to ``http_port`` which defaults
    to ``port + 1``. Health checks target the HTTP management endpoint so that status
    responses include component readiness information.

    Args:
        port: Host port that forwards to Milvus gRPC endpoint (container port 19530).
        scope: Logical scope for the resource (``"project"``, ``"workspace"``, etc.).
        mode: Environment mode metadata (``"local"``, ``"remote"``, etc.).
        **kwargs: Extra configuration values merged into the result.

    Returns:
        Dictionary configuring a Milvus container-based deployment.

    Example:
        >>> from pheno.kits.infra.templates import vectors
        >>> config = vectors.milvus(port=20010, scope="team", mode="local")
        >>> sorted(config["ports"].items())  # doctest: +ELLIPSIS
        [(20010, 19530), (20011, 19121)]
    """
    image = kwargs.pop("image", "milvusdb/milvus:v2.4.4")
    container_name = kwargs.pop("container_name", f"kinfra-milvus-{port}")
    cleanup_on_stop = kwargs.pop("cleanup_on_stop", True)
    restart_policy = kwargs.pop("restart_policy", "unless-stopped")

    http_port = kwargs.pop("http_port", port + 1)
    health_check = kwargs.pop(
        "health_check",
        {
            "type": "http",
            "port": http_port,
            "path": "/healthz",
        },
    )

    ports = {port: 19530}
    if http_port is not None:
        ports[http_port] = 19121

    config: dict[str, Any] = {
        "type": "docker",
        "scope": scope,
        "mode": mode,
        "image": image,
        "container_name": container_name,
        "ports": ports,
        "health_check": health_check,
        "cleanup_on_stop": cleanup_on_stop,
        "restart_policy": restart_policy,
    }

    config.update(kwargs)
    return config


def weaviate(
    port: int = 8080,
    scope: str = "project",
    mode: str = "local",
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a Weaviate vector database configuration.

    Args:
        port: Host port that forwards to the Weaviate REST API (container port 8080).
        scope: Scope identifier determining how the resource is shared.
        mode: Mode metadata (``"local"``, ``"remote"``, ``"managed"``).
        **kwargs: Additional config entries (e.g., environment, volumes).

    Returns:
        Dictionary configuring a Weaviate deployment for use with ``ResourceFactory``.

    Example:
        >>> from pheno.kits.infra.templates import vectors
        >>> config = vectors.weaviate(port=9090, scope="workspace", mode="local")
        >>> config["health_check"]["path"]
        '/v1/.well-known/ready'
    """
    image = kwargs.pop("image", "semitechnologies/weaviate:latest")
    container_name = kwargs.pop("container_name", f"kinfra-weaviate-{port}")
    cleanup_on_stop = kwargs.pop("cleanup_on_stop", True)
    restart_policy = kwargs.pop("restart_policy", "unless-stopped")
    health_check = kwargs.pop(
        "health_check",
        {"type": "http", "port": port, "path": "/v1/.well-known/ready"},
    )

    ports = {port: 8080}

    config: dict[str, Any] = {
        "type": "docker",
        "scope": scope,
        "mode": mode,
        "image": image,
        "container_name": container_name,
        "ports": ports,
        "health_check": health_check,
        "cleanup_on_stop": cleanup_on_stop,
        "restart_policy": restart_policy,
    }

    config.update(kwargs)
    return config


def chromadb(
    port: int = 8000,
    scope: str = "project",
    mode: str = "local",
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a ChromaDB server configuration.

    Args:
        port: Host port that forwards to the Chroma HTTP API (container port 8000).
        scope: Scope identifier for higher-level orchestration metadata.
        mode: Mode metadata describing where the instance runs.
        **kwargs: Additional configuration values merged into the returned dict.

    Returns:
        Dictionary configuring a ChromaDB deployment.

    Example:
        >>> from pheno.kits.infra.templates import vectors
        >>> config = vectors.chromadb(port=8100, scope="project", mode="local")
        >>> config["ports"][8100]
        8000
    """
    image = kwargs.pop("image", "ghcr.io/chroma-core/chroma:latest")
    container_name = kwargs.pop("container_name", f"kinfra-chromadb-{port}")
    cleanup_on_stop = kwargs.pop("cleanup_on_stop", True)
    restart_policy = kwargs.pop("restart_policy", "unless-stopped")
    health_check = kwargs.pop(
        "health_check", {"type": "http", "port": port, "path": "/api/v1/health"},
    )

    ports = {port: 8000}

    config: dict[str, Any] = {
        "type": "docker",
        "scope": scope,
        "mode": mode,
        "image": image,
        "container_name": container_name,
        "ports": ports,
        "health_check": health_check,
        "cleanup_on_stop": cleanup_on_stop,
        "restart_policy": restart_policy,
    }

    config.update(kwargs)
    return config


def lancedb(
    data_dir: Path,
    scope: str = "project",
    mode: str = "local",
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a LanceDB embedded vector store configuration.

    LanceDB runs in-process and stores data in the provided directory. The template
    captures metadata used by orchestration layers alongside a filesystem-based
    health check so supervisors can ensure the backing directory exists.

    Args:
        data_dir: Directory where LanceDB tables are stored (created externally).
        scope: Resource scope metadata (``"project"``, ``"workspace"``, etc.).
        mode: Execution mode (``"local"``, ``"embedded"``, ``"remote"``).
        **kwargs: Additional configuration values merged into the returned dict.

    Returns:
        Dictionary describing an embedded LanceDB deployment.

    Example:
        >>> from pathlib import Path
        >>> from pheno.kits.infra.templates import vectors
        >>> config = vectors.lancedb(Path("/tmp/lancedb"), scope="project", mode="local")
        >>> config["uri"]
        '/tmp/lancedb'
    """
    path = Path(data_dir).expanduser().resolve()
    health_check = kwargs.pop(
        "health_check", {"type": "filesystem", "path": str(path)},
    )

    config: dict[str, Any] = {
        "type": kwargs.pop("type", "local"),
        "scope": scope,
        "mode": mode,
        "image": kwargs.pop("image", "lancedb/local"),  # symbolic identifier for orchestration
        "uri": str(path),
        "ports": kwargs.pop("ports", {}),
        "health_check": health_check,
    }

    config.update(kwargs)
    return config


__all__ = ["chromadb", "lancedb", "milvus", "qdrant", "weaviate"]
