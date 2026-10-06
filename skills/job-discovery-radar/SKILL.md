---
name: job-discovery-radar
description: Autonomous job discovery, verified career portal monitoring, company hiring intelligence extraction, and live posting validation with SSRF protection.
target_models: [claude, gemma, gpt, qwen]
tools_required: [browse_job_page, scrape_company_insights, verify_application_link]
tags: [Career, JobSearch, Radar, Automation]
required_scope: system.browser.read
autonomy: autonomous
trust_class: core_trusted
triggers:
  - job radar
  - search jobs
  - discover jobs
  - find vacancies
---

# Job Discovery & Market Radar

## Mission
Autonomously discover and verify relevant job opportunities across verified company career portals, extract core requirements, and score role fit while enforcing strict URL security and quota budgets.

## Operating Rules
1. Ingest candidate career targets (role titles, seniority, tech stack, location preferences, remote status) from workspace profile memory.
2. Search and discover open requisitions across verified platforms and direct ATS domains (Greenhouse, Lever, Ashby, Workday), discarding stale listings older than 30 days.
3. Validate every outbound target URL through Vaeloom URL guard to prevent SSRF vulnerabilities, enforcing HTTPS-only and rejecting internal IP spaces.
4. Extract structured job metadata: exact title, hiring team, core technical requirements, nice-to-have qualifications, compensation bands, and visa sponsorship status.
5. Compute multi-factor match score combining semantic vector relevance, required tech stack overlap, and candidate years of experience.
6. Rate-limit external browser requests to honor workspace hourly scrape quotas, logging audit trails for every investigated career opportunity.

## Triggers
Use when the request contains job radar, search jobs, discover jobs, or find vacancies.

## Output Contract
Markdown table of discovered positions including job title, company name, match score, key requirements summary, verified application link, and discovery timestamp. Scope for this skill is `system.browser.read`.
