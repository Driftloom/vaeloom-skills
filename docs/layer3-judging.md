# Layer 3: Rubric-Anchored Judging

Layer 1 scores file structure. Layer 2 exercises helper scripts. **Neither can
say whether a skill document, followed by a competent model, produces a good
resume bullet.** This layer can, and is the prerequisite for SkillOpt, which
optimises against exactly this kind of signal.

> **Status: measured live against `gemma4:31b` via the provider's OpenAI-compatible
> endpoint.**
> Overall **5.30/10** at 3 seeds across 2 skills — **5.98/10 with the 2
> fabricating generations excluded**, because the plain mean misattributes
> their damage to prose quality. **6.7% of generations fabricate** (2 of 30).
> The anchors are written, not calibrated against human raters, so this is a
> first reading rather than a baseline. See the two sections below for what the
> number does and does not support.
>
> **These figures are from the Phase 2 branch run ("The Phase 2 run and what it
> actually proved", below), regenerated after ADR-001 added trigger 4 to the
> placeholder classifier.** They describe the `resume-bullet-writer` document
> *after* its template-removal edit, and that edit is not validated: the
> renamed third slot now measures — `[Method]` appears in 2 of 4 `rbw` tasks
> (worst case 2 scaffolded slots on `rbw-train-01`) — and fabrication rose
> from 0 of 30 to 2 of 30, vetoing the same task in every seed. The branch
> stopped at its own gate. Nothing in this header is a claim that the document
> change succeeded.
>
> **Regenerated under the placeholder caps (see "One stated placeholder
> policy").** A second model family agrees on **76%** of judgements. On fresh
> candidates neither judge had seen, agreement was **67%** and `impact`
> divergence rose to **3.00** — the caps did not generalise.
>
> An earlier revision of this header read **4.78/10** and **33% of generations
> fabricate**, directly above a line stating fabrication was **0.0%**. Neither
> stale figure matched any committed report; both are retracted here rather
> than left for a reader to reconcile.
>
> A previous revision of this file stated that no provider credentials were
> configured and that every run was synthetic. That was wrong: the keys live in
> the API app's `.env` (`OLLAMA_BASE_URL`, `OLLAMA_API_KEY`, `OLLAMA_MODEL`), which
> `config.py` loads. The mistake was checking only process environment variables
> and concluding the repository had no keys. The synthetic path remains the only
> one CI can run, so both are documented separately.

## The two skills chosen

`resume-bullet-writer` and `resume-quantifier`. Both are **prose-only** — no
helper script, therefore zero Layer 2 coverage — yet both have a crisp,
checkable output: one bullet.

`resume-quantifier` is the sharper test. Its entire purpose is turning
unquantified text into quantified text, which makes **fabrication the single
highest-severity failure mode**. A judge that rewards confident-sounding output
would make this skill worse.

Each has 2 `train` and 2 `held_out` tasks. Splits are disjoint; only `held_out`
may support a quality claim.

## Pipeline

```
SKILL.md  ──┐
            ├─► generate(seed) ──► candidate ──► mechanical evidence ──► judge(seed)
task input ─┘                     │                      │                    │
                                  └──────────────────────┴────────────────────┘
```

**Generation is a separate, required step.** The first version of this harness
passed the task input as *both* the source text and the candidate output, so the
judge graded the input against a rubric written about outputs and measured
nothing. `test_prompt_scores_the_generated_candidate_not_the_input` is the
regression guard.

## What the first live run found

Run once with `--seeds 1`, 4 tasks per skill, 40 calls, ~70 s:

| Skill | Mean | Range |
|---|---|---|
| `resume-bullet-writer` | 5.44/10 | 0.0 – 10.0 |
| `resume-quantifier` | 3.68/10 | 0.0 – 10.0 |

**The fabrication veto fired on 3 of 8 tasks.** Those were correct, not false
positives: the model wrote *"ensuring **100%** data integrity"* and *"reduced
spend by **15-20%**"* where the source contained no metric at all. Inventing
quantities is exactly what `resume-quantifier` exists to do, so **its own
instructions induce its failure mode.** Any fix has to address the skill text,
not just the judge.

Two flaws in the instrument surfaced here, both from reading the output rather
than trusting it.

**The detector vetoed placeholders.** `Managed the migration of [X]TB … reducing
latency by [X]%` scored `0.0` with `truthfulness` at 10 — punished *for marking
the blanks correctly*. It fired on any digit, so `[10]%` would have failed the
same way. Placeholders are now stripped before the check, which lifted
`resume-quantifier` from 0.00 to 4.25 on the held-out split.

**The `craft` criterion was not measuring craft.** Across **32 live judgements on
8 tasks it returned a constant 0/10**, while `agency` and `impact` spanned
`[0, 5, 10]` and `truthfulness` spanned `[0, 10]`. Worse, two of its rationales
objected to *fabricated claims* — `truthfulness`'s job — on the same artifact
`truthfulness` had scored 10. Rewriting the anchors to be purely about economy
did not change the output, which rules out wording and indicates **criterion
bleed**: the judge reasons globally about the artifact and re-emits the same
complaint regardless of which criterion it is scoring.

A constant criterion subtracts weight from every score and informs nothing, so it
is disabled and the remaining three renormalised to sum to 1.0. It is retained in
`layer3_tasks.json` with the evidence rather than deleted, so it can be reinstated
alongside a mechanical implementation or a stronger judge. The harness now
reports **any zero-variance criterion on every run**, weighted or not, so this
failure mode cannot hide again. Re-enabling `craft` fails
`test_craft_is_disabled_on_live_evidence`.

## How much of the score is signal

A single judged number is not a result, so the same 8 tasks were re-run at
`--seeds 3` — 120 calls, 181 s. The harness flagged both skills
*"criterion seeds disagreed; treat the mean as unreliable"*, which is why
`evals/layer3_variance.py` exists:

```
python evals/layer3_variance.py layer3-live-s3.json --compare layer3-live-report.json
```

| | 1 seed | 3 seeds | shift |
|---|---|---|---|
| `resume-bullet-writer` | 5.81 | 6.13 | +0.32 |
| `resume-quantifier` | 6.47 | 6.47 | 0.00 |
| **Overall** | **6.14** | **6.30** | **+0.16** |

*The table above records the Phase 1 re-run, a superseded measurement: both
live reports have since been regenerated twice, and the current reports agree
exactly (1-seed and 3-seed both read 4.1175 for `resume-bullet-writer`, see
"`--seeds` at temperature 0.0" below).*

These two runs no longer agree exactly: the 1-seed report gives
`resume-bullet-writer` **5.81** where the 3-seed report gives **6.13**. The
earlier revision of this table read 6.11 against 6.11 with a 0.00 shift and
called that agreement a working reproducibility check. Re-running the same
commands did not reproduce it — see "The determinism claim in this document no
longer holds as written" below, which records the same finding from the other
direction. `--seeds` is not a variance estimate at this temperature, so the
spread between these two runs was generator instability, not sampling error.

The task set grew from 8 to 10 once the fix landed — see the section on the sourced-number
tasks below, which exist because a 0% fabrication rate is also what a broken skill
would report.

- **On the Phase 1 re-run, ordering was not supported.** The gap was 0.34 against
  a seed-to-seed swing of 0.66 — a ratio of 0.5×, so the gap was inside the
  noise. On the regenerated Phase 2 reports the gap is **2.36** against a swing
  of **0.0** and a ratio that is undefined (division by zero): when the seeds
  stop moving, the ordering flag flips True vacuously, which is not a ranking
  signal. The first Phase 2 measure (2.92 against 0.29, ratio 10.0×) sat after
  the `resume-bullet-writer` document edit, so that gap partly measured the
  edit. See "The Phase 2 run and what it actually proved".
- **The judge was not self-consistent on the Phase 1 re-run.** 1 of 30
  criterion-task pairs returned the full `0`–`10` range (`rbw-train-01` `agency`,
  samples `[5.81, 6.47, 6.11]` at the skill level and `[0, 10, 0]` on the
  criterion), against 0 of 30 on the previous run and 2 of 24 before the skill
  documents changed. On the regenerated reports the full-range rate is
  **0.0%** (0 of 30). Note this is *self*-consistency; the cross-model
  comparison below is the harder test.
- **Fabrication was 0.0% per generation on the Phase 1 re-run** (0 of 30), down
  from 25.0% (6 of 24). On the regenerated reports it is **6.7%** (2 of 30) —
  the document edit moved fabrication, see the Phase 2 section.

### `--seeds` at temperature 0.0 is a reproducibility check, not a variance sample

The live judge is called at `temperature: 0.0`, and what `--seeds` measures has
flip-flopped with the provider across revisions. All three states are on
record so the next revision cannot misread either direction:

1. **First revision (flat).** Per-seed skill means `[6.11, 6.11, 6.11]` and
   `[6.47, 6.47, 6.47]` with no criterion moving at all, and that was reported
   as an exactly repeatable run.
2. **Second revision (variability).** The same commands re-run during the
   Phase 2 regeneration produced `[5.81, 6.47, 6.11]` for
   `resume-bullet-writer` — 4 of 40 criteria varying across seeds — against
   `[6.47, 6.47, 6.47]` for `resume-quantifier`, and an earlier revision of
   this document correctly retracted the exact-repeatability claim then.
3. **Current reports (flat again).** After ADR-001 added trigger 4 and both
   live reports were regenerated, every per-seed mean is identical —
   `[4.1175, 4.1175, 4.1175]` for `resume-bullet-writer` and
   `[6.4733, 6.4733, 6.4733]` for `resume-quantifier` — and the 1-seed mean
   equals the 3-seed mean to four decimals. Two criterion-task pairs are
   flagged unstable (`rbw-held-01` `agency`, `rq-sourced-01` `craft`), but
   none of that moves a score.

The provider's behaviour at temperature 0.0 is therefore not a property of the
rubric or the prompt; the same endpoint produced three different stability
profiles across revisions, so determinism is observed per run, not assumed.
`--judge-temperature > 0` exists so that the judge's distribution can be sampled
when it is wanted, and `test_judge_temperature_is_carried_into_the_request`
pins that the flag reaches the request rather than being a constant.

The between-skill gap is now **2.36** with a seed swing of **0.0**. Ordering
support flips to `True` mechanically whenever the swing floor collapses, so it
carries no ranking information under this endpoint — which is why no ordering
is asserted anywhere in this project.

An earlier revision of this document claimed a single seed understated fabrication
(`7.35` against `5.64`). That was a genuine observation, but it was an artefact of
which of the two committed reports happened to be regenerated when, not a property
of the seeds. It is not repeated here as a finding.

## The headline mean was measuring the wrong defect

A vetoed task is pinned to `0.0` however well it scored. That conflates
"writes badly" with "invents figures", and on the pre-fix run the conflation was
the result:

| Skill | overall | unvetoed | n | delta |
|---|---|---|---|---|
| `resume-bullet-writer` | 5.64 | **7.52** | 3 | −1.88 |
| `resume-quantifier` | 3.58 | **7.16** | 2 | −3.58 |

Both skills write at roughly 7/10 and both invent figures. Reporting only the
overall mean would have said these are bad writers and sent the fix at the wrong
thing. The fabrication rate is therefore the primary metric, and the harness and
analyser both print the split; `headline_mean_misattributes_fabrication` turns
the ≥1.0 gap into a flag so no future report can quietly hide it.

That split is now empty, and the current run shows why the flag still earns its
place. With no vetoes the two views cover the same tasks, so nothing is
separated: `resume-bullet-writer` reads **6.25** overall and **6.25** unvetoed,
`resume-quantifier` **6.47** against **6.47**.

Those are the **capped aggregate** — the mean of the task scores, which is what
`mean_score` holds in the report and what the harness CLI prints as "overall".
The variance analyser prints a *different* composite for the same report, and
the two are routinely mistaken for one figure:

| | `resume-bullet-writer` | `resume-quantifier` |
|---|---|---|
| **Capped aggregate** (`mean_score`, mean of task scores) | **6.25** | **6.47** |
| **Per-seed counterfactual** (analyser's `skill_means`: mean of `mean(score_by_seed)`) | **6.13** | **6.47** |

They differ by design. The harness caps a criterion's aggregated mean and then
averages the task scores; the per-seed view reads one generation at a time
through the same caps. The first is the number the tasks actually scored; the
second is the swing between generations. Neither is a decomposition of the
other, and neither is wrong.

`layer3_interjudge.py` compares a third thing again — raw `samples[0]`, the
uncapped judge score — and so **cannot see the caps at all**. Every figure in
the inter-judge tables below is that third view.

The figure that is still discriminating is the mechanical one: **3.3%** of
criterion-task pairs span the full `0`–`10` range across seeds, up from 0.0% on
the previous run, concentrated in `agency` on placeholder scaffolding.

`test_vetoed_work_is_reported_separately_from_writing_quality` scores a clean task
`10.0` and a fabricating task `10.0`, and requires `5.0` overall against `10.0`
unvetoed — so the two views cannot collapse into one.

The denominator matters more than it looks. The first analysis compared the
between-skill gap against per-task criterion spread (0–10) and concluded the
difference was unresolvable. That was the wrong denominator — it compares a
difference *between* skills with the spread *within* a single judgement. The
correct comparison is gap against seed-to-seed swing of the mean, which supports
the ordering. `test_gap_is_measured_against_the_swing_of_the_mean` pins this, with
a control that produces the same gap by a different route and must be rejected.

The analyser also had an inverted guard: it reported an ordering as *unsupported*
when seed swing was zero, treating perfect repeatability as absence of evidence.
Restoring that bug fails 3 tests.

## Closing the defect the measurement found

The 25.0% fabrication rate was not a model problem or a judge problem. Both skill
documents **required a number and forbade inventing one, with nothing resolving
the conflict**, and the model resolved it by inventing one:

- `resume-bullet-writer` operating rule 3 read *"Require specific numbers,
  percentages, time savings, or dollar amounts in every bullet"* while rule 6 read
  *"Never invent metrics."*
- `resume-quantifier` rule 2 licensed *"conservative, defensible estimates"*
  without defining what makes one defensible, so any plausible range passed rule 5.

Observed fabrications included *"increasing completion rates by 15% (from 70% to
85%)"* and *"ensuring 100% data integrity"* — both from inputs containing no
figure at all.

Each document now resolves the no-number case explicitly:
`resume-bullet-writer` has a **Decision Rule: No Number Available** with a
three-branch path ending in a placeholder plus a request, and forbids hedged
ranges and unqualified absolutes by name; `resume-quantifier` has a **Derivation
Test** requiring every figure to be traceable to a stated input with its
arithmetic shown, and forbids recall, convention and industry benchmarks.

Re-measured on the same tasks: **fabrication 25.0% (6/24) → 0.0% (0/30)**, overall
**4.61 → 7.21**.

### The 0% is only meaningful because of the two sourced-number tasks

A skill that simply refused to emit any figure would also score 0% here, so two
tasks were added that **supply** the numbers. `rq-sourced-01` gives
*"from 480ms to 120ms"* and `rq-sourced-02` gives *"40TB"* and *"4s to under 1s"*.
Both score high, and the transcripts show extraction and derivation rather than
refusal:

> Reduced p99 query latency on the payments API from 480ms to 120ms, a 75%
> reduction (derived: (480-120)/480).

> Migrated 40TB of warehouse data and reduced query latency from 4s to under 1s,
> an estimated 75% reduction (derived: (4-1)/4)

`rq-sourced-02` scores 8.43 rather than 10 because `under 1s` makes the true
reduction *greater* than 75% and the judge caught the imprecision — evidence the
rubric still discriminates rather than having gone flat.

The two decision rules are pinned by
`tests/test_resume_skill_fabrication_guard.py` (14 tests). A removed rule is
silent: the document still reads well and the score quietly regresses, so
restoring the old operating rule fails the suite.

## The Phase 2 run and what it actually proved

Phase 2 removed the literal `'Accomplished [X] as measured by [Y] by doing [Z]'`
template from `resume-bullet-writer` — candidates had been copying it verbatim —
and rewrote the placeholder guidance. The criteria have now been measured
three times: the Phase 1 baseline, a first post-edit measure under a classifier
blind to noun-headed slots (ADR-001), and a regeneration after trigger 4 was
added (both live reports regenerated, ~200 live calls). After the
regeneration, **one criterion is measured but unmet, one regressed on both
measures, and the stop gate still holds.**

| | Phase 1 (pre-edit) | Phase 2, first measure (blind classifier) | Phase 2, regenerated under trigger 4 |
|---|---|---|---|
| 1-seed mean, `resume-bullet-writer` | 5.81 | 3.46 | **4.12** |
| 3-seed mean, `resume-bullet-writer` | 6.13 | 3.56 | **4.12** |
| per-seed means, `resume-bullet-writer` | `[5.81, 6.47, 6.11]` | `[3.46, 3.46, 3.75]` | **`[4.12, 4.12, 4.12]`** |
| unvetoed mean, `resume-bullet-writer` | 6.25 | 4.74 | **5.49** |
| between-skill gap / swing / ratio | 0.34 / 0.66 / 0.5× | 2.92 / 0.29 / 10.0× | **2.36 / 0.0 / — (undefined)** |
| fabrication per generation | 0 of 30 (0.0%) | 2 of 30 (6.7%) | **2 of 30 (6.7%)** |
| fabrication, task level | 0 of 10 | 10.0% | **10.0%** |

Reading the table honestly:

- **Criterion 2 (scaffolding eliminated) is now measured — and still unmet.**
  Trigger 4 catches the renamed slot in the fresh outputs: `rbw-train-01`
  echoes `[Method]` in all three seeds (worst case **2 scaffolded** of the
  task's slots, on seed 1) and `rbw-held-01` echoes it in seed 0 (1); the
  other two `rbw` tasks carry none. The slot comes from the document's own
  prose — "accomplishment, then measurement, then method" — so the
  template-copying defect moved into a rename the model completes itself. The
  defect is real and now on the record; fixing it needs the document to stop
  teaching a third slot, not another classifier trigger.
- **Criterion 3 (fabrication stays 0.0%) regressed on both measures.** The
  fabricating generations volunteer example figures inside the parenthetical
  they use to ask the user for numbers — *"Fill in [N] and [M] (e.g., \"data
  accuracy by 20%\")"*. Removing the template moved fabrication out of the
  bullet and into the ask. The fresh run locates them exactly: `rbw-train-01`
  seeds 0 and 2, so the fabrication veto pins the task to 0.0 in all three
  seeds — the plain mean reads 4.12 where the unvetoed mean reads 5.49.
  Earlier this ledger attributed the rise to a document instruction to supply
  examples; the document contains no such instruction, and that claim is
  retracted — the cause is imitation of the exemplars' density, not a rule the
  document states.
- **The overall judged quality fell hard on both measures.** From Phase 1's
  6.13 to **4.12** (unvetoed: 6.25 to **5.49**). One task is vetoed in
  every seed (task-level rate 10.0%), which drags the plain mean, but the
  unvetoed figure also falls on its own. Whatever the document edit did, by
  the rubric's own measure it made the skill worse.
- **The 3.56 → 4.12 difference between the two post-edit measures is not
  attributable.** Both are fresh samples from a deterministic endpoint whose
  earlier instability did not reproduce (see "`--seeds` at temperature 0.0"),
  so that swing records measurement noise, not a change in the document.
- **The ordering is no signal.** The gap is 2.36 against a swing of 0.0 — a
  zero denominator makes the ratio undefined and flips `ordering_supported`
  True vacuously. (The first measure's 2.92 against a real 0.29 swing still
  measured the edit, not the skills.) No ranking is asserted from these
  reports.

The evidence lives in `layer3-live-s3.json` and `layer3-live-report.json`
(committed after the regeneration). Per ADR-001 as amended, `scaffolded`
figures from this harness may now be cited; the criterion's own verdict is
unmet, and the 2-of-4 task coverage is the honest reading of it.

## How much of this survives a different judge?

Self-agreement at `temperature 0.0` is trivially perfect and proves nothing about
whether the rubric is *right*. `evals/layer3_interjudge.py` re-judges the same 30
committed candidates with a second model family and reports the divergence:

```
python evals/layer3_interjudge.py --out layer3-interjudge.json
```

| | before | after |
|---|---|---|
| judgements compared | 30 | 30 |
| exact agreement | 15/30 (50%) | **22/30 (73%)** |
| mean absolute difference | 3.33 / 10 | **1.83 / 10** |
| worst difference | 10 | 10 |

| Criterion | before | after |
|---|---|---|
| `truthfulness` | 1.00 | 1.00 |
| `impact` | 2.00 | 2.00 |
| `agency` | **7.00** | **2.50** |

`agency` improved from 7.00 to 2.50 and both original failure modes are fixed:

- A refusal (`"I don't have figures for this one—send me…"`) no longer scores 10
  for agency under either judge. The old 10 anchor read *"the actor and the action
  are unambiguous in the first clause"*, and a polite request satisfies that
  literally: the actor is `I`, the action is `send me`. It is not an achievement.
- A conventional achievement bullet no longer gets capped at 5. The old 5 anchor
  read *"agency is implied but not stated"*, and every resume bullet omits the
  subject by convention. The anchor was punishing the convention, not a defect.

The rewritten anchors separate three things the old ones conflated: whether the
output is an achievement at all, whether the actor is obscured, and whether
ownership is unmistakable given that the subject is conventionally omitted.

### An earlier version of this section reported a false 0.00

An intermediate revision of this document claimed `agency` reached **0.00** —
perfect agreement on all ten judgements — and 86% overall. **That measurement was
wrong and the claim is retracted.**

`evals/layer3_interjudge.py` re-judges with the *current* anchors but reads the
primary judge's scores out of a report generated under the *previous* anchors.
The divergence it reported was therefore the difference between two rubrics, not
between two judges. The new agency anchors happened to reproduce exactly what the
old ones had produced, so primary and second agreed by coincidence.

Re-measured with both sides on the same rubric, `agency` is **2.50**, not 0.00.
The rewrite was still worth doing — 7.00 → 2.50, and overall 50% → 73% — but it
was credited with a result it did not produce.

The report did not record which rubric produced its scores, so nothing could
detect this. `evals/layer3_judge.py` now stamps a `rubric_fingerprint` into every
report, and `layer3_interjudge.py` **exits 2** rather than compare across rubrics.
`tests/test_layer3_staleness_guard.py` covers both rejections and asserts that
both committed reports match the shipped rubric — it caught the 1-seed report
stale on the first run.

### `impact` was rewritten, measured, and reverted

Its anchors looked equally conflated, and the primary judge was self-inconsistent
on identical input — it gave one placeholder bullet a 5 and three others 0. A
rewrite was implemented and measured against the acceptance criterion:

| config | agreement | mean \|delta\| | agency | impact | truthfulness |
|---|---|---|---|---|---|
| `impact` old | 73% | **1.83** | 2.50 | 2.00 | 1.00 |
| `impact` new | 73% | 2.00 | 2.50 | **1.50** | **2.00** |

The new `impact` anchors moved `impact` down 0.50 but pushed `truthfulness` up
1.00, and the composite got worse. They also caused refusals to score 5 — the new
5 anchor described a request for figures as "names what changed but leaves the
value unsupplied". Reverted. A criterion is not improved because its own number
moved in the right direction.

### What remains open

| Criterion | mean \|delta\| | note |
|---|---|---|
| `agency` | 2.50 | the disagreement is now direction: primary reads placeholder scaffolding as unstated agency (0) where the second reads it as unmistakable (10) |
| `impact` | 2.00 | primary reads it as *"was a metric present"*; second reads the placeholder as a named-but-unspecified outcome |
| `truthfulness` | 1.00 | one 10-point flip remains, and there it is the second judge that is wrong — it read `[N]% to [M]%` as a claim rather than a marked blank |

All three disagreements now point at the same root: **the rubric has no shared
understanding of what a placeholder is worth.** `truthfulness` treats marking a
blank as correct behaviour, `agency` and `impact` treat the resulting
missing-number as a defect. Rather than tune three anchors independently, the
next change should state once, in the rubric, how a placeholder is scored across
criteria. That is a design question, not a third round of anchor editing.

This remains the largest calibration gap and it is **not** closed. What exists
now is the measurement of it, so the ambiguity is a known number rather than an
assumption.

## One stated placeholder policy, and what re-measuring it did

The ambiguity above is answered by stating one rule rather than by a third
round of anchor editing.

### The classification rule

`classify_placeholders` (`evals/layer3_judge.py`) reads each `[...]` span and
asks one question: **does this placeholder occupy a structural slot, or is it
holding a value?** Four triggers make it `scaffolded`, any one is sufficient,
and **`named` is the default when none fires**:

| # | Trigger | Example |
|---|---|---|
| 1 | The contents are a formula variable — `^[XYZxyz]$` | `[X]`, `[Y]`, `[y]` |
| 2 | The phrase `as measured by` immediately precedes it, ignoring case | `improving throughput as measured by [the metric]` |
| 3 | The first word is an instruction verb (`insert`, `add`, `describe`, `specify`, `list`, `name`, `fill`, `enter`, `replace`, `provide`, `detail`, `quantify`, `write`, `state`) or is `your`. Punctuation is stripped from both ends of the word first, so `[Insert: the metric]` is recognised. | `[insert specific action]`, `[your e.g. example here]` |
| 4 | The contents are a schema label — one capitalized word of two or more letters, `^[A-Z][a-z]+$` | `[Method]`, `[Action]` — added by ADR-001 |

**`named` is the half that does the work.** Scaffolding needs positive evidence
of a structural slot. A rule that inferred a noun from the bare presence of
*capitalization* would classify `[Q3 pipeline value]` or
`[time-to-market]` as scaffolding — misreading a real quantity as a blank.
Trigger 4 borrows only the capitalized-word shape, and deliberately narrower:
a multi-word quantity, a hyphenated compound, a lowercase noun, an all-caps
acronym, a single letter, and something numeric all stay named, and absence of
evidence of a structural slot means the placeholder is holding a value, which
is the common case.

Only trigger 2 reads surrounding text, and it reads only what **immediately
precedes** the placeholder — never what follows it, and never at a distance.

Worked examples, each verified against the implementation rather than asserted:

| Output fragment | Verdict | Trigger |
|---|---|---|
| `improving completion rates from [N]% to [M]%` | 2 named | none fired |
| `cutting completion time from [N] to [M] days` | 2 named | none fired |
| `reducing manual effort by [N] hours per week` | 1 named | none fired — `by` is **not** a trigger |
| `cut cycle time by [N] days` | 1 named | none fired — `by` is **not** a trigger |
| `reduced [N]% to [M]%` | 2 named | none fired — **no unit-shaped-slot trigger exists** |
| `reduced [N] days` | 1 named | none fired, for the same reason |
| `[N]`, `[M]`, `[company]`, `[budget]`, `[end-to-end cycle time]` | 1 named | none fired — a bare letter is not a formula variable, and a noun's shape is not evidence |
| `[metric, e.g. 30%]` | 1 named | containment of `e.g.` is not a trigger |
| `improving [X] as measured by [Y] by [Z]` | 3 scaffolded | `[X]`/`[Y]`/`[Z]` are formula variables; `as measured by` also fires |
| `reduced [X]%` | 1 scaffolded | `[X]` is a formula variable — the `%` is irrelevant |
| `reduced spend by 15-20% through [insert specific action]` | 1 scaffolded | writer instruction |
| `improving [N] by [M] through [Method]` | 3 scaffolded | `[Method]` fires trigger 4 — ADR-001; the letters stay named |
| `... using [method]` | 1 named | lowercase word — not a schema label |
| `[QA]` | 1 named | all-caps acronym — not a schema label |
| `[Uptime]` | 1 scaffolded | the honest trade-off: a *filled* capitalized word reads as a blank — recorded in ADR-001 |
| `Led the migration of the legacy warehouse` | 0 placeholders | — |

Two rows here are the ones most likely to be read the other way, and both
deliberate. There is **no** trigger for a placeholder sitting in a unit-shaped
slot: `[X]%` is scaffolding only because `[X]` is a formula variable, and
`[N] days` is named because nothing about it is structural — the `%` and the
`days` are not read. And a placeholder directly after a bare `by` is **not**
scaffolding; an earlier draft said it was, which contradicted its own worked
examples, since `"cut cycle time by [N] days"` and `"reducing manual effort by
[N] hours per week"` are the same construction and differ only in base verb
versus gerund. That clause was written for the XYZ case `"...by [Z]"`, which
trigger 1 already catches, so it contributed no true positives and a false one
on every legitimate `by [N] <unit>`.

Every generation is classified, the counts are shown to the judge, and
`worst_case_placeholders` folds the per-seed counts with a **max per field, not
a sum** — the caps ask whether *any* generation did the thing, so one generation
with three placeholders is no worse than three generations with one.

### The three caps, and where they are enforced

`apply_placeholder_cap` (`evals/layer3_judge.py`) is a ceiling, never a floor: a
criterion the judge already scored low is reporting a real deficiency and is
left alone.

| Criterion | Cap | Why it is differentiated |
|---|---|---|
| `truthfulness` | **none** | marking a blank correctly *is* the behaviour this criterion exists to reward |
| `impact` | 5 when **any** placeholder is present | it asks for a real outcome value, and a placeholder is the absence of one |
| `agency` | 5 only when a **scaffolding** placeholder is present | a named one does not obscure the actor; a scaffolding one occupies the action slot, which is what agency measures |

Enforced at one place, `evals/layer3_judge.py`, applied to the criterion mean
and recorded as `mean_capped` alongside the raw `mean`; the arrow `judge->capped`
in the CLI output marks every criterion where the cap bit. `evals/layer3_variance.py`
imports the same three functions rather than reimplementing them, so the
analyser cannot drift from the harness, and it **refuses** to emit an uncapped
number for a capped report.

### What the caps actually did

The fabrication rate cannot move under the caps — the veto reads the candidate
with placeholders stripped out before any cap runs, so placeholder policy is
inert with respect to whether a digit was invented. That structural claim held
on the first caps-era regeneration, which measured 0/30; on the fresh
regeneration the generator itself regressed to **2 of 30 (6.7%)** — not through
the caps but around them. ADR-001's reminder stands inside that regression too:
a rate that *stays* at any number proves one thing, and 0% is also what a
broken skill would report.

Recomputing `layer3-live-s3.json` with the caps removed is exactly like-for-like
— same tasks, same judge scores, one variable — and it is not the same as
re-running the generator, which did not reproduce earlier revisions (see
"`--seeds` at temperature 0.0"). On that recomputation the caps **barely bit**.
Of 40 criterion entries, **exactly one** changed value: `rbw-held-01` `agency`,
6.67 → 5.0 — the scaffolded slot that trigger 4 now surfaces in the seed-0
generation of that task. Every score below is for
`resume-bullet-writer`, which carried placeholders in all four of its tasks;
`resume-quantifier` generated none across its six tasks (18 generations), so
no cap could reach it.

| composite | before caps | after caps | change |
|---|---|---|---|
| capped aggregate | 4.24 | **4.12** | −0.12 |
| per-seed counterfactual, uncapped mean | **4.24** | 4.12 | −0.12 |
| per-seed means, uncapped | `[4.49, 4.12, 4.12]` | `[4.12, 4.12, 4.12]` | only the seed-0 bump moves — the same agency entry |
| `resume-quantifier`, either composite | 6.47 | **6.47** | 0.00 |

Both "before" figures are **counterfactuals recomputed from
`layer3-live-s3.json`**, not read from any report that exists — the committed
reports were regenerated under the caps, which is the whole point. Each is
reproducible by hand from that one file:

- **4.24** — the mean of the four `resume-bullet-writer` task scores with
  `mean_capped` read as `mean` instead (i.e., only `rbw-held-01` `agency`
  keeps its 6.67 rather than being clamped to 5.0).
- **`[4.49, 4.12, 4.12]` (mean 4.24)** — per-seed task totals recomputed from
  the stored criterion samples with the cap removed per sample; only seed 0
  moves, because the only scaffolded slot it carries sits in that
  generation's classification.

There is no committed pre-cap report to read them from, and none should be
invented: hand-stamping one would assert a provenance it does not have.

The composite was not expected to rise (spec §4.1, D4) and it did not, on
either model.

**An earlier revision of this table read `6.10` in the "before caps" cell
against `6.13` in the "after" cell, and then asserted immediately below it that
"the composite was not expected to rise and it did not" — directly above a
+0.03 rise.** `6.10` is not a composite at all: it is **one seed's reading**,
the third element of the `[5.81, 6.47, 6.11]` per-seed list quoted earlier in
this file. The table was comparing a single seed against a three-seed mean, so
the "+0.03" was an artefact of the units rather than a measurement. The two
rows above are now the same model read both ways.

### Inter-judge, re-measured on the same candidates

| Criterion | before | after | direction |
|---|---|---|---|
| `agency` | 2.50 | **2.50** | unchanged |
| `impact` | 2.50 | **1.50** | fell |
| `truthfulness` | 1.00 | **1.00** | unchanged |
| exact agreement | 70% | **76%** | rose |
| mean absolute difference | 2.00 / 10 | **1.67 / 10** | fell |

Stated plainly: **`agency` did not move.** The disagreement it was supposed to
fix is still 2.50, still the weakest criterion, and still a single clean
polarisation — primary reads placeholder scaffolding as unstated agency (0) where
the second reads it as unmistakable (10), on `rbw-train-01` and `rbw-train-02`.
`impact` fell 2.50 → 1.50 and is the only criterion the policy moved. Overall
agreement rose from 70% to 76% and the mean difference fell from 2.00 to 1.67.

**Two caveats that limit what this comparison can carry.** First, the second
judge is `openai/gpt-oss-120b` at `temperature 0.0`, which is reproducible in
principle but returned 3 of 30 scores differently across these two runs, so a
one-point move in a mean over 10 pairs is inside the noise of the instrument.
Second — and this is the structural limit — **`layer3_interjudge.py` compares
`t["criteria"][key]["samples"][0]`, the raw uncapped judge score, not
`mean_capped`.** The inter-judge tool therefore **cannot see the caps at all**.
What moved between these two runs is the judge's raw scores, not the cap. This
comparison measures the same candidates re-judged; it does not independently
confirm the caps improved agreement.

### Fresh candidates — the only independent evidence

Spec §7 forbids presenting a re-measurement on the same candidates as
validation, so a third run generated at `--judge-temperature 0.4` produced
candidates neither judge had seen (`layer3-fresh.json`, deliberately not
overwriting either committed report):

| Criterion | committed run | fresh run | direction |
|---|---|---|---|
| `agency` | 2.50 | **2.50** | unchanged |
| `impact` | 1.50 | **3.00** | **rose — now AMBIGUOUS** |
| `truthfulness` | 1.00 | **1.00** | unchanged |
| exact agreement | 76% | **67%** | fell |
| mean absolute difference | 1.67 / 10 | **2.17 / 10** | rose |
| fabrication | 0.0% | **0.0%** | held |

**This is the honest result, and it is the one that should govern: on unseen
candidates the caps did not help.** `impact` rose 1.50 → 3.00 and crossed into
the `AMBIGUOUS` band the tool flags at ≥3.0, displacing `agency` as the weakest
criterion. Agreement fell from 76% to 67%. The `impact` improvement on the
committed candidates **did not generalise** — which is exactly the failure mode
the fresh-candidate run existed to catch, and it is the round-half-even fit the
brief warned could not be revealed by re-scoring the old set.

The mechanism is visible in the disagreements: on the fresh run the second judge
scored placeholder outputs at 5 on `impact` for `rq-train-01`, `rq-train-02` and
`rq-held-01` where the primary scored 0. The cap only *agrees* with one reading
of what a placeholder is worth; it does not make the two judges agree about it,
and on unseen output they still disagree.

### The determinism claim in this document no longer holds as written

This document previously reported that at `temperature 0.0` the judge returned
identical scores for all three seeds, with a seed swing of `0.0` and 0 of 30
criterion-task pairs spanning the full range. Re-running the same command
against the same rubric **contradicted that**: 4 of 40 criteria now vary across
seeds, `resume-bullet-writer` has a seed swing of **0.66**, and 1 of 30 pairs
(`rbw-train-01` `agency`, samples `[0, 10, 0]`) spans the full range. The
consequence is material — the between-skill gap is 0.34 against a swing of 0.66,
a ratio of **0.5×**, so **the ordering is no longer supported** and no ranking
is asserted.

The regenerated candidates are also not identical to the committed ones: 24 of 30
share the same bullet line, 6 differ only in the trailing `NOTE:` text, and 6
differ in the bullet itself (all `resume-quantifier` refusals, which vary in
which figures they ask for). Generation at `temperature 0.0` is therefore **not
byte-stable** in practice on this provider, so "the generator also runs at
temperature 0.0" is not sufficient to make a re-run a like-for-like
re-measurement. This is recorded rather than smoothed over: the earlier
zero-swing figures were real for that run and are not reproducible now.

### The staleness guard covered the rubric but not the scoring

The guard was built for the failure where a report is scored against *different
rubric anchors*. These reports were regenerated under a changed **scoring
function** with unchanged anchors, and `rubric_fingerprint` hashes the rubric
only — so `layer3_interjudge.py` did not reject the pre-cap reports. Running it
against the committed report exited **0** and completed a full 30-call run
rather than the expected exit 2. The staleness was real; the guard simply did
not detect this class of it.

That hole is now closed. `scoring_fingerprint` hashes the three functions that
turn anchor scores into reported numbers — `classify_placeholders`,
`worst_case_placeholders`, `apply_placeholder_cap` — together with the patterns
and constants they close over. The function bodies are read from the source
rather than restated in the hash, so a branch added to one of them cannot be
forgotten there and silently reopen the same gap. Every report records both
fingerprints, and `layer3_interjudge.py` **exits 2** on either mismatch.

**The cost, stated rather than absorbed: both committed reports predate
`scoring_fingerprint`, so `layer3_interjudge.py` now refuses them.** They were
produced before the field existed and cannot be shown to have been produced
under any particular scoring policy. The honest fix is to regenerate them
against the live backend —

```
python evals/layer3_judge.py --backend openai_compatible --split all \
    --seeds 3 --json layer3-live-s3.json
```

— which needs credentials and a few hundred paid calls, so it was not done here.
Making the guard lenient so the old reports keep working would have restored
exactly the defect it exists to close.

`layer3_variance.py` is unaffected and still analyses both reports. It reads
the harness's own recorded `score_by_seed` rather than recomputing a score
through its own model of the caps, so a changed policy cannot make it report a
number the harness did not produce. The inter-judge tool is where the staleness
was undetectable, because that tool compares two runs rather than reading one.
This is a real residual limitation and not a claim of full coverage: the
analyser will happily report a `score_by_seed` that a later policy would have
computed differently.

## Four design choices, each avoiding a dishonesty

**Mechanical evidence is computed first and handed to the judge.** Word count,
passive-voice markers, filler, and whether the source contains a metric at all
are decidable without a model. The judge sees them and is asked only about what it
alone can judge. This grounds the score and cuts paid calls.

**The rubric is anchored at 0, 5 and 10** with observable properties at each
level — not "rate quality 1–10". A test enforces that every criterion has all
three anchors and that each is longer than 20 characters, because a vague anchor
is worse than none.

**Multiple seeds, variance reported.** A single unseeded judge number is not a
result. Every task is judged `--seeds` times; a criterion whose seeds spread
more than 4 points is marked `unstable` and its mean is not treated as a
measurement. The stub backend varies by seed **on purpose**, so this machinery is
exercised in the only mode CI can run without credentials — a constant stub would
leave the instability detector as dead code.

**The fabrication veto cannot be outvoted.** If any generation introduces a figure
the source never contained, the task scores `0.0` regardless of how generous the
judge was. The individual judge scores are still recorded, so the veto is
auditable rather than invisible.

## Honesty properties, and how they are enforced

| Property | Test | Mutation check |
|---|---|---|
| Stub is marked synthetic | `test_stub_backend_is_marked_synthetic` | flipping the flag → 4 failures |
| Every stub result carries `synthetic: true` | `test_every_stub_result_is_labelled_synthetic` | — |
| Stub output contains a visible marker | `test_stub_output_carries_the_synthetic_marker` | — |
| CLI prints `PLUMBING REPORT`, never `QUALITY REPORT` | `test_cli_reports_synthetic_and_refuses_a_verdict` | — |
| JSON report is marked synthetic | `test_json_report_is_marked_synthetic_for_stub_runs` | — |
| Missing credentials exit non-zero | `test_live_backend_without_credentials_exits_non_zero` | degrading to stub → 2 failures |
| Partial credentials also exit non-zero | `test_partial_credentials_are_still_a_hard_error` | — |
| Stub run is deterministic | `test_stub_run_is_deterministic` | — |
| Zero-variance criterion is reported, weighted or not | `test_non_discriminating_criteria_are_detected` | returning `{}` |
| `craft` stays disabled with its cause recorded | `test_craft_is_disabled_on_live_evidence` | re-enabling it |
| Per-generation fabrication uses the mechanical flag | `test_untruthful_prose_is_not_counted_as_fabrication` | reinstating the truthfulness proxy → 5 failures |
| An invented figure scored 10 by the judge still counts | `test_invented_figure_scored_10_by_the_judge_is_still_fabrication` | — |
| A report without the flag is unmeasurable, not guessed | `test_report_without_the_per_seed_flag_is_reported_unmeasurable` | falling back to a proxy |
| Vetoed work is separable from prose quality | `test_vetoed_work_is_reported_separately_from_writing_quality` | collapsing both means |
| The ≥1.0 material-gap cutoff is pinned from both sides | `test_gap_just_under_the_threshold_is_not_material` | lowering it to 0.5 |
| A fully-vetoed skill raises no misattribution flag | `test_fully_vetoed_skill_reports_no_unvetoed_mean` | counting it as misattribution → 3 failures |
| `--judge-temperature` reaches the request | `test_judge_temperature_is_carried_into_the_request` | hardcoding 0.0 |
| A report scored under changed cap or classifier functions is refused | `tests/test_layer3_staleness_guard.py` | hashing anchors only |
| A report whose skills were not all scored by the same model is refused | `tests/test_layer3_variance.py` | blending the two means |
| Every figure quoted in this doc matches the reports | `scripts/check_doc_figures.py` (CI) | corrupting a quoted rate |

**Two of those guards have no figure behind them, and that is deliberate.**
`check_doc_figures.py` verifies that a number is *present* in this prose, not
that it appears next to the claim it supports — so a figure quoted in two
places passes if one occurrence is correct. That is why the composites above are
labelled with the artifact they come from rather than left to be inferred from
their neighbours. The classification section in this file is **not** checked at
all, by any tool: it was stale prose describing a classifier that no longer
existed for four rounds, and a maintainer reading it would have "fixed" correct
code to match. Extending `check_doc_figures.py` to cover it is the durable fix
and is not done here.

**There is no flag that converts a stub run into a claim.** The two backends
produce structurally different reports, and only the live one may be gated on.

## Two bugs the tests caught in this harness

**The fabrication detector was inverted.** It read
`has_number and not source_has_no_metric`, which flags a truthful restatement as
fabrication and passes actual fabrication — the worst possible failure for the
highest-severity check in the domain. Corrected to
`has_number and source_has_no_metric`; re-inverting it fails 3 tests.

**The filler matcher missed every morphological variant.** It substring-matched
`"leveraged"`, so it caught neither `"leveraging"` nor `"synergies"` — precisely
the vocabulary a model reaches for. Now inflects to a stem and matches with a
short tail. Verified against three genuinely clean bullets: no false positives.

## Running it

```bash
# harness self-check, offline, deterministic, no spend
python evals/layer3_judge.py --backend stub --split held_out --seeds 3

# live
OPENAI_COMPATIBLE_BASE_URL=https://ollama.com/v1 \
OPENAI_COMPATIBLE_API_KEY=... \
OPENAI_COMPATIBLE_MODEL=<model> \
python evals/layer3_judge.py --backend openai_compatible --split held_out \
    --seeds 3 --min-score 7.0 --json report.json

python evals/layer3_judge.py --list
```

`openai_compatible` targets any OpenAI Chat Completions endpoint, which includes
this project's `ollama_base_url = https://ollama.com`.

## Cost

Per task per seed: **1 generation + 1 judge call per enabled criterion**, so
4 calls with `craft` disabled. Measured, not estimated: `--split all --seeds 1`
(8 tasks) took **70 s**, and `--split all --seeds 3` (**120 calls**) took **181 s**.
`--split held_out --seeds 3` is 60 calls. One dry run should be measured before
any sweep — see [`skillopt-decision.md`](skillopt-decision.md).

## What this does not establish

- **The composite is judge-dependent.** A second model family agrees on 76% of
  judgements on the committed candidates and only 67% on fresh ones, with `agency`
  diverging by 2.50 points in both and `impact` reaching 3.00 on unseen output.
  `7.21` is a band, not a precise score.
- **It is not calibrated against human judgement.** No expert rater has scored any
  of these outputs. The anchors are written, not validated, and inter-judge
  agreement is a weaker proxy than a person.
- **The placeholder caps are not validated either.** They moved exactly one of 40
  criterion entries on the committed candidates, and on fresh candidates the
  criterion they targeted got *worse*. One criterion changing in forty is a
  policy with almost no measured effect, not a validated rule.
- **Two skills is a pilot, not a gate.** 25 prose-only skills remain unevaluated,
  and the 8 with helper scripts are covered only by Layer 2.
- **Ten tasks is a small sample, and the ordering is no longer supported.** The
  gap is 0.34 against a seed swing of 0.66 — a ratio of 0.5× — so the gap sits
  inside the noise and no ranking is asserted.
- **It does not verify the skill document is *followed*.** It measures what
  following the document produces. A skill with excellent prose and a weak
  playbook would score well and still be a problem.
- **The fabrication rate is measured on 30 generations.** 0.0% is a genuine
  improvement on 25.0% and the transcripts show the intended behaviour — but 30
  generations cannot prove a rate is zero, only that it is below what this sample
  detects. It should be re-measured as tasks are added, not treated as settled.
- **The unvetoed means are now uninformative by construction.** With no vetoes, the
  overall and unvetoed means cover the same tasks, so the split that changed the
  conclusion has nothing left to separate.