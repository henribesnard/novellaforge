"""Dialogue Master Agent - Authenticité des dialogues"""
from typing import Dict, Any, Optional
from .base_agent import BaseAgent


class DialogueMaster(BaseAgent):
    """Agent responsable de la qualité et authenticité des dialogues"""

    @property
    def name(self) -> str:
        return "Maître des Dialogues"

    @property
    def description(self) -> str:
        return "Crée et améliore l'authenticité de vos dialogues"

    @property
    def system_prompt(self) -> str:
        return """Tu es le Maître des Dialogues de NovellaForge, expert en écriture de dialogues authentiques.

Ton rôle est de:
- Créer des dialogues naturels et crédibles
- Adapter le langage à chaque personnage (voix unique)
- Équilibrer dialogue et narration
- Utiliser le sous-texte efficacement
- Éviter les dialogues explicatifs ou artificiels
- Créer du conflit et de la tension dans les échanges
- Rythmer les dialogues pour maintenir l'intérêt
- Utiliser les silences et non-dits

Tu crées des dialogues qui révèlent les personnages et font avancer l'intrigue.
Chaque personnage a une voix distincte et authentique."""

    async def execute(
        self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Exécute une tâche sur les dialogues"""

        action = task_data.get("action", "create_dialogue")

        if action == "create_dialogue":
            characters = task_data.get("characters", [])
            situation = task_data.get("situation", "")
            emotional_tone = task_data.get("emotional_tone", "neutre")

            prompt = f"""Crée un dialogue authentique pour cette scène:

PERSONNAGES: {', '.join(characters)}
SITUATION: {situation}
TON ÉMOTIONNEL: {emotional_tone}

Crée un dialogue qui:
1. Révèle les personnalités et relations
2. Fait avancer l'intrigue ou développe les personnages
3. Sonne naturel et crédible
4. Utilise le sous-texte (ce qui n'est pas dit est important)
5. Évite les expositions trop directes

Format: Alterne dialogue et indications narratives minimales."""

            result = await self._call_api(prompt, context, temperature=0.9)

            return {
                "agent": self.name,
                "action": action,
                "dialogue": result,
                "success": True,
            }

        elif action == "improve_dialogue":
            original_dialogue = task_data.get("dialogue", "")
            issues = task_data.get("issues", "général")

            prompt = f"""Améliore ce dialogue (problèmes identifiés: {issues}):

DIALOGUE ORIGINAL:
{original_dialogue}

Propose:
1. Une version améliorée du dialogue
2. Explication des changements (pourquoi c'est mieux)
3. Notes sur la voix de chaque personnage"""

            result = await self._call_api(prompt, context, temperature=0.8)

            return {
                "agent": self.name,
                "action": action,
                "improved_dialogue": result,
                "success": True,
            }

        elif action == "analyze_voice":
            character_name = task_data.get("character_name", "")
            dialogue_samples = task_data.get("dialogue_samples", [])

            prompt = f"""Analyse la voix de {character_name} à travers ces dialogues:

ÉCHANTILLONS:
{chr(10).join([f"- {sample}" for sample in dialogue_samples])}

Identifie:
1. Les caractéristiques de sa façon de parler
2. La cohérence de sa voix
3. Ce qui rend sa voix unique
4. Suggestions pour renforcer sa voix distinctive"""

            result = await self._call_api(prompt, context, temperature=0.6)

            return {
                "agent": self.name,
                "action": action,
                "voice_analysis": result,
                "success": True,
            }

        else:
            return {
                "agent": self.name,
                "action": action,
                "error": "Action non reconnue",
                "success": False,
            }
