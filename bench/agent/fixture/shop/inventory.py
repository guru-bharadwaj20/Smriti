"""Stock tracking."""


def in_stock(stock, sku, quantity=1):
    """True when at least `quantity` units of `sku` are available."""
    return stock.get(sku, 0) >= quantity


def reserve(stock, sku, quantity):
    """Remove reserved units from stock and return the remaining count."""
    if not in_stock(stock, sku, quantity):
        raise ValueError('insufficient stock')
    stock[sku] = stock[sku] - quantity
    return stock[sku]
