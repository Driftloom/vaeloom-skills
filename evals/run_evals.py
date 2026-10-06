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
sys.path.insert(0, str(REPO_ROOT / "skills" / "ats-audit" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "resume-optimization" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "salary-negotiation-playbook" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "star-interview-prep" / "scripts"))

from ats_checker import check_ats_compliance
from xyz_scorer import score_bullet
from comp_calculator import calculate_total_comp
from star_validator import audit_star_story


def run_evals() -> int:
    cases_file = REPO_ROOT / "evals" / "eval_cases.json"
    if not cases_file.is_file():
        print(f"Error: {cases_file} not found", file=sys.stderr)
        return 1

    cases = json.loads(cases_file.read_text(encoding="utf-8"))
    passed = 0
    failed = 0

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
                    elif a["type"] == "score_below":
                        if res["score"] >= a["threshold"]:
                            case_passed = False
                            failure_reasons.append(f"Expected score < {a['threshold']}, got {res['score']}")

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
