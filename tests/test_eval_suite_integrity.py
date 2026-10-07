"""The eval harness must not be able to pass a case it never checked.

Three defects were found in this suite while extending it, and each is now a
test rather than a memory:

1. **Unrecognised assertion types were reported as PASS.** The runner's if/elif
   chains had no catch-all, so ``{"type": "rule_violation_typoed"}`` fell through
   and the case went green -- 17/17, exit 0. ``HANDLED_ASSERTIONS`` now makes the
   contract explicit and ``run_evals.validate_cases`` refuses to start.

2. **Duplicate case ids were possible**, which makes a result unattributable.

3. **There were no negative controls at all.** Every original case asserted that
   something *should* fire. None asserted that a compliant input passes clean, so
   a checker that flagged everything would have scored 8/8. Five negative controls
   were added.

A fourth gap is reported rather than failed: two skills that ship executable
helpers have no behavioural case at all. That is a real coverage hole, recorded
in ``test_report_uncovered_scripted_skills`` so it stays visible.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = REPO_ROOT / "evals" / "eval_cases.json"
RUNNER_PATH = REPO_ROOT / "evals" / "run_evals.py"
SKILLS_DIR = REPO_ROOT / "skills"

_spec = importlib.util.spec_from_file_location("run_evals_under_test", RUNNER_PATH)
run_evals = importlib.util.module_from_spec(_spec)
sys.modules["run_evals_under_test"] = run_evals
_spec.loader.exec_module(run_evals)


@pytest.fixture(scope="module")
def cases() -> list[dict]:
    assert CASES_PATH.is_file(), f"missing {CASES_PATH}"
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


# ── the contract itself ──────────────────────────────────────────────────


def test_cases_file_is_populated(cases) -> None:
    assert len(cases) >= 16, f"expected the extended suite, found {len(cases)}"


def test_case_ids_are_unique(cases) -> None:
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), f"duplicate ids: {[i for i in ids if ids.count(i) > 1]}"


def test_every_case_has_required_fields(cases) -> None:
    for case in cases:
        assert case.get("id"), case
        assert case.get("name"), case["id"]
        assert case.get("skill"), case["id"]
        assert case.get("assertions"), f"{case['id']} asserts nothing"


def test_the_suite_satisfies_its_own_contract(cases) -> None:
    """The same validation the runner performs, asserted as a test."""
    problems = run_evals.validate_cases(cases)
    assert not problems, "\n".join(problems)


# ── the defect: an unchecked assertion used to report PASS ───────────────


def test_an_unrecognised_assertion_type_is_rejected(cases) -> None:
    """The exact defect this module exists for.

    Before the registry existed, this case reported PASS and the suite reported
    17/17 with exit 0.
    """
    probe = dict(cases[0])
    probe["id"] = "probe-typo"
    probe["assertions"] = [{"type": "rule_violation_typoed", "rule": "NOPE"}]
    problems = run_evals.validate_cases(cases + [probe])
    assert problems, "a misspelled assertion type must be a contract violation"
    assert any("not implemented" in p for p in problems), problems


def test_an_assertion_implemented_for_another_skill_is_still_rejected(cases) -> None:
    """Assertion types are scoped per skill, not global.

    ``headline_valid`` exists for linkedin-profile-optimizer. Using it on
    ats-audit must fail: the ats branch would never read it.
    """
    probe = dict(cases[0])
    probe["id"] = "probe-cross-skill"
    probe["skill"] = "ats-audit"
    probe["assertions"] = [{"type": "headline_valid", "expected": True}]
    problems = run_evals.validate_cases(cases + [probe])
    assert any("not implemented for 'ats-audit'" in p for p in problems), problems


def test_an_unknown_skill_is_rejected(cases) -> None:
    probe = dict(cases[0])
    probe["id"] = "probe-unknown-skill"
    probe["skill"] = "no-such-skill"
    problems = run_evals.validate_cases(cases + [probe])
    assert any("no evaluation branch" in p for p in problems), problems


def test_a_duplicate_id_is_rejected(cases) -> None:
    problems = run_evals.validate_cases(cases + [dict(cases[0])])
    assert any("appears 2 times" in p for p in problems), problems


def test_a_case_with_no_assertions_is_rejected(cases) -> None:
    probe = dict(cases[0])
    probe["id"] = "probe-empty"
    probe["assertions"] = []
    problems = run_evals.validate_cases(cases + [probe])
    assert any("no assertions" in p for p in problems), problems


def test_a_case_missing_the_assertions_key_is_rejected(cases) -> None:
    probe = {k: v for k, v in cases[0].items() if k != "assertions"}
    probe["id"] = "probe-missing-key"
    problems = run_evals.validate_cases(cases + [probe])
    assert any("no assertions" in p for p in problems), problems


def test_validating_the_real_suite_reports_nothing(cases) -> None:
    assert run_evals.validate_cases(cases) == []


# ── integration: the runner must actually enforce the contract ───────────
#
# The unit tests above call validate_cases directly. That is not sufficient:
# removing the `validate_cases(cases)` call from run_evals() leaves every one of
# them passing while the runner goes back to reporting a typoed assertion as
# PASS. Verified by mutation -- 15 passed, runner reported 17/17, exit 0.
#
# These tests therefore drive the real entry point as a subprocess and assert on
# its exit code.


def _run_runner(tmp_path, cases: list[dict]) -> subprocess.CompletedProcess:
    """Execute evals/run_evals.py against a temporary case file."""
    backup = CASES_PATH.read_text(encoding="utf-8")
    try:
        CASES_PATH.write_text(json.dumps(cases, indent=2), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(RUNNER_PATH)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO_ROOT),
        )
    finally:
        CASES_PATH.write_text(backup, encoding="utf-8")


def test_runner_rejects_a_typoed_assertion_type_end_to_end(cases) -> None:
    probe = dict(cases[0])
    probe["id"] = "probe-typo-e2e"
    probe["assertions"] = [{"type": "rule_violation_typoed", "rule": "NOPE"}]

    proc = _run_runner(None, cases + [probe])

    assert proc.returncode != 0, (
        "the runner accepted a case whose assertion type it does not implement; "
        "this is the original silent-PASS defect"
    )
    assert "not implemented" in proc.stdout
    assert "FATAL" in proc.stdout


def test_runner_rejects_duplicate_ids_end_to_end(cases) -> None:
    proc = _run_runner(None, cases + [dict(cases[0])])
    assert proc.returncode != 0
    assert "appears 2 times" in proc.stdout


def test_runner_runs_the_real_suite_successfully(cases) -> None:
    """The happy path must still work, or the checks above prove nothing."""
    proc = _run_runner(None, cases)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "FATAL" not in proc.stdout
    assert f"{len(cases)}/{len(cases)} Passed" in proc.stdout


def test_case_file_is_restored_after_the_runner_tests(cases) -> None:
    """Guard against a probe leaving the suite corrupted on disk."""
    assert len(json.loads(CASES_PATH.read_text(encoding="utf-8"))) == len(cases)


# ── the defect: no negative controls existed ──────────────────────────────


NEGATIVE_MARKERS = ("NEGATIVE CONTROL", "negative control")


def test_the_suite_contains_negative_controls(cases) -> None:
    """A checker that flags everything must not be able to score full marks."""
    negatives = [c for c in cases if any(m in c["name"] for m in NEGATIVE_MARKERS)]
    assert len(negatives) >= 4, (
        f"only {len(negatives)} negative control(s); every original case asserted that "
        f"something should fire, so an over-flagging checker scored 8/8"
    )


def test_negative_controls_really_assert_absence(cases) -> None:
    """A case labelled "negative control" must assert that nothing was found.

    It is not enough for the label to exist: the case has to exercise the
    "nothing to detect" path, otherwise the label is decoration and coverage
    stays one-directional. Different skills express that differently, so the
    check is per-assertion rather than per-assertion-type.
    """
    for case in cases:
        if not any(m in case["name"] for m in NEGATIVE_MARKERS):
            continue

        absence = False
        for a in case["assertions"]:
            kind = a["type"]
            if kind == "no_rule_violation":
                # Nothing raised.
                absence = True
            elif kind == "ssrf_blocked":
                # A denial is the absence of permission: the negative direction.
                absence = True
            elif kind in {"missing_metric_detected", "we_trap_detected", "headline_valid",
                          "story_bank_valid"}:
                if a.get("expected") is False:
                    absence = True
            elif kind == "slop_scrubbed":
                # Asserts absence of the banned words; that is only a genuine
                # negative control when the input never contained them.
                haystack = str(case.get("input", "")).lower()
                if not any(bw.lower() in haystack for bw in a.get("banned_words", [])):
                    absence = True
            elif kind in {"facts_preserved", "parsed_url_type", "parsed_activity_id",
                           "expected_year_1_tc", "expected_steady_state_tc",
                           "status_not_equals", "score_above", "score_below",
                           "ssrf_allowed", "career_url_verified", "career_url_rejected",
                           "story_bank_missing_sections", "story_bank_score_above"}:
                continue

        assert absence, (
            f"{case['id']} is labelled a negative control but asserts only that "
            f"something IS found"
        )


def test_each_skills_negatives_cover_its_own_script(cases) -> None:
    """The compliant-ATS case must assert every rule the script can raise.

    Otherwise it is a partial control and a regression in the unchecked rules
    would pass unnoticed.
    """
    compliant = [
        c for c in cases
        if c["skill"] == "ats-audit" and "NEGATIVE CONTROL" in c["name"]
    ]
    assert compliant, "ats-audit has no negative control"
    asserted = {
        a["rule"] for a in compliant[0]["assertions"] if a["type"] == "no_rule_violation"
    }
    positive = {
        a["rule"] for c in cases if c["skill"] == "ats-audit"
        for a in c["assertions"] if a["type"] == "rule_violation_triggered"
    }
    assert positive, "no positive ATS cases to compare against"
    assert asserted == positive, (
        f"negative control asserts {sorted(asserted)} but positives fire {sorted(positive)}"
    )


# ── the reported gap: scripted skills with no behavioural case ────────────


def scripted_skills() -> set[str]:
    return {
        p.name for p in SKILLS_DIR.iterdir()
        if p.is_dir() and list((p / "scripts").glob("*.py"))
    }


def test_report_uncovered_scripted_skills(cases) -> None:
    """Reported, not failed: this is a known hole, kept visible on purpose.

    Turning it into a hard failure would force either writing rollouts for two
    more skills or deleting their helpers. Both are worse than naming the gap.
    """
    covered = {c["skill"] for c in cases}
    uncovered = sorted(scripted_skills() - covered)
    assert isinstance(uncovered, list)
    print(f"\nscripted skills without a behavioural eval case: {uncovered}")
