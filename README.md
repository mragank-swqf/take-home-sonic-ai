# Sonic AI — Software Engineering Intern take-home

Accounts app for fictional **AcmeCorp**: overdue collections by email (LLM-assisted) and bank-statement reconciliation with human approval.

Evaluators: follow **Setup** below with your own mailbox and LLM key. No other install steps are required beyond Docker.

---

## Setup (start here)

### Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- Two email accounts you control (recommended: Gmail)
  - **Org mailbox** — AcmeCorp accounts inbox (SMTP + IMAP)
  - **Customer mailbox** — you will paste this into a customer’s email in the UI and reply as that customer
- An OpenAI-compatible LLM API key (free tiers work: Groq, OpenRouter, etc.)

### Steps

1. Clone this repository and enter it.

2. Create env file:

```bash
cp .env.example .env
```

3. Edit `.env` and set at least:

| Variable | What to put |
|---|---|
| `SMTP_USER` / `SMTP_PASSWORD` | Org mailbox + **App Password** (not the normal Gmail password) |
| `IMAP_USER` / `IMAP_PASSWORD` | Same org mailbox + same App Password |
| `ORG_MAILBOX_ADDRESS` | Same org mailbox address (From: for outbound mail) |
| `LLM_API_KEY` | Your provider key |
| `LLM_BASE_URL` | Provider OpenAI-compatible base URL (see examples below) |
| `LLM_MODEL` | A model that provider supports |

Leave Mongo / CORS / `NEXT_PUBLIC_API_URL` as in `.env.example` unless you change ports.

**Gmail:** enable 2-Step Verification → create an [App Password](https://myaccount.google.com/apppasswords) → enable IMAP in Gmail settings. Put the App Password in both `SMTP_PASSWORD` and `IMAP_PASSWORD`.

**LLM examples:**

| Provider | `LLM_BASE_URL` | Example `LLM_MODEL` |
|---|---|---|
| Groq | `https://api.groq.com/openai/v1` | `llama-3.1-8b-instant` |
| OpenRouter | `https://openrouter.ai/api/v1` | (pick a free model from their docs) |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |

4. Start everything:

```bash
docker compose up --build
```

5. Open:

| What | URL |
|---|---|
| Frontend | http://127.0.0.1:3000 |
| Backend health | http://127.0.0.1:8000/health |

6. On the Home page, click **Reset demo data** once (optional but useful). Seed data loads automatically on first empty DB from `data/`.

7. Stop when done: `Ctrl+C`, or `docker compose down`. Wipe DB volume: `docker compose down -v`.

Ports bind to **127.0.0.1** only. Mongo is **not** published to the host. There is **no login** (local evaluation only).

---

## What you can test

### Part A — base app (no mail/LLM required)

- **Organization** — AcmeCorp contacts, bank details, policies  
- **Customers** — list; edit a customer’s `contact_email` to your customer test inbox  
- **Invoices** — amounts, unpaid balance, computed **overdue** (never stored)  
- **Reset demo data** — restores seed; clears conversations, payments, statements, reminder cooldowns  

### Part C — bank reconciliation (no mail/LLM required)

1. Go to **Reconciliation**.  
2. Upload `data/bank_statement_sample.csv` (or your own CSV in the same format).  
3. Review suggestions / scores / reasons; use candidate buttons or hints to choose an invoice.  
4. **Approve** / **Reject**; for underpayments use **Close (TDS)** or **Leave open**.  
5. Confirm the invoice balance/status updates. Paid invoices are no longer chased by reminders.

### Part B — collections (needs SMTP; IMAP for inbound)

1. Set a customer email to your customer test inbox (**Customers**).  
2. **Collections** → **Send overdue reminders** — check Sent mail on the org account and the customer inbox.  
3. Reply from the customer account (balance question, payment claim, or dispute).  
4. **Check inbox now** (or wait for the IMAP poller) — auto-reply or **Needs attention**.  
5. On Needs attention: edit draft → **Send** (re-validated against DB figures).  

**Note:** Reminder **SMTP send** is implemented. If IMAP cannot reach your provider from the machine running Docker, inbound fetch will fail and replies will not be ingested automatically; the reply pipeline code is still present for environments where IMAP works.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), React, TypeScript |
| Backend | FastAPI, Python 3.12, Uvicorn |
| Database | MongoDB 7 (`mongo` service, named volume) |
| Matching | `rapidfuzz` (token-set ratio + Jaro-Winkler), deterministic weighted scoring |
| Email | SMTP (send) + IMAP (fetch) via env |
| LLM | OpenAI-compatible HTTP adapter (`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`) |
| Run | Docker Compose (`mongo`, `backend`, `frontend`) |

Architecture: frontend → API routes → services → repositories (Mongo) and adapters (SMTP / IMAP / LLM). The frontend never touches the DB, mail, LLM, or secrets.

---

## Project layout

```text
data/           # given seed files (do not modify)
docs/           # ASSIGNMENT.md, explanation.md
specs/          # product specs used to drive the build
backend/        # FastAPI app
frontend/       # Next.js UI
docker-compose.yml
.env.example
explanation.pdf # 2-page technical write-up
```

---

## Useful API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| POST | `/api/demo/reset` | Reseed + clear demo state |
| GET | `/api/organization` | Org profile |
| GET/PATCH | `/api/customers`, `/api/customers/{id}` | List / edit email |
| GET | `/api/invoices?overdue=true` | Invoices (+ computed overdue) |
| POST | `/api/reconciliation/uploads` | Upload statement CSV |
| GET | `/api/reconciliation/uploads/{id}/suggestions` | Suggestions |
| POST | `/api/collections/reminders/send` | Send overdue reminders |
| POST | `/api/collections/inbox/check` | Fetch IMAP once |

Full API shape: `specs/02-api.md`.

---

## Optional env knobs

| Variable | Default | Purpose |
|---|---|---|
| `REMINDER_COOLDOWN_MINUTES` | `5` | Per-customer reminder cooldown |
| `IMAP_POLL_INTERVAL_SECONDS` | `60` | Background IMAP poll |
| `LLM_MIN_CONFIDENCE` | `0.70` | Auto-send confidence floor |
| `DEMO_AS_OF_DATE` | empty | Freeze “today” for overdue (`YYYY-MM-DD`); empty = UTC today |
| `CORS_ORIGINS` | `http://127.0.0.1:3000` | Browser origin allowlist |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | API URL used by the browser |

---

## Status and limitations

| Area | Status |
|---|---|
| Part A (org, customers, invoices, reset) | Done |
| Reconciliation matcher + approve/reject/choose/TDS | Done |
| Reminder send, LLM classify/validate/route, Needs attention | Done |
| IMAP inbound fetch / auto-ingest replies | Partial — fails in my environment; not fixed |
| Rate limiting | Not done |
| Bonus: multi-invoice approve split | Not done (sum mentioned in reason only) |
| Bonus: payment-email ↔ bank row link | Not done |
| Bonus: OOO / bounce detection | Not done |
| Authentication | Not done (known limitation for local eval) |

More detail: `docs/explanation.md`, `explanation.pdf`. Specs: `specs/`. Assignment brief: `docs/ASSIGNMENT.md`.

Automated tests included: `backend/tests/test_matcher.py` (3 matcher cases). From repo with backend deps: `cd backend && PYTHONPATH=. pytest -q`.

---

## Troubleshooting

### Gmail SMTP/IMAP

1. Dedicated test Google account.  
2. 2-Step Verification → **App Password** (16 characters).  
3. Same App Password in `SMTP_PASSWORD` and `IMAP_PASSWORD`.  
4. IMAP enabled in Gmail settings.  
5. Restart after editing `.env`: `docker compose up --build`.

### Port conflicts

Free `3000` / `8000`, or change published ports in `docker-compose.yml` (keep the `127.0.0.1:` prefix) and align `NEXT_PUBLIC_API_URL` + `CORS_ORIGINS`.

### Frontend cannot reach API

Confirm http://127.0.0.1:8000/health returns `{"status":"ok"}`.

### IMAP “fetch failed”

Outbound SMTP can work while IMAP port 993 is blocked on some networks. Try another network/hotspot, or run where IMAP to your provider is allowed. Matching/Part A/C do not need IMAP.

### Fresh database

```bash
docker compose down -v
docker compose up --build
```
