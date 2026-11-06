# 06 — Docker and run

## Evaluator path

```bash
cp .env.example .env
# fill SMTP/IMAP/LLM
docker compose up --build
```

- Frontend: `http://127.0.0.1:3000`  
- Backend: `http://127.0.0.1:8000/health`  
- Mongo: **not published** (internal `mongo:27017` only)

## Ports

Bind host ports to loopback only:

```yaml
ports:
  - "127.0.0.1:8000:8000"
  - "127.0.0.1:3000:3000"
```

## Env additions

| Variable | Default | Purpose |
|---|---|---|
| `REMINDER_COOLDOWN_MINUTES` | `5` | Per-customer reminder cooldown |
| `DEMO_AS_OF_DATE` | empty | Empty → UTC today (`data-explanation.md` has no fixed reference today) |
| `LLM_MIN_CONFIDENCE` | `0.70` | Auto-send floor |

Plus `MONGO_*`, `SMTP_*`, `IMAP_*`, `ORG_MAILBOX_ADDRESS`, `LLM_*`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`, `IMAP_POLL_INTERVAL_SECONDS`.

## Seed / reset

Empty DB → seed from `data/`. Reset reloads seed and clears cooldowns, mail state, payments, statements.

## Known limitation

No authentication. Safe only because ports bind to `127.0.0.1`. Documented in README.
