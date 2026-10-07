# Skill Scorecard

**Layer 1 of the layered skill-quality instrument.**

- **Layer 1 — this document.** A deterministic 100-point rubric, no model call.
  The reproducible score.
- **Layer 2 —** `evals/run_evals.py`. Behavioural pass/fail. Hard sub-gate.
  **22 cases across 8 of 33 skills**, with 6 negative controls. Every skill that
  ships an executable helper is now covered; the 25 prose-only skills need an LLM
  judge to evaluate at all.
- **Layer 3 —** SkillOpt held-out accuracy. A ceiling measurement, never a gate.
  Blocked — see [`skillopt-decision.md`](skillopt-decision.md).

## The headline number is not 95

| Measure | Value |
|---|---|
| Skills scored | 33 |
| **Mean** | **58.1 / 100** (repo source) · **64.9 / 100** (effective) |
| Range | 45.4 – 76.9 |
| **At or above 95** | **0 of 33** |

**No skill in this catalogue currently reaches 95, and the gap is roughly 30
points per skill, not a handful of points across a few outliers.** Reporting
otherwise would require either moving the goalposts or editing the skills to
satisfy the scorer instead of to serve users. The second of those is the more
insidious failure: the rubric is mechanical, so it is trivially satisfiable by
inserting the words it greps for.

What CI enforces is therefore a **ratchet at 45.0**, not 95. The gate forbids the
catalogue from getting worse. Raising it is a deliberate act paired with an
actual improvement to a real skill.

## Two scoring modes, and why the difference matters

`scripts/score_skills.py` runs in two modes, and they disagree by ~7 points:

| Mode | Command | Mean |
|---|---|---|
| Repo source only | `python scripts/score_skills.py` | 58.1 |
| Effective (what ships) | `... --catalog <path>` | 64.9 |

**25 of 33 skills ship a bare two-line frontmatter** in this repo, and the
application catalog supplies their `required_scope`, `triggers` and `tags`.
Scoring the repo file alone reports those 25 as missing activation metadata when
the deployed skill is in fact complete.

That is an instrument measuring the wrong artifact, and it is the reason the
effective mode exists. CI runs the source-only mode because it has no access to
the application; that is a known, documented underestimate, not a hidden one.

## Where the points are

Per-dimension mean, effective mode:

| Dim | Mean | Dimension |
|---|---|---|
| D3 | 10.0 | Conciseness and token efficiency |
| D1 | 8.9 | Frontmatter specification compliance |
| D4 | 7.5 | Progressive disclosure and structure |
| D6 | 7.3 | Scope discipline |
| D10 | 7.0 | Completeness against the stated description |
| D2 | 6.7 | Description quality and triggering |
| D5 | 5.7 | Operating rule quality |
| D9 | 5.1 | Verifiability |
| D7 | 4.5 | Output contract specificity |
| **D8** | **2.1** | **Failure and edge-case handling** |

Conciseness is the one dimension the catalogue passes outright. **D8 is the
systemic gap**: these documents largely do not tell an agent what to do when
input is missing, a third party refuses, or a source is unavailable. D7 and D9
follow.

## The path from ~65 to 95

Roughly 30 points per skill, concentrated in three dimensions.

**D8 — failure and edge-case handling (+7.9 available).** Highest-value and
cheapest. Give each skill a named edge-case section and a stated
abstention/escalation path. This is real work that makes skills genuinely more
robust, and it is the change most worth making.

**D7 — output contract specificity (+5.5).** Contracts are currently one vague
sentence ("Produces a standardized professional reference sheet..."). They
should specify an ordering, an evidence requirement, and what to emit when data
is missing.

**D9 — verifiability (+4.9).** 25 skills have no helper script. They can still
score by declaring a measurable output limit and independently checkable rules —
but a genuinely deterministic check is worth more than a declared one.

## What this instrument cannot do

It is mechanical on purpose. A quality gate that needs an LLM to reproduce is not
a gate, and a judge score cannot be negative-tested — you cannot prove a judge is
measuring anything. So Layer 1 scores only what can be **proved from the file**,
and every awarded or withheld point carries a human-readable reason naming the
evidence.

The cost is that it cannot judge:

- whether the instructions are *good*, only whether they are present and shaped
- whether an Operating Rule is correct, only whether it carries an imperative
  verb and is not duplicated
- whether the condensation of the catalog tier is faithful in meaning (see
  [`two-tier-skill-contract.md`](two-tier-skill-contract.md), where 8 skills
  score 49–65% vocabulary overlap against their full sources)

Those need a human or a judge against a rubric. Layer 3 exists for that.

## Running it

```bash
python scripts/score_skills.py                       # whole catalogue
python scripts/score_skills.py --skill ats-audit     # one skill, every reason
python scripts/score_skills.py --min-score 45.0      # gate; exit 1 if breached
python scripts/score_skills.py --json out.json       # machine-readable
python scripts/score_skills.py --catalog <path>      # score what actually ships
```

`--skill` prints each criterion with a `+` / `~` / `-` mark and the evidence, so
any score can be argued with rather than merely reported.

## Guarantees, and how they are tested

| Property | Test |
|---|---|
| Every dimension is worth exactly 10 points | `test_every_dimension_is_worth_exactly_ten_points` |
| Scores bounded 0–100, dimensions never exceed their maximum | `test_totals_are_bounded_zero_to_one_hundred`, `test_dimension_scores_never_exceed_their_maximum` |
| Total equals the sum of its dimensions | `test_total_equals_the_sum_of_its_dimensions` |
| Reproducible, no model call | `test_scoring_is_reproducible`, `test_scoring_every_skill_is_reproducible` |
| Every criterion carries a reason | `test_every_criterion_carries_a_reason` |
| Responds to real degradation | `test_removing_canonical_sections_lowers_the_score`, `test_dropping_triggers_lowers_the_triggering_score`, `test_an_unknown_scope_is_penalised` |

The "exactly 10 points" test exists because it caught a real bug: D8 was
rebalanced to 4+3+3+3 and every score in the catalogue became a percentage of the
wrong denominator.

The scorer is mutation-tested — reintroducing the 13-point bug and disabling
structural edge-case detection each fail the suite.

### A false negative that was found and fixed

`reference-list-builder` scores **0/10 on D8** under a keyword-only scorer, despite
carrying a `## Handling Special Situations` section, a `### Who to Avoid` section,
and a `### Common Questions` section. Real edge-case handling, expressed in prose,
never using the word "error".

Left unfixed, the scorecard would have instructed someone to keyword-stuff 33
healthy skills and damaged them in the process. D8 now scores a **structural**
signal (a heading naming situations, edge cases or pitfalls) above the keyword
signal, because a named section is a deliberate authoring act and a stray
"error" is not.

Guarded by `test_edge_case_sections_are_detected_structurally_not_by_keyword`
and `test_structural_signal_outranks_a_stray_keyword`.

## Baseline

`docs/skill-scorecard-baseline.json` is the committed measurement at the time
this document was written. Regenerate it when the floor is deliberately raised:

```bash
python scripts/score_skills.py --json docs/skill-scorecard-baseline.json --quiet
```
