"""Shopping cart totals."""

from shop.discounts import apply_discount
from shop.money import to_cents


def subtotal(items):
    """Sum quantity * unit price (dollars) for every item, in cents."""
    return sum(to_cents(item['price']) * item.get('quantity', 1) for item in items)


def total(items, code=None):
    """Subtotal after an optional discount code, never below zero."""
    amount = subtotal(items)
    if code:
        amount = apply_discount(amount, code)
    return max(amount, 0)
