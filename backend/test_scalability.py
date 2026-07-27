import os
import sys
import unittest
import json
import redis

# Setup backend import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, Base, engine
from models import Organization, User, Job, Candidate, Resume, Score, Evaluation
import tasks

class TestScalabilityAndPerformance(unittest.TestCase):
    def setUp(self):
        # Initialize SQLite database for local test runs
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        
        # Clear or verify Redis caching connection
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis = redis.Redis.from_url(self.redis_url, decode_responses=True)
            self.redis.ping()
            self.redis_connected = True
        except Exception:
            self.redis_connected = False

        # Seed test organization and job
        self.org = Organization(name="Test Scalability Org")
        self.db.add(self.org)
        self.db.commit()
        self.db.refresh(self.org)
        
        self.job = Job(title="Scalability Job", description="FastAPI developer with Python skills", organization_id=self.org.id)
        self.db.add(self.job)
        self.db.commit()
        self.db.refresh(self.job)

    def tearDown(self):
        self.db.close()
        # Drop testing schema elements
        Base.metadata.drop_all(bind=engine)
        if self.redis_connected:
            try:
                # Clear test namespace keys
                keys = self.redis.keys("job_candidates:*")
                if keys:
                    self.redis.delete(*keys)
            except Exception:
                pass

    def test_redis_caching_layer(self):
        """Validates cache write, read, and invalidation behaviors."""
        if not self.redis_connected:
            self.skipTest("Redis not running locally - skipping cache test.")
            
        test_key = f"job_candidates:{self.job.id}:page:1:limit:10:filter:none:threshold:0:search:none:sw:40.0:skw:30.0:exw:30.0"
        test_payload = {"candidates": [{"filename": "resume1.pdf", "score": 90.0}], "total_pages": 1}
        
        # Set cache
        self.redis.setex(test_key, 60, json.dumps(test_payload))
        
        # Read cache
        cached_val = self.redis.get(test_key)
        self.assertIsNotNone(cached_val)
        self.assertEqual(json.loads(cached_val)["candidates"][0]["filename"], "resume1.pdf")
        
        # Invalidate cache
        keys = self.redis.keys(f"job_candidates:{self.job.id}:*")
        if keys:
            self.redis.delete(*keys)
            
        self.assertIsNone(self.redis.get(test_key))

    def test_celery_task_compilation(self):
        """Validates that Celery worker app parses imports and maps task targets correctly."""
        self.assertIsNotNone(tasks.celery_app)
        self.assertTrue(
            "backend.tasks.process_shortlist_task" in tasks.celery_app.tasks or
            "tasks.process_shortlist_task" in tasks.celery_app.tasks
        )

if __name__ == "__main__":
    unittest.main()
