"""
Nginx Template Generator - Auto-generate Nginx configuration files.

Generates Nginx reverse proxy configurations for:
- Health-aware routing
- Multi-tenant upstream management
- SSL/TLS termination
- Load balancing
- Caching policies
- Security headers
"""

import logging

logger = logging.getLogger(__name__)


class NginxTemplateGenerator:
    """
    Generate Nginx configuration files.
    """

    @staticmethod
    def generate_upstream(
        name: str,
        servers: list[dict[str, any]],
        method: str = "least_conn",
    ) -> str:
        """Generate upstream block.

        Args:
            name: Upstream name
            servers: List of server dicts with keys: host, port, weight (optional)
            method: Load balancing method (least_conn, round_robin, ip_hash, etc.)

        Returns:
            Nginx upstream block
        """
        lines = [f"upstream {name} {{"]

        if method != "round_robin":
            lines.append(f"    {method};")

        for server in servers:
            host = server.get("host", "localhost")
            port = server.get("port", 80)
            weight = server.get("weight")
            max_fails = server.get("max_fails")
            fail_timeout = server.get("fail_timeout", "30s")

            server_line = f"    server {host}:{port}"
            if weight:
                server_line += f" weight={weight}"
            if max_fails:
                server_line += f" max_fails={max_fails}"
            server_line += f" fail_timeout={fail_timeout};"

            lines.append(server_line)

        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def generate_server_block(
        server_name: str,
        upstream: str,
        listen_port: int = 443,
        ssl: bool = True,
        ssl_cert: str | None = None,
        ssl_key: str | None = None,
        client_max_body_size: str = "100M",
        proxy_connect_timeout: int = 60,
        proxy_read_timeout: int = 60,
        proxy_send_timeout: int = 60,
        cache_enabled: bool = False,
        cache_zone: str | None = None,
        cache_valid: dict[str, str] | None = None,
        compression: bool = True,
        gzip_types: list[str] | None = None,
        security_headers: bool = True,
        cors_enabled: bool = False,
        cors_origin: str = "*",
        rate_limit_zone: str | None = None,
        rate_limit: str | None = None,
    ) -> str:
        """Generate server block.

        Args:
            server_name: Server name (domain)
            upstream: Upstream name
            listen_port: Listen port
            ssl: Enable SSL
            ssl_cert: SSL certificate path
            ssl_key: SSL key path
            client_max_body_size: Max body size
            proxy_connect_timeout: Proxy connect timeout
            proxy_read_timeout: Proxy read timeout
            proxy_send_timeout: Proxy send timeout
            cache_enabled: Enable caching
            cache_zone: Cache zone name
            cache_valid: Cache validity rules
            compression: Enable gzip compression
            gzip_types: MIME types to compress
            security_headers: Add security headers
            cors_enabled: Enable CORS
            cors_origin: CORS origin
            rate_limit_zone: Rate limit zone name
            rate_limit: Rate limit rule

        Returns:
            Nginx server block
        """
        lines = ["server {"]
        lines.append(f"    listen {listen_port}" + (" ssl http2" if ssl else "") + ";")
        lines.append(f"    server_name {server_name};")

        if ssl and ssl_cert and ssl_key:
            lines.extend(
                [
                    f"    ssl_certificate {ssl_cert};",
                    f"    ssl_certificate_key {ssl_key};",
                    "    ssl_protocols TLSv1.2 TLSv1.3;",
                    "    ssl_ciphers HIGH:!aNULL:!MD5;",
                    "    ssl_prefer_server_ciphers on;",
                ],
            )

        # Rate limiting
        if rate_limit_zone and rate_limit:
            lines.append(f"    limit_req zone={rate_limit_zone} {rate_limit};")

        # Compression
        if compression:
            lines.extend(
                [
                    "    gzip on;",
                    "    gzip_vary on;",
                    "    gzip_proxied any;",
                    "    gzip_comp_level 6;",
                    "    gzip_types text/plain text/css text/xml text/javascript "
                     "application/json application/javascript application/xml+rss;",
                ],
            )

        # Logging
        lines.extend(
            [
                f"    access_log /var/log/nginx/{server_name}_access.log;",
                f"    error_log /var/log/nginx/{server_name}_error.log;",
            ],
        )

        # Client settings
        lines.append(f"    client_max_body_size {client_max_body_size};")

        # Caching
        if cache_enabled and cache_zone:
            lines.append(f"    proxy_cache {cache_zone};")
            if cache_valid:
                for status, duration in cache_valid.items():
                    lines.append(f"    proxy_cache_valid {status} {duration};")

        # Location block
        lines.extend(
            [
                "",
                "    location / {",
                f"        proxy_pass http://{upstream};",
                "        proxy_set_header Host $host;",
                "        proxy_set_header X-Real-IP $remote_addr;",
                "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
                "        proxy_set_header X-Forwarded-Proto $scheme;",
                f"        proxy_connect_timeout {proxy_connect_timeout}s;",
                f"        proxy_read_timeout {proxy_read_timeout}s;",
                f"        proxy_send_timeout {proxy_send_timeout}s;",
                "        proxy_http_version 1.1;",
                '        proxy_set_header Connection "";',
            ],
        )

        # CORS
        if cors_enabled:
            lines.extend(
                [
                    f'        add_header Access-Control-Allow-Origin "{cors_origin}" always;',
                    '        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;',
                    '        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization" always;',
                ],
            )

        # Security headers
        if security_headers:
            lines.extend(
                [
                    '        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;',
                    '        add_header X-Frame-Options "SAMEORIGIN" always;',
                    '        add_header X-Content-Type-Options "nosniff" always;',
                    '        add_header X-XSS-Protection "1; mode=block" always;',
                    '        add_header Referrer-Policy "strict-origin-when-cross-origin" always;',
                ],
            )

        lines.extend(
            [
                "    }",
                "",
                "    location /health {",
                "        access_log off;",
                "        proxy_pass http://" + upstream + ";",
                "    }",
                "",
                "}",
            ],
        )

        return "\n".join(lines)

    @staticmethod
    def generate_http_block(
        upstreams: list[str],
        cache_zones: dict[str, dict[str, any]] | None = None,
        rate_limit_zones: dict[str, dict[str, any]] | None = None,
    ) -> str:
        """Generate HTTP block with global settings.

        Args:
            upstreams: List of upstream definitions
            cache_zones: Cache zone definitions
            rate_limit_zones: Rate limit zone definitions

        Returns:
            Nginx HTTP block
        """
        lines = ["http {"]

        # Basic settings
        lines.extend(
            [
                "    include /etc/nginx/mime.types;",
                "    default_type application/octet-stream;",
                "",
                "    sendfile on;",
                "    tcp_nopush on;",
                "    tcp_nodelay on;",
                "    keepalive_timeout 65;",
                "    types_hash_max_size 2048;",
                "",
                "    log_format main '$remote_addr - $remote_user [$time_local] \"$request\" ' "
                 "'$status $body_bytes_sent \"$http_referer\" ' "
                 '\'"$http_user_agent" "$http_x_forwarded_for"\';',
                "",
                "    access_log /var/log/nginx/access.log main;",
                "",
            ],
        )

        # Cache zones
        if cache_zones:
            lines.append("    # Cache zones")
            for zone_name, zone_config in cache_zones.items():
                path = zone_config.get("path", "/var/cache/nginx/" + zone_name)
                size = zone_config.get("size", "10m")
                line = f"    proxy_cache_path {path} levels=1:2 keys_zone={zone_name}:{size};"
                lines.append(line)
            lines.append("")

        # Rate limit zones
        if rate_limit_zones:
            lines.append("    # Rate limit zones")
            for zone_name, zone_config in rate_limit_zones.items():
                rate = zone_config.get("rate", "10r/s")
                size = zone_config.get("size", "10m")
                line = (
                    f"    limit_req_zone $binary_remote_addr zone={zone_name}:{size} rate={rate};"
                )
                lines.append(line)
            lines.append("")

        # Include upstreams
        lines.extend(upstreams)
        lines.append("")

        # Include server blocks
        lines.append("    include /etc/nginx/conf.d/*.conf;")
        lines.append("}")

        return "\n".join(lines)

    @staticmethod
    def generate_full_config(
        server_names: list[str],
        upstream_servers: dict[str, list[dict[str, any]]],
        ssl_cert: str | None = None,
        ssl_key: str | None = None,
        enable_cache: bool = False,
        enable_compression: bool = True,
    ) -> str:
        """Generate complete Nginx configuration.

        Args:
            server_names: List of server names (domains)
            upstream_servers: Dict mapping upstream names to server lists
            ssl_cert: SSL certificate path
            ssl_key: SSL key path
            enable_cache: Enable response caching
            enable_compression: Enable gzip compression

        Returns:
            Complete Nginx configuration
        """
        # Generate upstreams
        upstreams = []
        for upstream_name, servers in upstream_servers.items():
            upstreams.append(NginxTemplateGenerator.generate_upstream(upstream_name, servers))

        # Cache zones
        cache_zones = None
        if enable_cache:
            cache_zones = {
                "my_cache": {
                    "path": "/var/cache/nginx/static",
                    "size": "10m",
                },
            }

        # Generate HTTP block
        http_block = NginxTemplateGenerator.generate_http_block(
            upstreams=upstreams,
            cache_zones=cache_zones,
        )

        # Generate server blocks
        server_blocks = []
        for i, server_name in enumerate(server_names):
            upstream_name = (
                list(upstream_servers.keys())[i]
                if i < len(upstream_servers)
                else next(iter(upstream_servers.keys()))
            )

            server_block = NginxTemplateGenerator.generate_server_block(
                server_name=server_name,
                upstream=upstream_name,
                listen_port=443,
                ssl=bool(ssl_cert and ssl_key),
                ssl_cert=ssl_cert,
                ssl_key=ssl_key,
                cache_enabled=enable_cache,
                cache_zone="my_cache" if enable_cache else None,
                compression=enable_compression,
                security_headers=True,
            )
            server_blocks.append(server_block)

        return "\n\n".join([http_block, *server_blocks])


# Example configurations


def example_reverse_proxy_config() -> str:
    """Example: Basic reverse proxy configuration."""
    return NginxTemplateGenerator.generate_server_block(
        server_name="example.com",
        upstream="backend",
        listen_port=443,
        ssl_cert="/etc/letsencrypt/live/example.com/fullchain.pem",
        ssl_key="/etc/letsencrypt/live/example.com/privkey.pem",
        security_headers=True,
        compression=True,
    )


def example_load_balanced_config() -> str:
    """Example: Load balanced configuration."""
    upstream_config = NginxTemplateGenerator.generate_upstream(
        name="backend",
        servers=[
            {"host": "backend1.internal", "port": 8000, "weight": 50},
            {"host": "backend2.internal", "port": 8000, "weight": 30},
            {"host": "backend3.internal", "port": 8000, "weight": 20},
        ],
        method="least_conn",
    )

    server_config = NginxTemplateGenerator.generate_server_block(
        server_name="api.example.com",
        upstream="backend",
        listen_port=443,
        ssl_cert="/etc/letsencrypt/live/api.example.com/fullchain.pem",
        ssl_key="/etc/letsencrypt/live/api.example.com/privkey.pem",
        cache_enabled=True,
        cache_zone="api_cache",
        cache_valid={"200": "10m", "404": "1m"},
        security_headers=True,
        rate_limit_zone="api_limit",
        rate_limit="burst=20 nodelay",
    )

    return upstream_config + "\n\n" + server_config


def example_multi_tenant_config() -> str:
    """Example: Multi-tenant configuration."""

    # Global HTTP block with rate limiting


    # Tenants
    tenants = [
        {"name": "tenant1.example.com", "upstream": "tenant1_backend"},
        {"name": "tenant2.example.com", "upstream": "tenant2_backend"},
        {"name": "tenant3.example.com", "upstream": "tenant3_backend"},
    ]

    # Generate upstreams
    upstreams = []
    for tenant in tenants:
        upstream = NginxTemplateGenerator.generate_upstream(
            name=tenant["upstream"],
            servers=[
                {"host": f"{tenant['upstream']}-1.internal", "port": 8000},
                {"host": f"{tenant['upstream']}-2.internal", "port": 8000},
            ],
            method="least_conn",
        )
        upstreams.append(upstream)

    # Generate server blocks
    server_blocks = []
    for tenant in tenants:
        server = NginxTemplateGenerator.generate_server_block(
            server_name=tenant["name"],
            upstream=tenant["upstream"],
            listen_port=443,
            ssl_cert=f"/etc/letsencrypt/live/{tenant['name']}/fullchain.pem",
            ssl_key=f"/etc/letsencrypt/live/{tenant['name']}/privkey.pem",
            cache_enabled=True,
            cache_zone="content_cache",
            security_headers=True,
            rate_limit_zone="api_limit",
            rate_limit="burst=50 nodelay",
        )
        server_blocks.append(server)

    return "\n\n".join(upstreams + server_blocks)
