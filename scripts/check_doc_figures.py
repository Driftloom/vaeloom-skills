"""Assert every quoted figure in docs/layer3-judging.md against the committed reports.

A document that quotes numbers nothing checks is the same defect the variance
analyser exists to prevent, one level up. This asserts the doc's claims against
the live reports and the analyser's own output, so a stale figure fails CI
instead of surviving until someone re-reads the prose.

It exists because it already caught two: the 1-seed mean for
`resume-bullet-writer` was quoted as 5.44 when the regenerated report read 7.35,
and the per-generation fabrication rate was written as 25% against an analyser
output of 25.0%.

Limitation, stated rather than papered over: this checks that each figure is
*present* in the prose, not that it appears in the right place. If a figure is
quoted in two places and only one is wrong, a single correct occurrence satisfies
the check. That is why the number appears both in the results tables and in the
prose -- there is no anchor to tie a figure to its claim. Making it positional
would mean hand-maintaining a map of which line asserts what, which drifts for its
own reasons. Treat this as a floor on doc accuracy, not a proof of it.

Run:  python scripts/check_doc_figures.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "layer3-judging.md"
ONE_SEED = "layer3-live-report.json"
THREE_SEED = "layer3-live-s3.json"
INTERJUDGE = "layer3-interjudge.json"

sys.path.insert(0, str(ROOT / "evals"))
from layer3_variance import analyse  # noqa: E402


def interjudge_figures() -> list[tuple[str, str]]:
    """Figures quoted from the cross-model comparison, if that run is committed."""
    path = ROOT / INTERJUDGE
    if not path.is_file():
        return []
    d = json.loads(path.read_text(encoding="utf-8"))
    out = [
        ("inter-judge exact agreement", f"{int(d['exact_agreement_pct'])}%"),
        ("inter-judge mean difference", f"{d['mean_abs_delta']:.2f}"),
        ("inter-judge worst difference", str(d["worst_delta"])),
    ]
    for key, value in d["per_criterion_mean_delta"].items():
        out.append((f"inter-judge delta {key}", f"{value:.2f}"))
    return out


def _variants(value: float) -> tuple[str, ...]:
    """Both renderings of a float that does not land exactly on two places.

    The analyser prints Python's round-half-even while the report stores
    round-half-up, so 6.105 can appear as either 6.10 or 6.11. The prose may use
    either; forcing one would put a number in the doc that neither tool emits.
    """
    lo, hi = f"{value:.2f}", f"{value + 0.01:.2f}"
    return (lo,) if lo == hi else (lo, hi)


def main() -> int:
    for report in (ONE_SEED, THREE_SEED):
        if not (ROOT / report).is_file():
            print(f"FATAL: {report} is missing; cannot verify the docs against data",
                  file=sys.stderr)
            return 1

    doc = DOC.read_text(encoding="utf-8")
    a1 = analyse(json.loads((ROOT / ONE_SEED).read_text(encoding="utf-8")))
    a3 = analyse(json.loads((ROOT / THREE_SEED).read_text(encoding="utf-8")))

    checks: list[tuple[str, str]] = []
    alternate: dict[str, str] = {}

    def need(label: str, needle: str, alt: str | None = None) -> None:
        checks.append((label, needle))
        if alt:
            alternate[label] = alt

    for skill, mean in a3["skill_means"].items():
        lo, hi = _variants(mean)
        need(f"3-seed mean {skill}", lo, hi)
    for skill, mean in a1["skill_means"].items():
        lo, hi = _variants(mean)
        need(f"1-seed mean {skill}", lo, hi)

    lo, hi = _variants(a3["between_skill_gap"])
    need("between-skill gap", lo, hi)
    need("max mean swing", f"{a3['max_mean_swing']}")
    if a3["gap_over_swing"]:
        need("gap/swing ratio", f"{a3['gap_over_swing']:.1f}×")

    need("per-generation fabrication", f"{a3['fabrication_rate_per_generation']}%")
    need("task-level fabrication", f"{a3['veto_rate_worst_case']}%")
    need("fabrication numerator",
         f"{a3['fabricating_generations']} of {a3['generations']}")

    need("full-range disagreements",
         f"{a3['full_range_disagreements']} of {a3['criterion_task_pairs']}")
    need("full-range rate", f"{a3['full_range_rate']}%")

    for skill in a3["skill_means"]:
        u = a3["unvetoed_means"][skill]
        need(f"unvetoed mean {skill}", f"{u:.2f}", f"{u + 0.01:.2f}")

    for skill, means in a3["per_skill_seed_means"].items():
        need(f"per-seed means {skill}",
             "`[" + ", ".join(_variants(m)[0] for m in means) + "]`",
             "`[" + ", ".join(_variants(m)[-1] for m in means) + "]`")

    # Criterion-task pairs is a denominator the doc quotes in prose.
    need("criterion-task pairs", f"{a3['criterion_task_pairs']}")

    for label, needle in interjudge_figures():
        need(label, needle)

    missing = [
        (label, needle)
        for label, needle in checks
        if needle not in doc and alternate.get(label, "\0") not in doc
    ]
    for label, needle in checks:
        alt = alternate.get(label)
        ok = needle in doc or (alt is not None and alt in doc)
        print(f"{'ok  ' if ok else 'MISS'}  {label:<40} {needle}"
              + (f" (or {alt})" if alt else ""))

    print(f"\n{len(checks) - len(missing)}/{len(checks)} doc figures verified")
    if missing:
        print("\nSTALE OR MISSING -- docs/layer3-judging.md disagrees with the data:")
        for label, needle in missing:
            print(f"  {label}: expected {needle!r}")
        return 1

    print(f"gap={a3['between_skill_gap']} swing={a3['max_mean_swing']} "
          f"ratio={a3['gap_over_swing']} supported={a3['ordering_supported']}")
    print(f"fabrication {a3['fabricating_generations']}/{a3['generations']} "
          f"= {a3['fabrication_rate_per_generation']}%")
    print(f"headline misattributes fabrication: "
          f"{a3['headline_mean_misattributes_fabrication']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())