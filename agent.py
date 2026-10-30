import os
import time
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, "api.env")
load_dotenv(env_path, override=True)  # caminho absoluto: funciona mesmo abrindo o programa de outra pasta

from roda_liso import PRESETS_EMPURRAO
from tools import aplicar_preset_por_nivel, ler_qualidade_atual
from confirmacao import abrir_janela_confirmacao
from nitidez import aplicar_nitidez

ATALHOS_JOGOS = {
    "The Witcher 3 2015": "steam://rungameid/292030",
    "Cyberpunk 2077": "steam://rungameid/1091500",
    "CS 2": "steam://rungameid/730",
    "GTA V": "steam://rungameid/271590",
    "Red Dead Redemption 2": "steam://rungameid/1174180"
}

def _agente_pausado() -> bool:
    """Mesma flag do botão PAUSAR do Roda Liso (RODALISO_MONITOR_ATIVO)."""
    return os.environ.get("RODALISO_MONITOR_ATIVO", "True").strip().lower() != "true"


class RodalisoState(TypedDict):
    telemetria: dict
    gap_desempenho: float
    qualidade_atual: str
    recomendacao: dict
    aprovado: Optional[bool]
    status_final: str

# Configuração dinâmica do modelo via variável de ambiente (padrão: openai/gpt-oss-20b)
nome_modelo = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
llm = ChatGroq(model_name=nome_modelo, temperature=0.2)

def node_calcular_deficit(state: RodalisoState) -> dict:
    fps_atual = state["telemetria"].get("fps_atual", 20.0)
    fps_alvo = state["telemetria"].get("fps_alvo", 30.0)
    gap = ((fps_alvo - fps_atual) / fps_alvo) * 100
    
    jogo = state["telemetria"]["jogo"]
    qualidade = ler_qualidade_atual(jogo)
    
    return {
        "gap_desempenho": max(0.0, gap),
        "qualidade_atual": qualidade
    }

def node_sugerir_otimizacao(state: RodalisoState) -> dict:
    gap = state["gap_desempenho"]
    jogo = state["telemetria"]["jogo"]
    qualidade_atual = state["qualidade_atual"]
    
    niveis_disponiveis = []
    if jogo in PRESETS_EMPURRAO:
        niveis_disponiveis = list(PRESETS_EMPURRAO[jogo]["niveis"].keys())
        
    prompt = (
        f"O jogo '{jogo}' está rodando a {state['telemetria']['fps_atual']} FPS (Meta: {state['telemetria']['fps_alvo']} FPS). "
        f"Déficit de desempenho: {gap:.1f}%.\n"
        f"Qualidade gráfica atual detectada no arquivo: {qualidade_atual}.\n"
        f"Presets disponíveis no Roda Liso: {niveis_disponiveis}.\n"
        f"Regra Estrita: Se o jogo estiver em 'Alto' ou 'Médio', NÃO recomende o nível 'Mais Baixo'. Recomende uma transição gradual para o 'Nível 2 - Baixo'. "
        f"Apenas recomende 'Nível 1 - Mais Baixo (Máx. FPS)' se o jogo já estiver no 'Baixo' ou se o déficit for >= 35%.\n"
        f"Responda em 1 frase indicando qual preset escolher e o motivo."
    )
    
    resposta = llm.invoke(prompt)
    
    # Seleção da chave lógica do preset
    if qualidade_atual in ["Alto", "Ultra"] and gap < 35.0:
        nivel_escolhido = "Nível 3 - Normal"
    elif gap >= 35.0 or qualidade_atual == "Baixo":
        nivel_escolhido = "Nível 1 - Mais Baixo (Máx. FPS)"
    elif gap >= 20.0:
        nivel_escolhido = "Nível 2 - Baixo"
    else:
        nivel_escolhido = "Nível 3 - Normal"
        
    return {
        "recomendacao": {
            "mensagem": resposta.content,
            "jogo": jogo,
            "nivel_preset": nivel_escolhido
        }
    }

def node_notificar_windows(state: RodalisoState) -> dict:
    if _agente_pausado():  # pausou enquanto a IA pensava: não incomoda o jogador com a janela
        return {"aprovado": False, "status_final": "Agente pausado: sugestão descartada."}
    gap = state["gap_desempenho"]
    jogo = state["telemetria"]["jogo"]
    nivel = state["recomendacao"]["nivel_preset"]
    mensagem = state["recomendacao"]["mensagem"]
    
    # Dispara a janela modal com atributos top-most do Windows
    aprovado = abrir_janela_confirmacao(
        nome_jogo=jogo, 
        nivel_sugerido=nivel, 
        gap_desempenho=gap, 
        mensagem_ia=mensagem
    )
    return {"aprovado": aprovado}

def node_executar_mudancas(state: RodalisoState) -> dict:
    if not state.get("aprovado"):
        return {"status_final": "Operação recusada pelo usuário."}
    if _agente_pausado():  # pausou com a janela aberta: não altera nada
        return {"status_final": "Agente pausado: nenhuma alteração foi feita."}
        
    jogo = state["recomendacao"]["jogo"]
    nivel = state["recomendacao"]["nivel_preset"]
    
    # 1. Aplica o preset (a função encerra o jogo e faz o backup automaticamente)
    sucesso, mensagem = aplicar_preset_por_nivel(jogo, nivel)
    
    # Filtro de nitidez (estilo FSR/CAS via ReShade) no nível escolhido na interface.
    # O jogo já foi fechado pelo passo anterior, então o ReShade.ini pode ser alterado com segurança.
    usar_fsr = os.environ.get("USAR_FSR_1", "False") == "True"
    if sucesso and usar_fsr:
        nivel_nitidez = os.environ.get("FSR_SHARPNESS", "Média (Padrão)")
        ok_nitidez, msg_nitidez = aplicar_nitidez(jogo, nivel_nitidez)
        mensagem += f" | Nitidez: {msg_nitidez}"

    # 2. Reinicia o jogo usando o protocolo de URI registrado na loja (Steam/Epic)
    if sucesso:
        print(f"[AGENTE IA] Aguardando a liberação do arquivo de configurações pelo sistema...")
        time.sleep(3)
        
        atalho = ATALHOS_JOGOS.get(jogo)
        if atalho:
            print(f"[AGENTE IA] Reiniciando {jogo} via protocolo {atalho}...")
            try:
                os.startfile(atalho)
                mensagem += f" | {jogo} reiniciado."
            except Exception as e:
                mensagem += f" | Erro ao reiniciar: {e}"
        else:
            mensagem += " | Atalho de reinício não configurado."
            
    return {"status_final": mensagem}

# Construção do Grafo de Estados
builder = StateGraph(RodalisoState)
builder.add_node("calcular_deficit", node_calcular_deficit)
builder.add_node("sugerir_otimizacao", node_sugerir_otimizacao)
builder.add_node("notificar_windows", node_notificar_windows)
builder.add_node("executar_mudancas", node_executar_mudancas)

builder.set_entry_point("calcular_deficit")
builder.add_edge("calcular_deficit", "sugerir_otimizacao")
builder.add_edge("sugerir_otimizacao", "notificar_windows")

def checar_autorizacao(state: RodalisoState):
    return "executar_mudancas" if state.get("aprovado") else END

builder.add_conditional_edges("notificar_windows", checar_autorizacao)
builder.add_edge("executar_mudancas", END)

agente_rodaliso = builder.compile()