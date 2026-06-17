"""KInfra Templates.

Pre-configured templates for common resources and services.
"""

from . import resources, vectors
from .caching import redis
from .cloud import neon_database, supabase_project, vercel_deployment
from .databases import mongodb, mysql, postgres
from .messaging import nats
from .resources import (
    api_resource,
    aws_rds_instance,
    custom_api,
    custom_command,
    custom_docker,
    kubernetes_deployment,
    railway_service,
    render_service,
    systemd_service,
)

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
    "resources",
    "supabase_project",
    "systemd_service",
    "vectors",
    "vercel_deployment",
]
