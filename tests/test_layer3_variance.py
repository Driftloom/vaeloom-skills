"""Tests for the Layer 3 variance analyser.

The analyser exists to stop a noisy number being quoted as a result, so most of
these tests pin the cases where it must refuse to confirm a difference.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.layer3_judge import evaluate_skill
from evals.layer3_variance import (
    CapsNotReproducible, analyse, main, report_is_capped, seed_scores,
    weighted_criteria,
)


WEIGHTED = {"truthfulness": 0.5, "agency": 0.3, "impact": 0.2}


def make_task(task_id, truth, agency, impact, *, vetoed=False, weights=None,
              fabrication_by_seed=None):
    weights = weights or WEIGHTED
    supplied = {"truthfulness": truth, "agency": agency, "impact": impact}
    criteria = {}
    for key, weight in weights.items():
        samples = supplied.get(key, [0, 0, 0])
        criteria[key] = {
            "samples": samples,
            "weight": weight,
            "mean": st_mean(samples),
            "stdev": 0.0,
            "spread": max(samples) - min(samples),
            "unstable": len(set(samples)) > 1,
        }
    task = {"id": task_id, "fabrication_vetoed": vetoed, "criteria": criteria}
    if fabrication_by_seed is not None:
        task["fabrication_by_seed"] = fabrication_by_seed
    return task


def st_mean(xs):
    return sum(xs) / len(xs)


def make_report(skills, seeds=3):
    """Mirrors the real report shape: `seeds` lives on each result, not the root.

    `mean_score` is derived from the tasks rather than stubbed at 0.0, because
    the fabrication-vs-prose gap is a difference against it -- a fixture whose
    mean_score is 0 while its tasks score 10 makes every gap read as zero and
    hides exactly the defect under test.
    """
    results = []
    for name, tasks in skills:
        scores = []
        for t in tasks:
            if t.get("fabrication_vetoed"):
                scores.append(0.0)
            elif "score" in t:
                scores.append(t["score"])
            else:
                scores.append(sum(
                    c["mean"] * c["weight"] for c in t["criteria"].values()
                    if c["weight"] > 0
                ))
        results.append({
            "skill": name,
            "mean_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "seeds": seeds,
            "tasks": tasks,
        })
    return {
        "backend": "openai_compatible",
        "synthetic": False,
        "results": results,
    }


class TestSeedScores:
    def test_mean_is_computed_per_seed(self):
        result = {"tasks": [
            make_task("t1", [10, 0, 0], [10, 0, 0], [10, 0, 0]),
        ]}
        assert seed_scores(result, 3) == pytest.approx([10.0, 0.0, 0.0])

    def test_veto_zeroes_the_task_for_every_seed(self):
        result = {"tasks": [
            make_task("t1", [10, 10, 10], [10, 10, 10], [10, 10, 10], vetoed=True),
        ]}
        assert seed_scores(result, 3) == [0.0, 0.0, 0.0]

    def test_disabled_criteria_are_excluded(self):
        weights = {"truthfulness": 1.0, "craft": 0.0}
        result = {"tasks": [
            make_task("t1", [10, 10, 10], [0, 0, 0], [0, 0, 0], weights=weights),
        ]}
        assert weighted_criteria(result) == ["truthfulness"]
        assert seed_scores(result, 3) == [10.0, 10.0, 10.0]

    def test_weights_are_applied(self):
        weights = {"truthfulness": 0.5, "agency": 0.5}
        result = {"tasks": [
            make_task("t1", [10, 10, 10], [0, 0, 0], [0, 0, 0], weights=weights),
        ]}
        assert seed_scores(result, 3) == [5.0, 5.0, 5.0]


class TestAnalyserAgreesWithTheHarnessOnCaps:
    """The analyser recomputes a task total when a report does not carry one.

    Since the placeholder caps landed, that total is computed from the capped
    criterion values. A fallback still built on the raw mean reports an uncapped
    number, so the analyser and the harness disagree about the same task -- and
    the disagreement is invisible, because the only thing that changed is which
    field a comprehension happens to read.
    """

    def _capped_task(self, *, include_score):
        """One task: the judge said 10 everywhere, the cap put impact at 5.

        Carries `candidates` and `score_by_seed` because evaluate_skill always
        writes both. A capped task without them is a report the analyser now
        refuses to read (see CapsNotReproducible), and a fixture that trips
        that would test the refusal rather than the fallback.
        """
        task = make_task("t1", [10] * 3, [10] * 3, [10] * 3,
                         fabrication_by_seed={"0": False, "1": False, "2": False})
        for key, capped in (("truthfulness", 10.0), ("agency", 10.0), ("impact", 5.0)):
            task["criteria"][key]["mean_capped"] = capped
        task["candidates"] = {str(s): "cut cycle time by [N] days" for s in range(3)}
        task["score_by_seed"] = [9.0, 9.0, 9.0]
        if include_score:
            task["score"] = round(sum(
                c["mean_capped"] * c["weight"] for c in task["criteria"].values()
                if c["weight"] > 0
            ), 2)
        return task

    def test_fallback_uses_the_capped_mean_not_the_raw_one(self):
        task = self._capped_task(include_score=False)
        # Drop the field the harness records, leaving only the compatibility
        # path, so this still tests the recomputation rather than the fast path.
        del task["score_by_seed"]
        report = make_report([("s", [task])])
        a = analyse(report)
        # 0.5*10 + 0.3*10 + 0.2*5 = 9.0. The raw mean would give 10.0.
        assert a["unvetoed_means"]["s"] == pytest.approx(9.0, abs=0.01)

    def test_a_pre_cap_report_still_analyses_on_its_raw_mean(self):
        """A report written before the caps has no mean_capped, and for that
        report the mean IS what the total was computed from. Falling back must
        not require the field, or every committed report stops analysing."""
        task = self._capped_task(include_score=False)
        for crit in task["criteria"].values():
            del crit["mean_capped"]
        report = make_report([("s", [task])])
        a = analyse(report)
        assert a["unvetoed_means"]["s"] == pytest.approx(10.0, abs=0.01)

    def test_a_recorded_score_still_wins_over_any_recomputation(self):
        report = make_report([("s", [self._capped_task(include_score=True)])])
        a = analyse(report)
        assert a["unvetoed_means"]["s"] == pytest.approx(9.0, abs=0.01)


class TestSeedScoresFallbackRecomputesTheCap:
    """The compatibility path: a report written before score_by_seed existed.

    These fixtures deliberately carry no per-seed field, so they reach the
    recomputation. They are here because the two committed reports are in
    exactly this state, and because the recomputation has to stay in step with
    the harness for as long as it is reachable -- the drift this module exists
    to catch is a recomputation that quietly stops agreeing.
    """

    def _task(self, text, *, vetoed=False, capped=True):
        task = make_task("t1", [10] * 3, [10] * 3, [10] * 3, vetoed=vetoed)
        task["candidates"] = {str(s): text for s in range(3)}
        task["fabrication_by_seed"] = {str(s): False for s in range(3)}
        if capped:
            # A capped report carries mean_capped on at least one criterion; a
            # pre-cap report carries none at all. That is what separates the
            # two, and the cap is applied only to the former.
            for key in WEIGHTED:
                task["criteria"][key]["mean_capped"] = 10.0
            task["criteria"]["impact"]["mean_capped"] = 5.0
        return task

    def _result(self, task):
        return {"tasks": [task]}

    def test_a_capped_task_does_not_read_ten_per_seed(self):
        """Judge said 10 on every sample and the output carries a placeholder.

        The harness totals this at 0.5*10 + 0.3*10 + 0.2*5 = 9.0, and impact is
        capped to 5 because of [N]. Reading 10.0 per seed here is the defect.
        """
        text = "cut cycle time by [N] days"
        result = self._result(self._task(text))
        got = seed_scores(result, 3)
        capped_total = sum(
            c["mean_capped"] * c["weight"]
            for c in result["tasks"][0]["criteria"].values() if c["weight"] > 0
        )
        assert capped_total == 9.0
        for score in got:
            assert score <= capped_total, (got, capped_total)
        assert got == [9.0, 9.0, 9.0]

    def test_a_clean_task_is_untouched_by_the_cap(self):
        """The cap must not lower a score that was never capped. A placeholder-
        free output totals 10.0 and has to keep reading 10.0 per seed."""
        got = seed_scores(self._result(self._task("Led the migration.")), 3)
        assert got == [10.0, 10.0, 10.0]

    def test_a_named_placeholder_leaves_agency_alone(self):
        """[N] and [M] are named, so agency keeps full marks and only impact is
        capped. Both halves of the cap rule have to survive into this reading."""
        got = seed_scores(
            self._result(self._task("improving completion rates from [N]% to [M]%")),
            3,
        )
        # 0.5*10 (truthfulness uncapped) + 0.3*10 (agency uncapped) + 0.2*5
        assert got == [9.0, 9.0, 9.0]

    def test_scaffolding_caps_agency_too(self):
        got = seed_scores(
            self._result(self._task("improving [X] as measured by [Y] by [Z]")),
            3,
        )
        # 0.5*10 (truthfulness uncapped) + 0.3*5 + 0.2*5
        assert got == [7.5, 7.5, 7.5]

    def test_the_veto_still_wins_over_the_cap(self):
        """A fabricating task reads 0.0, not 9.0. The cap is a ceiling on a
        criterion; the veto is a stronger claim about the whole task."""
        got = seed_scores(
            self._result(self._task("cut cycle time by [N] days", vetoed=True)), 3
        )
        assert got == [0.0, 0.0, 0.0]

    def test_a_pre_cap_report_is_still_analysed_uncapped(self):
        """The committed reports predate the caps and carry no mean_capped, even
        though their candidates contain placeholders. Analysing them with the cap
        applied would report numbers their harness never produced."""
        result = self._result(self._task("cut cycle time by [N] days", capped=False))
        assert seed_scores(result, 3) == [10.0, 10.0, 10.0]

    def test_the_cap_is_worst_case_across_seeds(self):
        """Seed 0 clean, seed 1 scaffolded: every seed is capped. Applying the
        cap from seed 0 alone would leave seeds 0 and 2 reading 10.0, which is
        the escape the harness aggregation was changed to fix."""
        task = self._task("Led the migration.")
        task["candidates"]["1"] = "improving [X] as measured by [Y] by [Z]"
        got = seed_scores(self._result(task), 3)
        assert got == [7.5, 7.5, 7.5]

    def test_a_capped_task_with_no_candidates_is_refused_not_uncapped(self):
        """Replaces a test that pinned the opposite, and called it safe.

        A capped report whose task carries no per-seed text has nothing the cap
        can be reproduced from. The old behaviour read 10.0 per seed while the
        same task's mean_capped said 5.0 -- this module reporting a number that
        contradicted the report it was analysing, with both looking like ordinary
        scores. Refusing is the only alternative that never emits it.
        """
        task = self._task("cut cycle time by [N] days")
        del task["candidates"]
        # The contradiction the refusal exists to prevent, stated as a fact
        # about the fixture rather than as a sentence in a docstring.
        assert task["criteria"]["impact"]["mean_capped"] == 5.0
        assert task["criteria"]["impact"]["mean"] == 10.0
        with pytest.raises(CapsNotReproducible, match="score_by_seed"):
            seed_scores(self._result(task), 3)

    def test_an_unanalysable_task_stops_the_whole_report(self):
        """A refusal has to reach analyse(), not just seed_scores.

        analyse() calls seed_scores for every skill, so one unreadable task must
        stop the report rather than yield a verdict computed from the tasks that
        happened to be readable.
        """
        task = self._task("cut cycle time by [N] days")
        del task["candidates"]
        with pytest.raises(CapsNotReproducible):
            analyse(make_report([("s", [task])]))

    def test_the_cli_reports_the_refusal_and_exits_non_zero(self, tmp_path, capsys,
                                                             monkeypatch):
        """A refusal that only shows as a non-zero exit code is invisible to
        anyone running this by hand, which is how a number nobody can justify
        would come back as a number."""
        report = {"backend": "b", "synthetic": False, "results": [{
            "skill": "s", "mean_score": 9.0, "seeds": 3,
            "tasks": [self._task("cut cycle time by [N] days")],
        }]}
        del report["results"][0]["tasks"][0]["candidates"]
        path = tmp_path / "unreadable.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["layer3_variance.py", str(path)])
        assert main() == 1
        assert "REFUSING TO ANALYSE" in capsys.readouterr().err


class TestReportIsCapped:
    """report_is_capped decides which reading of a report is the honest one.

    Wrong in the uncapped direction it scores already-capped criteria from their
    raw means; wrong in the capped direction it applies a cap a pre-cap report
    never ran. It is `any`, not `all`, and these pin that on both sides.
    """

    def _result(self, *, capped_keys):
        task = make_task("t1", [10] * 3, [10] * 3, [10] * 3)
        for key in capped_keys:
            task["criteria"][key]["mean_capped"] = task["criteria"][key]["mean"]
        return {"tasks": [task]}

    def test_a_pre_cap_report_is_not_capped(self):
        """A report carrying the field nowhere is uncapped, and for it `mean`
        is what the total was computed from. Every committed report is here."""
        assert report_is_capped(self._result(capped_keys=())) is False

    def test_a_fully_capped_report_is_capped(self):
        assert report_is_capped(self._result(capped_keys=list(WEIGHTED))) is True

    def test_a_half_migrated_report_counts_as_capped(self):
        """Deliberate, and the opposite of what the old docstring claimed.

        The field is written to every criterion or to none, so a partial
        migration cannot come from a single harness version -- but if one is
        ever seen, reading it as uncapped would score the already-capped
        criterion from its raw mean, which is the uncapped number this module
        must never emit. Reading it as capped applies the cap everywhere
        instead, and criteria no cap touched pass through unchanged. `any` is
        chosen for the direction it fails in: a refusal, not a number.
        """
        task = make_task("t1", [10] * 3, [10] * 3, [10] * 3)
        task["candidates"] = {str(s): "cut cycle time by [N] days" for s in range(3)}
        task["criteria"]["impact"]["mean_capped"] = 5.0  # truthfulness/agency bare
        result = {"tasks": [task]}

        assert report_is_capped(result) is True
        assert "mean_capped" not in task["criteria"]["truthfulness"]
        # Capped throughout: impact reads 5.0, the two uncapped criteria read
        # their own 10.0, so 0.5*10 + 0.3*10 + 0.2*5 = 9.0.
        assert seed_scores(result, 3) == [9.0, 9.0, 9.0]


class TestHarnessAndAnalyserAgree:
    """The analyser reports the harness's number rather than rebuilding it.

    Constructed through evaluate_skill and fed to seed_scores, so the agreement
    is demonstrated on a result the harness actually produced rather than assumed
    from both sides importing the same functions.
    """

    SPEC = {"tasks": [{
        "id": "t1", "split": "held_out", "label": "t",
        "input": "Led the migration of the legacy warehouse.",
        "judge_question": "Is the outcome stated?",
        "mechanical_expectations": {"must_not_fabricate": True,
                                    "source_has_no_metric": True},
    }]}

    def _harness_result(self, candidate, scores, criterion="impact"):
        class Backend:
            name, synthetic = "fixed", False

            def generate(self, *, skill_doc, task_input, seed):
                return candidate

            def judge(self, *, task_id, criterion, prompt, seed):
                return {"score": scores[seed], "rationale": "fixed"}

        rubric = {"criteria": [
            {"key": criterion, "label": criterion.capitalize(),
             "weight": 1.0, "anchors": {}},
        ]}
        return evaluate_skill(
            "resume-bullet-writer", self.SPEC, rubric, Backend(), "held_out",
            len(scores),
        )

    def test_seed_scores_reproduces_a_harness_result_exactly(self):
        result = self._harness_result("cut cycle time by [N] days", [10, 10, 4])
        task = result["tasks"][0]
        # The harness capped the mean of [10, 10, 4] to 5.0; per seed the same
        # ceiling gives 5, 5, 4. Two readings, both the harness's.
        assert task["score"] == 5.0
        assert task["score_by_seed"] == [5.0, 5.0, 4.0]
        assert seed_scores(result, 3) == task["score_by_seed"]

    def test_the_analyser_reports_a_harness_number_the_report_does_not_justify(self):
        """The case the recorded field exists for.

        Strip the per-seed text and the report can no longer justify any
        per-seed number, because the cap is derived from that text. The
        recorded field is the only remaining source. If seed_scores recomputed
        instead it would either refuse here or -- without the refusal -- emit
        10.0 against the task's own mean_capped of 5.0.
        """
        result = self._harness_result("cut cycle time by [N] days", [10, 10, 4])
        del result["tasks"][0]["candidates"]
        assert seed_scores(result, 3) == [5.0, 5.0, 4.0]

    def test_a_pre_field_report_still_falls_back(self):
        """The compatibility path, on a real harness result with the field
        removed rather than a hand-built fixture."""
        result = self._harness_result("cut cycle time by [N] days", [10, 10, 4])
        del result["tasks"][0]["score_by_seed"]
        assert seed_scores(result, 3) == [5.0, 5.0, 4.0]

    def test_a_vetoed_task_records_zero_for_every_seed(self):
        result = self._harness_result(
            "cut cycle time by [N] days and cut costs 15-20%", [10, 10, 10])
        task = result["tasks"][0]
        assert task["fabrication_vetoed"] is True
        assert task["score"] == 0.0
        assert task["score_by_seed"] == [0.0, 0.0, 0.0]
        assert seed_scores(result, 3) == [0.0, 0.0, 0.0]

    def test_the_per_seed_view_never_exceeds_the_task_total(self):
        """The cap is a ceiling applied before averaging, so averaging the
        capped samples cannot land above the capped mean. This is the invariant
        that makes `score` and `score_by_seed` two readings of one model rather
        than two answers to one question, and it is why neither may be
        substituted for the other by hand.
        """
        for candidate, scores in (
            ("cut cycle time by [N] days", [10, 10, 4]),
            ("improving [X] as measured by [Y] by [Z]", [10, 0, 6]),
            ("Led the migration of the legacy warehouse.", [10, 10, 10]),
        ):
            result = self._harness_result(candidate, scores)
            task = result["tasks"][0]
            mean_of_seeds = sum(task["score_by_seed"]) / len(task["score_by_seed"])
            assert mean_of_seeds <= task["score"] + 1e-9, (candidate, task)

    def test_the_per_seed_view_and_the_total_are_not_the_same_number(self):
        """Pins the divergence rather than leaving it to be discovered.

        samples [10, 10, 4]: the capped mean is 5.0, the mean of the capped
        samples is 4.67. Both are correct and they are not interchangeable. A
        reader who assumed they were would 'reconcile' a 0.33 gap that is not a
        bug -- which is precisely how this project produced its one false result.
        """
        result = self._harness_result("cut cycle time by [N] days", [10, 10, 4])
        task = result["tasks"][0]
        assert task["criteria"]["impact"]["samples"] == [10, 10, 4]
        assert task["criteria"]["impact"]["mean"] == 8.0
        assert task["criteria"]["impact"]["mean_capped"] == 5.0
        assert task["score"] == 5.0
        assert sum(task["score_by_seed"]) / 3 == pytest.approx(4.67, abs=0.01)

    def test_a_recorded_field_shorter_than_the_seed_count_is_refused(self):
        """A report whose per-seed field cannot answer every seed asked about is
        inconsistent with itself, and reading past its end would be an
        IndexError at best."""
        result = self._harness_result("Led the migration.", [10, 10, 10])
        result["tasks"][0]["score_by_seed"] = [10.0, 10.0]
        with pytest.raises(CapsNotReproducible, match="seed 2"):
            seed_scores(result, 3)


class TestMixedRecordingIsRefused:
    """A task set cannot be half read and half recomputed.

    Whether a task's score comes from the harness or from here is decided per
    task, so a set containing both kinds averages the harness's capped-mean
    model with the per-sample model and reports a number that is neither's.
    Nothing raises, and every task's score looks ordinary.

    Defensive in the strict sense: evaluate_skill writes score_by_seed on every
    task of a report or on none, so no report it produces reaches this. It is
    here so a report edited or truncated into that shape is refused rather than
    analysed.
    """

    def _two_task_result(self):
        """A real two-task harness run, so the mixed shape starts from a
        report the harness could actually have written."""
        class Backend:
            name, synthetic = "fixed", False

            def generate(self, *, skill_doc, task_input, seed):
                return "cut cycle time by [N] days"

            def judge(self, *, task_id, criterion, prompt, seed):
                return {"score": 10, "rationale": "fixed"}

        spec = {"tasks": [
            {"id": t, "split": "held_out", "label": t,
             "input": "Led the migration of the legacy warehouse.",
             "judge_question": "Is the outcome stated?",
             "mechanical_expectations": {"must_not_fabricate": True,
                                         "source_has_no_metric": True}}
            for t in ("t1", "t2")
        ]}
        rubric = {"criteria": [
            {"key": "impact", "label": "Impact", "weight": 1.0, "anchors": {}},
        ]}
        result = evaluate_skill(
            "resume-bullet-writer", spec, rubric, Backend(), "held_out", 3)
        # Precondition: the harness really does write it on every task.
        assert all("score_by_seed" in t for t in result["tasks"])
        return result

    def test_a_set_where_only_some_tasks_record_the_field_is_refused(self):
        result = self._two_task_result()
        # Task 2 loses the field and its text is edited, which is what a
        # truncated or hand-edited report looks like. Recomputing it now yields
        # 10.0, against a task whose own recorded score says 5.0 -- so the
        # blend would report 7.5 for a set whose two tasks both scored 5.0.
        # A number that contradicts the report it came from, from a cause with
        # no symptom.
        assert result["tasks"][1]["score"] == 5.0
        del result["tasks"][1]["score_by_seed"]
        result["tasks"][1]["candidates"] = {
            s: "Led the migration." for s in (0, 1, 2)}
        with pytest.raises(CapsNotReproducible) as exc:
            seed_scores(result, 3)
        message = str(exc.value)
        assert "1 of 2 tasks" in message
        assert "blends" in message

    def test_the_mixed_refusal_reaches_analyse(self):
        result = self._two_task_result()
        del result["tasks"][1]["score_by_seed"]
        with pytest.raises(CapsNotReproducible):
            analyse({"backend": "b", "synthetic": False, "results": [result]})

    def test_a_fully_recorded_set_is_not_refused(self):
        result = self._two_task_result()
        assert seed_scores(result, 3) == [5.0, 5.0, 5.0]

    def test_a_fully_unrecorded_set_is_not_refused(self):
        result = self._two_task_result()
        for task in result["tasks"]:
            del task["score_by_seed"]
        assert seed_scores(result, 3) == [5.0, 5.0, 5.0]

    def test_an_empty_task_set_is_not_mixed(self):
        """Neither recorded nor unrecorded. Not a mix, and the empty-set path
        in seed_scores is left to answer for it."""
        result = self._two_task_result()
        result["tasks"] = []
        assert seed_scores(result, 3) == [0.0, 0.0, 0.0]


class TestCrossSkillMixingIsRefused:
    """A report whose skills were not all scored by the same model is refused.

    `TestMixedRecordingIsRefused` settles the malformation inside one skill.
    One level up it survives that check entirely: each skill is internally
    consistent, and it is only the comparison *between* them that is wrong.
    The blended number is `between_skill_gap`, which is what
    `ordering_supported` and `gap_over_swing` are read from -- so the blend
    decides whether this report claims a ranking.

    Defensive like its per-skill counterpart: `evaluate_skill` writes the field
    on every task of a result or on none, so a report it produced cannot reach
    this. It is here for a report edited, merged or trimmed into that shape.
    """

    def _two_skill_report(self, *, recorded: bool):
        """Two skills from one real harness run, so the mixed shape starts from
        a report the harness could actually have written."""
        result = TestMixedRecordingIsRefused()._two_task_result()
        other = json.loads(json.dumps(result))
        result["skill"] = "resume-bullet-writer"
        other["skill"] = "resume-quantifier"
        if not recorded:
            for task in other["tasks"]:
                del task["score_by_seed"]
                task["candidates"] = {
                    s: "Led the migration." for s in (0, 1, 2)}
        else:
            for task in other["tasks"]:
                task["candidates"] = {
                    s: "cut cycle time by [N] days" for s in (0, 1, 2)}
        return {"backend": "b", "synthetic": False,
                "results": [result, other]}

    def test_one_skill_recorded_and_one_not_is_refused(self):
        report = self._two_skill_report(recorded=False)
        # Precondition: each skill passes its own per-skill check, which is
        # precisely why the blend is invisible without a report-level check.
        assert seed_scores(report["results"][0], 3) == [5.0, 5.0, 5.0]
        assert seed_scores(report["results"][1], 3) == [10.0, 10.0, 10.0]
        with pytest.raises(CapsNotReproducible) as exc:
            analyse(report)
        message = str(exc.value)
        assert "1 of 2 skills" in message
        assert "resume-bullet-writer" in message
        assert "resume-quantifier" in message

    def test_the_blend_would_have_produced_a_gap(self):
        """The refusal has to be worth making: show the wrong number it stops.

        Both skills ran the same tasks with the same judge. The recorded one is
        read at 5.0 per seed, because that is what the harness computed under
        the caps; the unrecorded one is recomputed at 10.0 per seed, because its
        placeholder text was edited away in the trim. A gap between those two
        numbers is a difference between scoring models, not between skills.
        """
        report = self._two_skill_report(recorded=False)
        assert [t["score"] for t in report["results"][0]["tasks"]] == [5.0, 5.0]
        assert [t["score"] for t in report["results"][1]["tasks"]] == [5.0, 5.0]
        harness_model = st_mean(seed_scores(report["results"][0], 3))
        recomputed_model = st_mean(seed_scores(report["results"][1], 3))
        assert harness_model == 5.0
        assert recomputed_model == 10.0, (
            "precondition: the two models must disagree, or the refusal "
            "protects against nothing"
        )

    def test_a_report_where_every_skill_is_recorded_is_not_refused(self):
        report = self._two_skill_report(recorded=True)
        a = analyse(report)
        assert a["between_skill_gap"] == 0.0

    def test_a_report_where_no_skill_is_recorded_is_not_refused(self):
        report = self._two_skill_report(recorded=False)
        for result in report["results"]:
            for task in result["tasks"]:
                task.pop("score_by_seed", None)
                task["candidates"] = {
                    s: "Led the migration." for s in (0, 1, 2)}
        assert analyse(report)["between_skill_gap"] == 0.0

    def test_a_single_skill_report_is_never_cross_skill_mixed(self):
        report = self._two_skill_report(recorded=False)
        report["results"] = report["results"][:1]
        assert analyse(report)["skill_means"]["resume-bullet-writer"] == 5.0

    def test_a_skill_that_is_itself_mixed_gets_the_more_specific_message(self):
        """The per-skill refusal names the tasks, so it must win the tie."""
        report = self._two_skill_report(recorded=True)
        del report["results"][0]["tasks"][1]["score_by_seed"]
        with pytest.raises(CapsNotReproducible) as exc:
            analyse(report)
        assert "1 of 2 tasks" in str(exc.value)

    def test_the_cli_reports_the_cross_skill_refusal(self, tmp_path, capsys):
        report = self._two_skill_report(recorded=False)
        path = tmp_path / "mixed.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "evals" / "layer3_variance.py"), str(path)],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert proc.returncode == 1, proc.stdout + proc.stderr
        assert "REFUSING TO ANALYSE" in proc.stderr
        assert "skills in this report record score_by_seed" in proc.stderr


class TestSignalVersusNoise:
    def test_large_gap_is_supported(self):
        a = analyse(make_report([
            ("high", [make_task("t1", [10, 10, 10], [10, 10, 10], [10, 10, 10])]),
            ("low", [make_task("t1", [0, 0, 0], [0, 0, 0], [0, 0, 0])]),
        ]))
        assert a["ordering_supported"] is True
        assert a["gap_over_swing"] is None  # no seed swing at all

    def test_gap_smaller_than_seed_swing_is_not_supported(self):
        # Mean gap is 10, but each seed swings the full 0-10 range.
        a = analyse(make_report([
            ("noisy-high", [make_task("t1", [10, 0, 10], [10, 0, 10], [10, 0, 10])]),
            ("noisy-low", [make_task("t1", [0, 10, 0], [0, 10, 0], [0, 10, 0])]),
        ]))
        assert a["ordering_supported"] is False

    def test_identical_skills_produce_no_supported_ordering(self):
        tasks = [make_task("t1", [10, 10, 10], [10, 10, 10], [10, 10, 10])]
        a = analyse(make_report([("one", tasks), ("two", tasks)]))
        assert a["between_skill_gap"] == 0.0
        assert a["ordering_supported"] is False

    def test_zero_seed_swing_means_maximal_confidence(self):
        """Zero swing is perfect repeatability, not absence of evidence.

        An earlier version guarded `ordering_supported` on `max_swing` being
        truthy, which reported a perfectly repeatable judge as UNSUPPORTED --
        exactly inverted.
        """
        a = analyse(make_report([
            ("steady", [make_task("t1", [10, 10, 10], [10, 10, 10], [10, 10, 10])]),
            ("flat", [make_task("t1", [0, 0, 0], [0, 0, 0], [0, 0, 0])]),
        ]))
        assert a["max_mean_swing"] == 0.0
        assert a["between_skill_gap"] == 10.0
        assert a["ordering_supported"] is True
        assert a["gap_over_swing"] is None  # a ratio against zero is undefined

    def test_gap_is_measured_against_the_swing_of_the_mean(self):
        """The bug that produced a wrong verdict in the first analysis.

        The gap between two skills must be compared with the seed-to-seed swing
        of each skill's MEAN, never with the 0-10 per-task criterion spread.
        Here the per-task spread is the full 10 for 'spread', yet the mean never
        moves between seeds. Using the spread as the denominator gives
        5 / 10 and declares the difference unresolvable, which is wrong.
        """
        a = analyse(make_report([
            # per-seed means [5, 5, 5]: swing 0. Per-task spread 10.
            ("spread", [
                make_task("t1", [10, 10, 10], [10, 10, 10], [10, 10, 10]),
                make_task("t2", [0, 0, 0], [0, 0, 0], [0, 0, 0]),
            ]),
            # per-seed means [0, 0, 0]: swing 0.
            ("none", [
                make_task("t1", [0, 0, 0], [0, 0, 0], [0, 0, 0]),
                make_task("t2", [0, 0, 0], [0, 0, 0], [0, 0, 0]),
            ]),
        ]))
        # A task-level spread would have been 10; the mean swing is 0.
        assert a["max_mean_swing"] == 0.0
        assert a["between_skill_gap"] == 5.0
        assert a["ordering_supported"] is True

    def test_large_swing_beats_a_small_even_without_task_spread(self):
        """The same gap IS unresolvable when the mean genuinely moves.

        Identical gap of 5.0 as the test above, but reached by seed variation
        rather than task variation. This is the control for the test above: it
        proves the analyser is reading mean swing, not the task count.
        """
        a = analyse(make_report([
            ("noisy", [make_task("t1", [10, 0, 10], [10, 0, 10], [10, 0, 10])]),
            ("quiet", [make_task("t1", [0, 0, 0], [0, 0, 0], [0, 0, 0])]),
        ]))
        assert a["max_mean_swing"] > 0.0
        assert a["ordering_supported"] is False


class TestJudgeConsistency:
    def test_full_range_disagreement_is_counted(self):
        a = analyse(make_report([
            ("s", [make_task("t1", [10, 0, 10], [5, 5, 5], [5, 5, 5])]),
        ]))
        assert a["full_range_disagreements"] == 1
        assert a["full_range_detail"][0]["criterion"] == "truthfulness"
        assert a["full_range_rate"] == pytest.approx(100 / 3, abs=0.1)

    def test_partial_spread_is_not_full_range(self):
        a = analyse(make_report([
            ("s", [make_task("t1", [10, 5, 10], [5, 5, 5], [5, 5, 5])]),
        ]))
        assert a["full_range_disagreements"] == 0

    def test_mean_stdev_alone_would_hide_a_disagreeing_judge(self):
        """A judge scoring 10,10,0 has a large sd and one full-range pair.

        Mean stdev is therefore not sufficient; both are reported so a calm
        average cannot hide a bimodal judge.
        """
        a = analyse(make_report([
            ("stable", [make_task("t1", [10, 10, 10], [10, 10, 10], [10, 10, 10])]),
        ]))
        assert a["full_range_disagreements"] == 0
        assert a["mean_criterion_stdev"] == 0.0

    def test_disabled_criteria_do_not_count_toward_pairs(self):
        weights = {"truthfulness": 1.0, "craft": 0.0}
        a = analyse(make_report([
            ("s", [make_task("t1", [10, 10, 10], [0, 0, 0], [0, 0, 0], weights=weights)]),
        ]))
        assert a["criterion_task_pairs"] == 1


class TestFabricationRates:
    def test_per_generation_rate_is_read_from_the_mechanical_flag(self):
        # Two of three generations fabricate in one task, two other tasks clean.
        # The flag is mechanical; the truthfulness scores are deliberately
        # inconsistent with it to prove they are not the source.
        tasks = [
            make_task("t1", [10, 10, 10], [10, 10, 10], [10, 10, 10], vetoed=True,
                      fabrication_by_seed={"0": False, "1": True, "2": True}),
            make_task("t2", [10, 10, 10], [10, 10, 10], [10, 10, 10],
                      fabrication_by_seed={"0": False, "1": False, "2": False}),
            make_task("t3", [0, 0, 0], [10, 10, 10], [10, 10, 10],
                      fabrication_by_seed={"0": False, "1": False, "2": False}),
        ]
        a = analyse(make_report([("s", tasks)]))
        assert a["generations"] == 9
        assert a["fabricating_generations"] == 2
        assert a["fabrication_rate_per_generation"] == pytest.approx(22.2, abs=0.1)
        assert a["vetoed_tasks"] == 1
        assert a["veto_rate_worst_case"] == pytest.approx(33.3, abs=0.1)
        # t3 scored truthfulness 0 on every seed yet fabricated in none. Counting
        # it would have reported 5 fabrications instead of 2.
        assert a["fabricating_generations"] == 2

    def test_untruthful_prose_is_not_counted_as_fabrication(self):
        """The bug this replaces: a truthfulness score of 0 was treated as
        evidence that a number was invented. Those are different defects -- a
        candidate can be untruthful with no figure in it, and conversely the
        mechanical check is the only one that can see an invented figure the
        judge happened to score 10."""
        tasks = [
            make_task("vague", [0, 0, 0], [10, 10, 10], [0, 0, 0],
                      fabrication_by_seed={"0": False, "1": False, "2": False}),
        ]
        a = analyse(make_report([("s", tasks)]))
        assert a["fabricating_generations"] == 0, "no figure was invented"
        assert a["fabrication_rate_per_generation"] == 0.0

    def test_invented_figure_scored_10_by_the_judge_is_still_fabrication(self):
        tasks = [
            make_task("sneaky", [10, 10, 10], [10, 10, 10], [10, 10, 10],
                      vetoed=True,
                      fabrication_by_seed={"0": True, "1": True, "2": False}),
        ]
        a = analyse(make_report([("s", tasks)]))
        assert a["fabricating_generations"] == 2
        assert a["fabrication_rate_per_generation"] == pytest.approx(66.7, abs=0.1)

    def test_report_without_the_per_seed_flag_is_reported_unmeasurable(self):
        """An older report cannot have its rate guessed at."""
        tasks = [make_task("t1", [10, 0, 0], [10, 10, 10], [10, 10, 10], vetoed=True)]
        a = analyse(make_report([("s", tasks)]))
        assert a["fabrication_inferred_from_truthfulness"] == 3
        assert a["fabrication_rate_per_generation"] is None, (
            "must be unmeasurable, not silently proxied"
        )
        # The worst-case task figure is still available.
        assert a["veto_rate_worst_case"] == 100.0

    def test_clean_run_reports_zero_rather_than_dividing_by_zero(self):
        tasks = [make_task("t1", [10, 10, 10], [10, 10, 10], [10, 10, 10],
                           fabrication_by_seed={"0": False, "1": False, "2": False})]
        a = analyse(make_report([("s", tasks)]))
        assert a["fabrication_rate_per_generation"] == 0.0
        assert a["veto_rate_worst_case"] == 0.0

    def test_report_without_truthfulness_does_not_crash(self):
        weights = {"agency": 1.0}
        tasks = [make_task("t1", [0, 0, 0], [10, 10, 10], [0, 0, 0], weights=weights,
                           fabrication_by_seed={"0": False, "1": False, "2": False})]
        a = analyse(make_report([("s", tasks)]))
        assert a["generations"] == 3
        assert a["fabrication_rate_per_generation"] == 0.0


class TestFabricationIsNotWritingQuality:
    """A vetoed task is pinned to 0 whatever it scored. That conflates two
    different defects, and on the live run the conflation is what the headline
    number was actually measuring."""

    def _skill_report(self, scores, vetoed):
        """One-skill report where each task's score is fully self-consistent.

        `truthfulness` carries the only weight, so its samples ARE the task
        score. That keeps `seed_scores` and the unvetoed mean agreeing, which
        is what makes the comparison between them meaningful.
        """
        weights = {"truthfulness": 1.0}
        tasks = [
            make_task(
                f"t{i}", [score] * 3, [10] * 3, [10] * 3,
                weights=weights, vetoed=vetoed[i],
                fabrication_by_seed={"0": vetoed[i], "1": vetoed[i], "2": vetoed[i]},
            )
            for i, score in enumerate(scores)
        ]
        report = make_report([("s", tasks)])
        assert report["results"][0]["mean_score"] == round(
            sum(0.0 if v else s for s, v in zip(scores, vetoed)) / len(scores), 2
        )
        return report

    def test_perfect_prose_plus_one_veto_is_still_reported_as_poor(self):
        a = analyse(self._skill_report([10.0, 0.0], [False, True]))
        assert a["skill_means"]["s"] == pytest.approx(5.0, abs=0.01)
        assert a["unvetoed_means"]["s"] == pytest.approx(10.0, abs=0.01)
        assert a["overall_minus_unvetoed"]["s"] == pytest.approx(-5.0, abs=0.01)
        assert a["headline_mean_misattributes_fabrication"] is True

    def test_clean_run_reports_no_gap(self):
        a = analyse(self._skill_report([10.0, 8.0], [False, False]))
        assert a["headline_mean_misattributes_fabrication"] is False

    def test_veto_pins_to_zero_however_good_the_prose_was(self):
        # 9/10 prose scores 0 once vetoed. That is the whole point of the split:
        # the headline cannot distinguish "wrote a 9 and invented a number" from
        # "wrote a 0".
        a = analyse(self._skill_report([10.0, 9.0], [False, True]))
        assert a["skill_means"]["s"] == pytest.approx(5.0, abs=0.01)
        assert a["unvetoed_means"]["s"] == pytest.approx(10.0, abs=0.01)
        assert a["overall_minus_unvetoed"]["s"] == pytest.approx(-5.0, abs=0.01)
        assert a["material_fabrication_gaps"] == {"s": -5.0}
        assert a["headline_mean_misattributes_fabrication"] is True

    def test_small_gap_is_not_called_material(self):
        # Nothing vetoed, so the two means average the same task set and the gap
        # is exactly zero. The split only ever opens when the veto fires.
        a = analyse(self._skill_report([10.0, 9.6], [False, False]))
        assert a["unvetoed_task_counts"]["s"] == 2
        assert a["overall_minus_unvetoed"]["s"] == pytest.approx(0.0, abs=1e-9)
        assert a["material_fabrication_gaps"] == {}
        assert a["headline_mean_misattributes_fabrication"] is False

    def test_gap_just_under_the_threshold_is_not_material(self):
        """Pins the 1.0 cutoff from below.

        Two tasks, one vetoed. overall = S/2, unvetoed = S, so the gap is
        -S/2. With S=1.8 that is exactly -0.9: real, but not enough to call the
        headline mean a misreading. If the threshold drifted to 0.5, ordinary
        score variation would be reported as a fabrication defect and send the
        fix at the wrong thing.
        """
        a = analyse(self._skill_report([1.8, 10.0], [False, True]))
        assert a["unvetoed_means"]["s"] == pytest.approx(1.8, abs=0.01)
        assert a["skill_means"]["s"] == pytest.approx(0.9, abs=0.01)
        assert a["overall_minus_unvetoed"]["s"] == pytest.approx(-0.9, abs=0.01)
        assert a["material_fabrication_gaps"] == {}, "0.9 is below the 1.0 cutoff"
        assert a["headline_mean_misattributes_fabrication"] is False

    def test_gap_exactly_at_the_threshold_is_material(self):
        a = analyse(self._skill_report([2.0, 10.0], [False, True]))
        assert a["unvetoed_means"]["s"] == pytest.approx(2.0, abs=0.01)
        assert a["overall_minus_unvetoed"]["s"] == pytest.approx(-1.0, abs=0.01)
        assert a["material_fabrication_gaps"] == {"s": -1.0}
        assert a["headline_mean_misattributes_fabrication"] is True

    def test_fully_vetoed_skill_reports_no_unvetoed_mean(self):
        a = analyse(self._skill_report([0.0, 0.0], [True, True]))
        assert a["unvetoed_means"]["s"] is None
        assert a["unvetoed_task_counts"]["s"] == 0
        assert a["headline_mean_misattributes_fabrication"] is False, (
            "with nothing unvetoed there is no prose quality to misattribute"
        )


class TestRealLiveReports:
    """The shipped reports must stay analysable and keep their conclusions."""

    @pytest.fixture(autouse=True)
    def _reports_exist(self):
        base = Path(__file__).resolve().parent.parent
        for name in ("layer3-live-report.json", "layer3-live-s3.json"):
            path = base / name
            if not path.exists():
                pytest.skip(f"{name} not present")

    def test_one_seed_report_is_analysable(self):
        a = analyse(json.loads((Path(__file__).resolve().parent.parent
                                / "layer3-live-report.json").read_text(encoding="utf-8")))
        assert a["synthetic"] is False
        assert a["seeds"] == 1
        # A 1-seed run records exactly one generation per task, so the
        # per-seed flag is present for every one of them.
        report = json.loads((Path(__file__).resolve().parent.parent
                             / "layer3-live-report.json").read_text(encoding="utf-8"))
        tasks = sum(len(x["tasks"]) for x in report["results"])
        assert a["generations"] == tasks, (a["generations"], tasks)
        assert a["fabrication_inferred_from_truthfulness"] == 0
        assert a["fabricating_generations"] >= 0
        assert a["fabrication_rate_per_generation"] is not None
        assert a["fabrication_rate_per_generation"] >= 0

    def test_three_seed_report_supports_no_skill_ranking(self):
        """It is no longer true that resume-bullet-writer outscores
        resume-quantifier, and a 0.37 gap on 10 tasks could not support a
        ranking either way.

        Under the older `agency` anchors, bullet-writer scored 7.94 against
        quantifier's 6.47, because a strong opening verb was enough for full
        agency marks. Tightening that anchor penalises bullet-writer specifically:
        most of its output is placeholder scaffolding ('improving [X] as measured
        by [Y] by [Z]'), which no longer reads as unmistakable ownership. It now
        scores 6.10, below quantifier's 6.47.

        This test asserts what the data actually supports instead of a ranking
        that flipped when the rubric tightened. Asserting an order here would
        re-introduce exactly the over-claiming this file exists to prevent -- the
        ordering was previously 'supported' only because the anchors were loose
        enough to separate the two.
        """
        import json
        a = analyse(json.loads((Path(__file__).resolve().parent.parent
                                / "layer3-live-s3.json").read_text(encoding="utf-8")))
        means = a["skill_means"]
        for skill, mean in means.items():
            assert mean > 0.0, f"{skill} scored {mean}; a skill should not be at zero"
        gap = a["between_skill_gap"]
        assert gap < 2.0, (
            f"between-skill gap is {gap}, which on 10 tasks with 2 skills is not "
            "enough to rank them; do not assert an ordering"
        )

    def test_fabrication_result_is_the_load_bearing_claim(self):
        """The headline worth pinning is the one measured mechanically, not the
        composite that depends on judge agreement."""
        import json
        a = analyse(json.loads((Path(__file__).resolve().parent.parent
                                / "layer3-live-s3.json").read_text(encoding="utf-8")))
        assert a["fabrication_rate_per_generation"] == 0.0, (
            "the resume skills were fixed to stop inventing figures; if this "
            "regresses the skill-document fix has been undone"
        )
        assert a["veto_rate_worst_case"] == 0.0

    def test_craft_stays_disabled_so_it_cannot_reintroduce_variance(self):
        import json
        base = Path(__file__).resolve().parent.parent
        report = json.loads((base / "layer3-live-s3.json").read_text(encoding="utf-8"))
        for result in report["results"]:
            for task in result["tasks"]:
                assert task["criteria"]["craft"]["weight"] == 0.0


import json  # noqa: E402  (used by the live-report tests)