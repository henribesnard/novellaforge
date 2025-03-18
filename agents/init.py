# Importer tous les agents pour faciliter l'accès
from .story_architect import StoryArchitect
from .plot_strategist import PlotStrategist
from .character_manager import CharacterManager
from .world_builder import WorldBuilder
from .chapter_writer import ChapterWriter
from .chapter_summarizer import ChapterSummarizer
from .continuity_guardian import ContinuityGuardian
from .memory_compiler import MemoryCompiler
from .narrative_enhancer import NarrativeEnhancer
from .reader_experience_manager import ReaderExperienceManager

# Fonction pour créer tous les agents
def create_all_agents(llm):
    """Crée tous les agents avec le modèle spécifié"""
    return {
        "story_architect": StoryArchitect(llm).create(),
        "plot_strategist": PlotStrategist(llm).create(),
        "character_manager": CharacterManager(llm).create(),
        "world_builder": WorldBuilder(llm).create(),
        "chapter_writer": ChapterWriter(llm).create(),
        "chapter_summarizer": ChapterSummarizer(llm).create(),
        "continuity_guardian": ContinuityGuardian(llm).create(),
        "memory_compiler": MemoryCompiler(llm).create(),
        "narrative_enhancer": NarrativeEnhancer(llm).create(),
        "reader_experience_manager": ReaderExperienceManager(llm).create()
    }
def create_agent_with_fallback(agent_class, llm, role, goal, backstory):
    """Crée un agent avec gestion des erreurs potentielles"""
    try:
        return agent_class(llm).create()
    except Exception as e:
        print(f"Erreur lors de la création de l'agent {agent_class.__name__}: {e}")
        # Création d'un agent basique en cas d'erreur
        from crewai import Agent
        return Agent(
            role=role,
            goal=goal, 
            backstory=backstory,
            llm=llm,
            verbose=True
        )