from __future__ import annotations

import re
from importlib import resources

DOCS: dict[str, dict] = {
    "overview": {
        "title": "Package Overview",
        "summary": "What raiffa does, when to use it, core concepts, and output format.",
        "file": "overview.md",
    },
    "getting-started": {
        "title": "Getting Started",
        "summary": "Complete worked example: init, tree construction, solve, sensitivity, and VOI.",
        "file": "getting-started.md",
    },
    "workflow": {
        "title": "Decision Analysis Workflow",
        "summary": "Phase-by-phase guide from decision framing through export.",
        "file": "workflow.md",
    },
    "best-practices": {
        "title": "Best Practices",
        "summary": "Elicitation guidance, tree design standards, common pitfalls, and quality checklist.",
        "file": "best-practices.md",
    },
    "cli-reference": {
        "title": "CLI Quick Reference",
        "summary": "All commands with syntax, flags, and examples.",
        "file": "cli-reference.md",
    },
}


def load_doc(topic: str) -> str:
    meta = DOCS[topic]
    pkg = resources.files("raiffa").joinpath("docs_content")
    return pkg.joinpath(meta["file"]).read_text(encoding="utf-8")


def search_docs(query: str) -> list[dict]:
    terms = re.findall(r"[A-Za-z0-9_-]+", query.lower())
    results = []
    for topic, meta in DOCS.items():
        text = load_doc(topic)
        haystack = f"{topic} {meta['title']} {meta['summary']} {text}".lower()
        score = sum(haystack.count(t) for t in terms)
        if score > 0:
            snippet = ""
            for term in terms:
                idx = haystack.find(term)
                if idx >= 0:
                    start = max(0, idx - 90)
                    end = min(len(text), idx + 200)
                    snippet = text[start:end].strip()
                    break
            results.append({**meta, "topic": topic, "score": score, "snippet": snippet})
    return sorted(results, key=lambda r: r["score"], reverse=True)
