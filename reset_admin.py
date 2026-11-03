"""إعادة تعيين كلمة مرور admin — شغّله مرة واحدة ثم احذفه."""
import hashlib, secrets, sqlite3, os

DB = os.environ.get("FBRAH_DATABASE", os.path.join(os.path.dirname(__file__), "fbrah.db"))
NEW = os.environ.get("FBRAH_RESET_ADMIN_PASSWORD", "Admin@123456")

salt = secrets.token_hex(16)
digest = hashlib.pbkdf2_hmac("sha256", NEW.encode(), salt.encode(), 240_000).hex()
stored = f"pbkdf2_sha256${salt}${digest}"

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("UPDATE users SET password_hash=? WHERE username='admin'", (stored,))
if cur.rowcount == 0:
    cur.execute(
        "INSERT INTO users (username,password_hash,role,created_at) VALUES ('admin',?,'admin',datetime('now'))",
        (stored,),
    )
conn.commit()
conn.close()
print(f"OK — username: admin  password: {NEW}")
print(f"DB: {DB}")
