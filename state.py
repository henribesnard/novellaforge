import json
import time
import os
from typing import Dict, List, Any, Tuple

class NovellaState:
    """Classe pour la gestion de l'état de la novella"""
    
    def __init__(self):
        # Informations de base
        self.title = ""
        self.concept = {}
        self.concept_details = ""
        self.arcs = []
        self.characters = []
        self.world = {}
        
        # Contenu généré
        self.chapters = []
        self.summaries = []
        self.compiled_memory = ""
        self.current_chapter = 0
        
        # Suivi avancé
        self.plot_elements = []  # Éléments d'intrigue utilisés
        self.timeline = []  # Points chronologiques établis
        self.chapter_metadata = []  # Métadonnées pour chaque chapitre
        self.contextual_additions = []  # Ajouts contextuels par chapitre
        
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
                if not hasattr(self, "plot_elements"):
                    self.plot_elements = []
                if not hasattr(self, "timeline"):
                    self.timeline = []
                if not hasattr(self, "chapter_metadata"):
                    self.chapter_metadata = []
                if not hasattr(self, "contextual_additions"):
                    self.contextual_additions = []
                
            return True
        except FileNotFoundError:
            return False
    
    def add_chapter(self, chapter_content, chapter_summary, metadata=None):
        """Ajoute un nouveau chapitre et son résumé"""
        self.current_chapter += 1
        
        # Ajouter le chapitre
        self.chapters.append({
            "number": self.current_chapter,
            "content": chapter_content,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Ajouter le résumé
        self.summaries.append({
            "number": self.current_chapter,
            "summary": chapter_summary
        })
        
        # Ajouter les métadonnées si fournies
        if metadata:
            metadata["number"] = self.current_chapter
            self.chapter_metadata.append(metadata)
        
        # Mise à jour de la mémoire compilée (pour simplifier, on prend les 5 derniers résumés)
        recent_summaries = [f"Chapitre {s['number']}: {s['summary']}" for s in self.summaries[-5:]]
        self.compiled_memory = "\n\n".join(recent_summaries)
        
        # Sauvegarde automatique après chaque chapitre
        self.save_to_file()
        
        return self.current_chapter
    
    def update_chapter(self, chapter_number, new_content, new_summary=None, metadata=None):
        """Met à jour un chapitre existant"""
        # Mettre à jour le contenu du chapitre
        for i, chapter in enumerate(self.chapters):
            if chapter["number"] == chapter_number:
                self.chapters[i]["content"] = new_content
                self.chapters[i]["last_modified"] = time.strftime("%Y-%m-%d %H:%M:%S")
                break
        
        # Mettre à jour le résumé si fourni
        if new_summary:
            for i, summary in enumerate(self.summaries):
                if summary["number"] == chapter_number:
                    self.summaries[i]["summary"] = new_summary
                    break
        
        # Mettre à jour les métadonnées si fournies
        if metadata:
            for i, meta in enumerate(self.chapter_metadata):
                if meta["number"] == chapter_number:
                    # Fusionner les nouvelles métadonnées avec les existantes
                    self.chapter_metadata[i].update(metadata)
                    break
            else:
                # Si pas de métadonnées existantes, en créer
                metadata["number"] = chapter_number
                self.chapter_metadata.append(metadata)
        
        # Reconstruire la mémoire compilée
        recent_summaries = [f"Chapitre {s['number']}: {s['summary']}" for s in self.summaries[-5:]]
        self.compiled_memory = "\n\n".join(recent_summaries)
        
        # Sauvegarde automatique
        self.save_to_file()
        
        return chapter_number
    
    def add_plot_element(self, element_name, description, chapter_number):
        """Ajoute un élément d'intrigue"""
        element = {
            "name": element_name,
            "description": description,
            "introduced_in": chapter_number,
            "last_mentioned_in": chapter_number
        }
        
        # Vérifier si l'élément existe déjà
        for i, existing in enumerate(self.plot_elements):
            if existing["name"] == element_name:
                # Mettre à jour l'élément existant
                self.plot_elements[i]["last_mentioned_in"] = chapter_number
                return self.plot_elements[i]
        
        # Ajouter le nouvel élément
        self.plot_elements.append(element)
        self.save_to_file()
        
        return element
    
    def add_timeline_event(self, event_name, description, when, chapter_number):
        """Ajoute un événement dans la chronologie"""
        event = {
            "name": event_name,
            "description": description,
            "when": when,  # Peut être relatif ("3 jours après le début") ou absolu ("15 juin 1242")
            "mentioned_in": chapter_number
        }
        
        self.timeline.append(event)
        # Trier la timeline par ordre chronologique (si possible)
        # Cette logique pourrait être complexifiée pour gérer différents formats de date
        
        self.save_to_file()
        return event
    
    def add_contextual_element(self, element_type, content, chapter_number):
        """Ajoute un élément contextuel fourni par l'utilisateur"""
        element = {
            "type": element_type,  # Ex: "character", "setting", "plot"
            "content": content,
            "chapter_number": chapter_number,
            "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.contextual_additions.append(element)
        self.save_to_file()
        
        return element
    
    def get_used_plot_elements(self, last_n_chapters=3):
        """Renvoie les éléments d'intrigue récemment utilisés"""
        if not self.chapters:
            return []
        
        current = self.current_chapter
        min_chapter = max(1, current - last_n_chapters + 1)
        
        recent_elements = []
        for element in self.plot_elements:
            if min_chapter <= element["last_mentioned_in"] <= current:
                recent_elements.append(element)
        
        return recent_elements
    
    def get_timeline_context(self):
        """Renvoie le contexte temporel actuel"""
        if not self.timeline:
            return "Aucun événement temporel établi."
        
        # Trier les événements par leur mention dans les chapitres
        sorted_events = sorted(self.timeline, key=lambda x: x["mentioned_in"], reverse=True)
        
        # Prendre les 5-10 événements les plus récents ou importants
        recent_events = sorted_events[:10]
        
        context = "Chronologie établie:\n"
        for event in recent_events:
            context += f"- {event['name']} ({event['when']}): {event['description']} [Ch.{event['mentioned_in']}]\n"
        
        return context
    
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