# 03 — Collections agent

## Pipeline (Figure 3) — numbered

1. **Fetch** unseen IMAP messages (poll or Check inbox now).  
2. **Idempotency:** skip if `imap_message_id` already stored.  
3. **Thread match:** `In-Reply-To` / `References`; else normalized subject + customer; else new conversation. **One conversation thread per customer** for reminders/replies when possible.  
4. **Sender → customer IN CODE** (case-insensitive email). Unknown → Needs attention, **no LLM**.  
5. Stretch: OOO/bounce → Needs attention, no LLM.  
6. **Context:** that customer's sent unpaid invoices + org bank/policies only.  
7. **LLM** structured JSON. Body = untrusted. **Parse defensively:** strip fences, `json.loads`; on failure **one retry** asking for JSON only; still fail → Needs attention (`llm_parse_error`).  
8. **Routing** (table). Multi-intent or low confidence → Needs attention.  
9. Routine path → **draft validator**. Fail → Needs attention.  
10. Pass → SMTP, save message; `payment_claim` writes note only (**never** marks paid).  
11. Reminders exclude `paid` invoices.

## LLM schema

```json
{
  "intent": "balance_query | payment_claim | extension_dispute_legal | other_company_or_unknown | other",
  "confidence": 0.0,
  "intents_detected": ["balance_query"],
  "draft": "string",
  "payment_claim": { "invoice_numbers": [], "pay_date": null, "reference": null }
}
```

`LLM_MIN_CONFIDENCE=0.70`. Multi-intent if `intents_detected.length > 1`.

## Routing

| Intent | Action |
|---|---|
| `balance_query` | Auto-send if confident + validator OK |
| `payment_claim` | Auto-send ack + note; never mark paid |
| `extension_dispute_legal` | Needs attention (never auto-send) |
| `other_company_or_unknown` | Needs attention; share nothing |
| `other` / low confidence / multi-intent / parse fail | Needs attention |

## Draft validator

Invoice numbers, amounts, dates in draft must match that customer's sent unpaid invoice data (and org bank account digits if present). Fail → Needs attention.

## Reminders (per customer)

- **One email per customer** listing **all** of that customer's overdue invoices.  
- Subject: `Overdue invoices — {org_name}`  
- Body lists each invoice (number, amount formatted, due date) + bank details.  
- Thread: reuse open conversation for that customer or create one.  
- Cooldown: `REMINDER_COOLDOWN_MINUTES` (default **5**), stored as `customers.last_reminder_sent_at`.  
- Batch send skips cooldown-active customers with reason `cooldown_active`.  
- `POST .../reminders/send/{customer_id}` with `force: true` = send-now override.  
- Reset demo clears all `last_reminder_sent_at`.

Currency format: INR en-IN; USD/EUR/GBP with symbol + 2 dp.

## Prompt injection

Delimit untrusted body; scoped context; JSON-only; validator gate; unknown sender = no LLM.

## Assumptions

1. Plain text bodies (HTML stripped).  
2. “R K Sharma” not a seed contact — irrelevant to collections matching.  
