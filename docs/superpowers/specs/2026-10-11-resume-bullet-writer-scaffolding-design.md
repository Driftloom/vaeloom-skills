# `resume-bullet-writer`: Stop the Model Copying the Template

**Date:** 2026-10-11
**Status:** Draft for review
**Scope:** `vaeloom-skills` — one skill document, its guard tests, and a harness check
**Depends on:** `docs/superpowers/specs/2026-10-11-placeholder-scoring-design.md` (merged as `5c5cf92`)

---

## 1. The problem, with its evidence

`resume-bullet-writer` emits literal template slots instead of writing bullets.

From the Phase 1 live run, `rbw-train-01` produced:

```
Optimized the internal analytics dashboard used by the sales team,
improving [X] as measured by [Y] by [Z]
```

That is not coincidence. `SKILL.md` operating rule 1 read:

> **Strict Google XYZ Architecture:** Format bullets as
> `'Accomplished [X] as measured by [Y] by doing [Z]'`

and a second occurrence at the `**Structure:**` line repeated it. The model
reproduced the template slot for slot, in order, connective tissue included.
`rbw-train-01` classified at **6 of 6 placeholders scaffolding**. Two further
tasks carried the template's trailing third slot as `by [Z]` (2 of 6 each).

Measured scaffolding by task, from the Phase 1 classifier:

| Task | placeholders | scaffolded | named |
|---|---|---|---|
| `rbw-train-01` | 6 | **6** | 0 |
| `rbw-train-02` | 6 | **2** | 4 |
| `rbw-held-01` | 6 | **2** | 4 |
| `rbw-held-02` | 2 | 0 | 2 |

`rbw-held-02` is the control that proves the mechanism: same skill, same run,
**zero** scaffolding. Its trailing `by [N] hours per week` sits on a *named*
quantity, not on a template slot.

**Root cause:** the document uses square brackets as *notation*. The model reads
them as *output*. Bracket notation in a document that a model imitates is not
metanotation — it is a template.

Phase 1 capped the scores these placeholders produce. That was correct as a
diagnostic and it did not touch this, because scoring happens after generation.

---

## 2. Decisions

Four questions were put to the owner and answered.

### D1 — Remove the bracketed template; teach by example; state that a metric-free bullet is complete

Not replace the slots with an uncopyable notation (B), and not teach by example
alone (C). All three parts together.

### D2 — Scope: `resume-bullet-writer` plus a harness check

Not a sweep of the 10 skills carrying bracket notation. Eight have no evidence of
misbehaving, and editing documents on a hunch is a mistake this project has made
twice. The harness check makes the others *measurable* instead of assumed.

### D3 — Examples: a labelled no-metric category, with the exemplar taken from measured output

Labelling matters more than count. Without a label the model reads a metric-free
bullet as a weaker cousin and keeps reaching for a number. The exemplar is drawn
from `rbw-held-02`, which the judges scored **10.0** — evidence-backed rather
than invented.

### D4 — Placeholder language narrowed to the classifier's own distinction

The document currently says *"A placeholder is a correct answer. A guess is a
defect."* That now contradicts D1. It becomes the distinction the Phase 1
classifier already draws: a blank on a **named quantity** is correct and
encouraged; a blank standing for a **structural slot** is padding and must be
omitted.

---

## 3. The document changes

Three edits to `skills/resume-bullet-writer/SKILL.md`. No other file's prose
changes.

### 3.1 Delete the bracketed template

**Operating rule 1**, currently:

> **Strict Google XYZ Architecture:** Format bullets as
> `'Accomplished [X] as measured by [Y] by doing [Z]'`

becomes:

> **1. Accomplish, measure, method — only where you have them.** When the
> material is there, shape the bullet so a reader can see what was accomplished,
> how it was measured, and by what means. When a part is missing, omit that
> clause. Do not reserve a slot for data you do not have.

**The `**Structure:**` line**, currently repeating the bracketed template,
becomes:

> **Structure:** accomplishment, then measurement, then method — in that order,
> each present only if you have it.

The literal strings `[X]`, `[Y]` and `[Z]` appear nowhere in the file after this
edit. That is criterion 1 and it is asserted by a test, not by review.

### 3.2 Add a labelled no-metric example category

The existing `**Examples:**` block gains a second category under an explicit
heading, so a metric-free bullet reads as a finished shape rather than a
fallback:

> **Complete without a metric.** These are finished bullets. A result you cannot
> source is better left out than estimated.
>
> BEFORE: "Helped maintain the customer onboarding flow."
> AFTER: "Led the customer onboarding flow, cutting completion time from [N] to
> [M] days." Fill in what your records show, or send me the figures and I will.
>
> BEFORE: "Responsible for the payments platform."
> AFTER: "Owned the payments platform end to end, covering uptime, cost and
> release cadence."

Neither AFTER contains a structural slot. The first keeps `[N]` and `[M]`
because they stand in for a quantity the bullet itself names — completion time
in days — which D4 permits and which `classify_placeholders` returns as *named*.
It drops the trailing `by [Z]`, because that slot existed only to satisfy the old
template and carries no quantity of its own.

An example here that kept `by [Z]` would teach exactly the defect this phase
exists to remove, which is why the wording above is fixed rather than left to the
implementer.

The second pair carries no placeholder at all, because some achievements have no
number and pretending otherwise is the failure this phase exists to stop.

### 3.3 Narrow the placeholder language

Inside the existing **Decision Rule: No Number Available**, the sentence
*"A placeholder is a correct answer. A guess is a defect."* becomes:

> A placeholder is correct when it marks a quantity you named and do not have a
> value for — `[N]`, `[M]` on a metric you identified. It is padding when it
> stands in for a slot in a structure you never filled, and that must be
> omitted rather than bracketed.

The three-branch decision rule and its worked example from Phase 1 are otherwise
unchanged. Only that one sentence changes.

---

## 4. The harness check

Phase 1's classifier already separates the two cases; this phase adds the
assertion that uses it.

A test asserts that **no live `resume-bullet-writer` candidate contains a
scaffolding placeholder**. It runs against a regenerated report, not against
source, because the defect only exists in generated output.

- **Live criterion:** after regenerating, `scaffolded == 0` for every `rbw-*`
  task in both the committed and the fresh-candidate runs.
- **Static criterion:** a separate test asserts the document contains no literal
  `[X]`, `[Y]` or `[Z]`, so the template cannot return unnoticed between live
  runs. This one is cheap and runs in CI without credentials.

If any of the other 8 skills later emits scaffolding, the same classifier
reports it. Extending the assertion to them is a one-line change at that point,
made on evidence.

---

## 5. Acceptance criteria

| # | Criterion | Measured by |
|---|---|---|
| 1 | No literal `[X]`/`[Y]`/`[Z]` anywhere in the document | static test, CI |
| 2 | **Zero** scaffolding placeholders in any live `rbw-*` candidate | live re-run; baseline 6/6, 2/6, 2/6 |
| 3 | Fabrication stays **0.0%** | mechanical; a non-zero rate **stops the work** |
| 4 | The document's stated rule matches what `classify_placeholders` does | test asserting both directions |
| 5 | All tests green, guard test rewritten rather than removed | suite |

**Criterion 3 is a stop gate.** If fabrication rises above 0.0%, the document
changes made behaviour worse and the phase is reported, not worked around.

**Criterion 4 is held hardest.** The last branch shipped documentation
describing a classifier that did not exist — `[N]` and `[company]` documented as
scaffolding while the code returned named. The test here asserts the document's
words and the code's behaviour agree, in both directions, so they cannot drift.

**Criterion 2 is the only one that proves the model changed.** The others prove
intent. A live run is required.

---

## 6. Testing

### 6.1 Rewrite `tests/test_resume_skill_fabrication_guard.py`

It currently pins Phase 1 doc strings, including `"A placeholder is a correct
answer"` and `"is not a failed bullet"`, which §3.3 changes. It is **rewritten,
not deleted** — a guard that is removed to permit a change guards nothing after.

New invariants it pins:

- the document contains no `[X]`, `[Y]` or `[Z]`
- the document states the named-versus-structural distinction (D4 wording)
- the Phase 1 Decision Rule section still exists — its three-branch path is not
  collateral damage
- the fabrication guarantees from Phase 1 still hold: hedged ranges and
  unqualified absolutes remain forbidden by name

### 6.2 New tests

- **No literal template slots** — the §5 criterion 1 test.
- **Rule matches behaviour** — for each of the four cases §3.3 distinguishes,
  assert both what the document says and what `classify_placeholders` returns.
- **No scaffolding in generated output** — over a regenerated report, the §5
  criterion 2 test.

### 6.3 Negative controls

Each must fail a named test:

1. Re-insert the bracketed template → the no-literal-slots test fails.
2. Restore *"A placeholder is a correct answer"* unqualified → the rule-matches-
   behaviour test fails.
3. Delete the no-metric example category → the category-presence test fails.

### 6.4 Existing suite

All 440 tests must stay green. The `check_doc_figures` CI step must stay green
if any figure quoted in `docs/layer3-judging.md` changes; if the new measurement
changes one, the doc is updated from the regenerated report rather than the
checker relaxed.

---

## 7. Scope

### In scope

- `skills/resume-bullet-writer/SKILL.md` — the three edits in §3.
- `tests/test_resume_skill_fabrication_guard.py` — rewritten per §6.1.
- New tests per §6.2.
- Regeneration and re-measurement; update to `docs/layer3-judging.md`.

### Explicitly out of scope

- **The other 9 skills carrying bracket notation.** No evidence, no edit. The
  check makes them measurable instead.
- **`resume-quantifier`.** Its slots are illustrative examples showing where a
  value goes, not a mandated structure, and it produced no scaffolding.
- **Rubric, cap, and harness scoring changes.** Nothing here touches how a
  candidate is scored. That is Phase 1, merged.
- **The `craft` criterion**, still disabled at weight 0.0.

### Known risk to the plan

This may not work. The bracketed template is the obvious cause but the *second*
suspect is the "Google XYZ" framing itself, reinforced by an example set with no
metric-free member. If §3.1 alone does not reach zero scaffolding, the examples
are the driver and the method needs a deeper rewrite — which would be a new
spec, not an extension of this one.

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| Removing the template does not stop scaffolding | Criterion 2 reports it. The remaining lever is the example set (§3.2), and beyond that the method framing — flagged in §7 as a possible new spec. |
| The model over-corrects and drops legitimate named-quantity placeholders | Criterion 2 only requires zero **scaffolding**. `[N]` on a named quantity stays correct and stays allowed; the two are distinguished by the classifier, not by a blanket ban. |
| Fabrication rises as the model changes behaviour | Criterion 3 is a stop gate, not a target to trade against. |
| The document and the classifier drift apart again | Criterion 4 tests both directions. |
| The rewrite weakens unrelated Phase 1 guarantees | §6.1 keeps the Decision Rule, the range ban and the absolute-claim ban pinned. |

---

## 9. Definition of done

1. §3.1, §3.2 and §3.3 applied to `SKILL.md`.
2. `tests/test_resume_skill_fabrication_guard.py` rewritten; the new §6.2 tests
   added.
3. All three §6.3 negative controls demonstrated to fail.
4. Full suite green, including `check_doc_figures`.
5. Both reports regenerated; criterion 2 measured and reported — **including if
   it is not zero**.
6. Criterion 3 confirmed 0.0%; if not, work stops and the result is reported.
7. `docs/layer3-judging.md` updated with the new measurement, from the
   regenerated reports.
8. Committed with a message stating the measured result, not the expected one.