import nlp_engine

def run_tests():
    print("--- Starting NLP Engine Validation Tests ---")
    
    # Mock Job Description
    mock_jd = """
    Looking for a Senior Backend Developer with extensive experience in Python, FastAPI, and Docker.
    Must have hands-on experience with databases such as PostgreSQL or MongoDB.
    Knowledge of CI/CD, Git, and Kubernetes is a big plus. Good communication and leadership skills are desired.
    """
    
    # Mock Resumes
    mock_resumes = [
        {
            "filename": "strong_backend_developer.txt",
            "raw_text": """
            John Doe - Backend Architect
            SKILLS:
            Languages: Python, SQL, JavaScript, Bash
            Frameworks: FastAPI, Flask, Django
            Tools & Databases: Docker, PostgreSQL, Redis, Git, GitLab CI
            Domains: DevOps, System Design, REST APIs, CI/CD
            Soft Skills: Teamwork, Problem Solving, Communication
            
            EXPERIENCE:
            Built high-performance microservices using Python and FastAPI. Dockerized applications and deployed to AWS GCP.
            """
        },
        {
            "filename": "frontend_developer.txt",
            "raw_text": """
            Jane Smith - Senior UI/UX Engineer
            SUMMARY:
            Frontend specialist focusing on React, Angular, and Next.js. Creative designer with a strong passion for CSS and modern layouts.
            
            SKILLS:
            TypeScript, JavaScript, HTML, CSS, TailwindCSS, Bootstrap, React, Vue, jQuery
            Figma, UI/UX, Git, Communication
            
            EXPERIENCE:
            Developed responsive web applications using React and Next.js. Collaborated with teams using Git.
            """
        },
        {
            "filename": "unrelated_accountant.txt",
            "raw_text": """
            Bob Johnson - Certified Public Accountant
            Over 8 years managing audits, payroll, financial spreadsheets, tax reports, and client consultation.
            Proficient in Microsoft Excel, QuickBooks, and financial management tools.
            Highly analytical with great time management and leadership capabilities.
            """
        }
    ]

    print("\nExecuting similarity computations...")
    ranked = nlp_engine.compute_nlp_shortlist(mock_jd, mock_resumes)
    
    print("\nResults Ranks:")
    for rank, candidate in enumerate(ranked, 1):
        print(f"Rank {rank}: {candidate['filename']}")
        print(f"  Match Score: {candidate['score']}%")
        print(f"  Cosine Score: {candidate['cosine_score']}%")
        print(f"  Skills Score: {candidate['skills_score']}%")
        print(f"  Matched Skills: {candidate['matched_skills']}")
        print(f"  Missing Skills: {candidate['missing_skills']}")
        print(f"  Extracted Skills List: {list(candidate['all_extracted_skills'].keys())}")
        print("-" * 40)

    # Verification assertions
    assert len(ranked) == 3, "Should return scores for all 3 mock candidates"
    assert ranked[0]['filename'] == "strong_backend_developer.txt", "Backend candidate should rank 1st"
    assert ranked[1]['filename'] == "frontend_developer.txt", "Frontend candidate should rank 2nd"
    assert ranked[2]['filename'] == "unrelated_accountant.txt", "Accountant should rank last"
    assert ranked[0]['score'] > ranked[1]['score'], "Rank 1 score must be higher than Rank 2"
    assert ranked[1]['score'] > ranked[2]['score'], "Rank 2 score must be higher than Rank 3"
    
    print("\nSUCCESS: NLP Engine passed all validation tests!")

if __name__ == "__main__":
    run_tests()
