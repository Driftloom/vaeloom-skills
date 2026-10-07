# Layer 2: Behavioural Evals

The scorecard in [`skill-scorecard.md`](skill-scorecard.md) is Layer 1. This is
**Layer 2**: cases that exercise what a skill's helper actually *does*, rather
than what its file looks like.

## Current coverage

**17 cases across 7 of 33 skills.** Every case is behavioural: it feeds input to
a helper and asserts on the result.

| Skill | Cases | Includes a negative control |
|---|---|---|
| `ats-audit` | 5 | yes — compliant resume must pass clean |
| `resume-optimization` | 3 | degenerate-input (empty bullet) |
| `star-interview-prep` | 2 | yes — individual agency must not trip the we-trap |
| `salary-negotiation-playbook` | 2 | zero-bonus boundary |
| `linkedin-profile-optimizer` | 3 | yes — over-budget headline must be rejected |
| `linkedin-humanizer` | 2 | yes — clean prose must pass through untouched |
| **`job-discovery-radar`** | **0** | — |
| **`linkedin-interviewer`** | **0** | — |
| 26 further skills | 0 | — |

**The two bolded skills ship executable helpers and have no behavioural case.**
That is a real hole, surfaced by
`test_eval_suite_integrity.py::test_report_uncovered_scripted_skills` rather than
hidden. It is reported, not failed, because failing it would force either writing
rollouts for two more skills or deleting their helpers, and both are worse than
naming the gap.

Skills with no helper script cannot be covered here at all without an LLM judge.
That is 25 of 33, and it is the reason Layer 3 exists.

## Three defects found in this suite

Each is now a test rather than a memory. See
[`tests/test_eval_suite_integrity.py`](../tests/test_eval_suite_integrity.py).

### 1. An unrecognised assertion type was reported as PASS

The runner's `if`/`elif` chains per skill had no catch-all. An assertion type the
chain did not recognise fell straight through, and the case was printed `[PASS]`.

Proven, not suspected:

```json
{"id": "probe-TYPO", "skill": "ats-audit",
 "assertions": [{"type": "rule_violation_typoed", "rule": "NOPE"}]}
```

```
[PASS] probe-TYPO: probe
Eval Results: 17/17 Passed (100.0% Accuracy)   exit=0
```

A typo, a rename, or a case written against a skill whose branch does not exist
would assert nothing and go green. That is worse than having no eval at all.

Fixed with an explicit `HANDLED_ASSERTIONS` registry — assertion types are scoped
per skill, so `headline_valid` used on `ats-audit` is also rejected — and a
`validate_cases` pass that runs **before any rollout** and exits 1 on the first
contract violation.

### 2. The unit tests did not prove the runner enforces the contract

The first version of the integrity suite called `validate_cases` directly. Those
tests all passed with the `validate_cases(cases)` call **removed from
`run_evals()`**, while the runner went back to reporting a typoed assertion as
PASS:

```
15 passed    Eval Results: 17/17 Passed    exit=0
```

The tests proved the function worked. They did not prove anything *called* it.
Four subprocess tests now drive the real entry point and assert on its exit code,
which is what catches that regression.

### 3. There were no negative controls at all

Every original case asserted that something *should* fire. None asserted that a
compliant input passes clean — so a checker that flagged every input would have
scored **8/8**. The suite could not distinguish a precise checker from a
broken one.

Four negative controls now exist. `test_negative_controls_really_assert_absence`
enforces that a case labelled `NEGATIVE CONTROL` genuinely asserts absence, so
the label cannot become decoration: the ATS control must assert `no_rule_violation`
for every rule its positive cases raise, and the humanizer control only counts
because its input never contained the banned words.

## Adding a case

1. Append to `evals/eval_cases.json`.
2. If the assertion type is new, register it in `HANDLED_ASSERTIONS` **under the
   right skill**. The runner will refuse to start otherwise, which is the point.
3. Give every skill that gains a positive case a negative one too. A checker with
   no clean-input case is unverified in the direction that matters most.

```bash
python evals/run_evals.py                        # run
python evals/run_evals.py --skill ats-audit      # not supported; see the JSON
pytest tests/test_eval_suite_integrity.py -v     # contract
```