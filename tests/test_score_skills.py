"""The scorecard must be a real instrument, not a number generator.

Three properties make ``scripts/score_skills.py`` trustworthy enough to gate a
build on:

1. **Bounded and normalised** -- every dimension is worth exactly 10 points and
   no dimension can silently exceed it. A dimension that scored out of 13 was
   written and shipped before this test existed; the score read as a percentage
   of the wrong denominator and every other score in the run was misread with it.
2. **Deterministic** -- the same input always produces the same score, with no
   model call and no clock or filesystem ordering dependence.
3. **Auditable** -- every awarded or withheld point carries a human-readable
   reason naming the evidence, so a score can be argued with rather than merely
   reported.

Plus one regression guard for a real false negative that was found and fixed:
a skill handling edge cases in prose (``reference-list-builder`` carries a whole
"Handling Special Situations" section) scored zero because the scorer only
grepped for the word "error". Left unfixed, the scorecard would have instructed
someone to keyword-stuff 33 healthy skills.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "score_skills.py"
SKILLS_DIR = REPO_ROOT / "skills"

# Import the script as a module. It is a script, not a package, and defining
# dataclasses at import time requires the module to be registered in sys.modules.
_spec = importlib.util.spec_from_file_location("score_skills_under_test", SCRIPT)
score_skills = importlib.util.module_from_spec(_spec)
sys.modules["score_skills_under_test"] = score_skills
_spec.loader.exec_module(score_skills)

DIMENSION_KEYS = [f"D{i}" for i in range(1, 11)]


@pytest.fixture(scope="module")
def scored() -> dict:
    return {
        p.name: score_skills.score_skill(p)
        for p in sorted(SKILLS_DIR.iterdir())
        if (p / "SKILL.md").is_file()
    }


# ── 1. bounded and normalised ────────────────────────────────────────────


def test_there_are_exactly_ten_dimensions() -> None:
    assert len(score_skills.DIMENSIONS) == 10


def test_every_dimension_is_worth_exactly_ten_points(scored) -> None:
    """A dimension worth 13 silently rescales every other score in the run.

    This test exists because it happened: the failure-handling dimension was
    rebalanced to 4+3+3+3 and every score in the scorecard became a percentage
    of the wrong denominator.
    """
    offenders = []
    for slug, result in scored.items():
        for dim in result["dimensions"]:
            if dim["max"] != 10.0:
                offenders.append((slug, dim["key"], dim["max"]))
    assert not offenders, f"dimensions not worth 10 points: {offenders[:6]}"


def test_totals_are_bounded_zero_to_one_hundred(scored) -> None:
    for slug, result in scored.items():
        assert 0.0 <= result["score"] <= 100.0, (slug, result["score"])


def test_dimension_scores_never_exceed_their_maximum(scored) -> None:
    for slug, result in scored.items():
        for dim in result["dimensions"]:
            assert dim["score"] <= dim["max"], (slug, dim["key"], dim["score"], dim["max"])


def test_total_equals_the_sum_of_its_dimensions(scored) -> None:
    for slug, result in scored.items():
        total = round(sum(d["score"] for d in result["dimensions"]), 2)
        assert total == result["score"], (slug, total, result["score"])


def test_dimension_keys_are_the_documented_set(scored) -> None:
    sample = next(iter(scored.values()))
    assert [d["key"] for d in sample["dimensions"]] == DIMENSION_KEYS


# ── 2. deterministic ─────────────────────────────────────────────────────


def test_scoring_is_reproducible() -> None:
    target = SKILLS_DIR / "ats-audit"
    first = score_skills.score_skill(target)
    second = score_skills.score_skill(target)
    assert first["score"] == second["score"]
    assert [d["score"] for d in first["dimensions"]] == [d["score"] for d in second["dimensions"]]


def test_scoring_every_skill_is_reproducible() -> None:
    one = [score_skills.score_skill(p)["score"]
           for p in sorted(SKILLS_DIR.iterdir()) if (p / "SKILL.md").is_file()]
    two = [score_skills.score_skill(p)["score"]
           for p in sorted(SKILLS_DIR.iterdir()) if (p / "SKILL.md").is_file()]
    assert one == two


# ── 3. auditable ─────────────────────────────────────────────────────────


def test_every_criterion_carries_a_reason(scored) -> None:
    """No point is awarded or withheld invisibly."""
    missing = []
    for slug, result in scored.items():
        for dim in result["dimensions"]:
            for crit in dim["criteria"]:
                if not crit["reason"].strip():
                    missing.append((slug, dim["key"]))
                if crit["max"] <= 0:
                    missing.append((slug, dim["key"], "zero-max criterion"))
    assert not missing, f"criteria without a reason or with a zero maximum: {missing[:6]}"


def test_criteria_maxima_sum_to_the_dimension_maximum(scored) -> None:
    sample = next(iter(scored.values()))
    for dim in sample["dimensions"]:
        assert round(sum(c["max"] for c in dim["criteria"]), 2) == dim["max"], dim["key"]


def test_scoring_reports_which_artifact_it_measured(scored) -> None:
    for result in scored.values():
        assert result["scored"] in {
            "repo source only (no catalog supplied)",
            "effective (repo body + catalog metadata)",
        }


# ── 4. the false-negative regression guard ───────────────────────────────


def test_edge_case_sections_are_detected_structurally_not_by_keyword() -> None:
    """A skill can handle edge cases in prose and never say 'error'.

    ``reference-list-builder`` carries "Handling Special Situations" and
    "Who to Avoid" but scored D8 0/10 under the original keyword-only scorer.
    """
    body = (
        "# Reference List Builder\n\n"
        "## Handling Special Situations\n\n### Who to Avoid\n\n"
        "If a reference will not respond, escalate to a backup.\n"
    )
    dim = score_skills.d8_failures(body)
    assert dim.score > 0, "a named edge-case section must score above zero"
    reasons = " ".join(c.reason for c in dim.criteria)
    assert "edge-case heading" in reasons


def test_a_document_with_no_edge_case_handling_scores_zero_on_d8() -> None:
    """The converse: the dimension must still be able to return zero."""
    body = (
        "# Flat Skill\n\n## Mission\nDo the thing.\n\n"
        "## Operating Rules\n1. Format the output.\n2. Cite the source.\n\n"
        "## Output Contract\nMarkdown.\n"
    )
    assert score_skills.d8_failures(body).score == 0.0


def test_structural_signal_outranks_a_stray_keyword() -> None:
    """A named section is deliberate; one occurrence of 'error' is not."""
    structural = score_skills.d8_failures(
        "## Edge Cases\n\nHandle the manager who left.\n"
    )
    incidental = score_skills.d8_failures(
        "## Notes\n\nIf there is an error, mention it somewhere in passing.\n"
    )
    assert structural.score > incidental.score


# ── 5. the scorer responds to real change ────────────────────────────────


def test_removing_canonical_sections_lowers_the_score(tmp_path) -> None:
    """The instrument must react to degradation, or it is decoration."""
    skill_dir = tmp_path / "toy"
    skill_dir.mkdir()
    good = (
        "---\nname: toy\ndescription: Toy skill that formats resumes accurately and quickly.\n"
        "version: 1.0.0\ntags: [Toy]\nrequired_scope: memory.read\ntriggers: [toy skill]\n---\n\n"
        "# Toy\n\n## Mission\nFormat resumes.\n\n## Operating Rules\n"
        "1. Never invent metrics; cite the source for every number.\n"
        "2. Validate the input and report what is missing.\n"
        "3. Refuse rather than guess when data is unavailable.\n\n"
        "## Triggers\nUse when the request contains toy skill.\n\n"
        "## Output Contract\n1. Findings. 2. Evidence with provenance. "
        "Never invent a figure; state that it is unknown.\n"
    )
    (skill_dir / "SKILL.md").write_text(good, encoding="utf-8")
    good_score = score_skills.score_skill(skill_dir)["score"]

    stripped = good.replace("## Output Contract", "## Other Notes")
    (skill_dir / "SKILL.md").write_text(stripped, encoding="utf-8")
    bad_score = score_skills.score_skill(skill_dir)["score"]

    assert bad_score < good_score, f"{bad_score} should be below {good_score}"


def test_dropping_triggers_lowers_the_triggering_score(tmp_path) -> None:
    skill_dir = tmp_path / "toy2"
    skill_dir.mkdir()
    body_tail = "\n\n# Toy\n\n## Mission\nFormat resumes.\n"
    (skill_dir / "SKILL.md").write_text(
        "---\nname: toy2\ndescription: Toy skill that formats resumes accurately and quickly "
        "when the user asks for tailored resume formatting help.\nversion: 1.0.0\ntags: [Toy]\n"
        "required_scope: memory.read\ntriggers: [toy two skill, tailor resume, format resumes]\n"
        f"---\n{body_tail}",
        encoding="utf-8",
    )
    with_triggers = score_skills.score_skill(skill_dir)["score"]

    (skill_dir / "SKILL.md").write_text(
        "---\nname: toy2\ndescription: Toy skill that formats resumes accurately and quickly "
        "when the user asks for tailored resume formatting help.\nversion: 1.0.0\ntags: [Toy]\n"
        f"required_scope: memory.read\ntriggers: []\n---\n{body_tail}",
        encoding="utf-8",
    )
    without = score_skills.score_skill(skill_dir)["score"]

    assert without < with_triggers


def test_an_unknown_scope_is_penalised(tmp_path) -> None:
    """A fabricated scope must not score like an authorized one."""
    scores = {}
    for scope in ("memory.read", "totally.made.up"):
        skill_dir = tmp_path / f"toy_{scope.replace('.', '_')}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_dir.name}\ndescription: Toy skill that formats resumes.\n"
            f"version: 1.0.0\ntags: [Toy]\nrequired_scope: {scope}\ntriggers: [toy]\n---\n\n"
            f"# Toy\n\n## Mission\nFormat resumes for {scope}.\n",
            encoding="utf-8",
        )
        scores[scope] = score_skills.score_skill(skill_dir)["score"]
    assert scores["totally.made.up"] < scores["memory.read"]
