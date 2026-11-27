# -*- coding: utf-8 -*-
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parent
APP=(ROOT/"app.py").read_text(encoding="utf-8")
HTML=(ROOT/"templates"/"index.html").read_text(encoding="utf-8")

def test_calculator_blueprint_is_registered():
    assert "register_calculator(app, os.path.join(DATA_DIR, \"fbrah_calculator_history.db\"))" in APP
    assert "/api/calculator/evaluate" in (ROOT/"fbrah_advanced_calculator.py").read_text(encoding="utf-8")

def test_scientific_calculator_ui_has_no_eval():
    assert "fbrahCalcPanel" in HTML and "fbrahCalcReport" in HTML
    script=HTML.split('<script id="fbrahAdvancedCalculatorUI">',1)[1].split("</script>",1)[0]
    assert "eval(" not in script and "new Function" not in script
    assert "calcScreenLines" in script

def test_news_sources_are_expanded_and_clickable():
    assert "arabic.cnn.com/api/v1/rss/rss.xml" in APP
    assert "cnbc.com/id/100727362/device/rss/rss.html" in APP
    assert "rss.dw.com/xml/rss-ar-all" in APP
    assert "window.open(u, \"_blank\", \"noopener,noreferrer\")" in HTML
    assert "marquee.addEventListener(\"mouseenter\"" in HTML
    assert "marquee.addEventListener(\"mouseleave\"" in HTML

def test_news_ticker_no_longer_uses_placeholder_news():
    block=APP[APP.index("def _build_live_news_payload"):APP.index("def _refresh_live_news_background")]
    assert "curated_news = []" in block
    assert "مصادر موثوقة" in block

def test_key_points_require_minimum_and_scale_with_file_size():
    assert "desired_points = max(5, min(30" in APP
    assert "key_points synthesis failed" in APP
    assert "def _extractive_key_points" in APP

def test_joke_rotation_module_and_no_fbrah_label():
    assert (ROOT/"fbrah_jokes.py").exists()
    assert 'source":"فبرا"' not in APP
    assert 'نكتة فبرا' not in HTML

def test_python_sources_compile():
    ast.parse(APP)
    ast.parse((ROOT/"fbrah_advanced_calculator.py").read_text(encoding="utf-8"))
    ast.parse((ROOT/"fbrah_jokes.py").read_text(encoding="utf-8"))


def test_new_integrated_modules_and_installer_are_in_package():
    for name in ("fbrah_calculation_router.py", "fbrah_reminder_core.py", "fbrah_reminder_worker.py"):
        assert (ROOT/name).exists()
    installer=(ROOT/"APPLY_UPDATE.ps1").read_text(encoding="utf-8-sig")
    assert "fbrah_calculation_router.py" in installer
    assert "fbrah_reminder_worker.py" in installer
    assert "fbrah.db" in installer and ".env" in installer
