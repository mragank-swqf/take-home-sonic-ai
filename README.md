# Sonic AI — Software Engineering Intern take-home

AcmeCorp accounts demo: overdue collections by email + bank reconciliation suggestions.

## Run with Docker

```bash
cp .env.example .env
```

Fill in SMTP/IMAP credentials (Gmail App Password recommended) and an OpenAI-compatible LLM key (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`).

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://127.0.0.1:3000 |
| Backend health | http://127.0.0.1:8000/health |

Ports bind to **127.0.0.1 only**. Mongo is **not** published to the host.

On first backend start (empty DB), seed data loads from `data/`.  
`POST /api/demo/reset` reloads seed data and clears conversations, payments, statements, and reminder cooldowns.

## Known limitation: no authentication

There is **no login**. This matches the take-home demo scope so evaluators can run quickly. It is only acceptable because Compose publishes the UI/API on loopback (`127.0.0.1`). Do not expose these ports on a public network.

## Specs

Design docs live in `specs/` (`00`–`06`, `tasks.md`). Assignment brief: `docs/ASSIGNMENT.md`.

## Troubleshooting

### Gmail SMTP/IMAP

1. Use a dedicated test Google account.  
2. Enable 2-Step Verification → create an **App Password**.  
3. Put that app password in `SMTP_PASSWORD` and `IMAP_PASSWORD`.  
4. Enable IMAP in Gmail settings.

### Port conflicts

If `3000` or `8000` is in use, stop the other process or change the published ports in `docker-compose.yml` (keep the `127.0.0.1:` prefix). Align `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS`.

### Frontend shows API error

Open http://127.0.0.1:8000/health. `NEXT_PUBLIC_API_URL` must be reachable from the browser.

### Wipe database volume

```bash
docker compose down -v
docker compose up --build
```
