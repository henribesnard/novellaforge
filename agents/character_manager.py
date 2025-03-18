from crewai import Agent

class CharacterManager:
    def __init__(self, llm):
        self.llm = llm
    
    def create(self):
        return Agent(
            role="Gestionnaire de Personnages",
            goal="Gérer tous les personnages de la novella et assurer leur cohérence et leur évolution sur 500+ chapitres",
            backstory="""Vous êtes spécialisé dans la création et la gestion de personnages complexes et évolutifs.
            Vous maintenez une base de données mentale de tous les personnages, leurs traits, motivations, relations,
            et vous assurez que leur développement reste cohérent tout en étant dynamique sur la durée.
            Vous savez comment faire évoluer les personnages de manière organique et convaincante.""",
            llm=self.llm,
            verbose=True
        )