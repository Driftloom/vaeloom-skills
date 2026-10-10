"""The inter-judge tool must refuse to compare reports scored under a different rubric.

This is the guard added after a real false result. The `agency` anchor rewrite
was measured at 0.00 mean divergence -- perfect agreement across all ten
judgements -- because the tool re-judged with the NEW anchors while reading the
primary scores out of a report generated under the OLD ones. The divergence it
reported was the difference between two rubrics, not between two judges.

Re-measured properly, `agency` is 2.50, not 0.00. The rewrite was still an
improvement (7.00 -> 2.50) but the headline it was credited with was false.
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