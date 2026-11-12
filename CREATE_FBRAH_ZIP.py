# -*- coding: utf-8 -*-
"""ينشئ FBRAH_COMPLETE_PRIORITY.zip جاهز للتحميل."""
import os
import zipfile
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "fbrah_src")
OUT = os.path.join(HERE, "FBRAH_COMPLETE_PRIORITY.zip")

SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    "QUARANTINE_DO_NOT_RUN", "backups", ".pytest_cache",
}
SKIP_SUFFIX = (".pyc", ".pyo", ".log", ".bak", ".db", ".db-wal", ".db-shm", ".db-journal")
SKIP_NAMES = {".secret_key", ".initial_admin_password", "fbrah.db"}


def skip(dirpath, name, is_dir):
    if is_dir and name in SKIP_DIRS:
        return True
    if not is_dir:
        if name in SKIP_NAMES or name.endswith(SKIP_SUFFIX):
            return True
        if name.startswith(".env") and name != ".env.example":
            return True
    return False


def main():
    assert os.path.isdir(SRC), SRC
    n = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "README_AR.txt",
            "FBRAH — حزمة الأولويات الكاملة P0–P3 (جزئي لـ P2/P3)\n"
            "1) فك الضغط\n"
            "2) انسخ محتويات FBRAH/ فوق مشروعك\n"
            "3) python app.py\n"
            "4) اختبارات: python tests/test_priority_smoke.py\n",
        )
        n += 1
        notes = os.path.join(HERE, "FBRAH_P0_P1_SECURITY_NOTES.md")
        if os.path.isfile(notes):
            z.write(notes, "FBRAH_P0_P1_SECURITY_NOTES.md")
            n += 1
        for dp, dns, fns in os.walk(SRC):
            dns[:] = [d for d in dns if not skip(dp, d, True)]
            for fn in fns:
                if skip(dp, fn, False):
                    continue
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, SRC).replace("\\", "/")
                z.write(full, "FBRAH/" + rel)
                n += 1
    print("WROTE", OUT)
    print("FILES", n)
    print("BYTES", os.path.getsize(OUT))


if __name__ == "__main__":
    main()
