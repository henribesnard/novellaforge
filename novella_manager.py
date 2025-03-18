from typing import Dict, Any
from utils.model_manager import ModelManager
from state import NovellaState
from crewai import Agent, Task, Crew, Process

class NovellaForgeManager:
    """Gestionnaire simplifié pour la génération de novellas"""
    
    def __init__(self, model_manager=None, state=None):
        self.model_manager = model_manager or ModelManager()
        self.state = state or NovellaState()
        
        # Au lieu d'utiliser l'abstraction LangChain, utilisons directement le client
        # Cette approche est plus simple et plus fiable
        if self.model_manager.primary_available:
            self.client = self.model_manager.deepseek_client
            self.is_deepseek = True
        elif self.model_manager.fallback_available:
            self.client = self.model_manager.openai_model
            self.is_deepseek = False
        else:
            raise Exception("Aucun modèle LLM disponible")
        
        # Créer des agents basiques qui fonctionnent sans dépendre de LangChain
        self.agents = self.create_agents()
    
    def create_agents(self):
        """Crée des agents basiques"""
        # Pour simplifier et éviter les erreurs, on peut créer des agents sans LLM
        # et gérer l'appel API nous-mêmes
        story_architect = Agent(
            role="Architecte Narratif",
            goal="Établir les fondements d'une novella qui peut s'étendre sur 500+ chapitres",
            backstory="Expert en structure narrative de longue durée",
            verbose=True
        )
        
        plot_strategist = Agent(
            role="Stratège d'Intrigue",
            goal="Concevoir et maintenir une structure narrative cohérente sur 500+ chapitres",
            backstory="Expert en séries longues et en arcs narratifs complexes",
            verbose=True
        )
        
        chapter_writer = Agent(
            role="Rédacteur de Chapitres",
            goal="Rédiger des chapitres captivants de 1000-1500 mots",
            backstory="Auteur talentueux qui transforme les concepts en prose engageante",
            verbose=True
        )
        
        return {
            "story_architect": story_architect,
            "plot_strategist": plot_strategist,
            "chapter_writer": chapter_writer
        }
    
    def generate_text(self, prompt):
        """Génère du texte avec le modèle approprié"""
        try:
            if self.is_deepseek:
                # Utiliser l'API DeepSeek
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                return response.choices[0].message.content
            else:
                # Utiliser directement l'API OpenAI via le modèle LangChain
                return self.client.invoke(prompt)
        except Exception as e:
            print(f"Erreur lors de la génération de texte: {e}")
            return f"Erreur: {str(e)}"
    
    def initialize_novella(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Initialise une nouvelle novella"""
        # Sauvegarder les informations de base
        self.state.title = user_input.get("title", "Sans titre")
        self.state.concept = user_input
        
        # Générer le concept avec le LLM
        prompt = f"""
        En tant qu'Architecte Narratif, créez un concept détaillé pour une novella de 500+ chapitres avec:
        
        Titre: {user_input.get('title')}
        Genre: {user_input.get('genre')}
        Univers: {user_input.get('setting')}
        Protagoniste(s): {user_input.get('protagonist')}
        Antagoniste(s): {user_input.get('antagonist')}
        
        Fournissez:
        1. Un pitch central de 2-3 phrases
        2. Les détails du genre et sous-genres
        3. Description détaillée de l'univers
        4. Profils des personnages principaux
        5. Le conflit central et ses ramifications
        6. Le ton et style narratif
        7. Points distinctifs pour soutenir 500+ chapitres
        """
        
        concept_response = self.generate_text(prompt)
        self.state.concept_details = concept_response
        
        # Générer les arcs narratifs
        arcs_prompt = f"""
        En tant que Stratège d'Intrigue, développez 5-7 grands arcs narratifs pour couvrir 500+ chapitres pour cette novella:
        
        {concept_response}
        
        Pour chaque arc, indiquez:
        1. Le nom et thème principal
        2. Estimation du nombre de chapitres
        3. Points pivots majeurs
        4. Progression des enjeux
        5. Sous-intrigues potentielles
        """
        
        arcs_response = self.generate_text(arcs_prompt)
        self.state.arcs = arcs_response
        
        self.state.save_to_file()
        
        return {
            "concept": concept_response,
            "arcs": arcs_response
        }
    
    def produce_chapter(self) -> Dict[str, Any]:
        """Produit un nouveau chapitre"""
        next_chapter = self.state.current_chapter + 1
        memory = self.state.compiled_memory if self.state.compiled_memory else "Premier chapitre de la novella."
        
        # Vérifier si concept_details existe
        concept_details = getattr(self.state, "concept_details", "")
        if not concept_details and self.state.concept:
            # Si concept_details n'existe pas mais concept existe, utiliser concept
            if isinstance(self.state.concept, dict):
                concept_details = "\n".join([f"{k}: {v}" for k, v in self.state.concept.items()])
            else:
                concept_details = str(self.state.concept)
        
        # Vérifier si arcs existe comme string ou liste
        arcs_info = getattr(self.state, "arcs", "")
        if isinstance(arcs_info, list) and arcs_info:
            arcs_text = "\n".join([str(arc) for arc in arcs_info])
        else:
            arcs_text = str(arcs_info)
        
        # Planifier le chapitre
        plan_prompt = f"""
        En tant que Stratège d'Intrigue, créez un plan détaillé pour le chapitre {next_chapter} de la novella "{self.state.title}".
        
        Concept de la novella:
        {concept_details}
        
        Arcs narratifs:
        {arcs_text}
        
        Mémoire narrative (chapitres précédents):
        {memory}
        
        Fournissez un plan incluant:
        1. Objectif narratif du chapitre
        2. Séquence d'événements clés
        3. Points de vue et personnages impliqués
        4. Développements d'intrigue, personnages et univers
        5. Accroche pour le chapitre suivant
        """
        
        chapter_plan = self.generate_text(plan_prompt)
        
        # Écrire le chapitre
        write_prompt = f"""
        En tant que Rédacteur de Chapitres, écrivez le chapitre {next_chapter} de la novella "{self.state.title}" en suivant ce plan:
        
        {chapter_plan}
        
        Mémoire narrative (chapitres précédents):
        {memory}
        
        Le chapitre doit:
        - Faire entre 1000 et 1500 mots
        - Maintenir un style engageant et cohérent
        - Faire avancer l'intrigue de manière captivante
        - Se terminer sur une note qui donne envie de lire la suite
        """
        
        chapter_content = self.generate_text(write_prompt)
        
        # Résumer le chapitre
        summary_prompt = f"""
        Créez un résumé concis mais complet (environ 200-300 mots) du chapitre suivant:
        
        {chapter_content}
        
        Le résumé doit capturer:
        1. Les événements principaux
        2. Les développements de personnages
        3. Les nouvelles informations sur l'univers
        4. Les avancées dans l'intrigue
        5. Les questions laissées en suspens
        """
        
        chapter_summary = self.generate_text(summary_prompt)
        
        # Ajouter le chapitre et le résumé à l'état
        self.state.add_chapter(chapter_content, chapter_summary)
        
        return {
            "chapter_number": next_chapter,
            "content": chapter_content,
            "summary": chapter_summary,
            "plan": chapter_plan
        }