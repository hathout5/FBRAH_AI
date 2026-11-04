import os
import sqlite3
import secrets
import hashlib
import getpass
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent

DB_FILE = Path(
    os.environ.get("FBRAH_DATABASE", str(BASE_DIR / "fbrah.db"))
).resolve()

BACKUP_DIR = BASE_DIR / "backups"


def main():
    if not DB_FILE.is_file():
        raise SystemExit("ERROR: Database not found.")

    password = getpass.getpass("Enter new admin password: ")
    confirm = getpass.getpass("Confirm new admin password: ")

    if len(password) < 12:
        raise SystemExit("ERROR: Password must be at least 12 characters.")

    if password != confirm:
        raise SystemExit("ERROR: Passwords do not match.")

    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        240_000
    ).hex()

    stored = f"pbkdf2_sha256${salt}${digest}"

    BACKUP_DIR.mkdir(exist_ok=True)

    backup_file = BACKUP_DIR / (
        "before_admin_reset_"
        + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        + ".db"
    )

    with sqlite3.connect(str(DB_FILE), timeout=30) as db:
        db.execute("PRAGMA busy_timeout=30000")

        integrity = db.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise SystemExit("ERROR: Database integrity check failed.")

        count = db.execute(
            "SELECT COUNT(*) FROM users WHERE username='admin'"
        ).fetchone()[0]

        if count != 1:
            raise SystemExit("ERROR: Admin account not found or duplicated.")

        with sqlite3.connect(str(backup_file)) as backup:
            db.backup(backup)

        with sqlite3.connect(str(backup_file)) as backup:
            if backup.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0] != "ok":
                backup_file.unlink(missing_ok=True)
                raise SystemExit("ERROR: Backup validation failed.")

        cursor = db.execute(
            "UPDATE users SET password_hash=? WHERE username='admin'",
            (stored,)
        )

        if cursor.rowcount != 1:
            raise SystemExit("ERROR: Admin password update failed.")

        db.commit()

    password = None
    confirm = None

    print("SUCCESS: Admin password updated.")
    print("Backup created:", backup_file)


if __name__ == "__main__":
    main()
