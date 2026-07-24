import sys
import os
import io
import time
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from database import Base, engine, SessionLocal
from models import AuditLog, Candidate, Resume, Evaluation
from encryption import decrypt_data

client = TestClient(app)

def test_security_suite():
    print("--- Starting Phase 3 Security & Compliance Validation Tests ---")
    
    # 1. Reset Database State
    print("Resetting database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # 2. Register & Login Test Admin
    print("Seeding compliance admin user...")
    reg_res = client.post("/api/auth/register", json={
        "email": "security_admin@talentai.local",
        "full_name": "Security Admin",
        "password": "password123",
        "role": "Admin",
        "organization_name": "Compliance Corp"
    })
    assert reg_res.status_code == 200
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. File Validation Whitelist Checks
    print("Testing extension whitelist validation (expect 400)...")
    bad_ext_res = client.post(
        "/api/shortlist",
        headers=headers,
        data={"jd": "Python Developer"},
        files={"resumes": ("test_pic.png", b"fake png bytes", "image/png")}
    )
    assert bad_ext_res.status_code == 400
    assert "Unsupported file format" in bad_ext_res.json()["detail"]
    
    # 4. File Size Limits Checks
    print("Testing file size limits validation (expect 400)...")
    oversized_bytes = b"X" * (5 * 1024 * 1024 + 100)  # > 5MB
    large_file_res = client.post(
        "/api/shortlist",
        headers=headers,
        data={"jd": "Python Developer"},
        files={"resumes": ("large.txt", oversized_bytes, "text/plain")}
    )
    assert large_file_res.status_code == 400
    assert "File too large" in large_file_res.json()["detail"]
    
    # 5. Corruption Checks
    print("Testing corrupted PDF check (expect 400)...")
    corrupt_pdf_bytes = b"%PDF-1.4 malformed content that is not a real pdf"
    corrupt_res = client.post(
        "/api/shortlist",
        headers=headers,
        data={"jd": "Python Developer"},
        files={"resumes": ("corrupt.pdf", corrupt_pdf_bytes, "application/pdf")}
    )
    assert corrupt_res.status_code == 400
    assert "Corrupted or malformed file" in corrupt_res.json()["detail"]
    
    # 6. Encryption at Rest & Database Isolation
    print("Testing successful shortlist + encryption at rest...")
    valid_text_resume = b"Skills: Python, FastAPI, Git, Postgres, CI/CD. Experience: 6 years. Degree: PhD"
    ok_res = client.post(
        "/api/shortlist",
        headers=headers,
        data={"jd": "Python Developer FastAPI Postgres"},
        files={"resumes": ("john_doe.txt", valid_text_resume, "text/plain")}
    )
    assert ok_res.status_code == 200
    job_id = ok_res.json()["job_id"]
    
    # Verify file is written encrypted on disk
    db = SessionLocal()
    try:
        resume_record = db.query(Resume).filter_by(filename="john_doe.txt").first()
        assert resume_record is not None
        assert os.path.exists(resume_record.file_path)
        
        # Read file from disk directly and verify it is encrypted
        with open(resume_record.file_path, "rb") as f:
            disk_bytes = f.read()
            
        # Raw text should not be present in the encrypted disk content
        assert b"Skills: Python" not in disk_bytes
        
        # Decrypted content matches the original upload bytes
        decrypted_bytes = decrypt_data(disk_bytes)
        assert decrypted_bytes == valid_text_resume
        print("Encryption at rest verified successfully!")
        
        # 7. AuditLog tracking on Status updates
        print("Updating candidate status (testing transition audit logs)...")
        status_res = client.post(
            "/api/evaluation/update",
            headers=headers,
            json={
                "job_id": job_id,
                "filename": "john_doe.txt",
                "status": "Shortlisted"
            }
        )
        assert status_res.status_code == 200
        
        # Check AuditLog for STATUS_CHANGE
        status_audit = db.query(AuditLog).filter_by(action="STATUS_CHANGE").first()
        assert status_audit is not None
        assert "Shortlisted" in status_audit.details
        print("Status update audit log verified!")
        
        # 8. Candidate Deletion & GDPR Purge
        candidate_record = db.query(Candidate).filter_by(name="john_doe.txt").first()
        assert candidate_record is not None
        cand_id = candidate_record.id
        
        print("Deleting candidate (GDPR Purge)...")
        del_res = client.delete(f"/api/candidates/{cand_id}", headers=headers)
        assert del_res.status_code == 200
        
        # Assert file is physically deleted from disk
        assert not os.path.exists(resume_record.file_path)
        print("Physical resume file successfully deleted from disk!")
        
        # Check database records are purged (cascades)
        assert db.query(Candidate).filter_by(id=cand_id).first() is None
        assert db.query(Resume).filter_by(candidate_id=cand_id).first() is None
        assert db.query(Evaluation).filter_by(candidate_id=cand_id).first() is None
        
        # Check AuditLog for GDPR_PURGE
        purge_audit = db.query(AuditLog).filter_by(action="GDPR_PURGE").first()
        assert purge_audit is not None
        assert "john_doe.txt" in purge_audit.details
        print("GDPR Purge audit logging verified!")
        
        # 9. Rate Limiting verification
        print("Testing rate limiting on login endpoint (expect 429 after 5 requests)...")
        rate_limited = False
        for i in range(10):
            login_res = client.post("/api/auth/login", data={
                "username": "security_admin@talentai.local",
                "password": "wrongpassword"
            })
            if login_res.status_code == 429:
                rate_limited = True
                break
        assert rate_limited, "Rate limiting did not trigger a 429 error!"
        print("Rate limiting verified successfully!")
        
        print("\nSUCCESS: All Phase 3 Security & Compliance tests passed successfully!")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_security_suite()
