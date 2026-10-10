# Layer 3: Rubric-Anchored Judging

Layer 1 scores file structure. Layer 2 exercises helper scripts. **Neither can
say whether a skill document, followed by a competent model, produces a good
resume bullet.** This layer can, and is the prerequisite for SkillOpt, which
optimises against exactly this kind of signal.

> **Status: measured live against `gemma4:31b` via `ollama.com/v1`.**
> Overall **4.78/10** at 3 seeds across 2 skills. **33% of generations fabricate.**
> The anchors are written, not calibrated against human raters, so this is a
> first reading rather than a baseline. See the two sections below for what the
> number does and does not support.
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
| `resume-bullet-writer` | 6.11 | 6.11 | 0.00 |
| `resume-quantifier` | 6.47 | 6.47 | 0.00 |
| **Overall** | **6.29** | **6.29** | **0.00** |

The two runs agree exactly. That is the reproducibility check working as intended
at `temperature 0.0`, not two independent samples — see the note below on why
`--seeds` is not a variance estimate at this temperature.

The task set grew from 8 to 10 once the fix landed — see the section on the sourced-number
tasks below, which exist because a 0% fabrication rate is also what a broken skill
would report.

- **Ordering is supported.** The gap is 1.47 against a seed-to-seed swing of `0.0`:
  the judge returned identical scores for all three seeds. Real, but on 10 tasks
  with 2 skills it is weak evidence, not a confident ranking.
- **The judge was fully self-consistent on this run.** 0 of 30 criterion-task pairs
  returned the full `0`–`10` range, against 2 of 24 before the skill documents
  changed. With `truthfulness` no longer flipping between 0 and 10 on the same
  artifact, the criterion is discriminating more sharply. Note this is
  *self*-consistency; the cross-model comparison below is the harder test.
- **Fabrication is 0.0% per generation** (0 of 30), down from 25.0% (6 of 24).

### `--seeds` at temperature 0.0 is a reproducibility check, not a variance sample

The live judge runs at `temperature: 0.0`, so the same input returns the same score.
The per-seed skill means are `[6.11, 6.11, 6.11]` and `[6.47, 6.47, 6.47]` — no
criterion moves at all. So the seeds confirm the harness is repeatable; they do
**not** sample the judge's distribution. `--judge-temperature > 0` exists so that
measurement is available when it is wanted, and
`test_judge_temperature_is_carried_into_the_request` pins that the flag reaches
the request rather than being a constant.

The between-skill gap is now **0.37** with a seed swing of `0.0`. That is far too
small to rank two skills on 10 tasks, and the ordering reversed when the `agency`
anchors tightened — which is why no ordering is asserted anywhere in this project.

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
| Every figure quoted in this doc matches the reports | `scripts/check_doc_figures.py` (CI) | corrupting a quoted rate |

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

- **The composite is judge-dependent.** A second model family agrees on only 50%
  of judgements, with `agency` diverging by 7.00 points on average. `7.21` is a
  band, not a precise score.
- **It is not calibrated against human judgement.** No expert rater has scored any
  of these outputs. The anchors are written, not validated, and inter-judge
  agreement is a weaker proxy than a person.
- **Two skills is a pilot, not a gate.** 25 prose-only skills remain unevaluated,
  and the 8 with helper scripts are covered only by Layer 2.
- **Ten tasks is a small sample.** The ordering survives by 1.47 against a seed
  swing of 0.0, but that ratio rests on one re-judgement and would move on a
  different ten tasks.
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