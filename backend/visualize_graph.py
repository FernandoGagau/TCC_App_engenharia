#!/usr/bin/env python
"""
Script para visualizar o grafo de agentes LangGraph
"""

import requests
import json
from pathlib import Path

def visualize_graph():
    """Chama o endpoint para visualizar o grafo"""

    # URL do endpoint
    url = "http://localhost:8000/agent/visualize"

    print("🔍 Visualizando Grafo de Agentes LangGraph...\n")

    try:
        # Faz a requisição
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        if data.get("success"):
            # Exibe ASCII art
            print("📊 Visualização ASCII do Grafo:")
            print("=" * 50)
            print(data.get("ascii", ""))
            print("=" * 50)

            # Exibe código Mermaid
            print("\n📈 Código Mermaid:")
            print("=" * 50)
            if data.get("mermaid"):
                print(data["mermaid"])

                # Salva em arquivo HTML para visualização
                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>LangGraph Agent Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{ startOnLoad: true }});</script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{ color: #333; }}
        .mermaid {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <h1>🤖 LangGraph Multi-Agent System Visualization</h1>
    <div class="mermaid">
{data["mermaid"]}
    </div>

    <h2>ASCII Representation:</h2>
    <pre style="background: #1e1e1e; color: #0ff; padding: 20px; border-radius: 8px;">
{data.get("ascii", "")}
    </pre>
</body>
</html>
"""

                # Salva o HTML
                with open("graph_visualization.html", "w") as f:
                    f.write(html_content)

                print("\n✅ Arquivos gerados:")
                print("  - graph_visualization.html (abra no navegador)")
                print("  - graph_mermaid.md (código Mermaid)")
                print("  - graph_visualization.png (se graphviz instalado)")

            print("\n" + "=" * 50)
            print(f"📝 {data.get('message', '')}")

        else:
            print(f"❌ Erro: {data.get('error', 'Erro desconhecido')}")

    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar ao servidor.")
        print("   Certifique-se de que o servidor está rodando na porta 8000.")

    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

def check_server_status():
    """Verifica se o servidor está rodando"""
    try:
        response = requests.get("http://localhost:8000/agent/info")
        if response.status_code == 200:
            info = response.json()
            print(f"✅ Servidor Online - Agente: {info.get('name', 'Unknown')}")
            print(f"   Versão: {info.get('version', 'Unknown')}")
            print(f"   Agentes disponíveis: {', '.join(info.get('agents', []))}")
            return True
    except:
        pass
    return False

if __name__ == "__main__":
    print("=" * 50)
    print("   LANGGRAPH AGENT VISUALIZER")
    print("=" * 50)

    # Verifica se o servidor está rodando
    if check_server_status():
        print()
        visualize_graph()
    else:
        print("\n❌ Servidor não está respondendo.")
        print("   Execute: python main.py")