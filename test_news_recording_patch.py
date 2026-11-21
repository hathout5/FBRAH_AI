# -*- coding: utf-8 -*-
"""Regression checks for the 2026-11-20 news and recording reliability patch."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text(encoding="utf-8")
HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


def test_news_endpoint_returns_cached_feed_and_refreshes_in_background():
    assert "def _build_live_news_payload(language):" in APP
    assert "def _refresh_live_news_background(language):" in APP
    assert "_NEWS_REFRESH_EXECUTOR = ThreadPoolExecutor(max_workers=2)" in APP
    assert '"refreshing": refreshing' in APP
    assert "ex.shutdown(wait=False, cancel_futures=True)" in APP


def test_news_feed_deduplicates_and_extracts_publication_date():
    assert "seen_news_keys = set()" in APP
    assert '"published": published' in APP
    assert "pubDate|published|updated|dc:date" in APP


def test_news_ticker_is_not_paused_by_hover():
    assert ".ticker-marquee:hover" not in HTML
    assert "function toggleTickerPause()" in HTML


def test_recording_is_manual_and_has_two_hour_cap():
    assert "maxMs: 120 * 60 * 1000" in HTML
    assert "Recording starts only from the explicit record button." in HTML
    assert "FBRAH_REC_START" not in HTML
    assert "function isRecStartCommand" not in HTML


def test_recording_upload_lock_is_released_on_failure():
    assert "finally {\n                fbrahRec._uploadLock = false;" in HTML
    assert "التسجيل فارغ — أعد المحاولة" in HTML


def test_recording_list_initializes_once():
    assert "initRecordingListOnce" in HTML
    assert "window._fbrahRecListInitDone" in HTML


def test_app_python_syntax():
    ast.parse(APP, filename="app.py")
