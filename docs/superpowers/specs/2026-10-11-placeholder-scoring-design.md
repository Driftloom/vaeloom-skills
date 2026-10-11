# Placeholder Scoring in the Layer 3 Rubric

**Date:** 2026-10-11
**Status:** Draft for review
**Scope:** `vaeloom-skills` — Layer 3 judging harness (`evals/`), rubric (`evals/layer3_tasks.json`)

---

## 1. The problem

The Layer 3 rubric has no position on what a placeholder is worth. That silence is
the single cause of the inter-judge disagreement measured on 2026-10-11.

Three layers of the system disagree about placeholders, and only one of them is
where the judge actually looks:

| Layer | Position on placeholders |
|---|---|
| `skills/resume-bullet-writer/SKILL.md` | "A placeholder is a correct answer. A guess is a defect." |
| `evals/layer3_judge.py` (`PLACEHOLDER_RE`) | Placeholders are stripped before the fabrication check, so they are exempt from the veto |
| `evals/layer3_tasks.json` (the rubric) | **Silent. Zero of four criteria mention one.** |

Because the rubric is silent, each judge constructs its own policy. Measured with
`evals/layer3_interjudge.py` over 30 criterion-task judgements:

| Criterion | Mean absolute difference between judges |
|---|---|
| `agency` | 2.50 |
| `impact` | 2.50 |
| `truthfulness` | 1.00 |

Every remaining disagreement traces to the same cause. `truthfulness` treats
marking a blank as correct behaviour and rewards it at 10. `agency` and `impact`
treat the resulting missing number as a defect and score the same output at 0.
Both readings are defensible; the rubric permits both, so nothing decides between
them.

**4 of the 10 live outputs contain a placeholder, and those are exactly the
contested judgements.**

---

## 2. Decisions

Four questions were put to the project owner and answered. They are recorded here
because the design below is only correct given all four.

### D1 — A placeholder-filled bullet is a legitimate but lesser answer

Not a complete deliverable (it is missing a value the reader needs), and not a
failure. It carries real information: which achievement, and which quantity
matters. It must never score at the top of a criterion that requires a real
outcome value.

It is explicitly **not** the case that a placeholder is a correct answer at every
level. An earlier draft of the skill documents said so; that wording is too
generous and is being narrowed by this spec.

### D2 — The harness classifies, mechanically

A placeholder's kind is decided by code, not by a judge. Delegating it to the
judges would reintroduce exactly the variance this work exists to remove.

### D3 — Differentiated caps, only where a real value is required

| Criterion | Effect of a placeholder | Rationale |
|---|---|---|
| `truthfulness` | **No cap.** A marked blank scores 10. | Crediting placeholder discipline is the criterion's job. |
| `impact` | **Capped at 5** when any placeholder is present. | The criterion wants a real outcome value. There is none. |
| `agency` | **Capped at 5 only when a *scaffolding* placeholder is present.** | A named placeholder does not obscure the actor. A scaffolding one occupies the action slot, which is precisely what `agency` measures. |

A blanket cap would wrongly suppress `truthfulness`. No cap at all would leave the
rule unenforced.

### D4 — Rubric first, skill documents second and conditional

Phase 1 changes the scoring only. Phase 2 changes `resume-bullet-writer` **only
if** a re-measure after Phase 1 shows the remaining shortfall is real rather than
an artefact of a broken instrument.

The first phase's numbers are not expected to look like progress. That is stated
here so it is not later read as a regression.

---

## 3. Classification rule

`classify_placeholders(candidate: str) -> dict` returns `{"total": int, "named":
int, "scaffolding": int}`.

Detection uses the existing `PLACEHOLDER_RE`
(`\[[^\]]*\]|\{[^}]*\}|<[^>]*>`), which already exists and is already used to
exempt placeholders from the fabrication veto. This spec adds no new placeholder
syntax.

### 3.1 Scaffolding — three triggers, any one is sufficient

A placeholder is **scaffolding** if:

1. **It is a formula variable.** Its contents match `^[XYZxyz]$`. The skill
   documents mandate the Google XYZ formula, so `[X]`, `[Y]`, `[Z]` are slots the
   formula requires to be filled by the writer's own material, not by data.

2. **It occupies a formula-governed slot.** The phrase `as measured by`
   immediately precedes it, ignoring case.

   This clause is deliberately narrow. An earlier draft also treated any
   placeholder directly after a standalone `by` as scaffolding, which
   contradicted §3.3: `"cut cycle time by [N] days"` and `"reducing manual
   effort by [N] hours per week"` are the same construction — a placeholder
   holding the *value* of a quantity the output names — and differ only in base
   verb versus gerund, which no rule restricted to preceding text can separate.
   Both are named. The bare-`by` clause existed for the XYZ case `"...by [Z]"`,
   where the placeholder is already caught by trigger 1.

3. **It is an instruction to the writer.** Its contents, lowercased, begin with
   a verb such as `insert`, `add`, `describe`, `specify`, `list`, `name`, `fill`
   — or begin with `your`.

   This is a **positive** test. A placeholder is named unless one of the three
   triggers fires. An earlier draft inferred an instruction from the *shape* of
   the characters (a noun-phrase character class), which misclassified
   `[end-to-end cycle time]`, `[Q3 pipeline value]` and `[time-to-market]` as
   scaffolding. Absence of evidence of a structural slot means the placeholder is
   holding a value, which is the common case.

   Containment of `e.g.` or `example` anywhere in the bracket is **not** a
   trigger: `[metric, e.g. 30%]` names a quantity and is named.

   Example: `[insert specific action, e.g. automated the deployment pipeline]`

### 3.2 Named — the default, when no scaffolding trigger fires

A placeholder is **named** when it is governed by a quantity the output itself
names. Concretely: strip the placeholder, and if any trigger in §3.1 fired, it is
scaffolding; otherwise it is named.

### 3.3 Worked examples

| Output fragment | Verdict | Trigger |
|---|---|---|
| `improving completion rates from [N]% to [M]%` | named (2) | none fired |
| `cutting completion time from [N] to [M] days` | named (2) | none fired |
| `reducing manual effort by [N] hours per week` | named (1) | none fired — `by` is not a trigger |
| `cut cycle time by [N] days` | named (1) | none fired — `by` is not a trigger |
| `improving [X] as measured by [Y] by [Z]` | scaffolding (3) | `[X]`/`[Y]`/`[Z]` are formula variables; `as measured by` also fires |
| `reduced spend by 15-20% through [insert specific action]` | scaffolding (1) | writer instruction |
| `Led the migration of the legacy warehouse` | none (0) | no placeholder present |

### 3.4 Explicit non-goals

The classifier does **not** attempt to judge whether the named quantity is a *good
thing* to measure, whether the placeholder is in a sensible position, or whether
the surrounding prose is high quality. Those remain the judge's work. The
classifier answers exactly one question: **does this placeholder occupy a
structural slot?**

---

## 4. Mechanism

Consistency with the existing architecture, which already splits mechanical
handling in two:

- **Inform** — `mechanical_evidence()` output is placed in the judge prompt.
  Existing examples: `words`, `within_budget`, `passive_markers`, `filler_terms`.
- **Enforce** — applied after judging, overriding the judge's score. Existing
  example: the fabrication veto.

The placeholder cap uses **both**, and must not introduce a third pattern:

1. `mechanical_evidence()` gains a `placeholders` field with the classification.
   It is rendered in the prompt alongside the other evidence, phrased as fact
   (`placeholders: 3 total, 0 named, 3 scaffolding`) with no instruction attached
   about what score to give.
2. Aggregation applies the caps from §D3 after the judge's criterion scores are
   aggregated, in the same place the fabrication veto is applied.

**Single source of truth.** The prompt copy and the clamp derive from one shared
function so they cannot disagree. A test asserts the rendered prompt text and the
clamp decision are computed from the same classification object. If the clamp and
the prompt copy ever disagree, the clamp wins silently — that is intentional, and
is the reason the shared-function test exists.

**Why the clamp is not prompt-only.** The judge is instructed not to exceed a cap
and does so anyway is the exact failure mode that produced the current 2.50/2.50
divergence. A cap that lives only in the prompt is a request, not a rule.

### 4.1 Where the cap is applied, precisely

Two things this spec must fix rather than leave to implementation:

1. **The cap applies to the criterion's aggregated mean, not per seed.** Each
   criterion's score is the mean of its per-seed samples. The cap clamps that
   mean. Clamping each seed first and then averaging could produce a different
   number, and the aggregated mean is what the report and the composite use.

2. **A fabrication vetoed task is unaffected by any cap.** The veto pins the task
   to `0.0` after the weighted sum is computed, so a cap that would have lowered
   a vetoed task from 5 to 5 is a no-op, and one that would have raised it is
   impossible — the veto is a floor of zero, applied last. Caps therefore only
   ever change the score of a task that was going to survive anyway. This
   interaction must be asserted by a test, because an implementation that clamps
   *after* the veto would appear to work and silently alter vetoed tasks.

### 4.2 Interaction with `truthfulness` and the veto

A placeholder and a fabrication are mutually exclusive by construction: the veto
fires on a digit that is not inside a placeholder, and `classify_placeholders`
only counts placeholders. So a task cannot be both placeholder-bearing and
vetoed on account of the same text. A task may still be vetoed for an unrelated
figure elsewhere in the output; §4.1 governs that case.

---

## 5. Implementation surface

| File | Change |
|---|---|
| `evals/layer3_judge.py` | Add `classify_placeholders()`. Add `placeholders` to `mechanical_evidence()` output. Render it in `build_prompt()`. Apply caps in `evaluate_skill()` after criterion aggregation. |
| `evals/layer3_tasks.json` | **No anchor wording changes in Phase 1.** The caps live in code, not in anchors — an anchor cannot enforce a cap, and putting it in an anchor would reintroduce judge variance. |
| `tests/test_layer3_judge.py` | Classifier unit tests, cap enforcement tests. |
| `tests/test_layer3_placeholder_rules.py` | New file — the classifier's own test surface. |

`craft` remains disabled at weight 0.0 and is unaffected.

---

## 6. Testing

### 6.1 Classifier

- One test per trigger in §3.1, plus one per worked example in §3.3.
- A property test that ordinary prose with no placeholder returns
  `{"total": 0, "named": 0, "scaffolding": 0}`.
- A property test that `total == named + scaffolding` for every case.
- A property test that an empty string and a string that is only placeholders do
  not raise.

### 6.2 Caps

- A candidate that the judge scores 10 on `impact` with a placeholder present
  lands at 5.
- A candidate scored 10 on `impact` with no placeholder is untouched at 10.
- A candidate scored 10 on `agency` with only *named* placeholders is untouched.
- A candidate scored 10 on `agency` with a *scaffolding* placeholder lands at 5.
- A candidate scored 10 on `truthfulness` with placeholders stays at 10 — this is
  the case a blanket cap would break.
- The cap is a ceiling, not a floor: a judge score of 2 with a placeholder present
  stays 2.
- The cap applies to the criterion's aggregated mean, not per seed (§4.1).
- A fabrication-vetoed task is unaffected by any cap (§4.1).

### 6.3 Negative controls

Each of the following must fail at least one test. A control that passes is a
vacuous test and must be fixed before the change is accepted.

1. Remove the formula-variable trigger → the worked-example test for
   `[X] as measured by [Y] by [Z]` fails.
2. Remove the writer-instruction trigger → the `[insert specific action]` test
   fails.
3. Make the `impact` cap unconditional (remove the `total > 0` condition) →
   the no-placeholder test fails.
4. Apply a blanket cap to all three criteria → the `truthfulness` test fails.
5. Make the clamp a no-op → the cap enforcement tests fail.

### 6.4 Existing suite

All 331 existing tests must stay green. The staleness guard means every committed
report must be regenerated after any change to the harness that affects scoring.

---

## 7. Validation, and the circularity problem

An earlier round in this project fitted rubric anchors to the observed
disagreements, re-ran the same judgements, and reported the improved agreement as
a result. It was an artefact: the measurement compared fresh second-judge scores
against stale primary scores. The reported improvement was partly false.

**This spec defends against that in three ways:**

1. **The classification rules are not fitted to the contested outputs.** They
   derive from placeholder syntax and from the XYZ formula the skill documents
   mandate. They were not chosen to reproduce what either judge said.
2. **Unit tests are written from the rules, not from the observed candidates.**
   §6.1 enumerates triggers; it does not enumerate "the four outputs where the
   judges disagreed".
3. **The end-to-end re-measurement must use candidates neither judge has been
   shown.** If no such candidates can be produced, that is reported as a limitation
   rather than quietly measuring on the same set again.

The `rubric_fingerprint` guard added in commit `281502f` must remain in place. Any
report whose fingerprint does not match the shipped rubric makes the
inter-judge tool exit 2; that behaviour is what caught the false result and it must
not be weakened.

---

## 8. Scope

### In scope (Phase 1)

- `classify_placeholders()` and its integration into evidence, prompt, and
  aggregation.
- The three caps per §D3.
- Tests per §6.
- Regeneration of `layer3-live-report.json` and `layer3-live-s3.json`, and an
  `layer3_interjudge.py` re-run.
- Update to `docs/layer3-judging.md`.

### Conditionally in scope (Phase 2, gated)

- `skills/resume-bullet-writer/SKILL.md`: teaching the skill not to emit
  structural scaffolding, and narrowing "a placeholder is a correct answer" per
  D1.

Phase 2 begins **only if** the Phase 1 re-measure shows `resume-bullet-writer`
still losing points to scaffolding. It is a separate commit with its own
measurement.

### Explicitly out of scope

- Changing any other skill document. `resume-quantifier` produces refusals rather
  than placeholders and is unaffected.
- Changing `truthfulness`, `impact` or `agency` anchor wording. The caps live in
  code precisely so that judge variance cannot reintroduce them.
- Re-enabling `craft`.
- Human calibration of the rubric. Still open, still the largest gap, and not
  addressable by this work.
- Extending Layer 3 beyond the two resume skills.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| The classifier mislabels an edge case and suppresses a fair 10. | It is a heuristic and is stated as one. A wrong label costs at most 5 points on one criterion, and the classification is recorded in the report so the cause is traceable. |
| Caps look blunt — a strong bullet containing one placeholder loses the top band on `impact`. | Intentional under D1: it *is* less complete. Recorded here so it is not later treated as a bug. |
| Prompt copy and clamp disagree. | Both derive from one shared function; a test asserts it. |
| The re-measure is circular again. | §7. If fresh candidates cannot be produced, the limitation is reported rather than hidden. |
| Judges learn to produce placeholder-free prose to dodge the cap, which would be a regression in honesty. | Guarded by `test_fabrication_result_is_the_load_bearing_claim`: if the mechanical fabrication rate rises from 0.0%, the change has done harm regardless of what the composite does. |

---

## 10. Definition of done

1. `classify_placeholders()` implemented and unit-tested.
2. All three caps implemented, shared-function test passing.
3. All five negative controls in §6.3 demonstrated to fail.
4. All 331 existing tests green.
5. Both committed reports regenerated under the new harness, fingerprints matching.
6. `layer3_interjudge.py` re-run; `agency` and `impact` mean absolute
   differences reported, whether or not they improved.
7. `docs/layer3-judging.md` updated, `scripts/check_doc_figures.py` green.
8. `resume-bullet-writer`'s score reported honestly, including if it did not
   improve.
