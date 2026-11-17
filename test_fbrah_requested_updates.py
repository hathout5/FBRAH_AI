# -*- coding: utf-8 -*-
"""Static regression checks for the requested 2026-11-17 UI updates."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def test_voice_drag_does_not_minimize_open_panel():
    start = HTML.index("function onDragDown(e)")
    end = HTML.index("function onDragMove(e)", start)
    block = HTML[start:end]
    assert "setMinimized(true" not in block
    assert "اسحب اللوحة كما هي" in block


def test_voice_default_fab_is_adjacent_to_news_ticker():
    assert 'document.getElementById("fbrahNewsTicker")' in HTML
    assert "tr.top : window.innerHeight - 48) - 66" in HTML


def test_ticker_uses_continuous_horizontal_duplicate_sequences():
    assert ".ticker-sequence" in HTML
    assert 'cloneNode(true)' in HTML
    assert 'transform: translateX(-50%)' in HTML
    assert "tickerPixelsPerSecond" in HTML


def test_ticker_news_refresh_and_source_open_are_present():
    assert "_fbrahNewsTimer = setInterval" in HTML
    assert 'window.open(url, "_blank", "noopener,noreferrer")' in HTML
    assert 'headline.textContent = body' in HTML
    assert 'date.textContent=published' in HTML
    assert '"published": it.get("published") or ""' in APP


def test_calculator_is_live_and_does_not_use_eval():
    assert 'id="fbrahCalcPreview"' in HTML
    assert "function tokenize(src)" in HTML
    assert "function calculate(source)" in HTML
    calc = HTML[HTML.rfind("(function initFbrahInlineCalculator") :]
    assert "eval(" not in calc
    assert "new Function" not in calc
    assert 'input.addEventListener("input",update)' in calc


def test_app_python_syntax():
    ast.parse(APP)


def test_answer_speech_waits_for_voices_and_keeps_full_text():
    speech = HTML[HTML.index("function speakAnswerDirect(spoken, opts)") : HTML.index("function speakAnswer(opts)")]
    assert "onvoiceschanged" in speech
    assert "setTimeout(begin, 900)" not in speech  # guarded fallback is explicit below
    assert "voiceWait" in speech
    assert "rest = rest.slice(cut).trim()" in speech
    assert "chunk.length > 500" not in speech
    answer = HTML[HTML.index("function speakAnswer(opts)") : HTML.index("function stopSpeak()")]
    assert '#answerBlock .answer' in answer
    assert 'spoken.length > 10000' not in answer
