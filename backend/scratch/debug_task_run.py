import io
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Force SQLite memory
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

from backend.database import Base, SessionLocal
from backend.models import Organization, User, Job, Candidate, Resume, Score
from backend.tasks import process_shortlist_task

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Seed Org & Job
org = Organization(name="Test Org")
db.add(org)
db.commit()

job = Job(title="FastAPI Expert", description="Experienced backend Python developer.", organization_id=org.id)
db.add(job)
db.commit()

# Create files info list
resumes_info = [
    {"filename": "alex.txt", "file_path": "mock_alex_path"},
    {"filename": "bob.txt", "file_path": "mock_bob_path"}
]

# Mock decrypt and read
import backend.tasks as tasks_module
import backend.nlp_engine as nlp_engine

# We mock decrypt_data and nlp_engine.extract_text to avoid hitting disk or complex parsing
tasks_module.decrypt_data = lambda data: data
nlp_engine.extract_text = lambda name, content: "Mock resume text with 5 years experience Python" if "alex" in name else "Mock accounting resume text"

print("Running process_shortlist_task synchronously...")
try:
    # Run the task directly (not async)
    result = process_shortlist_task(job.id, resumes_info, 0.5, 1)
    print("Task result:", result)
except Exception as e:
    import traceback
    print("EXCEPTION IN TASK:")
    traceback.print_exc()

print("\nQuerying Database candidates:")
cands = db.query(Candidate).all()
print("Number of candidates:", len(cands))
for c in cands:
    print(f"Candidate: {c.name}, Exp: {c.experience_years}")
