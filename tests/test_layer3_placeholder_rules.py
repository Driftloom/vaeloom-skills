"""The placeholder classifier, which decides one thing only: does a placeholder
occupy a structural slot?

The rules come from spec section 3.1. They are transcribed from the placeholder
syntax and from the Google XYZ formula the skill documents mandate. They are NOT
derived from the candidates on which the two judges happened to disagree --
fitting a rule to observed disagreements is what produced a false result in the
previous round.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "layer3_under_test", Path(__file__).resolve().parent.parent
    / "evals" / "layer3_judge.py"
)
layer3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(layer3)


def classify(text):
    return layer3.classify_placeholders(text)


# --- trigger 1: formula variable -------------------------------------------

@pytest.mark.parametrize("fragment,expected_total", [
    ("improving [X] as measured by [Y] by [Z]", 3),
    ("achieved [x] by [y]", 2),
])
def test_formula_variable_is_scaffolding(fragment, expected_total):
    # The expected count is per-fragment, not a literal 3: "achieved [x] by [y]"
    # holds two placeholders, and a classifier that reported three would be
    # counting a placeholder that is not in the text.
    r = classify(fragment)
    assert r["total"] == expected_total, r
    assert r["scaffolded"] == expected_total, r
    assert r["named"] == 0, r


# --- trigger 2: formula-governed slot --------------------------------------

def test_placeholder_directly_after_measured_by_is_scaffolding():
    # "[RATE]" is not a formula variable and "rate" is not an instruction verb,
    # so only trigger 2 can classify it.
    r = classify("reduced defects as measured by [RATE]")
    assert r["total"] == 1, r
    assert r["scaffolded"] == 1, r


def test_placeholder_not_after_measured_by_is_not_scaffolding():
    """The phrase has to immediately precede. One clause later is not a slot."""
    r = classify("reduced defects, as measured by the team, through [N] audits")
    assert r["total"] == 1, r
    assert r["scaffolded"] == 0, r
    assert r["named"] == 1, r


def test_a_by_at_a_distance_does_not_make_a_placeholder_scaffolding():
    # A bare "by" names a quantity slot, not a formula one: "cut cycle time by
    # [N] days" and "reducing manual effort by [N] hours per week" are the same
    # construction. An earlier rule read any of them as scaffolding and then had
    # to carve out whichever example it had not seen.
    r = classify("Led the recovery, recovering [N] accounts and closing the backlog")
    assert r["total"] == 1, r
    assert r["scaffolded"] == 0, r


# --- trigger 3: instruction to the writer ----------------------------------

@pytest.mark.parametrize("fragment", [
    "reduced spend through [insert specific action]",
    "delivered results via [add metric here]",
    "improved [describe the outcome] for the team",
    "shipped [your e.g. example here]",
    "reduced cost by [Insert: the metric]",
    "reduced cost by [describe: outcome]",
    "delivered [write the summary] to the board",
    "delivered [state the metric] to the board",
])
def test_writer_instruction_is_scaffolding(fragment):
    r = classify(fragment)
    assert r["total"] == 1, r
    assert r["scaffolded"] == 1, r


def test_punctuation_around_the_head_word_does_not_hide_the_instruction():
    """A writer punctuates the head word: "[Insert: the metric]" opens with
    "insert:" and "[describe the outcome (optional)]" with "describe". Without
    the strip, the lookup misses and an instruction to the writer is scored as a
    quantity the output named -- the expensive direction, because a named
    placeholder escapes the agency cap.

    The strip normalises one token and then matches exactly. It is not the
    character-class inference removed in the previous round, which guessed
    noun-ness from the shape of the contents and misread "[time-to-market]"."""
    for fragment in ("[Insert: the metric]", "[describe: the outcome (optional)]"):
        r = classify(f"reduced cost by {fragment}")
        assert r["total"] == 1, fragment
        assert r["scaffolded"] == 1, fragment
        assert r["named"] == 0, fragment


def test_your_marker_alone_makes_a_bracket_scaffolding():
    """The "your" guard is load-bearing, and it was not before.

    "[your e.g. example here]" carries no instruction verb, so nothing but this
    guard makes it scaffolding. It used to pass only because the dots defeated a
    noun-phrase regex that no longer exists. Delete _WRITER_MARKER and this
    fails; the rule that survives is the rule the code actually implements."""
    r = classify("shipped [your e.g. example here]")
    assert r["total"] == 1, r
    assert r["scaffolded"] == 1, r
    assert r["named"] == 0, r


def test_bracket_used_as_a_noun_is_named():
    """Review Focus 1: a bracketed word that names a quantity is not an
    instruction to the writer, and nothing in "[budget]" looks like one."""
    r = classify("managed the [budget] line for the division")
    assert r["total"] == 1, r
    assert r["scaffolded"] == 0, r
    assert r["named"] == 1, r


# --- named placeholders ------------------------------------------------------

@pytest.mark.parametrize("fragment,expected_total", [
    ("improving completion rates from [N]% to [M]%", 2),
    ("cutting completion time from [N] to [M] days", 2),
    ("reducing manual effort by [N] hours per week", 1),
    ("cut cycle time by [N] days", 1),
])
def test_named_placeholders(fragment, expected_total):
    r = classify(fragment)
    assert r["total"] == expected_total, r
    assert r["scaffolded"] == 0, r
    assert r["named"] == expected_total, r


@pytest.mark.parametrize("fragment", [
    "[end-to-end cycle time]",
    "[Q3 pipeline value]",
    "[time-to-market]",
    "[the budget]",
])
def test_quantity_named_by_the_output_is_named(fragment):
    """A quantity the output names for itself is not an instruction.

    These were the measured defect. The old rule inferred a noun from the
    characters -- letters and spaces only -- so every hyphen or digit outside
    that class escaped the inference and was called scaffolding, which is the
    expensive direction to be wrong in. Scaffolding now needs positive evidence
    of an instruction and the default is named."""
    r = classify(f"improving {fragment} for the division")
    assert r["total"] == 1, r
    assert r["scaffolded"] == 0, r
    assert r["named"] == 1, r


@pytest.mark.parametrize("fragment", [
    "{N}",
    "<N>",
])
def test_brace_and_angle_placeholder_forms_are_classified(fragment):
    """PLACEHOLDER_RE also matches {..} and <..>, so the classifier must not be
    square-bracket-specific."""
    r = classify(f"improving completion rates from {fragment} percent")
    assert r["total"] == 1, r
    assert r["scaffolded"] == 0, r
    assert r["named"] == 1, r


def test_two_placeholders_around_one_quantity_are_both_named():
    """Review Focus 2: neither may be classified from the other's vicinity."""
    r = classify("improving completion rates from [N]% to [M]%")
    assert r["total"] == 2, r
    assert r["named"] == 2, r


# --- invariants ---------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "",
    "Led the migration of the legacy warehouse to the new platform.",
    "improving [X] as measured by [Y] by [Z]",
    "improving completion rates from [N]% to [M]%",
    "reduced spend through [insert specific action] by [Z]",
])
def test_counts_are_consistent(text):
    r = classify(text)
    assert r["total"] == r["named"] + r["scaffolded"], r
    # type(...) and not isinstance(...): bool is a subclass of int, so a count
    # that came back True would satisfy isinstance and corrupt the arithmetic
    # above without tripping this assertion.
    assert all(type(r[k]) is int for k in ("total", "named", "scaffolded")), r


@pytest.mark.parametrize("text", [
    "",
    "no placeholders at all here",
    "Led the migration.",
])
def test_output_without_placeholders_is_all_zero(text):
    """Review Focus 4 and 5."""
    r = classify(text)
    assert r == {"total": 0, "named": 0, "scaffolded": 0}, r


def test_placeholder_only_output_does_not_crash():
    """Review Focus 3."""
    r = classify("[X]")
    assert r["total"] == 1, r
    assert r["scaffolded"] == 1, r
