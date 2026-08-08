import os
import sys
import datetime
from celery import Celery
from sqlalchemy.orm import Session

# Setup path so imports work correctly inside celery worker process
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.database import SessionLocal
    from backend.models import Job, Candidate, Resume, Score, Evaluation, AuditLog, TaskLifecycle
    from backend import nlp_engine
    from backend.encryption import decrypt_data
except ImportError:
    from database import SessionLocal
    from models import Job, Candidate, Resume, Score, Evaluation, AuditLog, TaskLifecycle
    import nlp_engine
    from encryption import decrypt_data

try:
    from backend.logger import logger
except ImportError:
    from logger import logger

try:
    from backend.config import settings
except ImportError:
    from config import settings

# Initialize Celery app
REDIS_URL = settings.REDIS_URL
celery_app = Celery("talentai_tasks", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

try:
    import redis
    r = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
    r.ping()
    logger.info("Celery broker connected to Redis successfully.")
except Exception as e:
    logger.warning(f"Redis broker connection failed: {e}. Enabling Celery Eager Mode with memory backend fallback.")
    celery_app.conf.broker_url = "memory://"
    celery_app.conf.result_backend = "cache+memory://"
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    celery_app.conf.task_store_eager_result = True

@celery_app.task(bind=True, max_retries=3)
def process_shortlist_task(self, job_id: int, resumes_info: list, semantic_weight: float, user_id: int):
    """Asynchronously parses and ranks candidate resumes for a given Job ID."""
    db = SessionLocal()
    
    # 1. Update task lifecycle status to running
    if self.request.id:
        lifecycle = db.query(TaskLifecycle).filter_by(task_id=self.request.id).first()
        if lifecycle:
            lifecycle.status = "running"
            lifecycle.retry_count = self.request.retries
            db.commit()
            
    try:
        # Load the Job context
        job = db.query(Job).filter_by(id=job_id).first()
        if not job:
            if self.request.id:
                self.update_state(state="FAILED", meta={"message": f"Job context {job_id} not found."})
            return {"error": "Job context not found"}
            
        jd = job.description
        total_files = len(resumes_info)
        
        # 1. Update initial state listing all files as 'pending'
        file_statuses = {res["filename"]: "pending" for res in resumes_info}
        if self.request.id:
            self.update_state(state="PROGRESS", meta={"progress": 0.0, "files": file_statuses})
        
        # 2. Concurrently extract text from files (simulated progress updates)
        resume_data = []
        for idx, res in enumerate(resumes_info):
            filename = res["filename"]
            file_path = res["file_path"]
            
            # Update state to 'processing'
            file_statuses[filename] = "processing"
            progress_pct = (idx / total_files) * 0.5 # Ingest & parsing takes first 50%
            if self.request.id:
                self.update_state(state="PROGRESS", meta={"progress": progress_pct, "files": file_statuses})
            
            # Read and decrypt file contents from disk
            if os.path.exists(file_path):
                try:
                    with open(file_path, "rb") as f:
                        disk_bytes = f.read()
                    file_bytes = decrypt_data(disk_bytes)
                    raw_text = nlp_engine.extract_text(filename, file_bytes)
                except Exception as e:
                    raw_text = f"Error reading/parsing file: {str(e)}"
            else:
                raw_text = f"File not found on disk: {file_path}"
                
            resume_data.append({
                "filename": filename,
                "raw_text": raw_text,
                "file_path": file_path
            })
            
            # Mark file as 'done' for parsing stage
            file_statuses[filename] = "done"
            
        # 3. Execute similarity computing and ranking
        if self.request.id:
            self.update_state(state="PROGRESS", meta={"progress": 0.6, "files": file_statuses})
        results = nlp_engine.compute_nlp_shortlist(jd, resume_data, semantic_weight)
        
        # 4. Save results to DB
        if self.request.id:
            self.update_state(state="PROGRESS", meta={"progress": 0.8, "files": file_statuses})
        
        for cand in results["candidates"]:
            filename = cand["filename"]
            raw_text = next(r["raw_text"] for r in resume_data if r["filename"] == filename)
            file_path = next(r["file_path"] for r in resume_data if r["filename"] == filename)
            
            # Find or create Candidate (scoped under tenant Org)
            candidate = db.query(Candidate).filter_by(name=filename, organization_id=job.organization_id).first()
            if not candidate:
                candidate = Candidate(
                    name=filename,
                    experience_years=cand["candidate_exp"],
                    experience_confidence=cand["experience_confidence"],
                    degrees=cand["candidate_degrees"],
                    degrees_confidence=cand["degrees_confidence"],
                    soft_traits=cand["soft_traits"],
                    organization_id=job.organization_id
                )
                db.add(candidate)
                db.commit()
                db.refresh(candidate)
            else:
                candidate.experience_years = cand["candidate_exp"]
                candidate.experience_confidence = cand["experience_confidence"]
                candidate.degrees = cand["candidate_degrees"]
                candidate.degrees_confidence = cand["degrees_confidence"]
                candidate.soft_traits = cand["soft_traits"]
                db.commit()
                
            # Create or update Resume reference
            resume = db.query(Resume).filter_by(filename=filename).first()
            if not resume:
                resume = Resume(
                    candidate_id=candidate.id,
                    filename=filename,
                    file_path=file_path,
                    raw_text=raw_text,
                    parsed_skills=cand["all_extracted_skills"]
                )
                db.add(resume)
            else:
                resume.file_path = file_path
                resume.raw_text = raw_text
                resume.parsed_skills = cand["all_extracted_skills"]
            db.commit()
            
            # Save Score
            score = Score(
                job_id=job.id,
                candidate_id=candidate.id,
                match_score=cand["score"],
                cosine_score=cand["cosine_score"],
                skills_score=cand["skills_score"],
                experience_score=cand["experience_score"],
                matched_skills=cand["matched_skills"],
                missing_skills=cand["missing_skills"]
            )
            db.add(score)
            db.commit()
            
            # Carry over evaluations
            existing_eval = db.query(Evaluation).join(Candidate).filter(
                Evaluation.candidate_id == candidate.id,
                Candidate.organization_id == job.organization_id
            ).order_by(Evaluation.id.desc()).first()
            
            status = existing_eval.status if existing_eval else "Under Review"
            comments = existing_eval.comments if existing_eval else ""
            
            evaluation = Evaluation(
                job_id=job.id,
                candidate_id=candidate.id,
                status=status,
                comments=comments
            )
            db.add(evaluation)
            db.commit()
            
        # Log to AuditLog
        audit = AuditLog(
            user_id=user_id,
            action="rank_candidates",
            details=f"Ranked {len(resumes_info)} candidates for Job ID {job.id} asynchronously."
        )
        db.add(audit)
        db.commit()
        
        # Clear any cached lookups for this job ID
        try:
            import redis
            redis_client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
            # Find and delete cached pages
            keys = redis_client.keys(f"job_candidates:{job_id}:*")
            if keys:
                redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis invalidation failed during task: {e}")
            
        # Update lifecycle status to success
        if self.request.id:
            lifecycle = db.query(TaskLifecycle).filter_by(task_id=self.request.id).first()
            if lifecycle:
                lifecycle.status = "success"
                db.commit()
                
        return {"success": True, "job_id": job.id}
    except Exception as exc:
        db.rollback()
        # Calculate backoff delay: 10 * (2 ** retries)
        backoff_delay = 10 * (2 ** self.request.retries)
        
        if self.request.retries < self.max_retries:
            logger.warning(f"Task {self.request.id} failed, retrying in {backoff_delay}s. Error: {exc}")
            if self.request.id:
                lifecycle = db.query(TaskLifecycle).filter_by(task_id=self.request.id).first()
                if lifecycle:
                    lifecycle.status = "queued" # Set back to queued/pending for retry
                    lifecycle.retry_count = self.request.retries + 1
                    lifecycle.error_message = f"Retry {self.request.retries + 1}: {str(exc)}"
                    db.commit()
            raise self.retry(exc=exc, countdown=backoff_delay)
        else:
            # Dead-letter handling: Max retries exceeded
            logger.error(f"Task {self.request.id} failed permanently after {self.request.retries} retries: {exc}")
            if self.request.id:
                lifecycle = db.query(TaskLifecycle).filter_by(task_id=self.request.id).first()
                if lifecycle:
                    lifecycle.status = "failed"
                    lifecycle.error_message = f"Failed permanently after max retries. Error: {str(exc)}"
                    db.commit()
            raise exc
    finally:
        db.close()
