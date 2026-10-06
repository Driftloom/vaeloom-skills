---
name: resume-optimization
description: Precision resume bullet rewriting, action verb hardening, metric quantification, and recruiter readability scoring using the Google XYZ formula and Harvard OCS standards.
version: 2.0.0
author: Driftloom / Vaeloom Core
tags:
  - Career
  - Resume
  - Optimization
  - Google XYZ
required_scope: memory.read
autonomy: suggest
trust_class: core
triggers:
  - resume optimization
  - bullet rewrite
  - xyz formula
  - improve resume bullets
  - quantify achievements
target_models:
  - claude-3-5-sonnet
  - gpt-4o
  - gemma4:31b
---

# Resume Bullet Optimization & Google XYZ Playbook

## Mission

Transform weak, passive, duty-focused job descriptions into compelling, metric-driven achievement statements using the Google XYZ formula (*"Accomplished [X] as measured by [Y], by doing [Z]"*) and the Harvard OCS action verb framework. Maximize recruiter conversion and hiring manager engagement while preserving absolute factual integrity without fabricating ungrounded claims.

## Operating Rules

1. **Google XYZ Syntactic Mandate**: Every bullet point must adhere to the structural pattern: *"Accomplished [X] as measured by [Y], by doing [Z]"* or active front-loaded variations (*"[Strong Action Verb] [Core System/Project], achieving [Specific Metric [Y]] by [Technical Architecture or Method [Z]]"*).
2. **Elimination of Passive Responsibility Phrasing**: Strictly ban phrases like *"Responsible for"*, *"Assisted with"*, *"Worked on"*, *"Tasked with"*, *"Helped team"*, and *"Participated in"*. Replace them with high-agency Tier-1 power verbs.
3. **Metric Grounding & Non-Fabrication**: Never invent numerical metrics, revenue figures, percentage improvements, or dollar amounts that the user has not confirmed. When a metric is missing, generate targeted discovery prompts (`[Metric Discovery: What was the latency reduction, percentage throughput increase, or dollar cost saved?]`).
4. **Context-Action-Result Balance**: Ensure each bullet concisely delivers all three components: the business context or problem, the technical/operational action taken by the candidate, and the measurable business outcome.
5. **Technical Specificity & Toolchain Context**: Embed concrete technical tools, frameworks, languages, and architecture paradigms directly into the execution clause [Z] (e.g., *"utilizing Redis clustering and asynchronous Celery workers"* rather than *"using caching"*).
6. **Brevity & Visual Density**: Constrain bullet length to 1 to 2 lines (maximum 35–45 words per bullet). Eliminate filler adjectives (*"successfully"*, *"effectively"*, *"seamlessly"*).
7. **Scope & Seniority Calibration**: Calibrate bullet complexity to target seniority level:
   - Junior/Mid (L3–L4): Focus on feature delivery, test coverage, code quality, execution speed, bug reduction.
   - Senior/Staff (L5–L7): Focus on system architecture, cross-team alignment, technical roadmap, latency at scale, multi-million dollar cost reductions, developer velocity force multiplication.
8. **Recruiter Readability Scoring**: Assess each bullet on a 5-dimension rubric (Agency, Metric Rigor, Technical Depth, Brevity, Scope). Produce a quantifiable improvement delta before and after rewriting.

## Power Action Verb Taxonomy (Harvard OCS Standards)

| Impact Category | High-Agency Tier-1 Action Verbs | Banned Weak Synonyms |
| :--- | :--- | :--- |
| **System Architecture** | Architected, Engineered, Designed, Orchestrated, Spearheaded, Deployed | Worked on, Helped build |
| **Performance & Scale** | Benchmarked, Optimized, Accelerated, Streamlined, Scaled, Condensed | Made faster, Improved |
| **Financial & Efficiency** | Slashed, Monetized, Curtailed, Yielded, Consolidated, Negotiated | Saved money, Cut costs |
| **Leadership & Direction** | Directed, Championed, Mobilized, Mentored, Standardized, Instituted | Managed, Was in charge of |
| **Data & Reliability** | Formulated, Diagnosed, Automated, Rectified, Audited, Synthesized | Analyzed, Checked |

## The Google XYZ Transformation Methodology

$$\text{Strong Bullet} = \underbrace{\text{Action Verb + Outcome [X]}}_{\text{Impact}} + \underbrace{\text{Quantified Measurement [Y]}}_{\text{Proof}} + \underbrace{\text{Methodology / Tech Stack [Z]}}_{\text{Competence}}$$

### Transformation 1: Senior Backend Engineer
- **Weak Original**: *"Worked on the checkout microservice to improve payment processing speed and reduce failures."*
- **Diagnostic Flaws**: Zero metrics; passive verb (*"Worked on"*); generic description (*"improve speed"*); missing technical tools.
- **10/10 XYZ Optimized**:
  > *"Architected and rolled out an asynchronous idempotency layer for the core checkout service, reducing payment processing latency by 38% (from 420ms to 260ms) and decreasing transaction drop-offs by 14% across 2.4M monthly active users using FastAPI, Redis, and Kafka."*

### Transformation 2: Full-Stack / Frontend Engineer
- **Weak Original**: *"Responsible for rebuilding the user onboarding flow and adding modern analytics."*
- **Diagnostic Flaws**: Passive responsibility label; unquantified impact; no tech stack mentioned.
- **10/10 XYZ Optimized**:
  > *"Spearheaded the complete redesign of the enterprise onboarding portal using Next.js 15, Server Components, and TanStack Query, driving an 18.5% increase in 7-day user activation and reducing time-to-first-workflow from 14 minutes to 3.2 minutes."*

### Transformation 3: DevOps / Site Reliability Engineer (SRE)
- **Weak Original**: *"Helped the team migrate cloud resources to Kubernetes and set up monitoring alerts."*
- **Diagnostic Flaws**: Diminished agency (*"Helped the team"*); zero cost or uptime metrics; no cluster scale mentioned.
- **10/10 XYZ Optimized**:
  > *"Orchestrated zero-downtime migration of 42 microservices from legacy EC2 instances to AWS EKS with Terraform and ArgoCD, slashing annualized AWS compute expenditure by $180,000 while maintaining 99.995% service availability across 8 global regions."*

### Transformation 4: Product Manager / Tech Lead
- **Weak Original**: *"Led product roadmap for the mobile search feature and coordinated with design and QA."*
- **Diagnostic Flaws**: Missing business metric; vague coordination; no customer impact.
- **10/10 XYZ Optimized**:
  > *"Directed cross-functional execution of AI-assisted conversational search across iOS and Android, driving a 26% lift in search-to-cart conversion and delivering $1.4M in incremental Q4 ARR within 90 days of launch."*

## Metric Discovery Heuristic Checklist

When candidate bullets lack numbers, guide them with these exact extraction probes:
- **Scale**: How many users, transactions, requests per second (RPS), or data volume (TB/PB) did this impact?
- **Efficiency**: By what percentage did you reduce latency, page load time, CPU utilization, or memory footprint?
- **Financial**: What was the direct dollar cost reduction, revenue unlock, or software license saving?
- **Time/Velocity**: How many hours per week did this save the team? By how much did build/deploy times drop?

## Triggers

Use when requests contain: `resume optimization`, `bullet rewrite`, `xyz formula`, `improve resume bullets`, or `quantify achievements`.

## Output Contract

Produce a structured markdown transformation package:
1. **Bullet-by-Bullet Comparison Table**: Showing Original Bullet $\rightarrow$ Weaknesses $\rightarrow$ 10/10 XYZ Optimized Bullet.
2. **Metric Discovery Open Questions**: Targeted prompts for missing metrics the user can easily verify.
3. **Power Verb Diversity Audit**: Count of action verbs utilized to guarantee lexical range.
4. **Recruiter Readability Scorecard**: 1–10 rating across Agency, Metric Rigor, and Technical Density.

Scope for this skill is `memory.read`: extracting and analyzing user career history from workspace memory without unauthorized writes.
