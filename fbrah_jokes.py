# -*- coding: utf-8 -*-
"""Egyptian jokes adapter for FBRAH ticker.

Fetches short jokes from public pages that publish Egyptian humor,
always with source name + article URL. Does not invent content.
Configure optional overrides:
  FBRAH_EGYPTIAN_JOKES_RSS_URL
  FBRAH_EGYPTIAN_JOKES_SOURCE
"""
from __future__ import annotations

import html
import os
import re
import time
from typing import List, Dict

_CACHE = {"at": 0.0, "items": []}
_CACHE_TTL = 300  # 5 minutes


def _clean_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _is_plausible_joke(text: str) -> bool:
    if not text or len(text) < 18 or len(text) > 280:
        return False
    # رفض عناوين أقسام وصفحات عامة
    bad = ("نكت مصرية", "أفضل نكت", "أجمل نكت", "مجموعة نكت", "اضحك", "اضغط", "المزيد")
    if any(b in text for b in bad) and len(text) < 40:
        return False
    # يفضّل وجود سياق حواري مصري خفيف
    markers = ("مرة", "واحد", "قالت", "قاله", "صاحبه", "مراته", "محشش", "صعيدي", "بيقول", "قال له", "؟")
    return sum(1 for m in markers if m in text) >= 1


def _fetch_url(url: str, timeout: float = 8.0) -> str:
    import urllib.request
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36 FBRAH/3.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ar,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(900000)
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return raw.decode("latin-1", errors="replace")


def _extract_list_items(page_html: str) -> List[str]:
    items = []
    # li bullets
    for m in re.finditer(r"<li[^>]*>(.*?)</li>", page_html, flags=re.I | re.S):
        t = _clean_text(m.group(1))
        if _is_plausible_joke(t):
            items.append(t)
    # paragraphs that look like jokes
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", page_html, flags=re.I | re.S):
        t = _clean_text(m.group(1))
        if _is_plausible_joke(t):
            items.append(t)
    # dedupe preserve order
    seen = set()
    out = []
    for t in items:
        key = t[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


# مصادر عامة تنشر نكتاً مصرية قصيرة مع صفحة قابلة للربط
_PUBLIC_SOURCES = [
    {
        "url": "https://wiifaq.com/%d9%86%d9%83%d8%aa-%d9%85%d8%b5%d8%b1%d9%8a%d8%a9-%d9%85%d8%b6%d8%ad%d9%83%d8%a9/",
        "source": "الوفاق",
    },
    {
        "url": "https://proarab.com/%D9%86%D9%83%D8%AA-%D9%85%D8%B5%D8%B1%D9%8A%D8%A9-%D9%85%D8%B6%D8%AD%D9%83%D8%A9/",
        "source": "برو عرب",
    },
    {
        "url": "https://www.proarab.net/2025/04/short-egyptian-jokes.html",
        "source": "ProArab",
    },
    {
        "url": "https://wiifaq.com/%d9%86%d9%83%d8%aa-%d9%85%d8%b6%d8%ad%d9%83%d8%a9-%d9%82%d8%b5%d9%8a%d8%b1%d8%a9-%d9%85%d8%b5%d8%b1%d9%8a%d8%a9/",
        "source": "الوفاق - قصيرة",
    },
    {
        "url": "https://proarab.com/%D9%86%D9%83%D8%AA-%D9%85%D8%B5%D8%B1%D9%8A%D8%A9-%D8%A8%D8%A7%D9%84%D8%B9%D8%A7%D9%85%D9%8A%D8%A9/",
        "source": "برو عرب - عامية",
    },
    {
        "url": "https://www.albawaba.com/ar/%D8%B5%D8%AD%D8%AA%D9%83%D9%90-%D9%88%D8%AC%D9%85%D8%A7%D9%84%D9%83%D9%90/%D9%86%D9%83%D8%AA-%D9%85%D8%B5%D8%B1%D9%8A%D8%A9-%D9%85%D8%B6%D8%AD%D9%83%D8%A9-1528956",
        "source": "البوابة",
    },
]


def _fetch_from_public_pages(limit: int = 20) -> List[Dict]:
    results: List[Dict] = []
    for src in _PUBLIC_SOURCES:
        if len(results) >= limit:
            break
        try:
            page = _fetch_url(src["url"])
            for joke in _extract_list_items(page):
                results.append({
                    "cat": "نكتة مصرية",
                    "icon": "😄",
                    "source": src["source"],
                    "text": joke,
                    "url": src["url"],
                    "published": "مصدر عام",
                })
                if len(results) >= limit:
                    break
        except Exception:
            continue
    return results


def _fetch_from_configured_rss(limit: int = 15) -> List[Dict]:
    feed = (os.environ.get("FBRAH_EGYPTIAN_JOKES_RSS_URL") or "").strip()
    source = (os.environ.get("FBRAH_EGYPTIAN_JOKES_SOURCE") or "").strip() or "نكت مصرية"
    if not feed.startswith("https://"):
        return []
    try:
        import urllib.request
        import xml.etree.ElementTree as ET
        req = urllib.request.Request(
            feed,
            headers={
                "User-Agent": "Mozilla/5.0 FBRAH/3.0",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read(500000)
        root = ET.fromstring(raw)

        def local(tag):
            return str(tag or "").rsplit("}", 1)[-1].split(":")[-1].lower()

        items = []
        for node in root.iter():
            if local(node.tag) not in ("item", "entry"):
                continue
            title = ""
            link = ""
            for child in list(node):
                t = local(child.tag)
                if t == "title":
                    title = _clean_text("".join(child.itertext()))
                elif t == "link":
                    href = (child.attrib.get("href") or "").strip()
                    text_link = (child.text or "").strip()
                    candidate = href or text_link
                    if candidate.startswith("http"):
                        link = candidate
            if title and link and _is_plausible_joke(title):
                items.append({
                    "cat": "نكتة مصرية",
                    "icon": "😄",
                    "source": source,
                    "text": title,
                    "url": link,
                    "published": "",
                })
            if len(items) >= limit:
                break
        return items
    except Exception:
        return []


def get_rotating_jokes(language: str = "ar", db_path=None, limit: int = 20) -> List[Dict]:
    """Return joke items for the ticker. Arabic only by default."""
    if not str(language or "ar").lower().startswith("ar"):
        return []
    now = time.time()
    if _CACHE["items"] and (now - float(_CACHE["at"] or 0)) < _CACHE_TTL:
        return list(_CACHE["items"])[:limit]

    items: List[Dict] = []
    items.extend(_fetch_from_configured_rss(limit=limit))
    if len(items) < limit:
        items.extend(_fetch_from_public_pages(limit=limit - len(items)))

    # dedupe by text prefix
    seen = set()
    unique = []
    for it in items:
        key = (it.get("text") or "")[:90]
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(it)

    if unique:
        _CACHE["at"] = now
        _CACHE["items"] = unique
    return unique[:limit]
