"""Common-origin clustering (GAP-25, AC-D08): copies of one release are one confirmation, not several.

Two texts share an origin when their word 5-shingle sets overlap by at least 60% of the smaller set
(containment, so a press release quoted whole inside a longer filing exhibit still matches). Clusters are
connected components, computed over at most `max_documents` texts; comparisons beyond the bound are
reported, not silently skipped. A cluster count is an upper bound on independence, never proof of it.
"""

import re

_WORD = re.compile(r"[a-z0-9]+")
CONTAINMENT = (3, 5)


def shingles(text: str, k: int = 5) -> frozenset:
    words = _WORD.findall(text.lower())
    return frozenset(" ".join(words[i:i + k]) for i in range(max(1, len(words) - k + 1)))


def same_origin(a: frozenset, b: frozenset) -> bool:
    small = min(len(a), len(b))
    return small > 0 and len(a & b) * CONTAINMENT[1] >= CONTAINMENT[0] * small


def clusters(documents: list, max_documents: int = 500) -> dict:
    """documents: [(doc_id, text)] -> {"clusters": [[doc_id...]], "truncated": bool}."""
    docs = documents[:max_documents]
    sets = [(d, shingles(t)) for d, t in docs]
    parent = list(range(len(sets)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            if same_origin(sets[i][1], sets[j][1]):
                parent[find(i)] = find(j)
    groups = {}
    for i, (doc_id, _) in enumerate(sets):
        groups.setdefault(find(i), []).append(doc_id)
    return {"clusters": sorted(sorted(g) for g in groups.values()), "truncated": len(documents) > max_documents}


def independent_confirmations(documents: list) -> int:
    """Upper bound on independent confirmations: the number of common-origin clusters."""
    return len(clusters(documents)["clusters"])
