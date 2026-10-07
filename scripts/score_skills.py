#!/usr/bin/env python3
"""Layer 1 of the Vaeloom skill scorecard: a deterministic 100-point rubric.

Scores every skill in ``skills/`` out of 100 across ten dimensions, ten points
each, using only mechanical checks. No model is called, so the score is
reproducible, free, and identical on every machine -- which is the point: a
quality gate that needs an LLM to reproduce is not a gate.

Why mechanical only. The obvious alternative is an LLM judge, and the honest
answer is that a judge score is not reproducible enough to gate a build on. It
also cannot be negative-tested: you cannot prove a judge is measuring anything.
So this layer scores what can be *proved* from the file, and the semantic
dimensions are written to score the presence of a property that a human or a
judge can then verify by reading the cited evidence. Each sub-score carries a
one-line reason naming the file and the evidence, so no point is awarded or
withheld invisibly.

  D1  Frontmatter specification compliance            10
  D2  Description quality and triggering             10
  D3  Conciseness / token efficiency                 10
  D4  Progressive disclosure and structure           10
  D5  Operating rule quality                         10
  D6  Scope discipline                               10
  D7  Output contract specificity                    10
  D8  Failure and edge-case handling                 10
  D9  Verifiability (helpers or explicit determinism) 10
  D10 Completeness against the stated description    10

Usage:
    python scripts/score_skills.py
    python scripts/score_skills.py --json scorecard.json
    python scripts/score_skills.py --min-score 95     # exit 1 if the floor is missed
    python scripts/score_skills.py --skill ats-audit  # one skill, with reasons
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# The tool-scope vocabulary the app accepts. The app derives this from the live
# tool registry (api.services.skill_catalog_service.tool_scope_vocabulary);
# it is mirrored here so the scorer runs without the app's dependencies. The
# skills-side test asserts this list is not empty and is a subset of the
# canonical set the schema test already enforces.
VALID_SCOPES = frozenset({
    "memory.read",
    "memory.write",
    "system.document.compile",
    "system.browser.read",
    "agent.spawn",
    "workspace.write",
    "connector.read",
})

CANONICAL_SECTIONS = ("Mission", "Operating Rules", "Triggers", "Output Contract")

# Words that signal the document explains rather than instructs.
FILLER_MARKERS = (
    "in this section",
    "let's explore",
    "as an ai",
    "it is important to note",
    "it's worth noting",
    "in today's world",
    "at the end of the day",
)

# First/second person, which a skill description should not use.
NON_IMPERATIVE = re.compile(r"\b(i can|i will|i help|you can|you should|let me|we will|our )\b", re.I)

# Imperative / deontic markers a real operating rule tends to contain.
RULE_VERB = re.compile(
    r"\b(never|always|must|require[sd]?|enforce[sd]?|ban(?:ned)?|prohibit(?:ed)?|"
    r"reject(?:ed)?|validat(?:e|ed)|verif(?:y|ied)|report(?:ed)?|never emit|"
    r"do not|don't|format|quantif(?:y|ied)|extract(?:ed)?|cite[ds]?|"
    r"ground(?:ed)?|flag(?:ged)?|block(?:ed)?|escalate[ds]?)\b",
    re.I,
)

# Words a good error/edge-case section reaches for.
FAILURE_MARKERS = (
    "error", "fail", "exception", "missing", "invalid", "unavailable", "timeout",
    "retry", "fallback", "abort", "refuse", "abstain", "edge case", "when in doubt",
    "do not fabricate", "never invent", "unknown",
)

# Words a good output contract reaches for.
EVIDENCE_MARKERS = (
    "evidence", "cite", "citation", "source", "provenance", "verify", "confidence",
    "quote", "reference",
)


@dataclass
class Criterion:
    """One scored sub-criterion: a point value and the evidence for it."""
    points: float
    max_points: float
    reason: str


@dataclass
class Dimension:
    key: str
    label: str
    criteria: list[Criterion] = field(default_factory=list)

    @property
    def score(self) -> float:
        return round(sum(c.points for c in self.criteria), 2)

    @property
    def max_score(self) -> float:
        return round(sum(c.max_points for c in self.criteria), 2)


def estimate_tokens(text: str) -> int:
    """~4 chars/token including whitespace, the ratio used across this repo."""
    return int(len(text) / 4.0)


def split_doc(markdown: str) -> tuple[dict, str]:
    parts = markdown.split("---", 2)
    if len(parts) < 3:
        return {}, markdown
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except Exception:
        meta = {}
    return (meta if isinstance(meta, dict) else {}), parts[2]


def section_body(body: str, heading: str) -> str:
    """Text under '## <heading>' up to the next '## '."""
    pattern = re.compile(
        r"^##\s+" + re.escape(heading) + r"\s*$(.*?)(?=^##\s+|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def numbered_rules(body: str) -> list[str]:
    rules_body = section_body(body, "Operating Rules")
    return [
        line.strip()
        for line in rules_body.splitlines()
        if re.match(r"^\s*\d+[\.\)]\s+\S", line)
    ]


def words(text: str) -> set[str]:
    return {w for w in re.split(r"[^\w]+", text.lower()) if len(w) > 3}


# ── dimensions ───────────────────────────────────────────────────────────


def d1_frontmatter(meta: dict, slug: str, description: str) -> Dimension:
    d = Dimension("D1", "Frontmatter specification compliance")
    name = str(meta.get("name") or "")
    d.criteria.append(Criterion(
        2.0 if name == slug else 0.0, 2.0,
        f"name={name!r} vs directory {slug!r}",
    ))
    ok_desc = 10 < len(description.strip()) <= 1024
    d.criteria.append(Criterion(
        2.0 if ok_desc else 0.0, 2.0,
        f"description is {len(description.strip())} chars (want 11-1024)",
    ))
    has_version = bool(meta.get("version"))
    has_tags = bool(meta.get("tags"))
    d.criteria.append(Criterion(
        1.0 if has_version else 0.0, 1.0,
        f"version={'set' if has_version else 'absent'}",
    ))
    d.criteria.append(Criterion(
        1.0 if has_tags else 0.0, 1.0,
        f"tags={'set' if has_tags else 'absent'} ({len(meta.get('tags') or [])} entries)",
    ))
    banned = bool(re.search(r"<(/?[a-zA-Z][^>]*)>", name + description))
    d.criteria.append(Criterion(
        0.0 if banned else 1.0, 1.0,
        "no XML tags in name/description" if not banned else "XML tag present",
    ))
    reserved = bool(re.search(r"anthropic|claude", name, re.I))
    d.criteria.append(Criterion(
        0.0 if reserved else 1.0, 1.0,
        "name carries no vendor keyword" if not reserved else "name names a vendor",
    ))
    d.criteria.append(Criterion(
        0.0 if NON_IMPERATIVE.search(description) else 2.0, 2.0,
        "description is third-person" if not NON_IMPERATIVE.search(description)
        else f"first/second person in description: {NON_IMPERATIVE.search(description).group(0)!r}",
    ))
    return d


def d2_triggering(meta: dict, body: str, description: str) -> Dimension:
    d = Dimension("D2", "Description quality and triggering")
    triggers = [str(t).strip() for t in (meta.get("triggers") or []) if str(t).strip()]
    d.criteria.append(Criterion(
        3.0 if len(triggers) >= 3 else (1.5 if len(triggers) == 2 else 0.0), 3.0,
        f"{len(triggers)} declared triggers (want >=3)",
    ))
    multiword = sum(1 for t in triggers if len(t.split()) >= 2)
    ratio = multiword / len(triggers) if triggers else 0.0
    d.criteria.append(Criterion(
        round(2.0 * ratio, 2), 2.0,
        f"{multiword}/{len(triggers)} triggers are multi-word phrases",
    ))
    echoed = sum(1 for t in triggers if t.lower() in body.lower())
    echo_ratio = echoed / len(triggers) if triggers else 0.0
    d.criteria.append(Criterion(
        round(3.0 * echo_ratio, 2), 3.0,
        f"{echoed}/{len(triggers)} triggers echoed verbatim in the body",
    ))
    n = len(description.strip())
    sweet = 80 <= n <= 400
    d.criteria.append(Criterion(
        2.0 if sweet else 1.0, 2.0,
        f"description {n} chars ({'in the 80-400 sweet spot' if sweet else 'outside 80-400'})",
    ))
    return d


def d3_conciseness(body: str, lines: int) -> Dimension:
    d = Dimension("D3", "Conciseness and token efficiency")
    tokens = estimate_tokens(body)
    d.criteria.append(Criterion(
        3.0 if lines <= 500 else (1.5 if lines <= 800 else 0.0), 3.0,
        f"SKILL.md is {lines} lines (want <=500)",
    ))
    d.criteria.append(Criterion(
        3.0 if tokens <= 5000 else (1.5 if tokens <= 8000 else 0.0), 3.0,
        f"~{tokens} tokens (want <=5000)",
    ))
    found = [m for m in FILLER_MARKERS if m in body.lower()]
    d.criteria.append(Criterion(
        0.0 if found else 2.0, 2.0,
        "no filler preamble" if not found else f"filler markers: {found}",
    ))
    paras = [p.strip() for p in body.split("\n\n") if len(p.strip()) > 80]
    dupes = len(paras) - len(set(paras))
    d.criteria.append(Criterion(
        0.0 if dupes else 2.0, 2.0,
        "no duplicated paragraphs" if not dupes else f"{dupes} duplicated paragraphs",
    ))
    return d


def d4_structure(body: str, skill_dir: Path) -> Dimension:
    d = Dimension("D4", "Progressive disclosure and structure")
    present = [s for s in CANONICAL_SECTIONS if section_body(body, s)]
    d.criteria.append(Criterion(
        4.0 * len(present) / len(CANONICAL_SECTIONS), 4.0,
        f"canonical sections present: {present or 'none'}",
    ))
    refs = skill_dir / "references"
    deep = []
    if refs.is_dir():
        deep = [p for p in refs.rglob("*") if p.is_file() and len(p.relative_to(refs).parts) > 1]
    d.criteria.append(Criterion(
        0.0 if deep else 2.0, 2.0,
        "references are one level deep" if not deep else f"nested references: {len(deep)}",
    ))
    long_refs = [
        p for p in (refs.rglob("*") if refs.is_dir() else [])
        if p.is_file() and p.suffix == ".md" and len(p.read_text(encoding="utf-8").splitlines()) > 100
    ]
    no_toc = [p.name for p in long_refs if "## Contents" not in p.read_text(encoding="utf-8")]
    d.criteria.append(Criterion(
        0.0 if not long_refs else (2.0 if not no_toc else 1.0), 2.0,
        "no long references" if not long_refs
        else f"{len(long_refs)} references >100 lines, {len(no_toc)} without a contents list",
    ))
    vague = []
    for sub in ("scripts", "references", "templates"):
        p = skill_dir / sub
        if p.is_dir():
            vague += [f.name for f in p.iterdir() if f.is_file() and re.fullmatch(r"(doc|file|temp|new|untitled)?\d*\.?\w*", f.stem)]
    d.criteria.append(Criterion(
        0.0 if vague else 2.0, 2.0,
        "filenames are descriptive" if not vague else f"vague filenames: {vague}",
    ))
    return d


def d5_rules(body: str) -> Dimension:
    d = Dimension("D5", "Operating rule quality")
    rules = numbered_rules(body)
    count = len(rules)
    d.criteria.append(Criterion(
        3.0 if count >= 5 else (2.0 if count >= 3 else 0.0), 3.0,
        f"{count} numbered operating rules (want >=5)",
    ))
    long_rules = [r for r in rules if len(r.split()) > 60]
    d.criteria.append(Criterion(
        0.0 if not long_rules else (3.0 if len(long_rules) <= 1 else 1.5), 3.0,
        f"{len(rules) - len(long_rules)}/{count} rules are a single readable sentence",
    ))
    verifiable = [r for r in rules if RULE_VERB.search(r)]
    vratio = len(verifiable) / count if count else 0.0
    d.criteria.append(Criterion(
        round(2.0 * vratio, 2), 2.0,
        f"{len(verifiable)}/{count} rules carry a checkable imperative verb",
    ))
    texts = [re.sub(r"^\s*\d+[\.\)]\s+", "", r).lower() for r in rules]
    dupes = len(texts) - len(set(texts))
    d.criteria.append(Criterion(
        0.0 if dupes else 2.0, 2.0,
        "no duplicate rules" if not dupes else f"{dupes} duplicate rules",
    ))
    return d


def d6_scope(meta: dict, body: str) -> Dimension:
    d = Dimension("D6", "Scope discipline")
    scope = str(meta.get("required_scope") or "").strip()
    d.criteria.append(Criterion(
        3.0 if scope else 0.0, 3.0,
        f"required_scope={scope!r}" if scope else "required_scope not declared",
    ))
    in_vocab = scope in VALID_SCOPES if scope else False
    d.criteria.append(Criterion(
        3.0 if in_vocab else 0.0, 3.0,
        f"scope is in the authorized vocabulary" if in_vocab
        else f"scope {scope!r} is not in {sorted(VALID_SCOPES)}",
    ))
    d.criteria.append(Criterion(
        2.0 if scope and scope in body else 0.0, 2.0,
        "body cites its own scope" if scope and scope in body else "body does not cite its scope",
    ))
    multi = bool(scope and "," in scope)
    d.criteria.append(Criterion(
        0.0 if multi else 2.0, 2.0,
        "exactly one scope declared" if not multi else f"comma-joined scopes: {scope!r}",
    ))
    return d


def d7_output_contract(body: str) -> Dimension:
    d = Dimension("D7", "Output contract specificity")
    contract = section_body(body, "Output Contract")
    d.criteria.append(Criterion(
        3.0 if contract else 0.0, 3.0,
        f"## Output Contract is {len(contract)} chars",
    ))
    ordered = bool(re.search(r"(1\.|first|then|in this order|order:|following)", contract, re.I))
    d.criteria.append(Criterion(
        3.0 if ordered else 0.0, 3.0,
        "contract specifies an ordering" if ordered else "contract does not specify an ordering",
    ))
    evidential = any(m in contract.lower() for m in EVIDENCE_MARKERS)
    d.criteria.append(Criterion(
        2.0 if evidential else 0.0, 2.0,
        "contract requires evidence/provenance" if evidential
        else "contract requires no evidence or provenance",
    ))
    honest = bool(re.search(r"(never invent|never fabricate|do not fabricate|say so|state that|"
                            r"report .*unknown|mark .*unavailable|do not guess)", contract, re.I))
    d.criteria.append(Criterion(
        2.0 if honest else 0.0, 2.0,
        "contract forbids fabrication / demands honest gaps" if honest
        else "contract does not say what to do when data is missing",
    ))
    return d


def d8_failures(body: str) -> Dimension:
    """Failure and edge-case handling.

    Scored on two independent signals, because either alone misleads:

    * **Structural** -- a heading that names situations, edge cases or pitfalls.
      A skill can handle "manager left the company" in prose without ever using
      the word "error", and a keyword-only scorer scores that as zero. That was a
      real false negative here: ``reference-list-builder`` carries a whole
      "Handling Special Situations" section and scored 0/10 on keywords alone.
    * **Semantic** -- failure vocabulary in the rules and output contract, which
      is where an agent actually learns what to do when something is missing.

    Structural weight is deliberately higher. A named section is a deliberate
    authoring act; a stray "error" in a sentence is not.
    """
    d = Dimension("D8", "Failure and edge-case handling")

    headings = re.findall(r"^#{2,4}\s+(.+)$", body, re.MULTILINE)
    structural = [
        h for h in headings
        if re.search(
            r"(special situation|edge case|pitfall|gotcha|common mistake|troubleshoot|"
            r"when .*(unavailable|refuse|missing|fail|decline|not available)|"
            r"what to do|if .*(refus|unavailable|missing|fail)|avoid|degrad|"
            r"anti-?pattern|do not confuse|limitations|caveat)",
            h, re.I)
    ]
    d.criteria.append(Criterion(
        min(4.0, 2.0 * len(structural)), 4.0,
        f"{len(structural)} dedicated edge-case heading(s): "
        f"{structural[:3] if structural else 'none'}",
    ))

    rules_body = section_body(body, "Operating Rules")
    contract = section_body(body, "Output Contract")
    haystack = (rules_body + "\n" + contract).lower()
    hits = [m for m in FAILURE_MARKERS if m in haystack]
    d.criteria.append(Criterion(
        min(3.0, 1.0 * len(hits)), 3.0,
        f"{len(hits)} failure signals in rules/contract "
        f"({', '.join(hits[:6]) or 'none'})",
    ))

    missing = bool(re.search(
        r"missing input|no input|empty|absent|not supplied|when .*(is|are) unavailable|"
        r"if .*(is|are) unavailable|unavailable", haystack + "\n" + body.lower(), re.I))
    d.criteria.append(Criterion(
        1.5 if missing else 0.0, 1.5,
        "addresses missing or unavailable input" if missing else "silent on missing input",
    ))

    refuses = bool(re.search(
        r"(refuse|abstain|escalat|ask the user|when in doubt|do not guess|do not invent|"
        r"never invent|never fabricate|rather than|escalate to a human)", haystack, re.I))
    d.criteria.append(Criterion(
        1.5 if refuses else 0.0, 1.5,
        "defines a refusal / abstention / escalation path" if refuses
        else "no refusal, abstention or escalation path in the rules",
    ))
    return d


def d9_verifiability(skill_dir: Path, body: str) -> Dimension:
    d = Dimension("D9", "Verifiability")
    scripts = list((skill_dir / "scripts").glob("*.py")) if (skill_dir / "scripts").is_dir() else []
    if scripts:
        helped = [s for s in scripts if "--help" in s.read_text(encoding="utf-8", errors="ignore")]
        d.criteria.append(Criterion(
            2.0 * len(helped) / len(scripts), 2.0,
            f"{len(helped)}/{len(scripts)} helper scripts document --help",
        ))
        structured = [
            s for s in scripts
            if re.search(r"json\.dump|print\(\s*json\.dumps|--json", s.read_text(encoding="utf-8", errors="ignore"))
        ]
        d.criteria.append(Criterion(
            2.0 * len(structured) / len(scripts), 2.0,
            f"{len(structured)}/{len(scripts)} emit structured output",
        ))
        exits = [
            s for s in scripts
            if re.search(r"sys\.exit|raise SystemExit|return \d", s.read_text(encoding="utf-8", errors="ignore"))
        ]
        d.criteria.append(Criterion(
            2.0 * len(exits) / len(scripts), 2.0,
            f"{len(exits)}/{len(scripts)} set a meaningful exit code",
        ))
        errors = [
            s for s in scripts
            if re.search(r"raise (ValueError|RuntimeError|KeyError)|sys\.stderr", s.read_text(encoding="utf-8", errors="ignore"))
        ]
        d.criteria.append(Criterion(
            2.0 * len(errors) / len(scripts), 2.0,
            f"{len(errors)}/{len(scripts)} handle errors explicitly",
        ))
        interactive = [
            s for s in scripts if re.search(r"\binput\(", s.read_text(encoding="utf-8", errors="ignore"))
        ]
        d.criteria.append(Criterion(
            0.0 if interactive else 2.0, 2.0,
            "no interactive prompts" if not interactive else f"{len(interactive)} scripts call input()",
        ))
        return d

    # No helpers: score the determinism the document itself promises.
    contract = section_body(body, "Output Contract")
    scored = any(m in contract.lower() for m in ("markdown", "json", "table", "schema", "field"))
    d.criteria.append(Criterion(
        2.0 if scored else 0.0, 2.0,
        "prose skill: contract names an output format" if scored
        else "prose skill: contract names no output format",
    ))
    numeric = bool(re.search(r"(character|word|line|token|\d+\s*(chars|words|lines)|score)", contract, re.I))
    d.criteria.append(Criterion(
        2.0 if numeric else 0.0, 2.0,
        "prose skill: contract states a measurable limit" if numeric
        else "prose skill: no measurable limit in the contract",
    ))
    rules = numbered_rules(body)
    testable = [r for r in rules if RULE_VERB.search(r)]
    ratio = len(testable) / len(rules) if rules else 0.0
    d.criteria.append(Criterion(
        round(4.0 * ratio, 2), 4.0,
        f"prose skill: {len(testable)}/{len(rules)} rules are independently checkable",
    ))
    d.criteria.append(Criterion(
        2.0 if section_body(body, "Triggers") else 0.0, 2.0,
        "prose skill: activation condition is stated in the body",
    ))
    return d


def d10_completeness(meta: dict, body: str, description: str) -> Dimension:
    d = Dimension("D10", "Completeness against the stated description")
    desc_words = {w for w in words(description) if w not in {"skill", "playbook", "tool", "agent"}}
    body_words = words(body)
    covered = desc_words & body_words
    ratio = len(covered) / len(desc_words) if desc_words else 0.0
    d.criteria.append(Criterion(
        round(4.0 * ratio, 2), 4.0,
        f"{len(covered)}/{len(desc_words)} distinctive description terms appear in the body",
    ))
    gotcha = bool(re.search(
        r"(gotcha|pitfall|watch out|non-obvious|counter-intuitive|caveat|edge case|"
        r"common mistake|do not confuse)", body, re.I))
    d.criteria.append(Criterion(
        3.0 if gotcha else 0.0, 3.0,
        "documents non-obvious pitfalls" if gotcha else "no gotchas or pitfalls section",
    ))
    rules = numbered_rules(body)
    d.criteria.append(Criterion(
        3.0 if len(rules) >= 5 else (2.0 if rules else 0.0), 3.0,
        f"scope is served by {len(rules)} concrete rules",
    ))
    return d


DIMENSIONS = (d1_frontmatter, d2_triggering, d3_conciseness, d4_structure, d5_rules,
              d6_scope, d7_output_contract, d8_failures, d9_verifiability, d10_completeness)


def score_skill(skill_dir: Path, entry=None) -> dict:
    """Score one skill.

    ``entry`` is the app catalog's ``SkillCatalogEntry`` when available. It
    matters: 25 of 33 skills ship a bare two-line frontmatter in this repo, and
    the catalog supplies their ``required_scope``, ``triggers`` and ``tags``.
    Scoring the repo file alone would report those 25 as missing activation
    metadata when the deployed skill is in fact complete -- a score that
    measures the wrong artifact. With an entry, metadata dimensions score what
    actually ships and only the body is read from the repo.
    """
    markdown = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    meta, body = split_doc(markdown)

    if entry is not None:
        meta = dict(meta)
        meta["description"] = getattr(entry, "description", meta.get("description"))
        meta["required_scope"] = getattr(entry, "required_scope", meta.get("required_scope"))
        meta["triggers"] = list(getattr(entry, "triggers", None) or meta.get("triggers") or [])
        meta["tags"] = list(getattr(entry, "tags", None) or meta.get("tags") or [])

    description = str(meta.get("description") or "")
    lines = len(markdown.splitlines())

    dims = [
        d1_frontmatter(meta, skill_dir.name, description),
        d2_triggering(meta, body, description),
        d3_conciseness(body, lines),
        d4_structure(body, skill_dir),
        d5_rules(body),
        d6_scope(meta, body),
        d7_output_contract(body),
        d8_failures(body),
        d9_verifiability(skill_dir, body),
        d10_completeness(meta, body, description),
    ]
    total = round(sum(d.score for d in dims), 2)
    return {
        "slug": skill_dir.name,
        "score": total,
        "scored": "effective (repo body + catalog metadata)" if entry is not None
                  else "repo source only (no catalog supplied)",
        "dimensions": [
            {
                "key": d.key,
                "label": d.label,
                "score": d.score,
                "max": d.max_score,
                "criteria": [
                    {"points": c.points, "max": c.max_points, "reason": c.reason}
                    for c in d.criteria
                ],
            }
            for d in dims
        ],
    }


def load_catalog(catalog_path: Path | None):
    """Import the app's SKILL_CATALOG, or return None when unavailable."""
    if catalog_path is None or not catalog_path.is_file():
        return None
    sys.path.insert(0, str(catalog_path.parents[2]))
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("_skill_catalog_scored", catalog_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return {e.slug: e for e in module.SKILL_CATALOG}
    except Exception as exc:  # pragma: no cover - depends on app environment
        print(f"note: could not import the catalog ({exc})", file=sys.stderr)
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, default=None, help="write the full scorecard")
    ap.add_argument("--min-score", type=float, default=None, help="fail if any skill scores below this")
    ap.add_argument("--skill", default=None, help="score one skill and print every reason")
    ap.add_argument(
        "--catalog",
        type=Path,
        default=None,
        help="path to the app's skill_catalog_service.py; score what actually ships",
    )
    ap.add_argument("--quiet", action="store_true", help="print only the summary line")
    args = ap.parse_args()

    catalog = load_catalog(args.catalog)
    if catalog is None and args.catalog is not None:
        print("note: catalog unavailable; scoring repo source only", file=sys.stderr)

    if args.skill:
        target = SKILLS_DIR / args.skill
        if not (target / "SKILL.md").is_file():
            print(f"no such skill: {args.skill}", file=sys.stderr)
            return 2
        result = score_skill(target, (catalog or {}).get(args.skill))
        print(f"{result['slug']}  {result['score']}/100")
        print(f"scored: {result['scored']}\n")
        for d in result["dimensions"]:
            print(f"  {d['key']:<4}{d['score']:>5}/{d['max']:<5}{d['label']}")
            for c in d["criteria"]:
                mark = "+" if c["points"] >= c["max"] else ("~" if c["points"] > 0 else "-")
                print(f"        {mark} {c['points']:>4}/{c['max']:<4}{c['reason']}")
        return 0

    results = [
        score_skill(p, (catalog or {}).get(p.name))
        for p in sorted(SKILLS_DIR.iterdir())
        if (p / "SKILL.md").is_file()
    ]
    results.sort(key=lambda r: r["score"])

    print("=" * 78)
    print("   VAELOOM SKILL SCORECARD  (Layer 1: deterministic 100-point rubric)")
    print("=" * 78)
    if catalog:
        n_with = sum(1 for r in results if "catalog metadata" in r["scored"])
        print(f"scored as: effective -- repo body + catalog metadata ({n_with} skills)")
        print(f"           {len(results) - n_with} skill(s) are repo-only and scored from source alone")
    else:
        print("scored as: repo source only (no --catalog supplied)")
        print("           metadata dimensions under-report: the catalog supplies")
        print("           required_scope/triggers for 25 of 33 skills")
    if not args.quiet:
        print(f"{'skill':<32}{'score':>7}   weakest dimension")
        print("-" * 78)
    for r in results:
        weakest = min(r["dimensions"], key=lambda d: (d["score"] / d["max"] if d["max"] else 1))
        if not args.quiet:
            print(f"{r['slug']:<32}{r['score']:>7.1f}   {weakest['key']} {weakest['label']} "
                  f"({weakest['score']}/{weakest['max']})")

    scores = [r["score"] for r in results]
    mean = sum(scores) / len(scores) if scores else 0.0
    at_floor = sum(1 for s in scores if s >= 95)
    print("-" * 78)
    print(f"skills scored   : {len(results)}")
    print(f"mean            : {mean:.1f}/100")
    print(f"min / max       : {min(scores):.1f} / {max(scores):.1f}")
    print(f"at or above 95  : {at_floor}/{len(results)}")

    # Per-dimension means, so systemic weaknesses are visible rather than averaged away.
    print("\nper-dimension mean:")
    keys = [d["key"] for d in results[0]["dimensions"]]
    labels = {d["key"]: d["label"] for d in results[0]["dimensions"]}
    for key in keys:
        vals = [next(d["score"] for d in r["dimensions"] if d["key"] == key) for r in results]
        mx = next(d["max"] for d in results[0]["dimensions"] if d["key"] == key)
        print(f"  {key:<5}{sum(vals)/len(vals):>6.1f}/{mx:<4}{labels[key]}")

    print("=" * 78)

    if args.json:
        args.json.write_text(
            json.dumps({"skills": results, "mean": mean, "min_score_floor": args.min_score}, indent=2),
            encoding="utf-8",
        )
        print(f"scorecard written to {args.json}")

    if args.min_score is not None:
        below = [r for r in results if r["score"] < args.min_score]
        if below:
            print(f"\nFAIL: {len(below)} skill(s) below the {args.min_score}/100 floor:")
            for r in below:
                print(f"  {r['slug']:<32}{r['score']:>6.1f}")
            return 1
        print(f"\nPASS: every skill is at or above {args.min_score}/100")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())