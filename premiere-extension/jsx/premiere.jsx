/**
 * ScriptCutAI - Premiere Pro JSX Script
 * Controls the Premiere Pro timeline to apply cuts
 */

// Enable QE DOM for advanced editing operations
try {
    app.enableQE();
} catch(e) {
    // QE might not be available in all versions
}

/**
 * Get the file path of the first video clip in the active sequence
 */
function getActiveClipPath() {
    try {
        var project = app.project;
        
        if (!project) {
            return null;
        }
        
        var sequence = project.activeSequence;
        
        if (!sequence) {
            return null;
        }
        
        // Get video tracks
        var videoTracks = sequence.videoTracks;
        
        if (videoTracks.numTracks === 0) {
            return null;
        }
        
        // Find the first clip
        for (var t = 0; t < videoTracks.numTracks; t++) {
            var track = videoTracks[t];
            var clips = track.clips;
            
            if (clips.numItems > 0) {
                var clip = clips[0];
                var projectItem = clip.projectItem;
                
                if (projectItem) {
                    var mediaPath = projectItem.getMediaPath();
                    return mediaPath;
                }
            }
        }
        
        return null;
    } catch(e) {
        return "Error: " + e.toString();
    }
}

/**
 * Apply cuts to the timeline based on edit segments
 * @param {string} segmentsJson - JSON string of edit segments
 */
function applyCuts(segmentsJson) {
    try {
        var segments = JSON.parse(segmentsJson);
        var project = app.project;
        var sequence = project.activeSequence;
        
        if (!sequence) {
            return "Error: No active sequence";
        }
        
        // Get ticks per second for time conversion
        var tps = getTicksPerSecond();
        
        // Collect all "remove" segments
        var removeSegments = [];
        for (var i = 0; i < segments.length; i++) {
            if (segments[i].action === "remove") {
                removeSegments.push({
                    start: segments[i].start,
                    end: segments[i].end
                });
            }
        }
        
        if (removeSegments.length === 0) {
            return "No segments to remove";
        }
        
        // Sort by start time descending (remove from end to preserve earlier timecodes)
        removeSegments.sort(function(a, b) {
            return b.start - a.start;
        });
        
        var removedCount = 0;
        
        // Process each segment - from end to beginning
        for (var r = 0; r < removeSegments.length; r++) {
            var seg = removeSegments[r];
            
            // Convert seconds to time object
            var startTime = secondsToTime(seg.start, tps);
            var endTime = secondsToTime(seg.end, tps);
            
            // Set in and out points
            sequence.setInPoint(startTime.ticks);
            sequence.setOutPoint(endTime.ticks);
            
            // Use QE to perform the lift/extract
            try {
                var qeSeq = qe.project.getActiveSequence();
                if (qeSeq) {
                    // Extract (ripple delete) - removes content and closes gap
                    qeSeq.extract();
                    removedCount++;
                }
            } catch(qeError) {
                // QE not available, try alternative method
                // At minimum, set the in/out points so user can manually extract
            }
        }
        
        // Clear in/out points after we're done
        sequence.setInPoint(0);
        sequence.setOutPoint(sequence.end);
        
        if (removedCount > 0) {
            return "success: Removed " + removedCount + " segments";
        } else {
            return "success: Marked " + removeSegments.length + " segments. Use Extract (;) to remove.";
        }
        
    } catch (e) {
        return "Error: " + e.toString();
    }
}

/**
 * Get ticks per second (timebase)
 */
function getTicksPerSecond() {
    // Premiere uses 254016000000 ticks per second (standard timebase)
    return 254016000000;
}

/**
 * Convert seconds to Premiere time ticks
 */
function secondsToTime(seconds, tps) {
    var ticks = Math.round(seconds * tps);
    return {
        seconds: seconds,
        ticks: ticks
    };
}

/**
 * Add markers at cut points for manual review
 */
function addCutMarkers(segmentsJson) {
    try {
        var segments = JSON.parse(segmentsJson);
        var project = app.project;
        var sequence = project.activeSequence;
        
        if (!sequence) {
            return "Error: No active sequence";
        }
        
        var tps = getTicksPerSecond();
        var markers = sequence.markers;
        var addedCount = 0;
        
        for (var i = 0; i < segments.length; i++) {
            var seg = segments[i];
            
            if (seg.action === "remove") {
                var startTicks = Math.round(seg.start * tps);
                var endTicks = Math.round(seg.end * tps);
                
                // Create marker at start of remove segment
                var marker = markers.createMarker(startTicks);
                marker.name = "REMOVE";
                marker.comments = "Remove: " + formatTime(seg.start) + " - " + formatTime(seg.end);
                marker.end = endTicks;
                
                // Set marker color to red (index 0)
                try {
                    marker.setColorByIndex(0);
                } catch(e) {
                    // Color setting might not be available in all versions
                }
                
                addedCount++;
            }
        }
        
        return "success: Added " + addedCount + " markers";
        
    } catch(e) {
        return "Error: " + e.toString();
    }
}

/**
 * Clear all ScriptCutAI markers
 */
function clearMarkers() {
    try {
        var project = app.project;
        var sequence = project.activeSequence;
        
        if (!sequence) {
            return "Error: No active sequence";
        }
        
        var markers = sequence.markers;
        var toRemove = [];
        
        // Collect markers to remove
        for (var i = markers.numMarkers - 1; i >= 0; i--) {
            var marker = markers[i];
            if (marker.name === "REMOVE" || marker.name === "KEEP") {
                toRemove.push(marker);
            }
        }
        
        // Remove them
        for (var j = 0; j < toRemove.length; j++) {
            markers.deleteMarker(toRemove[j]);
        }
        
        return "success: Removed " + toRemove.length + " markers";
        
    } catch(e) {
        return "Error: " + e.toString();
    }
}

/**
 * Format seconds to MM:SS string
 */
function formatTime(seconds) {
    var mins = Math.floor(seconds / 60);
    var secs = Math.floor(seconds % 60);
    return mins + ":" + (secs < 10 ? "0" : "") + secs;
}

/**
 * Move playhead to a specific time
 */
function seekTo(seconds) {
    try {
        var project = app.project;
        var sequence = project.activeSequence;
        
        if (!sequence) {
            return "Error: No active sequence";
        }
        
        var tps = getTicksPerSecond();
        var ticks = Math.round(seconds * tps);
        
        sequence.setPlayerPosition(ticks.toString());
        
        return "success";
    } catch(e) {
        return "Error: " + e.toString();
    }
}

/**
 * Get sequence info
 */
function getSequenceInfo() {
    try {
        var project = app.project;
        
        if (!project) {
            return JSON.stringify({error: "No project open"});
        }
        
        var sequence = project.activeSequence;
        
        if (!sequence) {
            return JSON.stringify({error: "No active sequence"});
        }
        
        var tps = getTicksPerSecond();
        var durationSecs = parseInt(sequence.end) / tps;
        
        var info = {
            name: sequence.name,
            duration: durationSecs,
            videoTrackCount: sequence.videoTracks.numTracks,
            audioTrackCount: sequence.audioTracks.numTracks
        };
        
        return JSON.stringify(info);
    } catch(e) {
        return JSON.stringify({error: e.toString()});
    }
}

/**
 * Perform razor cuts at segment boundaries then delete remove segments
 * This is a more reliable method than extract
 */
function applyCutsWithRazor(segmentsJson) {
    try {
        var segments = JSON.parse(segmentsJson);
        var project = app.project;
        var sequence = project.activeSequence;
        
        if (!sequence) {
            return "Error: No active sequence";
        }
        
        var tps = getTicksPerSecond();
        
        // Collect remove segments, sorted from end to start
        var removeSegments = [];
        for (var i = 0; i < segments.length; i++) {
            if (segments[i].action === "remove") {
                removeSegments.push({
                    start: segments[i].start,
                    end: segments[i].end
                });
            }
        }
        
        removeSegments.sort(function(a, b) {
            return b.start - a.start;
        });
        
        // Process using QE
        try {
            app.enableQE();
            var qeSeq = qe.project.getActiveSequence();
            
            if (!qeSeq) {
                return "Error: Could not access QE sequence";
            }
            
            for (var r = 0; r < removeSegments.length; r++) {
                var seg = removeSegments[r];
                
                // Set in/out points
                var startTicks = Math.round(seg.start * tps);
                var endTicks = Math.round(seg.end * tps);
                
                sequence.setInPoint(startTicks.toString());
                sequence.setOutPoint(endTicks.toString());
                
                // Perform ripple delete (extract)
                qeSeq.extract();
            }
            
            // Clear in/out points
            sequence.setInPoint("0");
            sequence.setOutPoint(sequence.end);
            
            return "success: Applied " + removeSegments.length + " cuts";
            
        } catch(qeError) {
            return "Error with QE: " + qeError.toString() + ". Try using markers instead.";
        }
        
    } catch(e) {
        return "Error: " + e.toString();
    }
}
