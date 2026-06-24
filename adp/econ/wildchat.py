"""Loader for real conversations from WildChat-1M (allenai/WildChat-1M, ODC-BY):
~838k real human-LLM conversations. Streams so we never download the full corpus.

Usage analysis only (not model training), per the dataset license. The text is
ChatGPT-traffic, a *proxy* for LLM usage — not Claude usage — so downstream
findings are descriptive, with that caveat.
"""
from __future__ import annotations


def load_wildchat(n: int = 200, max_chars: int = 2000, min_chars: int = 12, skip: int = 0) -> list[dict]:
    from datasets import load_dataset

    ds = load_dataset("allenai/WildChat-1M", split="train", streaming=True)
    out: list[dict] = []
    seen: set[str] = set()
    for i, row in enumerate(ds):
        if i < skip:
            continue
        conv = row.get("conversation") or []
        user = next((m.get("content", "") for m in conv if m.get("role") == "user"), "")
        user = (user or "").strip()
        if len(user) < min_chars:
            continue
        key = user[:120].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": f"wc{len(out):05d}", "text": user[:max_chars]})
        if len(out) >= n:
            break
    return out
