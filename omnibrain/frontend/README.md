# OmniBrain — Streamlit Frontend

A modular, polished Streamlit frontend for OmniBrain, fully wired to
the FastAPI backend in `../backend`.

## Run it

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

It talks to `http://localhost:8000` by default (with the `/api/v1`
prefix appended automatically). Change the backend URL any time from
**Settings → API Configuration**, or by editing `DEFAULT_BACKEND_URL`
in `config.py`. Start the backend first (see `../backend/README.md`)
or every page will show a friendly "can't reach the backend" message
instead of failing silently.

## Every page talks to a real endpoint

| Page | Backend calls |
|---|---|
| Dashboard | (uses session data from the other pages) |
| Analyze Website | `POST /analyze` — creates a project, returns it into session state |
| Documents | `POST /upload`, `GET /documents`, `DELETE /documents/{id}` |
| OmniBrain Chat | `POST /chat`, scoped to the current project via `project_id` |
| Simulation | `POST/GET /projects/{id}/simulation/*` |
| Analytics | `GET /analytics` |
| Settings | `GET /health` |

A project created on the Analyze Website page carries a real
`project_id` from the backend into `st.session_state["current_project"]`.
Chat and Documents both pick that up automatically — ask a question
after analyzing a site and it retrieves from that site's indexed
content specifically, not everything in the vector store.

## Demo-mode fallback

If a request 404s (e.g. you're pointed at an older backend, or one
that doesn't implement `/analyze` yet), `services/api_client.py`
degrades to clearly-labeled demo data instead of crashing the page —
useful for previewing the UI without a backend running at all. Once
a real backend responds, real data takes over automatically; no
frontend code needs to change either way.

## Structure

```
frontend/
├── app.py                    # entry point — wiring only
├── config.py                 # page config, session state defaults, nav items, API_PREFIX
├── pages/                    # one module per screen, each exports render()
├── components/                # sidebar, cards, progress steps, chat bubbles, arch diagram
├── services/api_client.py     # the ONLY place that talks HTTP to the backend
├── assets/styles.css          # the light/purple/blue AI SaaS theme
└── .streamlit/config.toml     # disables Streamlit's auto page-nav (we use a custom sidebar)
```
