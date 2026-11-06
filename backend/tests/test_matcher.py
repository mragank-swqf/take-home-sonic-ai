from datetime import date

from app.services.money import to_minor
from app.services.reconciliation_match import match_row


def _inv(**kwargs):
    base = {
        "invoice_number": "INV-1004",
        "customer_id": "C002",
        "currency": "INR",
        "status": "sent",
        "invoice_date": "2026-08-20",
        "due_date": "2026-09-19",
        "subtotal_minor": to_minor(50000),
        "total_minor": to_minor(59000),
        "balance_due_minor": to_minor(59000),
    }
    base.update(kwargs)
    return base


def test_kestrel_exact():
    customers = {
        "C002": {"name": "Kestrel Foods Private Limited", "country": "India"},
    }
    result = match_row(
        narration="IMPS/KESTREL FOODS/INV 1004",
        credit_minor=to_minor(59000),
        currency="INR",
        txn_date=date(2026, 9, 5),
        invoices=[_inv()],
        customers_by_id=customers,
        claimed_invoices=set(),
    )
    assert result["suggested_invoice_number"] == "INV-1004"


def test_r_k_sharma_none_with_hint():
    customers = {
        "C006": {"name": "Redwood Clinics Pvt Ltd", "country": "India"},
    }
    inv = _inv(
        invoice_number="INV-1017",
        customer_id="C006",
        subtotal_minor=to_minor(80000),
        total_minor=to_minor(88500),
        balance_due_minor=to_minor(88500),
        invoice_date="2026-10-02",
        due_date="2026-11-01",
    )
    result = match_row(
        narration="IMPS/R K SHARMA/CLINIC DUES",
        credit_minor=to_minor(88500),
        currency="INR",
        txn_date=date(2026, 10, 20),
        invoices=[inv],
        customers_by_id=customers,
        claimed_invoices=set(),
    )
    assert result["suggested_invoice_number"] is None
    assert any(h["invoice_number"] == "INV-1017" for h in result["ui_hints"])


def test_saffron_multi_sum_reason():
    customers = {
        "C004": {"name": "Saffron Peak Hospitality LLP", "country": "India"},
    }
    invoices = [
        _inv(
            invoice_number="INV-1010",
            customer_id="C004",
            total_minor=to_minor(82600),
            balance_due_minor=to_minor(82600),
            subtotal_minor=to_minor(70000),
            invoice_date="2026-09-05",
            due_date="2026-10-05",
        ),
        _inv(
            invoice_number="INV-1011",
            customer_id="C004",
            total_minor=to_minor(41300),
            balance_due_minor=to_minor(41300),
            subtotal_minor=to_minor(35000),
            invoice_date="2026-09-15",
            due_date="2026-10-15",
        ),
        _inv(
            invoice_number="INV-1012",
            customer_id="C004",
            total_minor=to_minor(70800),
            balance_due_minor=to_minor(70800),
            subtotal_minor=to_minor(65000),
            invoice_date="2026-09-25",
            due_date="2026-10-25",
        ),
    ]
    result = match_row(
        narration="NEFT CR-SAFFRON PEAK HOSP-OCT DUES",
        credit_minor=to_minor(194700),
        currency="INR",
        txn_date=date(2026, 10, 12),
        invoices=invoices,
        customers_by_id=customers,
        claimed_invoices=set(),
    )
    assert result["suggested_invoice_number"] is None
    assert "INV-1010" in result["reason"]
    assert "sum" in result["reason"].lower() or "sum of" in result["reason"]
