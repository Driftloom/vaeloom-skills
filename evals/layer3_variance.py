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

Usage:
    python evals/layer3_variance.py layer3-live-s3.json
    python evals/layer3_variance.py report.json --compare other.json
"""
from __future__ import annotations

import argparse
import json
import statistics as st
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


def seed_scores(result: dict, seeds: int) -> list[float]:
    """The skill's mean score computed one seed at a time."""
    keys = weighted_criteria(result)
    out = []
    for i in range(seeds):
        per_task = []
        for task in result["tasks"]:
            score = sum(task["criteria"][k]["samples"][i] * task["criteria"][k]["weight"]
                        for k in keys)
            per_task.append(0.0 if task["fabrication_vetoed"] else score)
        out.append(st.mean(per_task) if per_task else 0.0)
    return out


def analyse(report: dict) -> dict:
    seeds = report["results"][0]["seeds"]
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

    a = analyse(json.loads(args.report.read_text(encoding="utf-8")))
    b = analyse(json.loads(args.compare.read_text(encoding="utf-8"))) if args.compare else None
    render(a, b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())