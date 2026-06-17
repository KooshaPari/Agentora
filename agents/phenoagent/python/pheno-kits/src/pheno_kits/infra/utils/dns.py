"""DNS Utilities.

Common utilities for DNS-safe naming and slug generation. Extracted from tunnel_sync.py
and kinfra_networking.py.
"""

import logging
import re

logger = logging.getLogger(__name__)


def dns_safe_slug(value: str, default: str = "local") -> str:
    """Create a DNS-safe slug from a service name.

    Converts strings to lowercase, replaces invalid characters with hyphens,
    and ensures the result is a valid DNS label according to RFC 1123.

    DNS label rules:
    - Must start and end with alphanumeric character
    - Can contain alphanumeric characters and hyphens
    - Cannot contain consecutive hyphens
    - Maximum 63 characters per label

    Args:
        value: Input string to convert to DNS-safe slug
        default: Default value if input is empty or invalid (default: "local")

    Returns:
        DNS-safe slug string

    Examples:
        >>> dns_safe_slug("My Service Name")
        'my-service-name'
        >>> dns_safe_slug("api_v2.0")
        'api-v2-0'
        >>> dns_safe_slug("--invalid--")
        'invalid'
        >>> dns_safe_slug("")
        'local'
        >>> dns_safe_slug("CamelCaseService")
        'camelcaseservice'
    """
    if not value:
        return default

    # Convert to lowercase
    slug = value.lower()

    # Replace invalid characters with hyphens
    # Valid DNS characters: a-z, 0-9, hyphen
    slug = re.sub(r"[^a-z0-9-]", "-", slug)

    # Remove leading/trailing hyphens
    slug = re.sub(r"^-+|-+$", "", slug)

    # Replace multiple consecutive hyphens with single hyphen
    slug = re.sub(r"--+", "-", slug)

    # Return default if result is empty or invalid
    if not slug:
        return default

    # Truncate to 63 characters (DNS label limit)
    if len(slug) > 63:
        logger.warning(f"Slug '{slug}' truncated to 63 characters for DNS compliance")
        slug = slug[:63].rstrip("-")

    return slug


def validate_dns_label(label: str) -> bool:
    """Validate if a string is a valid DNS label according to RFC 1123.

    Args:
        label: String to validate

    Returns:
        True if valid DNS label, False otherwise

    Examples:
        >>> validate_dns_label("my-service")
        True
        >>> validate_dns_label("-invalid")
        False
        >>> validate_dns_label("valid123")
        True
        >>> validate_dns_label("too--many--hyphens")
        True  # Actually valid, just unusual
    """
    if not label or len(label) > 63:
        return False

    # Must start and end with alphanumeric
    if not label[0].isalnum() or not label[-1].isalnum():
        return False

    # Can only contain alphanumeric and hyphens
    return re.match(r"^[a-z0-9-]+$", label, re.IGNORECASE)


def create_subdomain(service_name: str, domain: str, max_levels: int = 3) -> str:
    """Create a full subdomain from service name and base domain.

    Args:
        service_name: Service name to use as subdomain
        domain: Base domain
        max_levels: Maximum number of subdomain levels (default: 3)

    Returns:
        Full subdomain string

    Examples:
        >>> create_subdomain("api", "example.com")
        'api.example.com'
        >>> create_subdomain("my_service", "example.com")
        'my-service.example.com'
        >>> create_subdomain("test", "api.example.com", max_levels=4)
        'test.api.example.com'
    """
    slug = dns_safe_slug(service_name)
    domain_lower = domain.lower()

    # Check total subdomain levels
    total_levels = len(domain_lower.split(".")) + 1
    if total_levels > max_levels:
        logger.warning(
            f"Subdomain {slug}.{domain_lower} has {total_levels} levels, "
            f"which may cause SSL certificate issues with some providers",
        )

    return f"{slug}.{domain_lower}"


def extract_service_name_from_hostname(hostname: str) -> str | None:
    """Extract service name from a hostname by taking the first label.

    Args:
        hostname: Full hostname (e.g., "my-service.example.com")

    Returns:
        Service name (first DNS label) or None if invalid

    Examples:
        >>> extract_service_name_from_hostname("api.example.com")
        'api'
        >>> extract_service_name_from_hostname("my-service.example.com")
        'my-service'
        >>> extract_service_name_from_hostname("invalid")
        'invalid'
    """
    if not hostname:
        return None

    parts = hostname.split(".")
    if not parts:
        return None

    service_label = parts[0]
    return service_label if validate_dns_label(service_label) else None
