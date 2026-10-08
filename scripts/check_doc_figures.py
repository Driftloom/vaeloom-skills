"""Assert every quoted figure in docs/layer3-judging.md against the committed reports.

A document that quotes numbers nothing checks is the same defect the variance
analyser exists to prevent, one level up. This asserts the doc's claims against
the live reports and the analyser's own output, so a stale figure fails CI
instead of surviving until someone re-reads the prose.

It exists because it already caught two: the 1-seed mean for
`resume-bullet-writer` was quoted as 5.44 when the regenerated report read 7.35,
and the per-generation fabrication rate was written as 25% against an analyser
output of 25.0%.

Run:  python scripts/check_doc_figures.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "layer3-judging.md"
ONE_SEED = "layer3-live-report.json"
THREE_SEED = "layer3-live-s3.json"

sys.path.insert(0, str(ROOT / "evals"))
from layer3_variance import analyse  # noqa: E402


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

    def need(label: str, needle: str) -> None:
        checks.append((label, needle))

    for skill, mean in a3["skill_means"].items():
        need(f"3-seed mean {skill}", f"{mean:.2f}")
    for skill, mean in a1["skill_means"].items():
        need(f"1-seed mean {skill}", f"{mean:.2f}")

    need("between-skill gap", f"{a3['between_skill_gap']}")
    need("max mean swing", f"{a3['max_mean_swing']}")
    if a3["gap_over_swing"]:
        need("gap/swing ratio", f"{a3['gap_over_swing']:.1f}×")

    need("per-generation fabrication", f"{a3['fabrication_rate_per_generation']}%")
    need("task-level fabrication", f"{a3['veto_rate_worst_case']}%")
    need("fabrication numerator",
         f"{a3['fabricating_generations']} of {a3['generations']}")

    need("full-range disagreements", f"{a3['full_range_disagreements']} of 24")
    need("full-range rate", f"{a3['full_range_rate']}%")

    for skill in a3["skill_means"]:
        need(f"unvetoed mean {skill}", f"{a3['unvetoed_means'][skill]:.2f}")

    for skill, means in a3["per_skill_seed_means"].items():
        need(f"per-seed means {skill}",
             "`[" + ", ".join(f"{m:.2f}" for m in means) + "]`")

    missing = [(label, needle) for label, needle in checks if needle not in doc]
    for label, needle in checks:
        print(f"{'ok  ' if needle in doc else 'MISS'}  {label:<40} {needle}")

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