"""
One-time migration script to re-extract emails from resume files on disk
and update candidate records with the correct email addresses.
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from models import Candidate, Resume

def extract_text_from_file(file_path):
    """Read text from a file, handling .txt and .pdf formats."""
    if not os.path.exists(file_path):
        return None
    
    if file_path.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    elif file_path.endswith('.pdf'):
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            print(f"  Error reading PDF {file_path}: {e}")
            return None
    return None

def fix_candidate_emails():
    db = SessionLocal()
    try:
        # Also try reading from the S3 local fallback storage
        try:
            from s3_client import storage_client
            import nlp_engine
            has_storage = True
        except Exception:
            has_storage = False
            
        # Get all candidates with their resumes
        candidates = db.query(Candidate).all()
        updated = 0
        skipped = 0
        
        for candidate in candidates:
            resume = db.query(Resume).filter_by(candidate_id=candidate.id).first()
            if not resume:
                print(f"  SKIP: {candidate.name} (ID: {candidate.id}) -- no resume record")
                skipped += 1
                continue
            
            raw_text = None
            
            # Strategy 1: Try reading the extracted text from S3 storage (.txt version)
            if has_storage and resume.file_path:
                try:
                    text_key = resume.file_path + ".txt"
                    text_bytes = storage_client.download_bytes(text_key)
                    if text_bytes:
                        raw_text = text_bytes.decode('utf-8', errors='ignore')
                except Exception:
                    pass
            
            # Strategy 2: Try reading the original file from S3 storage
            if not raw_text and has_storage and resume.file_path:
                try:
                    file_bytes = storage_client.download_bytes(resume.file_path)
                    if file_bytes:
                        raw_text = nlp_engine.extract_text(resume.filename, file_bytes)
                except Exception:
                    pass
            
            # Strategy 3: Try reading from dummy_resumes directory
            if not raw_text:
                dummy_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dummy_resumes')
                possible_path = os.path.join(dummy_dir, resume.filename)
                raw_text = extract_text_from_file(possible_path)
            
            if not raw_text:
                print(f"  SKIP: {candidate.name} (ID: {candidate.id}) -- could not read resume text from any source")
                skipped += 1
                continue
            
            # Extract email from resume text
            email_match = re.search(r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b', raw_text)
            extracted_email = email_match.group(0) if email_match else None
            
            old_email = candidate.email
            if extracted_email and extracted_email != old_email:
                candidate.email = extracted_email
                db.commit()
                print(f"  UPDATED: {candidate.name} (ID: {candidate.id}): {old_email} -> {extracted_email}")
                updated += 1
            elif extracted_email and extracted_email == old_email:
                print(f"  OK: {candidate.name} (ID: {candidate.id}): already correct ({old_email})")
            else:
                print(f"  NO EMAIL: {candidate.name} (ID: {candidate.id}) -- no email pattern found in resume")
                skipped += 1
                
        print(f"\nDone. Updated: {updated}, Skipped: {skipped}, Total: {len(candidates)}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_candidate_emails()