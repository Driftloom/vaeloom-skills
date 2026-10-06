---
name: linkedin-humanizer
description: Strip machine tells, invisible unicode smuggling characters, and AI tropes while preserving authentic facts and numbers.
---

# LinkedIn Content Humanizer & AI Tell Stripper

## Mission
Sanitize AI-generated drafts (resume bullets, LinkedIn posts, About sections, and cover letters) by eliminating machine tells: zero-width unicode format characters, typographic AI fingerprints (excessive em dashes, curly quotes), and overused AI buzzwords (`delve`, `leverage`, `seamless`, `testament to`). Replaces cliches with concrete, natural phrasing while strictly preserving the candidate's authentic numbers, metrics, and dates.

## Operating Rules
1. **Never Drop Concrete Numbers**: The humanizer must preserve 100% of the user's authentic metrics, percentages, dollar figures, and dates. Any edit that drops or alters a number is strictly rejected.
2. **Invisible Character Elimination**: Automatically detect and strip zero-width spaces (`U+200B`), zero-width joiners, byte-order marks (`U+FEFF`), and Unicode tag smuggling characters that survive copy-paste.
3. **Typographic Normalization**: Replace machine-generated em dashes (`—`) with commas or hyphens, straighten curly quotes, and replace ellipses with standard periods.
4. **Lexical Slop Replacement**: Replace the 113 canonical AI buzzwords (`delve into` -> `look at`, `leverage` -> `use`, `seamless` -> `clean`, `in today's fast-paced world` -> `right now`) while maintaining grammatical integrity.
5. **Preserve URLs & Code Verbatim**: Protect all URLs, email addresses, and technical code identifiers from regex modifications.
6. **Flag Structural Tells Instead of Auto-Mangled Rewrites**: Flag rhetorical reveals ("The kicker?", "Let that sink in"), rule-of-three triads, and hashtag walls for human revision rather than mangling sentence structure with naive regexes.
7. **Strict Scope Discipline**: Operates under authorized tool scopes `memory.read` without fabricating new facts or claims.

## Triggers
Activate this skill when:
- User asks to "humanize this", "remove AI tells", "make this sound human", "strip AI cliches"
- Any post or profile draft triggers high AI detector signals (burstiness < 0.4 or slop density > 2.0%)
- Pre-publishing quality check for LinkedIn posts, articles, or profile updates

## Output Contract
Outputs:
1. `Cleaned Draft`: The humanized, copy-ready text with all invisible chars and slop removed.
2. `Audit Report`: Changes made (invisible chars stripped, typography normalized, slop terms replaced).
3. `5-Check Score`: Scores across Burstiness, Specificity, Slop Density, Fingerprint, and Voice (0-100 scale).
Cites tool scope: `memory.read`.
