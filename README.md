# Vaeloom Career Skills

Official enterprise collection of production-grade **Career Intelligence Skills, Benchmarks, and Tooling** for autonomous AI agents. Built for the **Vaeloom Personal Career Intelligence Platform** and fully compliant with the Anthropic and OpenAI Agent Skills specifications (`agentskills.io`).

---

## 🏛️ Repository Architecture (Anthropic & OpenAI Standard)

This repository adheres to the progressive disclosure architecture used by premier agent skill ecosystems (Anthropic & OpenAI):

```
vaeloom-skills/
├── .github/workflows/
│   └── ci.yml                     # Continuous integration running tests and evals
├── evals/
│   ├── eval_cases.json            # Deterministic evaluation test cases & assertions
│   └── run_evals.py               # Evals benchmark test runner with strict scoring
├── tests/
│   ├── test_skills_schema.py      # Frontmatter schema, section, & reference JSON tests
│   └── test_skill_scripts.py      # Unit and regression tests for all helper scripts
├── pyproject.toml                 # Python project configuration (pytest, dependencies)
├── package.json                   # NPM manifest with test, eval, and lint scripts
└── skills/
    ├── <skill-slug>/
    │   ├── SKILL.md               # Primary progressive-disclosure agent instructions
    │   ├── scripts/               # Optional deterministic CLI helpers & validators
    │   ├── references/            # Optional domain JSON schemas & reference ontologies
    │   └── templates/             # Optional production templates (markdown, text)
```

---

## 🎯 Skill Catalog (30 Skills)

### 🌟 Core Vaeloom Flagship Skills

| Skill | Name | Required Scope | Autonomy | Scripts & References |
| :--- | :--- | :--- | :--- | :--- |
| [`ats-resume-builder`](skills/ats-resume-builder/SKILL.md) | ATS Resume Builder | `system.document.compile` | `approval_required` | `templates/standard_single_column.md` |
| [`career-coaching`](skills/career-coaching/SKILL.md) | Career Coaching & Strategy | `memory.read` | `suggest` | Diagnostic coaching & promotion readiness |
| [`ats-audit`](skills/ats-audit/SKILL.md) | ATS Format & Parseability Audit | `system.document.compile` | `suggest` | `scripts/ats_checker.py`, `references/sovren_parsing_rules.json` |
| [`resume-optimization`](skills/resume-optimization/SKILL.md) | Resume Bullet Optimization | `memory.read` | `suggest` | `scripts/xyz_scorer.py`, `references/action_verbs_taxonomy.json` |
| [`job-discovery-radar`](skills/job-discovery-radar/SKILL.md) | Job Discovery & Market Radar | `system.browser.read` | `autonomous` | `scripts/portal_scanner.py`, `references/ats_endpoints.json` |
| [`cover-letter-architect`](skills/cover-letter-architect/SKILL.md) | Cover Letter Architect | `memory.read` | `suggest` | `templates/three_act_cover_letter.md` |
| [`star-interview-prep`](skills/star-interview-prep/SKILL.md) | STAR Interview Story Prep | `memory.read` | `suggest` | `scripts/star_validator.py`, `references/bar_raiser_rubric.json` |
| [`salary-negotiation-playbook`](skills/salary-negotiation-playbook/SKILL.md) | Salary & Offer Negotiation | `memory.read` | `suggest` | `scripts/comp_calculator.py`, `references/negotiation_scripts.json`, `templates/counter_offer_email.md` |

### 🛠️ Specialized Role, Document & Interview Skills (22 Skills)

| Skill Slug | Description |
| :--- | :--- |
| [`academic-cv-builder`](skills/academic-cv-builder/SKILL.md) | Academic CVs with publications, grants, and teaching tenure. |
| [`application-form-filler`](skills/application-form-filler/SKILL.md) | Context-aware job application field filling from CV and JD. |
| [`career-changer-translator`](skills/career-changer-translator/SKILL.md) | Translate cross-industry competencies and transferable skills. |
| [`cold-email-writer`](skills/cold-email-writer/SKILL.md) | Personalized outreach to hiring managers and technical leads. |
| [`cover-letter-generator`](skills/cover-letter-generator/SKILL.md) | Structured 250–400 word value-driven cover letter generation. |
| [`creative-portfolio-resume`](skills/creative-portfolio-resume/SKILL.md) | Balances aesthetic visual presentation with strict ATS compliance. |
| [`executive-resume-writer`](skills/executive-resume-writer/SKILL.md) | C-suite and VP level leadership resumes emphasizing P&L and scale. |
| [`interview-prep-generator`](skills/interview-prep-generator/SKILL.md) | Question prediction, STAR answer banking, and reverse interview queries. |
| [`linkedin-profile-optimizer`](skills/linkedin-profile-optimizer/SKILL.md) | Headline & profile conversion optimization, 220-char budget linting, and 12-criteria 100-pt audit. | `scripts/profile_evaluator.py`, `scripts/headline_lint.py`, `references/rubric.json` |
| [`linkedin-interviewer`](skills/linkedin-interviewer/SKILL.md) | Diagnostic interview builder compiling verified receipts, turning points, and scars into a Story Bank. | `scripts/story_bank_validator.py`, `references/question-bank.md`, `templates/story_bank.md` |
| [`linkedin-humanizer`](skills/linkedin-humanizer/SKILL.md) | Strips invisible unicode smuggling, normalizes typography, and removes 113 AI tropes while preserving numbers. | `scripts/humanize.py`, `scripts/detect.py`, `references/slop.json` |
| [`linkedin-post-writer`](skills/linkedin-post-writer/SKILL.md) | Drafts viral-ready, high-dwell-time posts using 21 hook formulas and 10 founder angles. | `references/hooks.json`, `references/founder-topics.md` |
| [`offer-comparison-analyzer`](skills/offer-comparison-analyzer/SKILL.md) | Multi-offer side-by-side total compensation and benefits comparison. |
| [`portfolio-case-study-writer`](skills/portfolio-case-study-writer/SKILL.md) | Deep engineering and product case studies with architecture impact. |
| [`reference-list-builder`](skills/reference-list-builder/SKILL.md) | Formatted reference sheets with context briefings for advocates. |
| [`resume-ats-optimizer`](skills/resume-ats-optimizer/SKILL.md) | Comprehensive keyword optimization and ATS parseability linting. |
| [`resume-bullet-writer`](skills/resume-bullet-writer/SKILL.md) | Achievement-focused bullet transformations with active power verbs. |
| [`resume-formatter`](skills/resume-formatter/SKILL.md) | Parser-safe typographic hierarchy and clean single-column layouts. |
| [`resume-quantifier`](skills/resume-quantifier/SKILL.md) | Extracting metrics, estimates, and business impact from plain responsibilities. |
| [`resume-section-builder`](skills/resume-section-builder/SKILL.md) | Target section composition (Projects, Certifications, Leadership). |
| [`resume-tailor`](skills/resume-tailor/SKILL.md) | Truthful JD-to-resume tailoring without fabrication or false credentials. |
| [`resume-version-manager`](skills/resume-version-manager/SKILL.md) | Master resume version tracking and variant management. |
| [`salary-negotiation-prep`](skills/salary-negotiation-prep/SKILL.md) | 75th percentile market compensation benchmarks and negotiation scripts. |
| [`tech-resume-optimizer`](skills/tech-resume-optimizer/SKILL.md) | Software engineering, systems architecture, and engineering management resumes. |

---

## 🧪 Testing & Continuous Evaluation

This repository includes automated testing and evaluation harnesses mirroring production standards:

### 1. Schema & Unit Tests
Run the test suite with `pytest`:
```bash
pytest tests/ -v
```
- **Schema Validation**: Validates frontmatter, YAML format, required sections (`# Title`, `## Mission`, `## Operating Rules`, `## Triggers`, `## Output Contract`).
- **Placeholder Detection**: Ensures no unresolved `TODO` or template tags exist.
- **Reference JSON Integrity**: Confirms all reference data files parse as valid JSON.
- **Script Unit Tests**: Exercises every Python helper script against valid and adversarial inputs.

### 2. Evaluation Benchmark Harness (`evals/`)
Run deterministic evaluations:
```bash
python evals/run_evals.py
```
Validates agent tool scripts against real-world scenarios:
- `eval-ats-001`: Multi-column and table parsing hazard detection.
- `eval-xyz-001`: Passive verb flagging and metric density scoring.
- `eval-xyz-002`: High-agency metric-driven XYZ bullet point scoring.
- `eval-comp-001`: Accurate multi-component Total Comp modeling (Base + Bonus + Equity + Sign-on).
- `eval-star-001`: Detection of the "We Trap" (passive team deflection) in behavioral interviews.

### 3. Continuous Integration
All PRs and pushes to `master` trigger the GitHub Actions workflow in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## 📦 Usage & Installation

### With Vaeloom
These skills are bundled directly into Vaeloom's catalog (`apps/api` and `apps/web`) and can be dynamically synced via:
```bash
POST /capabilities/sync-github
```

### With Claude Code & Antigravity Agents
Install into your active agent directory:
```bash
cp -r skills/* ~/.agents/skills/
```

---

## 📄 License
MIT
