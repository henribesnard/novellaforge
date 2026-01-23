"""POV Validator - Validate point of view consistency."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.llm_client import DeepSeekClient

logger = logging.getLogger(__name__)


class POVValidator:
    """
    Validates point of view consistency in narrative.

    Detects violations like:
    - Accessing thoughts of non-POV characters in limited POV
    - Knowing information the POV character couldn't know
    - Accidental omniscience in limited/first-person narratives
    """

    POV_TYPES = {
        "first_person": "Narrateur = personnage principal, 'je'",
        "limited": "Troisième personne, accès aux pensées d'un seul personnage",
        "omniscient": "Narrateur omniscient, accès à toutes les pensées",
        "objective": "Narrateur externe, pas d'accès aux pensées",
    }

    def __init__(self) -> None:
        self.llm_client = DeepSeekClient()
        self.enabled = settings.POV_VALIDATOR_ENABLED
        self.default_type = settings.POV_DEFAULT_TYPE

    async def validate_pov(
        self,
        chapter_text: str,
        pov_character: str,
        pov_type: Optional[str] = None,
        known_information: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Validate POV consistency in a chapter.

        Args:
            chapter_text: The chapter content.
            pov_character: The POV character's name.
            pov_type: Type of POV (first_person, limited, omniscient, objective).
            known_information: List of facts the POV character knows.

        Returns:
            Validation result with any violations found.
        """
        if not self.enabled:
            return {
                "pov_character": pov_character,
                "pov_type": pov_type or self.default_type,
                "violations": [],
                "valid": True,
                "note": "POV validation disabled",
            }

        if pov_type is None:
            pov_type = self.default_type

        if pov_type == "omniscient":
            return {
                "pov_character": pov_character,
                "pov_type": pov_type,
                "violations": [],
                "valid": True,
                "note": "POV omniscient allows access to all thoughts",
            }

        known_info_text = ""
        if known_information:
            known_info_text = "\n".join([f"- {info}" for info in known_information])

        prompt = f"""Tu es un expert en narration et point de vue (POV).

CONFIGURATION DU POV :
- Personnage POV : {pov_character}
- Type de POV : {pov_type} ({self.POV_TYPES.get(pov_type, '')})

INFORMATIONS CONNUES PAR {pov_character} :
{known_info_text if known_info_text else "Non spécifié"}

CHAPITRE À ANALYSER :
{chapter_text[:4000]}

Détecte les violations de POV :

1. PENSÉES INTERDITES : En POV {pov_type}, le narrateur ne devrait pas accéder aux pensées/émotions internes des personnages autres que {pov_character}.

2. INFORMATIONS IMPOSSIBLES : Le narrateur ne devrait pas révéler des informations que {pov_character} ne peut pas connaître (événements en son absence, secrets non révélés, etc.).

3. OMNISCIENCE ACCIDENTELLE : Passages où le narrateur semble tout savoir alors que le POV est {pov_type}.

Retourne JSON :
{{
    "violations": [
        {{
            "type": "forbidden_thoughts|impossible_knowledge|accidental_omniscience",
            "severity": "high|medium|low",
            "location": "Citation du passage problématique",
            "character_involved": "Personnage dont on accède aux pensées/infos",
            "explanation": "Pourquoi c'est une violation",
            "suggested_fix": "Comment corriger"
        }}
    ],
    "valid": true/false,
    "overall_assessment": "Évaluation globale de la cohérence POV"
}}
"""

        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )

        try:
            result = json.loads(response)
            result["pov_character"] = pov_character
            result["pov_type"] = pov_type
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse POV validation response")
            return {
                "pov_character": pov_character,
                "pov_type": pov_type,
                "violations": [],
                "valid": True,
                "error": "Analysis failed",
            }

    async def detect_pov_from_text(
        self,
        chapter_text: str,
    ) -> Dict[str, Any]:
        """
        Auto-detect POV type and character from text.

        Args:
            chapter_text: The chapter content.

        Returns:
            Detected POV configuration.
        """
        if not self.enabled:
            return {
                "pov_type": "unknown",
                "pov_character": None,
                "confidence": 0.0,
                "note": "POV validation disabled",
            }

        prompt = f"""Analyse ce texte et détermine le point de vue narratif :

{chapter_text[:2000]}

Retourne JSON :
{{
    "pov_type": "first_person|limited|omniscient|objective",
    "pov_character": "Nom du personnage POV (si applicable)",
    "confidence": 0.0-1.0,
    "indicators": ["Indices ayant permis la détection"]
}}
"""

        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "json_object"},
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "pov_type": "unknown",
                "pov_character": None,
                "confidence": 0.0,
            }

    async def validate_chapter_with_auto_detect(
        self,
        chapter_text: str,
        known_information: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Auto-detect POV and validate in one step.

        Args:
            chapter_text: The chapter content.
            known_information: Optional known information.

        Returns:
            Combined detection and validation result.
        """
        # First, detect POV
        detection = await self.detect_pov_from_text(chapter_text)

        pov_type = detection.get("pov_type", self.default_type)
        pov_character = detection.get("pov_character")

        if not pov_character or pov_type == "unknown":
            return {
                "detection": detection,
                "validation": {
                    "valid": True,
                    "note": "Could not detect POV, skipping validation",
                },
            }

        # Then validate
        validation = await self.validate_pov(
            chapter_text=chapter_text,
            pov_character=pov_character,
            pov_type=pov_type,
            known_information=known_information,
        )

        return {
            "detection": detection,
            "validation": validation,
        }

    def get_pov_guidelines(self, pov_type: str) -> Dict[str, Any]:
        """
        Get writing guidelines for a specific POV type.

        Args:
            pov_type: The POV type.

        Returns:
            Guidelines for the POV type.
        """
        guidelines = {
            "first_person": {
                "allowed": [
                    "Pensées et émotions du narrateur ('je')",
                    "Observations et déductions du narrateur",
                    "Dialogues entendus par le narrateur",
                ],
                "forbidden": [
                    "Pensées des autres personnages",
                    "Événements en l'absence du narrateur",
                    "Informations que le narrateur ne peut pas connaître",
                ],
                "tips": [
                    "Utilisez des verbes comme 'semblait', 'paraissait' pour les autres",
                    "Limitez les informations à ce que le narrateur peut observer",
                ],
            },
            "limited": {
                "allowed": [
                    "Pensées et émotions du personnage POV",
                    "Observations du personnage POV",
                    "Ce que le personnage POV peut déduire",
                ],
                "forbidden": [
                    "Pensées des autres personnages (sauf déductions)",
                    "Événements hors de la présence du personnage POV",
                    "Informations secrètes non révélées au personnage POV",
                ],
                "tips": [
                    "Restez 'collé' au personnage POV",
                    "Utilisez le discours indirect libre pour ses pensées",
                ],
            },
            "omniscient": {
                "allowed": [
                    "Toutes les pensées de tous les personnages",
                    "Informations passées, présentes, futures",
                    "Commentaires du narrateur sur l'action",
                ],
                "forbidden": [],
                "tips": [
                    "Évitez les changements de focus trop fréquents",
                    "Maintenez une voix narrative cohérente",
                ],
            },
            "objective": {
                "allowed": [
                    "Actions observables",
                    "Dialogues",
                    "Descriptions physiques",
                ],
                "forbidden": [
                    "Toutes les pensées internes",
                    "Émotions non exprimées",
                    "Motivations non verbalisées",
                ],
                "tips": [
                    "Montrez les émotions par les actions et gestes",
                    "Style 'caméra' neutre",
                ],
            },
        }

        return guidelines.get(pov_type, {})
