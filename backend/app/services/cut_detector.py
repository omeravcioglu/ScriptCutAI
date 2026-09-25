"""
Cut Decision Engine - v2
Analyzes sentence attempts and generates edit instructions.
Now enforces strict script order and tighter boundaries.
"""
from typing import Optional

from app.models.schemas import (
    WordSegment,
    SentenceAttempt,
    EditSegment,
    EditAction,
    TranscriptResult
)
from app.services.alignment import (
    AlignmentService,
    split_into_sentences
)


class CutDetector:
    """
    Analyzes transcripts and script alignment to generate edit decisions.
    
    Strategy:
    1. Find ALL attempts at each script sentence
    2. Select best takes IN SCRIPT ORDER (sentence 1 before 2, etc.)
    3. Everything between good takes = REMOVE
    4. Tight boundaries around actual speech
    """
    
    def __init__(
        self,
        pre_speech_buffer: float = 0.1,     # Buffer before speech starts
        post_speech_buffer: float = 0.1,    # Buffer after speech ends
        min_gap_to_cut: float = 0.3,        # Minimum gap to cut
        silence_threshold: float = 1.0,      # Internal silence to cut
    ):
        self.pre_speech_buffer = pre_speech_buffer
        self.post_speech_buffer = post_speech_buffer
        self.min_gap_to_cut = min_gap_to_cut
        self.silence_threshold = silence_threshold
        self.alignment_service = AlignmentService()
    
    def analyze(
        self,
        transcript: TranscriptResult,
        script_text: str
    ) -> list[EditSegment]:
        """Main analysis entry point."""
        sentences = split_into_sentences(script_text)
        
        if not sentences:
            return [EditSegment(
                start=0.0, end=transcript.duration,
                action=EditAction.KEEP,
                reason="No script provided"
            )]
        
        print(f"  Script has {len(sentences)} sentences")
        
        # Find all attempts at each sentence
        attempts = self.alignment_service.find_sentence_attempts(
            transcript.words, sentences
        )
        print(f"  Found {len(attempts)} total attempts")
        
        # Group by sentence
        grouped = self.alignment_service.group_attempts_by_sentence(
            attempts, len(sentences)
        )
        
        # Select best takes enforcing strict script order
        best_takes = self._select_ordered_takes(grouped, len(sentences))
        print(f"  Selected {len(best_takes)} best takes")
        
        # Generate segments
        segments = self._generate_segments(
            best_takes, transcript.words, transcript.duration
        )
        
        return segments
    
    def _select_ordered_takes(
        self,
        grouped: dict[int, list[SentenceAttempt]],
        num_sentences: int
    ) -> list[SentenceAttempt]:
        """
        Select best take for each sentence, enforcing script order.
        Each selected take must start AFTER the previous one ends.
        """
        selected: list[SentenceAttempt] = []
        min_start_time = 0.0
        
        for sent_idx in range(num_sentences):
            attempts = grouped.get(sent_idx, [])
            
            # Filter to attempts that start after previous take
            valid = [a for a in attempts if a.start >= min_start_time - 0.2]
            
            if not valid:
                # No valid attempt for this sentence - skip it
                print(f"    Sentence {sent_idx + 1}: No valid take found after {min_start_time:.1f}s")
                continue
            
            # Pick the best valid attempt
            # Sort by: quality score, then prefer earlier (first good take)
            valid.sort(key=lambda a: (-a.score * a.completeness, a.start))
            best = valid[0]
            
            selected.append(best)
            min_start_time = best.end
            print(f"    Sentence {sent_idx + 1}: {best.start:.1f}s - {best.end:.1f}s (score: {best.score:.2f})")
        
        return selected
    
    def _generate_segments(
        self,
        takes: list[SentenceAttempt],
        words: list[WordSegment],
        duration: float
    ) -> list[EditSegment]:
        """Generate KEEP/REMOVE segments from selected takes."""
        segments: list[EditSegment] = []
        
        if not takes:
            return [EditSegment(
                start=0.0, end=duration,
                action=EditAction.REMOVE,
                reason="No matching content"
            )]
        
        current_time = 0.0
        
        for take in takes:
            # Get actual word boundaries for this take
            take_words = [w for w in words 
                         if w.start >= take.start - 0.1 and w.end <= take.end + 0.1]
            
            if not take_words:
                continue
            
            # Tight boundaries
            speech_start = max(0, take_words[0].start - self.pre_speech_buffer)
            speech_end = take_words[-1].end + self.post_speech_buffer
            
            # Remove content before this take
            if speech_start > current_time + self.min_gap_to_cut:
                # Check what's in this gap
                gap_words = [w for w in words 
                            if w.start >= current_time and w.end <= speech_start]
                
                if gap_words:
                    reason = f"Off-script ({len(gap_words)} words)"
                else:
                    reason = "Silence/pause"
                
                segments.append(EditSegment(
                    start=current_time,
                    end=speech_start,
                    action=EditAction.REMOVE,
                    reason=reason
                ))
            
            # Keep this take
            segments.append(EditSegment(
                start=speech_start,
                end=speech_end,
                action=EditAction.KEEP,
                reason=f"Sentence {take.sentence_index + 1}"
            ))
            
            current_time = speech_end
        
        # Remove content after last take
        if current_time < duration - 0.1:
            segments.append(EditSegment(
                start=current_time,
                end=duration,
                action=EditAction.REMOVE,
                reason="After script ends"
            ))
        
        # Merge and clean
        segments = self._merge_segments(segments)
        
        # Split on internal silence
        segments = self._handle_internal_silence(segments, words)
        
        return segments
    
    def _merge_segments(self, segments: list[EditSegment]) -> list[EditSegment]:
        """Merge adjacent segments of same type."""
        if not segments:
            return []
        
        merged: list[EditSegment] = [segments[0]]
        
        for seg in segments[1:]:
            last = merged[-1]
            
            if last.action == seg.action and seg.start <= last.end + 0.05:
                # Merge
                last.end = max(last.end, seg.end)
                if seg.reason and last.reason:
                    if seg.reason not in last.reason:
                        last.reason = f"{last.reason}; {seg.reason}"
            else:
                merged.append(seg)
        
        return merged
    
    def _handle_internal_silence(
        self,
        segments: list[EditSegment],
        words: list[WordSegment]
    ) -> list[EditSegment]:
        """Remove long silences inside KEEP segments."""
        result: list[EditSegment] = []
        
        for seg in segments:
            if seg.action == EditAction.REMOVE:
                result.append(seg)
                continue
            
            # Find words in this segment
            seg_words = [w for w in words 
                        if w.start >= seg.start and w.end <= seg.end]
            
            if len(seg_words) < 2:
                result.append(seg)
                continue
            
            # Check for long gaps between words
            current_start = seg.start
            has_splits = False
            
            for i in range(len(seg_words) - 1):
                gap = seg_words[i + 1].start - seg_words[i].end
                
                if gap >= self.silence_threshold:
                    # Split here
                    has_splits = True
                    
                    # Keep up to current word
                    result.append(EditSegment(
                        start=current_start,
                        end=seg_words[i].end + self.post_speech_buffer,
                        action=EditAction.KEEP,
                        reason=seg.reason
                    ))
                    
                    # Remove the silence
                    result.append(EditSegment(
                        start=seg_words[i].end + self.post_speech_buffer,
                        end=seg_words[i + 1].start - self.pre_speech_buffer,
                        action=EditAction.REMOVE,
                        reason="Internal pause"
                    ))
                    
                    current_start = seg_words[i + 1].start - self.pre_speech_buffer
            
            # Add remaining portion
            if has_splits:
                if current_start < seg.end:
                    result.append(EditSegment(
                        start=current_start,
                        end=seg.end,
                        action=EditAction.KEEP,
                        reason=seg.reason
                    ))
            else:
                result.append(seg)
        
        return self._merge_segments(result)
    
    def get_statistics(self, segments: list[EditSegment]) -> tuple[float, float]:
        """Calculate kept and removed duration."""
        kept = sum(s.end - s.start for s in segments if s.action == EditAction.KEEP)
        removed = sum(s.end - s.start for s in segments if s.action == EditAction.REMOVE)
        return kept, removed
