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
