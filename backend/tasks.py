import os
import sys
import datetime
from celery import Celery
from sqlalchemy.orm import Session
from typing import Optional

# Setup path so imports work correctly inside celery worker process
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.database import SessionLocal
    from backend.models import Job, Candidate, Resume, Score, Evaluation, AuditLog, TaskLifecycle
    from backend import nlp_engine
    from backend.encryption import decrypt_data
    from backend.repositories import UserRepository, JobRepository, CandidateRepository, TaskLifecycleRepository
    from backend.services import AuthService, JobService, CandidateService, TaskLifecycleService
except ImportError:
    from database import SessionLocal
    from models import Job, Candidate, Resume, Score, Evaluation, AuditLog, TaskLifecycle
    import nlp_engine
    from encryption import decrypt_data
    from repositories import UserRepository, JobRepository, CandidateRepository, TaskLifecycleRepository
    from services import AuthService, JobService, CandidateService, TaskLifecycleService

try:
    from backend.logger import logger
except ImportError:
    from logger import logger

try:
    from backend.config import settings
except ImportError:
    from config import settings

# S3/MinIO Object Storage Wrapper
try:
    from backend.s3_client import storage_client
except ImportError:
    from s3_client import storage_client

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

from celery.signals import task_prerun, task_postrun, task_failure
import time

try:
    from backend.logger import task_id_var
    from backend.metrics import metrics_manager
except ImportError:
    from logger import task_id_var
    from metrics import metrics_manager

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra_kwargs):
    # Set logging context
    task_id_var.set(task_id)
    # Store start time on the task instance
    if task:
        task._start_time = time.time()
        
        # Calculate queue latency
        if kwargs and "queued_at" in kwargs:
            try:
                latency = time.time() - kwargs["queued_at"]
                metrics_manager.record_queue_latency(sender.name, latency)
            except Exception as e:
                logger.warning(f"Failed to record queue latency: {e}")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, retval=None, state=None, **kwargs):
    # Reset logging context
    task_id_var.set(None)
    
    # Record duration metric
    if task and hasattr(task, "_start_time"):
        duration = time.time() - task._start_time
        metrics_manager.record_task_duration(sender.name, duration)

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    # Record task failure metric
    metrics_manager.record_failure(f"task_{sender.name}_failure")

@celery_app.task(bind=True, max_retries=3)
def process_shortlist_task(self, job_id: int, resumes_info: list, semantic_weight: float, user_id: int, queued_at: Optional[float] = None):
    """Asynchronously parses and ranks candidate resumes for a given Job ID."""
    db = SessionLocal()
    lifecycle_service = TaskLifecycleService(db)
    
    # 1. Update task lifecycle status to running
    if self.request.id:
        lifecycle_service.update_task_status(
            task_id=self.request.id,
            status="running",
            retry_count=self.request.retries
        )
            
    try:
        # Load the Job context (read query)
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
            
            # Read and decrypt file contents from S3 or fallback storage
            try:
                disk_bytes = storage_client.download_bytes(file_path)
                try:
                    file_bytes = decrypt_data(disk_bytes)
                except Exception:
                    # If it's not encrypted (like new uploads directly to S3), treat as raw bytes
                    file_bytes = disk_bytes
                raw_text = nlp_engine.extract_text(filename, file_bytes)
            except Exception as e:
                raw_text = f"Error reading/parsing file: {str(e)}"
                
            # Upload extracted text to S3/MinIO
            try:
                text_key = file_path + ".txt"
                storage_client.upload_bytes(text_key, raw_text.encode("utf-8"), content_type="text/plain")
            except Exception as e:
                logger.error(f"Failed to upload extracted text for candidate {filename} to S3: {e}")
                
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
        team_profile = getattr(job, "team_profile", None)
        results = nlp_engine.compute_nlp_shortlist(jd, resume_data, semantic_weight, team_profile=team_profile)
        
        # 4. Save results to DB
        if self.request.id:
            self.update_state(state="PROGRESS", meta={"progress": 0.8, "files": file_statuses})
        
        for cand in results["candidates"]:
            filename = cand["filename"]
            raw_text = next(r["raw_text"] for r in resume_data if r["filename"] == filename)
            file_path = next(r["file_path"] for r in resume_data if r["filename"] == filename)
            
            # Find or create Candidate (scoped under tenant Org)
            import re
            
            # Extract email from raw resume text
            email_match = re.search(r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b', raw_text)
            candidate_email = email_match.group(0) if email_match else None
            
            # Extract clean name from filename
            clean_name = filename
            clean_name = re.sub(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}-', '', clean_name)
            clean_name = os.path.splitext(clean_name)[0]
            if clean_name.lower().endswith('.txt') or clean_name.lower().endswith('.pdf') or clean_name.lower().endswith('.docx'):
                clean_name = os.path.splitext(clean_name)[0]
            clean_name = clean_name.replace('_', ' ').replace('-', ' ').title()

            candidate = db.query(Candidate).filter(
                (Candidate.name == clean_name) | (Candidate.name == filename),
                Candidate.organization_id == job.organization_id
            ).first()

            if not candidate:
                candidate = Candidate(
                    name=clean_name,
                    email=candidate_email,
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
                candidate.name = clean_name
                candidate.email = candidate_email
                candidate.experience_years = cand["candidate_exp"]
                candidate.experience_confidence = cand["experience_confidence"]
                candidate.degrees = cand["candidate_degrees"]
                candidate.degrees_confidence = cand["degrees_confidence"]
                candidate.soft_traits = cand["soft_traits"]
                db.commit()
                
            # Create or update Resume reference (keep raw_text empty in database to save space)
            resume = db.query(Resume).filter_by(candidate_id=candidate.id, filename=filename).first()
            if not resume:
                resume = Resume(
                    candidate_id=candidate.id,
                    filename=filename,
                    file_path=file_path,
                    raw_text="",
                    parsed_skills=cand["all_extracted_skills"]
                )
                db.add(resume)
            else:
                resume.file_path = file_path
                resume.raw_text = ""
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
                missing_skills=cand["missing_skills"],
                model_version=cand.get("model_version", "v2.1.0"),
                explainability=cand.get("explainability", {"reasons_high": [], "reasons_low": []})
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
            lifecycle_service.update_task_status(
                task_id=self.request.id,
                status="success"
            )
                
        return {"success": True, "job_id": job.id}
    except Exception as exc:
        db.rollback()
        # Calculate backoff delay: 10 * (2 ** retries)
        backoff_delay = 10 * (2 ** self.request.retries)
        
        if self.request.retries < self.max_retries:
            logger.warning(f"Task {self.request.id} failed, retrying in {backoff_delay}s. Error: {exc}")
            if self.request.id:
                lifecycle_service.update_task_status(
                    task_id=self.request.id,
                    status="queued",
                    error_message=f"Retry {self.request.retries + 1}: {str(exc)}",
                    retry_count=self.request.retries + 1
                )
            raise self.retry(exc=exc, countdown=backoff_delay)
        else:
            # Dead-letter handling: Max retries exceeded
            logger.error(f"Task {self.request.id} failed permanently after {self.request.retries} retries: {exc}")
            if self.request.id:
                lifecycle_service.update_task_status(
                    task_id=self.request.id,
                    status="failed",
                    error_message=f"Failed permanently after max retries. Error: {str(exc)}"
                )
            raise exc
    finally:
        db.close()


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

@celery_app.task(bind=True, max_retries=3)
def send_status_update_email(self, candidate_id: int, job_id: int, old_status: Optional[str], new_status: str):
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter_by(id=candidate_id).first()
        job = db.query(Job).filter_by(id=job_id).first()
        if not candidate or not job:
            logger.warning(f"Candidate {candidate_id} or Job {job_id} not found. Skipping status update email.")
            return f"Candidate {candidate_id} or Job {job_id} not found."
            
        candidate_email = candidate.email
        candidate_name = candidate.name
        
        if not candidate_email:
            logger.warning(f"Candidate {candidate_name} (ID: {candidate_id}) has no email address. Skipping email dispatch.")
            return "Skipped: No email address on candidate record."

        try:
            from backend.models import Organization
        except ImportError:
            from models import Organization
            
        org = db.query(Organization).filter_by(id=candidate.organization_id).first()
        org_name = org.name if org else "TalentAI Organization"

        subject = f"Application Status Update: {job.title} at {org_name}"
        
        if new_status == "Shortlisted":
            email_body = f"""
            <html>
            <body style="font-family: 'Outfit', 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.6; background: #f8fafc; padding: 24px;">
                <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                    <div style="text-align: center; margin-bottom: 24px; border-bottom: 1px solid #e2e8f0; padding-bottom: 16px;">
                        <h2 style="color: #6366f1; font-weight: 700; margin: 0; font-size: 1.5rem;">TalentAI Automated Notification</h2>
                    </div>
                    <p>Dear <strong>{candidate_name}</strong>,</p>
                    <p>Congratulations! We have reviewed your application and we are pleased to inform you that your resume has been <strong>shortlisted</strong> for the <strong>{job.title}</strong> opening.</p>
                    <p>You are invited to the next stage of our recruitment process, which includes a formal interview or technical assessment.</p>
                    <p>Our team will contact you shortly to coordinate scheduling details.</p>
                    <div style="margin-top: 32px; border-top: 1px solid #e2e8f0; padding-top: 16px; font-size: 0.85rem; color: #64748b;">
                        <p>Best regards,</p>
                        <p><strong>The Recruitment Team</strong><br>{org_name}</p>
                    </div>
                </div>
            </body>
            </html>
            """
        elif new_status == "Rejected":
            email_body = f"""
            <html>
            <body style="font-family: 'Outfit', 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.6; background: #f8fafc; padding: 24px;">
                <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                    <div style="text-align: center; margin-bottom: 24px; border-bottom: 1px solid #e2e8f0; padding-bottom: 16px;">
                        <h2 style="color: #6366f1; font-weight: 700; margin: 0; font-size: 1.5rem;">TalentAI Automated Notification</h2>
                    </div>
                    <p>Dear <strong>{candidate_name}</strong>,</p>
                    <p>Thank you for your interest in the <strong>{job.title}</strong> role at {org_name}.</p>
                    <p>After careful review of your application, we regret to inform you that we will not be moving forward with your candidacy at this time.</p>
                    <p>We appreciate the time you took to share your credentials with us and wish you the best of luck in your job search.</p>
                    <div style="margin-top: 32px; border-top: 1px solid #e2e8f0; padding-top: 16px; font-size: 0.85rem; color: #64748b;">
                        <p>Best regards,</p>
                        <p><strong>The Recruitment Team</strong><br>{org_name}</p>
                    </div>
                </div>
            </body>
            </html>
            """
        else: # Under Review
            email_body = f"""
            <html>
            <body style="font-family: 'Outfit', 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.6; background: #f8fafc; padding: 24px;">
                <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                    <div style="text-align: center; margin-bottom: 24px; border-bottom: 1px solid #e2e8f0; padding-bottom: 16px;">
                        <h2 style="color: #6366f1; font-weight: 700; margin: 0; font-size: 1.5rem;">TalentAI Automated Notification</h2>
                    </div>
                    <p>Dear <strong>{candidate_name}</strong>,</p>
                    <p>Your application for the <strong>{job.title}</strong> role at {org_name} has been received and is currently <strong>under review</strong>.</p>
                    <p>We will contact you as soon as an evaluation decision is finalized.</p>
                    <div style="margin-top: 32px; border-top: 1px solid #e2e8f0; padding-top: 16px; font-size: 0.85rem; color: #64748b;">
                        <p>Best regards,</p>
                        <p><strong>The Recruitment Team</strong><br>{org_name}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.warning(f"SMTP Credentials not configured. Simulated E-Mail Body for {candidate_email}:\\n{email_body}")
            return "Email simulated successfully (credentials missing)."

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = candidate_email
        msg.attach(MIMEText(email_body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, candidate_email, msg.as_string())
            
        logger.info(f"Status email successfully dispatched to {candidate_email} for status {new_status}.")
        return "Email sent successfully."
    except Exception as exc:
        logger.error(f"Failed to dispatch status email: {exc}. Retrying...")
        is_eager = getattr(celery_app.conf, "task_always_eager", False)
        if is_eager:
            logger.error(f"Eager mode active. Skipping Celery retry to prevent request failures. Error was: {exc}")
            return f"Failed to send email: {str(exc)}"
        backoff_delay = 10 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=backoff_delay)
    finally:
        db.close()
