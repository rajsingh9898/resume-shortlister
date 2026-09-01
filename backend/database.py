import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

try:
    from backend.config import settings
except ImportError:
    from config import settings

DATABASE_URL = settings.DATABASE_URL

# Setup database engine with robust SQLite fallback for offline developer ease
try:
    # Try connecting to PostgreSQL
    if "postgresql" in DATABASE_URL:
        # Strip pgbouncer parameter if present to avoid psycopg2 DSN validation error
        cleaned_url = DATABASE_URL
        if "pgbouncer=" in cleaned_url:
            import urllib.parse
            parsed = urllib.parse.urlparse(cleaned_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            query_params.pop("pgbouncer", None)
            new_query = urllib.parse.urlencode(query_params, doseq=True)
            cleaned_url = urllib.parse.urlunparse(parsed._replace(query=new_query))
        
        engine = create_engine(
            cleaned_url,
            pool_size=30,
            max_overflow=20,
            pool_recycle=1800,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10}
        )
    else:
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False, "timeout": 60} if "sqlite" in DATABASE_URL else {},
            pool_pre_ping=True
        )
    # Test the connection immediately and set WAL mode for SQLite
    with engine.connect() as conn:
        if "sqlite" in str(engine.url):
            try:
                from sqlalchemy import text
                conn.execute(text("PRAGMA journal_mode=WAL;"))
                conn.execute(text("PRAGMA synchronous=NORMAL;"))
            except Exception:
                pass
except (OperationalError, Exception) as e:
    print(f"\n[WARNING] PostgreSQL connection to {DATABASE_URL} failed: {str(e)}")
    print("[INFO] Automatically falling back to local SQLite database ('sqlite:///./talentai.db')\n")
    # Fallback SQLite configuration with 60s timeout & WAL mode
    SQLITE_URL = "sqlite:///./talentai.db"
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False, "timeout": 60},
        pool_pre_ping=True
    )
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            conn.execute(text("PRAGMA synchronous=NORMAL;"))
    except Exception:
        pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- THEME-SAFE LOCAL CANDIDATES CACHE ---
import threading

class LocalCandidatesCache:
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
        
    def get(self, job_id: int):
        with self._lock:
            return self._cache.get(job_id)
            
    def set(self, job_id: int, data):
        with self._lock:
            self._cache[job_id] = data
            
    def invalidate(self, job_id: int):
        with self._lock:
            self._cache.pop(job_id, None)
            
    def clear(self):
        with self._lock:
            self._cache.clear()

candidates_local_cache = LocalCandidatesCache()
