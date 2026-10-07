"""Layer 3 harness correctness -- and its honesty properties.

The harness is only worth building if three things are true:

1. **It is deterministic under the stub**, so CI can verify the plumbing with no
   credentials and no spend.
2. **It cannot manufacture a quality claim.** The stub is not a model; every
   result it produces must be marked synthetic, the summary must refuse to print
   a verdict, and no flag may convert a stub run into a claim.
3. **It refuses to degrade.** A live backend without credentials must exit
   non-zero. Silently falling back to the stub is the most dangerous behaviour
   this script could have: it would produce a fabricated quality score with a
   real-looking report.

One design defect was found and fixed while building this: the judge prompt
originally used the task input as both the "source text" and the "candidate
output", so it graded the input against a rubric written about outputs and
measured nothing. Generation is now a separate, required step.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
JUDGE_PATH = REPO_ROOT / "evals" / "layer3_judge.py"
TASKS_PATH = REPO_ROOT / "evals" / "layer3_tasks.json"

_spec = importlib.util.spec_from_file_location("layer3_under_test", JUDGE_PATH)
layer3 = importlib.util.module_from_spec(_spec)
sys.modules["layer3_under_test"] = layer3
_spec.loader.exec_module(layer3)


@pytest.fixture(scope="module")
def spec() -> dict:
    return json.loads(TASKS_PATH.read_text(encoding="utf-8"))


def run_cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    environ = dict(os.environ)
    # Never let a developer's real credentials leak into a harness self-check.
    for key in ("OPENAI_COMPATIBLE_BASE_URL", "OPENAI_COMPATIBLE_API_KEY",
                "OPENAI_COMPATIBLE_MODEL"):
        environ.pop(key, None)
    if env:
        environ.update(env)
    return subprocess.run(
        [sys.executable, str(JUDGE_PATH), *args],
        capture_output=True, text=True, timeout=180, cwd=str(REPO_ROOT), env=environ,
    )


# ── mechanical evidence ──────────────────────────────────────────────────


def test_detects_passive_voice_and_filler() -> None:
    ev = layer3.mechanical_evidence(
        "Responsible for leveraging synergies across the cutting-edge platform.",
        {"must_not_fabricate": False, "max_words": 60},
    )
    assert "responsible for" in ev["passive_markers"]
    assert "synergy" in ev["filler_terms"] or "leveraged" in ev["filler_terms"]
    assert ev["fabrication_risk"] is False


def test_fabrication_tripwire_fires_when_a_number_is_invented() -> None:
    """The highest-severity failure in resume writing: inventing a figure."""
    ev = layer3.mechanical_evidence(
        "Cut latency 45% across 14 services.",
        {"must_not_fabricate": True, "source_has_no_metric": True},
    )
    assert ev["contains_number"] is True
    assert ev["fabrication_risk"] is True


def test_a_number_from_the_source_is_not_fabrication() -> None:
    ev = layer3.mechanical_evidence(
        "Cut p99 latency 45% across 14 services.",
        {"must_not_fabricate": True, "source_has_no_metric": False},
    )
    assert ev["contains_number"] is True
    assert ev["fabrication_risk"] is False


def test_word_budget_is_enforced() -> None:
    long_text = "word " * 80
    assert layer3.mechanical_evidence(long_text, {"max_words": 40})["within_budget"] is False
    assert layer3.mechanical_evidence("short bullet", {"max_words": 40})["within_budget"] is True


# ── the prompt must judge the candidate, not the input ───────────────────


def test_prompt_scores_the_generated_candidate_not_the_input() -> None:
    """Regression guard for the defect where the judge graded the task input."""
    task = {"input": "Worked on reducing page load time.", "judge_question": "q?"}
    criterion = {"key": "agency", "label": "Explicit agency", "anchors": {"0": "passive", "10": "clear"}}
    ev = layer3.mechanical_evidence("candidate", {})

    prompt = layer3.build_prompt(task, criterion, ev, "I cut page load time in half.")

    assert "I cut page load time in half." in prompt
    assert "CANDIDATE OUTPUT (score this)" in prompt
    # The input must appear only as the source of truth, not as the thing scored.
    assert prompt.count("Worked on reducing page load time.") == 1


# ── the rubric must be anchored ──────────────────────────────────────────


def test_every_rubric_criterion_is_anchored_at_zero_five_and_ten(spec) -> None:
    for criterion in spec["rubric"]["criteria"]:
        anchors = criterion["anchors"]
        for level in ("0", "5", "10"):
            assert level in anchors, f"{criterion['key']} has no anchor at {level}"
            assert len(anchors[level].strip()) > 20, f"{criterion['key']}/{level} anchor is too vague"


def test_rubric_weights_sum_to_one(spec) -> None:
    total = sum(c["weight"] for c in spec["rubric"]["criteria"])
    assert abs(total - 1.0) < 1e-9, total


def test_truthfulness_carries_the_heaviest_weight(spec) -> None:
    """Fabrication is the most damaging failure in this domain."""
    weights = {c["key"]: c["weight"] for c in spec["rubric"]["criteria"]}
    assert weights["truthfulness"] == max(weights.values())


# ── splits ───────────────────────────────────────────────────────────────


def test_train_and_held_out_splits_are_disjoint(spec) -> None:
    for skill, data in spec["skills"].items():
        ids = [t["id"] for t in data["tasks"]]
        train = {t["id"] for t in data["tasks"] if t["split"] == "train"}
        held = {t["id"] for t in data["tasks"] if t["split"] == "held_out"}
        assert not (train & held), f"{skill}: {train & held}"
        assert len(ids) == len(set(ids)), f"{skill}: duplicate task ids"


def test_every_skill_has_a_held_out_split(spec) -> None:
    """A skill with no held-out tasks has nothing a quality claim could rest on."""
    for skill, data in spec["skills"].items():
        held = [t for t in data["tasks"] if t["split"] == "held_out"]
        assert held, f"{skill} has no held-out tasks"
        assert len(held) >= 2, f"{skill} has only {len(held)} held-out task(s)"


def test_every_judged_skill_has_a_real_document(spec) -> None:
    """Judging a skill whose playbook is missing would measure nothing."""
    for skill in spec["skills"]:
        doc = layer3.read_skill_doc(skill)
        assert len(doc.strip()) > 500, f"{skill}: SKILL.md body is suspiciously short"


def test_a_missing_skill_document_is_a_hard_error() -> None:
    with pytest.raises(layer3.BackendUnavailable):
        layer3.read_skill_doc("no-such-skill-exists")


# ── honesty properties ───────────────────────────────────────────────────


def test_stub_backend_is_marked_synthetic() -> None:
    assert layer3.StubBackend().synthetic is True


def test_every_stub_result_is_labelled_synthetic() -> None:
    backend = layer3.StubBackend()
    for skill, data in json.loads(TASKS_PATH.read_text(encoding="utf-8"))["skills"].items():
        result = layer3.evaluate_skill(
            skill, data,
            json.loads(TASKS_PATH.read_text(encoding="utf-8"))["rubric"],
            backend, "held_out", 2,
        )
        assert result["synthetic"] is True, skill


def test_stub_output_carries_the_synthetic_marker() -> None:
    """So a stub number can never be mistaken for a model judgement."""
    out = layer3.StubBackend().generate(skill_doc="# doc", task_input="x", seed=0)
    assert "synthetic" in out


def test_stub_marker_is_digit_free() -> None:
    """A digit in the marker would trip the fabrication veto and make the
    plumbing demo report a veto that never happened."""
    for seed in range(5):
        out = layer3.StubBackend().generate(skill_doc="# doc", task_input="x", seed=seed)
        assert not any(ch.isdigit() for ch in out), (seed, out)


def test_cli_reports_synthetic_and_refuses_a_verdict() -> None:
    proc = run_cli("--backend", "stub", "--split", "held_out", "--seeds", "2")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SYNTHETIC" in proc.stdout
    assert "PLUMBING REPORT" in proc.stdout
    assert "NOT a quality measurement" in proc.stdout
    assert "QUALITY REPORT" not in proc.stdout


def test_live_backend_without_credentials_exits_non_zero() -> None:
    """It must NOT degrade to the stub. That would fabricate a quality score."""
    proc = run_cli("--backend", "openai_compatible", "--split", "held_out", "--seeds", "1")
    assert proc.returncode != 0
    assert "FATAL" in proc.stderr
    assert "Refusing to fall back" in proc.stderr
    assert "SYNTHETIC" not in proc.stdout


def test_partial_credentials_are_still_a_hard_error() -> None:
    proc = run_cli(
        "--backend", "openai_compatible", "--split", "held_out", "--seeds", "1",
        env={"OPENAI_COMPATIBLE_BASE_URL": "https://example.invalid/v1"},
    )
    assert proc.returncode != 0
    assert "Refusing to fall back" in proc.stderr


def test_unknown_backend_is_rejected() -> None:
    proc = run_cli("--backend", "gpt5", "--split", "held_out")
    assert proc.returncode != 0
    assert "unknown backend" in proc.stderr


# ── determinism and variance ─────────────────────────────────────────────


def test_stub_run_is_deterministic() -> None:
    rubric = json.loads(TASKS_PATH.read_text(encoding="utf-8"))["rubric"]
    spec_data = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    skill = "resume-bullet-writer"
    first = layer3.evaluate_skill(skill, spec_data["skills"][skill], rubric,
                                 layer3.StubBackend(), "held_out", 3)
    second = layer3.evaluate_skill(skill, spec_data["skills"][skill], rubric,
                                   layer3.StubBackend(), "held_out", 3)
    assert first["mean_score"] == second["mean_score"]
    assert [t["score"] for t in first["tasks"]] == [t["score"] for t in second["tasks"]]


def test_multiple_seeds_produce_a_reported_spread() -> None:
    """A single unseeded judge number is not a result."""
    rubric = json.loads(TASKS_PATH.read_text(encoding="utf-8"))["rubric"]
    spec_data = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    skill = "resume-bullet-writer"
    result = layer3.evaluate_skill(skill, spec_data["skills"][skill], rubric,
                                   layer3.StubBackend(), "held_out", 3)
    for task in result["tasks"]:
        for key, c in task["criteria"].items():
            assert len(c["samples"]) == 3, (task["id"], key)
            assert "stdev" in c and "spread" in c


def test_instability_is_detected_rather_than_averaged_away() -> None:
    """Seeds that disagree must be reported, not silently collapsed into a mean."""
    rubric = json.loads(TASKS_PATH.read_text(encoding="utf-8"))["rubric"]
    spec_data = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    skill = "resume-bullet-writer"
    result = layer3.evaluate_skill(skill, spec_data["skills"][skill], rubric,
                                   layer3.StubBackend(), "held_out", 3)
    flagged = [k for t in result["tasks"] for k in t["unstable_criteria"]]
    assert flagged, (
        "the stub varies by seed, so at least one criterion must be flagged unstable; "
        "if this fails the instability detector is dead code"
    )
    assert result["unstable"] is True


def test_a_single_seed_is_allowed_but_reported_as_zero_spread() -> None:
    rubric = json.loads(TASKS_PATH.read_text(encoding="utf-8"))["rubric"]
    spec_data = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    skill = "resume-quantifier"
    result = layer3.evaluate_skill(skill, spec_data["skills"][skill], rubric,
                                   layer3.StubBackend(), "held_out", 1)
    for task in result["tasks"]:
        for c in task["criteria"].values():
            assert c["stdev"] == 0.0
            assert c["unstable"] is False


def test_zero_seeds_is_rejected() -> None:
    proc = run_cli("--backend", "stub", "--seeds", "0")
    assert proc.returncode != 0


# ── the fabrication veto ─────────────────────────────────────────────────


def test_fabrication_veto_zeroes_a_task_despite_a_generous_judge() -> None:
    """A confident judge must not be able to outvote a mechanical veto."""

    class GenerousStub(layer3.StubBackend):
        def generate(self, *, skill_doc, task_input, seed):
            return "Cut latency 45% across 14 services."  # invents figures

        def judge(self, *, task_id, criterion, prompt, seed):
            return {"score": 10, "rationale": "looks great"}

    rubric = json.loads(TASKS_PATH.read_text(encoding="utf-8"))["rubric"]
    spec_data = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    skill = "resume-quantifier"
    result = layer3.evaluate_skill(skill, spec_data["skills"][skill], rubric,
                                   GenerousStub(), "held_out", 1)
    task = result["tasks"][0]
    assert task["fabrication_vetoed"] is True
    assert task["score"] == 0.0, task["score"]
    assert result["any_fabrication"] is True
    # The judge scores are still recorded, so the veto is auditable rather than
    # invisible.
    assert any(c["mean"] > 0 for c in task["criteria"].values())


# ── CLI surface ──────────────────────────────────────────────────────────


def test_list_reports_the_split_census() -> None:
    proc = run_cli("--list")
    assert proc.returncode == 0
    assert "resume-bullet-writer" in proc.stdout
    assert "held_out" in proc.stdout


def test_json_report_is_marked_synthetic_for_stub_runs() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.json"
        proc = run_cli("--backend", "stub", "--split", "held_out", "--seeds", "2",
                       "--json", str(out))
        assert proc.returncode == 0, proc.stdout + proc.stderr
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["synthetic"] is True
        assert all(r["synthetic"] for r in data["results"])