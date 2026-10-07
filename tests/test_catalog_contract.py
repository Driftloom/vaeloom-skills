"""The declared two-tier contract must stay internally consistent.

``catalog_contract.json`` declares which skills live only in this repo and which
live only in the app catalog. ``scripts/check_catalog_fidelity.py`` compares
reality against that declaration and fails on any difference.

A declared contract that is wrong is worse than none: it would make the gate
green while documenting a state that does not exist. These tests check the
declaration against this repo, without needing the app.

See ``docs/two-tier-skill-contract.md`` for why the two tiers exist at all.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
CONTRACT = REPO_ROOT / "catalog_contract.json"
SCRIPT = REPO_ROOT / "scripts" / "check_catalog_fidelity.py"


def _contract() -> dict:
    assert CONTRACT.is_file(), f"missing {CONTRACT.name}"
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _repo_skills() -> set[str]:
    return {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}


def test_contract_file_exists_and_is_an_object() -> None:
    _contract()


def test_repo_has_the_expected_number_of_skills() -> None:
    """If this fails, the contract lists were almost certainly not updated."""
    assert len(_repo_skills()) == 33


@pytest.mark.parametrize("key", ["repo_only", "catalog_only"])
def test_declared_list_has_no_duplicates_and_no_overlap(key: str) -> None:
    listed = _contract()[key]["skills"]
    assert len(listed) == len(set(listed)), f"{key} lists a skill twice"
    other = "catalog_only" if key == "repo_only" else "repo_only"
    other_set = set(_contract()[other]["skills"])
    assert not (set(listed) & other_set), (
        f"{key} and {other} overlap; a skill cannot be in both"
    )


@pytest.mark.parametrize("key", ["repo_only", "catalog_only"])
def test_every_declared_skill_is_a_plausible_slug(key: str) -> None:
    for slug in _contract()[key]["skills"]:
        assert slug == slug.strip().lower(), slug
        assert " " not in slug, slug
        assert slug.replace("-", "").isalnum(), slug


def test_repo_only_skills_are_real_skills_in_this_repo() -> None:
    """Every repo_only entry must actually exist here.

    These are the skills that can never reach an agent, because the app catalog
    is the only thing skill_injection reads. A typo would silently drop a real
    skill out of the declared gap.
    """
    repo = _repo_skills()
    listed = set(_contract()["repo_only"]["skills"])
    missing = listed - repo
    assert not missing, f"repo_only lists skills that do not exist here: {sorted(missing)}"


def test_catalog_only_skills_are_not_present_in_this_repo() -> None:
    """App-native skills must genuinely be absent, or the tier boundary is wrong."""
    repo = _repo_skills()
    listed = set(_contract()["catalog_only"]["skills"])
    leaked = listed & repo
    assert not leaked, (
        f"these are declared app-native but exist in this repo: {sorted(leaked)}"
    )


def test_condensed_only_trigger_allowlist_covers_every_shared_skill() -> None:
    """The allowlist names every skill present in both places.

    ``scripts/check_catalog_fidelity.py`` permits the condensed tier to declare
    trigger phrases the full reference does not. This list documents which
    skills currently do; it should be the full shared set, so a newly shared
    skill forces a decision instead of inheriting the exemption silently.
    """
    listed = set(_contract()["condensed_only_triggers"]["skills"])
    assert listed, "allowlist is empty; the exemption would be meaningless"
    assert all(s in _repo_skills() for s in listed), (
        f"allowlist names skills absent from this repo: {sorted(s for s in listed if s not in _repo_skills())}"
    )


def test_script_exists_and_documents_the_contract() -> None:
    assert SCRIPT.is_file(), f"missing {SCRIPT}"
    source = SCRIPT.read_text(encoding="utf-8")
    assert "catalog_contract.json" in source, "script does not read the contract"
    assert "contract_mismatches" in source, "script does not report contract drift"


def test_script_passes_budget_constant_matches_the_app() -> None:
    """The script keeps a local copy of the directive budget.

    It cannot import the app here, so the value is duplicated. This pins the
    local literal and reminds the reader it is a duplicate; the app-side test
    ``test_skill_capacity_selection.py::test_skill_budget_is_the_measured_value``
    pins the real one. If the budget moves, both must move.
    """
    source = SCRIPT.read_text(encoding="utf-8")
    assert "DIRECTIVE_TOKEN_BUDGET = 4000" in source, (
        "update the local budget literal to match "
        "api.services.skill_injection.SKILL_DIRECTIVE_TOKEN_BUDGET"
    )
