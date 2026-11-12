# FBRAH AI — Feature Delivery Matrix / مصفوفة تنفيذ الخصائص

| المجال | ما تم في هذه الحزمة / Delivered | ما لم يُعتمد بعد / Pending |
|---|---|---|
| الأمن | CSRF hooks, security headers, reset-token delivery rollback and atomic one-time claim, account XSS escaping, admin-only self-heal | Global revocation of all old sessions after password change; deeper ownership/path-containment review for every recording file operation; production penetration testing |
| النماذج | Centralized cloud routing through `resolve_llm`; bounded `FBRAH_CLOUD_TIMEOUT` (default 30s, 10–60s); Gemini model-ID/provider fallback is opt-in; local/cloud fallback defaults remain `0`; no cross-mode fallback | Provider live connectivity, quota and latency tests in the user's environment |
| الرفع وOCR | 500 MB global request cap; 200-page PDF OCR cap; strict handwriting image size/format/pixel checks | Route-specific caps for every upload class; large-PDF memory/time profiling |
| Voice / FBRAH wake | Navy active state `#001F3F` with gold border/glow after wake phrase | Browser/device matrix, wake-word false-positive/false-negative measurements, accessibility testing |
| Pen board | Adds `/api/pen/export`, reuses the protected handwriting OCR path, creates DOCX | Structured table reconstruction, spreadsheet export from detected tables, diagram semantic interpretation, OCR confidence scoring |
| Documents | Existing DOCX/XLSX/PPTX/PDF generation functions retained | End-to-end regression tests for Arabic RTL, tables, charts, pagination, fonts and large documents |
| News | RSS aggregation across legal, economic, political, global and market queries; publisher label and link per item; safe DOM rendering; 270/240/210s ticker cycle speeds; V1 preference migration to V2 | Direct publisher feeds per region, deduplication quality, article freshness labels and source reliability ranking |
| FX / gold | No fabricated static rates | Live FX/gold provider, units, timestamp, licensing and source attribution |
| RAG | Existing BM25 + vector + re-ranking + Arabic/English expansion preserved | Benchmark-driven RRF/ranking changes, evaluation corpus, citation scoring and latency profiling |
| Answer page | Existing answer page and export actions preserved; ticker rendering hardened | Full visual redesign, evidence/citation cards, answer outline, confidence/uncertainty panels |
| Dialogue & scenarios | Existing multi-turn session behavior preserved | Dedicated scenario builder with assumptions, base/upside/downside/stress, probability rationale and sensitivity analysis |
| Language | Main bilingual UI preserved; docs supplied in Arabic and English | Full English localization of account, admin, password-reset and all status/error messages |

**Release rule:** A pending item must not be described as complete. It should be implemented in a separate tested change set without deleting existing functionality.
