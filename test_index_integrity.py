"""اختبارات ثابتة وآمنة لحزمة FBRAH AI — لا تستورد Flask ولا تلمس قواعد البيانات."""
import ast
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text(encoding="utf-8")
HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
ENV_EXAMPLE = (ROOT / ".env.example").read_text(encoding="utf-8")
TREE = ast.parse(APP)


def function_node(name):
    for node in TREE.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


class ProjectIntegrityTests(unittest.TestCase):
    def test_python_ast_parses(self):
        self.assertIsNotNone(TREE)

    def test_index_scope_guard_exists(self):
        self.assertIsNotNone(function_node("index_needs_rebuild"))
        self.assertIn("doc_index.scope_signature != expected", APP)

    def test_vector_clear_handles_chroma_and_qdrant(self):
        self.assertIn('self.backend == "chroma"', APP)
        self.assertIn('self.backend == "qdrant"', APP)
        self.assertIn("create_collection(", APP)
        self.assertIn("def _rebuild_vector_chunks", APP)

    def test_vector_ids_are_deterministic(self):
        self.assertIn('hashlib.sha256(str(it["id"]).encode("utf-8")).hexdigest()', APP)
        self.assertNotIn('abs(hash(it["id"]))', APP)

    def test_vector_off_really_disables_operations(self):
        self.assertIn('if not items or self.backend == "off":', APP)
        self.assertIn('if self.backend == "off":\n            return []', APP)

    def test_hybrid_vector_results_are_limited_to_current_index_paths(self):
        self.assertIn("allowed_paths = {", APP)
        self.assertIn("if not hit_path or hit_path not in allowed_paths:", APP)

    def test_selected_file_is_owner_checked(self):
        fn = function_node("_load_selected_uploaded_file")
        self.assertIsNotNone(fn)
        src = ast.get_source_segment(APP, fn)
        self.assertIn("uploaded_by=?", src)
        self.assertIn("os.path.commonpath", src)

    def test_selected_file_uses_one_resolved_path(self):
        fn = function_node("process_selected_uploaded_file")
        self.assertIsNotNone(fn)
        src = ast.get_source_segment(APP, fn)
        self.assertIn("_load_selected_uploaded_file(file_id)", src)
        self.assertIn("extract_text_from_file(item[\"filepath\"])", src)
        self.assertIn("resolve_llm(", src)
        self.assertNotIn("_collect_sticky_file_rows()", src)


    def test_legacy_document_translation_routes_cloud_models_correctly(self):
        fn = function_node("translate_text_quality")
        self.assertIsNotNone(fn)
        src = ast.get_source_segment(APP, fn)
        self.assertIn("resolve_llm(", src)
        self.assertIn("if is_api:", src)

    def test_legacy_document_processing_respects_selected_cloud_provider(self):
        fn = function_node("process_document")
        self.assertIsNotNone(fn)
        src = ast.get_source_segment(APP, fn)
        self.assertIn("is_cloud_model", src)
        self.assertIn("resolve_llm(", src)
        self.assertIn("if is_cloud_model:", src)
        self.assertIn("trans_model = model", src)

    def test_web_search_does_not_receive_document_contents(self):
        fn = function_node("_selected_file_web_context")
        self.assertIsNotNone(fn)
        src = ast.get_source_segment(APP, fn)
        self.assertIn("search_web(query", src)
        self.assertNotIn("extract_text_from_file", src)

    def test_exclusive_file_selector_exists(self):
        self.assertIn('name="selected_file_id"', HTML)
        self.assertIn('id="selected_file_id"', HTML)
        self.assertIn("targetFileOnlyHint", HTML)

    def test_key_points_action_exists(self):
        self.assertIn('value="key_points"', HTML)
        self.assertIn('elif action == "key_points":', APP)
        self.assertIn("key_points:1", HTML)

    def test_arabic_and_english_copy_exists(self):
        self.assertIn('targetFileLabel: "الملف المستهدف حصرياً', HTML)
        self.assertIn('targetFileLabel: "Exclusive target file', HTML)
        self.assertIn('keyPoints: "أهم النقاط"', HTML)
        self.assertIn('keyPoints: "Key points"', HTML)

    def test_cloud_and_local_fallback_flags_are_preserved(self):
        self.assertRegex(ENV_EXAMPLE, r"(?m)^FBRAH_ALLOW_CLOUD_FALLBACK=1$")
        self.assertRegex(ENV_EXAMPLE, r"(?m)^FBRAH_ALLOW_LOCAL_MODEL_FALLBACK=1$")
        self.assertIn("Gemini↔GROQ ومحلي↔محلي فقط", APP)

    def test_internet_only_does_not_process_local_file_actions(self):
        self.assertIn('if use_web and not use_web_and_local:', APP)
        self.assertIn("وضع «الإنترنت فقط» لا يعالج الملفات المحلية", APP)

    def test_file_reading_and_generation_features_remain(self):
        for name in (
            "extract_text_from_file", "generate_pdf", "generate_word",
            "generate_excel", "generate_pptx", "search_web",
            "handle_link_content_request",
        ):
            self.assertIn(f"def {name}(", APP)

    def test_brand_palette_is_preserved(self):
        for color in ("#001F3F", "#d4af37", "#760d0d"):
            self.assertIn(color.lower(), HTML.lower())


    def test_database_maintenance_utilities_are_present_and_parse(self):
        for filename in ("backup_db.py", "restore_db.py", "reset_admin.py"):
            source = (ROOT / filename).read_text(encoding="utf-8-sig")
            ast.parse(source, filename=filename)

    def test_admin_reset_is_interactive_and_has_no_password_fallback(self):
        source = (ROOT / "reset_admin.py").read_text(encoding="utf-8-sig")
        self.assertIn("getpass.getpass", source)
        self.assertIn("len(password) < 12", source)
        self.assertNotIn("FBRAH_RESET_ADMIN_PASSWORD", source)
        self.assertIsNone(re.search(r"(?im)^\s*(?:password|new_password)\s*=\s*['\"]", source))

    def test_restore_utility_checks_project_paths_and_database_integrity(self):
        source = (ROOT / "restore_db.py").read_text(encoding="utf-8")
        self.assertIn("is_inside_project", source)
        self.assertIn("PRAGMA integrity_check", source)
        self.assertIn("os.replace(temp_database, target)", source)

    def test_no_embedded_env_or_database_in_release_tree(self):
        import subprocess

        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        )
        tracked = [
            item.decode("utf-8", errors="replace")
            for item in result.stdout.split(b"\\0")
            if item
        ]

        forbidden_suffixes = (".db", ".sqlite", ".sqlite3", ".pem", ".key")
        for relative_path in tracked:
            normalized = relative_path.replace("\\\\", "/")
            filename = Path(normalized).name

            self.assertNotEqual(
                filename, ".env",
                f"Secret environment file is tracked: {relative_path}",
            )
            self.assertFalse(
                filename.lower().endswith(forbidden_suffixes),
                f"Sensitive file is tracked: {relative_path}",
            )
            self.assertNotRegex(
                normalized,
                r"(^|/)(data|backups|\\.git|\\.venv|venv)/",
                f"Private directory is tracked: {relative_path}",
            )



if __name__ == "__main__":
    unittest.main(verbosity=2)
