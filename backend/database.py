import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost:5432/talentai"
)

# Setup database engine with robust SQLite fallback for offline developer ease
try:
    # Try connecting to PostgreSQL
    if "postgresql" in DATABASE_URL:
        engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 3})
    else:
        engine = create_engine(DATABASE_URL)
    # Test the connection immediately
    with engine.connect() as conn:
        pass
except (OperationalError, Exception) as e:
    print(f"\n[WARNING] PostgreSQL connection to {DATABASE_URL} failed: {str(e)}")
    print("[INFO] Automatically falling back to local SQLite database ('sqlite:///./talentai.db')\n")
    # Fallback SQLite configuration
    SQLITE_URL = "sqlite:///./talentai.db"
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
