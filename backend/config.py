import os
import warnings
from typing import Optional

# Suppress TensorFlow logging, oneDNN notifications, and general deprecation warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

def find_env_file(filename: str) -> Optional[str]:
    """Helper to locate .env file in backend/ or root directory."""
    curr = os.path.dirname(os.path.abspath(__file__))
    for _ in range(3):
        path = os.path.join(curr, filename)
        if os.path.exists(path):
            return path
        curr = os.path.dirname(curr)
    return None

try:
    from dotenv import load_dotenv
    # Load single configuration .env file
    env_path = find_env_file(".env")
    if env_path:
        load_dotenv(env_path)
except ImportError:
    pass

class Settings:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./talentai.db"
    )
    DIRECT_URL: Optional[str] = os.getenv("DIRECT_URL")
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    if not SECRET_KEY:
        if ENVIRONMENT == "production":
            raise ValueError("SECRET_KEY environment variable must be set in production!")
        SECRET_KEY = "insecure_dev_fallback_secret_key"
        
    ENCRYPTION_KEY: Optional[str] = os.getenv("ENCRYPTION_KEY")
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    
    # S3 Object Storage Configuration
    S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL")
    S3_ACCESS_KEY: Optional[str] = os.getenv("S3_ACCESS_KEY")
    S3_SECRET_KEY: Optional[str] = os.getenv("S3_SECRET_KEY")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "talentai-resumes")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")

settings = Settings()
