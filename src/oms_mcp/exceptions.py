class OMSError(Exception):
    """Safe error message suitable for a tool result."""


class AuthenticationError(OMSError):
    pass
