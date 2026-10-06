#!/usr/bin/env python3
"""Google XYZ Resume Bullet Quality Scorer.

Analyzes individual bullet points or full resume files against the Google XYZ formula:
Accomplished [X] as measured by [Y] by doing [Z].
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BANNED_PASSIVE = [
    r"\bresponsible for\b",
    r"\bassisted with\b",
    r"\bworked on\b",
    r"\btasked with\b",
    r"\bhelped team\b",
    r"\bparticipated in\b",
    r"\binvolved in\b",
]

METRIC_PATTERNS = [
    r"\b\d+(\.\d+)?%\b",                 # percentages e.g. 38%
    r"\$\d+([,\.]\d+)?([KkMmBb])?\b",    # currency e.g. $180,000, $1.4M
    r"\b\d+([,\.]\d+)?[KkMmBb]\+?\b",    # quantities e.g. 5M+, 120k
    r"\b\d+\s*(ms|seconds?|minutes?|hours?|days?)\b", # time latency
    r"\b\d+x\b",                         # multipliers e.g. 8x
]

STRONG_VERBS = {
    "architected", "engineered", "designed", "orchestrated", "spearheaded",
    "deployed", "optimized", "accelerated", "streamlined", "benchmarked",
    "scaled", "slashed", "consolidated", "monetized", "yielded",
    "formulated", "diagnosed", "automated", "synthesized", "directed",
    "championed", "mobilized", "mentored", "standardized", "instituted",
}


def score_bullet(bullet: str) -> dict:
    text = bullet.strip().lstrip("•-* ").strip()
    words = text.split()
    issues: list[str] = []
    score = 100

    if not words:
        return {"score": 0, "issues": ["Empty bullet"], "has_metric": False, "strong_verb": False}

    # 1. Check for banned passive phrasing
    lowered = text.lower()
    for pattern in BANNED_PASSIVE:
        if re.search(pattern, lowered):
            issues.append(f"Passive responsibility phrase detected matching '{pattern}'. Use an active power verb.")
            score -= 30
            break

    # 2. Check first word (Active Action Verb)
    first_word = re.sub(r"[^\w]", "", words[0].lower())
    if first_word not in STRONG_VERBS:
        score -= 20
        issues.append(f"Opening word '{words[0]}' is not a recognized high-agency Tier-1 action verb.")

    # 3. Check for measurable metrics [Y]
    has_metric = any(bool(re.search(pat, text, re.IGNORECASE)) for pat in METRIC_PATTERNS)
    if not has_metric:
        score -= 30
        issues.append("Missing quantified metric [Y] (e.g. % reduction, latency ms, $ savings, or user scale).")

    # 4. Check word count (Brevity & Density)
    if len(words) < 12:
        score -= 15
        issues.append("Bullet is too brief (< 12 words); lacks technical context [Z] or business problem [X].")
    elif len(words) > 50:
        score -= 10
        issues.append("Bullet is too long (> 50 words); split into two distinct achievements.")

    score = max(0, score)
    return {
        "bullet": text,
        "score": score,
        "rating": "EXCELLENT" if score >= 85 else ("GOOD" if score >= 65 else "NEEDS_REVISION"),
        "has_metric": has_metric,
        "opening_verb": words[0] if words else "",
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Google XYZ Resume Bullet Quality Scorer")
    parser.add_argument("bullet_or_file", help="A single bullet string or path to a text file")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    target = args.bullet_or_file
    path = Path(target)
    bullets = []

    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            clean = line.strip().lstrip("•-* ")
            if clean and len(clean.split()) >= 4:
                bullets.append(clean)
    else:
        bullets.append(target)

    results = [score_bullet(b) for b in bullets]

    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2))
    else:
        for r in results:
            print(f"\nBullet: {r['bullet']}")
            print(f"Score: {r['score']}/100 [{r['rating']}]")
            if r["issues"]:
                print("Recommendations:")
                for iss in r["issues"]:
                    print(f"  - {iss}")


if __name__ == "__main__":
    main()
