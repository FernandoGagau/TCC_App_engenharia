"""
Definição do grafo para LangGraph Studio
"""

import os
# Define flag para o Studio
os.environ["LANGGRAPH_STUDIO"] = "true"

from domain.agents.construction_agent import ConstructionAnalysisAgent

# Inicializa o agente (sem checkpointer para o Studio)
construction_agent_instance = ConstructionAnalysisAgent()

# Exporta o grafo compilado para o LangGraph Studio
agent = construction_agent_instance.graph
