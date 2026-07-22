import io
import re
import PyPDF2
import docx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Hardcoded common English stopwords to ensure offline reliability
STOPWORDS = set([
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them",
    "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does",
    "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of",
    "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "s", "t", "can", "will", "just", "don", "should", "now", "of", "in", "to", "for", "with", "on", "at", "by",
    "from", "up", "about", "into", "over", "after"
])

# Large lexicon of common technical and professional skills for NER/extraction
SKILLS_DB = {
    "Languages": [
        "python", "javascript", "typescript", "java", "c\\+\\+", "c#", "ruby", "golang", "rust", 
        "php", "html", "css", "sql", "r", "swift", "kotlin", "scala", "perl", "bash", "shell"
    ],
    "Frameworks & Libraries": [
        "react", "angular", "vue", "next\\.js", "node\\.js", "express", "django", "flask", "fastapi", 
        "spring boot", "laravel", "rails", "asp\\.net", "tensorflow", "pytorch", "keras", "pandas", 
        "numpy", "scikit-learn", "scipy", "jquery", "bootstrap", "tailwind", "nextjs", "nodejs", 
        "spring", "dotnet", "react native", "flutter", "vuejs"
    ],
    "Databases & Tools": [
        "postgresql", "mysql", "mongodb", "redis", "sqlite", "oracle", "sql server", "dynamodb", 
        "elasticsearch", "cassandra", "firebase", "neo4j", "mariadb", "postgres"
    ],
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "docker", "kubernetes", "git", "github", "gitlab", "jenkins", 
        "terraform", "ansible", "ci/cd", "linux", "nginx", "apache", "kubernetes", "circleci", 
        "amazon web services", "google cloud"
    ],
    "Methodologies & Domains": [
        "agile", "scrum", "project management", "machine learning", "deep learning", "nlp", 
        "computer vision", "data analysis", "data science", "devops", "qa testing", "ui/ux", 
        "frontend", "backend", "full stack", "web development", "software engineering", "microservices",
        "rest api", "graphql", "system design", "artificial intelligence", "ai"
    ],
    "Soft Skills": [
        "communication", "leadership", "teamwork", "problem solving", "critical thinking", 
        "time management", "collaboration", "creativity", "presentation", "negotiation"
    ]
}

# Semantic synonyms map to handle abbreviations, spellings, and variations (Phase 8 Advanced AI)
SKILL_SYNONYMS = {
    "PostgreSQL": ["postgresql", "postgres", "sql database", "psql"],
    "FastAPI": ["fastapi", "fast api", "asgi", "python asgi"],
    "Docker": ["docker", "containers", "containerization", "dockerfiles", "dockerize"],
    "Kubernetes": ["kubernetes", "k8s", "helm", "orchestration", "argocd"],
    "React": ["react", "reactjs", "react.js", "react-router", "redux"],
    "CI/CD": ["ci/cd", "pipeline", "pipelines", "jenkins", "github actions", "gitlab ci", "continuous integration"],
    "Git": ["git", "github", "gitlab", "bitbucket", "version control"],
    "MongoDB": ["mongodb", "mongo", "nosql", "document database"],
    "Python": ["python", "django", "flask", "fastapi", "asyncio"],
    "JavaScript": ["javascript", "js", "typescript", "ts", "es6"]
}

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts text from PDF bytes."""
    text = ""
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = PyPDF2.PdfReader(pdf_file)
        for page in reader.pages:
            val = page.extract_text()
            if val:
                text += val + "\n"
    except Exception as e:
        text = f"Error parsing PDF: {str(e)}"
    return text

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extracts text from DOCX bytes."""
    try:
        doc_file = io.BytesIO(file_bytes)
        doc = docx.Document(doc_file)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text.append(cell.text)
        return "\n".join(text)
    except Exception as e:
        return f"Error parsing DOCX: {str(e)}"

def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extracts text from raw TXT bytes."""
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        return f"Error parsing text file: {str(e)}"

def extract_text(filename: str, file_bytes: bytes) -> str:
    """Determines file type by name and extracts its text contents."""
    ext = filename.split('.')[-1].lower()
    if ext == 'pdf':
        return extract_text_from_pdf(file_bytes)
    elif ext in ['docx', 'doc']:
        return extract_text_from_docx(file_bytes)
    else:
        return extract_text_from_txt(file_bytes)

def preprocess_text(text: str) -> str:
    """Cleans text: lowercases, tokenizes, and removes common stopwords."""
    text = text.lower()
    words = re.findall(r'\b[a-z0-9#\+\-\.]+\b', text)
    cleaned = [w for w in words if w not in STOPWORDS and len(w) > 1]
    return " ".join(cleaned)

def parse_experience_years(text: str) -> float:
    """
    Parses years of experience from text using regular expressions.
    Returns maximum years of experience found, limited to a realistic range (< 40).
    """
    text_lower = text.lower()
    
    # Matching phrases like "5+ years", "3 years of experience", "4 yrs in industry", "10 years exp", "total of 6 years"
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*(?:years?|yrs?)\b(?:\s*(?:of)?\s*(?:experience|exp|work|industry|professional|in))?',
        r'(?:experience|exp|work)\s*(?:of)?\s*(?:at\s+least|over)?\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)',
        r'total\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)'
    ]
    
    max_years = 0.0
    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        for m in matches:
            try:
                val = float(m)
                if val > max_years and val < 40:  # Avoid matching future years e.g., 2026
                    max_years = val
            except ValueError:
                pass
    return max_years

def parse_education_degrees(text: str) -> list:
    """
    Identifies academic degrees in text.
    Returns list containing matched standard categories e.g., ['PhD', 'Master', 'Bachelor']
    """
    text_lower = text.lower()
    degrees = []
    
    degree_map = {
        "PhD": ["ph.d", "phd", "doctor of philosophy", "doctorate"],
        "Master": ["master", "m.s.", "ms", "m.tech", "mtech", "mba", "mca", "m.sc", "msc"],
        "Bachelor": ["bachelor", "b.s.", "bs", "b.tech", "btech", "b.a.", "ba", "bca", "b.sc", "bsc"]
    }
    
    for deg_type, terms in degree_map.items():
        for term in terms:
            # Anchor search with word boundaries
            pattern = r'\b' + re.escape(term) + r'\b'
            if term.endswith('.'):
                pattern = r'\b' + re.escape(term)
                
            if re.search(pattern, text_lower):
                degrees.append(deg_type)
                break  # Match only once per category
                
    return degrees

def parse_soft_traits(text: str) -> list:
    """
    Parses soft skills and leadership traits from text using regular expressions (Phase 8 Advanced AI).
    """
    text_lower = text.lower()
    traits = []
    
    trait_patterns = {
        "Leadership & Mentorship": [r"\bmanaged\b", r"\blead\b", r"\bmentor\b", r"\bspearheaded\b", r"\bdirected\b", r"\bleadership\b"],
        "System Design & Architecture": [r"\bscalability\b", r"\barchitecture\b", r"\bmicroservices\b", r"\bsystem design\b", r"\brefactor\b"],
        "Agile Delivery & DevOps": [r"\bagile\b", r"\bscrum\b", r"\bsprint\b", r"\bjira\b", r"\bdevops\b", r"\bci/cd\b"]
    }
    
    for trait, patterns in trait_patterns.items():
        for pat in patterns:
            if re.search(pat, text_lower):
                traits.append(trait)
                break
    return traits

def extract_skills_from_text(text: str) -> dict:
    """Identifies skills from the skills lexicon present in the raw text."""
    text_lower = text.lower()
    extracted = {}
    
    for category, skills in SKILLS_DB.items():
        matched = []
        for skill in skills:
            if '+' in skill or '#' in skill or '.' in skill:
                pattern = r'(?:^|\s|[.,/():\-])' + skill + r'(?:$|\s|[.,/():\-])'
            else:
                pattern = r'\b' + skill + r'\b'
                
            if re.search(pattern, text_lower):
                clean_name = skill.replace("\\", "")
                
                if clean_name == "nextjs":
                    clean_name = "next.js"
                elif clean_name == "nodejs":
                    clean_name = "node.js"
                elif clean_name == "vuejs":
                    clean_name = "vue"
                elif clean_name == "postgres":
                    clean_name = "postgresql"
                elif clean_name == "dotnet":
                    clean_name = "asp.net"
                elif clean_name == "amazon web services":
                    clean_name = "aws"
                elif clean_name == "google cloud":
                    clean_name = "gcp"
                
                proper_cases = {
                    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
                    "java": "Java", "c++": "C++", "c#": "C#", "ruby": "Ruby", "golang": "Go",
                    "rust": "Rust", "php": "PHP", "html": "HTML", "css": "CSS", "sql": "SQL",
                    "r": "R", "swift": "Swift", "kotlin": "Kotlin", "scala": "Scala",
                    "perl": "Perl", "bash": "Bash", "shell": "Shell", "react": "React",
                    "angular": "Angular", "vue": "Vue", "next.js": "Next.js", "node.js": "Node.js",
                    "express": "Express", "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
                    "spring boot": "Spring Boot", "laravel": "Laravel", "rails": "Ruby on Rails",
                    "asp.net": "ASP.NET", "tensorflow": "TensorFlow", "pytorch": "PyTorch",
                    "keras": "Keras", "pandas": "Pandas", "numpy": "NumPy", "scikit-learn": "Scikit-Learn",
                    "scipy": "SciPy", "jquery": "jQuery", "bootstrap": "Bootstrap", "tailwind": "Tailwind",
                    "postgresql": "PostgreSQL", "mysql": "MySQL", "mongodb": "MongoDB", "redis": "Redis",
                    "sqlite": "SQLite", "oracle": "Oracle", "sql server": "SQL Server", "dynamodb": "DynamoDB",
                    "elasticsearch": "Elasticsearch", "cassandra": "Cassandra", "firebase": "Firebase",
                    "neo4j": "Neo4j", "mariadb": "MariaDB", "aws": "AWS", "azure": "Azure", "gcp": "GCP",
                    "docker": "Docker", "kubernetes": "Kubernetes", "git": "Git", "github": "GitHub",
                    "gitlab": "GitLab", "jenkins": "Jenkins", "terraform": "Terraform", "ansible": "Ansible",
                    "ci/cd": "CI/CD", "linux": "Linux", "nginx": "Nginx", "apache": "Apache",
                    "circleci": "CircleCI", "agile": "Agile", "scrum": "Scrum",
                    "project management": "Project Management", "machine learning": "Machine Learning",
                    "deep learning": "Deep Learning", "nlp": "NLP", "computer vision": "Computer Vision",
                    "data analysis": "Data Analysis", "data science": "Data Science", "devops": "DevOps",
                    "qa testing": "QA & Testing", "ui/ux": "UI/UX", "frontend": "Frontend",
                    "backend": "Backend", "full stack": "Full Stack", "web development": "Web Development",
                    "software engineering": "Software Engineering", "microservices": "Microservices",
                    "rest api": "REST APIs", "graphql": "GraphQL", "system design": "System Design",
                    "artificial intelligence": "AI", "communication": "Communication",
                    "leadership": "Leadership", "teamwork": "Teamwork", "problem solving": "Problem Solving",
                    "critical thinking": "Critical Thinking", "time management": "Time Management",
                    "collaboration": "Collaboration", "creativity": "Creativity",
                    "presentation": "Presentation", "negotiation": "Negotiation"
                }
                
                final_name = proper_cases.get(clean_name, clean_name.title())
                if final_name not in matched:
                    matched.append(final_name)
                    
        if matched:
            extracted[category] = sorted(matched)
            
    return extracted

def check_skill_match_raw(jd_skill: str, candidate_text: str, candidate_skills: set) -> bool:
    """Checks if a skill or any of its synonyms are present in candidate skills or text (Phase 8 Advanced AI)."""
    jd_lower = jd_skill.lower()
    cand_lower = {c.lower() for c in candidate_skills}
    
    # 1. Exact match in candidate extracted skills
    if jd_lower in cand_lower:
        return True
        
    # 2. Check synonyms aliases in candidate skills
    aliases = SKILL_SYNONYMS.get(jd_skill, [])
    for alias in aliases:
        if alias.lower() in cand_lower:
            return True
            
    # 3. Check synonyms aliases in candidate text directly (handles non-lexicon mappings)
    text_lower = candidate_text.lower()
    for alias in aliases:
        if '+' in alias or '#' in alias or '.' in alias:
            pattern = r'(?:^|\s|[.,/():\-])' + re.escape(alias.lower()) + r'(?:$|\s|[.,/():\-])'
        else:
            pattern = r'\b' + re.escape(alias.lower()) + r'\b'
            
        if re.search(pattern, text_lower):
            return True
            
    return False

def compute_nlp_shortlist(jd_raw: str, resumes: list) -> list:
    """
    Parses JD and candidate resumes.
    Returns list of candidates ranked by overall score.
    """
    # 1. Parse Job Description Parameters
    jd_clean = preprocess_text(jd_raw)
    jd_skills_dict = extract_skills_from_text(jd_raw)
    jd_exp = parse_experience_years(jd_raw)
    jd_degrees = parse_education_degrees(jd_raw)
    
    # Flatten JD skills
    jd_skills = []
    for cat_skills in jd_skills_dict.values():
        jd_skills.extend(cat_skills)
    jd_skills_set = set(jd_skills)
    
    # Cleaned JD backup
    if not jd_clean.strip():
        jd_clean = jd_raw.lower()
        
    cleaned_resumes = []
    for res in resumes:
        cleaned_resumes.append(preprocess_text(res['raw_text']))
        
    # 2. Calculate TF-IDF & Cosine Similarity
    similarities = [0.0] * len(resumes)
    if jd_clean.strip() and any(r.strip() for r in cleaned_resumes):
        try:
            documents = [jd_clean] + cleaned_resumes
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(documents)
            sim_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])
            similarities = sim_scores[0].tolist()
        except Exception:
            pass
            
    # 3. Calculate candidate scores and compile analysis reports
    candidates_list = []
    for idx, res in enumerate(resumes):
        raw_txt = res['raw_text']
        c_skills_dict = extract_skills_from_text(raw_txt)
        
        # Flatten candidate skills
        c_skills = []
        for cat_skills in c_skills_dict.values():
            c_skills.extend(cat_skills)
        c_skills_set = set(c_skills)
        
        # Skill matching using Synonyms alias expanders
        matched_skills = []
        missing_skills = []
        for req_skill in jd_skills_set:
            if check_skill_match_raw(req_skill, raw_txt, c_skills_set):
                matched_skills.append(req_skill)
            else:
                missing_skills.append(req_skill)
                
        matched_skills.sort()
        missing_skills.sort()
        
        skills_score = 0.0
        if jd_skills_set:
            skills_score = len(matched_skills) / len(jd_skills_set)
            
        # Experience matching
        candidate_exp = parse_experience_years(raw_txt)
        experience_score = 0.0
        if jd_exp > 0.0:
            if candidate_exp >= jd_exp:
                experience_score = 1.0
            else:
                experience_score = candidate_exp / jd_exp
        else:
            experience_score = 1.0 # 100% match if experience not specified in JD
            
        # Degree matching
        candidate_degrees = parse_education_degrees(raw_txt)
        degree_match = False
        if jd_degrees:
            degree_match = len(set(jd_degrees).intersection(set(candidate_degrees))) > 0
        else:
            degree_match = True # Match if not specified
            
        # Soft Traits extraction
        soft_traits = parse_soft_traits(raw_txt)
            
        # Calculate scores
        cosine_sim = max(0.0, min(1.0, similarities[idx]))
        
        # Default weights: 40% Cosine Similarity, 35% Skills Matching, 25% Experience Matching
        final_score = (cosine_sim * 0.4) + (skills_score * 0.35) + (experience_score * 0.25)
        
        candidates_list.append({
            "filename": res['filename'],
            "score": round(final_score * 100, 1),
            "cosine_score": round(cosine_sim * 100, 1),
            "skills_score": round(skills_score * 100, 1),
            "experience_score": round(experience_score * 100, 1),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "all_extracted_skills": c_skills_dict,
            "candidate_exp": candidate_exp,
            "candidate_degrees": candidate_degrees,
            "degree_match": degree_match,
            "soft_traits": soft_traits,
            "snippet": raw_txt[:400] + ("..." if len(raw_txt) > 400 else "")
        })
        
    # Sort candidates by score descending
    candidates_list.sort(key=lambda x: x['score'], reverse=True)
    
    # Return both the ranked list and the parsed JD requirements
    return {
        "candidates": candidates_list,
        "jd_requirements": {
            "skills": sorted(list(jd_skills_set)),
            "experience_years": jd_exp,
            "degrees": jd_degrees
        }
    }
