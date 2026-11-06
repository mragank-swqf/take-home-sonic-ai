from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import combinations
from typing import Any

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from app.services.dates import parse_iso_date

INV_RE = re.compile(r"INV[- ]?(\d{3,})", re.IGNORECASE)
PREFIX_RE = re.compile(
    r"\b(NEFT|RTGS|IMPS|UPI|SWIFT|SEPA)\b|[-\/]|(\bCR\b|\bDR\b)",
    re.IGNORECASE,
)


@dataclass
class ScoredCandidate:
    invoice_number: str
    customer_id: str
    score: float
    inv_signal: float
    name_signal: float
    amount_signal: float
    date_signal: float
    reasons: list[str] = field(default_factory=list)


def normalize_payer_text(narration: str) -> str:
    text = PREFIX_RE.sub(" ", narration)
    text = INV_RE.sub(" ", text)
    text = re.sub(r"\d+", " ", text)
    return re.sub(r"\s+", " ", text).strip().upper()


def extract_invoice_numbers(narration: str) -> set[str]:
    return {f"INV-{m.group(1)}" for m in INV_RE.finditer(narration)}


def _name_points(narration: str, customer_name: str) -> tuple[float, str | None]:
    left = normalize_payer_text(narration)
    right = customer_name.upper()
    if not left or not right:
        return 0.0, None
    token = fuzz.token_set_ratio(left, right)
    jw = JaroWinkler.normalized_similarity(left, right) * 100
    best = max(token, jw)
    if best >= 90:
        return 30.0, f"strong name match ({best:.0f})"
    if best >= 80:
        return 22.0, f"good name match ({best:.0f})"
    if best >= 70:
        return 14.0, f"fair name match ({best:.0f})"
    if best >= 60:
        return 6.0, f"weak name match ({best:.0f})"
    return 0.0, None


def _tds_expected(total_minor: int, subtotal_minor: int) -> int:
    # 10% of subtotal in minor units (integer)
    return total_minor - (subtotal_minor * 10 + 5) // 100


def _amount_points(
    credit_minor: int,
    inv: dict[str, Any],
    customer: dict[str, Any],
) -> tuple[float, str | None]:
    b = int(inv["balance_due_minor"])
    t = int(inv["total_minor"])
    s = int(inv["subtotal_minor"])
    if credit_minor == b:
        return 25.0, "exact balance"
    if credit_minor == t and b == t:
        return 25.0, "exact total"
    if (
        inv.get("currency") == "INR"
        and customer.get("country") == "India"
        and credit_minor == _tds_expected(t, s)
    ):
        return 25.0, "TDS amount (total − 10% subtotal)"
    if 0 < credit_minor < b:
        return 12.0, "partial payment"
    if credit_minor > b:
        return 8.0, "overpayment"
    return 0.0, None


def _date_points(txn_date: date, inv: dict[str, Any]) -> tuple[float, str | None]:
    inv_d = parse_iso_date(inv["invoice_date"])
    due = parse_iso_date(inv["due_date"])
    if inv_d <= txn_date <= due + timedelta(days=45):
        return 5.0, "date plausible"
    if txn_date < inv_d:
        return 0.0, None
    return 2.0, "late vs due+45"


def score_invoice(
    *,
    narration: str,
    credit_minor: int,
    txn_date: date,
    inv: dict[str, Any],
    customer: dict[str, Any],
) -> ScoredCandidate:
    found = extract_invoice_numbers(narration)
    inv_signal = 40.0 if inv["invoice_number"] in found else 0.0
    name_signal, name_why = _name_points(narration, customer["name"])
    amount_signal, amount_why = _amount_points(credit_minor, inv, customer)
    date_signal, date_why = _date_points(txn_date, inv)
    reasons = []
    if inv_signal:
        reasons.append("invoice number in narration")
    if name_why:
        reasons.append(name_why)
    if amount_why:
        reasons.append(amount_why)
    if date_why:
        reasons.append(date_why)
    return ScoredCandidate(
        invoice_number=inv["invoice_number"],
        customer_id=inv["customer_id"],
        score=inv_signal + name_signal + amount_signal + date_signal,
        inv_signal=inv_signal,
        name_signal=name_signal,
        amount_signal=amount_signal,
        date_signal=date_signal,
        reasons=reasons,
    )


def find_multi_invoice_sum_hint(
    credit_minor: int,
    invoices: list[dict[str, Any]],
    customers_by_id: dict[str, dict[str, Any]],
) -> str | None:
    by_customer: dict[str, list[dict[str, Any]]] = {}
    for inv in invoices:
        by_customer.setdefault(inv["customer_id"], []).append(inv)
    for cid, group in by_customer.items():
        same_ccy: dict[str, list[dict[str, Any]]] = {}
        for inv in group:
            same_ccy.setdefault(inv["currency"], []).append(inv)
        for _ccy, bucket in same_ccy.items():
            for n in (2, 3):
                if len(bucket) < n:
                    continue
                for combo in combinations(bucket, n):
                    if sum(int(i["balance_due_minor"]) for i in combo) == credit_minor:
                        nums = ", ".join(i["invoice_number"] for i in combo)
                        name = customers_by_id.get(cid, {}).get("name", cid)
                        return f"Amount equals sum of {nums} for {name} (no auto-split)"
    return None


def match_row(
    *,
    narration: str,
    credit_minor: int,
    currency: str,
    txn_date: date,
    invoices: list[dict[str, Any]],
    customers_by_id: dict[str, dict[str, Any]],
    claimed_invoices: set[str],
) -> dict[str, Any]:
    eligible = [
        inv
        for inv in invoices
        if inv["currency"] == currency
        and inv["invoice_number"] not in claimed_invoices
        and inv.get("status") == "sent"
        and int(inv.get("balance_due_minor", 0)) > 0
    ]
    scored = [
        score_invoice(
            narration=narration,
            credit_minor=credit_minor,
            txn_date=txn_date,
            inv=inv,
            customer=customers_by_id.get(inv["customer_id"], {"name": "", "country": ""}),
        )
        for inv in eligible
    ]
    scored.sort(key=lambda s: (-s.score, -s.inv_signal, s.invoice_number))
    candidates = [{"invoice_number": s.invoice_number, "score": round(s.score, 2)} for s in scored[:5]]

    ui_hints: list[dict[str, str]] = []
    for s in scored:
        # Amount-only / weak-name hints (e.g. R K Sharma → INV-1017)
        if s.inv_signal == 0 and s.amount_signal >= 25 and s.name_signal < 14:
            ui_hints.append(
                {
                    "invoice_number": s.invoice_number,
                    "why": "Exact amount match; payer name not recognized",
                }
            )
            break

    multi_hint = find_multi_invoice_sum_hint(credit_minor, eligible, customers_by_id)

    top = scored[0] if scored else None
    second = scored[1] if len(scored) > 1 else None

    def _meets_threshold(s: ScoredCandidate, runner_up: ScoredCandidate | None) -> bool:
        if s.score >= 55:
            return True
        # Strong payer + partial/overpay with a clear gap (e.g. Orbis part payment)
        gap_ok = runner_up is None or (s.score - runner_up.score) >= 8
        return s.name_signal >= 22 and s.amount_signal >= 12 and s.score >= 38 and gap_ok

    if not top or not _meets_threshold(top, second):
        reason = multi_hint or "No confident match"
        if scored and scored[0].score > 0 and not multi_hint:
            top_txt = ", ".join(f"{c['invoice_number']} ({c['score']})" for c in candidates[:3])
            reason = f"Below threshold; top candidates: {top_txt}"
        return {
            "suggested_invoice_number": None,
            "suggested_score": None,
            "reason": reason,
            "candidates": candidates,
            "ui_hints": ui_hints,
            "match_status": "suggested" if candidates else "pending",
        }

    found_nums = extract_invoice_numbers(narration)

    ambiguous = False
    if second and (top.score - second.score) < 8 and _meets_threshold(second, None):
        # Invoice number in narration overrides close-score ambiguity
        top_has = top.invoice_number in found_nums
        second_has = second.invoice_number in found_nums
        if top_has and not second_has:
            ambiguous = False
        elif second_has and not top_has:
            top = second
            ambiguous = False
        else:
            ambiguous = True

    if ambiguous:
        names = f"{scored[0].invoice_number} and {scored[1].invoice_number}"
        return {
            "suggested_invoice_number": None,
            "suggested_score": None,
            "reason": f"Ambiguous match between {names}",
            "candidates": candidates,
            "ui_hints": ui_hints,
            "match_status": "suggested",
        }

    reason = ", ".join(top.reasons) if top.reasons else "Matched"
    if multi_hint and top.invoice_number not in (multi_hint or ""):
        # keep multi hint only when we still suggest None — here we have a single match
        pass

    return {
        "suggested_invoice_number": top.invoice_number,
        "suggested_score": round(top.score, 2),
        "reason": reason,
        "candidates": candidates,
        "ui_hints": ui_hints,
        "match_status": "suggested",
    }


def assign_unique_suggestions(row_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Greedy unique invoice assignment across rows (highest score first)."""
    proposals: list[tuple[int, float, str]] = []
    for idx, result in enumerate(row_results):
        inv = result.get("suggested_invoice_number")
        score = result.get("suggested_score")
        if inv and score is not None:
            proposals.append((idx, float(score), inv))
    proposals.sort(key=lambda x: -x[1])

    claimed: set[str] = set()
    winners: dict[int, str] = {}
    for idx, _score, inv in proposals:
        if inv in claimed:
            continue
        claimed.add(inv)
        winners[idx] = inv

    out: list[dict[str, Any]] = []
    for idx, result in enumerate(row_results):
        r = dict(result)
        suggested = r.get("suggested_invoice_number")
        if suggested and winners.get(idx) != suggested:
            # Lost uniqueness — demote to None but keep candidates
            r["reason"] = (
                f"Invoice {suggested} already suggested on another row; "
                f"choose manually from candidates"
            )
            r["suggested_invoice_number"] = None
            r["suggested_score"] = None
        out.append(r)
    return out
