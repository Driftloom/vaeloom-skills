"""Skills Schema & Quality Gate Tests.

Validates that every skill package in the repository complies with:
1. Valid directory structure and existence of SKILL.md.
2. Valid YAML frontmatter with required fields (name, description).
3. Canonical Vaeloom sections (Mission, Operating Rules, Triggers, Output Contract).
4. Sufficient numbered operating rules (>= 3 rules).
5. Explicit citation of valid tool scope (memory.read, memory.write, system.document.compile, system.browser.read).
6. No unresolved TODOs or template placeholders.
7. All references in references/ are valid JSON.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

VALID_SCOPES = frozenset({
    "memory.read",
    "memory.write",
    "system.document.compile",
    "system.browser.read",
    "agent.spawn",
    "workspace.write",
    "connector.read",
})


def get_all_skill_dirs() -> list[Path]:
    return [p for p in SKILLS_DIR.iterdir() if p.is_dir()]


class TestSkillsSchema:
    def test_skills_directory_exists_and_populated(self):
        assert SKILLS_DIR.is_dir()
        dirs = get_all_skill_dirs()
        assert len(dirs) >= 30, f"Expected at least 30 skills, found {len(dirs)}"

    @pytest.mark.parametrize("skill_dir", get_all_skill_dirs(), ids=lambda p: p.name)
    def test_skill_md_present_and_valid_frontmatter(self, skill_dir: Path):
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.is_file(), f"Missing SKILL.md in {skill_dir.name}"

        content = skill_md.read_text(encoding="utf-8")
        assert content.startswith("---"), f"{skill_dir.name}/SKILL.md must start with YAML frontmatter delimiter '---'"

        parts = content.split("---", 2)
        assert len(parts) >= 3, f"{skill_dir.name}/SKILL.md does not have closing '---' delimiter"

        frontmatter = yaml.safe_load(parts[1])
        assert isinstance(frontmatter, dict), f"Frontmatter in {skill_dir.name} is not a valid dictionary"
        assert "name" in frontmatter, f"{skill_dir.name} frontmatter missing 'name'"
        assert "description" in frontmatter, f"{skill_dir.name} frontmatter missing 'description'"
        assert len(frontmatter["description"].strip()) > 10, f"{skill_dir.name} description is too short"

    @pytest.mark.parametrize("skill_dir", get_all_skill_dirs(), ids=lambda p: p.name)
    def test_canonical_sections_present(self, skill_dir: Path):
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        body = parts[2] if len(parts) >= 3 else content

        for sec in ("Mission", "Operating Rules", "Triggers", "Output Contract"):
            assert re.search(r"^##\s+" + re.escape(sec), body, re.IGNORECASE | re.MULTILINE), (
                f"{skill_dir.name}/SKILL.md is missing required section '## {sec}'"
            )

    @pytest.mark.parametrize("skill_dir", get_all_skill_dirs(), ids=lambda p: p.name)
    def test_operating_rules_numbered_and_sufficient(self, skill_dir: Path):
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        lines = content.splitlines()

        count = 0
        in_rules = False
        for line in lines:
            if re.search(r"^##\s+Operating Rules", line, re.IGNORECASE):
                in_rules = True
                continue
            elif in_rules and line.startswith("## "):
                break
            elif in_rules:
                if re.match(r"^\s*\d+[\.\)]\s+", line):
                    count += 1

        assert count >= 3, f"{skill_dir.name}/SKILL.md has only {count} numbered operating rules, requires >= 3"

    @pytest.mark.parametrize("skill_dir", get_all_skill_dirs(), ids=lambda p: p.name)
    def test_scope_discipline_and_citation(self, skill_dir: Path):
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        has_scope = any(scope in content for scope in VALID_SCOPES)
        assert has_scope, f"{skill_dir.name}/SKILL.md does not cite any valid tool scope from {VALID_SCOPES}"

    @pytest.mark.parametrize("skill_dir", get_all_skill_dirs(), ids=lambda p: p.name)
    def test_no_unresolved_placeholders(self, skill_dir: Path):
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        assert "{{TODO}}" not in content
        assert "<REPLACE_ME>" not in content
        assert "<placeholder>" not in content

    def test_references_json_validity(self):
        json_files = list(SKILLS_DIR.glob("*/references/*.json"))
        assert len(json_files) > 0, "Expected references JSON files across skills"
        for jf in json_files:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                assert isinstance(data, dict), f"{jf} is not a JSON object"
            except Exception as e:
                pytest.fail(f"Invalid JSON in {jf}: {e}")
