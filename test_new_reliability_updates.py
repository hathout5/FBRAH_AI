# -*- coding: utf-8 -*-
from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parent
APP=(ROOT/'app.py').read_text(encoding='utf-8')
HTML=(ROOT/'templates'/'index.html').read_text(encoding='utf-8')
CALC=(ROOT/'fbrah_advanced_calculator.py').read_text(encoding='utf-8')


def test_calculator_accepts_arabic_digits_and_percent_without_eval():
    assert 'def normalize_expression' in CALC
    assert 'digits = str.maketrans' in CALC
    assert 're.sub(r"(\\d+(?:\\.\\d+)?|\\([^()]*\\))\\s*%"' in CALC
    assert 'calculator_clear_history' in CALC and 'calculator_preview' in CALC
    assert 'eval(' not in CALC and 'new Function' not in CALC


def test_calculator_is_opened_from_question_row_and_can_insert_result():
    assert 'id="fbrahCalcInlineBtn"' in HTML
    assert 'id="fbrahCalcInsert"' in HTML
    assert 'id="fbrahCalcClear"' in HTML
    assert 'method:"DELETE"' in HTML


def test_reminders_support_recurrence_snooze_update_and_windows_worker():
    assert '"repeat_rule"' in APP and 'TEXT DEFAULT' in APP
    assert 'snooze_until' in APP
    assert 'def api_reminder_snooze' in APP
    assert 'def api_reminder_update_delete' in APP
    assert 'repeat_rule = "daily"' in APP
    assert 'repeat_rule = "weekly"' in APP
    assert 'repeat_rule = "monthly"' in APP
    assert 'fbrah_reminder_worker.py' in (ROOT/'START_FBRAH_REMINDERS.bat').read_text(encoding='utf-8')


def test_reminder_manager_and_tone_options_are_present():
    assert 'id="reminderManagerPanel"' in HTML
    assert '/api/reminders/"+it.id+"/snooze' in HTML
    assert 'id="alarmTone"' in HTML
    assert 'value="chime"' in HTML and 'value="ascending"' in HTML
    assert 'id="alarmVolume"' in HTML and 'id="alarmRepeatCount"' in HTML
    assert 'id="alarmTestBtn"' in HTML
    assert 'fbrahCalcDragHandle' in HTML and 'pointermove' in HTML


def test_news_never_invents_publisher_or_placeholder_content():
    assert 'return [];' in HTML[HTML.index('function fbrahTickerFallbackItems'):HTML.index('function renderTickerItems')]
    assert 'if not text or not publisher or not _is_article_url(raw_url):' in APP
    assert 'items = cleaned' in APP
    assert 'FBRAH_EGYPTIAN_JOKES_RSS_URL' in APP
    assert 'source:"FBRAH"' not in HTML and 'source:"فبرا"' not in HTML


def test_answer_style_and_dialogue_context_are_prompted():
    assert '_answer_style' in APP
    assert '_dialogue_context = recent_chat_context' in APP
    assert '_question_for_history = question' in APP
    assert 'calculate_question(' in APP and 'calculator routed locally; web search skipped' in APP
    assert 'dir="auto"' in HTML


def test_app_python_syntax():
    ast.parse(APP)
