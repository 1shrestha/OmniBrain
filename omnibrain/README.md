# OmniBrain

An AI-powered website intelligence and document Q&A platform.
Point it at a URL or a PDF, and ask it questions.

```
omnibrain/
├── backend/     FastAPI — scraping, RAG, chat, projects, simulation
├── frontend/    Streamlit — the UI in this repo
├── deploy/      nginx config + Let's Encrypt bootstrap for omnibrain.in
└── docker-compose.yml
```

## Run both locally (no Docker)

Two terminals:

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
cp .env.example .env        # add your GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Open the Streamlit URL it prints (usually `http://localhost:8501`).
The sidebar shows **Backend Connected** / **AI Engine Active** once
both are up.

## Deploying to omnibrain.in

```bash
docker compose up -d --build
```

...will run it locally in containers, but getting it live at
`https://omnibrain.in` needs DNS pointed at a real server and a TLS
certificate first — **`deploy/DEPLOY.md` walks through the whole
thing step by step**, from pointing the domain's DNS at a server
through to Let's Encrypt auto-renewal. Nothing about the app itself
needs to change between "running locally" and "running at
omnibrain.in" — `docker-compose.yml` and `deploy/nginx/omnibrain.conf`
are already configured for that domain.

## What each README covers

- `backend/README.md` — the bugs found and fixed in the backend you
  uploaded (a case-sensitive import path, and dependency "singletons"
  that weren't), plus what was added for website analysis and
  simulation.
- `frontend/README.md` — which page calls which endpoint, and how
  the demo-mode fallback works if the backend isn't reachable.
- `deploy/DEPLOY.md` — DNS, server setup, and getting HTTPS working
  on omnibrain.in.

## The one thing worth knowing before you deploy

Both in-memory registries (`AnalyticsService` for documents,
`ProjectService` for projects/chat history/simulation sessions) live
in process memory and reset on restart. Vector embeddings persist
(ChromaDB writes to disk under `backend/vector_store/`), but the
metadata *about* them doesn't yet. Fine for local development and
demos; swap those two services for a real database before this goes
anywhere permanent — every route talks to them through a handful of
methods, so nothing above that layer needs to change.
