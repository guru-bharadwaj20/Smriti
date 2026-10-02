"""Customer-facing text."""


def slugify(name):
    """Lowercase product name with spaces replaced by single hyphens."""
    return name.lower().replace(' ', '-')
