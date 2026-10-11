"""The inter-judge tool must refuse to compare reports that are not current.

This is the guard added after a real false result. The `agency` anchor rewrite
was measured at 0.00 mean divergence -- perfect agreement across all ten
judgements -- because the tool re-judged with the NEW anchors while reading the
primary scores out of a report generated under the OLD ones. The divergence it
reported was the difference between two rubrics, not between two judges.

Re-measured properly, `agency` is 2.50, not 0.00. The rewrite was still an
improvement (7.00 -> 2.50) but the headline it was credited with was false.

That fix left a hole of the same kind. `rubric_fingerprint` hashes the
anchors, so the placeholder caps -- which changed how anchor scores become
reported numbers, with the anchors untouched -- left it identical. A pre-cap
report still looked current: a live run against the committed report expected
exit 2, spent 30 calls and exited 0. `scoring_fingerprint` closes that.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def run_interjudge(report: Path) -> subprocess.CompletedProcess:
    env = {
        **dict(__import__("os").environ),
        "OPENAI_COMPATIBLE_BASE_URL": "",  # never reached; we expect exit 2 first
    }
    return subprocess.run(
        [sys.executable, str(ROOT / "evals" / "layer3_interjudge.py"),
         "--report", str(report)],
        cwd=ROOT, capture_output=True, text=True, env=env,
    )


@pytest.fixture
def spec() -> dict:
    return json.loads((ROOT / "evals" / "layer3_tasks.json").read_text(encoding="utf-8"))


def current_fingerprint(spec: dict) -> str:
    sys.path.insert(0, str(ROOT / "evals"))
    from layer3_judge import rubric_fingerprint
    return rubric_fingerprint(spec["rubric"])


def current_scoring_fingerprint() -> str:
    sys.path.insert(0, str(ROOT / "evals"))
    from layer3_judge import scoring_fingerprint
    return scoring_fingerprint()


def current_report(spec: dict, **overrides) -> dict:
    """A report that is current in every respect the guard checks."""
    return {
        "rubric_fingerprint": current_fingerprint(spec),
        "scoring_fingerprint": current_scoring_fingerprint(),
        "results": [],
        **overrides,
    }


class TestStaleReportIsRefused:
    def test_report_without_a_fingerprint_is_rejected(self, tmp_path: Path, spec) -> None:
        report = tmp_path / "no-fingerprint.json"
        report.write_text(json.dumps({"results": []}), encoding="utf-8")
        result = run_interjudge(report)
        assert result.returncode == 2, result.stdout + result.stderr
        assert "records no rubric_fingerprint" in result.stderr

    def test_report_scored_under_another_rubric_is_rejected(
        self, tmp_path: Path, spec
    ) -> None:
        report = tmp_path / "other-rubric.json"
        report.write_text(
            json.dumps({"rubric_fingerprint": "deadbeefdeadbeef", "results": []}),
            encoding="utf-8",
        )
        result = run_interjudge(report)
        assert result.returncode == 2, result.stdout + result.stderr
        assert "was scored against rubric deadbeefdeadbeef" in result.stderr
        assert current_fingerprint(spec) in result.stderr, (
            "the error must name the current rubric so the fix is obvious"
        )

    def test_the_rejection_explains_the_failure_mode(self, tmp_path: Path) -> None:
        """A bare 'exit 2' teaches nothing. The message must say that comparing
        across rubrics measures the rubric change, not judge disagreement."""
        report = tmp_path / "other-rubric.json"
        report.write_text(
            json.dumps({"rubric_fingerprint": "deadbeefdeadbeef", "results": []}),
            encoding="utf-8",
        )
        result = run_interjudge(report)
        combined = result.stdout + result.stderr
        assert "rubric" in combined.lower()
        assert "judge" in combined.lower()


class TestScoringStalenessIsRefused:
    """The rubric fingerprint is blind to the code that produces the numbers.

    The caps landed with the anchors untouched. `rubric_fingerprint` therefore
    stayed identical across the change and every pre-cap report still looked
    current -- demonstrated live, where a run that was expected to exit 2 spent
    30 calls and exited 0.
    """

    def test_a_report_with_no_scoring_fingerprint_is_rejected(
        self, tmp_path: Path, spec
    ) -> None:
        report = tmp_path / "no-scoring.json"
        report.write_text(
            json.dumps({"rubric_fingerprint": current_fingerprint(spec),
                        "results": []}),
            encoding="utf-8",
        )
        result = run_interjudge(report)
        assert result.returncode == 2, result.stdout + result.stderr
        assert "records no scoring_fingerprint" in result.stderr

    def test_a_report_scored_under_another_scoring_policy_is_rejected(
        self, tmp_path: Path, spec
    ) -> None:
        """The live failure, exactly: matching anchors, stale scoring.

        Without this the tool compares a pre-cap report against a post-cap run
        and reports the policy change as judge disagreement.
        """
        report = tmp_path / "other-scoring.json"
        report.write_text(
            json.dumps({"rubric_fingerprint": current_fingerprint(spec),
                        "scoring_fingerprint": "deadbeefdeadbeef",
                        "results": []}),
            encoding="utf-8",
        )
        result = run_interjudge(report)
        assert result.returncode == 2, result.stdout + result.stderr
        assert "was scored under scoring policy deadbeefdeadbeef" in result.stderr
        assert current_scoring_fingerprint() in result.stderr, (
            "the error must name the current scoring policy so the fix is obvious"
        )

    def test_the_scoring_rejection_names_the_failure_mode(
        self, tmp_path: Path, spec
    ) -> None:
        report = tmp_path / "other-scoring.json"
        report.write_text(
            json.dumps({"rubric_fingerprint": current_fingerprint(spec),
                        "scoring_fingerprint": "deadbeefdeadbeef",
                        "results": []}),
            encoding="utf-8",
        )
        combined = (run_interjudge(report).stdout
                    + run_interjudge(report).stderr)
        assert "anchor" in combined.lower()
        assert "policy change" in combined.lower()

    def test_a_current_report_is_accepted(self, spec) -> None:
        """The accept case, checked without credentials or a single call.

        `provenance_problem` is the seam: through the CLI the next step is a
        live request, so this case is otherwise untestable and the guard could
        only ever be shown refusing.
        """
        sys.path.insert(0, str(ROOT / "evals"))
        from layer3_interjudge import provenance_problem

        assert provenance_problem(
            current_report(spec), spec["rubric"], "current.json"
        ) is None, "a report that is current in both fingerprints must be accepted"


class TestTheTwoFingerprintsAreIndependent:
    """Each must move for its own reason and not for the other's.

    If changing a cap also moved the rubric fingerprint, the second check would
    be redundant; if changing an anchor also moved the scoring one, the first
    would be redundant. Either collapse would leave a hole the other is
    currently covering.
    """

    def _judge_module(self):
        sys.path.insert(0, str(ROOT / "evals"))
        import layer3_judge
        return layer3_judge

    def test_changing_the_cap_moves_only_the_scoring_fingerprint(
        self, spec, monkeypatch
    ) -> None:
        module = self._judge_module()
        rubric_before = module.rubric_fingerprint(spec["rubric"])
        scoring_before = module.scoring_fingerprint()

        monkeypatch.setattr(module, "PLACEHOLDER_CAP", 3.0)
        assert module.scoring_fingerprint() != scoring_before, (
            "moving the cap is a scoring change and must be visible"
        )
        assert module.rubric_fingerprint(spec["rubric"]) == rubric_before, (
            "moving the cap is not a rubric change; the anchors did not move"
        )

    def test_changing_a_classification_trigger_moves_only_the_scoring_fingerprint(
        self, spec, monkeypatch
    ) -> None:
        """The classifier is half the scoring policy, not just the cap.

        Widening the instruction-verb set reclassifies placeholders, which
        changes `agency` scores without touching a single anchor.
        """
        module = self._judge_module()
        rubric_before = module.rubric_fingerprint(spec["rubric"])
        scoring_before = module.scoring_fingerprint()

        monkeypatch.setattr(
            module, "_INSTRUCTION_VERBS", module._INSTRUCTION_VERBS | {"quantify-by"}
        )
        assert module.scoring_fingerprint() != scoring_before
        assert module.rubric_fingerprint(spec["rubric"]) == rubric_before

    def test_changing_an_anchor_moves_only_the_rubric_fingerprint(self, spec) -> None:
        module = self._judge_module()
        rubric = json.loads(json.dumps(spec["rubric"]))
        scoring_before = module.scoring_fingerprint()

        for criterion in rubric["criteria"]:
            criterion["anchors"]["5"] = "A differently worded middle anchor entirely."
        assert module.rubric_fingerprint(rubric) != module.rubric_fingerprint(
            spec["rubric"]
        )
        assert module.scoring_fingerprint() == scoring_before, (
            "rewording an anchor changes no scoring function"
        )


class TestCommittedReportsAreCurrent:
    """The shipped reports must match the shipped rubric, or CI is asserting
    against evidence that no longer exists."""

    @pytest.fixture(autouse=True)
    def _reports_exist(self):
        for name in ("layer3-live-report.json", "layer3-live-s3.json"):
            if not (ROOT / name).is_file():
                pytest.skip(f"{name} not present")

    @pytest.mark.parametrize("name", ["layer3-live-report.json", "layer3-live-s3.json"])
    def test_committed_report_matches_the_current_rubric(self, name: str, spec) -> None:
        report = json.loads((ROOT / name).read_text(encoding="utf-8"))
        assert report.get("rubric_fingerprint"), (
            f"{name} predates the rubric fingerprint; regenerate it"
        )
        assert report["rubric_fingerprint"] == current_fingerprint(spec), (
            f"{name} was scored against a different rubric than the one now in "
            "evals/layer3_tasks.json; re-run layer3_judge.py before trusting "
            "any comparison that uses it"
        )

    @pytest.mark.parametrize("name", ["layer3-live-report.json", "layer3-live-s3.json"])
    def test_the_committed_reports_predate_the_scoring_fingerprint(
        self, name: str, spec
    ) -> None:
        """A known-stale state, asserted rather than left to be discovered.

        Both committed reports were produced before `scoring_fingerprint`
        existed, so neither can show which scoring policy produced its numbers
        -- only which rubric did. `layer3_interjudge.py` therefore refuses them,
        and this test pins that refusal on the real artifacts rather than only
        on synthetic fixtures.

        The fix is regeneration against the live backend:

            python evals/layer3_judge.py --backend openai_compatible \\
                --split all --seeds 3 --json <report>

        which this environment cannot do: it needs credentials and spends a few
        hundred calls. When it is done the report will carry the field, this
        assertion will fail, and the honest response is to delete it -- not to
        loosen it into something that passes either way.

        `layer3_variance.py` is unaffected and keeps analysing these reports.
        It reads the harness's own recorded `score_by_seed` rather than
        recomputing a score through its own model of the caps, so a changed
        policy cannot make it report a number the harness did not produce. The
        inter-judge tool is where the staleness was undetectable, because that
        tool compares two runs rather than reading one.
        """
        report = json.loads((ROOT / name).read_text(encoding="utf-8"))
        assert "scoring_fingerprint" not in report, (
            f"{name} now records a scoring_fingerprint. If it was regenerated "
            "under the current policy, this test is obsolete -- delete it. If "
            "it was hand-stamped instead, the report is now claiming a "
            "provenance it does not have."
        )
        sys.path.insert(0, str(ROOT / "evals"))
        from layer3_interjudge import provenance_problem

        problem = provenance_problem(report, spec["rubric"], name)
        assert problem is not None, (
            "a report with no scoring_fingerprint must be refused"
        )
        assert "no scoring_fingerprint" in problem