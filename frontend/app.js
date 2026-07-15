// State management for uploaded files, candidate rankings, and JD requirements
let selectedFiles = [];
let rankedCandidates = [];
let activeJdSkills = [];
let jdExperienceRequired = 0;
let jdDegreesRequired = [];

// Filtering states (Phase 3)
let activeFilterCategory = 'all'; // 'all', 'high', 'mid', 'exp', 'edu'
let activeChartSkillFilter = null; // Filter candidates by specific clicked chart skill bar

// DOM Elements
const dropzone = document.getElementById('dropzone');
const resumeInput = document.getElementById('resume-input');
const fileList = document.getElementById('file-list');
const shortlistForm = document.getElementById('shortlist-form');
const jobDescriptionInput = document.getElementById('job-description');
const submitBtn = document.getElementById('submit-btn');
const btnLoader = document.getElementById('btn-loader');
const btnText = submitBtn.querySelector('.btn-text');

// Weight Sliders
const sliderSemantic = document.getElementById('weight-semantic');
const sliderSkills = document.getElementById('weight-skills');
const sliderExperience = document.getElementById('weight-experience');
const lblSemantic = document.getElementById('lbl-weight-semantic');
const lblSkills = document.getElementById('lbl-weight-skills');
const lblExperience = document.getElementById('lbl-weight-experience');
const weightTotalBadge = document.getElementById('weight-total');

// JD Requirements Editor Panel
const jdRequirementsPanel = document.getElementById('jd-requirements-panel');
const reqExperienceVal = document.getElementById('req-experience-val');
const reqDegreesVal = document.getElementById('req-degrees-val');
const jdSkillsChipsList = document.getElementById('jd-skills-chips-list');
const newSkillInput = document.getElementById('new-skill-input');
const addSkillBtn = document.getElementById('add-skill-btn');

// Pool Skills Chart DOM (Phase 3)
const poolSkillsChartPanel = document.querySelector('.pool-skills-chart-panel');
const poolSkillsChart = document.getElementById('pool-skills-chart');

// Filter Badges DOM (Phase 3)
const filterBadgesContainer = document.getElementById('filter-badges-container');

// Dashboard State DOM Elements
const emptyState = document.getElementById('empty-state');
const resultsState = document.getElementById('results-state');
const statTotal = document.getElementById('stat-total');
const statMatches = document.getElementById('stat-matches');
const statAvg = document.getElementById('stat-avg');
const candidatesContainer = document.getElementById('candidates-container');
const searchCandidate = document.getElementById('search-candidate');
const exportBtn = document.getElementById('export-btn');

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
const detailExperienceScore = document.getElementById('detail-experience-score');
const detailExperienceBar = document.getElementById('detail-experience-bar');

const detailReqExp = document.getElementById('detail-req-exp');
const detailCandExp = document.getElementById('detail-cand-exp');
const detailExpStatusIcon = document.getElementById('detail-exp-status-icon');
const detailCandDegrees = document.getElementById('detail-cand-degrees');
const detailDegreeMatchStatus = document.getElementById('detail-degree-match-status');

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

/* Dynamic Weights (Slider Recalculations) */
[sliderSemantic, sliderSkills, sliderExperience].forEach(slider => {
    slider.addEventListener('input', () => {
        updateWeightsUI();
        if (rankedCandidates.length > 0 && isWeightsSumValid()) {
            recalculateRanking();
        }
    });
});

function getWeights() {
    return {
        semantic: parseInt(sliderSemantic.value),
        skills: parseInt(sliderSkills.value),
        experience: parseInt(sliderExperience.value)
    };
}

function isWeightsSumValid() {
    const w = getWeights();
    return (w.semantic + w.skills + w.experience) === 100;
}

function updateWeightsUI() {
    const w = getWeights();
    lblSemantic.textContent = `${w.semantic}%`;
    lblSkills.textContent = `${w.skills}%`;
    lblExperience.textContent = `${w.experience}%`;
    
    const sum = w.semantic + w.skills + w.experience;
    weightTotalBadge.textContent = `${sum}%`;
    
    if (sum === 100) {
        weightTotalBadge.className = 'weight-total-badge valid';
        submitBtn.disabled = false;
        submitBtn.style.opacity = '1';
    } else {
        weightTotalBadge.className = 'weight-total-badge invalid';
        submitBtn.disabled = true;
        submitBtn.style.opacity = '0.5';
    }
}

/* Client-Side Scoring & Ranking Engine */
function recalculateRanking() {
    const w = getWeights();
    const activeSkillsSet = new Set(activeJdSkills);

    rankedCandidates.forEach(cand => {
        // 1. Recalculate Skills Score based on dynamic chip tags
        const candSkillsList = [];
        Object.values(cand.all_extracted_skills).forEach(catSkills => {
            candSkillsList.push(...catSkills);
        });
        const candSkillsSet = new Set(candSkillsList);

        const matched = [...activeSkillsSet].filter(s => candSkillsSet.has(s));
        const missing = [...activeSkillsSet].filter(s => !candSkillsSet.has(s));
        
        cand.matched_skills = matched.sort();
        cand.missing_skills = missing.sort();
        
        if (activeSkillsSet.size > 0) {
            cand.skills_score = (matched.length / activeSkillsSet.size) * 100;
        } else {
            cand.skills_score = 100.0;
        }

        // 2. Recalculate Experience Score dynamically
        if (jdExperienceRequired > 0.0) {
            if (cand.candidate_exp >= jdExperienceRequired) {
                cand.experience_score = 100.0;
            } else {
                cand.experience_score = (cand.candidate_exp / jdExperienceRequired) * 100;
            }
        } else {
            cand.experience_score = 100.0;
        }

        // 3. Compute final weighted combination
        const finalScore = (cand.cosine_score * w.semantic / 100) + 
                             (cand.skills_score * w.skills / 100) + 
                             (cand.experience_score * w.experience / 100);
                             
        cand.score = parseFloat(finalScore.toFixed(1));
    });

    rankedCandidates.sort((a, b) => b.score - a.score);
    
    // Refresh UI display list and dashboard metrics
    renderDashboard(rankedCandidates);
    
    // Re-draw skill frequency chart
    renderPoolSkillsChart();
}

/* Submit Form to Backend API */
shortlistForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!isWeightsSumValid()) {
        showToast("Scoring weights must sum to exactly 100%.", "error");
        return;
    }

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
            
            // Populate extracted requirements
            activeJdSkills = data.jd_requirements.skills;
            jdExperienceRequired = data.jd_requirements.experience_years;
            jdDegreesRequired = data.jd_requirements.degrees;

            // Reset dashboard filters
            activeFilterCategory = 'all';
            activeChartSkillFilter = null;
            updateFilterBadgesUI();

            // Load requirements editor panel
            renderRequirementsEditor();
            
            // Perform ranking calculations
            recalculateRanking();
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

    // Apply active filters on candidates list before rendering
    applyCandidatesFiltering();
}

/* Filter Application Engine (Phase 3) */
function applyCandidatesFiltering() {
    let filteredList = [...rankedCandidates];

    // 1. Filter by Active Filter Badges Category
    if (activeFilterCategory === 'high') {
        filteredList = filteredList.filter(c => c.score >= 70.0);
    } else if (activeFilterCategory === 'mid') {
        filteredList = filteredList.filter(c => c.score >= 40.0 && c.score < 70.0);
    } else if (activeFilterCategory === 'exp') {
        filteredList = filteredList.filter(c => jdExperienceRequired === 0 || c.candidate_exp >= jdExperienceRequired);
    } else if (activeFilterCategory === 'edu') {
        filteredList = filteredList.filter(c => c.degree_match === true);
    }

    // 2. Filter by Active clicked skill bar from pool chart
    if (activeChartSkillFilter) {
        filteredList = filteredList.filter(c => {
            const candSkillsList = [];
            Object.values(c.all_extracted_skills).forEach(catSkills => {
                candSkillsList.push(...catSkills);
            });
            return candSkillsList.includes(activeChartSkillFilter);
        });
    }

    // 3. Filter by Search Query
    const query = searchCandidate.value.toLowerCase().trim();
    if (query) {
        filteredList = filteredList.filter(c => c.filename.toLowerCase().includes(query));
    }

    renderCandidatesList(filteredList);
}

function renderCandidatesList(candidates) {
    candidatesContainer.innerHTML = '';
    
    if (candidates.length === 0) {
        candidatesContainer.innerHTML = `
            <div class="empty-state" style="padding: 40px; text-align: center; color: var(--text-dark);">
                <i class="fa-solid fa-folder-open" style="font-size: 1.5rem; margin-bottom: 8px;"></i>
                <p>No matching candidates fit the active criteria.</p>
            </div>
        `;
        return;
    }

    candidates.forEach((candidate, index) => {
        let scoreClass = 'low';
        if (candidate.score >= 70) scoreClass = 'high';
        else if (candidate.score >= 40) scoreClass = 'mid';

        const item = document.createElement('div');
        item.className = 'candidate-card';
        item.onclick = () => openDrawer(candidate, index + 1);

        const expLabel = candidate.candidate_exp > 0 ? `${candidate.candidate_exp} Yrs Exp` : 'Exp not listed';
        const degreeLabel = candidate.candidate_degrees.length > 0 ? candidate.candidate_degrees.join(', ') : 'No Degree listed';

        // Extract top 3 matched skills for card micro-badges
        const microBadgesHtml = candidate.matched_skills.slice(0, 3).map(skill => 
            `<span class="cand-meta-badge skills-micro">${skill}</span>`
        ).join('');

        item.innerHTML = `
            <div class="candidate-main">
                <span class="rank-badge">#${index + 1}</span>
                <div class="candidate-profile">
                    <span class="candidate-title" title="${candidate.filename}">${candidate.filename}</span>
                    <span class="candidate-subtitle">
                        <span class="cand-meta-badge">${expLabel}</span>
                        <span class="cand-meta-badge">${degreeLabel}</span>
                        ${microBadgesHtml}
                    </span>
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
searchCandidate.addEventListener('input', () => {
    applyCandidatesFiltering();
});

/* Toggle Quick Filter Badges (Phase 3) */
filterBadgesContainer.addEventListener('click', (e) => {
    const badge = e.target.closest('.filter-badge');
    if (!badge) return;

    const filterVal = badge.getAttribute('data-filter');
    activeFilterCategory = filterVal;
    
    updateFilterBadgesUI();
    applyCandidatesFiltering();
});

function updateFilterBadgesUI() {
    const badges = filterBadgesContainer.querySelectorAll('.filter-badge');
    badges.forEach(b => {
        if (b.getAttribute('data-filter') === activeFilterCategory) {
            b.classList.add('active');
        } else {
            b.classList.remove('active');
        }
    });
}

/* Pool Skills Frequency Chart rendering (Phase 3) */
function renderPoolSkillsChart() {
    if (rankedCandidates.length === 0) {
        poolSkillsChartPanel.classList.remove('active');
        return;
    }

    poolSkillsChartPanel.classList.add('active');
    poolSkillsChart.innerHTML = '';

    // Count skills frequencies across candidates
    const freq = {};
    rankedCandidates.forEach(cand => {
        const skillsSet = new Set();
        Object.values(cand.all_extracted_skills).forEach(catSkills => {
            catSkills.forEach(s => skillsSet.add(s));
        });
        skillsSet.forEach(s => {
            freq[s] = (freq[s] || 0) + 1;
        });
    });

    // Sort skills by frequency descending
    const sortedSkills = Object.keys(freq).map(skill => {
        return { name: skill, count: freq[skill] };
    }).sort((a, b) => b.count - a.count).slice(0, 5); // Take top 5 skills

    if (sortedSkills.length === 0) {
        poolSkillsChart.innerHTML = '<span class="text-dark" style="font-size: 0.8rem;">No skills identified in the candidate pool.</span>';
        return;
    }

    sortedSkills.forEach(item => {
        const percentage = (item.count / rankedCandidates.length) * 100;
        
        const barGroup = document.createElement('div');
        barGroup.className = 'chart-bar-group';
        if (activeChartSkillFilter === item.name) {
            barGroup.classList.add('filter-active');
        }
        
        barGroup.onclick = () => toggleSkillChartFilter(item.name);

        barGroup.innerHTML = `
            <span class="bar-label" title="${item.name}">${item.name}</span>
            <div class="bar-track">
                <div class="bar-fill" style="width: 0%;"></div>
            </div>
            <span class="bar-count">${item.count} Candidate${item.count > 1 ? 's' : ''}</span>
        `;
        
        poolSkillsChart.appendChild(barGroup);
        
        // Trigger width animation in next frame
        setTimeout(() => {
            const fill = barGroup.querySelector('.bar-fill');
            if (fill) fill.style.width = `${percentage}%`;
        }, 50);
    });
}

function toggleSkillChartFilter(skillName) {
    if (activeChartSkillFilter === skillName) {
        activeChartSkillFilter = null; // Clear filter if clicked again
        showToast("Cleared skill chart filter.", "info");
    } else {
        activeChartSkillFilter = skillName;
        showToast(`Filtering candidate pool for: ${skillName}`, "success");
    }
    renderPoolSkillsChart();
    applyCandidatesFiltering();
}

/* JD Requirements Panel Editor */
function renderRequirementsEditor() {
    jdRequirementsPanel.classList.add('active');
    reqExperienceVal.textContent = jdExperienceRequired > 0 ? `${jdExperienceRequired}+ Years` : 'None required';
    reqDegreesVal.textContent = jdDegreesRequired.length > 0 ? jdDegreesRequired.join(', ') : 'Any degree';
    
    renderSkillsChips();
}

function renderSkillsChips() {
    jdSkillsChipsList.innerHTML = '';
    if (activeJdSkills.length === 0) {
        jdSkillsChipsList.innerHTML = '<span class="text-dark" style="font-size: 0.75rem; padding: 4px;">No skills specified.</span>';
        return;
    }

    activeJdSkills.forEach((skill, idx) => {
        const chip = document.createElement('span');
        chip.className = 'jd-chip';
        chip.innerHTML = `
            ${skill}
            <i class="fa-solid fa-xmark jd-chip-remove" onclick="removeJdSkill(${idx})"></i>
        `;
        jdSkillsChipsList.appendChild(chip);
    });
}

window.removeJdSkill = function(index) {
    const removedSkill = activeJdSkills[index];
    activeJdSkills.splice(index, 1);
    renderSkillsChips();
    recalculateRanking();
    showToast(`Removed skill requirements: ${removedSkill}`, "info");
};

function addCustomJdSkill() {
    const skill = newSkillInput.value.trim();
    if (!skill) return;
    
    const normalized = skill.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');

    if (activeJdSkills.includes(normalized)) {
        showToast("Skill is already required.", "error");
        return;
    }

    activeJdSkills.push(normalized);
    activeJdSkills.sort();
    newSkillInput.value = '';
    renderSkillsChips();
    recalculateRanking();
    showToast(`Added skill requirement: ${normalized}`, "success");
}

addSkillBtn.addEventListener('click', addCustomJdSkill);
newSkillInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        addCustomJdSkill();
    }
});

/* Dynamic Skill Highlighter (Phase 3) */
function highlightTextSkills(rawText, matchedSkills, missingSkills) {
    let tempText = rawText;
    const replacements = {};
    let tokenIndex = 0;
    
    // Gather all keywords to highlight and flag their types
    const keywords = [];
    matchedSkills.forEach(s => keywords.push({ word: s, type: 'match' }));
    missingSkills.forEach(s => keywords.push({ word: s, type: 'miss' }));
    
    // Sort keywords by length descending to prevent shorter words eating longer matches
    keywords.sort((a, b) => b.word.length - a.word.length);
    
    function escapeRegExp(str) {
        return str.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
    }
    
    keywords.forEach(kw => {
        const pattern = new RegExp('\\b(' + escapeRegExp(kw.word) + ')\\b', 'gi');
        tempText = tempText.replace(pattern, (match) => {
            const token = `__TOKEN_SKILL_${tokenIndex}__`;
            replacements[token] = `<mark class="highlight-${kw.type}">${match}</mark>`;
            tokenIndex++;
            return token;
        });
    });
    
    // HTML escape the text to prevent any visual scripts, keeping placeholders intact
    const dummyDiv = document.createElement('div');
    dummyDiv.innerText = tempText;
    let safeHtml = dummyDiv.innerHTML;
    
    // Finally replace placeholders with marked HTML
    Object.keys(replacements).forEach(token => {
        safeHtml = safeHtml.replace(token, replacements[token]);
    });
    
    return safeHtml;
}

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
    
    let scoreColor = 'var(--danger)';
    if (candidate.score >= 70) scoreColor = 'var(--success)';
    else if (candidate.score >= 40) scoreColor = 'var(--warning)';
    detailRingVal.style.stroke = scoreColor;

    // Detailed scores progress bars
    detailCosineScore.textContent = `${candidate.cosine_score}%`;
    detailCosineBar.style.width = `${candidate.cosine_score}%`;
    
    detailSkillsScore.textContent = `${candidate.skills_score.toFixed(1)}%`;
    detailSkillsBar.style.width = `${candidate.skills_score}%`;

    detailExperienceScore.textContent = `${candidate.experience_score.toFixed(1)}%`;
    detailExperienceBar.style.width = `${candidate.experience_score}%`;

    // Experience Card metrics
    detailReqExp.textContent = jdExperienceRequired > 0 ? `${jdExperienceRequired} Years` : '0 Years (None)';
    detailCandExp.textContent = `${candidate.candidate_exp} Years`;
    
    detailExpStatusIcon.className = 'meta-card-status';
    if (jdExperienceRequired === 0) {
        detailExpStatusIcon.innerHTML = '<i class="fa-solid fa-circle-check"></i>';
        detailExpStatusIcon.classList.add('match');
    } else if (candidate.candidate_exp >= jdExperienceRequired) {
        detailExpStatusIcon.innerHTML = '<i class="fa-solid fa-circle-check"></i>';
        detailExpStatusIcon.classList.add('match');
    } else if (candidate.candidate_exp > 0) {
        detailExpStatusIcon.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i>';
        detailExpStatusIcon.classList.add('partial');
    } else {
        detailExpStatusIcon.innerHTML = '<i class="fa-solid fa-circle-xmark"></i>';
        detailExpStatusIcon.classList.add('fail');
    }

    // Education Card metrics
    detailCandDegrees.textContent = candidate.candidate_degrees.length > 0 ? candidate.candidate_degrees.join(', ') : 'None listed';
    detailDegreeMatchStatus.textContent = candidate.degree_match ? 'Matched' : 'Not Matched';
    detailDegreeMatchStatus.style.color = candidate.degree_match ? 'var(--success)' : 'var(--danger)';

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

    // Highlight candidate raw snippet details (Phase 3)
    const highlightedSnippet = highlightTextSkills(candidate.snippet, candidate.matched_skills, candidate.missing_skills);
    detailSnippet.innerHTML = highlightedSnippet;

    // Toggle drawer open
    detailDrawer.classList.add('open');
}

function closeDrawer() {
    detailDrawer.classList.remove('open');
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && detailDrawer.classList.contains('open')) {
        closeDrawer();
    }
});

/* Export Shortlist report to CSV file */
exportBtn.addEventListener('click', () => {
    if (rankedCandidates.length === 0) {
        showToast("No candidates available to export.", "error");
        return;
    }

    const headers = [
        "Rank", "Candidate Name", "Match Score (%)", "Semantic Similarity (%)", 
        "Required Skills Score (%)", "Experience Score (%)", 
        "Years of Experience", "Degrees Extracted", "Degree Match Status"
    ];

    const rows = rankedCandidates.map((cand, idx) => [
        idx + 1,
        `"${cand.filename}"`,
        cand.score,
        cand.cosine_score,
        cand.skills_score.toFixed(1),
        cand.experience_score.toFixed(1),
        cand.candidate_exp,
        `"${cand.candidate_degrees.join(', ')}"`,
        cand.degree_match ? "Yes" : "No"
    ]);

    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'talentai_shortlist_report.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("CSV report downloaded successfully!", "success");
});
