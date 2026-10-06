---
name: salary-negotiation-playbook
description: Total compensation negotiation, counter-offer strategy, equity math valuation, and executive compensation scripts based on Patrick McKenzie and Haseeb Qureshi frameworks.
version: 2.0.0
author: Driftloom / Vaeloom Core
tags:
  - Career
  - Compensation
  - Negotiation
  - Strategy
required_scope: memory.read
autonomy: suggest
trust_class: core
triggers:
  - salary negotiation playbook
  - negotiate salary
  - counter offer
  - equity math
  - compensation review
target_models:
  - claude-3-5-sonnet
  - gpt-4o
  - gemma4:31b
---

# Salary Negotiation & Total Compensation Playbook

## Mission

Maximize candidate Total Compensation (TC) across base salary, equity, signing bonuses, and executive benefits using game-theoretic negotiation frameworks (Patrick McKenzie / Haseeb Qureshi). Eliminate unforced concessions, anchor bias traps, and equity valuation misunderstandings through data-grounded, collaborative scripts.

## Operating Rules

1. **The Iron Law of Anchoring**: Never reveal current compensation or state a specific number first during early recruitment stages. Deflect compensation queries with market-aligned, collaborative positioning until a formal written or verbal offer is extended.
2. **Total Compensation (TC) Holism**: Always evaluate and negotiate the complete package rather than fixating solely on base salary:
   $$\text{Total Compensation (Year 1)} = \text{Base Salary} + \text{Annual Target Bonus} + \frac{\text{Equity Grant}}{\text{Vesting Period Years}} + \text{Signing Bonus}$$
3. **BATNA Maximization**: Establish and quantify the candidate's Best Alternative to a Negotiated Agreement (BATNA)—whether it is a competing written offer, current role retention with promotion trajectory, or active late-stage interview pipelines.
4. **Equity Valuation & Liquidity Diligence**:
   - For Public Companies: Value RSUs at current 30-day Volume Weighted Average Price (VWAP) with clear vesting schedules (standard 4-year, 1-year cliff, quarterly thereafter).
   - For Private Startups: Never accept raw "options count" or vague dollar projections. Mandate disclosure of Total Fully Diluted Shares, Current 409A Valuation, Preferred Share Price at most recent round, and Liquidation Preferences.
5. **Enthusiasm-Anchored Countering**: Every counter-offer must begin with genuine enthusiasm for the team and mission (*"I am thrilled about the opportunity to build the core platform with the team..."*), framing the financial delta as an alignment of market value that will allow immediate, enthusiastic acceptance.
6. **Multi-Lever Trade-Off Strategy**: If the employer claims rigid band constraints on base salary, immediately pivot negotiation to alternative high-value levers:
   - Year-1 Signing Bonus (drawn from separate recruiting budgets, not departmental OPEX).
   - Additional Equity / Options pool allocation.
   - Accelerated Performance Review (written clause for formal compensation review at 6 months instead of 12).
   - Relocation, home office stipend, or remote working allowances.
7. **Absolute Non-Ultimatum Principle**: Never make artificial threats, deliver hostile ultimatums, or bluff nonexistent competing offers. Recruiter relationships and reputations compound across decades.
8. **Writing-Only Closing Mandate**: Never accept an offer orally on the phone. Always request 24–48 hours to review the detailed offer letter with family/advisors, and submit counters in crisp, professional written form.

## Tech Equity Compensation Breakdown

| Instrument | Common Stage | Valuation Metric | Core Risk / Tax Traps |
| :--- | :--- | :--- | :--- |
| **RSUs (Restricted Stock Units)** | Public / Late-stage Pre-IPO | Dollar value linked to public stock ticker. | Treated as ordinary income upon vesting; subject to market volatility. |
| **ISOs (Incentive Stock Options)** | Early to Mid-Stage Startups | Spread between Strike Price and Fair Market Value (FMV). | Alternative Minimum Tax (AMT) risk upon exercise; 90-day post-termination exercise window. |
| **NSOs (Non-Qualified Options)** | Advisors / Contractors / Late Startups | Spread between Strike Price and FMV. | Ordinary income tax on spread at time of exercise. |

## 4 Word-for-Word Negotiation Script Templates

### Template 1: Early-Stage Anchor Deflection (Recruiter Screen)
* **Recruiter Prompt**: *"What are your salary expectations for this role, or what are you currently making?"*
* **Response**:
  > *"I’m focused on finding the right role where I can make an immediate technical impact on your distributed systems roadmap. Since I don't yet have full context on the team's scope and the complete benefits package, I'm confident that if we determine there’s a strong mutual fit, you'll make a competitive offer aligned with the market for this level. What is the approved compensation range for this position?"*

### Template 2: Receiving the Verbal Offer (Enthusiasm Without Acceptance)
* **Recruiter Prompt**: *"We’d like to offer you $175,000 base and $80,000 equity over 4 years. Can you accept today?"*
* **Response**:
  > *"Thank you so much! I really enjoyed meeting Sarah and the engineering team, and I’m genuinely excited about the challenge of scaling the platform. This is an important career decision, so I’d like to review the formal offer letter and equity documentation in detail with my family. Could you email over the written offer details? I will review everything thoroughly and get back to you within 48 hours."*

### Template 3: The Formal Written Counter-Offer (Competing Leverage)
* **Use Case**: Candidate has another offer or strong market data:
  > *"Subject: [Candidate Name] — Offer Discussion & Next Steps  
  > 
  > Hi [Recruiter Name],  
  > 
  > Thank you again for extending the offer to join [Company] as [Title]. I had wonderful conversations with the team, and I am very eager to contribute to [Specific Project/Goal].  
  > 
  > I’ve evaluated the complete package of $175k base and $80k equity over 4 years. As mentioned, I am currently in late-stage conversations with another team where the total compensation package is around $225k.  
  > 
  > [Company] remains my clear top choice because of the engineering team's culture and the mission. If we can adjust the package to **$190,000 base salary** and a **$25,000 signing bonus** (or equivalent equity adjustment), I would be thrilled to decline my other processes and sign the offer immediately today.  
  > 
  > Let me know if that is feasible on your end. I really appreciate your partnership in making this work!  
  > 
  > Best regards,  
  > [Candidate Name]"*

### Template 4: Pivoting to Non-Base Levers (When Base is Capped)
* **Recruiter Response**: *"Our band strictly caps base salary at $175,000 for this level."*
* **Candidate Response**:
  > *"I completely understand and respect internal band constraints. Since base salary is fixed, would you be able to bridge the gap through a one-time signing bonus of $20,000, or an additional 4,000 equity shares? That would bring the first-year compensation to where I need it to be and enable me to commit today."*

## Triggers

Use when requests contain: `salary negotiation playbook`, `negotiate salary`, `counter offer`, `equity math`, or `compensation review`.

## Output Contract

Produce a structured negotiation strategy document:
1. **Current Package vs Target TC Matrix**: Itemized breakdown of Base, Bonus, Equity, Signing.
2. **Leverage & BATNA Audit**: Assessment of candidate's bargaining strength and risks.
3. **Target Counter Numbers**: Realistic Best-Case, Target, and Walk-Away thresholds.
4. **Customized Written Script**: Tailored email response ready for recruiter communication.
5. **Contingency Decision Tree**: Next steps for accepted, counter-offered, or rejected outcomes.

Scope for this skill is `memory.read`: extracting user career goals and compensation history from workspace memory.
