"""A small bundled set of realistic user requests to an AI assistant, spanning the
taxonomy, with a usage-like weighting. Deterministic (seeded) so the demo / tests
are reproducible and run offline.

For real results, replace this with WildChat-1M (allenai/WildChat-1M, ODC-BY):
~838k real human-LLM conversations. See README for the loader stub.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

# Per-occupation example requests (each naturally contains that occupation's cues).
TEMPLATES: dict[str, list[str]] = {
    "15-1252": [
        "Write a Python function to deduplicate a list while keeping order.",
        "Debug this JavaScript code that throws a null reference error.",
        "Help me understand how a REST API handles authentication.",
        "Generate a SQL query to join orders and customers by id.",
    ],
    "27-3042": [
        "Draft a 600-word blog article about remote work productivity.",
        "Rewrite this paragraph to sound more concise and confident.",
        "Help me outline an essay on climate policy.",
    ],
    "15-2051": [
        "Analyze this sales dataset and tell me the monthly trend.",
        "Build a chart comparing revenue across four regions.",
        "How do I run a regression to predict churn from usage data?",
    ],
    "25-2031": [
        "Explain how gradient descent works to a beginner.",
        "Help me with my calculus homework on integrals.",
        "Teach me the concept of opportunity cost with an example.",
    ],
    "13-1161": [
        "Write ad copy for a new productivity app launch.",
        "Plan a social media campaign for a coffee brand.",
        "Create a catchy slogan for an eco-friendly water bottle.",
    ],
    "23-1011": [
        "Review this contract clause about liability and flag risks.",
        "Draft simple terms of service for a small SaaS.",
        "Explain what an NDA compliance obligation means.",
    ],
    "13-2011": [
        "Build a monthly budget from these expenses.",
        "Help me compute the ROI of this marketing spend.",
        "Explain how to read a balance sheet.",
    ],
    "27-3091": [
        "Translate this email from English to Spanish.",
        "Fix the grammar in this French paragraph.",
        "Localize this product description for a German audience.",
    ],
    "11-1021": [
        "Draft a project roadmap for a 3-month product launch.",
        "Help me prepare an agenda for a strategy meeting.",
        "Write OKRs for a small operations team.",
    ],
    "27-1024": [
        "Design a color palette for a calm meditation app.",
        "Suggest a logo concept for a bakery called Rise.",
    ],
    "43-4051": [
        "Reply to a customer complaint about a late refund politely.",
        "Draft an apology email to a customer for a shipping delay.",
    ],
    "29-1000": [
        "Explain the common symptoms of dehydration.",
        "Help me plan a balanced weekly diet for more energy.",
    ],
    "19-1000": [
        "Review the literature on spaced repetition for memory.",
        "Help me design an experiment to test a hypothesis about sleep.",
    ],
    "00-0000": [
        "Plan a 5-day trip to Kyoto on a modest budget.",
        "Suggest a thoughtful birthday gift for my sister.",
    ],
}

# Rough usage-like weighting (software / writing / data / education dominate).
WEIGHTS: dict[str, float] = {
    "15-1252": 0.24, "27-3042": 0.18, "15-2051": 0.11, "25-2031": 0.10,
    "13-1161": 0.07, "11-1021": 0.06, "23-1011": 0.04, "13-2011": 0.04,
    "27-3091": 0.04, "27-1024": 0.03, "43-4051": 0.03, "29-1000": 0.02,
    "19-1000": 0.02, "00-0000": 0.02,
}


def generate_conversations(n: int = 60, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    codes = list(WEIGHTS)
    weights = [WEIGHTS[c] for c in codes]
    convs = []
    for i in range(n):
        code = rng.choices(codes, weights=weights, k=1)[0]
        text = rng.choice(TEMPLATES[code])
        convs.append({"id": f"c{i:04d}", "text": text})
    return convs


def write_csv(convs: list[dict], path: str | Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "text"])
        w.writeheader()
        w.writerows(convs)
    return str(path)
