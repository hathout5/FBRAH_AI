# -*- coding: utf-8 -*-
"""اختبارات دخان عربية/إنجليزية لأولويات FBRAH — تشغيل: python -m pytest tests/ -q"""
import os
import sys

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_import_enhancements():
    import fbrah_priority_enhancements as e
    assert hasattr(e, "enhance_image_prompt")
    assert hasattr(e, "ocr_cloud_allowed")


def test_image_prompt_ar():
    import fbrah_priority_enhancements as e
    meta = e.enhance_image_prompt("ارسم مخططاً قانونياً لعقد بيع")
    assert meta["user_lang"] == "ar"
    assert meta["style"] in ("legal", "diagram", "illustration")
    assert "prompt" in meta and len(meta["prompt"]) > 10


def test_image_prompt_en():
    import fbrah_priority_enhancements as e
    meta = e.enhance_image_prompt("Draw a realistic photo of a courtroom")
    assert meta["user_lang"] == "en"
    assert meta["style"] == "realistic"


def test_insufficient_passages():
    import fbrah_priority_enhancements as e
    assert e.passages_look_insufficient([]) is True
    assert e.passages_look_insufficient([{"content": "x"}]) is True
    assert e.passages_look_insufficient([{"content": "a" * 500}]) is False


def test_legal_split():
    import fbrah_priority_enhancements as e
    text = "مقدمة\n\nالمادة 1\nنص المادة الأولى.\n\nالمادة 2\nنص الثانية."
    parts = e.split_legal_sections(text)
    assert len(parts) >= 1


def test_ocr_cloud_default_off(monkeypatch=None):
    import fbrah_priority_enhancements as e
    os.environ.pop("FBRAH_OCR_ALLOW_CLOUD", None)
    assert e.ocr_cloud_allowed() is False


def test_answer_output_uses_jinja_autoescape():
    with open(os.path.join(ROOT, "templates", "index.html"), "r", encoding="utf-8") as f:
        html = f.read()
    assert "{{ answer }}" in html
    assert "{{ answer|safe }}" not in html


def test_security_extension_is_registered():
    with open(os.path.join(ROOT, "app.py"), "r", encoding="utf-8") as f:
        source = f.read()
    assert "from security_hardening import init_security_hardening" in source
    assert "init_security_hardening(app, get_db, hash_password)" in source
    assert "getpass" not in source  # admin reset prompts are isolated in reset_admin.py


if __name__ == "__main__":
    test_import_enhancements()
    test_image_prompt_ar()
    test_image_prompt_en()
    test_insufficient_passages()
    test_legal_split()
    test_ocr_cloud_default_off()
    test_answer_output_uses_jinja_autoescape()
    test_security_extension_is_registered()
    print("OK all smoke tests passed")
