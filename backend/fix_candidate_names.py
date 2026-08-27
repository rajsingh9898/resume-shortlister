"""
Migration script to update existing candidate names in the database using their actual names extracted from the resume file text.
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Candidate, Resume
from s3_client import storage_client
from encryption import decrypt_data
import nlp_engine

def clean_filename_to_name(filename: str) -> str:
    clean_name = filename
    clean_name = re.sub(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}-', '', clean_name)
    clean_name = os.path.splitext(clean_name)[0]
    if clean_name.lower().endswith('.txt') or clean_name.lower().endswith('.pdf') or clean_name.lower().endswith('.docx'):
        clean_name = os.path.splitext(clean_name)[0]
    clean_name = clean_name.replace('_', ' ').replace('-', ' ').title()
    return clean_name

def extract_name_from_text(raw_text: str, filename: str) -> str:
    if not raw_text or not raw_text.strip():
        return clean_filename_to_name(filename)
    
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    if not lines:
        return clean_filename_to_name(filename)
    
    first_line = lines[0]
    parts = re.split(r'[,|•\t]', first_line)
    candidate_name = parts[0].strip()
    candidate_name = re.sub(r'\b(CPA|PMP|Ph\.D|PhD|MD|MBA|CFA)\b.*$', '', candidate_name, flags=re.IGNORECASE).strip()
    candidate_name = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b', '', candidate_name).strip()
    candidate_name = re.sub(r'\b\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '', candidate_name).strip()
    
    words = candidate_name.split()
    if not candidate_name or len(words) > 5 or len(candidate_name) > 40 or len(candidate_name) < 2:
        return clean_filename_to_name(filename)
        
    return candidate_name

def run_name_backfill():
    db = SessionLocal()
    try:
        candidates = db.query(Candidate).all()
        updated_count = 0
        
        for cand in candidates:
            # Find the resume record for this candidate
            resume = db.query(Resume).filter_by(candidate_id=cand.id).first()
            if not resume or not resume.file_path:
                print(f"Skipping candidate {cand.name} (ID: {cand.id}) - No resume record or file path found.")
                continue
                
            raw_text = None
            
            # Download file bytes
            try:
                disk_bytes = storage_client.download_bytes(resume.file_path)
                try:
                    file_bytes = decrypt_data(disk_bytes)
                except Exception:
                    file_bytes = disk_bytes
                raw_text = nlp_engine.extract_text(resume.filename, file_bytes)
            except Exception as e:
                print(f"Error reading file {resume.file_path} for candidate {cand.name}: {e}")
                
            # If S3 lookup fails, fallback to local directory scan of dummy_resumes if available
            if not raw_text:
                dummy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dummy_resumes', resume.filename)
                if os.path.exists(dummy_path):
                    try:
                        with open(dummy_path, 'r', encoding='utf-8', errors='ignore') as f:
                            raw_text = f.read()
                    except Exception:
                        pass
                        
            if not raw_text:
                print(f"Skipping candidate {cand.name} (ID: {cand.id}) - Could not load raw text.")
                continue
                
            actual_name = extract_name_from_text(raw_text, resume.filename)
            if actual_name and actual_name != cand.name:
                print(f"Updating Candidate {cand.id}: '{cand.name}' -> '{actual_name}'")
                cand.name = actual_name
                db.commit()
                updated_count += 1
                
        print(f"Successfully backfilled names! Updated {updated_count} candidates.")
    finally:
        db.close()

if __name__ == "__main__":
    run_name_backfill()
