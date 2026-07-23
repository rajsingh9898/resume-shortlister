import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Base, engine, SessionLocal
from models import Organization, User, Job, Candidate, Resume, Score, Evaluation, AuditLog

def run_db_tests():
    print("--- Starting Database Layer Validation Tests ---")
    
    # 1. Initialize Tables
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Get DB Session
    db = SessionLocal()
    try:
        # 3. Create Org and User
        print("Creating mock organization and user...")
        org = db.query(Organization).filter_by(name="Test Org").first()
        if not org:
            org = Organization(name="Test Org")
            db.add(org)
            db.commit()
            db.refresh(org)
            
        user = db.query(User).filter_by(email="test_user@talentai.local").first()
        if not user:
            user = User(email="test_user@talentai.local", full_name="Test User", organization_id=org.id)
            db.add(user)
            db.commit()
            db.refresh(user)
            
        # 4. Create Job
        print("Creating mock job...")
        job = Job(title="Test Python Developer Job", description="FastAPI, Python, databases requirements.", organization_id=org.id)
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # 5. Create Candidate & Resume
        print("Creating mock candidate and resume...")
        cand = Candidate(name="john_doe_resume.pdf", experience_years=4.5, degrees=["Master"], soft_traits=["Leadership"], organization_id=org.id)
        db.add(cand)
        db.commit()
        db.refresh(cand)
        
        res = Resume(candidate_id=cand.id, filename="john_doe_resume.pdf", file_path="/storage/john_doe_resume.pdf", raw_text="John Doe Python Architect", parsed_skills={"Languages": ["Python"]})
        db.add(res)
        
        # 6. Create Score & Evaluation
        print("Creating mock candidate score and evaluation...")
        score = Score(
            job_id=job.id,
            candidate_id=cand.id,
            match_score=85.0,
            cosine_score=40.0,
            skills_score=90.0,
            experience_score=100.0,
            matched_skills=["Python", "FastAPI"],
            missing_skills=[]
        )
        db.add(score)
        
        evaluation = Evaluation(
            job_id=job.id,
            candidate_id=cand.id,
            status="Shortlisted",
            comments="Excellent Python skills."
        )
        db.add(evaluation)
        db.commit()
        
        # 7. Verification queries
        print("\nVerifying database records...")
        score_db = db.query(Score).filter_by(job_id=job.id, candidate_id=cand.id).first()
        assert score_db is not None, "Score record not found in database"
        assert score_db.match_score == 85.0, f"Expected match score 85.0, got {score_db.match_score}"
        
        eval_db = db.query(Evaluation).filter_by(job_id=job.id, candidate_id=cand.id).first()
        assert eval_db is not None, "Evaluation record not found in database"
        assert eval_db.status == "Shortlisted", f"Expected status Shortlisted, got {eval_db.status}"
        assert eval_db.comments == "Excellent Python skills.", f"Expected comments, got {eval_db.comments}"
        
        print("\nSUCCESS: Database Layer ORM & schema passed all validation tests!")
        
        # Clean up test records (except default seed setup if needed, but let's delete test entries to keep db clean)
        print("Cleaning up test records...")
        db.delete(evaluation)
        db.delete(score)
        db.delete(res)
        db.delete(cand)
        db.delete(job)
        db.delete(user)
        db.delete(org)
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"\nFAILURE: Database validation test crashed: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_db_tests()
