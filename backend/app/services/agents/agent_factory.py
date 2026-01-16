"""Agent Factory - Crée et gère les agents IA"""
from typing import Dict, Type
from .base_agent import BaseAgent
from .narrative_architect import NarrativeArchitect
from .character_manager import CharacterManager
from .style_expert import StyleExpert
from .dialogue_master import DialogueMaster


class AgentFactory:
    """Factory pour créer et gérer les agents NovellaForge"""

    _agents: Dict[str, Type[BaseAgent]] = {
        "narrative_architect": NarrativeArchitect,
        "character_manager": CharacterManager,
        "style_expert": StyleExpert,
        "dialogue_master": DialogueMaster,
        # TODO: Ajouter les 7 autres agents
        # "scene_planner": ScenePlanner,
        # "timeline_keeper": TimelineKeeper,
        # "consistency_analyst": ConsistencyAnalyst,
        # "atmosphere_descriptor": AtmosphereDescriptor,
        # "writer": Writer,
        # "corrector": Corrector,
        # "synthesizer": Synthesizer,
    }

    @classmethod
    def create_agent(cls, agent_type: str) -> BaseAgent:
        """Crée une instance d'agent"""
        if agent_type not in cls._agents:
            raise ValueError(f"Agent type '{agent_type}' not found")

        return cls._agents[agent_type]()

    @classmethod
    def get_available_agents(cls) -> Dict[str, str]:
        """Retourne la liste des agents disponibles avec leurs descriptions"""
        agents_info = {}
        for agent_type, agent_class in cls._agents.items():
            instance = agent_class()
            agents_info[agent_type] = {
                "name": instance.name,
                "description": instance.description,
            }
        return agents_info

    @classmethod
    def list_agent_types(cls) -> list[str]:
        """Retourne la liste des types d'agents disponibles"""
        return list(cls._agents.keys())
