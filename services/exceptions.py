# exceptions.py

class ProvisioningError(Exception):
    """Generic error during provisioning operations.
    Use this for unexpected failures when talking to external servers or performing provisioning steps.
    """
    def __init__(self, message: str = "Provisioning failed", *, cause: Exception | None = None, details: dict | None = None):
        super().__init__(message)
        self.cause = cause
        self.details = details or {}

class NoServerAvailableError(ProvisioningError):
    """Raised when no suitable server is available to host a subscription."""
    def __init__(self, message: str = "No server available", *, details: dict | None = None):
        super().__init__(message, cause=None, details=details)
