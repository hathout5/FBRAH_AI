# FBRAH AI — Ticker Direction, Reading Speed & Feed Coverage Update

Date: 2026-11-17

## Changes

- Arabic ticker now moves visually from left to right.
- English ticker now moves visually from right to left.
- Reduced all three ticker speeds by increasing their loop durations:
  - Slow: 720 seconds
  - Normal: 540 seconds
  - Fast: 390 seconds
- When a feed returns only a small number of items, the ticker repeats the actual returned items (with their existing source labels and original links) enough to fill the visible track. This prevents a large blank stretch without inventing news or descriptions.
- Expanded Arabic RSS discovery with additional Arabic-language publishers: Al Araby Al Jadeed, Asharq Al-Awsat, Anadolu Arabic, Al Bayan, and Al Ain.
- Increased the bounded per-feed item scan from 15 to 25 entries.
- Preserved the existing per-language last-good cache, direct-source links, source labels, pause/resume behavior, and refresh logic.

## Validation

- `python -m py_compile app.py`: passed.
- `node --check` on all 6 inline scripts in `templates/index.html`: passed.
- `python -m unittest test_ticker_continuity.py test_index_integrity.py test_priority_smoke.py`: 32 tests passed.
- Live RSS connectivity and visual browser playback were not verified in this environment. The expanded feeds depend on the user's server network access and the publishers' continued RSS availability.

## Apply safely

This is a source update package, not a full runtime backup. Extract into the existing FBRAH project and overwrite the included source/test/note files. Preserve the local `.env`, database, `data` folder, legal documents, indexes, and `.git` directory.
