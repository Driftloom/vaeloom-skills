---
name: job-discovery-radar
description: Autonomous job discovery, verified career portal monitoring, company hiring intelligence extraction, and live posting validation with SSRF protection.
version: 2.0.0
author: Driftloom / Vaeloom Core
tags:
  - Career
  - Job Search
  - Radar
  - Automation
required_scope: system.browser.read
autonomy: autonomous
trust_class: core
triggers:
  - job discovery radar
  - job search
  - find jobs
  - career radar
  - scrape job posting
target_models:
  - claude-3-5-sonnet
  - gpt-4o
  - gemma4:31b
---

# Autonomous Job Discovery Radar & Hiring Intelligence Playbook

## Mission

Autonomously discover, verify, and filter unindexed and high-signal engineering job openings across premier applicant tracking endpoints (Greenhouse, Lever, Ashby, Workday). Shield candidates from stale listings, ghost jobs, and staffing agency traps while extracting high-leverage company intelligence, tech stack requirements, and compensation bands.

## Operating Rules

1. **SSRF Guard & Domain Allowlist**: Strictly validate every job URL before fetching via browser or HTTP connectors. Enforce HTTPS, resolve DNS to verify non-private/non-loopback IP ranges (`127.0.0.1`, `10.0.0.0/8`, `192.168.0.0/16` strictly denied), and block untrusted redirects.
2. **First-Party Career Board Prioritization**: Prioritize direct enterprise ATS career portals over third-party scrapers or aggregators:
   - `boards.greenhouse.io/*`
   - `jobs.lever.co/*`
   - `jobs.ashbyhq.com/*`
   - `*.myworkdayjobs.com/*`
   - Official company engineering career subdomains (`company.com/careers`).
3. **Ghost Job & Stale Listing Elimination**: Reject and filter out listings displaying any of the following ghost signals:
   - Posted or refreshed > 60 days ago with continuous open status.
   - Ambiguous company identity or third-party recruitment agency camouflage (*"Our client, a stealth unicorn..."*).
   - Reposted more than 4 times in 90 days without hiring manager activity.
4. **Structured Intelligence Extraction**: For every verified opportunity, extract a canonical structured schema:
   - Company Name & Stage (Seed, Series A–D, Public, Bootstrapped).
   - Exact Job Title & Seniority Classification (IC3/IC4/IC5/IC6).
   - Remote / Hybrid / On-site Policy & Geographic Restrictions.
   - Base Salary Range & Equity Compensation Disclosures.
   - Primary Tech Stack (Languages, Frameworks, Cloud, Databases).
   - Key Pain Points / Major Product Initiatives described in the role overview.
5. **Team Velocity & Funding Signal Correlation**: Correlate open job postings with company momentum signals:
   - Recent capital raises (Crunchbase / PitchBook announcements).
   - Engineering blog activity (recent architecture migrations, open-source releases).
   - Team growth rate and retention telemetry.
6. **Rate-Limit & Scraping Etiquette**: Respect site concurrency boundaries. Enforce backoff on HTTP 429 errors and adhere to workspace quotas (default: maximum 20 requests/hour per workspace) to maintain zero platform fingerprinting.
7. **Semantic Fit Scoring**: Compare extracted role responsibilities against candidate experience stored in workspace memory, computing a deterministic Match Index (0–100%) broken into Skills Fit, Seniority Fit, and Domain Fit.
8. **Link Verification Invariant**: Test live HTTP responsiveness (`200 OK`) and ensure application forms are active before adding any listing to the candidate's active application queue.

## Canonical ATS Endpoint Signatures

| ATS Provider | URL Structure | Extraction Technique |
| :--- | :--- | :--- |
| **Greenhouse** | `boards.greenhouse.io/{company}/jobs/{id}` | Direct JSON API endpoint (`/v1/boards/{company}/jobs/{id}`) or clean HTML parsing. |
| **Lever** | `jobs.lever.co/{company}/{uuid}` | Clean microdata schema extraction (`schema.org/JobPosting`). |
| **Ashby** | `jobs.ashbyhq.com/{company}/{uuid}` | Hydrated React state extraction or GraphQL query. |
| **Workday** | `{company}.wd5.myworkdayjobs.com/{board}/job/{id}` | Direct REST payload inspection (`/wday/cxs/{company}/{board}/jobs`). |

## Multi-Factor Job Verification Scorecard

$$\text{Opportunity Score} = (0.35 \times \text{Skills Fit}) + (0.25 \times \text{Compensation Transparency}) + (0.20 \times \text{Company Health}) + (0.20 \times \text{Freshness})$$

### Concrete Extraction Case: Senior Systems Engineer at Driftloom

```json
{
  "company": "Driftloom",
  "title": "Senior Systems Engineer — Distributed Runtimes",
  "level": "L5 / Senior",
  "location": "San Francisco, CA (Hybrid 2d) or Remote US",
  "salary_range": {
    "min": 185000,
    "max": 235000,
    "currency": "USD",
    "equity": "0.15% - 0.35% ISOs"
  },
  "tech_stack": ["Rust", "Python", "FastAPI", "PostgreSQL", "Docker", "eBPF"],
  "core_initiatives": [
    "Building zero-overhead isolated sandboxes for LLM agent code execution",
    "Scaling distributed SQLite memory synchronization across 10,000 edge nodes"
  ],
  "hiring_signals": {
    "freshness_days": 4,
    "verified_direct_board": true,
    "agency_flag": false,
    "ghost_job_risk": "VERY LOW"
  },
  "candidate_match_score": 94
}
```

## Triggers

Use when requests contain: `job discovery radar`, `job search`, `find jobs`, `career radar`, or `scrape job posting`.

## Output Contract

Produce a structured markdown opportunity dossier:
1. **Curated Job Queue Table**: Company, Title, Location, Compensation, Match %, Application Link.
2. **Deep-Dive Opportunity Cards**: For top 3 matches, provide Tech Stack, Product Pain Points, and Hiring Insights.
3. **Ghost Job & Exclusion Log**: List of rejected listings with clear reasons (stale date, agency, SSRF failure).
4. **Tailored Application Recommendations**: Recommended custom resume angle and cover letter hooks.

Scope for this skill is `system.browser.read`: observing and parsing public career web pages under strict SSRF containment.
