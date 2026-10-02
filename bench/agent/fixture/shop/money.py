"""Currency helpers."""


def to_cents(amount):
    """Convert a decimal amount in dollars to integer cents."""
    return round(amount * 100)


def format_price(cents):
    """Render cents as a dollar string such as '$4.05'."""
    return f'${cents // 100}.{cents % 100:02d}'
