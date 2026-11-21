# -*- coding: utf-8 -*-
"""Read-only smoke tests for the installed FBRAH security extension."""
import os
import sys

os.environ.setdefault("FBRAH_AUTO_INDEX", "0")


def main():
    from app import app
    client = app.test_client()

    r = client.get("/login")
    assert r.status_code == 200, ("GET /login", r.status_code)
    html = r.get_data(as_text=True)
    assert 'name="fbrah-csrf"' in html, "CSRF meta token missing"
    assert 'name="_csrf_token"' in html, "CSRF hidden input missing"
    assert "X-FBRAH-CSRF" in html, "fetch CSRF helper missing"
    assert "/forgot-password" in html, "Forgot-password link missing"

    # POST without token must be rejected before reaching business handlers.
    r = client.post("/api/clear_dialogue", json={})
    assert r.status_code == 400, ("CSRF should reject unsafe POST", r.status_code)

    with client.session_transaction() as sess:
        token = sess.get("_fbrah_csrf")
    assert token, "CSRF session token missing"

    # GET must never perform the old clear-dialogue mutation; logout is POST-only.
    r = client.get("/api/clear_dialogue")
    assert r.status_code in (404, 405), ("GET clear dialogue should be disabled", r.status_code)
    r = client.get("/logout")
    assert r.status_code == 405, ("GET logout should be disabled", r.status_code)

    # Correct CSRF token should pass the CSRF layer (auth may then redirect).
    r = client.post("/api/clear_dialogue", json={}, headers={"X-FBRAH-CSRF": token})
    assert r.status_code != 400, ("Valid CSRF token rejected", r.status_code)

    # Password reset pages exist; no account data is required for the generic request response.
    r = client.get("/forgot-password")
    assert r.status_code == 200, ("GET forgot-password", r.status_code)
    assert "استعادة كلمة المرور" in r.get_data(as_text=True)

    # Security headers are present.
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "SAMEORIGIN"

    print("PASS: login page + CSRF injection + CSRF rejection + GET mutation disabled + reset page + headers")


if __name__ == "__main__":
    main()
