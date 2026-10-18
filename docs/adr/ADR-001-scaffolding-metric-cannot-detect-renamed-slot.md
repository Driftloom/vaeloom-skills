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
| `rbw-train-01` | `[Z]` | `[Method]` | `named` — not counted |
| `rbw-train-01` | — | `[N] [M] [Method]` | `named` — not counted |
| `rbw-train-02` | `[Z]` | `[N] [M]` | `named` — not counted |
| `rbw-held-01` | `[Z]` | `[N] [M] [Method]` | `named` — not counted |
| `rbw-held-01` | — | `[N] [M] [Method]` | `named` — not counted |
| `rbw-held-02` | — | `[N] [N]` | `named` — not counted |

`rbw-train-01` and `rbw-held-01` are the same two tasks that carried `[Z]` in
Phase 1. `[Method]` is the third structural slot under a different name. The
classifier scores it `named` because "method" is not one of the three literals
it recognises, no `as measured by` precedes it, and "method" is not an
instruction verb.

Criterion 2 was therefore unproven, not met.

## Why this matters more than the missed fix

Phase 1's own thesis is that a measurement blind to its own defect is
worthless. That thesis was correct, and it was violated by the metric it
produced. Concretely:

- **A `scaffolded == 0` result from this harness carries no information about
  whether the skill document is fixed.** The three tokens that define the
  metric were never a general rule for "structural slot"; they were a literal
  read of the Phase 1 template.
- **This bounds what Phase 1's merge (`5c5cf92`) can claim.** The other Phase 1
  findings — the fabrication detector, the caps, the staleness guard — are
  unaffected. The scaffolding figure specifically is now known to be
  under-counting.
- **The failure mode is reusable.** Any metric keyed to specific literal strings
  rather than to shape will silently pass when the subject renames them. The
  document-side fix cannot be validated by the metric that motivated it.

## Decision

**Fix the classifier before trusting any further scaffolding figure.**

1. `classify_placeholders` must key on shape, not on three literal names. A
   token is a structural slot if it is a bare single capital letter, or if it
   names an instruction the skill asks the model to perform (`Method`,
   `Action`, `Approach`, `Verb`) rather than a quantity. Named quantities
   (`N`, `M`, `pct`, units) stay `named`.
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