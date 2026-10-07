"""CI completeness guard.

`pyproject.toml` collects every ``tests/test_*.py`` via ``python_files``, but CI
invokes test files by explicit path. Those two sets drift: a new test file is
collected locally, passes locally, and is never executed by CI -- a green
pipeline that silently stopped testing something.

This module fails the build when a collected test file is not referenced by
`.github/workflows/ci.yml`, so the gap is caught at PR time rather than after a
regression ships unobserved.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
CI_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"

# Matches the *target* of a pytest invocation on a single line, e.g.
#   `pytest tests/ -v`                  -> target "tests/"  (directory form)
#   `pytest tests/test_skills_schema.py` -> target "tests/test_skills_schema.py"
# The target is anchored between the command and its first flag so that
# "pytest tests" cannot match "pytest tests/test_foo.py" -- a substring test here
# makes this guard permanently vacuous.
_PYTEST_TARGET = re.compile(
    r"\bpytest\b\s+(?P<target>[\w./\\-]+)",
    re.IGNORECASE,
)

_LINE_COMMENT = re.compile(r"(?<!#)#.*$")


def _collected_test_files() -> list[Path]:
    # This module is excluded: it is guaranteed to execute whenever pytest
    # collects the suite, so requiring CI to name it would be a false positive.
    self_name = Path(__file__).name
    return [p for p in sorted(TESTS_DIR.glob("test_*.py")) if p.name != self_name]


def _ci_blob() -> str:
    assert CI_PATH.is_file(), f"missing CI workflow: {CI_PATH}"
    return CI_PATH.read_text(encoding="utf-8")


def _ci_covers_whole_tests_dir() -> bool:
    """True when CI runs pytest against the tests directory itself.

    That form covers every collected file, including ones added later, so
    per-file mention is then unnecessary.
    """
    for raw in _ci_blob().splitlines():
        line = _LINE_COMMENT.sub("", raw)
        for match in _PYTEST_TARGET.finditer(line):
            target = match.group("target").replace("\\", "/").rstrip("/")
            if target in {"tests", "test"}:
                return True
    return False


def test_ci_workflow_is_valid_yaml() -> None:
    """A malformed workflow would make every check below vacuous."""
    data = yaml.safe_load(_ci_blob())
    assert isinstance(data, dict), "ci.yml did not parse to a mapping"
    assert "jobs" in data, "ci.yml defines no jobs"


def test_there_are_test_files_to_check() -> None:
    """Guard against the guard silently passing on an empty directory."""
    assert _collected_test_files(), f"no test files found under {TESTS_DIR}"


@pytest.mark.parametrize(
    "test_file",
    _collected_test_files(),
    ids=lambda p: p.name,
)
def test_ci_workflow_runs_this_test_file(test_file: Path) -> None:
    if _ci_covers_whole_tests_dir():
        return
    normalized = test_file.name.replace("\\", "/")
    for raw in _ci_blob().splitlines():
        line = _LINE_COMMENT.sub("", raw)
        if normalized in line.lower():
            return
    pytest.fail(
        f"{test_file.name} is collected by pytest "
        f"(python_files = ['test_*.py']) but is not invoked by {CI_PATH.name}. "
        f"Add a CI step for it, or point one step at the whole tests/ directory."
    )