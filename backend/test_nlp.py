import nlp_engine

def run_tests():
    print("--- Starting NLP Engine Phase 8 Validation Tests ---")
    
    # 1. Test basic extraction methods first
    print("\nValidating extraction methods...")
    
    # Test Experience parser
    jd_exp_text = "Looking for a React developer with 3+ years experience and 5 yrs of Docker work"
    extracted_exp = nlp_engine.parse_experience_years(jd_exp_text)
    print(f"Extracted experience (expected max ~5): {extracted_exp}")
    assert extracted_exp == 5.0, "Experience extraction failed to get maximum years from text"
    
    # Test Degree parser
    jd_degree_text = "Must have a Master's degree or PhD in Computer Science and a Bachelor's in engineering."
    extracted_degrees = nlp_engine.parse_education_degrees(jd_degree_text)
    print(f"Extracted degrees (expected Bachelor, Master, PhD): {extracted_degrees}")
    assert "Bachelor" in extracted_degrees, "Bachelor not found in degrees"
    assert "Master" in extracted_degrees, "Master not found in degrees"
    assert "PhD" in extracted_degrees, "PhD not found in degrees"

    # Test Soft Traits parser
    mock_soft_text = "I managed a team of developers and led architecture refactoring sprints using scrum."
    extracted_traits = nlp_engine.parse_soft_traits(mock_soft_text)
    print(f"Extracted soft traits: {extracted_traits}")
    assert "Leadership & Mentorship" in extracted_traits, "Leadership trait not extracted"
    assert "System Design & Architecture" in extracted_traits, "Architecture trait not extracted"
    assert "Agile Delivery & DevOps" in extracted_traits, "Agile trait not extracted"
    
    # 2. Test Combined compute_nlp_shortlist with Synonym mappings
    # Mock Job Description
    mock_jd = """
    Looking for a Senior Backend Developer with 5+ years of experience in Python and FastAPI.
    Must have hands-on experience with databases such as PostgreSQL or MongoDB.
    Knowledge of CI/CD, Git, and Kubernetes is a big plus. A Master's degree or PhD is required.
    """
    
    # Mock Resumes utilizing synonym terms:
    # Postgres is a synonym of PostgreSQL
    # GitHub is a synonym of Git
    # pipelines is a synonym of CI/CD
    # Fast API is a synonym of FastAPI
    mock_resumes = [
        {
            "filename": "strong_backend_developer.txt",
            "raw_text": """
            John Doe - Backend Architect
            SKILLS:
            Languages: Python, SQL
            Frameworks: Fast API, Flask
            Tools & Databases: Docker, Postgres, GitHub
            Domains: DevOps, continuous integration pipelines
            Education:
            PhD in Distributed Systems. Master of Science in CS. B.S. in IT.
            Experience:
            Over 6 years of professional software engineering. I managed a team and mentored juniors.
            """
        },
        {
            "filename": "mid_frontend_developer.txt",
            "raw_text": """
            Jane Smith - UI Engineer
            SUMMARY:
            Frontend specialist focusing on React and Next.js. Creative designer.
            Education:
            Bachelor's degree in Web Development.
            Experience:
            3 years experience in frontend building.
            """
        }
    ]

    print("\nExecuting similarity computations...")
    results = nlp_engine.compute_nlp_shortlist(mock_jd, mock_resumes)
    
    candidates = results["candidates"]
    requirements = results["jd_requirements"]
    
    print(f"\nExtracted JD requirements:")
    print(f"  Skills: {requirements['skills']}")
    print(f"  Exp Required: {requirements['experience_years']} Years")
    print(f"  Degrees Required: {requirements['degrees']}")
    
    assert requirements['experience_years'] == 5.0, "JD Experience required not extracted correctly"
    assert "Master" in requirements['degrees'] and "PhD" in requirements['degrees'], "JD Degrees required not extracted correctly"
    
    print("\nShortlist Results Ranks:")
    for rank, candidate in enumerate(candidates, 1):
        print(f"Rank {rank}: {candidate['filename']}")
        print(f"  Match Score: {candidate['score']}%")
        print(f"  Cosine Score: {candidate['cosine_score']}%")
        print(f"  Skills Score: {candidate['skills_score']}%")
        print(f"  Experience Score: {candidate['experience_score']}%")
        print(f"  Candidate Exp: {candidate['candidate_exp']} years")
        print(f"  Candidate Degrees: {candidate['candidate_degrees']}")
        print(f"  Degree Match: {candidate['degree_match']}")
        print(f"  Matched Skills: {candidate['matched_skills']}")
        print(f"  Missing Skills: {candidate['missing_skills']}")
        print(f"  Soft Traits Extracted: {candidate.get('soft_traits')}")
        print("-" * 40)

    # Verification assertions
    assert len(candidates) == 2, "Should return scores for both mock candidates"
    assert candidates[0]['filename'] == "strong_backend_developer.txt", "Backend candidate should rank 1st"
    
    # Synonym verification assertions
    matched_skills = candidates[0]['matched_skills']
    assert "PostgreSQL" in matched_skills, "Failed to match PostgreSQL from synonym 'Postgres'"
    assert "Git" in matched_skills, "Failed to match Git from synonym 'GitHub'"
    assert "CI/CD" in matched_skills, "Failed to match CI/CD from synonym 'pipelines'"
    assert "FastAPI" in matched_skills, "Failed to match FastAPI from synonym 'Fast API'"

    assert "Leadership & Mentorship" in candidates[0]['soft_traits'], "Soft traits extraction failed"
    
    print("\nSUCCESS: NLP Engine passed all advanced validation tests!")

if __name__ == "__main__":
    run_tests()
