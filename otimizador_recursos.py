"""Roda Liso - Liberação de RAM/CPU com confirmação do usuário.

Fluxo:
  1. monitor.py chama verificar_recursos() a cada medição.
  2. Se CPU ou RAM ficar >= limite por LEITURAS_SEGUIDAS leituras, o módulo procura
     aplicativos em segundo plano que estejam na lista CANDIDATOS.
  3. Mostra uma janela com a lista (nome, RAM e nº de processos) e pergunta Sim/Não.
  4. Se Sim: pede o fechamento "educado" (taskkill sem /F, o app pode salvar o estado);
     o que não fechar em 4 s é encerrado à força.

Segurança (várias camadas):
  - Só entra quem está em CANDIDATOS (lista permitida, e não uma lista de proibidos).
  - _eh_protegido() ainda barra: jogos, PresentMon, Python/Roda Liso, qualquer coisa
    dentro da pasta do Windows e processos de outros usuários/SYSTEM.
  - Nada é fechado sem o usuário clicar em Sim.
"""
import ctypes
import os
import subprocess
import time

import psutil

# ---------------- Configuração ----------------
LIMITE_PADRAO = 95.0       # % de CPU ou RAM que dispara a sugestão
LEITURAS_SEGUIDAS = 3      # evita disparar por um pico isolado (3 x ~3 s)
COOLDOWN_S = 300           # depois de perguntar, só pergunta de novo após 5 min
MIN_RAM_MB = 200           # ignora apps que ocupam pouca RAM (não vale incomodar)
MIN_CPU_PCT = 1.0          # em alerta de CPU, só lista apps que realmente usam CPU

# nome do processo (minúsculo) -> nome amigável. Edite à vontade.
CANDIDATOS = {
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Mozilla Firefox",
    "brave.exe": "Brave",
    "opera.exe": "Opera",
    "discord.exe": "Discord",
    "spotify.exe": "Spotify",
    "telegram.exe": "Telegram",
    "whatsapp.exe": "WhatsApp",
    "ms-teams.exe": "Microsoft Teams",
    "teams.exe": "Microsoft Teams",
    "onedrive.exe": "OneDrive",
    "epicgameslauncher.exe": "Epic Games Launcher",
    # Só a interface web da Steam. Fechar steam.exe pode derrubar o jogo, então não está aqui.
    # Efeito colateral: o overlay (Shift+Tab) fica indisponível até reabrir a Steam.
    "steamwebhelper.exe": "Steam (interface/overlay)",
}

# Nunca tocar, mesmo que alguém coloque por engano em CANDIDATOS
PROTEGIDOS = {
    "witcher3.exe", "cyberpunk2077.exe", "cs2.exe", "gta5.exe", "rdr2.exe",
    "presentmon.exe", "python.exe", "pythonw.exe", "code.exe",
    "explorer.exe", "dwm.exe", "csrss.exe", "winlogon.exe", "services.exe",
    "lsass.exe", "svchost.exe", "system", "steam.exe",
}

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_leituras_criticas = 0
_ultimo_alerta = 0.0


def _pausado() -> bool:
    return os.environ.get("RODALISO_MONITOR_ATIVO", "True").strip().lower() != "true"


def _eh_protegido(proc: psutil.Process, nome: str) -> bool:
    if nome in PROTEGIDOS or proc.pid in (os.getpid(), os.getppid()):
        return True
    try:
        exe = (proc.exe() or "").lower()
        windir = os.environ.get("WINDIR", r"C:\Windows").lower()
        if exe.startswith(windir):
            return True
        # processo de outro usuário (SYSTEM, serviços): não é nosso para fechar
        dono = (proc.username() or "").split("\\")[-1].lower()
        if dono != psutil.Process().username().split("\\")[-1].lower():
            return True
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        return True  # na dúvida, protege
    return False


def _coletar_candidatos() -> dict:
    """Agrupa por aplicativo: {nome_exe: {'nome', 'ram_mb', 'cpu', 'procs'}}."""
    achados = []
    for p in psutil.process_iter(["name"]):
        nome = (p.info["name"] or "").lower()
        if nome in CANDIDATOS and not _eh_protegido(p, nome):
            try:
                p.cpu_percent(None)  # "aquece" o contador de CPU do processo
                achados.append((nome, p))
            except psutil.NoSuchProcess:
                pass

    time.sleep(0.5)  # janela curta para medir o CPU de cada processo
    n_cpu = psutil.cpu_count() or 1
    grupos = {}
    for nome, p in achados:
        try:
            rss = p.memory_info().rss
            cpu = p.cpu_percent(None) / n_cpu
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        g = grupos.setdefault(nome, {"nome": CANDIDATOS[nome], "ram_mb": 0.0, "cpu": 0.0, "procs": 0})
        g["ram_mb"] += rss / (1024 ** 2)
        g["cpu"] += cpu
        g["procs"] += 1
    return grupos


def _janela_confirmacao(jogo: str, motivo: str, grupos: dict) -> bool:
    linhas = []
    for g in sorted(grupos.values(), key=lambda x: x["ram_mb"], reverse=True):
        ram = f"{g['ram_mb'] / 1024:.1f} GB" if g["ram_mb"] >= 1024 else f"{g['ram_mb']:.0f} MB"
        linhas.append(f"  • {g['nome']} — {ram}, CPU {g['cpu']:.0f}% ({g['procs']} processos)")
    total_gb = sum(g["ram_mb"] for g in grupos.values()) / 1024

    texto = (
        f"{motivo}\n\n"
        f"Sugerimos fechar estes aplicativos em segundo plano para melhorar o {jogo}:\n\n"
        + "\n".join(linhas)
        + f"\n\nRAM a liberar (aprox.): {total_gb:.1f} GB\n\n"
        "O jogo, o Windows e o Roda Liso NÃO serão fechados.\n"
        "Salve o que estiver aberto (abas, mensagens) antes de clicar em Sim.\n\n"
        "Fechar esses aplicativos agora?"
    )
    # 4 = Sim/Não | 48 = ícone de aviso | 4096 = sempre no topo
    return ctypes.windll.user32.MessageBoxW(0, texto, "Roda Liso - Recursos no limite", 4 | 48 | 4096) == 6


def _fechar(grupos: dict) -> str:
    # 1) pedido educado (sem /F): o app pode salvar o estado e fechar sozinho
    for exe in grupos:
        subprocess.run(["taskkill", "/IM", exe], capture_output=True, creationflags=_NO_WINDOW)
    time.sleep(4)

    # 2) o que ainda estiver vivo é encerrado à força
    for exe in grupos:
        subprocess.run(["taskkill", "/F", "/IM", exe], capture_output=True, creationflags=_NO_WINDOW)

    nomes = ", ".join(g["nome"] for g in grupos.values())
    return f"Aplicativos fechados: {nomes}."


def verificar_recursos(jogo: str, cpu_pct: float, ram_pct: float, limite: float = LIMITE_PADRAO):
    """Chame a cada medição. Devolve uma mensagem de status ou None (nada aconteceu)."""
    global _leituras_criticas, _ultimo_alerta

    if _pausado():
        _leituras_criticas = 0
        return None

    ram_critica = ram_pct >= limite
    cpu_critica = cpu_pct >= limite
    if not (ram_critica or cpu_critica):
        _leituras_criticas = 0
        return None

    _leituras_criticas += 1
    if _leituras_criticas < LEITURAS_SEGUIDAS:
        return None
    if time.monotonic() - _ultimo_alerta < COOLDOWN_S:
        return None

    # Monta o motivo com números reais (ex.: "7.1 GB / 7.2 GB")
    mem = psutil.virtual_memory()
    partes = []
    if ram_critica:
        partes.append(f"A RAM está no limite: {mem.used / 1024**3:.1f} GB / {mem.total / 1024**3:.1f} GB ({ram_pct:.0f}%).")
    if cpu_critica:
        partes.append(f"A CPU está no limite: {cpu_pct:.0f}% de uso.")
    motivo = " ".join(partes)

    grupos = _coletar_candidatos()
    if ram_critica and not cpu_critica:
        grupos = {k: v for k, v in grupos.items() if v["ram_mb"] >= MIN_RAM_MB}
    if cpu_critica and not ram_critica:
        grupos = {k: v for k, v in grupos.items() if v["cpu"] >= MIN_CPU_PCT}
    if ram_critica and cpu_critica:
        grupos = {k: v for k, v in grupos.items() if v["ram_mb"] >= MIN_RAM_MB or v["cpu"] >= MIN_CPU_PCT}

    _leituras_criticas = 0
    _ultimo_alerta = time.monotonic()  # conta mesmo se não houver o que sugerir (evita ficar escaneando)

    if not grupos:
        return f"{motivo} Nenhum aplicativo em segundo plano seguro para fechar foi encontrado."

    if _pausado():  # pausou enquanto escaneava
        return None

    if not _janela_confirmacao(jogo, motivo, grupos):
        return "Sugestão de liberar recursos recusada pelo usuário (nada foi fechado)."
    if _pausado():
        return "Agente pausado: nenhum aplicativo foi fechado."
    return _fechar(grupos)
