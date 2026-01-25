"""Chekhov's Gun Tracker - Track narrative elements awaiting resolution."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.config import settings
from app.services.llm_client import DeepSeekClient
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class ChekhovGun:
    """Represents a narrative element awaiting resolution."""
    
    def __init__(
        self,
        element: str,
        element_type: str,
        expectation: str,
        introduced_chapter: int,
        urgency: int = 5,
        resolved: bool = False,
        resolved_chapter: Optional[int] = None,
        hints_dropped: Optional[List[Dict[str, Any]]] = None,
    ):
        self.element = element
        self.element_type = element_type  # object, skill, threat, promise, foreshadowing
        self.expectation = expectation
        self.introduced_chapter = introduced_chapter
        self.urgency = urgency  # 1-10
        self.resolved = resolved
        self.resolved_chapter = resolved_chapter
        self.hints_dropped = hints_dropped or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "element": self.element,
            "element_type": self.element_type,
            "expectation": self.expectation,
            "introduced_chapter": self.introduced_chapter,
            "urgency": self.urgency,
            "resolved": self.resolved,
            "resolved_chapter": self.resolved_chapter,
            "hints_dropped": self.hints_dropped,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChekhovGun":
        return cls(
            element=data.get("element", ""),
            element_type=data.get("element_type", "object"),
            expectation=data.get("expectation", ""),
            introduced_chapter=data.get("introduced_chapter", 1),
            urgency=data.get("urgency", 5),
            resolved=data.get("resolved", False),
            resolved_chapter=data.get("resolved_chapter"),
            hints_dropped=data.get("hints_dropped", []),
        )


class ChekhovTracker:
    """Track and manage Chekhov's Guns in a narrative."""
    
    def __init__(
        self,
        llm_client: Optional[DeepSeekClient] = None,
        memory_service: Optional[MemoryService] = None,
    ) -> None:
        self.llm_client = llm_client or DeepSeekClient()
        self.memory_service = memory_service or MemoryService()
    
    async def extract_guns(
        self,
        chapter_text: str,
        chapter_index: int,
        existing_guns: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Extract new Chekhov's Guns from chapter text.
        
        Args:
            chapter_text: The chapter content to analyze.
            chapter_index: Current chapter number.
            existing_guns: List of already tracked guns.
            
        Returns:
            Dict with new_guns and resolved_guns.
        """
        existing_guns = existing_guns or []
        existing_summary = self._summarize_existing_guns(existing_guns)
        
        prompt = f"""Tu es un analyste narratif expert. Analyse ce chapitre pour identifier :

1. NOUVEAUX ÉLÉMENTS (Chekhov's Guns) qui créent une attente chez le lecteur :
   - Objets significatifs (armes, clés, lettres, artefacts)
   - Compétences ou secrets révélés mais non utilisés
   - Menaces évoquées mais non concrétisées
   - Promesses faites par des personnages
   - Foreshadowing explicite ou implicite
   - Questions posées sans réponse

2. RÉSOLUTIONS d'éléments précédemment introduits :
   - Un objet utilisé
   - Une compétence mise en œuvre
   - Une menace concrétisée
   - Une promesse tenue ou brisée
   - Une question répondue

ÉLÉMENTS DÉJÀ TRACKÉS :
{existing_summary}

CHAPITRE {chapter_index} :
{chapter_text[:4000]}

Retourne un JSON strict :
{{
    "new_guns": [
        {{
            "element": "Description courte de l'élément",
            "element_type": "object|skill|threat|promise|foreshadowing|question",
            "expectation": "Ce que le lecteur attend comme résolution",
            "urgency": 1-10,
            "justification": "Pourquoi cet élément crée une attente"
        }}
    ],
    "resolved_guns": [
        {{
            "element": "L'élément résolu (doit matcher un élément existant)",
            "resolution_type": "fulfilled|subverted|abandoned",
            "resolution_detail": "Comment l'élément a été résolu"
        }}
    ],
    "hints_dropped": [
        {{
            "for_element": "L'élément concerné",
            "hint": "Description de l'indice",
            "chapter": {chapter_index}
        }}
    ]
}}
"""
        
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
        
        return self._parse_extraction_response(response, chapter_index)
    
    async def check_unresolved(
        self,
        guns: List[Dict[str, Any]],
        current_chapter: int,
        max_chapters_unresolved: int = 15,
        urgency_threshold: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Check for guns that have been unresolved too long.
        
        Args:
            guns: List of tracked guns.
            current_chapter: Current chapter index.
            max_chapters_unresolved: Max chapters before alerting.
            urgency_threshold: Min urgency to trigger alert.
            
        Returns:
            List of overdue guns with alerts.
        """
        alerts = []
        
        for gun_data in guns:
            gun = ChekhovGun.from_dict(gun_data)
            
            if gun.resolved:
                continue
            
            chapters_waiting = current_chapter - gun.introduced_chapter
            
            # High urgency guns need faster resolution
            adjusted_max = max_chapters_unresolved
            if gun.urgency >= 8:
                adjusted_max = max(5, max_chapters_unresolved // 2)
            elif gun.urgency >= 6:
                adjusted_max = max(8, int(max_chapters_unresolved * 0.7))
            
            if chapters_waiting > adjusted_max and gun.urgency >= urgency_threshold:
                alerts.append({
                    "element": gun.element,
                    "element_type": gun.element_type,
                    "expectation": gun.expectation,
                    "introduced_chapter": gun.introduced_chapter,
                    "chapters_waiting": chapters_waiting,
                    "urgency": gun.urgency,
                    "severity": "high" if gun.urgency >= 8 else "medium",
                    "recommendation": self._generate_resolution_recommendation(gun),
                })
        
        return alerts
    
    async def suggest_resolutions(
        self,
        unresolved_guns: List[Dict[str, Any]],
        story_context: str,
        upcoming_chapters: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Suggest ways to resolve pending narrative elements.
        
        Args:
            unresolved_guns: List of unresolved guns.
            story_context: Current story context/summary.
            upcoming_chapters: How many chapters to plan for.
            
        Returns:
            List of resolution suggestions.
        """
        if not unresolved_guns:
            return []
        
        guns_summary = "\n".join([
            f"- {g['element']} ({g['element_type']}): {g['expectation']} "
            f"[Urgence: {g['urgency']}/10, Attente: {g.get('chapters_waiting', '?')} chapitres]"
            for g in unresolved_guns
        ])
        
        prompt = f"""Tu es un consultant en structure narrative.

ÉLÉMENTS NON RÉSOLUS :
{guns_summary}

CONTEXTE DE L'HISTOIRE :
{story_context[:2000]}

Pour chaque élément, propose une résolution créative pour les {upcoming_chapters} prochains chapitres.
Types de résolution possibles :
- fulfilled: L'attente est satisfaite comme prévu
- subverted: L'attente est détournée de manière intéressante
- escalated: L'élément devient plus important/urgent

Retourne JSON :
{{
    "suggestions": [
        {{
            "element": "...",
            "resolution_type": "fulfilled|subverted|escalated",
            "suggested_chapter": N,
            "resolution_idea": "Description de comment résoudre",
            "integration_hint": "Comment l'intégrer naturellement"
        }}
    ]
}}
"""
        
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        
        try:
            result = json.loads(response)
            return result.get("suggestions", [])
        except json.JSONDecodeError:
            logger.error("Failed to parse resolution suggestions")
            return []
    
    def update_gun_status(
        self,
        guns: List[Dict[str, Any]],
        resolved_guns: List[Dict[str, Any]],
        hints: List[Dict[str, Any]],
        chapter_index: int,
    ) -> List[Dict[str, Any]]:
        """
        Update gun statuses based on chapter analysis.
        
        Args:
            guns: Current list of guns.
            resolved_guns: Guns identified as resolved.
            hints: Hints dropped in this chapter.
            chapter_index: Current chapter.
            
        Returns:
            Updated list of guns.
        """
        updated_guns = []
        
        for gun_data in guns:
            gun = ChekhovGun.from_dict(gun_data)
            
            # Check if resolved
            for resolved in resolved_guns:
                if self._elements_match(gun.element, resolved.get("element", "")):
                    gun.resolved = True
                    gun.resolved_chapter = chapter_index
                    break
            
            # Add hints
            for hint in hints:
                if self._elements_match(gun.element, hint.get("for_element", "")):
                    gun.hints_dropped.append({
                        "hint": hint.get("hint", ""),
                        "chapter": hint.get("chapter", chapter_index),
                    })
            
            updated_guns.append(gun.to_dict())
        
        return updated_guns
    
    def _summarize_existing_guns(self, guns: List[Dict[str, Any]]) -> str:
        if not guns:
            return "Aucun élément tracké."
        
        lines = []
        for g in guns:
            status = "✅ Résolu" if g.get("resolved") else "⏳ En attente"
            lines.append(
                f"- [{status}] {g.get('element')} ({g.get('element_type')}): "
                f"{g.get('expectation')} [Ch.{g.get('introduced_chapter')}]"
            )
        return "\n".join(lines)
    
    def _parse_extraction_response(
        self, response: str, chapter_index: int
    ) -> Dict[str, Any]:
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            logger.error("Failed to parse Chekhov extraction response")
            return {"new_guns": [], "resolved_guns": [], "hints_dropped": []}
        
        new_guns = []
        for gun in data.get("new_guns", []):
            new_guns.append({
                "element": gun.get("element", ""),
                "element_type": gun.get("element_type", "object"),
                "expectation": gun.get("expectation", ""),
                "introduced_chapter": chapter_index,
                "urgency": min(10, max(1, gun.get("urgency", 5))),
                "resolved": False,
                "resolved_chapter": None,
                "hints_dropped": [],
            })
        
        return {
            "new_guns": new_guns,
            "resolved_guns": data.get("resolved_guns", []),
            "hints_dropped": data.get("hints_dropped", []),
        }
    
    def _elements_match(self, element1: str, element2: str) -> bool:
        """Check if two element descriptions refer to the same thing."""
        e1 = element1.lower().strip()
        e2 = element2.lower().strip()
        
        if e1 == e2:
            return True
        
        # Check for significant word overlap
        words1 = set(e1.split())
        words2 = set(e2.split())
        common = words1 & words2
        
        # If >50% words match, consider same element
        if len(common) >= min(len(words1), len(words2)) * 0.5:
            return True
        
        return False
    
    def _generate_resolution_recommendation(self, gun: ChekhovGun) -> str:
        """Generate a recommendation for resolving a gun."""
        recommendations = {
            "object": f"L'objet '{gun.element}' devrait être utilisé ou sa pertinence expliquée.",
            "skill": f"La compétence mentionnée devrait être mise en pratique.",
            "threat": f"La menace devrait se concrétiser ou être neutralisée.",
            "promise": f"La promesse devrait être tenue, brisée, ou son statut clarifié.",
            "foreshadowing": f"L'élément de préfiguration devrait se réaliser.",
            "question": f"La question soulevée mérite une réponse.",
        }
        return recommendations.get(gun.element_type, "Cet élément attend une résolution.")
