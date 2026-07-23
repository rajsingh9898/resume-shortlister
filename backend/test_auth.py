import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from database import Base, engine, SessionLocal
from models import Organization, User, Candidate, Resume, Evaluation

client = TestClient(app)

def run_auth_tests():
    print("--- Starting Phase 2 Auth & Multi-Tenancy Validation Tests ---")
    
    # 1. Setup Fresh Database
    print("Initializing test tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # 2. Test Registration (Admin in Org A)
    print("Registering Admin user for Org A...")
    reg_res_a = client.post("/api/auth/register", json={
        "email": "admin_a@talentai.local",
        "full_name": "Admin A",
        "password": "password123",
        "role": "Admin",
        "organization_name": "Org A"
    })
    assert reg_res_a.status_code == 200
    token_a = reg_res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    # 3. Test Registration (Hiring Manager in Org B)
    print("Registering Hiring Manager user for Org B...")
    reg_res_b = client.post("/api/auth/register", json={
        "email": "manager_b@talentai.local",
        "full_name": "Manager B",
        "password": "password123",
        "role": "Hiring Manager",
        "organization_name": "Org B"
    })
    assert reg_res_b.status_code == 200
    token_b = reg_res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # 4. Test Login
    print("Testing Login endpoint...")
    login_res = client.post("/api/auth/login", data={
        "username": "admin_a@talentai.local",
        "password": "password123"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()
    
    # 5. Test Profile endpoint
    print("Testing Profile (/api/auth/me) endpoint...")
    me_res = client.get("/api/auth/me", headers=headers_a)
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "Admin"
    assert me_res.json()["organization"]["name"] == "Org A"
    
    # 6. Test Route Protection (Expect 401 without token)
    print("Testing Route Protection on shortlist (expect 401)...")
    unauth_res = client.post("/api/shortlist")
    assert unauth_res.status_code == 401
    
    # 7. Test Multi-Tenancy Data Isolation
    print("Testing Multi-Tenancy database candidate/evaluation isolation...")
    # Add a mock candidate shell under Org A
    db = SessionLocal()
    try:
        org_a = db.query(Organization).filter_by(name="Org A").first()
        org_b = db.query(Organization).filter_by(name="Org B").first()
        
        # Save candidate for Org A
        cand_a = Candidate(name="candidate_a.pdf", organization_id=org_a.id)
        db.add(cand_a)
        db.commit()
        db.refresh(cand_a)
        res_a = Resume(candidate_id=cand_a.id, filename="candidate_a.pdf", file_path="/storage/candidate_a.pdf", raw_text="")
        db.add(res_a)
        db.commit()
        
        # Save candidate for Org B
        cand_b = Candidate(name="candidate_b.pdf", organization_id=org_b.id)
        db.add(cand_b)
        db.commit()
        db.refresh(cand_b)
        res_b = Resume(candidate_id=cand_b.id, filename="candidate_b.pdf", file_path="/storage/candidate_b.pdf", raw_text="")
        db.add(res_b)
        db.commit()
        
        # Let's test if User B can view candidate A evaluations
        # 8. Test Role Permission Restriction
        print("Testing Hiring Manager status update block (expect 403)...")
        # Hiring Manager B tries to update candidate_b status to Shortlisted
        eval_update_res = client.post("/api/evaluation/update", headers=headers_b, json={
            "filename": "candidate_b.pdf",
            "status": "Shortlisted"
        })
        # Should be blocked since Manager B is a Hiring Manager (read + comments only)
        assert eval_update_res.status_code == 403
        
        # Hiring Manager B tries to update candidate_b comments (should succeed!)
        print("Testing Hiring Manager comment update (expect 200)...")
        eval_update_comments_res = client.post("/api/evaluation/update", headers=headers_b, json={
            "filename": "candidate_b.pdf",
            "comments": "Great soft skills."
        })
        assert eval_update_comments_res.status_code == 200
        
        # Verify comment is saved
        eval_db = db.query(Evaluation).filter_by(candidate_id=cand_b.id).first()
        assert eval_db is not None
        assert eval_db.comments == "Great soft skills."
        
        # Admin A tries to update candidate B status (should be blocked or created in A, since they cannot see candidate B!)
        # Because candidate B belongs to Org B, Admin A query won't find candidate B and will create a new candidate_b shell in Org A!
        print("Testing Multi-Tenancy candidate filename overlap separation...")
        admin_update_res = client.post("/api/evaluation/update", headers=headers_a, json={
            "filename": "candidate_b.pdf",
            "status": "Shortlisted"
        })
        assert admin_update_res.status_code == 200
        
        # Check that Admin A created candidate_b in Org A, without modifying candidate_b in Org B
        cand_b_org_a = db.query(Candidate).filter_by(name="candidate_b.pdf", organization_id=org_a.id).first()
        assert cand_b_org_a is not None, "Candidate should be created inside Admin A's organization"
        
        # Candidate B in Org B should not have its status changed to Shortlisted by Admin A
        eval_b_org_b = db.query(Evaluation).filter_by(candidate_id=cand_b.id).first()
        assert eval_b_org_b.status != "Shortlisted", "Candidate in Org B was incorrectly modified by Admin in Org A!"
        
        print("\nSUCCESS: All Auth & Multi-Tenancy tests passed successfully!")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_auth_tests()
