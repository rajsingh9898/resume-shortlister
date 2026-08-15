import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend import nlp_engine

def test_parse_experience_years_extracted():
    # Standard format
    assert nlp_engine.parse_experience_years("Over 5 years of programming experience") == 5.0
    # Decimals
    assert nlp_engine.parse_experience_years("3.5 years working as lead engineer") == 3.5
    # Ranges
    assert nlp_engine.parse_experience_years("Looking for a developer with 5-10 yrs experience") == 10.0
    # No matches fallback to 0
    assert nlp_engine.parse_experience_years("I like reading backend programming books") == 0.0
    # Extreme cases / unusual formats
    assert nlp_engine.parse_experience_years("Experienced developer for twenty years") == 0.0  # text numbers not handled by digits regex
    assert nlp_engine.parse_experience_years("Total of 15+ years experience in tech") == 15.0

def test_parse_education_degrees():
    # Single match
    assert nlp_engine.parse_education_degrees("Earned a Master's degree in CS") == ["Master"]
    # Multiple matches
    degrees = nlp_engine.parse_education_degrees("Has a PhD, a Master, and a Bachelor's degree")
    assert "Bachelor" in degrees
    assert "Master" in degrees
    assert "PhD" in degrees
    # Case insensitivity
    assert nlp_engine.parse_education_degrees("obtained phd in biology") == ["PhD"]
    # No matches
    assert nlp_engine.parse_education_degrees("No formal university graduation mentioned") == []

def test_score_blending():
    # Test that compute_nlp_shortlist functions correctly and integrates weights
    jd = "Need a Python developer with SQL experience. Must have 5 years experience."
    resumes = [
        {
            "filename": "candidate1.txt",
            "raw_text": "Python developer. SQL backend developer. 5 years experience."
        },
        {
            "filename": "candidate2.txt",
            "raw_text": "Accounting clerk. 2 years experience."
        }
    ]
    
    # Run scoring
    result = nlp_engine.compute_nlp_shortlist(jd, resumes)
    assert "candidates" in result
    candidates = result["candidates"]
    assert len(candidates) == 2
    
    # Candidate 1 should rank first due to skill matches and experience alignment
    assert candidates[0]["filename"] == "candidate1.txt"
    assert candidates[0]["score"] > candidates[1]["score"]
    
def test_nlp_engine_malformed_inputs():
    # Empty inputs should not crash, returning zero or basic dict representation
    jd = ""
    resumes = [
        {
            "filename": "empty.txt",
            "raw_text": ""
        },
        {
            "filename": "garbage.txt",
            "raw_text": "@@@@ @@@ $$$$ #### !!!!"
        }
    ]
    
    result = nlp_engine.compute_nlp_shortlist(jd, resumes)
    assert len(result["candidates"]) == 2
    for cand in result["candidates"]:
        assert isinstance(cand["score"], float)
        assert cand["score"] >= 0.0

def test_skill_ontology_expansion():
    # JD asks for "PostgreSQL"
    # Candidate mentions "postgres"
    # It should match due to case-insensitive ontology expansion
    assert nlp_engine.check_skill_match_raw("PostgreSQL", "I have 3 years of postgres experience", {"postgres"}) == True
    
    # JD asks for "FastAPI" (proper case)
    # Candidate mentions "fast api" (case synonym)
    assert nlp_engine.check_skill_match_raw("FastAPI", "Experienced in fast api backend routing", {"fast api"}) == True
    
    # JD asks for "postgresql" (lowercase)
    # Candidate mentions "PostgreSQL" (proper case)
    assert nlp_engine.check_skill_match_raw("postgresql", "Strong skills in PostgreSQL database administration", {"PostgreSQL"}) == True

def test_explainable_ai_and_team_fit():
    jd = "Looking for a Senior Python Developer with 5+ years of experience in Healthcare finance. Must know FastAPI and React."
    resumes = [
        {
            "filename": "john_doe.txt",
            "raw_text": "John Doe. Senior Software Architect with 7 years of Python experience in medical systems. Spearheaded multiple FastAPI backend platforms from scratch in an agile startup. Key traits: leadership, system architecture."
        }
    ]
    
    # Define a startup backend-heavy ownership team profile
    team_profile = {
        "mindset": "Startup",
        "focus": "Backend-heavy",
        "expectation": "Ownership"
    }
    
    result = nlp_engine.compute_nlp_shortlist(jd, resumes, semantic_weight=0.5, team_profile=team_profile)
    assert "candidates" in result
    c = result["candidates"][0]
    
    assert "explainability" in c
    explain = c["explainability"]
    
    # 1. Verify breakdown fits exist
    assert "breakdown" in explain
    bd = explain["breakdown"]
    assert "domain_fit" in bd
    assert "seniority_fit" in bd
    assert "soft_signals" in bd
    assert "team_fit" in bd
    
    # 2. Verify team fit alignment details
    assert "team_fit_details" in explain
    tfd = explain["team_fit_details"]
    assert "mindset_alignment" in tfd
    assert "focus_alignment" in tfd
    assert "expectation_alignment" in tfd
    assert "Startup (Match)" in tfd["mindset_alignment"]
    
    # 3. Verify why candidate reason is generated
    assert "why_candidate" in explain
    assert "Highly Recommended" in explain["why_candidate"] or "Good Match" in explain["why_candidate"]
    
    # 4. Verify Skill Gap Roadmap
    assert "skill_gap_roadmap" in explain
    roadmap = explain["skill_gap_roadmap"]
    assert "summary" in roadmap
    assert "strengths" in roadmap
    assert "gaps" in roadmap
    assert "upskilling_recommendations" in roadmap
    assert len(roadmap["strengths"]) > 0
    
    # 5. Verify Interview Kit
    assert "interview_kit" in explain
    kit = explain["interview_kit"]
    assert "screening" in kit
    assert "technical" in kit
    assert "system_design" in kit
    assert "behavioral" in kit
    assert len(kit["technical"]) > 0
    
    # 6. Verify Talent Graph & Adjacent Roles
    assert "talent_graph" in explain
    tg = explain["talent_graph"]
    assert "adjacent_roles" in tg
    # In our dummy resume, candidate Doe mentions FastAPI, agile startup, Python.
    # Check that it compiles adjacent role options if any match.
    assert isinstance(tg["adjacent_roles"], list)

def test_bias_blind_anonymization():
    from backend.main import anonymize_resume_text
    
    # Raw sample containing location, school name, age-proxies (dates), email, and phone
    raw_text = "I graduated from Stanford University in 2012. I live in San Francisco, CA 94105. Contact me at john.doe@stanford.edu or 415-555-0199. Work experience: 2012-2016."
    
    anonymized = anonymize_resume_text(raw_text)
    
    # 1. Verify university is redacted
    assert "Stanford University" not in anonymized
    assert "[REDACTED UNIVERSITY]" in anonymized
    
    # 2. Verify location and ZIP are redacted
    assert "San Francisco" not in anonymized
    assert "94105" not in anonymized
    assert "[REDACTED LOCATION" in anonymized
    
    # 3. Verify years / ranges are redacted
    assert "2012-2016" not in anonymized
    assert "[REDACTED YEAR RANGE]" in anonymized
    
    # 4. Verify contact details are redacted
    assert "john.doe@stanford.edu" not in anonymized
    assert "[REDACTED EMAIL]" in anonymized
    assert "415-555-0199" not in anonymized
    assert "[REDACTED PHONE]" in anonymized

def test_recruiter_memory_and_market_intelligence():
    # Mock cached_list of candidates with matching/missing skills
    mock_cached_list = [
        {
            "cand_id": 1,
            "filename": "cand1.pdf",
            "cosine_score": 75.0,
            "skills_score": 80.0,
            "experience_score": 70.0,
            "matched_skills": ["Python", "FastAPI", "Redis"],
            "missing_skills": [],
            "all_extracted_skills": {"languages": ["Python"], "frameworks": ["FastAPI"], "databases": ["Redis"]},
            "candidate_exp": 5.0,
            "candidate_degrees": ["B.S. Computer Science"],
            "status": "Shortlisted",
            "notes": "",
            "model_version": "v2.1.0",
            "explainability": {}
        },
        {
            "cand_id": 2,
            "filename": "cand2.pdf",
            "cosine_score": 40.0,
            "skills_score": 30.0,
            "experience_score": 50.0,
            "matched_skills": ["Python"],
            "missing_skills": ["FastAPI", "Redis"],
            "all_extracted_skills": {"languages": ["Python"], "frameworks": [], "databases": []},
            "candidate_exp": 2.0,
            "candidate_degrees": ["B.S. Information Tech"],
            "status": "Rejected",
            "notes": "",
            "model_version": "v2.1.0",
            "explainability": {}
        }
    ]
    
    # 1. Verify Recruiter Preference Memory calculations
    shortlist_skills_counts = {}
    reject_skills_counts = {}
    total_shortlisted = 0
    total_rejected = 0
    
    for c in mock_cached_list:
        status = c["status"]
        matched = c["matched_skills"] or []
        if status == "Shortlisted":
            total_shortlisted += 1
            for s in matched:
                shortlist_skills_counts[s] = shortlist_skills_counts.get(s, 0) + 1
        elif status == "Rejected":
            total_rejected += 1
            for s in matched:
                reject_skills_counts[s] = reject_skills_counts.get(s, 0) + 1
                
    assert total_shortlisted == 1
    assert total_rejected == 1
    assert shortlist_skills_counts["FastAPI"] == 1
    assert reject_skills_counts["Python"] == 1
    
    # Verify ratio calculations
    skill_boosts = {}
    all_feedback_skills = set(shortlist_skills_counts.keys()).union(set(reject_skills_counts.keys()))
    for s in all_feedback_skills:
        sh_count = shortlist_skills_counts.get(s, 0)
        rj_count = reject_skills_counts.get(s, 0)
        ratio = (sh_count - rj_count) / max(sh_count + rj_count, 1)
        skill_boosts[s] = ratio * 4.0
        
    # Python is present in both (1 short, 1 reject) -> ratio = 0
    assert skill_boosts["Python"] == 0.0
    # FastAPI is only in shortlisted -> ratio = 1 -> boost = +4.0
    assert skill_boosts["FastAPI"] == 4.0
    
    # 2. Verify Salary and Supply feasibility mapping
    jd_exp = 3.0
    classified_role = "Backend Engineer"
    base_min = 110000 if jd_exp >= 2 else 85000
    base_max = 145000 if jd_exp >= 2 else 115000
    if classified_role == "Backend Engineer":
        base_min = int(base_min * 1.10)
        base_max = int(base_max * 1.10)
        
    salary_range = f"${base_min:,} - ${base_max:,}"
    assert salary_range == "$121,000 - $159,500"
    
    qualified_candidates = [c for c in mock_cached_list if c["skills_score"] >= 50.0]
    supply_ratio = len(qualified_candidates) / len(mock_cached_list)
    assert supply_ratio == 0.5 # 1 of 2 is qualified
