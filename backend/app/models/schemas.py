"""
Pydantic models for ScriptCutAI API
"""
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class EditAction(str, Enum):
    """Action to take on a time segment"""
    KEEP = "keep"
    REMOVE = "remove"


class WordSegment(BaseModel):
    """A single transcribed word with timing"""
    word: str
    start: float  # seconds
    end: float    # seconds
    confidence: Optional[float] = None


class TranscriptResult(BaseModel):
    """Full transcription result"""
    words: list[WordSegment]
    full_text: str
    duration: float  # total audio duration in seconds


class SentenceAttempt(BaseModel):
    """One attempt at speaking a script sentence"""
    sentence_index: int          # which sentence in the script
    start: float                 # start time in video
    end: float                   # end time in video
    spoken_text: str             # what was actually said
    completeness: float          # 0-1: how much of sentence was said
    score: float                 # overall quality score


class EditSegment(BaseModel):
    """A single edit instruction"""
    start: float      # start time in seconds
    end: float        # end time in seconds
    action: EditAction
    reason: Optional[str] = None  # why this decision was made


class AnalysisRequest(BaseModel):
    """Request to analyze a video"""
    video_path: str
    script_text: str
    whisper_model: str = "base"  # tiny, base, small, medium, large


class AnalysisResult(BaseModel):
    """Complete analysis result"""
    transcript: TranscriptResult
    edit_segments: list[EditSegment]
    kept_duration: float    # total duration of kept segments
    removed_duration: float # total duration of removed segments
    script_sentences: list[str]  # parsed sentences from script

