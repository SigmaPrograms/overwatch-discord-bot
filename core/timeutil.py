from datetime import datetime
from zoneinfo import ZoneInfo

def local_to_utc(naive_dt: datetime, tz: str) -> datetime:
    return naive_dt.replace(tzinfo=ZoneInfo(tz)).astimezone(ZoneInfo("UTC"))

def utc_to_local(utc_dt: datetime, tz: str) -> datetime:
    return utc_dt.astimezone(ZoneInfo(tz))