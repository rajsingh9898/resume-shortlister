import io
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Force SQLite memory for this debug script to isolate from real DB
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import backend.database as db_module
db_module.engine = engine
db_module.SessionLocal = TestingSessionLocal

from backend.main import app
from backend.database import Base, SessionLocal
from backend.models import Organization, User, Job
from backend.auth import get_password_hash, create_access_token

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Seed organization
org = Organization(name="Test Org")
db.add(org)
db.commit()
db.refresh(org)

# Seed user
user = User(
    email="admin@test.com",
    full_name="Admin User",
    hashed_password=get_password_hash("password"),
    role="Admin",
    organization_id=org.id
)
db.add(user)
db.commit()
db.refresh(user)

token = create_access_token({"sub": user.email})
headers = {"Authorization": f"Bearer {token}"}

from fastapi.testclient import TestClient
client = TestClient(app)

job = Job(title="FastAPI Expert", description="Experienced backend Python developer.", organization_id=org.id)
db.add(job)
db.commit()
db.refresh(job)

file1 = (io.BytesIO(b"Alex Smith. Python development experience of 5 years. PhD in Computer Science."), "alex.txt")
file2 = (io.BytesIO(b"Bob Vance. Accounting experience of 2 years. High school graduate."), "bob.txt")

files = [
    ("resumes", (file1[1], file1[0], "text/plain")),
    ("resumes", (file2[1], file2[0], "text/plain"))
]

data = {
    "jd": "Must have python experience and CS degree",
    "semantic_weight": 0.5,
    "job_id": job.id
}

print("Posting request...")
res = client.post("/api/shortlist", headers=headers, data=data, files=files)
print("Response status:", res.status_code)
print("Response json:", res.json())
