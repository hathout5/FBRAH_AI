# -*- coding: utf-8 -*-
"""Windows background reminder worker for FBRAH.
Run in the signed-in user's desktop session. Requires optional package winotify.
"""
from __future__ import annotations
import os, sqlite3, time, datetime as dt, sys, argparse, json, math, wave, struct, tempfile, unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_local_env():
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def database_path():
    _load_local_env()
    value = os.environ.get("FBRAH_DATABASE") or str(BASE_DIR / "fbrah.db")
    path = Path(value).expanduser()
    return path if path.is_absolute() else (BASE_DIR / path).resolve()


def _rtl_toast_text(value: str) -> str:
    """Normalize Arabic text and isolate its direction inside Windows toast XML."""
    value = unicodedata.normalize("NFC", str(value or ""))
    # Remove only invisible formatting marks that can leak in from copied text;
    # keep ZWJ/ZWNJ because they can be meaningful for Arabic shaping.
    value = value.replace("\ufeff", "").replace("\u200b", "")
    value = " ".join(value.split()).strip()
    if not value:
        return "موعدك"
    # RLI/PDI isolate Arabic from the Latin FBRAH brand and date/time fragments.
    return "\u200f\u2067" + value + "\u2069\u200f"


def _sound_settings() -> dict:
    path = BASE_DIR / "fbrah_reminder_sound.json"
    defaults = {"tone": "classic", "volume": 80, "repeats": 3}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return defaults
        tone = str(data.get("tone", defaults["tone"]))
        volume = max(0, min(100, int(data.get("volume", defaults["volume"]))))
        repeats = max(1, min(30, int(data.get("repeats", defaults["repeats"]))))
        if tone not in {"classic", "soft", "urgent", "double", "chime", "ascending", "digital", "bell", "melody", "pulse", "radar", "xylophone", "alarm", "softchime", "triple"}:
            tone = defaults["tone"]
        return {"tone": tone, "volume": volume, "repeats": repeats}
    except Exception:
        return defaults


def _play_custom_sound(settings=None) -> bool:
    """Play a selectable multi-tone WAV with real amplitude control on Windows."""
    if sys.platform != "win32":
        return False
    try:
        import winsound
        settings = settings or _sound_settings()
        patterns = {
            "classic": ([880, 660, 880], 0.16, 0.10, "sine"),
            "soft": ([440, 523, 440], 0.23, 0.13, "sine"),
            "urgent": ([1046, 784, 1046, 784], 0.12, 0.07, "square"),
            "double": ([660, 660, 880, 880], 0.14, 0.08, "sine"),
            "chime": ([784, 988, 1175, 988], 0.22, 0.07, "sine"),
            "ascending": ([392, 494, 587, 784], 0.17, 0.06, "sine"),
            "digital": ([1200, 800, 1200, 800], 0.09, 0.07, "square"),
            "bell": ([880, 880, 660, 660], 0.25, 0.08, "sine"),
            "melody": ([523, 659, 784, 659, 523], 0.18, 0.08, "sine"),
            "pulse": ([700, 700, 700], 0.09, 0.16, "square"),
            "radar": ([400, 900, 400, 900, 400], 0.11, 0.06, "sawtooth"),
            "xylophone": ([1046, 1318, 1568, 1318, 1046], 0.12, 0.05, "triangle"),
            "alarm": ([880, 0, 880, 0, 880], 0.16, 0.10, "square"),
            "softchime": ([523, 659, 784], 0.28, 0.12, "sine"),
            "triple": ([660, 880, 1100, 880, 660], 0.14, 0.07, "triangle"),
        }
        freqs, duration, gap, wave_type = patterns.get(settings["tone"], patterns["classic"])
        volume = max(0.0, min(1.0, settings["volume"] / 100.0))
        if volume <= 0:
            return True
        sample_rate = 22050
        samples = bytearray()
        for freq in freqs:
            count = int(sample_rate * duration)
            for i in range(count):
                t = i / sample_rate
                envelope = min(1.0, i / max(1, sample_rate * 0.012), (count - i) / max(1, sample_rate * 0.025))
                raw = math.sin(2 * math.pi * freq * t)
                if wave_type == "square":
                    raw = 1.0 if raw >= 0 else -1.0
                # Conservative peak to avoid clipping on system output.
                sample = int(32767 * 0.32 * volume * envelope * raw)
                samples.extend(struct.pack("<h", sample))
            samples.extend(b"\x00\x00" * int(sample_rate * gap))
        # One short WAV per cycle, repeated according to the selected count.
        with tempfile.NamedTemporaryFile(prefix="fbrah_alarm_", suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        try:
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(bytes(samples))
            for _ in range(max(1, min(10, int(settings["repeats"])) )):
                winsound.PlaySound(wav_path, winsound.SND_FILENAME)
                time.sleep(0.22)
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass
        return True
    except Exception as exc:
        print(f"[FBRAH reminder] Custom sound unavailable: {exc}", flush=True)
        try:
            import winsound
            winsound.MessageBeep()
            return True
        except Exception:
            return False


def _toast(title: str, message: str) -> bool:
    try:
        from winotify import Notification, audio
        title = _rtl_toast_text(title)[:100]
        message = _rtl_toast_text(message)[:300]
        toast = Notification(app_id="FBRAH AI", title=title, msg=message, duration="long")
        # Silence Windows' fixed default tone; the worker plays the chosen
        # local WAV afterwards so tone, loudness and repetition are controllable.
        try:
            toast.set_audio(audio.Silent, loop=False)
        except Exception:
            pass
        toast.show()
        _play_custom_sound()
        return True
    except Exception as exc:
        print(f"[FBRAH reminder] Notification unavailable: {exc}", flush=True)
        return False


def deliver_due_once(db_path=None, now=None, notify=_toast, username=None):
    """Deliver due Windows toasts; after a 15-minute acknowledgement window,
    complete one-time reminders or advance recurring ones so they never remain stuck.
    """
    path = str(db_path or database_path())
    now_dt = now or dt.datetime.now()
    now_iso = now_dt.isoformat(timespec="seconds")
    grace_before = (now_dt - dt.timedelta(minutes=15)).isoformat(timespec="seconds")
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(reminders)").fetchall()}
        if not {"os_notified_at", "snooze_until", "repeat_rule"}.issubset(cols):
            return 0
        if not username:
            print("[FBRAH reminder] No FBRAH username configured; skipping to protect other accounts.", flush=True)
            return 0
        rows = con.execute(
            """SELECT id, username, message, kind FROM reminders
               WHERE username=? AND done=0 AND os_notified_at IS NULL
                 AND COALESCE(snooze_until, remind_at)<=?
               ORDER BY COALESCE(snooze_until, remind_at) LIMIT 30""",
            (username, now_iso),
        ).fetchall()
        delivered = 0
        for row in rows:
            kind = row["kind"] or "remind"
            title = "موعد في FBRAH" if kind == "appointment" else ("منبّه في FBRAH" if kind == "alarm" else "تذكير من FBRAH")
            if notify(title, row["message"] or "موعدك"):
                cur = con.execute(
                    "UPDATE reminders SET os_notified_at=? WHERE id=? AND os_notified_at IS NULL AND done=0",
                    (now_iso, row["id"]),
                )
                delivered += max(0, cur.rowcount)
        # If the user did not acknowledge the Windows toast in 15 minutes,
        # treat it as delivered and advance recurrence/complete the one-time reminder.
        stale = con.execute(
            """SELECT id, remind_at, repeat_rule FROM reminders
               WHERE username=? AND done=0 AND os_notified_at IS NOT NULL AND os_notified_at<=?
               ORDER BY os_notified_at LIMIT 30""",
            (username, grace_before),
        ).fetchall()
        for row in stale:
            rule = (row["repeat_rule"] or "").strip().lower()
            if rule in ("daily", "weekly", "monthly"):
                try:
                    from fbrah_reminder_core import next_occurrence
                    next_at = next_occurrence(row["remind_at"], rule, now_dt)
                    con.execute(
                        "UPDATE reminders SET remind_at=?, snooze_until=NULL, os_notified_at=NULL WHERE id=? AND username=? AND done=0",
                        (next_at, row["id"], username),
                    )
                except Exception as exc:
                    print(f"[FBRAH reminder] recurrence advance failed for {row['id']}: {exc}", flush=True)
            else:
                con.execute(
                    "UPDATE reminders SET done=1, snooze_until=NULL WHERE id=? AND username=? AND done=0",
                    (row["id"], username),
                )
        con.commit()
        return delivered
    finally:
        con.close()


def run_forever(interval=10, username=None):
    path = database_path()
    print(f"FBRAH Windows reminder worker started. DB={path}; user={username or '(not set)'}", flush=True)
    while True:
        try:
            deliver_due_once(path, username=username)
        except KeyboardInterrupt:
            print("FBRAH reminder worker stopped.", flush=True)
            return
        except Exception as exc:
            print(f"[FBRAH reminder] worker error: {exc}", flush=True)
        time.sleep(max(3, int(interval)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default=os.environ.get("FBRAH_REMINDER_USERNAME", ""))
    parser.add_argument("--interval", type=int, default=int(os.environ.get("FBRAH_REMINDER_POLL_SECONDS", "10")))
    args = parser.parse_args()
    try:
        run_forever(args.interval, args.username.strip())
    except KeyboardInterrupt:
        pass
