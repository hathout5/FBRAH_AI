# -*- coding: utf-8 -*-
import sqlite3
import tempfile
import datetime as dt
from pathlib import Path
from fbrah_reminder_worker import deliver_due_once


def test_worker_only_delivers_configured_user_and_marks_once():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / 'reminders.db'
        con = sqlite3.connect(db)
        con.execute('''CREATE TABLE reminders(
            id INTEGER PRIMARY KEY, username TEXT, message TEXT, remind_at TEXT,
            kind TEXT, done INTEGER DEFAULT 0, repeat_rule TEXT DEFAULT '',
            snooze_until TEXT, os_notified_at TEXT)''')
        now = dt.datetime(2026, 11, 26, 8, 0, 0)
        due = (now - dt.timedelta(minutes=1)).isoformat(timespec='seconds')
        con.execute('INSERT INTO reminders(username,message,remind_at,kind,done,repeat_rule) VALUES(?,?,?,?,0,?)', ('alice','جلسة المحكمة',due,'appointment',''))
        con.execute('INSERT INTO reminders(username,message,remind_at,kind,done,repeat_rule) VALUES(?,?,?,?,0,?)', ('bob','موعد خاص',due,'remind',''))
        con.commit(); con.close()
        shown=[]
        notify=lambda title,msg: shown.append((title,msg)) or True
        assert deliver_due_once(db, now=now, notify=notify, username='alice') == 1
        assert shown == [('موعد في FBRAH','جلسة المحكمة')]
        assert deliver_due_once(db, now=now, notify=notify, username='alice') == 0
        con=sqlite3.connect(db)
        alice=con.execute('SELECT os_notified_at FROM reminders WHERE username="alice"').fetchone()[0]
        bob=con.execute('SELECT os_notified_at FROM reminders WHERE username="bob"').fetchone()[0]
        con.close()
        assert alice is not None and bob is None


def test_worker_refuses_to_show_all_users_when_username_missing():
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/'empty.db'
        con=sqlite3.connect(db)
        con.execute('''CREATE TABLE reminders(id INTEGER PRIMARY KEY, username TEXT, message TEXT, remind_at TEXT, kind TEXT, done INTEGER, repeat_rule TEXT, snooze_until TEXT, os_notified_at TEXT)''')
        con.commit();con.close()
        assert deliver_due_once(db, username=None, notify=lambda *a: True) == 0


def test_recurring_date_advance_daily_weekly_and_monthly_end_of_month():
    from fbrah_reminder_core import next_occurrence
    now=dt.datetime(2026, 11, 26, 8, 0, 0)
    assert next_occurrence("2026-11-25T09:00:00", "daily", now) == "2026-11-26T09:00:00"
    assert next_occurrence("2026-11-19T09:00:00", "weekly", now) == "2026-11-26T09:00:00"
    assert next_occurrence("2026-01-31T09:00:00", "monthly", dt.datetime(2026,2,1,0,0,0)) == "2026-02-28T09:00:00"


def test_worker_completes_one_time_and_advances_recurring_after_grace():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / 'reminders.db'
        con = sqlite3.connect(db)
        con.execute('''CREATE TABLE reminders(
            id INTEGER PRIMARY KEY, username TEXT, message TEXT, remind_at TEXT,
            kind TEXT, done INTEGER DEFAULT 0, repeat_rule TEXT DEFAULT '',
            snooze_until TEXT, os_notified_at TEXT)''')
        now = dt.datetime(2026, 11, 26, 10, 0, 0)
        due = (now - dt.timedelta(minutes=1)).isoformat(timespec='seconds')
        con.execute('INSERT INTO reminders(username,message,remind_at,kind,done,repeat_rule) VALUES(?,?,?,?,0,?)', ('alice','موعد منفرد',due,'remind',''))
        con.execute('INSERT INTO reminders(username,message,remind_at,kind,done,repeat_rule) VALUES(?,?,?,?,0,?)', ('alice','مراجعة يومية',due,'remind','daily'))
        con.commit(); con.close()
        notify=lambda *a: True
        assert deliver_due_once(db, now=now, notify=notify, username='alice') == 2
        later=now+dt.timedelta(minutes=16)
        assert deliver_due_once(db, now=later, notify=notify, username='alice') == 0
        con=sqlite3.connect(db)
        one=con.execute('SELECT done FROM reminders WHERE message="موعد منفرد"').fetchone()[0]
        recurring=con.execute('SELECT done,remind_at,os_notified_at FROM reminders WHERE message="مراجعة يومية"').fetchone()
        con.close()
        assert one == 1
        assert recurring[0] == 0 and recurring[1] == '2026-11-27T09:59:00' and recurring[2] is None
