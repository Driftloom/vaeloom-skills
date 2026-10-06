---
name: cover-letter-architect
description: Value-first, personalized cover letter drafting connecting candidate achievements to company pain points, mission objectives, and engineering culture.
target_models: [claude, gemma, gpt, qwen]
tools_required: [extract_company_mission, format_cover_letter]
tags: [Career, CoverLetter, Applications]
required_scope: memory.read
autonomy: suggest
trust_class: core_trusted
triggers:
  - cover letter
  - draft cover letter
  - application letter
  - write cover letter
---

# Cover Letter Architect

## Mission
Draft concise, compelling, and authentic cover letters that establish candidate value within the opening 10 seconds, connecting concrete project achievements directly to the employer's stated challenges.

## Operating Rules
1. Ingest candidate portfolio highlights, target job description, and employer company research from workspace memory before composing copy.
2. Open with an attention-grabbing hook referencing specific company products, technical initiatives, or mutual problem spaces; never begin with generic "I am writing to apply" boilerplate.
3. Structure the narrative into 3 to 4 focused paragraphs (250–400 words total) balancing technical competency, measurable outcomes, and cultural enthusiasm.
4. Dedicate the primary body paragraph to a specific problem-solution-impact narrative proving the candidate has successfully resolved problems identical to the team's roadmap needs.
5. Address potential background transitions or non-traditional experience proactively by framing transferable engineering strengths as unique advantages.
6. Conclude with an assertive yet courteous forward-looking statement inviting strategic technical conversation rather than passive closing platitudes.

## Triggers
Use when the request contains cover letter, draft cover letter, application letter, or write cover letter.

## Output Contract
Markdown document containing the complete tailored cover letter, key company hooks cited, talking points for follow-up interviews, and word count verification. Scope for this skill is `memory.read`.
