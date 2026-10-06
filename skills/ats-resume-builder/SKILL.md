---
name: ats-resume-builder
description: Automated ATS resume optimization, parsing, semantic scoring, keyword gap extraction, bullet point enhancement (XYZ formula), and Playwright PDF/DOCX page-budget compilation.
target_models: [claude, gemma, gpt, qwen]
tools_required: [compile_resume, extract_keywords, calculate_ats_score]
tags: [Career, Resume, ATS, Compilation]
required_scope: system.document.compile
autonomy: approval_required
trust_class: core_trusted
triggers:
  - build resume
  - tailor resume
  - ats match
  - compile resume
---

# ATS Resume Builder

## Mission
Produce a machine-readable, ATS-compliant resume tailored to target job descriptions that fits strict page budgets and maximizes recruiter interview conversion without fabricating candidate facts.

## Operating Rules
1. Ingest the candidate master profile and target job description before generating or modifying any resume sections.
2. Extract critical hard technical keywords, domain certifications, and core competencies, explicitly reporting match and gap statuses.
3. Rewrite professional achievement bullets using the Google XYZ formula: Accomplished [X], as measured by [Y], by doing [Z].
4. Enforce strict single-column typographical layout with standard margins (0.5in–0.75in) and ATS-safe font hierarchies (Georgia, Garamond, Inter).
5. Compile pixel-perfect PDF/DOCX assets via headless Playwright page-budget fitting, automatically shrinking type until the document fits the strict 1-page or 2-page ceiling.
6. Never fabricate fictitious companies, degrees, unearned certifications, or false employment dates under any circumstance.

## Triggers
Use when the request contains build resume, tailor resume, ats match, or compile resume.

## Output Contract
Markdown report containing extracted keyword gaps, tailored XYZ achievement bullets, composite ATS match score (0-100), and compiled document artifact metadata. Scope for this skill is `system.document.compile`.
