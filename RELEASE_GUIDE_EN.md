# FBRAH AI — Release and Hardening Bundle

## Scope
This release candidate is based on the uploaded Flask project. It preserves the existing application, bilingual main UI, RAG components, local/cloud model routing, and document-generation stack.

## Implemented in this bundle
- Local and cloud model fallback flags default to `0` in every located code path.
- Cloud model calls use `FBRAH_CLOUD_TIMEOUT=30` by default (bounded to 10–60 seconds); Gemini model retries and configured Groq model/provider switching require `FBRAH_ALLOW_CLOUD_FALLBACK=1`; local retries use installed Ollama models only when `FBRAH_ALLOW_LOCAL_MODEL_FALLBACK=1`. The release template enables both within-mode fallbacks. Cloud/local mode crossing is forbidden in both directions.
- Cloud routing is centralized through `resolve_llm`; `ask_ollama` delegates explicit cloud model IDs rather than maintaining a second cloud-routing implementation.
- News ticker cycle durations are 270/240/210 seconds; V1 browser preferences migrate to V2 without losing paused/hidden state.
- General upload cap defaults to 500 MB and is bounded to 1–500 MB; OCR PDF pages are bounded to 1–200.
- Handwriting OCR validates Base64, image format, file size and pixel dimensions.
- Gemini OCR API keys are sent in the `x-goog-api-key` header, not in the URL.
- Adds `/api/pen/export` to recognize a pen-board PNG and generate a DOCX.
- Escapes account messages and attributes, validates usernames, and enforces 12–256 character passwords on the account password-change path.
- Recording export mutations are POST-only; the storage-location endpoint no longer discloses absolute server paths.
- System diagnostics GET is read-only; self-healing is POST-only and admin-only.
- Registers `security_hardening.py` at startup: CSRF, security headers, login throttling, and password-reset endpoints.
- Password-reset tokens are revoked when email delivery fails and are consumed with a conditional update to prevent concurrent reuse.
- The voice talk button uses navy `#001F3F` with a gold border/glow after the FBRAH wake phrase.
- Replaces hard-coded sample headlines with RSS aggregation and publisher attribution; frontend renders untrusted headline text through DOM text APIs.

## RAG architecture
The existing application already includes BM25, vector retrieval, local embeddings/fallback embedding, Cross-Encoder re-ranking with lexical fallback, Arabic/English query expansion, and document chunking/metadata. This bundle does not replace those components or trigger model downloads. `FBRAH_ALLOW_ONLINE_EMBED=0` remains the default. See `RAG_QUALITY_ROADMAP_AR_EN.md` for benchmark-driven next steps.

## News and market data
The ticker now retrieves RSS headlines for legal, economic, political, international, and market topics and shows publisher name plus article link. Google News RSS is an aggregator; follow the linked publisher to verify the report.

The Gemini model identifiers in `.env.example` are the identifiers supplied for this project; validate availability for the account/provider at runtime. Live FX and gold figures are intentionally not fabricated or hard-coded. A verified market-data provider, its terms/credentials, currency units, timestamps, and source attribution must be selected before adding numeric prices.

## Source reconciliation before installation

Read `RECONCILIATION_REQUIRED_AR.md`: the local PowerShell audit reported different sizes for `app.py` and `templates/index.html` than this release candidate. The installer displays branch/status and hashes, and requires typing `APPLY` before replacing files. Review source differences first.

## Safe installation
1. Back up source files. Do not include `.env`, databases, Qdrant data, or backups in the release.
2. Extract this bundle to a temporary folder.
3. Run `INSTALL_RELEASE.ps1` from PowerShell, passing the project path:
   `powershell -ExecutionPolicy Bypass -File .\INSTALL_RELEASE.ps1 -ProjectRoot "C:\path\to\Fbrah Ai G"`
4. The installer backs up files it replaces and does not modify `.env`, databases, `data`, Qdrant, or backup folders.
5. Run the package checks:
   `python -m unittest -v test_release_integrity.py test_index_integrity.py`
   then `python test_priority_smoke.py`. These checks do not start Flask or access the user database.
6. Full Flask, SMTP, OCR, and AI-provider tests must be run in a disposable environment with separate credentials and a separate database; they were not live-tested while building this ZIP.
7. Test against a disposable database and separate SMTP/model credentials, then inspect Git diffs and status.

## Publishing cautions
Never commit `.env`, database/WAL/SHM files, `data/`, Qdrant, `backups/`, logs, or `.git`. Do not force-push or rewrite history. Review every changed file before staging/committing/pushing. The 500 MB cap must also be configured at the reverse proxy/web server. Passing static checks is not proof of live OCR, SMTP, database, or provider integration.

## Not yet completed
A full answer-page redesign, benchmark-validated RAG ranking changes, advanced table extraction from pen images, scenario/probability workbench, live FX/gold data, and full English localization of account/admin/password-reset pages remain separate tasks requiring functional tests.


See `OLLAMA_TROUBLESHOOTING_AR.md` for Ollama model discovery and refresh steps. When a Gemini key and internet access are available, Gemini is the default; when internet is unavailable, Qwen is selected if installed. Explicit manual model choices persist, and automatic cloud/local crossing is forbidden.

See `FEATURE_MATRIX_AR_EN.md` for a precise separation of delivered changes and pending work.
