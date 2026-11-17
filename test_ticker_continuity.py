"""Static regression checks for the continuous bilingual ticker."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


class TickerContinuityTests(unittest.TestCase):
    def test_marquee_uses_two_identical_sequences(self):
        self.assertIn(".ticker-sequence", HTML)
        self.assertIn("var second = first.cloneNode(true)", HTML)
        self.assertIn("translateX(-50%)", HTML)

    def test_arabic_and_english_have_opposite_flow_directions(self):
        self.assertIn('marquee.style.animationName = isEn ? "ticker-slide-rtl" : "ticker-slide-ltr"', HTML)
        self.assertIn('first.scrollWidth < tickerViewportWidth * 1.35', HTML)
        self.assertIn('fillPass < 8', HTML)
        self.assertIn('var map = { slow: "720s", normal: "540s", fast: "390s" }', HTML)
        self.assertIn("@keyframes ticker-slide-rtl", HTML)
        self.assertIn("@keyframes ticker-slide-ltr", HTML)

    def test_refresh_does_not_clear_current_items_before_fetch(self):
        fetch_start = HTML.index("function fetchLiveNews(force)")
        fetch_end = HTML.index("function startLiveNewsAutoRefresh()", fetch_start)
        fetch_code = HTML[fetch_start:fetch_end]
        self.assertNotIn("|| force", fetch_code)
        self.assertIn("لا تمسح الأخبار الحالية عند بدء التحديث", fetch_code)
        self.assertIn('if (!marquee.querySelector(".ticker-item"))', fetch_code)

    def test_failed_or_empty_refresh_keeps_existing_content(self):
        fetch_start = HTML.index("function fetchLiveNews(force)")
        fetch_end = HTML.index("function startLiveNewsAutoRefresh()", fetch_start)
        fetch_code = HTML[fetch_start:fetch_end]
        self.assertIn("else if (!marquee.querySelector(\".ticker-item\"))", fetch_code)
        self.assertIn(".catch(function(){", fetch_code)

    def test_each_language_has_an_independent_last_good_cache(self):
        self.assertIn('"by_lang"', APP)
        self.assertIn('"ar": {"at": 0.0, "items": [], "live": [], "live_at": 0.0}', APP)
        self.assertIn('"en": {"at": 0.0, "items": [], "live": [], "live_at": 0.0}', APP)
        self.assertIn("now - cached_live_at <= 900", APP)

    def test_arabic_rss_source_coverage_is_expanded(self):
        self.assertIn('"https://www.alaraby.co.uk/rss.xml", "العربي الجديد"', APP)
        self.assertIn('"https://aawsat.com/feed", "الشرق الأوسط"', APP)
        self.assertIn('"https://www.aa.com.tr/ar/rss/default?cat=all", "وكالة الأناضول"', APP)
        self.assertIn('"https://www.albayan.ae/rss", "البيان"', APP)
        self.assertIn('"https://www.al-ain.com/rss", "العين الإخبارية"', APP)

    def test_source_name_and_clickable_source_are_rendered(self):
        self.assertIn('srcNode.textContent = (isEn ? "Source: " : "المصدر: ") + src', HTML)
        self.assertIn('span.addEventListener("click", openTickerSource)', HTML)
        self.assertIn('window.open(url, "_blank", "noopener,noreferrer")', HTML)

    def test_rss_items_include_the_actual_source_summary_not_only_homepage_text(self):
        self.assertIn("content:encoded", APP)
        self.assertIn("description|summary", APP)
        self.assertIn('body = title if not summary', APP)
        self.assertIn('"text": body[:520]', APP)
        self.assertIn('curated_news = [it for it in curated_news if', APP)

    def test_fallback_does_not_present_generic_homepage_descriptions_as_news(self):
        start = HTML.index("function fbrahTickerFallbackItems()")
        end = HTML.index("function renderTickerItems(items)", start)
        fallback = HTML[start:end]
        self.assertNotIn("Central Bank of Egypt", fallback)
        self.assertNotIn("وزارة العدل المصرية", fallback)
        self.assertIn('source:"FBRAH"', fallback)
        self.assertIn('source:"فبرا"', fallback)

    def test_english_microphone_restore_is_icon_only(self):
        self.assertIn('voiceShow: "🎤"', HTML)
        self.assertIn('vrest.textContent = "🎤"', HTML)
        self.assertIn('"Show voice bar"', HTML)


if __name__ == "__main__":
    unittest.main()
