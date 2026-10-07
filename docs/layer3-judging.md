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
| `resume-bullet-writer` | 5.44 | 5.64 | +0.20 |
| `resume-quantifier` | 3.68 | 3.92 | +0.25 |
| **Overall** | **4.56** | **4.78** | **+0.22** |

- **Ordering is supported, by 2.3×.** The gap is 1.72 against a largest
  seed-to-seed swing of any skill's mean of 0.74. `resume-bullet-writer` does
  score above `resume-quantifier` — but by a modest margin, so the ordering is
  weak evidence, not a confident ranking.
- **The judge is not reliable on 1 judgement in 8.** 3 of 24 criterion-task pairs
  (12.5%) returned the full `0`–`10` range across seeds, e.g. `truthfulness`
  `[10, 10, 0]` and `agency` `[0, 10, 0]`. Those judgements carry no information
  and are listed in the analyser output rather than silently averaged.
- **Fabrication is 33% per generation** (8 of 24), not the 38% task-level figure.
  The task rule zeroes a task if *any* of its generations fabricated, which is the
  correct rule for fabrication but the wrong thing to quote as a rate.

The denominator matters more than it looks. The first analysis compared the
between-skill gap against per-task criterion spread (0–10) and concluded the
difference was unresolvable. That was the wrong denominator — it compares a
difference *between* skills with the spread *within* a single judgement. The
correct comparison is gap against seed-to-seed swing of the mean, which supports
the ordering at 2.3×. `test_gap_is_measured_against_the_swing_of_the_mean` pins
this, with a control that produces the same gap by a different route and must be
rejected.

The analyser also had an inverted guard: it reported an ordering as *unsupported*
when seed swing was zero, treating perfect repeatability as absence of evidence.
Restoring that bug fails 3 tests.

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

- **It is not calibrated against human judgement.** The anchors are written, not
  validated against expert raters. This is the largest remaining gap: the judge
  disagrees with itself on 12.5% of criterion-task pairs, and nobody has checked
  whether it agrees with a person on the rest.
- **Two skills is a pilot, not a gate.** 25 prose-only skills remain unevaluated,
  and the 8 with helper scripts are covered only by Layer 2.
- **Eight tasks is a small sample.** The ordering of the two skills survives the
  noise by 2.3×, which is real but thin. Per-criterion figures come from as few
  as 8 observations.
- **It does not verify the skill document is *followed*.** It measures what
  following the document produces. A skill with excellent prose and a weak
  playbook would score well and still be a problem.
- **The fabrication rate is measured on 8 tasks.** 33% is precise enough to act
  on — the failure is unambiguous — but not precise enough to publish as a
  headline metric.