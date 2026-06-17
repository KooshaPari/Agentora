"""Resource templates package split from templates/resources.py.

Re-exports for backward compatibility.
"""

from __future__ import annotations

from .cache import redis
from .cloud import (
    api_resource,
    aws_rds_instance,
    custom_api,
    kubernetes_deployment,
    neon_database,
    railway_service,
    render_service,
    supabase_project,
    vercel_deployment,
)
from .db import mongodb, mysql, postgres
from .dockerish import custom_command, custom_docker, systemd_service
from .messaging import nats

__all__ = [
    "api_resource",
    "aws_rds_instance",
    "custom_api",
    "custom_command",
    "custom_docker",
    "kubernetes_deployment",
    "mongodb",
    "mysql",
    "nats",
    "neon_database",
    "postgres",
    "railway_service",
    "redis",
    "render_service",
    "supabase_project",
    "systemd_service",
    "vercel_deployment",
]
