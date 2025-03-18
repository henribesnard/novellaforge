from crewai import Agent

class ChapterSummarizer:
    def __init__(self, llm):
        self.llm = llm
    
    def create(self):
        return Agent(
            role="Résumeur de Chapitres",
            goal="Créer des résumés concis et informatifs de chaque chapitre pour maintenir la continuité narrative",
            backstory="""Vous excellez dans l'art de distiller l'information essentielle. Vous savez identifier
            les éléments clés d'un chapitre - développements de l'intrigue, évolutions des personnages,
            révélations importantes - et les présenter de manière concise et structurée.
            Vos résumés sont complets mais jamais verbeux, capturant l'essence de longs contenus.""",
            llm=self.llm,
            verbose=True
        )