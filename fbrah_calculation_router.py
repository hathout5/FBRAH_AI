# -*- coding: utf-8 -*-
"""Route explicit/pure arithmetic questions to the safe calculator, never to web search."""
from __future__ import annotations
import os, re, time
from fbrah_advanced_calculator import _db, evaluate_expression, normalize_expression

_PREFIXES = (
    r"احسب(?:لي| لي)?", r"احسب", r"كم يساوي", r"ما ناتج", r"ناتج",
    r"calculate", r"compute", r"what is", r"what's", r"evaluate",
)
_ALLOWED = re.compile(r"^[0-9٠-٩۰-۹\s+\-−*/×÷%^٪().,٫٬A-Za-z_\u0600-\u06ff]+$")
_HAS_OPERATOR = re.compile(r"[+\-−*/×÷%^٪]|\b(?:sqrt|sin|cos|tan|log|ln|exp|mean|median|percent|compound|pi|ans)\b|جذر|جا|جتا|ظا", re.I)
_PERCENT_OF = re.compile(r"^\s*([0-9٠-٩۰-۹]+(?:[.٫][0-9٠-٩۰-۹]+)?)\s*(?:%|٪|بالمئة|بالمائة)\s*(?:من|of)\s*([0-9٠-٩۰-۹]+(?:[.٫][0-9٠-٩۰-۹]+)?)\s*$", re.I)


def extract_expression(question: str):
    q = str(question or "").strip()
    if not q:
        return None
    q = re.sub(r"^(?:يا\s*)?(?:فبرا|خبرا|صبرا|fbrah|fbra)\s*[,،:؛-]?\s*", "", q, flags=re.I)
    q = q.strip().rstrip("؟?؛;.!،,")
    # لا تُحوّل التواريخ المكتوبة كأرقام إلى عمليات طرح أو قسمة.
    if re.fullmatch(r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}", q):
        return None
    explicit = False
    for prefix in _PREFIXES:
        m = re.match(r"^\s*(?:" + prefix + r")\s*[:：=]?\s*", q, flags=re.I)
        if m:
            q = q[m.end():].strip()
            explicit = True
            break
    percent = _PERCENT_OF.fullmatch(q)
    if percent:
        return f"{percent.group(2)}*{percent.group(1)}%"
    # لا تعتبر أرقام المواد وأرقام القوانين أو الجمل العربية حسابات لمجرد وجود / أو -.
    if not explicit and re.search(r"[ء-ي]", q) and not re.search(r"جذر|جا|جتا|ظا|باي", q):
        return None
    if not _ALLOWED.fullmatch(q):
        return None
    if not explicit and not _HAS_OPERATOR.search(q):
        return None
    if not _HAS_OPERATOR.search(q):
        return None
    return q


def calculate_question(question: str, username: str, db_path: str):
    expression = extract_expression(question)
    if not expression:
        return None
    user = (username or "").strip()
    if not user:
        return None
    con = _db(db_path)
    try:
        row = con.execute(
            "SELECT result FROM calculator_history WHERE username=? ORDER BY id DESC LIMIT 1",
            (user,),
        ).fetchone()
        ans = row["result"] if row else "0"
        source, value = evaluate_expression(expression, ans)
        result = format(value, "f")
        if "." in result:
            result = result.rstrip("0").rstrip(".")
        con.execute(
            "INSERT INTO calculator_history(username,expression,result,created_at) VALUES(?,?,?,?)",
            (user, source, result, time.time()),
        )
        con.commit()
        return {"expression": source, "result": result}
    finally:
        con.close()
