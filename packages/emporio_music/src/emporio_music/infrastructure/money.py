"""Exact positive BRL parsing shared by snapshot importers, without float/rounding."""

from decimal import Decimal, InvalidOperation


def parse_centavos(value: str) -> int:
    try:
        amount = Decimal(value.strip())
        if (
            not amount.is_finite()
            or amount <= 0
            or amount > Decimal("92233720368547758.07")
        ):
            raise ValueError
        parts = amount.as_tuple()
        assert isinstance(parts.exponent, int)
        digits = "".join(str(digit) for digit in parts.digits)
        shift = parts.exponent + 2
        if shift < 0:
            if -shift >= len(digits) or any(digit != "0" for digit in digits[shift:]):
                raise ValueError
            digits = digits[:shift]
        else:
            if len(digits) + shift > 19:
                raise ValueError
            digits += "0" * shift
        return int(digits)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(
            "Expected positive finite BRL with exact supported centavos"
        ) from exc
