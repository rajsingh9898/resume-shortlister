"""
Backfill missing Resume records for candidates that have Scores but no Resume record.
This fixes the JOIN issue where candidates are dropped from the query results.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from models import Candidate, Score, Resume

db = SessionLocal()

# Find all candidates that have scores but no resume records
candidates = db.query(Candidate).all()
fixed = 0

for cand in candidates:
    scores = db.query(Score).filter_by(candidate_id=cand.id).all()
    if not scores:
        continue  # No scores, not relevant
    
    resume = db.query(Resume).filter_by(candidate_id=cand.id).first()
    if resume:
        continue  # Already has a resume record
    
    # This candidate has scores but no resume - find a resume with the same name from another candidate
    # Look for any resume with a matching filename pattern
    similar_resumes = db.query(Resume).all()
    matched_resume = None
    for sr in similar_resumes:
        # Check if the resume filename matches the candidate name pattern
        clean_fn = os.path.splitext(sr.filename)[0].replace('_', ' ').replace('-', ' ').title()
        if clean_fn == cand.name:
            matched_resume = sr
            break
    
    if matched_resume:
        # Create a new resume record for this candidate, copying from the matched one
        new_resume = Resume(
            candidate_id=cand.id,
            filename=matched_resume.filename,
            file_path=matched_resume.file_path,
            raw_text=matched_resume.raw_text or "",
            parsed_skills=matched_resume.parsed_skills
        )
        db.add(new_resume)
        db.commit()
        print(f"  CREATED Resume for Cand {cand.id} ({cand.name}): filename={matched_resume.filename}")
        fixed += 1
    else:
        print(f"  SKIP: Cand {cand.id} ({cand.name}): no matching resume template found")

print(f"\nDone. Created {fixed} missing resume records.")
db.close()
