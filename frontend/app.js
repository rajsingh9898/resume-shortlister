// State management for uploaded files and candidate rankings
let selectedFiles = [];
let rankedCandidates = [];

// DOM Elements
const dropzone = document.getElementById('dropzone');
const resumeInput = document.getElementById('resume-input');
const fileList = document.getElementById('file-list');
const shortlistForm = document.getElementById('shortlist-form');
const jobDescriptionInput = document.getElementById('job-description');
const submitBtn = document.getElementById('submit-btn');
const btnLoader = document.getElementById('btn-loader');
const btnText = submitBtn.querySelector('.btn-text');

// Dashboard State DOM Elements
const emptyState = document.getElementById('empty-state');
const resultsState = document.getElementById('results-state');
const statTotal = document.getElementById('stat-total');
const statMatches = document.getElementById('stat-matches');
const statAvg = document.getElementById('stat-avg');
const candidatesContainer = document.getElementById('candidates-container');
const searchCandidate = document.getElementById('search-candidate');

// Detail Drawer DOM Elements
const detailDrawer = document.getElementById('detail-drawer');
const cRank = document.getElementById('c-rank');
const cName = document.getElementById('c-name');
const detailScore = document.getElementById('detail-score');
const detailRingVal = document.getElementById('detail-ring-val');
const detailCosineScore = document.getElementById('detail-cosine-score');
const detailCosineBar = document.getElementById('detail-cosine-bar');
const detailSkillsScore = document.getElementById('detail-skills-score');
const detailSkillsBar = document.getElementById('detail-skills-bar');
const detailMatchedSkills = document.getElementById('detail-matched-skills');
const detailMissingSkills = document.getElementById('detail-missing-skills');
const detailAllSkillsCategories = document.getElementById('detail-all-skills-categories');
const detailSnippet = document.getElementById('detail-snippet');

// Toast DOM Element
const toast = document.getElementById('toast');

/* Toast Notification Helper */
function showToast(message, type = 'success') {
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    setTimeout(() => {
        toast.className = 'toast';
    }, 4000);
}

/* Drag and Drop File Handlers */
dropzone.addEventListener('click', () => resumeInput.click());

dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
});

resumeInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});

function handleFiles(files) {
    const maxFiles = 15;
    if (selectedFiles.length + files.length > maxFiles) {
        showToast(`You can upload a maximum of ${maxFiles} resumes at a time.`, 'error');
        return;
    }

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const ext = file.name.split('.').pop().toLowerCase();
        const validExtensions = ['pdf', 'docx', 'doc', 'txt'];

        if (!validExtensions.includes(ext)) {
            showToast(`File type not supported: ${file.name}`, 'error');
            continue;
        }

        // Avoid adding duplicate files
        if (selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
            continue;
        }

        selectedFiles.push(file);
    }
    updateFileListUI();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileListUI();
}

function updateFileListUI() {
    fileList.innerHTML = '';
    selectedFiles.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        
        let iconClass = 'fa-file-lines';
        const ext = file.name.split('.').pop().toLowerCase();
        if (ext === 'pdf') iconClass = 'fa-file-pdf';
        else if (ext === 'docx' || ext === 'doc') iconClass = 'fa-file-word';

        item.innerHTML = `
            <div class="file-info">
                <i class="fa-solid ${iconClass}"></i>
                <span class="file-name" title="${file.name}">${file.name}</span>
            </div>
            <i class="fa-solid fa-trash-can file-remove" onclick="removeFile(${index})"></i>
        `;
        fileList.appendChild(item);
    });
}

/* Submit Form to Backend API */
shortlistForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const jd = jobDescriptionInput.value.trim();
    if (!jd) {
        showToast("Please enter a job description.", "error");
        return;
    }

    if (selectedFiles.length === 0) {
        showToast("Please upload at least one resume.", "error");
        return;
    }

    // Enter Loading State
    submitBtn.disabled = true;
    btnLoader.style.display = 'inline-block';
    btnText.textContent = 'Analyzing...';
    submitBtn.style.opacity = '0.85';

    const formData = new FormData();
    formData.append('jd', jd);
    selectedFiles.forEach(file => {
        formData.append('resumes', file);
    });

    try {
        const response = await fetch('/api/shortlist', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.success) {
            rankedCandidates = data.candidates;
            renderDashboard(rankedCandidates);
            showToast("Resumes ranked and dashboard loaded successfully!", "success");
        } else {
            const errorMsg = data.detail || "Failed to process resumes. Try again.";
            showToast(errorMsg, "error");
        }
    } catch (error) {
        console.error(error);
        showToast("Server connection error. Ensure backend is running.", "error");
    } finally {
        // Exit Loading State
        submitBtn.disabled = false;
        btnLoader.style.display = 'none';
        btnText.textContent = 'Rank Candidates';
        submitBtn.style.opacity = '1';
    }
});

/* Dashboard Rendering */
function renderDashboard(candidates) {
    emptyState.classList.remove('active');
    resultsState.classList.add('active');

    // Update Stats Cards
    statTotal.textContent = candidates.length;
    
    const strongMatchesCount = candidates.filter(c => c.score >= 70.0).length;
    statMatches.textContent = strongMatchesCount;

    const avgScore = candidates.reduce((acc, c) => acc + c.score, 0) / candidates.length;
    statAvg.textContent = `${avgScore.toFixed(1)}%`;

    // Render Candidates List
    renderCandidatesList(candidates);
}

function renderCandidatesList(candidates) {
    candidatesContainer.innerHTML = '';
    
    if (candidates.length === 0) {
        candidatesContainer.innerHTML = `
            <div class="empty-state" style="padding: 30px; text-align: center; color: var(--text-muted);">
                No matching candidates found.
            </div>
        `;
        return;
    }

    candidates.forEach((candidate, index) => {
        // Classify scores for visual color coding
        let scoreClass = 'low';
        if (candidate.score >= 70) scoreClass = 'high';
        else if (candidate.score >= 40) scoreClass = 'mid';

        const item = document.createElement('div');
        item.className = 'candidate-card';
        item.onclick = () => openDrawer(candidate, index + 1);

        item.innerHTML = `
            <div class="candidate-main">
                <span class="rank-badge">#${index + 1}</span>
                <div class="candidate-profile">
                    <span class="candidate-title" title="${candidate.filename}">${candidate.filename}</span>
                    <span class="candidate-subtitle">Matched ${candidate.matched_skills.length} skills • Cosine: ${candidate.cosine_score}%</span>
                </div>
            </div>
            <div class="candidate-right">
                <div class="score-badge">
                    <span class="score-percent ${scoreClass}">${candidate.score}%</span>
                    <span class="score-lbl">Match Score</span>
                </div>
                <i class="fa-solid fa-chevron-right arrow-icon"></i>
            </div>
        `;
        candidatesContainer.appendChild(item);
    });
}

/* Local Filter Input Listener */
searchCandidate.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    const filtered = rankedCandidates.filter(c => c.filename.toLowerCase().includes(query));
    renderCandidatesList(filtered);
});

/* Detail Drawer Handlers */
function openDrawer(candidate, rank) {
    cRank.textContent = `#${rank}`;
    cName.textContent = candidate.filename;
    cName.title = candidate.filename;
    
    // Set match percentage circle
    detailScore.textContent = `${candidate.score}%`;
    const ringRadius = 42;
    const circumference = 2 * Math.PI * ringRadius;
    const offset = circumference - (candidate.score / 100) * circumference;
    detailRingVal.style.strokeDashoffset = offset;
    
    // Score visual coloring
    let scoreColor = 'var(--danger)';
    if (candidate.score >= 70) scoreColor = 'var(--success)';
    else if (candidate.score >= 40) scoreColor = 'var(--warning)';
    detailRingVal.style.stroke = scoreColor;

    // Detailed scores progress bars
    detailCosineScore.textContent = `${candidate.cosine_score}%`;
    detailCosineBar.style.width = `${candidate.cosine_score}%`;
    
    detailSkillsScore.textContent = `${candidate.skills_score}%`;
    detailSkillsBar.style.width = `${candidate.skills_score}%`;

    // Matched skills badges
    detailMatchedSkills.innerHTML = '';
    if (candidate.matched_skills.length === 0) {
        detailMatchedSkills.innerHTML = '<span class="text-dark" style="font-size: 0.8rem;">None matched.</span>';
    } else {
        candidate.matched_skills.forEach(skill => {
            const badge = document.createElement('span');
            badge.className = 'badge';
            badge.textContent = skill;
            detailMatchedSkills.appendChild(badge);
        });
    }

    // Missing skills badges
    detailMissingSkills.innerHTML = '';
    if (candidate.missing_skills.length === 0) {
        detailMissingSkills.innerHTML = '<span class="text-dark" style="font-size: 0.8rem;">No missing skills identified.</span>';
    } else {
        candidate.missing_skills.forEach(skill => {
            const badge = document.createElement('span');
            badge.className = 'badge';
            badge.textContent = skill;
            detailMissingSkills.appendChild(badge);
        });
    }

    // Categorized all extracted skills matrix
    detailAllSkillsCategories.innerHTML = '';
    const cats = candidate.all_extracted_skills;
    const categoriesList = Object.keys(cats);
    
    if (categoriesList.length === 0) {
        detailAllSkillsCategories.innerHTML = '<div style="color: var(--text-dark); font-size: 0.85rem;">No skills identified from standard index.</div>';
    } else {
        categoriesList.forEach(category => {
            const catContainer = document.createElement('div');
            catContainer.className = 'skills-matrix-cat';
            
            const title = document.createElement('h5');
            title.textContent = category;
            
            const badgesDiv = document.createElement('div');
            badgesDiv.className = 'badge-list';
            
            cats[category].forEach(s => {
                const badge = document.createElement('span');
                badge.className = 'badge';
                badge.textContent = s;
                badgesDiv.appendChild(badge);
            });
            
            catContainer.appendChild(title);
            catContainer.appendChild(badgesDiv);
            detailAllSkillsCategories.appendChild(catContainer);
        });
    }

    // Snippet raw preview
    detailSnippet.textContent = candidate.snippet;

    // Toggle drawer open
    detailDrawer.classList.add('open');
}

function closeDrawer() {
    detailDrawer.classList.remove('open');
}

// Close drawer on ESC key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && detailDrawer.classList.contains('open')) {
        closeDrawer();
    }
});
