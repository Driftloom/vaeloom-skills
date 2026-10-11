"""Inter-judge calibration: judge the same candidates with a second model family.

Self-agreement at temperature 0.0 is trivially perfect and says nothing about
whether the rubric is right. Two judges from different families agreeing is
evidence the anchors describe something real; two judges diverging localises
exactly which criterion is ambiguous.

No generation happens here. The candidates come from a committed live report, so
this measures the rubric rather than the generator, and costs one judging call
per criterion-task pair.

Credentials come from the API app's .env (LLM_PROVIDER=groq, LLM_API_KEY,
LLM_MODEL) -- the same miss as the Layer 3 live run, where an earlier check that
read only process env vars concluded no keys existed.

Run:  python evals/layer3_interjudge.py [--report layer3-live-s3.json]
Exit: 0 on a completed comparison, 2 when the report cannot be compared
against the current rubric or scoring policy. It does not gate on agreement --
a rubric two judges disagree about is a finding to act on, not a build failure.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics as st
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_CANDIDATES = (
    ROOT.parent / "Vaeloom" / ".env",
    ROOT / ".env",
)

GRADING_INSTRUCTIONS = (
    "You are a strict rubric grader. Reply with JSON only: "
    '{"score": <int 0-10>, "rationale": "<one sentence>"}. '
    "Use only the rubric anchors provided. Do not reward length."
)


def load_env() -> dict:
    for path in ENV_CANDIDATES:
        if path.is_file():
            values = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    values[k.strip()] = v.strip().strip('"').strip("'")
            if values.get("LLM_API_KEY"):
                return values
    raise SystemExit(
        "FATAL: no LLM_API_KEY found. Looked in:\n  "
        + "\n  ".join(str(p) for p in ENV_CANDIDATES)
        + "\nRefusing to run without credentials rather than report a made-up number."
    )


class SecondJudge:
    def __init__(self, model: str, base_url: str, api_key: str) -> None:
        self.model = model
        self.base = base_url.rstrip("/")
        self.key = api_key
        self.calls = 0

    def score(self, criterion: dict, task: dict, candidate: str, attempt: int = 0) -> int:
        anchors = "\n".join(
            f"  {k}: {v}" for k, v in sorted(criterion["anchors"].items())
        )
        prompt = (
            f"RUBRIC CRITERION: {criterion['label']}\n{anchors}\n\n"
            f"SOURCE TEXT (the only claims that are true; the candidate may not add any):\n"
            f"  {task['input']}\n\n"
            f"CANDIDATE OUTPUT (score this):\n  {candidate}\n\n"
            f"QUESTION: {task['judge_question']}\n\n"
            "Score the CANDIDATE OUTPUT against the anchors. Return JSON only."
        )
        body = json.dumps({
            "model": self.model,
            # gpt-oss rejects the "system" role with a 403, so the grading
            # instructions are prepended to the user turn instead.
            "messages": [{"role": "user", "content": GRADING_INSTRUCTIONS + "\n\n" + prompt}],
            "temperature": 0.0,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                # Without an explicit User-Agent the edge returns 403 code 1010.
                "User-Agent": "curl/8.0",
                "Authorization": f"Bearer {self.key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                text = json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"]
            self.calls += 1
        except urllib.error.HTTPError as exc:
            # Bounded backoff. An unbounded retry turns a rate limit into a hung
            # run, which is how the first version of this script died.
            if exc.code == 429 and attempt < 6:
                time.sleep(12 * (attempt + 1))
                return self.score(criterion, task, candidate, attempt + 1)
            raise SystemExit(
                f"FATAL: second judge returned HTTP {exc.code} after {attempt} retries: "
                f"{exc.read().decode('utf-8')[:200]}"
            ) from None
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise SystemExit(f"FATAL: second judge returned no JSON: {text[:200]}")
        return json.loads(match.group(0))["score"]


def provenance_problem(report: dict, rubric: dict, report_name: str) -> str | None:
    """Why this report may not be compared against a fresh judgement, or None.

    Two independent questions, and they fail independently.

    **Rubric.** A report produced under different anchors cannot be compared
    against one judged with the current ones: the tool would measure the rubric
    change and report it as judge disagreement. That mistake cost one wasted
    measurement here before this check existed.

    **Scoring.** A report produced under different scoring *functions* has the
    same problem one level down, and the rubric check cannot see it -- the caps
    landed with the anchors untouched, so the two fingerprints that matter
    disagree while the one being checked matches. Running this check before the
    caps existed cost a full 30-call comparison and an exit 0 where the honest
    answer was exit 2.

    Returns the reason rather than raising, so the caller prints it once and
    exits 2. A test can therefore ask whether a report would be accepted
    without credentials and without spending a call, which is the only way to
    test the accept case at all.
    """
    sys.path.insert(0, str(ROOT / "evals"))
    from layer3_judge import rubric_fingerprint, scoring_fingerprint

    current = rubric_fingerprint(rubric)
    recorded = report.get("rubric_fingerprint")
    if recorded is None:
        return (f"{report_name} records no rubric_fingerprint, so it "
                "cannot be shown to have been scored against the current anchors.\n"
                "       Re-generate it:\n"
                "         python evals/layer3_judge.py --backend openai_compatible "
                "--split all --seeds 3 --json <report>")
    if recorded != current:
        return (f"{report_name} was scored against rubric "
                f"{recorded}, but the current rubric is {current}.\n"
                "       Comparing them would measure the rubric change, not "
                "judge agreement. Re-generate the report first.")

    current_scoring = scoring_fingerprint()
    recorded_scoring = report.get("scoring_fingerprint")
    if recorded_scoring is None:
        return (f"{report_name} records no scoring_fingerprint, so it cannot be "
                "shown to have been scored under the current placeholder caps. "
                "Matching anchors are not sufficient: the cap and "
                "classification functions are what turn them into numbers.\n"
                "       Re-generate it:\n"
                "         python evals/layer3_judge.py --backend openai_compatible "
                "--split all --seeds 3 --json <report>")
    if recorded_scoring != current_scoring:
        return (f"{report_name} was scored under scoring policy "
                f"{recorded_scoring}, but the current one is {current_scoring}.\n"
                "       The anchors are the same, so the rubric fingerprint "
                "matches; what moved is the code that caps and classifies. "
                "Comparing them would measure the policy change, not judge "
                "agreement. Re-generate the report first.")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=Path, default=ROOT / "layer3-live-s3.json")
    ap.add_argument("--out", type=Path, default=None,
                    help="write the agreement result as JSON")
    args = ap.parse_args()

    env = load_env()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    spec = json.loads((ROOT / "evals" / "layer3_tasks.json").read_text(encoding="utf-8"))
    rubric = spec["rubric"]
    active = [c for c in rubric["criteria"] if c.get("enabled", True) and c["weight"] > 0]

    problem = provenance_problem(report, rubric, args.report.name)
    if problem is not None:
        print(f"FATAL: {problem}", file=sys.stderr)
        return 2

    judge = SecondJudge(
        env.get("LLM_MODEL", "openai/gpt-oss-120b"),
        "https://api.groq.com/openai/v1",
        env["LLM_API_KEY"],
    )

    pairs: list[dict] = []
    for result in report["results"]:
        meta = {t["id"]: t for t in spec["skills"][result["skill"]]["tasks"]}
        for t in result["tasks"]:
            task = meta[t["id"]]
            candidate = t["candidates"]["0"]
            for c in active:
                pairs.append({
                    "skill": result["skill"],
                    "task": t["id"],
                    "criterion": c["key"],
                    "primary": t["criteria"][c["key"]]["samples"][0],
                    "second": judge.score(c, task, candidate),
                })

    deltas = [abs(p["primary"] - p["second"]) for p in pairs]
    exact = sum(1 for p in pairs if p["primary"] == p["second"])
    per_criterion: dict[str, list[int]] = {}
    for p in pairs:
        per_criterion.setdefault(p["criterion"], []).append(
            abs(p["primary"] - p["second"])
        )

    print("=" * 72)
    print(f"INTER-JUDGE AGREEMENT   primary vs {judge.model}")
    print("=" * 72)
    print(f"  judgements compared          : {len(pairs)} ({judge.calls} calls)")
    print(f"  exact agreement             : {exact}/{len(pairs)} "
          f"({100 * exact / len(pairs):.0f}%)")
    print(f"  mean absolute difference    : {st.mean(deltas):.2f} / 10")
    print(f"  worst difference            : {max(deltas)}")
    print()
    print("  per criterion -- a high value means the anchor is ambiguous:")
    for key, ds in sorted(per_criterion.items(), key=lambda kv: -st.mean(kv[1])):
        verdict = "AMBIGUOUS" if st.mean(ds) >= 3.0 else (
            "weak" if st.mean(ds) >= 1.5 else "usable")
        print(f"    {key:<16} n={len(ds):<4} mean|delta|={st.mean(ds):.2f}  "
              f"max={max(ds):<4} {verdict}")

    big = [p for p in pairs if abs(p["primary"] - p["second"]) >= 5]
    print()
    print(f"  disagreements >= 5 points: {len(big)}")
    for p in big[:10]:
        print(f"    {p['skill']:<22}{p['task']:<16}{p['criterion']:<15}"
              f"primary={p['primary']}  second={p['second']}")

    worst = max(per_criterion, key=lambda k: st.mean(per_criterion[k]))
    print()
    print(f"  Weakest criterion: {worst} (mean |delta| {st.mean(per_criterion[worst]):.2f}).")
    print("  Scores on that criterion should not be quoted as precise until its")
    print("  anchors distinguish the levels better.")

    if args.out:
        args.out.write_text(json.dumps({
            "second_judge": judge.model,
            "compared": len(pairs),
            "exact_agreement_pct": round(100 * exact / len(pairs), 1),
            "mean_abs_delta": round(st.mean(deltas), 2),
            "worst_delta": max(deltas),
            "per_criterion_mean_delta": {k: round(st.mean(v), 2)
                                        for k, v in per_criterion.items()},
            "weakest_criterion": worst,
            "pairs": pairs,
        }, indent=2), encoding="utf-8")
        print(f"\n  written to {args.out}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())