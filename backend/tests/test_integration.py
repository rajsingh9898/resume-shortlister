import io
import os
import sys
import pytest
from fastapi import status

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_auth_protected_routes(client):
    # Calling candidates endpoint without token should return 401
    res = client.get("/api/jobs/1/candidates")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Register/login with invalid credentials
    res = client.post("/api/auth/login", data={"username": "notfound@test.com", "password": "any"})
    assert res.status_code == status.HTTP_400_BAD_REQUEST

def test_role_based_access_controls(client, db, test_organization, admin_headers, recruiter_headers, manager_headers):
    # Setup a job first
    from backend.models import Job
    job = Job(title="QA Engineer", description="Testing engineer", organization_id=test_organization.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # 1. Hiring Manager should NOT be able to delete job
    res = client.delete(f"/api/jobs/{job.id}", headers=manager_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 2. Recruiter should NOT be able to delete job (only Admin has full deletion capabilities)
    res = client.delete(f"/api/jobs/{job.id}", headers=recruiter_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 3. Admin should be able to delete job
    res = client.delete(f"/api/jobs/{job.id}", headers=admin_headers)
    assert res.status_code == 200

def test_main_shortlisting_api_flow(client, db, test_organization, admin_headers):
    # 1. Create a Job Description
    from backend.models import Job
    job = Job(title="FastAPI Expert", description="Experienced backend Python developer.", organization_id=test_organization.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # 2. Get pre-signed upload URLs and upload files using mock endpoints
    res_presign1 = client.post("/api/storage/presign-upload", headers=admin_headers, json={"filename": "alex.txt", "content_type": "text/plain"})
    assert res_presign1.status_code == 200
    p1 = res_presign1.json()
    alex_key = p1["object_key"]
    
    # PUT directly to upload URL (points to mock upload under offline fallback)
    res_upload1 = client.put(p1["upload_url"], content=b"Alex Smith. Python development experience of 5 years. PhD in Computer Science.")
    assert res_upload1.status_code == 200
    
    res_presign2 = client.post("/api/storage/presign-upload", headers=admin_headers, json={"filename": "bob.txt", "content_type": "text/plain"})
    assert res_presign2.status_code == 200
    p2 = res_presign2.json()
    bob_key = p2["object_key"]
    
    res_upload2 = client.put(p2["upload_url"], content=b"Bob Vance. Accounting experience of 2 years. High school graduate.")
    assert res_upload2.status_code == 200
    
    # 3. Post shortlist request with JSON body
    shortlist_data = {
        "jd": "Must have python experience and CS degree",
        "semantic_weight": 0.5,
        "resumes": [
            {"filename": "alex.txt", "object_key": alex_key},
            {"filename": "bob.txt", "object_key": bob_key}
        ]
    }
    res = client.post("/api/shortlist", headers=admin_headers, json=shortlist_data)
    if res.status_code != 200:
        print("ERROR RESPONSE:", res.text)
    assert res.status_code == 200
    resp_data = res.json()
    assert "task_id" in resp_data
    assert "job_id" in resp_data
    
    # 3. Retrieve task progress
    task_id = resp_data["task_id"]
    res_task = client.get(f"/api/tasks/{task_id}", headers=admin_headers)
    assert res_task.status_code == 200
    print("TASK RESPONSE JSON:", res_task.json())
    assert res_task.json()["status"] == "SUCCESS"
    
    # 4. Fetch Paginated candidate rankings list
    db.commit()
    res_list = client.get(f"/api/jobs/{resp_data['job_id']}/candidates?page=1&limit=10", headers=admin_headers)
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert "candidates" in list_data
    assert list_data["total_count"] == 2
    
    # Verify rankings: candidate with python and PhD (Alex) should rank first
    cands = list_data["candidates"]
    assert cands[0]["filename"] == "alex.txt"
    assert cands[1]["filename"] == "bob.txt"
    
    # Assert model version and explainability
    assert "model_version" in cands[0]
    assert cands[0]["model_version"] == "v2.1.0"
    assert "explainability" in cands[0]
    assert "reasons_high" in cands[0]["explainability"]
    assert "reasons_low" in cands[0]["explainability"]
    
    # 5. Update candidate evaluation status
    alex_id = cands[0]["id"]
    res_eval = client.post("/api/evaluation/update", headers=admin_headers, json={
        "job_id": resp_data["job_id"],
        "filename": "alex.txt",
        "status": "Shortlisted",
        "comments": "Superb profile!"
    })
    assert res_eval.status_code == 200
    
    # 6. Export database backup
    res_export = client.get("/api/backup/export", headers=admin_headers)
    assert res_export.status_code == 200
    export_resp = res_export.json()
    assert "download_url" in export_resp
    
    # Download the backup file directly from storage
    download_url = export_resp["download_url"]
    res_download = client.get(download_url, headers=admin_headers)
    assert res_download.status_code == 200
    backup_data = res_download.json()
    assert "talentai_status_alex.txt" in backup_data
    
    # 7. Purge candidate (GDPR Forgotten Check)
    res_del = client.delete(f"/api/candidates/{alex_id}", headers=admin_headers)
    assert res_del.status_code == 200
    
    # Verify candidate is removed from list
    res_list_after = client.get(f"/api/jobs/{resp_data['job_id']}/candidates?page=1&limit=10", headers=admin_headers)
    assert len(res_list_after.json()["candidates"]) == 1
