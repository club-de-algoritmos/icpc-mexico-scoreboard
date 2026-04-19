from datetime import datetime
from zoneinfo import ZoneInfo


UTC = ZoneInfo("UTC")
MEXICO_CITY_TZ = ZoneInfo("America/Mexico_City")


def _as_local_time(dt: datetime) -> datetime:
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(MEXICO_CITY_TZ)


def format_as_local_time(dt: datetime) -> str:
    return _as_local_time(dt).strftime("%Y-%m-%d %H:%M:%S CDMX")
