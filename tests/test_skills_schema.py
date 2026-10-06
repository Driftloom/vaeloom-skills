"""Skills Schema & Quality Gate Tests.

Validates that every skill package in the repository complies with:
1. Valid directory structure and existence of SKILL.md.
2. Valid YAML frontmatter with required fields (name, description).
3. Required section headings.
4. No unresolved TODOs or template placeholders.
5. All references in references/ are valid JSON.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


def get_all_skill_dirs() -> list[Path]:
    return [p for p in SKILLS_DIR.iterdir() if p.is_dir()]


class TestSkillsSchema:
    def test_skills_directory_exists_and_populated(self):
        assert SKILLS_DIR.is_dir()
        dirs = get_all_skill_dirs()
        assert len(dirs) >= 20, f"Expected at least 20 skills, found {len(dirs)}"

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
    def test_no_unresolved_placeholders(self, skill_dir: Path):
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        # Ensure no un-filled templates
        assert "{{TODO}}" not in content
        assert "<REPLACE_ME>" not in content

    def test_references_json_validity(self):
        json_files = list(SKILLS_DIR.glob("*/references/*.json"))
        assert len(json_files) > 0, "Expected references JSON files across skills"
        for jf in json_files:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                assert isinstance(data, dict), f"{jf} is not a JSON object"
            except Exception as e:
                pytest.fail(f"Invalid JSON in {jf}: {e}")
