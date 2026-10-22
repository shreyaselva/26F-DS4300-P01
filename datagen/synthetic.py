"""Synthetic keys and query workloads.  *** YOU IMPLEMENT THIS FILE. ***

Real data (Spotify) shows how the indexes behave on realistic keys.
Synthetic data lets you control one variable at a time: how many keys, what
order they arrive in, how many lookups hit vs miss, how wide a range is.

Rules for every function:

* Use ``rng = random.Random(seed)`` and draw all randomness from ``rng``, so
  the same seed always produces the same output (on any machine).
* Never modify the list you are given; return a new one.

``tests/test_synthetic.py`` checks each function against this spec. Run it
with ``make test``.
"""

from __future__ import annotations

import random
import string
from typing import Any, Optional, Sequence


def random_keys(
    n: int,
    length: int = 8,
    alphabet: str = string.ascii_lowercase,
    seed: Optional[int] = None,
) -> list[str]:
    """Return ``n`` *distinct* random strings, each exactly ``length`` characters
    long, using only characters from ``alphabet``, in random order.

    Raise ``ValueError`` if ``n`` is larger than the number of possible
    strings (``len(alphabet) ** length``).
    """
    rng = random.Random(seed)
    if n > len(alphabet) ** length:
        raise ValueError(f"cannot make {n} distinct keys of length {length}")
    keys = []
    seen = set()
    while len(keys) < n:
        key = "".join(rng.choice(alphabet) for _ in range(length))
        if key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def arrange(
    keys: Sequence[Any],
    order: str,
    seed: Optional[int] = None,
    swap_fraction: float = 0.05,
) -> list[Any]:
    if order not in ("random", "sorted", "reversed", "nearly_sorted"):
        raise ValueError(f"unknown order: {order!r}")
    rng = random.Random(seed)
    if order == "sorted":
        return sorted(keys)
    if order == "reversed":
        return sorted(keys, reverse=True)
    if order == "random":
        result = list(keys)
        rng.shuffle(result)
        return result
    result = sorted(keys)
    n = len(result)
    for _ in range(round(swap_fraction * n)):
        i = rng.randrange(n)
        j = rng.randrange(n)
        result[i], result[j] = result[j], result[i]
    return result

# returns a list of look up queries where some of them are in the dataset and some aren't (the ratio is pre-defined in the input of this function)
def point_queries(
    keys: Sequence[str],
    n_queries: int,
    hit_rate: float,
    seed: Optional[int] = None,
) -> list[str]:
    """Return ``n_queries`` lookup keys in random order.

    Exactly ``round(n_queries * hit_rate)`` of them are *hits*: chosen at
    random (repeats allowed) from ``keys``. The rest are *misses*: random
    strings that are guaranteed NOT to be in ``keys``, each the same length as
    a randomly chosen key from ``keys``.
    """
    rng = random.Random(seed)
    key_set = set(keys)
    chars = sorted({c for k in keys for c in k}) # creates an ordered list (set) of unique characters present in each of the keys
    n_hits = round(n_queries * hit_rate) # how many look ups (n_queries) of the given should be hit. For for lookups, 0.5 hit rate, 2 must be hit
    queries = [rng.choice(keys) for _ in range(n_hits)]
    for _ in range(n_queries - n_hits): # run the loop no. of lookup queries - no. of hit times 
        length = len(rng.choice(keys))
        while True:
            candidate = "".join(rng.choice(chars) for _ in range(length))
            if candidate not in key_set:
                break
        queries.append(candidate)
    rng.shuffle(queries)
    return queries


def range_queries(
    keys: Sequence[Any],
    n_queries: int,
    selectivity: float,
    seed: Optional[int] = None,
) -> list[tuple[Any, Any]]:
    """Return ``n_queries`` ranges ``(lo, hi)`` for ``index.range_search(lo, hi)``.

    Let ``d`` be the number of *distinct* keys and ``w = max(1, round(selectivity * d))``.
    Sort the distinct keys, pick a random starting position that leaves room
    for ``w`` keys, and use the key there as ``lo`` and the key ``w - 1``
    positions later as ``hi``. So exactly ``w`` distinct keys satisfy
    ``lo <= key <= hi``. Works for any comparable keys (strings or numbers).
    """
    rng = random.Random(seed)
    distinct = sorted(set(keys))
    d = len(distinct)
    w = max(1, round(selectivity * d))
    ranges = []
    for _ in range(n_queries):
        start = rng.randrange(d - w + 1)
        ranges.append((distinct[start], distinct[start + w - 1]))
    return ranges


# cuts down keys to pre-defined uniform length (prefix)... Handbag, handshake - both get stored as hand and hand
def prefix_queries(
    keys: Sequence[str],
    n_queries: int,
    prefix_length: int,
    seed: Optional[int] = None,
) -> list[str]:
    """Return ``n_queries`` prefixes for ``index.prefix_search(prefix)``.

    Each prefix is the first ``prefix_length`` characters of a randomly chosen
    key that is at least ``prefix_length`` characters long, so every prefix
    matches at least one key.
    """
    rng = random.Random(seed)
    eligible = [k for k in keys if len(k) >= prefix_length]
    if not eligible:
        raise ValueError("no key is long enough for this prefix_length")
    return [rng.choice(eligible)[:prefix_length] for _ in range(n_queries)]
