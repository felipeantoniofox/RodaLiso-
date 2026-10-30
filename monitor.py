import os
import time
import shutil
import subprocess
import psutil
from agent import agente_rodaliso
from fps_presentmon import medir_fps_presentmon, rodando_como_admin
from otimizador_recursos import verificar_recursos

PROCESSOS_JOGOS = {
    "witcher3.exe": "The Witcher 3 2015",
    "cyberpunk2077.exe": "Cyberpunk 2077",
    "cs2.exe": "CS 2",
    "gta5.exe": "GTA V",
    "rdr2.exe": "Red Dead Redemption 2"
}

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_avisou_gpu = False


def agente_pausado() -> bool:
    """O botão PAUSAR do Roda Liso grava RODALISO_MONITOR_ATIVO=False e o ATIVAR grava True.
    Sem a variável (monitor.py rodando sozinho no terminal), o agente fica ativo."""
    return os.environ.get("RODALISO_MONITOR_ATIVO", "True").strip().lower() != "true"


def _fps_alvo_atual(padrao: float) -> float:
    """A interface pode mudar a meta de FPS com o agente já rodando (variável RODALISO_FPS_ALVO)."""
    try:
        return float(os.environ.get("RODALISO_FPS_ALVO", padrao))
    except ValueError:
        return padrao


def _dormir(segundos: float) -> bool:
    """Dorme em fatias de 1 s para o PAUSAR funcionar mesmo durante esperas longas.
    Retorna False se o agente foi pausado no meio da espera."""
    fim = time.monotonic() + segundos
    while time.monotonic() < fim:
        if agente_pausado():
            return False
        time.sleep(max(0.0, min(1.0, fim - time.monotonic())))
    return True


def detectar_jogo_ativo():
    """Varre os processos do Windows e retorna o nome do jogo e seu executável se estiver rodando."""
    for proc in psutil.process_iter(['name']):
        try:
            nome_proc = (proc.info['name'] or "").lower()  # 'name' pode vir None (acesso negado)
            if nome_proc in PROCESSOS_JOGOS:
                return PROCESSOS_JOGOS[nome_proc], nome_proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None, None


def _gpu_nvidia():
    """NVIDIA: uso de GPU e VRAM (%) via nvidia-smi."""
    saida = subprocess.run(
        ["nvidia-smi",
         "--query-gpu=utilization.gpu,memory.used,memory.total",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=3, creationflags=_NO_WINDOW
    ).stdout.strip().splitlines()[0]
    gpu, usada, total = [float(x) for x in saida.split(",")]
    return round(gpu, 1), round((usada / total) * 100, 1)


def _gpu_windows_generico():
    """AMD / Intel / qualquer GPU: contadores de desempenho do Windows via WMI.

    Usa classes WMI (não dependem do idioma do Windows, ao contrário do Get-Counter).
    Devolve o uso do motor 3D em %. O Windows não informa o total de VRAM por
    contador, então o percentual de VRAM fica None nesse caminho.
    """
    ps = (
        "$e=(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine "
        "| Where-Object { $_.Name -like '*engtype_3D*' } "
        "| Measure-Object UtilizationPercentage -Sum).Sum; "
        "Write-Output $e"
    )
    saida = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, text=True, timeout=8, creationflags=_NO_WINDOW
    ).stdout.strip()
    gpu = float(saida.replace(",", ".")) if saida else 0.0
    return round(min(gpu, 100.0), 1), None


def obter_telemetria_gpu_vram():
    """Retorna (gpu_%, vram_%). Usa nvidia-smi se existir; senão, contadores do Windows.

    Nunca devolve valores inventados: se nada funcionar, devolve (None, None).
    """
    global _avisou_gpu
    try:
        if shutil.which("nvidia-smi"):
            return _gpu_nvidia()
        return _gpu_windows_generico()
    except Exception as e:
        if not _avisou_gpu:
            print(f"[AVISO] Não consegui ler GPU/VRAM: {e}")
            _avisou_gpu = True
        return None, None


def iniciar_monitoramento_tempo_real(limite_fps=30.0, segundos_consecutivos=10, delay_inicio_jogo=120):
    print("[RODALISO] Monitoramento de Hardware em Tempo Real (via PresentMon ETW) Ativado...")
    print(f"[CONFIG] Alvo: {limite_fps} FPS | Tolerância: {segundos_consecutivos}s | Aquecimento: {delay_inicio_jogo}s")

    if not rodando_como_admin():
        print("[AVISO] Não estou rodando como Administrador. O PresentMon pode falhar. "
              "Abra o terminal/VS Code como Administrador ou adicione seu usuário ao grupo 'Performance Log Users'.")

    jogo_anterior = None
    inicio_abaixo_limite = None  # instante (time.monotonic) em que o FPS caiu abaixo do alvo
    avisou_pausa = False

    psutil.cpu_percent(interval=None)  # "aquece" o contador de CPU (a 1ª chamada sempre retorna 0.0)

    while True:
        # ---- Botão PAUSAR: sem medir, sem PresentMon, sem alertas, até o ATIVAR AGENTE ----
        if agente_pausado():
            if not avisou_pausa:
                print("\n[RODALISO] ⏸️ Agente pausado: nenhuma medição será feita até você clicar em ATIVAR AGENTE.")
                avisou_pausa = True
            inicio_abaixo_limite = None
            time.sleep(1)
            continue
        if avisou_pausa:
            print("[RODALISO] ▶️ Agente retomado.")
            avisou_pausa = False

        limite_fps = _fps_alvo_atual(limite_fps)  # acompanha a meta escolhida na interface
        jogo_atual, exe_jogo = detectar_jogo_ativo()

        if jogo_atual:
            # Se o jogo acabou de ser iniciado no Windows, aguarda o tempo de aquecimento (2 min)
            if jogo_atual != jogo_anterior:
                print(f"\n🎮 [JOGO DETECTADO] '{jogo_atual}' em execução!")
                print(f"⏳ Aguardando {delay_inicio_jogo}s de aquecimento (menus e telas de carregamento)...")
                if not _dormir(delay_inicio_jogo):  # pausado durante o aquecimento
                    continue
                jogo_anterior = jogo_atual
                inicio_abaixo_limite = None
                print("▶️ Aquecimento concluído. Medindo FPS real via PresentMon...")

            # A medição de FPS já leva ~2-3s, então CPU usa a média desde a última volta (sem sleep extra)
            fps_atual = medir_fps_presentmon(exe_jogo, duracao_segundos=2, debug=True)
            cpu_usage = psutil.cpu_percent(interval=None)
            ram_usage = psutil.virtual_memory().percent
            gpu_usage, vram_usage = obter_telemetria_gpu_vram()

            # Falha de leitura NÃO é "FPS baixo": ignora esta rodada e tenta de novo
            if fps_atual is None:
                inicio_abaixo_limite = None
                time.sleep(1)
                continue

            print(f"[{jogo_atual}] FPS Real: {fps_atual} | CPU: {cpu_usage}% | GPU: {gpu_usage}% | "
                  f"RAM: {ram_usage}% | VRAM: {vram_usage}%")

            # CPU/RAM no limite: sugere fechar apps em segundo plano (só com confirmação do usuário)
            try:
                msg_recursos = verificar_recursos(jogo_atual, cpu_usage, ram_usage)
            except Exception as e:
                msg_recursos = f"Erro no otimizador de recursos: {e}"
            if msg_recursos:
                print(f"[RODALISO] {msg_recursos}")
                inicio_abaixo_limite = None  # a janela bloqueia o loop: recomeça a contagem de FPS

            if fps_atual < limite_fps:
                if inicio_abaixo_limite is None:
                    inicio_abaixo_limite = time.monotonic()
                tempo_abaixo = time.monotonic() - inicio_abaixo_limite
                print(f"⚠️ FPS abaixo de {limite_fps:.0f}! Há {tempo_abaixo:.0f}s/{segundos_consecutivos}s")

                if tempo_abaixo >= segundos_consecutivos:
                    print(f"\n🚨 [ALERTA RODALISO] Desempenho instável detectado por {segundos_consecutivos}s! Invocando Agente de IA...")

                    telemetria = {
                        "jogo": jogo_atual,
                        "fps_atual": fps_atual,
                        "fps_alvo": limite_fps,
                        "cpu_usage": cpu_usage,
                        "gpu_usage": gpu_usage,
                        "ram_usage": ram_usage,
                        "vram_usage": vram_usage
                    }

                    try:
                        estado = agente_rodaliso.invoke({"telemetria": telemetria})
                        print(f"[RODALISO] Resultado: {estado.get('status_final') or 'Sugestão recusada pelo usuário (nada foi alterado).'}")
                    except Exception as e:
                        print(f"❌ Erro ao invocar agente: {e}")

                    # Pausa pós-otimização para evitar acionamentos em loop (o PAUSAR também interrompe esta espera)
                    print("[RODALISO] Pausa de 120s de cooldown pós-otimização...")
                    _dormir(120)
                    inicio_abaixo_limite = None
            else:
                inicio_abaixo_limite = None
        else:
            jogo_anterior = None
            inicio_abaixo_limite = None
            print("[RODALISO] Aguardando um jogo compatível ser iniciado no Windows...", end="\r")
            time.sleep(3)


if __name__ == "__main__":
    try:
        iniciar_monitoramento_tempo_real()
    except KeyboardInterrupt:
        print("\n[RODALISO] Monitoramento encerrado pelo usuário.")
