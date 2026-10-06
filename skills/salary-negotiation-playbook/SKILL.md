---
name: salary-negotiation-playbook
description: Total compensation negotiation guide, market percentile benchmarking, equity valuation models, and respectful counter-offer scripts for offers and promotions.
target_models: [claude, gemma, gpt, qwen]
tools_required: [benchmark_compensation_tiers, compare_offer_packages]
tags: [Career, Salary, Negotiation, Compensation]
required_scope: memory.read
autonomy: suggest
trust_class: core_trusted
triggers:
  - salary negotiation
  - negotiate offer
  - counter offer
  - compensation benchmark
---

# Salary & Offer Negotiation

## Mission
Equip candidates with data-driven compensation benchmarks, total remuneration models, and respectful negotiation scripts to secure competitive compensation packages without endangering offers.

## Operating Rules
1. Calculate full Total Compensation (TC) across all components: Base Salary, Annual Performance Bonus, Equity Grants (RSUs/Options with vesting schedules), and Benefits value.
2. Establish market percentiles (25th, 50th, 75th, and 90th percentile) using verified compensation data sources (Levels.fyi, Blind) adjusted for geographic tier and role seniority.
3. Formulate polite, persuasive counter-offer emails and live call scripts that lead with genuine role enthusiasm before presenting data-backed asks.
4. Prepare contingency fallback levers when base salary is rigid, including signing bonuses, equity refreshers, accelerated review cycles, remote flexibility, and learning stipends.
5. Provide structured responses for early salary deflection questions, preserving negotiation leverage until written offers are presented.
6. Verify all agreed adjustments are documented in updated written offer letters prior to final candidate signature.

## Triggers
Use when the request contains salary negotiation, negotiate offer, counter offer, or compensation benchmark.

## Output Contract
Markdown negotiation strategy report featuring total compensation breakdown table, market benchmark range, written counter-offer email script, and scenario pushback talking points. Scope for this skill is `memory.read`.
