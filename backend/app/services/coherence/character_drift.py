"""Character Drift Detector - Detect unjustified character changes."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.llm_client import DeepSeekClient
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class CharacterDriftDetector:
    """
    Detects when a character's behavior drifts from their established arc
    without proper justification through events or development.
    """

    def __init__(self) -> None:
        self.llm_client = DeepSeekClient()
        self.memory_service = MemoryService()
        self.enabled = settings.CHARACTER_DRIFT_ENABLED
        self.threshold = settings.CHARACTER_DRIFT_THRESHOLD

    async def analyze_character_consistency(
        self,
        character_name: str,
        current_behavior: str,
        project_id: str,
        chapter_index: int,
    ) -> Dict[str, Any]:
        """
        Analyze if current character behavior is consistent with their arc.

        Args:
            character_name: Name of the character.
            current_behavior: Description of current behavior/dialogue.
            project_id: Project identifier.
            chapter_index: Current chapter number.

        Returns:
            Analysis result with drift detection.
        """
        if not self.enabled:
            return {
                "character": character_name,
                "drift_detected": False,
                "reason": "Character drift detection disabled",
            }

        # Get character evolution from Neo4j
        evolution = self.memory_service.query_character_evolution(
            character_name, project_id
        )

        if not evolution:
            return {
                "character": character_name,
                "drift_detected": False,
                "reason": "No historical data for character",
            }

        # Get character from story bible if available
        character_bible = await self._get_character_from_bible(
            character_name, project_id
        )

        # Analyze drift
        prompt = f"""Tu es un analyste de cohérence de personnage.

PERSONNAGE : {character_name}

DONNÉES HISTORIQUES (Neo4j) :
- Première apparition : chapitre {evolution.get('first_appearance', '?')}
- Dernière vue : chapitre {evolution.get('last_seen_chapter', '?')}
- Historique des statuts : {evolution.get('status_history', [])}

DÉFINITION DANS LA STORY BIBLE :
{json.dumps(character_bible, ensure_ascii=False, indent=2) if character_bible else "Non défini"}

COMPORTEMENT ACTUEL (Chapitre {chapter_index}) :
{current_behavior}

Analyse si le comportement actuel est cohérent avec l'arc établi du personnage.

Questions à considérer :
1. Le comportement correspond-il aux traits établis ?
2. Si le comportement diffère, y a-t-il un événement justificatif ?
3. L'évolution est-elle naturelle ou abrupte ?

Retourne JSON :
{{
    "drift_detected": true/false,
    "drift_type": "personality|motivation|values|relationships|null",
    "severity": 1-10,
    "analysis": "Explication détaillée",
    "established_traits": ["trait1", "trait2"],
    "conflicting_behavior": "Description du conflit si drift détecté",
    "justification_found": true/false,
    "justification_event": "Événement justificatif si trouvé",
    "suggested_resolution": "Comment résoudre le drift si nécessaire"
}}
"""

        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
            response_format={"type": "json_object"},
        )

        try:
            result = json.loads(response)
            result["character"] = character_name
            result["chapter_index"] = chapter_index
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse character drift analysis")
            return {
                "character": character_name,
                "drift_detected": False,
                "error": "Analysis parsing failed",
            }

    async def analyze_chapter_characters(
        self,
        chapter_text: str,
        project_id: str,
        chapter_index: int,
        known_characters: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Analyze all characters in a chapter for drift.

        Args:
            chapter_text: The chapter content.
            project_id: Project identifier.
            chapter_index: Current chapter number.
            known_characters: List of known character names.

        Returns:
            List of drift analyses per character.
        """
        if not self.enabled:
            return []

        results = []

        # Extract character behaviors from chapter
        behaviors = await self._extract_character_behaviors(
            chapter_text, known_characters
        )

        for char_name, behavior in behaviors.items():
            analysis = await self.analyze_character_consistency(
                character_name=char_name,
                current_behavior=behavior,
                project_id=project_id,
                chapter_index=chapter_index,
            )

            if analysis.get("drift_detected"):
                results.append(analysis)

        return results

    async def _get_character_from_bible(
        self,
        character_name: str,
        project_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get character definition from story bible."""
        # This would fetch from project metadata
        # Implementation depends on how story_bible is stored
        try:
            from sqlalchemy import select
            from app.db.session import AsyncSessionLocal
            from app.models.project import Project
            from uuid import UUID

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Project).where(Project.id == UUID(project_id))
                )
                project = result.scalar_one_or_none()

                if not project:
                    return None

                metadata = project.project_metadata or {}
                story_bible = metadata.get("story_bible", {})
                characters = story_bible.get("characters", [])

                for char in characters:
                    if char.get("name", "").lower() == character_name.lower():
                        return char

        except Exception as e:
            logger.error(f"Failed to get character from bible: {e}")

        return None

    async def _extract_character_behaviors(
        self,
        chapter_text: str,
        known_characters: List[str],
    ) -> Dict[str, str]:
        """Extract character behaviors from chapter text."""
        if not known_characters:
            return {}

        characters_list = ", ".join(known_characters)

        prompt = f"""Extrait les comportements et dialogues des personnages suivants dans ce chapitre :
Personnages à analyser : {characters_list}

Chapitre :
{chapter_text[:3000]}

Pour chaque personnage présent, décris :
- Ses actions principales
- Son attitude/ton
- Ses dialogues clés (paraphrasés)
- Ses décisions

Retourne JSON :
{{
    "personnages": {{
        "NomPersonnage": "Description du comportement dans ce chapitre"
    }}
}}

N'inclus que les personnages effectivement présents dans le chapitre.
"""

        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        try:
            result = json.loads(response)
            return result.get("personnages", {})
        except json.JSONDecodeError:
            return {}

    def calculate_drift_score(
        self,
        drift_analyses: List[Dict[str, Any]],
    ) -> float:
        """
        Calculate overall drift score from multiple character analyses.

        Args:
            drift_analyses: List of drift analysis results.

        Returns:
            Overall drift score (0-1, lower is better).
        """
        if not drift_analyses:
            return 0.0

        # Count drifts weighted by severity
        total_severity = 0
        drift_count = 0

        for analysis in drift_analyses:
            if analysis.get("drift_detected"):
                severity = analysis.get("severity", 5)
                total_severity += severity
                drift_count += 1

        if drift_count == 0:
            return 0.0

        # Normalize to 0-1 (higher severity = higher drift score)
        avg_severity = total_severity / drift_count
        return min(1.0, avg_severity / 10)
