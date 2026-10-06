# Vaeloom Career Skills

Official open-standard collection of production-grade **Career Intelligence Skills** for autonomous AI agents, built for the **Vaeloom Personal Career Intelligence Platform** and compatible with the Anthropic Agent Skills standard (`SKILL.md`).

## 🎯 Included Skills

| Skill | Name | Required Scope | Autonomy | Description |
| :--- | :--- | :--- | :--- | :--- |
| [`ats-resume-builder`](skills/ats-resume-builder/SKILL.md) | ATS Resume Builder | `system.document.compile` | `approval_required` | Machine-readable resume compilation, ATS keyword gap analysis, and Playwright PDF page-fit loop. |
| [`career-coaching`](skills/career-coaching/SKILL.md) | Career Coaching & Strategy | `memory.read` | `suggest` | Strategic career pathing, promotion readiness, milestone planning, and executive behavioral coaching. |
| [`ats-audit`](skills/ats-audit/SKILL.md) | ATS Format & Parseability Audit | `system.document.compile` | `suggest` | Multi-engine ATS parseability audit (Workday, Greenhouse, Lever, Taleo, Ashby), formatting traps, and date linting. |
| [`resume-optimization`](skills/resume-optimization/SKILL.md) | Resume Bullet Optimization | `memory.read` | `suggest` | Google XYZ formula bullet point rewriting, power verb hardening, and quantified metric amplification. |
| [`job-discovery-radar`](skills/job-discovery-radar/SKILL.md) | Job Discovery & Market Radar | `system.browser.read` | `autonomous` | Autonomous career portal monitoring, requirements extraction, SSRF-guarded browser navigation, and fit scoring. |
| [`cover-letter-architect`](skills/cover-letter-architect/SKILL.md) | Cover Letter Architect | `memory.read` | `suggest` | Value-first, hook-driven cover letters connecting candidate achievements directly to employer pain points. |
| [`star-interview-prep`](skills/star-interview-prep/SKILL.md) | STAR Interview Story Prep | `memory.read` | `suggest` | Behavioral interview story banking distilling experiences into 90-second Situation-Task-Action-Result scripts. |
| [`salary-negotiation-playbook`](skills/salary-negotiation-playbook/SKILL.md) | Salary & Offer Negotiation | `memory.read` | `suggest` | Total compensation benchmarking, equity valuation models, counter-offer scripting, and pushback handling. |

## 🏗️ Architecture & Open Standard

Every skill adheres strictly to the **Vaeloom 8-Rule Verification Standard**:
1. `# <Title>` top-level heading.
2. `## Mission` defining the purpose and boundary.
3. `## Operating Rules` with at least 6 numbered invariant rules.
4. `## Triggers` with explicit user intent keywords.
5. `## Output Contract` specifying schema and citing required tool scopes.
6. Zero placeholders (`TODO`, `{{`, `<placeholder>`).
7. Authorized tool scope binding from `tool_scope_vocabulary()`.
8. Anti-hallucination and truthfulness mandates.

## 📦 Usage & Installation

### With Vaeloom
These skills are bundled directly into Vaeloom's catalog (`apps/api` and `apps/web`) and can be dynamically synced via `POST /capabilities/sync-github`.

### With Claude Code / Antigravity Agents
Copy the target folder into your local `.agents/skills` or `.claude/skills` directory:
```bash
cp -r skills/career-coaching ~/.agents/skills/
```

## 📄 License
Apache-2.0
