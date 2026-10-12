class CalendarError(RuntimeError):
    """Base error raised by calendar providers."""


class CalendarAuthExpired(CalendarError):
    """Raised when an OAuth calendar provider needs re-authentication."""
