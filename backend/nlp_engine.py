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
    # Find all words, allowing characters commonly found in tech terms
    words = re.findall(r'\b[a-z0-9#\+\-\.]+\b', text)
    # Filter stopwords and short tokens
    cleaned = [w for w in words if w not in STOPWORDS and len(w) > 1]
    return " ".join(cleaned)

def extract_skills_from_text(text: str) -> dict:
    """Identifies skills from the skills lexicon present in the raw text."""
    text_lower = text.lower()
    extracted = {}
    
    for category, skills in SKILLS_DB.items():
        matched = []
        for skill in skills:
            # Create regex pattern representing the skill
            # Handle special characters like C++, C#, .NET, Node.js
            if '+' in skill or '#' in skill or '.' in skill:
                pattern = r'(?:^|\s|[.,/():\-])' + skill + r'(?:$|\s|[.,/():\-])'
            else:
                pattern = r'\b' + skill + r'\b'
                
            if re.search(pattern, text_lower):
                # Clean up backslashes used for regex escaping
                clean_name = skill.replace("\\", "")
                
                # Normalize common variations for display
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
                
                # Capitalize nicely for display
                display_name = clean_name
                # List of standard formats to keep consistent case
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

def compute_nlp_shortlist(jd_raw: str, resumes: list) -> list:
    """
    Parses JD and candidates resumes. Ranks candidates by score.
    resumes format: list of dicts like {'filename': str, 'raw_text': str}
    """
    # 1. Preprocess Job Description
    jd_clean = preprocess_text(jd_raw)
    jd_skills_dict = extract_skills_from_text(jd_raw)
    
    # Flatten JD skills to list
    jd_skills = []
    for cat_skills in jd_skills_dict.values():
        jd_skills.extend(cat_skills)
    jd_skills_set = set(jd_skills)
    
    # If cleaned JD is empty, use raw text
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
            
            # Cosine similarity between JD (first row) and each resume (subsequent rows)
            sim_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])
            similarities = sim_scores[0].tolist()
        except Exception as e:
            # Fallback if vectorization fails (e.g. empty vocab)
            pass
            
    # 3. Compile report and calculate final hybrid score
    ranked_candidates = []
    for idx, res in enumerate(resumes):
        raw_txt = res['raw_text']
        c_skills_dict = extract_skills_from_text(raw_txt)
        
        # Flatten candidate skills
        c_skills = []
        for cat_skills in c_skills_dict.values():
            c_skills.extend(cat_skills)
        c_skills_set = set(c_skills)
        
        # Find matched & missing JD skills
        matched_skills = sorted(list(jd_skills_set.intersection(c_skills_set)))
        missing_skills = sorted(list(jd_skills_set.difference(c_skills_set)))
        
        # Calculate Skill Coverage Ratio
        skill_score = 0.0
        if jd_skills_set:
            skill_score = len(matched_skills) / len(jd_skills_set)
            
        # Hybrid Score: 60% TF-IDF Cosine Similarity + 40% Skill Coverage Score
        cosine_sim = similarities[idx]
        # Normalize cosine_sim to be 0 to 1 range (in case of floating point quirks, clip to [0,1])
        cosine_sim = max(0.0, min(1.0, cosine_sim))
        
        final_score = (cosine_sim * 0.6) + (skill_score * 0.4)
        
        # Convert to percentage
        match_percentage = round(final_score * 100, 1)
        
        ranked_candidates.append({
            "filename": res['filename'],
            "score": match_percentage,
            "cosine_score": round(cosine_sim * 100, 1),
            "skills_score": round(skill_score * 100, 1),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "all_extracted_skills": c_skills_dict,
            "snippet": raw_txt[:400] + ("..." if len(raw_txt) > 400 else "")
        })
        
    # Sort candidates by score descending
    ranked_candidates.sort(key=lambda x: x['score'], reverse=True)
    return ranked_candidates
