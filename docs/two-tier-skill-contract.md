# The Two-Tier Skill Contract

Vaeloom ships each career skill at **two different sizes**, for **two different
consumers**. Neither this repository nor the application said so, which is why
the relationship between them drifted unnoticed.

## The tiers

| Tier | Lives in | Size | Consumer |
|------|----------|------|----------|
| **Full reference** | `skills/<slug>/SKILL.md` (this repo) | 500–3,700 tokens | A human, or an agent that reads the file on demand |
| **Condensed directive** | `markdown_doc` in `apps/api/src/api/services/skill_catalog_service.py` | 400–640 tokens | The agent, injected into the system prompt |

## Why the condensation is forced, not cosmetic

`skill_injection` **drops whole skills rather than truncating them**:

```python
if spent + cost > budget:
    # Whole-skill drop. Truncating here would deliver half an Operating
    # Rules list, which reads as an instruction set with rules missing.
```

A directive that does not fit `SKILL_DIRECTIVE_TOKEN_BUDGET` is therefore
excluded from the run entirely. Measured across the catalog:

- all 33 condensed directives total **~15,960 tokens**
- `SKILL_DIRECTIVE_TOKEN_BUDGET` is **4,000** (raised from 1,500 on 2026-10-07)
- so a run admits roughly **10 of 33** skills

That is the whole reason the app carries a shorter document. The full reference
cannot be injected as-is: **17 of 22** full documents exceed the entire budget on
their own.

## How faithful is the condensation?

Measured vocabulary overlap between each condensed directive and its full
source, across the 22 shared skills. The distribution is **bimodal**:

```
 8 skills   49.6% – 65.4%   condensed by paraphrase (different wording)
14 skills   94.3% – 99.5%   condensed near-verbatim
                                    (gap: 65% → 94%)
```

Both clusters are legitimate. The low-overlap eight were written independently of
the full text; the high-overlap fourteen were derived from it. `check_catalog_fidelity.py`
therefore uses overlap as a **smoke test for unrelated text** (threshold 0.40,
below the observed minimum), not as a paraphrase-quality grade, and prints the
per-skill figure so real divergence stays visible even when it passes.

## What the checker enforces

For every skill present in both places:

1. the condensed document declares the same `required_scope` as the full one
2. the condensed document keeps **every** trigger phrase the full one declares
3. both declare the canonical sections (Mission / Operating Rules / Triggers /
   Output Contract)
4. the condensed document fits the directive budget
5. the condensed document is derived from the full one

Point 2 is one-directional on purpose. The condensed tier **may** declare extra
activation phrases; it **may not** drop any. A dropped trigger means a real
request activates nothing, which is invisible until someone reports the skill
"not working".

That check has already caught one real defect: `ats-resume-builder` was missing
`build ats resume` and `single column resume` from its condensed tier, so those
phrasings activated no skill at all.

## The two one-sided sets are intentional

Both collections hold 33 skills but only **22 overlap**.

**11 repo-only** — in this repo, absent from the app catalog. Measured
consequence: **none of these can ever reach an agent**, because the catalog is
the only thing `skill_injection` reads.

```
cover-letter-generator   interview-prep-generator  resume-ats-optimizer
resume-bullet-writer     resume-formatter          resume-quantifier
resume-section-builder   resume-tailor             resume-version-manager
salary-negotiation-prep  tech-resume-optimizer
```

**11 catalog-only** — app-native platform skills with no source here. They belong
to the product, not to the career catalog.

```
acceptance-criteria-review  accessibility-testing  agent-building
agentic-workflows           autoplan                check-work
deep-learning-rag-evals     frontend-design         llm-engineering
system-design               ui-ux-pro-max
```

Both sets are declared in [`catalog_contract.json`](../catalog_contract.json) and
verified against reality. Without a declaration the checker could only ever be
red; with one, an accidental addition or removal fails the build.

## Running it

```bash
# from this repo, pointing at the application
python scripts/check_catalog_fidelity.py \
  --catalog ../Vaeloom/apps/api/src/api/services/skill_catalog_service.py

# machine-readable
python scripts/check_catalog_fidelity.py --catalog <path> --json report.json
```

Exit code is `0` only when there are no fidelity failures **and** no contract
drift. Omit `--catalog` and it reports the repository-side state without
comparing.

## What this does not solve

- **Trigger vocabulary coverage.** Token-set matching (see
  `skill_injection._trigger_hits`) means *"tailor my resume"* now activates
  `ats-resume-builder`. But *"I want ATS feedback on my resume formatting"*
  still activates nothing, because `ats-audit` declares `audit resume
  formatting` and the message says *feedback*. Closing that means broadening the
  declared triggers, which is a content decision.
- **The 11 repo-only skills still never reach an agent.** Declaring the gap
  makes it visible; it does not close it.
- **Paraphrase fidelity.** The 8 low-overlap skills are not measurably faithful
  to their full sources; they are only measurably *related*. Grading that needs
  an LLM judge against a rubric, not a word-overlap threshold.
