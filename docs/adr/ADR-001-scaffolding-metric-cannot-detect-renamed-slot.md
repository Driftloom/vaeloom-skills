## Amendment (2026-10-20)

An adversarial audit of this ADR found two defects in it, both corrected below.
They are recorded here rather than silently rewritten.

**1. The mechanism was stated as a symptom, not as the design it is.** The
original said `[Method]` scores `named` because `"method" is not one of the three
literals`. That is true and incomplete. `classify_placeholders`
(`evals/layer3_judge.py:99`) is a deliberate conservative design: three positive
triggers (formula variable, `as measured by`, instruction verb or `your`) with
**named as the default when none fires** — per spec section 3.1, with a source
comment asserting the list is complete. The escape class is not "any token
outside X/Y/Z"; it is **noun-headed structural slots**. Probes:

- `[Method]` → `named` — wrong, it is a slot
- `[Action]` → `named` — wrong, same class as `[Method]`
- `[pct]` → `named` — **correct**, it is a quantity

`[pct]` staying named is right, so the `named` bucket is not undiscriminated; it
is the default, and the triggers simply produce no evidence for noun-headed
slots. The completeness comment made this blind spot a documented feature.

**2. The Decision rule contradicted its own Options section.** Rule 1 proposed
an allowlist (`Method`, `Action`, `Approach`, `Verb`) — the exact pattern the
Options section rejects as fixing today's symptom. Rule 1 is rewritten below as
a requirement, not a mechanism. One further fact the original missed: `[N]` and
`[M]` are themselves bare single capital letters, so **shape alone cannot
separate a named quantity from a formula variable** — the distinction is
conventional, and any shape rule must say what it does with that.

---

# ADR-001: The scaffolding metric cannot detect a renamed structural slot

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** broh (human), Claude
- **Relates to:** `evals/layer3_judge.py` (`classify_placeholders`), Phase 1 merge (`5c5cf92`), Phase 2 branch `fix/rbw-template-scaffold`

## Context

Phase 1 of the Layer 3 rubric introduced `classify_placeholders`, which sorts
bracketed tokens in a generated candidate into two buckets:

- **scaffolded** — formula-variable tokens the model left unfilled
- **named** — tokens that read as a requested quantity, e.g. `[N]`, `[M]`

The classifier decides this by shape. A token is treated as a formula variable
only if it matches `[X]`, `[Y]` or `[Z]` case-insensitively. Phase 1 then
reported scaffolding as `6, 2, 2, 0` across the four `rbw-*` tasks, and the
`rbw-*` guard was the highest-measured defect in the pilot.

Phase 2 removed the literal `'Accomplished [X] as measured by [Y] by doing [Z]'`
template from `skills/resume-bullet-writer/SKILL.md` on the theory that the
template was being copied verbatim. Regenerating the reports returned `0` across
all four tasks, and I reported that as the intended defect being fixed.

It was not.

## The finding

The structural slot did not disappear. It was renamed.

| task | Phase 1 | Phase 2 | classifier verdict |
|---|---|---|---|
| `rbw-train-01` | `[X] [Y] [Z]` | `[Method]` | `named` — not counted |
| `rbw-train-02` | `[Z]` | `[N] [M]` | `named` — not counted |
| `rbw-held-01` | `[Z]` | `[N] [M] [Method]` | `named` — not counted |
| `rbw-held-02` | — | `[N]` | `named` — correct |

`rbw-train-01` and `rbw-held-01` are the same two tasks that carried `[Z]` in
Phase 1. `[Method]` is the third structural slot under a different name.

The mechanism, read from source rather than inferred from one probe: the
classifier fires `scaffolded` on three positive triggers only — the token is
`[X]`/`[Y]`/`[Z]`, the phrase `as measured by` immediately precedes it, or its
first word is an instruction verb or `your`. **`named` is the default when none
fires.** `[Method]` gets no positive evidence (it is not a formula variable, no
`as measured by` precedes it, `method` is not an instruction verb), so it falls
to the default. `[Action]` falls identically. This is per spec section 3.1,
whose source comment calls the trigger list *complete*.

Criterion 2 was therefore unproven, not met.

## Why this matters more than the missed fix

Phase 1's own thesis is that a measurement blind to its own defect is
worthless. That thesis was correct, and it was violated by the metric it
produced. Concretely:

- **A `scaffolded == 0` result from this harness carries no information about
  whether the skill document is fixed.** The triggers that define the metric
  produce no evidence for noun-headed structural slots, and `named` is the
  default — so an unfilled slot under any noun head counts as a filled one.
- **The escape class is general, not specific to this rename.** `[Method]` and
  `[Action]` escape today; the next document could use `[Role]`, `[Tool]`,
  `[Approach]` tomorrow. Any metric with a default-on-no-evidence rule passes
  whatever the subject renames, as long as the rename avoids the trigger words.
- **This bounds what Phase 1's merge (`5c5cf92`) can claim.** The other Phase 1
  findings — the fabrication detector, the caps, the staleness guard — are
  unaffected. The scaffolding figure specifically is now known to be
  under-counting.
- **The failure mode is reusable.** Any metric keyed to specific literal strings
  rather than to shape will silently pass when the subject renames them. The
  document-side fix cannot be validated by the metric that motivated it.

## Decision

**Fix the classifier before trusting any further scaffolding figure.**

1. `classify_placeholders` must catch noun-headed structural slots. The current
   rule produces no positive evidence for them, so they fall to the `named`
   default. The mechanism is deliberately unspecified here; the requirement is
   that the next rename cannot escape silently. Any rule must hold all of:
   `[N]`, `[M]` stay `named` (they are bare single capitals too, so shape alone
   cannot separate them from `[X]`); `[pct]`, `[time-to-market]` and other
   quantity references stay `named`; and the char-shape inference that
   misclassified `[time-to-market]` as scaffolding (the reason the default
   exists) must not return.
2. The `rbw-*` guard test must assert **absence of slot-shaped tokens**, not
   `scaffolded == 0`. A test that passes only when the metric is working is
   not a test of the skill.
3. Until (1) and (2) land, no `scaffolded` figure from this harness may be cited
   as evidence that a document change succeeded.

The guard helper in `tests/test_resume_skill_fabrication_guard.py` must widen
its scan beyond `resume-bullet-writer`; the module docstring already scopes two
documents but only one is scanned.

## Options considered

- **Rename-aware allowlist only** (add `Method` to the recognised set). Rejected:
  it fixes today's symptom and leaves the class of defect open. The next rename
  fails identically and silently.
- **Lower `scaffolded` counts by document inspection only.** Rejected: this is
  what produced the current blind spot. Automated scoring must be able to see
  the thing the guard test asserts.
- **Retire the scaffolding dimension entirely.** Rejected: the defect is real and
  recurring; retiring the metric would hide it rather than fix it.

## Consequences

- Phase 2 branch `fix/rbw-template-scaffold` **must not be merged on the strength
  of its measurement**. The document edits may still be worthwhile, but the
  evidence for them does not currently exist. Salvaging the guard-test work
  (converting presence-only assertions to absence assertions) is independent of
  this and should be kept.
- The fabrication result (`0/30` → `2/30 = 6.7%`) is **unaffected** by this
  finding — it is a different classifier, keyed on figure shapes rather than
  placeholder names. That regression is real.
- A correction is owed to `docs/layer3-judging.md`, which must state the
  scaffolding figure is under-counting and cite this ADR.

## Follow-up

Scoped to Phase 1, not to Phase 2. Requires its own branch and its own review.
The gate on starting it: this ADR merged, so that no later reader revives
`[Method]` as an acceptable named quantity.

## Adopted mechanism (2026-10-21)

The follow-up was executed on this branch rather than a new one, by explicit
user direction ("extend and push and merge"), which waives the separate-branch
step above; it was not waived lightly, and this note is what remains of the
review that would otherwise have happened there.

Trigger 4 was added to `classify_placeholders`
(`evals/layer3_judge.py`): the contents are a schema label when they match
`^[A-Z][a-z]+$` -- one capitalized word of two or more letters. The narrowed
shape is the whole point of this ADR:

- single letters (`[N]`, `[M]`) stay named -- single-character blanks are the
  document's own vocabulary, and all-caps acronyms stay named because a
  writer chose them;
- lowercase words stay named, including multi-word and hyphenated ones --
  the class the earlier phrase-structure rule died on (`[time-to-market]`);
- only the capitalized-word shape is taken, which is exactly the shape the
  rename gave the slot (`[Z]` -> `[Method]`); no phrase-structure inference
  returns.

The trade-off is recorded, not resolved: a filled quantity written in
capitalized-word form (`[Uptime]`) will read as scaffolding. The rubric's own
blank style is single letters and lowercase metric names, so the rule errs
toward catching the escape class that hid `[Method]`.

Provenance traced while tracing the miss, and worth keeping: the committed
outputs carry `[Method]` even though neither `evals/layer3_tasks.json` nor the
document's brackets contain it. The document teaches "accomplishment, then
measurement, then method" and keeps `[N]`/`[M]` as its only blank vocabulary;
the model volunteers the third leg as `[Method]` in that same register when
the method is missing. The rename never lived in a file -- it is the model
completing the schema the document describes.

Regression coverage: the renamed slot, the doubled ask-the-user note, four
further label shapes, and the four named-protection classes
(`[method]`, `[QA]`, `[Continue for each bullet...]`, `[99.9%]`).
Because the trigger participates in `scoring_fingerprint`, the committed
reports are stale against the new policy, and regeneration is the next step
before any figure in `docs/layer3-judging.md` may be updated.

## Outcome of the adopted mechanism (2026-10-21, after regeneration)

Trigger 4 was added and **both live reports were regenerated** against the
OpenAI-compatible endpoint (~200 live calls). The renamed slot now measures:

- `rbw-train-01` echoes `[Method]` in all three seeds; the worst case classifies
  **2 scaffolded** slots (seed 1) and the fabrication veto pins the task to 0.0
  in every seed.
- `rbw-held-01` echoes it in seed 0 (1 scaffolded); the other two `rbw` tasks
  carry none. Two of four `rbw` tasks carry the defect.

The criterion's verdict is still **unmet** — the slot is real, and closing it
needs the document to stop teaching a third leg ("accomplishment, then
measurement, then method"), not another classifier trigger.

Headline figures moved from the first post-edit measure (3.56 mean / 4.74
unvetoed / gap 2.92 / swing 0.29) to the regenerated state (4.12 / 5.49 /
2.36 / 0.0). The swing floor is zero — the provider came back deterministic at
temperature 0.0 — so `ordering_supported` is vacuously True and
`gap_over_swing` is `None`; the ratio is a division by zero and is quoted as
undefined. The 3.56 → 4.12 movement between the two measures is not
attributable: both are fresh samples from a deterministic endpoint whose
earlier instability did not reproduce, so it records measurement noise.

Fabrication measured the same **2 of 30 (6.7%)** independent of the classifier
change: `rbw-train-01` seeds 0 and 2. The regression coverage above is what
made the diagnostic possible; without trigger 4 the regeneration would have
repeated the blind zero and no "unmet" could have been distinguished from
"unmeasured".