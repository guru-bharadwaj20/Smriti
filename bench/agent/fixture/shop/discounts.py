"""Discount codes."""

CODES = {'SAVE10': 10, 'HALF': 50}


def apply_discount(cents, code):
    """Apply a percentage discount code; unknown codes leave the amount unchanged."""
    percent = CODES.get(code, 0)
    return cents - cents * percent // 100
