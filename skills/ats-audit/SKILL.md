---
name: ats-audit
description: Comprehensive ATS parseability and format audit across Workday, Greenhouse, Lever, Taleo, and Ashby parsers, identifying layout traps and keyword density anomalies.
target_models: [claude, gemma, gpt, qwen]
tools_required: [audit_ats_formatting, extract_missing_hard_skills]
tags: [Career, ATS, Audit, Compliance]
required_scope: system.document.compile
autonomy: suggest
trust_class: core_trusted
triggers:
  - ats audit
  - audit resume
  - ats format check
  - parseability audit
---

# ATS Format & Parseability Audit

## Mission
Audit candidate resume documents against the parsing specifications of major Applicant Tracking Systems to eliminate layout failures, multi-column corruption, and missing section headers before submission.

## Operating Rules
1. Verify document layout adheres strictly to single-column top-down linear streams; flag multi-column tables, text boxes, and sidebar graphics as critical parser traps.
2. Audit section heading nomenclature against universal ATS standard dictionaries (`EXPERIENCE`, `EDUCATION`, `SKILLS`), flagging non-standard creative headers.
3. Validate date intervals for consistency across `MM/YYYY - MM/YYYY` or `Month YYYY - Present` conventions, highlighting unaddressed employment gaps exceeding 6 months.
4. Verify typography and glyphs use standard UTF-8 characters and universal fonts (Georgia, Garamond, Inter, Arial), flagging unparseable custom icon fonts.
5. Inspect document margins, header/footer text placements, and page breaks to ensure no contact info or critical skills are concealed in ignored footer bands.
6. Generate an ATS parseability confidence score (0-100) with specific, actionable remediation steps categorized by target ATS engine (Workday, Greenhouse, Lever, Taleo, Ashby).

## Triggers
Use when the request contains ats audit, audit resume, ats format check, or parseability audit.

## Output Contract
Markdown audit report containing composite parseability score, engine-specific compatibility flags, detected formatting violations with line locations, and remediation checklist. Scope for this skill is `system.document.compile`.
