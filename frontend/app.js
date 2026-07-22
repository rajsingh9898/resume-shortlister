// State management for uploaded files, candidate rankings, and JD requirements
let selectedFiles = [];
let rankedCandidates = [];
let activeJdSkills = [];
let jdExperienceRequired = 0;
let jdDegreesRequired = [];

// Filtering states
let activeFilterCategory = 'all'; // 'all', 'high', 'mid', 'exp', 'edu', 'shortlisted', 'rejected'
let activeChartSkillFilter = null; // Filter candidates by specific clicked chart skill bar
let activeMatchThreshold = 0; // Filter candidates by minimum score slider
let activeHistogramFilter = null; // Filter candidates by click on score distribution tier

// Candidate Checkbox Selection states
let selectedCandidates = [];

// Active Candidate in Details Drawer
let currentDrawerCandidate = null;

// DOM Elements
const appMain = document.getElementById('app-main');
const dropzone = document.getElementById('dropzone');
const resumeInput = document.getElementById('resume-input');
const fileList = document.getElementById('file-list');
const shortlistForm = document.getElementById('shortlist-form');
const jobDescriptionInput = document.getElementById('job-description');
const submitBtn = document.getElementById('submit-btn');
const btnLoader = document.getElementById('btn-loader');
const btnText = submitBtn.querySelector('.btn-text');

// Layout control buttons
const collapseSidebarBtn = document.getElementById('collapse-sidebar-btn');
const expandSidebarBtn = document.getElementById('expand-sidebar-btn');

// Backup DB restore DOM (Phase 7)
const dbDropzone = document.getElementById('db-dropzone');
const restoreDbInput = document.getElementById('restore-db-input');

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

// Pool Skills Chart DOM
const poolSkillsChartPanel = document.querySelector('.pool-skills-chart-panel');
const poolSkillsChart = document.getElementById('pool-skills-chart');

// Score Histogram Panel DOM
const scoreHistogramPanel = document.querySelector('.score-histogram-panel');
const scoreHistogram = document.getElementById('score-histogram');

// Filter Badges DOM
const filterBadgesContainer = document.getElementById('filter-badges-container');

// Threshold Filter DOM
const scoreThresholdSlider = document.getElementById('score-threshold-slider');
const lblThresholdVal = document.getElementById('lbl-threshold-val');

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

// Drawer Evaluation components
const btnStatusShortlisted = document.getElementById('btn-status-shortlisted');
const btnStatusReview = document.getElementById('btn-status-review');
const btnStatusRejected = document.getElementById('btn-status-rejected');
const drawerRecruiterNotes = document.getElementById('drawer-recruiter-notes');
const detailAiVerdictText = document.getElementById('detail-ai-verdict-text');
const detailInterviewQuestionsList = document.getElementById('detail-interview-questions-list');

// Pros & Cons lists (Phase 7)
const detailProsList = document.getElementById('detail-pros-list');
const detailConsList = document.getElementById('detail-cons-list');

// Soft Skills & Traits (Phase 8)
const detailSoftTraits = document.getElementById('detail-soft-traits');

// SVG Donut Rings DOM
const donutSegmentLanguages = document.getElementById('donut-segment-languages');
const donutSegmentFrameworks = document.getElementById('donut-segment-frameworks');
const donutSegmentDatabases = document.getElementById('donut-segment-databases');
const donutCenterTotal = document.getElementById('donut-center-total');
const legendLanguagesVal = document.getElementById('legend-languages-val');
const legendFrameworksVal = document.getElementById('legend-frameworks-val');
const legendDatabasesVal = document.getElementById('legend-databases-val');

// Floating Compare Bar DOM
const compareBar = document.getElementById('compare-bar');
const compareBarText = document.getElementById('compare-bar-text');
const compareClearBtn = document.getElementById('compare-clear-btn');
const compareTriggerBtn = document.getElementById('compare-trigger-btn');

// Comparison Modal DOM
const compareModal = document.getElementById('compare-modal');
const compareTable = document.getElementById('compare-table');

// Full-screen stage loader DOM
const processingOverlay = document.getElementById('processing-overlay');

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

/* Backup DB Restore Handlers (Phase 7) */
dbDropzone.addEventListener('click', () => restoreDbInput.click());

dbDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dbDropzone.classList.add('dragover');
});

dbDropzone.addEventListener('dragleave', () => {
    dbDropzone.classList.remove('dragover');
});

dbDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dbDropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
        processBackupJsonFile(e.dataTransfer.files[0]);
    }
});

restoreDbInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        processBackupJsonFile(e.target.files[0]);
    }
});

function processBackupJsonFile(file) {
    if (file.type !== 'application/json' && !file.name.endsWith('.json')) {
        showToast("Please upload a valid JSON backup file.", "error");
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const data = JSON.parse(e.target.result);
            if (typeof data !== 'object') {
                showToast("Invalid database structure.", "error");
                return;
            }

            let restoredCount = 0;
            Object.keys(data).forEach(key => {
                if (key.startsWith('talentai_status_') || key.startsWith('talentai_notes_')) {
                    localStorage.setItem(key, data[key]);
                    restoredCount++;
                }
            });

            showToast(`Successfully restored ${restoredCount} database entries!`, "success");
            
            // Reload candidates list to display restored tags and comments
            if (rankedCandidates.length > 0) {
                applyCandidatesFiltering();
            }
        } catch (err) {
            showToast("Failed to parse JSON file.", "error");
        }
    };
    reader.readAsText(file);
}

/* Sidebar Collapsing Layout Toggles */
collapseSidebarBtn.addEventListener('click', collapseSidebar);
expandSidebarBtn.addEventListener('click', expandSidebar);

function collapseSidebar() {
    appMain.classList.add('collapsed');
    expandSidebarBtn.classList.remove('hidden');
}

function expandSidebar() {
    appMain.classList.remove('collapsed');
    expandSidebarBtn.classList.add('hidden');
}

/* Strategy Weights Presets (Phase 7) */
window.applyWeightPreset = function(presetName) {
    const presets = {
        balanced: { semantic: 40, skills: 35, experience: 25 },
        tech: { semantic: 20, skills: 60, experience: 20 },
        leader: { semantic: 20, skills: 20, experience: 60 }
    };

    const target = presets[presetName];
    if (!target) return;

    // Toggle active state in HTML
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`preset-${presetName}`).classList.add('active');

    // Update slider values
    sliderSemantic.value = target.semantic;
    sliderSkills.value = target.skills;
    sliderExperience.value = target.experience;

    updateWeightsUI();
    if (rankedCandidates.length > 0) {
        recalculateRanking();
    }
};

/* Dynamic Weights (Slider Recalculations) */
[sliderSemantic, sliderSkills, sliderExperience].forEach(slider => {
    slider.addEventListener('input', () => {
        // Clear active class from preset buttons if user does manual adjustments
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.classList.remove('active');
        });
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

        if (jdExperienceRequired > 0.0) {
            if (cand.candidate_exp >= jdExperienceRequired) {
                cand.experience_score = 100.0;
            } else {
                cand.experience_score = (cand.candidate_exp / jdExperienceRequired) * 100;
            }
        } else {
            cand.experience_score = 100.0;
        }

        const finalScore = (cand.cosine_score * w.semantic / 100) + 
                             (cand.skills_score * w.skills / 100) + 
                             (cand.experience_score * w.experience / 100);
                             
        cand.score = parseFloat(finalScore.toFixed(1));
    });

    rankedCandidates.sort((a, b) => b.score - a.score);
    renderDashboard(rankedCandidates);
    renderPoolSkillsChart();
    renderScoreHistogram();
}

/* Multi-stage Processing Loader Controllers */
function showStageLoader() {
    processingOverlay.classList.add('active');
    const stages = ['ingest', 'tfidf', 'cosine', 'skills'];
    stages.forEach(st => setStageStatus(st, 'pending'));
}

function hideStageLoader() {
    processingOverlay.classList.remove('active');
}

function setStageStatus(stageId, status) {
    const el = document.getElementById(`stage-${stageId}`);
    if (!el) return;

    el.className = status;
    const icon = el.querySelector('i');
    
    if (status === 'pending') {
        icon.className = 'fa-regular fa-circle';
    } else if (status === 'active') {
        icon.className = 'fa-solid fa-spinner fa-spin';
    } else if (status === 'completed') {
        icon.className = 'fa-solid fa-circle-check';
    }
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
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

    showStageLoader();
    setStageStatus('ingest', 'active');

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

        setStageStatus('ingest', 'completed');
        setStageStatus('tfidf', 'active');
        await delay(600);

        setStageStatus('tfidf', 'completed');
        setStageStatus('cosine', 'active');
        await delay(600);

        const data = await response.json();

        setStageStatus('cosine', 'completed');
        setStageStatus('skills', 'active');
        await delay(500);

        if (response.ok && data.success) {
            rankedCandidates = data.candidates;
            
            activeJdSkills = data.jd_requirements.skills;
            jdExperienceRequired = data.jd_requirements.experience_years;
            jdDegreesRequired = data.jd_requirements.degrees;

            activeFilterCategory = 'all';
            activeChartSkillFilter = null;
            activeHistogramFilter = null;
            activeMatchThreshold = 0;
            scoreThresholdSlider.value = 0;
            lblThresholdVal.textContent = '0%';
            selectedCandidates = [];
            updateCompareBar();
            updateFilterBadgesUI();

            renderRequirementsEditor();
            recalculateRanking();
            
            setStageStatus('skills', 'completed');
            await delay(400);
            hideStageLoader();
            
            showToast("Resumes parsed and ranked successfully!", "success");
            
            setTimeout(() => {
                collapseSidebar();
            }, 1000);
        } else {
            hideStageLoader();
            const errorMsg = data.detail || "Failed to process resumes. Try again.";
            showToast(errorMsg, "error");
        }
    } catch (error) {
        hideStageLoader();
        console.error(error);
        showToast("Server connection error. Ensure backend is running.", "error");
    }
});

/* Dashboard Rendering */
function renderDashboard(candidates) {
    emptyState.classList.remove('active');
    resultsState.classList.add('active');

    statTotal.textContent = candidates.length;
    
    const strongMatchesCount = candidates.filter(c => c.score >= 70.0).length;
    statMatches.textContent = strongMatchesCount;

    const avgScore = candidates.reduce((acc, c) => acc + c.score, 0) / candidates.length;
    statAvg.textContent = `${avgScore.toFixed(1)}%`;

    applyCandidatesFiltering();
}

/* Filter Application Engine */
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
    } else if (activeFilterCategory === 'shortlisted') {
        filteredList = filteredList.filter(c => localStorage.getItem(`talentai_status_${c.filename}`) === 'Shortlisted');
    } else if (activeFilterCategory === 'rejected') {
        filteredList = filteredList.filter(c => localStorage.getItem(`talentai_status_${c.filename}`) === 'Rejected');
    }

    // 2. Filter by Match Tier Histogram Selection
    if (activeHistogramFilter) {
        if (activeHistogramFilter === 'low') {
            filteredList = filteredList.filter(c => c.score < 40.0);
        } else if (activeHistogramFilter === 'mid') {
            filteredList = filteredList.filter(c => c.score >= 40.0 && c.score < 70.0);
        } else if (activeHistogramFilter === 'high') {
            filteredList = filteredList.filter(c => c.score >= 70.0);
        }
    }

    // 3. Filter by Minimum Score Match Threshold slider
    if (activeMatchThreshold > 0) {
        filteredList = filteredList.filter(c => c.score >= activeMatchThreshold);
    }

    // 4. Filter by Active clicked skill bar from pool chart
    if (activeChartSkillFilter) {
        filteredList = filteredList.filter(c => {
            const candSkillsList = [];
            Object.values(c.all_extracted_skills).forEach(catSkills => {
                candSkillsList.push(...catSkills);
            });
            return candSkillsList.includes(activeChartSkillFilter);
        });
    }

    // 5. Filter by Search Query
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
        item.onclick = (e) => {
            if (e.target.closest('.candidate-checkbox-container') || e.target.closest('.candidate-card-checkbox')) {
                return;
            }
            openDrawer(candidate, index + 1);
        };

        const expLabel = candidate.candidate_exp > 0 ? `${candidate.candidate_exp} Yrs Exp` : 'Exp not listed';
        const degreeLabel = candidate.candidate_degrees.length > 0 ? candidate.candidate_degrees.join(', ') : 'No Degree listed';

        // Extract top 3 matched skills for card micro-badges
        const microBadgesHtml = candidate.matched_skills.slice(0, 3).map(skill => 
            `<span class="cand-meta-badge skills-micro">${skill}</span>`
        ).join('');

        const isChecked = selectedCandidates.includes(candidate.filename);

        const savedStatus = localStorage.getItem(`talentai_status_${candidate.filename}`);
        let statusBadgeHtml = '';
        if (savedStatus) {
            let badgeClass = 'review';
            if (savedStatus === 'Shortlisted') badgeClass = 'shortlisted';
            else if (savedStatus === 'Rejected') badgeClass = 'rejected';
            
            statusBadgeHtml = `<span class="cand-status-badge ${badgeClass}">${savedStatus}</span>`;
        }

        item.innerHTML = `
            <div class="candidate-checkbox-container">
                <input type="checkbox" class="candidate-card-checkbox" data-filename="${candidate.filename}" ${isChecked ? 'checked' : ''}>
            </div>
            <div class="candidate-main">
                <span class="rank-badge">#${index + 1}</span>
                <div class="candidate-profile">
                    <span class="candidate-title" title="${candidate.filename}">
                        ${candidate.filename}
                    </span>
                    <span class="candidate-subtitle">
                        ${statusBadgeHtml}
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
        
        const cb = item.querySelector('.candidate-card-checkbox');
        cb.addEventListener('change', (e) => {
            handleCandidateSelection(e.target.getAttribute('data-filename'), e.target.checked);
        });

        candidatesContainer.appendChild(item);
    });
}

/* Local Filter Input Listener */
searchCandidate.addEventListener('input', () => {
    applyCandidatesFiltering();
});

/* Toggle Quick Filter Badges */
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

/* Match Score Threshold Slider Listener */
scoreThresholdSlider.addEventListener('input', (e) => {
    activeMatchThreshold = parseInt(e.target.value);
    lblThresholdVal.textContent = `${activeMatchThreshold}%`;
    applyCandidatesFiltering();
});

/* Candidate Compare Selections Logic */
function handleCandidateSelection(filename, isChecked) {
    if (isChecked) {
        if (!selectedCandidates.includes(filename)) {
            if (selectedCandidates.length >= 3) {
                showToast("You can compare a maximum of 3 candidates side-by-side.", "error");
                const box = candidatesContainer.querySelector(`.candidate-card-checkbox[data-filename="${filename}"]`);
                if (box) box.checked = false;
                return;
            }
            selectedCandidates.push(filename);
        }
    } else {
        selectedCandidates = selectedCandidates.filter(f => f !== filename);
    }
    updateCompareBar();
}

function updateCompareBar() {
    const count = selectedCandidates.length;
    if (count > 0) {
        compareBar.classList.add('show');
        compareBarText.innerHTML = `<i class="fa-solid fa-circle-info"></i> Selected <strong>${count}</strong> candidate${count > 1 ? 's' : ''} for comparison.`;
        
        if (count >= 2 && count <= 3) {
            compareTriggerBtn.disabled = false;
            compareTriggerBtn.style.opacity = '1';
        } else {
            compareTriggerBtn.disabled = true;
            compareTriggerBtn.style.opacity = '0.5';
        }
    } else {
        compareBar.classList.remove('show');
    }
}

compareClearBtn.addEventListener('click', () => {
    selectedCandidates = [];
    updateCompareBar();
    const checkboxes = candidatesContainer.querySelectorAll('.candidate-card-checkbox');
    checkboxes.forEach(c => c.checked = false);
});

compareTriggerBtn.addEventListener('click', () => {
    if (selectedCandidates.length < 2 || selectedCandidates.length > 3) return;
    
    renderComparisonTable();
    compareModal.classList.add('open');
});

function closeCompareModal() {
    compareModal.classList.remove('open');
}

/* Render side-by-side matrices */
function renderComparisonTable() {
    compareTable.innerHTML = '';
    
    const targets = rankedCandidates.filter(c => selectedCandidates.includes(c.filename));
    
    const headRow = document.createElement('tr');
    const headerLabelCol = document.createElement('th');
    headerLabelCol.textContent = 'Qualification / Metric';
    headRow.appendChild(headerLabelCol);
    
    targets.forEach((cand, idx) => {
        const th = document.createElement('th');
        th.innerHTML = `<div style="color: var(--primary-color);">Candidate #${idx+1}</div><div style="font-size:0.85rem; word-break:break-all;">${cand.filename}</div>`;
        headRow.appendChild(th);
    });
    compareTable.appendChild(headRow);

    const rowsMap = [
        {
            label: "Overall Match Score",
            renderer: (cand) => {
                let scoreClass = 'low';
                if (cand.score >= 70) scoreClass = 'high';
                else if (cand.score >= 40) scoreClass = 'mid';
                return `<strong class="compare-score ${scoreClass}">${cand.score}%</strong>`;
            }
        },
        {
            label: "Review Status",
            renderer: (cand) => {
                const status = localStorage.getItem(`talentai_status_${cand.filename}`) || 'Under Review';
                let styleStr = 'color: var(--text-dark);';
                if (status === 'Shortlisted') styleStr = 'color: #34d399; font-weight:700;';
                else if (status === 'Under Review') styleStr = 'color: #fbbf24; font-weight:700;';
                else if (status === 'Rejected') styleStr = 'color: #fb7185; font-weight:700;';
                return `<span style="${styleStr}">${status}</span>`;
            }
        },
        {
            label: "Semantic Relevance",
            renderer: (cand) => `${cand.cosine_score}%`
        },
        {
            label: "Skills Coverage",
            renderer: (cand) => `${cand.skills_score.toFixed(1)}%`
        },
        {
            label: "Experience Alignment",
            renderer: (cand) => `${cand.experience_score.toFixed(1)}%`
        },
        {
            label: "Years of Experience",
            renderer: (cand) => `<strong>${cand.candidate_exp} Years</strong> (Required: ${jdExperienceRequired} Yrs)`
        },
        {
            label: "Degree Extracted",
            renderer: (cand) => cand.candidate_degrees.length > 0 ? cand.candidate_degrees.join(', ') : 'None listed'
        },
        {
            label: "Degree Match Status",
            renderer: (cand) => cand.degree_match ? 
                '<span style="color:var(--success); font-weight:600;"><i class="fa-solid fa-circle-check"></i> Matched</span>' : 
                '<span style="color:var(--danger); font-weight:600;"><i class="fa-solid fa-circle-xmark"></i> Not Matched</span>'
        },
        {
            label: "Matched Skills",
            renderer: (cand) => {
                if (cand.matched_skills.length === 0) return '<span style="color:var(--text-dark);">None</span>';
                return `<div class="compare-badge-list">${cand.matched_skills.map(s => `<span class="badge" style="background:var(--success-bg); color:#34d399; border:1px solid var(--success-border);">${s}</span>`).join('')}</div>`;
            }
        },
        {
            label: "Missing Required Skills",
            renderer: (cand) => {
                if (cand.missing_skills.length === 0) return '<span style="color:var(--text-dark);">None</span>';
                return `<div class="compare-badge-list">${cand.missing_skills.map(s => `<span class="badge" style="background:var(--danger-bg); color:#fb7185; border:1px solid var(--danger-border);">${s}</span>`).join('')}</div>`;
            }
        }
    ];

    rowsMap.forEach(rowData => {
        const row = document.createElement('tr');
        const labelCol = document.createElement('td');
        labelCol.textContent = rowData.label;
        row.appendChild(labelCol);
        
        targets.forEach(cand => {
            const td = document.createElement('td');
            td.innerHTML = rowData.renderer(cand);
            row.appendChild(td);
        });
        compareTable.appendChild(row);
    });
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && compareModal.classList.contains('open')) {
        closeCompareModal();
    }
});

/* Heuristic AI Verdict Summary Card generator */
function generateCandidateVerdict(cand) {
    const score = cand.score;
    const matchedCount = cand.matched_skills.length;
    const requiredCount = activeJdSkills.length;
    
    let summary = '';
    
    if (score >= 70.0) {
        summary = `<strong>Highly Recommended</strong>: <em>${cand.filename}</em> shows an outstanding profile alignment with a <strong>${score}% Match Score</strong>. They cover <strong>${matchedCount} of ${requiredCount}</strong> required skills including core areas like <em>${cand.matched_skills.slice(0, 3).join(', ')}</em>. They meet or exceed the required experience threshold with <strong>${cand.candidate_exp} years</strong> of experience, and their educational degrees meet the criteria. Recommended next step: Schedule a direct technical interview.`;
    } else if (score >= 40.0) {
        const gapText = cand.missing_skills.length > 0 ? ` They exhibit missing required skills in key JD areas: <em>${cand.missing_skills.slice(0, 3).join(', ')}</em>.` : '';
        
        summary = `<strong>Under Review</strong>: <em>${cand.filename}</em> is a partial match with a <strong>${score}% Match Score</strong>. They have <strong>${cand.candidate_exp} years</strong> of experience and match <strong>${matchedCount} of ${requiredCount}</strong> required skills.${gapText} Recommended next step: Conduct a phone screening call to assess their competency details in the missing core skills.`;
    } else {
        const degreeNotice = !cand.degree_match && jdDegreesRequired.length > 0 ? ' Educational degree requirements are also not aligned.' : '';
        
        summary = `<strong>Not Recommended</strong>: <em>${cand.filename}</em> is a low match with a <strong>${score}% Match Score</strong>. They only match <strong>${matchedCount} of ${requiredCount}</strong> required skills, and have <strong>${cand.candidate_exp} years</strong> of experience.${degreeNotice} Recommended next step: Archive application.`;
    }
    
    return summary;
}

/* Contextual Screening Questions Generator based on skill gaps */
function generateInterviewQuestions(cand) {
    const list = [];
    
    const skillQuestionsTemplates = {
        'Docker': "Could you walk us through how you would optimize a Dockerfile using multi-stage builds and minimize image sizes?",
        'Kubernetes': "How have you managed Kubernetes secrets, resource configurations, and ingress traffic routing in staging or production?",
        'FastAPI': "What are the core differences between FastAPI async endpoints and traditional WSGI frameworks like Flask, and how do you handle exception testing?",
        'React': "Can you explain React fiber reconciliation and how you would prevent unnecessary re-rendering in large lists?",
        'CI/CD': "How have you automated pipelines in your previous role, and what steps did you include to handle validation test failures?",
        'Git': "How do you handle complex git merge conflicts or cherry-picking scenarios within a multi-developer git workflow?",
        'PostgreSQL': "Can you describe a scenario where you had to debug a slow query in PostgreSQL, and how did you use indexing or EXPLAIN ANALYZE?",
        'Python': "What are your preferred methods for profiling and optimizing execution speeds or memory usage in Python applications?"
    };

    if (cand.missing_skills.length > 0) {
        cand.missing_skills.slice(0, 3).forEach(skill => {
            const template = skillQuestionsTemplates[skill];
            if (template) {
                list.push(`<strong>Focus on ${skill}</strong>: "${template}"`);
            } else {
                list.push(`<strong>Focus on ${skill}</strong>: "Can you detail a scenario in a previous project where you had to implement ${skill}? What technical challenges did you encounter?"`);
            }
        });
    }

    if (jdExperienceRequired > 0 && cand.candidate_exp < jdExperienceRequired) {
        list.push(`<strong>Experience Alignment</strong>: "The JD requests ${jdExperienceRequired} years of experience, and your profile lists ${cand.candidate_exp} years. Can you describe how your intensive hands-on experience has equipped you to succeed in this role?"`);
    }

    if (list.length === 0) {
        list.push(`<strong>System Scaling</strong>: "Can you describe a complex system design challenge you resolved in a past role, focusing on security and scaling?"`);
        list.push(`<strong>Technology Ingestion</strong>: "How do you evaluate and safely integrate new frameworks or packages into an existing production codebase?"`);
    }

    return list;
}

/* LocalStorage status rating setters */
window.setCandidateStatus = function(status) {
    if (!currentDrawerCandidate) return;
    
    const filename = currentDrawerCandidate.filename;
    localStorage.setItem(`talentai_status_${filename}`, status);
    
    updateDrawerStatusUI(status);
    applyCandidatesFiltering();
    
    showToast(`Status updated: ${filename} is now marked as "${status}"`, "success");
};

function updateDrawerStatusUI(status) {
    btnStatusShortlisted.classList.remove('active');
    btnStatusReview.classList.remove('active');
    btnStatusRejected.classList.remove('active');
    
    if (status === 'Shortlisted') {
        btnStatusShortlisted.classList.add('active');
    } else if (status === 'Under Review') {
        btnStatusReview.classList.add('active');
    } else if (status === 'Rejected') {
        btnStatusRejected.classList.add('active');
    }
}

drawerRecruiterNotes.addEventListener('input', (e) => {
    if (!currentDrawerCandidate) return;
    const filename = currentDrawerCandidate.filename;
    localStorage.setItem(`talentai_notes_${filename}`, e.target.value);
});

/* Dynamic Pros & Cons bullet points logic generator (Phase 7) */
function renderProsAndConsList(candidate) {
    detailProsList.innerHTML = '';
    detailConsList.innerHTML = '';

    const pros = [];
    const cons = [];

    // 1. Check Experience alignment
    if (jdExperienceRequired > 0) {
        if (candidate.candidate_exp >= jdExperienceRequired) {
            const extra = candidate.candidate_exp - jdExperienceRequired;
            if (extra > 0) {
                pros.push(`Experience (<strong>${candidate.candidate_exp} years</strong>) exceeds requirements by <strong>${extra} Yrs</strong>.`);
            } else {
                pros.push(`Meets experience requirement exactly (<strong>${candidate.candidate_exp} years</strong>).`);
            }
        } else {
            const short = jdExperienceRequired - candidate.candidate_exp;
            cons.push(`Experience (<strong>${candidate.candidate_exp} Yrs</strong>) is short of requirement by <strong>${short} years</strong>.`);
        }
    } else {
        if (candidate.candidate_exp > 0) {
            pros.push(`Candidate brings <strong>${candidate.candidate_exp} years</strong> of hands-on experience.`);
        }
    }

    // 2. Check Degree Match
    if (jdDegreesRequired.length > 0) {
        if (candidate.degree_match) {
            pros.push(`Educational credentials matched: Found <strong>${candidate.candidate_degrees.join(', ')}</strong>.`);
        } else {
            cons.push(`Missing requested educational degree (Requires: <strong>${jdDegreesRequired.join(' or ')}</strong>).`);
        }
    }

    // 3. Check Matched Skills strengths
    if (candidate.matched_skills.length > 0) {
        const topMatched = candidate.matched_skills.slice(0, 3);
        pros.push(`Strong core matches for required skill chips: <em>${topMatched.join(', ')}</em>.`);
    } else {
        cons.push(`Matches 0 required skills specified on the active requirements index.`);
    }

    // 4. Check missing skills gaps
    if (candidate.missing_skills.length > 0) {
        const topMissing = candidate.missing_skills.slice(0, 3);
        cons.push(`Gaps identified in required skills: <em>${topMissing.join(', ')}</em>.`);
    } else if (activeJdSkills.length > 0) {
        pros.push(`Flawless required skills profile - covers 100% of skills index!`);
    }

    // Render lists in HTML
    if (pros.length === 0) {
        detailProsList.innerHTML = '<li>No significant strengths flagged.</li>';
    } else {
        pros.forEach(p => {
            const li = document.createElement('li');
            li.innerHTML = p;
            detailProsList.appendChild(li);
        });
    }

    if (cons.length === 0) {
        detailConsList.innerHTML = '<li>No significant gaps flagged.</li>';
    } else {
        cons.forEach(c => {
            const li = document.createElement('li');
            li.innerHTML = c;
            detailConsList.appendChild(li);
        });
    }
}

/* Interactive Score Distribution Histogram Rendering */
function renderScoreHistogram() {
    if (rankedCandidates.length === 0) {
        scoreHistogramPanel.classList.remove('active');
        return;
    }

    scoreHistogramPanel.classList.add('active');
    scoreHistogram.innerHTML = '';

    // Calculate score bins
    let lowCount = 0;
    let midCount = 0;
    let highCount = 0;

    rankedCandidates.forEach(c => {
        if (c.score < 40.0) lowCount++;
        else if (c.score < 70.0) midCount++;
        else Math.max(0, highCount++);
    });

    const maxCount = Math.max(lowCount, midCount, highCount, 1);
    
    const bins = [
        { key: 'low', count: lowCount, label: 'Low (<40%)' },
        { key: 'mid', count: midCount, label: 'Mid (40-70%)' },
        { key: 'high', count: highCount, label: 'Strong (70-100%)' }
    ];

    bins.forEach(bin => {
        const heightPercent = (bin.count / maxCount) * 100;
        
        const binEl = document.createElement('div');
        binEl.className = 'histogram-bin';
        if (activeHistogramFilter === bin.key) {
            binEl.classList.add('filter-active');
        }
        
        binEl.onclick = () => toggleHistogramFilter(bin.key);

        binEl.innerHTML = `
            <span class="histogram-count">${bin.count}</span>
            <div class="histogram-bar-track">
                <div class="histogram-bar-fill" style="height: 0%;"></div>
            </div>
            <span class="histogram-label">${bin.label}</span>
        `;

        scoreHistogram.appendChild(binEl);
        
        // Trigger height transition
        setTimeout(() => {
            const fill = binEl.querySelector('.histogram-bar-fill');
            if (fill) fill.style.height = `${heightPercent}%`;
        }, 50);
    });
}

function toggleHistogramFilter(binKey) {
    if (activeHistogramFilter === binKey) {
        activeHistogramFilter = null;
        showToast("Cleared score band filter.", "info");
    } else {
        activeHistogramFilter = binKey;
        showToast(`Filtering candidates by match tier: ${binKey}`, "success");
    }
    renderScoreHistogram();
    applyCandidatesFiltering();
}

/* Category Skill Mapping Helper */
function getSkillCategoryRatios(candidate) {
    const categoriesMap = {
        languages: ['Python', 'Javascript', 'Go', 'C++', 'Rust', 'Java', 'TypeScript', 'SQL', 'HTML', 'CSS', 'Ruby', 'Bash', 'C#'],
        frameworks: ['FastAPI', 'Django', 'Flask', 'React', 'Angular', 'Vue', 'Next.js', 'Node.js', 'Express', 'Spring', 'PyTorch', 'TensorFlow', 'Keras', 'Django REST Framework', 'Tailwind', 'Sass'],
        databases: ['Docker', 'Kubernetes', 'AWS', 'GCP', 'Azure', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch', 'Git', 'CI/CD', 'GitHub', 'Jenkins', 'Terraform', 'Ansible', 'Linux']
    };

    const candSkills = new Set();
    Object.values(candidate.all_extracted_skills).forEach(catSkills => {
        catSkills.forEach(s => candSkills.add(s));
    });

    const getMatchedInCategory = (catName) => {
        const refs = categoriesMap[catName];
        const matched = activeJdSkills.filter(s => candSkills.has(s) && refs.includes(s));
        const required = activeJdSkills.filter(s => refs.includes(s));
        
        return {
            matchedCount: matched.length,
            requiredCount: required.length,
            ratio: required.length > 0 ? (matched.length / required.length) * 100 : 100.0
        };
    };

    return {
        languages: getMatchedInCategory('languages'),
        frameworks: getMatchedInCategory('frameworks'),
        databases: getMatchedInCategory('databases')
    };
}

/* Animate SVG Donut concentric rings */
function animateSkillDonut(candidate) {
    const ratios = getSkillCategoryRatios(candidate);
    
    const rings = [
        { el: donutSegmentLanguages, r: 45, ratio: ratios.languages.ratio, legend: legendLanguagesVal },
        { el: donutSegmentFrameworks, r: 33, ratio: ratios.frameworks.ratio, legend: legendFrameworksVal },
        { el: donutSegmentDatabases, r: 21, ratio: ratios.databases.ratio, legend: legendDatabasesVal }
    ];

    rings.forEach(ring => {
        ring.el.setAttribute('r', ring.r);
        
        const circ = 2 * Math.PI * ring.r;
        ring.el.style.strokeDasharray = `${circ}`;
        ring.el.style.strokeDashoffset = `${circ}`;
        
        setTimeout(() => {
            const offset = circ - (ring.ratio / 100) * circ;
            ring.el.style.strokeDashoffset = offset;
        }, 50);
        
        ring.legend.textContent = `${ring.ratio.toFixed(0)}%`;
    });

    const totalCoverage = candidate.skills_score;
    donutCenterTotal.textContent = `${totalCoverage.toFixed(0)}%`;
}

/* PDF print candidate screening report trigger */
window.printCandidateReport = function() {
    if (!currentDrawerCandidate) return;
    
    const originalTitle = document.title;
    document.title = `TalentAI_Screening_Report_${currentDrawerCandidate.filename.replace(/\.[^/.]+$/, "")}`;
    
    window.print();
    
    document.title = originalTitle;
};

/* Export full recruiter database backup package (Phase 7) */
window.exportDatabaseBackup = function() {
    const backupObj = {};
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key.startsWith('talentai_status_') || key.startsWith('talentai_notes_')) {
            backupObj[key] = localStorage.getItem(key);
        }
    }

    const jsonStr = JSON.stringify(backupObj, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `talentai_database_backup_${new Date().toISOString().slice(0,10)}.json`;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast("JSON database backup package exported successfully!", "success");
};

/* Pool Skills Frequency Chart rendering */
function renderPoolSkillsChart() {
    if (rankedCandidates.length === 0) {
        poolSkillsChartPanel.classList.remove('active');
        return;
    }

    poolSkillsChartPanel.classList.add('active');
    poolSkillsChart.innerHTML = '';

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

    const sortedSkills = Object.keys(freq).map(skill => {
        return { name: skill, count: freq[skill] };
    }).sort((a, b) => b.count - a.count).slice(0, 5);

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
        
        setTimeout(() => {
            const fill = barGroup.querySelector('.bar-fill');
            if (fill) fill.style.width = `${percentage}%`;
        }, 50);
    });
}

function toggleSkillChartFilter(skillName) {
    if (activeChartSkillFilter === skillName) {
        activeChartSkillFilter = null;
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

/* Dynamic Skill Highlighter with Synonym Support (Phase 8) */
const SKILL_SYNONYMS = {
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
};

function highlightTextSkills(rawText, matchedSkills, missingSkills) {
    let tempText = rawText;
    const replacements = {};
    let tokenIndex = 0;
    
    const keywords = [];
    matchedSkills.forEach(s => keywords.push({ word: s, type: 'match' }));
    missingSkills.forEach(s => keywords.push({ word: s, type: 'miss' }));
    
    keywords.sort((a, b) => b.word.length - a.word.length);
    
    function escapeRegExp(str) {
        return str.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
    }
    
    keywords.forEach(kw => {
        const searchWords = [kw.word];
        if (SKILL_SYNONYMS[kw.word]) {
            searchWords.push(...SKILL_SYNONYMS[kw.word]);
        }
        searchWords.sort((a, b) => b.length - a.length);

        searchWords.forEach(word => {
            const pattern = new RegExp('\\b(' + escapeRegExp(word) + ')\\b', 'gi');
            tempText = tempText.replace(pattern, (match) => {
                const token = `__TOKEN_SKILL_${tokenIndex}__`;
                replacements[token] = `<mark class="highlight-${kw.type}">${match}</mark>`;
                tokenIndex++;
                return token;
            });
        });
    });
    
    const dummyDiv = document.createElement('div');
    dummyDiv.innerText = tempText;
    let safeHtml = dummyDiv.innerHTML;
    
    Object.keys(replacements).forEach(token => {
        safeHtml = safeHtml.replace(token, replacements[token]);
    });
    
    return safeHtml;
}

/* Detail Drawer Handlers */
function openDrawer(candidate, rank) {
    currentDrawerCandidate = candidate;
    
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

    // Load persisted status & notes from localStorage
    const savedStatus = localStorage.getItem(`talentai_status_${candidate.filename}`) || 'Under Review';
    updateDrawerStatusUI(savedStatus);
    
    const savedNotes = localStorage.getItem(`talentai_notes_${candidate.filename}`) || '';
    drawerRecruiterNotes.value = savedNotes;

    // Generate dynamic Heuristic AI Verdict fit summary
    detailAiVerdictText.innerHTML = generateCandidateVerdict(candidate);

    // Render pros & cons list (Phase 7)
    renderProsAndConsList(candidate);

    // Render soft traits list (Phase 8)
    detailSoftTraits.innerHTML = '';
    if (!candidate.soft_traits || candidate.soft_traits.length === 0) {
        detailSoftTraits.innerHTML = '<span class="text-dark" style="font-size: 0.8rem;">No leadership or architectural soft traits flagged.</span>';
    } else {
        candidate.soft_traits.forEach(trait => {
            const badge = document.createElement('span');
            badge.className = 'badge';
            badge.style.background = 'rgba(192, 132, 252, 0.12)';
            badge.style.color = '#c084fc';
            badge.style.border = '1px solid rgba(192, 132, 252, 0.2)';
            badge.innerHTML = `<i class="fa-solid fa-circle-nodes" style="margin-right: 5px; font-size: 0.7rem;"></i> ${trait}`;
            detailSoftTraits.appendChild(badge);
        });
    }

    // Generate context screening questions list
    const questions = generateInterviewQuestions(candidate);
    detailInterviewQuestionsList.innerHTML = '';
    questions.forEach(q => {
        const li = document.createElement('li');
        li.innerHTML = q;
        detailInterviewQuestionsList.appendChild(li);
    });

    // Animate SVG category donut chart coverage
    animateSkillDonut(candidate);

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

    // Highlight candidate raw snippet details
    const highlightedSnippet = highlightTextSkills(candidate.snippet, candidate.matched_skills, candidate.missing_skills);
    detailSnippet.innerHTML = highlightedSnippet;

    // Toggle drawer open
    detailDrawer.classList.add('open');
}

// Bind button status selector events dynamically
btnStatusShortlisted.onclick = () => setCandidateStatus('Shortlisted');
btnStatusReview.onclick = () => setCandidateStatus('Under Review');
btnStatusRejected.onclick = () => setCandidateStatus('Rejected');

function closeDrawer() {
    detailDrawer.classList.remove('open');
    currentDrawerCandidate = null;
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
        "Rank", "Candidate Name", "Match Score (%)", "Evaluation Status", "Semantic Similarity (%)", 
        "Required Skills Score (%)", "Experience Score (%)", 
        "Years of Experience", "Degrees Extracted", "Degree Match Status", "Recruiter Notes"
    ];

    const rows = rankedCandidates.map((cand, idx) => {
        const savedStatus = localStorage.getItem(`talentai_status_${cand.filename}`) || 'Under Review';
        const savedNotes = localStorage.getItem(`talentai_notes_${cand.filename}`) || '';
        const cleanedNotes = savedNotes.replace(/"/g, '""');

        return [
            idx + 1,
            `"${cand.filename}"`,
            cand.score,
            `"${savedStatus}"`,
            cand.cosine_score,
            cand.skills_score.toFixed(1),
            cand.experience_score.toFixed(1),
            cand.candidate_exp,
            `"${cand.candidate_degrees.join(', ')}"`,
            cand.degree_match ? "Yes" : "No",
            `"${cleanedNotes}"`
        ];
    });

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

// Theme switcher state management (Phase 8 Theme Toggle)
const themeToggleBtn = document.getElementById('theme-toggle-btn');
const savedTheme = localStorage.getItem('talentai_theme') || 'light';

if (savedTheme === 'dark') {
    document.body.classList.add('dark-theme');
    if (themeToggleBtn) themeToggleBtn.innerHTML = '<i class="fa-solid fa-sun"></i>';
} else {
    document.body.classList.remove('dark-theme');
    if (themeToggleBtn) themeToggleBtn.innerHTML = '<i class="fa-solid fa-moon"></i>';
}

if (themeToggleBtn) {
    themeToggleBtn.onclick = () => {
        if (document.body.classList.contains('dark-theme')) {
            document.body.classList.remove('dark-theme');
            themeToggleBtn.innerHTML = '<i class="fa-solid fa-moon"></i>';
            localStorage.setItem('talentai_theme', 'light');
            showToast("Switched to Light Unicorn Silver theme", "success");
        } else {
            document.body.classList.add('dark-theme');
            themeToggleBtn.innerHTML = '<i class="fa-solid fa-sun"></i>';
            localStorage.setItem('talentai_theme', 'dark');
            showToast("Switched to Dark Unicorn Silver theme", "success");
        }
    };
}
