---
name: ats-audit
description: Comprehensive ATS parseability, typography, and keyword density audit across Workday, Greenhouse, Lever, Taleo, and Ashby parsers.
version: 2.0.0
author: Driftloom / Vaeloom Core
tags:
  - Career
  - ATS
  - Audit
  - Compliance
required_scope: system.document.compile
autonomy: suggest
trust_class: core
triggers:
  - ats audit
  - ats scan
  - parse test
  - resume parser check
  - audit resume formatting
target_models:
  - claude-3-5-sonnet
  - gpt-4o
  - gemma4:31b
---

# ATS Formatting & Parseability Audit Playbook

## Mission

Deliver rigorous, parser-accurate diagnostic audits of candidate resumes against the technical ingestion engines of enterprise Applicant Tracking Systems (Workday/Sovren, Greenhouse, Lever, Taleo, iCIMS, and Ashby). Eliminate silent parsing failures, layout traps, and entity extraction corruption before human recruiters ever review the application.

## Operating Rules

1. **Parser Engine Parity**: Never evaluate a resume purely as a visual visual artifact; always simulate linear text stream extraction (`pdftotext`, Apache PDFBox, Daxtra, and Sovren OCR tokenizers).
2. **Column & Table Prohibition**: Flag any multi-column layout, sidebar, embedded table, or text box as a critical parsing hazard that causes interleaved reading-order corruption in legacy ATS engines.
3. **Contact Header Integrity**: Verify that email, phone number, LinkedIn URL, GitHub profile, and geographic location are located in the main document body, not hidden inside PDF header/footer metadata zones which 40% of parsers ignore.
4. **Section Ontology Compliance**: Enforce standard industry header labels (`Work Experience`, `Professional Experience`, `Education`, `Technical Skills`, `Certifications`). Flag creative synonyms like "Where I've Been" or "Capabilities Matrix" that break heuristic classifier ontologies.
5. **Date Normalization Standards**: Audit all date ranges for unambiguous chronological syntax (`MM/YYYY - MM/YYYY` or `Month YYYY - Present`). Flag missing months or ambiguous year-only dates (`2021 - 2022`) that cause parsers to default to January 1st and miscalculate total tenure.
6. **Glyph & Ligature Sanitization**: Identify non-standard bullet characters, decorative icon fonts (FontAwesome icons used for phone/email), and complex ligatures (`fi`, `fl`, `ffi`) that translate into null bytes or corrupted unicode (`\uFFFD`).
7. **Semantic Keyword Density**: Compare extracted hard skills against target Job Description requirements using cosine similarity thresholds and exact token matching, identifying missing competencies without recommending keyword-stuffing anti-patterns.
8. **Deterministic 100-Point Scoring**: Produce an objective, rubric-backed Parseability Index broken into Parse Stream Integrity (30 pts), Section Classification (25 pts), Entity Extraction (25 pts), and Chronology Consistency (20 pts).

## ATS Technical Parser Profiles

| Parser Engine | Primary Platforms | Core Failure Vulnerability | Strict Requirement |
| :--- | :--- | :--- | :--- |
| **Sovren Engine** | Workday, Taleo | Multi-column layouts interleave text lines into scrambled sentences. | Single-column linear flow; no tables or text frames. |
| **Daxtra Engine** | Greenhouse, iCIMS | Complex vector graphics and header/footer metadata blocks get dropped. | Contact info must reside in the body root (top 15% of page). |
| **Lever Native Parser** | Lever | Skill tags hidden in separate columns fail semantic entity recognition. | Skills clearly grouped under a formal `Technical Skills` header. |
| **Ashby Parser** | Ashby, Modern Startups | Strict markdown and plaintext tokenization; sensitive to non-standard bullets. | Standard bullet characters (`•`, `-`) and standard UTF-8 encoding. |

## Audit Methodology & Execution Phases

### Phase 1: Text Stream Extraction & Layout Forensics
- Extract raw plaintext from the document in sequential reading order.
- Inspect whether columns, sidebars, or floating text boxes cause text from disparate sections to merge horizontally.
- Verify page margin safety (minimum 0.5 inches, recommended 0.75 inches).

### Phase 2: Entity & Contact Extraction Audit
- Test regular expression and NLP extraction for:
  - Full Name (must be the dominant H1 text element).
  - Primary Email (must be RFC 5322 compliant, clickable mailto link).
  - Phone Number (must include standard formatting: `(XXX) XXX-XXXX` or `+1-XXX-XXX-XXXX`).
  - Physical Location (City, State/Country - no full street address required).
  - Web Properties (LinkedIn, GitHub, Portfolio - explicit URLs without obfuscated link text).

### Phase 3: Section Hierarchy & Chronology Audit
- Ensure headers use distinct, ascending heading levels or clear capitalization hierarchy.
- Validate date consistency across all roles:
  - Check for chronological order (most recent role first).
  - Verify concurrent roles are clearly labeled.
  - Flag overlapping date conflicts or unexplained multi-year gaps for user review.

### Phase 4: Keyword Matching & Semantic Density
- Extract hard technical skills, tools, frameworks, and certifications.
- Calculate exact-match frequency (ideal: 2–4 occurrences for primary skills across bullet points).
- Flag keyword stuffing traps (e.g., hidden white text, endless lists of uncontextualized acronyms) that trigger anti-cheat rejection filters.

## Concrete Diagnostic Example

### Bad Input (Parsing Trap):
```text
[Left Sidebar - 30% Width]        [Main Column - 70% Width]
SKILLS                           EXPERIENCE
Python, React, AWS               Acme Corp | Senior Engineer | 2022 - Present
CONTACT                          - Built distributed pipeline handling 5M msgs.
john@doe.com                     Beta Inc | Software Engineer | 2020 - 2022
(555) 019-2831                   - Created user auth service.
```

### Parser Output Disruption:
`SKILLS EXPERIENCE Python, React, AWS Acme Corp | Senior Engineer | 2022 - Present CONTACT - Built distributed pipeline...`  
*(Notice how skills and company names collide into unparseable entities).*

### Remediated Recommendation (Single-Column Linear Flow):
```text
John Doe
San Francisco, CA • john@doe.com • (555) 019-2831 • linkedin.com/in/johndoe • github.com/johndoe

PROFESSIONAL EXPERIENCE
Acme Corp — Senior Software Engineer                         03/2022 – Present
• Architected and deployed distributed event pipeline processing 5M+ daily messages with 99.99% uptime.

Beta Inc — Software Engineer                                  06/2020 – 02/2022
• Engineered OAuth2/OIDC authentication service supporting 120k active enterprise users.

TECHNICAL SKILLS
• Languages & Frameworks: Python, TypeScript, React, Node.js, FastAPI
• Cloud & Infrastructure: AWS (ECS, S3, RDS), Docker, Kubernetes, Terraform
```

## Triggers

Use when requests contain: `ats audit`, `ats scan`, `parse test`, `resume parser check`, or `audit resume formatting`.

## Output Contract

Produce a structured markdown audit report:
1. **Executive Summary & Parseability Score** (`0–100` Index with Pass/Conditional/Fail verdict).
2. **Critical Parsing Hazards (P0/P1)**: Explicit layout, table, header, or font issues that guarantee parser failure.
3. **Entity Extraction Report**: Table showing extracted Name, Email, Phone, Location, Social URLs.
4. **Section & Chronology Breakdown**: Status of each standard section header and date formatting.
5. **Keyword Alignment & Missing Skills**: Sourced list of critical keywords missing from the text.
6. **Remediation Action Plan**: Step-by-step checklist to achieve a 95+ score.

Scope for this skill is `system.document.compile`: auditing and compiling verified ATS document specifications.
