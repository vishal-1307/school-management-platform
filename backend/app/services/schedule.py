"""Fixed school-day period schedule (IST) — for "current period" highlighting.

TimetableSlot only stores a period NUMBER, not a start/end time, so there is
nothing in the data model to compare "now" against. Real schools run on a
fixed bell schedule, so this hardcodes one (matching the 6-period day the
demo seed uses) purely to drive the UI's "current period" highlight. It is
a scheduling convention, not seeded/fake data — adjust PERIOD_TIMES if the
school's actual bell times differ.
"""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# (period_number, start, end) — 40-minute periods with short breaks.
PERIOD_TIMES: list[tuple[int, time, time]] = [
    (1, time(8, 0), time(8, 40)),
    (2, time(8, 45), time(9, 25)),
    (3, time(9, 30), time(10, 10)),
    (4, time(10, 15), time(10, 55)),
    (5, time(11, 10), time(11, 50)),
    (6, time(11, 55), time(12, 35)),
]

_DAY_NAMES = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
]


def now_ist() -> datetime:
    return datetime.now(IST)


def today_day_name() -> str:
    """Today's weekday as stored on TimetableSlot ('monday'..'sunday'), IST."""
    return _DAY_NAMES[now_ist().weekday()]


def current_period_number() -> int | None:
    """Which fixed period is happening right now (IST), or None outside school hours."""
    now = now_ist().time()
    for number, start, end in PERIOD_TIMES:
        if start <= now <= end:
            return number
    return None
