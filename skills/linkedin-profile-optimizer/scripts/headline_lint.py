#!/usr/bin/env python3
"""
headline_lint.py - Lint and evaluate LinkedIn headlines.

Validates:
1. Character limit: <= 220 chars
2. Formula: [What You Do] | [Who You Help] [Result / Context]
3. Prohibited buzzwords: passionate, driven, results-oriented, thought leader
4. Emoji traps: rocket, fire, bulb chains
5. Search keywords: identifies specific role and domain keywords
"""
import re
import sys
from typing import Dict, Any, List

BANNED_BUZZWORDS = [
    "passionate", "driven", "results-oriented", "thought leader", 
    "guru", "ninja", "rockstar", "dynamic", "synergistic", "visionary"
]
EMOJI_TRAPS = re.compile(r"[\U0001F680\U0001F525\U0001F4A1\u2728\U0001F3AF]{2,}")

def lint_headline(headline: str) -> Dict[str, Any]:
    text = headline.strip()
    length = len(text)
    issues: List[str] = []
    suggestions: List[str] = []
    strengths: List[str] = []

    # 1. Length check
    if length == 0:
        return {"valid": False, "score": 0, "length": 0, "issues": ["Headline is empty"], "suggestions": [], "strengths": []}
    
    if length > 220:
        issues.append(f"Exceeds 220 character limit ({length}/220 characters).")
    elif length >= 120:
        strengths.append(f"Good utilization of character budget ({length}/220 characters).")
    else:
        suggestions.append(f"Under-utilizing character budget ({length}/220 characters). Aim for 120-200 characters.")

    # 2. Formula structure (pipe or bullet separation)
    parts = [p.strip() for p in re.split(r"[|\u2022\u00b7]", text) if p.strip()]
    if len(parts) >= 2:
        strengths.append(f"Uses structured multi-part formula ({len(parts)} parts).")
    else:
        issues.append("Lacks structured separator ('|'). Use: [What You Do] | [Who You Help] [Result].")

    # 3. Buzzwords
    lower = text.lower()
    found_buzzwords = [bw for bw in BANNED_BUZZWORDS if bw in lower]
    if found_buzzwords:
        issues.append(f"Contains empty buzzwords: {', '.join(found_buzzwords)}. Replace with proof.")

    # 4. Emoji traps
    if EMOJI_TRAPS.search(text):
        issues.append("Contains emoji chains (e.g. 🚀🔥). Limit to max 1 subtle separator emoji.")

    # 5. Proof / metrics
    has_numbers = bool(re.search(r"\b\d+[%kKmMbB]?\b|\$\d+", text))
    if has_numbers:
        strengths.append("Contains concrete metrics or scale indicators.")
    else:
        suggestions.append("No numbers or concrete scale markers found. Include measurable impact.")

    # Score calculation (0-100)
    score = 100
    if length > 220:
        score -= 40
    elif length < 80:
        score -= 15
    if len(parts) < 2:
        score -= 20
    if found_buzzwords:
        score -= 20 * len(found_buzzwords)
    if not has_numbers:
        score -= 10
    if EMOJI_TRAPS.search(text):
        score -= 15
    
    score = max(0, min(100, score))
    return {
        "valid": len(issues) == 0,
        "score": score,
        "length": length,
        "parts_count": len(parts),
        "issues": issues,
        "suggestions": suggestions,
        "strengths": strengths
    }

if __name__ == "__main__":
    test_headline = sys.argv[1] if len(sys.argv) > 1 else "Senior Software Engineer | Building Scalable RAG Systems at Scale | $10M ARR Impact"
    res = lint_headline(test_headline)
    print(f"Headline: '{test_headline}'")
    print(f"Score: {res['score']}/100 | Length: {res['length']}/220 | Valid: {res['valid']}")
    if res["issues"]:
        print("Issues:")
        for iss in res["issues"]:
            print(f"  - {iss}")
    if res["suggestions"]:
        print("Suggestions:")
        for sg in res["suggestions"]:
            print(f"  ~ {sg}")
    if res["strengths"]:
        print("Strengths:")
        for st in res["strengths"]:
            print(f"  + {st}")
