# Implementation tasks (~5 focused hours)

## 0. Foundation

- [x] Docker Compose (127.0.0.1 binds; mongo not published)
- [x] `.env.example`, Dockerfiles, seed on empty DB
- [x] Settings, layered folders, `/health`, demo reset

## 1. Part A — Base app

- [x] Org / customers (edit email) / invoices with computed overdue
- [x] Frontend pages + Reset demo data

## 2. Reconciliation

- [x] CSV upload, SHA-256 dupe, matcher (weights, close&lt;8, inv# override, uniqueness)
- [x] Candidates + ui_hints; multi-sum reason; R K Sharma → None + INV-1017 hint
- [x] Approve / reject / choose + TDS options
- [x] Frontend table

## 3. Collections agent

- [x] Per-customer reminder email; `REMINDER_COOLDOWN_MINUTES`; force send; skipped reasons
- [x] IMAP poll + Check inbox now; Message-ID idempotency; sender gate
- [x] LLM JSON + one retry → Needs attention; routing; draft validator
- [x] Needs attention edit-and-send UI

## 4. Integration + security polish

- [ ] Rate limiting
- [ ] End-to-end Docker smoke with real mailbox/LLM
- [ ] explanation.pdf + video

## 5. Bonus

- [ ] Multi-invoice approve split
- [ ] Payment-email ↔ bank row
- [ ] OOO / bounce
