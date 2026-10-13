"""Pin the anti-fabrication decision rules in the two resume skill documents.

These rules are the fix for the measured defect: 25.0% of generations invented a
figure the source never contained, because `resume-bullet-writer` demanded a
metric "in every bullet" while also forbidding invention, and `resume-quantifier`
licensed "conservative, defensible estimates" with no test of what made one
defensible. Neither document said what to do when no number was available, so the
model invented one.

After the fix the same 8 tasks produced 0 fabrications in 24 generations. That
number is only meaningful while the rules stay in the documents, so they are
asserted here rather than left to a future edit.

A missing rule is silent: the document still reads well and the score quietly
regresses. These tests fail the moment either rule is removed or softened.

A second defect needed the same treatment. The document wrote the XYZ shape
literally, as `'Accomplished [X] as measured by [Y] by doing [Z]'`, and the model
copied it slot for slot rather than writing a bullet. Brackets used as notation
read as output to an imitation-following model, so the file now asserts that the
document carries no structural slot anywhere — including inside a "do not do this"
example, which would teach the defect as firmly as the rule ever did. It also
pins the narrowing that made the removal safe: a blank on a *named quantity*
stays allowed, because that is what keeps the document from teaching the model
to omit a clause it could have filled.
"""
from __future__ import annotations

from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parent.parent / "skills"


def doc(skill: str) -> str:
    return (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")


def test_no_literal_template_slots_anywhere_in_the_document() -> None:
    """A mention anywhere reintroduces the copyable pattern, including inside a
    'do not do this' example, so the whole file is scanned rather than the rule
    that changed."""
    text = doc("resume-bullet-writer")
    for slot in ("[X]", "[Y]", "[Z]"):
        assert slot not in text, f"{slot} reintroduces the template the model copies"


def test_the_no_metric_example_category_exists_and_is_labelled() -> None:
    text = doc("resume-bullet-writer")
    assert "Complete without a metric" in text
    assert "These are finished bullets" in text


def test_placeholder_language_distinguishes_named_from_structural() -> None:
    text = doc("resume-bullet-writer")
    assert "A placeholder is a correct answer" not in text, (
        "the unqualified claim contradicts the no-padding rule"
    )
    assert "stands in for a slot" in text
    assert "[N]" in text and "[M]" in text, (
        "named-quantity placeholders stay allowed; the document must still show them"
    )


def test_phase_one_guarantees_survive_the_rewrite() -> None:
    """Collateral-damage check. The rewrite must not quietly drop Phase 1."""
    text = doc("resume-bullet-writer")
    assert "## Decision Rule: No Number Available" in text
    assert "Plausible-sounding ranges" in text
    assert "Unqualified absolutes" in text


class TestResumeBulletWriterCannotBeReverted:
    """The contradiction was "require a metric in every bullet" + "never invent"."""

    def test_mandatory_metric_rule_is_gone(self) -> None:
        text = doc("resume-bullet-writer")
        assert "Mandatory Metric Quantification" not in text, (
            "this rule demanded a metric in every bullet and had no "
            "no-number-available path, which is what produced the fabrications"
        )

    def test_a_no_number_decision_rule_exists(self) -> None:
        assert "## Decision Rule: No Number Available" in doc("resume-bullet-writer")

    def test_hedged_ranges_are_explicitly_forbidden(self) -> None:
        # "15-20%" was the most common fabrication and reads as careful, not invented.
        assert "Plausible-sounding ranges" in doc("resume-bullet-writer")
        assert "15-20%" in doc("resume-bullet-writer")

    def test_unqualified_absolutes_are_explicitly_forbidden(self) -> None:
        # "ensuring 100% data integrity" was observed verbatim in a live run.
        text = doc("resume-bullet-writer")
        assert "Unqualified absolutes" in text
        assert "100% data integrity" in text

    def test_a_bullet_without_a_metric_is_still_valid(self) -> None:
        # Otherwise the pressure to fabricate comes straight back.
        assert "is not a failed bullet" in doc("resume-bullet-writer")


class TestResumeQuantifierCannotBeReverted:
    """The rule licensed estimates with nothing to test them against."""

    def test_unfalsifiable_estimation_rule_is_gone(self) -> None:
        text = doc("resume-quantifier")
        assert "Conservative Estimation Modeling" not in text, (
            "'conservative, defensible' had no test, so any plausible range passed"
        )

    def test_a_derivation_test_exists(self) -> None:
        assert "## The Derivation Test" in doc("resume-quantifier")

    def test_convention_and_industry_benchmarks_are_forbidden(self) -> None:
        text = doc("resume-quantifier")
        assert "never by recall, convention, or intuition" in text
        assert "industry-typical" in text

    def test_every_estimate_must_ship_its_inputs(self) -> None:
        assert "Every estimate ships with its inputs" in doc("resume-quantifier")

    def test_derived_must_stay_labelled_as_derived(self) -> None:
        # An estimate presented as a stated fact is the laundering risk.
        assert "Label anything derived as derived" in doc("resume-quantifier")

    def test_declining_to_answer_is_permitted(self) -> None:
        assert "that is the answer" in doc("resume-quantifier")

    @pytest.mark.parametrize("skill", ["resume-bullet-writer", "resume-quantifier"])
    def test_both_docs_still_forbid_absolute_claims(self, skill: str) -> None:
        assert "100%" in doc(skill), (
            f"{skill} should still name the absolute-claim failure mode"
        )
