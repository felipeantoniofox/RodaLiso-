import os
import shutil
import psutil
import subprocess
import time
import configparser
from typing import Optional, Tuple
from langchain_core.tools import tool

JOGOS_PROTEGIDOS = [
    "witcher3.exe", "cyberpunk2077.exe", "cs2.exe", "gta5.exe", "rdr2.exe"
]

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

try:
    from roda_liso import PRESETS_EMPURRAO
except ImportError:
    PRESETS_EMPURRAO = {}

def ler_qualidade_atual(jogo: str) -> str:
    """
    Examina o arquivo de configuração ativo do jogo e estima o nível gráfico atual.
    """
    user_home = os.path.expanduser("~")
    local_app_data = os.environ.get('LOCALAPPDATA', '')

    if "witcher" in jogo.lower():
        caminho_config = os.path.join(user_home, "Documents", "The Witcher 3", "user.settings")
        if not os.path.exists(caminho_config):
            return "Desconhecido"

        try:
            config = configparser.ConfigParser(strict=False)
            config.read(caminho_config, encoding='utf-8')
            tex_quality = config.getint('Rendering', 'TextureQuality', fallback=1)
            
            if tex_quality <= 0:
                return "Baixo"
            elif tex_quality == 1:
                return "Médio"
            elif tex_quality >= 2:
                return "Alto"
        except Exception:
            return "Médio"

    elif "cyberpunk" in jogo.lower():
        caminho_config = os.path.join(local_app_data, "CD Projekt Red", "Cyberpunk 2077", "UserSettings.json")
        if os.path.exists(caminho_config):
            return "Médio"

    return "Médio"

def gerenciar_processo_e_backup(jogo: str) -> Tuple[Optional[str], str]:
    """
    Força o encerramento do processo do jogo, garante a criação da pasta de backup e copia a config original.
    """
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PASTA_BACKUP_BASE = os.path.join(BASE_DIR, "Rodaliso_Backups")

    nome_processo = "witcher3.exe" if "witcher" in jogo.lower() else ""
    caminho_exe = None

    # 1. Encerra o jogo ativamente para liberar a trava do arquivo (lock) e evitar reescrita
    if nome_processo:
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == nome_processo.lower():
                    caminho_exe = proc.info['exe']
                    print(f"[RODALISO] Encerrando {nome_processo} para liberar arquivos de configuração...")
                    proc.kill()
                    proc.wait(timeout=5)
                    break
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.TimeoutExpired):
                pass

    # 2. Localização da pasta de configuração original do usuário
    caminho_original_usuario = None
    if jogo in PRESETS_EMPURRAO:
        for caminho_teste in PRESETS_EMPURRAO[jogo].get("caminhos_comuns", []):
            if os.path.exists(caminho_teste):
                caminho_original_usuario = caminho_teste
                break

    if not caminho_original_usuario:
        return caminho_exe, "Arquivo de configuração original do jogo não encontrado."

    # 3. Criação do Backup Isolado na pasta do Projeto
    pasta_backup_jogo = os.path.join(PASTA_BACKUP_BASE, jogo)
    os.makedirs(pasta_backup_jogo, exist_ok=True)
    
    nome_arquivo_alvo = PRESETS_EMPURRAO[jogo]["arquivo_alvo"]
    caminho_backup_final = os.path.join(pasta_backup_jogo, f"{nome_arquivo_alvo}.bak")

    if not os.path.exists(caminho_backup_final):
        shutil.copyfile(caminho_original_usuario, caminho_backup_final)
        print(f"[RODALISO] Backup limpo preservado em: {caminho_backup_final}")

    return caminho_exe, "Backup e encerramento concluídos."

def aplicar_preset_por_nivel(jogo: str, nivel_escolhido: str) -> Tuple[bool, str]:
    """
    Aplica o preset gráfico físico mapeado no dicionário PRESETS_EMPURRAO.
    """
    if jogo not in PRESETS_EMPURRAO:
        return False, f"Jogo '{jogo}' não cadastrado no banco do Roda Liso."

    dados_jogo = PRESETS_EMPURRAO[jogo]
    
    if nivel_escolhido not in dados_jogo["niveis"]:
        return False, f"Nível '{nivel_escolhido}' não encontrado nas opções do jogo."

    caminho_preset_fonte = dados_jogo["niveis"][nivel_escolhido]["arquivo"]

    if not os.path.exists(caminho_preset_fonte):
        return False, f"Arquivo físico do preset não encontrado em: {caminho_preset_fonte}"

    # Encerra o jogo e faz o backup
    caminho_exe, status = gerenciar_processo_e_backup(jogo)

    # Localiza o arquivo de destino do usuário
    caminho_original_usuario = None
    for caminho_teste in dados_jogo.get("caminhos_comuns", []):
        if os.path.exists(caminho_teste):
            caminho_original_usuario = caminho_teste
            break

    if not caminho_original_usuario:
        return False, "Caminho do arquivo de configuração do usuário não foi encontrado."

    try:
        shutil.copyfile(caminho_preset_fonte, caminho_original_usuario)
        print(f"[RODALISO] Preset '{nivel_escolhido}' aplicado em: {caminho_original_usuario}")
        return True, f"Preset '{nivel_escolhido}' aplicado com sucesso em {jogo}."
    except Exception as e:
        return False, f"Erro na cópia do arquivo: {e}"

# Tools do Agente para Otimizações de SO
@tool
def alterar_prioridade_jogo(nome_executavel: str) -> str:
    """Altera a prioridade do processo do jogo no Windows para ALTA (High Priority)."""
    try:
        nome_executavel = nome_executavel.lower()
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and proc.info['name'].lower() == nome_executavel:
                proc.nice(psutil.HIGH_PRIORITY_CLASS)
                return f"[Sucesso] Prioridade de '{nome_executavel}' alterada para ALTA."
        return f"[Aviso] Processo '{nome_executavel}' não encontrado."
    except Exception as e:
        return f"[Erro] Falha ao alterar prioridade: {e}"

@tool
def encerrar_processos_pesados() -> str:
    """Encerra navegadores e aplicadores em segundo plano para liberar memória RAM."""
    alvos = ['chrome.exe', 'msedge.exe', 'discord.exe', 'epicgameslauncher.exe', 'steamwebhelper.exe']
    encerrados = set()
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            nome = proc.info['name']
            if not nome: continue
            nome_lower = nome.lower()
            if nome_lower in JOGOS_PROTEGIDOS or nome_lower == "presentmon.exe": continue
            if nome_lower in alvos:
                try:
                    proc.kill()
                    encerrados.add(nome_lower)
                except Exception: pass
        if encerrados:
            return f"[Sucesso] Processos encerrados: {', '.join(encerrados)}."
        return "[Aviso] Nenhum processo pesado encontrado."
    except Exception as e:
        return f"[Erro] Falha ao encerrar processos: {e}"

ferramentas_rodaliso = [alterar_prioridade_jogo, encerrar_processos_pesados]