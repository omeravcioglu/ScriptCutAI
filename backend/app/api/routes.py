"""
API Routes for ScriptCutAI
Exposes endpoints for video analysis and edit generation.
"""
import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.models.schemas import (
    AnalysisRequest,
    AnalysisResult,
    TranscriptResult,
    EditSegment
)
from app.services.transcription import get_transcription_service
from app.services.cut_detector import CutDetector
from app.services.alignment import split_into_sentences

router = APIRouter()


class TranscribeRequest(BaseModel):
    """Request for transcription only"""
    video_path: str
    whisper_model: str = "base"


class TranscribeResponse(BaseModel):
    """Response from transcription"""
    success: bool
    transcript: TranscriptResult | None = None
    error: str | None = None


class AnalyzeResponse(BaseModel):
    """Response from full analysis"""
    success: bool
    result: AnalysisResult | None = None
    error: str | None = None


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_video(request: TranscribeRequest):
    """
    Transcribe a video file with word-level timestamps.
    
    This endpoint only performs transcription, without script comparison.
    Useful for previewing what Whisper heard before running full analysis.
    """
    try:
        # Validate file exists
        if not os.path.exists(request.video_path):
            raise HTTPException(
                status_code=404,
                detail=f"Video file not found: {request.video_path}"
            )
        
        # Get transcription service
        service = get_transcription_service(request.whisper_model)
        
        # Transcribe
        transcript = service.transcribe(request.video_path)
        
        return TranscribeResponse(
            success=True,
            transcript=transcript
        )
        
    except FileNotFoundError as e:
        return TranscribeResponse(
            success=False,
            error=str(e)
        )
    except Exception as e:
        return TranscribeResponse(
            success=False,
            error=f"Transcription failed: {str(e)}"
        )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_video(request: AnalysisRequest):
    """
    Full analysis: transcribe video, compare to script, generate edit instructions.
    
    This is the main endpoint that:
    1. Transcribes the video using Whisper
    2. Aligns the transcript with the provided script
    3. Identifies best takes for each sentence
    4. Generates KEEP/REMOVE edit segments
    
    The edit segments can be used to automatically cut the video in Premiere Pro.
    """
    try:
        # Validate file exists
        if not os.path.exists(request.video_path):
            raise HTTPException(
                status_code=404,
                detail=f"Video file not found: {request.video_path}"
            )
        
        # Validate script
        if not request.script_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Script text cannot be empty"
            )
        
        # Step 1: Transcribe
        print(f"[1/3] Transcribing video: {request.video_path}")
        transcription_service = get_transcription_service(request.whisper_model)
        transcript = transcription_service.transcribe(request.video_path)
        print(f"      Found {len(transcript.words)} words, duration: {transcript.duration:.2f}s")
        
        # Step 2: Analyze and generate cuts
        print("[2/3] Analyzing transcript against script...")
        cut_detector = CutDetector()
        edit_segments = cut_detector.analyze(transcript, request.script_text)
        print(f"      Generated {len(edit_segments)} edit segments")
        
        # Step 3: Calculate statistics
        print("[3/3] Calculating statistics...")
        kept_duration, removed_duration = cut_detector.get_statistics(edit_segments)
        
        # Parse sentences for response
        script_sentences = split_into_sentences(request.script_text)
        
        result = AnalysisResult(
            transcript=transcript,
            edit_segments=edit_segments,
            kept_duration=kept_duration,
            removed_duration=removed_duration,
            script_sentences=script_sentences
        )
        
        print(f"Analysis complete!")
        print(f"  - Keep: {kept_duration:.2f}s")
        print(f"  - Remove: {removed_duration:.2f}s")
        print(f"  - Reduction: {(removed_duration / transcript.duration * 100):.1f}%")
        
        return AnalyzeResponse(
            success=True,
            result=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        return AnalyzeResponse(
            success=False,
            error=f"Analysis failed: {str(e)}"
        )


@router.get("/edits/premiere-format")
async def get_premiere_format_info():
    """
    Information about the edit format for Premiere Pro integration.
    
    The edit_segments returned by /analyze can be used in Premiere Pro's JSX:
    - Each segment has start/end times in seconds
    - action: "keep" or "remove"
    - Apply cuts at segment boundaries and delete "remove" segments
    """
    return {
        "format": {
            "start": "Start time in seconds (float)",
            "end": "End time in seconds (float)", 
            "action": "keep or remove",
            "reason": "Human-readable explanation"
        },
        "usage": {
            "step1": "Call POST /api/analyze with video_path and script_text",
            "step2": "Get edit_segments from response",
            "step3": "In Premiere JSX, iterate segments and apply razor cuts",
            "step4": "Delete clips where action == 'remove'"
        },
        "example_jsx": """
// Pseudocode for Premiere Pro JSX
var segments = getSegmentsFromAPI();
for (var i = 0; i < segments.length; i++) {
    var seg = segments[i];
    if (seg.action === 'remove') {
        // Select time range seg.start to seg.end
        // Delete selected clips
    }
}
        """
    }


@router.post("/unload-model")
async def unload_model():
    """
    Unload the Whisper model from memory.
    Call this when done processing to free up RAM/VRAM.
    """
    try:
        service = get_transcription_service()
        service.unload_model()
        return {"success": True, "message": "Model unloaded"}
    except Exception as e:
        return {"success": False, "error": str(e)}

