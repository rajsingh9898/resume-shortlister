import os
import uvicorn
import asyncio
import datetime
import io
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
import math
import json
import redis

# Import logger
try:
    from backend.logger import logger
except ImportError:
    from logger import logger

try:
    from backend.config import settings
except ImportError:
    from config import settings

# Redis Caching Setup
REDIS_URL = settings.REDIS_URL
try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=0.5, socket_timeout=0.5)
    # Check connectivity
    redis_client.ping()
    logger.info("Connected to Redis for caching successfully.")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Falling back to no cache.")
    redis_client = None

# Import Celery background worker tasks
try:
    from backend.tasks import celery_app, process_shortlist_task
except ImportError:
    from tasks import celery_app, process_shortlist_task

# slowapi rate limiting dependencies
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# pypdf and python-docx for upload format verification
try:
    import pypdf
except ImportError:
    import PyPDF2 as pypdf
import docx

# Symmetric encryption at rest utilities
try:
    from backend.encryption import encrypt_data, decrypt_data
except ImportError:
    from encryption import encrypt_data, decrypt_data

# Import database, models and authentication
try:
    from backend.database import get_db, Base, engine, SessionLocal
    from backend.models import Organization, User, Job, Candidate, Resume, Score, Evaluation, AuditLog, TaskLifecycle
    from backend import nlp_engine
    from backend.auth import get_password_hash, verify_password, create_access_token, get_current_user, require_role
except ImportError:
    from database import get_db, Base, engine, SessionLocal
    from models import Organization, User, Job, Candidate, Resume, Score, Evaluation, AuditLog, TaskLifecycle
    import nlp_engine
    from auth import get_password_hash, verify_password, create_access_token, get_current_user, require_role

# Seed default organization and user helper with bcrypt password hashes
def seed_defaults(db: Session):
    org = db.query(Organization).filter_by(name="Default Org").first()
    if not org:
        org = Organization(name="Default Org")
        db.add(org)
        db.commit()
        db.refresh(org)
    
    # 1. Admin
    admin = db.query(User).filter_by(email="admin@talentai.local").first()
    if not admin:
        admin = User(
            email="admin@talentai.local",
            full_name="Raj Singh (Admin)",
            hashed_password=get_password_hash("admin123"),
            role="Admin",
            organization_id=org.id
        )
        db.add(admin)
        
    # 2. Recruiter
    recruiter = db.query(User).filter_by(email="recruiter@talentai.local").first()
    if not recruiter:
        recruiter = User(
            email="recruiter@talentai.local",
            full_name="Raj Singh (Recruiter)",
            hashed_password=get_password_hash("recruiter123"),
            role="Recruiter",
            organization_id=org.id
        )
        db.add(recruiter)
        
    # 3. Hiring Manager
    manager = db.query(User).filter_by(email="manager@talentai.local").first()
    if not manager:
        manager = User(
            email="manager@talentai.local",
            full_name="Raj Singh (Hiring Manager)",
            hashed_password=get_password_hash("manager123"),
            role="Hiring Manager",
            organization_id=org.id
        )
        db.add(manager)
        
    db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create tables if not present on startup
    try:
        # Check if direct URL is available for pgBouncer-safe PostgreSQL DDL on port 5432
        import os
        direct_url = os.getenv("DIRECT_URL")
        if direct_url:
            from sqlalchemy import create_engine as ddl_create_engine
            ddl_engine = ddl_create_engine(direct_url)
            Base.metadata.create_all(bind=ddl_engine)
            logger.info("Database schema initialized/checked on PostgreSQL using DIRECT_URL.")
        elif "sqlite" in str(engine.url):
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema initialized/checked on local SQLite fallback.")
    except Exception as e:
        logger.info(f"Database schema initialization skipped or already present: {e}")
    db = SessionLocal()
    try:
        seed_defaults(db)
    except Exception as e:
        logger.warning(f"Default seeding skipped or already present: {e}")
    finally:
        db.close()
    yield

import threading

class LocalCandidatesCache:
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
        
    def get(self, job_id: int):
        with self._lock:
            return self._cache.get(job_id)
            
    def set(self, job_id: int, data):
        with self._lock:
            self._cache[job_id] = data
            
    def invalidate(self, job_id: int):
        with self._lock:
            self._cache.pop(job_id, None)
            
    def clear(self):
        with self._lock:
            self._cache.clear()

candidates_local_cache = LocalCandidatesCache()

limiter = Limiter(key_func=get_remote_address, enabled=(settings.ENVIRONMENT != "development"))
app = FastAPI(title="AI-Based Resume Shortlisting System", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enable CORS for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Suppress static file caching in development to ensure instant updates
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if settings.ENVIRONMENT == "development":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Allocate thread pool executor for CPU-bound document parsing tasks
executor = ThreadPoolExecutor(max_workers=6)

# Locate directories
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../frontend"))
STORAGE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../storage"))
os.makedirs(STORAGE_DIR, exist_ok=True)

def parse_document_sync(filename: str, file_bytes: bytes) -> str:
    """Helper executed in a worker thread to extract document text."""
    return nlp_engine.extract_text(filename, file_bytes)

def validate_upload_file(filename: str, content: bytes):
    """Enforces whitelist extensions, max 5MB size, and rejects corrupted or malformed documents."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".pdf", ".docx", ".txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format: {filename}. Whitelisted formats: .pdf, .docx, .txt"
        )
        
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {filename}. Maximum permitted size is 5MB."
        )
        
    try:
        if ext == ".pdf":
            pdf_file = io.BytesIO(content)
            reader = pypdf.PdfReader(pdf_file)
            _ = len(reader.pages)
        elif ext == ".docx":
            docx_file = io.BytesIO(content)
            doc = docx.Document(docx_file)
            _ = len(doc.paragraphs)
        elif ext == ".txt":
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                content.decode("latin-1")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Corrupted or malformed file: {filename}. Error details: {str(e)}"
        )

# Pydantic schemas for request validation
class UserRegister(BaseModel):
    email: str
    full_name: str
    password: str
    role: Optional[str] = "Recruiter"
    organization_name: Optional[str] = "Default Org"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str

class EvaluationUpdate(BaseModel):
    job_id: Optional[int] = None
    filename: str
    status: Optional[str] = None
    comments: Optional[str] = None

# --- AUTH ENTRIES ---

@app.post("/api/auth/register", response_model=TokenResponse)
@limiter.limit("5/minute")
def register(request: Request, data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter_by(email=data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered.")
        
    org_name = data.organization_name if data.organization_name else "Default Org"
    org = db.query(Organization).filter_by(name=org_name).first()
    if not org:
        org = Organization(name=org_name)
        db.add(org)
        db.commit()
        db.refresh(org)
        
    new_user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        role=data.role if data.role else "Recruiter",
        organization_id=org.id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token({"sub": new_user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": new_user.role,
        "full_name": new_user.full_name
    }

@app.post("/api/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email is not registered.")
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password.")
        
    token = create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name
    }

@app.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "organization": {
            "id": current_user.organization_id,
            "name": current_user.organization.name
        }
    }

@app.get("/api/jobs/latest")
def get_latest_job(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter_by(organization_id=current_user.organization_id).order_by(Job.id.desc()).first()
    if not job:
        raise HTTPException(status_code=404, detail="No jobs found.")
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description
    }

# --- BUSINESS LOGIC PORTALS ---

@app.post("/api/shortlist")
@limiter.limit("15/minute")
async def shortlist(
    request: Request,
    background_tasks: BackgroundTasks,
    jd: str = Form(...), 
    resumes: List[UploadFile] = File(...),
    semantic_weight: float = Form(0.5),
    current_user: User = Depends(require_role(["Admin", "Recruiter"])),
    db: Session = Depends(get_db)
):
    if not jd.strip():
        raise HTTPException(status_code=400, detail="Job description text cannot be empty.")
    if not resumes:
        raise HTTPException(status_code=400, detail="Please upload at least one resume.")
        
    try:
        # 1. Concurrently read file contents from FastAPI upload streams (Async I/O)
        read_tasks = [res.read() for res in resumes]
        file_contents = await asyncio.gather(*read_tasks)
        
        # 2. Validate all files for size, extension, and corruption before parsing
        for idx, res in enumerate(resumes):
            validate_upload_file(res.filename, file_contents[idx])
            
        # 3. Compute SHA-256 Idempotency Key
        import hashlib
        hasher = hashlib.sha256()
        hasher.update(jd.encode("utf-8"))
        for content in file_contents:
            hasher.update(content)
        idempotency_key = hasher.hexdigest()
        
        # Check if a task is already processing/finished for this idempotency key
        existing_lifecycle = db.query(TaskLifecycle).filter_by(idempotency_key=idempotency_key).first()
        if existing_lifecycle:
            if existing_lifecycle.status in ["queued", "running", "success"]:
                logger.info(f"Duplicate request detected. Reusing existing task: {existing_lifecycle.task_id}")
                return {
                    "success": True,
                    "task_id": existing_lifecycle.task_id,
                    "job_id": existing_lifecycle.job_id
                }
            elif existing_lifecycle.status == "failed":
                db.delete(existing_lifecycle)
                db.commit()
                
    except HTTPException:
        # Re-raise file validation HTTP exceptions directly
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Concurrently reading documents failed: {str(e)}")
            
    try:
        # Save Job record under active tenant (pending background computations)
        job = Job(
            title=f"Shortlist Run - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", 
            description=jd, 
            organization_id=current_user.organization_id
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Build resumes info lists and save encrypted files to storage
        resumes_info = []
        for idx, res in enumerate(resumes):
            filename = res.filename
            file_bytes = file_contents[idx]
            saved_file_path = os.path.join(STORAGE_DIR, filename)
            
            # Save file to disk storage folder (encrypted at rest)
            encrypted_bytes = encrypt_data(file_bytes)
            with open(saved_file_path, "wb") as f:
                f.write(encrypted_bytes)
                
            resumes_info.append({
                "filename": filename,
                "file_path": saved_file_path
            })
            
        # Generate custom unique Task ID upfront to persist in database lifecycle tracker
        import uuid
        task_id = str(uuid.uuid4())
        
        # Persist task lifecycle record as 'queued'
        lifecycle = TaskLifecycle(
            task_id=task_id,
            job_id=job.id,
            status="queued",
            idempotency_key=idempotency_key
        )
        db.add(lifecycle)
        db.commit()
            
        # Dispatch Celery background task
        is_eager = getattr(celery_app.conf, "task_always_eager", False)
        if is_eager:
            background_tasks.add_task(
                process_shortlist_task.apply,
                args=(job.id, resumes_info, semantic_weight, current_user.id),
                task_id=task_id
            )
            class MockTask:
                id = task_id
            task = MockTask()
        else:
            task = process_shortlist_task.apply_async(
                args=(job.id, resumes_info, semantic_weight, current_user.id),
                task_id=task_id
            )
        
        # Log to audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="queue_shortlist",
            details=f"Queued background shortlist task for Job ID {job.id} (Task ID: {task.id})"
        )
        db.add(audit_log)
        db.commit()
        
        # Invalidate local cache in case re-running or updating candidates
        candidates_local_cache.invalidate(job.id)
        
        return {
            "success": True, 
            "task_id": task.id,
            "job_id": job.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Shortlisting integration failed: {str(e)}")

@app.get("/api/tasks/{task_id}")
@limiter.limit("60/minute")
def get_task_status(
    request: Request, 
    task_id: str, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from celery.result import AsyncResult
    from celery.backends.base import DisabledBackend
    
    # Query lifecycle tracker table first
    lifecycle = db.query(TaskLifecycle).filter_by(task_id=task_id).first()
    
    if lifecycle:
        state_map = {
            "queued": "PENDING",
            "running": "PROGRESS",
            "success": "SUCCESS",
            "failed": "FAILURE"
        }
        state = state_map.get(lifecycle.status, "PENDING")
        error_msg = lifecycle.error_message
    else:
        # Fallback to Celery Result Backend query
        res = AsyncResult(task_id)
        if isinstance(res.backend, DisabledBackend):
            state = "SUCCESS"
        else:
            try:
                state = res.state
            except AttributeError:
                state = "SUCCESS"
        error_msg = None
        
    response = {
        "task_id": task_id,
        "status": state,
        "progress": 0.0,
        "files": {},
        "retry_count": lifecycle.retry_count if lifecycle else 0
    }
    
    if error_msg:
        response["error"] = error_msg
        
    # If task is still pending or running, query Celery result store for live progress percentage updates
    if state in ["PENDING", "PROGRESS"]:
        res = AsyncResult(task_id)
        try:
            info = res.info or {}
            response["progress"] = info.get("progress", 0.0)
            response["files"] = info.get("files", {})
            if res.state == "FAILURE":
                response["status"] = "FAILURE"
                response["error"] = str(info)
        except Exception:
            pass
    elif state == "SUCCESS":
        response["progress"] = 1.0
        
    return response

@app.get("/api/jobs/{job_id}/candidates")
@limiter.limit("60/minute")
def get_job_candidates(
    request: Request,
    job_id: int,
    page: int = 1,
    limit: int = 10,
    filter: Optional[str] = None,
    threshold: int = 0,
    search: Optional[str] = None,
    skill: Optional[str] = None,
    semantic_w: float = 40.0,
    skills_w: float = 30.0,
    experience_w: float = 30.0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import re
    # Verify job belongs to user's org
    job = db.query(Job).filter_by(id=job_id, organization_id=current_user.organization_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found in your organization.")
        
    # Check local cache first to serve dynamic weight blending slider changes instantly
    cached_payload = candidates_local_cache.get(job_id)
    
    if cached_payload is None:
        # Load candidate records, selecting specific columns and only a 400-char substring of Resume.raw_text
        # to optimize query speed and database network bandwidth.
        candidates_records = db.query(
            Candidate, 
            Score, 
            Resume.filename,
            Resume.parsed_skills,
            func.substr(Resume.raw_text, 1, 400).label("raw_text_snippet"),
            Evaluation
        ).select_from(Candidate)\
            .join(Score, Score.candidate_id == Candidate.id)\
            .join(Resume, Resume.candidate_id == Candidate.id)\
            .join(Evaluation, Evaluation.candidate_id == Candidate.id)\
            .filter(Score.job_id == job_id, Evaluation.job_id == job_id, Candidate.organization_id == current_user.organization_id)\
            .all()
            
        # Parse requirement parameters for degree matching check
        jd_degrees = nlp_engine.parse_education_degrees(job.description)
        jd_exp = nlp_engine.parse_experience_years(job.description)
        jd_skills_dict = nlp_engine.extract_skills_from_text(job.description)
        
        jd_skills = []
        for cat_skills in jd_skills_dict.values():
            jd_skills.extend(cat_skills)
        jd_skills_set = set(jd_skills)
        
        cached_records = []
        for cand, score, resume_filename, resume_parsed_skills, raw_text_snippet, evaluation in candidates_records:
            candidate_degrees = cand.degrees or []
            degree_match = len(set(jd_degrees).intersection(set(candidate_degrees))) > 0 if jd_degrees else True
            
            # Read pre-calculated and cached scores directly from Score model
            skills_score = score.skills_score
            experience_score = score.experience_score
            matched_skills = score.matched_skills or []
            missing_skills = score.missing_skills or []
            
            cached_records.append({
                "cand_id": cand.id,
                "filename": resume_filename,
                "cosine_score": score.cosine_score,
                "skills_score": skills_score,
                "experience_score": experience_score,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "all_extracted_skills": resume_parsed_skills or {},
                "candidate_exp": cand.experience_years,
                "experience_confidence": cand.experience_confidence,
                "candidate_degrees": candidate_degrees,
                "degrees_confidence": cand.degrees_confidence,
                "degree_match": degree_match,
                "soft_traits": cand.soft_traits or [],
                "status": evaluation.status,
                "notes": evaluation.comments or "",
                "snippet": (raw_text_snippet or "") + ("..." if raw_text_snippet and len(raw_text_snippet) >= 400 else "")
            })
        cached_payload = (jd_exp, jd_skills_set, jd_degrees, cached_records)
        candidates_local_cache.set(job_id, cached_payload)
        
    jd_exp, jd_skills_set, jd_degrees, cached_list = cached_payload
    
    # Calculate dynamic final scores based on current weight blend configurations
    all_candidates = []
    for c in cached_list:
        final_score = (c["cosine_score"] * semantic_w / 100.0) + \
                      (c["skills_score"] * skills_w / 100.0) + \
                      (c["experience_score"] * experience_w / 100.0)
        final_score = round(final_score, 1)
        
        cand_dict = {
            "id": c["cand_id"],
            "filename": c["filename"],
            "score": final_score,
            "cosine_score": c["cosine_score"],
            "skills_score": c["skills_score"],
            "experience_score": c["experience_score"],
            "matched_skills": c["matched_skills"],
            "missing_skills": c["missing_skills"],
            "all_extracted_skills": c["all_extracted_skills"],
            "candidate_exp": c["candidate_exp"],
            "experience_confidence": c["experience_confidence"],
            "candidate_degrees": c["candidate_degrees"],
            "degrees_confidence": c["degrees_confidence"],
            "degree_match": c["degree_match"],
            "soft_traits": c["soft_traits"],
            "status": c["status"],
            "notes": c["notes"],
            "snippet": c["snippet"]
        }
        all_candidates.append(cand_dict)
        
    # Calculate stats across ALL matching records for this job run BEFORE pagination filters
    total_resumes = len(all_candidates)
    strong_matches = len([c for c in all_candidates if c["score"] >= 70.0])
    avg_score = round(sum(c["score"] for c in all_candidates) / total_resumes, 1) if total_resumes > 0 else 0.0
    
    # Histogram counts on entire set
    hist_low = len([c for c in all_candidates if c["score"] < 40.0])
    hist_mid = len([c for c in all_candidates if c["score"] >= 40.0 and c["score"] < 70.0])
    hist_high = len([c for c in all_candidates if c["score"] >= 70.0])
    
    # Calculate top pool skills globally
    skills_freq = {}
    for cand_dict in all_candidates:
        cand_skills_set = set()
        for cat_skills in cand_dict["all_extracted_skills"].values():
            for s in cat_skills:
                cand_skills_set.add(s)
        for s in cand_skills_set:
            skills_freq[s] = skills_freq.get(s, 0) + 1
    sorted_skills = [{"name": name, "count": count} for name, count in skills_freq.items()]
    sorted_skills.sort(key=lambda x: x["count"], reverse=True)
    top_skills = sorted_skills[:5]
    
    # Apply filtering in Python
    filtered_candidates = all_candidates
    
    if filter == "high":
        filtered_candidates = [c for c in filtered_candidates if c["score"] >= 70.0]
    elif filter == "mid":
        filtered_candidates = [c for c in filtered_candidates if c["score"] >= 40.0 and c["score"] < 70.0]
    elif filter == "low":
        filtered_candidates = [c for c in filtered_candidates if c["score"] < 40.0]
    elif filter == "exp":
        if jd_exp > 0.0:
            filtered_candidates = [c for c in filtered_candidates if c["candidate_exp"] >= jd_exp]
    elif filter == "edu":
        filtered_candidates = [c for c in filtered_candidates if c["degree_match"]]
    elif filter == "shortlisted":
        filtered_candidates = [c for c in filtered_candidates if c["status"] == "Shortlisted"]
    elif filter == "rejected":
        filtered_candidates = [c for c in filtered_candidates if c["status"] == "Rejected"]
    elif filter == "review":
        filtered_candidates = [c for c in filtered_candidates if c["status"] == "Under Review"]
        
    if threshold > 0:
        filtered_candidates = [c for c in filtered_candidates if c["score"] >= threshold]
        
    if search:
        search_lower = search.lower().strip()
        filtered_candidates = [c for c in filtered_candidates if search_lower in c["filename"].lower()]
        
    if skill:
        skill_lower = skill.lower().strip()
        filtered_candidates = [
            c for c in filtered_candidates 
            if any(skill_lower == s.lower() for cat in c["all_extracted_skills"].values() for s in cat)
        ]
        
    # Sort candidates by score descending
    filtered_candidates.sort(key=lambda x: x["score"], reverse=True)
    
    # Calculate paginated subset
    filtered_count = len(filtered_candidates)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_list = filtered_candidates[start_idx:end_idx]
    
    # Calculate bias warnings on entire set
    bias_warnings = []
    if len(all_candidates) >= 2:
        scores = [c["score"] for c in all_candidates]
        lengths = []
        gaps = []
        formatting_flags = []
        for cand_dict in all_candidates:
            res_rec = db.query(Resume).filter_by(candidate_id=cand_dict["id"]).first()
            txt = res_rec.raw_text if res_rec else ""
            lengths.append(len(txt))
            gaps.append(1.0 if any(g in txt.lower() for g in ["career break", "career gap", "employment gap", "sabbatical", "parental leave"]) else 0.0)
            
            special_count = len(re.findall(r'[^a-zA-Z0-9\s]', txt))
            total_count = len(txt) if len(txt) > 0 else 1
            ratio = special_count / total_count
            formatting_flags.append(1.0 if ratio > 0.15 or len(txt) < 200 else 0.0)
            
        corr_len = nlp_engine.pearson_correlation(scores, lengths)
        if abs(corr_len) > 0.5:
            bias_warnings.append(f"⚠️ Bias Alert: Match scores correlate strongly with resume length (correlation: {corr_len:.2f}). Longer resumes may have an unfair advantage.")
            
        corr_gaps = nlp_engine.pearson_correlation(scores, gaps)
        if corr_gaps < -0.4:
            bias_warnings.append(f"⚠️ Bias Alert: Candidate scores are negatively correlated with career breaks or employment gaps (correlation: {corr_gaps:.2f}). System may be penalizing gaps.")
            
        corr_format = nlp_engine.pearson_correlation(scores, formatting_flags)
        if corr_format < -0.4:
            bias_warnings.append(f"⚠️ Bias Alert: Match scores correlate negatively with non-standard formatting (correlation: {corr_format:.2f}). Formatting issues may be penalizing candidates.")
            
    response_data = {
        "candidates": paginated_list,
        "total_count": filtered_count,
        "total_unfiltered": total_resumes,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(filtered_count / limit) if limit > 0 else 1,
        "stats": {
            "total_resumes": total_resumes,
            "strong_matches": strong_matches,
            "average_score": avg_score,
            "histogram": {
                "low": hist_low,
                "mid": hist_mid,
                "high": hist_high
            },
            "top_skills": top_skills
        },
        "jd_requirements": {
            "skills": sorted(list(jd_skills_set)),
            "experience_years": jd_exp,
            "degrees": jd_degrees
        },
        "bias_warnings": bias_warnings
    }
    
    # Save cache
    if redis_client:
        try:
            redis_client.setex(cache_key, 3600, json.dumps(response_data))
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")
            
    return response_data

@app.get("/api/candidates/{candidate_id}/resume-text")
@limiter.limit("30/minute")
def get_candidate_resume_text(
    request: Request,
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify candidate belongs to user's org
    candidate = db.query(Candidate).filter_by(id=candidate_id, organization_id=current_user.organization_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found in your organization.")
        
    resume = db.query(Resume).filter_by(candidate_id=candidate.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found for this candidate.")
        
    return {"raw_text": resume.raw_text}

@app.post("/api/evaluation/update")
@limiter.limit("30/minute")
def update_evaluation(
    request: Request,
    data: EvaluationUpdate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Hiring Manager is comment-only and cannot change candidate status
    if current_user.role == "Hiring Manager" and data.status is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Hiring Managers are read + comment only and cannot modify candidate status tags."
        )

    try:
        # Find the Resume / Candidate matching the logged in tenant organization
        resume = db.query(Resume).join(Candidate).filter(
            Resume.filename == data.filename,
            Candidate.organization_id == current_user.organization_id
        ).first()
        
        if not resume:
            candidate = Candidate(name=data.filename, organization_id=current_user.organization_id)
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
            resume = Resume(candidate_id=candidate.id, filename=data.filename, file_path="", raw_text="")
            db.add(resume)
            db.commit()
        else:
            candidate = resume.candidate
            
        # Resolve Job ID
        job_id = data.job_id
        if not job_id:
            latest_job = db.query(Job).filter_by(organization_id=current_user.organization_id).order_by(Job.id.desc()).first()
            job_id = latest_job.id if latest_job else None
            
        if not job_id:
            job = Job(title="Default Job Context", description="System generated context", organization_id=current_user.organization_id)
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id
            
        # Find or create Evaluation record
        eval_record = db.query(Evaluation).filter_by(job_id=job_id, candidate_id=candidate.id).first()
        old_status = eval_record.status if eval_record else None
        status_changed = False
        
        if not eval_record:
            eval_record = Evaluation(
                job_id=job_id,
                candidate_id=candidate.id,
                status=data.status if data.status is not None else "Under Review",
                comments=data.comments if data.comments is not None else ""
            )
            db.add(eval_record)
            status_changed = True
        else:
            if data.status is not None and eval_record.status != data.status:
                old_status = eval_record.status
                eval_record.status = data.status
                status_changed = True
            if data.comments is not None:
                eval_record.comments = data.comments
        db.commit()
        
        # Log audit details with what changed
        if status_changed:
            log_action = "STATUS_CHANGE"
            log_details = f"Candidate '{data.filename}' status updated from '{old_status}' to '{eval_record.status}'"
        else:
            log_action = "update_evaluation"
            log_details = f"Updated comments for candidate '{data.filename}'"
            
        log = AuditLog(
            user_id=current_user.id,
            action=log_action,
            details=log_details
        )
        db.add(log)
        db.commit()
        
        # Invalidate local memory cache for this job context
        candidates_local_cache.invalidate(job_id)
        
        # Invalidate Redis cache for this job
        if redis_client:
            try:
                keys = redis_client.keys(f"job_candidates:{job_id}:*")
                if keys:
                    redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis cache clear failed: {e}")
        
        return {"success": True, "message": "Evaluation saved successfully in PostgreSQL."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")

@app.get("/api/backup/export")
def export_backup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Export evaluations scoped strictly to candidate tenant organization
        evaluations = db.query(Evaluation).join(Candidate).filter(
            Candidate.organization_id == current_user.organization_id
        ).all()
        
        backup_data = {}
        for ev in evaluations:
            # Find candidate's resume
            resume = db.query(Resume).filter_by(candidate_id=ev.candidate_id).first()
            if resume:
                backup_data[f"talentai_status_{resume.filename}"] = ev.status
                backup_data[f"talentai_notes_{resume.filename}"] = ev.comments
        return backup_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.post("/api/backup/import")
def import_backup(
    data: dict, 
    current_user: User = Depends(require_role(["Admin", "Recruiter"])),
    db: Session = Depends(get_db)
):
    try:
        latest_job = db.query(Job).filter_by(organization_id=current_user.organization_id).order_by(Job.id.desc()).first()
        job_id = latest_job.id if latest_job else None
        
        if not job_id:
            job = Job(title="Imported Job Context", description="Requirements context", organization_id=current_user.organization_id)
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id
            
        restored_count = 0
        
        for key, value in data.items():
            if not value:
                continue
            
            filename = None
            is_status = False
            is_notes = False
            
            if key.startswith("talentai_status_"):
                filename = key.replace("talentai_status_", "")
                is_status = True
            elif key.startswith("talentai_notes_"):
                filename = key.replace("talentai_notes_", "")
                is_notes = True
                
            if filename:
                # Find or create candidate/resume shell if not exists under active tenant org
                resume = db.query(Resume).join(Candidate).filter(
                    Resume.filename == filename,
                    Candidate.organization_id == current_user.organization_id
                ).first()
                
                if not resume:
                    candidate = Candidate(name=filename, organization_id=current_user.organization_id)
                    db.add(candidate)
                    db.commit()
                    db.refresh(candidate)
                    resume = Resume(candidate_id=candidate.id, filename=filename, file_path="", raw_text="")
                    db.add(resume)
                    db.commit()
                else:
                    candidate = resume.candidate
                    
                # Find or create evaluation
                eval_record = db.query(Evaluation).filter_by(job_id=job_id, candidate_id=candidate.id).first()
                if not eval_record:
                    eval_record = Evaluation(job_id=job_id, candidate_id=candidate.id, status="Under Review", comments="")
                    db.add(eval_record)
                    
                if is_status:
                    eval_record.status = value
                elif is_notes:
                    eval_record.comments = value
                    
                db.commit()
                restored_count += 1
                
        # Write audit logs
        log = AuditLog(
            user_id=current_user.id,
            action="import_backup",
            details=f"Imported backup containing {restored_count} entries to DB."
        )
        db.add(log)
        db.commit()
        
        # Invalidate local memory cache completely
        candidates_local_cache.clear()
        
        # Invalidate Redis cache
        if redis_client:
            try:
                keys = redis_client.keys("job_candidates:*")
                if keys:
                    redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis cache clear failed: {e}")
        
        return {"success": True, "restored_count": restored_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

# --- DELETION ENDPOINTS ---

@app.delete("/api/jobs/{job_id}")
def delete_job(
    job_id: int, 
    current_user: User = Depends(require_role(["Admin"])), 
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter_by(id=job_id, organization_id=current_user.organization_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found in your organization.")
    db.delete(job)
    db.commit()
    candidates_local_cache.invalidate(job_id)
    return {"success": True, "message": "Job deleted successfully."}

@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(
    candidate_id: int, 
    current_user: User = Depends(require_role(["Admin"])), 
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter_by(id=candidate_id, organization_id=current_user.organization_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found in your organization.")
        
    # Retrieve all associated resumes to delete files physically
    resumes = db.query(Resume).filter_by(candidate_id=candidate.id).all()
    for resume in resumes:
        if resume.file_path and os.path.exists(resume.file_path):
            try:
                os.remove(resume.file_path)
            except Exception as e:
                logger.error(f"Error purging file {resume.file_path}: {e}")
                
    candidate_name = candidate.name
    
    # Delete database candidate entity (cascades automatically to resumes/scores/evaluations)
    db.delete(candidate)
    
    # Log GDPR_PURGE audit trail
    audit = AuditLog(
        user_id=current_user.id,
        action="GDPR_PURGE",
        details=f"Fully purged candidate '{candidate_name}' and all associated scores/files for GDPR Right to be Forgotten compliance."
    )
    db.add(audit)
    db.commit()
    
    # Invalidate local memory cache completely
    candidates_local_cache.clear()
    
    # Invalidate Redis cache
    if redis_client:
        try:
            keys = redis_client.keys("job_candidates:*")
            if keys:
                redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis cache clear failed: {e}")
            
    return {"success": True, "message": "Candidate and all associated data fully purged for GDPR compliance."}

# Route to serve homepage
@app.get("/")
def get_home():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend files not found. Ensure the frontend/ folder exists."}

# Mount static files for assets, stylesheet and scripts (after specific API and root routes)
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
