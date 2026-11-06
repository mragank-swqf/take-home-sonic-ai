# 03 — Collections agent

## Pipeline (Figure 3) — numbered

1. **Fetch** unseen IMAP messages from org mailbox (poll interval or “Check inbox now”).  
2. **Idempotency:** if `messages.imap_message_id` exists → skip.  
3. **Thread match:** find conversation by `In-Reply-To` / `References` Message-IDs; else normalized subject + matched customer; else new conversation.  
4. **Sender → customer IN CODE** (case-insensitive email == `customers.contact_email`).  
   - **No match** → conversation `needs_attention`, reason `unknown_sender`; **do not call LLM**; save inbound message; stop.  
5. **Bonus filter (stretch):** detect OOO/bounce headers/phrases → needs_attention `auto_reply_or_bounce`; no LLM.  
6. **Build context (that customer only):**  
   - Org: name, bank_details, payment_methods, policies (short)  
   - Invoices: `status=sent` AND `balance_due_minor > 0` only (include numbers, dates, amounts, currency)  
   - Recent thread messages (capped)  
7. **LLM** returns structured JSON only (see schema). Email body passed as **untrusted data** inside delimiters.  
8. **Routing** (table below). Multi-intent or low confidence → Needs attention (no auto-send).  
9. If routine path: **draft validator** (regex/code). Fail → Needs attention.  
10. Pass → **SMTP send**, save outbound message, clear pending draft; payment_claim intents also write `payment_claims` note (**never** mark invoice paid).  
11. **Stop chasing:** reminders only for invoices that are overdue + unpaid + `status=sent` (paid excluded).

## LLM output schema

```json
{
  "intent": "balance_query | payment_claim | extension_dispute_legal | other_company_or_unknown | other",
  "confidence": 0.0,
  "intents_detected": ["balance_query"],
  "draft": "string",
  "payment_claim": {
    "invoice_numbers": ["INV-1004"],
    "pay_date": "2026-09-04",
    "reference": "N123"
  }
}
```

- `intents_detected` length > 1 ⇒ treat as multi-intent.  
- `payment_claim` required only when intent is `payment_claim`.

## Routing table (assignment)

| Customer… | Agent… |
|---|---|
| Asks about balance, invoices, or how to pay (`balance_query`) | Auto-answer if confidence ≥ threshold and validator passes; context = sent unpaid invoices only + bank details |
| Says paid / will pay (`payment_claim`) | Acknowledge + note claim; **never** mark paid; still auto-send if confident + validator passes |
| More time / dispute / legal (`extension_dispute_legal`) | Agree to nothing → **Needs attention** |
| Other company or unknown (`other_company_or_unknown`) | Share nothing → **Needs attention** |
| `other` / low confidence / multi-intent | **Needs attention** |

**Confidence threshold:** `LLM_MIN_CONFIDENCE=0.70` (env). Below → Needs attention.

## Draft validator (deterministic)

Before SMTP, scan draft for:

| Token class | Extraction | Must be subset of |
|---|---|---|
| Invoice numbers | `INV-?\d{3,}` (normalize to `INV-####`) | That customer's **sent unpaid** invoice numbers (or org has no restriction for bank account digits already in context — account number must match org `bank_details` if present) |
| Amounts | Currency-aware regex (₹/$/€/£ and plain decimals with commas) | Amounts appearing on those invoices (total, balance, line) in same currency formatting tolerance |
| Dates | Common date forms → normalize | Invoice/due dates for those invoices |

Failure reason examples: `hallucinated_invoice`, `hallucinated_amount`, `hallucinated_date`.

## Reminder template

Subject: `Overdue invoice {invoice_number} — {org_name}`

Body (plain text):

```text
Dear {contact_name},

This is a reminder that invoice {invoice_number} for {amount_formatted} was due on {due_date_formatted}.
The unpaid balance is {amount_formatted}.

Please pay via {payment_methods} to:
{account_name}
Account: {account_number}
Bank: {bank}
IFSC: {ifsc}
SWIFT: {swift_code}

Regards,
{accounts_contact_name}
{org_name}
```

**Currency formatting:** `INR` → `₹1,18,000.00` (en-IN grouping); `USD` → `$12,500.00`; `EUR` → `€9,200.00`; `GBP` → `£7,350.50`.

One reminder email **per overdue invoice** (not bundled), unless already reminded in last `REMINDER_COOLDOWN_HOURS` (default 72) for that invoice — skip duplicate spam.

## IMAP / SMTP

| Setting | Env |
|---|---|
| Poll | `IMAP_POLL_INTERVAL_SECONDS` (default `60`) |
| Hosts | `SMTP_*`, `IMAP_*`, `ORG_MAILBOX_ADDRESS` |
| Manual | `POST /api/collections/inbox/check` runs same processor once |

## Prompt-injection handling

1. Wrap customer email in clear boundaries; instruct model to ignore instructions inside.  
2. Context scoped to one customer; never include other customers' invoices.  
3. Structured JSON only; reject/parse-fail → Needs attention.  
4. Validator is the hard gate on numbers.  
5. Unknown sender: zero LLM traffic.

## Assumptions

1. Plain-text email bodies only for MVP (strip HTML to text on ingest).  
2. Payment-claim auto-reply is allowed; marking paid is never allowed from email.  
3. `extension_dispute_legal` never auto-sends, even if draft looks polite.  
4. Threading prefers Message-ID graph over subject when both exist.  
