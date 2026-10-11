#!/usr/bin/env python3
"""Layer 3: rubric-anchored LLM judging for prose-only skills.

Layer 1 scores file structure. Layer 2 exercises helper scripts. Neither can say
whether a skill document, followed by a competent model, produces a good
resume bullet. This layer can -- and is the prerequisite for SkillOpt, which
optimises against exactly this kind of signal.

Design decisions, each of which exists because the alternative was dishonest:

**Mechanical evidence is computed first and handed to the judge.** Length,
passive-voice markers, filler, and whether the source contains any metric at all
are all decidable without a model. The judge sees them and is asked only about
what it alone can judge. This grounds the score and cuts paid calls roughly in
half.

**Anchored rubric.** Every criterion has concrete descriptors at 0, 5 and 10. A
judge asked to "rate quality 1-10" returns noise; one asked to place a specific
bullet against written anchors returns something arguable.

**Multiple seeds, variance reported.** A single unseeded judge number is not a
result. Every task is judged ``--seeds`` times and the mean, spread and standard
deviation are reported. A criterion whose seeds disagree wildly is reported as
unstable rather than averaged into a clean-looking score.

**The offline backend is marked synthetic and cannot produce a verdict.**
``--backend stub`` exists so the harness itself is testable in CI with no
credentials and no spend. It is deterministic and it is NOT a model. Any result
it produces carries ``synthetic: true``, and the summary refuses to print a
quality verdict for synthetic runs -- it prints a plumbing report instead. There
is no flag that turns a stub run into a claim.

**No credential is a hard error, not a silent fallback.** If a live backend is
selected and its credentials are missing, this exits non-zero. Silently degrading
to the stub would be the single most dangerous behaviour this script could have.

Usage:
    # harness self-check, offline, deterministic
    python evals/layer3_judge.py --backend stub --split held_out --seeds 3

    # live judging
    OPENAI_COMPATIBLE_BASE_URL=https://ollama.com/v1 \\
    OPENAI_COMPATIBLE_API_KEY=... \\
    OPENAI_COMPATIBLE_MODEL=<model> \\
    python evals/layer3_judge.py --backend openai_compatible --split held_out --seeds 3

    python evals/layer3_judge.py --list
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics as st
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_PATH = REPO_ROOT / "evals" / "layer3_tasks.json"

FILLER = (
    "synergy", "leveraged", "delve", "robust", "cutting-edge", "testament",
    "in today's", "passionate", "results-driven", "dynamic professional",
    "spearheaded", "utilize", "best-in-class",
)
PASSIVE_MARKERS = (
    "responsible for", "helped", "assisted", "worked on", "involved in",
    "participated", "contributed to", "was tasked", "duties included",
)

# Bracketed blanks the candidate is meant to fill in: [X], [X]%, $[Y]K, [10x].
# These are the rubric's preferred way to express an unknowable quantity, so they
# must not read as fabricated figures.
PLACEHOLDER_RE = re.compile(r"\[[^\]]*\]|\{[^}]*\}|<[^>]*>")

# A placeholder is "scaffolding" when it occupies a structural slot rather than
# naming a quantity. These are the three triggers from spec section 3.1 and the
# complete list -- a fourth would change behaviour that no decision covers.
_FORMULA_VARIABLE_RE = re.compile(r"^[XYZxyz]$")
_MEASURED_BY_RE = re.compile(r"\bas\s+measured\s+by\s*$", re.IGNORECASE)
_INSTRUCTION_VERBS = {
    "insert", "add", "describe", "specify", "list", "name", "fill",
    "enter", "replace", "provide", "detail", "quantify", "write", "state",
}
# Not a verb, but a bracket opening with "your" addresses the writer rather than
# naming a quantity, so it is scaffolding on the same footing as one.
_WRITER_MARKER = "your"
# Punctuation a bracket may put at either end of its first word: "[Insert: the
# metric]", "[describe the outcome (optional)]", "[**write** the summary]".
# Stripped from both ends so the word is still recognisable. This normalises one
# token before an exact lookup; it does not decide noun-ness from a character
# class, which is the inference that misread "[time-to-market]" as scaffolding.
_HEAD_PUNCTUATION = ".,:;!?()[]{}\"'*-–—"


def classify_placeholders(text: str) -> dict:
    """Classify every placeholder as scaffolding or named.

    Answers exactly one question: does this placeholder occupy a structural
    slot? It does not judge whether the named quantity is a good thing to
    measure or whether the surrounding prose is good. Those remain the judge's.

    Three triggers, any one sufficient, and named is the default when none
    fires:

      1. the contents are a formula variable -- [X], [Y], [Z];
      2. the phrase "as measured by" immediately precedes it;
      3. the first word of the contents is an instruction verb, or is "your",
         which makes the bracket a note to the writer rather than a quantity.
         Punctuation around that word is stripped first, so "[Insert: the
         metric]" is recognised as the same instruction as "[insert]".

    The default is the half that matters. Scaffolding needs positive evidence of
    an instruction, so a quantity the output names for itself -- "[end-to-end
    cycle time]", "[time-to-market]" -- stays named. A rule that inferred a
    noun from the shape of the characters classified those as scaffolding.

    Only trigger 2 reads surrounding text, and it reads only what immediately
    precedes the placeholder -- never what follows it, and never at a distance.
    """
    total = named = scaffolded = 0
    for match in PLACEHOLDER_RE.finditer(text):
        total += 1
        inner = match.group(0)[1:-1].strip()
        if _FORMULA_VARIABLE_RE.match(inner):
            scaffolded += 1
            continue
        before = text[: match.start()].rstrip()
        if _MEASURED_BY_RE.search(before):
            scaffolded += 1
            continue
        words = inner.lower().split()
        head = words[0].strip(_HEAD_PUNCTUATION) if words else ""
        if head in _INSTRUCTION_VERBS or head == _WRITER_MARKER:
            scaffolded += 1
            continue
        named += 1
    return {"total": total, "named": named, "scaffolded": scaffolded}


# Word-boundary variants. Matching a bare substring misses every morphological
# form, so "leveraged" would not catch "leveraging" and "synergy" would not catch
# "synergies" -- which is precisely the vocabulary a model actually reaches for.
# Inflectional suffixes are therefore stripped to a stem and the stem is matched
# with a short tail. Appending suffixes to the full term does not work: "synergy"
# + a suffix cannot match "synerg"+"ies".
_INFLECTIONS = ("ing", "ies", "ied", "ed", "es", "s", "y")


def _stem(term: str) -> str:
    lowered = term.lower()
    for suffix in _INFLECTIONS:
        if lowered.endswith(suffix) and len(lowered) - len(suffix) >= 4:
            return lowered[: -len(suffix)]
    return lowered.rstrip("e") if lowered.endswith("e") and len(lowered) > 4 else lowered


def _find_terms(haystack: str, terms) -> list[str]:
    found = []
    for term in terms:
        stem = re.escape(_stem(term))
        # \w{0,4} covers the inflectional tail without reaching whole words that
        # merely start the same way.
        if re.search(rf"\b{stem}\w{{0,4}}\b", haystack, re.IGNORECASE):
            found.append(term)
    return found


# ── mechanical evidence (no model involved) ──────────────────────────────


def mechanical_evidence(text: str, expectations: dict) -> dict:
    """Everything decidable without a model.

    Deliberately not a score. It is evidence the judge is shown, and a hard
    fabrication tripwire that can veto a high judge score outright.
    """
    lowered = text.lower()
    words = len(text.split())
    hits = _find_terms(lowered, PASSIVE_MARKERS)
    filler = _find_terms(lowered, FILLER)
    has_number = bool(re.search(r"\d", text))
    # Fabrication is a number in the output that the source never contained.
    # (This was previously inverted, which flagged truthful restatements as
    # fabrication and passed real fabrication -- the worst possible failure for
    # the highest-severity check in the domain.)
    #
    # Placeholders are exempt. "[X]%", "[X]TB" and "$[Y]K" contain no digits so
    # they never reached here, but "[10]%" or a stray year would, and vetoing a
    # candidate for marking a blank would punish exactly the behaviour the
    # rubric's truthfulness anchor rewards.
    _stripped = PLACEHOLDER_RE.sub("", text)
    invented = bool(re.search(r"\d", _stripped)) and bool(
        expectations.get("source_has_no_metric", False)
    )
    return {
        "words": words,
        "within_budget": words <= int(expectations.get("max_words", 60)),
        "passive_markers": hits,
        "filler_terms": filler,
        "contains_number": has_number,
        "fabrication_risk": bool(invented) if expectations.get("must_not_fabricate") else False,
        "placeholders": classify_placeholders(text),
    }


# ── judge backends ───────────────────────────────────────────────────────


class BackendUnavailable(RuntimeError):
    """Raised when a requested backend cannot serve. Never falls back."""


def _stub_score(task_id: str, criterion: str, seed: int) -> int:
    """Deterministic stand-in so the harness can be tested without a model.

    NOT a quality signal. It returns a fixed pattern so variance, aggregation
    and gate behaviour are all exercised, and every result it produces is
    labelled synthetic.

    Varies with ``seed`` deliberately: a constant would leave the variance
    computation and the instability detector as dead code in the only mode this
    harness can run without credentials.
    """
    seed_value = sum(ord(c) for c in f"{task_id}:{criterion}") + seed
    return [0, 5, 10][seed_value % 3]


class StubBackend:
    name = "stub"
    synthetic = True

    def generate(self, *, skill_doc: str, task_input: str, seed: int) -> str:
        """Deterministic stand-in producer, so generation plumbing is testable.

        NOT a model and not a rewrite. It produces a fixed, obviously synthetic
        candidate so that the judge path, the fabrication veto and the variance
        machinery are all exercised without credentials or spend.
        """
        if not skill_doc.strip():
            raise BackendUnavailable("stub generator received an empty skill document")
        # The marker is deliberately digit-free. A digit here would be scored as
        # a fabricated figure by mechanical_evidence, and the plumbing demo would
        # report a FABRICATION VETO that never actually happened.
        marker = chr(ord("a") + (seed % 26))
        return f"[synthetic-{marker}] Rewritten candidate for: {task_input}"

    def judge(self, *, task_id: str, criterion: str, prompt: str, seed: int) -> dict:
        if "rubric" not in prompt.lower():
            raise BackendUnavailable("stub backend expects the rubric in the prompt")
        # Varies by seed on purpose. If the stub returned a constant, the
        # variance computation and the instability detector would never fire,
        # and the only runnable mode of this harness would leave them untested.
        return {
            "score": _stub_score(task_id, criterion, seed),
            "rationale": f"synthetic (seed {seed})",
        }


class OpenAICompatibleBackend:
    """Any OpenAI Chat Completions endpoint.

    Matches the project's ``ollama_base_url`` (https://ollama.com) as well as
    Azure, vLLM, Groq's compatibility endpoint, and similar.
    """

    name = "openai_compatible"
    synthetic = False

    def __init__(self, temperature: float = 0.0) -> None:
        base = os.environ.get("OPENAI_COMPATIBLE_BASE_URL", "").strip()
        key = os.environ.get("OPENAI_COMPATIBLE_API_KEY", "").strip()
        self.model = os.environ.get("OPENAI_COMPATIBLE_MODEL", "").strip()
        if not base or not key or not self.model:
            raise BackendUnavailable(
                "openai_compatible needs OPENAI_COMPATIBLE_BASE_URL, "
                "OPENAI_COMPATIBLE_API_KEY and OPENAI_COMPATIBLE_MODEL. "
                "Refusing to fall back to the stub: a degraded backend would "
                "produce a fabricated quality score."
            )
        self.base = base.rstrip("/")
        self.key = key
        self.temperature = temperature

    def _chat(self, system: str, user: str, seed: int) -> str:
        import urllib.request

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "seed": seed,
        }
        req = urllib.request.Request(
            f"{self.base}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.key}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]

    def generate(self, *, skill_doc: str, task_input: str, seed: int) -> str:
        """Produce the candidate output the judge will score.

        This is the step that makes Layer 3 meaningful. Without it the judge is
        grading the task input against a rubric written about outputs, which
        measures nothing. The skill document is supplied verbatim so the score
        reflects what following this document produces.
        """
        if not skill_doc.strip():
            raise BackendUnavailable("skill document is empty; refusing to judge the skill")
        return self._chat(
            "You rewrite resume bullets. Follow the skill playbook exactly. "
            "Return only the rewritten bullet, no preamble, no quotes, no explanation.",
            f"SKILL PLAYBOOK:\n{skill_doc}\n\n"
            f"REWRITE THIS BULLET:\n{task_input}",
            seed,
        ).strip()

    def judge(self, *, task_id: str, criterion: str, prompt: str, seed: int) -> dict:
        text = self._chat(
            "You are a strict rubric grader. Reply with JSON only: "
            '{"score": <int 0-10>, "rationale": "<one sentence>"}. '
            "Use only the rubric anchors provided. Do not reward length.",
            prompt,
            seed,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise BackendUnavailable(f"judge returned non-JSON for {task_id}/{criterion}: {text[:120]}")
        parsed = json.loads(match.group(0))
        return {"score": max(0, min(10, int(parsed["score"]))), "rationale": parsed.get("rationale", "")}


def build_backend(name: str, temperature: float = 0.0):
    if name == "stub":
        return StubBackend()
    if name == "openai_compatible":
        return OpenAICompatibleBackend(temperature)
    raise BackendUnavailable(f"unknown backend {name!r}; expected 'stub' or 'openai_compatible'")


# ── prompt construction ──────────────────────────────────────────────────


def build_prompt(task: dict, criterion: dict, evidence: dict, candidate: str) -> str:
    anchors = "\n".join(f"  {score}: {text}" for score, text in sorted(criterion["anchors"].items()))
    return (
        f"RUBRIC CRITERION: {criterion['label']}\n"
        f"{anchors}\n\n"
        f"SOURCE TEXT (the only claims that are true; the candidate may not add any):\n"
        f"  {task['input']}\n\n"
        f"CANDIDATE OUTPUT (score this):\n"
        f"  {candidate}\n\n"
        f"MECHANICAL EVIDENCE (already verified, do not re-derive):\n"
        f"  words={evidence['words']} within_budget={evidence['within_budget']}\n"
        f"  passive_markers={evidence['passive_markers']}\n"
        f"  filler_terms={evidence['filler_terms']}\n"
        f"  contains_number={evidence['contains_number']}\n"
        f"  fabrication_risk={evidence['fabrication_risk']}\n"
        f"  placeholders: {evidence['placeholders']['total']} total, "
        f"{evidence['placeholders']['named']} named, "
        f"{evidence['placeholders']['scaffolded']} scaffolding\n\n"
        f"QUESTION: {task['judge_question']}\n\n"
        f"Score the CANDIDATE OUTPUT against the anchors. The mechanical evidence is "
        f"context, not the score. Return JSON only."
    )


# ── evaluation ───────────────────────────────────────────────────────────


def read_skill_doc(skill: str) -> str:
    path = REPO_ROOT / "skills" / skill / "SKILL.md"
    if not path.is_file():
        raise BackendUnavailable(f"no SKILL.md for {skill} at {path}")
    parts = path.read_text(encoding="utf-8").split("---", 2)
    return parts[2].strip() if len(parts) >= 3 else path.read_text(encoding="utf-8")


def active_criteria(rubric: dict) -> list[dict]:
    """Criteria that carry weight. Disabled ones are still judged and reported."""
    return [c for c in rubric["criteria"] if c.get("enabled", True) and c["weight"] > 0]


def non_discriminating(results: list[dict]) -> dict[str, set]:
    """Criteria whose scores never varied across every task judged.

    A constant criterion cannot inform a mean -- it subtracts its weight from
    every score and contributes nothing. This exists because ``craft`` returned
    0/10 on all 8 live tasks while the other three spanned 0-10, and 2 of its
    rationales complained about fabrication, which is the truthfulness
    criterion's job. That is criterion bleed, and it was only caught by reading
    the output. The harness now reports it on every run.
    """
    seen: dict[str, set] = {}
    for result in results:
        for task in result["tasks"]:
            for key, crit in task["criteria"].items():
                seen.setdefault(key, set()).update(crit["samples"])
    return {k: v for k, v in seen.items() if len(v) == 1 and len(results) >= 1} if results else {}


def evaluate_skill(skill: str, spec: dict, rubric: dict, backend, split: str, seeds: int) -> dict:
    tasks = [t for t in spec["tasks"] if split == "all" or t["split"] == split]
    skill_doc = read_skill_doc(skill)
    per_task = []

    for task in tasks:
        # 1. GENERATE -- the model follows the actual skill document.
        candidates = {
            s: backend.generate(skill_doc=skill_doc, task_input=task["input"], seed=s)
            for s in range(seeds)
        }

        # 2. EVIDENCE -- computed per candidate, never model-scored.
        evidences = {
            s: mechanical_evidence(text, task.get("mechanical_expectations", {}))
            for s, text in candidates.items()
        }
        # Worst-case fabrication across seeds: if any generation invented a
        # figure, the task is vetoed.
        fabrication = any(e["fabrication_risk"] for e in evidences.values())
        # The per-seed flags are kept. Only the boolean above survives into the
        # task record, and from it a per-generation rate cannot be recovered --
        # inferring one from a truthfulness score of 0 conflates "invented a
        # number" with "wrote untruthfully", which is a different defect.
        fabrication_by_seed = {
            str(s): bool(e["fabrication_risk"]) for s, e in evidences.items()
        }

        # 3. JUDGE -- per criterion, per seed.
        criteria_scores: dict[str, dict] = {}
        for criterion in rubric["criteria"]:
            samples = []
            for s in range(seeds):
                prompt = build_prompt(task, criterion, evidences[s], candidates[s])
                samples.append(
                    backend.judge(task_id=task["id"], criterion=criterion["key"],
                                  prompt=prompt, seed=s)
                )
            values = [s["score"] for s in samples]
            spread = max(values) - min(values)
            sd = st.pstdev(values) if len(values) > 1 else 0.0
            criteria_scores[criterion["key"]] = {
                "weight": criterion["weight"],
                "samples": values,
                "mean": round(st.mean(values), 2),
                "stdev": round(sd, 2),
                "spread": spread,
                # A criterion the seeds cannot agree on is not measured. Reporting
                # its mean anyway would manufacture false precision.
                "unstable": spread > 4,
                "rationale": samples[0].get("rationale", ""),
            }

        total = round(
            sum(
                c["mean"] * c["weight"]
                for c in criteria_scores.values()
                if c["weight"] > 0
            ),
            2,
        )
        if fabrication:
            # A fabrication veto cannot be outvoted by a confident judge.
            total = 0.0

        per_task.append({
            "id": task["id"],
            "split": task["split"],
            "candidates": candidates,
            "evidence": evidences[0],
            "fabrication_by_seed": fabrication_by_seed,
            "criteria": criteria_scores,
            "score": total,
            "fabrication_vetoed": fabrication,
            "unstable_criteria": [k for k, v in criteria_scores.items() if v["unstable"]],
        })

    scores = [t["score"] for t in per_task]
    unvetoed = [t for t in per_task if not t["fabrication_vetoed"]]

    return {
        "skill": skill,
        "backend": backend.name,
        "synthetic": backend.synthetic,
        "split": split,
        "seeds": seeds,
        "tasks": per_task,
        "mean_score": round(st.mean(scores), 2) if scores else 0.0,
        "min_score": min(scores) if scores else 0.0,
        "max_score": max(scores) if scores else 0.0,
        "stdev": round(st.pstdev(scores), 2) if len(scores) > 1 else 0.0,
        "any_fabrication": any(t["fabrication_vetoed"] for t in per_task),
        "unstable": any(t["unstable_criteria"] for t in per_task),
        # Vetoed tasks are counted as zeros above. That conflates "writes badly"
        # with "invents figures", so the mean over unvetoed work is reported
        # alongside. On the live run these were 5.44/7.26 and 3.68/7.36 -- the
        # overall numbers were measuring fabrication, not prose.
        "unvetoed_mean_score": round(st.mean([t["score"] for t in unvetoed]), 2)
        if unvetoed
        else None,
        "unvetoed_tasks": len(unvetoed),
    }


def rubric_fingerprint(rubric: dict) -> str:
    """Identify the exact rubric a report was scored against.

    A report that does not record its rubric cannot be compared against one
    produced under a different rubric. That failure is silent: the inter-judge
    tool re-judges with the current anchors and reads the primary scores out of
    a report generated under older ones, then reports the difference between
    fresh numbers and stale ones as a disagreement between judges.
    """
    payload = json.dumps(
        {c["key"]: c["anchors"] for c in rubric["criteria"]
         if c.get("enabled", True) and c["weight"] > 0},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backend", default="stub",
                    help="'stub' (offline, synthetic) or 'openai_compatible' (live)")
    ap.add_argument("--split", default="held_out", choices=["held_out", "train", "all"])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--judge-temperature", type=float, default=0.0,
                    help="Sampling temperature for the judge. 0.0 (default) makes "
                         "--seeds a reproducibility check -- same input, same score, "
                         "which is what a regression gate needs. Raise it above 0 to "
                         "make --seeds a sampling-variance measurement instead.")
    ap.add_argument("--min-score", type=float, default=None,
                    help="fail if any skill scores below this (live backends only)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    if args.seeds < 1:
        print("--seeds must be at least 1", file=sys.stderr)
        return 2

    spec = json.loads(TASKS_PATH.read_text(encoding="utf-8"))

    if args.list:
        for skill, data in spec["skills"].items():
            counts: dict[str, int] = {}
            for t in data["tasks"]:
                counts[t["split"]] = counts.get(t["split"], 0) + 1
            print(f"{skill:<28}{counts}")
        return 0

    try:
        backend = build_backend(args.backend, args.judge_temperature)
    except BackendUnavailable as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1

    results = [
        evaluate_skill(skill, data, spec["rubric"], backend, args.split, args.seeds)
        for skill, data in spec["skills"].items()
    ]

    print("=" * 76)
    print("   VAELOOM SKILL JUDGING  (Layer 3: rubric-anchored)")
    print("=" * 76)
    print(f"backend   : {backend.name}")
    print(f"split     : {args.split}")
    print(f"seeds     : {args.seeds}")
    if args.judge_temperature == 0.0 and args.seeds > 1:
        print("            -> reproducibility mode (temperature 0.0): these seeds")
        print("               confirm the same input yields the same score. This is")
        print("               NOT sampling variance -- use --judge-temperature > 0")
        print("               for that.")
    if backend.synthetic:
        print("SYNTHETIC : TRUE -- deterministic stand-in, NOT a model. No quality")
        print("            verdict is available from this run. See below.")
    print("=" * 76)

    for r in results:
        print(f"\n{r['skill']}  mean={r['mean_score']}/10  "
              f"(min {r['min_score']}, max {r['max_score']}, sd {r['stdev']})")
        for t in r["tasks"]:
            flag = " FABRICATION-VETOED" if t["fabrication_vetoed"] else ""
            unstable = f"  unstable={t['unstable_criteria']}" if t["unstable_criteria"] else ""
            print(f"  {t['id']:<20} score={t['score']:<6}{flag}{unstable}")
            for key, c in t["criteria"].items():
                mark = "!" if c["unstable"] else " "
                weight = f"w={c['weight']:<6}" if c["weight"] > 0 else "DISABLED "
                print(f"    {mark}{key:<14}{c['mean']:>5}/10  {weight}samples={c['samples']} sd={c['stdev']}")

    # Surfaced automatically so a criterion that has stopped measuring anything
    # is reported rather than quietly subtracted from every score.
    flat = non_discriminating(results)
    if flat:
        print("\nNON-DISCRIMINATING CRITERIA (constant across every task judged):")
        for key, values in sorted(flat.items()):
            weighted = any(
                c["key"] == key and c["weight"] > 0 for c in spec["rubric"]["criteria"]
            )
            state = "STILL WEIGHTED - its score is meaningless" if weighted else "already disabled (excluded from the mean)"
            print(f"  {key:<14} returned only {sorted(values)} across "
                  f"{sum(len(r['tasks']) for r in results)} task(s) -- {state}")

    print("\n" + "-" * 76)
    if backend.synthetic:
        print("PLUMBING REPORT (synthetic backend -- NOT a quality measurement)")
        print("  The harness executed, splits were disjoint, scoring aggregated and")
        print("  variance was computed. None of that says anything about the skills.")
        print("  For a real number, select a live backend and provide credentials.")
        print("-" * 76)
        if args.json:
            args.json.write_text(
                json.dumps({
                    "synthetic": True,
                    "rubric_fingerprint": rubric_fingerprint(spec["rubric"]),
                    "results": results,
                }, indent=2),
                encoding="utf-8",
            )
            print(f"report written to {args.json}")
        return 0

    print("QUALITY REPORT (live backend)")

    # The fabrication rate is reported ahead of the rubric means because when it
    # is high it dominates them: a vetoed task is pinned to 0 regardless of how
    # well it scored on the rubric. Quoting the mean alone would hide that.
    total_tasks = sum(len(r["tasks"]) for r in results)
    vetoed = sum(1 for r in results for t in r["tasks"] if t["fabrication_vetoed"])
    rate = (100.0 * vetoed / total_tasks) if total_tasks else 0.0
    print(f"\n  FABRICATION RATE : {vetoed}/{total_tasks} tasks ({rate:.0f}%)")
    print("    This is the load-bearing result. Any task that invents a figure not")
    print("    present in its source is pinned to 0 by the mechanical veto, so a")
    print("    high rate compresses the rubric means downward and makes them")
    print("    uninformative on their own. Fix fabrication first, then read means.")
    print()

    # Vetoed work is excluded from this mean rather than counted as a zero, so
    # that "writes well" and "invents numbers" stay separable. On the live run
    # the two skills scored 5.34 and 3.48 overall but 7.13 and 6.96 on unvetoed
    # work -- the headline was measuring fabrication, not writing.
    print(f"  {'skill':<26}{'overall':>9}{'unvetoed':>10}{'n':>4}   reading")
    print("  " + "-" * 70)
    for r in results:
        if r["unvetoed_tasks"]:
            unvetoed_mean = r["unvetoed_mean_score"]
            gap = round(r["mean_score"] - unvetoed_mean, 2)
            reading = (
                f"writing is fine; the loss is fabrication ({gap:+.2f})"
                if abs(gap) >= 1.0
                else "consistent across both views"
            )
            print(f"  {r['skill']:<26}{r['mean_score']:>9}{unvetoed_mean:>10}"
                  f"{r['unvetoed_tasks']:>4}   {reading}")
        else:
            print(f"  {r['skill']:<26}{r['mean_score']:>9}{'n/a':>10}{0:>4}   every task vetoed")
    print()
    print("    overall includes vetoed tasks as zeros; unvetoed excludes them.")
    print("    A large gap means the skill is not bad at the writing, it is bad at")
    print("    not inventing numbers -- a different and more fixable defect.")
    print()
    for r in results:
        if r["any_fabrication"]:
            print(f"  {r['skill']}: FABRICATION observed -- mechanical veto applied")
        if r["unstable"]:
            print(f"  {r['skill']}: criterion seeds disagreed; treat the mean as unreliable")
    if vetoed == total_tasks and total_tasks:
        print("  NOTE: every task was vetoed, so the rubric contributed nothing to")
        print("        this run's scores. This measures fabrication, not writing skill.")
    print("-" * 76)

    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "synthetic": False,
                    "backend": backend.name,
                    "rubric_fingerprint": rubric_fingerprint(spec["rubric"]),
                    "judge_temperature": args.judge_temperature,
                    "fabrication": {
                        "vetoed_tasks": vetoed,
                        "total_tasks": total_tasks,
                        "rate_pct": round(rate, 1),
                        "primary_metric": True,
                    },
                    "results": results,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"report written to {args.json}")

    if args.min_score is not None:
        below = [r for r in results if r["mean_score"] < args.min_score]
        if below:
            print(f"\nFAIL: below the {args.min_score}/10 floor:")
            for r in below:
                print(f"  {r['skill']:<28}{r['mean_score']}")
            return 1
        print(f"\nPASS: every judged skill is at or above {args.min_score}/10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())