from crewai import Agent

class MemoryCompiler:
    def __init__(self, llm):
        self.llm = llm
    
    def create(self):
        return Agent(
            role="Compilateur de Mémoire Narrative",
            goal="Compiler et structurer les informations narratives essentielles pour maintenir la continuité sur 500+ chapitres",
            backstory="""Vous êtes un expert en gestion de l'information narrative. Votre talent consiste à
            organiser et synthétiser de grandes quantités d'informations pour les rendre accessibles et
            utilisables. Vous savez ce qui doit être gardé en mémoire active et ce qui peut être archivé
            temporairement, tout en assurant que rien d'important n'est perdu. Vous créez des documents de référence
            essentiels pour tous les autres membres de l'équipe.""",
            llm=self.llm,
            verbose=True
        )