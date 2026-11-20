"""Static regression checks for the FBRAH news ticker and draggable voice bar."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text(encoding="utf-8")
HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
TREE = ast.parse(APP)


class NewsVoiceFeatureTests(unittest.TestCase):
    def test_news_endpoint_is_rss_backed_not_static_headlines(self):
        self.assertIn("_LIVE_NEWS_FEEDS", APP)
        self.assertIn("ET.fromstring", APP)
        self.assertIn("@app.route(\"/api/live_news", APP)
        self.assertNotIn("محكمة النقض تؤكد في أحدث مبادئها", APP)

    def test_feed_hosts_are_preconfigured_and_https(self):
        self.assertIn('"url": "https://feeds.bbci.co.uk/arabic/rss.xml"', APP)
        self.assertIn('"url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"', APP)
        self.assertIn('"url": "https://www.almasryalyoum.com/rss/"', APP)
        self.assertIn('"url": "https://www.nature.com/nature.rss"', APP)

    def test_news_ticker_uses_safe_dom_text(self):
        self.assertIn("marquee.replaceChildren()", HTML)
        self.assertIn("title.textContent = item.text", HTML)
        self.assertIn('link.rel = "noopener noreferrer"', HTML)
        self.assertNotIn('span.innerHTML = "<span class=\'ticker-cat\'>"', HTML)

    def test_voice_bar_persists_position_and_clamps_to_viewport(self):
        self.assertIn('var storageKey = "fbrahVoiceBarPosV2"', HTML)
        self.assertIn("window.addEventListener(\"pointermove\", onDragMove)", HTML)
        self.assertIn("window.innerWidth - Math.min(w, window.innerWidth)", HTML)
        self.assertIn("handle.addEventListener(\"keydown\"", HTML)

    def test_no_duplicate_mouse_drag_handlers(self):
        self.assertNotIn('window.addEventListener("mousemove", function (e)', HTML)
        self.assertNotIn('handle.addEventListener("mousedown", function (e)', HTML)

    def test_tts_reads_answer_body_and_stops_before_sources(self):
        self.assertIn("function stripLinksForSpeech(text)", HTML)
        self.assertIn("var sourceHeading =", HTML)
        self.assertIn('clone.querySelectorAll("a, img, script, style, button, nav, footer, sup', HTML)
        self.assertNotIn("spoken.length > 1800", HTML)
        self.assertIn("var max = 800, offset = 0", HTML)

    def test_minimized_voice_toolbar_is_a_draggable_microphone_icon(self):
        self.assertIn("width:68px !important; height:68px !important", HTML)
        self.assertIn("#voiceBar.voice-minimized .voice-toolbar-actions { display:none", HTML)
        self.assertIn("suppressMiniClick", HTML)
        self.assertIn('handle.textContent = minimized ? "🎙️"', HTML)
        self.assertIn("bar.dataset.lastWidth", HTML)
        self.assertIn("hidden: hidden", HTML)

    def test_wake_listening_has_longer_silence_window(self):
        self.assertIn("}, 6500);", HTML)
        self.assertNotIn("}, 2200);", HTML)
        self.assertIn("if (isListening && !voiceSubmitLock)", HTML)

    def test_auto_model_routing_is_network_checked_and_local_offline(self):
        self.assertIn("FBRAH_AUTO_MODEL_ROUTING", APP)
        self.assertIn("def _select_auto_model", APP)
        self.assertIn("generativelanguage.googleapis.com/v1beta/models", APP)
        self.assertIn('GROQ_BASE_URL + "/models"', APP)
        self.assertIn("no authenticated cloud provider reachable; using local Ollama", APP)
        self.assertIn('value="auto"', HTML)
        env = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("FBRAH_RUNTIME_MODE=hybrid", env)
        self.assertIn("FBRAH_AUTO_MODEL_ROUTING=1", env)
        self.assertIn("FBRAH_ALLOW_LOCAL_MODEL_FALLBACK=1", env)
        self.assertIn("FBRAH_ALLOW_CLOUD_FALLBACK=1", env)

    def test_send_button_resets_after_completed_page_response(self):
        self.assertIn('window.addEventListener("pageshow", resetSend)', HTML)
        self.assertIn('send.disabled = false', HTML)
        self.assertIn('send.classList.remove("busy", "fbrah-working", "working", "is-busy")', HTML)


if __name__ == "__main__":
    unittest.main(verbosity=2)
