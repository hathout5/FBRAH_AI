# -*- coding: utf-8 -*-
"""Date arithmetic for FBRAH recurring reminders."""
import calendar
import datetime as dt

def next_occurrence(remind_at, rule, now=None):
    when = dt.datetime.fromisoformat(str(remind_at)) if not isinstance(remind_at, dt.datetime) else remind_at
    now = now or dt.datetime.now().astimezone().replace(tzinfo=None)
    if when.tzinfo is not None:
        when = when.astimezone().replace(tzinfo=None)
    if now.tzinfo is not None:
        now = now.astimezone().replace(tzinfo=None)
    rule = (rule or "").strip().lower()
    if rule == "daily":
        step = dt.timedelta(days=1)
        nxt = when + step
        while nxt <= now: nxt += step
    elif rule == "weekly":
        step = dt.timedelta(days=7)
        nxt = when + step
        while nxt <= now: nxt += step
    elif rule == "monthly":
        nxt = when
        while nxt <= now:
            year, month = nxt.year, nxt.month + 1
            if month > 12: year, month = year + 1, 1
            day = min(when.day, calendar.monthrange(year, month)[1])
            nxt = nxt.replace(year=year, month=month, day=day)
    else:
        raise ValueError("Unsupported recurrence rule")
    return nxt.isoformat(timespec="seconds")
