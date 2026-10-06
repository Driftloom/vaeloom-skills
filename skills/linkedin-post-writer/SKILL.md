---
name: linkedin-post-writer
description: Draft high-agency career and technical LinkedIn posts using 21 proven hook formulas with zero AI cliches.
---

# LinkedIn Post Writer & Career Thought Leadership

## Mission
Draft authentic, high-dwell-time LinkedIn posts showcasing career milestones, technical systems, architecture decisions, and contrarian engineering convictions. Employs 21 battle-tested hook formulas to capture reader attention before the 210-character mobile fold while maintaining zero AI slop, zero fabricated numbers, and a human conversational voice.

## Operating Rules
1. **The Fold is Everything**: Line 1 and 2 must capture the reader's interest before LinkedIn's fold (210 chars on desktop, 140 chars on mobile). Never waste line 1 on pleasantries, setups, or greetings.
2. **Numbers Beat Adjectives**: Specific figures ($14,200, 31%, 47 minutes) must always replace vague qualifiers ("significant cost", "massive growth", "fast deployment").
3. **One Idea Per Post**: Focus strictly on one clear insight or lesson. If an idea requires multiple disparate pivots, split it into separate posts.
4. **Zero AI Cliches**: Never include prohibited tropes ("delve", "leverage", "testament to", "in today's fast-paced world", "game-changer", rocket/fire emoji chains).
5. **No External Links in Body**: Keep external URLs out of the post body to protect reach; instruct links to be placed in the first comment or profile featured section.
6. **Ground in Verified Experience**: Pull real facts, roles, and lessons directly from the candidate's Story Bank or workspace memory vault (`memory.read`). Never fabricate metrics.
7. **Strict Scope Discipline**: Operates under authorized tool scopes `memory.read` and generates candidate-approved copy ready for publication.

## Triggers
Activate this skill when:
- User asks to "write a LinkedIn post", "draft an update about my new project", "share a technical win"
- Candidate wants to build engineering presence or personal branding
- Sharing a career lesson, architecture decision, or milestone

## Output Contract
Outputs:
1. `Selected Hook Formula`: Cites the formula ID and rationale.
2. `Full Post Draft`: Copy-ready post text formatted with whitespace for mobile readability (900-1,300 chars).
3. `First-Comment Call to Action`: Optional link or follow-up question.
Cites tool scope: `memory.read`.
