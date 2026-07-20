# TalentAI — AI-Based Resume Shortlisting System

**TalentAI** is a premium, lightweight, and highly interactive recruiting intelligence tool designed to automate candidate shortlisting. It parses candidate resumes (PDF, DOCX, TXT) and matches them against Job Descriptions using an advanced NLP pipeline.

Developed as a senior recruiter helper suite for **Raj Singh**.

---

## 🌟 Key Features

1. **High-Efficiency Document Ingestion Engine**:
   - Parses multiple resumes concurrently using an asynchronous thread executor.
   - Extracts structured details including years of experience, educational degrees, contact emails, and matched/unmatched skills.

2. **Advanced NLP Semantic Scoring Pipeline**:
   - Computes TF-IDF vector vocabulary mappings.
   - Computes Cosine Similarity between job requirements and resume texts.
   - Applies custom weighting values dynamically (Semantic Similarity, Skills Match, and Experience Match).

3. **Enterprise Recruiter Evaluation Suite (LocalStorage Binding)**:
   - Interactive status tagging (Shortlisted, Under Review, Rejected) per candidate card.
   - Persistent recruiter comments and evaluation notes saved instantly.
   - Heuristic AI Candidate Fit Verdict outputs natural-language qualification summaries.
   - Custom tailored interview screening questions generated dynamically based on candidate skill gaps.

4. **Premium Visual Analytics & Reports Layout**:
   - **Concentric SVG Category Coverage Progress Wheel**: Multi-ring concentric charts animating Language, Framework, and Database alignment percentages inside inspection drawers.
   - **Match Tier Distribution Histogram**: Dynamic interactive bar chart grouping candidates into score bands (Low, Mid, Strong). Clicking histogram bars filters candidates instantly.
   - **Candidate Pool Skill Frequency Chart**: Visual bar indicators illustrating common skills.
   - **Candidate Summary Print PDF Engine**: Exports beautifully formatted printout templates containing verdicts, notes, and screening questions.
   - **Shortlist Comparison Grid**: Side-by-side matrices comparing up to 3 candidates simultaneously.
   - **Match Score Threshold Filter**: Dynamic range slider to screen out low-matching resumes instantly.

---

## 🚀 Quick Start Guide

Double-click the launcher script in the project directory to launch the server and open the browser automatically:
```powershell
./start.bat
```

Alternatively, launch the FastAPI server manually:
```bash
cd backend
python main.py
```
Then navigate to `http://127.0.0.1:8000` in your web browser.

---

## 📂 Project Architecture

```
resume-shortlister/
│
├── backend/
│   ├── main.py             # FastAPI Server & REST Endpoints
│   ├── nlp_engine.py       # TF-IDF, Regex Parsers & NER Skill Extractors
│   └── test_nlp.py         # Backend NLP engine validator
│
├── frontend/
│   ├── index.html          # Dashboard HTML Layout
│   ├── style.css           # Glassmorphism Styling & Print templates
│   └── app.js              # State Controllers & Visualizations
│
├── dummy_resumes/          # Mock Resumes for testing
├── screenshots/            # UI recordings and screenshots
├── requirements.txt        # Backend dependencies
└── start.bat               # Desktop launcher script
```

---

## 👥 Authorship
Developed and maintained by **Raj Singh** (Senior Recruiter / AI Specialist).
