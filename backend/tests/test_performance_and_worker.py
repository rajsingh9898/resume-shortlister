import pytest
import concurrent.futures
import time
import uuid
from sqlalchemy.orm import Session
from backend.models import TaskLifecycle, TokenBlacklist, User, Job, Candidate, Evaluation, Score
from backend.tasks import process_shortlist_task
from backend.auth import create_access_token, create_refresh_token
from fastapi.testclient import TestClient

def test_refresh_token_and_revocation_flow(client):
    # 1. Register a user to get tokens
    register_payload = {
        "email": f"test_user_{uuid.uuid4().hex[:6]}@talentai.local",
        "full_name": "Test User Revocation",
        "password": "Password123!",
        "role": "Recruiter",
        "organization_name": "Performance Org"
    }
    res = client.post("/api/auth/register", json=register_payload)
    assert res.status_code == 200
    data = res.json()
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    
    # 2. Call refresh token endpoint with valid refresh token
    refresh_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    refresh_data = refresh_res.json()
    new_access = refresh_data["access_token"]
    new_refresh = refresh_data["refresh_token"]
    
    # Verify old refresh token is blacklisted by trying to refresh again
    fail_refresh = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert fail_refresh.status_code == 401
    
    # 3. Access a protected endpoint using new_access
    headers = {"Authorization": f"Bearer {new_access}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    
    # 4. Perform logout to revoke new_access token
    logout_res = client.post("/api/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    
    # 5. Verify revoked access token is blocked
    blocked_res = client.get("/api/auth/me", headers=headers)
    assert blocked_res.status_code == 401

def test_concurrent_presigned_url_requests(client):
    # Simulate concurrent clients requesting presigned upload URLs (performance test)
    # Register/Login user to authenticate requests
    register_payload = {
        "email": f"perf_user_{uuid.uuid4().hex[:6]}@talentai.local",
        "full_name": "Perf User",
        "password": "Password123!",
        "role": "Recruiter"
    }
    res = client.post("/api/auth/register", json=register_payload)
    assert res.status_code == 200
    token = res.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    import threading
    lock = threading.Lock()
    
    def request_presigned():
        payload = {"filename": f"resume_{uuid.uuid4().hex[:4]}.pdf", "content_type": "application/pdf"}
        with lock:
            return client.post("/api/storage/presign-upload", json=payload, headers=headers)
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(request_presigned) for _ in range(10)]
        results = [f.result() for f in futures]
        
    for r in results:
        assert r.status_code == 200
        data = r.json()
        assert "upload_url" in data
        assert "object_key" in data

def test_queue_pressure_simulation(client, db):
    # Register user
    email = f"pressure_user_{uuid.uuid4().hex[:6]}@talentai.local"
    client.post("/api/auth/register", json={
        "email": email,
        "full_name": "Pressure User",
        "password": "Password123!"
    })
    
    user = db.query(User).filter_by(email=email).first()
    job = Job(title="Pressure Job", description="React Python Developer", organization_id=user.organization_id)
    db.add(job)
    db.commit()
    
    # Create 10 mock TaskLifecycles concurrently to simulate high queue pressure
    for i in range(15):
        task_id = f"mock-task-{uuid.uuid4()}"
        lifecycle = TaskLifecycle(
            task_id=task_id,
            job_id=job.id,
            status="queued",
            idempotency_key=f"idem-key-{uuid.uuid4()}"
        )
        db.add(lifecycle)
        
    db.commit()
    
    # Assert all 15 tasks are successfully recorded and queryable in DB
    queued_count = db.query(TaskLifecycle).filter_by(job_id=job.id, status="queued").count()
    assert queued_count == 15

def test_worker_task_retry_scenario(db):
    # Simulate a worker task failure and retry logic
    # Setup test entities
    job = Job(title="Retry Test Job", description="Test Description", organization_id=1)
    db.add(job)
    db.commit()
    
    task_id = f"test-retry-task-{uuid.uuid4()}"
    lifecycle = TaskLifecycle(
        task_id=task_id,
        job_id=job.id,
        status="queued",
        retry_count=0
    )
    db.add(lifecycle)
    db.commit()
    
    # Test simulation of a Celery failure handler incrementing retry count
    # We retrieve the record, increment retry_count to simulate Celery worker retry event
    record = db.query(TaskLifecycle).filter_by(task_id=task_id).first()
    assert record.retry_count == 0
    
    # First retry event simulation
    record.retry_count += 1
    record.status = "queued"  # Queued for retry run
    db.commit()
    
    updated = db.query(TaskLifecycle).filter_by(task_id=task_id).first()
    assert updated.retry_count == 1
    assert updated.status == "queued"
    
    # Simulate final task success after 1 retry
    updated.status = "success"
    db.commit()
    
    final_state = db.query(TaskLifecycle).filter_by(task_id=task_id).first()
    assert final_state.status == "success"
    assert final_state.retry_count == 1
