import streamlit as st
import os
from dotenv import load_dotenv
import base64
from utils.model_manager import ModelManager
from state import NovellaState
from novella_manager import NovellaForgeManager

# Chargement des variables d'environnement
load_dotenv()

# Titre de l'application
st.title("NovellaForge - Générateur de Mini-Novellas")

# Initialisation du gestionnaire
@st.cache_resource
def get_manager():
    model_manager = ModelManager()
    state = NovellaState()
    return NovellaForgeManager(model_manager, state)

manager = get_manager()

# Vérifier si une novella existe déjà
has_existing_novella = manager.state.load_from_file()

# Interface principale
tabs = st.tabs(["Concept", "Chapitres", "Export"])

# Onglet Concept
with tabs[0]:
    st.header("Définition du Concept")
    
    if has_existing_novella and manager.state.concept:
        st.success(f"Concept existant: {manager.state.title}")
        
        if st.button("Réinitialiser"):
            manager.state = NovellaState()
            st.rerun()  # Correction de experimental_rerun
    else:
        with st.form("concept_form"):
            title = st.text_input("Titre de la novella", "")
            genre = st.text_input("Genre principal", "Fantasy")
            setting = st.text_area("Univers", "Un monde médiéval avec de la magie")
            protagonist = st.text_area("Protagoniste(s)", "Un jeune apprenti magicien")
            antagonist = st.text_area("Antagoniste ou conflit", "Un ancien mal qui s'éveille")
            
            if st.form_submit_button("Générer le concept"):
                if not title:
                    st.error("Le titre est obligatoire")
                else:
                    with st.spinner("Génération du concept..."):
                        try:
                            user_input = {
                                "title": title,
                                "genre": genre,
                                "setting": setting,
                                "protagonist": protagonist,
                                "antagonist": antagonist
                            }
                            
                            # Initialisation de la novella
                            manager.initialize_novella(user_input)
                            st.success("Concept généré!")
                            st.rerun()  # Correction de experimental_rerun
                        except Exception as e:
                            st.error(f"Erreur: {e}")

# Onglet Chapitres
with tabs[1]:
    st.header("Chapitres")
    
    if not has_existing_novella:
        st.warning("Créez d'abord un concept dans l'onglet précédent")
    else:
        if not manager.state.chapters:
            st.info("Aucun chapitre généré")
            
            if st.button("Générer le premier chapitre"):
                with st.spinner("Génération du chapitre 1..."):
                    try:
                        result = manager.produce_chapter()
                        st.success("Chapitre 1 généré!")
                        st.rerun()  # Correction de experimental_rerun
                    except Exception as e:
                        st.error(f"Erreur: {e}")
        else:
            # Afficher les chapitres existants
            for idx, chapter in enumerate(manager.state.chapters):
                with st.expander(f"Chapitre {chapter['number']}"):
                    st.write(chapter['content'])
            
            # Bouton pour générer le chapitre suivant
            if st.button(f"Générer le chapitre {manager.state.current_chapter + 1}"):
                with st.spinner(f"Génération du chapitre {manager.state.current_chapter + 1}..."):
                    try:
                        result = manager.produce_chapter()
                        st.success(f"Chapitre {manager.state.current_chapter} généré!")
                        st.rerun()  # Correction de experimental_rerun
                    except Exception as e:
                        st.error(f"Erreur: {e}")

# Onglet Export
with tabs[2]:
    st.header("Export")
    
    if not has_existing_novella or not manager.state.chapters:
        st.warning("Générez d'abord des chapitres")
    else:
        if st.button("Exporter en Markdown"):
            try:
                md_path = manager.state.export_as_markdown()
                st.success(f"Novella exportée: {md_path}")
                
                with open(md_path, "r", encoding="utf-8") as f:
                    md_content = f.read()
                    b64 = base64.b64encode(md_content.encode()).decode()
                    href = f'<a href="data:file/markdown;base64,{b64}" download="novella.md">Télécharger le fichier</a>'
                    st.markdown(href, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Erreur d'export: {e}")