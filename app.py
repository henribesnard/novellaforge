import streamlit as st
import os
from dotenv import load_dotenv
import base64
import time
import json
import glob
from utils.model_manager import ModelManager
from state import NovellaState
from novella_manager import NovellaForgeManager

# Chargement des variables d'environnement
load_dotenv()

# Configuration de base de Streamlit
st.set_page_config(
    page_title="NovellaForge - Générateur de Novellas",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Création du dossier data s'il n'existe pas
os.makedirs("data", exist_ok=True)
os.makedirs("data/projects", exist_ok=True)

# Fonction pour lister tous les projets existants
def list_projects():
    projects = []
    for file_path in glob.glob("data/projects/*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                project_name = data.get("title", "Sans titre")
                project_id = os.path.basename(file_path).replace(".json", "")
                chapters = len(data.get("chapters", []))
                last_modified = os.path.getmtime(file_path)
                projects.append({
                    "id": project_id,
                    "name": project_name,
                    "chapters": chapters,
                    "last_modified": last_modified
                })
        except Exception as e:
            print(f"Erreur lors de la lecture du projet {file_path}: {e}")
    
    # Trier par date de modification (le plus récent en premier)
    projects.sort(key=lambda x: x["last_modified"], reverse=True)
    return projects

# Fonction pour initialiser ou charger un gestionnaire de novella
@st.cache_resource
def get_manager(project_id=None):
    model_manager = ModelManager()
    state = NovellaState(project_id=project_id)
    return NovellaForgeManager(model_manager, state)

# Page d'accueil - Sélection de projet
def home_page():
    st.title("📚 NovellaForge")
    st.markdown("### Générateur de novellas basé sur l'IA")
    
    # Liste des projets existants
    projects = list_projects()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Projets existants")
        if not projects:
            st.info("Aucun projet existant. Créez votre première novella!")
        else:
            for i, project in enumerate(projects):
                with st.container(border=True):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.subheader(project["name"])
                        st.write(f"Chapitres: {project['chapters']}")
                        st.caption(f"Dernière modification: {time.ctime(project['last_modified'])}")
                    with col_b:
                        st.button("✏️ Ouvrir", key=f"open_{i}", on_click=open_project, args=(project["id"],))
                        if st.button("🗑️ Supprimer", key=f"delete_{i}"):
                            if st.session_state.get(f"confirm_delete_{i}", False):
                                delete_project(project["id"])
                                st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{i}"] = True
                                st.warning("Confirmer la suppression?")
                                st.button("Annuler", key=f"cancel_delete_{i}", on_click=cancel_delete, args=(i,))
    
    with col2:
        st.header("Nouveau projet")
        with st.form("new_project_form"):
            title = st.text_input("Titre de la novella")
            genre = st.text_input("Genre", "Fantasy")
            submit = st.form_submit_button("🚀 Créer nouveau projet")
            
            if submit and title:
                # Créer un nouvel identifiant unique pour le projet
                project_id = f"project_{int(time.time())}"
                
                # Initialiser un état de novella vide avec les informations de base
                state = NovellaState(project_id=project_id)
                state.title = title
                state.concept = {"title": title, "genre": genre}
                state.save_to_file()
                
                # Définir le projet actif et naviguer vers l'application principale
                st.session_state["active_project"] = project_id
                st.session_state["view"] = "app"
                st.rerun()

# Fonction pour ouvrir un projet
def open_project(project_id):
    st.session_state["active_project"] = project_id
    st.session_state["view"] = "app"

# Fonction pour supprimer un projet
def delete_project(project_id):
    try:
        file_path = f"data/projects/{project_id}.json"
        if os.path.exists(file_path):
            os.remove(file_path)
            st.success("Projet supprimé avec succès")
    except Exception as e:
        st.error(f"Erreur lors de la suppression: {e}")

# Fonction pour annuler la suppression
def cancel_delete(index):
    if f"confirm_delete_{index}" in st.session_state:
        del st.session_state[f"confirm_delete_{index}"]

# Application principale - Gestion d'une novella
def app_page():
    # Récupérer l'ID du projet actif
    project_id = st.session_state.get("active_project")
    if not project_id:
        st.error("Aucun projet actif")
        return_to_home()
        return
    
    # Initialiser le gestionnaire avec le projet actif
    manager = get_manager(project_id)
    has_existing_novella = manager.state.load_from_file()
    
    if not has_existing_novella:
        st.error("Le projet n'a pas pu être chargé")
        return_to_home()
        return
    
    # Titre et présentation
    st.title(f"📖 {manager.state.title}")
    
    # Barre latérale pour informations générales
    with st.sidebar:
        st.button("🏠 Retour à l'accueil", on_click=return_to_home)
        
        st.subheader("NovellaForge")
        
        # Afficher le statut du modèle
        if manager.model_manager.primary_available:
            st.success("✓ Modèle principal connecté")
        elif manager.model_manager.fallback_available:
            st.warning("⚠ Utilisation du modèle de secours")
        else:
            st.error("✗ Aucun modèle LLM disponible")
        
        # Afficher les informations du projet
        st.subheader("Projet actuel")
        st.markdown(f"**Titre:** {manager.state.title}")
        st.markdown(f"**Chapitres:** {manager.state.current_chapter}")
    
    # Interface principale
    tabs = st.tabs(["📝 Concept", "📄 Chapitres", "📊 Analyse", "📤 Export"])
    
    # Onglet Concept
    with tabs[0]:
        st.header("Définition du Concept")
        
        if manager.state.concept_details:
            # Permettre la modification du concept
            with st.expander("✏️ Modifier le concept", expanded=False):
                edit_concept(manager)
            
            # Afficher le concept détaillé
            with st.expander("📋 Détails du concept", expanded=True):
                st.markdown(manager.state.concept_details)
                
            # Afficher les arcs narratifs
            with st.expander("🔄 Arcs narratifs", expanded=False):
                st.markdown(manager.state.arcs)
        else:
            # Formulaire de création de concept
            with st.form("concept_form"):
                create_concept_form(manager)
    
    # Onglet Chapitres
    with tabs[1]:
        st.header("Écriture des Chapitres")
        
        # Afficher la chronologie
        with st.expander("⏱️ Chronologie", expanded=False):
            st.markdown(manager.state.get_timeline_context())
        
        # Ajout d'un bouton externe pour la génération du chapitre suivant
        if manager.state.chapters:
            st.subheader("Action rapide")
            if st.button(f"📝 Générer le chapitre {manager.state.current_chapter + 1}", 
                        use_container_width=True, 
                        key="quick_generate_button"):
                with st.spinner(f"Génération du chapitre {manager.state.current_chapter + 1} en cours..."):
                    try:
                        # Utiliser les valeurs par défaut
                        result = manager.produce_chapter(
                            word_count=(1000, 1500),  # valeur par défaut : moyen
                            additional_context="",
                            avoid_repetition=True
                        )
                        st.success(f"✅ Chapitre {manager.state.current_chapter} généré avec succès!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur: {e}")
                        st.error("Essayez d'utiliser les options avancées pour plus de contrôle.")
            st.markdown("---")
        
        # Formulaire pour la génération de chapitre avec options détaillées
        with st.expander("⚙️ Options de génération avancées", expanded=not manager.state.chapters):
            chapter_generation_form(manager)
        
        # Affichage et gestion des chapitres existants
        if not manager.state.chapters:
            st.info("ℹ️ Aucun chapitre n'a encore été généré. Utilisez les options ci-dessus pour créer le premier chapitre.")
        else:
            display_chapters(manager)
    
    # Onglet Analyse
    with tabs[2]:
        st.header("Analyse de la Novella")
        
        if not manager.state.chapters:
            st.warning("⚠️ Générez d'abord des chapitres pour accéder à l'analyse")
        else:
            display_analysis(manager)
    
    # Onglet Export
    with tabs[3]:
        st.header("Export de la Novella")
        
        if not manager.state.chapters:
            st.warning("⚠️ Générez d'abord des chapitres pour pouvoir les exporter")
        else:
            export_options(manager)

# Fonction pour créer/modifier le formulaire de concept
def create_concept_form(manager):
    # Récupérer les valeurs actuelles si elles existent
    concept = manager.state.concept or {}
    
    # Informations de base
    st.subheader("📌 Informations essentielles")
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Titre de la novella", value=concept.get("title", ""))
    with col2:
        genre = st.text_input("Genre principal", value=concept.get("genre", "Fantasy"))
    subgenres = st.text_input("Sous-genres (optionnel)", value=concept.get("subgenres", ""))
    
    # Contexte détaillé
    st.subheader("🌍 Contexte détaillé")
    setting = st.text_area("Univers/Cadre", value=concept.get("setting", "Un monde médiéval avec de la magie"))
    
    col1, col2 = st.columns(2)
    with col1:
        time_period = st.text_input("Époque/Période", value=concept.get("time_period", ""))
    with col2:
        timeline_constraints = st.text_input("Contraintes temporelles", value=concept.get("timeline_constraints", ""))
    
    # Personnages
    st.subheader("👥 Personnages")
    protagonist = st.text_area("Protagoniste(s)", value=concept.get("protagonist", "Un jeune apprenti magicien"))
    antagonist = st.text_area("Antagoniste(s) ou conflit", value=concept.get("antagonist", "Un ancien mal qui s'éveille"))
    supporting_characters = st.text_area("Personnages secondaires importants", value=concept.get("supporting_characters", ""))
    
    # Éléments narratifs
    st.subheader("📚 Éléments narratifs")
    main_plot = st.text_area("Intrigue principale", value=concept.get("main_plot", ""))
    subplots = st.text_area("Sous-intrigues potentielles", value=concept.get("subplots", ""))
    themes = st.text_area("Thèmes à explorer", value=concept.get("themes", ""))
    
    col1, col2 = st.columns(2)
    with col1:
        tone_options = ["Très sombre", "Sombre", "Réaliste", "Léger", "Humoristique", "Satirique"]
        tone = st.select_slider("Ton général", options=tone_options, value=concept.get("tone", "Réaliste"))
    with col2:
        style_options = ["Très descriptif", "Descriptif", "Équilibré", "Action", "Dialogue"]
        writing_style = st.select_slider("Style d'écriture", options=style_options, value=concept.get("writing_style", "Équilibré"))
    
    pov_options = ["Première personne", "Troisième personne limitée", "Troisième personne omnisciente"]
    narrative_pov = st.selectbox("Point de vue narratif", options=pov_options, index=pov_options.index(concept.get("narrative_pov", "Troisième personne limitée")))
    
    # Contraintes additionnelles
    st.subheader("⚙️ Contraintes additionnelles")
    special_requests = st.text_area("Requêtes spéciales", value=concept.get("special_requests", ""))
    elements_to_avoid = st.text_area("Éléments à éviter", value=concept.get("elements_to_avoid", ""))
    
    col1, col2 = st.columns(2)
    with col1:
        submit_button = st.form_submit_button("🚀 Générer le concept", use_container_width=True)
    with col2:
        reset_button = st.form_submit_button("🔄 Réinitialiser le formulaire", use_container_width=True)
    
    if submit_button:
        if not title:
            st.error("Le titre est obligatoire")
        else:
            with st.spinner("Génération du concept en cours..."):
                try:
                    # Création d'un dictionnaire complet avec toutes les informations
                    user_input = {
                        "title": title,
                        "genre": genre,
                        "subgenres": subgenres,
                        "setting": setting,
                        "time_period": time_period,
                        "timeline_constraints": timeline_constraints,
                        "protagonist": protagonist,
                        "antagonist": antagonist,
                        "supporting_characters": supporting_characters,
                        "main_plot": main_plot,
                        "subplots": subplots,
                        "themes": themes,
                        "tone": tone,
                        "writing_style": writing_style,
                        "narrative_pov": narrative_pov,
                        "special_requests": special_requests,
                        "elements_to_avoid": elements_to_avoid
                    }
                    
                    # Initialisation ou mise à jour de la novella
                    result = manager.initialize_novella(user_input)
                    st.success("✅ Concept généré avec succès!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {e}")

# Fonction pour éditer un concept existant
def edit_concept(manager):
    with st.form("edit_concept_form"):
        create_concept_form(manager)

# Formulaire pour la génération de chapitre
def chapter_generation_form(manager):
    chapter_length = st.select_slider(
        "Longueur du chapitre",
        options=["Court (500-800 mots)", "Moyen (1000-1500 mots)", "Long (1800-2500 mots)"],
        value="Moyen (1000-1500 mots)"
    )
    
    additional_context = st.text_area(
        "Éléments contextuels à intégrer",
        placeholder="Ajoutez des éléments spécifiques à intégrer dans ce chapitre...",
        help="Des détails particuliers à introduire dans ce chapitre: lieux, objets, événements, etc."
    )
    
    col1, col2 = st.columns(2)
    with col1:
        avoid_repetition = st.checkbox("Éviter les répétitions d'intrigues", value=True)
    with col2:
        enforce_temporal = st.checkbox("Strict sur la cohérence temporelle", value=True)
    
    # Contraintes supplémentaires pour ce chapitre
    additional_constraints = st.text_area(
        "Contraintes narratives spécifiques",
        placeholder="Ex: focus sur un personnage particulier, scène d'action spécifique...",
        help="Contraintes spéciales pour ce chapitre uniquement"
    )
    
    # Utiliser un texte dynamique et une clé distincte pour le bouton de génération
    generate_text = "📝 Générer le premier chapitre" if not manager.state.chapters else f"📝 Générer le chapitre {manager.state.current_chapter + 1}"
    
    if st.button(generate_text, key="advanced_generate_button", use_container_width=True):
        with st.spinner(f"Génération du chapitre {manager.state.current_chapter + 1} en cours..."):
            try:
                # Conversion de la sélection en mots
                if "Court" in chapter_length:
                    word_count = (500, 800)
                elif "Moyen" in chapter_length:
                    word_count = (1000, 1500)
                else:
                    word_count = (1800, 2500)
                
                # Construction du contexte additionnel
                full_context = additional_context
                if additional_constraints:
                    full_context += f"\nContraintes narratives:\n{additional_constraints}"
                
                # Ajout des paramètres à la fonction produce_chapter
                result = manager.produce_chapter(
                    word_count=word_count,
                    additional_context=full_context,
                    avoid_repetition=avoid_repetition
                )
                st.success(f"✅ Chapitre {manager.state.current_chapter} généré avec succès!")
                # Force une actualisation complète pour garantir l'affichage des nouveaux chapitres
                st.rerun()
            except Exception as e:
                st.error(f"Erreur: {e}")
                st.error("Vérifiez les données fournies et réessayez.")

# Affichage des chapitres
def display_chapters(manager):
    st.subheader("Chapitres existants")
    
    # Onglets pour chaque chapitre
    chapter_tabs = st.tabs([f"Chapitre {ch['number']}" for ch in manager.state.chapters])
    
    for idx, (chapter, tab) in enumerate(zip(manager.state.chapters, chapter_tabs)):
        with tab:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Afficher le contenu du chapitre
                st.markdown(chapter['content'])
            
            with col2:
                # Afficher le résumé et les métadonnées
                with st.expander("📋 Résumé", expanded=True):
                    chapter_summary = None
                    for summary in manager.state.summaries:
                        if summary["number"] == chapter["number"]:
                            chapter_summary = summary["summary"]
                            break
                    
                    if chapter_summary:
                        st.markdown(chapter_summary)
                    else:
                        st.info("Pas de résumé disponible")
                
                # Formulaire pour réécrire le chapitre
                with st.expander("✏️ Modifier ce chapitre", expanded=False):
                    with st.form(f"edit_chapter_{chapter['number']}"):
                        st.subheader(f"Éditer le chapitre {chapter['number']}")
                        
                        edit_instructions = st.text_area(
                            "Instructions de réécriture",
                            placeholder="Précisez les modifications souhaitées...",
                            help="Ex: Ajouter plus de dialogue, changer le ton, développer un personnage...",
                            key=f"edit_instr_{chapter['number']}"
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            rewrite_button = st.form_submit_button("✏️ Réviser", use_container_width=True)
                        with col2:
                            regenerate_button = st.form_submit_button("🔄 Régénérer", use_container_width=True)
                        
                        if rewrite_button and edit_instructions:
                            with st.spinner(f"Révision du chapitre {chapter['number']} en cours..."):
                                try:
                                    result = manager.rewrite_chapter(
                                        chapter_number=chapter['number'],
                                        instructions=edit_instructions,
                                        complete_rewrite=False
                                    )
                                    st.success(f"✅ Chapitre {chapter['number']} révisé!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur: {e}")
                        
                        if regenerate_button:
                            with st.spinner(f"Régénération du chapitre {chapter['number']} en cours..."):
                                try:
                                    result = manager.rewrite_chapter(
                                        chapter_number=chapter['number'],
                                        instructions=edit_instructions,
                                        complete_rewrite=True
                                    )
                                    st.success(f"✅ Chapitre {chapter['number']} régénéré!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur: {e}")

# Analyse de la novella
def display_analysis(manager):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Progression narrative")
        
        # Afficher la chronologie complète
        with st.expander("⏱️ Chronologie détaillée", expanded=True):
            st.markdown(manager.state.get_timeline_context())
        
        # Afficher les éléments d'intrigue
        with st.expander("🔍 Éléments d'intrigue", expanded=True):
            if hasattr(manager.state, 'plot_elements') and manager.state.plot_elements:
                for element in manager.state.plot_elements:
                    st.markdown(f"**{element['name']}** (Ch. {element['introduced_in']} → Ch. {element['last_mentioned_in']})")
                    st.markdown(f"_{element['description']}_")
                    st.markdown("---")
            else:
                st.info("Aucun élément d'intrigue suivi pour le moment")
    
    with col2:
        st.subheader("👥 Personnages")
        
        # Simuler une analyse des personnages (à implémenter réellement)
        with st.expander("Analyse des personnages", expanded=True):
            st.info("Fonctionnalité d'analyse des personnages à venir")
            st.markdown("Cette section permettra d'analyser l'évolution des personnages au fil des chapitres.")
        
        # Simuler une analyse du ton et du style
        with st.expander("Ton et style", expanded=True):
            st.info("Fonctionnalité d'analyse du ton et du style à venir")
            st.markdown("Cette section permettra d'analyser l'évolution du ton et du style au fil des chapitres.")
    
    # Demander une analyse personnalisée
    st.subheader("🔎 Analyse personnalisée")
    with st.form("custom_analysis"):
        analysis_type = st.selectbox(
            "Type d'analyse",
            ["Cohérence narrative", "Évolution des personnages", "Progression temporelle", "Structure et rythme"]
        )
        
        # Vérifier si des chapitres existent avant de créer le multiselect
        chapter_options = [f"Chapitre {ch['number']}" for ch in manager.state.chapters]
        focus_chapters = st.multiselect(
            "Chapitres à analyser",
            options=chapter_options,
            default=chapter_options
        )
        
        analyze_button = st.form_submit_button("🔍 Analyser", use_container_width=True)
        
        if analyze_button:
            st.info("Fonctionnalité d'analyse personnalisée à venir")
            st.markdown("Cette fonction permettra de générer des analyses spécifiques selon vos besoins.")

# Options d'export
def export_options(manager):
    st.subheader("📥 Options d'export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Export en Markdown
        st.markdown("### Markdown")
        if st.button("📄 Exporter en Markdown", key="export_md", use_container_width=True):
            try:
                md_path = manager.state.export_as_markdown()
                st.success(f"✅ Novella exportée: {md_path}")
                
                with open(md_path, "r", encoding="utf-8") as f:
                    md_content = f.read()
                    b64 = base64.b64encode(md_content.encode()).decode()
                    href = f'<a href="data:file/markdown;base64,{b64}" download="{manager.state.title.replace(" ", "_")}.md">📥 Télécharger le fichier Markdown</a>'
                    st.markdown(href, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Erreur d'export: {e}")
    
    with col2:
        # Export en format texte brut
        st.markdown("### Texte brut")
        if st.button("📄 Exporter en texte brut", key="export_txt", use_container_width=True):
            try:
                txt_content = manager.state.get_all_chapters_as_markdown().replace("# ", "").replace("## ", "")
                b64 = base64.b64encode(txt_content.encode()).decode()
                href = f'<a href="data:file/txt;base64,{b64}" download="{manager.state.title.replace(" ", "_")}.txt">📥 Télécharger le fichier texte</a>'
                st.markdown(href, unsafe_allow_html=True)
                st.success("✅ Fichier texte préparé pour le téléchargement")
            except Exception as e:
                st.error(f"Erreur d'export: {e}")
    
    # Option d'export de la structure
    st.markdown("### Structure narrative")
    if st.button("📋 Exporter la structure narrative", key="export_structure", use_container_width=True):
        try:
            # Créer un document de structure narrative
            structure = f"# Structure narrative de '{manager.state.title}'\n\n"
            
            # Ajouter le concept
            structure += "## Concept\n\n"
            structure += manager.state.concept_details + "\n\n"
            
            # Ajouter les arcs narratifs
            structure += "## Arcs narratifs\n\n"
            structure += manager.state.arcs + "\n\n"
            
            # Ajouter la chronologie
            structure += "## Chronologie\n\n"
            structure += manager.state.get_timeline_context() + "\n\n"
            
            # Ajouter les résumés de chapitres
            structure += "## Résumés des chapitres\n\n"
            for summary in manager.state.summaries:
                structure += f"### Chapitre {summary['number']}\n\n"
                structure += summary['summary'] + "\n\n"
            
            # Créer le lien de téléchargement
            b64 = base64.b64encode(structure.encode()).decode()
            href = f'<a href="data:file/markdown;base64,{b64}" download="Structure_{manager.state.title.replace(" ", "_")}.md">📥 Télécharger la structure narrative</a>'
            st.markdown(href, unsafe_allow_html=True)
            st.success("✅ Structure narrative préparée pour le téléchargement")
        except Exception as e:
            st.error(f"Erreur d'export de la structure: {e}")

# Fonction pour retourner à l'accueil
def return_to_home():
    st.session_state["view"] = "home"
    if "active_project" in st.session_state:
        del st.session_state["active_project"]

# Contrôle de navigation principal
if __name__ == "__main__":
    # Définir la vue par défaut si ce n'est pas déjà fait
    if "view" not in st.session_state:
        st.session_state["view"] = "home"
    
    # Afficher la page appropriée
    if st.session_state["view"] == "home":
        home_page()
    else:
        app_page()
    
    # Pied de page
    st.markdown("---")
    st.markdown("NovellaForge © 2025 - Un outil d'écriture assistée par IA")