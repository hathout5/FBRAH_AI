
import sqlite3
from pathlib import Path
from datetime import datetime

# Project paths
BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "fbrah.db"
BACKUP_DIR = BASE_DIR / "backups"


def backup_database():
    if not DB_FILE.exists():
        print("ERROR: Database file not found.")
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = BACKUP_DIR / f"fbrah_{timestamp}.db"

    try:
        # Create a consistent SQLite backup
        with sqlite3.connect(str(DB_FILE)) as source:
            with sqlite3.connect(str(backup_file)) as destination:
                source.backup(destination)

                result = destination.execute(
                    "PRAGMA integrity_check"
                ).fetchone()

                if not result or result[0] != "ok":
                    raise RuntimeError("Database integrity check failed")

        print("SUCCESS: Database backup created.")
        print(f"Backup location: {backup_file}")

    except Exception as error:
        if backup_file.exists():
            backup_file.unlink()

        print(f"BACKUP FAILED: {error}")
        raise


if __name__ == "__main__":
    backup_database()
