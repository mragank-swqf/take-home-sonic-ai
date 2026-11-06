# 00 — Overview

## Product

Accounts-team app for **AcmeCorp**: chase overdue invoices by email (collections agent), answer routine customer mail with an LLM, and suggest bank-statement → invoice matches for human approval.

## Must-have

| Area | Scope |
|---|---|
| Part A | Org, customers, invoices (with **computed overdue** + unpaid amount); edit customer email; **Reset demo data** |
| Part B | SMTP reminders (one email per customer listing all overdue); IMAP poll + **Check inbox now**; conversations; LLM classify/draft; draft validator; Needs attention edit-and-send |
| Part C | CSV upload; local weighted matcher (no LLM for core); approve / reject / choose invoice; TDS close vs leave open; approval updates balances and stops chasing |
| Cross-cutting | MongoDB; FastAPI + Next.js; Docker Compose one-command run; secrets in env; layered backend |

## Bonus (stretch — last)

1. Link payment-claim emails to statement rows  
2. One payment → several invoices (split)  
3. Out-of-office / bounce detection  

## Out of scope

- Auth / multi-tenant SaaS login (**known limitation** — localhost demo only; documented in README)  
- RAG / vector DB  
- Sending statement rows to an LLM for matching  
- Revenue recognition UI (Section 9 is interview reading only)

## Final folder layout

```text
repo/
├── docs/ASSIGNMENT.md
├── data/                    # given files, untouched
├── specs/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── adapters/
│   │   ├── models/
│   │   ├── core/
│   │   └── main.py
│   ├── Dockerfile
│   ├── .dockerignore
│   └── requirements.txt
├── frontend/
│   ├── src/app/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── package.json
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── explanation.pdf
```

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14+, React, TypeScript; talks only to backend API |
| Backend | FastAPI, Python 3.12, Uvicorn |
| DB | MongoDB 7 (not published to host) |
| Email | SMTP send + IMAP poll |
| LLM | OpenAI-compatible HTTP client; defensive JSON parse + one retry → Needs attention |
| Matching | `rapidfuzz` + regex, deterministic scoring |
| Run | Docker Compose; ports bound to `127.0.0.1` only |

## Assumptions / decisions

1. Money: integer **minor units** (×100).  
2. **As-of date:** `data/data-explanation.md` has no fixed reference “today” → default `DEMO_AS_OF_DATE` empty means **UTC today**. If a fixed demo date is later added to the data docs, set the env default to match.  
3. LLM confidence floor: `0.70`.  
4. Matcher close-score / uniqueness rules: see `04-reconciliation.md`.  
5. TDS: INR + India customers only; total − 10% of subtotal.  
6. Multi-invoice sum (e.g. Saffron): suggest `None`, mention possible combo in reason.  
7. “R K Sharma” is **not** a contact/director in seed data → payer match uses **company name only**; amount-only UI hint may include INV-1017.  
8. One reminder email **per customer** (all overdue listed); cooldown `REMINDER_COOLDOWN_MINUTES` default **5**; cleared on reset.  
9. Payment claims acknowledged, never mark paid.  
10. No auth (localhost).  
11. Stack as above.  
