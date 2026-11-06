# 06 — Docker and run

Implemented in Phase 2 (this repo). Spec = contract the scaffolding must meet.

## Evaluator path

```bash
cp .env.example .env
# fill SMTP/IMAP/LLM + optional overrides
docker compose up --build
```

- Frontend: `http://localhost:3000`  
- Backend: `http://localhost:8000` (`GET /health`)  
- Mongo: internal `mongo:27017` (not required to publish for MVP; optional `27017:27017` for debugging)

## Services

| Service | Image / build | Notes |
|---|---|---|
| `mongo` | `mongo:7` | Named volume `mongo_data`; healthcheck `mongosh --eval "db.adminCommand('ping')"` |
| `backend` | `./backend` Python 3.12-slim | Uvicorn; non-root; waits for mongo healthy; mounts or copies `../data` for seed |
| `frontend` | `./frontend` Node 20 alpine multi-stage | `next start` on 3000; waits for backend |

## Env (`.env.example` placeholders)

| Variable | Purpose |
|---|---|
| `MONGO_URI` | e.g. `mongodb://mongo:27017` |
| `MONGO_DB` | e.g. `sonic_acme` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Outbound mail |
| `IMAP_HOST`, `IMAP_PORT`, `IMAP_USER`, `IMAP_PASSWORD` | Inbound mail |
| `ORG_MAILBOX_ADDRESS` | From-address / org inbox |
| `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | OpenAI-compatible |
| `IMAP_POLL_INTERVAL_SECONDS` | Default `60` |
| `CORS_ORIGINS` | e.g. `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | e.g. `http://localhost:8000` |
| `LLM_MIN_CONFIDENCE` | Default `0.70` |
| `DEMO_AS_OF_DATE` | Optional `YYYY-MM-DD` for overdue |

## LLM adapter

One interface: `complete_json(system, user) -> dict` over OpenAI-compatible `/v1/chat/completions`. Changing provider = env only (Gemini/Groq/OpenRouter/OpenAI).

## Seed

- On backend startup: if DB empty → load `data/organization.json`, `customers.json`, `invoices.json`.  
- Idempotent via `meta` collection.  
- Same path used by `POST /api/demo/reset`.

## Phase 2 MVP proof

- FastAPI `/health`  
- Next.js page fetches `/health` and shows status  
- Full Part A–C features come after specs implementation (not required for scaffold boot)

## Assumptions

1. Data files copied into backend image at ` /app/data`.  
2. Gmail requires App Password + IMAP enabled (README troubleshooting).  
3. Compose project name default; ports 3000/8000 must be free.  
