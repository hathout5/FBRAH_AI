# FBRAH AI — RAG Quality & Performance Roadmap / خارطة تطوير RAG

## Current verified implementation / الموجود فعلياً
- BM25 lexical retrieval over chunks produced by `split_text_articles`.
- Chunk metadata includes title, path, article number and legal metadata where extractable.
- Vector retrieval is merged with BM25 in `hybrid_retrieve`.
- Embeddings try local `sentence-transformers`; optional Ollama embedding path and a hash fallback exist.
- Cross-Encoder reranking is used only when the model is available locally; otherwise lexical overlap reranking is used.
- Query expansion includes Arabic/English legal and general terms.
- BM25 score caching is bounded and invalidated on rebuild.

## Safe improvements to implement next / التحسينات التالية
1. **Measure before changing ranking:** build a gold set of 100–300 queries from actual anonymized legal and general tasks. Label relevant documents/passages. Track Recall@5, Recall@10, MRR, nDCG@10, answer citation coverage, and latency p50/p95.
2. **Hybrid score fusion:** test Reciprocal Rank Fusion (RRF) or calibrated rank fusion instead of adding raw BM25/vector scores with different scales. Keep the existing method as a feature-flagged baseline.
3. **Legal-aware chunking:** preserve article boundaries, law number, article number, issuing authority, jurisdiction, effective date, amendment/repeal state, and source filename. Never merge adjacent legal articles if doing so loses the article identity.
4. **Query understanding:** classify request intent (legal rule, case law, contract, legislation, economic indicator, news, general knowledge, document task). Expand only with domain-appropriate synonyms; preserve quoted terms, statute/article numbers, dates, names, and exact phrases.
5. **Metadata filters:** use jurisdiction, document type, date, source authority, and user-selected folders as hard filters when explicitly requested. Do not infer jurisdiction from Arabic language alone.
6. **Reranker efficiency:** retrieve a bounded candidate set (for example 30–60), deduplicate, truncate each passage, batch Cross-Encoder inference, and rerank only the shortlist. Keep lexical fallback available.
7. **Context assembly:** avoid near-duplicate passages; include source title/path and article metadata; allocate context by relevance and diversity; never let one long document consume the entire context.
8. **Answer grounding:** require source-backed statements for retrieved legal claims; distinguish binding law, court principles, commentary, and news. If evidence is absent or outdated, say so rather than filling gaps.
9. **Freshness:** local law sources need amendment/effective-date metadata. News and market data need retrieval timestamps and publisher/provider attribution. A cached headline is not a verified current legal rule.
10. **Speed:** fingerprint only relevant library roots; incremental re-index changed files; persist embeddings safely; avoid model initialization per request; use bounded concurrency and timeouts; measure CPU/RAM/VRAM before enabling large rerankers.
11. **Table and image understanding:** preprocess scans with deskew, denoise, adaptive threshold, layout segmentation and OCR confidence. For tables, reconstruct rows/columns and validate totals; do not trust OCR text as a structured table without confidence checks.
12. **Scenario and probability analysis:** expose assumptions, variables, ranges, scenario labels (base/upside/downside/stress), probability source, sensitivity drivers, and uncertainty. Do not present subjective probabilities as statistical facts.

## Proposed quality gates / بوابات الجودة
- No regression in Recall@10 or MRR on the frozen evaluation set.
- Citation coverage target >= 90% for legal answers that claim source-backed rules.
- p95 latency measured separately for local and cloud modes.
- A source freshness timestamp on every live news/market item.
- No automatic cross-mode fallback. Cloud can fall back only to cloud; local only to local, and both remain disabled by default.
- No background download of embedding/reranking models unless `FBRAH_ALLOW_ONLINE_EMBED=1` is explicitly configured.

## Important limitation
This document is a tested design plan, not a claim that all the listed enhancements have already been implemented. The current bundle preserves the existing RAG engine and makes no unbenchmarked change to its retrieval scoring.
