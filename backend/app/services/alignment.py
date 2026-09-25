"""
Script Alignment Service
Matches transcribed speech to the original script sentences.
Detects multiple attempts, mistakes, and incomplete readings.
"""
import re
from typing import Optional
from Levenshtein import ratio as levenshtein_ratio

from app.models.schemas import WordSegment, SentenceAttempt


# Common filler words to filter out
FILLER_WORDS = {
    "um", "uh", "ah", "er", "erm", "uhm",
    "like", "you know", "i mean", "basically",
    "so", "well", "okay", "ok", "right",
    "yeah", "yes", "no", "hmm", "hm"
}

# Common off-script indicators (talking to crew)
OFF_SCRIPT_INDICATORS = {
    "wait", "hold on", "sorry", "again", "one more",
    "let me", "can we", "is that", "how was",
    "good", "perfect", "great", "that was",
    "okay so", "alright", "ready", "go ahead",
    "cut", "stop", "pause", "retry"
}


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    Removes punctuation, lowercases, and normalizes whitespace.
    """
    text = re.sub(r"[^\w\s']", " ", text)
    text = " ".join(text.lower().split())
    return text


def split_into_sentences(script_text: str) -> list[str]:
    """
    Split script into sentences.
    Handles common sentence endings and preserves the original text.
    """
    sentences = re.split(r'(?<=[.!?])\s+', script_text.strip())
    return [s.strip() for s in sentences if s.strip()]


def get_sentence_words(sentence: str) -> list[str]:
    """Get normalized words from a sentence"""
    return normalize_text(sentence).split()


def is_filler_word(word: str) -> bool:
    """Check if a word is a filler word"""
    return normalize_text(word) in FILLER_WORDS


def looks_like_off_script(words: list[str]) -> bool:
    """
    Check if a sequence of words looks like off-script talking.
    E.g., "wait let me try again" or "sorry can we redo that"
    """
    text = " ".join(normalize_text(w) for w in words[:6])
    
    for indicator in OFF_SCRIPT_INDICATORS:
        if indicator in text:
            return True
    
    return False


class AlignmentService:
    """
    Aligns transcribed speech with the original script.
    """
    
    def __init__(
        self, 
        similarity_threshold: float = 0.55,
        min_words_to_match: int = 3
    ):
        """
        Args:
            similarity_threshold: Minimum similarity (0-1) to consider a match
            min_words_to_match: Minimum words needed for a valid match
        """
        self.similarity_threshold = similarity_threshold
        self.min_words_to_match = min_words_to_match
    
    def find_sentence_attempts(
        self,
        words: list[WordSegment],
        script_sentences: list[str]
    ) -> list[SentenceAttempt]:
        """
        Find all attempts at reading each script sentence.
        """
        attempts: list[SentenceAttempt] = []
        
        if not words or not script_sentences:
            return attempts
        
        # Pre-compute normalized sentence data
        sentence_data = []
        for idx, sent in enumerate(script_sentences):
            sent_words = get_sentence_words(sent)
            sentence_data.append({
                "index": idx,
                "original": sent,
                "words": sent_words,
                "normalized": " ".join(sent_words),
                "key_words": self._extract_key_words(sent_words)
            })
        
        # Sliding window through transcript
        i = 0
        while i < len(words):
            # Skip filler words
            while i < len(words) and is_filler_word(words[i].word):
                i += 1
            
            if i >= len(words):
                break
            
            # Check if this looks like off-script talking
            upcoming_words = [w.word for w in words[i:min(i+6, len(words))]]
            if looks_like_off_script(upcoming_words):
                i += 1
                continue
            
            # Try to match a sentence starting here
            best_match = self._find_best_match_at_position(words, i, sentence_data)
            
            if best_match:
                attempts.append(best_match)
                # Move past most of this match, but allow some overlap for repeated sentences
                skip_to = self._find_word_index_at_time(words, best_match.end - 0.3)
                i = max(i + 1, skip_to)
            else:
                i += 1
        
        return sorted(attempts, key=lambda a: a.start)
    
    def _extract_key_words(self, words: list[str]) -> set[str]:
        """Extract important words from a sentence (nouns, verbs, etc.)"""
        # Simple heuristic: words with 4+ characters are likely important
        return {w for w in words if len(w) >= 4}
    
    def _find_best_match_at_position(
        self,
        words: list[WordSegment],
        start_idx: int,
        sentence_data: list[dict]
    ) -> Optional[SentenceAttempt]:
        """Find the best matching sentence starting at a position."""
        best_attempt: Optional[SentenceAttempt] = None
        best_score = 0.0
        
        for sent_info in sentence_data:
            attempt = self._try_match_sentence(words, start_idx, sent_info)
            
            if attempt and attempt.score > best_score:
                best_score = attempt.score
                best_attempt = attempt
        
        return best_attempt
    
    def _try_match_sentence(
        self,
        words: list[WordSegment],
        start_idx: int,
        sent_info: dict
    ) -> Optional[SentenceAttempt]:
        """
        Try to match a specific sentence starting at a position.
        """
        sent_words = sent_info["words"]
        sent_normalized = sent_info["normalized"]
        key_words = sent_info["key_words"]
        
        if not sent_words or len(sent_words) < self.min_words_to_match:
            return None
        
        # Quick check: do the first few words look like a match?
        first_spoken = [normalize_text(words[start_idx + j].word) 
                       for j in range(min(3, len(words) - start_idx))]
        first_script = sent_words[:3]
        
        # At least one of the first 3 words should match
        if not any(sw in first_spoken for sw in first_script):
            # Check for key word presence as fallback
            first_few = [normalize_text(words[start_idx + j].word) 
                        for j in range(min(6, len(words) - start_idx))]
            if not any(kw in first_few for kw in key_words):
                return None
        
        # Try different window sizes
        min_words_needed = max(self.min_words_to_match, len(sent_words) // 2)
        max_window = min(len(words) - start_idx, len(sent_words) * 2)
        
        best_similarity = 0.0
        best_end_idx = start_idx
        best_spoken = ""
        best_word_count = 0
        
        for window_size in range(min_words_needed, max_window + 1):
            end_idx = start_idx + window_size
            if end_idx > len(words):
                break
            
            # Extract spoken words (filter fillers)
            spoken_words = []
            for w in words[start_idx:end_idx]:
                if not is_filler_word(w.word):
                    spoken_words.append(normalize_text(w.word))
            
            if len(spoken_words) < self.min_words_to_match:
                continue
            
            spoken_text = " ".join(spoken_words)
            
            # Compare with sentence
            similarity = levenshtein_ratio(spoken_text, sent_normalized)
            
            # Bonus for matching key words
            matched_keys = sum(1 for kw in key_words if kw in spoken_text)
            key_bonus = matched_keys / max(len(key_words), 1) * 0.1
            
            adjusted_similarity = similarity + key_bonus
            
            if adjusted_similarity > best_similarity:
                best_similarity = adjusted_similarity
                best_end_idx = end_idx
                best_spoken = " ".join(w.word for w in words[start_idx:end_idx])
                best_word_count = len(spoken_words)
        
        # Check if match is good enough
        if best_similarity < self.similarity_threshold:
            return None
        
        # Calculate completeness
        completeness = min(1.0, best_word_count / len(sent_words))
        
        # Require reasonable completeness
        if completeness < 0.4:
            return None
        
        return SentenceAttempt(
            sentence_index=sent_info["index"],
            start=words[start_idx].start,
            end=words[best_end_idx - 1].end,
            spoken_text=best_spoken,
            completeness=completeness,
            score=best_similarity
        )
    
    def _find_word_index_at_time(self, words: list[WordSegment], time: float) -> int:
        """Find the word index at or after a given time"""
        for i, word in enumerate(words):
            if word.start >= time:
                return i
        return len(words)
    
    def group_attempts_by_sentence(
        self,
        attempts: list[SentenceAttempt],
        num_sentences: int
    ) -> dict[int, list[SentenceAttempt]]:
        """Group attempts by sentence index."""
        grouped: dict[int, list[SentenceAttempt]] = {
            i: [] for i in range(num_sentences)
        }
        
        for attempt in attempts:
            if 0 <= attempt.sentence_index < num_sentences:
                grouped[attempt.sentence_index].append(attempt)
        
        # Sort each group by score (best first)
        for sent_idx in grouped:
            grouped[sent_idx].sort(key=lambda a: a.score, reverse=True)
        
        return grouped
