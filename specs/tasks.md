# Implementation tasks (~5 focused hours)

Checkboxes are the build order. Estimates are rough.

## 0. Foundation (done in Phase 2 scaffold) — ~0.5h

- [x] Docker Compose: mongo, backend, frontend  
- [x] `.env.example`, Dockerfiles, `.dockerignore`, `.gitignore`  
- [x] FastAPI `/health` + Next.js hello calling it  
- [x] README Docker run + troubleshooting  
- [ ] Settings module + Mongo connection + startup seed hook  
- [ ] Layer folders: `api` / `services` / `repositories` / `adapters`

## 1. Part A — Base app — ~1.0h

- [ ] Repositories + seed from `data/` (minor-unit conversion)  
- [ ] `GET /api/organization`, customers CRUD-lite (`PATCH` email), invoices with `is_overdue` + unpaid  
- [ ] `POST /api/demo/reset`  
- [ ] Frontend pages: Organization, Customers (edit email), Invoices (overdue badge), Reset button  

## 2. Reconciliation (Part C) — ~1.5h

- [ ] CSV upload + validation + SHA-256 dupe  
- [ ] Matcher (weights/threshold per `04-reconciliation.md`) + suggestions API  
- [ ] Approve / reject / choose-invoice + TDS options + live balance re-check  
- [ ] Frontend reconciliation table  
- [ ] Verify sample CSV mentally against edge-case table  

## 3. Collections agent (Part B) — ~1.5h

- [ ] SMTP reminder send + template + currency format + cooldown  
- [ ] IMAP adapter + poller + Check inbox now  
- [ ] Message-ID idempotency + thread matching  
- [ ] Sender→customer gate (no LLM if unknown)  
- [ ] LLM adapter (OpenAI-compatible JSON) + routing table  
- [ ] Draft validator → send or Needs attention  
- [ ] Frontend: conversations, Needs attention edit-and-send  
- [ ] Confirm paid invoices stop reminders  

## 4. Integration + security — ~0.5h

- [ ] CORS allowlist, rate limits, HTML escaping in UI  
- [ ] Safe errors; env-only secrets check  
- [ ] End-to-end: approve payment → invoice paid → no further chase  
- [ ] README polish for evaluator email/LLM setup  

## 5. Bonus (only if time) — leftover

- [ ] Multi-invoice split (Saffron 194700)  
- [ ] Payment-email ↔ bank row link  
- [ ] OOO / bounce detection  

## Submit wrap (after coding hours)

- [ ] `explanation.pdf` (2–3 pages)  
- [ ] Demo video 2.5–3 min  
- [ ] Public GitHub + email reply  
