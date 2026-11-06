# 02 — REST API

Base: `http://127.0.0.1:8000`  
Errors: `{ "detail": string | [{loc, msg, type}] }`  
Codes: `400` validation, `404` missing, `409` conflict, `413` too large, `422` body, `429` rate limit, `500`/`502` safe message.

**No auth** (localhost demo limitation).

---

## Health / demo

| Method | Path | Response |
|---|---|---|
| GET | `/health` | `{ "status": "ok" }` |
| POST | `/api/demo/reset` | `{ "ok": true, "seeded": { "customers", "invoices" } }` — also clears reminder cooldowns, conversations, payments, statements |

---

## Organization / customers / invoices

| Method | Path | Request | Response | Errors |
|---|---|---|---|---|
| GET | `/api/organization` | — | Org doc | — |
| GET | `/api/customers` | — | `{ "items": [Customer] }` | — |
| GET | `/api/customers/{customer_id}` | — | `Customer` | 404 |
| PATCH | `/api/customers/{customer_id}` | `{ "contact_email": string }` | `Customer` | 400, 409, 404 |
| GET | `/api/invoices` | `customer_id?`, `status?`, `overdue=true?` | `{ "items": [InvoiceView] }` | — |
| GET | `/api/invoices/{invoice_number}` | — | `InvoiceView` | 404 |

`InvoiceView` includes derived `is_overdue`, `unpaid_amount_minor` (= `balance_due_minor`). Overdue uses as-of date from settings (UTC today if `DEMO_AS_OF_DATE` empty).

---

## Collections

| Method | Path | Request | Response | Errors |
|---|---|---|---|---|
| POST | `/api/collections/reminders/send` | `{ "customer_ids"?: string[] }` omit = all with overdue | `{ "sent": [SentReminder], "skipped": [{ "customer_id", "reason" }] }` | 502 SMTP |
| POST | `/api/collections/reminders/send/{customer_id}` | `{ "force"?: true }` | same shape for one customer; `force=true` bypasses cooldown | 404, 502 |
| POST | `/api/collections/inbox/check` | — | `{ "processed", "needs_attention", "sent_replies" }` | 502 |
| GET | `/api/collections/conversations` | `status?` | `{ "items": [...] }` | — |
| GET | `/api/collections/conversations/{id}` | — | Conversation + messages | 404 |
| GET | `/api/collections/needs-attention` | — | `{ "items": [NeedsAttentionItem] }` | — |
| PATCH | `/api/collections/needs-attention/{id}` | `{ "draft": string }` | item | 404 |
| POST | `/api/collections/needs-attention/{id}/send` | `{ "draft"?: string }` | `{ "message_id", "conversation_id" }` | 400, 404, 502 |

`SentReminder`: `customer_id`, `invoice_numbers`, `message_id`, `conversation_id`.

Skip reasons: `no_overdue`, `cooldown_active`, `no_contact_email`, `smtp_not_configured`.

---

## Reconciliation

| Method | Path | Request | Response | Errors |
|---|---|---|---|---|
| POST | `/api/reconciliation/uploads` | multipart `file` | `{ "upload_id", "rows", "suggestions_ready": true }` | 400, 409, 413 |
| GET | `/api/reconciliation/uploads` | — | `{ "items": [UploadSummary] }` | — |
| GET | `/api/reconciliation/uploads/{upload_id}/suggestions` | — | `{ "items": [SuggestionRow] }` | 404 |
| POST | `/api/reconciliation/rows/{row_id}/approve` | `{ "invoice_number"?: string, "tds_option"?: "close"\|"leave_open" }` | `{ "payment_id", "invoice" }` | 400, 404, 409 |
| POST | `/api/reconciliation/rows/{row_id}/reject` | — | `{ "row_id", "match_status": "rejected" }` | 404, 409 |
| POST | `/api/reconciliation/rows/{row_id}/choose-invoice` | `{ "invoice_number": string }` | Updated row | 400, 404 |

`SuggestionRow`:

```json
{
  "id": "...",
  "txn_date": "2026-10-20",
  "narration": "...",
  "amount_minor": 8850000,
  "currency": "INR",
  "match_status": "suggested",
  "suggested_invoice_number": null,
  "suggested_score": null,
  "reason": "Ambiguous match between INV-1024 and INV-1025",
  "candidates": [
    { "invoice_number": "INV-1024", "score": 72.0 },
    { "invoice_number": "INV-1025", "score": 68.0 }
  ],
  "ui_hints": [
    { "invoice_number": "INV-1017", "why": "Exact amount match; payer name not recognized" }
  ],
  "tds_required": false,
  "chosen_invoice_number": null
}
```

`candidates` always lists top scored invoices for one-click choose when suggestion is `None`/ambiguous. `ui_hints` for amount-only weak signals (e.g. INV-1017 for R K Sharma row).

---

## Assumptions

1. Compose publishes API/UI on `127.0.0.1` only; Mongo not published.  
2. IMAP poller in-process; manual check shares pipeline.  
3. Choose-invoice sets selection; approve applies money.  
