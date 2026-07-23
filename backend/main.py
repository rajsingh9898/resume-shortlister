import os
import uvicorn
import asyncio
import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import database, models and authentication
try:
    from backend.database import get_db, Base, engine, SessionLocal
    from backend.models import Organization, User, Job, Candidate, Resume, Score, Evaluation, AuditLog
    from backend import nlp_engine
    from backend.auth import get_password_hash, verify_password, create_access_token, get_current_user, require_role
except ImportError:
    from database import get_db, Base, engine, SessionLocal
    from models import Organization, User, Job, Candidate, Resume, Score, Evaluation, AuditLog
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
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()
    yield

app = FastAPI(title="AI-Based Resume Shortlisting System", lifespan=lifespan)

# Enable CORS for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
def register(data: UserRegister, db: Session = Depends(get_db)):
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
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password.")
        
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

# --- BUSINESS LOGIC PORTALS ---

@app.post("/api/shortlist")
async def shortlist(
    jd: str = Form(...), 
    resumes: List[UploadFile] = File(...),
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
        
        # 2. Concurrently extract text from files offloaded to thread executor (Parallel CPU operations)
        loop = asyncio.get_running_loop()
        parse_tasks = []
        for idx, res in enumerate(resumes):
            task = loop.run_in_executor(
                executor, 
                parse_document_sync, 
                res.filename, 
                file_contents[idx]
            )
            parse_tasks.append(task)
            
        parsed_texts = await asyncio.gather(*parse_tasks)
        
        # Assemble resume data structure
        resume_data = []
        for idx, res in enumerate(resumes):
            resume_data.append({
                "filename": res.filename,
                "raw_text": parsed_texts[idx]
            })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Concurrently reading/parsing documents failed: {str(e)}")
            
    try:
        # Run NLP engine scoring
        results = nlp_engine.compute_nlp_shortlist(jd, resume_data)
        
        # Save Job record under active tenant
        job = Job(
            title=f"Shortlist Run - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", 
            description=jd, 
            organization_id=current_user.organization_id
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Process and save candidates & scores to DB under tenant constraints
        candidates_output = []
        for cand in results["candidates"]:
            filename = cand["filename"]
            raw_text = next(r["raw_text"] for r in resume_data if r["filename"] == filename)
            file_bytes = next(file_contents[idx] for idx, r in enumerate(resumes) if r.filename == filename)
            
            # Save file to disk storage folder
            saved_file_path = os.path.join(STORAGE_DIR, filename)
            with open(saved_file_path, "wb") as f:
                f.write(file_bytes)
                
            # Find or create Candidate isolated by tenant organization
            candidate = db.query(Candidate).filter_by(name=filename, organization_id=current_user.organization_id).first()
            if not candidate:
                candidate = Candidate(
                    name=filename,
                    experience_years=cand["candidate_exp"],
                    degrees=cand["candidate_degrees"],
                    soft_traits=cand["soft_traits"],
                    organization_id=current_user.organization_id
                )
                db.add(candidate)
                db.commit()
                db.refresh(candidate)
            else:
                candidate.experience_years = cand["candidate_exp"]
                candidate.degrees = cand["candidate_degrees"]
                candidate.soft_traits = cand["soft_traits"]
                db.commit()
                
            # Find or create Resume pointing to file path (Resume is candidate scoped, Candidate is org scoped)
            resume = db.query(Resume).filter_by(filename=filename).first()
            if not resume:
                resume = Resume(
                    candidate_id=candidate.id,
                    filename=filename,
                    file_path=saved_file_path,
                    raw_text=raw_text,
                    parsed_skills=cand["all_extracted_skills"]
                )
                db.add(resume)
            else:
                resume.file_path = saved_file_path
                resume.raw_text = raw_text
                resume.parsed_skills = cand["all_extracted_skills"]
            db.commit()
            
            # Save Score record
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
            
            # Find any previous evaluation to carry over evaluation state globally inside tenant Org
            existing_eval = db.query(Evaluation).join(Candidate).filter(
                Evaluation.candidate_id == candidate.id,
                Candidate.organization_id == current_user.organization_id
            ).order_by(Evaluation.id.desc()).first()
            
            status = existing_eval.status if existing_eval else "Under Review"
            comments = existing_eval.comments if existing_eval else ""
            
            # Save Evaluation record for current job run
            evaluation = Evaluation(
                job_id=job.id,
                candidate_id=candidate.id,
                status=status,
                comments=comments
            )
            db.add(evaluation)
            db.commit()
            
            # Augment candidate dictionary output with DB evaluations info
            cand["status"] = status
            cand["notes"] = comments
            candidates_output.append(cand)
            
        # Log to audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="rank_candidates",
            details=f"Ranked {len(resumes)} candidates for Job ID {job.id}"
        )
        db.add(audit_log)
        db.commit()
        
        return {
            "success": True, 
            "candidates": candidates_output,
            "jd_requirements": results["jd_requirements"],
            "job_id": job.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Shortlisting integration failed: {str(e)}")

@app.post("/api/evaluation/update")
def update_evaluation(
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
        if not eval_record:
            eval_record = Evaluation(
                job_id=job_id,
                candidate_id=candidate.id,
                status=data.status if data.status is not None else "Under Review",
                comments=data.comments if data.comments is not None else ""
            )
            db.add(eval_record)
        else:
            if data.status is not None:
                eval_record.status = data.status
            if data.comments is not None:
                eval_record.comments = data.comments
        db.commit()
        
        # Log audit details
        log = AuditLog(
            user_id=current_user.id,
            action="update_evaluation",
            details=f"Updated candidate {data.filename} evaluation in Job {job_id}"
        )
        db.add(log)
        db.commit()
        
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
    db.delete(candidate)
    db.commit()
    return {"success": True, "message": "Candidate deleted successfully."}

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
