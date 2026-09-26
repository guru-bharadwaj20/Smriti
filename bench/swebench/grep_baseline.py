"""Issue-word grep baseline without lexical index or learned embeddings."""

import re
from collections.abc import Sequence

from smriti.lexical.index import SearchHit
from smriti.models import Symbol

STOP_WORDS = frozenset(
    'the a an and or to of in is it for with this that be are was as by from at'.split()
)


def grep_baseline(symbols: Sequence[Symbol], query: str, k: int = 50) -> list[SearchHit]:
    if k < 0:
        raise ValueError('k must be nonnegative')
    words = set(re.findall(r'[a-z][a-z0-9_]+', query.casefold())) - STOP_WORDS
    scored = []
    for symbol in symbols:
        if symbol.path == '<external>' or not symbol.body:
            continue
        content = (symbol.path + ' ' + symbol.body).casefold()
        score = sum(content.count(word) for word in words)
        if score:
            scored.append(SearchHit(symbol.id, float(score)))
    return sorted(scored, key=lambda hit: (-hit.score, hit.id))[:k]
