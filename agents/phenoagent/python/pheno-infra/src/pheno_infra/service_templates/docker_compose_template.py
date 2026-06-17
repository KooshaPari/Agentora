"""
Docker Compose Template Generator - Auto-generate docker-compose.yml files.

Generates docker-compose configurations for managing multi-container deployments with:
- Service definitions with environment variables
- Volume management
- Network configuration
- Health checks
- Resource limits
- Logging configuration
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DockerComposeTemplateGenerator:
    """
    Generate docker-compose.yml files for deployment.
    """

    @staticmethod
    def generate_compose_file(
        version: str = "3.8",
        services: dict[str, dict[str, Any]] | None = None,
        volumes: dict[str, dict[str, Any]] | None = None,
        networks: dict[str, dict[str, Any]] | None = None,
        environment: dict[str, str] | None = None,
    ) -> str:
        """Generate docker-compose.yml content.

        Args:
            version: Docker Compose version
            services: Service definitions
            volumes: Volume definitions
            networks: Network definitions
            environment: Global environment variables

        Returns:
            docker-compose.yml content as string
        """
        import yaml

        compose_dict = {
            "version": version,
            "services": services or {},
        }

        if volumes:
            compose_dict["volumes"] = volumes
        if networks:
            compose_dict["networks"] = networks

        # Convert to YAML
        return yaml.dump(compose_dict, default_flow_style=False, sort_keys=False)

    @staticmethod
    def create_service(
        image: str,
        container_name: str | None = None,
        ports: dict[int, int] | None = None,
        environment: dict[str, str] | None = None,
        volumes: dict[str, str] | None = None,
        restart_policy: str = "unless-stopped",
        cpu_shares: int | None = None,
        memory_limit: str | None = None,
        healthcheck: dict[str, Any] | None = None,
        depends_on: list[str] | None = None,
        networks: list[str] | None = None,
        command: str | None = None,
        entrypoint: str | None = None,
        logging: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a service definition.

        Args:
            image: Docker image
            container_name: Container name
            ports: Port mappings {host: container}
            environment: Environment variables
            volumes: Volume mounts {host: container}
            restart_policy: Restart policy
            cpu_shares: CPU shares
            memory_limit: Memory limit
            healthcheck: Health check configuration
            depends_on: Depends on other services
            networks: Networks to connect to
            command: Override command
            entrypoint: Override entrypoint
            logging: Logging configuration

        Returns:
            Service definition dict
        """
        service = {
            "image": image,
            "restart_policy": restart_policy,
        }

        if container_name:
            service["container_name"] = container_name

        if ports:
            service["ports"] = [f"{host}:{container}" for host, container in ports.items()]

        if environment:
            service["environment"] = environment

        if volumes:
            service["volumes"] = [f"{host}:{container}" for host, container in volumes.items()]

        if cpu_shares:
            service["cpu_shares"] = cpu_shares

        if memory_limit:
            service["mem_limit"] = memory_limit

        if healthcheck:
            service["healthcheck"] = healthcheck

        if depends_on:
            service["depends_on"] = depends_on

        if networks:
            service["networks"] = networks

        if command:
            service["command"] = command

        if entrypoint:
            service["entrypoint"] = entrypoint

        if logging:
            service["logging"] = logging

        return service

    @staticmethod
    def create_healthcheck(
        test: str,
        interval: int = 30,
        timeout: int = 10,
        retries: int = 3,
        start_period: int = 0,
    ) -> dict[str, Any]:
        """Create a health check definition.

        Args:
            test: Health check command
            interval: Interval in seconds
            timeout: Timeout in seconds
            retries: Number of retries
            start_period: Start period in seconds

        Returns:
            Health check definition dict
        """
        return {
            "test": ["CMD-SHELL", test],
            "interval": f"{interval}s",
            "timeout": f"{timeout}s",
            "retries": retries,
            "start_period": f"{start_period}s",
        }

    @staticmethod
    def create_volume(driver: str = "local") -> dict[str, Any]:
        """Create a volume definition.

        Args:
            driver: Volume driver

        Returns:
            Volume definition dict
        """
        return {"driver": driver}

    @staticmethod
    def create_network(driver: str = "bridge") -> dict[str, Any]:
        """Create a network definition.

        Args:
            driver: Network driver

        Returns:
            Network definition dict
        """
        return {"driver": driver}

    @staticmethod
    def save_compose_file(
        content: str,
        output_path: str = "docker-compose.yml",
    ) -> Path | None:
        """Save docker-compose file.

        Args:
            content: File content
            output_path: Output file path

        Returns:
            Path to saved file, or None if error
        """
        try:
            path = Path(output_path)
            path.write_text(content)
            logger.info(f"✓ Docker Compose file saved: {path}")
            return path

        except Exception as e:
            logger.exception(f"Failed to save Docker Compose file: {e}")
            return None


# Example configurations


def example_postgres_redis_app() -> str:
    """Example: PostgreSQL + Redis + Python App."""
    try:
        import yaml
    except ImportError:
        logger.exception("PyYAML required for Docker Compose generation")
        return ""

    generator = DockerComposeTemplateGenerator()

    # PostgreSQL service
    postgres_service = generator.create_service(
        image="postgres:16-alpine",
        container_name="postgres-db",
        ports={5432: 5432},
        environment={
            "POSTGRES_USER": "app",
            "POSTGRES_PASSWORD": "changeme",
            "POSTGRES_DB": "appdb",
        },
        volumes={
            "postgres_data": "/var/lib/postgresql/data",
        },
        healthcheck=generator.create_healthcheck(
            "pg_isready -U app -d appdb",
            interval=10,
        ),
    )

    # Redis service
    redis_service = generator.create_service(
        image="redis:7-alpine",
        container_name="redis-cache",
        ports={6379: 6379},
        healthcheck=generator.create_healthcheck(
            "redis-cli ping",
            interval=10,
        ),
    )

    # App service
    app_service = generator.create_service(
        image="my-app:latest",
        container_name="my-app",
        ports={8000: 8000},
        environment={
            "DATABASE_URL": "postgresql://app:changeme@postgres-db:5432/appdb",
            "REDIS_URL": "redis://redis-cache:6379",
            "LOG_LEVEL": "INFO",
        },
        depends_on=["postgres-db", "redis-cache"],
        healthcheck=generator.create_healthcheck(
            "curl -f http://localhost:8000/health",
            interval=30,
        ),
        memory_limit="1g",
    )

    return generator.generate_compose_file(
        services={
            "postgres": postgres_service,
            "redis": redis_service,
            "app": app_service,
        },
        volumes={
            "postgres_data": generator.create_volume(),
        },
        networks={
            "default": generator.create_network(),
        },
    )



def example_microservices() -> str:
    """Example: Microservices architecture."""
    try:
        import yaml
    except ImportError:
        logger.exception("PyYAML required for Docker Compose generation")
        return ""

    generator = DockerComposeTemplateGenerator()

    # API Gateway
    gateway_service = generator.create_service(
        image="api-gateway:latest",
        container_name="api-gateway",
        ports={80: 8080, 443: 8443},
        environment={
            "UPSTREAM_SERVICES": "user-service,order-service,product-service",
        },
        healthcheck=generator.create_healthcheck("curl -f http://localhost:8080/health"),
    )

    # User Service
    user_service = generator.create_service(
        image="user-service:latest",
        container_name="user-service",
        ports={8001: 8000},
        environment={
            "DATABASE_HOST": "postgres",
            "REDIS_HOST": "redis",
        },
        depends_on=["postgres", "redis"],
    )

    # Order Service
    order_service = generator.create_service(
        image="order-service:latest",
        container_name="order-service",
        ports={8002: 8000},
        environment={
            "DATABASE_HOST": "postgres",
            "MESSAGE_QUEUE": "rabbitmq",
        },
        depends_on=["postgres", "rabbitmq"],
    )

    # Product Service
    product_service = generator.create_service(
        image="product-service:latest",
        container_name="product-service",
        ports={8003: 8000},
        environment={
            "DATABASE_HOST": "postgres",
        },
        depends_on=["postgres"],
    )

    # PostgreSQL
    postgres_service = generator.create_service(
        image="postgres:16-alpine",
        container_name="postgres",
        ports={5432: 5432},
        environment={
            "POSTGRES_PASSWORD": "secret",
        },
        volumes={"postgres_data": "/var/lib/postgresql/data"},
    )

    # Redis
    redis_service = generator.create_service(
        image="redis:7-alpine",
        container_name="redis",
        ports={6379: 6379},
    )

    # RabbitMQ
    rabbitmq_service = generator.create_service(
        image="rabbitmq:3-management",
        container_name="rabbitmq",
        ports={5672: 5672, 15672: 15672},
        environment={
            "RABBITMQ_DEFAULT_USER": "guest",
            "RABBITMQ_DEFAULT_PASS": "guest",
        },
    )

    return generator.generate_compose_file(
        services={
            "gateway": gateway_service,
            "user-service": user_service,
            "order-service": order_service,
            "product-service": product_service,
            "postgres": postgres_service,
            "redis": redis_service,
            "rabbitmq": rabbitmq_service,
        },
        volumes={
            "postgres_data": generator.create_volume(),
        },
    )

