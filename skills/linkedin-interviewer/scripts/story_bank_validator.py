#!/usr/bin/env python3
"""
story_bank_validator.py - Validates Career Story Bank completeness and integrity.

Ensures:
1. Required sections exist: Roles, Receipts, Turning Points, Defended Positions.
2. Receipts contain verifiable numbers or metrics.
3. No unresolved placeholder tokens.
4. Identifies thin sections requiring further interview probing.
"""
import re
import sys
from typing import Dict, Any, List

REQUIRED_SECTIONS = [
    "roles & scopes",
    "receipts",
    "turning points",
    "defended positions"
]

def validate_story_bank(text: str) -> Dict[str, Any]:
    lines = text.splitlines()
    lower_text = text.lower()
    
    missing_sections = []
    for sec in REQUIRED_SECTIONS:
        if sec not in lower_text:
            missing_sections.append(sec)

    # Check for concrete figures/metrics
    numbers_found = re.findall(r"\b\d+[%kKmMbB]?\b|\$\d+", text)
    
    # Check for placeholder tokens
    placeholders = re.findall(r"\{\{[^}]+\}\}|<[^>]+>", text)

    # Check section thickness
    thin_sections = []
    if "receipts" in lower_text and len(numbers_found) < 3:
        thin_sections.append("Receipts contains fewer than 3 concrete metrics.")
    if "turning points" in lower_text and len(re.findall(r"(scar|mistake|wrong|downtime|failure)", lower_text)) == 0:
        thin_sections.append("Turning Points lacks specific failure or learning moments.")

    is_valid = (len(missing_sections) == 0) and (len(numbers_found) >= 3) and (len(placeholders) == 0)

    score = 100
    if missing_sections:
        score -= 25 * len(missing_sections)
    if len(numbers_found) < 3:
        score -= 20
    if placeholders:
        score -= 15 * len(placeholders)
    score = max(0, min(100, score))

    return {
        "valid": is_valid,
        "score": score,
        "metrics_count": len(numbers_found),
        "missing_sections": missing_sections,
        "placeholders": placeholders,
        "thin_sections": thin_sections
    }

if __name__ == "__main__":
    test_text = sys.stdin.read() if not sys.stdin.isatty() else open(sys.argv[1]).read() if len(sys.argv) > 1 else ""
    if not test_text:
        print("Usage: python story_bank_validator.py <path/to/story_bank.md>")
        sys.exit(1)
    res = validate_story_bank(test_text)
    print(f"Story Bank Valid: {res['valid']} | Score: {res['score']}/100 | Metrics: {res['metrics_count']}")
    if res["missing_sections"]:
        print(f"Missing sections: {res['missing_sections']}")
    if res["thin_sections"]:
        print(f"Thin sections: {res['thin_sections']}")
