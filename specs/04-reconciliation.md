# 04 — Bank reconciliation

## Principle

Local deterministic matcher. **Precision over recall.** Optional LLM may polish reason text only — never choose the invoice.

## Eligible invoices

- `status == "sent"`, `balance_due_minor > 0`, `currency == row.currency` (hard filter)  
- Exclude `draft` / `paid`  
- **Global uniqueness:** an invoice number must not be the primary suggestion for two rows in the same upload. Greedy assign highest-scoring unique pairs first; losers re-resolve without claimed invoices or become `None` with candidates listed.

Debits → `ignored`, suggestion `None`.

## Payer name

Compare narration (prefixes stripped) to customer **`name` only**.  
“R K Sharma” is **not** in `customers.json` / invoices as contact or director → do **not** match on contact-person names. Amount-only rows may expose `ui_hints` (e.g. INV-1017).

## Signals (0–100)

| Signal | Weight | Scoring |
|---|---|---|
| Invoice # in narration | 40 | `INV[- ]?(\d{3,})` → `INV-####`; hit on candidate → 40 |
| Payer name | 30 | `max(token_set_ratio, jaro_winkler×100)` vs customer name; ≥90→30, ≥80→22, ≥70→14, ≥60→6, else 0 |
| Amount | 25 | exact balance/total 25; TDS (INR+India) `T - round(S*0.10)` 25; partial 12; overpay 8 |
| Date | 5 | `invoice_date ≤ txn ≤ due+45d` → 5; else as before |

## Decision rules

| Rule | Detail |
|---|---|
| Suggest | Best score ≥ **55**, not blocked by uniqueness. Also allow ≥ **38** when name ≥ 22 and amount ≥ 12 with gap ≥ 8 (strong payer + partial, e.g. Orbis) |
| Close scores | If top − second **< 8** and both meet threshold → treat as ambiguous **unless** an invoice number appears in the narration for exactly one of them (**inv# overrides**) |
| Ambiguous / below threshold | `suggested_invoice_number = null`; reason names candidates; `candidates` array for one-click choose |
| Multi-invoice sum | If credit equals sum of **2–3** open balances for one customer+currency → still `None`, reason mentions those invoice numbers and the sum (no auto-split) |
| Amount-only hint | Name score 0, no inv#, exact amount on one invoice → `None` + `ui_hints` with that invoice |

## CSV / approve

Same validation as before (2 MB, 5k rows, SHA-256 dupe). Approve re-checks live balance; TDS close vs leave open per API spec.

## Edge cases (sample)

| Row | Expected |
|---|---|
| Kestrel INV 1004 / 59000 | INV-1004 |
| Orbis part 200000 | INV-1013 (partial) |
| Quillon 324000 | INV-1007 (TDS) |
| Nordlys RE 1024 / 9200 | INV-1024 (inv# breaks tie) |
| Harbour INV1021 | INV-1021 |
| Brightline INV-1002 | INV-1002 |
| Redwood Clinic 59000 | INV-1016 |
| Office rent debit | ignored |
| Thornfield 7350.5 | INV-1026 |
| Saffron 194700 | **None**; reason mentions INV-1010+1011+1012 sum |
| R K Sharma 88500 | **None**; `ui_hints`: INV-1017 |
| Maple Retail | None |
| Interest | None |

## Assumptions

1. Weights/threshold fixed unless README notes a change.  
2. No embeddings.  
