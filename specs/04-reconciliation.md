# 04 — Bank reconciliation

## Principle

Local deterministic matcher only for the core decision. **Precision over recall:** wrong invoice suggestions cost more than `None`. Optional LLM may **polish the reason string only** after scores are fixed — never choose the invoice.

## Eligible invoices (candidates)

Include invoice if all true:

- `status == "sent"`
- `balance_due_minor > 0`
- `currency == row.currency` (**hard filter**)
- Not already linked to an **approved** payment that fully claims this row (row-level)
- Exclude invoices already selected on another **pending/suggested** row in the same upload with score ≥ threshold only as soft preference — still allow ties to surface; on approve, re-check live balance

Exclude: `draft`, `paid`, wrong currency.

Debit rows → `match_status=ignored`, suggestion `None`, reason `Debit — not a customer receipt`.

## Signals (independent → weighted score 0–100)

| Signal | Weight | Scoring |
|---|---|---|
| **Invoice number in narration** | 40 | Regex find `INV[- ]?(\d{3,})` → normalize `INV-####`. Exact candidate hit → 40; else 0 |
| **Payer name similarity** | 30 | Normalize narration: strip transfer prefixes (`NEFT|RTGS|IMPS|UPI|SWIFT|SEPA`, `CR`/`DR`, refs). Compare to customer `name` with `max(token_set_ratio, jaro_winkler*100)` via **rapidfuzz**. Map: ≥90 → 30; ≥80 → 22; ≥70 → 14; ≥60 → 6; else 0 |
| **Amount** | 25 | See amount rules below |
| **Date plausibility** | 5 | `invoice_date ≤ txn_date ≤ due_date + 45 days` → 5; `txn_date < invoice_date` → 0; `txn_date > due_date + 45` → 2 if other signals strong else 0 |

**Currency:** not a scored signal — candidates with other currency are removed before scoring.

### Amount rules (25 pts max)

Let `C` = credit_minor, `B` = balance_due_minor, `T` = total_minor, `S` = subtotal_minor.

| Case | Condition | Points |
|---|---|---|
| Exact balance | `C == B` | 25 |
| Exact total (unpaid full) | `C == T` and `B == T` | 25 |
| TDS (INR + customer.country == India only) | `C == T - round(S * 0.10)` (minor-units integer math) | 25 |
| Partial | `0 < C < B` | 12 |
| Overpayment | `C > B` | 8 |
| Else | — | 0 |

TDS example (assignment): INV-1007 `T=354000`, `S=300000` → expected credit `324000`.

## Thresholds & ties

| Rule | Value |
|---|---|
| Suggest invoice | best score **≥ 55** |
| Else | `None` (reason from top miss or `No confident match`) |
| Tie | Same score within **1.0**: prefer higher invoice-number signal; then earlier `due_date`; then lower `invoice_number`. If still tied → `None` with reason `Ambiguous match` (precision) |
| Second-best gap | If top − second < 5 and both ≥ 55 → `None` / `Ambiguous match` |

## CSV validation

Required headers (exact): `txn_date,narration,reference,credit,debit,currency`

| Check | Action |
|---|---|
| Missing/unknown columns | 400 |
| Bad date | 400 row error |
| Both credit and debit non-empty | 400 |
| Both empty | 400 |
| Currency not in org `accepted_currencies` | 400 |
| Max size | 2 MB / 5 000 rows |
| Content-Type / extension | `.csv` only |
| Duplicate file | SHA-256 of raw bytes → 409 if `bank_statement_uploads.content_sha256` exists |

After validate: insert upload + rows; run matcher; set `suggested_*`.

## Approval re-check

On approve:

1. Lock row (status must be `suggested` or pending with chosen invoice).  
2. Re-load invoice; abort 409 if paid/draft, currency mismatch, or `balance_due_minor` changed such that chosen action is invalid.  
3. Apply payment (see `02-api.md`).  
4. Mark row `approved`; create `payments` doc.  
5. Collections agent stops reminders for that invoice when `status=paid`.

## Optional LLM reason polish

Input: already-chosen invoice + signal breakdown. Output: one short sentence. On LLM failure, keep template reason from signals (e.g. `Invoice number found, exact amount`).

## Edge cases (sample statement)

| Row (short) | Expected | Why |
|---|---|---|
| `IMPS/KESTREL FOODS/INV 1004` 59000 INR | **INV-1004** high | Inv# + name + exact |
| `UPI/ORBIS PKG/PART PAYMENT` 200000 INR | **INV-1013** medium | Name + partial (largest open Orbis) |
| `RTGS CR-QUILLON TECH…` 324000 INR | **INV-1007** high | TDS amount + name |
| `SEPA CR NORDLYS… RE 1024` 9200 EUR | **INV-1024** | Inv# 1024 in narration breaks tie with INV-1025 |
| `SWIFT CR HARBOUR… INV1021` 12500 USD | **INV-1021** | Inv# + exact |
| `NEFT…BRIGHTLINE…INV-1002` 236000 INR | **INV-1002** | Inv# + exact |
| `NEFT CR-REDWOOD CLINIC` 59000 INR | **INV-1016** | Name + exact on 1016 (not 1017) |
| `NEFT DR-OFFICE RENT` debit | **None** / ignored | Debit |
| `SWIFT CR THORNFIELD…` 7350.5 GBP | **INV-1026** | Name + exact minor units |
| `NEFT…SAFFRON PEAK…OCT DUES` 194700 INR | **None** (MVP) / bonus multi | 82600+41300+70800; MVP: no single invoice exact → None or weak partial — **prefer None** unless bonus split implemented |
| `SWIFT DR SOFTWARE VENDOR` | ignored | Debit |
| `IMPS/R K SHARMA/CLINIC DUES` 88500 INR | **None** or low | Amount matches INV-1017 but payer ≠ Redwood; precision → None if name score 0 and no inv# |
| `NEFT CR-MAPLE RETAIL…` 12750 INR | **None** | Unknown payer |
| `INT.PD:…` 431.22 INR | **None** | Interest / no customer |

## Bonus (stretch)

| Item | Spec sketch |
|---|---|
| Multi-invoice split | Search subsets of same customer+currency unpaid invoices whose balances sum to credit; suggest list + split on approve |
| Payment-email link | On suggestion UI, show `payment_claims` with matching invoice/reference near row |
| OOO/bounce | Handled in collections (`03`), not matcher |

## Assumptions

1. Weights/threshold above are fixed defaults; tune only if sample precision suffers — document changes in README.  
2. MVP does **not** auto-split multi-invoice payments (Saffron 194700 → None).  
3. `rapidfuzz` token_set_ratio + Jaro-Winkler only (no embeddings) for the time budget.  
4. Partial payments suggest the single best-scoring invoice, not “any partial”.  
