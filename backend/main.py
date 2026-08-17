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
import re

def anonymize_resume_text(text: str) -> str:
    if not text:
        return ""
    
    # 1. Redact potential university names (e.g., University of X, X University, X College)
    text = re.sub(
        r'\b(?:University\s+of\s+[A-Za-z0-9\s\-]+|([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+University)|([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+College))\b',
        '[REDACTED UNIVERSITY]',
        text,
        flags=re.IGNORECASE
    )
    
    # 2. Redact location proxies (e.g., City, State or ZIP codes)
    text = re.sub(
        r'\b[A-Z][a-zA-Z\s\.\-]+,\s+[A-Z]{2}\s+\d{5}\b',
        '[REDACTED LOCATION & ZIP]',
        text
    )
    text = re.sub(
        r'\b[A-Z][a-zA-Z\s\.\-]+,\s+[A-Z]{2}\b',
        '[REDACTED LOCATION]',
        text
    )
    
    # 3. Redact year ranges (age proxies)
    text = re.sub(
        r'\b(19\d{2}|20\d{2})\s*(?:-|to)\s*(19\d{2}|20\d{2})\b',
        '[REDACTED YEAR RANGE]',
        text
    )
    
    # 4. Redact single years with contexts (since, graduated, from, class of)
    text = re.sub(
        r'\b(?:in|since|graduated\s+in|from|class\s+of)\s+(19\d{2}|20\d{2})\b',
        lambda m: m.group(0).replace(m.group(1), '[REDACTED YEAR]'),
        text,
        flags=re.IGNORECASE
    )
    
    # 5. Redact candidate contact details (Email/Phone) to be extremely secure
    text = re.sub(
        r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b',
        '[REDACTED EMAIL]',
        text
    )
    text = re.sub(
        r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        '[REDACTED PHONE]',
        text
    )
    
    return text

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

# S3/MinIO Object Storage Wrapper
try:
    from backend.s3_client import storage_client
except ImportError:
    from s3_client import storage_client

# Import database, models and authentication
try:
    from backend.database import get_db, Base, engine, SessionLocal
    from backend.models import Organization, User, Job, Candidate, Resume, Score, Evaluation, AuditLog, TaskLifecycle, TokenBlacklist
    from backend import nlp_engine
    from backend.auth import get_password_hash, verify_password, create_access_token, create_refresh_token, verify_token_not_revoked, get_current_user, require_role, oauth2_scheme
    from backend.repositories import UserRepository, JobRepository, CandidateRepository, TaskLifecycleRepository
    from backend.services import AuthService, JobService, CandidateService, TaskLifecycleService
except ImportError:
    from database import get_db, Base, engine, SessionLocal
    from models import Organization, User, Job, Candidate, Resume, Score, Evaluation, AuditLog, TaskLifecycle, TokenBlacklist
    import nlp_engine
    from auth import get_password_hash, verify_password, create_access_token, create_refresh_token, verify_token_not_revoked, get_current_user, require_role, oauth2_scheme
    from repositories import UserRepository, JobRepository, CandidateRepository, TaskLifecycleRepository
    from services import AuthService, JobService, CandidateService, TaskLifecycleService

def get_read_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_write_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

def run_schema_migrations(engine_to_migrate):
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine_to_migrate)
        columns = [c['name'] for c in inspector.get_columns('scores')]
        
        with engine_to_migrate.begin() as conn:
            if 'model_version' not in columns:
                try:
                    conn.execute(text("ALTER TABLE scores ADD COLUMN model_version VARCHAR(50)"))
                    logger.info("Migrated database: added 'model_version' column to 'scores' table.")
                except Exception as e:
                    logger.warning(f"Failed to add model_version column: {e}")
                    
            if 'explainability' not in columns:
                try:
                    dialect = engine_to_migrate.dialect.name
                    col_type = "JSON" if dialect == "postgresql" else "TEXT"
                    conn.execute(text(f"ALTER TABLE scores ADD COLUMN explainability {col_type}"))
                    logger.info("Migrated database: added 'explainability' column to 'scores' table.")
                except Exception as e:
                    logger.warning(f"Failed to add explainability column: {e}")
                    
            # Add team_profile to jobs if not present
            try:
                job_columns = [c['name'] for c in inspector.get_columns('jobs')]
                if 'team_profile' not in job_columns:
                    dialect = engine_to_migrate.dialect.name
                    col_type = "JSON" if dialect == "postgresql" else "TEXT"
                    conn.execute(text(f"ALTER TABLE jobs ADD COLUMN team_profile {col_type}"))
                    logger.info("Migrated database: added 'team_profile' column to 'jobs' table.")
            except Exception as e:
                logger.warning(f"Failed to add team_profile column to jobs: {e}")
                    
            # Ensure indexes exist on high-query columns
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_evaluations_status ON evaluations (status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_resumes_candidate_id ON resumes (candidate_id)"))
                logger.info("Migrated database: ensured evaluations.status and resumes.candidate_id indexes exist.")
            except Exception as e:
                logger.warning(f"Failed to create dynamic indexes: {e}")
    except Exception as e:
        logger.warning(f"Dynamic database migration failed: {e}")

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
            run_schema_migrations(ddl_engine)
            logger.info("Database schema initialized/checked on PostgreSQL using DIRECT_URL.")
        elif "sqlite" in str(engine.url):
            Base.metadata.create_all(bind=engine)
            run_schema_migrations(engine)
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

from fastapi import APIRouter
from pydantic import Field
from typing import Generic, TypeVar, List

T = TypeVar("T")

class PageMetadata(BaseModel):
    total_count: int = Field(..., description="Total items matching filter")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Maximum items per page")
    total_pages: int = Field(..., description="Total pages")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    metadata: PageMetadata

api_router = APIRouter()

# Enable CORS for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Allocate thread pool executor for CPU-bound document parsing tasks
import time
import uuid

try:
    from backend.logger import request_id_var
    from backend.metrics import metrics_manager
except ImportError:
    from logger import request_id_var
    from metrics import metrics_manager

@app.middleware("http")
async def operations_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_var.set(request_id)
    
    start_time = time.time()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        # Suppress static file caching in development to ensure instant updates
        if settings.ENVIRONMENT == "development":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            
        duration = time.time() - start_time
        path = request.url.path
        if not path.startswith(("/static", "/metrics", "/health", "/api/metrics", "/api/health")):
            metrics_manager.record_api_latency(path, duration)
            if response.status_code >= 400:
                metrics_manager.record_failure(f"api_http_{response.status_code}")
                
        return response
    except Exception as e:
        duration = time.time() - start_time
        path = request.url.path
        if not path.startswith(("/static", "/metrics", "/health", "/api/metrics", "/api/health")):
            metrics_manager.record_api_latency(path, duration)
            metrics_manager.record_failure("api_exception")
        raise e
    finally:
        request_id_var.reset(token)

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
    refresh_token: str
    token_type: str
    role: str
    full_name: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class EvaluationUpdate(BaseModel):
    job_id: Optional[int] = None
    filename: str
    status: Optional[str] = None
    comments: Optional[str] = None

# --- AUTH ENTRIES ---

@api_router.post("/auth/register", response_model=TokenResponse)
@limiter.limit("5/minute")
def register(
    request: Request,
    data: UserRegister,
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db)
):
    auth_service = AuthService(read_db, write_db)
    existing_user = auth_service.get_user_by_email(data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered.")
        
    org_name = data.organization_name if data.organization_name else "Default Org"
    new_user = auth_service.create_user_with_organization(
        email=data.email,
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        organization_name=org_name
    )
    
    # Log audit log
    audit = AuditLog(
        user_id=new_user.id,
        action="USER_REGISTER",
        details=f"User '{new_user.email}' registered successfully."
    )
    write_db.add(audit)
    write_db.commit()
    
    access_token = create_access_token({"sub": new_user.email})
    refresh_token = create_refresh_token({"sub": new_user.email})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": new_user.role,
        "full_name": new_user.full_name
    }

@api_router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db)
):
    auth_service = AuthService(read_db, write_db)
    user = auth_service.get_user_by_email(form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Email is not registered.")
    if not verify_password(form_data.password, user.hashed_password):
        # Log login failure
        audit = AuditLog(
            user_id=user.id,
            action="USER_LOGIN_FAILED",
            details=f"Failed login attempt for user '{user.email}' (incorrect password)."
        )
        write_db.add(audit)
        write_db.commit()
        raise HTTPException(status_code=400, detail="Incorrect password.")
        
    # Log login success
    audit = AuditLog(
        user_id=user.id,
        action="USER_LOGIN",
        details=f"User '{user.email}' logged in successfully."
    )
    write_db.add(audit)
    write_db.commit()
    
    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name
    }

@api_router.post("/auth/refresh", response_model=TokenResponse)
def refresh(
    data: RefreshTokenRequest,
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db)
):
    try:
        payload = verify_token_not_revoked(data.refresh_token, read_db)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type.")
            
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token subject.")
            
        user = read_db.query(User).filter_by(email=email).first()
        if not user:
            raise HTTPException(status_code=400, detail="User not found.")
            
        # Revoke old refresh token (token rotation)
        import jwt
        from backend.auth import SECRET_KEY, ALGORITHM
        try:
            exp_timestamp = payload.get("exp")
            expires_at = datetime.datetime.utcfromtimestamp(exp_timestamp)
        except Exception:
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=7)
            
        revoked_old = TokenBlacklist(token=data.refresh_token, expires_at=expires_at)
        write_db.add(revoked_old)
        write_db.commit()
        
        access_token = create_access_token({"sub": user.email})
        refresh_token = create_refresh_token({"sub": user.email})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "role": user.role,
            "full_name": user.full_name
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=401, detail="Refresh token is expired or invalid.")

@api_router.post("/auth/logout")
def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    write_db: Session = Depends(get_write_db)
):
    if not token:
        raise HTTPException(status_code=400, detail="Authorization token is required.")
        
    import jwt
    from backend.auth import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        expires_at = datetime.datetime.utcfromtimestamp(exp_timestamp)
    except Exception:
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        
    existing = write_db.query(TokenBlacklist).filter_by(token=token).first()
    if not existing:
        blacklisted = TokenBlacklist(token=token, expires_at=expires_at)
        write_db.add(blacklisted)
        
    audit = AuditLog(
        user_id=current_user.id,
        action="USER_LOGOUT",
        details=f"User '{current_user.email}' logged out and revoked access token."
    )
    write_db.add(audit)
    write_db.commit()
    
    return {"success": True, "message": "Logged out successfully and token revoked."}

@api_router.get("/auth/me")
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

@api_router.get("/jobs/latest")
def get_latest_job(
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db),
    current_user: User = Depends(get_current_user)
):
    job_service = JobService(read_db, write_db)
    job = job_service.get_latest_job(current_user.organization_id)
    if not job:
        raise HTTPException(status_code=404, detail="No jobs found.")
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description
    }

@api_router.get("/jobs")
def get_jobs(
    page: int = 1,
    limit: int = 10,
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db),
    current_user: User = Depends(get_current_user)
):
    job_service = JobService(read_db, write_db)
    res = job_service.get_all_jobs_paginated(current_user.organization_id, page=page, limit=limit)
    items_serialized = []
    for job in res["items"]:
        items_serialized.append({
            "id": job.id,
            "title": job.title,
            "description": job.description,
            "created_at": job.created_at.isoformat() if job.created_at else None
        })
    return {
        "items": items_serialized,
        "metadata": res["metadata"]
    }


# S3 Presigned URL & Mock Storage Endpoints
from fastapi import Response

class PresignRequest(BaseModel):
    filename: str
    content_type: str = "application/pdf"

class ShortlistResumeItem(BaseModel):
    filename: str
    object_key: str

class TeamProfile(BaseModel):
    mindset: str = "Enterprise"
    focus: str = "Backend-heavy"
    expectation: str = "Ownership"

class ShortlistJSONRequest(BaseModel):
    jd: str
    semantic_weight: float = 0.5
    resumes: List[ShortlistResumeItem]
    team_profile: Optional[TeamProfile] = None

@api_router.post("/storage/presign-upload")
def get_presigned_upload_url(
    payload: PresignRequest,
    current_user: User = Depends(get_current_user)
):
    ext = os.path.splitext(payload.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".txt"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {payload.filename}. Whitelisted formats: .pdf, .docx, .txt"
        )
    
    import uuid
    object_key = f"resumes/{uuid.uuid4()}-{payload.filename}"
    
    upload_url = storage_client.generate_presigned_upload_url(object_key, payload.content_type)
    return {
        "upload_url": upload_url,
        "object_key": object_key,
        "filename": payload.filename
    }

@api_router.put("/storage/mock-upload")
async def mock_upload_file(request: Request, key: str):
    body_bytes = await request.body()
    # Write the uploaded bytes directly to simulated storage
    storage_client.upload_bytes(key, body_bytes)
    return {"status": "success", "message": "Uploaded mock object successfully."}

@api_router.get("/storage/mock-download")
def mock_download_file(key: str):
    try:
        content = storage_client.download_bytes(key)
        return Response(content=content, media_type="application/octet-stream")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in simulated S3 storage.")

# --- BUSINESS LOGIC PORTALS ---

@api_router.post("/shortlist")
@limiter.limit("15/minute")
async def shortlist(
    request: Request,
    payload: ShortlistJSONRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(["Admin", "Recruiter"])),
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db)
):
    if not payload.jd.strip():
        raise HTTPException(status_code=400, detail="Job description text cannot be empty.")
    if not payload.resumes:
        raise HTTPException(status_code=400, detail="Please upload at least one resume.")
        
    try:
        # 1. Compute SHA-256 Idempotency Key based on Job Description and S3 keys
        import hashlib
        hasher = hashlib.sha256()
        hasher.update(payload.jd.encode("utf-8"))
        for res in payload.resumes:
            hasher.update(res.object_key.encode("utf-8"))
        idempotency_key = hasher.hexdigest()
        
        # Check if a task is already processing/finished for this idempotency key
        lifecycle_service = TaskLifecycleService(read_db, write_db)
        existing_lifecycle = lifecycle_service.get_task_by_idempotency_key(idempotency_key)
        if existing_lifecycle:
            if existing_lifecycle.status in ["queued", "running", "success"]:
                logger.info(f"Duplicate request detected. Reusing existing task: {existing_lifecycle.task_id}")
                return {
                    "success": True,
                    "task_id": existing_lifecycle.task_id,
                    "job_id": existing_lifecycle.job_id
                }
            elif existing_lifecycle.status == "failed":
                write_db.delete(existing_lifecycle)
                write_db.commit()
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Idempotency validation failed: {str(e)}")
            
    try:
        # Save Job record under active tenant (pending background computations)
        job_service = JobService(read_db, write_db)
        team_profile_dict = payload.team_profile.dict() if payload.team_profile else None
        job = job_service.create_job(
            title=f"Shortlist Run - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", 
            description=payload.jd, 
            organization_id=current_user.organization_id,
            team_profile=team_profile_dict
        )
        
        # Build resumes info lists pointing to S3 keys
        resumes_info = [
            {"filename": res.filename, "file_path": res.object_key}
            for res in payload.resumes
        ]
            
        # Generate custom unique Task ID upfront to persist in database lifecycle tracker
        import uuid
        task_id = str(uuid.uuid4())
        
        # Persist task lifecycle record as 'queued'
        lifecycle = lifecycle_service.create_task(
            task_id=task_id,
            job_id=job.id,
            idempotency_key=idempotency_key
        )
            
        # Dispatch Celery background task
        is_eager = getattr(celery_app.conf, "task_always_eager", False)
        import time
        task_kwargs = {"queued_at": time.time()}
        
        if is_eager:
            background_tasks.add_task(
                process_shortlist_task.apply,
                args=(job.id, resumes_info, payload.semantic_weight, current_user.id),
                kwargs=task_kwargs,
                task_id=task_id
            )
            class MockTask:
                id = task_id
            task = MockTask()
        else:
            task = process_shortlist_task.apply_async(
                args=(job.id, resumes_info, payload.semantic_weight, current_user.id),
                kwargs=task_kwargs,
                task_id=task_id
            )
        
        # Log to audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="queue_shortlist",
            details=f"Queued background shortlist task for Job ID {job.id} (Task ID: {task.id})"
        )
        write_db.add(audit_log)
        write_db.commit()
        
        # Invalidate local cache in case re-running or updating candidates
        candidates_local_cache.invalidate(job.id)
        
        return {
            "success": True, 
            "task_id": task.id,
            "job_id": job.id
        }
        
    except Exception as e:
        write_db.rollback()
        raise HTTPException(status_code=500, detail=f"Shortlisting integration failed: {str(e)}")

@api_router.get("/tasks/{task_id}")
@limiter.limit("60/minute")
def get_task_status(
    request: Request, 
    task_id: str, 
    current_user: User = Depends(get_current_user),
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db)
):
    from celery.result import AsyncResult
    from celery.backends.base import DisabledBackend
    
    # Query lifecycle tracker table first
    lifecycle_service = TaskLifecycleService(read_db, write_db)
    lifecycle = lifecycle_service.get_task_by_id(task_id)
    
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
        
     # Ensure we read retry_count safely
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

@api_router.get("/jobs/{job_id}/candidates")
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
    bias_blind: bool = False,
    current_user: User = Depends(get_current_user),
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db)
):
    import re
    # Verify job belongs to user's org
    job_service = JobService(read_db, write_db)
    job = job_service.get_job_by_id(job_id, current_user.organization_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found in your organization.")
        
    # Check local cache first to serve dynamic weight blending slider changes instantly
    cached_payload = candidates_local_cache.get(job_id)
    
    candidate_service = CandidateService(read_db, write_db)
    
    if cached_payload is None:
        # Load candidate records via candidate service layer (routing to read_db)
        candidates_records = candidate_service.get_job_candidates_records(job_id, current_user.organization_id)
            
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
            
            def parse_json_field(val):
                if not val:
                    return {"reasons_high": [], "reasons_low": []}
                if isinstance(val, dict):
                    return val
                try:
                    import json
                    return json.loads(val)
                except Exception:
                    return {"reasons_high": [], "reasons_low": []}

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
                "model_version": getattr(score, "model_version", "v1.0.0") or "v1.0.0",
                "explainability": parse_json_field(getattr(score, "explainability", None)),
                "snippet": (raw_text_snippet or "") + ("..." if raw_text_snippet and len(raw_text_snippet) >= 400 else "")
            })
        cached_payload = (jd_exp, jd_skills_set, jd_degrees, cached_records)
        candidates_local_cache.set(job_id, cached_payload)
        
    jd_exp, jd_skills_set, jd_degrees, cached_list = cached_payload
    
    # 1. Recruiter Preference Memory calculations
    shortlist_skills_counts = {}
    reject_skills_counts = {}
    total_shortlisted = 0
    total_rejected = 0
    
    for c in cached_list:
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
                
    # Calculate adaptive skill boosts
    skill_boosts = {}
    all_feedback_skills = set(shortlist_skills_counts.keys()).union(set(reject_skills_counts.keys()))
    for s in all_feedback_skills:
        sh_count = shortlist_skills_counts.get(s, 0)
        rj_count = reject_skills_counts.get(s, 0)
        ratio = (sh_count - rj_count) / max(sh_count + rj_count, 1)
        skill_boosts[s] = ratio * 4.0
        
    preferred_skills = sorted(
        [{"skill": s, "boost": round(b, 1)} for s, b in skill_boosts.items() if b > 0.5],
        key=lambda x: x["boost"],
        reverse=True
    )
    penalized_skills = sorted(
        [{"skill": s, "penalty": round(abs(b), 1)} for s, b in skill_boosts.items() if b < -0.5],
        key=lambda x: x["penalty"],
        reverse=True
    )

    # 2. Market Intelligence Insight calculations
    jd_text_lower = job.description.lower()
    classified_role = "Backend Engineer"
    if "frontend" in jd_text_lower:
        classified_role = "Frontend Engineer"
    elif "fullstack" in jd_text_lower or "full stack" in jd_text_lower:
        classified_role = "Fullstack Engineer"
    elif "devops" in jd_text_lower or "platform" in jd_text_lower or "kubernetes" in jd_text_lower:
        classified_role = "DevOps/Platform Engineer"
    elif "data engineer" in jd_text_lower or "etl" in jd_text_lower or "hadoop" in jd_text_lower:
        classified_role = "Data Engineer"
    elif "product manager" in jd_text_lower or "agile" in jd_text_lower:
        classified_role = "Product Manager"
        
    base_min = 85000
    base_max = 115000
    if jd_exp > 5:
        base_min = 145000
        base_max = 205000
    elif jd_exp >= 2:
        base_min = 110000
        base_max = 145000
        
    if classified_role in ["DevOps/Platform Engineer", "Backend Engineer", "Data Engineer"]:
        base_min = int(base_min * 1.10)
        base_max = int(base_max * 1.10)
        
    salary_range = f"${base_min:,} - ${base_max:,}"
    
    qualified_candidates = [c for c in cached_list if c["skills_score"] >= 0.5]
    supply_ratio = len(qualified_candidates) / len(cached_list) if cached_list else 0.0
    
    if supply_ratio < 0.2:
        difficulty = "Low Supply (Difficult to Hire)"
        feasibility = "Challenging"
    elif supply_ratio < 0.5:
        difficulty = "Moderate Supply"
        feasibility = "Moderate"
    else:
        difficulty = "High Supply (Easy to Hire)"
        feasibility = "Highly Feasible"
        
    jd_skills_top = list(jd_skills_set)[:3]
    skills_str = " + ".join(jd_skills_top) if jd_skills_top else "Required skills"
    market_summary = f"{skills_str} profiles are in high demand and {difficulty.lower()}. Feasibility is {feasibility.lower()}."

    # Fetch active jobs for multi-role alignment
    from backend.models import Job
    org_jobs = read_db.query(Job).filter(Job.organization_id == current_user.organization_id).all()
    
    # Parse requirements for each job
    jobs_parsed_skills = {}
    for oj in org_jobs:
        oj_skills_dict = nlp_engine.extract_skills_from_text(oj.description)
        oj_skills = []
        for cat_skills in oj_skills_dict.values():
            oj_skills.extend(cat_skills)
        jobs_parsed_skills[oj.id] = {
            "title": oj.title,
            "skills": {s.lower() for s in oj_skills}
        }

    # Calculate dynamic final scores based on current weight blend configurations
    all_candidates = []
    for c in cached_list:
        final_score = (c["cosine_score"] * semantic_w / 100.0) + \
                      (c["skills_score"] * skills_w / 100.0) + \
                      (c["experience_score"] * experience_w / 100.0)
        
        # Apply recruiter preference boost/penalty
        preference_adjustment = 0.0
        for s in c["matched_skills"]:
            preference_adjustment += skill_boosts.get(s, 0.0)
        preference_adjustment = max(min(preference_adjustment, 12.0), -12.0)
        
        final_score = max(min(final_score + preference_adjustment, 100.0), 0.0)
        final_score = round(final_score, 1)
        
        # Compute Multi-Role Workforce matching
        cand_flat_skills = {s.lower() for cat in c["all_extracted_skills"].values() for s in cat}
        other_matches = []
        for oj_id, oj_data in jobs_parsed_skills.items():
            oj_skills_set = oj_data["skills"]
            intersect = cand_flat_skills.intersection(oj_skills_set)
            match_pct = round((len(intersect) / len(oj_skills_set) * 100), 1) if oj_skills_set else 0.0
            
            other_matches.append({
                "job_id": oj_id,
                "title": oj_data["title"],
                "match_percentage": match_pct,
                "shared_skills": sorted(list(intersect))
            })
            
        other_matches.sort(key=lambda x: x["match_percentage"], reverse=True)
        best_fit = other_matches[0] if other_matches else None
        secondary_matches = [m for m in other_matches[1:] if m["match_percentage"] >= 20.0]
        
        cand_multi_role = {
            "best_fit": best_fit,
            "secondary_matches": secondary_matches[:3]
        }
        
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
            "candidate_degrees": list(c["candidate_degrees"]),
            "degrees_confidence": c["degrees_confidence"],
            "degree_match": c["degree_match"],
            "soft_traits": c["soft_traits"],
            "status": c["status"],
            "notes": c["notes"],
            "model_version": c["model_version"],
            "explainability": dict(c["explainability"]),
            "snippet": c["snippet"],
            "preference_adjustment": round(preference_adjustment, 1),
            "multi_role_planning": cand_multi_role
        }
        all_candidates.append(cand_dict)
        
    # Sort all candidates by final score descending
    all_candidates.sort(key=lambda x: x["score"], reverse=True)
    
    # Compute dynamic similar candidates based on matched skills overlap
    for idx, c1 in enumerate(all_candidates):
        c1_skills = set(c1["matched_skills"])
        sims = []
        for c2 in all_candidates:
            if c2["id"] == c1["id"]:
                continue
            c2_skills = set(c2["matched_skills"])
            intersection = c1_skills.intersection(c2_skills)
            union = c1_skills.union(c2_skills)
            sim_percentage = round((len(intersection) / len(union) * 100), 0) if union else 0.0
            
            c2_idx = all_candidates.index(c2)
            c2_label = f"Candidate #{c2_idx + 1}" if bias_blind else c2["filename"]
            
            sims.append({
                "id": c2["id"],
                "label": c2_label,
                "score": c2["score"],
                "similarity": sim_percentage,
                "shared_skills": sorted(list(intersection))
            })
        sims.sort(key=lambda x: x["similarity"], reverse=True)
        c1["similar_candidates"] = sims[:3]
        
    # If Bias-Blind mode is requested, redact candidate information dynamically
    if bias_blind:
        for idx, c in enumerate(all_candidates):
            c["filename"] = f"Candidate #{idx + 1}"
            c["snippet"] = anonymize_resume_text(c["snippet"])
            
            # Anonymize degree names (remove school references)
            scrubbed_degrees = []
            for deg in c["candidate_degrees"]:
                scrubbed_deg = re.sub(r'\s+(?:from|at)\s+.+$', '', deg, flags=re.IGNORECASE)
                scrubbed_deg = re.sub(
                    r'\b(?:University\s+of\s+[A-Za-z0-9\s\-]+|([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+University))\b',
                    '[REDACTED SCHOOL]',
                    scrubbed_deg,
                    flags=re.IGNORECASE
                )
                scrubbed_degrees.append(scrubbed_deg)
            c["candidate_degrees"] = scrubbed_degrees
            
            # Clean why_candidate statement in explainability if present
            if "explainability" in c and "why_candidate" in c["explainability"]:
                c["explainability"]["why_candidate"] = anonymize_resume_text(c["explainability"]["why_candidate"])
            if "explainability" in c and "skill_gap_roadmap" in c["explainability"]:
                c["explainability"]["skill_gap_roadmap"]["summary"] = anonymize_resume_text(c["explainability"]["skill_gap_roadmap"]["summary"])
        
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
            res_rec = candidate_service.get_resume_by_candidate_id(cand_dict["id"], current_user.organization_id)
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
            
    # 3. Generate concise Hiring Brief for Hiring Managers
    pool_strengths = []
    pool_risks = []
    interview_focus = []
    final_recommendations = ""
    
    # Analyze matched vs missing skills frequencies globally
    global_matched_freq = {}
    global_missing_freq = {}
    for cand in all_candidates:
        for s in cand["matched_skills"]:
            global_matched_freq[s] = global_matched_freq.get(s, 0) + 1
        for s in cand["missing_skills"]:
            global_missing_freq[s] = global_missing_freq.get(s, 0) + 1
            
    # Rank matched skills and missing skills
    sorted_matched = sorted(global_matched_freq.items(), key=lambda x: x[1], reverse=True)
    sorted_missing = sorted(global_missing_freq.items(), key=lambda x: x[1], reverse=True)
    
    # Pool Strengths
    top_matched = [s for s, count in sorted_matched[:3]]
    if top_matched:
        pool_strengths.append(f"Strong match alignment across the pool in core competencies: {', '.join(top_matched)}.")
    pool_strengths.append(f"The pool features an average candidate matching score of {avg_score}%.")
    
    # Pool Risks
    top_missing = [s for s, count in sorted_missing[:3]]
    if top_missing:
        pool_risks.append(f"Technical stack gaps identified: a significant portion of candidates lack {', '.join(top_missing)}.")
    if avg_score < 60.0:
        pool_risks.append("Overall pool scoring is below average, indicating high difficulty finding a perfect fit.")
        
    # Interview Focus
    if top_missing:
        interview_focus.append(f"Practical problem solving around missing skill domains: {', '.join(top_missing)}.")
    interview_focus.append("System architecture scalability, database optimization patterns, and core tooling competency.")
    
    # Final Recommendation
    shortlisted_candidates = [c for c in all_candidates if c["score"] >= 70.0]
    if shortlisted_candidates:
        # Anonymize candidate filenames if bias_blind mode is requested
        top_cand_names = []
        for c in shortlisted_candidates[:2]:
            if bias_blind:
                top_cand_names.append(f"Candidate #{all_candidates.index(c) + 1}")
            else:
                top_cand_names.append(c["filename"])
        final_recommendations = f"Proceed to screening loops with top candidates ({', '.join(top_cand_names)}) who demonstrate high core requirements match. Use technical loops to probe remaining pool candidates on missing stack items."
    else:
        final_recommendations = "No candidate currently meets the 70% shortlist threshold. Recommend expanding the search or adjusting the skills criteria weight slider."
        
    hiring_brief = {
        "role_title": classified_role,
        "strengths": pool_strengths,
        "risks": pool_risks,
        "interview_focus": interview_focus,
        "recommendation": final_recommendations
    }

    response_data = {
        "candidates": paginated_list, # legacy candidates envelope
        "items": paginated_list,      # standardized items envelope
        "total_count": filtered_count,
        "total_unfiltered": total_resumes,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(filtered_count / limit) if limit > 0 else 1,
        "metadata": {                 # standardized metadata envelope
            "total_count": filtered_count,
            "page": page,
            "limit": limit,
            "total_pages": math.ceil(filtered_count / limit) if limit > 0 else 1
        },
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
        "bias_warnings": bias_warnings,
        "recruiter_learning": {
            "total_shortlisted": total_shortlisted,
            "total_rejected": total_rejected,
            "preferred_skills": preferred_skills[:5],
            "penalized_skills": penalized_skills[:5]
        },
        "market_intelligence": {
            "classified_role": classified_role,
            "salary_range": salary_range,
            "difficulty": difficulty,
            "feasibility": feasibility,
            "summary": market_summary
        },
        "hiring_brief": hiring_brief
    }
    
    # Save cache
    if redis_client:
        try:
            redis_client.setex(cache_key, 3600, json.dumps(response_data))
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")
            
    return response_data

@api_router.get("/candidates/{candidate_id}/resume-text")
@limiter.limit("30/minute")
def get_candidate_resume_text(
    request: Request,
    candidate_id: int,
    bias_blind: bool = False,
    current_user: User = Depends(get_current_user),
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db)
):
    # Verify candidate belongs to user's org
    candidate_service = CandidateService(read_db, write_db)
    candidate = candidate_service.get_candidate_by_id(candidate_id, current_user.organization_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found in your organization.")
        
    resume = candidate_service.get_resume_by_candidate_id(candidate.id, current_user.organization_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found for this candidate.")
        
    try:
        text_key = resume.file_path + ".txt"
        raw_text_bytes = storage_client.download_bytes(text_key)
        raw_text = raw_text_bytes.decode("utf-8")
    except Exception:
        raw_text = resume.raw_text or "No parsed text available."
        
    if bias_blind:
        raw_text = anonymize_resume_text(raw_text)
        
    return {"raw_text": raw_text}

@api_router.post("/evaluation/update")
@limiter.limit("30/minute")
def update_evaluation(
    request: Request,
    data: EvaluationUpdate, 
    current_user: User = Depends(get_current_user),
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db)
):
    # Hiring Manager is comment-only and cannot change candidate status
    if current_user.role == "Hiring Manager" and data.status is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Hiring Managers are read + comment only and cannot modify candidate status tags."
        )

    try:
        # Find the Resume / Candidate matching the logged in tenant organization (read query)
        resume = read_db.query(Resume).join(Candidate).filter(
            Resume.filename == data.filename,
            Candidate.organization_id == current_user.organization_id
        ).first()
        
        if not resume:
            # Write operations route to write_db
            candidate = Candidate(name=data.filename, organization_id=current_user.organization_id)
            write_db.add(candidate)
            write_db.commit()
            write_db.refresh(candidate)
            resume = Resume(candidate_id=candidate.id, filename=data.filename, file_path="", raw_text="")
            write_db.add(resume)
            write_db.commit()
        else:
            candidate = resume.candidate
            
        # Resolve Job ID
        job_id = data.job_id
        if not job_id:
            job_service = JobService(read_db, write_db)
            latest_job = job_service.get_latest_job(current_user.organization_id)
            job_id = latest_job.id if latest_job else None
            
        if not job_id:
            job = Job(title="Default Job Context", description="System generated context", organization_id=current_user.organization_id)
            write_db.add(job)
            write_db.commit()
            write_db.refresh(job)
            job_id = job.id
            
        # Find or create Evaluation record (read query)
        eval_record = read_db.query(Evaluation).filter_by(job_id=job_id, candidate_id=candidate.id).first()
        old_status = eval_record.status if eval_record else None
        status_changed = False
        
        if not eval_record:
            eval_record = Evaluation(
                job_id=job_id,
                candidate_id=candidate.id,
                status=data.status if data.status is not None else "Under Review",
                comments=data.comments if data.comments is not None else ""
            )
            write_db.add(eval_record)
            status_changed = True
        else:
            if data.status is not None and eval_record.status != data.status:
                old_status = eval_record.status
                eval_record.status = data.status
                status_changed = True
            if data.comments is not None:
                eval_record.comments = data.comments
        write_db.commit()
        
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
        write_db.add(log)
        write_db.commit()
        
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
        write_db.rollback()
        raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")

@api_router.get("/backup/export")
def export_backup(
    current_user: User = Depends(get_current_user),
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db)
):
    try:
        # Export evaluations scoped strictly to candidate tenant organization (read query)
        evaluations = read_db.query(Evaluation).join(Candidate).filter(
            Candidate.organization_id == current_user.organization_id
        ).all()
        
        backup_data = {}
        for ev in evaluations:
            # Find candidate's resume (read query)
            resume = read_db.query(Resume).filter_by(candidate_id=ev.candidate_id).first()
            if resume:
                backup_data[f"talentai_status_{resume.filename}"] = ev.status
                backup_data[f"talentai_notes_{resume.filename}"] = ev.comments
                
        # Serialize database backup to JSON bytes
        json_bytes = json.dumps(backup_data, indent=2).encode("utf-8")
        
        # Define export key on S3
        import uuid
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        export_key = f"exports/org_{current_user.organization_id}/backup_{timestamp}_{uuid.uuid4().hex[:8]}.json"
        
        # Save to S3 object storage
        storage_client.upload_bytes(export_key, json_bytes, content_type="application/json")
        
        # Generate pre-signed S3 download URL
        download_url = storage_client.generate_presigned_download_url(export_key)
        
        # Log to audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="BACKUP_EXPORTED",
            details=f"Database backup exported to key: {export_key}"
        )
        write_db.add(audit_log)
        write_db.commit()
        
        return {
            "success": True,
            "download_url": download_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@api_router.post("/backup/import")
def import_backup(
    data: dict, 
    current_user: User = Depends(require_role(["Admin", "Recruiter"])),
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db)
):
    try:
        job_service = JobService(read_db, write_db)
        latest_job = job_service.get_latest_job(current_user.organization_id)
        job_id = latest_job.id if latest_job else None
        
        if not job_id:
            job = Job(title="Imported Job Context", description="Requirements context", organization_id=current_user.organization_id)
            write_db.add(job)
            write_db.commit()
            write_db.refresh(job)
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
                # Find or create candidate/resume shell if not exists under active tenant org (read query)
                resume = read_db.query(Resume).join(Candidate).filter(
                    Resume.filename == filename,
                    Candidate.organization_id == current_user.organization_id
                ).first()
                
                if not resume:
                    # Write operations routed to write_db
                    candidate = Candidate(name=filename, organization_id=current_user.organization_id)
                    write_db.add(candidate)
                    write_db.commit()
                    write_db.refresh(candidate)
                    resume = Resume(candidate_id=candidate.id, filename=filename, file_path="", raw_text="")
                    write_db.add(resume)
                    write_db.commit()
                else:
                    candidate = resume.candidate
                    
                # Find or create evaluation (read query)
                eval_record = read_db.query(Evaluation).filter_by(job_id=job_id, candidate_id=candidate.id).first()
                if not eval_record:
                    eval_record = Evaluation(job_id=job_id, candidate_id=candidate.id, status="Under Review", comments="")
                    write_db.add(eval_record)
                    
                if is_status:
                    eval_record.status = value
                elif is_notes:
                    eval_record.comments = value
                    
                write_db.commit()
                restored_count += 1
                
        # Write audit logs
        log = AuditLog(
            user_id=current_user.id,
            action="import_backup",
            details=f"Imported backup containing {restored_count} entries to DB."
        )
        write_db.add(log)
        write_db.commit()
        
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
        write_db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

# --- DELETION ENDPOINTS ---

@api_router.delete("/jobs/{job_id}")
def delete_job(
    job_id: int, 
    current_user: User = Depends(require_role(["Admin"])), 
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db)
):
    job_service = JobService(read_db, write_db)
    success = job_service.delete_job(job_id, current_user.organization_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found in your organization.")
        
    candidates_local_cache.invalidate(job_id)
    
    # Log to audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="JOB_DELETED",
        details=f"Job description with ID {job_id} deleted by Admin."
    )
    write_db.add(audit_log)
    write_db.commit()
    
    return {"success": True, "message": "Job deleted successfully."}

@api_router.delete("/candidates/{candidate_id}")
def delete_candidate(
    candidate_id: int, 
    current_user: User = Depends(require_role(["Admin"])), 
    read_db: Session = Depends(get_read_db),
    write_db: Session = Depends(get_write_db)
):
    candidate_service = CandidateService(read_db, write_db)
    candidate = candidate_service.get_candidate_by_id(candidate_id, current_user.organization_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found in your organization.")
        
    # Retrieve all associated resumes to delete files physically (read query)
    resumes = read_db.query(Resume).filter_by(candidate_id=candidate.id).all()
    for resume in resumes:
        if resume.file_path and os.path.exists(resume.file_path):
            try:
                os.remove(resume.file_path)
            except Exception as e:
                logger.error(f"Error purging file {resume.file_path}: {e}")
                
    candidate_name = candidate.name
    
    # Delete database candidate entity via candidate service (write operations)
    candidate_service.delete_candidate(candidate_id, current_user.organization_id)
    
    # Log GDPR_PURGE audit trail
    audit = AuditLog(
        user_id=current_user.id,
        action="GDPR_PURGE",
        details=f"Fully purged candidate '{candidate_name}' and all associated scores/files for GDPR Right to be Forgotten compliance."
    )
    write_db.add(audit)
    write_db.commit()

    
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

# --- OBSERVABILITY & HEALTH ENDPOINTS ---
from fastapi import Response

@app.get("/metrics")
@api_router.get("/metrics")
def get_metrics_endpoint():
    return metrics_manager.get_summary()

@app.get("/health")
@api_router.get("/health")
def get_health_status():
    from sqlalchemy import text
    
    db_ok = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error(f"Health check Database failure: {e}")
    finally:
        db.close()
        
    redis_ok = False
    if redis_client:
        try:
            redis_client.ping()
            redis_ok = True
        except Exception as e:
            logger.error(f"Health check Redis failure: {e}")
            
    worker_ok = True
    if not celery_app.conf.task_always_eager:
        try:
            inspect = celery_app.control.inspect(timeout=0.5)
            pings = inspect.ping()
            worker_ok = pings is not None and len(pings) > 0
        except Exception as e:
            logger.error(f"Health check Worker failure: {e}")
            worker_ok = False
            
    status_code = status.HTTP_200_OK if (db_ok and redis_ok and worker_ok) else status.HTTP_503_SERVICE_UNAVAILABLE
    
    content = {
        "status": "healthy" if status_code == 200 else "degraded",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "components": {
            "database": "healthy" if db_ok else "unhealthy",
            "redis": "healthy" if redis_ok else "unhealthy",
            "celery_worker": "healthy" if worker_ok else "unhealthy"
        }
    }
    
    return Response(
        content=json.dumps(content),
        media_type="application/json",
        status_code=status_code
    )

# Route to serve homepage
@app.get("/")
def get_home():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend files not found. Ensure the frontend/ folder exists."}

# Include APIRouter versioning prefixes
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")

# Mount static files for assets, stylesheet and scripts (after specific API and root routes)
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
