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

def test_placeholder_directly_after_standalone_by_is_scaffolding():
    r = classify("cut cycle time by [N] days")
    assert r["scaffolded"] == 1, r


def test_placeholder_not_after_by_is_named():
    # "recovered by the team" -- the "by" is far away and governs a different
    # phrase. A proximity window would wrongly fire here.
    r = classify("Led the recovery, recovering [N] accounts and closing the backlog")
    assert r["total"] == 1, r
    assert r["scaffolded"] == 0, r


# --- trigger 3: instruction to the writer ----------------------------------

@pytest.mark.parametrize("fragment", [
    "reduced spend through [insert specific action]",
    "delivered results via [add metric here]",
    "improved [describe the outcome] for the team",
    "shipped [your e.g. example here]",
])
def test_writer_instruction_is_scaffolding(fragment):
    r = classify(fragment)
    assert r["total"] == 1, r
    assert r["scaffolded"] == 1, r


def test_bracket_used_as_a_noun_is_named():
    """Review Focus 1: a bracketed word that merely starts with a verb is a
    quantity name, not an instruction to the writer."""
    r = classify("managed the [budget] line for the division")
    assert r["total"] == 1, r
    assert r["scaffolded"] == 0, r
    assert r["named"] == 1, r


# --- named placeholders ------------------------------------------------------

@pytest.mark.parametrize("fragment,expected_total", [
    ("improving completion rates from [N]% to [M]%", 2),
    ("cutting completion time from [N] to [M] days", 2),
])
def test_named_placeholders(fragment, expected_total):
    r = classify(fragment)
    assert r["total"] == expected_total, r
    assert r["scaffolded"] == 0, r
    assert r["named"] == expected_total, r


def test_spec_worked_example_conflicts_with_the_standalone_by_trigger():
    """Spec section 3.3 lists "reducing manual effort by [N] hours per week" as
    named, and section 3.1 trigger 2 makes a placeholder directly after a
    standalone "by" scaffolding. Both cannot hold: the two strings are the same
    construction -- <verb> ... by [N] <unit> -- differing only in base verb
    against gerund, which is not a distinction any rule may key on.

    Trigger 2 wins here because it is one of the three triggers the plan fixes,
    and because test_placeholder_directly_after_standalone_by_is_scaffolding is
    the only test that exercises it. This test exists so the disagreement is
    pinned in the suite rather than settled silently; if the project decides
    section 3.3 is the correct reading, this expectation and trigger 2 both
    move, and the named list above takes this string back."""
    r = classify("reducing manual effort by [N] hours per week")
    assert r["total"] == 1, r
    assert r["scaffolded"] == 1, r
    assert r["named"] == 0, r


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
    assert all(isinstance(r[k], int) for k in ("total", "named", "scaffolded")), r


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