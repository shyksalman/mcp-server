from calendar_mcp.config import CalendarSettings
from calendar_mcp.providers.base import CalendarProvider
from calendar_mcp.providers.google import GoogleCalendarProvider
from calendar_mcp.providers.local import LocalCalendarProvider
from calendar_mcp.providers.microsoft import MicrosoftCalendarProvider


def build_provider(settings: CalendarSettings) -> CalendarProvider:
    provider = settings.calendar_provider.lower()
    if provider == "google":
        return GoogleCalendarProvider(settings.calendar_timezone)
    if provider in {"microsoft", "outlook"}:
        return MicrosoftCalendarProvider(settings.calendar_timezone)
    return LocalCalendarProvider(settings.calendar_timezone)
