"""A small reference occupation-share distribution to validate against, plus
ranking utilities (Spearman). Lets the pipeline answer "does my distribution look
right?" with no network.

For a real validation, load Anthropic's published Economic Index release
(Anthropic/EconomicIndex on Hugging Face, CC-BY) and compare your occupation
shares to theirs. This bundled reference is a coarse stand-in shaped like the
public finding (software / writing / data lead).
"""
from __future__ import annotations

# coarse reference shares by occupation code (sum ~1.0)
REFERENCE_SHARES: dict[str, float] = {
    "15-1252": 0.25, "27-3042": 0.17, "15-2051": 0.12, "25-2031": 0.10,
    "13-1161": 0.07, "11-1021": 0.06, "23-1011": 0.04, "13-2011": 0.04,
    "27-3091": 0.04, "27-1024": 0.03, "43-4051": 0.03, "29-1000": 0.02,
    "19-1000": 0.02, "00-0000": 0.01,
}


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n < 2:
        return 0.0
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((y - mb) ** 2 for y in b) ** 0.5
    if va == 0 or vb == 0:
        return 0.0
    return cov / (va * vb)


def spearman(computed: dict[str, float], reference: dict[str, float] | None = None) -> float:
    reference = reference or REFERENCE_SHARES
    codes = sorted(set(computed) | set(reference))
    a = [computed.get(c, 0.0) for c in codes]
    b = [reference.get(c, 0.0) for c in codes]
    return round(_pearson(_rank(a), _rank(b)), 4)
