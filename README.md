# TalentAI — AI-Based Resume Shortlisting System

**TalentAI** is a premium, lightweight, and highly interactive recruiting intelligence tool designed to automate candidate shortlisting. It parses candidate resumes (PDF, DOCX, TXT) and matches them against Job Descriptions using an advanced NLP pipeline.

Developed by **Raj Singh**.

---

## 🌟 Key Features

1. **High-Efficiency Document Ingest Engine**:
   - Parses multiple resumes concurrently using an asynchronous thread executor.
   - Extracts structured details including years of experience, educational degrees, contact emails, and matched/unmatched skills.

2. **Hybrid NLP Semantic Scoring Pipeline**:
   - **Dense Semantic Embeddings**: Uses Sentence-Transformers (`all-MiniLM-L6-v2`) to compute high-dimensional dense vector embeddings of job descriptions and resumes, capturing deep semantic context beyond simple keyword matches.
   - **Sparse TF-IDF Vectorization**: Computes traditional TF-IDF vocabulary mappings and cosine similarity to ensure strict keyword alignment.
   - **Dynamic Hybrid Blending**: Blends semantic transformer similarity and keyword TF-IDF similarity using a configurable sliding weight scale (e.g., 50/50 semantic vs. keyword blend).
   - **Semantic Skill Synonyms**: Maps aliases and abbreviations (e.g., *postgres* to *PostgreSQL*, *pipelines* to *CI/CD*, *GitHub* to *Git*, and *Fast API* to *FastAPI*) for highly accurate parsing.
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

### 1. Database Setup (PostgreSQL)
Ensure you have Docker running on your system, then start the PostgreSQL service container:
```bash
docker-compose up -d
```

Run database migrations to initialize the tables:
```bash
cd backend
alembic upgrade head
```

*Note: If PostgreSQL is not running, the application will print a warning and automatically fall back to a local SQLite database (`backend/talentai.db`) so you can run the app offline or without Docker!*

### 2. Launch the Application
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

### 3. Log In with Test Users
For local testing and evaluation, explore role-based access control using the local seed accounts (Admin, Recruiter, and Hiring Manager). 

> [!WARNING]
> Seed credentials (e.g. `admin@talentai.local`) and default local SQLite storage fallback are provided strictly for offline development and local quick-starts. Always override these variables in staging and production deployment profiles!

---

## 🔒 Security & Production Configuration
To prepare the application for production, configure environment variables securely. Do not commit `.env` files to source control.

| Environment Variable | Description | Recommendation |
| --- | --- | --- |
| `ENVIRONMENT` | Run profile (`development`, `production`) | Set to `production` |
| `SECRET_KEY` | JWT signature key | Generate a random 64-character hex string |
| `DATABASE_URL` | PostgreSQL connection URL | Set connection string scoped to your secure database instance |
| `REDIS_URL` | Redis caching URL | Set connection string scoped to your secure Redis cluster |
| `ENCRYPTION_KEY` | Rest encryption key | Hex-encoded key for database payload encryption |
| `S3_ACCESS_KEY` | Object storage access ID | Configure your secure cloud IAM keys |
| `S3_SECRET_KEY` | Object storage secret key | Configure your secure cloud IAM keys |

---

## 📂 Project Architecture

```
resume-shortlister/
│
├── backend/
│   ├── main.py             # FastAPI Server & REST Endpoints
│   ├── nlp_engine.py       # Sentence-Transformers, TF-IDF, Regex Parsers & NER Extractors
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
Developed and maintained by **Raj Singh**  (AI Engineer) 
