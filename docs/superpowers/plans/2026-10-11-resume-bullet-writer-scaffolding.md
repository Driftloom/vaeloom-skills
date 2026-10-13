# Resume-Bullet-Writer Template Scaffold — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `resume-bullet-writer` emitting literal `[X]`/`[Y]`/`[Z]` template slots, and prove it with a live measurement.

**Architecture:** The skill document's bracketed XYZ template is the cause — a model imitates it verbatim. Three edits remove it, add a labelled no-metric example category, and narrow the placeholder language to the distinction the Phase 1 classifier already draws. A static test stops the template returning; a live re-run proves the output changed.

**Tech Stack:** Markdown skill document, Python 3.12, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-11-resume-bullet-writer-scaffolding-design.md`

## Global Constraints

- **Literal `[X]`, `[Y]`, `[Z]` must appear nowhere in `skills/resume-bullet-writer/SKILL.md`** after Task 1. The spec's prose quoting the old text lives in `docs/`, not in the skill.
- The replacement wording for all four edits is **fixed by spec §3.1–§3.3 and must be used verbatim**. Do not paraphrase, extend, or improve it — an earlier draft of the spec kept a trailing `by [Z]` in its own example, which is exactly the defect this phase removes.
- A blank on a **named quantity** (`[N]`, `[M]` on a metric the bullet names) is correct and stays allowed. A blank on a **structural slot** is padding and must be omitted. This is the classifier's distinction, not a blanket placeholder ban.
- `tests/test_resume_skill_fabrication_guard.py` is **rewritten, never deleted or skipped**. A guard removed to permit a change guards nothing after.
- Fabrication staying at **0.0%** is a stop gate, not a target to trade against. If it rises, stop and report — do not adjust the document to recover it.
- No comment or document prose may describe behaviour the code does not have.
- Do not modify `evals/layer3_judge.py`, `evals/layer3_variance.py`, `evals/layer3_tasks.json`, or `skills/resume-quantifier/`. Phase 1's scoring is merged and out of scope.
- Run all commands from the repository root `C:\PROJECTS\PIOS\ClonU\Driftloom\vaeloom-skills`.
- Set `$env:PYTHONDONTWRITEBYTECODE="1"` before Python invocations.

## Review Focus

The spec is a vision document; these are the inputs it implies but no task's tests would otherwise exercise, most likely to bite first.

1. **A skill document that quotes the template while describing it.** Any mention of `[X]`/`[Y]`/`[Z]` — including inside a "this is what not to do" example — reintroduces the copyable pattern. The static test must scan the whole file, not just the rule that changed.
2. **A bullet with no metric at all.** The most likely over-correction. The document must not push the model toward padding every bullet with something, which would trade scaffolding fabrication for a different falsehood. A metric-free bullet must remain a finished answer.
3. **`[N]`/`[M]` surviving in the no-metric example category.** The category shows complete bullets; a blank left in one contradicts its own heading. Every exemplar in it must classify as *named* or carry no slots at all.
4. **A future edit reintroducing `[X]` between live runs.** The static test is cheap and runs without credentials precisely so this cannot wait for the next paid measurement to notice.
5. **The guard test passing vacuously.** Rewriting it can leave a test that reads the document and asserts only that it is a non-empty string. Each assertion must fail if its target string is removed.

---

### Task 1: Remove the template and teach the no-metric case

**Files:**
- Modify: `skills/resume-bullet-writer/SKILL.md` (operating rule 1; the `**Structure:**` line; the `**Examples:**` block; one sentence inside the Decision Rule)
- Test: `tests/test_resume_skill_fabrication_guard.py` (rewrite)

**Interfaces:**
- Consumes: nothing. This is the first task.
- Produces: a document satisfying `classify_placeholders` semantics — no structural slots. Task 2 tests this document against the harness function, so **Task 2 must not change the document's wording.**

- [ ] **Step 1: Write the failing tests**

Rewrite `tests/test_resume_skill_fabrication_guard.py`. Keep its existing module docstring purpose (it guards the Phase 1 fabrication fix) and its existing `doc()` helper; add these tests:

```python
def test_no_literal_template_slots_anywhere_in_the_document() -> None:
    """A mention anywhere reintroduces the copyable pattern, including inside a
    'do not do this' example, so the whole file is scanned rather than the rule
    that changed."""
    text = doc("resume-bullet-writer")
    for slot in ("[X]", "[Y]", "[Z]"):
        assert slot not in text, f"{slot} reintroduces the template the model copies"


def test_the_no_metric_example_category_exists_and_is_labelled() -> None:
    text = doc("resume-bullet-writer")
    assert "Complete without a metric" in text
    assert "These are finished bullets" in text


def test_placeholder_language_distinguishes_named_from_structural() -> None:
    text = doc("resume-bullet-writer")
    assert "A placeholder is a correct answer" not in text, (
        "the unqualified claim contradicts the no-padding rule"
    )
    assert "stands in for a slot" in text
    assert "[N]" in text and "[M]" in text, (
        "named-quantity placeholders stay allowed; the document must still show them"
    )


def test_phase_one_guarantees_survive_the_rewrite() -> None:
    """Collateral-damage check. The rewrite must not quietly drop Phase 1."""
    text = doc("resume-bullet-writer")
    assert "## Decision Rule: No Number Available" in text
    assert "Plausible-sounding ranges" in text
    assert "Unqualified absolutes" in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_resume_skill_fabrication_guard.py -q`
Expected: FAIL — `test_no_literal_template_slots_anywhere_in_the_document` on `[X]`, and the placeholder-language test on the unqualified claim.

- [ ] **Step 3: Apply the four document edits, using spec §3.1–§3.3 verbatim**

**Edit 1 — operating rule 1.** Replace:

> **Strict Google XYZ Architecture:** Format bullets as `'Accomplished [X] as measured by [Y] by doing [Z]'`

with:

> **1. Accomplish, measure, method — only where you have them.** When the material is there, shape the bullet so a reader can see what was accomplished, how it was measured, and by what means. When a part is missing, omit that clause. Do not reserve a slot for data you do not have.

**Edit 2 — the `**Structure:**` line.** Replace the bracketed template with:

> **Structure:** accomplishment, then measurement, then method — in that order, each present only if you have it.

**Edit 3 — the example category.** In the `**Examples:**` block, after the existing metric-rich pairs, add exactly this:

> **Complete without a metric.** These are finished bullets. A result you cannot source is better left out than estimated.
>
> BEFORE: "Helped maintain the customer onboarding flow."
> AFTER: "Led the customer onboarding flow, cutting completion time from [N] to [M] days." Fill in what your records show, or send me the figures and I will.
>
> BEFORE: "Responsible for the payments platform."
> AFTER: "Owned the payments platform end to end, covering uptime, cost and release cadence."

**Edit 4 — the placeholder sentence.** Inside `## Decision Rule: No Number Available`, replace:

> A placeholder is a correct answer. A guess is a defect.

with:

> A placeholder is correct when it marks a quantity you named and do not have a value for — `[N]`, `[M]` on a metric you identified. It is padding when it stands in for a slot in a structure you never filled, and that must be omitted rather than bracketed.

Leave the rest of the Decision Rule, including its three-branch path and worked example, unchanged.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_resume_skill_fabrication_guard.py -q`
Expected: all pass.

- [ ] **Step 5: Negative control — re-insert the template**

Temporarily change operating rule 1 back to the bracketed form, run the command, confirm `test_no_literal_template_slots_anywhere_in_the_document` fails. Restore.

- [ ] **Step 6: Negative control — restore the unqualified placeholder claim**

Temporarily restore *"A placeholder is a correct answer. A guess is a defect."*, run the command, confirm `test_placeholder_language_distinguishes_named_from_structural` fails. Restore.

- [ ] **Step 7: Negative control — delete the example category**

Temporarily remove the `**Complete without a metric.**` block, run the command, confirm `test_the_no_metric_example_category_exists_and_is_labelled` fails. Restore.

- [ ] **Step 8: Run the full suite**

Run: `python -m pytest tests/ -q`
Expected: all green. Baseline is 440.

- [ ] **Step 9: Commit**

```bash
git add skills/resume-bullet-writer/SKILL.md tests/test_resume_skill_fabrication_guard.py
git commit -m "fix(skills): stop resume-bullet-writer handing the model a fillable template

Operating rule 1 read 'Format bullets as Accomplished [X] as measured by [Y] by
doing [Z]'. The model reproduced it slot for slot, connective tissue included --
a document using brackets as notation becomes a template to an imitation-following
model. rbw-train-01 emitted 'improving [X] as measured by [Y] by [Z]' at 6 of 6
placeholders scaffolding.

The bracketed template is gone, stated instead as a shape to satisfy where the
material exists and to omit where it does not.

Metric-free bullets gain their own labelled category, because every existing
example was metric-dense and the prose was losing to the examples. One exemplar
carries [N] and [M] on a named quantity, which stays correct; none carries a
structural slot, because an example that kept one would teach the defect.

The placeholder language is narrowed to the distinction the classifier already
draws. The Phase 1 decision rule and its bans on hedged ranges and unqualified
absolutes are unchanged and pinned.

The guard test is rewritten, not deleted."
```

---

### Task 2: Pin the document's rule to the classifier's actual behaviour

**Files:**
- Test: `tests/test_layer3_placeholder_rules.py` (append)

**Interfaces:**
- Consumes: the Task 1 document; `classify_placeholders(text) -> dict` already in `evals/layer3_judge.py`, returning exactly `{"total", "named", "scaffolded"}`; the module's existing `classify(text)` helper.
- Produces: nothing new. Tests only.

- [ ] **Step 1: Write the tests**

Append to `tests/test_layer3_placeholder_rules.py`:

```python
class TestTheDocumentAndTheClassifierAgree:
    """Spec section 5, criterion 4: the previous branch shipped documentation
    describing a classifier that did not exist. These assert both directions --
    what the document says, and what the code does -- so they cannot drift."""

    @staticmethod
    def _doc() -> str:
        base = Path(__file__).resolve().parent.parent
        return (base / "skills" / "resume-bullet-writer" / "SKILL.md").read_text(
            encoding="utf-8"
        )

    def test_no_document_exemplar_scaffolds(self):
        """Every exemplar the document offers must classify as named or empty.

        This is the one that bites: an example keeping 'by [Z]' teaches the
        defect the phase exists to remove."""
        text = self._doc()
        checked = 0
        for kind in ("BEFORE", "AFTER"):
            for example in re.findall(rf'{kind}: "([^"]+)"', text):
                checked += 1
                got = classify(example.replace("\n", " "))
                assert got["scaffolded"] == 0, f"{kind} scaffolds: {example!r} -> {got}"
        assert checked >= 2, f"no exemplars found; the regex is wrong ({checked})"

    def test_the_named_quantity_exemplar_is_classified_named(self):
        """The document keeps [N]/[M] on a metric it named. If the classifier
        ever called those scaffolding, document and code would describe
        different things."""
        text = self._doc()
        examples = [e.replace("\n", " ") for e in re.findall(r'AFTER: "([^"]+)"', text)]
        target = next((e for e in examples if "[N]" in e), None)
        assert target is not None, "the [N]/[M] exemplar is missing from the document"
        got = classify(target)
        assert got["named"] >= 2, (target, got)
        assert got["scaffolded"] == 0, (target, got)
```

Add `import re` to the module imports if absent. The module already defines
`classify(text)` and imports `Path` and `pytest`.

- [ ] **Step 2: Run the tests**

Run: `python -m pytest tests/test_layer3_placeholder_rules.py -k DocumentAndTheClassifier -q`
Expected: PASS. These assert a property the Task 1 output already satisfies; their purpose is to keep it satisfied.

**If one fails, fix the document, not the test.** A failing assertion means the document is teaching scaffolding — which is the defect, not the expectation.

- [ ] **Step 3: Negative control — prove the control is not vacuous**

Temporarily append `by [Z]` to the `[N]`/`[M]` exemplar in the document, run the same command, and confirm both tests fail. This is what proves the tests would catch a regression rather than passing for an unrelated reason. Restore and re-run to green.

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest tests/ -q`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add tests/test_layer3_placeholder_rules.py
git commit -m "test(evals): the document and the classifier must agree

The previous branch shipped documentation describing a classifier that did not
exist -- [N] and [company] documented as scaffolding while the code returned
named. Nothing asserted the two together.

Every exemplar the skill document offers is now classified by the harness
function and asserted to produce no scaffolding, and the exemplar that keeps
[N]/[M] on a named quantity is asserted to classify as named. Both directions
are pinned, so the document and the code cannot drift apart silently.

Verified non-vacuous: appending 'by [Z]' to the exemplar fails both."
```

---

### Task 3: Regenerate and measure

**Files:**
- Modify (regenerated): `layer3-live-report.json`, `layer3-live-s3.json`
- Modify: `docs/layer3-judging.md`

**Interfaces:**
- Consumes: the Task 1 document; credentials from `..\Vaeloom\.env` (`OLLAMA_BASE_URL`, `OLLAMA_API_KEY`, `OLLAMA_MODEL`).
- Produces: the measurement that decides whether Phase 2 worked. This is the only task that proves it.

- [ ] **Step 1: Confirm the reports are stale before regenerating**

Run: `python evals/layer3_interjudge.py`
Expected: exit code **2**. If it exits 0, the staleness guard has a hole and the rest of this task cannot be trusted — report that rather than continuing.

- [ ] **Step 2: Load credentials**

```powershell
$vals=@{}; Get-Content ..\Vaeloom\.env | ForEach-Object { $l=$_.Trim(); if($l -and -not $l.StartsWith('#') -and $l.Contains('=')){ $k,$v=$l.Split('=',2); $vals[$k.Trim()]=$v.Trim().Trim('"').Trim("'") } }
$base=$vals['OLLAMA_BASE_URL'].TrimEnd('/'); if(-not $base.EndsWith('/v1')){ $base="$base/v1" }
$env:OPENAI_COMPATIBLE_BASE_URL=$base
$env:OPENAI_COMPATIBLE_API_KEY=$vals['OLLAMA_API_KEY']
$env:OPENAI_COMPATIBLE_MODEL=$vals['OLLAMA_MODEL']
```

Never echo a key value.

- [ ] **Step 3: Regenerate the 3-seed report**

Run: `python evals/layer3_judge.py --backend openai_compatible --split all --seeds 3 --json layer3-live-s3.json`
Expected: exit 0, `report written to layer3-live-s3.json`.

- [ ] **Step 4: Regenerate the 1-seed report**

Run: `python evals/layer3_judge.py --backend openai_compatible --split all --seeds 1 --json layer3-live-report.json`
Expected: exit 0.

- [ ] **Step 5: Measure scaffolding per task and compare to the baseline**

Classify every `rbw-*` candidate in the regenerated report with `classify_placeholders` and report `total` and `scaffolded` for each:

| Task | Phase 1 baseline |
|---|---|
| `rbw-train-01` | 6 scaffolded |
| `rbw-train-02` | 2 scaffolded |
| `rbw-held-01` | 2 scaffolded |
| `rbw-held-02` | 0 scaffolded |

**Record the numbers whatever they are.** Zero across all four is the criterion. Non-zero is a finding about the XYZ framing, and spec §7 routes that to a **new spec**, not an extension of this one.

- [ ] **Step 6: STOP GATE — check fabrication**

Run: `python evals/layer3_variance.py layer3-live-s3.json`
Expected: `per generation (mechanical): 0/30 = 0.0%`

**If it is not 0.0%, stop immediately** — no further steps, no commit. The document change made behaviour worse: the model is inventing figures again, which is worse than a flat scaffolding count. Report the number and stop.

- [ ] **Step 7: Update `docs/layer3-judging.md`**

Add the measurement: scaffolding before and after per task, the fabrication rate, and an explicit statement of whether criterion 2 was met. If it was not, say so plainly and name the next suspect the spec identifies — the example set and the XYZ framing.

Keep every existing figure, including the earlier `impact` revert history and the statement that the caps did not improve judge agreement. Then run `python scripts/check_doc_figures.py`; if it reports a figure stale, fix it by reading the regenerated report, **never by relaxing the checker**.

- [ ] **Step 8: Commit**

```bash
git add layer3-live-report.json layer3-live-s3.json docs/layer3-judging.md
git commit -m "fix(skills): measure whether removing the template stopped the scaffolding

Regenerates both live reports after the document change and reports the
scaffolding count per task against the Phase 1 baseline of 6, 2, 2 and 0.

Records the number measured, not the number expected. Zero is the criterion; a
non-zero result is evidence that the XYZ framing rather than the bracketed
template is the driver, which the spec routes to a new specification rather than
an extension of this one.

The mechanical fabrication rate is the stop gate and is reported first."
```