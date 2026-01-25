"""Voice Consistency Analyzer - Analyze character voice consistency."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import numpy as np

from app.core.config import settings
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Voice analysis limited.")


class VoiceConsistencyAnalyzer:
    """
    Analyzes character voice consistency by comparing dialogues
    with validated historical patterns.
    """

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        memory_service: Optional[MemoryService] = None,
    ) -> None:
        self.memory_service = memory_service or MemoryService()
        self.model = None
        self.enabled = settings.VOICE_ANALYZER_ENABLED
        self.threshold = settings.VOICE_CONSISTENCY_THRESHOLD
        self.min_dialogues = settings.VOICE_MIN_DIALOGUES_FOR_ANALYSIS

        if not self.enabled:
            logger.info("Voice analyzer disabled by configuration")
            return

        if EMBEDDINGS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                logger.info(f"Voice analyzer loaded model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")

    def extract_dialogues(
        self,
        text: str,
        character_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract dialogues from text, optionally filtering by character.

        Args:
            text: The text to extract dialogues from.
            character_name: Optional character to filter for.

        Returns:
            List of dialogue entries with speaker and content.
        """
        dialogues = []

        # Pattern for dialogues: "text" or « text » or — text
        patterns = [
            r'"([^"]+)"',  # "dialogue"
            r'«\s*([^»]+)\s*»',  # « dialogue »
            r'—\s*([^—\n]+)',  # — dialogue
            r'-\s+([A-Z][^-\n]+)',  # - Dialogue starting with capital
        ]

        # Pattern to detect speaker before dialogue (French verbs)
        speaker_pattern = r'(\b[A-Z][a-zàâäéèêëïîôùûüÿœæç]+)\s+(?:dit|demanda|répondit|murmura|cria|chuchota|expliqua|ajouta|déclara|s\'exclama|protesta|affirma)'

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                dialogue = match.group(1).strip()
                if len(dialogue) < 5:
                    continue

                # Try to find speaker
                speaker = None
                context_start = max(0, match.start() - 100)
                context = text[context_start:match.start()]

                speaker_match = re.search(speaker_pattern, context)
                if speaker_match:
                    speaker = speaker_match.group(1)

                # Filter by character if specified
                if character_name and speaker:
                    if speaker.lower() != character_name.lower():
                        continue

                dialogues.append({
                    "speaker": speaker,
                    "dialogue": dialogue,
                    "position": match.start(),
                })

        return dialogues

    async def analyze_voice_consistency(
        self,
        character_name: str,
        new_dialogues: List[str],
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Analyze voice consistency for a character.

        Args:
            character_name: Name of the character.
            new_dialogues: New dialogues to analyze.
            project_id: Project identifier.

        Returns:
            Voice consistency analysis.
        """
        if not self.enabled:
            return {
                "character": character_name,
                "voice_consistency_score": 1.0,
                "analysis_available": False,
                "reason": "Voice analysis disabled",
            }

        if not self.model or not new_dialogues:
            return {
                "character": character_name,
                "voice_consistency_score": 1.0,
                "analysis_available": False,
                "reason": "No model or dialogues available",
            }

        # Retrieve validated dialogues from ChromaDB
        validated_dialogues = self.memory_service.retrieve_style_memory(
            project_id=project_id,
            query=f"dialogues de {character_name}",
            top_k=20,
        )

        if not validated_dialogues or len(validated_dialogues) < self.min_dialogues:
            return {
                "character": character_name,
                "voice_consistency_score": 1.0,
                "analysis_available": False,
                "reason": "Insufficient historical dialogues",
            }

        # Embed dialogues
        new_embeddings = self.model.encode(new_dialogues, convert_to_numpy=True)
        validated_embeddings = self.model.encode(validated_dialogues, convert_to_numpy=True)

        # Compute average similarity
        similarities = []
        outliers = []

        for i, new_emb in enumerate(new_embeddings):
            # Compute cosine similarity with all validated
            sims = self._cosine_similarity(new_emb, validated_embeddings)
            avg_sim = float(np.mean(sims))
            max_sim = float(np.max(sims))

            similarities.append(avg_sim)

            # Flag outliers
            if avg_sim < self.threshold:
                outliers.append({
                    "dialogue": new_dialogues[i],
                    "avg_similarity": avg_sim,
                    "max_similarity": max_sim,
                })

        overall_score = float(np.mean(similarities))
        drift_detected = overall_score < self.threshold

        return {
            "character": character_name,
            "voice_consistency_score": overall_score,
            "analysis_available": True,
            "drift_detected": drift_detected,
            "dialogues_analyzed": len(new_dialogues),
            "reference_dialogues": len(validated_dialogues),
            "outlier_dialogues": outliers,
            "individual_scores": similarities,
        }

    async def analyze_chapter_voices(
        self,
        chapter_text: str,
        project_id: str,
        known_characters: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze voice consistency for all characters in a chapter.

        Args:
            chapter_text: The chapter content.
            project_id: Project identifier.
            known_characters: List of known character names.

        Returns:
            Dict mapping character names to voice analyses.
        """
        if not self.enabled:
            return {}

        results = {}

        for character in known_characters:
            dialogues = self.extract_dialogues(chapter_text, character)

            if not dialogues:
                continue

            dialogue_texts = [d["dialogue"] for d in dialogues]

            analysis = await self.analyze_voice_consistency(
                character_name=character,
                new_dialogues=dialogue_texts,
                project_id=project_id,
            )

            results[character] = analysis

        return results

    def store_validated_dialogues(
        self,
        character_name: str,
        dialogues: List[str],
        project_id: str,
        chapter_index: int,
    ) -> None:
        """
        Store validated dialogues for future reference.

        Args:
            character_name: Name of the character.
            dialogues: List of dialogue texts.
            project_id: Project identifier.
            chapter_index: Chapter number.
        """
        if not dialogues:
            return

        for dialogue in dialogues:
            self.memory_service.store_style_memory(
                project_id=project_id,
                content=dialogue,
                metadata={
                    "type": "dialogue",
                    "character": character_name,
                    "chapter_index": chapter_index,
                    "validated": True,
                },
            )

    def _cosine_similarity(
        self, embedding: np.ndarray, embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarity between one embedding and many."""
        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=-1, keepdims=True)

        # Compute similarity
        return np.dot(embeddings, embedding)

    def analyze_dialogue_patterns(
        self,
        dialogues: List[str],
    ) -> Dict[str, Any]:
        """
        Analyze linguistic patterns in dialogues.

        Args:
            dialogues: List of dialogue texts.

        Returns:
            Pattern analysis results.
        """
        if not dialogues:
            return {}

        # Compute basic statistics
        lengths = [len(d.split()) for d in dialogues]
        avg_length = np.mean(lengths)

        # Count punctuation patterns
        question_count = sum(1 for d in dialogues if "?" in d)
        exclamation_count = sum(1 for d in dialogues if "!" in d)

        # Count common words
        all_words = " ".join(dialogues).lower().split()
        word_freq = {}
        for word in all_words:
            if len(word) > 3:  # Skip short words
                word_freq[word] = word_freq.get(word, 0) + 1

        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_dialogues": len(dialogues),
            "avg_word_count": float(avg_length),
            "question_ratio": question_count / len(dialogues) if dialogues else 0,
            "exclamation_ratio": exclamation_count / len(dialogues) if dialogues else 0,
            "characteristic_words": dict(top_words),
        }
