from __future__ import annotations

import re
from datetime import date
from typing import Any

from app.services.dates import parse_iso_date
from app.services.formatting import format_money

INV_RE = re.compile(r"INV[- ]?(\d{3,})", re.IGNORECASE)
AMOUNT_RE = re.compile(
    r"(?:₹|\$|€|£)\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)"
    r"|([0-9]{1,3}(?:,[0-9]{2,3})+\.[0-9]{2})"
)
DATE_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})\b"
)


def _parse_amount_token(raw: str) -> int | None:
    cleaned = raw.replace(",", "")
    try:
        from app.services.money import to_minor

        return to_minor(cleaned)
    except Exception:  # noqa: BLE001
        return None


def _allowed_amounts(invoices: list[dict[str, Any]]) -> set[int]:
    allowed: set[int] = set()
    for inv in invoices:
        for key in ("total_minor", "balance_due_minor", "subtotal_minor", "tax_minor"):
            if key in inv:
                allowed.add(int(inv[key]))
        for item in inv.get("line_items") or []:
            if "amount_minor" in item:
                allowed.add(int(item["amount_minor"]))
        # also allow sum of balances for the draft total line
    if invoices:
        allowed.add(sum(int(i["balance_due_minor"]) for i in invoices))
    return allowed


def _allowed_dates(invoices: list[dict[str, Any]]) -> set[date]:
    out: set[date] = set()
    for inv in invoices:
        out.add(parse_iso_date(inv["invoice_date"]))
        out.add(parse_iso_date(inv["due_date"]))
    return out


def _parse_date_token(raw: str) -> date | None:
    raw = raw.strip()
    try:
        return parse_iso_date(raw)
    except ValueError:
        pass
    from datetime import datetime

    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw.replace(",", ""), fmt.replace(",", "")).date()
        except ValueError:
            continue
    return None


def validate_draft(
    draft: str,
    *,
    invoices: list[dict[str, Any]],
    org: dict[str, Any],
) -> tuple[bool, str | None]:
    allowed_inv = {i["invoice_number"] for i in invoices}
    for m in INV_RE.finditer(draft):
        num = f"INV-{m.group(1)}"
        if num not in allowed_inv:
            return False, "hallucinated_invoice"

    allowed_amt = _allowed_amounts(invoices)
    # org account number digits should be allowed if present
    acct = (org.get("bank_details") or {}).get("account_number")
    for m in AMOUNT_RE.finditer(draft):
        token = m.group(1) or m.group(2)
        minor = _parse_amount_token(token)
        if minor is None:
            continue
        if acct and token.replace(",", "").replace(".", "") == acct:
            continue
        if minor not in allowed_amt:
            return False, "hallucinated_amount"

    allowed_dates = _allowed_dates(invoices)
    for m in DATE_RE.finditer(draft):
        d = _parse_date_token(m.group(1))
        if d and d not in allowed_dates:
            return False, "hallucinated_date"

    return True, None


def reminder_body(
    *,
    contact_name: str,
    invoices: list[dict[str, Any]],
    org: dict[str, Any],
) -> str:
    lines = [
        f"Dear {contact_name},",
        "",
        "This is a reminder that the following invoice(s) are overdue:",
        "",
    ]
    for inv in invoices:
        lines.append(
            f"- {inv['invoice_number']}: {format_money(inv['balance_due_minor'], inv['currency'])} "
            f"due {inv['due_date']}"
        )
    bank = org.get("bank_details") or {}
    methods = ", ".join(org.get("payment_methods") or [])
    lines.extend(
        [
            "",
            f"Please pay via {methods} to:",
            f"{bank.get('account_name', org.get('name'))}",
            f"Account: {bank.get('account_number')}",
            f"Bank: {bank.get('bank')}",
            f"IFSC: {bank.get('ifsc')}",
            f"SWIFT: {bank.get('swift_code')}",
            "",
            "Regards,",
            org.get("accounts_contact_name", "Accounts Team"),
            org.get("name", "AcmeCorp"),
        ]
    )
    return "\n".join(lines)
