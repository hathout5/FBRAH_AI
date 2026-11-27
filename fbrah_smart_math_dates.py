# -*- coding: utf-8 -*-
"""حساب التواريخ والأعمار والمتواليات الحسابية/الهندسية — عربي/إنجليزي."""
from __future__ import annotations

import calendar
import datetime as dt
import re
from decimal import Decimal, getcontext
from typing import Any, Dict, List, Optional, Tuple

getcontext().prec = 50

_AR_MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "ابريل": 4, "أبريل": 4, "مايو": 5,
    "يونيو": 6, "يوليو": 7, "اغسطس": 8, "أغسطس": 8, "سبتمبر": 9, "اكتوبر": 10,
    "أكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
_AR_WEEKDAYS = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
_EN_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _is_en(q: str) -> bool:
    ql = (q or "").lower()
    return bool(re.search(r"[a-z]{3,}", ql)) and not re.search(r"[\u0600-\u06FF]{3,}", q or "")


def parse_date_token(text: str) -> Optional[dt.date]:
    s = (text or "").strip()
    if not s:
        return None
    s = s.replace("\\", "/").replace(".", "/")
    # ISO / numeric
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except Exception:
            pass
    m = re.match(r"^(\d{1,2})\s+([^\s\d/]+)\s+(\d{4})$", s)
    if m:
        day = int(m.group(1))
        mon = _AR_MONTHS.get(m.group(2).lower()) or _AR_MONTHS.get(m.group(2))
        year = int(m.group(3))
        if mon:
            try:
                return dt.date(year, mon, day)
            except Exception:
                return None
    return None


def extract_dates(question: str) -> List[dt.date]:
    q = question or ""
    found: List[dt.date] = []
    patterns = [
        r"\b(\d{4}-\d{1,2}-\d{1,2})\b",
        r"\b(\d{1,2}/\d{1,2}/\d{4})\b",
        r"\b(\d{1,2}-\d{1,2}-\d{4})\b",
        r"\b(\d{1,2}\s+(?:يناير|فبراير|مارس|أبريل|ابريل|مايو|يونيو|يوليو|أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b",
    ]
    for pat in patterns:
        for m in re.finditer(pat, q, re.I):
            d = parse_date_token(m.group(1))
            if d and d not in found:
                found.append(d)
    return found


def age_from_birth(birth: dt.date, on_date: Optional[dt.date] = None) -> Dict[str, Any]:
    on = on_date or dt.date.today()
    if birth > on:
        return {"error": "birth_after_ref"}
    years = on.year - birth.year
    months = on.month - birth.month
    days = on.day - birth.day
    if days < 0:
        months -= 1
        prev = on.replace(day=1) - dt.timedelta(days=1)
        days += prev.day
    if months < 0:
        years -= 1
        months += 12
    total_days = (on - birth).days
    return {
        "years": years,
        "months": months,
        "days": days,
        "total_days": total_days,
        "birth": birth.isoformat(),
        "on": on.isoformat(),
        "weekday_birth": birth.weekday(),
    }


def date_diff(a: dt.date, b: dt.date) -> Dict[str, Any]:
    if a > b:
        a, b = b, a
    delta = b - a
    return {
        "from": a.isoformat(),
        "to": b.isoformat(),
        "days": delta.days,
        "weeks": delta.days // 7,
        "approx_years": round(delta.days / 365.2425, 2),
    }


def answer_date_age_question(question: str) -> Optional[str]:
    q = (question or "").strip()
    if not q:
        return None
    ql = q.lower()
    en = _is_en(q)
    dates = extract_dates(q)
    today = dt.date.today()

    wants_age = any(k in q for k in ("عمر", "سني", "سنيّ", "عمره", "عمرها")) or any(
        k in ql for k in ("age", "how old", "years old", "born on")
    )
    wants_diff = any(k in q for k in ("فرق", "بين تاريخ", "كم يوم", "كم يومًا", "كم يوما", "المدة بين")) or any(
        k in ql for k in ("difference", "how many days", "days between", "date difference")
    )
    wants_weekday = any(k in q for k in ("أي يوم", "اى يوم", "كان يوم", "يوافق")) or any(
        k in ql for k in ("what day", "which day", "day of week")
    )
    wants_add = any(k in q for k in ("بعد", "زائد", "أضف", "اضف")) and any(
        k in q for k in ("يوم", "أيام", "شهر", "سنة", "أسبوع")
    )

    if wants_age and dates:
        birth = dates[0]
        ref = dates[1] if len(dates) > 1 else today
        info = age_from_birth(birth, ref)
        if info.get("error"):
            return "تاريخ الميلاد بعد تاريخ المرجع — راجع التواريخ." if not en else "Birth date is after the reference date."
        wd = _EN_WEEKDAYS[info["weekday_birth"]] if en else _AR_WEEKDAYS[info["weekday_birth"]]
        if en:
            return (
                f"Age on {info['on']}:\n"
                f"• {info['years']} years, {info['months']} months, {info['days']} days\n"
                f"• Total days lived: {info['total_days']:,}\n"
                f"• Birth weekday: {wd}\n"
                f"• Birth date: {info['birth']}"
            )
        return (
            f"العمر في {info['on']}:\n"
            f"• {info['years']} سنة و {info['months']} شهر و {info['days']} يوم\n"
            f"• إجمالي الأيام: {info['total_days']:,}\n"
            f"• يوم الميلاد: {wd}\n"
            f"• تاريخ الميلاد: {info['birth']}"
        )

    if wants_diff and len(dates) >= 2:
        d = date_diff(dates[0], dates[1])
        if en:
            return (
                f"Date difference between {d['from']} and {d['to']}:\n"
                f"• {d['days']:,} days\n"
                f"• {d['weeks']:,} full weeks\n"
                f"• ≈ {d['approx_years']} years"
            )
        return (
            f"الفرق بين {d['from']} و {d['to']}:\n"
            f"• {d['days']:,} يوم\n"
            f"• {d['weeks']:,} أسبوع كامل\n"
            f"• ≈ {d['approx_years']} سنة"
        )

    if wants_weekday and dates:
        d0 = dates[0]
        wd = _EN_WEEKDAYS[d0.weekday()] if en else _AR_WEEKDAYS[d0.weekday()]
        if en:
            return f"{d0.isoformat()} falls on {wd}."
        return f"تاريخ {d0.isoformat()} يوافق يوم {wd}."

    # كم يوم مضى منذ تاريخ
    if dates and any(k in q for k in ("مضى", "مرت", "من يوم", "منذ")):
        d0 = dates[0]
        days = (today - d0).days
        if en:
            return f"From {d0.isoformat()} to today ({today.isoformat()}): {days:,} days."
        return f"من {d0.isoformat()} حتى اليوم ({today.isoformat()}): {days:,} يوم."

    return None


def geom_sum(a: Decimal, r: Decimal, n: int) -> Decimal:
    if n <= 0:
        return Decimal(0)
    if r == 1:
        return a * n
    return a * (r ** n - 1) / (r - 1)


def answer_sequence_word_problem(question: str) -> Optional[str]:
    """متواليات حسابية/هندسية ومسائل تضاعف يومي مقابل راتب شهري."""
    q = (question or "").strip()
    if not q:
        return None
    ql = q.lower()
    en = _is_en(q)

    # نموذج: دولار يتضاعف كل يوم لنهاية الشهر مقابل مليون شهرياً
    doubling = any(k in q for k in ("يتضاعف", "مضاعف", "تضاعف", "يتضاعف")) or any(
        k in ql for k in ("double", "doubles", "doubling", "twice each day")
    )
    million = any(k in q for k in ("مليون", "million", "1000000", "1,000,000"))
    day_pay = any(k in q for k in ("يوم", "اليوم الأول", "اول يوم", "أول يوم")) or "day" in ql
    month_pay = any(k in q for k in ("شهر", "شهريا", "شهريًا", "month"))

    if doubling and (million or month_pay) and day_pay:
        # افتراض 30 يوم إن لم يُحدد
        days = 30
        m = re.search(r"(\d{1,2})\s*(?:يوم|days?)", q, re.I)
        if m:
            days = max(1, min(366, int(m.group(1))))
        # أيام الشهر
        for name, num in (("يناير", 31), ("فبراير", 28), ("مارس", 31), ("ابريل", 30), ("أبريل", 30),
                          ("مايو", 31), ("يونيو", 30), ("يوليو", 31), ("اغسطس", 31), ("أغسطس", 31),
                          ("سبتمبر", 30), ("اكتوبر", 31), ("أكتوبر", 31), ("نوفمبر", 30), ("ديسمبر", 31)):
            if name in q:
                days = num
        start = Decimal(1)
        # إن ذُكر مبلغ بداية
        m2 = re.search(r"(?:دولار|dollar|\$)\s*([0-9]+(?:\.[0-9]+)?)", ql)
        if not m2:
            m2 = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:دولار|dollar|\$)", q, re.I)
        if m2:
            start = Decimal(m2.group(1))
        monthly = Decimal(1_000_000)
        m3 = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:مليون|million)", q, re.I)
        if m3:
            monthly = Decimal(m3.group(1).replace(",", "")) * Decimal(1_000_000)
        elif re.search(r"\b1\s*million\b|\bmillion\b", ql) and not m3:
            monthly = Decimal(1_000_000)
        total_double = geom_sum(start, Decimal(2), days)
        better = "doubling" if total_double > monthly else "monthly"
        if en:
            return (
                f"Comparison for {days} days:\n"
                f"• Fixed: {monthly:,.2f} per month\n"
                f"• Geometric (start {start}, ×2 each day): sum = {total_double:,.2f}\n"
                f"• Better choice: {'daily doubling' if better == 'doubling' else 'fixed monthly pay'}\n"
                f"• Difference: {abs(total_double - monthly):,.2f}\n"
                f"Formula: S_n = a (r^n − 1)/(r − 1) with a={start}, r=2, n={days}"
            )
        return (
            f"مقارنة لمدة {days} يوماً:\n"
            f"• الراتب الثابت: {monthly:,.2f} في الشهر\n"
            f"• المتوالية الهندسية (بداية {start} وتتضاعف يومياً): المجموع = {total_double:,.2f}\n"
            f"• الأفضل: {'التضاعف اليومي' if better == 'doubling' else 'الراتب الشهري الثابت'}\n"
            f"• الفرق: {abs(total_double - monthly):,.2f}\n"
            f"• القانون: S_n = a (r^n − 1)/(r − 1) حيث a={start} و r=2 و n={days}"
        )

    # متوالية هندسية صريحة
    if any(k in q for k in ("متوالية هندسية", "متتابعة هندسية", "geometric sequence", "geometric progression")):
        nums = [Decimal(x) for x in re.findall(r"[0-9]+(?:\.[0-9]+)?", q.replace(",", ""))]
        if len(nums) >= 3:
            a, r, n = nums[0], nums[1], int(nums[2])
            n = max(1, min(500, n))
            sn = geom_sum(a, r, n)
            an = a * (r ** (n - 1))
            if en:
                return f"Geometric sequence: a={a}, r={r}, n={n}\n• a_n = {an}\n• S_n = {sn}"
            return f"متوالية هندسية: a={a} ، r={r} ، n={n}\n• الحد النوني a_n = {an}\n• مجموع n حداً S_n = {sn}"

    # متوالية حسابية
    if any(k in q for k in ("متوالية حسابية", "متتابعة حسابية", "arithmetic sequence", "arithmetic progression")):
        nums = [Decimal(x) for x in re.findall(r"[0-9]+(?:\.[0-9]+)?", q.replace(",", ""))]
        if len(nums) >= 3:
            a, d, n = nums[0], nums[1], int(nums[2])
            n = max(1, min(10000, n))
            an = a + (n - 1) * d
            sn = n * (2 * a + (n - 1) * d) / 2
            if en:
                return f"Arithmetic sequence: a={a}, d={d}, n={n}\n• a_n = {an}\n• S_n = {sn}"
            return f"متوالية حسابية: a={a} ، d={d} ، n={n}\n• الحد النوني a_n = {an}\n• مجموع n حداً S_n = {sn}"

    return None


def try_smart_math_dates(question: str) -> Optional[str]:
    """نقطة دخول موحّدة."""
    for fn in (answer_sequence_word_problem, answer_date_age_question):
        try:
            ans = fn(question)
            if ans:
                return ans
        except Exception:
            continue
    return None
