#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only release integrity checks. Does not import app.py or touch databases."""
from pathlib import Path
import ast
import os
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent

class ReleaseIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / "app.py").read_text(encoding="utf-8-sig")
        cls.html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8-sig")
        cls.env = (ROOT / ".env.example").read_text(encoding="utf-8-sig")

    def test_dialogue_country_context_helpers_are_present(self):
        self.assertIn("def infer_dialogue_country(", self.app)
        self.assertIn("def apply_dialogue_context(", self.app)
        self.assertIn("_recent_dialogue = recent_chat_context", self.app)
        self.assertIn("لا تنقل سياق بلد أو شخص أو ملف من حوار قديم", self.app)

    def test_dialogue_country_inference_examples(self):
        import re
        tree = ast.parse(self.app)
        wanted = {"infer_dialogue_country", "apply_dialogue_context"}
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
        module = ast.Module(body=nodes, type_ignores=[])
        namespace = {"re": re, "_DIALOGUE_COUNTRY_ALIASES": {
            "Egypt": ("مصر", "مصرية", "المصرية", "egypt", "egyptian", "cairo"),
            "United States": ("أمريكا", "الولايات المتحدة", "الولايات المتحده", "الولايات الامريكية", "usa", "united states", "american"),
            "United Kingdom": ("بريطانيا", "المملكة المتحدة", "المملكه المتحده", "uk", "united kingdom", "britain"),
            "Saudi Arabia": ("السعودية", "السعوديه", "المملكة العربية السعودية", "saudi arabia", "ksa"),
            "United Arab Emirates": ("الإمارات", "الامارات", "الإمارات العربية المتحدة", "uae", "united arab emirates"),
        }}
        exec(compile(module, "app.py", "exec"), namespace)
        infer = namespace["infer_dialogue_country"]
        apply = namespace["apply_dialogue_context"]
        self.assertEqual(infer("متى عُيّن وزير الدفاع؟", "من رئيس مصر؟", "رئيس جمهورية مصر العربية"), "Egypt")
        self.assertEqual(infer("Who is the prime minister?", "Who is the president of Egypt?", "Egypt's president"), "Egypt")
        self.assertEqual(infer("من رئيس الوزراء في السعودية؟", "من رئيس مصر؟", ""), "Saudi Arabia")
        self.assertEqual(infer("اشرح قانون العمل", "من رئيس مصر؟", ""), "")
        expanded, country = apply("متى عُيّن وزير الدفاع؟", "من رئيس مصر؟", "رئيس مصر")
        self.assertEqual(country, "Egypt")
        self.assertIn("Egypt", expanded)
        explicit, country = apply("من رئيس الوزراء في بريطانيا؟", "من رئيس مصر؟", "رئيس مصر")
        self.assertEqual(country, "United Kingdom")
        self.assertNotIn("مستنتج من الحوار", explicit)

    def test_python_syntax(self):
        for source in ROOT.glob("*.py"):
            if source.name.startswith("test_") or source.name in {
                "app.py", "backup_db.py", "restore_db.py", "reset_admin.py", "security_hardening.py"
            }:
                ast.parse(source.read_text(encoding="utf-8-sig"), filename=source.name)

    def test_release_manifest_matches_all_listed_files(self):
        manifest = ROOT / "MANIFEST_SHA256.txt"
        self.assertTrue(manifest.is_file())
        import hashlib
        for line in manifest.read_text(encoding="ascii").splitlines():
            if not line.strip():
                continue
            expected, relative = line.split(None, 1)
            target = ROOT / relative.strip().lstrip("*")
            self.assertTrue(target.is_file(), f"Missing manifest file: {relative}")
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertEqual(actual, expected.lower(), f"Hash mismatch: {relative}")

    def test_fallback_policy_enables_isolated_local_and_cloud_paths(self):
        self.assertIn('FBRAH_ALLOW_LOCAL_MODEL_FALLBACK=1', self.env)
        self.assertIn('FBRAH_ALLOW_CLOUD_FALLBACK=1', self.env)
        security_env = (ROOT / "ENV_SECURITY.example").read_text(encoding="utf-8-sig")
        self.assertIn('FBRAH_ALLOW_CLOUD_FALLBACK=1', security_env)
        self.assertIn('FBRAH_ALLOW_LOCAL_MODEL_FALLBACK=1', security_env)
        self.assertTrue((ROOT / "ENABLE_FALLBACK_LOCAL.ps1").is_file())
        self.assertIn('FBRAH_ALLOW_LOCAL_MODEL_FALLBACK") or "0"', self.app)
        self.assertIn('FBRAH_ALLOW_CLOUD_FALLBACK") or "0"', self.app)
        self.assertIn('GROQ_MODELS_LIST', self.app)
        self.assertIn('models_try[:4]', self.app)
        self.assertIn('return ask_ollama(', self.app[self.app.find('def resolve_llm('):self.app.find('def _rebuild_vector_chunks')])


    def test_local_gpt_oss_name_is_not_misclassified_as_groq(self):
        tree = ast.parse(self.app)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "is_groq_model")
        namespace = {}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "app.py", "exec"), namespace)
        classify = namespace["is_groq_model"]
        self.assertFalse(classify("gpt-oss:20b"))
        self.assertTrue(classify("groq:openai/gpt-oss-120b"))
        self.assertTrue(classify("openai/gpt-oss-120b"))

    def test_online_default_prefers_configured_gemini_and_offline_prefers_installed_local(self):
        tree = ast.parse(self.app)
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "choose_default_model"]
        self.assertEqual(len(nodes), 1)
        namespace = {
            "DEFAULT_MODEL": "qwen2.5:7b",
            "GEMINI_MODEL": "gemini-3.8-flash",
            "GEMINI_API_KEY": "configured",
            "GROQ_API_KEY": "configured",
            "is_internet_available": lambda: True,
            "is_gemini_model": lambda value: str(value or "").lower().startswith("gemini"),
            "is_groq_model": lambda value: str(value or "").lower().startswith(("groq", "openai/")),
        }
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "app.py", "exec"), namespace)
        choose = namespace["choose_default_model"]
        self.assertEqual(choose(["qwen2.5:7b", "gemini:gemini-3.8-flash"]), "gemini:gemini-3.8-flash")
        namespace["is_internet_available"] = lambda: False
        self.assertEqual(choose(["qwen2.5:7b", "gemini:gemini-3.8-flash"]), "qwen2.5:7b")

    def test_browser_persists_only_explicit_manual_model_selection(self):
        self.assertIn("model_user_selected: modelWasManuallySelected", self.html)
        self.assertIn("prefs.model_user_selected === true", self.html)
        self.assertIn("modelWasManuallySelected = true", self.html)
        self.assertIn("var previousModel = modelElBind.value", self.html)
        self.assertIn("modelElBind.value = previousModel", self.html)

    def test_ollama_refresh_endpoint_is_read_only_and_forces_discovery(self):
        self.assertIn('@app.route("/api/ollama/models", methods=["GET"])', self.app)
        endpoint = self.app[self.app.find("def api_ollama_models("):self.app.find("# 10. MAIN PAGE")]
        self.assertIn("get_available_models(force=True)", endpoint)
        self.assertIn("ollama_status()", endpoint)

    def test_terminal_logs_include_pid_and_provider_attempts(self):
        self.assertIn('[PID:{os.getpid()}]', self.app)
        self.assertIn('Process PID', self.app)
        self.assertIn('Cloud provider=GEMINI', self.app)
        self.assertIn('Cloud provider=GROQ', self.app)
        self.assertIn('Local provider=OLLAMA', self.app)

    def _load_resolver(self, ask_gemini, ask_groq, ask_ollama):
        from types import SimpleNamespace
        tree = ast.parse(self.app)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "resolve_llm")
        namespace = {
            "os": os,
            "GROQ_API_KEY": "configured-groq-key",
            "GEMINI_API_KEY": "configured-gemini-key",
            "GROQ_MODEL": "groq-default-model",
            "GEMINI_MODEL": "gemini-default-model",
            "is_gemini_model": lambda value: str(value or "").lower().startswith("gemini"),
            "is_groq_model": lambda value: str(value or "").lower().startswith("groq"),
            "ask_gemini": ask_gemini,
            "ask_groq": ask_groq,
            "ask_ollama": ask_ollama,
            "app": SimpleNamespace(logger=SimpleNamespace(warning=lambda *a, **k: None)),
            "log_terminal": lambda *a, **k: None,
        }
        exec(compile(ast.Module(body=[node], type_ignores=[]), "app.py", "exec"), namespace)
        return namespace["resolve_llm"]

    def test_gemini_429_falls_back_to_groq_only_when_enabled(self):
        calls = []
        resolver = self._load_resolver(
            lambda *a, **k: "GEMINI_HTTP_429: quota exceeded",
            lambda *a, **k: calls.append("groq") or "Groq success",
            lambda *a, **k: "local",
        )
        with patch.dict(os.environ, {"FBRAH_ALLOW_CLOUD_FALLBACK": "1"}):
            result = resolver("test", model="gemini")
        self.assertIn("تحويل تلقائي Gemini → GROQ", result)
        self.assertIn("Groq success", result)
        self.assertEqual(calls, ["groq"])

    def test_cloud_fallback_disabled_does_not_change_selected_provider(self):
        calls = []
        resolver = self._load_resolver(
            lambda *a, **k: "GEMINI_HTTP_429: quota exceeded",
            lambda *a, **k: calls.append("groq") or "Groq success",
            lambda *a, **k: calls.append("local") or "local answer",
        )
        with patch.dict(os.environ, {"FBRAH_ALLOW_CLOUD_FALLBACK": "0"}):
            result = resolver("test", model="gemini")
        self.assertIn("تجاوز Gemini حصة الاستخدام", result)
        self.assertEqual(calls, [])

    def test_gemini_invalid_key_does_not_fall_back_to_groq(self):
        calls = []
        resolver = self._load_resolver(
            lambda *a, **k: "خطأ Gemini (403): invalid API key",
            lambda *a, **k: calls.append("groq") or "Groq success",
            lambda *a, **k: "local",
        )
        with patch.dict(os.environ, {"FBRAH_ALLOW_CLOUD_FALLBACK": "1"}):
            result = resolver("test", model="gemini")
        self.assertIn("غير قابل للتحويل", result)
        self.assertEqual(calls, [])

    def test_local_mode_never_crosses_to_cloud(self):
        calls = []
        resolver = self._load_resolver(
            lambda *a, **k: calls.append("gemini") or "cloud",
            lambda *a, **k: calls.append("groq") or "cloud",
            lambda *a, **k: calls.append("ollama") or "local answer",
        )
        with patch.dict(os.environ, {"FBRAH_ALLOW_CLOUD_FALLBACK": "1", "FBRAH_ALLOW_LOCAL_MODEL_FALLBACK": "1"}):
            result = resolver("test", model="qwen2.5:7b")
        self.assertEqual(result, "local answer")
        self.assertEqual(calls, ["ollama"])

    def test_groq_429_falls_back_to_gemini_only_when_enabled(self):
        calls = []
        resolver = self._load_resolver(
            lambda *a, **k: calls.append("gemini") or "Gemini success",
            lambda *a, **k: "GROQ_HTTP_429: rate limit",
            lambda *a, **k: "local",
        )
        with patch.dict(os.environ, {"FBRAH_ALLOW_CLOUD_FALLBACK": "1"}):
            result = resolver("test", model="groq")
        self.assertIn("تحويل تلقائي GROQ → Gemini", result)
        self.assertIn("Gemini success", result)
        self.assertEqual(calls, ["gemini"])

    def test_groq_tries_configured_models_after_transient_failure(self):
        import requests
        tree = ast.parse(self.app)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "ask_groq")
        class Response:
            def __init__(self, status, payload=None):
                self.status_code = status
                self.ok = 200 <= status < 300
                self.text = "rate limit" if status == 429 else ""
                self._payload = payload or {}
            def json(self): return self._payload
        class Session:
            def __init__(self): self.models=[]
            def post(self, url, json, **kwargs):
                self.models.append(json["model"])
                if len(self.models)==1: return Response(429)
                return Response(200, {"choices":[{"message":{"content":"second model answer"}}]})
        session=Session()
        namespace={"GROQ_API_KEY":"test-key","GROQ_MODEL":"model-a","GROQ_MODELS_LIST":["model-a","model-b"],"GROQ_BASE_URL":"https://example.invalid","os":os,"requests":requests,"get_http_session":lambda:session,"_cloud_timeout_seconds":lambda value=None:30,"log_terminal":lambda *a,**k:None}
        exec(compile(ast.Module(body=[node],type_ignores=[]),"app.py","exec"),namespace)
        with patch.dict(os.environ,{"FBRAH_ALLOW_CLOUD_FALLBACK":"1"}):
            result=namespace["ask_groq"]("prompt",model="model-a")
        self.assertEqual(result,"second model answer")
        self.assertEqual(session.models,["model-a","model-b"])

    def test_gemini_tries_configured_models_after_429(self):
        import requests, time
        tree=ast.parse(self.app)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="ask_gemini")
        class Response:
            def __init__(self,status,payload=None):
                self.status_code=status; self.ok=200<=status<300
                self.text="quota exceeded" if status==429 else ""
                self._payload=payload or {}
            def json(self): return self._payload
        class Session:
            def __init__(self): self.models=[]
            def post(self,url,**kwargs):
                self.models.append(url.split("/models/")[1].split(":")[0])
                if len(self.models)==1: return Response(429)
                return Response(200,{"candidates":[{"content":{"parts":[{"text":"second Gemini model answer"}]}}]})
        session=Session()
        namespace={"GEMINI_API_KEY":"test-key","GEMINI_MODEL":"gemini-a","GEMINI_MODELS_LIST":["gemini-a","gemini-b"],"_GEMINI_MODELS_CACHE":{"ts":time.time(),"names":["gemini-b"]},"os":os,"time":time,"requests":requests,"normalize_gemini_model_id":lambda x:x,"_cloud_timeout_seconds":lambda value=None:30,"get_http_session":lambda:session,"log_terminal":lambda *a,**k:None,"app":type("A",(),{"logger":type("L",(),{"warning":staticmethod(lambda *a,**k:None)})()})()}
        exec(compile(ast.Module(body=[node],type_ignores=[]),"app.py","exec"),namespace)
        with patch.dict(os.environ,{"FBRAH_ALLOW_CLOUD_FALLBACK":"1"}):
            result=namespace["ask_gemini"]("prompt",model="gemini-a")
        self.assertEqual(result,"second Gemini model answer")
        self.assertEqual(session.models[:2],["gemini-a","gemini-b"])

    def test_local_fallback_candidates_are_installed_models_only(self):
        tree=ast.parse(self.app)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="_pick_local_qwen_fallbacks")
        namespace={"os":os,"get_available_models":lambda:["llama3.2","qwen2.5:7b","deepseek-r1:7b"],"DEFAULT_MODEL":"qwen2.5:7b"}
        exec(compile(ast.Module(body=[node],type_ignores=[]),"app.py","exec"),namespace)
        with patch.dict(os.environ,{"FBRAH_ALLOW_LOCAL_MODEL_FALLBACK":"1"}):
            self.assertEqual(namespace["_pick_local_qwen_fallbacks"]("qwen2.5:7b"),["qwen2.5:7b","llama3.2","deepseek-r1:7b"])
        with patch.dict(os.environ,{"FBRAH_ALLOW_LOCAL_MODEL_FALLBACK":"0"}):
            self.assertEqual(namespace["_pick_local_qwen_fallbacks"]("not-installed"),["not-installed"])

    def test_gemini_429_is_not_mislabeled_as_503(self):
        section = self.app[self.app.find('def ask_gemini('):self.app.find('def normalize_gemini_model_id')]
        self.assertIn('GEMINI_HTTP_{r.status_code}', section)
        self.assertNotIn('GEMINI_BUSY_503', section)
        self.assertIn('r.status_code in (408, 425, 429, 500, 502, 503, 504)', section)

    def test_cloud_timeout_is_configurable_and_bounded(self):
        self.assertIn('def _cloud_timeout_seconds(value=None):', self.app)
        self.assertIn('os.environ.get("FBRAH_CLOUD_TIMEOUT", "30")', self.app)
        self.assertIn('return max(10, min(parsed, 60))', self.app)
        self.assertIn('FBRAH_CLOUD_TIMEOUT=30', self.env)
        self.assertIn('timeout=(5, request_timeout)', self.app)

    def test_cloud_timeout_policy_values(self):
        tree = ast.parse(self.app)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_cloud_timeout_seconds")
        namespace = {"os": os}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "app.py", "exec"), namespace)
        policy = namespace["_cloud_timeout_seconds"]
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(policy(), 30)
        with patch.dict(os.environ, {"FBRAH_CLOUD_TIMEOUT": "5"}, clear=True):
            self.assertEqual(policy(), 10)
        with patch.dict(os.environ, {"FBRAH_CLOUD_TIMEOUT": "90"}, clear=True):
            self.assertEqual(policy(), 60)
        with patch.dict(os.environ, {"FBRAH_CLOUD_TIMEOUT": "invalid"}, clear=True):
            self.assertEqual(policy(), 30)

    def test_gemini_model_fallback_is_opt_in(self):
        self.assertIn('allow_model_fallback = (os.environ.get("FBRAH_ALLOW_CLOUD_FALLBACK") or "0")', self.app)
        self.assertIn('models_try = [model]', self.app)
        self.assertIn('if allow_model_fallback:', self.app)
        gemini = self.app[self.app.find('def ask_gemini('):self.app.find('def normalize_gemini_model_id')]
        self.assertLess(gemini.find('request_timeout = _cloud_timeout_seconds(timeout)'), gemini.find('v1beta/models?key='))
        self.assertIn('if allow_model_fallback:\n        try:\n            now = time.time()', gemini)

    def test_cloud_routing_is_centralized_and_mode_isolated(self):
        ollama = self.app[self.app.find('def ask_ollama('):self.app.find('def _strip_wrong_script')]
        self.assertIn('return resolve_llm(', ollama)
        self.assertNotIn('cloud_budget', ollama)
        resolver = self.app[self.app.find('def resolve_llm('):self.app.find('def _rebuild_vector_chunks')]
        self.assertIn('return ask_ollama(', resolver)
        self.assertIn('if GROQ_API_KEY and allow_cloud:', resolver)
        self.assertNotIn('FAILOVER(web)', self.app)
        self.assertNotIn('GEMINI_BUSY_503', self.app)
        self.assertIn('if GEMINI_API_KEY and allow_cloud:', resolver)
        self.assertIn('FBRAH_ALLOW_LOCAL_MODEL_FALLBACK', self.app)

    def test_upload_limits(self):
        self.assertIn('_bounded_int_env("FBRAH_MAX_UPLOAD_MB", 500, 1, 500)', self.app)
        self.assertIn('_bounded_int_env("FBRAH_OCR_MAX_PAGES", 200, 1, 200)', self.app)
        self.assertIn("FBRAH_MAX_UPLOAD_MB=500", self.env)

    def test_security_regressions(self):
        self.assertIn('html.escape(str(message), quote=True)', self.app)
        self.assertIn('len(password) < 12 or len(password) > 256', self.app)
        self.assertIn('len(new_pw) < 12 or len(new_pw) > 256', self.app)
        self.assertIn('12 <= len(password) <= 256', self.app)
        self.assertIn('@admin_required\n def api_self_heal', self.app.replace('def api_self_heal', ' def api_self_heal'))
        self.assertIn('methods=["POST"]', self.app[self.app.find('def api_recordings_export_all')-400:self.app.find('def api_recordings_export_all')])
        self.assertIn('x-goog-api-key', self.app)
        self.assertIn('init_security_hardening(app, get_db, hash_password)', self.app)
        self.assertIn('origin_parts.scheme != host_parts.scheme', (ROOT / "security_hardening.py").read_text(encoding="utf-8-sig"))
        self.assertIn('if not delivered:', (ROOT / "security_hardening.py").read_text(encoding="utf-8-sig"))
        self.assertIn('claimed.rowcount != 1', (ROOT / "security_hardening.py").read_text(encoding="utf-8-sig"))

    def test_pen_export_endpoint(self):
        self.assertIn('@app.route("/api/pen/export", methods=["POST"])', self.app)

    def test_news_has_source_and_safe_dom(self):
        self.assertIn('"source": source[:100]', self.app)
        self.assertIn('headline.textContent', self.html)
        self.assertIn('link.rel = "noopener noreferrer"', self.html)

    def test_mic_activation_is_navy(self):
        tail = self.html[self.html.rfind('/* حالة التفعيل بعد نداء'): ]
        self.assertIn('background: #001F3F !important;', tail)

    def test_state_changing_session_routes_are_post_only(self):
        self.assertIn('@app.route("/logout", methods=["POST"])', self.app)
        self.assertIn('@app.route("/api/clear_dialogue", methods=["POST"])', self.app)
        self.assertNotIn('@app.route("/api/clear_dialogue", methods=["POST", "GET"])', self.app)

    def test_public_sample_has_no_machine_specific_path(self):
        self.assertNotIn("C:\\\\Users\\\\", self.env)
        self.assertIn("FBRAH_LAW_OFFICE_FOLDER=~/FBRAH_Law_Office", self.env)
        self.assertNotIn("C:\\\\Users\\\\", self.app)


    def test_ticker_has_three_slower_speeds_pause_hide_restore_and_migration(self):
        self.assertIn('value="270">بطيء جداً', self.html)
        self.assertIn('value="240" selected>بطيء', self.html)
        self.assertIn('value="210">متوسط', self.html)
        self.assertIn('fbrahTickerPrefsV2', self.html)
        self.assertIn('fbrahTickerPrefsV1', self.html)
        self.assertIn('"150": 270', self.html)
        self.assertIn('"120": 240', self.html)
        self.assertIn('"90": 210', self.html)
        self.assertIn('function toggleTickerPause()', self.html)
        self.assertIn('function hideTicker()', self.html)
        self.assertIn('function showTicker()', self.html)

    def test_pen_uses_pointer_events_and_undo(self):
        self.assertIn('id="penUndo"', self.html)
        self.assertIn('canvas.addEventListener("pointerdown",start)', self.html)
        self.assertIn('canvas.addEventListener("pointercancel",end)', self.html)
        self.assertIn('function saveUndo()', self.html)

    def test_voice_activation_uses_navy_and_gold(self):
        self.assertIn('mic.style.background = "#001F3F"', self.html)
        self.assertIn('wakeBtn.setAttribute("aria-pressed", "true")', self.html)

    def test_hybrid_retrieval_uses_reciprocal_rank_fusion(self):
        self.assertIn('Reciprocal Rank Fusion', self.app)
        self.assertIn('weight / (rrf_k + rank)', self.app)
        self.assertIn('retrieval_sources', self.app)


    def test_answer_container_supports_arabic_and_english_direction(self):
        self.assertIn('role="status" dir="auto"', self.html)
        self.assertIn('unicode-bidi:plaintext', self.html)
        self.assertIn('text-align:start', self.html)

    def test_answer_output_is_not_marked_safe(self):
        self.assertNotIn("{{ answer|safe }}", self.html)
        self.assertIn("{{ answer }}", self.html)

    def test_bootstrap_password_is_not_written_to_logs(self):
        self.assertNotIn("كلمة مرور المدير الأولية: %s", self.app)
        self.assertIn("لن تُسجل كلمة المرور", self.app)

    def test_ollama_unavailable_does_not_advertise_fake_models(self):
        section = self.app[self.app.find("def get_available_models("):self.app.find("def get_models_for_ui(")]
        self.assertIn("_model_cache.update(at=now, models=[])", section)
        self.assertNotIn('"tinyllama:latest"', section)

    def test_pen_cloud_vision_requires_explicit_gemini_choice(self):
        section = self.app[self.app.find("def api_ocr_handwriting("):self.app.find('@app.route("/api/pen/export")')]
        self.assertIn('data.get("use_cloud_vision") is True', section)
        self.assertIn("is_gemini_model(selected_ocr_model)", section)

    def test_translation_reports_incomplete_parts_and_uses_chunking(self):
        section = self.app[self.app.find("def translate_text_quality("):self.app.find("def translate_text_to_arabic(")]
        self.assertIn("hard_limit = 120000", section)
        self.assertIn("failed.append(index)", section)
        self.assertIn("لم تُخفَ هذه الفجوة", section)

    def test_legacy_artifacts_are_ignored(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8-sig")
        self.assertIn("QUARANTINE_DO_NOT_RUN/", ignore)
        self.assertIn("test_fbrah_system.py", ignore)
        self.assertNotIn("test_index_integrity.py", ignore)
        self.assertNotIn("test_priority_smoke.py", ignore)

if __name__ == "__main__":
    unittest.main(verbosity=2)
