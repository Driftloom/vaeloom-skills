"""Skill Executable Helper Scripts Integration Tests.

Verifies that the standalone Python utility scripts inside skill packages
execute reliably, correctly detect violations, and return expected outputs.
"""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Import skill scripts dynamically
sys.path.insert(0, str(REPO_ROOT / "skills" / "ats-audit" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "resume-optimization" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "salary-negotiation-playbook" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "star-interview-prep" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "job-discovery-radar" / "scripts"))

from ats_checker import check_ats_compliance
from xyz_scorer import score_bullet
from comp_calculator import calculate_total_comp
from star_validator import audit_star_story
from portal_scanner import analyze_career_url


class TestSkillScripts:
    def test_ats_checker_clean_document(self):
        doc = """# Jane Doe
San Francisco, CA • jane@example.com • (555) 123-4567 • linkedin.com/in/janedoe

## PROFESSIONAL EXPERIENCE
Acme Corp — Senior Systems Engineer
01/2022 – Present
- Architected distributed data pipeline.

## EDUCATION
UC Berkeley — BS CS
"""
        result = check_ats_compliance(doc)
        assert result["status"] == "PASS"
        assert result["score"] >= 80
        assert len(result["violations"]) == 0

    def test_ats_checker_detects_table_hazard(self):
        doc = """# Jane Doe
| Skill | Level |
| --- | --- |
| Python | Expert |
| AWS | Senior |
"""
        result = check_ats_compliance(doc)
        assert result["score"] < 80
        assert any(v["type"] == "TABLE_LAYOUT_DETECTED" for v in result["violations"])

    def test_xyz_scorer_weak_vs_strong(self):
        weak = "Responsible for helping the team with the website checkout flow."
        weak_res = score_bullet(weak)
        assert weak_res["rating"] == "NEEDS_REVISION"
        assert weak_res["score"] < 65
        assert weak_res["has_metric"] is False

        strong = (
            "Architected high-throughput idempotency layer, reducing payment latency "
            "by 38% and dropping error rates by 14% across 2.4M users using FastAPI and Redis."
        )
        strong_res = score_bullet(strong)
        assert strong_res["rating"] == "EXCELLENT"
        assert strong_res["score"] >= 85
        assert strong_res["has_metric"] is True

    def test_comp_calculator(self):
        res = calculate_total_comp(
            base=160000.0,
            bonus_pct=15.0,
            rsu_grant_value=200000.0,
            vesting_years=4.0,
            signing_bonus=25000.0,
        )
        ann = res["annualized"]
        # Expected: base 160k + bonus 24k + equity 50k + signing 25k = 259,000
        assert ann["year_1_total_compensation"] == 259000.0
        assert ann["steady_state_total_compensation"] == 234000.0

    def test_star_validator_detects_we_trap(self):
        story = """
        Situation: We had a massive database outage during sale week.
        Task: Our team was tasked with fixing the query bottleneck.
        Action: We decided to scale the cluster and we added indexes together.
        Result: We reduced query load by 50% and we fixed the website.
        """
        res = audit_star_story(story)
        assert res["agency_counts"]["we_trap_detected"] is True
        assert any("We Trap" in iss for iss in res["issues"])

    def test_portal_scanner_identifies_greenhouse(self):
        res = analyze_career_url("https://boards.greenhouse.io/stripe/jobs/12345")
        assert res["platform"] == "Greenhouse"
        assert res["status"] in ("VERIFIED_SAFE", "SSRF_DENIED")
