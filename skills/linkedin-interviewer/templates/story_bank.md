# Career Story Bank

Persistent record of authentic career experiences, receipts, turning points, and scars.
Populated via the `linkedin-interviewer` skill. No fabricated metrics or fictional claims.

---

## 1. Roles & Scopes
- **Role Title**: Senior Software Engineer / Lead Platform Architect
- **Company / Org**: TechCorp Inc.
- **Tenure**: 2022 - Present
- **Team Size**: 12 distributed engineers (frontend, backend, SRE)
- **Primary Mission**: Core payment and API billing platform infrastructure

---

## 2. Receipts & Concrete Figures (The Numbers)
- **Throughput**: Scaled transaction throughput from 2,500 RPS to 14,000 RPS.
- **Cost Reduction**: Cut AWS cloud infrastructure expenditure by 34% ($18,500/month reduction).
- **Incident Recovery**: Reduced MTTR (Mean Time to Resolution) from 85 minutes to 11 minutes.
- **Deployment Velocity**: Automated CI/CD pipeline reducing release cycle from 3 days to 18 minutes.

---

## 3. Turning Points & Scars (What Went Wrong & What Changed)
- **The Scar**: In March 2023, an unthrottled distributed webhook consumer caused cascading Redis memory exhaustion, causing 42 minutes of downtime during peak billing.
- **The Correction**: Rebuilt the ingestion architecture around Kafka partitions and resilient backpressure circuit breakers. Stopped assuming upstream producers would honor rate limits.

---

## 4. Defended Positions (Unpopular Opinions & Convictions)
- **Position**: Microservices at seed/Series A stages are an unforced architectural error. A modular monolith with clean domain boundaries ships 5x faster and scales to $20M ARR without Kubernetes complexity.
- **Cost Paid**: Defended this against external advisors; retained lean 4-person infrastructure overhead for 2 years.

---

## 5. Off-Limits Boundaries
- Do not publicly name enterprise client contracts under NDA.
- Do not disclose unreleased Series B valuation figures.
