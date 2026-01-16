"""Character Manager Agent - Gestion des personnages"""
from typing import Dict, Any, Optional
from .base_agent import BaseAgent


class CharacterManager(BaseAgent):
    """Agent responsable de la cohérence et du développement des personnages"""

    @property
    def name(self) -> str:
        return "Gestionnaire de Personnages"

    @property
    def description(self) -> str:
        return "Développe et maintient la cohérence de vos personnages"

    @property
    def system_prompt(self) -> str:
        return """Tu es le Gestionnaire de Personnages de NovellaForge, expert en création et développement de personnages.

Ton rôle est de:
- Créer des personnages complexes et crédibles
- Assurer la cohérence des personnages tout au long du récit
- Développer des arcs de personnages significatifs
- Créer des relations et dynamiques interpersonnelles
- Identifier les incohérences dans le comportement des personnages
- Suggérer des traits de personnalité, motivations et conflits internes
- Veiller à la diversité et l'originalité des personnages

Tu crées des personnages tridimensionnels avec des forces, faiblesses, désirs et peurs.
Tes suggestions sont toujours en cohérence avec le genre et le ton de l'histoire."""

    async def execute(
        self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Exécute une tâche de gestion de personnages"""

        action = task_data.get("action", "create_character")

        if action == "create_character":
            role = task_data.get("role", "supporting")
            context_story = task_data.get("story_context", "")

            prompt = f"""Crée un personnage détaillé pour cette histoire:

CONTEXTE DE L'HISTOIRE: {context_story}
RÔLE DU PERSONNAGE: {role}

Fournis:
1. Nom et âge
2. Description physique
3. Traits de personnalité (5-7 traits principaux)
4. Backstory (histoire personnelle)
5. Motivations et objectifs
6. Peurs et faiblesses
7. Arc de transformation potentiel
8. Relations avec les autres personnages
9. Particularités/Quirks qui le rendent mémorable"""

            result = await self._call_api(prompt, context, temperature=0.9)

            return {
                "agent": self.name,
                "action": action,
                "character": result,
                "success": True,
            }

        elif action == "analyze_consistency":
            character_name = task_data.get("character_name", "")
            character_profile = task_data.get("character_profile", "")
            scenes = task_data.get("scenes", [])

            prompt = f"""Analyse la cohérence de ce personnage à travers les scènes:

PERSONNAGE: {character_name}
PROFIL: {character_profile}

SCÈNES À ANALYSER:
{chr(10).join([f"- {scene}" for scene in scenes])}

Identifie:
1. Les incohérences de comportement
2. Les contradictions avec le profil établi
3. L'évolution du personnage (est-elle logique?)
4. Les opportunités manquées de développement
5. Suggestions pour améliorer la cohérence"""

            result = await self._call_api(prompt, context, temperature=0.6)

            return {
                "agent": self.name,
                "action": action,
                "analysis": result,
                "success": True,
            }

        elif action == "develop_relationship":
            char1 = task_data.get("character_1", "")
            char2 = task_data.get("character_2", "")

            prompt = f"""Développe la relation entre ces deux personnages:

PERSONNAGE 1: {char1}
PERSONNAGE 2: {char2}

Propose:
1. Nature de leur relation (alliés, rivaux, etc.)
2. Dynamique entre eux
3. Conflits potentiels
4. Moments clés de leur relation
5. Comment leur relation évolue au cours de l'histoire"""

            result = await self._call_api(prompt, context, temperature=0.8)

            return {
                "agent": self.name,
                "action": action,
                "relationship": result,
                "success": True,
            }

        else:
            return {
                "agent": self.name,
                "action": action,
                "error": "Action non reconnue",
                "success": False,
            }
