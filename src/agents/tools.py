"""Tools available to team members."""
from collections.abc import Callable

NO_NEW_EVENTS = "No new calendar events since the last check."


def make_read_calendar(calendar: dict) -> Callable[[], str]:
    """Bind the tool to a dict whose 'current' key holds this turn's synthetic dump."""

    def read_calendar() -> str:
        """Read the user's full calendar for the current week."""
        return calendar.get("current") or NO_NEW_EVENTS

    return read_calendar
