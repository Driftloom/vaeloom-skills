---
name: resume-optimization
description: Precision resume bullet rewriting, action verb hardening, metric quantification, and recruiter readability scoring using the Google XYZ formula.
target_models: [claude, gemma, gpt, qwen]
tools_required: [calculate_semantic_ats_score, tailor_resume_bullets]
tags: [Career, Resume, Optimization, Bullets]
required_scope: memory.read
autonomy: suggest
trust_class: core_trusted
triggers:
  - optimize resume
  - tailor bullets
  - xyz formula
  - rewrite bullet
---

# Resume Bullet Optimization

## Mission
Transform passive job task descriptions into quantified, high-impact accomplishment bullets that highlight candidate engineering ownership and business outcomes without exaggerating achievements.

## Operating Rules
1. Ingest raw experience bullets and evaluate each against the Google XYZ formula: Accomplished [X], as measured by [Y], by doing [Z].
2. Replace passive verbs and duty descriptions ("responsible for", "helped with") with decisive leadership and engineering power verbs (Architected, Spearheaded, Refactored, Streamlined).
3. Extract and amplify verifiable quantitative metrics (throughput, latency, error reduction, revenue, cost savings, user scale) for every project bullet.
4. Align rewritten bullets directly with target job description competencies while preserving 100% factual accuracy from the candidate's actual work history.
5. Prevent keyword stuffing by integrating technical competencies naturally into execution context rather than appending isolated keyword lists.
6. Provide side-by-side Before vs. After comparisons with an Impact Delta rating explaining why the revision elevates candidate competitiveness.

## Triggers
Use when the request contains optimize resume, tailor bullets, xyz formula, or rewrite bullet.

## Output Contract
Markdown table contrasting original bullets with optimized XYZ revisions, accompanied by metric explanations, power verb improvements, and estimated impact gain. Scope for this skill is `memory.read`.
