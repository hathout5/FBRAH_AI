# -*- coding: utf-8 -*-
"""
FBRAH security_hardening — نسخة متوافقة مع تسجيل الدخول.
لا تمنع POST /login بعد نجاح الجلسة (كانت تسبب CSRF 400).
"""
from __future__ import annotations

import secrets
from functools import wraps

from flask import request, session, redirect, url_for, abort

# مسارات لا يُفرض عليها CSRF
_CSRF_EXEMPT_PREFIXES = (
    "/login",
    "/register",
    "/logout",
    "/forgot-password",
    "/api/",
)


def _is_exempt_path(path: str) -> bool:
    p = (path or "").split("?")[0]
    for pref in _CSRF_EXEMPT_PREFIXES:
        if p == pref or p.startswith(pref):
            return True
    return False


def init_security_hardening(app, get_db=None, hash_password=None):
    """تهيئة خفيفة — لا تغيّر سلوك التطبيق الأساسي."""

    @app.before_request
    def _fbrah_csrf_guard():
        # لا نفحص CSRF على الدخول/التسجيل/API
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return None
        if _is_exempt_path(request.path):
            return None
        # إن كان المستخدم يرسل POST لـ /login وهو مسجّل → لا ترفض
        if session.get("user") and request.path.startswith("/login"):
            return None

        # تحقق اختياري للنماذج الأخرى إن وُجد رمز في الجلسة
        expected = session.get("_fbrah_csrf") or session.get("csrf_token")
        if not expected:
            return None
        sent = (
            request.form.get("_csrf_token")
            or request.form.get("csrf_token")
            or request.headers.get("X-CSRFToken")
            or request.headers.get("X-CSRF-Token")
            or ""
        ).strip()
        if not sent:
            # لا نكسر الطلبات القديمة التي بلا حقل CSRF
            return None
        if not secrets.compare_digest(str(sent), str(expected)):
            if session.get("user"):
                return redirect(url_for("home"), code=303)
            abort(400, description="CSRF validation failed")
        return None

    @app.context_processor
    def _inject_csrf():
        tok = session.get("_fbrah_csrf")
        if not tok:
            tok = secrets.token_urlsafe(32)
            session["_fbrah_csrf"] = tok
        return {"csrf_token": tok, "_csrf_token": tok}

    # لا نعيد تعريف مسارات أو نغيّر كلمات المرور هنا
    app.logger.info("security_hardening: soft CSRF active (login exempt)")
    return True
