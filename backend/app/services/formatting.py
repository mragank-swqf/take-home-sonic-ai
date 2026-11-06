from decimal import Decimal


def format_money(amount_minor: int, currency: str) -> str:
    major = Decimal(amount_minor) / Decimal(100)
    quantized = f"{major:.2f}"
    whole, frac = quantized.split(".")
    if currency == "INR":
        grouped = _group_en_in(whole)
        return f"₹{grouped}.{frac}"
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, f"{currency} ")
    grouped = _group_en_us(whole)
    return f"{symbol}{grouped}.{frac}"


def _group_en_us(whole: str) -> str:
    sign = ""
    if whole.startswith("-"):
        sign, whole = "-", whole[1:]
    parts: list[str] = []
    while whole:
        parts.append(whole[-3:])
        whole = whole[:-3]
    return sign + ",".join(reversed(parts))


def _group_en_in(whole: str) -> str:
    sign = ""
    if whole.startswith("-"):
        sign, whole = "-", whole[1:]
    if len(whole) <= 3:
        return sign + whole
    last3 = whole[-3:]
    rest = whole[:-3]
    parts: list[str] = []
    while rest:
        parts.append(rest[-2:])
        rest = rest[:-2]
    return sign + ",".join(reversed(parts)) + "," + last3
