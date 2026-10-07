#!/usr/bin/env python3
"""Automated Evals & Benchmark Runner for Vaeloom Career Skills.

Executes test evaluation cases defined in evals/eval_cases.json against
the respective skill evaluation engines and asserts behavioral accuracy.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "skills" / "ats-audit" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "resume-optimization" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "salary-negotiation-playbook" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "star-interview-prep" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "linkedin-profile-optimizer" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "linkedin-humanizer" / "scripts"))

sys.path.insert(0, str(REPO_ROOT / "skills" / "job-discovery-radar" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "linkedin-interviewer" / "scripts"))

from ats_checker import check_ats_compliance
from xyz_scorer import score_bullet
from comp_calculator import calculate_total_comp
from star_validator import audit_star_story
from headline_lint import lint_headline
from humanize import pass_lexical, load_lexicon
from lib.url_parser import parse_linkedin_url
from portal_scanner import is_ssrf_safe, analyze_career_url
from story_bank_validator import validate_story_bank


# Assertion types each skill's evaluation engine actually implements.
#
# This registry exists because the runner's if/elif chains had no catch-all: an
# assertion type the chain did not recognise fell straight through and the case
# was reported PASS. Verified by adding a case asserting
# ``{"type": "rule_violation_typoed"}`` -- 17/17 passed, exit 0. A typo, a
# rename, or a case written against a skill whose branch does not exist would
# therefore assert nothing and go green, which is worse than having no eval.
#
# Every case is validated against this before a single rollout runs, so a
# misspelled assertion is a hard failure that names the skill and the type.
HANDLED_ASSERTIONS: dict[str, frozenset[str]] = {
    "ats-audit": frozenset({
        "rule_violation_triggered", "no_rule_violation", "score_below", "score_above",
    }),
    "resume-optimization": frozenset({
        "passive_phrase_detected", "missing_metric_detected", "rating_equals",
        "score_above", "score_below",
    }),
    "salary-negotiation-playbook": frozenset({
        "expected_year_1_tc", "expected_steady_state_tc",
    }),
    "star-interview-prep": frozenset({
        "we_trap_detected", "status_not_equals",
    }),
    "linkedin-profile-optimizer": frozenset({
        "headline_valid", "score_above", "parsed_url_type", "parsed_activity_id",
    }),
    "linkedin-humanizer": frozenset({
        "slop_scrubbed", "facts_preserved",
    }),
    "job-discovery-radar": frozenset({
        "ssrf_blocked", "ssrf_allowed", "career_url_verified", "career_url_rejected",
    }),
    "linkedin-interviewer": frozenset({
        "story_bank_valid", "story_bank_score_above", "story_bank_missing_sections",
    }),
}


def validate_cases(cases: list[dict]) -> list[str]:
    """Return a list of contract violations. Empty means the suite is runnable."""
    problems: list[str] = []
    seen_ids: dict[str, int] = {}

    for case in cases:
        cid = case.get("id", "<missing id>")
        seen_ids[cid] = seen_ids.get(cid, 0) + 1

        skill = case.get("skill")
        if skill not in HANDLED_ASSERTIONS:
            problems.append(
                f"{cid}: skill {skill!r} has no evaluation branch in run_evals.py "
                f"(known: {sorted(HANDLED_ASSERTIONS)})"
            )
            continue

        assertions = case.get("assertions")
        if not assertions:
            # Covers both a missing key and an empty list: a case with nothing to
            # check would be reported PASS, which is the failure mode the whole
            # registry exists to prevent.
            problems.append(f"{cid}: case declares no assertions; it cannot fail")
            continue

        for assertion in assertions:
            atype = assertion.get("type")
            if atype not in HANDLED_ASSERTIONS[skill]:
                problems.append(
                    f"{cid}: assertion type {atype!r} is not implemented for {skill!r}. "
                    f"Implemented: {sorted(HANDLED_ASSERTIONS[skill])}. An unrecognised "
                    f"type is reported as PASS, so this case would assert nothing."
                )

    for cid, count in sorted(seen_ids.items()):
        if count > 1:
            problems.append(f"{cid}: id appears {count} times; ids must be unique")
    return problems


def run_evals() -> int:
    cases_file = REPO_ROOT / "evals" / "eval_cases.json"
    if not cases_file.is_file():
        print(f"Error: {cases_file} not found", file=sys.stderr)
        return 1

    cases = json.loads(cases_file.read_text(encoding="utf-8"))
    passed = 0
    failed = 0

    problems = validate_cases(cases)
    if problems:
        print("==================================================")
        print("      VAELOOM CAREER SKILLS EVALS HARNESS        ")
        print("==================================================")
        print(f"[FATAL] {len(problems)} eval contract violation(s); nothing was run:\n")
        for p in problems:
            print(f"  - {p}")
        print("-" * 50)
        print(f"Eval Results: 0/{len(cases)} Passed (0.0% Accuracy)")
        print("==================================================")
        return 1

    print("==================================================")
    print("      VAELOOM CAREER SKILLS EVALS HARNESS        ")
    print("==================================================")

    for case in cases:
        case_id = case["id"]
        name = case["name"]
        skill = case["skill"]
        case_passed = True
        failure_reasons = []

        try:
            if skill == "ats-audit":
                res = check_ats_compliance(case["input"])
                for a in case["assertions"]:
                    if a["type"] == "rule_violation_triggered":
                        if not any(v["type"] == a["rule"] for v in res["violations"]):
                            case_passed = False
                            failure_reasons.append(f"Expected rule violation '{a['rule']}' not triggered")
                    elif a["type"] == "no_rule_violation":
                        # Negative control: a compliant document must NOT be
                        # flagged. Without these the suite only proves the
                        # checker can complain, never that it can stay quiet.
                        if any(v["type"] == a["rule"] for v in res["violations"]):
                            case_passed = False
                            failure_reasons.append(
                                f"Rule violation '{a['rule']}' fired on a compliant document: "
                                f"{[v['message'] for v in res['violations'] if v['type'] == a['rule']]}"
                            )
                    elif a["type"] == "score_below":
                        if res["score"] >= a["threshold"]:
                            case_passed = False
                            failure_reasons.append(f"Expected score < {a['threshold']}, got {res['score']}")
                    elif a["type"] == "score_above":
                        if res["score"] < a["threshold"]:
                            case_passed = False
                            failure_reasons.append(f"Expected score >= {a['threshold']}, got {res['score']}")

            elif skill == "resume-optimization":
                res = score_bullet(case["input"])
                for a in case["assertions"]:
                    if a["type"] == "passive_phrase_detected":
                        if not any(a["phrase"] in iss.lower() for iss in res["issues"]):
                            case_passed = False
                            failure_reasons.append(f"Expected passive phrase '{a['phrase']}' not detected")
                    elif a["type"] == "missing_metric_detected":
                        if res["has_metric"] != (not a["expected"]):
                            case_passed = False
                            failure_reasons.append(f"Expected missing metric: {a['expected']}, got {res['has_metric']}")
                    elif a["type"] == "rating_equals":
                        if res["rating"] != a["rating"]:
                            case_passed = False
                            failure_reasons.append(f"Expected rating {a['rating']}, got {res['rating']}")
                    elif a["type"] == "score_above":
                        if res["score"] < a["threshold"]:
                            case_passed = False
                            failure_reasons.append(f"Expected score >= {a['threshold']}, got {res['score']}")
                    elif a["type"] == "score_below":
                        if res["score"] >= a["threshold"]:
                            case_passed = False
                            failure_reasons.append(f"Expected score < {a['threshold']}, got {res['score']}")

            elif skill == "salary-negotiation-playbook":
                inp = case["input"]
                res = calculate_total_comp(
                    base=inp["base"],
                    bonus_pct=inp["bonus_pct"],
                    rsu_grant_value=inp["equity"],
                    vesting_years=inp["years"],
                    signing_bonus=inp["signing"],
                )
                for a in case["assertions"]:
                    if a["type"] == "expected_year_1_tc":
                        got = res["annualized"]["year_1_total_compensation"]
                        if got != a["expected"]:
                            case_passed = False
                            failure_reasons.append(f"Expected Year 1 TC {a['expected']}, got {got}")
                    elif a["type"] == "expected_steady_state_tc":
                        got = res["annualized"]["steady_state_total_compensation"]
                        if got != a["expected"]:
                            case_passed = False
                            failure_reasons.append(f"Expected Steady State TC {a['expected']}, got {got}")

            elif skill == "star-interview-prep":
                res = audit_star_story(case["input"])
                for a in case["assertions"]:
                    if a["type"] == "we_trap_detected":
                        got = res["agency_counts"]["we_trap_detected"]
                        if got != a["expected"]:
                            case_passed = False
                            failure_reasons.append(f"Expected we_trap_detected {a['expected']}, got {got}")
                    elif a["type"] == "status_not_equals":
                        if res["status"] == a["status"]:
                            case_passed = False
                            failure_reasons.append(f"Expected status != {a['status']}, got {res['status']}")

            elif skill == "linkedin-profile-optimizer":
                if case["input_type"] == "headline":
                    res = lint_headline(case["input"])
                    for a in case["assertions"]:
                        if a["type"] == "headline_valid":
                            if res["valid"] != a["expected"]:
                                case_passed = False
                                failure_reasons.append(f"Expected valid {a['expected']}, got {res['valid']} ({res['issues']})")
                        elif a["type"] == "score_above":
                            if res["score"] < a["threshold"]:
                                case_passed = False
                                failure_reasons.append(f"Expected score >= {a['threshold']}, got {res['score']}")
                elif case["input_type"] == "url":
                    parsed = parse_linkedin_url(case["input"])
                    for a in case["assertions"]:
                        if a["type"] == "parsed_url_type":
                            if parsed["url_type"] != a["expected"]:
                                case_passed = False
                                failure_reasons.append(f"Expected url_type {a['expected']}, got {parsed['url_type']}")
                        elif a["type"] == "parsed_activity_id":
                            if parsed["post_activity_id"] != a["expected"]:
                                case_passed = False
                                failure_reasons.append(f"Expected activity_id {a['expected']}, got {parsed['post_activity_id']}")

            elif skill == "linkedin-humanizer":
                lex = load_lexicon()
                cleaned, hits = pass_lexical(case["input"], lex)
                for a in case["assertions"]:
                    if a["type"] == "slop_scrubbed":
                        for bw in a["banned_words"]:
                            if bw in cleaned.lower():
                                case_passed = False
                                failure_reasons.append(f"Banned word '{bw}' still present in cleaned text: '{cleaned}'")
                    elif a["type"] == "facts_preserved":
                        for fact in a["required_facts"]:
                            if fact not in cleaned:
                                case_passed = False
                                failure_reasons.append(f"Required fact '{fact}' dropped from cleaned text: '{cleaned}'")

            elif skill == "linkedin-interviewer":
                res = validate_story_bank(case["input"])
                for a in case["assertions"]:
                    if a["type"] == "story_bank_valid":
                        if res["valid"] != a["expected"]:
                            case_passed = False
                            failure_reasons.append(
                                f"Expected valid={a['expected']}, got {res['valid']} "
                                f"(missing sections: {res['missing_sections']})"
                            )
                    elif a["type"] == "story_bank_score_above":
                        if res["score"] < a["threshold"]:
                            case_passed = False
                            failure_reasons.append(
                                f"Expected story bank score > {a['threshold']}, got {res['score']}"
                            )
                    elif a["type"] == "story_bank_missing_sections":
                        if not res["missing_sections"]:
                            case_passed = False
                            failure_reasons.append(
                                "Expected missing_sections to be reported, got none"
                            )

            elif skill == "job-discovery-radar":
                for a in case["assertions"]:
                    if a["type"] in ("ssrf_allowed", "ssrf_blocked"):
                        host = a["host"]
                        allowed, reason = is_ssrf_safe(host)
                        if a["type"] == "ssrf_allowed" and not allowed:
                            case_passed = False
                            failure_reasons.append(
                                f"Host '{host}' should be allowed but was blocked: {reason}"
                            )
                        if a["type"] == "ssrf_blocked" and allowed:
                            case_passed = False
                            failure_reasons.append(
                                f"SSRF: host '{host}' was ALLOWED but must be blocked "
                                f"(loopback, link-local and cloud metadata targets)"
                            )
                        if a["type"] == "ssrf_blocked" and not reason:
                            case_passed = False
                            failure_reasons.append(
                                f"Blocked host '{host}' gave no reason; a denial must be explainable"
                            )
                    elif a["type"] in ("career_url_verified", "career_url_rejected"):
                        res = analyze_career_url(case["input"])
                        rejected = res.get("status") == "REJECTED"
                        if a["type"] == "career_url_rejected" and not rejected:
                            case_passed = False
                            failure_reasons.append(
                                f"URL {case['input']!r} should be REJECTED, got {res.get('status')}"
                            )
                        if a["type"] == "career_url_verified" and rejected:
                            case_passed = False
                            failure_reasons.append(
                                f"URL {case['input']!r} should verify, got {res.get('status')}: "
                                f"{res.get('error')}"
                            )

            if case_passed:
                print(f"[PASS] {case_id}: {name}")
                passed += 1
            else:
                print(f"[FAIL] {case_id}: {name}")
                for r in failure_reasons:
                    print(f"       -> {r}")
                failed += 1

        except Exception as e:
            print(f"[ERROR] {case_id}: {name} - Exception: {e}")
            failed += 1

    total = passed + failed
    accuracy = (passed / total * 100.0) if total > 0 else 0.0
    print("--------------------------------------------------")
    print(f"Eval Results: {passed}/{total} Passed ({accuracy:.1f}% Accuracy)")
    print("==================================================")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_evals())
