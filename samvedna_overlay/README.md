# SAMVEDNA overlay (Tasks 2–5)

Drop-in copies of the TinyFish routes and console surfaces. Apply onto the
live SAMVEDNA tree:

`D:\Samvedna SIH with Truevoice\samvedna\samvedna`

Copy each relative path over the matching file. New files:

- `src/samvedna/api/tinyfish_routes.py`
- `tests/test_tinyfish_routes.py`
- `web/components/WelfareDirectory.tsx`
- `web/app/evidence/page.tsx`
- `web/app/trust/page.tsx`

Set `SAMVEDNA_SERVICE_TOKEN` and optionally `SAMVEDNA_TINYFISH_ROOT` in the
SAMVEDNA `.env`. Routes never make outbound HTTP; the sidecar POSTs in.

`uv run pytest tests/test_tinyfish_routes.py -v` (or the project venv) — 14 tests.
