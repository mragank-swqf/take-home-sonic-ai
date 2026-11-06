# 01 — Data model (MongoDB)

## Money

| Rule | Detail |
|---|---|
| Storage | Integer **minor units** (currency × 100). Example: `59000.00 INR` → `5900000` |
| API JSON | `{ "amount_minor": 5900000, "currency": "INR", "amount_display": "₹59,000.00" }` — display is derived |
| Seed | Convert seed floats/strings from `data/*.json` and CSV at load time via `Decimal` → round half-up to 2 dp → ×100 |
| Never | Python `float` for money math; never store overdue |

## Derived (never stored)

| Field | Rule |
|---|---|
| `is_overdue` | `status == "sent"` AND `balance_due_minor > 0` AND `due_date < as_of_date` |
| `unpaid_amount_minor` | Same as `balance_due_minor` (kept explicit in API) |
| Display money / dates | Formatted in API or frontend from stored values |

## Collections

### `organization` (singleton)

| Field | Type | Notes |
|---|---|---|
| `_id` | `"acme"` | Fixed |
| `name`, `address`, `phone` | str | |
| `accounts_contact_name`, `accounts_email` | str | Org mailbox |
| `default_currency`, `accepted_currencies` | str / [str] | |
| `payment_terms`, `payment_methods` | str / [str] | |
| `bank_details` | object | account_name, account_number, bank, ifsc, swift_code |
| `policies` | object | tds, bank_charges, extensions, disputes, working_hours |

### `customers`

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `customer_id` | str | Unique, e.g. `C002` |
| `name`, `contact_name`, `contact_email` | str | Email editable |
| `phone`, `city`, `country`, `currency` | str | |

**Indexes:** unique `customer_id`; unique `contact_email` (case-insensitive via normalized `contact_email_lower`).

### `invoices`

| Field | Type | Notes |
|---|---|---|
| `invoice_number` | str | Unique |
| `customer_id`, `customer_name` | str | |
| `po_number` | str \| null | |
| `invoice_date`, `due_date` | date (ISO `YYYY-MM-DD`) | |
| `payment_terms` | str | |
| `currency` | str | |
| `line_items` | [{description, quantity, unit_price_minor, amount_minor}] | |
| `subtotal_minor`, `discount_minor`, `tax_minor`, `total_minor` | int | |
| `tax_name` | str | |
| `amount_paid_minor`, `balance_due_minor` | int | Updated only on approved payments |
| `status` | `"draft" \| "sent" \| "paid"` | |

**Indexes:** unique `invoice_number`; `{customer_id: 1, status: 1}`; `{status: 1, due_date: 1}`.

### `conversations`

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `customer_id` | str \| null | null if unknown sender |
| `subject` | str | Normalized subject (strip Re:/Fwd:) |
| `status` | `"open" \| "needs_attention" \| "closed"` | |
| `needs_attention_reason` | str \| null | |
| `pending_draft` | str \| null | Editable draft for Needs attention |
| `pending_intent` | str \| null | |
| `last_message_at` | datetime | |
| `created_at` | datetime | |

**Indexes:** `{customer_id: 1, last_message_at: -1}`; `{status: 1, last_message_at: -1}`.

### `messages`

| Field | Type | Notes |
|---|---|---|
| `conversation_id` | ObjectId | |
| `direction` | `"inbound" \| "outbound"` | |
| `from_email`, `to_email` | str | |
| `subject`, `body_text` | str | Raw text; HTML escaped only at UI |
| `imap_message_id` | str | Unique; RFC Message-ID |
| `in_reply_to`, `references` | str \| null / [str] | Threading |
| `sent_at` | datetime | |
| `kind` | `"reminder" \| "customer_reply" \| "agent_reply" \| "manual_reply"` | |
| `llm_intent`, `llm_confidence` | str \| null / float \| null | Outbound agent only |
| `validation_passed` | bool \| null | |

**Indexes:** unique `imap_message_id`; `{conversation_id: 1, sent_at: 1}`.

### `payments`

| Field | Type | Notes |
|---|---|---|
| `invoice_number` | str | |
| `customer_id` | str | |
| `amount_minor` | int | Applied amount |
| `currency` | str | |
| `source` | `"bank_reconciliation"` | |
| `bank_statement_row_id` | ObjectId | |
| `tds_closed` | bool | True if Close invoice (TDS) |
| `approved_at` | datetime | |
| `note` | str \| null | e.g. payment-claim note from email (not a paid mark) |

**Indexes:** `{invoice_number: 1}`; `{bank_statement_row_id: 1}`.

### `bank_statement_uploads`

| Field | Type | Notes |
|---|---|---|
| `filename` | str | |
| `content_sha256` | str | Duplicate-upload protection |
| `row_count` | int | |
| `uploaded_at` | datetime | |

**Indexes:** unique `content_sha256`.

### `bank_statement_rows`

| Field | Type | Notes |
|---|---|---|
| `upload_id` | ObjectId | |
| `row_index` | int | 0-based in file |
| `txn_date` | date | |
| `narration`, `reference` | str | |
| `credit_minor`, `debit_minor` | int \| null | One side usually null/0 |
| `currency` | str | |
| `direction` | `"credit" \| "debit"` | Debits are not matched to invoices |
| `match_status` | `"pending" \| "suggested" \| "approved" \| "rejected" \| "ignored"` | |
| `suggested_invoice_number` | str \| null | |
| `suggested_score` | float \| null | 0–100 |
| `suggested_reason` | str \| null | |
| `chosen_invoice_number` | str \| null | Manual override before approve |
| `tds_option` | `"close" \| "leave_open" \| null` | Required when underpay |

**Indexes:** `{upload_id: 1, row_index: 1}` unique; `{match_status: 1}`.

### `payment_claims` (notes only — never marks paid)

| Field | Type | Notes |
|---|---|---|
| `customer_id` | str | |
| `message_id` | ObjectId | Source inbound message |
| `claimed_invoice_numbers` | [str] | Parsed / LLM |
| `claimed_pay_date` | date \| null | |
| `claimed_reference` | str \| null | Bonus link to bank txn |
| `note` | str | |
| `created_at` | datetime | |

### `meta`

| Field | Type | Notes |
|---|---|---|
| `_id` | `"seed"` | |
| `seeded_at` | datetime | Idempotent first-boot flag |
| `seed_version` | str | e.g. `"data-v1"` |

## Seed / reset

1. On backend startup: if `meta.seed` missing or collections empty → load `data/*.json` (+ no CSV until upload).  
2. `POST /api/demo/reset`: drop app collections (keep Mongo), re-seed from `data/`, clear conversations, messages, payments, claims, statement uploads/rows.

## Assumptions

1. Minor-unit scale is always 100 for INR/USD/EUR/GBP in this dataset (supports `7350.5` GBP and `431.22` interest).  
2. `balance_due_minor` is the source of truth for unpaid; recomputed as `total_minor - amount_paid_minor` after each approval.  
3. Unknown-sender conversations allowed with `customer_id: null`.  
4. Draft invoices are never in LLM context and never matched for payment.  
