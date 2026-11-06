# 00 — Overview

## Product

Accounts-team app for **AcmeCorp**: chase overdue invoices by email (collections agent), answer routine customer mail with an LLM, and suggest bank-statement → invoice matches for human approval.

## Must-have

| Area | Scope |
|---|---|
| Part A | Org, customers, invoices (with **computed overdue** + unpaid amount); edit customer email; **Reset demo data** |
| Part B | SMTP reminders; IMAP poll + **Check inbox now**; per-customer conversations; LLM classify/draft; draft validator; Needs attention edit-and-send |
| Part C | CSV upload; local weighted matcher (no LLM for core); approve / reject / choose invoice; TDS close vs leave open; approval updates balances and stops chasing |
| Cross-cutting | MongoDB; FastAPI + Next.js; Docker Compose one-command run; secrets in env; layered backend |

## Bonus (stretch — last)

1. Link payment-claim emails to statement rows  
2. One payment → several invoices (split)  
3. Out-of-office / bounce detection  

## Out of scope

- Auth / multi-tenant SaaS login  
- RAG / vector DB  
- Sending statement rows to an LLM for matching  
- Revenue recognition UI (Section 9 is interview reading only)

## Final folder layout

```text
repo/
├── docs/ASSIGNMENT.md
├── data/                    # given files, untouched
├── specs/                   # this folder
├── backend/                 # FastAPI
│   ├── app/
│   │   ├── api/             # routes
│   │   ├── services/        # business logic
│   │   ├── repositories/    # Mongo access
│   │   ├── adapters/        # email, LLM
│   │   ├── models/
│   │   ├── core/            # settings, db, security
│   │   └── main.py
│   ├── Dockerfile
│   ├── .dockerignore
│   └── requirements.txt
├── frontend/                # Next.js (App Router)
│   ├── src/app/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── package.json
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── explanation.pdf          # submit later
```

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14+, React, TypeScript; talks only to backend API |
| Backend | FastAPI, Python 3.12, Uvicorn |
| DB | MongoDB 7 |
| Email | SMTP send + IMAP poll (env-configured) |
| LLM | OpenAI-compatible HTTP client (base URL + key + model) — Gemini / Groq / OpenRouter / OpenAI via env |
| Matching | `rapidfuzz` (token set ratio + Jaro-Winkler), regex, deterministic scoring |
| Run | Docker Compose: `mongo`, `backend`, `frontend` |

## Assumptions

1. Single org (AcmeCorp); no multi-org tenancy. Customer isolation is by `customer_id` / contact email match.  
2. Demo “today” for overdue uses server UTC date unless `DEMO_AS_OF_DATE` is set (for reproducible demos).  
3. Frontend pages: Organization, Customers, Invoices, Collections, Reconciliation (+ Reset).  
4. Money stored as **integer minor units** (×100), never float.  
5. ~5 focused hours: ship Part A + reconciliation core + collections MVP before bonuses.  
