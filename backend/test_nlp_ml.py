import json
import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi import UploadFile

# Set environment variable to run tests offline/mocked if needed
os.environ["DATABASE_URL"] = "sqlite:///./test_talentai_temp.db"

import nlp_engine
from main import app
from models import Candidate
from database import SessionLocal, engine, Base

class TestNLPMLUpgrade(unittest.TestCase):
    
    def setUp(self):
        # Create temp sqlite database
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        
    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("./test_talentai_temp.db"):
            try:
                os.remove("./test_talentai_temp.db")
            except Exception:
                pass

    def test_skills_taxonomy_loaded(self):
        """Verifies skills taxonomy has been populated either from json or default fallbacks."""
        self.assertIsNotNone(nlp_engine.SKILLS_DB)
        self.assertIsNotNone(nlp_engine.SKILL_SYNONYMS)
        self.assertTrue("Languages" in nlp_engine.SKILLS_DB)
        self.assertTrue("PostgreSQL" in nlp_engine.SKILL_SYNONYMS)

    def test_experience_confidence_scoring(self):
        """Tests that experience parsing yields appropriate years and confidence flags."""
        # High certainty match
        exp1, conf1 = nlp_engine.parse_experience_years_with_confidence(
            "Experienced Python engineer with 6 years of experience working with FastAPI."
        )
        self.assertEqual(exp1, 6.0)
        self.assertGreaterEqual(conf1, 0.8) # High confidence

        # Low certainty/ambiguous match
        exp2, conf2 = nlp_engine.parse_experience_years_with_confidence(
            "I spent 4 years working in the UK. I also did Docker."
        )
        self.assertEqual(exp2, 4.0)
        self.assertLess(conf2, 0.7) # Low confidence

        # No experience listed
        exp3, conf3 = nlp_engine.parse_experience_years_with_confidence(
            "Fresh graduate looking for opportunities."
        )
        self.assertEqual(exp3, 0.0)
        self.assertGreaterEqual(conf3, 0.9) # High confidence that none is listed

    def test_education_confidence_scoring(self):
        """Tests education degree parser outputs correct categories and confidence metrics."""
        # High certainty
        deg1, conf1 = nlp_engine.parse_education_degrees_with_confidence(
            "I hold a Bachelor of Science and a Master of Science in CS."
        )
        self.assertTrue("Bachelor" in deg1)
        self.assertTrue("Master" in deg1)
        self.assertGreaterEqual(conf1, 0.8)

        # Low certainty
        deg2, conf2 = nlp_engine.parse_education_degrees_with_confidence(
            "Completed some MS courses."
        )
        self.assertTrue("Master" in deg2)
        self.assertLess(conf2, 0.7)

    def test_pearson_correlation(self):
        """Validates the Pearson correlation coefficient calculations."""
        x = [10, 20, 30, 40]
        y = [2, 4, 6, 8]
        corr = nlp_engine.pearson_correlation(x, y)
        self.assertAlmostEqual(corr, 1.0)

        x_rev = [10, 20, 30, 40]
        y_rev = [8, 6, 4, 2]
        corr_rev = nlp_engine.pearson_correlation(x_rev, y_rev)
        self.assertAlmostEqual(corr_rev, -1.0)

    def test_nlp_shortlist_bias_checks(self):
        """Ensures that nlp engine compute detects correlation and returns appropriate alerts."""
        jd = "Looking for Python FastAPI developer with 5 years experience"
        
        # We craft resumes that correlate score exactly with length to trigger length bias
        # Resume 1: matches skills, high length
        resumes = [
            {
                "filename": "good.txt",
                "raw_text": "Python FastAPI developer. " + "word " * 1000 + " 5 years of experience."
            },
            {
                "filename": "poor.txt",
                "raw_text": "Short resume. 1 year."
            }
        ]
        
        results = nlp_engine.compute_nlp_shortlist(jd, resumes, semantic_weight=0.0)
        self.assertIn("candidates", results)
        
        # Verify that bias warnings list is present
        self.assertIn("bias_warnings", results)
        # Should flag bias since good has high score/length, poor has low score/length
        has_len_warning = any("resume length" in w for w in results["bias_warnings"])
        self.assertTrue(has_len_warning, "Should flag resume length bias alert")

if __name__ == "__main__":
    unittest.main()
