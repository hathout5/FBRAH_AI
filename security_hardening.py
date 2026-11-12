# -*- coding: utf-8 -*-
"""FBRAH security extension: CSRF, safe password reset by email, and headers.

This module is intentionally independent of the application's business logic.
It uses the existing SQLite connection factory and password hasher supplied by
app.py. No password or reset token is logged or stored in plaintext.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import smtplib
import ssl
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from functools import wraps
from urllib.parse import urlparse

from flask import (Blueprint, abort, current_app, jsonify, make_response,
                   redirect, render_template_string, request, session, url_for)


CSRF_SESSION_KEY = "_fbrah_csrf"
CSRF_HEADER = "X-FBRAH-CSRF"
RESET_TTL_MINUTES = 20
RESET_MESSAGE_AR = "إذا كانت بيانات الحساب صحيحة وكان البريد مسجلاً، فستصلك رسالة تتضمن رابطاً مؤقتاً لإعادة التعيين. تحقق من البريد الوارد والرسائل غير المرغوب فيها."
RESET_MESSAGE_EN = "If the account details are valid and an email is registered, a time-limited reset link will be sent. Check your inbox and spam folder."


def _utcnow():
    return datetime.now(timezone.utc)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _db_exec(get_db, sql, params=()):
    with get_db() as db:
        cur = db.execute(sql, params)
        db.commit()
        return cur


def _send_reset_email(email: str, reset_url: str) -> bool:
    host = (os.environ.get("FBRAH_SMTP_HOST") or "").strip()
    sender = (os.environ.get("FBRAH_SMTP_FROM") or "").strip()
    username = (os.environ.get("FBRAH_SMTP_USER") or "").strip()
    password = os.environ.get("FBRAH_SMTP_PASSWORD") or ""
    if not host or not sender:
        current_app.logger.error("Password reset email is not configured (SMTP host/from missing).")
        return False
    try:
        port = int(os.environ.get("FBRAH_SMTP_PORT", "465"))
        timeout = min(max(int(os.environ.get("FBRAH_SMTP_TIMEOUT", "10")), 3), 30)
        msg = EmailMessage()
        msg["Subject"] = "FBRAH — Password reset / إعادة تعيين كلمة المرور"
        msg["From"] = sender
        msg["To"] = email
        msg.set_content(
            "طلب إعادة تعيين كلمة مرور FBRAH. الرابط صالح لمدة 20 دقيقة ولمرة واحدة فقط:\n\n"
            + reset_url + "\n\nإذا لم تطلب ذلك فتجاهل الرسالة. لا تشارك الرابط مع أحد."
        )
        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                if username:
                    smtp.login(username, password)
                smtp.send_message(msg)
        return True
    except Exception:
        current_app.logger.exception("Password reset email delivery failed.")
        return False


def init_security_hardening(app, get_db, hash_password):
    """Register hardening hooks and password-reset routes exactly once."""
    if app.extensions.get("fbrah_security_hardening"):
        return
    app.extensions["fbrah_security_hardening"] = True
    bp = Blueprint("fbrah_security", __name__)

    with app.app_context():
        with get_db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS fbrah_password_reset_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_fbrah_reset_user ON fbrah_password_reset_tokens(user_id)")
            db.execute("""CREATE TABLE IF NOT EXISTS fbrah_auth_throttle (
                bucket TEXT PRIMARY KEY,
                attempts INTEGER NOT NULL DEFAULT 0,
                window_started REAL NOT NULL,
                blocked_until REAL NOT NULL DEFAULT 0
            )""")
            db.commit()

    @app.before_request
    def _fbrah_csrf_guard():
        if not session.get(CSRF_SESSION_KEY):
            session[CSRF_SESSION_KEY] = secrets.token_urlsafe(32)
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            supplied = request.headers.get(CSRF_HEADER, "")
            if not supplied:
                supplied = request.form.get("_csrf_token", "")
            expected = session.get(CSRF_SESSION_KEY, "")
            if not expected or not supplied or not hmac.compare_digest(str(expected), str(supplied)):
                if request.path in ("/api/client_telemetry", "/api/client_log"):
                    # sendBeacon cannot set custom headers: accept only browser same-origin beacon.
                    origin = request.headers.get("Origin", "")
                    origin_parts = urlparse(origin)
                    host_parts = urlparse(request.host_url)
                    if (
                        not origin_parts.scheme
                        or origin_parts.scheme != host_parts.scheme
                        or origin_parts.netloc.casefold() != host_parts.netloc.casefold()
                        or origin_parts.username
                        or origin_parts.password
                    ):
                        abort(400, description="CSRF validation failed")
                else:
                    if request.path.startswith("/api/") or request.is_json:
                        return jsonify({"ok": False, "error": "csrf", "message": "انتهت صلاحية الطلب. حدّث الصفحة ثم أعد المحاولة."}), 400
                    abort(400, description="CSRF validation failed")

    @app.after_request
    def _fbrah_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(self), microphone=(self), geolocation=()")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if request.path.startswith(("/forgot-password", "/reset-password/")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Referrer-Policy"] = "no-referrer"
        if request.is_secure or os.environ.get("FBRAH_HTTPS") == "1":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        # Inject the synchronizer token into server-rendered forms, and into a meta tag
        # used by same-origin fetch requests. Only HTML responses are touched.
        if response.mimetype == "text/html" and response.direct_passthrough is False:
            try:
                body = response.get_data(as_text=True)
                token = session.get(CSRF_SESSION_KEY, "")
                meta = '<meta name="fbrah-csrf" content="' + token + '">'
                if "name=\"fbrah-csrf\"" not in body:
                    body = re.sub(r"(<head[^>]*>)", r"\1" + meta, body, count=1, flags=re.I)
                hidden = '<input type="hidden" name="_csrf_token" value="' + token + '">'
                body = re.sub(r"(<form\b[^>]*>)", lambda m: m.group(1) + hidden, body, flags=re.I)
                helper = """<script>(function(){var m=document.querySelector('meta[name=\\\"fbrah-csrf\\\"]');if(!m)return;var t=m.content;var f=window.fetch;window.fetch=function(input,init){init=init||{};var u=typeof input==='string'?input:(input&&input.url)||'';var method=(init.method||(input&&input.method)||'GET').toUpperCase();try{var x=new URL(u,location.href);if(x.origin===location.origin&&['POST','PUT','PATCH','DELETE'].indexOf(method)>=0){var h=new Headers(init.headers||(input&&input.headers)||{});h.set('X-FBRAH-CSRF',t);init.headers=h;}}catch(e){}return f.call(this,input,init);};})();</script>"""
                if "X-FBRAH-CSRF" not in body:
                    body = body.replace("</body>", helper + "</body>")
                response.set_data(body)
            except Exception:
                current_app.logger.exception("Could not inject CSRF token into HTML response")
        return response

    def _throttle_state(bucket):
        now = time.time()
        with get_db() as db:
            row = db.execute("SELECT attempts,window_started,blocked_until FROM fbrah_auth_throttle WHERE bucket=?", (bucket,)).fetchone()
            if not row:
                db.execute("INSERT INTO fbrah_auth_throttle(bucket,attempts,window_started,blocked_until) VALUES(?,0,?,0)", (bucket, now))
                db.commit()
                return False
            if float(row["blocked_until"] or 0) > now:
                return True
            return False

    def _consume_throttle(bucket, limit=5, window_seconds=3600, block_seconds=3600):
        now = time.time()
        with get_db() as db:
            row = db.execute("SELECT attempts,window_started,blocked_until FROM fbrah_auth_throttle WHERE bucket=?", (bucket,)).fetchone()
            if row and float(row["blocked_until"] or 0) > now:
                return False
            started = float(row["window_started"] or now) if row else now
            attempts = int(row["attempts"] or 0) if row else 0
            if now - started > window_seconds:
                started, attempts = now, 0
            attempts += 1
            blocked = now + block_seconds if attempts >= limit else 0
            db.execute("INSERT INTO fbrah_auth_throttle(bucket,attempts,window_started,blocked_until) VALUES(?,?,?,?) ON CONFLICT(bucket) DO UPDATE SET attempts=excluded.attempts,window_started=excluded.window_started,blocked_until=excluded.blocked_until", (bucket, attempts, started, blocked))
            db.commit()
            return True

    @app.before_request
    def _fbrah_login_throttle():
        if request.path == "/login" and request.method == "POST":
            ip = request.remote_addr or "unknown"
            ident = (request.form.get("username") or "").strip().lower()[:160]
            if _throttle_state("ip:" + ip) or _throttle_state("id:" + hashlib.sha256(ident.encode()).hexdigest()):
                return make_response("تم تجاوز عدد محاولات الدخول. انتظر 15 دقيقة ثم أعد المحاولة.", 429)

    @app.after_request
    def _fbrah_login_throttle_result(response):
        if request.path == "/login" and request.method == "POST":
            ip = request.remote_addr or "unknown"
            ident = (request.form.get("username") or "").strip().lower()[:160]
            buckets = ["ip:" + ip, "id:" + hashlib.sha256(ident.encode()).hexdigest()]
            if "user" in session:
                with get_db() as db:
                    db.executemany("DELETE FROM fbrah_auth_throttle WHERE bucket=?", [(b,) for b in buckets])
                    db.commit()
            elif response.status_code == 200:
                now = time.time()
                with get_db() as db:
                    for bucket in buckets:
                        row = db.execute("SELECT attempts,window_started FROM fbrah_auth_throttle WHERE bucket=?", (bucket,)).fetchone()
                        if not row:
                            db.execute("INSERT INTO fbrah_auth_throttle(bucket,attempts,window_started,blocked_until) VALUES(?,1,?,0)", (bucket, now))
                        else:
                            started = float(row["window_started"] or now)
                            attempts = 1 if now-started > 900 else int(row["attempts"] or 0)+1
                            blocked = now+900 if attempts >= 8 else 0
                            db.execute("UPDATE fbrah_auth_throttle SET attempts=?,window_started=?,blocked_until=? WHERE bucket=?", (attempts, now if attempts == 1 else started, blocked, bucket))
                    db.commit()
        return response

    @bp.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        message = ""
        if request.method == "POST":
            login_id = (request.form.get("username") or "").strip()[:160]
            # Identical response regardless of account existence or email configuration.
            ip_bucket = "reset-ip:" + (request.remote_addr or "unknown")
            allowed = _consume_throttle(ip_bucket, limit=5, window_seconds=3600, block_seconds=3600)
            if login_id and allowed:
                with get_db() as db:
                    user = db.execute("SELECT id,email FROM users WHERE username=? OR email=?", (login_id, login_id)).fetchone()
                if user and user["email"]:
                    raw = secrets.token_urlsafe(40)
                    digest = _token_hash(raw)
                    expires = (_utcnow() + timedelta(minutes=RESET_TTL_MINUTES)).isoformat()
                    created = _utcnow().isoformat()
                    with get_db() as db:
                        db.execute("UPDATE fbrah_password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL", (created, user["id"]))
                        db.execute("INSERT INTO fbrah_password_reset_tokens(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)", (digest, user["id"], expires, created))
                        db.commit()
                    public_base = (os.environ.get("FBRAH_PUBLIC_BASE_URL") or "").strip().rstrip("/")
                    parsed_base = urlparse(public_base)
                    delivered = False
                    if (public_base and parsed_base.scheme in ("https", "http") and parsed_base.netloc
                            and not parsed_base.username and not parsed_base.password
                            and not parsed_base.query and not parsed_base.fragment
                            and parsed_base.path in ("", "/")
                            and (parsed_base.scheme == "https" or parsed_base.hostname in ("localhost", "127.0.0.1"))):
                        reset_path = url_for("fbrah_security.reset_password", token=raw, _external=False)
                        delivered = _send_reset_email(user["email"], public_base + reset_path)
                    else:
                        current_app.logger.error("Password reset link delivery disabled: set FBRAH_PUBLIC_BASE_URL to the canonical public HTTPS URL.")
                    if not delivered:
                        # لا تترك رمزاً صالحاً لم يُسلّم إلى صاحب الحساب.
                        with get_db() as db:
                            db.execute(
                                "DELETE FROM fbrah_password_reset_tokens WHERE token_hash=? AND used_at IS NULL",
                                (digest,),
                            )
                            db.commit()
            message = RESET_MESSAGE_AR
        return render_template_string(_RESET_REQUEST_HTML, message=message)

    @bp.route("/reset-password/<token>", methods=["GET", "POST"])
    def reset_password(token):
        if not re.fullmatch(r"[A-Za-z0-9_-]{40,100}", token or ""):
            abort(404)
        digest = _token_hash(token)
        message = ""
        if request.method == "POST":
            pw = request.form.get("password") or ""
            pw2 = request.form.get("password2") or ""
            if len(pw) < 12 or len(pw) > 256:
                message = "يجب أن تكون كلمة المرور بين 12 و256 حرفاً."
            elif pw != pw2:
                message = "تأكيد كلمة المرور غير متطابق."
            else:
                now = _utcnow().isoformat()
                with get_db() as db:
                    row = db.execute(
                        "SELECT user_id FROM fbrah_password_reset_tokens "
                        "WHERE token_hash=? AND used_at IS NULL AND expires_at>?",
                        (digest, now),
                    ).fetchone()
                    if not row:
                        abort(400, description="رابط إعادة التعيين غير صالح أو منتهي الصلاحية.")
                    # Claim the one-time token first; concurrent submissions cannot both win.
                    claimed = db.execute(
                        "UPDATE fbrah_password_reset_tokens SET used_at=? "
                        "WHERE token_hash=? AND used_at IS NULL AND expires_at>?",
                        (now, digest, now),
                    )
                    if claimed.rowcount != 1:
                        abort(400, description="رابط إعادة التعيين استُخدم بالفعل أو انتهت صلاحيته.")
                    updated = db.execute(
                        "UPDATE users SET password_hash=? WHERE id=?",
                        (hash_password(pw), row["user_id"]),
                    )
                    if updated.rowcount != 1:
                        abort(400, description="تعذر تحديث الحساب المرتبط برابط الاستعادة.")
                    db.execute(
                        "UPDATE fbrah_password_reset_tokens SET used_at=? "
                        "WHERE user_id=? AND used_at IS NULL",
                        (now, row["user_id"]),
                    )
                    db.commit()
                session.clear()
                return redirect(url_for("login"))
        return render_template_string(_RESET_PASSWORD_HTML, message=message)

    app.register_blueprint(bp)


_RESET_REQUEST_HTML = """<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>استعادة كلمة المرور — FBRAH</title></head><body style='font-family:Tahoma,Arial;background:#f6f4ef;padding:30px'><main style='max-width:480px;margin:auto;background:white;padding:24px;border-radius:14px'><h2>استعادة كلمة المرور</h2><p>أدخل اسم المستخدم أو البريد الإلكتروني المسجل.</p><p>{{ message }}</p><form method='post'><label>اسم المستخدم أو البريد</label><input name='username' required maxlength='160' autocomplete='username'><button type='submit'>إرسال رابط الاستعادة</button></form><p><a href='/login'>العودة لتسجيل الدخول</a></p></main></body></html>"""
_RESET_PASSWORD_HTML = """<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>تعيين كلمة مرور جديدة — FBRAH</title></head><body style='font-family:Tahoma,Arial;background:#f6f4ef;padding:30px'><main style='max-width:480px;margin:auto;background:white;padding:24px;border-radius:14px'><h2>تعيين كلمة مرور جديدة</h2><p>{{ message }}</p><form method='post'><label>كلمة المرور الجديدة (12 حرفاً على الأقل)</label><input type='password' name='password' minlength='12' required autocomplete='new-password'><label>تأكيد كلمة المرور</label><input type='password' name='password2' minlength='12' required autocomplete='new-password'><button type='submit'>حفظ كلمة المرور</button></form></main></body></html>"""
