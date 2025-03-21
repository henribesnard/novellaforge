from typing import Dict, Any, Tuple, List
from utils.model_manager import ModelManager
from state import NovellaState
from crewai import Agent, Task, Crew, Process

class NovellaForgeManager:
    """Gestionnaire pour la génération de novellas"""
    
    def __init__(self, model_manager=None, state=None):
        self.model_manager = model_manager or ModelManager()
        self.state = state or NovellaState()
        
        # Obtenir le client approprié
        if self.model_manager.primary_available:
            self.client = self.model_manager.deepseek_client
            self.is_deepseek = True
        elif self.model_manager.fallback_available:
            self.client = self.model_manager.openai_model
            self.is_deepseek = False
        else:
            raise Exception("Aucun modèle LLM disponible")
        
        # Créer des agents basiques
        self.agents = self.create_agents()
    
    def create_agents(self):
        """Crée des agents basiques"""
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
            goal="Rédiger des chapitres captivants selon les spécifications fournies",
            backstory="Auteur talentueux qui transforme les concepts en prose engageante",
            verbose=True
        )
        
        temporal_guardian = Agent(
            role="Gardien de la Temporalité",
            goal="Assurer la cohérence temporelle et chronologique de la narration",
            backstory="Expert en chronologie narrative et temporalité fictionnelle",
            verbose=True
        )
        
        continuity_guardian = Agent(
            role="Gardien de la Continuité",
            goal="Assurer la cohérence narrative parfaite sur l'ensemble des chapitres",
            backstory="Expert en détails et cohérence narrative",
            verbose=True
        )
        
        return {
            "story_architect": story_architect,
            "plot_strategist": plot_strategist,
            "chapter_writer": chapter_writer,
            "temporal_guardian": temporal_guardian,
            "continuity_guardian": continuity_guardian
        }
    
    def generate_text(self, prompt):
        """Génère du texte avec le modèle approprié"""
        try:
            if self.is_deepseek:
                # Utiliser l'API DeepSeek
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=4000  # Augmenté pour les chapitres plus longs
                )
                return response.choices[0].message.content
            else:
                # Utiliser directement l'API OpenAI via le modèle LangChain
                return self.client.invoke(prompt)
        except Exception as e:
            print(f"Erreur lors de la génération de texte: {e}")
            return f"Erreur: {str(e)}"
    
    def initialize_novella(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Initialise une nouvelle novella avec des détails enrichis"""
        # Sauvegarder les informations de base
        self.state.title = user_input.get("title", "Sans titre")
        self.state.concept = user_input
        
        # Générer le concept avec le LLM
        prompt = f"""
        En tant qu'Architecte Narratif, créez un concept détaillé pour une novella avec les éléments suivants:
        
        ## Informations de base
        Titre: {user_input.get('title')}
        Genre principal: {user_input.get('genre')}
        Sous-genres: {user_input.get('subgenres', 'Non spécifié')}
        
        ## Contexte détaillé
        Univers/Cadre: {user_input.get('setting')}
        Époque/Période: {user_input.get('time_period', 'Non spécifié')}
        Contraintes temporelles: {user_input.get('timeline_constraints', 'Non spécifié')}
        
        ## Personnages
        Protagoniste(s): {user_input.get('protagonist')}
        Antagoniste(s): {user_input.get('antagonist')}
        Personnages secondaires: {user_input.get('supporting_characters', 'Non spécifié')}
        
        ## Éléments narratifs
        Intrigue principale: {user_input.get('main_plot', 'Non spécifié')}
        Sous-intrigues: {user_input.get('subplots', 'Non spécifié')}
        Thèmes à explorer: {user_input.get('themes', 'Non spécifié')}
        Ton général: {user_input.get('tone', 'Non spécifié')}
        
        ## Style d'écriture
        Style d'écriture: {user_input.get('writing_style', 'Non spécifié')}
        Point de vue narratif: {user_input.get('narrative_pov', 'Non spécifié')}
        
        ## Contraintes additionnelles
        Requêtes spéciales: {user_input.get('special_requests', 'Non spécifié')}
        Éléments à éviter: {user_input.get('elements_to_avoid', 'Non spécifié')}
        
        Fournissez un concept détaillé avec:
        1. Un pitch central captivant (2-3 phrases)
        2. Description approfondie du cadre/univers
        3. Profils détaillés des personnages principaux (histoire, motivations, conflits)
        4. Le conflit central et ses implications
        5. Une structure narrative générale
        6. Les thèmes principaux à explorer
        7. Le ton et style narratif qui définiront l'œuvre
        """
        
        concept_response = self.generate_text(prompt)
        self.state.concept_details = concept_response
        
        # Générer les arcs narratifs
        arcs_prompt = f"""
        En tant que Stratège d'Intrigue, développez 5-7 grands arcs narratifs pour cette novella:
        
        {concept_response}
        
        Pour chaque arc, indiquez:
        1. Le nom et thème principal de l'arc
        2. Les principaux événements 
        3. Points pivots majeurs
        4. Les personnages centraux impliqués
        5. L'évolution émotionnelle/caractérielle attendue
        6. Sous-intrigues potentielles
        7. Liens avec les autres arcs
        
        Établissez également une chronologie générale indiquant:
        1. La durée approximative couverte par chaque arc
        2. Les saisons ou périodes importantes
        3. Les événements temporels fixes qui serviront de repères
        
        L'objectif est de créer une structure narrative solide qui évite les répétitions d'intrigues
        et maintient une progression temporelle cohérente.
        """
        
        arcs_response = self.generate_text(arcs_prompt)
        self.state.arcs = arcs_response
        
        # Initialiser une chronologie de base
        timeline_prompt = f"""
        En tant que Gardien de la Temporalité, établissez une chronologie initiale pour cette novella:
        
        {concept_response}
        
        Arcs narratifs:
        {arcs_response}
        
        Créez une chronologie avec:
        1. Le point de départ temporel précis de l'histoire
        2. 5-10 événements marquants qui serviront d'ancres temporelles 
        3. Les saisons, années ou époques importantes
        4. La durée approximative couverte par l'ensemble de la narration
        5. Tout cycle temporel significatif (lunaisons, célébrations, etc.)
        
        Présentez ces informations de manière structurée pour faciliter le suivi temporel.
        """
        
        timeline_response = self.generate_text(timeline_prompt)
        # Initier la chronologie de base
        self.state.add_timeline_event(
            "Début de l'histoire", 
            "Point de départ temporel de la narration", 
            "Début", 
            0
        )
        
        # Sauvegarder l'état
        self.state.save_to_file()
        
        return {
            "concept": concept_response,
            "arcs": arcs_response,
            "timeline": timeline_response
        }
    
    def produce_chapter(self, word_count=(1000, 1500), additional_context="", avoid_repetition=True) -> Dict[str, Any]:
        """Produit un nouveau chapitre avec options avancées"""
        next_chapter = self.state.current_chapter + 1
        memory = self.state.compiled_memory if self.state.compiled_memory else "Premier chapitre de la novella."
        
        # Obtenir le contexte du concept
        concept_details = self.state.concept_details or ""
        if not concept_details and isinstance(self.state.concept, dict):
            concept_details = "\n".join([f"{k}: {v}" for k, v in self.state.concept.items()])
        
        # Obtenir les informations sur les arcs narratifs
        arcs_info = self.state.arcs or ""
        
        # Obtenir le contexte temporel
        timeline_context = self.state.get_timeline_context()
        
        # Identifier les éléments d'intrigue récemment utilisés
        recent_plot_elements = ""
        if avoid_repetition:
            elements = self.state.get_used_plot_elements(last_n_chapters=3)
            if elements:
                recent_plot_elements = "Éléments d'intrigue récemment utilisés (à éviter de répéter):\n"
                for elem in elements:
                    recent_plot_elements += f"- {elem['name']}: {elem['description']} (Ch.{elem['last_mentioned_in']})\n"
        
        # Intégrer le contexte additionnel fourni par l'utilisateur
        if additional_context:
            self.state.add_contextual_element("user_input", additional_context, next_chapter)
            context_note = f"\nContexte spécifique à intégrer dans ce chapitre:\n{additional_context}\n"
        else:
            context_note = ""
        
        # Planifier le chapitre
        plan_prompt = f"""
        En tant que Stratège d'Intrigue, créez un plan détaillé pour le chapitre {next_chapter} de la novella "{self.state.title}".
        
        INFORMATIONS DE BASE:
        {concept_details}
        
        ARCS NARRATIFS:
        {arcs_info}
        
        CONTEXTE TEMPOREL:
        {timeline_context}
        
        MÉMOIRE NARRATIVE (chapitres précédents):
        {memory}
        
        {recent_plot_elements}
        {context_note}
        
        CONTRAINTES SPÉCIFIQUES:
        - Longueur cible: {word_count[0]}-{word_count[1]} mots
        - Maintenir une progression temporelle cohérente
        - Éviter les répétitions d'intrigues récentes
        - Intégrer naturellement tout contexte spécifique demandé
        
        Fournissez un plan détaillé incluant:
        1. Objectif narratif du chapitre
        2. Ancrage temporel précis (quand ce chapitre se déroule)
        3. Séquence chronologique d'événements
        4. Points de vue et personnages impliqués
        5. Développements d'intrigue, personnages et univers
        6. Nouveaux éléments narratifs à introduire
        7. Accroche pour le chapitre suivant
        """
        
        chapter_plan = self.generate_text(plan_prompt)
        
        # Vérifier la cohérence temporelle
        temporal_prompt = f"""
        En tant que Gardien de la Temporalité, vérifiez la cohérence temporelle du plan de chapitre suivant:
        
        {chapter_plan}
        
        CONTEXTE TEMPOREL ÉTABLI:
        {timeline_context}
        
        MÉMOIRE NARRATIVE:
        {memory}
        
        Analysez:
        1. La cohérence du moment où se déroule ce chapitre par rapport aux chapitres précédents
        2. La plausibilité temporelle des événements décrits
        3. Tout problème potentiel de continuité temporelle
        4. Les nouveaux éléments temporels à documenter
        
        Si vous identifiez des problèmes, proposez des corrections précises.
        """
        
        temporal_analysis = self.generate_text(temporal_prompt)
        
        # Vérifier s'il y a des incohérences temporelles majeures
        correction_needed = False
        if "incohérence" in temporal_analysis.lower() or "problème" in temporal_analysis.lower():
            correction_needed = True
            # Corriger le plan si nécessaire
            correction_prompt = f"""
            En tant que Stratège d'Intrigue, corrigez le plan du chapitre pour résoudre les problèmes temporels identifiés:
            
            PLAN ORIGINAL:
            {chapter_plan}
            
            ANALYSE TEMPORELLE:
            {temporal_analysis}
            
            Fournissez un nouveau plan corrigé qui maintient les éléments narratifs essentiels
            tout en résolvant les problèmes de cohérence temporelle.
            """
            
            chapter_plan = self.generate_text(correction_prompt)
        
        # Écrire le chapitre
        write_prompt = f"""
        En tant que Rédacteur de Chapitres, écrivez le chapitre {next_chapter} de la novella "{self.state.title}" 
        en suivant ce plan:
        
        {chapter_plan}
        
        MÉMOIRE NARRATIVE (chapitres précédents):
        {memory}
        
        {context_note}
        
        CONTRAINTES D'ÉCRITURE:
        - Longueur: {word_count[0]}-{word_count[1]} mots exactement
        - Style: {self.state.concept.get('writing_style', 'Équilibré')}
        - Point de vue: {self.state.concept.get('narrative_pov', 'Troisième personne')}
        - Ton: {self.state.concept.get('tone', 'Neutre')}
        
        Le chapitre doit:
        - Maintenir une voix narrative cohérente
        - Éviter les répétitions de tournures de phrases
        - Faire avancer l'intrigue de manière captivante
        - Se terminer sur une note qui donne envie de lire la suite
        - Intégrer harmonieusement les contraintes temporelles
        """
        
        chapter_content = self.generate_text(write_prompt)
        
        # Extraire des éléments temporels et d'intrigue
        extract_prompt = f"""
        Analysez le chapitre suivant et extrayez:
        
        1. ÉLÉMENTS TEMPORELS: Identifiez 2-3 événements ou références temporelles importantes qui devraient être documentés
        2. ÉLÉMENTS D'INTRIGUE: Identifiez 3-5 éléments d'intrigue significatifs introduits ou développés
        
        Chapitre:
        {chapter_content}
        
        Formatez votre réponse ainsi:
        
        ÉLÉMENTS TEMPORELS:
        - [Nom événement 1]: [Description] | [Quand]
        - [Nom événement 2]: [Description] | [Quand]
        
        ÉLÉMENTS D'INTRIGUE:
        - [Nom élément 1]: [Description brève]
        - [Nom élément 2]: [Description brève]
        """
        
        extracted_elements = self.generate_text(extract_prompt)
        
        # Résumer le chapitre
        summary_prompt = f"""
        Créez un résumé concis mais complet (environ 200-300 mots) du chapitre suivant:
        
        {chapter_content}
        
        Le résumé doit capturer:
        1. Les événements principaux dans leur ordre chronologique
        2. Les développements de personnages significatifs
        3. Les nouvelles informations sur l'univers
        4. Les avancées dans l'intrigue principale et les sous-intrigues
        5. Les questions laissées en suspens
        6. Le cadre temporel précis du chapitre
        """
        
        chapter_summary = self.generate_text(summary_prompt)
        
        # Créer les métadonnées du chapitre
        metadata = {
            "plan": chapter_plan,
            "temporal_analysis": temporal_analysis,
            "extracted_elements": extracted_elements,
            "word_count_target": word_count,
            "additional_context": additional_context
        }
        
        # Ajouter le chapitre et le résumé à l'état
        self.state.add_chapter(chapter_content, chapter_summary, metadata)
        
        # Traiter les éléments temporels et d'intrigue extraits
        # Cette partie est simplifiée - dans une implémentation complète,
        # on analyserait le texte extrait pour mettre à jour la timeline et les éléments d'intrigue
        
        # Exemple simplifié d'ajout d'éléments à la timeline
        if "ÉLÉMENTS TEMPORELS" in extracted_elements:
            parts = extracted_elements.split("ÉLÉMENTS D'INTRIGUE")
            temporal_section = parts[0]
            
            # Analyse très simplifiée - une implémentation réelle utiliserait du NLP
            for line in temporal_section.split("\n"):
                if line.strip().startswith("- "):
                    # Tentative d'extraction d'informations temporelles
                    parts = line.strip("- ").split(":")
                    if len(parts) > 1:
                        event_name = parts[0].strip()
                        description_parts = parts[1].split("|")
                        description = description_parts[0].strip()
                        when = description_parts[1].strip() if len(description_parts) > 1 else "Non spécifié"
                        
                        self.state.add_timeline_event(event_name, description, when, next_chapter)
        
        return {
            "chapter_number": next_chapter,
            "content": chapter_content,
            "summary": chapter_summary,
            "plan": chapter_plan,
            "temporal_analysis": temporal_analysis,
            "metadata": metadata
        }
    
    def rewrite_chapter(self, chapter_number, instructions="", complete_rewrite=False) -> Dict[str, Any]:
        """Réécrit ou modifie un chapitre existant"""
        # Vérifier que le chapitre existe
        chapter_content = None
        for chapter in self.state.chapters:
            if chapter["number"] == chapter_number:
                chapter_content = chapter["content"]
                break
        
        if not chapter_content:
            raise ValueError(f"Chapitre {chapter_number} non trouvé")
        
        # Obtenir le résumé du chapitre
        chapter_summary = None
        for summary in self.state.summaries:
            if summary["number"] == chapter_number:
                chapter_summary = summary["summary"]
                break
        
        # Obtenir le contexte narratif
        memory = self.state.compiled_memory
        
        # Obtenir les métadonnées du chapitre si elles existent
        chapter_metadata = None
        for metadata in self.state.chapter_metadata:
            if metadata["number"] == chapter_number:
                chapter_metadata = metadata
                break
        
        plan = chapter_metadata.get("plan", "") if chapter_metadata else ""
        word_count = chapter_metadata.get("word_count_target", (1000, 1500)) if chapter_metadata else (1000, 1500)
        
        if complete_rewrite:
            # Régénérer complètement le chapitre
            rewrite_prompt = f"""
            En tant que Rédacteur de Chapitres, réécrivez COMPLÈTEMENT le chapitre {chapter_number} de la novella "{self.state.title}".
            
            PLAN ORIGINAL:
            {plan}
            
            INSTRUCTIONS SPÉCIFIQUES:
            {instructions}
            
            MÉMOIRE NARRATIVE:
            {memory}
            
            CONTRAINTES D'ÉCRITURE:
            - Longueur: {word_count[0]}-{word_count[1]} mots
            - Maintenir la cohérence avec l'histoire globale
            - Respecter la chronologie établie
            - Intégrer les instructions spécifiques fournies
            
            Créez une version entièrement nouvelle du chapitre qui respecte les points narratifs essentiels
            mais avec une approche fraîche et renouvelée.
            """
            
            new_content = self.generate_text(rewrite_prompt)
        else:
            # Modifier le chapitre existant
            edit_prompt = f"""
            En tant que Rédacteur de Chapitres, modifiez le chapitre {chapter_number} de la novella "{self.state.title}"
            en suivant ces instructions:
            
            {instructions}
            
            CHAPITRE ORIGINAL:
            {chapter_content}
            
            MÉMOIRE NARRATIVE:
            {memory}
            
            Apportez uniquement les modifications demandées tout en préservant la structure et les éléments
            essentiels du chapitre. Maintenez la cohérence avec l'ensemble de l'histoire.
            """
            
            new_content = self.generate_text(edit_prompt)
        
        # Créer un nouveau résumé
        summary_prompt = f"""
        Créez un résumé concis mais complet (environ 200-300 mots) pour la version révisée du chapitre:
        
        {new_content}
        
        Le résumé doit capturer:
        1. Les événements principaux
        2. Les développements de personnages significatifs
        3. Les nouvelles informations sur l'univers
        4. Les avancées dans l'intrigue
        """
        
        new_summary = self.generate_text(summary_prompt)
        
        # Mettre à jour les métadonnées
        new_metadata = {
            "rewritten_at": "date actuelle",
            "rewrite_instructions": instructions,
            "complete_rewrite": complete_rewrite
        }
        
        # Mettre à jour le chapitre
        self.state.update_chapter(chapter_number, new_content, new_summary, new_metadata)
        
        return {
            "chapter_number": chapter_number,
            "content": new_content,
            "summary": new_summary,
            "was_complete_rewrite": complete_rewrite
        }



