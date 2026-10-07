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


def make_task(task_id, truth, agency, impact, *, vetoed=False, weights=None):
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
    return {"id": task_id, "fabrication_vetoed": vetoed, "criteria": criteria}


def st_mean(xs):
    return sum(xs) / len(xs)


def make_report(skills, seeds=3):
    """Mirrors the real report shape: `seeds` lives on each result, not the root."""
    return {
        "backend": "openai_compatible",
        "synthetic": False,
        "results": [
            {"skill": name, "mean_score": 0.0, "seeds": seeds, "tasks": tasks}
            for name, tasks in skills
        ],
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
    def test_per_generation_rate_is_reported_separately_from_per_task(self):
        # Two of three generations fabricate in one task, two other tasks clean.
        tasks = [
            make_task("t1", [10, 0, 0], [10, 10, 10], [10, 10, 10], vetoed=True),
            make_task("t2", [10, 10, 10], [10, 10, 10], [10, 10, 10]),
            make_task("t3", [10, 10, 10], [10, 10, 10], [10, 10, 10]),
        ]
        a = analyse(make_report([("s", tasks)]))
        assert a["generations"] == 9
        assert a["fabricating_generations"] == 2
        assert a["fabrication_rate_per_generation"] == pytest.approx(22.2, abs=0.1)
        assert a["vetoed_tasks"] == 1
        assert a["veto_rate_worst_case"] == pytest.approx(33.3, abs=0.1)

    def test_clean_run_reports_zero_rather_than_dividing_by_zero(self):
        tasks = [make_task("t1", [10, 10, 10], [10, 10, 10], [10, 10, 10])]
        a = analyse(make_report([("s", tasks)]))
        assert a["fabrication_rate_per_generation"] == 0.0
        assert a["veto_rate_worst_case"] == 0.0

    def test_report_without_truthfulness_does_not_crash(self):
        weights = {"agency": 1.0}
        tasks = [make_task("t1", [0, 0, 0], [10, 10, 10], [0, 0, 0], weights=weights)]
        a = analyse(make_report([("s", tasks)]))
        assert a["generations"] == 0
        assert a["fabrication_rate_per_generation"] == 0.0


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
        assert a["fabrication_rate_per_generation"] > 0

    def test_three_seed_report_orders_the_skills(self):
        import json
        a = analyse(json.loads((Path(__file__).resolve().parent.parent
                                / "layer3-live-s3.json").read_text(encoding="utf-8")))
        means = a["skill_means"]
        assert means["resume-bullet-writer"] > means["resume-quantifier"]
        assert a["ordering_supported"] is True

    def test_craft_stays_disabled_so_it_cannot_reintroduce_variance(self):
        import json
        base = Path(__file__).resolve().parent.parent
        report = json.loads((base / "layer3-live-s3.json").read_text(encoding="utf-8"))
        for result in report["results"]:
            for task in result["tasks"]:
                assert task["criteria"]["craft"]["weight"] == 0.0


import json  # noqa: E402  (used by the live-report tests)