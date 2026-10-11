#!/usr/bin/env python3
"""Is a Layer 3 score real, or is it judge noise?

A single judged number is not a result. This answers three questions about a
saved report, and refuses to answer them any other way:

1. **Signal or noise?** Is the gap between two skills larger than the
   seed-to-seed swing of either skill's mean? The comparison that matters is
   gap-vs-mean-swing. Comparing it against per-task criterion spread (0-10) is
   the wrong denominator and will always declare a difference unresolvable.

2. **How self-consistent is the judge?** Mean standard deviation hides
   catastrophic disagreement: a judge that returns 0, 5 and 10 on three seeds
   has a large sd, but a judge that returns 10, 10 and 10 on one task and
   0, 10, 0 on another does not. Full-range pairs are counted separately,
   because those are the judgements that cannot be trusted at all.

3. **How often does the skill actually fabricate?** The task-level veto is a
   worst-case rule -- one fabricating generation out of three zeroes the task --
   which is correct for fabrication but is not the expected fabrication rate.
   Both are reported so they cannot be confused.

Two refusals guard the arithmetic, at report level and at task-set level: a
report whose skills are not all scored by the same model is refused rather than
averaged into a `between_skill_gap` that belongs to neither.

Usage:
    python evals/layer3_variance.py layer3-live-s3.json
    python evals/layer3_variance.py report.json --compare other.json
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

# Criteria that carry weight. Disabled ones are excluded from every mean.
WEIGHTED_KEYS = ("truthfulness", "agency", "impact")


def weighted_criteria(result: dict) -> list[str]:
    keys = set()
    for task in result["tasks"]:
        for key, crit in task["criteria"].items():
            if crit.get("weight", 0) > 0:
                keys.add(key)
    return sorted(keys)


def _cap_helpers():
    """The harness's own cap functions, imported rather than reimplemented.

    A local copy of the cap rule here is precisely the drift this module exists
    to catch: the analyser would go on reporting numbers the harness never
    emitted, and the gate would certify a disagreement it had created.

    Two import forms because there are two ways in, and a single one does not
    cover both: imported as part of the `evals` package the module is
    `evals.layer3_judge`, and run as a script (`python evals/layer3_variance.py`)
    the repo root is not on sys.path at all, so only the flat name resolves.
    The package form is tried first so a test process shares one module object
    with the rest of the suite rather than growing a third copy.
    """
    try:
        from evals.layer3_judge import (
            apply_placeholder_cap, classify_placeholders, worst_case_placeholders,
        )
    except ImportError:
        from layer3_judge import (
            apply_placeholder_cap, classify_placeholders, worst_case_placeholders,
        )
    return apply_placeholder_cap, classify_placeholders, worst_case_placeholders


class CapsNotReproducible(RuntimeError):
    """A report claims to be capped and the analyser cannot reproduce the cap.

    Raised instead of a number. Emitting an uncapped score for a capped report
    is worse than refusing: the same report's own `mean_capped` would say 5.0
    while this module said 10.0, and the disagreement is invisible in the
    output because both look like ordinary scores.
    """


def report_is_capped(result: dict) -> bool:
    """Whether a harness with the placeholder caps produced these scores.

    Any criterion anywhere carrying `mean_capped` marks the whole result as
    capped. That is deliberately `any` and not `all`: a report that is halfway
    through migration has some criteria capped and some not, and reading it as
    uncapped would score the already-capped ones from their raw means -- the
    uncapped number this module exists to refuse. Reading it as capped applies
    the cap everywhere, and a criterion no cap ever touched passes through
    unchanged. A report predating the caps carries the field nowhere, so
    `any` over it is false and it is analysed uncapped, which is correct: for
    those reports `mean` is what the total was computed from.

    The trade is the price of `any` -- a result with a single stray
    `mean_capped` is treated as capped throughout. That is the direction that
    degrades into a refusal (`CapsNotReproducible`) rather than into a wrong
    number, which is the only direction worth being wrong in.
    """
    return any(
        "mean_capped" in crit
        for task in result["tasks"]
        for crit in task["criteria"].values()
    )


def task_placeholders_by_seed(task: dict) -> dict:
    """The harness's own per-seed placeholder classification, from the report.

    A report stores each seed's generated text but not its classification, so it
    is recomputed with the harness's own classifier over that text. The result is
    identical to what the harness computed, because classify_placeholders is a
    pure function of the text and reads none of the task's expectations.

    A task carrying no candidates yields nothing, which worst_case_placeholders
    then reads as "no placeholders" -- so a minimal fixture is simply uncapped
    rather than an error.
    """
    _, classify_placeholders, _ = _cap_helpers()
    out = {}
    for seed, text in (task.get("candidates") or {}).items():
        try:
            out[int(seed)] = classify_placeholders(text)
        except (TypeError, ValueError):
            continue
    return out


def _refuse_mixed_recording(result: dict) -> None:
    """Refuse a task set where only some tasks carry `score_by_seed`.

    The decision of read-or-recompute is per task, so a set containing both
    kinds of task would be scored partly by the harness's capped-mean model and
    partly by the per-sample model here, and the mean of the two is neither
    model's number. That is the same drift this module exists to catch, reached
    through a malformed report rather than a second implementation of the rule,
    and it is silent: every task's score looks like an ordinary score and the
    average of two different models looks like an ordinary average.

    This is defensive. The harness writes the field on every task of a report
    or on none, so no report it produces can get here. It exists so that a
    report edited, merged or truncated into that shape is refused rather than
    quietly analysed as a blend.

    Checked once for the whole task set rather than per task, because the
    answer is a property of the set and every task needs the same answer. An
    empty set is not mixed, and is left to the empty-set path in `seed_scores`.
    """
    tasks = result["tasks"]
    recorded = [t for t in tasks if t.get("score_by_seed") is not None]
    if not recorded or len(recorded) == len(tasks):
        return
    raise CapsNotReproducible(
        f"{len(recorded)} of {len(tasks)} tasks in skill {result.get('skill')!r} "
        "record score_by_seed and the rest do not. A task set read partly from "
        "the harness and partly recomputed here blends the harness's "
        "capped-mean model with the per-sample model, and the mean of the two "
        "belongs to neither. Re-run the harness so the report is written whole."
    )


def _recording_state(result: dict) -> str:
    """`recorded`, `unrecorded` or `mixed` for one skill's task set.

    `mixed` is returned rather than resolved here: `_refuse_mixed_recording`
    already names the offending tasks, which is a better message than anything
    the report-level check could produce, so a mixed skill is left to it.
    """
    tasks = result.get("tasks") or []
    recorded = sum(1 for t in tasks if t.get("score_by_seed") is not None)
    if not recorded:
        return "unrecorded"
    return "recorded" if recorded == len(tasks) else "mixed"


def _refuse_cross_skill_mix(report: dict) -> None:
    """Refuse a report where one skill is recorded and another is recomputed.

    `_refuse_mixed_recording` settles this inside a single skill. The same
    malformation one level up blends two skills' means into
    `between_skill_gap`, which is the number the signal-versus-noise verdict is
    read from: a gap whose two sides came from different scoring models belongs
    to neither, and the ratio computed from it looks like an ordinary ratio.

    Each skill passes its own per-skill check first, so this malformation is
    precisely the one that survives both -- it is only visible once the skills
    are compared with each other. That is the same shape as the defect this
    whole branch exists to repair: two places each individually correct, whose
    composition is a wrong answer nobody computed.

    Defensive, like its per-skill counterpart: `evaluate_skill` writes
    `score_by_seed` on every task of a result, so a report it produced cannot
    reach here. It exists so a report edited, merged or trimmed into that shape
    is refused rather than analysed as a blend.

    A skill that is itself mixed is ignored by the tally and left to
    `_refuse_mixed_recording`, which can name the tasks. An all-mixed or
    single-skill report therefore takes the more specific message.
    """
    states = {
        r.get("skill"): _recording_state(r)
        for r in (report.get("results") or [])
    }
    settled = set(states.values()) - {"mixed"}
    if len(settled) < 2:
        return
    recorded = sorted(s for s, v in states.items() if v == "recorded")
    unrecorded = sorted(s for s, v in states.items() if v == "unrecorded")
    raise CapsNotReproducible(
        f"{len(recorded)} of {len(states)} skills in this report record "
        f"score_by_seed ({', '.join(recorded)}) and {len(unrecorded)} do not "
        f"({', '.join(unrecorded)}). Each skill passes its own check, but the "
        "gap between them would then compare the harness's capped-mean model "
        "against the per-sample model, and that gap belongs to neither. "
        "Record the field on every skill or on none; if the report is a "
        "deliberately trimmed subset, drop it from those skills too so the "
        "analyser recomputes all of them by one rule."
    )


def _task_score_at_seed(task: dict, i: int, keys: list[str], capped_report: bool) -> float:
    """One task's score at seed `i`, preferring the number the harness recorded.

    Three cases, in the order they are trusted:

    1. The harness recorded `score_by_seed`. Read it. This is the whole point:
       the harness ran this model, so its number is the harness's number and
       not a reconstruction that has to be kept in step with the harness by
       hand.
    2. No such field, on a task set where no task has it -- a report predating
       it, or one trimmed down to its criteria. Recomputed here from the
       stored samples, capped only if the report says it is capped. This is
       the same shape as the `mean_capped` fallback in `analyse`: the field is
       the fast path, the recomputation is the compatibility path, and both
       read `mean_capped` to decide. A task set where *some* tasks have the
       field is refused by `_refuse_mixed_recording` before this runs, so
       choosing per task here cannot blend the two.
    3. A capped report whose task also carries no per-seed text. The cap cannot
       be reproduced from anything, and the uncapped number this would produce
       contradicts the report's own `mean_capped`. Refuse.

    The fabrication veto is applied last on every path, including the
    recomputation, so a vetoed task reads 0.0 whatever the cap produced.
    """
    recorded = task.get("score_by_seed")
    if recorded is not None:
        if i >= len(recorded):
            raise CapsNotReproducible(
                f"task {task.get('id')!r} records {len(recorded)} per-seed scores "
                f"but seed {i} was requested; the report is inconsistent with the "
                "seed count it is being analysed at"
            )
        return recorded[i]

    if not capped_report:
        return 0.0 if task["fabrication_vetoed"] else sum(
            task["criteria"][k]["samples"][i] * task["criteria"][k]["weight"]
            for k in keys
        )

    if not (task.get("candidates") or {}):
        raise CapsNotReproducible(
            f"task {task.get('id')!r} is part of a capped report but records "
            "neither score_by_seed nor the per-seed text the cap is derived "
            "from. Analysing it uncapped would contradict its own mean_capped."
        )

    apply_placeholder_cap, _, worst_case_placeholders = _cap_helpers()
    worst = worst_case_placeholders({
        s: {"placeholders": p}
        for s, p in task_placeholders_by_seed(task).items()
    })
    score = sum(
        apply_placeholder_cap(k, task["criteria"][k]["samples"][i], worst)
        * task["criteria"][k]["weight"]
        for k in keys
    )
    return 0.0 if task["fabrication_vetoed"] else score


def seed_scores(result: dict, seeds: int) -> list[float]:
    """The skill's mean score computed one seed at a time.

    Reads the harness's own `score_by_seed` wherever the report carries it. The
    classification used to be recomputed here from the stored candidate text,
    which meant the analyser reached its signal-versus-noise verdict through a
    scoring model the harness never ran -- the harness caps a criterion's
    aggregated mean, this capped each sample. Both are defensible alone, and
    the disagreement between them is the one shape of drift this module exists
    to catch, so the number is taken rather than reconstructed.

    Recomputation survives only for reports predating the field, and is the
    same shape as the `mean_capped` fallback in `analyse`. Which of the two a
    task takes is decided per task, so the whole task set is checked for a mix
    first: a set where some tasks record the field and some do not raises
    `CapsNotReproducible` rather than averaging the harness's model with this
    module's. A capped report whose task offers nothing to recompute from
    raises the same way, rather than reporting an uncapped score.

    The veto still wins: a fabricating task reads 0.0 whatever the cap
    produced, because one fabricating generation out of three is meant to zero
    the task.
    """
    _refuse_mixed_recording(result)
    keys = weighted_criteria(result)
    capped_report = report_is_capped(result)
    out = []
    for i in range(seeds):
        per_task = [
            _task_score_at_seed(task, i, keys, capped_report)
            for task in result["tasks"]
        ]
        out.append(st.mean(per_task) if per_task else 0.0)
    return out


def analyse(report: dict) -> dict:
    seeds = report["results"][0]["seeds"]
    _refuse_cross_skill_mix(report)
    per_skill = {r["skill"]: seed_scores(r, seeds) for r in report["results"]}

    pairs = 0
    full_range = []
    sds = []
    for r in report["results"]:
        for t in r["tasks"]:
            for key, crit in t["criteria"].items():
                if crit.get("weight", 0) <= 0:
                    continue
                pairs += 1
                samples = crit["samples"]
                sds.append(crit["stdev"])
                if max(samples) - min(samples) >= 10:
                    full_range.append((r["skill"], t["id"], key, samples))

    gens = 0
    fab_gens = 0
    inferred = 0
    vetoed = 0
    tasks = 0
    # Split by whether the mechanical veto fired. A veto pins a task to 0
    # regardless of how it scored, so a single mean conflates "writes badly"
    # with "invents figures". Those need different fixes, so both are reported.
    unvetoed_means: dict[str, float] = {}
    unvetoed_counts: dict[str, int] = {}
    fabrication_gap: dict[str, float] = {}
    for r in report["results"]:
        # Prefer the recorded task score; older or minimal fixtures may only
        # carry the weighted criteria, so fall back to those rather than
        # requiring a field every report shape has to have.
        #
        # The fallback must read mean_capped, not mean. Since the placeholder
        # caps landed, the harness computes a task total from the capped values,
        # so a fallback built on mean would silently report an uncapped number
        # for exactly the fixtures that lack a recorded score. Reports written
        # before the caps have no mean_capped, and for those mean IS the value
        # the total was computed from, so it remains the correct fallback.
        def task_score(t):
            if "score" in t:
                return t["score"]
            return sum(
                c.get("mean_capped", c["mean"]) * c["weight"]
                for c in t["criteria"].values() if c["weight"] > 0
            )

        clean = [task_score(t) for t in r["tasks"] if not t["fabrication_vetoed"]]
        unvetoed_counts[r["skill"]] = len(clean)
        unvetoed_means[r["skill"]] = round(st.mean(clean), 2) if clean else None
        if clean:
            fabrication_gap[r["skill"]] = round(r["mean_score"] - st.mean(clean), 2)
        for t in r["tasks"]:
            tasks += 1
            vetoed += 1 if t["fabrication_vetoed"] else 0
            # Per-generation fabrication is the mechanical per-seed flag.
            # It was previously inferred from a truthfulness score of 0, which
            # silently counted "wrote untruthfully" as "invented a number" and
            # reported 50% where the real figure was different.
            flags = t.get("fabrication_by_seed")
            if flags is None:
                # Report predates the per-seed field. Say so rather than guess.
                inferred += len(t["criteria"].get("truthfulness", {}).get("samples", []))
                continue
            for flag in flags.values():
                gens += 1
                if flag:
                    fab_gens += 1

    swings = {k: (max(v) - min(v)) for k, v in per_skill.items()}
    means = {k: st.mean(v) for k, v in per_skill.items()}
    if len(means) == 2:
        gap = abs(list(means.values())[0] - list(means.values())[1])
    else:
        gap = max(means.values()) - min(means.values()) if means else 0.0
    max_swing = max(swings.values()) if swings else 0.0

    # On the live run the overall means said "these skills write badly" while the
    # unvetoed means said "these skills write well and invent numbers". If the
    # gap is material the headline mean is measuring fabrication, not prose.
    material_gaps = {
        k: v for k, v in fabrication_gap.items() if abs(v) >= 1.0
    }
    headline_is_fabrication = bool(material_gaps)

    return {
        "backend": report.get("backend"),
        "synthetic": report.get("synthetic"),
        "judge_temperature": report.get("judge_temperature"),
        "seeds": seeds,
        "unvetoed_means": unvetoed_means,
        "unvetoed_task_counts": unvetoed_counts,
        "overall_minus_unvetoed": fabrication_gap,
        "material_fabrication_gaps": material_gaps,
        # If True, quoting mean_score alone misattributes a fabrication defect
        # to prose quality.
        "headline_mean_misattributes_fabrication": headline_is_fabrication,
        "per_skill_seed_means": per_skill,
        "skill_means": means,
        "seed_swing": swings,
        "between_skill_gap": round(gap, 2),
        "max_mean_swing": round(max_swing, 2),
        "gap_over_swing": round(gap / max_swing, 2) if max_swing else None,
        # Zero seed swing means the judge was perfectly repeatable, which is the
        # strongest possible signal. Guarding this on `max_swing` being truthy
        # would invert the answer and report steady judges as unsupported.
        "ordering_supported": bool(gap > max_swing),
        "criterion_task_pairs": pairs,
        "full_range_disagreements": len(full_range),
        "full_range_detail": [
            {"skill": s, "task": t, "criterion": k, "samples": v}
            for s, t, k, v in full_range
        ],
        "full_range_rate": round(100 * len(full_range) / pairs, 1) if pairs else 0.0,
        "mean_criterion_stdev": round(st.mean(sds), 2) if sds else 0.0,
        "generations": gens,
        "fabricating_generations": fab_gens,
        "fabrication_rate_per_generation": round(100 * fab_gens / gens, 1) if gens else None,
        # Non-zero when the report predates the per-seed field, so the rate is
        # genuinely unavailable rather than silently approximated.
        "fabrication_inferred_from_truthfulness": inferred,
        "tasks": tasks,
        "vetoed_tasks": vetoed,
        "veto_rate_worst_case": round(100 * vetoed / tasks, 1) if tasks else 0.0,
    }


def render(a: dict, b: dict | None = None) -> None:
    print("=" * 72)
    print("  LAYER 3 VARIANCE ANALYSIS")
    print("=" * 72)
    print(f"backend {a['backend']}   synthetic={a['synthetic']}   seeds={a['seeds']}")

    print("\n--- skill means and seed swing ---")
    for skill, means in a["per_skill_seed_means"].items():
        swing = a["seed_swing"][skill]
        print(f"  {skill:<26}{[round(m, 2) for m in means]}"
              f"  mean={a['skill_means'][skill]:.2f}  swing={swing:.2f}")

    print("\n--- is the difference real? ---")
    print(f"  between-skill gap                    : {a['between_skill_gap']}")
    print(f"  largest seed-to-seed swing of a mean : {a['max_mean_swing']}")
    if a["max_mean_swing"] == 0:
        print("  the judge was perfectly repeatable across seeds")
    elif a["gap_over_swing"] is not None:
        print(f"  ratio                                : {a['gap_over_swing']}x")
    print(f"  ordering supported                   : {a['ordering_supported']}")
    if not a["ordering_supported"]:
        print("  => the gap does not exceed the noise. Do not report a ranking.")

    print("\n--- judge self-consistency ---")
    print(f"  criterion-task pairs                 : {a['criterion_task_pairs']}")
    print(f"  mean criterion stdev                 : {a['mean_criterion_stdev']}")
    print(f"  full-range (0 vs 10) disagreements   : {a['full_range_disagreements']}"
          f"  ({a['full_range_rate']}%)")
    for d in a["full_range_detail"]:
        print(f"    {d['skill']:<22}{d['task']:<15}{d['criterion']:<14}{d['samples']}")
    print("  These judgements carry no information and should not be averaged.")

    print("\n--- fabrication ---")
    if a["fabrication_inferred_from_truthfulness"]:
        print("  UNMEASURABLE: this report predates the per-seed fabrication flag, so a")
        print(f"  per-generation rate cannot be computed ({a['fabrication_inferred_from_truthfulness']}"
              " generations lack it). Re-run the harness; the task-level figure")
        print("  below is a worst-case rate, not a frequency.")
    else:
        print(f"  per generation (mechanical)           : "
              f"{a['fabricating_generations']}/{a['generations']} = "
              f"{a['fabrication_rate_per_generation']}%")
    print(f"  task level (worst-case veto rule)    : {a['vetoed_tasks']}"
          f"/{a['tasks']} = {a['veto_rate_worst_case']}%")
    print("  The task figure is a worst-case rate: one fabricating generation out")
    print("  of three zeroes the task. Right rule for fabrication, wrong as a")
    print("  frequency. Quote the per-generation number.")

    print("\n--- writing quality vs fabrication (they are different defects) ---")
    print(f"  {'skill':<24}{'overall':>9}{'unvetoed':>10}{'n':>4}   delta")
    for skill in a["skill_means"]:
        u = a["unvetoed_means"].get(skill)
        n = a["unvetoed_task_counts"].get(skill, 0)
        if u is None:
            print(f"  {skill:<24}{a['skill_means'][skill]:>9.2f}{'n/a':>10}{n:>4}"
                  f"   every task vetoed")
            continue
        print(f"  {skill:<24}{a['skill_means'][skill]:>9.2f}{u:>10.2f}{n:>4}"
              f"   {a['overall_minus_unvetoed'][skill]:+.2f}")
    print("  overall counts vetoed tasks as zeros; unvetoed drops them.")
    if a["headline_mean_misattributes_fabrication"]:
        print("\n  MATERIAL GAP: for "
              + ", ".join(sorted(a["material_fabrication_gaps"]))
              + " the overall mean understates the prose by >=1.0 point.")
        print("  These skills do not write badly; they invent figures. Quoting the")
        print("  headline mean would point the fix at the wrong defect.")
    else:
        print("\n  No material gap: overall and unvetoed agree, so the headline mean")
        print("  is not being driven by the veto.")

    if b:
        print("\n--- sample-size sensitivity ---")
        for skill in a["skill_means"]:
            other = b["skill_means"].get(skill)
            if other is None:
                continue
            print(f"  {skill:<26} other={other:>5.2f}   this={a['skill_means'][skill]:>5.2f}"
                  f"   shift={a['skill_means'][skill] - other:+.2f}")
        oa = sum(a["skill_means"].values()) / len(a["skill_means"])
        ob = sum(b["skill_means"].values()) / len(b["skill_means"])
        print(f"  {'OVERALL':<26} other={ob:>5.2f}   this={oa:>5.2f}   shift={oa - ob:+.2f}")

    print("=" * 72)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("report", type=Path)
    ap.add_argument("--compare", type=Path, default=None,
                    help="a second report, e.g. a 1-seed run against a 3-seed one")
    args = ap.parse_args()

    try:
        a = analyse(json.loads(args.report.read_text(encoding="utf-8")))
        b = analyse(json.loads(args.compare.read_text(encoding="utf-8"))) if args.compare else None
    except CapsNotReproducible as exc:
        # Refusing has to be visible from the command line, or the exit status
        # is the only signal and a reader running this by hand sees nothing.
        print(f"REFUSING TO ANALYSE: {exc}", file=sys.stderr)
        return 1
    render(a, b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())