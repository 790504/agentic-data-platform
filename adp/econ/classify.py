"""Classify a conversation into (occupation, automation/augmentation) with a
pluggable backend:

  heuristic  - keyword match against the taxonomy. Free, offline, deterministic.
               Default; used by tests/CI and the zero-cost demo.
  ollama     - a local LLM via Ollama (free; uses the machine's GPU).
  claude     - the Anthropic API (paid; highest quality). Needs an API key.

All backends return the same dict, so the pipeline is backend-agnostic. A backend
failure on a single row falls back to the heuristic for that row (graceful).
"""
from __future__ import annotations

import json
import logging

from ..config import Settings
from ..monitoring import METRICS, get_logger, log
from . import taxonomy as T

_log = get_logger("adp.econ.classify")


def _heuristic(text: str) -> dict:
    low = text.lower()
    best_code, best_hits = T.DEFAULT_CODE, 0
    for occ in T.OCCUPATIONS:
        hits = sum(1 for kw in occ["keywords"] if kw in low)
        if hits > best_hits:
            best_code, best_hits = occ["code"], hits
    auto = sum(1 for c in T.AUTOMATION_CUES if c in low)
    aug = sum(1 for c in T.AUGMENTATION_CUES if c in low)
    mode = "augmentation" if aug > auto else "automation"
    confidence = min(0.95, 0.4 + 0.12 * best_hits) if best_hits else 0.3
    return {"occupation_code": best_code, "mode": mode, "confidence": round(confidence, 3), "backend": "heuristic"}


def _prompt(text: str) -> tuple[str, str]:
    codes = "\n".join(f'{o["code"]}: {o["title"]}' for o in T.OCCUPATIONS)
    system = (
        "You classify a user's request to an AI assistant into ONE occupational category and decide whether "
        "the user wants the AI to do the task (automation) or to help/learn (augmentation). "
        "Reply ONLY with compact JSON: "
        '{"occupation_code": "<code>", "mode": "automation"|"augmentation", "confidence": 0..1}.'
    )
    user = f"Categories:\n{codes}\n\nRequest:\n{text}"
    return system, user


def _coerce(raw: str, text: str) -> dict:
    try:
        start, end = raw.find("{"), raw.rfind("}")
        obj = json.loads(raw[start:end + 1])
        code = obj.get("occupation_code", "")
        if code not in T.CODE_TO_TITLE:
            return _heuristic(text)
        mode = obj.get("mode") if obj.get("mode") in ("automation", "augmentation") else "automation"
        conf = float(obj.get("confidence", 0.7))
        return {"occupation_code": code, "mode": mode, "confidence": round(min(max(conf, 0.0), 1.0), 3)}
    except Exception:
        return _heuristic(text)


def _ollama(text: str, settings: Settings) -> dict:
    import httpx

    system, user = _prompt(text)
    resp = httpx.post(
        f"{settings.econ_ollama_url}/api/chat",
        json={
            "model": settings.econ_ollama_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        },
        timeout=120,
    )
    resp.raise_for_status()
    out = _coerce(resp.json()["message"]["content"], text)
    out["backend"] = "ollama"
    return out


def _claude(text: str, settings: Settings) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    system, user = _prompt(text)
    msg = client.messages.create(model=settings.model, max_tokens=128, system=system,
                                 messages=[{"role": "user", "content": user}])
    raw = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    out = _coerce(raw, text)
    out["backend"] = "claude"
    return out


def classify_one(text: str, backend: str, settings: Settings) -> dict:
    if backend == "heuristic":
        return _heuristic(text)
    try:
        with METRICS.timer(f"econ.classify.{backend}"):
            return _ollama(text, settings) if backend == "ollama" else _claude(text, settings)
    except Exception as exc:  # noqa: BLE001 — any backend failure degrades to heuristic for this row
        METRICS.incr(f"econ.classify.{backend}.fallback")
        log(_log, logging.WARNING, "classify_fallback", backend=backend, error=str(exc))
        out = _heuristic(text)
        out["backend"] = f"{backend}->heuristic"
        return out


def classify_all(conversations: list[dict], backend: str, settings: Settings) -> list[dict]:
    rows = []
    for c in conversations:
        result = classify_one(c["text"], backend, settings)
        rows.append({
            "id": c["id"],
            "text": c["text"],
            "occupation_code": result["occupation_code"],
            "occupation": T.CODE_TO_TITLE[result["occupation_code"]],
            "mode": result["mode"],
            "confidence": result["confidence"],
            "backend": result["backend"],
        })
        METRICS.incr("econ.classified")
    return rows
