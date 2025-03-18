import json
import time
import os
from typing import Dict, List, Any

class NovellaState:
    """Classe pour la gestion de l'état de la novella"""
    
    def __init__(self):
        # Informations de base
        self.title = ""
        self.concept = {}
        self.concept_details = ""  # Ajout de l'attribut manquant
        self.arcs = []
        self.characters = []
        self.world = {}
        
        # Contenu généré
        self.chapters = []
        self.summaries = []
        self.compiled_memory = ""
        self.current_chapter = 0
        
        # Créer le dossier data s'il n'existe pas
        os.makedirs("data", exist_ok=True)
    
    def save_to_file(self, filename="data/novella_state.json"):
        """Sauvegarde l'état actuel dans un fichier JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.__dict__, f, ensure_ascii=False, indent=4)
        return filename
    
    def load_from_file(self, filename="data/novella_state.json"):
        """Charge l'état depuis un fichier JSON"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key, value in data.items():
                    setattr(self, key, value)
                
                # Ajouter des attributs par défaut s'ils n'existent pas
                if not hasattr(self, "concept_details"):
                    self.concept_details = ""
                
            return True
        except FileNotFoundError:
            return False
    
    def add_chapter(self, chapter_content, chapter_summary):
        """Ajoute un nouveau chapitre et son résumé"""
        self.current_chapter += 1
        self.chapters.append({
            "number": self.current_chapter,
            "content": chapter_content,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        self.summaries.append({
            "number": self.current_chapter,
            "summary": chapter_summary
        })
        
        # Mise à jour de la mémoire compilée (pour simplifier, on prend les 5 derniers résumés)
        recent_summaries = [f"Chapitre {s['number']}: {s['summary']}" for s in self.summaries[-5:]]
        self.compiled_memory = "\n\n".join(recent_summaries)
        
        # Sauvegarde automatique après chaque chapitre
        self.save_to_file()
        
        return self.current_chapter
    
    def get_chapter_as_markdown(self, chapter_number):
        """Renvoie un chapitre au format Markdown"""
        for chapter in self.chapters:
            if chapter["number"] == chapter_number:
                title = f"# Chapitre {chapter_number}"
                return f"{title}\n\n{chapter['content']}"
        return None
    
    def get_all_chapters_as_markdown(self):
        """Renvoie tous les chapitres au format Markdown"""
        result = f"# {self.title}\n\n"
        for chapter in self.chapters:
            result += f"## Chapitre {chapter['number']}\n\n{chapter['content']}\n\n"
        return result
    
    def export_as_markdown(self, filename="data/novella.md"):
        """Exporte la novella complète en fichier Markdown"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.get_all_chapters_as_markdown())
        return filename