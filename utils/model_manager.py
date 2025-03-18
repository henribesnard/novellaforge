import os
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ChatMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from typing import Any, List, Optional, Dict
from pydantic import Field

class ModelManager:
    """Gestionnaire des modèles LLM avec fallback"""
    
    def __init__(self):
        # Vérifier si le modèle DeepSeek est disponible
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        self.primary_available = False
        self.fallback_available = False
        
        # Tester DeepSeek
        if self.deepseek_api_key:
            try:
                self.deepseek_client = OpenAI(
                    api_key=self.deepseek_api_key,
                    base_url="https://api.deepseek.com/v1"
                )
                
                # Test simple
                response = self.deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": "Test"}],
                    max_tokens=5
                )
                self.primary_available = True
                print("Connexion à DeepSeek établie avec succès")
            except Exception as e:
                print(f"Erreur lors de l'initialisation de DeepSeek: {e}")
        
        # Tester OpenAI comme fallback
        if self.openai_api_key:
            try:
                self.openai_model = ChatOpenAI(
                    model_name="gpt-4",
                    api_key=self.openai_api_key,
                    temperature=0.7
                )
                self.fallback_available = True
                print("Connexion à OpenAI établie avec succès")
            except Exception as e:
                print(f"Erreur lors de l'initialisation d'OpenAI: {e}")
    
    def get_model(self):
        """Renvoie le modèle à utiliser"""
        if self.primary_available:
            # Utiliser DeepSeek
            print("Utilisation du modèle DeepSeek")
            
            # Définition de la classe en dehors de la méthode
            class DeepSeekChatModel(BaseChatModel):
                """Wrapper LangChain pour DeepSeek"""
                client: Any = Field(description="Client OpenAI pour DeepSeek")
                model_name: str = Field(default="deepseek-chat")
                temperature: float = Field(default=0.7)
                
                def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                    # Convertir les messages LangChain en format OpenAI
                    openai_messages = []
                    for message in messages:
                        if isinstance(message, HumanMessage):
                            openai_messages.append({"role": "user", "content": message.content})
                        elif isinstance(message, AIMessage):
                            openai_messages.append({"role": "assistant", "content": message.content})
                        elif isinstance(message, SystemMessage):
                            openai_messages.append({"role": "system", "content": message.content})
                        elif isinstance(message, ChatMessage):
                            openai_messages.append({"role": message.role, "content": message.content})
                    
                    # Appeler l'API DeepSeek
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=openai_messages,
                        temperature=self.temperature,
                        stop=stop,
                        **kwargs
                    )
                    
                    # Convertir la réponse en format LangChain
                    message = AIMessage(content=response.choices[0].message.content)
                    generation = ChatGeneration(message=message)
                    return ChatResult(generations=[generation])
                
                @property
                def _llm_type(self):
                    return "deepseek-chat"
            
            # Créer une instance avec le client explicitement passé
            return DeepSeekChatModel(client=self.deepseek_client)
            
        elif self.fallback_available:
            # Utiliser OpenAI comme fallback
            print("Utilisation du modèle de fallback (OpenAI)")
            return self.openai_model
        else:
            raise Exception("Aucun modèle LLM disponible. Vérifiez vos clés API.")