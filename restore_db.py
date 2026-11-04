import sqlite3
import os
import argparse
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "fbrah.db"
BACKUP_DIR = BASE_DIR / "backups"


def is_inside_project(path):
    try:
        path.resolve().relative_to(BASE_DIR.resolve())
        return True
    except ValueError:
        return False


def check_database(path):
    try:
        with sqlite3.connect(str(path)) as conn:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            return bool(result and result[0] == "ok")
    except sqlite3.Error:
        return False


def list_backups():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    backups = sorted(
        BACKUP_DIR.glob("*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    valid = []

    print("\nAvailable database backups:\n")

    for backup in backups:
        if check_database(backup):
            valid.append(backup)
            print(f"{len(valid)}. {backup.name} [VALID]")
        else:
            print(f"INVALID: {backup.name}")

    if not valid:
        print("No valid backups found.")

    return valid


def checkpoint_database(path):
    with sqlite3.connect(str(path), timeout=10) as conn:
        result = conn.execute(
            "PRAGMA wal_checkpoint(TRUNCATE)"
        ).fetchone()

        if result and result[0] != 0:
            raise RuntimeError(
                "Database is busy. Close the application and try again."
            )


def remove_sidecars(path):
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(path) + suffix)
        if sidecar.exists():
            sidecar.unlink()


def create_sqlite_backup(source_path, destination_path):
    with sqlite3.connect(str(source_path)) as source:
        with sqlite3.connect(str(destination_path)) as destination:
            source.backup(destination)


def restore_database(target, backup):
    target = target.resolve()
    backup = backup.resolve()

    if not is_inside_project(target) or not is_inside_project(backup):
        print("ERROR: Both files must be inside the project folder.")
        return False

    if not target.is_file():
        print(f"ERROR: Target database not found: {target.name}")
        return False

    if not backup.is_file() or not check_database(backup):
        print("ERROR: Backup is missing or invalid.")
        return False

    if target == backup:
        print("ERROR: Source and target cannot be the same file.")
        return False

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    safety_backup = BACKUP_DIR / (
        f"before_restore_{timestamp}.db"
    )

    temp_database = target.with_name(
        f"{target.name}.{timestamp}.restore.tmp"
    )

    try:
        # Checkpoint WAL before touching the target.
        checkpoint_database(target)

        # Preserve the current target database.
        create_sqlite_backup(target, safety_backup)

        if not check_database(safety_backup):
            raise RuntimeError("Safety backup verification failed.")

        # Build the restored database separately.
        create_sqlite_backup(backup, temp_database)

        if not check_database(temp_database):
            raise RuntimeError("Restored database verification failed.")

        # Remove old sidecars only after checkpoint and backup.
        remove_sidecars(target)

        # Replace the target only after successful verification.
        os.replace(temp_database, target)

        print("\nRESTORE SUCCESSFUL.")
        print(f"Target: {target.name}")
        print(f"Restored from: {backup.name}")
        print(f"Safety backup: {safety_backup.name}")
        print("Integrity: OK")

        return True

    except Exception as error:
        print(f"\nRESTORE FAILED: {error}")
        print(f"Safety backup, if created: {safety_backup}")
        return False

    finally:
        if temp_database.exists():
            temp_database.unlink()

        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(temp_database) + suffix)
            if sidecar.exists():
                sidecar.unlink()


def main():
    parser = argparse.ArgumentParser(
        description="Fbrah AI database restore utility"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List valid backups"
    )

    parser.add_argument(
        "--target",
        type=Path,
        default=DB_FILE,
        help="Target database inside the project folder"
    )

    parser.add_argument(
        "--backup",
        type=Path,
        help="Specific backup file inside the project folder"
    )

    args = parser.parse_args()

    if args.list:
        list_backups()
        return

    target = args.target.resolve()

    if not is_inside_project(target):
        print("ERROR: Target must be inside the project folder.")
        return

    print("=" * 48)
    print("FBRAH AI - DATABASE RESTORE")
    print("=" * 48)

    print(f"\nTarget database: {target.name}")
    print("\nIMPORTANT:")
    print("- Close the application before restoring.")
    print("- Ensure no other process is using the database.")
    print("- The current target will be backed up first.")

    if args.backup:
        selected = args.backup.resolve()

        if not is_inside_project(selected):
            print("ERROR: Backup must be inside the project folder.")
            return

        if not selected.is_file() or not check_database(selected):
            print("ERROR: Selected backup is invalid or missing.")
            return
    else:
        backups = list_backups()

        if not backups:
            return

        try:
            choice = input(
                "\nEnter backup number to restore (or 0 to cancel): "
            ).strip()

            if not choice.isdigit():
                print("Invalid selection.")
                return

            number = int(choice)

            if number == 0:
                print("Restore cancelled.")
                return

            if number > len(backups):
                print("Invalid backup number.")
                return

            selected = backups[number - 1]

        except KeyboardInterrupt:
            print("\nRestore cancelled.")
            return

    print(f"\nSelected backup: {selected.name}")

    confirmation = input(
        '\nType RESTORE to confirm: '
    ).strip()

    if confirmation != "RESTORE":
        print("Restore cancelled.")
        return

    restore_database(target, selected)


if __name__ == "__main__":
    main()