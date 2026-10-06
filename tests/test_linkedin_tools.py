"""Tests for LinkedIn tools, scripts, and validators in vaeloom-skills."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "skills" / "linkedin-profile-optimizer" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "linkedin-interviewer" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "linkedin-humanizer" / "scripts"))

from lib.url_parser import parse_linkedin_url
from headline_lint import lint_headline
from profile_evaluator import evaluate_profile
from story_bank_validator import validate_story_bank
from humanize import pass_invisible, pass_typographic, pass_lexical, load_lexicon
from detect import check_burstiness, check_specificity, check_slop


class TestLinkedInUrlParser:
    def test_parse_activity_url(self):
        url = "https://www.linkedin.com/posts/alex-dev_activity-7448808898326654978-iW20"
        res = parse_linkedin_url(url)
        assert res["url_type"] == "post"
        assert res["post_activity_id"] == "7448808898326654978"
        assert res["post_urn"] == "urn:li:activity:7448808898326654978"

    def test_parse_comment_url(self):
        url = "https://www.linkedin.com/feed/update/urn:li:activity:7448808898326654978?commentUrn=urn%3Ali%3Acomment%3A%28activity%3A7448808898326654978%2C7448809999999999999%29"
        res = parse_linkedin_url(url)
        assert res["url_type"] == "comment"
        assert res["comment_id"] == "7448809999999999999"
        assert "7448808898326654978" in res["comment_urn"]


class TestHeadlineLint:
    def test_strong_headline_passes(self):
        headline = "Staff Software Engineer | Distributed Systems & RAG Platforms | Scaled to $15M ARR"
        res = lint_headline(headline)
        assert res["valid"] is True
        assert res["score"] >= 80
        assert res["length"] <= 220

    def test_buzzword_and_length_violations_detected(self):
        headline = "Passionate and visionary guru looking for exciting synergistic opportunities " * 4
        res = lint_headline(headline)
        assert res["valid"] is False
        assert any("buzzword" in iss.lower() for iss in res["issues"])
        assert any("220 character limit" in iss.lower() for iss in res["issues"])


class TestProfileEvaluator:
    def test_complete_profile_scores_high(self):
        sample = {
            "headline": "Lead Platform Engineer | Kubernetes & Cloud Ops | 99.99% Uptime",
            "about": "Why do 60% of cloud architectures suffer from runaway egress costs?\n\nI architect cloud infrastructure that cuts costs while maintaining high availability.\n\nSpecialties: Kubernetes, Terraform, AWS, Python, Go.\nReach out at lead@example.com",
            "has_custom_banner": True,
            "has_professional_photo": True,
            "featured": ["Asset 1", "Asset 2", "Asset 3"],
            "current_role": {"bullets": ["Automated cluster scaling saving $40k/yr", "Decreased latency by 35%"]},
            "past_roles_count": 2,
            "skills": ["Kubernetes", "AWS", "Terraform", "Python", "Go"],
            "recommendations_count": 3,
            "active_last_7_days": True,
            "has_custom_url": True,
        }
        res = evaluate_profile(sample)
        assert res["total_score"] >= 85
        assert len(res["priority_fixes"]) <= 3

    def test_empty_profile_flags_fixes(self):
        res = evaluate_profile({})
        assert res["total_score"] <= 20
        assert len(res["priority_fixes"]) >= 8


class TestStoryBankValidator:
    def test_valid_story_bank(self):
        text = """
        # Story Bank
        ## Roles & Scopes
        Lead architect at FinTech Corp.
        ## Receipts
        Scaled throughput from 1,000 to 12,000 RPS.
        Reduced costs by 34% ($18k/month).
        Drove $5M ARR expansion.
        ## Turning Points & Scars
        In 2023, an unthrottled consumer caused downtime failure. Rebuilt with Kafka.
        ## Defended Positions
        Monoliths beat microservices for seed stage startups.
        """
        res = validate_story_bank(text)
        assert res["valid"] is True
        assert res["metrics_count"] >= 3

    def test_missing_sections_detected(self):
        text = "Just some random notes with no structured sections."
        res = validate_story_bank(text)
        assert res["valid"] is False
        assert len(res["missing_sections"]) >= 2


class TestHumanizer:
    def test_removes_invisible_characters_and_typography(self):
        lex = load_lexicon()
        # Invisible zero-width space U+200B
        dirty_text = "Clean\u200bText with an em dash \u2014 and curly \u201cquotes\u201d."
        clean, hits = pass_invisible(dirty_text, lex)
        assert "\u200b" not in clean
        assert len(hits) > 0

        clean_typo, typo_hits = pass_typographic(clean, lex)
        assert "\u2014" not in clean_typo
        assert "\u201c" not in clean_typo
        assert "\u201d" not in clean_typo

    def test_lexical_slop_replacement_preserves_numbers(self):
        lex = load_lexicon()
        text = "We leveraged a robust architecture to delve into 47 microservices and cut latency by 35% in Q3."
        clean, hits = pass_lexical(text, lex)
        # Banned terms replaced
        assert "leveraged" not in clean.lower()
        assert "robust" not in clean.lower()
        assert "delve into" not in clean.lower()
        # User's concrete numbers STRICTLY PRESERVED
        assert "47" in clean
        assert "35%" in clean
        assert "Q3" in clean
