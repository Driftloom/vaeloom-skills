#!/usr/bin/env python3
"""
profile_evaluator.py - Deterministic 100-point LinkedIn Profile Evaluator.

Scores 12 criteria based on the rubric defined in rubric.json.
Generates an itemized audit, score out of 100, and prioritized action plan.
"""
import json
import os
import re
import sys
from typing import Dict, Any, List

HERE = os.path.dirname(os.path.abspath(__file__))
RUBRIC_PATH = os.path.join(HERE, "..", "references", "rubric.json")

def load_rubric():
    if os.path.exists(RUBRIC_PATH):
        with open(RUBRIC_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"total": 100, "items": []}

def evaluate_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    rubric = load_rubric()
    scores: Dict[str, int] = {}
    feedback: Dict[str, str] = {}
    total_score = 0

    # 1. Headline (max 12 pts)
    headline = str(profile_data.get("headline", "")).strip()
    hl_pts = 0
    if len(headline) >= 120 and len(headline) <= 220:
        hl_pts += 4
    elif len(headline) > 0 and len(headline) < 120:
        hl_pts += 2
    if "|" in headline or "\u2022" in headline:
        hl_pts += 4
    if re.search(r"\b\d+[%kKmMbB]?\b|\$\d+", headline):
        hl_pts += 4
    scores["headline"] = min(12, hl_pts)
    feedback["headline"] = "Full marks for formula, proof metric, and character budget." if hl_pts >= 12 else "Needs structured value proposition, concrete proof, and >=120 characters."

    # 2. About Open (max 10 pts)
    about = str(profile_data.get("about", "")).strip()
    lines = [line.strip() for line in about.splitlines() if line.strip()]
    first_two = " ".join(lines[:2]) if lines else ""
    ab_open_pts = 0
    if first_two:
        if len(first_two) <= 275 and len(first_two) >= 50:
            ab_open_pts += 4
        if not re.search(r"\b(passionate about|welcome to my profile|hello|hi my name is)\b", first_two.lower()):
            ab_open_pts += 3
        if re.search(r"\?|\b\d+[%kKmM]?\b", first_two):
            ab_open_pts += 3
    scores["about_open"] = min(10, ab_open_pts)
    feedback["about_open"] = "Compelling opening hook within the 265-char mobile fold." if ab_open_pts >= 10 else "Opening must hook the reader before 'see more' without generic greetings."

    # 3. About Body (max 10 pts)
    ab_body_pts = 0
    if len(about) >= 600 and len(about) <= 2000:
        ab_body_pts += 4
    elif len(about) > 0:
        ab_body_pts += 2
    if re.search(r"\b(specialties|skills|stack):", about.lower()):
        ab_body_pts += 3
    if re.search(r"\b(dm|email|reach|contact|connect)\b", about.lower()):
        ab_body_pts += 3
    scores["about_body"] = min(10, ab_body_pts)
    feedback["about_body"] = "Structured narrative with keyword specialties and clear call to action." if ab_body_pts >= 10 else "Add searchable specialties and explicit next-step contact CTA."

    # 4. Featured (max 8 pts)
    featured = profile_data.get("featured", [])
    feat_pts = min(8, len(featured) * 3) if isinstance(featured, list) else (8 if featured else 0)
    scores["featured"] = feat_pts
    feedback["featured"] = "3+ high-impact featured assets." if feat_pts >= 8 else "Add 3 featured items: best post, proof/portfolio link, and booking/contact asset."

    # 5. Banner (max 6 pts)
    has_banner = bool(profile_data.get("has_custom_banner", False))
    scores["banner"] = 6 if has_banner else 0
    feedback["banner"] = "Custom banner with value statement." if has_banner else "Default banner in use. Upload a custom banner with positioning statement."

    # 6. Photo (max 6 pts)
    has_photo = bool(profile_data.get("has_professional_photo", False))
    scores["photo"] = 6 if has_photo else 0
    feedback["photo"] = "Professional headshot configured." if has_photo else "Missing high-res headshot filling ~60% of frame."

    # 7. Current Role (max 10 pts)
    current_role = profile_data.get("current_role", {})
    cr_bullets = current_role.get("bullets", []) if isinstance(current_role, dict) else []
    cr_pts = 0
    if cr_bullets and len(cr_bullets) >= 2:
        cr_pts += 5
        has_metrics = sum(1 for b in cr_bullets if re.search(r"\b\d+[%kKmM]?\b|\$\d+", str(b)))
        if has_metrics >= 2:
            cr_pts += 5
        elif has_metrics >= 1:
            cr_pts += 2
    scores["current_role"] = min(10, cr_pts)
    feedback["current_role"] = "Current role contains quantified outcome achievements." if cr_pts >= 10 else "Add at least 2-3 outcome bullets with verifiable metrics."

    # 8. Experience Depth (max 8 pts)
    roles_count = int(profile_data.get("past_roles_count", 0))
    scores["experience_depth"] = 8 if roles_count >= 2 else (4 if roles_count == 1 else 0)
    feedback["experience_depth"] = "Sufficient role history." if scores["experience_depth"] >= 8 else "Detail at least two past roles."

    # 9. Top Skills (max 6 pts)
    skills = profile_data.get("skills", [])
    skills_count = len(skills) if isinstance(skills, list) else int(skills or 0)
    scores["skills"] = 6 if skills_count >= 5 else (3 if skills_count >= 1 else 0)
    feedback["skills"] = "Top target skills curated." if scores["skills"] >= 6 else "Add target role skills and pin your top 3."

    # 10. Recommendations (max 8 pts)
    recs_count = int(profile_data.get("recommendations_count", 0))
    scores["recommendations"] = 8 if recs_count >= 3 else (recs_count * 2)
    feedback["recommendations"] = "Healthy recommendation social proof (3+)." if scores["recommendations"] >= 8 else f"Only {recs_count} recommendations. Target at least 3 recent outcome-focused recommendations."

    # 11. Activity (max 10 pts)
    has_recent_activity = bool(profile_data.get("active_last_7_days", False))
    scores["activity"] = 10 if has_recent_activity else 0
    feedback["activity"] = "Active within past 7 days." if has_recent_activity else "No recent activity. Post or leave 3 high-signal comments to boost algorithm score."

    # 12. Contact (max 6 pts)
    has_custom_url = bool(profile_data.get("has_custom_url", False))
    scores["contact"] = 6 if has_custom_url else 2
    feedback["contact"] = "Custom vanity URL configured." if has_custom_url else "Claim a clean custom URL (e.g. linkedin.com/in/yourname)."

    total_score = sum(scores.values())

    # Generate prioritized fix-first list
    priority_fixes = []
    for k, v in scores.items():
        max_v = 12 if k == "headline" else (10 if k in ("about_open", "about_body", "current_role", "activity") else (8 if k in ("featured", "experience_depth", "recommendations") else 6))
        gap = max_v - v
        if gap > 0:
            priority_fixes.append({"criteria": k, "lost_points": gap, "action": feedback[k]})
    
    priority_fixes.sort(key=lambda x: x["lost_points"], reverse=True)

    return {
        "total_score": total_score,
        "max_score": 100,
        "criteria_scores": scores,
        "criteria_feedback": feedback,
        "priority_fixes": priority_fixes
    }

if __name__ == "__main__":
    sample = {
        "headline": "Senior Software Engineer | Scalable Distributed Systems | 10M Users",
        "about": "Why do 60% of distributed microservices suffer cascading failures?\n\nI design high-availability backend platforms that handle 50,000+ RPS.\n\nSpecialties: Python, Go, Kubernetes, Kafka, Distributed Systems.\nDM me or reach out at engineer@example.com",
        "has_custom_banner": True,
        "has_professional_photo": True,
        "featured": ["Post 1", "Case Study Link", "Cal.com"],
        "current_role": {"bullets": ["Engineered core payment service handling $20M ARR", "Reduced latency by 45% via Redis caching"]},
        "past_roles_count": 2,
        "skills": ["Python", "Kubernetes", "Distributed Systems", "PostgreSQL", "Go"],
        "recommendations_count": 3,
        "active_last_7_days": True,
        "has_custom_url": True
    }
    result = evaluate_profile(sample)
    print(f"Profile Audit Score: {result['total_score']}/100")
    for fix in result["priority_fixes"]:
        print(f"  [-] {fix['criteria']} (-{fix['lost_points']} pts): {fix['action']}")
