"""Narrative Architect Agent - Structure globale du récit"""
from typing import Dict, Any, Optional
from .base_agent import BaseAgent


class NarrativeArchitect(BaseAgent):
    """Agent responsable de la structure narrative globale"""

    @property
    def name(self) -> str:
        return "Architecte Narratif"

    @property
    def description(self) -> str:
        return "Analyse et structure la narration globale de votre histoire"

    @property
    def system_prompt(self) -> str:
        return """Tu es l'Architecte Narratif de NovellaForge, spécialisé dans la structure globale des récits.

Ton rôle est de:
- Analyser la structure narrative d'une histoire
- Proposer des améliorations structurelles (3 actes, voyage du héros, etc.)
- Identifier les problèmes de rythme et de progression
- Suggérer des points de retournement et climax
- Vérifier l'équilibre entre les différentes parties du récit
- Assurer la cohérence de l'arc narratif global

Tu travailles de manière méthodique et fournis des analyses détaillées avec des exemples concrets.
Tes recommandations sont toujours accompagnées d'explications sur pourquoi elles fonctionneraient."""

    async def execute(
        self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Exécute une analyse de structure narrative

        Args:
            task_data: Doit contenir 'action' et les données pertinentes
            context: Contexte du projet (optionnel)

        Returns:
            Résultat de l'analyse
        """
        action = task_data.get("action", "analyze_structure")

        if action == "analyze_structure":
            # Analyser la structure globale
            story_outline = task_data.get("story_outline", "")
            current_structure = task_data.get("current_structure", "")

            prompt = f"""Analyse la structure narrative suivante et fournis des recommandations détaillées:

RÉSUMÉ DE L'HISTOIRE:
{story_outline}

STRUCTURE ACTUELLE:
{current_structure}

Fournis:
1. Une analyse de la structure actuelle
2. Les forces et faiblesses identifiées
3. Des suggestions concrètes d'amélioration
4. Un plan de structure recommandé avec justifications"""

            result = await self._call_api(prompt, context, temperature=0.7)

            return {
                "agent": self.name,
                "action": action,
                "analysis": result,
                "success": True,
            }

        elif action == "suggest_structure":
            # Suggérer une structure adaptée
            genre = task_data.get("genre", "")
            story_concept = task_data.get("story_concept", "")

            prompt = f"""Sur la base du concept suivant, propose une structure narrative optimale:

GENRE: {genre}
CONCEPT: {story_concept}

Propose:
1. Le modèle de structure le plus adapté (3 actes, voyage du héros, etc.)
2. La répartition des actes/parties
3. Les points clés et retournements suggérés
4. L'arc émotionnel global"""

            result = await self._call_api(prompt, context, temperature=0.8)

            return {
                "agent": self.name,
                "action": action,
                "suggestions": result,
                "success": True,
            }

        else:
            return {
                "agent": self.name,
                "action": action,
                "error": "Action non reconnue",
                "success": False,
            }
