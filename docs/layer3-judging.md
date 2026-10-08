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
| `resume-bullet-writer` | 7.35 | 5.64 | −1.72 |
| `resume-quantifier` | 3.68 | 3.58 | −0.10 |
| **Overall** | **5.51** | **4.61** | **−0.91** |

The 1-seed figure for `resume-bullet-writer` is not noise around 5.64 — it is a
different verdict. At one seed the judge happened not to flag two of the three
fabrications, so the task was not vetoed and scored `7.35`. Re-judging the same
candidate at three seeds caught them. A single seed under-reports fabrication
here, which is the practical argument for more than one.

- **Ordering is supported, by 7.0×.** The gap is 2.06 against a largest
  seed-to-seed swing of any skill's mean of 0.29. `resume-bullet-writer` does
  score above `resume-quantifier` — but on 8 tasks with 2 skills that is weak
  evidence, not a confident ranking.
- **The judge is not reliable on 1 judgement in 12.** 2 of 24 criterion-task pairs
  (8.3%) returned the full `0`–`10` range across seeds, both `truthfulness` on
  `resume-quantifier` (`[10, 0, 0]` and `[0, 10, 10]`). Those judgements carry no
  information and are listed in the analyser output rather than silently averaged.
- **Fabrication is 25.0% per generation** (6 of 24), read from the mechanical
  per-seed flag, not from judge scores. The task-level figure is 37.5% (3 of 8)
  because the veto zeroes a task if *any* generation fabricated — the correct rule
  for fabrication, the wrong thing to quote as a rate.

### `--seeds` at temperature 0.0 is a reproducibility check, not a variance sample

The live judge runs at `temperature: 0.0`, so the same input tends to return the
same score. Across 24 judgements only one criterion moved (`rq-held-02` `agency`,
`[0, 5, 0]`), and the per-seed skill means were `[5.44, 5.74, 5.74]` and
`[3.38, 3.68, 3.68]` — a swing of `0.29` each, which is the floor rather than zero.
So the seeds mostly confirmed the harness is repeatable; they did **not** sample
the judge's distribution. `--judge-temperature > 0` exists so that measurement is
available when it is wanted, and
`test_judge_temperature_is_carried_into_the_request` pins that the flag reaches the
request rather than being a constant.

## The headline mean was measuring the wrong defect

A vetoed task is pinned to `0.0` however well it scored. That conflates
"writes badly" with "invents figures", and on this run the conflation was the
result:

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

- **It is not calibrated against human judgement.** The anchors are written, not
  validated against expert raters. This is the largest remaining gap: the judge
  returns the full `0`–`10` range on 8.3% of criterion-task pairs, and nobody has
  checked whether it agrees with a person on the rest.
- **Two skills is a pilot, not a gate.** 25 prose-only skills remain unevaluated,
  and the 8 with helper scripts are covered only by Layer 2.
- **Eight tasks is a small sample.** The ordering survives the noise by 7.0×, but
  that ratio rests on a single re-judgement and would move on a different eight
  tasks. Per-criterion figures come from as few as 8 observations.
- **It does not verify the skill document is *followed*.** It measures what
  following the document produces. A skill with excellent prose and a weak
  playbook would score well and still be a problem.
- **The fabrication rate is measured on 24 generations.** 25.0% is precise enough
  to act on — the failure is unambiguous, and the invented figures are quoted in
  the report — but not precise enough to publish as a headline metric.
- **The unvetoed means rest on 2 and 3 tasks.** The gap between overall and
  unvetoed is large enough to change the conclusion, and it points the fix at
  fabrication rather than prose, but with single-digit task counts neither number
  is a stable estimate.