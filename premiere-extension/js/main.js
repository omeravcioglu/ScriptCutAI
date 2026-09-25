/**
 * ScriptCutAI - Premiere Pro Extension
 * Main panel logic
 */

// API Configuration
const API_BASE_URL = 'http://127.0.0.1:8000';

// State
let csInterface = null;
let analysisResult = null;
let isAnalyzing = false;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);

function init() {
    // Initialize CSInterface
    csInterface = new CSInterface();
    
    // Set up event listeners
    document.getElementById('btnSelectVideo').addEventListener('click', getVideoFromTimeline);
    document.getElementById('btnAnalyze').addEventListener('click', analyzeVideo);
    document.getElementById('btnApplyCuts').addEventListener('click', applyCutsToTimeline);
    document.getElementById('btnPreview').addEventListener('click', previewCuts);
    
    // Check server connection
    checkServerConnection();
    
    // Log startup
    log('ScriptCutAI panel loaded', 'info');
    log('Make sure the Python server is running on port 8000', 'info');
}

/**
 * Check if the Python backend server is running
 */
async function checkServerConnection() {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');
    
    try {
        const response = await fetch(`${API_BASE_URL}/health`, {
            method: 'GET',
            mode: 'cors'
        });
        const data = await response.json();
        
        if (data.status === 'healthy') {
            statusDot.classList.add('connected');
            statusText.textContent = 'Server connected';
            log('Connected to ScriptCutAI server', 'success');
        }
    } catch (error) {
        statusDot.classList.remove('connected');
        statusText.textContent = 'Server offline';
        log('Server not running!', 'error');
        log('Run: cd backend && .\\venv\\Scripts\\Activate.ps1 && uvicorn app.main:app --host 127.0.0.1 --port 8000', 'info');
    }
}

/**
 * Get the video file path from the active timeline
 */
function getVideoFromTimeline() {
    log('Getting video from timeline...');
    
    if (!csInterface) {
        log('CSInterface not available', 'error');
        return;
    }
    
    // Call JSX to get the active sequence's video clip
    csInterface.evalScript('getActiveClipPath()', function(result) {
        log('JSX returned: ' + result);
        
        if (result && result !== 'null' && result !== 'undefined' && !result.startsWith('Error') && result !== 'EvalScript error.') {
            // Clean up the path (remove quotes if present)
            let path = result.replace(/^["']|["']$/g, '');
            
            document.getElementById('videoPath').textContent = path;
            document.getElementById('videoPath').classList.add('has-file');
            log('Video selected: ' + path, 'success');
        } else {
            log('Could not get video. Make sure:', 'error');
            log('1. A sequence is open', 'info');
            log('2. The sequence has a video clip', 'info');
            
            // For testing, allow manual path entry
            const testPath = prompt('Enter video file path manually (or cancel):');
            if (testPath) {
                document.getElementById('videoPath').textContent = testPath;
                document.getElementById('videoPath').classList.add('has-file');
                log('Manual path set: ' + testPath, 'success');
            }
        }
    });
}

/**
 * Analyze the video against the script
 */
async function analyzeVideo() {
    if (isAnalyzing) {
        log('Analysis already in progress...', 'info');
        return;
    }
    
    const videoPath = document.getElementById('videoPath').textContent;
    const scriptText = document.getElementById('scriptText').value.trim();
    const whisperModel = document.getElementById('whisperModel').value;
    
    // Validation
    if (videoPath === 'No video selected' || !videoPath) {
        log('Please select a video first', 'error');
        return;
    }
    
    if (!scriptText) {
        log('Please enter the script text', 'error');
        return;
    }
    
    isAnalyzing = true;
    showProgress(true);
    updateProgress(10, 'Sending to server...');
    document.getElementById('btnAnalyze').disabled = true;
    
    try {
        log('Starting analysis with ' + whisperModel + ' model...');
        log('This may take several minutes for long videos...', 'info');
        updateProgress(20, 'Transcribing audio (please wait)...');
        
        const response = await fetch(`${API_BASE_URL}/api/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                video_path: videoPath,
                script_text: scriptText,
                whisper_model: whisperModel
            })
        });
        
        if (!response.ok) {
            throw new Error('Server returned ' + response.status);
        }
        
        const data = await response.json();
        
        if (data.success && data.result) {
            analysisResult = data.result;
            updateProgress(100, 'Analysis complete!');
            showResults(data.result);
            log('Analysis complete!', 'success');
            log('Found ' + data.result.edit_segments.length + ' segments', 'success');
            log('Keep: ' + formatTime(data.result.kept_duration) + ' | Remove: ' + formatTime(data.result.removed_duration), 'info');
        } else {
            throw new Error(data.error || 'Unknown error from server');
        }
        
    } catch (error) {
        log('Analysis failed: ' + error.message, 'error');
        updateProgress(0, 'Failed');
    } finally {
        isAnalyzing = false;
        document.getElementById('btnAnalyze').disabled = false;
        setTimeout(() => showProgress(false), 3000);
    }
}

/**
 * Show/hide progress section
 */
function showProgress(show) {
    document.getElementById('progressSection').style.display = show ? 'block' : 'none';
}

/**
 * Update progress bar
 */
function updateProgress(percent, text) {
    document.getElementById('progressBar').style.width = percent + '%';
    document.getElementById('progressText').textContent = text;
}

/**
 * Display analysis results
 */
function showResults(result) {
    document.getElementById('resultsSection').style.display = 'block';
    
    // Format durations
    document.getElementById('statKeep').textContent = formatTime(result.kept_duration);
    document.getElementById('statRemove').textContent = formatTime(result.removed_duration);
    
    // Calculate reduction percentage
    const total = result.kept_duration + result.removed_duration;
    const reduction = Math.round((result.removed_duration / total) * 100);
    document.getElementById('statReduction').textContent = reduction + '%';
}

/**
 * Format seconds to MM:SS
 */
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins + ':' + secs.toString().padStart(2, '0');
}

/**
 * Preview cuts - show in log what will be removed
 */
function previewCuts() {
    if (!analysisResult) {
        log('No analysis results. Run analysis first.', 'error');
        return;
    }
    
    log('========== CUT PREVIEW ==========', 'info');
    log('Segments to process:', 'info');
    
    let keepCount = 0;
    let removeCount = 0;
    
    analysisResult.edit_segments.forEach((seg, i) => {
        const start = formatTime(seg.start);
        const end = formatTime(seg.end);
        const duration = formatTime(seg.end - seg.start);
        const action = seg.action.toUpperCase();
        
        if (seg.action === 'keep') {
            log((i + 1) + '. [' + start + ' - ' + end + '] (' + duration + ') KEEP', 'success');
            keepCount++;
        } else {
            log((i + 1) + '. [' + start + ' - ' + end + '] (' + duration + ') REMOVE', 'error');
            removeCount++;
        }
    });
    
    log('=================================', 'info');
    log('Total: ' + keepCount + ' keep, ' + removeCount + ' remove', 'info');
    log('Click "Apply Cuts" to execute', 'info');
}

/**
 * Apply cuts to the Premiere Pro timeline
 */
function applyCutsToTimeline() {
    if (!analysisResult) {
        log('No analysis results. Run analysis first.', 'error');
        return;
    }
    
    if (!csInterface) {
        log('Not connected to Premiere Pro', 'error');
        return;
    }
    
    log('Applying cuts to timeline...', 'info');
    log('This will modify your sequence!', 'info');
    
    // Convert segments to JSON for JSX
    const segmentsJson = JSON.stringify(analysisResult.edit_segments);
    const escapedJson = escapeForJsx(segmentsJson);
    
    // First try the razor/extract method
    csInterface.evalScript("applyCutsWithRazor('" + escapedJson + "')", function(result) {
        log('JSX result: ' + result);
        
        if (result && result.indexOf('success') === 0) {
            log('Cuts applied successfully!', 'success');
            log(result, 'success');
        } else if (result && result.indexOf('Error') === 0) {
            log(result, 'error');
            log('Trying marker method instead...', 'info');
            
            // Fallback to markers
            csInterface.evalScript("addCutMarkers('" + escapedJson + "')", function(markerResult) {
                if (markerResult && markerResult.indexOf('success') === 0) {
                    log('Added markers at cut points', 'success');
                    log('Use keyboard shortcut ";" (semicolon) to extract marked regions', 'info');
                } else {
                    log('Marker method also failed: ' + markerResult, 'error');
                }
            });
        } else {
            log('Unexpected result: ' + result, 'error');
        }
    });
}

/**
 * Escape string for JSX - handle special characters
 */
function escapeForJsx(str) {
    return str
        .replace(/\\/g, '\\\\')
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '\\r');
}

/**
 * Add log entry to the log panel
 */
function log(message, type = '') {
    const logContent = document.getElementById('logContent');
    const entry = document.createElement('div');
    entry.className = 'log-entry' + (type ? ' ' + type : '');
    
    const time = new Date().toLocaleTimeString();
    entry.textContent = '[' + time + '] ' + message;
    
    logContent.appendChild(entry);
    logContent.scrollTop = logContent.scrollHeight;
    
    // Also log to console for debugging
    console.log('[ScriptCutAI]', message);
}
