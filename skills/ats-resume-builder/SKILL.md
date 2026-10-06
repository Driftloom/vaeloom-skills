---
name: ats-resume-builder
description: High-fidelity ATS-optimized resume formatting, single-column architecture, typography standards, and parser-safe compilation.
version: 2.0.0
author: Driftloom / Vaeloom Core
tags:
  - Career
  - Resume
  - Builder
  - Compilation
required_scope: system.document.compile
autonomy: suggest
trust_class: core
triggers:
  - ats resume builder
  - build ats resume
  - format resume
  - compile resume
  - single column resume
target_models:
  - claude-3-5-sonnet
  - gpt-4o
  - gemma4:31b
---

# ATS Resume Builder & Single-Column Architecture Playbook

## Mission

Compile clean, elegant, parser-bulletproof resumes that guarantee 100% extraction fidelity across enterprise Applicant Tracking Systems (Workday, Taleo, Greenhouse, Lever, iCIMS, Ashby). Enforce single-column visual hierarchy, typographic best practices, and deterministic section ordering that eliminates layout corruption while presenting an executive aesthetic to human reviewers.

## Operating Rules

1. **Single-Column Architectural Invariant**: Never emit multi-column layouts, sidebars, floating text boxes, graphic dividers, or embedded HTML/Word tables. The visual flow must strictly follow top-to-bottom linear streaming.
2. **Deterministic Section Ordering**: Organize document sections in standard industry hierarchy:
   - Header: Full Name (H1), Contact Data (Location, Phone, Email, LinkedIn, GitHub).
   - Professional Experience: Chronological order (most recent first).
   - Technical Skills: Categorized by sub-domains (Languages, Frameworks, Cloud/Infra, Tools).
   - Education: Degree, Major, Institution, Graduation Year.
   - Certifications & Patents (Optional, if verified).
3. **Typography & Metric Margins**:
   - Margins: 0.5 inches (dense) to 0.75 inches (standard); never exceed 1.0 inch or drop below 0.4 inches.
   - Font Families: Universal system fonts with standard unicode mappings (Calibri, Arial, Helvetica, Georgia, Garamond). Strictly prohibit custom web fonts, vector glyph icons, or icon fonts (e.g. FontAwesome phone icons).
   - Font Sizes: Full Name 18–22pt, Section Headings 13–15pt (Bold), Company/Role 11–12pt, Body Bullets 10–11pt.
4. **Clean Plaintext Extraction Verification**: The resulting document must yield 100% intelligible, correctly ordered plaintext when processed through `pdftotext` or clipboard copy-paste.
5. **Standardized Header Tokenizer Labels**: Use universal, unambiguous section titles:
   - Use `PROFESSIONAL EXPERIENCE` or `WORK EXPERIENCE` (avoid "Career Journey").
   - Use `TECHNICAL SKILLS` (avoid "Core Capabilities").
   - Use `EDUCATION` (avoid "Academic Background").
6. **Chronological Syntax Normalization**: Enforce uniform date styling across all employment entries: `Month YYYY – Month YYYY` (e.g., `Jan 2022 – Present` or `03/2021 – 11/2023`). Right-align dates and company locations consistently.
7. **Bullet Point Density & Punctuation**: Every bullet point must begin with an active power verb, contain 25 to 45 words, and end with consistent period punctuation. Maximize whitespace readability with 2–4pt line spacing between bullets.
8. **Page-Fit Budgeting**: Calibrate total content volume to exact page targets:
   - Under 7 years of experience: Strictly 1 page.
   - 8+ years or executive level: Strictly 2 full pages (never 1.25 or 1.5 pages).

## Structural Document Blueprint

```markdown
# FIRSTNAME LASTNAME
City, State/Country • +1 (555) 012-3456 • email@domain.com • linkedin.com/in/profile • github.com/username

## PROFESSIONAL EXPERIENCE

**Acme Cloud Inc** — Senior Software Engineer | Distributed Systems             San Francisco, CA
*Mar 2022 – Present*
• Architected high-throughput event ingestion engine processing 14M daily messages, achieving 99.99% availability by deploying asynchronous worker pools in Python and FastAPI.
• Slashed p99 database query latency by 42% (from 380ms to 220ms) by designing a tiered caching architecture with Redis Cluster and connection pooling.
• Spearheaded the zero-downtime migration of 18 microservices to AWS EKS with Terraform and Helm, reducing cloud infrastructure spend by $140,000 annually.

**Beta Technologies** — Software Engineer | Core Services                        Austin, TX
*Jun 2019 – Feb 2022*
• Engineered OAuth2/OIDC single sign-on authentication service supporting 250,000 active enterprise users using TypeScript and Node.js.
• Automated CI/CD deployment pipelines using GitHub Actions and Docker, reducing average release cycle time from 45 minutes to 8 minutes.

## TECHNICAL SKILLS

• **Languages**: Python, TypeScript, Go, SQL, Rust, Bash
• **Frameworks & Libraries**: FastAPI, Next.js, Node.js, React, PyTorch, Celery
• **Cloud & Infrastructure**: AWS (EKS, S3, RDS, DynamoDB), Docker, Kubernetes, Terraform, Redis, Kafka
• **Developer Tools & Databases**: PostgreSQL, Git, Linux, Prometheus, Grafana, Datadog

## EDUCATION

**University of California, Berkeley** — Bachelor of Science in Computer Science        Berkeley, CA
*Graduated May 2019*
```

## Triggers

Use when requests contain: `ats resume builder`, `build ats resume`, `format resume`, `compile resume`, or `single column resume`.

## Output Contract

Produce a compiled, verified ATS document package:
1. **Single-Column Markdown Document**: Fully structured, formatted, and syntax-checked resume.
2. **Extraction Fidelity Verification**: Proof of linear text extraction order.
3. **Page-Fit & Length Analysis**: Assessment of line counts and page budget adherence.
4. **Compilation Directives**: Formatter instructions for PDF/DOCX rendering engines.

Scope for this skill is `system.document.compile`: compiling verified ATS document specifications.
