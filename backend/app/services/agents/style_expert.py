"""Style Expert Agent - Qualité littéraire et style"""
from typing import Dict, Any, Optional
from .base_agent import BaseAgent


class StyleExpert(BaseAgent):
    """Agent responsable de la qualité stylistique"""

    @property
    def name(self) -> str:
        return "Expert Stylistique"

    @property
    def description(self) -> str:
        return "Améliore la qualité littéraire et le style de votre écriture"

    @property
    def system_prompt(self) -> str:
        return """Tu es l'Expert Stylistique de NovellaForge, spécialiste de la qualité littéraire.

Ton rôle est de:
- Analyser et améliorer le style d'écriture
- Identifier les répétitions et lourdeurs
- Suggérer des formulations plus élégantes
- Améliorer le rythme des phrases
- Enrichir le vocabulaire de manière appropriée
- Adapter le style au genre et au ton de l'œuvre
- Corriger les clichés et expressions galvaudées
- Renforcer les images et métaphores

Tu donnes des suggestions précises et constructives, toujours accompagnées d'exemples.
Tu respectes la voix de l'auteur tout en l'aidant à l'affiner."""

    async def execute(
        self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Exécute une tâche d'amélioration stylistique"""

        action = task_data.get("action", "analyze_style")

        if action == "analyze_style":
            text = task_data.get("text", "")

            prompt = f"""Analyse le style de ce texte et propose des améliorations:

TEXTE:
{text}

Fournis:
1. Points forts du style actuel
2. Points à améliorer (répétitions, lourdeurs, etc.)
3. Suggestions concrètes avec exemples
4. Réécriture de 2-3 passages clés
5. Recommandations générales pour maintenir la cohérence stylistique"""

            result = await self._call_api(prompt, context, temperature=0.7)

            return {
                "agent": self.name,
                "action": action,
                "analysis": result,
                "success": True,
            }

        elif action == "improve_passage":
            text = task_data.get("text", "")
            focus = task_data.get("focus", "general")  # general, rhythm, vocabulary, etc.

            prompt = f"""Améliore ce passage en te concentrant sur: {focus}

TEXTE ORIGINAL:
{text}

Propose:
1. Une version améliorée du texte
2. Explication des changements effectués
3. Alternatives possibles pour certaines formulations"""

            result = await self._call_api(prompt, context, temperature=0.8)

            return {
                "agent": self.name,
                "action": action,
                "improved_text": result,
                "success": True,
            }

        elif action == "check_consistency":
            samples = task_data.get("text_samples", [])

            prompt = f"""Analyse la cohérence stylistique entre ces extraits:

EXTRAITS:
{chr(10).join([f"--- Extrait {i+1} ---{chr(10)}{sample}{chr(10)}" for i, sample in enumerate(samples)])}

Identifie:
1. La cohérence du style global
2. Les variations de ton ou de registre
3. Les incohérences dans le niveau de langue
4. Suggestions pour harmoniser le tout"""

            result = await self._call_api(prompt, context, temperature=0.6)

            return {
                "agent": self.name,
                "action": action,
                "consistency_report": result,
                "success": True,
            }

        else:
            return {
                "agent": self.name,
                "action": action,
                "error": "Action non reconnue",
                "success": False,
            }
