# 05 — Security

## Secrets

| Rule | Detail |
|---|---|
| Never commit | `.env`, API keys, mailbox passwords |
| Provide | `.env.example` placeholders + comments only |
| Runtime | Pydantic settings from env; frontend only gets `NEXT_PUBLIC_API_URL` |

## Input validation

| Surface | Controls |
|---|---|
| JSON bodies | Pydantic models; strict types; email `EmailStr` |
| Path params | Constrained strings (`^C\d{3}$`, `^INV-\d+$`, ObjectId) |
| Query params | Enums / whitelists |
| CSV | Schema, size, row cap, SHA-256 dupe check (`04`) |

## Mongo injection

- No raw query assembly from user strings.  
- Use parameterized dict filters with typed values.  
- Never `$where` / eval.  
- Operator injection: reject keys starting with `$` in user-provided objects (none expected in MVP bodies).

## CSV upload

| Limit | Value |
|---|---|
| Max bytes | 2 MB |
| Max rows | 5 000 |
| Types | `.csv` / `text/csv` / `application/vnd.ms-excel` careful allowlist |
| Store | Parsed fields only; do not execute formulas |

## CORS

- `CORS_ORIGINS` env allowlist (e.g. `http://localhost:3000`).  
- No `*` when credentials used; MVP: explicit origins only.

## Rate limiting

| Route class | Limit (per IP) |
|---|---|
| Default API | 120 / minute |
| `POST /api/reconciliation/uploads` | 10 / minute |
| `POST /api/collections/inbox/check` | 20 / minute |
| `POST /api/collections/reminders/send` | 10 / minute |
| `POST /api/demo/reset` | 5 / minute |

Implementation: slowapi or simple in-memory token bucket (document Docker single-worker assumption).

## Data scoping

| Rule | Detail |
|---|---|
| Customer email match | Inbound mail tied only to matching customer |
| LLM context | That customer's unpaid sent invoices + org public bank details only |
| API | Invoice/customer fetches by id; no cross-customer dump beyond list endpoints intended for Accounts UI |
| Unknown sender | No invoice data in any auto reply |

## Email content in UI

- Treat body as untrusted.  
- React/Next: render as text or with HTML escaped (no `dangerouslySetInnerHTML`).  
- API may return raw text; UI escapes.

## LLM output

- Untrusted until draft validator passes.  
- Needs-attention drafts still escaped in UI; human edits re-validated for invoice/amount/date tokens before send (same validator).

## Error messages

- Clients get generic `detail` without stack traces, Mongo errors, or SMTP credentials.  
- Log internals server-side only.

## Docker / process

- Backend container runs as **non-root**.  
- No secrets in images; only env at runtime.  
- Frontend never receives SMTP/IMAP/LLM keys.  
- Compose binds published ports to **`127.0.0.1` only**.  
- **Mongo port is not published** to the host.

## LLM JSON

- Defensive parse (strip markdown fences, `json.loads`).  
- **One retry** with a stricter “JSON only” prompt.  
- Still invalid → Needs attention (`llm_parse_error`); never crash the poller.

## Assumptions

1. **No authentication** — intentional demo limitation for localhost evaluators; documented in README. Do not expose beyond loopback.  
2. Single-worker uvicorn for in-memory rate limit correctness.  
