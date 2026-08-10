from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from backend.models import Organization, User, Job, Candidate, Resume, Score, Evaluation, TaskLifecycle
except ImportError:
    from models import Organization, User, Job, Candidate, Resume, Score, Evaluation, TaskLifecycle

class BaseRepository:
    def __init__(self, read_db: Session, write_db: Optional[Session] = None):
        self.read_db = read_db
        # Route write operations to write_db if provided, else fall back to read_db (single db mode)
        self.write_db = write_db or read_db

class UserRepository(BaseRepository):
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.read_db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.read_db.query(User).filter(User.email == email).first()

    def create(self, user: User) -> User:
        self.write_db.add(user)
        self.write_db.commit()
        self.write_db.refresh(user)
        return user

    def get_organization_by_name(self, name: str) -> Optional[Organization]:
        return self.read_db.query(Organization).filter(Organization.name == name).first()

    def create_organization(self, name: str) -> Organization:
        org = Organization(name=name)
        self.write_db.add(org)
        self.write_db.commit()
        self.write_db.refresh(org)
        return org

class JobRepository(BaseRepository):
    def get_by_id_and_org(self, job_id: int, organization_id: int) -> Optional[Job]:
        return self.read_db.query(Job).filter(Job.id == job_id, Job.organization_id == organization_id).first()

    def get_latest_by_org(self, organization_id: int) -> Optional[Job]:
        return self.read_db.query(Job).filter(Job.organization_id == organization_id).order_by(Job.id.desc()).first()

    def get_all_by_org_paginated(self, organization_id: int, skip: int = 0, limit: int = 10) -> List[Job]:
        return self.read_db.query(Job).filter(Job.organization_id == organization_id).order_by(Job.id.desc()).offset(skip).limit(limit).all()

    def count_by_org(self, organization_id: int) -> int:
        return self.read_db.query(func.count(Job.id)).filter(Job.organization_id == organization_id).scalar() or 0

    def create(self, job: Job) -> Job:
        self.write_db.add(job)
        self.write_db.commit()
        self.write_db.refresh(job)
        return job

    def delete(self, job: Job) -> None:
        self.write_db.delete(job)
        self.write_db.commit()

class CandidateRepository(BaseRepository):
    def get_candidate_by_id_and_org(self, candidate_id: int, organization_id: int) -> Optional[Candidate]:
        return self.read_db.query(Candidate).filter(Candidate.id == candidate_id, Candidate.organization_id == organization_id).first()

    def get_candidate_by_email_and_org(self, email: str, organization_id: int) -> Optional[Candidate]:
        return self.read_db.query(Candidate).filter(Candidate.email == email, Candidate.organization_id == organization_id).first()

    def create_candidate(self, candidate: Candidate) -> Candidate:
        self.write_db.add(candidate)
        self.write_db.commit()
        self.write_db.refresh(candidate)
        return candidate

    def delete_candidate(self, candidate: Candidate) -> None:
        self.write_db.delete(candidate)
        self.write_db.commit()

    def get_resume_by_candidate_id(self, candidate_id: int) -> Optional[Resume]:
        return self.read_db.query(Resume).filter(Resume.candidate_id == candidate_id).first()

    def create_resume(self, resume: Resume) -> Resume:
        self.write_db.add(resume)
        self.write_db.commit()
        self.write_db.refresh(resume)
        return resume

    def get_score_by_job_and_candidate(self, job_id: int, candidate_id: int) -> Optional[Score]:
        return self.read_db.query(Score).filter(Score.job_id == job_id, Score.candidate_id == candidate_id).first()

    def create_score(self, score: Score) -> Score:
        self.write_db.add(score)
        self.write_db.commit()
        self.write_db.refresh(score)
        return score

    def get_evaluation_by_job_and_candidate(self, job_id: int, candidate_id: int) -> Optional[Evaluation]:
        return self.read_db.query(Evaluation).filter(Evaluation.job_id == job_id, Evaluation.candidate_id == candidate_id).first()

    def create_evaluation(self, evaluation: Evaluation) -> Evaluation:
        self.write_db.add(evaluation)
        self.write_db.commit()
        self.write_db.refresh(evaluation)
        return evaluation

    def get_all_evaluation_records(self, organization_id: int) -> List[tuple]:
        # Perform read queries to load evaluations
        return self.read_db.query(Candidate, Resume, Score, Evaluation)\
            .join(Resume, Resume.candidate_id == Candidate.id)\
            .join(Score, Score.candidate_id == Candidate.id)\
            .join(Evaluation, Evaluation.candidate_id == Candidate.id)\
            .filter(Candidate.organization_id == organization_id)\
            .all()

    def get_job_candidates_records(self, job_id: int, organization_id: int) -> List[tuple]:
        return self.read_db.query(
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
            .filter(Score.job_id == job_id, Evaluation.job_id == job_id, Candidate.organization_id == organization_id)\
            .all()

class TaskLifecycleRepository(BaseRepository):
    def get_by_id(self, task_id: str) -> Optional[TaskLifecycle]:
        return self.read_db.query(TaskLifecycle).filter(TaskLifecycle.task_id == task_id).first()

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[TaskLifecycle]:
        if not idempotency_key:
            return None
        return self.read_db.query(TaskLifecycle).filter(TaskLifecycle.idempotency_key == idempotency_key).first()

    def create(self, task: TaskLifecycle) -> TaskLifecycle:
        self.write_db.add(task)
        self.write_db.commit()
        self.write_db.refresh(task)
        return task

    def update(self, task: TaskLifecycle) -> TaskLifecycle:
        self.write_db.commit()
        self.write_db.refresh(task)
        return task
