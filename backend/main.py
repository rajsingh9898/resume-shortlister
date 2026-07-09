import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List

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

@app.post("/api/shortlist")
async def shortlist(jd: str = Form(...), resumes: List[UploadFile] = File(...)):
    if not jd.strip():
        raise HTTPException(status_code=400, detail="Job description text cannot be empty.")
    if not resumes:
        raise HTTPException(status_code=400, detail="Please upload at least one resume.")
        
    resume_data = []
    for res in resumes:
        try:
            contents = await res.read()
            raw_text = nlp_engine.extract_text(res.filename, contents)
            resume_data.append({
                "filename": res.filename,
                "raw_text": raw_text
            })
        except Exception as e:
            # Append filename but with error message to allow system to process other files
            resume_data.append({
                "filename": res.filename,
                "raw_text": f"Error loading file: {str(e)}"
            })
            
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
