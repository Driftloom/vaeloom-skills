# Decision: SkillOpt is blocked on a behavioural scorer, not on installation

**Status:** deferred. Revisit when Layer 2 of the scorecard has prose-sensitive
scored cases for specific skills.

## What SkillOpt is

A text-space optimiser that treats a skill document as the trainable state of a
frozen agent. A target model executes scored rollouts, a separate optimiser model
proposes bounded add/delete/replace edits, and a candidate is adopted only if it
strictly improves a held-out validation split. Published results: best-or-tied on
all 52 evaluated (model, benchmark, harness) cells; +23.5 points average no-skill
accuracy on GPT-5.5 in direct chat.

It is a good fit for this repository *in principle*. It is blocked *in practice*
for one specific, nameable reason.

## Verified installation facts

Checked on 2026-10-07, not assumed:

| Question | Answer |
|---|---|
| Is `skillopt` installable? | Yes — PyPI `0.2.0` downloads and installs cleanly. |
| Does it need a source checkout? | **Yes, for our use.** A benchmark is `skillopt/envs/<name>/` with `dataloader.py`, `rollout.py` and a seed `initial.md`. Those env packages, the benchmark configs and the agent-integration shells are **not in the wheel**. |
| Can it talk to our LLM provider? | Not from PyPI. `llm_provider = ollama` with `ollama_base_url = https://ollama.com` is OpenAI-compatible, which maps to the `openai_compatible` backend — and that backend "landed after that release and requires a source install from `main`". |
| Does it need an API key? | Yes, for real training. The `SkillOpt-Sleep` mock backend needs none, but "it is not evidence that a real model's quality improved". |

So: installable, source checkout required, `openai_compatible` unavailable until
a release, and real API cost per rollout.

## The blocker: there is no objective function to optimise against

SkillOpt's whole mechanism is *propose edits → measure on scored rollouts → keep
only what improves held-out score*. Remove the score and it is not an optimiser;
it is a text editor with a validation gate around it.

We have three candidate scores. All three are wrong for this purpose:

**Layer 1, the structural scorecard — actively harmful as an objective.**
`scripts/score_skills.py` scores file shape: does D8 see an edge-case heading, do
D2's triggers appear verbatim, is the body under 500 lines. SkillOpt would drive
that score up by inserting the exact headings and phrases the scorer greps for,
producing documents that score 95+ and instruct an agent no better than before.

This is not a hypothetical. It is the specific failure this repository already
hit once: an earlier keyword-only D8 scored `reference-list-builder` at 0/10
despite a real `## Handling Special Situations` section, and "fixing" that score
would have damaged a good skill. Pointing an optimiser at the scorer would
automate that damage across 33 skills.

**Layer 2, the existing eval harness — measures scripts, not documents.**
`evals/run_evals.py` imports `ats_checker`, `xyz_scorer`, `comp_calculator`,
`star_validator`, `headline_lint` and `humanize`, and asserts on their return
values. It verifies that a Python function computes the right number. It never
invokes a model, never reads a skill document, and cannot distinguish a good
`SKILL.md` from a bad one. Optimising prose against it would move the score not
at all.

**Layer 3, an LLM judge — not yet built, and not yet trustworthy enough.**
This is the right answer and the real prerequisite. It needs, per target skill: a
task set with a held-out split, a rollout that actually runs the skill, and a
rubric-anchored scoring function with reported variance across seeds. None of
that exists. And a single unseeded judge number is not a gate — it is a
vibes-check that will not survive contact with a rollback.

## What unblocks it

In order:

1. **Pick two skills with a crisp, checkable behavioural outcome.** Good
   candidates are `ats-audit` and `star-interview-prep`: both have deterministic
   scripts already, so the *outcome* is checkable even though the prose is not.
2. **Build Layer 2 cases for those two** that are sensitive to the document, not
   just the script — e.g. an adversarial resume that the operating rules should
   catch and a compliant one they should not flag.
3. **Cost one dry run before committing.** Rollouts × epochs × optimiser model is
   unbounded until measured. Produce a token and dollar estimate from a single
   epoch, then decide.
4. **Then pilot SkillOpt on those two**, source checkout, `openai_compatible`
   against Ollama Cloud, held-out gate enforced, `best_skill.md` reviewed by a
   human before it lands.

## Explicitly not recommended: SkillOpt-Sleep

SkillOpt-Sleep rewrites `SKILL.md` files overnight, behind a held-out gate, with
staged adoption. Against this repository that is a bad fit:

- `vaeloom-skills` is the canonical, CI-gated source of truth. Nightly
  self-editing would bypass the very gates this work established.
- Its own documentation is candid: the gate "is not a security boundary or a
  proof of general improvement".
- The draft syntax layer it would optimise is precisely the layer Layer 1 already
  showed is gameable.

If it is ever adopted, it should point at a scratch copy with `--target-skill-path`
and never at the canonical tree.

## The honest summary

SkillOpt is a strong candidate for this catalogue and the wrong tool for it
today. The blocker is not installation and not cost — it is that **we have not
built the instrument it optimises against.** Building that instrument is the work;
running the optimiser is a consequence of it.
