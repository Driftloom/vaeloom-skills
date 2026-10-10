# Placeholder Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Layer 3 rubric hold one explicit position on what a placeholder is worth, so the three criteria stop disagreeing about the same output.

**Architecture:** The harness classifies each placeholder mechanically as *scaffolding* (fills a formula slot or instructs the writer) or *named* (governed by a quantity the output itself names), exposes that classification as mechanical evidence in the judge prompt, and enforces three differentiated caps during aggregation. The cap is applied to a criterion's aggregated mean, before the fabrication veto, so a vetoed task is unaffected.

**Tech Stack:** Python 3.12, pytest, JSON rubric. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-11-placeholder-scoring-design.md`

## Global Constraints

- The classification rules are fixed by spec Â§3.1 and must be transcribed exactly. Do not add a fourth trigger.
- The cap is a **ceiling, not a floor**: `min(score, cap)`. A judge score below the cap is never raised.
- The cap applies to the criterion's **aggregated mean** (`criteria_scores[key]["mean"]`), not per seed. Clamping per seed and then averaging yields a different number.
- Caps are applied **before** the fabrication veto. An implementation that clamps after the veto would silently alter vetoed tasks.
- Anchor wording in `evals/layer3_tasks.json` does **not** change in Phase 1. The caps live in code because an anchor cannot enforce a cap.
- `craft` stays disabled at weight `0.0` and is unaffected by everything here.
- No comment or string may describe an effect the code does not have. Where a comment states a rule, the code must implement that rule.
- `rubric_fingerprint` (added in `281502f`) must remain intact. Any harness change that affects scoring requires both committed reports to be regenerated before the inter-judge tool will run.
- Run all commands from the repository root `C:\PROJECTS\PIOS\ClonU\Driftloom\vaeloom-skills`.
- Set `$env:PYTHONDONTWRITEBYTECODE="1"` before Python invocations to avoid `__pycache__` noise.

## Review Focus

The spec is a vision document; these are the inputs it implies but no task's tests would otherwise exercise, most likely to bite first.

1. **A placeholder inside a quoted metric name**, e.g. `"[budget]"` used as a noun the output itself names. Must be treated as *named*, never as an instruction to the writer, because the classifier must not fire the writer-instruction trigger on a word that merely starts with a verb.
2. **Two placeholders bracketing one quantity**, e.g. `from [N] to [M] days`. Must be `named` Ã—2 â€” the first must not consume the second via a proximity window, and neither may be classified from the text *after* it.
3. **A placeholder as the entire output.** `total` must be â‰¥1 and `scaffolding` must be 0, not a crash and not an invented instruction reading.
4. **A candidate with no placeholder at all.** Every cap must be inert. This is the case a buggy "always clamp" implementation breaks silently, because scores still look plausible.
5. **An empty string.** `classify_placeholders("")` must return zeros, not raise â€” `mechanical_evidence` is called on every candidate including degenerate ones.

---

### Task 1: The classifier

**Files:**
- Modify: `evals/layer3_judge.py:76` (next to `PLACEHOLDER_RE`)
- Test: `tests/test_layer3_placeholder_rules.py` (create)

**Interfaces:**
- Consumes: `PLACEHOLDER_RE` (already defined at `evals/layer3_judge.py:76`).
- Produces: `classify_placeholders(text: str) -> dict` returning **exactly three
  keys** â€” `{"total": int, "named": int, "scaffolded": int}`. No fourth key: a
  test asserts whole-dict equality, so adding one breaks it. Callers that want a
  boolean read `placeholders["scaffolded"] > 0`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_layer3_placeholder_rules.py`:

```python
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

@pytest.mark.parametrize("fragment", [
    "improving [X] as measured by [Y] by [Z]",
    "achieved [x] by [y]",
])
def test_formula_variable_is_scaffolding(fragment):
    r = classify(fragment)
    assert r["total"] == 3, r
    assert r["scaffolded"] == 3, r
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
    ("reducing manual effort by [N] hours per week", 1),
])
def test_named_placeholders(fragment, expected_total):
    r = classify(fragment)
    assert r["total"] == expected_total, r
    assert r["scaffolded"] == 0, r
    assert r["named"] == expected_total, r


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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_layer3_placeholder_rules.py -q`
Expected: collection error or `AttributeError: module 'layer3_under_test' has no attribute 'classify_placeholders'`

- [ ] **Step 3: Implement `classify_placeholders` in `evals/layer3_judge.py`**

Add immediately after `PLACEHOLDER_RE` (line 76). Two module-level constants and one function:

```python
# A placeholder is "scaffolding" when it fills a slot that exists for the formula
# rather than for the writer's data. These are the triggers from spec section 3.1
# and the complete list -- a fourth would change behaviour that no decision covers.
_FORMULA_VARIABLE_RE = re.compile(r"^[XYZxyz]$")
_STANDALONE_BY_RE = re.compile(r"\bby\s*$", re.IGNORECASE)
# A bracket that names a quantity rather than instructing the writer. Checked
# before the instruction trigger so "[budget]" is never read as "begin with a verb".
_BRACKETED_NOUN_RE = re.compile(r"^(?:the\s+)?[a-z][a-z ]{0,24}$", re.IGNORECASE)
_INSTRUCTION_VERBS = {
    "insert", "add", "describe", "specify", "list", "name", "fill",
    "enter", "replace", "provide", "detail", "quantify",
}


def classify_placeholders(text: str) -> dict:
    """Classify every placeholder as scaffolding or named.

    Answers exactly one question: does this placeholder occupy a structural
    slot? It does not judge whether the named quantity is a good thing to
    measure or whether the surrounding prose is good. Those remain the judge's.

    A scaffolding trigger fires only on the text immediately preceding the
    placeholder -- never on what follows it, and never at a distance -- because
    a proximity window misclassifies "recovered by the team, recovering [N]
    accounts" as scaffolding.
    """
    total = named = scaffolded = 0
    for match in PLACEHOLDER_RE.finditer(text):
        total += 1
        inner = match.group(0)[1:-1].strip()
        before = text[: match.start()].rstrip()
        if _FORMULA_VARIABLE_RE.match(inner):
            scaffolded += 1
            continue
        if _STANDALONE_BY_RE.search(before):
            scaffolded += 1
            continue
        lowered = inner.lower()
        if lowered and _BRACKETED_NOUN_RE.match(inner) and not lowered.startswith("your"):
            # "[budget]" names a quantity; "[add metric]" tells the writer to act.
            if lowered.split()[0] not in _INSTRUCTION_VERBS:
                named += 1
                continue
        scaffolded += 1
    return {"total": total, "named": named, "scaffolded": scaffolded}
```

Note on the writer-instruction trigger: a bracket is scaffolding unless its
contents look like a noun phrase *and* do not begin with an instruction verb.
That single rule covers every example in the test without a second regex.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_layer3_placeholder_rules.py -q`
Expected: `26 passed`

If `test_placeholder_not_after_by_is_named` fails, the trigger is reading text
*after* the placeholder rather than before â€” check that `before` is
`text[: match.start()]` and not a window around the match.

- [ ] **Step 5: Negative control - remove the formula-variable trigger**

Temporarily change `_FORMULA_VARIABLE_RE` to `re.compile(r"^$")`, run
`python -m pytest tests/test_layer3_placeholder_rules.py -q`, and confirm
`test_formula_variable_is_scaffolding` fails. Restore the line.

- [ ] **Step 6: Negative control - remove the writer-instruction branch**

Temporarily replace the final `scaffolded += 1` fallback path so every non-
formula-variable placeholder is `named`, run the tests, and confirm
`test_writer_instruction_is_scaffolding` fails. Restore.

- [ ] **Step 7: Commit**

```bash
git add evals/layer3_judge.py tests/test_layer3_placeholder_rules.py
git commit -m "feat(evals): classify placeholders as scaffolding or named

The rubric holds no position on placeholders, so each judge invented one and
truthfulness ended up rewarding a marked blank at 10 while agency and impact
scored the same output at 0.

The classifier answers exactly one question: does this placeholder occupy a
structural slot? Three triggers from the spec -- a formula variable such as [X],
a placeholder directly after a standalone 'by', or a bracket that instructs the
writer rather than naming a quantity. Everything else is named.

Triggers read only the text immediately preceding a placeholder. A proximity
window misclassifies 'recovered by the team, recovering [N] accounts' as
scaffolding, so there is a test for exactly that.

A bracket is scaffolding unless its contents look like a noun phrase and do not
begin with an instruction verb, which keeps '[budget]' from being read as an
instruction."
```

---

### Task 2: Expose the classification as mechanical evidence

**Files:**
- Modify: `evals/layer3_judge.py:109-140` (`mechanical_evidence`), `evals/layer3_judge.py:289-307` (`build_prompt`)
- Test: `tests/test_layer3_judge.py` (modify â€” append a class)

**Interfaces:**
- Consumes: `classify_placeholders(text: str) -> dict` from Task 1.
- Produces: `mechanical_evidence(text, expectations)["placeholders"]` holding the
  Task 1 dict verbatim. `build_prompt` renders it as one line.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_layer3_judge.py`:

```python
class TestPlaceholderEvidenceIsShownToTheJudge:
    """The judge is shown what the harness found, as fact and not as an
    instruction. Spec section 4: evidence informs, and enforcement happens in
    Task 3. Putting 'do not score above 5' in the prompt would reintroduce the
    judge variance this work exists to remove."""

    def test_evidence_carries_the_classification(self):
        ev = layer3.mechanical_evidence(
            "improving [X] as measured by [Y] by [Z]",
            {"must_not_fabricate": True, "source_has_no_metric": True},
        )
        assert ev["placeholders"]["total"] == 3
        assert ev["placeholders"]["scaffolded"] == 3

    def test_evidence_is_stable_for_placeholder_free_text(self):
        ev = layer3.mechanical_evidence("Led the migration.", {})
        assert ev["placeholders"] == {"total": 0, "named": 0, "scaffolded": 0}

    def test_prompt_states_the_counts_as_fact(self):
        prompt = layer3.build_prompt(
            task={"input": "x", "judge_question": "q"},
            criterion={"key": "impact", "label": "Impact", "anchors": {}},
            evidence=layer3.mechanical_evidence(
                "improving [X] by [Y]", {"must_not_fabricate": False}
            ),
            candidate="improving [X] by [Y]",
        )
        assert "placeholders: 2 total, 0 named, 2 scaffolding" in prompt

    def test_prompt_contains_no_cap_instruction(self):
        """The prompt must not tell the judge what score to give. If it did, the
        cap would live in the prompt only and the judge could ignore it."""
        prompt = layer3.build_prompt(
            task={"input": "x", "judge_question": "q"},
            criterion={"key": "impact", "label": "Impact", "anchors": {}},
            evidence=layer3.mechanical_evidence(
                "improving [X] by [Y]", {"must_not_fabricate": False}
            ),
            candidate="improving [X] by [Y]",
        )
        lowered = prompt.lower()
        for forbidden in ("do not exceed", "cap", "maximum score", "at most"):
            assert forbidden not in lowered, (
                f"prompt leaks scoring instruction {forbidden!r}"
            )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_layer3_judge.py -k PlaceholderEvidence -q`
Expected: FAIL with `KeyError: 'placeholders'`

- [ ] **Step 3: Add `placeholders` to `mechanical_evidence`**

In `evals/layer3_judge.py`, inside the returned dict of `mechanical_evidence`
(after the `fabrication_risk` key at line 139), add:

```python
        "placeholders": classify_placeholders(text),
```

- [ ] **Step 4: Render it in `build_prompt`**

In `build_prompt`, after the `fabrication_risk` line (line 303), add one line
that states the counts and nothing else:

```python
        f"  placeholders: {evidence['placeholders']['total']} total, "
        f"{evidence['placeholders']['named']} named, "
        f"{evidence['placeholders']['scaffolded']} scaffolding\n\n"
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_layer3_judge.py -q`
Expected: all pass, including the pre-existing suite in that file.

- [ ] **Step 6: Negative control - leak a cap instruction into the prompt**

Temporarily append `" Do not score above 5."` to the prompt f-string, run
`python -m pytest tests/test_layer3_judge.py -k PlaceholderEvidence -q`, and
confirm `test_prompt_contains_no_cap_instruction` fails. Remove the sentence.

- [ ] **Step 7: Commit**

```bash
git add evals/layer3_judge.py tests/test_layer3_judge.py
git commit -m "feat(evals): show the judge what the harness found about placeholders

mechanical_evidence() gains a 'placeholders' field and build_prompt renders it
as a count, alongside the evidence the judge already sees (words, passive
markers, filler, fabrication risk).

The line states counts and nothing more. A test asserts the prompt contains no
scoring instruction, because a cap that lives in the prompt is a request rather
than a rule -- which is the failure this whole change exists to close."
```

---

### Task 3: Enforce the differentiated caps in aggregation

**Files:**
- Modify: `evals/layer3_judge.py:385-407` (`criteria_scores` assignment, `total` computation, veto)
- Test: `tests/test_layer3_judge.py` (modify â€” append a class)

**Interfaces:**
- Consumes: `criteria_scores` entries with keys `weight`, `mean`, `samples`, and
  `classify_placeholders()`.
- Produces: `apply_placeholder_cap(criterion_key: str, mean: float, placeholders: dict) -> float`.
  Later tasks and the re-measure rely only on report fields, never on this
  function directly.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_layer3_judge.py`:

```python
class TestPlaceholderCaps:
    """Spec D3. The cap is a ceiling applied to a criterion's aggregated mean,
    before the fabrication veto, so a vetoed task is unaffected."""

    CAP = 5.0

    def _run(self, candidate, judge_score, criterion_key="impact"):
        class Fixed:
            name, synthetic = "fixed", False

            def generate(self, *, skill_doc, task_input, seed):
                return candidate

            def judge(self, *, task_id, criterion, prompt, seed):
                return {"score": judge_score, "rationale": "fixed"}

        spec = {"tasks": [{
            "id": "t1", "split": "held_out", "label": "t",
            "input": "Led the migration of the legacy warehouse.",
            "judge_question": "Is the outcome stated?",
            "mechanical_expectations": {"must_not_fabricate": True,
                                        "source_has_no_metric": False},
        }]}
        rubric = {"criteria": [
            {"key": criterion_key, "label": criterion_key.capitalize(),
             "weight": 1.0, "anchors": {}},
        ]}
        result = layer3.evaluate_skill(
            "resume-bullet-writer", spec, rubric, Fixed(), "held_out", 3
        )
        return result["tasks"][0]

    # --- impact: capped whenever any placeholder is present ------------------

    def test_impact_capped_at_five_with_a_placeholder(self):
        t = self._run("cut cycle time by [N] days", 10, "impact")
        assert t["criteria"]["impact"]["mean"] == self.CAP
        assert t["score"] == self.CAP

    def test_impact_untouched_without_a_placeholder(self):
        t = self._run("Led the migration of the legacy warehouse.", 10, "impact")
        assert t["criteria"]["impact"]["mean"] == 10.0
        assert t["score"] == 10.0

    def test_impact_capped_for_a_named_placeholder_too(self):
        t = self._run("improving completion rates from [N]% to [M]%", 10, "impact")
        assert t["criteria"]["impact"]["mean"] == self.CAP

    # --- agency: capped only for scaffolding ---------------------------------

    def test_agency_capped_for_scaffolding(self):
        t = self._run("improving [X] as measured by [Y] by [Z]", 10, "agency")
        assert t["criteria"]["agency"]["mean"] == self.CAP

    def test_agency_untouched_for_named_placeholders(self):
        t = self._run("improving completion rates from [N]% to [M]%", 10, "agency")
        assert t["criteria"]["agency"]["mean"] == 10.0

    def test_agency_untouched_without_placeholders(self):
        t = self._run("Led the migration of the legacy warehouse.", 10, "agency")
        assert t["criteria"]["agency"]["mean"] == 10.0

    # --- truthfulness: never capped ------------------------------------------

    def test_truthfulness_is_never_capped(self):
        t = self._run("improving [X] as measured by [Y] by [Z]", 10, "truthfulness")
        assert t["criteria"]["truthfulness"]["mean"] == 10.0
        assert t["score"] == 10.0

    # --- the cap is a ceiling, not a floor -----------------------------------

    def test_a_low_judge_score_is_never_raised(self):
        t = self._run("improving [X] as measured by [Y]", 2, "impact")
        assert t["criteria"]["impact"]["mean"] == 2.0

    # --- ordering against the veto (spec 4.1) --------------------------------

    def test_a_vetoed_task_is_unaffected_by_the_cap(self):
        """A veto pins the task to 0.0 whatever the cap did to the criteria.
        Clamping after the veto would still read 0.0, so this asserts the
        criteria themselves were clamped and the task still landed at 0.0."""
        t = self._run("cut cycle time by [N] days and cut costs 15-20%", 10, "impact")
        assert t["fabrication_vetoed"] is True
        assert t["score"] == 0.0
        assert t["criteria"]["impact"]["mean"] == self.CAP

    def test_cap_applies_to_the_mean_not_to_each_seed(self):
        """Clamping three seeds of 10 and averaging gives 5.0; clamping the mean
        of 10 gives 5.0 too. They differ once seeds disagree: samples
        [10, 10, 4] must clamp to 5.0, not to the mean of [5, 5, 4]."""
        assert layer3.apply_placeholder_cap(
            "impact", 8.0, {"total": 1, "named": 1, "scaffolded": 0}
        ) == self.CAP
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_layer3_judge.py -k PlaceholderCaps -q`
Expected: FAIL â€” `AttributeError: module ... has no attribute 'apply_placeholder_cap'`, and the caps are not yet applied.

- [ ] **Step 3: Implement `apply_placeholder_cap`**

Add above `evaluate_skill` in `evals/layer3_judge.py`:

```python
PLACEHOLDER_CAP = 5.0


def apply_placeholder_cap(criterion_key: str, mean: float, placeholders: dict) -> float:
    """Cap a criterion score when the output's placeholders contradict it.

    Spec D3, and deliberately differentiated:

      truthfulness  no cap -- marking a blank IS the correct behaviour, and this
                    criterion exists to reward it
      impact        capped whenever any placeholder is present -- it wants a real
                    outcome value and there is none
      agency        capped only for a scaffolding placeholder -- a named one does
                    not obscure the actor, a scaffolding one occupies the action
                    slot, which is what agency measures

    A ceiling, never a floor. A criterion the judge already scored low is
    reporting a real deficiency and is left alone.
    """
    if placeholders.get("total", 0) <= 0:
        return mean
    if criterion_key == "impact":
        return min(mean, PLACEHOLDER_CAP)
    if criterion_key == "agency" and placeholders.get("scaffolded", 0) > 0:
        return min(mean, PLACEHOLDER_CAP)
    return mean
```

- [ ] **Step 4: Apply the cap to the aggregated mean**

In `evaluate_skill`, insert between the criteria loop (which ends at line 395)
and `total = round(` (line 397):

```python
        # Spec 4.1: caps apply to the aggregated mean and before the veto, so a
        # vetoed task still lands on 0.0 for the reason the veto gave it. Every
        # criterion reads the same classification object that build_prompt
        # rendered, so the prompt copy and the clamp cannot drift apart.
        for criterion in rubric["criteria"]:
            entry = criteria_scores[criterion["key"]]
            entry["mean_capped"] = apply_placeholder_cap(
                criterion["key"], entry["mean"], evidences[0]["placeholders"]
            )
```

- [ ] **Step 5: Make `total` read the capped mean**

Change `total = round(` at line 397 to read `c["mean_capped"]`:

```python
        total = round(
            sum(
                c["mean_capped"] * c["weight"]
                for c in criteria_scores.values()
                if c["weight"] > 0
            ),
            2,
        )
```

`mean_capped` equals `mean` when no cap applies, so uncapped criteria are
unchanged.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest tests/test_layer3_judge.py -q`
Expected: all pass.

- [ ] **Step 7: Negative control - make the cap unconditional**

Change `if criterion_key == "impact":` to `if True:` and delete the `agency`
branch, run `python -m pytest tests/test_layer3_judge.py -k PlaceholderCaps -q`,
and confirm `test_impact_untouched_without_a_placeholder` and
`test_truthfulness_is_never_capped` fail. Restore.

- [ ] **Step 8: Negative control - apply a blanket cap to all criteria**

Change the final `return mean` to `return min(mean, PLACEHOLDER_CAP)`, run the
same command, and confirm `test_truthfulness_is_never_capped` fails. Restore.

- [ ] **Step 9: Negative control - no-op the clamp**

Change `entry["mean_capped"] = apply_placeholder_cap(...)` to
`entry["mean_capped"] = entry["mean"]`, run
`python -m pytest tests/test_layer3_judge.py -k PlaceholderCaps -q`, and confirm
the capping tests fail. Restore.

- [ ] **Step 10: Negative control - clamp after the veto**

Move the cap loop to below the `if fabrication: total = 0.0` block, run
`python -m pytest tests/test_layer3_judge.py -k PlaceholderCaps -q`, and confirm
`test_a_vetoed_task_is_unaffected_by_the_cap` fails. Restore.

- [ ] **Step 11: Run the full suite**

Run: `python -m pytest tests/ -q`
Expected: all pass. The pre-existing count is 331.

- [ ] **Step 12: Commit**

```bash
git add evals/layer3_judge.py tests/test_layer3_judge.py
git commit -m "feat(evals): enforce differentiated placeholder caps

truthfulness is never capped -- marking a blank is the behaviour it exists to
reward. impact is capped at 5 whenever any placeholder is present, because it
wants a real outcome value and there is none. agency is capped at 5 only for a
scaffolding placeholder, since a named one does not obscure the actor.

The cap is a ceiling, never a floor: a criterion the judge already scored low is
reporting a real deficiency and is left alone.

Applied to each criterion's aggregated mean and before the fabrication veto, so a
vetoed task keeps landing on 0.0 for the reason the veto gave it rather than for
a second one. Every criterion reads the same classification object that
build_prompt rendered, so the prompt copy and the clamp cannot drift apart.

Four negative controls, each demonstrated to fail: an unconditional cap, a
blanket cap, a no-op clamp, and clamping after the veto."
```

---

### Task 4: Regenerate the reports and re-measure

**Files:**
- Modify (regenerated): `layer3-live-report.json`, `layer3-live-s3.json`, `layer3-interjudge.json`
- Modify: `docs/layer3-judging.md`

**Interfaces:**
- Consumes: the harness from Tasks 1â€“3, credentials from
  `C:\PROJECTS\PIOS\ClonU\Driftloom\Vaeloom\.env` (`OLLAMA_BASE_URL`,
  `OLLAMA_API_KEY`, `OLLAMA_MODEL`, and `LLM_API_KEY` for the second judge).
- Produces: reports whose `rubric_fingerprint` matches the shipped rubric.

- [ ] **Step 1: Confirm the staleness guard now rejects the old reports**

Run: `python evals/layer3_interjudge.py`
Expected: exit code 2 with `FATAL: ... was scored against rubric <old>, but the
current rubric is <new>`. This confirms the committed reports are stale after the
harness change, which is the guard working.

- [ ] **Step 2: Load credentials**

```powershell
$vals=@{}; Get-Content ..\Vaeloom\.env | ForEach-Object { $l=$_.Trim(); if($l -and -not $l.StartsWith('#') -and $l.Contains('=')){ $k,$v=$l.Split('=',2); $vals[$k.Trim()]=$v.Trim().Trim('"').Trim("'") } }
$base=$vals['OLLAMA_BASE_URL'].TrimEnd('/'); if(-not $base.EndsWith('/v1')){ $base="$base/v1" }
$env:OPENAI_COMPATIBLE_BASE_URL=$base
$env:OPENAI_COMPATIBLE_API_KEY=$vals['OLLAMA_API_KEY']
$env:OPENAI_COMPATIBLE_MODEL=$vals['OLLAMA_MODEL']
```

Never echo the key values.

- [ ] **Step 3: Regenerate the 3-seed report**

Run: `python evals/layer3_judge.py --backend openai_compatible --split all --seeds 3 --json layer3-live-s3.json`
Expected: exit 0 and `report written to layer3-live-s3.json`. Roughly 150 calls.

- [ ] **Step 4: Regenerate the 1-seed report**

Run: `python evals/layer3_judge.py --backend openai_compatible --split all --seeds 1 --json layer3-live-report.json`
Expected: exit 0.

- [ ] **Step 5: Verify both fingerprints match**

Run: `python -m pytest tests/test_layer3_staleness_guard.py -q`
Expected: pass. A failure here means a report was written under a different
rubric â€” regenerate rather than editing the fingerprint.

- [ ] **Step 6: Re-run the inter-judge comparison**

Run: `python evals/layer3_interjudge.py --out layer3-interjudge.json`
Expected: exit 0. Record the per-criterion mean absolute differences for
`agency`, `impact`, and `truthfulness`, and the exact-agreement count.

**Read this result as a like-for-like comparison only.** Steps 3â€“4 re-judge the
same candidates as before, because the generator also runs at
`temperature: 0.0`. This measures the caps' effect, not the rubric's
generalisability.

- [ ] **Step 7: Produce fresh candidates neither judge has seen**

Spec Â§7 forbids presenting a re-measurement on the same candidates as
validation. A non-zero temperature makes the generator sample, so the output is
new:

Run: `python evals/layer3_judge.py --backend openai_compatible --split all --seeds 3 --judge-temperature 0.4 --json layer3-fresh.json`
Expected: exit 0. Write to `layer3-fresh.json`, **not** over either committed
report â€” its scores are not comparable to them.

Then run the inter-judge tool against it:

Run: `python evals/layer3_interjudge.py --report layer3-fresh.json --out layer3-interjudge-fresh.json`
Expected: exit 0. Report `agency` and `impact` mean absolute differences and
state whether they are better, worse, or the same as the committed run.

**This is the only evidence in the plan that is independent of the observed
disagreements.** If it shows the caps did not help on unseen output, say so â€” the
rules are then wrong in a way the round-half-even fit on the old candidates
could not reveal.

- [ ] **Step 8: Check the fabrication rate has not regressed**

Run: `python evals/layer3_variance.py layer3-live-s3.json`
Expected: `per generation (mechanical): 0/30 = 0.0%`

**If this is no longer 0.0%, stop and report.** A non-zero rate means candidates
started avoiding placeholders rather than filling them honestly, which would mean
the caps made behaviour worse. That is the one outcome in this plan that must not
be committed without discussion.

- [ ] **Step 9: Update `docs/layer3-judging.md`**

Add a section recording: the three caps and where they are enforced; the
classification rule in one paragraph; the new inter-judge figures; and an honest
statement of whether `agency` and `impact` divergence fell, rose, or did not
change. Per spec Â§4.1 and D4, this phase is **not** expected to improve the
composite; state that plainly rather than presenting a flat number as progress.

Keep every existing figure in the document, including the `impact` revert
history. `scripts/check_doc_figures.py` verifies the prose against the reports in
the next step.

- [ ] **Step 10: Verify the documentation against the data**

Run: `python scripts/check_doc_figures.py`
Expected: all figures verified, exit 0. Fix any figure it reports as stale by
reading it from the regenerated reports â€” never by relaxing the checker.

- [ ] **Step 11: Commit**

```bash
git add layer3-live-report.json layer3-live-s3.json layer3-interjudge.json docs/layer3-judging.md
git commit -m "fix(evals): score placeholders under one stated policy

Regenerates both live reports under the placeholder caps and re-runs the
cross-model comparison.

Records whether the agency and impact divergence moved, in either direction.
This phase tightens the rubric and is not expected to raise the composite: the
cap exists so a placeholder cannot take the top band on a criterion that requires
a real value, and a stricter rubric can only lower scores that were previously
too generous.

The fabrication rate is reported first and is the load-bearing number. If it is
no longer 0.0%, the caps made behaviour worse rather than the scoring stricter."
```

---

### Task 5: Decide Phase 2 on evidence

**Files:** none. This task reads a number and decides whether a fifth change is
warranted.

**Interfaces:**
- Consumes: the `layer3-live-s3.json` per-criterion data from Task 4.
- Produces: a decision, recorded in the commit message or the docs, and either a
  new spec for Phase 2 or an explicit statement that Phase 2 is not needed.

- [ ] **Step 1: Inspect `resume-bullet-writer`'s remaining loss**

Run: `python evals/layer3_interjudge.py`
Expected: exit 0. Record the `agency` scores for the four `rbw-*` tasks.

**Decision rule, fixed in advance so it is not renegotiated after seeing the
result:**

- If every `rbw-*` task has `agency` at or above the cap **and** zero
  scaffolding placeholders in its candidate, the docs are already producing
  non-scaffolding output. Phase 2 is **not** needed. Record that.
- If any `rbw-*` candidate still contains a scaffolding placeholder â€” including
  bare `[X]`, `[Y]`, `[Z]` or an `[insert ...]` bracket â€” Phase 2 **is** needed.
  Do not change the document in this task. Write a new spec at
  `docs/superpowers/specs/2026-10-11-placeholder-skill-docs-design.md`, covering
  the narrowing of "a placeholder is a correct answer" per spec D1 and the
  instruction not to emit structural scaffolding, and take it through review.

- [ ] **Step 2: Report the decision**

State plainly which branch was taken and on what evidence. Do not begin Phase 2
implementation in this task.
