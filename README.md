# Sonic AI — Software Engineering Intern take-home

AcmeCorp accounts demo: collections agent + bank reconciliation.

## Run with Docker

```bash
cp .env.example .env
```

Edit `.env` and set at least:

- Your org Gmail (or other) address + **App Password** for `SMTP_*` / `IMAP_*` / `ORG_MAILBOX_ADDRESS`
- An OpenAI-compatible `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` (Groq / OpenRouter / Gemini bridge / OpenAI all work by changing these)

Then:

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend health | http://localhost:8000/health |

On first backend start (empty DB), seed data loads from `data/`.  
`POST http://localhost:8000/api/demo/reset` reloads demo data and clears conversations/payments.

Specs for the full app are in `specs/`. Assignment brief: `docs/ASSIGNMENT.md`.

## Troubleshooting

### Gmail SMTP/IMAP

1. Use a dedicated test Google account.  
2. Enable 2-Step Verification, then create an **App Password** (Google Account → Security).  
3. Put the app password in `SMTP_PASSWORD` and `IMAP_PASSWORD` (not your normal login password).  
4. Ensure IMAP is enabled in Gmail settings.  
5. If Google blocks sign-in, try again after unlocking / allowing the app password.

### Port conflicts

If `3000` or `8000` is already in use, stop the other process or change the left-hand ports in `docker-compose.yml` (e.g. `"3001:3000"`). Keep `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS` aligned with whatever you publish.

### Frontend shows API error

Confirm backend is healthy: open http://localhost:8000/health.  
`NEXT_PUBLIC_API_URL` must be reachable **from your browser** (usually `http://localhost:8000`).

### Mongo / rebuild

```bash
docker compose down
docker compose up --build
```

To wipe the database volume:

```bash
docker compose down -v
```
