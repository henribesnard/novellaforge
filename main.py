import os
from dotenv import load_dotenv
from crewai import Crew, Process, Task
from agents import create_all_agents
from utils.model_manager import ModelManager
from state import NovellaState
from typing import Dict, Any

# Chargement des variables d'environnement
load_dotenv()

class NovellaForgeManager:
    """Gestionnaire principal pour la génération de novellas"""
    
    def __init__(self, model_manager=None, state=None):
        # Initialiser le gestionnaire de modèles
        self.model_manager = model_manager or ModelManager()
        
        # Initialiser l'état de la novella
        self.state = state or NovellaState()
        
        # Obtenir le modèle LLM
        self.llm = self.model_manager.get_model()
        
        # Créer tous les agents
        self.agents = create_all_agents(self.llm)
    
    def initialize_novella(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Initialise une nouvelle novella en interaction avec l'utilisateur"""
        
        # Définir les tâches d'initialisation
        init_concept_task = Task(
            description=f"""
            Discutez avec l'utilisateur pour établir le concept fondamental de la novella:
            
            Titre: {user_input.get('title', 'Non spécifié')}
            Genre: {user_input.get('genre', 'Non spécifié')}
            Cadre/Univers: {user_input.get('setting', 'Non spécifié')}
            Protagoniste(s): {user_input.get('protagonist', 'Non spécifié')}
            Antagoniste(s): {user_input.get('antagonist', 'Non spécifié')}
            Ton: {user_input.get('tone', 'Non spécifié')}
            Informations supplémentaires: {user_input.get('additional_info', 'Non spécifié')}
            
            Créez un document fondateur avec tous ces éléments, suffisamment riche pour soutenir 500+ chapitres
            mais suffisamment flexible pour permettre l'évolution de l'histoire.
            """,
            expected_output="""
            Un document détaillé présentant:
            1. Le pitch central de la novella (2-3 phrases)
            2. Les détails du genre et sous-genres
            3. Description de l'univers/cadre
            4. Profils des personnages principaux
            5. Le conflit central et ses ramifications potentielles
            6. Ton et style narratif
            7. Éléments distinctifs qui soutiendront une longue narration
            """,
            agent=self.agents["story_architect"]
        )
        
        develop_arcs_task = Task(
            description="""
            Sur la base du concept établi, développez:
            - 5-7 grands arcs narratifs qui peuvent couvrir l'ensemble des 500+ chapitres
            - La structure générale de ces arcs (exposition, développement, points de tension, climax)
            - Comment ces arcs s'imbriquent et se succèdent
            - Les points pivots majeurs qui marqueront des transitions importantes
            
            Votre plan doit être suffisamment détaillé pour guider l'histoire mais assez flexible pour permettre
            des ajustements en cours de route.
            """,
            expected_output="""
            Un document stratégique contenant:
            1. Vue d'ensemble des 5-7 arcs narratifs principaux
            2. Estimation approximative du nombre de chapitres par arc
            3. Principaux points pivots de l'histoire
            4. Progression générale des enjeux et de la tension narrative
            5. Potentiels points d'entrée pour des sous-intrigues significatives
            """,
            agent=self.agents["plot_strategist"],
            context=[init_concept_task]
        )
        
        create_characters_task = Task(
            description="""
            Créez une bible des personnages complète incluant:
            - Profils détaillés des personnages principaux (5-10)
            - Profils de base des personnages secondaires importants (10-20)
            - Relations et dynamiques entre les personnages
            - Arcs de développement potentiels sur la durée de la novella
            - Secrets, motivations cachées et conflits internes qui pourront être explorés
            
            Cette bible servira de référence pour maintenir la cohérence des personnages
            tout au long des 500+ chapitres.
            """,
            expected_output="""
            Une bible des personnages exhaustive avec:
            1. Fiches détaillées pour chaque personnage principal
            2. Fiches de base pour les personnages secondaires
            3. Schéma des relations entre personnages
            4. Trajectoires d'évolution prévues
            5. Points de tension interpersonnelle à exploiter
            """,
            agent=self.agents["character_manager"],
            context=[init_concept_task, develop_arcs_task]
        )
        
        establish_world_task = Task(
            description="""
            Développez un guide détaillé de l'univers de la novella incluant:
            - Lois physiques ou magiques particulières
            - Géographie et lieux importants
            - Histoire et événements passés significatifs
            - Cultures, religions, organisations sociales
            - Technologies ou systèmes magiques
            - Conflits sociopolitiques et enjeux globaux
            
            Ce guide doit être suffisamment détaillé pour éviter les incohérences mais prévoir
            des zones d'expansion pour les 500+ chapitres à venir.
            """,
            expected_output="""
            Un guide d'univers complet contenant:
            1. Règles fondamentales de l'univers (physiques/magiques/technologiques)
            2. Cartographie et descriptions des lieux principaux
            3. Chronologie historique avec événements majeurs
            4. Structures sociales, culturelles et politiques
            5. Systèmes économiques, religieux et éducatifs pertinents
            6. Conflits préexistants et tensions à explorer
            """,
            agent=self.agents["world_builder"],
            context=[init_concept_task, develop_arcs_task]
        )
        
        # Créer le crew d'initialisation
        init_crew = Crew(
            agents=[
                self.agents["story_architect"],
                self.agents["plot_strategist"],
                self.agents["character_manager"],
                self.agents["world_builder"]
            ],
            tasks=[
                init_concept_task,
                develop_arcs_task,
                create_characters_task,
                establish_world_task
            ],
            process=Process.sequential,
            verbose=True
        )
        
        # Exécuter le crew
        result = init_crew.kickoff()
        
        # Sauvegarder les résultats dans l'état
        self.state.concept = result.get("init_concept_task", {})
        self.state.arcs = result.get("develop_arcs_task", {})
        self.state.characters = result.get("create_characters_task", {})
        self.state.world = result.get("establish_world_task", {})
        
        # Sauvegarder l'état
        self.state.save_to_file()
        
        return result
    
    def produce_chapter(self) -> Dict[str, Any]:
        """Produit un nouveau chapitre de la novella"""
        # Déterminer le numéro du chapitre
        next_chapter = self.state.current_chapter + 1
        
        # Obtenir la mémoire narrative compilée
        memory = self.state.compiled_memory if self.state.compiled_memory else "Premier chapitre de la novella."
        
        # 1. Planifier le chapitre
        plan_task = Task(
            description=f"""
            Sur la base des chapitres précédents et de la stratégie narrative globale,
            élaborez un plan détaillé pour le chapitre {next_chapter} incluant:
            - Les événements principaux qui doivent se produire
            - Les personnages impliqués et leurs objectifs
            - Comment ce chapitre fait avancer l'intrigue globale
            - Éléments de l'univers à mettre en valeur
            - Les enjeux émotionnels et narratifs
            
            Mémoire narrative à considérer:
            {memory}
            
            Titre de la novella: {self.state.title}
            """,
            expected_output=f"""
            Un plan détaillé pour le chapitre {next_chapter} contenant:
            1. Objectif narratif du chapitre
            2. Séquence d'événements clés
            3. Points de vue et personnages principaux
            4. Développements attendus (intrigue, personnages, univers)
            5. Accroche pour le chapitre suivant
            """,
            agent=self.agents["plot_strategist"]
        )
        
        # Exécuter la tâche de planification
        plan_result = plan_task.execute()
        
        # 2. Écrire le chapitre
        write_task = Task(
            description=f"""
            Écrivez le chapitre {next_chapter} de la novella en suivant le plan fourni.
            Le chapitre doit faire entre 1000 et 1500 mots et maintenir le style établi.
            Intégrez naturellement les éléments narratifs, les personnages et les aspects de 
            l'univers qui ont été définis.
            
            Mémoire narrative à considérer:
            {memory}
            
            Plan du chapitre:
            {plan_result}
            
            Titre de la novella: {self.state.title}
            """,
            expected_output=f"""
            Un chapitre complet de 1000-1500 mots qui:
            1. Respecte le plan fourni
            2. Maintient la cohérence avec les chapitres précédents
            3. Fait avancer l'intrigue de manière engageante
            4. Utilise un style d'écriture captivant et approprié
            5. Se termine sur une note qui incite à continuer la lecture
            """,
            agent=self.agents["chapter_writer"]
        )
        
        # Exécuter la tâche d'écriture
        chapter_content = write_task.execute()
        
        # 3. Résumer le chapitre
        summarize_task = Task(
            description=f"""
            Créez un résumé concis mais complet du chapitre qui vient d'être écrit.
            Ce résumé doit capturer tous les éléments narratifs importants pour maintenir
            la continuité de l'histoire.
            
            Chapitre à résumer:
            {chapter_content}
            """,
            expected_output=f"""
            Un résumé de 200-300 mots qui capture:
            1. Les événements principaux du chapitre
            2. Les développements de personnages significatifs
            3. Les nouvelles informations sur l'univers
            4. Les avancées dans l'intrigue principale et les sous-intrigues
            5. Les questions laissées en suspens
            """,
            agent=self.agents["chapter_summarizer"]
        )
        
        # Exécuter la tâche de résumé
        chapter_summary = summarize_task.execute()
        
        # 4. Vérifier la continuité
        continuity_task = Task(
            description=f"""
            Vérifiez la cohérence du chapitre qui vient d'être écrit avec les chapitres précédents
            et les éléments établis de l'univers, des personnages et de l'intrigue.
            Identifiez toute incohérence, contradiction ou problème potentiel.
            
            Chapitre à vérifier:
            {chapter_content}
            
            Mémoire narrative compilée:
            {memory}
            """,
            expected_output=f"""
            Un rapport de cohérence indiquant:
            1. État général de la cohérence (OK ou problèmes)
            2. Incohérences ou contradictions relevées (si applicable)
            3. Suggestions de corrections (si nécessaire)
            4. Éléments à garder en mémoire pour les chapitres futurs
            """,
            agent=self.agents["continuity_guardian"]
        )
        
        # Exécuter la tâche de vérification de continuité
        continuity_report = continuity_task.execute()
        
        # Si des incohérences majeures sont détectées, réécrire le chapitre
        # (Logique simplifiée - en production, on pourrait faire une analyse plus fine du rapport)
        if "problèmes majeurs" in continuity_report.lower() or "incohérences majeures" in continuity_report.lower():
            # Réécrire en tenant compte des commentaires
            write_task = Task(
                description=f"""
                Réécrivez le chapitre {next_chapter} en corrigeant les incohérences suivantes:
                
                Rapport de continuité:
                {continuity_report}
                
                Chapitre original:
                {chapter_content}
                
                Plan du chapitre:
                {plan_result}
                
                Mémoire narrative:
                {memory}
                """,
                expected_output=f"""
                Un chapitre révisé de 1000-1500 mots qui corrige les incohérences tout en:
                1. Respectant le plan fourni
                2. Maintenant la cohérence avec les chapitres précédents
                3. Faisant avancer l'intrigue de manière engageante
                """,
                agent=self.agents["chapter_writer"]
            )
            
            # Exécuter la réécriture
            chapter_content = write_task.execute()
            
            # Mettre à jour le résumé également
            summarize_task.description = f"Créez un nouveau résumé pour le chapitre révisé: {chapter_content}"
            chapter_summary = summarize_task.execute()
        
        # 5. Enrichir la qualité narrative (commentaires pour les prochains chapitres)
        enhance_task = Task(
            description=f"""
            Analysez le chapitre qui vient d'être écrit et proposez des améliorations
            narratives pour enrichir l'histoire dans les prochains chapitres. Identifiez les opportunités
            d'approfondissement des thèmes, des personnages ou de l'univers.
            
            Chapitre à analyser:
            {chapter_content}
            
            Contexte narratif:
            Chapitre {next_chapter} d'une novella prévue pour 500+ chapitres.
            """,
            expected_output=f"""
            Des suggestions d'enrichissement narratif incluant:
            1. Thèmes à développer dans les prochains chapitres
            2. Opportunités de caractérisation approfondie
            3. Éléments d'univers à explorer davantage
            4. Possibilités de sous-intrigues intéressantes
            5. Améliorations stylistiques potentielles
            """,
            agent=self.agents["narrative_enhancer"]
        )
        
        # Exécuter la tâche d'enrichissement
        enhancement_suggestions = enhance_task.execute()
        
        # 6. Évaluer l'expérience lecteur
        reader_task = Task(
            description=f"""
            Évaluez l'expérience de lecture du chapitre {next_chapter} et son impact sur
            l'engagement global du lecteur. Identifiez les forces et faiblesses
            en termes de rythme, tension narrative, et connexion émotionnelle.
            
            Chapitre à évaluer:
            {chapter_content}
            """,
            expected_output=f"""
            Une évaluation de l'expérience lecteur contenant:
            1. Points forts du chapitre pour l'engagement
            2. Aspects potentiellement problématiques
            3. Équilibre du rythme narratif
            4. Suggestions pour maintenir l'intérêt du lecteur
            5. Prévisions pour les prochains chapitres
            """,
            agent=self.agents["reader_experience_manager"]
        )
        
        # Exécuter la tâche d'évaluation
        reader_evaluation = reader_task.execute()
        
        # 7. Ajouter le chapitre et le résumé à l'état de la novella
        self.state.add_chapter(chapter_content, chapter_summary)
        
        # Sauvegarder les métadonnées du chapitre
        chapter_metadata = {
            "number": next_chapter,
            "plan": plan_result,
            "continuity_report": continuity_report,
            "enhancement_suggestions": enhancement_suggestions,
            "reader_evaluation": reader_evaluation
        }
        
        # Si on avait un attribut pour les métadonnées dans la classe NovellaState
        # self.state.add_chapter_metadata(chapter_metadata)
        
        # Sauvegarder l'état
        self.state.save_to_file()
        
        return {
            "chapter_number": next_chapter,
            "content": chapter_content,
            "summary": chapter_summary,
            "metadata": chapter_metadata
        }


if __name__ == "__main__":
    # Point d'entrée pour les tests en ligne de commande
    model_manager = ModelManager()
    state = NovellaState()
    manager = NovellaForgeManager(model_manager, state)
    
    # Si une novella existe déjà, la charger
    if state.load_from_file():
        print(f"Novella existante chargée: {state.title}")
        print(f"Nombre de chapitres existants: {state.current_chapter}")
        
        # Demander s'il faut générer un nouveau chapitre
        while input("Générer un nouveau chapitre? (o/n): ").lower() == 'o':
            print(f"Génération du chapitre {state.current_chapter + 1}...")
            result = manager.produce_chapter()
            print(f"Chapitre {result['chapter_number']} généré avec succès!")
            print("Résumé du chapitre:")
            print(result['summary'])
    else:
        # Sinon, initialiser une nouvelle novella
        print("Initialisation d'une nouvelle novella...")
        user_input = {
            "title": input("Titre de la novella: "),
            "genre": input("Genre principal: "),
            "setting": input("Cadre/Univers: "),
            "protagonist": input("Protagoniste(s): "),
            "antagonist": input("Antagoniste(s): "),
            "tone": input("Ton (Dramatique, Humoristique, Sombre, etc.): "),
            "additional_info": input("Informations supplémentaires: ")
        }
        
        result = manager.initialize_novella(user_input)
        print("Novella initialisée avec succès!")
        
        # Demander s'il faut générer le premier chapitre
        if input("Générer le premier chapitre? (o/n): ").lower() == 'o':
            print("Génération du chapitre 1...")
            result = manager.produce_chapter()
            print("Chapitre 1 généré avec succès!")
            print("Résumé du chapitre:")
            print(result['summary'])