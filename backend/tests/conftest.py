import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure project root directory is in python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# SQLite in-memory test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import backend.database as db_module
db_module.engine = engine
db_module.SessionLocal = TestingSessionLocal

from backend.database import Base, get_db
from backend.main import app
from backend.models import Organization, User
from backend.auth import get_password_hash, create_access_token
from backend.tasks import celery_app

# Force Celery to execute tasks synchronously during tests
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True

@pytest.fixture(scope="session")
def db_engine():
    yield engine

@pytest.fixture(scope="function")
def db(db_engine):
    # Drop and recreate tables for clean test isolation without nested transaction issues
    Base.metadata.drop_all(bind=db_engine)
    Base.metadata.create_all(bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()

@pytest.fixture(scope="function")
def client(db):
    from backend.main import get_read_db, get_write_db
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_read_db] = override_get_db
    app.dependency_overrides[get_write_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_organization(db):
    org = Organization(name="Test Corporate Inc")
    db.add(org)
    db.commit()
    db.refresh(org)
    return org

@pytest.fixture(scope="function")
def test_admin_user(db, test_organization):
    user = User(
        email="admin@talentai.test",
        full_name="Admin User",
        hashed_password=get_password_hash("adminpass123"),
        role="Admin",
        organization_id=test_organization.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture(scope="function")
def test_recruiter_user(db, test_organization):
    user = User(
        email="recruiter@talentai.test",
        full_name="Recruiter User",
        hashed_password=get_password_hash("recruiterpass123"),
        role="Recruiter",
        organization_id=test_organization.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture(scope="function")
def test_hiring_manager_user(db, test_organization):
    user = User(
        email="manager@talentai.test",
        full_name="Manager User",
        hashed_password=get_password_hash("managerpass123"),
        role="Hiring Manager",
        organization_id=test_organization.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture(scope="function")
def admin_headers(test_admin_user):
    token = create_access_token(data={"sub": test_admin_user.email})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="function")
def recruiter_headers(test_recruiter_user):
    token = create_access_token(data={"sub": test_recruiter_user.email})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="function")
def manager_headers(test_hiring_manager_user):
    token = create_access_token(data={"sub": test_hiring_manager_user.email})
    return {"Authorization": f"Bearer {token}"}
