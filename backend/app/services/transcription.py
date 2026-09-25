"""
Transcription Service using OpenAI Whisper
Provides word-level timestamps for audio/video files
"""
import whisper
import torch
import os
from typing import Optional

from app.models.schemas import WordSegment, TranscriptResult


class TranscriptionService:
    """
    Handles audio transcription using Whisper.
    Extracts word-level timestamps for precise editing.
    """
    
    def __init__(self, model_name: str = "base"):
        """
        Initialize the transcription service.
        
        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
        """
        self.model_name = model_name
        self.model: Optional[whisper.Whisper] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def load_model(self) -> None:
        """Load the Whisper model into memory"""
        if self.model is None:
            print(f"Loading Whisper '{self.model_name}' model on {self.device}...")
            self.model = whisper.load_model(self.model_name, device=self.device)
            print("Model loaded successfully!")
    
    def transcribe(self, audio_path: str) -> TranscriptResult:
        """
        Transcribe audio/video file with word-level timestamps.
        
        Args:
            audio_path: Path to audio or video file
            
        Returns:
            TranscriptResult with words, timestamps, and full text
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Ensure model is loaded
        self.load_model()
        
        print(f"Transcribing: {audio_path}")
        
        # Transcribe with word-level timestamps
        result = self.model.transcribe(
            audio_path,
            word_timestamps=True,
            language="en",  # Can be made configurable
            verbose=False
        )
        
        # Extract word segments from all segments
        words: list[WordSegment] = []
        
        for segment in result.get("segments", []):
            segment_words = segment.get("words", [])
            for word_info in segment_words:
                words.append(WordSegment(
                    word=word_info["word"].strip(),
                    start=word_info["start"],
                    end=word_info["end"],
                    confidence=word_info.get("probability")
                ))
        
        # Calculate total duration from the last word or segment
        duration = 0.0
        if words:
            duration = words[-1].end
        elif result.get("segments"):
            duration = result["segments"][-1]["end"]
        
        return TranscriptResult(
            words=words,
            full_text=result.get("text", "").strip(),
            duration=duration
        )
    
    def unload_model(self) -> None:
        """Unload model to free memory"""
        if self.model is not None:
            del self.model
            self.model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("Model unloaded")


# Global instance for reuse (avoids reloading model on each request)
_transcription_service: Optional[TranscriptionService] = None


def get_transcription_service(model_name: str = "base") -> TranscriptionService:
    """Get or create the transcription service singleton"""
    global _transcription_service
    
    if _transcription_service is None or _transcription_service.model_name != model_name:
        if _transcription_service is not None:
            _transcription_service.unload_model()
        _transcription_service = TranscriptionService(model_name)
    
    return _transcription_service

