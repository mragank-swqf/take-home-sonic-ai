from decimal import ROUND_HALF_UP, Decimal


def to_minor(value: float | int | str | Decimal) -> int:
    """Convert major-unit amount to integer minor units (×100)."""
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(amount * 100)
