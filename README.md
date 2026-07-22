# TalentAI — AI-Based Resume Shortlisting System

**TalentAI** is a premium, lightweight, and highly interactive recruiting intelligence tool designed to automate candidate shortlisting. It parses candidate resumes (PDF, DOCX, TXT) and matches them against Job Descriptions using an advanced NLP pipeline.

Developed as a senior recruiter helper suite for **Raj Singh**.

---

## 🌟 Key Features

1. **High-Efficiency Document Ingest Engine**:
   - Parses multiple resumes concurrently using an asynchronous thread executor.
   - Extracts structured details including years of experience, educational degrees, contact emails, and matched/unmatched skills.

2. **Advanced NLP Semantic Scoring Pipeline**:
   - Computes TF-IDF vector vocabulary mappings.
   - Computes Cosine Similarity between job requirements and resume texts.
   - Applies custom weighting values dynamically (Semantic Similarity, Skills Match, and Experience Match).
   - **Semantic Skill Synonyms**: Maps aliases and abbreviations (e.g. *postgres* to *PostgreSQL*, *pipelines* to *CI/CD*, *GitHub* to *Git*, and *Fast API* to *FastAPI*) for highly accurate parsing.
   - **Soft Traits Extraction**: Automatically detects professional traits: *Leadership & Mentorship*, *System Design & Architecture*, and *Agile Delivery & DevOps*.

3. **Premium Unicorn Silver Design System**:
   - Stunning visual interface with deep metallic slate gradient background and iridescent mesh glows (pastel rose, lavender, cyan).
   - Frosty translucent panels with silver border sheens (`rgba(255, 255, 255, 0.12)`).
   - Reflective chrome silver button gradients (`linear-gradient(135deg, #ffffff, #cbd5e1, #94a3b8)`) for action triggers.

4. **Recruiter Strategy Weight Presets**:
   - Offers quick-set weight presets to shift priorities instantly:
     - **Balanced Fit**: 40% Semantic, 35% Skills, 25% Experience.
     - **Tech Spec**: 20% Semantic, 60% Skills, 20% Experience.
     - **Leader**: 20% Semantic, 20% Skills, 60% Experience.

5. **Enterprise Recruiter Evaluation Suite**:
   - Interactive status tagging (Shortlisted, Under Review, Rejected) per candidate card.
   - Persistent recruiter comments and evaluation notes saved instantly.
   - Heuristic AI Candidate Fit Verdict outputs natural-language qualification summaries.
   - Custom tailored interview screening questions generated dynamically based on candidate skill gaps.
   - **Pros & Cons Analysis Matrix**: Dynamic positive-negative bullet list outlining candidate strengths and development gaps.

6. **Premium Visual Analytics & Portability**:
   - **Concentric SVG Category Coverage Progress Wheel**: Multi-ring concentric charts animating Language, Framework, and Database alignment percentages inside inspection drawers.
   - **Match Tier Distribution Histogram**: Dynamic interactive bar chart grouping candidates into score bands. Clicking histogram bars filters candidates instantly.
   - **Candidate Summary Print PDF Engine**: Exports beautifully formatted printout templates containing verdicts, notes, and screening questions.
   - **Shortlist Comparison Grid**: Side-by-side matrices comparing up to 3 candidates simultaneously.
   - **Database Backup & Restoration (JSON)**: Back up all candidate statuses and notes to a JSON file, or drag-and-drop a backup to restore recruiter comments instantly.

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
