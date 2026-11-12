# -*- coding: utf-8 -*-
"""
تحسينات أولويات FBRAH (P2/P3) — تُستورد من app.py عند التوفر.
توليد صور، أدلة RAG، بوابة OCR سحابي، تنسيق مصادر.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote


# ---------- توليد الصور (P2) ----------

STYLE_KEYWORDS = {
    "realistic": ("واقعي", "واقعية", "فوتو", "photo", "realistic", "photoreal"),
    "illustration": ("توضيحي", "illustration", "رسم توضيحي", "تعليمي", "educational"),
    "legal": ("قانوني", "محكمة", "عقد", "legal", "court", "contract"),
    "cartoon": ("كرتون", "cartoon", "أنمي", "anime", "كاريكاتير", "caricature"),
    "diagram": ("مخطط", "diagram", "هندسي", "infographic", "إنفوجرافيك", "رسم بياني"),
    "infographic": ("إنفوجرافيك", "infographic", "معلومات مصورة"),
}


def detect_user_prompt_language(text: str) -> str:
    t = text or ""
    ar = len(re.findall(r"[\u0600-\u06ff]", t))
    lat = len(re.findall(r"[A-Za-z]", t))
    if ar >= max(3, lat // 2):
        return "ar"
    if lat >= 3:
        return "en"
    return "ar"


def detect_image_style(text: str) -> str:
    low = (text or "").lower()
    for style, keys in STYLE_KEYWORDS.items():
        if any(k.lower() in low or k in (text or "") for k in keys):
            return style
    return "illustration"


def enhance_image_prompt(user_text: str) -> Dict[str, Any]:
    """
    يفهم لغة الوصف، يحدد أسلوب الصورة، ويحسّن البرومبت لمحرك الرسم.
    لغة النص داخل الصورة تُحدد من الطلب أو تُطابق لغة الوصف.
    """
    raw = (user_text or "").strip()
    # إزالة أفعال الطلب الشائعة
    cleaned = re.sub(
        r"^(ارسم|رسم|ولد|ولّد|generate|draw|create|صورة|image)\s*",
        "",
        raw,
        flags=re.I,
    ).strip() or raw
    lang = detect_user_prompt_language(cleaned)
    style = detect_image_style(cleaned)

    # لغة النصوص داخل الصورة (مستقلة إن طُلبت)
    text_in_image = lang
    low = cleaned.lower()
    if any(x in low or x in cleaned for x in ("نص عربي", "كتابة عربية", "arabic text", "in arabic")):
        text_in_image = "ar"
    if any(x in low or x in cleaned for x in ("نص إنجليزي", "english text", "in english", "كتابة انجليزية")):
        text_in_image = "en"

    style_en = {
        "realistic": "photorealistic, high detail, natural lighting",
        "illustration": "clean educational illustration, clear labels",
        "legal": "professional legal diagram, formal, neutral colors",
        "cartoon": "cartoon style, friendly, clean outlines",
        "diagram": "technical diagram, vector-like, labeled parts",
        "infographic": "infographic layout, icons, readable typography",
    }.get(style, "clean illustration")

    if text_in_image == "ar":
        text_rule = "Any visible text in the image must be clear Arabic script, legible, high contrast."
    else:
        text_rule = "Any visible text in the image must be clear English, legible, high contrast."

    prompt = (
        f"{cleaned}. Style: {style_en}. {text_rule} "
        "No watermark, no logo, sharp focus, suitable for professional use."
    )
    return {
        "prompt": prompt,
        "style": style,
        "user_lang": lang,
        "text_in_image": text_in_image,
        "raw": cleaned,
    }


def pollinations_image_url(prompt: str, width: int = 1024, height: int = 1024) -> str:
    q = quote(prompt[:800], safe="")
    return f"https://image.pollinations.ai/prompt/{q}?width={width}&height={height}&nologo=true"


def format_generated_image_answer(meta: Dict[str, Any], url: str, is_en: bool = False) -> str:
    title = "Generated image" if is_en else "صورة مولَّدة"
    style = meta.get("style") or ""
    return (
        f"**{title}** ({style})\n\n"
        f'<div class="fbrah-media"><img src="{url}" alt="generated" '
        f'style="max-width:min(100%,520px);border-radius:10px;border:1px solid #d4af37" '
        f'loading="lazy" /></div>\n\n'
        f"{'Open / download:' if is_en else 'فتح / حفظ:'}\n{url}\n"
    )


# ---------- RAG / أدلة (P2) ----------

def passages_look_insufficient(passages: List[Any], min_chars: int = 180) -> bool:
    if not passages:
        return True
    total = 0
    for p in passages:
        if isinstance(p, dict):
            total += len((p.get("content") or p.get("text") or "")[:2000])
        else:
            total += len(str(p)[:2000])
    return total < min_chars


def format_passage_citations(passages: List[Any], limit: int = 8, is_en: bool = False) -> str:
    if not passages:
        return ""
    lines = ["**Sources / المصادر:**" if is_en else "**المصادر المستند إليها:**"]
    for i, p in enumerate(passages[:limit], 1):
        if isinstance(p, dict):
            title = p.get("title") or p.get("filepath") or p.get("source") or f"#{i}"
            path = p.get("filepath") or p.get("url") or ""
            snippet = (p.get("content") or p.get("text") or "")[:120].replace("\n", " ")
            lines.append(f"{i}. {title}" + (f" — {path}" if path else "") + (f"\n   «{snippet}…»" if snippet else ""))
        else:
            lines.append(f"{i}. {str(p)[:160]}")
    return "\n".join(lines)


def insufficient_evidence_message(is_en: bool = False) -> str:
    if is_en:
        return (
            "Insufficient retrieved passages to answer from local files with confidence. "
            "Upload related documents or enable web search."
        )
    return (
        "المقاطع المسترجعة من الملفات غير كافية للإجابة بثقة. "
        "ارفع مستندات ذات صلة أو فعّل البحث على الإنترنت."
    )


# ---------- OCR سحابي (P0/P1) ----------

def ocr_cloud_allowed() -> bool:
    return (os.environ.get("FBRAH_OCR_ALLOW_CLOUD") or "0").strip().lower() in ("1", "true", "yes")


def runtime_mode() -> str:
    return (os.environ.get("FBRAH_RUNTIME_MODE") or "hybrid").strip().lower()


def model_allowed_in_mode(model: str) -> bool:
    """فصل البيئات: local / cloud / hybrid."""
    mode = runtime_mode()
    m = (model or "").lower()
    is_cloud = m.startswith("gemini") or m.startswith("groq") or "gpt-oss" in m or "openai/" in m
    if mode == "local":
        return not is_cloud
    if mode == "cloud":
        return is_cloud
    return True  # hybrid


# ---------- تقسيم قانوني بسيط (P2) ----------

ARTICLE_SPLIT_RE = re.compile(
    r"(?=(?:^|\n)\s*(?:المادة|مادة|Article|Art\.)\s*\d+)",
    re.I | re.M,
)


def split_legal_sections(text: str, max_chunk: int = 1800) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in ARTICLE_SPLIT_RE.split(text) if p and p.strip()]
    if len(parts) <= 1:
        # تقسيم فقري
        paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        chunks, buf = [], ""
        for p in paras:
            if len(buf) + len(p) + 2 > max_chunk:
                if buf:
                    chunks.append(buf)
                buf = p
            else:
                buf = (buf + "\n\n" + p).strip() if buf else p
        if buf:
            chunks.append(buf)
        return chunks or [text[:max_chunk]]
    # دمج أجزاء المواد إن كانت قصيرة
    out, buf = [], ""
    for p in parts:
        if len(buf) + len(p) + 2 <= max_chunk:
            buf = (buf + "\n\n" + p).strip() if buf else p
        else:
            if buf:
                out.append(buf)
            buf = p
    if buf:
        out.append(buf)
    return out
