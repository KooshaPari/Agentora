"""KInfra Service Definitions.

Pre-configured service definitions for common applications using KInfra infrastructure.
Makes it easy to spin up standardized services across projects.
"""

from .byteport import BytePortConfig, get_byteport_services

__all__ = ["BytePortConfig", "get_byteport_services"]
