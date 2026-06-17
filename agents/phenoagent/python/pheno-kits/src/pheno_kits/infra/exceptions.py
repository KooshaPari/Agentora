"""
KInfra exception hierarchy for comprehensive error handling.
"""


class KInfraError(Exception):
    """
    Base exception for all KInfra operations.
    """



class PortAllocationError(KInfraError):
    """
    Raised when port allocation fails.
    """



class TunnelError(KInfraError):
    """
    Raised when tunnel operations fail.
    """



class ServiceConflictError(KInfraError):
    """
    Raised when service conflicts cannot be resolved.
    """



class ProcessManagementError(KInfraError):
    """
    Raised when process management operations fail.
    """



class ConfigurationError(KInfraError):
    """
    Raised when configuration is invalid or missing.
    """



class ServiceError(KInfraError):
    """
    Raised when service management operations fail.
    """

