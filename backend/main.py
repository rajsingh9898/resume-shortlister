import os
import uvicorn
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List
from concurrent.futures import ThreadPoolExecutor

# Import our NLP parser
try:
    from backend import nlp_engine
except ImportError:
    import nlp_engine

app = FastAPI(title="AI-Based Resume Shortlisting System")

# Enable CORS for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Allocate thread pool executor for CPU-bound document parsing tasks (PDF/DOCX rendering)
executor = ThreadPoolExecutor(max_workers=6)

def parse_document_sync(filename: str, file_bytes: bytes) -> str:
    """Helper executed in a worker thread to extract document text without blocking the event loop."""
    return nlp_engine.extract_text(filename, file_bytes)

@app.post("/api/shortlist")
async def shortlist(jd: str = Form(...), resumes: List[UploadFile] = File(...)):
    if not jd.strip():
        raise HTTPException(status_code=400, detail="Job description text cannot be empty.")
    if not resumes:
        raise HTTPException(status_code=400, detail="Please upload at least one resume.")
        
    try:
        # 1. Concurrently read file contents from FastAPI upload streams (Async I/O)
        read_tasks = [res.read() for res in resumes]
        file_contents = await asyncio.gather(*read_tasks)
        
        # 2. Concurrently extract text from files offloaded to thread executor (Parallel CPU operations)
        loop = asyncio.get_running_loop()
        parse_tasks = []
        for idx, res in enumerate(resumes):
            task = loop.run_in_executor(
                executor, 
                parse_document_sync, 
                res.filename, 
                file_contents[idx]
            )
            parse_tasks.append(task)
            
        parsed_texts = await asyncio.gather(*parse_tasks)
        
        # Assemble resume data structure
        resume_data = []
        for idx, res in enumerate(resumes):
            resume_data.append({
                "filename": res.filename,
                "raw_text": parsed_texts[idx]
            })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Concurrently reading/parsing documents failed: {str(e)}")
            
    try:
        results = nlp_engine.compute_nlp_shortlist(jd, resume_data)
        return {
            "success": True, 
            "candidates": results["candidates"],
            "jd_requirements": results["jd_requirements"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NLP computations failed: {str(e)}")

# Locate the frontend directory path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../frontend"))

# Route to serve page
@app.get("/")
def get_home():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend files not found. Ensure the frontend/ folder exists."}

# Mount static files for assets, stylesheet and scripts (after specific API and root routes)
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
