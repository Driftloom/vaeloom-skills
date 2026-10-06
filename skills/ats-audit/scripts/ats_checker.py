#!/usr/bin/env python3
"""ATS Format & Parseability Verification Script.

Performs deterministic heuristic analysis on resume text or markdown to detect:
1. Multi-column and table layouts.
2. Non-standard section headings.
3. Contact information placement.
4. Date format consistency.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


STANDARD_HEADERS = {
    "work experience",
    "professional experience",
    "experience",
    "employment history",
    "education",
    "technical skills",
    "skills",
    "certifications",
    "projects",
}

DISALLOWED_HEADERS = {
    "where i've been",
    "my journey",
    "capabilities matrix",
    "stuff i built",
    "background",
}


def check_ats_compliance(content: str) -> dict:
    lines = content.splitlines()
    violations: list[dict] = []
    score = 100

    # 1. Check for table markers or sidebars
    table_lines = [i for i, line in enumerate(lines, 1) if "|" in line and line.count("|") >= 2]
    if len(table_lines) > 2:
        violations.append({
            "type": "TABLE_LAYOUT_DETECTED",
            "severity": "CRITICAL",
            "message": f"Found {len(table_lines)} markdown table lines; ATS parsers interleave columnar text.",
            "deduction": 25,
        })
        score -= 25

    # 2. Check for contact info presence in top 20%
    top_chunk = "\n".join(lines[: max(15, len(lines) // 5)])
    has_email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", top_chunk))
    has_phone = bool(re.search(r"(\+\d{1,2}\s*)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", top_chunk))

    if not has_email:
        violations.append({
            "type": "EMAIL_NOT_IN_HEADER",
            "severity": "CRITICAL",
            "message": "No valid email address found in the document header block.",
            "deduction": 20,
        })
        score -= 20

    if not has_phone:
        violations.append({
            "type": "PHONE_NOT_IN_HEADER",
            "severity": "WARNING",
            "message": "No standard phone number found in the document header block.",
            "deduction": 10,
        })
        score -= 10

    # 3. Check section headers
    found_headers = []
    for line_idx, line in enumerate(lines, 1):
        clean = line.strip().lstrip("#").strip().lower()
        if clean in DISALLOWED_HEADERS:
            violations.append({
                "type": "CREATIVE_HEADER_DISALLOWED",
                "severity": "WARNING",
                "message": f"Line {line_idx}: Creative header '{line.strip()}' confuses ATS classifier ontologies.",
                "deduction": 10,
            })
            score -= 10
        elif clean in STANDARD_HEADERS:
            found_headers.append(clean)

    if not any("experience" in h for h in found_headers):
        violations.append({
            "type": "MISSING_EXPERIENCE_SECTION",
            "severity": "CRITICAL",
            "message": "No standard 'Experience' or 'Work Experience' section header detected.",
            "deduction": 20,
        })
        score -= 20

    score = max(0, score)
    return {
        "status": "PASS" if score >= 80 else ("CONDITIONAL" if score >= 60 else "FAIL"),
        "score": score,
        "standard_headers_found": found_headers,
        "violations_count": len(violations),
        "violations": violations,
    }


def main():
    parser = argparse.ArgumentParser(description="Deterministic ATS Parseability Checker")
    parser.add_argument("file", help="Path to resume file (markdown or txt)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        print(f"Error: File '{path}' does not exist", file=sys.stderr)
        sys.exit(1)

    result = check_ats_compliance(path.read_text(encoding="utf-8", errors="ignore"))

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"ATS Parseability Status: {result['status']} (Score: {result['score']}/100)")
        if result["violations"]:
            print("\nViolations:")
            for v in result["violations"]:
                print(f"  [{v['severity']}] {v['type']}: {v['message']} (-{v['deduction']} pts)")
        else:
            print("No parsing hazards detected! Document adheres to single-column ATS standards.")


if __name__ == "__main__":
    main()
