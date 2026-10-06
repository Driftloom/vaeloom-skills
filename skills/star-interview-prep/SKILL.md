---
name: star-interview-prep
description: Behavioral interview preparation engine transforming candidate experiences into structured, concise Situation-Task-Action-Result (STAR) stories with quantified outcomes.
target_models: [claude, gemma, gpt, qwen]
tools_required: [extract_project_milestones, format_star_story]
tags: [Career, Interview, STAR, Behavioral]
required_scope: memory.read
autonomy: suggest
trust_class: core_trusted
triggers:
  - interview prep
  - star story
  - behavioral interview
  - mock interview
---

# STAR Interview Story Prep

## Mission
Prepare candidates for rigorous behavioral interviews by distilling verified project work into structured, compelling Situation-Task-Action-Result (STAR) stories calibrated for 90-second delivery.

## Operating Rules
1. Ingest candidate project artifacts and verified work history, mapping key milestones across core behavioral competencies (Leadership, Complexity, Conflict, Failure & Growth).
2. Structure every story using the strict STAR framework: Situation (15s context), Task (15s ownership), Action (45s specific personal actions), and Result (15s quantified outcome).
3. Ensure the Action component focuses unambiguously on candidate individual contributions rather than diffuse team actions, highlighting technical decision tradeoffs.
4. Conclude every narrative with measurable business impact (latency cut, dollars saved, users onboarded) and a reflective learning synthesis.
5. Provide a 60-second condensed elevator version and high-yield follow-up talking points for each banked story.
6. Prepare strategic, high-signal reverse questions tailored for engineering hiring managers, technical peers, and executive leaders.

## Triggers
Use when the request contains interview prep, star story, behavioral interview, or mock interview.

## Output Contract
Markdown story bank detailing question prompt, 90-second STAR narrative script, key metrics emphasized, and tailored reverse questions for the interviewer. Scope for this skill is `memory.read`.
