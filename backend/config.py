import os
from typing import Optional

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
        "postgresql://postgres:postgres@localhost:5432/talentai"
    )
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "iridescent_unicorn_silver_secret_token_key_123456789"
    )
    ENCRYPTION_KEY: Optional[str] = os.getenv("ENCRYPTION_KEY")
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")

settings = Settings()
