from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

try:
    from backend.models import User, Job, Candidate, Resume, Score, Evaluation, TaskLifecycle
    from backend.repositories import UserRepository, JobRepository, CandidateRepository, TaskLifecycleRepository
except ImportError:
    from models import User, Job, Candidate, Resume, Score, Evaluation, TaskLifecycle
    from repositories import UserRepository, JobRepository, CandidateRepository, TaskLifecycleRepository

class BaseService:
    def __init__(self, read_db: Session, write_db: Optional[Session] = None):
        self.read_db = read_db
        self.write_db = write_db or read_db

class AuthService(BaseService):
    def __init__(self, read_db: Session, write_db: Optional[Session] = None):
        super().__init__(read_db, write_db)
        self.user_repo = UserRepository(self.read_db, self.write_db)

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.user_repo.get_by_email(email)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.user_repo.get_by_id(user_id)

    def create_user_with_organization(self, email: str, full_name: str, hashed_password: str, organization_name: str) -> User:
        org = self.user_repo.get_organization_by_name(organization_name)
        if not org:
            org = self.user_repo.create_organization(organization_name)
            
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            organization_id=org.id
        )
        return self.user_repo.create(user)

class JobService(BaseService):
    def __init__(self, read_db: Session, write_db: Optional[Session] = None):
        super().__init__(read_db, write_db)
        self.job_repo = JobRepository(self.read_db, self.write_db)

    def get_job_by_id(self, job_id: int, organization_id: int) -> Optional[Job]:
        return self.job_repo.get_by_id_and_org(job_id, organization_id)

    def get_latest_job(self, organization_id: int) -> Optional[Job]:
        return self.job_repo.get_latest_by_org(organization_id)

    def get_all_jobs_paginated(self, organization_id: int, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        skip = (page - 1) * limit
        items = self.job_repo.get_all_by_org_paginated(organization_id, skip=skip, limit=limit)
        total_count = self.job_repo.count_by_org(organization_id)
        
        return {
            "items": items,
            "metadata": {
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1
            }
        }

    def create_job(self, title: str, description: str, organization_id: int) -> Job:
        job = Job(
            title=title,
            description=description,
            organization_id=organization_id
        )
        return self.job_repo.create(job)

    def delete_job(self, job_id: int, organization_id: int) -> bool:
        job = self.job_repo.get_by_id_and_org(job_id, organization_id)
        if not job:
            return False
        self.job_repo.delete(job)
        return True

class CandidateService(BaseService):
    def __init__(self, read_db: Session, write_db: Optional[Session] = None):
        super().__init__(read_db, write_db)
        self.cand_repo = CandidateRepository(self.read_db, self.write_db)

    def get_candidate_by_id(self, candidate_id: int, organization_id: int) -> Optional[Candidate]:
        return self.cand_repo.get_candidate_by_id_and_org(candidate_id, organization_id)

    def delete_candidate(self, candidate_id: int, organization_id: int) -> bool:
        cand = self.cand_repo.get_candidate_by_id_and_org(candidate_id, organization_id)
        if not cand:
            return False
        self.cand_repo.delete_candidate(cand)
        return True

    def get_resume_by_candidate_id(self, candidate_id: int, organization_id: int) -> Optional[Resume]:
        cand = self.cand_repo.get_candidate_by_id_and_org(candidate_id, organization_id)
        if not cand:
            return None
        return self.cand_repo.get_resume_by_candidate_id(candidate_id)

    def create_or_update_evaluation_status(self, job_id: int, candidate_id: int, status: str, comments: str) -> Evaluation:
        eval_record = self.cand_repo.get_evaluation_by_job_and_candidate(job_id, candidate_id)
        if not eval_record:
            eval_record = Evaluation(
                job_id=job_id,
                candidate_id=candidate_id,
                status=status,
                comments=comments
            )
            return self.cand_repo.create_evaluation(eval_record)
        else:
            # Modify record using write_db session transaction
            eval_record.status = status
            eval_record.comments = comments
            self.write_db.commit()
            self.write_db.refresh(eval_record)
            return eval_record

    def get_all_evaluation_records(self, organization_id: int) -> List[tuple]:
        return self.cand_repo.get_all_evaluation_records(organization_id)

    def get_job_candidates_records(self, job_id: int, organization_id: int) -> List[tuple]:
        return self.cand_repo.get_job_candidates_records(job_id, organization_id)

class TaskLifecycleService(BaseService):
    def __init__(self, read_db: Session, write_db: Optional[Session] = None):
        super().__init__(read_db, write_db)
        self.task_repo = TaskLifecycleRepository(self.read_db, self.write_db)

    def get_task_by_id(self, task_id: str) -> Optional[TaskLifecycle]:
        return self.task_repo.get_by_id(task_id)

    def get_task_by_idempotency_key(self, idempotency_key: str) -> Optional[TaskLifecycle]:
        return self.task_repo.get_by_idempotency_key(idempotency_key)

    def create_task(self, task_id: str, job_id: int, idempotency_key: Optional[str] = None) -> TaskLifecycle:
        task = TaskLifecycle(
            task_id=task_id,
            job_id=job_id,
            idempotency_key=idempotency_key,
            status="queued"
        )
        return self.task_repo.create(task)

    def update_task_status(self, task_id: str, status: str, error_message: Optional[str] = None, retry_count: Optional[int] = None) -> Optional[TaskLifecycle]:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return None
        task.status = status
        if error_message is not None:
            task.error_message = error_message
        if retry_count is not None:
            task.retry_count = retry_count
        return self.task_repo.update(task)
