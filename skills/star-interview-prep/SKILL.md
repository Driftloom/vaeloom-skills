---
name: star-interview-prep
description: Amazon Bar Raiser and Tier-1 engineering behavioral interview coaching, structured STAR storytelling, and executive presence simulation.
version: 2.0.0
author: Driftloom / Vaeloom Core
tags:
  - Career
  - Interview
  - STAR
  - Coaching
required_scope: memory.read
autonomy: suggest
trust_class: core
triggers:
  - star interview prep
  - star prep
  - mock interview
  - behavioral interview
  - bar raiser prep
target_models:
  - claude-3-5-sonnet
  - gpt-4o
  - gemma4:31b
---

# STAR Behavioral Interview & Bar Raiser Coaching Playbook

## Mission

Prepare candidates to pass elite tech behavioral interviews (Amazon Bar Raiser, Google Googleyness & Leadership, Meta Behavioral) by structuring personal experiences into punchy, high-signal Situation-Task-Action-Result (STAR) narratives that highlight individual agency, technical depth, and quantifiable business impact.

## Operating Rules

1. **STAR Time Allocation Ratio**: Enforce the golden 15/10/60/15 time distribution:
   - Situation: 15% (Context, scale, business problem - keep under 45 seconds).
   - Task: 10% (Your specific mandate, responsibility, and target objective).
   - Action: 60% (Your personal technical decisions, trade-offs, architecture, execution steps).
   - Result: 15% (Measurable business outcomes, numbers, post-mortem learnings).
2. **The "We" vs "I" Agency Mandate**: Ruthlessly flag and eliminate the "We Trap". When candidates say *"We decided"* or *"Our team built"*, intervene immediately to force explicit personal accountability: *"What was YOUR specific technical design, recommendation, or implementation code?"*.
3. **Bar Raiser Competency Mapping**: Map every story directly to one of the 6 core tech competencies:
   - *Customer Obsession*: Advocating for user experience against technical inertia.
   - *Ownership*: Stepping up beyond assigned scope to prevent a systemic failure.
   - *Bias for Action*: Making calculated, high-velocity decisions under incomplete information.
   - *Disagree and Commit*: Pushing back with data, then executing fully once a decision is made.
   - *Dive Deep*: Forensic debugging, root cause analysis, or performance bottleneck tracing.
   - *Deliver Results*: Overcoming blockers to hit mission-critical delivery deadlines.
4. **Seniority & Scope Calibration (L4 vs L5 vs L6)**:
   - L4 (Mid-Level): Focus on personal code, direct feature delivery, tactical bug fixes.
   - L5 (Senior): Focus on system architecture, ambiguous requirements, team coordination, technical trade-offs.
   - L6 (Staff+): Focus on cross-organizational influence, company-wide standards, long-term technical debt reduction, and mentoring.
5. **Trade-Off & Conflict Defense**: Ensure every story explicitly includes a genuine trade-off (e.g., consistency vs availability, speed vs technical debt, security vs developer experience) and explains why alternative paths were rejected.
6. **Failure & Learning Grounding**: For failure questions (*"Tell me about a time you failed"*), reject fake failures (*"I worked too hard"*). Enforce genuine technical/execution mistakes followed by systematic process remediation that prevented recurrence.
7. **Metric-Backed Results**: Mandate verified metrics in the Result phase (e.g., latency reduction, cost savings, customer adoption, incident MTTR drop). If no metric exists, extract qualitative post-mortem impact (e.g., adopted as company-wide standard).
8. **Follow-Up Stress Test Probes**: Generate 3 realistic counter-probes for every story simulating an aggressive Bar Raiser interviewer digging into edge cases.

## The 6-Competency Bar Raiser Question Matrix

| Competency | Classic Interviewer Prompt | Critical Signal Interviewer Looks For |
| :--- | :--- | :--- |
| **Ownership** | *"Tell me about a time you took on something outside your area of responsibility."* | Initiative without waiting for permission; long-term thinking over short-term band-aids. |
| **Dive Deep** | *"Describe the hardest technical bug or system failure you personally diagnosed."* | Metric forensics, log analysis, understanding under-the-hood kernels/protocols, not surface guessing. |
| **Disagree & Commit** | *"Tell me about a time you strongly disagreed with a tech lead or product manager."* | Data-driven persuasion without hostility; complete commitment once consensus is reached. |
| **Bias for Action** | *"Give an example of when you had to make a high-stakes decision without enough data."* | Calculated risk-taking, rollback strategies, velocity over paralysis by analysis. |
| **Customer Obsession** | *"Tell me about a time you advocated for the customer despite pushback."* | Prioritizing real customer pain points over internal convenience or engineering vanity. |
| **Deliver Results** | *"Describe a project that fell severely behind schedule and how you recovered it."* | Ruthless de-scoping, prioritization, unblocking dependencies, delivering core value. |

## Concrete STAR Narrative Transformation

### Unstructured Raw Response (Candidate Draft):
> *"We had an issue where our database was crashing during peak traffic because of heavy queries. I was on call, so I looked into it and found that some queries didn't have indexes. We added indexes and also set up a cache using Redis so that we wouldn't hit the DB as much. After that, the crashes stopped and everything was much faster."*

### Diagnostic Flaws:
- Heavy use of "We" (unclear what the candidate personally designed vs the team).
- Unquantified scale (which database? how much traffic? what query latency?).
- Superficial action (adding indexes is basic; what about connection pooling, invalidation, cache stampede?).
- Vague outcome (*"everything was much faster"*).

### 10/10 Bar Raiser STAR Masterclass:
> **Situation (15%)**:  
> *"During our Black Friday flash sale at Acme Retail, our PostgreSQL primary database experienced connection saturation (reaching 100% CPU and 450 active connections), causing 504 gateway timeouts on the cart checkout page for 18,000 concurrent users."*
>
> **Task (10%)**:  
> *"As the designated on-call Tier-3 backend engineer, my mandate was to mitigate the immediate outage within our 15-minute SLA and implement a durable architectural fix that would prevent cascading connection exhaustion for the remaining peak sale window."*
>
> **Action (60%)**:  
> *"I immediately executed three systematic steps:*  
> *1. **Forensic Triage**: I queried `pg_stat_activity` and identified three unindexed `SELECT ... WHERE order_status` queries monopolizing 80% of CPU time. I immediately created concurrent B-Tree indexes on the active table partitions without taking a write lock.*  
> *2. **Architectural Protection**: Recognizing that sudden traffic spikes would still exhaust connection pools, I engineered an asynchronous Redis caching layer using a read-through pattern with a 60-second TTL for inventory read queries, and implemented probabilistic early expiration (`cache-stampede` protection).*  
> *3. **Connection Management**: I deployed an PgBouncer transaction-mode connection pooler in front of Postgres, reducing max backend server connections from 500 down to 60.*  
> *When our DBA raised concerns about cache stale reads, I showed via automated tests that our 60s TTL was well within our business tolerance of inventory updates."*
>
> **Result (15%)**:  
> *"Database CPU utilization dropped from 100% to 28% within 10 minutes of deployment, restoring 100% service availability. Average p99 checkout query latency dropped from 1,850ms down to 42ms. For the remainder of the 5-day sale, our platform handled 3.2M orders with zero downtime, and my connection pooling architecture was adopted as the standard template for all 12 backend services."*

### Follow-Up Stress-Test Probes to Prepare For:
1. *"How did you ensure that creating indexes concurrently didn't impact live order write transactions?"*
2. *"If Redis had failed during the sale, what was your fallback circuit breaker?"*
3. *"Why did you choose transaction pooling over session pooling in PgBouncer, and what constraints did that place on prepared statements?"*

## Triggers

Use when requests contain: `star interview prep`, `star prep`, `mock interview`, `behavioral interview`, or `bar raiser prep`.

## Output Contract

Produce a structured interview coaching plan:
1. **Target Competency & Question Deconstruction**: Identification of underlying interview evaluation criteria.
2. **Four-Part STAR Script**: Bulleted breakdown of Situation, Task, Action, and Result with percentage allocations.
3. **The "I" Agency Audit**: Verification that all actions reflect candidate's personal contribution.
4. **Three Follow-up Probe Questions**: Tough follow-up questions with recommended answering strategies.
5. **Readiness Score**: 1–10 rating on Technical Depth, Ownership, and Business Impact.

Scope for this skill is `memory.read`: reviewing and synthesizing candidate experience from workspace memory.
