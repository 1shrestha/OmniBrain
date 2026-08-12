# OmniBrain — FastAPI Backend

## Run it

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # then add your GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Docs at `http://localhost:8000/docs`. Everything is mounted under `/api/v1`
(e.g. `http://localhost:8000/api/v1/health`) — `app/main.py` does
`app.include_router(router, prefix="/api/v1")`.

## What was already here

Your upload's `app/` folder was a real, working PDF Q&A backend:
upload → extract (PyPDF2, OCR fallback) → chunk → embed
(sentence-transformers) → store (ChromaDB) → retrieve → generate
(Gemini via a LangGraph workflow). That pipeline is untouched.

## Bugs fixed

1. **`app.models` import path.** The schemas lived in `app/MODELS/`
   (uppercase). `routes.py` imported `from app.models.schemas import
   ...` — that only resolves on a case-insensitive filesystem
   (Windows). On Linux it would raise `ModuleNotFoundError` the
   moment the server started. Fixed by making the real package
   `app/models/` (lowercase).

2. **Fake singletons in `core/dependencies.py`.** Every getter
   (`get_document_service()`, etc.) just did `return DocumentService()`
   — a brand-new instance, with a brand-new empty in-memory registry,
   on *every request*. In practice this meant: upload a PDF, then call
   `GET /documents` a moment later, and it would come back empty,
   because the `AnalyticsService` holding the registry had already
   been thrown away and recreated. `/health`'s uptime was always ~0
   for the same reason. Fixed with `@lru_cache()` on each getter so
   they're real singletons for the life of the process.

3. **`main.py` CORS origins** didn't include Streamlit's default port
   (8501) — added it.

## What was added

The frontend's spec described website analysis and simulation, which
weren't implemented yet. Added, reusing the existing pipeline
wherever the shape matched:

- **`services/scraper_service.py`** — `requests` + `BeautifulSoup`
  breadth-first crawler, same-domain only, capped at
  `SCRAPER_MAX_PAGES` (default 15). Not a headless browser, so
  JS-only single-page apps will yield thin content — swap
  `fetch_page()` for Playwright later if that turns out to matter;
  nothing else needs to change.
- **`services/website_service.py`** — orchestrates
  crawl → clean → chunk → embed → store, **reusing
  `PDFService.clean_text`/`chunk_document`** rather than duplicating
  chunking logic. A scraped page and a PDF page are both just "text
  with a page number" by the time they reach that step.
- **`services/project_service.py`** — in-memory project registry
  (same pattern as the existing `AnalyticsService` document
  registry). Ties together a project's website, its documents, its
  chat history, and its simulation session.
- **`services/simulation_service.py`** — generates the dynamic
  UI-component list the Simulation page renders. Deterministic and
  template-based rather than another LLM call, so it works even
  without `GEMINI_API_KEY` set — swap `_build_components()` for a
  Gemini call later if you want it content-aware; the shape it
  returns wouldn't need to change.
- **New endpoints**: `POST /analyze`, `GET /projects`,
  `GET /projects/{id}/status`, `GET /projects/{id}/chat-history`,
  `POST /projects/{id}/simulation/start`,
  `GET /projects/{id}/simulation/state`,
  `POST /projects/{id}/simulation/stop`, `GET /analytics`.
- **`/chat` and `/upload`** now accept an optional `project_id` so a
  question or a document can be scoped to a specific analyzed
  website — chunks from both PDFs and scraped pages live in the same
  ChromaDB collection, tagged with `source_type` (`document` |
  `website`) and `project_id`.

## What's still a reasonable next step, not done here

- The in-memory registries (`AnalyticsService`, `ProjectService`)
  reset on server restart — fine for a demo, not for production.
  Swap them for a real database (Postgres/SQLite) behind the same
  method signatures and nothing above them changes.
- `ScraperService` doesn't check `robots.txt` or rate-limit itself
  beyond `SCRAPER_TIMEOUT_SECONDS` per request — worth adding before
  pointing it at sites you don't own.
- No auth is enforced by default (`AUTH_ENABLED=false`). Turn it on
  and set `API_KEY` in `.env` for anything beyond local development.

## Environment variables

See `.env.example`. The only one you actually need to set for `/chat`
to generate real answers is `GEMINI_API_KEY` — everything else has a
sane default.
