# 02 — REST API

Base: `http://localhost:8000/api`  
Errors: `{ "detail": string | [{loc, msg, type}] }`  
Common codes: `400` validation, `404` missing, `409` conflict, `422` body, `429` rate limit, `500` safe message.

---

## Health / demo

| Method | Path | Request | Response | Errors |
|---|---|---|---|---|
| GET | `/health` | — | `{ "status": "ok" }` | — |
| POST | `/api/demo/reset` | — | `{ "ok": true, "seeded": { customers, invoices } }` | 500 |

---

## Organization

| Method | Path | Response |
|---|---|---|
| GET | `/api/organization` | Full org document (no secrets) |

---

## Customers

| Method | Path | Request | Response | Errors |
|---|---|---|---|---|
| GET | `/api/customers` | — | `{ "items": [Customer] }` | — |
| GET | `/api/customers/{customer_id}` | — | `Customer` | 404 |
| PATCH | `/api/customers/{customer_id}` | `{ "contact_email": string }` | `Customer` | 400 invalid email, 409 email taken, 404 |

`Customer` includes all stored fields; emails returned raw (UI may display as-is).

---

## Invoices

| Method | Path | Query | Response |
|---|---|---|---|
| GET | `/api/invoices` | `customer_id?`, `status?`, `overdue=true?` | `{ "items": [InvoiceView] }` |
| GET | `/api/invoices/{invoice_number}` | — | `InvoiceView` |

`InvoiceView` = stored invoice + derived:

```json
{
  "invoice_number": "INV-1004",
  "status": "sent",
  "currency": "INR",
  "total_minor": 5900000,
  "amount_paid_minor": 0,
  "balance_due_minor": 5900000,
  "unpaid_amount_minor": 5900000,
  "is_overdue": true,
  "due_date": "2026-09-19",
  "...": "..."
}
```

---

## Collections — reminders & inbox

| Method | Path | Request | Response | Errors |
|---|---|---|---|---|
| POST | `/api/collections/reminders/send` | `{ "invoice_numbers"?: string[] }` omit = all overdue unpaid sent | `{ "sent": [...], "skipped": [...] }` | 400, 502 SMTP |
| POST | `/api/collections/inbox/check` | — | `{ "processed": n, "needs_attention": n, "sent_replies": n }` | 502 IMAP |
| GET | `/api/collections/conversations` | `status?` (`open`\|`needs_attention`\|`closed`) | `{ "items": [ConversationSummary] }` | — |
| GET | `/api/collections/conversations/{id}` | — | Conversation + messages (chronological) | 404 |
| GET | `/api/collections/needs-attention` | — | `{ "items": [NeedsAttentionItem] }` | — |
| PATCH | `/api/collections/needs-attention/{conversation_id}` | `{ "draft": string }` | Updated item | 404, 400 |
| POST | `/api/collections/needs-attention/{conversation_id}/send` | `{ "draft"?: string }` uses body or stored pending_draft | `{ "message_id": "...", "conversation_id": "..." }` | 400 empty, 404, 502 SMTP |

`NeedsAttentionItem`: conversation_id, customer_id?, subject, reason, pending_draft, pending_intent, latest inbound snippet.

---

## Reconciliation

| Method | Path | Request | Response | Errors |
|---|---|---|---|---|
| POST | `/api/reconciliation/uploads` | `multipart/form-data` file=`*.csv` | `{ "upload_id", "rows": n, "suggestions_ready": true }` | 400 bad CSV, 409 duplicate sha256, 413 too large |
| GET | `/api/reconciliation/uploads` | — | `{ "items": [UploadSummary] }` | — |
| GET | `/api/reconciliation/uploads/{upload_id}/suggestions` | — | `{ "items": [SuggestionRow] }` | 404 |
| POST | `/api/reconciliation/rows/{row_id}/approve` | `{ "invoice_number"?: string, "tds_option"?: "close"\|"leave_open" }` | `{ "payment_id", "invoice": InvoiceView }` | 400, 404, 409 stale balance / already approved |
| POST | `/api/reconciliation/rows/{row_id}/reject` | — | `{ "row_id", "match_status": "rejected" }` | 404, 409 |
| POST | `/api/reconciliation/rows/{row_id}/choose-invoice` | `{ "invoice_number": string }` | Updated suggestion row (status still pending until approve) | 404 invoice, 400 currency mismatch |

`SuggestionRow`: date, narration, amount_minor, currency, suggested_invoice_number, score, reason, match_status, tds_required bool.

**Approve rules**

- Re-load invoice; reject if currency mismatch, invoice paid/draft, or row not credit/pending|suggested|chosen.  
- Amount vs balance: exact → pay full; underpay → require `tds_option`; overpay → apply up to balance, note overpay in payment.note (balance → 0, status paid).  
- `tds_option=close` → set `amount_paid_minor = total_minor`, `balance_due_minor = 0`, `status=paid`, `tds_closed=true`.  
- `tds_option=leave_open` → add credit to `amount_paid_minor`, reduce balance, stay `sent` if balance > 0.

---

## Assumptions

1. No auth headers for the take-home; network exposure assumed local Docker.  
2. Reminder endpoint is explicit (UI button); also safe to call for all overdue.  
3. IMAP background poller runs in-process (asyncio) using `IMAP_POLL_INTERVAL_SECONDS`; manual check uses same pipeline.  
4. Choose-invoice only sets selection; approve applies money.  
