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
regresses. These tests fail the moment a rule is removed or softened.

A second defect needed the same treatment. The document wrote the XYZ shape
literally, as `'Accomplished [X] as measured by [Y] by doing [Z]'`, and the model
copied it slot for slot rather than writing a bullet. Brackets used as notation
read as output to an imitation-following model, so the file now asserts that the
document carries no structural slot anywhere — including inside a "do not do this"
example, which would teach the defect as firmly as the rule ever did. The scan
also covers the *unbracketed* form: `X = What you achieved` is the same template
with its brackets removed, and a check for `[X]` alone cannot see it. It pins
the narrowing that made the removal safe: a blank on a *named quantity* stays
allowed, because that is what keeps the document from teaching the model to omit
a clause it could have filled.

The Phase 1 fix was itself only half applied, which is why the assertions below
are not all presence checks. `Every bullet should have at least ONE number` and a
menu of estimation strategies survived underneath the Decision Rule that bans
them; a document can forbid hedged ranges on page one and license them on page
four, and a presence-only test passes that document happily. Each rule asserted
here is therefore paired with the absence of the guidance that contradicts it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parent.parent / "skills"

# Guidance that told the model to produce a number it did not have. Each string
# here was live in the document at the time these tests were written.
FORBIDDEN_GUIDANCE = (
    "Every bullet should have at least ONE number",
    "Use estimation strategies",
    "Use ranges",
    "Use conservative estimates",
    "If you think it was 60%, say 50%",
    "At least one number/metric",
    "Add at least one number",
)

# The template with its brackets removed. Same defect, invisible to a `[X]` scan.
SLOT_LABELS = ("X =", "Y =", "Z =")


def doc(skill: str) -> str:
    return (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")


def assert_no_contradicting_guidance(text: str) -> None:
    """Assert the document does not ask for a number it cannot have.

    A presence assertion cannot catch a self-contradicting document: every rule
    can be present and correct while a later section licenses the fabrication the
    rule forbids. Each phrase below was found live in the document after the
    Decision Rule had already banned it.
    """
    for phrase in FORBIDDEN_GUIDANCE:
        assert phrase not in text, (
            f"{phrase!r} tells the model to invent or bracket a number, which is "
            "the fabrication Phase 1 measured"
        )
    for label in SLOT_LABELS:
        assert label not in text, (
            f"{label!r} is the three-slot template without its brackets; a named "
            "slot is one the reader will try to fill"
        )


def test_no_literal_template_slots_anywhere_in_the_document() -> None:
    """A mention anywhere reintroduces the copyable pattern, including inside a
    'do not do this' example, so the whole file is scanned rather than the rule
    that changed."""
    text = doc("resume-bullet-writer")
    for slot in ("[X]", "[Y]", "[Z]"):
        assert slot not in text, f"{slot} reintroduces the template the model copies"
    assert_no_contradicting_guidance(text)


def test_the_no_metric_example_category_exists_and_is_labelled() -> None:
    text = doc("resume-bullet-writer")
    assert "Complete without a metric" in text
    assert "These are finished bullets" in text
    # The category claims a metric-free bullet is complete. Guidance demanding a
    # metric everywhere would contradict it from the inside.
    assert_no_contradicting_guidance(text)


def test_placeholder_language_distinguishes_named_from_structural() -> None:
    text = doc("resume-bullet-writer")
    assert "A placeholder is a correct answer" not in text, (
        "the unqualified claim contradicts the no-padding rule"
    )
    assert "stands in for a slot" in text
    assert "[N]" in text and "[M]" in text, (
        "named-quantity placeholders stay allowed; the document must still show them"
    )


def test_the_metric_free_claim_and_the_placeholder_branch_are_separated() -> None:
    """Two claims that are each correct read as a contradiction when adjacent.

    "These bullets are finished as written" and "leave a placeholder on that
    quantity" are both true; the second governs only the case where a figure
    genuinely exists. Stated as consecutive sentences with no transition between
    them, the paragraph tells the reader a bullet needs no number and to leave a
    blank in the same breath. Both branches have to survive, so this pins the
    transition rather than deleting either claim — and pins its *position*, since
    a transition that has drifted to the end of the paragraph stops doing its job.
    """
    text = doc("resume-bullet-writer")
    no_figure = "These bullets are finished as written."
    transition = "it changes the instruction rather than the exemplar"
    placeholder = "leave a placeholder on that quantity"
    assert no_figure in text, "the metric-free branch of the category is gone"
    assert transition in text, (
        "the conditional was dropped; without it the placeholder instruction "
        "reads as contradicting the category it sits in"
    )
    assert placeholder in text, (
        "branch 3 must still authorise a placeholder where a figure exists"
    )
    assert text.index(no_figure) < text.index(transition) < text.index(placeholder), (
        "the two claims are adjacent again; the transition has to sit between "
        "the metric-free claim and the placeholder instruction"
    )


def test_phase_one_guarantees_survive_the_rewrite() -> None:
    """Collateral-damage check. The rewrite must not quietly drop Phase 1.

    Asserts the Decision Rule's *shape* — the ordered branches and the thing
    branch 3 asks the model to do — none of which the per-rule tests below cover.
    A document can keep every banned phrase quoted in its Forbidden list while
    deleting the branch that resolves "no number anywhere", and still pass those.
    """
    text = doc("resume-bullet-writer")
    assert "Apply this in order and stop at the first branch that fits" in text
    for branch in (
        "A number exists in the input",
        "A number exists in the vault",
        "No number exists anywhere",
    ):
        assert branch in text, f"the Decision Rule lost a branch: {branch!r}"
    assert "**ask the user to fill it in.**" in text, (
        "branch 3 must still instruct the model to ask; pinning what a "
        "placeholder is does not pin the affordance it exists to serve"
    )
    assert_no_contradicting_guidance(text)


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
