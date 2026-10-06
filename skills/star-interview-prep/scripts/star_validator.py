#!/usr/bin/env python3
"""STAR Story Structure & Agency Validator.

Audits behavioral interview responses to ensure:
1. Complete STAR structure (Situation, Task, Action, Result).
2. Elimination of the "We Trap" (verifies high "I" individual agency).
3. Metric verification in the Result section.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def audit_star_story(text: str) -> dict:
    lowered = text.lower()
    words = re.findall(r"\b[a-zA-Z']+\b", lowered)

    # 1. Check section presence
    has_situation = "situation" in lowered or "context" in lowered
    has_task = "task" in lowered or "mandate" in lowered or "responsibility" in lowered
    has_action = "action" in lowered or "i did" in lowered or "i built" in lowered or "i engineered" in lowered
    has_result = "result" in lowered or "outcome" in lowered or "impact" in lowered

    sections_found = {
        "situation": has_situation,
        "task": has_task,
        "action": has_action,
        "result": has_result,
    }

    # 2. Check "We" vs "I" Agency
    i_count = len(re.findall(r"\b(i|my|mine|myself)\b", lowered))
    we_count = len(re.findall(r"\b(we|our|us|team)\b", lowered))

    agency_ratio = (i_count / (we_count + 1e-5)) if we_count > 0 else float(i_count)
    we_trap = we_count > (i_count * 1.5) and we_count >= 4

    # 3. Check for quantified metrics in the text
    metrics = re.findall(r"\b\d+(\.\d+)?%|\$\d+[,\d]*|\b\d+\s*(ms|seconds|minutes|hours|days|users|orders)\b", lowered)

    issues: list[str] = []
    score = 100

    if not all(sections_found.values()):
        missing = [k for k, v in sections_found.items() if not v]
        issues.append(f"Missing distinct STAR component(s): {', '.join(missing)}")
        score -= 25

    if we_trap:
        issues.append(
            f"Candidate fell into the 'We Trap': used 'we/our/team' {we_count} times vs 'I/my' {i_count} times. "
            "Bar Raisers will probe for individual contribution."
        )
        score -= 30

    if not metrics:
        issues.append("Result section lacks quantified metrics (% improvement, latency drop, $ savings).")
        score -= 20

    score = max(0, score)
    return {
        "status": "PASS" if score >= 80 else ("NEEDS_WORK" if score >= 60 else "FAIL"),
        "score": score,
        "agency_counts": {
            "first_person_singular_i": i_count,
            "first_person_plural_we": we_count,
            "we_trap_detected": we_trap,
        },
        "sections_detected": sections_found,
        "metric_count": len(metrics),
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="STAR Behavioral Story Validator")
    parser.add_argument("file_or_text", help="Path to text/markdown file or raw story string")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    target = args.file_or_text
    path = Path(target)
    content = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else target

    result = audit_star_story(content)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"STAR Audit Status: {result['status']} (Score: {result['score']}/100)")
        print(f"Agency Breakdown: 'I' mentions: {result['agency_counts']['first_person_singular_i']}, 'We' mentions: {result['agency_counts']['first_person_plural_we']}")
        if result["issues"]:
            print("\nCoaching Feedback:")
            for issue in result["issues"]:
                print(f"  - {issue}")


if __name__ == "__main__":
    main()
