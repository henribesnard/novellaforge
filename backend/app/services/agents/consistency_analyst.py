"""Consistency Analyst Agent - Narrative coherence analysis."""
from __future__ import annotations

import json
from typing import Dict, Any, Optional, List

from app.services.memory_service import MemoryService
from .base_agent import BaseAgent


class ConsistencyAnalyst(BaseAgent):
    """Agent specialized in narrative coherence analysis."""

    def __init__(self) -> None:
        super().__init__()
        self.memory_service = MemoryService()

    def _load_intentional_mysteries(
        self, context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Load intentional mysteries from project context."""
        if not context:
            return []

        metadata = context.get("metadata") or context.get("project", {}).get("metadata") or {}
        story_bible = metadata.get("story_bible") or {}
        return story_bible.get("intentional_mysteries", [])

    def _matches_mystery(
        self,
        contradiction: Dict[str, Any],
        mysteries: List[Dict[str, Any]],
    ) -> bool:
        """Check if a contradiction matches an intentional mystery."""
        if not mysteries:
            return False

        contradiction_desc = str(contradiction.get("description", "")).lower()
        contradiction_type = str(contradiction.get("type", "")).lower()

        for mystery in mysteries:
            mystery_desc = str(mystery.get("description", "")).lower()
            mystery_chars = [c.lower() for c in mystery.get("characters_involved", [])]

            # Check description overlap
            if mystery_desc and mystery_desc in contradiction_desc:
                return True

            # Check if contradiction involves mystery characters
            location = str(contradiction.get("location_in_text", "")).lower()
            if any(char in location or char in contradiction_desc for char in mystery_chars):
                # Additional check: is contradiction type compatible with mystery?
                mystery_type = mystery.get("contradiction_type", "")
                if mystery_type in ("lie", "unreliable_narrator", "hidden_info"):
                    return True

        return False

    @property
    def name(self) -> str:
        return "Analyste de Coherence"

    @property
    def description(self) -> str:
        return "Detecte et corrige les incoherences narratives, temporelles et factuelles"

    @property
    def system_prompt(self) -> str:
        return (
            "Tu es l'Analyste de Coherence de NovellaForge, expert en continuite narrative.\n\n"
            "Ton role est de:\n"
            "- Detecter les contradictions factuelles (personnages, lieux, evenements)\n"
            "- Verifier la coherence temporelle (timeline, chronologie)\n"
            "- Identifier les violations de regles du monde etablies\n"
            "- Reperer les incoherences de personnalite/motivation\n"
            "- Valider que les faits etablis ne sont pas contredits\n"
            "- Suggere des corrections precises et justifiees\n\n"
            "Tu es meticuleux, objectif et constructif. Tu hierarchises les problemes par gravite:\n"
            "- CRITICAL: Brise la logique fondamentale de l'histoire\n"
            "- HIGH: Contradiction majeure qui perturbe l'immersion\n"
            "- MEDIUM: Incoherence notable mais recuperable\n"
            "- LOW: Detail mineur a surveiller\n\n"
            "Tu fournis toujours des exemples concrets et des suggestions de correction."
        )

    async def execute(
        self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a coherence analysis task."""
        action = task_data.get("action", "analyze_chapter")

        if action == "analyze_chapter":
            return await self._analyze_chapter_coherence(task_data, context)
        if action == "analyze_project":
            return await self._analyze_project_coherence(task_data, context)
        if action == "suggest_fixes":
            return await self._suggest_coherence_fixes(task_data, context)

        return {
            "agent": self.name,
            "action": action,
            "error": "Action non reconnue",
            "success": False,
        }

    async def _analyze_chapter_coherence(
        self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze chapter coherence against established context."""
        chapter_text, memory_context, story_bible, previous_chapters = self._resolve_chapter_inputs(
            task_data, context
        )

        prompt = (
            "Analyse la coherence de ce chapitre par rapport au contexte etabli.\n\n"
            f"CHAPITRE A ANALYSER:\n{chapter_text}\n\n"
            f"MEMOIRE DE CONTINUITE:\n{memory_context}\n\n"
            "STORY BIBLE (Regles du monde et faits etablis):\n"
            f"{self._format_bible(story_bible)}\n\n"
            "EXTRAITS DES CHAPITRES PRECEDENTS:\n"
            f"{chr(10).join(previous_chapters[-5:])}\n\n"
            "Retourne un JSON avec la structure:\n"
            "{\n"
            '  "contradictions": [\n'
            '    {\n'
            '      "type": "factual/temporal/character/world_rule",\n'
            '      "severity": "critical/high/medium/low",\n'
            '      "description": "Description precise de la contradiction",\n'
            '      "location_in_text": "Citation du passage problematique",\n'
            '      "conflicts_with": "Reference a ce qui est contredit",\n'
            '      "established_in_chapter": number or "story_bible",\n'
            '      "suggested_fix": "Comment corriger sans casser l\'histoire"\n'
            "    }\n"
            "  ],\n"
            '  "timeline_issues": [\n'
            "    {\n"
            '      "issue": "Description du probleme temporel",\n'
            '      "severity": "critical/high/medium/low",\n'
            '      "suggested_fix": "Correction suggeree"\n'
            "    }\n"
            "  ],\n"
            '  "character_inconsistencies": [\n'
            "    {\n"
            '      "character": "Nom du personnage",\n'
            '      "issue": "Description de l\'incoherence",\n'
            '      "severity": "critical/high/medium/low",\n'
            '      "previous_state": "Etat/comportement etabli",\n'
            '      "current_state": "Etat/comportement dans ce chapitre",\n'
            '      "suggested_fix": "Comment reconcilier"\n'
            "    }\n"
            "  ],\n"
            '  "world_rule_violations": [\n'
            "    {\n"
            '      "rule": "Regle violee",\n'
            '      "violation": "Comment elle est violee",\n'
            '      "severity": "critical/high/medium/low",\n'
            '      "suggested_fix": "Correction ou justification a ajouter"\n'
            "    }\n"
            "  ],\n"
            '  "overall_coherence_score": 0-10,\n'
            '  "summary": "Resume de l\'analyse",\n'
            '  "blocking_issues": ["Liste des problemes qui DOIVENT etre corriges"]\n'
            "}\n\n"
            "Sois exhaustif et precis dans ton analyse."
        )

        response = await self._call_api(prompt, context, temperature=0.2)
        analysis = self._safe_json(response)

        # Filter contradictions that match intentional mysteries
        intentional_mysteries = self._load_intentional_mysteries(context)
        if intentional_mysteries:
            filtered_contradictions = []
            filtered_out = []

            for contradiction in analysis.get("contradictions", []):
                if self._matches_mystery(contradiction, intentional_mysteries):
                    filtered_out.append({
                        **contradiction,
                        "filtered_reason": "Matches intentional mystery",
                    })
                else:
                    filtered_contradictions.append(contradiction)

            analysis["contradictions"] = filtered_contradictions
            analysis["filtered_intentional"] = filtered_out

        return {
            "agent": self.name,
            "action": "analyze_chapter",
            "analysis": analysis,
            "success": True,
            "total_issues": self._count_issues(analysis),
            "critical_count": self._count_by_severity(analysis, "critical"),
        }

    async def _analyze_project_coherence(
        self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze project-wide coherence across chapters."""
        all_chapters, story_bible, continuity_memory = self._resolve_project_inputs(task_data, context)

        prompt = (
            "Analyse la coherence globale de ce roman sur tous les chapitres.\n\n"
            f"CHAPITRES DU ROMAN ({len(all_chapters)} chapitres):\n"
            f"{self._format_chapters_summary(all_chapters)}\n\n"
            "STORY BIBLE:\n"
            f"{self._format_bible(story_bible)}\n\n"
            "MEMOIRE DE CONTINUITE GLOBALE:\n"
            f"{self._format_memory(continuity_memory)}\n\n"
            "Retourne un JSON avec:\n"
            "{\n"
            '  "global_contradictions": [...],\n'
            '  "timeline_coherence": {\n'
            '    "score": 0-10,\n'
            '    "issues": [...],\n'
            '    "gaps": [...]\n'
            "  },\n"
            '  "character_arcs_consistency": [\n'
            "    {\n"
            '      "character": "...",\n'
            '      "arc_coherence_score": 0-10,\n'
            '      "issues": [...],\n'
            '      "evolution_summary": "..." \n'
            "    }\n"
            "  ],\n"
            '  "world_building_consistency": {\n'
            '    "score": 0-10,\n'
            '    "rule_violations": [...],\n'
            '    "unexplained_changes": [...]\n'
            "  },\n"
            '  "plot_threads": [\n'
            "    {\n"
            '      "thread": "...",\n'
            '      "status": "resolved/ongoing/abandoned",\n'
            '      "chapters": [1, 5, 8],\n'
            '      "coherence_score": 0-10,\n'
            '      "issues": [...]\n'
            "    }\n"
            "  ],\n"
            '  "overall_project_coherence_score": 0-10,\n'
            '  "critical_issues_to_fix": [...],\n'
            '  "recommendations": [...]\n'
            "}"
        )

        response = await self._call_api(prompt, context, temperature=0.3)
        analysis = self._safe_json(response)

        return {
            "agent": self.name,
            "action": "analyze_project",
            "global_analysis": analysis,
            "success": True,
        }

    async def _suggest_coherence_fixes(
        self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Suggest fixes for identified coherence issues."""
        issues = task_data.get("issues") or []
        chapter_text = task_data.get("chapter_text", "")
        context_data = task_data.get("context", "")
        issues_block = chr(10).join(
            f"- {issue.get('description', issue)}" if isinstance(issue, dict) else f"- {issue}"
            for issue in issues
        )

        prompt = (
            "Propose des corrections precises pour ces problemes de coherence.\n\n"
            f"TEXTE PROBLEMATIQUE:\n{chapter_text}\n\n"
            f"CONTEXTE:\n{context_data}\n\n"
            "PROBLEMES A CORRIGER:\n"
            f"{issues_block}\n\n"
            "Pour chaque probleme, propose:\n"
            "1. Une correction minimale (changer le moins possible)\n"
            "2. Une correction extensive (reecrire la section)\n"
            "3. Une explication narrative pour justifier l'incoherence (si possible)\n\n"
            "Retourne JSON:\n"
            "{\n"
            '  "fixes": [\n'
            "    {\n"
            '      "issue": "...",\n'
            '      "minimal_fix": {"type": "edit", "original": "...", "replacement": "..."},\n'
            '      "extensive_fix": {"type": "rewrite", "section": "...", "new_text": "..."},\n'
            '      "narrative_justification": {"type": "add_explanation", "text": "..."},\n'
            '      "recommendation": "minimal/extensive/justification"\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        response = await self._call_api(prompt, context, temperature=0.4)
        fixes = self._safe_json(response)

        return {
            "agent": self.name,
            "action": "suggest_fixes",
            "fixes": fixes,
            "success": True,
        }

    def _resolve_chapter_inputs(
        self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> tuple[str, str, Dict[str, Any], List[str]]:
        chapter_text = str(task_data.get("chapter_text") or "")
        memory_context = str(task_data.get("memory_context") or "")
        story_bible = task_data.get("story_bible") if isinstance(task_data.get("story_bible"), dict) else {}
        previous_chapters = task_data.get("previous_chapters")
        if not isinstance(previous_chapters, list):
            previous_chapters = []

        if context:
            if not memory_context:
                metadata = context.get("project", {}).get("metadata")
                if isinstance(metadata, dict):
                    memory_context = self.memory_service.build_context_block(metadata)
            if not story_bible:
                bible = context.get("story_bible")
                if isinstance(bible, dict):
                    story_bible = bible
            if not previous_chapters:
                docs = context.get("documents")
                if isinstance(docs, list):
                    previous_chapters = [
                        str(doc.get("content_preview") or "")
                        for doc in docs
                        if isinstance(doc, dict) and doc.get("content_preview")
                    ]

        return chapter_text, memory_context, story_bible, previous_chapters

    def _resolve_project_inputs(
        self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
        all_chapters = task_data.get("all_chapters")
        if not isinstance(all_chapters, list):
            all_chapters = []
        story_bible = task_data.get("story_bible") if isinstance(task_data.get("story_bible"), dict) else {}
        continuity_memory = task_data.get("continuity_memory")
        if not isinstance(continuity_memory, dict):
            continuity_memory = {}

        if context:
            if not all_chapters:
                docs = context.get("documents")
                if isinstance(docs, list):
                    all_chapters = []
                    for doc in docs:
                        if not isinstance(doc, dict):
                            continue
                        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
                        all_chapters.append(
                            {
                                "index": metadata.get("chapter_index") or doc.get("order_index"),
                                "title": doc.get("title") or "",
                                "summary": metadata.get("summary") or doc.get("content_preview") or "",
                            }
                        )
            if not story_bible:
                bible = context.get("story_bible")
                if isinstance(bible, dict):
                    story_bible = bible
            if not continuity_memory:
                metadata = context.get("project", {}).get("metadata")
                if isinstance(metadata, dict):
                    continuity_memory = metadata.get("continuity") or {}

        return all_chapters, story_bible, continuity_memory

    def _safe_json(self, text: Any) -> Dict[str, Any]:
        if isinstance(text, dict):
            return text
        try:
            payload = json.loads(text or "")
            if isinstance(payload, dict):
                return payload
        except (json.JSONDecodeError, TypeError):
            pass
        return {}

    def _format_bible(self, bible: Dict[str, Any]) -> str:
        if not isinstance(bible, dict) or not bible:
            return "Aucune story bible fournie."
        parts: List[str] = []
        rules = bible.get("world_rules")
        if isinstance(rules, list) and rules:
            parts.append("REGLES DU MONDE:")
            for rule in rules[:10]:
                if isinstance(rule, dict):
                    rule_text = rule.get("rule") or ""
                    if rule_text:
                        parts.append(f"- {rule_text}")
        timeline = bible.get("timeline")
        if isinstance(timeline, list) and timeline:
            parts.append("TIMELINE:")
            for event in timeline[:10]:
                if isinstance(event, dict):
                    label = event.get("event") or ""
                    chapter_index = event.get("chapter_index")
                    if label:
                        suffix = f" (ch.{chapter_index})" if chapter_index else ""
                        parts.append(f"- {label}{suffix}")
        facts = bible.get("established_facts")
        if isinstance(facts, list) and facts:
            parts.append("FAITS ETABLIS:")
            for fact in facts[:10]:
                if isinstance(fact, dict):
                    fact_text = fact.get("fact") or ""
                    if fact_text:
                        parts.append(f"- {fact_text}")
        return "\n".join(parts)

    def _format_chapters_summary(self, chapters: List[Dict[str, Any]]) -> str:
        if not chapters:
            return "Aucun chapitre fourni."
        return "\n\n".join(
            [
                f"CHAPITRE {ch.get('index', '?')}: {ch.get('title', '')}\n{ch.get('summary', '')}"
                for ch in chapters
                if isinstance(ch, dict)
            ]
        )

    def _format_memory(self, continuity_memory: Dict[str, Any]) -> str:
        if not isinstance(continuity_memory, dict) or not continuity_memory:
            return "Aucune memoire de continuite."
        characters = continuity_memory.get("characters") or []
        locations = continuity_memory.get("locations") or []
        relations = continuity_memory.get("relations") or []
        events = continuity_memory.get("events") or []
        return (
            f"Characters: {len(characters)}\n"
            f"Locations: {len(locations)}\n"
            f"Relations: {len(relations)}\n"
            f"Events: {len(events)}"
        )

    def _count_issues(self, analysis: Dict[str, Any]) -> int:
        return sum(
            [
                len(analysis.get("contradictions", []) or []),
                len(analysis.get("timeline_issues", []) or []),
                len(analysis.get("character_inconsistencies", []) or []),
                len(analysis.get("world_rule_violations", []) or []),
            ]
        )

    def _count_by_severity(self, analysis: Dict[str, Any], severity: str) -> int:
        count = 0
        target = str(severity).lower()
        for key in [
            "contradictions",
            "timeline_issues",
            "character_inconsistencies",
            "world_rule_violations",
        ]:
            items = analysis.get(key, []) or []
            for item in items:
                if isinstance(item, dict) and str(item.get("severity") or "").lower() == target:
                    count += 1
        return count
