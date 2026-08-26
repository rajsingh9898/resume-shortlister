import sys; sys.path.insert(0,'.')
from database import SessionLocal
from models import Candidate, Score, Resume, Evaluation

db = SessionLocal()

for job_id in [6, 7]:
    scores = db.query(Score).filter(Score.job_id == job_id).all()
    print(f"Job {job_id} has {len(scores)} scores:")
    for s in scores:
        cand = db.query(Candidate).filter_by(id=s.candidate_id).first()
        resume = db.query(Resume).filter_by(candidate_id=s.candidate_id).first()
        eval_r = db.query(Evaluation).filter_by(candidate_id=s.candidate_id, job_id=job_id).first()
        cand_name = cand.name if cand else "MISSING"
        has_resume = "YES" if resume else "NO"
        has_eval = "YES" if eval_r else "NO"
        print(f"  Cand {s.candidate_id} ({cand_name}): Resume={has_resume}, Eval={has_eval}")
    print()

db.close()
