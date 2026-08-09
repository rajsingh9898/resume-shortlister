import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
try:
    from backend.database import Base
except ImportError:
    from database import Base

class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="organization", cascade="all, delete-orphan")
    candidates = relationship("Candidate", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="Recruiter", nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    organization = relationship("Organization", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    organization = relationship("Organization", back_populates="jobs")
    scores = relationship("Score", back_populates="job", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="job", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    experience_years = Column(Float, default=0.0)
    degrees = Column(JSON, default=[])
    soft_traits = Column(JSON, default=[])
    consent_given = Column(Boolean, default=True, nullable=False)
    experience_confidence = Column(Float, default=1.0, nullable=False)
    degrees_confidence = Column(Float, default=1.0, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    organization = relationship("Organization", back_populates="candidates")
    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="candidate", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="candidate", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    filename = Column(String(255), index=True, nullable=False)
    file_path = Column(String(500), nullable=False)
    raw_text = Column(Text, nullable=False)
    parsed_skills = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    candidate = relationship("Candidate", back_populates="resumes")


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    match_score = Column(Float, nullable=False)
    cosine_score = Column(Float, nullable=False)
    skills_score = Column(Float, nullable=False)
    experience_score = Column(Float, nullable=False)
    matched_skills = Column(JSON, default=[])
    missing_skills = Column(JSON, default=[])
    model_version = Column(String(50), nullable=True)
    explainability = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    job = relationship("Job", back_populates="scores")
    candidate = relationship("Candidate", back_populates="scores")


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    status = Column(String(50), default="Under Review", nullable=False)
    comments = Column(Text, default="", nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    job = relationship("Job", back_populates="evaluations")
    candidate = relationship("Candidate", back_populates="evaluations")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(Text, nullable=True)

    user = relationship("User", back_populates="audit_logs")


class TaskLifecycle(Base):
    __tablename__ = "task_lifecycles"
    __table_args__ = {"extend_existing": True}

    task_id = Column(String(255), primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="queued", nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    job = relationship("Job")
