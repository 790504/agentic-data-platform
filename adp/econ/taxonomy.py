"""A compact occupation taxonomy (an O*NET/SOC-flavored subset) used to classify
what kind of work a conversation is about.

For a faithful full run, swap this for the real O*NET task database
(https://www.onetcenter.org/database.html, CC-BY 4.0). This subset keeps the
demo offline and dependency-free.
"""
from __future__ import annotations

# code (SOC-flavored) | title | keywords (for the offline heuristic) | example tasks
OCCUPATIONS: list[dict] = [
    {"code": "15-1252", "title": "Software & IT",
     "keywords": ["code", "function", "bug", "python", "javascript", "api", "debug", "program", "sql", "app", "script", "regex", "compile"],
     "tasks": ["write code", "debug a program", "design an API"]},
    {"code": "27-3042", "title": "Writing & Content",
     "keywords": ["write", "essay", "blog", "article", "story", "draft", "copy", "rewrite", "paragraph", "headline", "newsletter"],
     "tasks": ["draft an article", "rewrite copy", "outline an essay"]},
    {"code": "15-2051", "title": "Data & Analysis",
     "keywords": ["data", "analysis", "dataset", "chart", "statistics", "regression", "pandas", "visualize", "dashboard", "spreadsheet", "forecast"],
     "tasks": ["analyze a dataset", "build a chart", "run a regression"]},
    {"code": "25-2031", "title": "Education & Tutoring",
     "keywords": ["explain", "teach", "learn", "concept", "homework", "study", "understand", "lesson", "tutor", "quiz", "example of"],
     "tasks": ["explain a concept", "help with homework", "create a lesson"]},
    {"code": "13-1161", "title": "Marketing & Sales",
     "keywords": ["marketing", "campaign", "seo", "ad", "audience", "brand", "social media", "slogan", "pitch", "landing page", "tagline"],
     "tasks": ["write ad copy", "plan a campaign", "draft a pitch"]},
    {"code": "23-1011", "title": "Legal",
     "keywords": ["contract", "legal", "clause", "lawsuit", "terms", "compliance", "agreement", "law", "policy", "liability", "nda"],
     "tasks": ["review a contract", "draft terms", "check compliance"]},
    {"code": "13-2011", "title": "Finance & Accounting",
     "keywords": ["tax", "accounting", "invoice", "budget", "financial", "balance sheet", "expense", "audit", "valuation", "cash flow", "roi"],
     "tasks": ["build a budget", "compute taxes", "model cash flow"]},
    {"code": "27-3091", "title": "Translation & Languages",
     "keywords": ["translate", "translation", "language", "chinese", "spanish", "french", "localize", "grammar", "pronunciation", "german"],
     "tasks": ["translate text", "localize content", "fix grammar"]},
    {"code": "11-1021", "title": "Management & Business Ops",
     "keywords": ["strategy", "plan", "meeting", "business", "manage", "project", "roadmap", "decision", "okrs", "agenda", "process"],
     "tasks": ["draft a plan", "prep a meeting", "build a roadmap"]},
    {"code": "27-1024", "title": "Design & Creative",
     "keywords": ["design", "logo", "color", "layout", "creative", "illustration", "font", "moodboard", "wireframe", "palette"],
     "tasks": ["design a logo", "pick a palette", "sketch a layout"]},
    {"code": "43-4051", "title": "Customer Service & Support",
     "keywords": ["customer", "support", "complaint", "refund", "ticket", "reply to", "email response", "apology", "help desk"],
     "tasks": ["reply to a customer", "handle a complaint", "draft an apology"]},
    {"code": "29-1000", "title": "Healthcare & Wellness",
     "keywords": ["symptom", "health", "medical", "diagnosis", "patient", "medicine", "doctor", "treatment", "diet", "fitness", "sleep"],
     "tasks": ["explain symptoms", "plan a diet", "summarize a study"]},
    {"code": "19-1000", "title": "Science & Research",
     "keywords": ["research", "experiment", "hypothesis", "paper", "literature", "study design", "scientific", "methodology", "citation", "abstract"],
     "tasks": ["review literature", "design an experiment", "write an abstract"]},
    {"code": "00-0000", "title": "Personal & Other",
     "keywords": ["recipe", "travel", "advice", "relationship", "trip", "gift", "personal", "cook", "workout", "hobby"],
     "tasks": ["plan a trip", "suggest a gift", "give advice"]},
]

CODE_TO_TITLE = {o["code"]: o["title"] for o in OCCUPATIONS}
DEFAULT_CODE = "00-0000"

# Verb cues that distinguish "do it for me" (automation) from "help me do it" (augmentation).
AUTOMATION_CUES = ["write", "generate", "create", "make", "build", "translate", "fix", "do ", "produce",
                   "draft", "code", "compose", "design", "summarize", "convert", "rewrite", "give me", "reply to"]
AUGMENTATION_CUES = ["explain", "help me understand", "how do", "how can", "what is", "what are", "review",
                     "feedback", "improve my", "check my", "teach me", "learn", "why ", "critique", "advice"]


def occupation_codes() -> list[str]:
    return [o["code"] for o in OCCUPATIONS]
