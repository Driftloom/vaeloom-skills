"""Tests for the Layer 3 variance analyser.

The analyser exists to stop a noisy number being quoted as a result, so most of
these tests pin the cases where it must refuse to confirm a difference.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.layer3_variance import analyse, seed_scores, weighted_criteria


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
        """One task: the judge said 10 everywhere, the cap put impact at 5."""
        task = make_task("t1", [10] * 3, [10] * 3, [10] * 3,
                         fabrication_by_seed={"0": False, "1": False, "2": False})
        for key, capped in (("truthfulness", 10.0), ("agency", 10.0), ("impact", 5.0)):
            task["criteria"][key]["mean_capped"] = capped
        if include_score:
            task["score"] = round(sum(
                c["mean_capped"] * c["weight"] for c in task["criteria"].values()
                if c["weight"] > 0
            ), 2)
        return task

    def test_fallback_uses_the_capped_mean_not_the_raw_one(self):
        report = make_report([("s", [self._capped_task(include_score=False)])])
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


class TestSeedScoresApplyTheCap:
    """The per-seed view is a second reading of the same scored report.

    It exists to measure seed-to-seed swing, and the swing it reported was
    computed from raw judge samples. A task the harness capped at 5.0 therefore
    read 10.0 here, and this module -- the gate on the signal-versus-noise
    claims -- was reporting a number its own harness never emitted.
    """

    def _task(self, text, *, vetoed=False, capped=True):
        task = make_task("t1", [10] * 3, [10] * 3, [10] * 3, vetoed=vetoed)
        task["candidates"] = {str(s): text for s in range(3)}
        task["fabrication_by_seed"] = {str(s): False for s in range(3)}
        if capped:
            # A capped report carries mean_capped on every criterion; a pre-cap
            # report carries none at all. That is what separates the two, and
            # the cap is applied only to the former.
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
        # 0.5*10 + 0.3*10 (agency uncapped) + 0.2*5 (impact capped)
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

    def test_a_task_with_no_candidates_is_uncapped_not_an_error(self):
        """A minimal fixture has no per-seed text to classify, so no cap. It
        reads uncapped rather than raising, which is the safe direction: the
        seed-to-seed swing is still measurable."""
        task = self._task("cut cycle time by [N] days")
        del task["candidates"]
        assert seed_scores(self._result(task), 3) == [10.0, 10.0, 10.0]


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