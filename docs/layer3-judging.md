# Layer 3: Rubric-Anchored Judging

Layer 1 scores file structure. Layer 2 exercises helper scripts. **Neither can
say whether a skill document, followed by a competent model, produces a good
resume bullet.** This layer can, and is the prerequisite for SkillOpt, which
optimises against exactly this kind of signal.

> **Status: the harness is built and tested. No live quality number exists yet.**
> No provider credentials are configured in this repository or its CI, so every
> run recorded here used the synthetic backend. That is stated plainly rather
> than papered over, because a fabricated judge score would be worse than no
> score at all.

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

Per task per seed: **1 generation + 1 judge call per criterion** (4 criteria), so
5 calls. At 2 held-out tasks × 2 skills × 3 seeds that is **60 calls** per run.
`--seeds 1` cuts it to 20. One dry run should be measured before any sweep —
see [`skillopt-decision.md`](skillopt-decision.md).

## What this does not establish

- **It is not calibrated against human judgement.** The anchors are written, not
  validated against expert raters. Until someone compares judge output to human
  scores on the same tasks, the numbers are internally consistent and externally
  unverified.
- **Two skills is a pilot, not a gate.** 25 prose-only skills remain unevaluated.
- **It does not verify the skill document is *followed*.** It measures what
  following the document produces. A skill with excellent prose and a weak
  playbook would score well and still be a problem.