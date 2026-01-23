"""Semantic Validator - Detect subtle contradictions using embeddings."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Semantic validation disabled.")


class SemanticValidator:
    """
    Validates narrative consistency using semantic embeddings.

    Detects contradictions that are semantically related but logically
    incompatible, which LLM analysis might miss.
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
        """
        Initialize the semantic validator.

        Args:
            model_name: Name of the sentence-transformers model to use.
        """
        self.model = None
        self.model_name = model_name
        self.enabled = settings.SEMANTIC_VALIDATOR_ENABLED

        if not self.enabled:
            logger.info("Semantic validator disabled by configuration")
            return

        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                logger.info(f"Loaded sentence transformer model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load sentence transformer: {e}")

    def extract_facts(self, text: str) -> List[str]:
        """
        Extract factual statements from text.

        Args:
            text: Text to extract facts from.

        Returns:
            List of factual statements.
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)

        facts = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            # Filter for likely factual statements
            # (contains names, descriptions, states, actions)
            if any([
                # Contains a proper noun (capitalized word not at start)
                re.search(r'(?<!^)\b[A-Z][a-zàâäéèêëïîôùûüÿœæç]+', sentence),
                # Contains "est" or "était" (being verbs in French)
                re.search(r'\b(est|était|sont|étaient|a|avait|possède|déteste|aime)\b', sentence, re.I),
                # Contains descriptive patterns
                re.search(r'\b(toujours|jamais|souvent|parfois)\b', sentence, re.I),
            ]):
                facts.append(sentence)

        return facts

    def embed(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed.

        Returns:
            Numpy array of embeddings or None if model not available.
        """
        if not self.model or not texts:
            return None

        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return None

    def find_similar_facts(
        self,
        new_fact: str,
        new_embedding: np.ndarray,
        established_facts: List[str],
        established_embeddings: np.ndarray,
        threshold: float = 0.7,
    ) -> List[Tuple[str, float]]:
        """
        Find established facts similar to a new fact.

        Args:
            new_fact: The new fact to compare.
            new_embedding: Embedding of the new fact.
            established_facts: List of established facts.
            established_embeddings: Embeddings of established facts.
            threshold: Minimum similarity threshold.

        Returns:
            List of (fact, similarity_score) tuples.
        """
        if established_embeddings is None or len(established_embeddings) == 0:
            return []

        # Compute cosine similarities
        similarities = self._cosine_similarity(new_embedding, established_embeddings)

        # Find facts above threshold
        similar = []
        for i, sim in enumerate(similarities):
            if sim >= threshold:
                similar.append((established_facts[i], float(sim)))

        # Sort by similarity descending
        similar.sort(key=lambda x: x[1], reverse=True)
        return similar

    def detect_contradictions(
        self,
        new_facts: List[str],
        established_facts: List[str],
        similarity_threshold: Optional[float] = None,
        contradiction_patterns: Optional[List[Tuple[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect potential contradictions between new and established facts.

        Args:
            new_facts: Facts from the new content.
            established_facts: Previously established facts.
            similarity_threshold: Min similarity to consider related.
            contradiction_patterns: Pairs of contradictory patterns.

        Returns:
            List of potential contradictions with details.
        """
        if not self.model:
            return []

        if not new_facts or not established_facts:
            return []

        # Use config threshold if not provided
        if similarity_threshold is None:
            similarity_threshold = settings.SEMANTIC_CONFLICT_THRESHOLD

        # Default contradiction patterns (French)
        if contradiction_patterns is None:
            contradiction_patterns = [
                ("vivant", "mort"),
                ("aime", "déteste"),
                ("ami", "ennemi"),
                ("présent", "absent"),
                ("possède", "a perdu"),
                ("connaît", "ignore"),
                ("jeune", "vieux"),
                ("riche", "pauvre"),
                ("grand", "petit"),
                ("fort", "faible"),
                ("marié", "célibataire"),
                ("innocent", "coupable"),
                ("confiance", "méfiance"),
                ("ouvert", "fermé"),
                ("jour", "nuit"),
            ]

        # Embed all facts
        new_embeddings = self.embed(new_facts)
        established_embeddings = self.embed(established_facts)

        if new_embeddings is None or established_embeddings is None:
            return []

        contradictions = []

        for i, new_fact in enumerate(new_facts):
            new_emb = new_embeddings[i:i+1]

            # Find similar established facts
            similar = self.find_similar_facts(
                new_fact, new_emb, established_facts, established_embeddings,
                threshold=similarity_threshold
            )

            for est_fact, similarity in similar:
                # Check for contradiction patterns
                is_contradiction, pattern = self._check_contradiction_patterns(
                    new_fact, est_fact, contradiction_patterns
                )

                if is_contradiction:
                    contradictions.append({
                        "new_fact": new_fact,
                        "established_fact": est_fact,
                        "similarity_score": similarity,
                        "contradiction_type": "pattern_match",
                        "pattern": pattern,
                        "confidence": min(0.95, similarity + 0.1),
                        "severity": "high",
                    })
                elif similarity > 0.85:
                    # Very high similarity but different - might be contradiction
                    if self._facts_differ(new_fact, est_fact):
                        contradictions.append({
                            "new_fact": new_fact,
                            "established_fact": est_fact,
                            "similarity_score": similarity,
                            "contradiction_type": "semantic_conflict",
                            "pattern": None,
                            "confidence": similarity * 0.7,
                            "severity": "medium",
                        })

        return contradictions

    def _cosine_similarity(
        self, embedding: np.ndarray, embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarity between one embedding and many."""
        # Normalize
        embedding = embedding / np.linalg.norm(embedding, axis=-1, keepdims=True)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=-1, keepdims=True)

        # Compute similarity
        return np.dot(embedding, embeddings.T).flatten()

    def _check_contradiction_patterns(
        self,
        fact1: str,
        fact2: str,
        patterns: List[Tuple[str, str]],
    ) -> Tuple[bool, Optional[Tuple[str, str]]]:
        """Check if two facts contain contradictory patterns."""
        f1_lower = fact1.lower()
        f2_lower = fact2.lower()

        for p1, p2 in patterns:
            # Check if one fact has p1 and other has p2
            if (p1 in f1_lower and p2 in f2_lower) or (p2 in f1_lower and p1 in f2_lower):
                return True, (p1, p2)

        return False, None

    def _facts_differ(self, fact1: str, fact2: str) -> bool:
        """Check if two similar facts say different things."""
        # Extract potential subjects (capitalized words)
        subjects1 = set(re.findall(r'\b[A-Z][a-zàâäéèêëïîôùûüÿœæç]+\b', fact1))
        subjects2 = set(re.findall(r'\b[A-Z][a-zàâäéèêëïîôùûüÿœæç]+\b', fact2))

        common_subjects = subjects1 & subjects2

        if not common_subjects:
            return False

        # If they share subjects but aren't nearly identical, they might conflict
        # Compute word overlap
        words1 = set(fact1.lower().split())
        words2 = set(fact2.lower().split())

        overlap = len(words1 & words2) / max(len(words1), len(words2))

        # If overlap is between 30-70%, likely saying different things about same subject
        return 0.3 < overlap < 0.7


# Convenience function for integration
async def validate_chapter_semantically(
    chapter_text: str,
    established_context: str,
    threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Validate a chapter against established context using semantic analysis.

    Args:
        chapter_text: The new chapter content.
        established_context: Previously established facts/context.
        threshold: Contradiction detection threshold.

    Returns:
        List of potential semantic contradictions.
    """
    if not settings.SEMANTIC_VALIDATOR_ENABLED:
        return []

    validator = SemanticValidator()

    new_facts = validator.extract_facts(chapter_text)
    established_facts = validator.extract_facts(established_context)

    return validator.detect_contradictions(
        new_facts=new_facts,
        established_facts=established_facts,
        similarity_threshold=threshold,
    )
