from datetime import date, datetime


def parse_iso_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def is_overdue(*, status: str, balance_due_minor: int, due_date: str | date, as_of: date) -> bool:
    if status != "sent" or balance_due_minor <= 0:
        return False
    return parse_iso_date(due_date) < as_of
