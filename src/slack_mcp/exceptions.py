class SlackMCPError(RuntimeError):
    """Base Slack MCP error."""


class SlackAuthenticationError(SlackMCPError):
    """Raised when Slack authentication fails."""


class SlackPermissionError(SlackMCPError):
    """Raised when the app lacks access or required scopes."""


class SlackRateLimitError(SlackMCPError):
    def __init__(self, retry_after: int | None = None):
        self.retry_after = retry_after
        message = "Slack rate limit reached"
        if retry_after:
            message = f"{message}; retry after {retry_after} seconds"
        super().__init__(message)


class SlackAmbiguousUserError(SlackMCPError):
    """Raised when a name lookup returns multiple candidates."""


class SlackBulkLimitError(SlackMCPError):
    """Raised when a write request exceeds the configured bulk limit."""
