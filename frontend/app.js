// State management for uploaded files, candidate rankings, and JD requirements
let selectedFiles = [];
let rankedCandidates = [];
let activeJdSkills = [];
let jdExperienceRequired = 0;
let jdDegreesRequired = [];
let currentJobId = null;
let biasBlindMode = false;
let currentHiringBrief = null;
let currentPage = 1;
let currentLimit = 1000;
let totalPages = 1;
let currentUser = null;
let userToken = localStorage.getItem('talentai_token') || null;

// Filtering states
let activeFilterCategory = 'all'; 
let activeChartSkillFilter = null;
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

// On-demand Full Resume Text elements
const btnToggleResumeText = document.getElementById('btn-toggle-resume-text');
const fullResumeTextContainer = document.getElementById('full-resume-text-container');
const detailFullResumeText = document.getElementById('detail-full-resume-text');

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
    const maxFiles = 50;
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

            // Upload backup to PostgreSQL database restore endpoint
            fetch('/api/backup/import', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${userToken}`
                },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(resData => {
                if (resData.success) {
                    // Synchronize client-side local cache
                    let restoredCount = 0;
                    Object.keys(data).forEach(key => {
                        if (key.startsWith('talentai_status_') || key.startsWith('talentai_notes_')) {
                            localStorage.setItem(key, data[key]);
                            restoredCount++;
                        }
                    });

                    showToast(`Successfully restored ${resData.restored_count} database entries!`, "success");
                    
                    // Reload candidates list to display restored tags and comments
                    if (rankedCandidates.length > 0) {
                        applyCandidatesFiltering();
                    }
                } else {
                    showToast("Backup restore failed on PostgreSQL database.", "error");
                }
            })
            .catch(err => {
                showToast("Failed to connect to database backup service.", "error");
                console.error(err);
            });
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
    if (currentJobId) {
        fetchJobCandidates(currentJobId, 1);
        return;
    }
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

    const biasContainer = document.getElementById('bias-warnings-container');
    if (biasContainer) biasContainer.style.display = 'none';

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

    const blendWeightSlider = document.getElementById('semantic-blend-weight');
    const semanticWeight = blendWeightSlider ? parseFloat(blendWeightSlider.value) / 100.0 : 0.5;

    try {
        // 1. Generate pre-signed upload URLs and upload files directly to S3
        const resumesPayload = [];
        for (const file of selectedFiles) {
            const presignRes = await fetch('/api/storage/presign-upload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${userToken}`
                },
                body: JSON.stringify({
                    filename: file.name,
                    content_type: file.type || "application/octet-stream"
                })
            });
            if (!presignRes.ok) {
                const errData = await presignRes.json();
                throw new Error(errData.detail || `Failed to generate pre-signed URL for ${file.name}`);
            }
            const presignData = await presignRes.json();
            
            // PUT file directly to pre-signed URL (MinIO/S3 or simulated endpoint)
            const uploadRes = await fetch(presignData.upload_url, {
                method: 'PUT',
                headers: {
                    'Content-Type': file.type || "application/octet-stream"
                },
                body: file
            });
            if (!uploadRes.ok) {
                throw new Error(`Failed to upload ${file.name} directly to storage bucket.`);
            }
            
            resumesPayload.push({
                filename: file.name,
                object_key: presignData.object_key
            });
        }

        const mindsetEl = document.getElementById('team-mindset');
        const focusEl = document.getElementById('team-focus');
        const expectationEl = document.getElementById('team-expectation');
        const teamProfile = {
            mindset: mindsetEl ? mindsetEl.value : 'Enterprise',
            focus: focusEl ? focusEl.value : 'Backend-heavy',
            expectation: expectationEl ? expectationEl.value : 'Ownership'
        };

        // 2. Dispatch the shortlist task with S3 object keys JSON
        const response = await fetch('/api/shortlist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${userToken}`
            },
            body: JSON.stringify({
                jd: jd,
                semantic_weight: semanticWeight,
                resumes: resumesPayload,
                team_profile: teamProfile
            })
        });

        const data = await response.json();
        if (!response.ok || !data.success) {
            hideStageLoader();
            const errorMsg = data.detail || "Failed to start shortlisting.";
            showToast(errorMsg, "error");
            return;
        }

        setStageStatus('ingest', 'completed');
        setStageStatus('tfidf', 'active');
        await delay(300);

        setStageStatus('tfidf', 'completed');
        setStageStatus('cosine', 'active');
        await delay(300);

        // Hide stages loader and show task progress modal
        hideStageLoader();
        const taskModal = document.getElementById('task-progress-modal');
        const progressBar = document.getElementById('task-progress-bar');
        const filesList = document.getElementById('task-files-list');
        
        if (taskModal) taskModal.style.display = 'flex';
        if (progressBar) progressBar.style.width = '0%';
        if (filesList) filesList.innerHTML = '';

        const taskId = data.task_id;
        currentJobId = data.job_id;

        // Start polling Celery task status
        const pollInterval = setInterval(async () => {
            try {
                const pollRes = await fetch(`/api/tasks/${taskId}`, {
                    headers: { 'Authorization': `Bearer ${userToken}` }
                });
                if (!pollRes.ok) throw new Error("Failed to check task progress.");
                const pollData = await pollRes.json();

                if (pollData.status === 'PROGRESS') {
                    // Update progress bar
                    if (progressBar) progressBar.style.width = (pollData.progress * 100) + '%';
                    
                    // Update files list checklist in modal
                    if (filesList && pollData.files) {
                        filesList.innerHTML = '';
                        Object.entries(pollData.files).forEach(([filename, status]) => {
                            let badgeColor = '#94a3b8';
                            let icon = '<i class="fa-regular fa-clock"></i>';
                            if (status === 'processing') {
                                badgeColor = '#3b82f6';
                                icon = '<i class="fa-solid fa-spinner fa-spin"></i>';
                            } else if (status === 'done') {
                                badgeColor = '#22c55e';
                                icon = '<i class="fa-solid fa-check"></i>';
                            }
                            filesList.innerHTML += `
                                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; padding: 6px 12px; background: rgba(255, 255, 255, 0.02); border-radius: 6px;">
                                    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 320px;">${filename}</span>
                                    <span style="color: ${badgeColor}; display: flex; align-items: center; gap: 6px;">${icon} ${status}</span>
                                </div>
                            `;
                        });
                    }
                } else if (pollData.status === 'SUCCESS') {
                    clearInterval(pollInterval);
                    if (progressBar) progressBar.style.width = '100%';
                    await delay(500);
                    if (taskModal) taskModal.style.display = 'none';

                    // Reset filters
                    activeFilterCategory = 'all';
                    activeChartSkillFilter = null;
                    activeHistogramFilter = null;
                    activeMatchThreshold = 0;
                    scoreThresholdSlider.value = 0;
                    lblThresholdVal.textContent = '0%';
                    selectedCandidates = [];
                    updateCompareBar();
                    updateFilterBadgesUI();

                    // Load paginated candidates for page 1
                    currentPage = 1;
                    await fetchJobCandidates(currentJobId, 1);
                    
                    showToast("Resumes parsed and ranked successfully!", "success");

                    setTimeout(() => {
                        collapseSidebar();
                    }, 1000);

                } else if (pollData.status === 'FAILURE' || pollData.status === 'REVOKED') {
                    clearInterval(pollInterval);
                    if (taskModal) taskModal.style.display = 'none';
                    showToast(`Background process failed: ${pollData.error || 'Job revoked.'}`, "error");
                }
            } catch (pollErr) {
                console.error("Polling error:", pollErr);
            }
        }, 1500);

    } catch (error) {
        hideStageLoader();
        console.error(error);
        showToast("Server connection error. Ensure backend is running.", "error");
    }
});

/* Asynchronously Fetch Job Candidates from Paginated API */
async function fetchJobCandidates(jobId, page = 1) {
    if (!jobId) return;
    currentPage = page;
    
    let filter = activeFilterCategory;
    if (activeHistogramFilter) {
        filter = activeHistogramFilter;
    }
    const threshold = activeMatchThreshold;
    const search = searchCandidate.value.trim();
    const w = getWeights();
    
    let url = `/api/jobs/${jobId}/candidates?page=${page}&limit=${currentLimit}`;
    url += `&semantic_w=${w.semantic}&skills_w=${w.skills}&experience_w=${w.experience}&bias_blind=${biasBlindMode}`;
    
    if (filter && filter !== 'all') {
        url += `&filter=${filter}`;
    }
    if (threshold > 0) {
        url += `&threshold=${threshold}`;
    }
    if (search) {
        url += `&search=${encodeURIComponent(search)}`;
    }
    if (activeChartSkillFilter) {
        url += `&skill=${encodeURIComponent(activeChartSkillFilter)}`;
    }
    
    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${userToken}` }
        });
        if (!response.ok) throw new Error("Failed to fetch job candidates.");
        const data = await response.json();
        
        rankedCandidates = data.candidates;
        totalPages = data.total_pages;
        
        // Sync candidate status/comments into localStorage for card render status sync
        rankedCandidates.forEach(cand => {
            if (cand.status) {
                localStorage.setItem(`talentai_status_${cand.filename}`, cand.status);
            }
            if (cand.notes !== undefined) {
                localStorage.setItem(`talentai_notes_${cand.filename}`, cand.notes);
            }
        });
        
        // Render stats counters
        statTotal.textContent = data.stats.total_resumes;
        statMatches.textContent = data.stats.strong_matches;
        statAvg.textContent = `${data.stats.average_score.toFixed(1)}%`;
        
        // Render requirements
        activeJdSkills = data.jd_requirements.skills;
        jdExperienceRequired = data.jd_requirements.experience_years;
        jdDegreesRequired = data.jd_requirements.degrees;
        renderRequirementsEditor();
        
        // Render Market Intelligence Dashboard Card
        const marketPanel = document.getElementById('market-intelligence-panel');
        if (marketPanel && data.market_intelligence) {
            const mi = data.market_intelligence;
            
            // Classified role
            const roleEl = marketPanel.querySelector('.fa-brain-circuit + span');
            if (roleEl) roleEl.textContent = `Market Insight: ${mi.classified_role}`;
            
            // Salary range
            const salaryVal = document.getElementById('market-salary-val');
            if (salaryVal) salaryVal.textContent = mi.salary_range;
            
            // Supply difficulty / Feasibility
            const difficultyBadge = document.getElementById('market-difficulty-badge');
            if (difficultyBadge) {
                difficultyBadge.textContent = mi.difficulty;
                if (mi.difficulty.includes("Low Supply")) {
                    difficultyBadge.style.background = 'rgba(239, 68, 68, 0.2)';
                    difficultyBadge.style.color = '#f87171';
                    difficultyBadge.style.border = '1px solid rgba(239, 68, 68, 0.3)';
                } else if (mi.difficulty.includes("Moderate")) {
                    difficultyBadge.style.background = 'rgba(245, 158, 11, 0.2)';
                    difficultyBadge.style.color = '#fbbf24';
                    difficultyBadge.style.border = '1px solid rgba(245, 158, 11, 0.3)';
                } else {
                    difficultyBadge.style.background = 'rgba(16, 185, 129, 0.2)';
                    difficultyBadge.style.color = '#34d399';
                    difficultyBadge.style.border = '1px solid rgba(16, 185, 129, 0.3)';
                }
            }
            
            // Feasibility Level
            const feasibilityVal = document.getElementById('market-feasibility-val');
            if (feasibilityVal) {
                feasibilityVal.textContent = mi.feasibility;
                if (mi.feasibility === "Challenging") {
                    feasibilityVal.style.color = '#f87171';
                } else if (mi.feasibility === "Moderate") {
                    feasibilityVal.style.color = '#fbbf24';
                } else {
                    feasibilityVal.style.color = '#34d399';
                }
            }
            
            // Market summary text
            const summaryText = document.getElementById('market-summary-text');
            if (summaryText) summaryText.textContent = mi.summary;
        }

        // Render Recruiter Learning Banner
        const learningBanner = document.getElementById('recruiter-learning-banner');
        const learningText = document.getElementById('recruiter-learning-text');
        if (learningBanner && learningText && data.recruiter_learning) {
            const rl = data.recruiter_learning;
            const totalActions = rl.total_shortlisted + rl.total_rejected;
            if (totalActions > 0) {
                let text = `Recruiter Preference adaptation model active: Adapting scoring weights based on ${rl.total_shortlisted} shortlisted and ${rl.total_rejected} rejected profiles.`;
                if (rl.preferred_skills.length > 0) {
                    text += ` Preferred: ${rl.preferred_skills.map(ps => ps.skill).slice(0, 3).join(', ')}.`;
                }
                if (rl.penalized_skills.length > 0) {
                    text += ` Adjusted: ${rl.penalized_skills.map(ps => ps.skill).slice(0, 3).join(', ')}.`;
                }
                learningText.textContent = text;
                learningBanner.style.display = 'flex';
            } else {
                learningBanner.style.display = 'none';
            }
        }
        
        currentHiringBrief = data.hiring_brief;
        
        // Render candidate listing items
        emptyState.classList.remove('active');
        resultsState.classList.add('active');
        renderCandidatesList(rankedCandidates);
        
        // Render charts globally
        renderPoolSkillsChart(data.stats.top_skills, data.total_unfiltered);
        renderScoreHistogram(data.stats.histogram);
        
        // Render bias warnings
        const biasContainer = document.getElementById('bias-warnings-container');
        const biasList = document.getElementById('bias-warnings-list');
        if (biasContainer && biasList) {
            biasList.innerHTML = '';
            const warnings = data.bias_warnings || [];
            if (warnings.length > 0) {
                warnings.forEach(warning => {
                    const li = document.createElement('li');
                    li.textContent = warning;
                    biasList.appendChild(li);
                });
                biasContainer.style.display = 'block';
            } else {
                biasContainer.style.display = 'none';
            }
        }
        
        // Update pagination UI footer buttons
        updatePaginationUI();
    } catch (err) {
        showToast(err.message, "error");
    }
}

window.changePage = function(delta) {
    const targetPage = currentPage + delta;
    if (targetPage >= 1 && targetPage <= totalPages) {
        fetchJobCandidates(currentJobId, targetPage);
    }
};

function updatePaginationUI() {
    const controls = document.getElementById('pagination-controls');
    const info = document.getElementById('pagination-info');
    const prevBtn = document.getElementById('pagination-prev-btn');
    const nextBtn = document.getElementById('pagination-next-btn');
    
    if (!controls) return;
    
    if (!currentJobId || totalPages <= 1) {
        controls.style.display = 'none';
        return;
    }
    
    controls.style.display = 'flex';
    info.textContent = `Page ${currentPage} of ${totalPages}`;
    
    prevBtn.disabled = (currentPage === 1);
    prevBtn.style.opacity = (currentPage === 1) ? '0.5' : '1';
    prevBtn.style.cursor = (currentPage === 1) ? 'not-allowed' : 'pointer';
    
    nextBtn.disabled = (currentPage === totalPages);
    nextBtn.style.opacity = (currentPage === totalPages) ? '0.5' : '1';
    nextBtn.style.cursor = (currentPage === totalPages) ? 'not-allowed' : 'pointer';
}

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
    if (currentJobId) {
        fetchJobCandidates(currentJobId, 1);
        return;
    }
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

        let prefBadgeHtml = '';
        if (candidate.preference_adjustment && candidate.preference_adjustment !== 0) {
            const isPositive = candidate.preference_adjustment > 0;
            const sign = isPositive ? '+' : '';
            const badgeBg = isPositive ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.12)';
            const badgeColor = isPositive ? '#34d399' : '#f87171';
            const badgeBorder = isPositive ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.2)';
            prefBadgeHtml = `
                <span class="cand-meta-badge" style="background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeBorder}; font-size: 0.72rem; font-weight: 700; margin-left: 6px; padding: 2px 6px; border-radius: 4px; display: inline-flex; align-items: center; gap: 4px;">
                    <i class="fa-solid fa-graduation-cap"></i> ${sign}${candidate.preference_adjustment}
                </span>
            `;
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
                    <span class="candidate-subtitle" style="display: flex; align-items: center; flex-wrap: wrap; gap: 4px;">
                        ${statusBadgeHtml}
                        <span class="cand-meta-badge">${expLabel}</span>
                        <span class="cand-meta-badge">${degreeLabel}</span>
                        ${microBadgesHtml}
                        ${prefBadgeHtml}
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

/* Local Filter Input Listener with 300ms Search Debounce */
let searchDebounceTimeout = null;
searchCandidate.addEventListener('input', () => {
    if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);
    searchDebounceTimeout = setTimeout(() => {
        applyCandidatesFiltering();
    }, 300);
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

/* LocalStorage status rating setters & Database synchronization */
window.setCandidateStatus = function(status) {
    if (!currentDrawerCandidate) return;
    
    const filename = currentDrawerCandidate.filename;
    localStorage.setItem(`talentai_status_${filename}`, status);
    
    // Sync status to PostgreSQL database
    fetch('/api/evaluation/update', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${userToken}`
        },
        body: JSON.stringify({
            job_id: currentJobId,
            filename: filename,
            status: status
        })
    }).catch(err => console.error("Database update failed:", err));
    
    updateDrawerStatusUI(status);
    if (currentJobId) {
        fetchJobCandidates(currentJobId, currentPage);
    } else {
        applyCandidatesFiltering();
    }
    
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

let notesDebounceTimer = null;
drawerRecruiterNotes.addEventListener('input', (e) => {
    if (!currentDrawerCandidate) return;
    const filename = currentDrawerCandidate.filename;
    localStorage.setItem(`talentai_notes_${filename}`, e.target.value);
    
    // Sync notes to PostgreSQL database with a debounce
    clearTimeout(notesDebounceTimer);
    notesDebounceTimer = setTimeout(() => {
        fetch('/api/evaluation/update', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${userToken}`
            },
            body: JSON.stringify({
                job_id: currentJobId,
                filename: filename,
                comments: e.target.value
            })
        }).catch(err => console.error("Database notes update failed:", err));
    }, 500);
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
function renderScoreHistogram(histogramData) {
    if (!histogramData && rankedCandidates.length === 0) {
        scoreHistogramPanel.classList.remove('active');
        return;
    }

    scoreHistogramPanel.classList.add('active');
    scoreHistogram.innerHTML = '';

    // Calculate score bins
    let lowCount = 0;
    let midCount = 0;
    let highCount = 0;

    if (histogramData) {
        lowCount = histogramData.low || 0;
        midCount = histogramData.mid || 0;
        highCount = histogramData.high || 0;
    } else {
        rankedCandidates.forEach(c => {
            if (c.score < 40.0) lowCount++;
            else if (c.score < 70.0) midCount++;
            else Math.max(0, highCount++);
        });
    }

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

/* Export full recruiter database backup package (Phase 7 - PostgreSQL) */
window.exportDatabaseBackup = function() {
    // Fetch full backup representation from PostgreSQL database
    fetch('/api/backup/export', {
        headers: {
            'Authorization': `Bearer ${userToken}`
        }
    })
        .then(res => res.json())
        .then(data => {
            if (!data.success || !data.download_url) {
                throw new Error("Invalid export response from server.");
            }
            
            const link = document.createElement('a');
            link.href = data.download_url;
            link.download = `talentai_database_backup_${new Date().toISOString().slice(0,10)}.json`;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            showToast("JSON database backup package exported successfully!", "success");
        })
        .catch(err => {
            showToast("Failed to fetch database backup from server.", "error");
            console.error(err);
        });
};

/* Pool Skills Frequency Chart rendering */
function renderPoolSkillsChart(topSkillsData, totalCount) {
    if (!topSkillsData && rankedCandidates.length === 0) {
        poolSkillsChartPanel.classList.remove('active');
        return;
    }

    poolSkillsChartPanel.classList.add('active');
    poolSkillsChart.innerHTML = '';

    let sortedSkills = [];
    let denom = rankedCandidates.length;

    if (topSkillsData) {
        sortedSkills = topSkillsData;
        denom = totalCount || rankedCandidates.length;
    } else {
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
        sortedSkills = Object.keys(freq).map(skill => {
            return { name: skill, count: freq[skill] };
        }).sort((a, b) => b.count - a.count).slice(0, 5);
    }

    if (sortedSkills.length === 0) {
        poolSkillsChart.innerHTML = '<span class="text-dark" style="font-size: 0.8rem;">No skills identified in the candidate pool.</span>';
        return;
    }

    sortedSkills.forEach(item => {
        const percentage = denom > 0 ? (item.count / denom) * 100 : 0;
        
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
    
    // Reset on-demand full resume text viewer
    if (fullResumeTextContainer) fullResumeTextContainer.style.display = 'none';
    if (btnToggleResumeText) btnToggleResumeText.innerHTML = '<i class="fa-solid fa-eye"></i> Show Full Resume Text';
    if (detailFullResumeText) detailFullResumeText.textContent = '';
    
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
    
    // Check role restrictions for candidate evaluation
    const isManager = (currentUser && currentUser.role === 'Hiring Manager');
    btnStatusShortlisted.disabled = isManager;
    btnStatusReview.disabled = isManager;
    btnStatusRejected.disabled = isManager;
    if (isManager) {
        btnStatusShortlisted.style.opacity = '0.5';
        btnStatusShortlisted.style.cursor = 'not-allowed';
        btnStatusShortlisted.title = 'Hiring Managers are read + comment only';
        btnStatusReview.style.opacity = '0.5';
        btnStatusReview.style.cursor = 'not-allowed';
        btnStatusReview.title = 'Hiring Managers are read + comment only';
        btnStatusRejected.style.opacity = '0.5';
        btnStatusRejected.style.cursor = 'not-allowed';
        btnStatusRejected.title = 'Hiring Managers are read + comment only';
    } else {
        btnStatusShortlisted.style.opacity = '';
        btnStatusShortlisted.style.cursor = 'pointer';
        btnStatusShortlisted.title = '';
        btnStatusReview.style.opacity = '';
        btnStatusReview.style.cursor = 'pointer';
        btnStatusReview.title = '';
        btnStatusRejected.style.opacity = '';
        btnStatusRejected.style.cursor = 'pointer';
        btnStatusRejected.title = '';
    }
    
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

    // Populate Skill Gap Roadmap
    const explain = candidate.explainability || { reasons_high: [], reasons_low: [] };
    const roadmap = explain.skill_gap_roadmap || {
        summary: "No skill gaps calculated.",
        strengths: candidate.matched_skills,
        gaps: candidate.missing_skills,
        upskilling_recommendations: ["Ensure candidate baseline requirements are verified during interview."]
    };
    
    const summaryEl = document.getElementById('roadmap-summary');
    if (summaryEl) summaryEl.textContent = roadmap.summary;
    
    const strengthsEl = document.getElementById('roadmap-strengths');
    if (strengthsEl) {
        strengthsEl.innerHTML = '';
        if (roadmap.strengths && roadmap.strengths.length > 0) {
            roadmap.strengths.forEach(s => {
                const b = document.createElement('span');
                b.className = 'badge';
                b.style.background = 'rgba(74, 222, 128, 0.12)';
                b.style.color = '#4ade80';
                b.style.border = '1px solid rgba(74, 222, 128, 0.2)';
                b.textContent = s;
                strengthsEl.appendChild(b);
            });
        } else {
            strengthsEl.innerHTML = '<span style="color: #64748b; font-size: 0.75rem;">None listed</span>';
        }
    }
    
    const gapsEl = document.getElementById('roadmap-gaps');
    if (gapsEl) {
        gapsEl.innerHTML = '';
        if (roadmap.gaps && roadmap.gaps.length > 0) {
            roadmap.gaps.forEach(g => {
                const b = document.createElement('span');
                b.className = 'badge';
                b.style.background = 'rgba(248, 113, 113, 0.12)';
                b.style.color = '#f87171';
                b.style.border = '1px solid rgba(248, 113, 113, 0.2)';
                b.textContent = g;
                gapsEl.appendChild(b);
            });
        } else {
            gapsEl.innerHTML = '<span style="color: #64748b; font-size: 0.75rem;">None listed</span>';
        }
    }
    
    const recsEl = document.getElementById('roadmap-recommendations');
    if (recsEl) {
        recsEl.innerHTML = '';
        if (roadmap.upskilling_recommendations) {
            roadmap.upskilling_recommendations.forEach(r => {
                const li = document.createElement('li');
                li.textContent = r;
                recsEl.appendChild(li);
            });
        }
    }
    
    // Render Adjacent Roles Fit
    const adjacentRolesList = document.getElementById('detail-adjacent-roles-list');
    if (adjacentRolesList) {
        adjacentRolesList.innerHTML = '';
        const adjacentRoles = (explain.talent_graph && explain.talent_graph.adjacent_roles) || [];
        if (adjacentRoles.length === 0) {
            adjacentRolesList.innerHTML = '<span style="color: #64748b; font-size: 0.8rem; font-style: italic;">No adjacent matches found. Target profile remains highly focused.</span>';
        } else {
            adjacentRoles.forEach(roleFit => {
                const card = document.createElement('div');
                card.style.background = 'rgba(255, 255, 255, 0.03)';
                card.style.border = '1px solid rgba(255,255,255,0.06)';
                card.style.padding = '10px';
                card.style.borderRadius = '6px';
                card.style.display = 'flex';
                card.style.justifyContent = 'space-between';
                card.style.alignItems = 'center';
                
                const infoDiv = document.createElement('div');
                infoDiv.innerHTML = `
                    <div style="font-weight: 600; font-size: 0.85rem; color: #e2e8f0;">${roleFit.role}</div>
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Transferable: ${roleFit.transferable_skills.join(', ')}</div>
                `;
                
                const pctBadge = document.createElement('span');
                pctBadge.style.background = 'rgba(168, 85, 247, 0.15)';
                pctBadge.style.color = '#c084fc';
                pctBadge.style.border = '1px solid rgba(168, 85, 247, 0.3)';
                pctBadge.style.padding = '2px 8px';
                pctBadge.style.borderRadius = '4px';
                pctBadge.style.fontSize = '0.8rem';
                pctBadge.style.fontWeight = '600';
                pctBadge.textContent = `${roleFit.confidence}% Match`;
                
                card.appendChild(infoDiv);
                card.appendChild(pctBadge);
                adjacentRolesList.appendChild(card);
            });
        }
    }

    // Render Multi-Role Planning Mobility
    const mrTitle = document.getElementById('detail-multi-role-best-title');
    const mrPct = document.getElementById('detail-multi-role-best-pct');
    const mrBar = document.getElementById('detail-multi-role-best-bar');
    const mrSecondaryList = document.getElementById('detail-multi-role-secondary-list');
    
    if (candidate.multi_role_planning) {
        const mr = candidate.multi_role_planning;
        
        // Best fit
        if (mr.best_fit) {
            if (mrTitle) mrTitle.textContent = mr.best_fit.title;
            if (mrPct) mrPct.textContent = `${mr.best_fit.match_percentage.toFixed(0)}%`;
            if (mrBar) mrBar.style.width = `${mr.best_fit.match_percentage}%`;
        } else {
            if (mrTitle) mrTitle.textContent = 'None identified';
            if (mrPct) mrPct.textContent = '0%';
            if (mrBar) mrBar.style.width = '0%';
        }
        
        // Secondary openings
        if (mrSecondaryList) {
            mrSecondaryList.innerHTML = '';
            if (!mr.secondary_matches || mr.secondary_matches.length === 0) {
                mrSecondaryList.innerHTML = '<span style="color: #64748b; font-size: 0.8rem; font-style: italic;">No secondary role fits found.</span>';
            } else {
                mr.secondary_matches.forEach(match => {
                    const row = document.createElement('div');
                    row.style.display = 'flex';
                    row.style.alignItems = 'center';
                    row.style.justifyContent = 'space-between';
                    row.style.background = 'rgba(255,255,255,0.02)';
                    row.style.border = '1px solid rgba(255,255,255,0.05)';
                    row.style.padding = '8px 12px';
                    row.style.borderRadius = '6px';
                    row.style.fontSize = '0.8rem';
                    row.style.cursor = 'pointer';
                    row.style.transition = 'all 0.2s ease';
                    
                    row.onmouseover = () => { row.style.background = 'rgba(99, 102, 241, 0.1)'; };
                    row.onmouseout = () => { row.style.background = 'rgba(255,255,255,0.02)'; };
                    
                    row.onclick = () => {
                        closeDrawer();
                        currentJobId = match.job_id;
                        
                        // Select job visually in sidebar
                        const sidebarItems = document.querySelectorAll('.job-item');
                        sidebarItems.forEach(item => {
                            const jobIdAttr = item.getAttribute('data-job-id');
                            if (jobIdAttr == match.job_id.toString()) {
                                item.classList.add('active');
                            } else {
                                item.classList.remove('active');
                            }
                        });
                        
                        fetchJobCandidates(currentJobId, 1);
                        showToast(`Switched workspace to job: ${match.title}`, "info");
                    };
                    
                    row.innerHTML = `
                        <span style="font-weight: 600; color: #cbd5e1; display: flex; align-items: center; gap: 6px;">
                            <i class="fa-solid fa-arrow-right-arrow-left" style="font-size: 0.7rem; color: #818cf8;"></i>
                            <span>${match.title}</span>
                        </span>
                        <span style="color: #818cf8; font-weight: 700;">${match.match_percentage.toFixed(0)}%</span>
                    `;
                    mrSecondaryList.appendChild(row);
                });
            }
        }
    }

    // Render Similar Candidates
    const similarCandidatesList = document.getElementById('detail-similar-candidates-list');
    if (similarCandidatesList) {
        similarCandidatesList.innerHTML = '';
        const similarCandidates = candidate.similar_candidates || [];
        if (similarCandidates.length === 0) {
            similarCandidatesList.innerHTML = '<span style="color: #64748b; font-size: 0.8rem; font-style: italic;">No similar candidates identified in the current pool.</span>';
        } else {
            similarCandidates.forEach(simCand => {
                const item = document.createElement('div');
                item.style.background = 'rgba(255, 255, 255, 0.03)';
                item.style.border = '1px solid rgba(255,255,255,0.06)';
                item.style.padding = '10px';
                item.style.borderRadius = '6px';
                item.style.display = 'flex';
                item.style.justifyContent = 'space-between';
                item.style.alignItems = 'center';
                item.style.cursor = 'pointer';
                item.style.transition = 'all 0.2s ease';
                
                item.onmouseover = () => { item.style.background = 'rgba(255, 255, 255, 0.08)'; };
                item.onmouseout = () => { item.style.background = 'rgba(255, 255, 255, 0.03)'; };
                
                // Click to view similar candidate details immediately
                item.onclick = () => {
                    const targetCand = rankedCandidates.find(rc => rc.id === simCand.id);
                    if (targetCand) {
                        openDrawer(targetCand);
                    }
                };
                
                const nameDiv = document.createElement('div');
                nameDiv.innerHTML = `
                    <div style="font-weight: 600; font-size: 0.85rem; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                        <i class="fa-solid fa-user-tag" style="font-size: 0.75rem;"></i>
                        <span>${simCand.label}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Shared Skills: ${simCand.shared_skills.slice(0, 3).join(', ')}${simCand.shared_skills.length > 3 ? '...' : ''}</div>
                `;
                
                const simBadge = document.createElement('span');
                simBadge.style.background = 'rgba(245, 158, 11, 0.15)';
                simBadge.style.color = '#fbbf24';
                simBadge.style.border = '1px solid rgba(245, 158, 11, 0.3)';
                simBadge.style.padding = '2px 8px';
                simBadge.style.borderRadius = '4px';
                simBadge.style.fontSize = '0.8rem';
                simBadge.style.fontWeight = '600';
                simBadge.textContent = `${simCand.similarity}% Similar`;
                
                item.appendChild(nameDiv);
                item.appendChild(simBadge);
                similarCandidatesList.appendChild(item);
            });
        }
    }
    
    // Initialize Interview Kit Tab
    switchInterviewRound('screening');

    // Animate SVG category donut chart coverage
    animateSkillDonut(candidate);

    // Detailed scores progress bars
    detailCosineScore.textContent = `${candidate.cosine_score}%`;
    detailCosineBar.style.width = `${candidate.cosine_score}%`;
    
    detailSkillsScore.textContent = `${candidate.skills_score.toFixed(1)}%`;
    detailSkillsBar.style.width = `${candidate.skills_score}%`;

    detailExperienceScore.textContent = `${candidate.experience_score.toFixed(1)}%`;
    detailExperienceBar.style.width = `${candidate.experience_score}%`;

    // Populate explainability and version
    const detailModelVersion = document.getElementById('detail-model-version');
    const explainHighList = document.getElementById('explain-high-list');
    const explainLowList = document.getElementById('explain-low-list');
    const explainHighBlock = document.getElementById('explain-high-block');
    const explainLowBlock = document.getElementById('explain-low-block');
    
    if (detailModelVersion) {
        detailModelVersion.textContent = candidate.model_version || 'v2.1.0';
    }
    
    
    const breakdown = explain.breakdown || { domain_fit: 80, seniority_fit: 90, soft_signals: 75, team_fit: 85 };
    const teamFitDetails = explain.team_fit_details || { mindset_alignment: "N/A", focus_alignment: "N/A", expectation_alignment: "N/A" };
    const whyCandidate = explain.why_candidate || "No dynamic evaluation summary generated for this candidate.";
    
    // Domain Fit
    const domVal = breakdown.domain_fit || 0;
    const domEl = document.getElementById('detail-breakdown-domain');
    const domBar = document.getElementById('detail-breakdown-domain-bar');
    if (domEl) domEl.textContent = `${domVal.toFixed(0)}%`;
    if (domBar) domBar.style.width = `${domVal}%`;
    
    // Seniority Fit
    const senVal = breakdown.seniority_fit || 0;
    const senEl = document.getElementById('detail-breakdown-seniority');
    const senBar = document.getElementById('detail-breakdown-seniority-bar');
    if (senEl) senEl.textContent = `${senVal.toFixed(0)}%`;
    if (senBar) senBar.style.width = `${senVal}%`;
    
    // Culture Fit
    const cultVal = breakdown.soft_signals || breakdown.culture_fit || 0;
    const cultEl = document.getElementById('detail-breakdown-culture');
    const cultBar = document.getElementById('detail-breakdown-culture-bar');
    if (cultEl) cultEl.textContent = `${cultVal.toFixed(0)}%`;
    if (cultBar) cultBar.style.width = `${cultVal}%`;
    
    // Team Fit
    const teamVal = breakdown.team_fit || 0;
    const teamEl = document.getElementById('detail-breakdown-team');
    const teamBar = document.getElementById('detail-breakdown-team-bar');
    if (teamEl) teamEl.textContent = `${teamVal.toFixed(0)}%`;
    if (teamBar) teamBar.style.width = `${teamVal}%`;
    
    // Why Candidate Text
    const whyEl = document.getElementById('detail-why-candidate-text');
    if (whyEl) whyEl.textContent = whyCandidate;
    
    // Team Fit Alignment Dimensions Badges
    const mindsetBadge = document.getElementById('detail-alignment-mindset');
    const focusBadge = document.getElementById('detail-alignment-focus');
    const expectationBadge = document.getElementById('detail-alignment-expectation');
    
    if (mindsetBadge) {
        mindsetBadge.textContent = teamFitDetails.mindset_alignment || "N/A";
        const isMatch = (teamFitDetails.mindset_alignment || "").includes("Match");
        mindsetBadge.style.background = isMatch ? "rgba(16, 185, 129, 0.2)" : "rgba(239, 68, 68, 0.2)";
        mindsetBadge.style.color = isMatch ? "#34d399" : "#f87171";
        mindsetBadge.style.border = isMatch ? "1px solid rgba(16, 185, 129, 0.3)" : "1px solid rgba(239, 68, 68, 0.3)";
    }
    if (focusBadge) {
        focusBadge.textContent = teamFitDetails.focus_alignment || "N/A";
        const isMatch = (teamFitDetails.focus_alignment || "").includes("Match");
        const isPartial = (teamFitDetails.focus_alignment || "").includes("Partial");
        if (isMatch) {
            focusBadge.style.background = "rgba(16, 185, 129, 0.2)";
            focusBadge.style.color = "#34d399";
            focusBadge.style.border = "1px solid rgba(16, 185, 129, 0.3)";
        } else if (isPartial) {
            focusBadge.style.background = "rgba(245, 158, 11, 0.2)";
            focusBadge.style.color = "#fbbf24";
            focusBadge.style.border = "1px solid rgba(245, 158, 11, 0.3)";
        } else {
            focusBadge.style.background = "rgba(239, 68, 68, 0.2)";
            focusBadge.style.color = "#f87171";
            focusBadge.style.border = "1px solid rgba(239, 68, 68, 0.3)";
        }
    }
    if (expectationBadge) {
        expectationBadge.textContent = teamFitDetails.expectation_alignment || "N/A";
        const isMatch = (teamFitDetails.expectation_alignment || "").includes("Match");
        expectationBadge.style.background = isMatch ? "rgba(16, 185, 129, 0.2)" : "rgba(239, 68, 68, 0.2)";
        expectationBadge.style.color = isMatch ? "#34d399" : "#f87171";
        expectationBadge.style.border = isMatch ? "1px solid rgba(16, 185, 129, 0.3)" : "1px solid rgba(239, 68, 68, 0.3)";
    }
    
    if (explainHighList) {
        explainHighList.innerHTML = '';
        if (explain.reasons_high && explain.reasons_high.length > 0) {
            if (explainHighBlock) explainHighBlock.style.display = 'block';
            explain.reasons_high.forEach(reason => {
                const li = document.createElement('li');
                li.textContent = reason;
                explainHighList.appendChild(li);
            });
        } else {
            if (explainHighBlock) explainHighBlock.style.display = 'none';
        }
    }
    
    if (explainLowList) {
        explainLowList.innerHTML = '';
        if (explain.reasons_low && explain.reasons_low.length > 0) {
            if (explainLowBlock) explainLowBlock.style.display = 'block';
            explain.reasons_low.forEach(reason => {
                const li = document.createElement('li');
                li.textContent = reason;
                explainLowList.appendChild(li);
            });
        } else {
            if (explainLowBlock) explainLowBlock.style.display = 'none';
        }
    }

    // Experience Card metrics
    detailReqExp.textContent = jdExperienceRequired > 0 ? `${jdExperienceRequired} Years` : '0 Years (None)';
    detailCandExp.textContent = `${candidate.candidate_exp} Years`;
    
    // Confidence warnings (Phase 4)
    const expConfidenceFlag = document.getElementById('detail-exp-confidence-flag');
    if (expConfidenceFlag) {
        if (candidate.experience_confidence !== undefined && candidate.experience_confidence < 0.7) {
            expConfidenceFlag.style.display = 'inline-block';
            expConfidenceFlag.title = `Confidence: ${Math.round(candidate.experience_confidence * 100)}% (low confidence extraction)`;
        } else {
            expConfidenceFlag.style.display = 'none';
        }
    }
    
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
    
    // Confidence warnings (Phase 4)
    const degreeConfidenceFlag = document.getElementById('detail-degree-confidence-flag');
    if (degreeConfidenceFlag) {
        if (candidate.degrees_confidence !== undefined && candidate.degrees_confidence < 0.7) {
            degreeConfidenceFlag.style.display = 'inline-block';
            degreeConfidenceFlag.title = `Confidence: ${Math.round(candidate.degrees_confidence * 100)}% (low confidence extraction)`;
        } else {
            degreeConfidenceFlag.style.display = 'none';
        }
    }

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

const biasBlindToggleBtn = document.getElementById('bias-blind-toggle');
if (biasBlindToggleBtn) {
    biasBlindToggleBtn.addEventListener('click', () => {
        biasBlindMode = !biasBlindMode;
        if (biasBlindMode) {
            biasBlindToggleBtn.innerHTML = '<i class="fa-solid fa-eye-slash"></i> <span>Bias-Blind Mode: On</span>';
            biasBlindToggleBtn.style.background = 'rgba(99, 102, 241, 0.2)';
            biasBlindToggleBtn.style.color = '#818cf8';
            biasBlindToggleBtn.style.border = '1px solid rgba(99, 102, 241, 0.4)';
        } else {
            biasBlindToggleBtn.innerHTML = '<i class="fa-solid fa-eye"></i> <span>Bias-Blind Mode: Off</span>';
            biasBlindToggleBtn.style.background = 'rgba(255,255,255,0.05)';
            biasBlindToggleBtn.style.color = '#94a3b8';
            biasBlindToggleBtn.style.border = '1px solid rgba(255,255,255,0.1)';
        }
        if (currentJobId) {
            fetchJobCandidates(currentJobId, currentPage);
        }
    });
}

function closeDrawer() {
    detailDrawer.classList.remove('open');
    currentDrawerCandidate = null;
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && detailDrawer.classList.contains('open')) {
        closeDrawer();
    }
});

function showHiringBriefModal() {
    if (!currentHiringBrief) {
        showToast("Hiring brief data is not loaded yet.", "error");
        return;
    }
    const modal = document.getElementById('hiring-brief-modal');
    if (modal) {
        document.getElementById('brief-role-title').textContent = `Hiring Brief: ${currentHiringBrief.role_title}`;
        
        const strengthsList = document.getElementById('brief-strengths-list');
        strengthsList.innerHTML = '';
        currentHiringBrief.strengths.forEach(s => {
            const li = document.createElement('li');
            li.textContent = s;
            strengthsList.appendChild(li);
        });
        
        const risksList = document.getElementById('brief-risks-list');
        risksList.innerHTML = '';
        currentHiringBrief.risks.forEach(r => {
            const li = document.createElement('li');
            li.textContent = r;
            risksList.appendChild(li);
        });
        
        const focusList = document.getElementById('brief-focus-list');
        focusList.innerHTML = '';
        currentHiringBrief.interview_focus.forEach(f => {
            const li = document.createElement('li');
            li.textContent = f;
            focusList.appendChild(li);
        });
        
        document.getElementById('brief-recommendation-text').textContent = currentHiringBrief.recommendation;
        
        modal.style.display = 'flex';
    }
}

function closeHiringBriefModal() {
    const modal = document.getElementById('hiring-brief-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

window.closeHiringBriefModal = closeHiringBriefModal;

const hiringBriefBtn = document.getElementById('hiring-brief-btn');
if (hiringBriefBtn) {
    hiringBriefBtn.addEventListener('click', showHiringBriefModal);
}

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

/* --- Phase 2 Authentication Client-Side Orchestration --- */

const authOverlay = document.getElementById('auth-overlay');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const tabLogin = document.getElementById('tab-login');
const tabRegister = document.getElementById('tab-register');
const userProfileWidget = document.getElementById('user-profile-widget');
const userAvatarInitials = document.getElementById('user-avatar-initials');
const userNameDisplay = document.getElementById('user-name-display');
const userRoleBadge = document.getElementById('user-role-badge');

window.switchAuthTab = function(tab) {
    if (tab === 'login') {
        tabLogin.classList.add('active');
        tabRegister.classList.remove('active');
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
    } else {
        tabLogin.classList.remove('active');
        tabRegister.classList.add('active');
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
    }
};

window.handleLoginSubmit = function(event) {
    event.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const errorMsgDiv = document.getElementById('login-error-msg');
    
    if (errorMsgDiv) {
        errorMsgDiv.style.display = 'none';
    }
    
    const bodyData = new URLSearchParams();
    bodyData.append('username', email);
    bodyData.append('password', password);
    
    fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: bodyData
    })
    .then(async res => {
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || "Authentication failed.");
        }
        return data;
    })
    .then(data => {
        userToken = data.access_token;
        localStorage.setItem('talentai_token', userToken);
        showToast("Welcome back to TalentAI!", "success");
        checkUserSession();
    })
    .catch(err => {
        showToast(err.message, "error");
        if (errorMsgDiv) {
            errorMsgDiv.style.display = 'flex';
            const errorTextSpan = errorMsgDiv.querySelector('.error-text');
            if (errorTextSpan) {
                errorTextSpan.textContent = err.message;
            }
        }
    });
};

window.handleRegisterSubmit = function(event) {
    event.preventDefault();
    const name = document.getElementById('register-name').value;
    const email = document.getElementById('register-email').value;
    const org = document.getElementById('register-org').value;
    const role = document.getElementById('register-role').value;
    const password = document.getElementById('register-password').value;
    const errorMsgDiv = document.getElementById('register-error-msg');
    
    if (errorMsgDiv) {
        errorMsgDiv.style.display = 'none';
    }
    
    fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email: email,
            full_name: name,
            password: password,
            role: role,
            organization_name: org
        })
    })
    .then(async res => {
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || "Registration failed.");
        }
        return data;
    })
    .then(data => {
        userToken = data.access_token;
        localStorage.setItem('talentai_token', userToken);
        showToast("Account created successfully!", "success");
        checkUserSession();
    })
    .catch(err => {
        showToast(err.message, "error");
        if (errorMsgDiv) {
            errorMsgDiv.style.display = 'flex';
            const errorTextSpan = errorMsgDiv.querySelector('.error-text');
            if (errorTextSpan) {
                errorTextSpan.textContent = err.message;
            }
        }
    });
};

window.handleLogout = function() {
    userToken = null;
    currentUser = null;
    localStorage.removeItem('talentai_token');
    
    // Reset view states
    rankedCandidates = [];
    currentJobId = null;
    
    // Clear display container
    const candidatesContainer = document.getElementById('candidates-container');
    if (candidatesContainer) {
        candidatesContainer.innerHTML = '';
    }
    
    const emptyState = document.getElementById('empty-state');
    if (emptyState) {
        emptyState.classList.add('active');
    }
    
    const landingPage = document.getElementById('landing-page');
    const appContainer = document.getElementById('app-container');
    if (landingPage) landingPage.style.display = 'block';
    if (appContainer) appContainer.style.display = 'none';
    
    userProfileWidget.style.display = 'none';
    authOverlay.classList.remove('active');
    
    // Reset login fields
    document.getElementById('login-email').value = '';
    document.getElementById('login-password').value = '';
    
    showToast("Logged out successfully.", "success");
};

async function loadLatestJob() {
    try {
        const response = await fetch('/api/jobs/latest', {
            headers: { 'Authorization': `Bearer ${userToken}` }
        });
        if (response.ok) {
            const job = await response.json();
            currentJobId = job.id;
            if (jobDescriptionInput) {
                jobDescriptionInput.value = job.description || "";
            }
            await fetchJobCandidates(currentJobId, 1);
        }
    } catch (err) {
        console.warn("Failed to load latest job:", err);
    }
}

window.togglePasswordVisibility = function(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (input && icon) {
        if (input.type === "password") {
            input.type = "text";
            icon.classList.remove("fa-eye");
            icon.classList.add("fa-eye-slash");
        } else {
            input.type = "password";
            icon.classList.remove("fa-eye-slash");
            icon.classList.add("fa-eye");
        }
    }
};

window.openAuthModal = function() {
    authOverlay.classList.add('active');
};

window.closeAuthModal = function() {
    authOverlay.classList.remove('active');
};

function checkUserSession() {
    const landingPage = document.getElementById('landing-page');
    const appContainer = document.getElementById('app-container');
    
    if (!userToken) {
        if (landingPage) landingPage.style.display = 'block';
        if (appContainer) appContainer.style.display = 'none';
        authOverlay.classList.remove('active');
        userProfileWidget.style.display = 'none';
        return;
    }
    
    fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${userToken}` }
    })
    .then(async res => {
        if (!res.ok) {
            throw new Error("Session expired.");
        }
        return res.json();
    })
    .then(user => {
        currentUser = user;
        
        // Hide landing page, show app dashboard
        if (landingPage) landingPage.style.display = 'none';
        if (appContainer) appContainer.style.display = 'block';
        
        // Show profile widget
        userNameDisplay.textContent = user.full_name;
        userRoleBadge.textContent = user.role;
        
        // Initials avatar
        const initials = user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        userAvatarInitials.textContent = initials;
        
        userProfileWidget.style.display = 'flex';
        authOverlay.classList.remove('active');
        
        applyRolePermissions();
        
        // Load latest analyzed job context if none loaded
        if (!currentJobId) {
            loadLatestJob();
        }
    })
    .catch(err => {
        console.error("Session load failed:", err);
        handleLogout();
    });
}

function applyRolePermissions() {
    const isManager = (currentUser && currentUser.role === 'Hiring Manager');
    const submitBtn = document.getElementById('submit-btn');
    const dropzone = document.getElementById('dropzone');
    const dbDropzone = document.getElementById('db-dropzone');
    
    if (isManager) {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.5';
            submitBtn.style.cursor = 'not-allowed';
            submitBtn.title = 'Hiring Managers cannot rank candidates';
        }
        if (dropzone) {
            dropzone.style.pointerEvents = 'none';
            dropzone.style.opacity = '0.5';
        }
        if (dbDropzone) {
            dbDropzone.style.pointerEvents = 'none';
            dbDropzone.style.opacity = '0.5';
        }
    } else {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.style.opacity = '';
            submitBtn.style.cursor = 'pointer';
            submitBtn.title = '';
        }
        if (dropzone) {
            dropzone.style.pointerEvents = 'all';
            dropzone.style.opacity = '1';
        }
        if (dbDropzone) {
            dbDropzone.style.pointerEvents = 'all';
            dbDropzone.style.opacity = '1';
        }
    }
}

// Check user status upon script load
checkUserSession();

// Local cache for candidate resume texts to prevent redundant API queries
const candidateResumeTextCache = {};

if (btnToggleResumeText) {
    btnToggleResumeText.addEventListener('click', () => {
        if (!currentDrawerCandidate) return;
        
        const isCollapsed = fullResumeTextContainer.style.display === 'none';
        
        if (isCollapsed) {
            // Expand the container
            fullResumeTextContainer.style.display = 'block';
            btnToggleResumeText.innerHTML = '<i class="fa-solid fa-eye-slash"></i> Hide Resume Text';
            
            const candId = currentDrawerCandidate.id;
            
            const cacheKey = candId + "_" + biasBlindMode;
            // Check cache first
            if (candidateResumeTextCache[cacheKey]) {
                detailFullResumeText.textContent = candidateResumeTextCache[cacheKey];
            } else {
                detailFullResumeText.textContent = 'Loading full parsed resume text...';
                
                fetch(`/api/candidates/${candId}/resume-text?bias_blind=${biasBlindMode}`, {
                    headers: {
                        'Authorization': `Bearer ${userToken}`
                    }
                })
                .then(res => {
                    if (!res.ok) throw new Error("Could not retrieve resume text.");
                    return res.json();
                })
                .then(data => {
                    const text = data.raw_text || "No text content found in this resume.";
                    candidateResumeTextCache[cacheKey] = text;
                    // Make sure the candidate hasn't changed while downloading
                    if (currentDrawerCandidate && currentDrawerCandidate.id === candId) {
                        detailFullResumeText.textContent = text;
                    }
                })
                .catch(err => {
                    console.error("Resume text load failed:", err);
                    detailFullResumeText.textContent = "Error: Failed to load full parsed resume text.";
                });
            }
        } else {
            // Collapse the container
            fullResumeTextContainer.style.display = 'none';
            btnToggleResumeText.innerHTML = '<i class="fa-solid fa-eye"></i> Show Full Resume Text';
        }
    });
}

window.switchInterviewRound = function(roundName) {
    if (!currentDrawerCandidate) return;
    
    // Update active tab button style
    const tabIds = {
        'screening': 'btn-tab-screening',
        'technical': 'btn-tab-technical',
        'system_design': 'btn-tab-system_design',
        'behavioral': 'btn-tab-behavioral'
    };
    
    Object.keys(tabIds).forEach(r => {
        const btn = document.getElementById(tabIds[r]);
        if (btn) {
            if (r === roundName) {
                btn.style.background = 'var(--primary-color)';
                btn.style.color = 'white';
            } else {
                btn.style.background = 'transparent';
                btn.style.color = '#94a3b8';
            }
        }
    });
    
    // Render round-specific questions
    const explain = currentDrawerCandidate.explainability || {};
    const kit = explain.interview_kit || {};
    const questions = kit[roundName] || [
        "What key learnings have you obtained from your most recent technical project?",
        "How do you approach learning a new tool or framework rapidly under tight client constraints?"
    ];
    
    const qList = document.getElementById('interview-kit-questions-list');
    if (qList) {
        qList.innerHTML = '';
        questions.forEach(q => {
            const li = document.createElement('li');
            li.style.display = 'flex';
            li.style.justifyContent = 'space-between';
            li.style.alignItems = 'flex-start';
            li.style.gap = '15px';
            
            const txt = document.createElement('span');
            txt.textContent = q;
            txt.style.flex = '1';
            
            const copyBtn = document.createElement('button');
            copyBtn.className = 'btn';
            copyBtn.style.padding = '3px 8px';
            copyBtn.style.fontSize = '0.7rem';
            copyBtn.style.background = 'rgba(255,255,255,0.06)';
            copyBtn.style.border = '1px solid rgba(255,255,255,0.1)';
            copyBtn.style.color = '#cbd5e1';
            copyBtn.style.cursor = 'pointer';
            copyBtn.style.borderRadius = '4px';
            copyBtn.style.minWidth = '75px';
            copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
            
            copyBtn.onclick = () => {
                navigator.clipboard.writeText(q).then(() => {
                    copyBtn.innerHTML = '<i class="fa-solid fa-check" style="color: #4ade80;"></i> Copied';
                    showToast("Question copied to clipboard!", "success");
                    setTimeout(() => {
                        copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
                    }, 2000);
                }).catch(() => {
                    showToast("Failed to copy question.", "error");
                });
            };
            
            li.appendChild(txt);
            li.appendChild(copyBtn);
            qList.appendChild(li);
        });
    }
};
